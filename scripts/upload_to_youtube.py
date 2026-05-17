"""
Uploads rendered videos to YouTube using the YouTube Data API v3.
Handles both long-form videos and Shorts.
Requires: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN as env vars.
"""

import json
import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path


TOKEN_URL = "https://oauth2.googleapis.com/token"
YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"


def get_access_token() -> str:
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]

    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=15)
    if not resp.ok:
        print(f"Token error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()["access_token"]


def upload_video(
    access_token: str,
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    is_shorts: bool = False,
    schedule_time: str = None,
) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}

    category_id = "22"  # People & Blogs (good for finance content)
    privacy = "private" if schedule_time else "public"

    snippet = {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags[:500],
        "categoryId": category_id,
        "defaultLanguage": "en",
    }

    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if schedule_time:
        status["privacyStatus"] = "private"
        status["publishAt"] = schedule_time

    metadata = json.dumps({"snippet": snippet, "status": status}).encode()

    # Resumable upload
    init_resp = requests.post(
        YT_UPLOAD_URL,
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            **headers,
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(os.path.getsize(video_path)),
        },
        data=metadata,
        timeout=30,
    )
    init_resp.raise_for_status()
    upload_url = init_resp.headers["Location"]

    # Upload file in chunks
    chunk_size = 5 * 1024 * 1024  # 5MB chunks
    file_size = os.path.getsize(video_path)
    video_id = None

    with open(video_path, "rb") as f:
        start = 0
        while start < file_size:
            chunk = f.read(chunk_size)
            end = start + len(chunk) - 1
            upload_resp = requests.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Type": "video/mp4",
                },
                data=chunk,
                timeout=120,
            )
            if upload_resp.status_code in (200, 201):
                video_id = upload_resp.json()["id"]
                break
            elif upload_resp.status_code == 308:
                start = int(upload_resp.headers.get("Range", f"bytes=0-{end}").split("-")[1]) + 1
            else:
                upload_resp.raise_for_status()

    return video_id


def add_thumbnail(access_token: str, video_id: str, thumbnail_path: str):
    if not os.path.exists(thumbnail_path):
        return
    headers = {"Authorization": f"Bearer {access_token}"}
    with open(thumbnail_path, "rb") as f:
        resp = requests.post(
            f"{YT_API_BASE}/thumbnails/set",
            params={"videoId": video_id},
            headers={**headers, "Content-Type": "image/jpeg"},
            data=f.read(),
            timeout=30,
        )
    if resp.status_code == 200:
        print(f"  Thumbnail set for {video_id}")


def main():
    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    with open("data/video_content.json") as f:
        content = json.load(f)

    meta = content["meta"]
    access_token = get_access_token()

    results = {}

    # Upload long-form video
    longform_path = "output/longform.mp4"
    if os.path.exists(longform_path):
        print(f"Uploading long-form video: {meta['title']}")
        video_id = upload_video(
            access_token=access_token,
            video_path=longform_path,
            title=meta["title"],
            description=meta["description"],
            tags=meta["tags"] if isinstance(meta["tags"], list) else meta["tags"].split(","),
        )
        print(f"  Uploaded: https://youtu.be/{video_id}")
        results["longform_id"] = video_id

        # Set thumbnail if exists
        add_thumbnail(access_token, video_id, "output/thumbnail.jpg")
    else:
        print("WARNING: longform.mp4 not found, skipping")

    # Upload Shorts
    shorts_path = "output/shorts.mp4"
    if os.path.exists(shorts_path):
        shorts_title = meta.get("shorts_title", meta["title"][:50] + " #Shorts")
        if "#Shorts" not in shorts_title:
            shorts_title = f"{shorts_title} #Shorts"
        print(f"Uploading Short: {shorts_title}")
        shorts_id = upload_video(
            access_token=access_token,
            video_path=shorts_path,
            title=shorts_title,
            description=f"{meta['description']}\n\n#Shorts #Forex #COT",
            tags=(meta["tags"] if isinstance(meta["tags"], list) else meta["tags"].split(",")) + ["Shorts"],
            is_shorts=True,
        )
        print(f"  Uploaded Short: https://youtu.be/{shorts_id}")
        results["shorts_id"] = shorts_id
    else:
        print("WARNING: shorts.mp4 not found, skipping")

    with open("data/upload_results.json", "w") as f:
        json.dump({"uploaded_at": datetime.utcnow().isoformat(), **results}, f, indent=2)

    print("\nAll uploads complete.")


if __name__ == "__main__":
    main()
