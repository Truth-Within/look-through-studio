"""Stage 5 (optional): resumable upload to YouTube Data API v3."""
import random
import time
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN = Path("token.json")
SECRETS = Path("client_secret.json")


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not SECRETS.exists():
                raise FileNotFoundError("client_secret.json missing (see README, 'Uploading')")
            creds = InstalledAppFlow.from_client_secrets_file(str(SECRETS), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return creds


def upload(video, script, thumbnail=None, shorts=False, privacy="private", publish_at=None):
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=_credentials())
    title = script["title"][:100]
    desc = script.get("description", "")
    if shorts and "#shorts" not in (title + desc).lower():
        desc += "\n\n#Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": script.get("tags", [])[:15],
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(script.get("contains_synthetic_media", False)),
        },
    }
    if publish_at:  # scheduled release: must be private until the time arrives
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at
    # chunk size must be a multiple of 256 KB; 8 MB = 32 x 256 KB
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    resp, retries = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status:
                print(f"  uploaded {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < 8:
                retries += 1
                time.sleep(2**retries + random.random())
            else:
                raise

    vid = resp["id"]
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail))).execute()
        except HttpError as e:
            print(f"  thumbnail not set (channel may need verification): {e}")
    return f"https://youtu.be/{vid}"
