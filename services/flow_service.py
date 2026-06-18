import os
import asyncio
import httpx
from typing import Dict, Any, Tuple
from pathlib import Path
from config.settings import settings
from loguru import logger

class FlowService:
    def __init__(self):
        self.api_key = settings.FLOW_API_KEY or os.environ.get("FLOW_API_KEY", "mock-key")
        self.api_url = settings.FLOW_API_URL
        self.is_mocked = self.api_key == "mock-key"
        
        if self.is_mocked:
            logger.warning("Google Flow API key not provided. Running FlowService in MOCK mode.")

    async def submit_video_generation(self, prompt: str, duration: float = 5.0) -> str:
        """Submit a prompt to Google Flow (Veo) for video generation. Returns a Job ID."""
        if self.is_mocked:
            # Simulate job submission and return a dummy job ID
            import uuid
            job_id = f"flow-job-{uuid.uuid4()}"
            logger.info(f"[Mock] Submitted video prompt: '{prompt[:30]}...', Job ID: {job_id}")
            return job_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "duration_seconds": duration,
            "aspect_ratio": "16:9",
            "resolution": "720p"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/videos:generate",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                # Assuming response schema returns a field named "name" or "id"
                job_id = data.get("name") or data.get("id") or data.get("job_id")
                if not job_id:
                    raise ValueError(f"Unexpected response format: {data}")
                return job_id
        except Exception as e:
            logger.error(f"Error in FlowService submit_video_generation: {e}")
            raise e

    async def check_status(self, job_id: str) -> Tuple[str, Optional[str]]:
        """Check status of video generation. Returns (status, download_url)."""
        if self.is_mocked:
            # Mock status progression: always returns COMPLETED with a mock URL
            logger.debug(f"[Mock] Checking status for job: {job_id} -> COMPLETED")
            return "COMPLETED", "https://example.com/mock_video.mp4"

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/operations/{job_id}",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Check operation status. Standard Google API LRO (Long Running Operations) schema:
                # { "name": "...", "done": true, "response": { "videoUrl": "..." } } or "error"
                done = data.get("done", False)
                if done:
                    error = data.get("error")
                    if error:
                        logger.error(f"Flow generation job {job_id} failed: {error}")
                        return "FAILED", None
                    
                    response_payload = data.get("response", {})
                    video_url = response_payload.get("videoUrl") or response_payload.get("url")
                    return "COMPLETED", video_url
                else:
                    return "RUNNING", None
        except Exception as e:
            logger.error(f"Error in FlowService check_status: {e}")
            return "FAILED", None

    async def download_video(self, url: str, dest_path: str, duration: float = 5.0) -> None:
        """Download video file from url or generate mock video if mocked."""
        dest_dir = Path(dest_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if self.is_mocked or not url.startswith("http"):
            logger.info(f"[Mock] Creating a local dummy MP4 video clip at {dest_path}")
            # Generate a real color MP4 using MoviePy so subsequent compose steps succeed
            try:
                from moviepy.editor import ColorClip
                # Create a 5-second blue clip at 1280x720
                clip = ColorClip(size=(1280, 720), color=(18, 18, 36), duration=duration)
                # Ensure write operates in a thread pool to not block async execution
                await asyncio.to_thread(
                    clip.write_videofile,
                    dest_path,
                    fps=24,
                    codec="libx264",
                    audio=False,
                    logger=None
                )
                clip.close()
                logger.info(f"[Mock] Dummy video successfully created: {dest_path}")
            except Exception as e:
                logger.error(f"Failed to generate mock video via MoviePy: {e}. Writing a dummy empty file.")
                # Fallback: write a 0-byte file (though it might break MoviePy later)
                with open(dest_path, "wb") as f:
                    f.write(b"")
            return

        # Real download logic
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(dest_path, "wb") as f:
                        async for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
            logger.info(f"Successfully downloaded video from {url} to {dest_path}")
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            raise e
