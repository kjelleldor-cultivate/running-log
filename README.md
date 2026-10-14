# Kjell Eldor's Running Log

A one-page running dashboard built from my Strava activities.

**Live:** https://kjelleldor-cultivate.github.io/running-log/

- `index.html` is the whole dashboard (d3, no build step).
- `data/runs.json` holds every run. The **Refresh** button re-reads it.
- `scripts/merge.py` merges new Strava activities into `runs.json`. A daily
  scheduled Claude task pulls new runs from Strava, runs the merge and pushes.

Treadmill runs (no GPS location) and runs flagged `walk`, `gps` or `dup` in the
data are left out of pace stats.

## Garmin recovery data (encrypted)

A GitHub Action (`.github/workflows/garmin.yml`) runs every morning, pulls HRV,
resting heart rate, sleep, Body Battery, stress, steps, VO2 max and training
readiness from Garmin Connect, and saves them **encrypted** to
`data/garmin.enc.json`. The dashboard asks for the password and decrypts in the
browser. Without the password the file is unreadable, even though the repo is public.

Repository secrets (Settings → Secrets and variables → Actions):

| Secret | What |
|---|---|
| `DASHBOARD_PASSWORD` | The password you'll type on the dashboard. 8+ characters; longer is better. |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | Your Garmin Connect login. |
| `GARMINTOKENS` | Optional. Use instead of email/password if you have two-step verification. Create with `scripts/garmin_token.py`. |

Changing `DASHBOARD_PASSWORD` later: delete `data/garmin.enc.json`, update the
secret, then run the workflow with days = 180 to rebuild it.

The Garmin side uses the unofficial `garminconnect` library, so it may break
when Garmin changes its login. Check the Actions tab if the data stops updating.
