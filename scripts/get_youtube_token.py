"""
Run this ONCE locally to get your YouTube refresh token.
After running, copy the refresh_token into your GitHub secret YOUTUBE_REFRESH_TOKEN.

Usage:
  pip install google-auth-oauthlib
  python scripts/get_youtube_token.py
"""

import json
import os

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Run: pip install google-auth-oauthlib")
    raise

SCOPES = ["https://www.googleapis.com/auth/youtube"]

CLIENT_ID = input("Paste your YouTube OAuth Client ID: ").strip()
CLIENT_SECRET = input("Paste your YouTube OAuth Client Secret: ").strip()

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== YOUR TOKENS ===")
print(f"YOUTUBE_CLIENT_ID={CLIENT_ID}")
print(f"YOUTUBE_CLIENT_SECRET={CLIENT_SECRET}")
print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
print("\nCopy these into your GitHub repo secrets.")
