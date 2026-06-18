import asyncio
from services.flow_service import FlowService
from loguru import logger

class FlowAgent:
    def __init__(self, flow_service: FlowService):
        self.flow_service = flow_service

    async def submit_scene(self, scene_id: int, prompt: str, duration: float = 5.0) -> str:
        """Submit scene visual prompt for video generation."""
        logger.info(f"FlowAgent: Submitting video generation job for scene {scene_id}")
        try:
            job_id = await self.flow_service.submit_video_generation(prompt, duration)
            logger.info(f"FlowAgent: Scene {scene_id} submitted. Flow Job ID: {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"FlowAgent: Submission failed for scene {scene_id}: {e}")
            raise e

    async def check_status(self, job_id: str) -> tuple[str, str]:
        """Poll Google Flow for the job status. Returns (status, download_url)."""
        logger.debug(f"FlowAgent: Checking status of job {job_id}")
        return await self.flow_service.check_status(job_id)

    async def wait_for_completion(self, job_id: str, poll_interval: float = 5.0, timeout: float = 300.0) -> str:
        """Poll job status until COMPLETED or FAILED, or timeout reached. Returns the download URL."""
        elapsed = 0.0
        while elapsed < timeout:
            status, url = await self.check_status(job_id)
            if status == "COMPLETED":
                if not url:
                    raise ValueError(f"Job {job_id} completed but returned no video URL.")
                logger.info(f"FlowAgent: Job {job_id} succeeded.")
                return url
            elif status == "FAILED":
                raise RuntimeError(f"FlowAgent: Video generation job {job_id} failed on Google Flow.")
            
            logger.debug(f"FlowAgent: Job {job_id} is still running... Waiting {poll_interval}s.")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
        raise TimeoutError(f"FlowAgent: Video generation job {job_id} timed out after {timeout} seconds.")

    async def download_video(self, url: str, dest_path: str, duration: float = 5.0) -> None:
        """Download video file to the local filesystem."""
        logger.info(f"FlowAgent: Downloading video from {url} to {dest_path}")
        try:
            await self.flow_service.download_video(url, dest_path, duration)
            logger.info(f"FlowAgent: Downloaded video to {dest_path}")
        except Exception as e:
            logger.error(f"FlowAgent: Failed to download video: {e}")
            raise e
