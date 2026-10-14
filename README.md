# Kjell Eldor's Running Log

A one-page running dashboard built from my Strava activities.

**Live:** https://kjelleldor-cultivate.github.io/running-log/

- `index.html` is the whole dashboard (d3, no build step).
- `data/runs.json` holds every run. The **Refresh** button re-reads it.
- `scripts/merge.py` merges new Strava activities into `runs.json`. A daily
  scheduled Claude task pulls new runs from Strava, runs the merge and pushes.

Treadmill runs (no GPS location) and runs flagged `walk`, `gps` or `dup` in the
data are left out of pace stats.
