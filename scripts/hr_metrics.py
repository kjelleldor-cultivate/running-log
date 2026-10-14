#!/usr/bin/env python3
"""Turn Strava heart-rate streams into per-run metrics in data/hr.json.

Usage:
  python3 scripts/hr_metrics.py streams.json [more.json ...]

Each input file maps activity id -> the raw output of the Strava connector's
get_activity_streams tool (streams: time, heart_rate, distance; resolution 60):
  {"20582221569": {"time": [...], "heart_rate": [...], "distance": [...]}}

Per run it stores:
  avg_hr, max_hr  time-weighted while moving
  zs              seconds in each of the 5 heart-rate zones
  ef              efficiency: metres per minute per heartbeat (higher = fitter)
  drift           Pa:HR decoupling in % for runs of 40+ min (under ~5% = good
                  aerobic endurance at that pace)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hr.json"
# Strava zones (upper bounds of Z1-Z4); refreshed from get_athlete_zones when known
DEFAULT_ZONES = [118, 147, 161, 176]


def segments(s):
    t, hr, d = s.get("time") or [], s.get("heart_rate") or [], s.get("distance") or []
    n = min(len(t), len(hr), len(d))
    out = []
    for i in range(1, n):
        dt, dd = t[i] - t[i - 1], d[i] - d[i - 1]
        if dt <= 0 or dt > 180:  # long gap = paused watch
            continue
        out.append({"t": t[i], "dt": dt, "hr": (hr[i] + hr[i - 1]) / 2, "v": dd / dt})
    return out


def metrics(s, zones):
    seg = segments(s)
    if len(seg) < 10:
        return None
    zs = [0] * 5
    for x in seg:
        z = next((i for i, ub in enumerate(zones) if x["hr"] <= ub), 4)
        zs[z] += x["dt"]
    mov = [x for x in seg if x["v"] >= 1.2]  # ignore standing / walking breaks
    if len(mov) < 10:
        return None
    w = lambda xs, k: sum(x[k] * x["dt"] for x in xs) / sum(x["dt"] for x in xs)
    total = sum(x["dt"] for x in mov)
    # skip the first 10% as warm-up for efficiency and drift
    acc, body = 0, []
    for x in mov:
        acc += x["dt"]
        if acc > total * 0.1:
            body.append(x)
    hr_b, v_b = w(body, "hr"), w(body, "v")
    out = {
        "avg_hr": round(w(mov, "hr")),
        "max_hr": round(max(x["hr"] for x in seg)),
        "zs": [round(z) for z in zs],
        "ef": round(v_b * 60 / hr_b, 3),
        "drift": None,
    }
    if total >= 40 * 60:
        half, acc, a, b = sum(x["dt"] for x in body) / 2, 0, [], []
        for x in body:
            (a if acc < half else b).append(x)
            acc += x["dt"]
        r1, r2 = w(a, "v") / w(a, "hr"), w(b, "v") / w(b, "hr")
        out["drift"] = round((r1 - r2) / r1 * 100, 1)
    return out


def main(paths):
    data = json.loads(OUT.read_text()) if OUT.exists() else {"zones": DEFAULT_ZONES, "runs": {}}
    zones = data.get("zones") or DEFAULT_ZONES
    n = 0
    for p in paths:
        for rid, s in json.loads(pathlib.Path(p).read_text()).items():
            m = metrics(s, zones)
            if m:
                data["runs"][str(rid)] = m
                n += 1
    OUT.write_text(json.dumps(data, indent=1))
    print(f"{n} runs processed, {len(data['runs'])} with heart rate data")


if __name__ == "__main__":
    main(sys.argv[1:])
