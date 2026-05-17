"""
Uploads rendered videos to YouTube using the official Google API client library.
Requires: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN as env vars.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def get_youtube_client():
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_video(
    youtube,
    video_path: str,
    title: str,
    description: str,
    tags: list,
    is_shorts: bool = False,
) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
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
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    return response["id"]


def main():
    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    with open("data/video_content.json") as f:
        content = json.load(f)

    meta = content["meta"]
    tags = meta["tags"] if isinstance(meta["tags"], list) else meta["tags"].split(",")

    print("Connecting to YouTube API...")
    youtube = get_youtube_client()

    results = {}

    # Upload long-form video
    longform_path = "output/longform.mp4"
    if os.path.exists(longform_path):
        print(f"Uploading long-form: {meta['title']}")
        try:
            video_id = upload_video(
                youtube=youtube,
                video_path=longform_path,
                title=meta["title"],
                description=meta["description"],
                tags=tags,
            )
            print(f"  Uploaded: https://youtu.be/{video_id}")
            results["longform_id"] = video_id
        except HttpError as e:
            print(f"  Upload error: {e}")
    else:
        print("WARNING: longform.mp4 not found, skipping")

    # Upload Shorts
    shorts_path = "output/shorts.mp4"
    if os.path.exists(shorts_path):
        shorts_title = meta.get("shorts_title", meta["title"][:50])
        if "#Shorts" not in shorts_title:
            shorts_title = f"{shorts_title} #Shorts"
        print(f"Uploading Short: {shorts_title}")
        try:
            shorts_id = upload_video(
                youtube=youtube,
                video_path=shorts_path,
                title=shorts_title,
                description=f"{meta['description']}\n\n#Shorts #Forex #COT",
                tags=tags + ["Shorts"],
                is_shorts=True,
            )
            print(f"  Uploaded Short: https://youtu.be/{shorts_id}")
            results["shorts_id"] = shorts_id
        except HttpError as e:
            print(f"  Short upload error: {e}")
    else:
        print("WARNING: shorts.mp4 not found, skipping")

    with open("data/upload_results.json", "w") as f:
        json.dump({"uploaded_at": datetime.utcnow().isoformat(), **results}, f, indent=2)

    print("\nDone.")


if __name__ == "__main__":
    main()
