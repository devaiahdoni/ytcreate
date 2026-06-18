from typing import List
from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from loguru import logger

class SEOOutput(BaseModel):
    title: str = Field(description="SEO optimized, high-CTR YouTube title (max 100 characters).")
    description: str = Field(description="Comprehensive YouTube description containing keywords and video summary.")
    tags: List[str] = Field(description="List of relevant search tags for YouTube metadata indexing.")

class SEOAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, topic: str, script: str) -> SEOOutput:
        """Generates search-engine optimized title, description, and tags based on script context."""
        logger.info("SEOAgent: Optimizing metadata")

        system_prompt = (
            "You are an expert YouTube SEO consultant. Your goal is to maximize search discoverability "
            "and suggest CTR-optimized title variations, metadata descriptions, and keyword tags."
        )

        prompt = (
            f"Review the video details:\n"
            f"Topic: '{topic}'\n"
            f"Script Content: '{script[:2000]}...'\n\n"
            f"Generate an optimized YouTube title, description, and tags list."
        )

        try:
            seo_data = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=SEOOutput,
                system_prompt=system_prompt
            )
            logger.info(f"SEOAgent: SEO optimization completed. Chosen Title: '{seo_data.title}'")
            return seo_data
        except Exception as e:
            logger.error(f"SEOAgent failed: {e}")
            raise e
