import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from config.settings import settings
from loguru import logger

T = TypeVar("T", bound=BaseModel)

class OpenAIService:
    def __init__(self):
        # Allow fallback or mock behavior if API key is not configured for local standalone testing
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "mock-key")
        self.client = AsyncOpenAI(api_key=api_key)
        self.is_mocked = api_key == "mock-key"
        if self.is_mocked:
            logger.warning("OpenAI API key not provided. Running OpenAIService in MOCK mode.")

    async def generate_text(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """Generate plain text from OpenAI Chat Completions."""
        if self.is_mocked:
            return f"Mocked OpenAI text response for: {prompt[:30]}..."
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error in OpenAI generate_text: {e}")
            raise e

    async def generate_structured_json(self, prompt: str, response_model: Type[T], system_prompt: str = "You are a helpful assistant.") -> T:
        """Generate structured data parsed into a Pydantic model using OpenAI Structured Outputs."""
        if self.is_mocked:
            # Create a mock instance of the response model with empty/default fields
            # We will use simple heuristics or fallback dicts
            logger.debug(f"Mocking structured JSON for model {response_model.__name__}")
            # Try to return a dummy model structure
            mock_data = self._get_mock_structure(response_model, prompt)
            return response_model.model_validate(mock_data)

        try:
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_model,
                temperature=0.7
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise ValueError("Failed to parse structured output from OpenAI.")
            return parsed
        except Exception as e:
            logger.error(f"Error in OpenAI generate_structured_json: {e}")
            raise e

    async def generate_image(self, prompt: str) -> str:
        """Generate an image using DALL-E 3 and return the image URL."""
        if self.is_mocked:
            return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600" # fallback elegant abstract art URL

        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="url"
            )
            return response.data[0].url or ""
        except Exception as e:
            logger.error(f"Error in OpenAI generate_image: {e}")
            raise e

    def _get_mock_structure(self, response_model: Type[T], prompt: str) -> dict:
        """Utility to construct valid dummy mock data based on the requested model name."""
        name = response_model.__name__.lower()
        if "script" in name:
            return {
                "title": f"The Secrets of {prompt[:15]}",
                "hook": "Ever wondered how this works? Let me tell you a secret...",
                "full_script": "This is scene 1 script block. And here is scene 2 script. Finally, this is scene 3 script block."
            }
        elif "scenes" in name or "splitter" in name or "split" in name:
            return {
                "scenes": [
                    {
                        "scene_number": 1,
                        "voice_text": "Ever wondered how this works? Let me tell you a secret.",
                        "video_prompt": "Cinematic visual of a glowing mysterious object on a table, soft lighting",
                        "duration": 5.0
                    },
                    {
                        "scene_number": 2,
                        "voice_text": "It all started when a group of researchers made a breakthrough.",
                        "video_prompt": "Futuristic laboratory setup, scientists in clean suits inspecting screens",
                        "duration": 6.5
                    },
                    {
                        "scene_number": 3,
                        "voice_text": "And now, this technology is available right in your pocket.",
                        "video_prompt": "Close up shot of a hand holding a glowing modern smartphone, outdoors day",
                        "duration": 5.5
                    }
                ]
            }
        elif "prompt" in name or "prompts" in name or "promptengineer" in name:
            return {
                "scene_id": 1,
                "video_prompt": "Close up cinematic shot of glowing particles in the dark, hyper-realistic, 4k",
                "camera_motion": "slow zoom in",
                "lighting": "neon glow with low-key studio lighting",
                "style": "photorealistic sci-fi",
                "negative_prompt": "blurry, low quality, cartoon, noise"
            }
        elif "voice" in name or "narration" in name:
            return {
                "scene_id": 1,
                "voice_text": "Welcome back to the channel. Today we're exploring the future.",
                "emotion": "excited",
                "pause_points": [2.5, 4.0]
            }
        elif "seo" in name:
            return {
                "title": f"This Changes Everything! {prompt[:15]} Exposed",
                "description": f"Learn the absolute truth about {prompt}. In this video, we cover everything you need to know step-by-step.",
                "tags": ["AI", "Tech", "Future", "Innovation"]
            }
        elif "thumbnail" in name:
            return {
                "thumbnail_prompt": "Vibrant and striking design with glowing central item and a shocked expressions silhouette, dark background",
                "headline_text": "MIND BLOWING!"
            }
        return {}

import os
