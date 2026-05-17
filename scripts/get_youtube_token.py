"""
Run this ONCE locally to get your YouTube credentials JSON.
Paste the entire JSON output as the YOUTUBE_CREDENTIALS secret in GitHub.

Usage:
  pip install google-auth-oauthlib google-api-python-client
  python scripts/get_youtube_token.py
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

CLIENT_ID = input("Paste your YouTube OAuth Client ID: ").strip()
CLIENT_SECRET = input("Paste your YouTube OAuth Client Secret: ").strip()

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=8080, access_type="offline", prompt="consent")

credentials_json = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scopes": SCOPES,
}

output = json.dumps(credentials_json)

print("\n=== COPY THIS ENTIRE LINE AS YOUR GITHUB SECRET ===")
print(f"Secret name: YOUTUBE_CREDENTIALS")
print(f"Secret value: {output}")
print("\nAdd this as a single secret in GitHub Actions.")
