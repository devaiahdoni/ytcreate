from typing import List
from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from loguru import logger

class SceneDetail(BaseModel):
    scene_number: int = Field(description="Sequential index of the scene starting from 1.")
    voice_text: str = Field(description="The segment of script narration to be read aloud in this scene.")
    visual_description: str = Field(description="Detailed visual summary of what should be shown on screen during this narration.")
    duration: float = Field(description="Estimated duration of this scene in seconds, based on text length (approx 2.5 words per second, minimum 3 seconds).")

class SceneSplitterOutput(BaseModel):
    scenes: List[SceneDetail] = Field(description="List of scenes splitting the full script.")

class SceneAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, full_script: str) -> SceneSplitterOutput:
        """Splits the full script into sequential logical scenes."""
        logger.info("SceneAgent: Splitting script into scenes")
        
        system_prompt = (
            "You are a professional film/video editor and storyboard artist. Your task is "
            "to split a continuous text script into logical visual scenes. For each scene, "
            "extract the exact voice-over segment, describe the visual elements, and estimate "
            "the duration based on word count. Every word of the original script must be preserved "
            "across the voice_text fields of the scenes without omissions or overlap."
        )
        
        prompt = (
            f"Review the full script below:\n\n{full_script}\n\n"
            f"Split this script into a sequence of logical visual scenes. Provide precise "
            f"voice_text segments, visual descriptions, and duration estimations."
        )

        try:
            scenes_data = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=SceneSplitterOutput,
                system_prompt=system_prompt
            )
            logger.info(f"SceneAgent: Successfully split script into {len(scenes_data.scenes)} scenes.")
            return scenes_data
        except Exception as e:
            logger.error(f"SceneAgent failed: {e}")
            raise e
