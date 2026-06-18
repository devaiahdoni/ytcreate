import os
from typing import Optional
import google.generativeai as genai
from config.settings import settings
from loguru import logger

class GeminiService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "mock-key")
        self.is_mocked = api_key == "mock-key"
        if self.is_mocked:
            logger.warning("Gemini API key not provided. Running GeminiService in MOCK mode.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate text using Gemini 1.5 Flash."""
        if self.is_mocked:
            return f"Mocked Gemini text response for: {prompt[:30]}..."

        try:
            # Running synchronous API in an executor thread or standard call since it's small,
            # or calling the client directly.
            # Using run_in_executor helper or calling genai client
            kwargs = {}
            if system_instruction:
                kwargs["system_instruction"] = system_instruction
            
            # Simple wrapper to avoid blocking the event loop
            import asyncio
            model = genai.GenerativeModel("gemini-1.5-flash", **kwargs)
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini generate_text: {e}")
            raise e

    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image using Gemini's vision capability (multimodal)."""
        if self.is_mocked:
            return f"Mocked Gemini analysis for image {image_path}: This looks like a professional CTR optimized thumbnail."

        try:
            import asyncio
            from PIL import Image
            img = Image.open(image_path)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = await asyncio.to_thread(model.generate_content, [prompt, img])
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini analyze_image: {e}")
            raise e
