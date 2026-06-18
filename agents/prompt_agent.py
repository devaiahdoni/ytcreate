from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from loguru import logger

class PromptOutput(BaseModel):
    scene_id: int = Field(description="The matching scene index/number.")
    video_prompt: str = Field(description="An optimized, detailed text prompt for video generation models like Google Veo.")
    camera_motion: str = Field(description="Desired camera movement (e.g. slow panning, dolly zoom, tracking shot).")
    lighting: str = Field(description="Lighting style (e.g. cinematic, volumetric, high contrast, warm sunset).")
    style: str = Field(description="Visual art/film style (e.g. photorealistic 8k, digital art, cinematic 35mm film).")
    negative_prompt: str = Field(description="Things to exclude from the visual generation (e.g. text, watermark, bad anatomy, cartoon).")

class PromptAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, scene_id: int, visual_description: str, general_style: str = "photorealistic cinematic") -> PromptOutput:
        """Generates cinematic video generation prompts for a scene, keeping styles consistent."""
        logger.info(f"PromptAgent: Designing prompt for scene {scene_id}")
        
        system_prompt = (
            "You are a professional AI Prompt Engineer for advanced text-to-video generators (e.g., Google Veo, OpenAI Sora). "
            "Your task is to take a scene's visual description and output a highly descriptive visual prompt, "
            "camera motion directives, lighting keys, style targets, and negative prompts, ensuring they are cinematic and "
            "optimally structured for generative AI."
        )

        prompt = (
            f"Generate optimized prompt parameters for Scene ID: {scene_id}.\n"
            f"Scene visual description: '{visual_description}'\n"
            f"Target style family: '{general_style}'\n"
            f"Produce highly detailed visual prompts that specify environment details, key subjects, colors, "
            f"and composition. Keep character and location details consistent."
        )

        try:
            prompt_data = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=PromptOutput,
                system_prompt=system_prompt
            )
            # Override or set the scene_id to guarantee match
            prompt_data.scene_id = scene_id
            logger.info(f"PromptAgent: Completed prompt for scene {scene_id}: '{prompt_data.video_prompt[:30]}...'")
            return prompt_data
        except Exception as e:
            logger.error(f"PromptAgent failed for scene {scene_id}: {e}")
            raise e
