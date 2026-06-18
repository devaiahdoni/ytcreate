import os
import asyncio
from typing import List, Optional, Tuple
from pathlib import Path
from config.settings import settings
from loguru import logger

# Import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

class YouTubeService:
    def __init__(self):
        self.client_id = settings.YOUTUBE_CLIENT_ID or os.environ.get("YOUTUBE_CLIENT_ID")
        self.client_secret = settings.YOUTUBE_CLIENT_SECRET or os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = settings.YOUTUBE_REFRESH_TOKEN or os.environ.get("YOUTUBE_REFRESH_TOKEN")
        
        self.is_mocked = not (GOOGLE_LIBS_AVAILABLE and self.client_id and self.client_secret and self.refresh_token)
        
        if self.is_mocked:
            logger.warning(
                "YouTube credentials missing or googleapiclient not installed. YouTubeService will run in MOCK mode."
            )

    def _get_credentials(self) -> Any:
        """Create Credentials object from configuration settings."""
        if self.is_mocked:
            return None
        return Credentials(
            token=None,  # Will refresh automatically
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
        )

    async def upload_video(self, video_path: str, title: str, description: str, tags: Optional[List[str]] = None, category_id: str = "22", privacy_status: str = "private") -> str:
        """Upload video to YouTube and return the uploaded Video ID."""
        if self.is_mocked:
            logger.info(f"[Mock] Uploading video {video_path} to YouTube: Title='{title}'")
            await asyncio.sleep(2)  # Simulate network latency
            return "dQw4w9WgXcQ"  # Return a mock video ID

        def _execute_upload():
            creds = self._get_credentials()
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title[:100],  # YouTube titles are limited to 100 chars
                    "description": description[:5000],
                    "tags": tags or [],
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024,
                resumable=True,
                mimetype="video/mp4"
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploading video... {int(status.progress() * 100)}% complete.")
            
            video_id = response.get("id")
            if not video_id:
                raise ValueError("YouTube upload succeeded but no video ID was returned.")
            logger.info(f"Video uploaded successfully. Video ID: {video_id}")
            return video_id

        try:
            return await asyncio.to_thread(_execute_upload)
        except Exception as e:
            logger.error(f"Error in YouTube upload: {e}")
            raise e

    async def set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """Upload and associate a custom thumbnail image with the YouTube video."""
        if self.is_mocked:
            logger.info(f"[Mock] Setting thumbnail {thumbnail_path} for YouTube video {video_id}")
            await asyncio.sleep(1)
            return

        def _execute_thumbnail():
            creds = self._get_credentials()
            youtube = build("youtube", "v3", credentials=creds)

            request = youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png")
            )
            response = request.execute()
            logger.info(f"Custom thumbnail set successfully for video {video_id}. Response: {response}")

        try:
            await asyncio.to_thread(_execute_thumbnail)
        except Exception as e:
            logger.error(f"Error setting YouTube thumbnail: {e}")
            raise e

    async def publish_video(self, video_id: str, privacy_status: str = "public") -> None:
        """Update video status/privacy setting to public/unlisted/private."""
        if self.is_mocked:
            logger.info(f"[Mock] Publishing YouTube video {video_id} to status '{privacy_status}'")
            return

        def _execute_publish():
            creds = self._get_credentials()
            youtube = build("youtube", "v3", credentials=creds)

            # Retrieve existing snippet to avoid overwriting metadata
            video_response = youtube.videos().list(part="snippet", id=video_id).execute()
            items = video_response.get("items", [])
            if not items:
                raise ValueError(f"Video with ID {video_id} not found.")
            
            snippet = items[0]["snippet"]

            body = {
                "id": video_id,
                "snippet": snippet,
                "status": {
                    "privacyStatus": privacy_status
                }
            }

            request = youtube.videos().update(part="snippet,status", body=body)
            response = request.execute()
            logger.info(f"Video {video_id} publication status updated to {privacy_status}. Response: {response}")

        try:
            await asyncio.to_thread(_execute_publish)
        except Exception as e:
            logger.error(f"Error publishing YouTube video: {e}")
            raise e

from typing import Any
