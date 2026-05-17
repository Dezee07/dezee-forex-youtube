"""
Uploads 3 educational Shorts to YouTube daily.
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
    info = json.loads(os.environ["YOUTUBE_CREDENTIALS"])
    creds = Credentials(
        token=None,  # force refresh — don't rely on the stored short-lived token
        refresh_token=info["refresh_token"],
        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=info["client_id"],
        client_secret=info["client_secret"],
        scopes=info.get("scopes", ["https://www.googleapis.com/auth/youtube"]),
    )
    creds.refresh(Request())  # always refresh upfront so we have a valid token
    return build("youtube", "v3", credentials=creds)


def upload_short(youtube, video_path: str, title: str, description: str, tags: list) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": [t.strip("#") for t in tags][:30],
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5*1024*1024)
    req   = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"    {int(status.progress()*100)}%")

    return response["id"]


def set_thumbnail(youtube, video_id: str, thumb_path: str):
    if not os.path.exists(thumb_path):
        return
    try:
        media = MediaFileUpload(thumb_path, mimetype="image/jpeg")
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"    Thumbnail set.")
    except HttpError as e:
        print(f"    Thumbnail error: {e}")


def main():
    if not os.environ.get("YOUTUBE_CREDENTIALS"):
        print("ERROR: YOUTUBE_CREDENTIALS not set")
        sys.exit(1)

    with open("data/video_content.json") as f:
        content = json.load(f)

    shorts = content["shorts"]
    youtube = get_youtube_client()
    results = []

    for short in shorts:
        idx       = short["index"]
        vid_path  = f"output/short_{idx}.mp4"
        thumb_path = f"output/thumb_{idx}.jpg"

        if not os.path.exists(vid_path):
            print(f"WARNING: {vid_path} not found, skipping")
            continue

        title   = short["title"]
        caption = short["caption"]
        tags    = short.get("hashtags", [])

        print(f"\nUploading Short {idx}: {title}")
        try:
            vid_id = upload_short(youtube, vid_path, title, caption, tags)
            print(f"  Uploaded: https://youtu.be/{vid_id}")
            set_thumbnail(youtube, vid_id, thumb_path)
            results.append({"index": idx, "topic": short["topic"], "video_id": vid_id})
        except HttpError as e:
            print(f"  Error: {e}")

    with open("data/upload_results.json", "w") as f:
        json.dump({"uploaded_at": datetime.utcnow().isoformat(), "videos": results}, f, indent=2)

    print(f"\nDone. {len(results)}/{len(shorts)} Shorts uploaded.")


if __name__ == "__main__":
    main()
