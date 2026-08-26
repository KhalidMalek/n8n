from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    def __init__(self, privacy_status: str = "private", category_id: str = "28") -> None:
        self.privacy_status = privacy_status
        self.category_id = category_id
        self.token_file = Path(os.getenv("YOUTUBE_TOKEN_FILE", "/app/secrets/youtube_token.json"))

    def _service(self):
        if not self.token_file.exists():
            raise RuntimeError(
                "YouTube OAuth token is missing. Run scripts/youtube_auth.py once, then keep the generated token in secrets/."
            )
        creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        if not creds.valid:
            raise RuntimeError("YouTube OAuth token is invalid; run the one-time authorization script again.")
        return build("youtube", "v3", credentials=creds)

    def upload(
        self,
        video_path: Path,
        thumbnail_path: Path,
        title: str,
        description: str,
        tags: list[str],
    ) -> str:
        youtube = self._service()
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags[:30],
                    "categoryId": self.category_id,
                },
                "status": {"privacyStatus": self.privacy_status, "selfDeclaredMadeForKids": False},
            },
            media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response["id"]
        if thumbnail_path.exists():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
        return video_id
