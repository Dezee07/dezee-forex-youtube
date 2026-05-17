"""
Uploads rendered videos to YouTube using the official Google API client library.
Requires: YOUTUBE_CREDENTIALS env var (JSON string with full OAuth credentials).
"""

import json
import os
import sys
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def get_youtube_client():
    creds_json = os.environ.get("YOUTUBE_CREDENTIALS")
    if not creds_json:
        print("ERROR: YOUTUBE_CREDENTIALS secret not set")
        sys.exit(1)

    info = json.loads(creds_json)
    creds = Credentials(
        token=info.get("token"),
        refresh_token=info["refresh_token"],
        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=info["client_id"],
        client_secret=info["client_secret"],
        scopes=info.get("scopes", ["https://www.googleapis.com/auth/youtube"]),
    )

    # Refresh if expired
    if not creds.valid:
        print("Refreshing credentials...")
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: str, title: str, description: str, tags: list) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": [t.strip() for t in tags][:500],
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Upload {pct}%")

    return response["id"]


def main():
    with open("data/video_content.json") as f:
        content = json.load(f)

    meta = content["meta"]
    tags = meta["tags"] if isinstance(meta["tags"], list) else [t.strip() for t in meta["tags"].split(",")]

    print("Connecting to YouTube API...")
    youtube = get_youtube_client()
    print("Connected.")

    results = {}

    longform_path = "output/longform.mp4"
    if os.path.exists(longform_path):
        print(f"Uploading: {meta['title']}")
        try:
            vid_id = upload_video(youtube, longform_path, meta["title"], meta["description"], tags)
            print(f"  Done: https://youtu.be/{vid_id}")
            results["longform_id"] = vid_id
        except HttpError as e:
            print(f"  Error: {e}")
    else:
        print("WARNING: longform.mp4 not found")

    shorts_path = "output/shorts.mp4"
    if os.path.exists(shorts_path):
        shorts_title = meta.get("shorts_title", meta["title"][:50])
        if "#Shorts" not in shorts_title:
            shorts_title = f"{shorts_title} #Shorts"
        print(f"Uploading Short: {shorts_title}")
        try:
            short_id = upload_video(youtube, shorts_path, shorts_title,
                                    f"{meta['description']}\n\n#Shorts #Forex #COT",
                                    tags + ["Shorts"])
            print(f"  Done: https://youtu.be/{short_id}")
            results["shorts_id"] = short_id
        except HttpError as e:
            print(f"  Error: {e}")
    else:
        print("WARNING: shorts.mp4 not found")

    with open("data/upload_results.json", "w") as f:
        json.dump({"uploaded_at": datetime.utcnow().isoformat(), **results}, f, indent=2)

    print("\nAll done.")


if __name__ == "__main__":
    main()
