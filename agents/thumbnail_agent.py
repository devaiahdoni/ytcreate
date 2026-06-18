import os
import httpx
import asyncio
from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from loguru import logger
from pathlib import Path

class ThumbnailDesign(BaseModel):
    thumbnail_prompt: str = Field(description="Visual generation prompt for DALL-E, focusing on bold colors, high contrast, and clear focal objects.")
    headline_text: str = Field(description="Punchy, large text overlay suggestion for the thumbnail, maximum 3-4 words.")

class ThumbnailAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, topic: str, hook: str, dest_path: str) -> tuple[ThumbnailDesign, str]:
        """Generates CTR-optimized thumbnail prompts, creates the thumbnail image, and saves it locally."""
        logger.info("ThumbnailAgent: Designing thumbnail ideas")

        system_prompt = (
            "You are an expert YouTube thumbnail designer and digital marketer. Your job is "
            "to design high-click-through-rate (CTR) thumbnail visual prompts and punchy text "
            "overlays that create curiosity or emotion and immediately draw viewers' attention."
        )

        prompt = (
            f"Create a thumbnail design for a video on the topic: '{topic}'.\n"
            f"The video's hook is: '{hook}'.\n"
            f"Generate a visual prompt for an image generation tool describing the scene, lighting, "
            f"and focal point, along with a text overlay of 3-4 words."
        )

        try:
            # 1. Generate prompt design
            design = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=ThumbnailDesign,
                system_prompt=system_prompt
            )
            logger.info(f"ThumbnailAgent: Design completed. Suggestion: '{design.headline_text}'")

            # 2. Call image generation API
            logger.info("ThumbnailAgent: Requesting image generation...")
            img_url = await self.openai_service.generate_image(design.thumbnail_prompt)
            
            # 3. Download the image locally
            logger.info(f"ThumbnailAgent: Downloading image from URL to {dest_path}")
            await self._download_file(img_url, dest_path)
            logger.info(f"ThumbnailAgent: Saved thumbnail locally to {dest_path}")
            
            return design, dest_path
        except Exception as e:
            logger.error(f"ThumbnailAgent failed: {e}")
            raise e

    async def _download_file(self, url: str, dest_path: str) -> None:
        """Download remote image URL to local filesystem."""
        dest_dir = Path(dest_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if not url.startswith("http"):
            # Mock mode: create a dummy thumbnail image
            logger.info("[Mock] Writing a dummy thumbnail image locally.")
            try:
                from PIL import Image, ImageDraw
                # Create a simple red color canvas for the thumbnail
                img = Image.new("RGB", (1280, 720), color=(128, 0, 32))
                draw = ImageDraw.Draw(img)
                # Draw a placeholder box
                draw.rectangle([(100, 100), (1180, 620)], outline="gold", width=10)
                # Save the image
                await asyncio.to_thread(img.save, dest_path, "PNG")
            except Exception as e:
                logger.error(f"Failed to create PIL dummy image: {e}. Writing empty file.")
                with open(dest_path, "wb") as f:
                    f.write(b"")
            return

        # Real download logic
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            raise e
