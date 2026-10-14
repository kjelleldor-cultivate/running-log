#!/usr/bin/env python3
"""Run this ONCE on your own computer to create a GARMINTOKENS secret.

Use it if your Garmin account has two-step verification turned on, or if the
GitHub Action's login gets blocked. It logs in (asking for your code if needed)
and prints a long token string. Paste that into a repository secret called
GARMINTOKENS. Tokens last about a year; run this again if the sync starts failing.

  pip install garminconnect
  python3 garmin_token.py
"""
import getpass
from garminconnect import Garmin

email = input("Garmin email: ").strip()
pw = getpass.getpass("Garmin password: ")
api = Garmin(email, pw, prompt_mfa=lambda: input("Two-step verification code: ").strip())
api.login()
print("\nCopy everything on the next line into a GitHub secret called GARMINTOKENS:\n")
print(api.garth.dumps())
