import os
import json
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    token_path = Path(config.YOUTUBE_TOKEN_CACHE)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.YOUTUBE_CLIENT_SECRETS, SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds

def _upload_sync(video_path: str, title: str, description: str,
                  tags: list, privacy: str, thumbnail_path: str | None) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:30],
            "categoryId": "27",
            "defaultLanguage": "en"
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path, chunksize=-1, resumable=True, mimetype="video/mp4"
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response["id"]

    if thumbnail_path and Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()

    return f"https://youtu.be/{video_id}"

async def upload_episode(video_path: Path, seo: dict,
                          thumbnail_path: Path | None = None,
                          privacy: str = "private") -> str:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        url = await loop.run_in_executor(
            pool,
            _upload_sync,
            str(video_path),
            seo.get("title", "Untitled"),
            seo.get("description", ""),
            seo.get("tags", []),
            privacy,
            str(thumbnail_path) if thumbnail_path else None
        )
    return url
