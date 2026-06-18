from typing import List, Optional
from services.youtube_service import YouTubeService
from loguru import logger

class YouTubeAgent:
    def __init__(self, youtube_service: YouTubeService):
        self.youtube_service = youtube_service

    async def upload(self, video_path: str, title: str, description: str, tags: Optional[List[str]] = None, thumbnail_path: Optional[str] = None, publish: bool = False) -> str:
        """Orchestrates the YouTube upload flow: video upload, thumbnail binding, and optional publication."""
        logger.info(f"YouTubeAgent: Initiating upload process for video {video_path}")
        
        try:
            # 1. Upload Video
            privacy_status = "public" if publish else "private"
            video_id = await self.youtube_service.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=privacy_status
            )
            logger.info(f"YouTubeAgent: Video uploaded. Video ID: {video_id}")

            # 2. Upload Thumbnail if path is provided
            if thumbnail_path:
                logger.info(f"YouTubeAgent: Attaching custom thumbnail {thumbnail_path} to video {video_id}")
                await self.youtube_service.set_thumbnail(video_id=video_id, thumbnail_path=thumbnail_path)
                logger.info("YouTubeAgent: Custom thumbnail uploaded successfully.")

            # 3. Publish if requested and not already public
            if publish:
                logger.info(f"YouTubeAgent: Setting visibility to public for video {video_id}")
                await self.youtube_service.publish_video(video_id=video_id, privacy_status="public")
                logger.info("YouTubeAgent: Video published successfully.")

            return video_id
        except Exception as e:
            logger.error(f"YouTubeAgent failed upload sequence: {e}")
            raise e
