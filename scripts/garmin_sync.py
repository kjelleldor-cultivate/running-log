#!/usr/bin/env python3
"""Pull daily wellness metrics from Garmin Connect into data/garmin.enc.json.

Runs in GitHub Actions. Login comes from repository secrets:
  GARMINTOKENS                       (preferred: saved login tokens, see README)
  GARMIN_EMAIL + GARMIN_PASSWORD     (fallback)

The output is encrypted with DASHBOARD_PASSWORD (AES-256-GCM, key from
PBKDF2-SHA256) and written to data/garmin.enc.json. Plain wellness data is
never written into the repo. The dashboard decrypts it in the browser.

Usage: python3 scripts/garmin_sync.py [days]
  days defaults to 10 (re-checks recent days, since Garmin finalises sleep/HRV
  late). If data/garmin.enc.json does not exist yet it backfills 180 days.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "garmin.enc.json"
ITER = 310_000
b64, unb64 = (lambda b: base64.b64encode(b).decode()), base64.b64decode


def _key(pw, salt, it=ITER):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(pw.encode())


def encrypt(obj, pw):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(pw, salt)).encrypt(iv, json.dumps(obj).encode(), None)
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def decrypt(env, pw):
    key = _key(pw, unb64(env["salt"]), env.get("iter", ITER))
    return json.loads(AESGCM(key).decrypt(unb64(env["iv"]), unb64(env["ct"]), None))


def g(d, *path):
    """Safe nested get. Lists step into their first item."""
    for p in path:
        if isinstance(d, list):
            d = d[0] if d else None
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def call(fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # one missing metric shouldn't sink the day
        print(f"  {fn.__name__}: {type(e).__name__}: {str(e)[:120]}")
        return None


def login():
    tokens = os.environ.get("GARMINTOKENS", "").strip()
    if tokens:
        api = Garmin()
        api.login(tokens)
        return api
    email, pw = os.environ.get("GARMIN_EMAIL"), os.environ.get("GARMIN_PASSWORD")
    if not (email and pw):
        sys.exit("No Garmin login: set GARMINTOKENS, or GARMIN_EMAIL and GARMIN_PASSWORD, as repository secrets.")
    api = Garmin(email, pw)
    api.login()
    return api


def day(api, d):
    ds = d.isoformat()
    hrv = call(api.get_hrv_data, ds)
    sleep = call(api.get_sleep_data, ds)
    stats = call(api.get_stats, ds)
    maxm = call(api.get_max_metrics, ds)
    ready = call(api.get_training_readiness, ds)

    s = g(sleep, "dailySleepDTO") or {}
    secs = s.get("sleepTimeSeconds")
    row = {
        "date": ds,
        "hrv": g(hrv, "hrvSummary", "lastNightAvg"),
        "hrv_week": g(hrv, "hrvSummary", "weeklyAvg"),
        "hrv_low": g(hrv, "hrvSummary", "baseline", "balancedLow"),
        "hrv_high": g(hrv, "hrvSummary", "baseline", "balancedUpper"),
        "hrv_status": g(hrv, "hrvSummary", "status"),
        "rhr": g(stats, "restingHeartRate"),
        "sleep_h": round(secs / 3600, 2) if secs else None,
        "sleep_score": g(s, "sleepScores", "overall", "value"),
        "deep_h": round(s["deepSleepSeconds"] / 3600, 2) if s.get("deepSleepSeconds") else None,
        "rem_h": round(s["remSleepSeconds"] / 3600, 2) if s.get("remSleepSeconds") else None,
        "bb_high": g(stats, "bodyBatteryHighestValue"),
        "bb_low": g(stats, "bodyBatteryLowestValue"),
        "stress": g(stats, "averageStressLevel"),
        "steps": g(stats, "totalSteps"),
        "vo2": g(maxm, "generic", "vo2MaxPreciseValue") or g(maxm, "generic", "vo2MaxValue"),
        "readiness": g(ready, "score"),
    }
    # Garmin uses -1 / -2 for "no reading"
    for k, v in row.items():
        if isinstance(v, (int, float)) and v < 0:
            row[k] = None
    return row


def main():
    pw = os.environ.get("DASHBOARD_PASSWORD", "")
    if len(pw) < 8:
        sys.exit("Set a DASHBOARD_PASSWORD repository secret (8+ characters) before syncing.")
    existing = decrypt(json.loads(OUT.read_text()), pw) if OUT.exists() else {"days": []}
    days = int(sys.argv[1]) if len(sys.argv) > 1 else (10 if existing["days"] else 180)
    api = login()
    by_date = {r["date"]: r for r in existing["days"]}
    today = dt.date.today()
    for i in range(days):
        d = today - dt.timedelta(days=i)
        print(d)
        row = day(api, d)
        if any(v is not None for k, v in row.items() if k != "date"):
            by_date[row["date"]] = row
        time.sleep(0.4)
    out = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "days": sorted(by_date.values(), key=lambda r: r["date"]),
    }
    OUT.write_text(json.dumps(encrypt(out, pw)))
    print(f"{len(out['days'])} days saved")


if __name__ == "__main__":
    main()
