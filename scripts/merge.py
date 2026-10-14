#!/usr/bin/env python3
"""Merge Strava list_activities output into data/runs.json.

Usage: python3 scripts/merge.py new_activities.json [more.json ...]

Each input file is the raw JSON returned by the Strava connector's
list_activities tool ({"activities": [...]}). Only runs are kept,
existing rows are updated in place (matched on id), and manual flags
(walk / dup / gps) already in the file are preserved.
"""
import json, sys, datetime, pathlib

RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "runs.json"


def r(x, n=1):
    return None if x is None else round(float(x), n)


def to_row(a):
    s = a.get("summary", {})
    loc = (a.get("location_summary") or "").replace(", United Kingdom", "")
    return [
        str(a["id"]), a["start_local"], (a.get("name") or "Run").strip(),
        r(s.get("distance")), s.get("moving_time"), s.get("elapsed_time"),
        r(s.get("elevation_gain")), s.get("relative_effort"),
        r(s.get("avg_cadence")), r(s.get("max_speed"), 2), s.get("pr_count", 0),
        loc, a.get("gear_id"), None,
    ]


def main(paths):
    data = json.loads(DATA.read_text())
    rows = {row[0]: row for row in data["runs"]}
    added = updated = 0
    for p in paths:
        acts = json.loads(pathlib.Path(p).read_text()).get("activities", [])
        for a in acts:
            if a.get("sport_type") not in RUN_TYPES:
                continue
            if (a.get("summary", {}).get("distance") or 0) < 500:
                continue
            row = to_row(a)
            if row[0] in rows:
                row[13] = rows[row[0]][13]  # keep manual flag
                if rows[row[0]] != row:
                    updated += 1
            else:
                added += 1
            rows[row[0]] = row
            g = row[12]
            if g and g not in data["gear"]:
                data["gear"][g] = {"name": "Shoe " + g, "retired": False}
    data["runs"] = sorted(rows.values(), key=lambda x: x[1], reverse=True)
    data["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"added {added}, updated {updated}, total {len(data['runs'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
