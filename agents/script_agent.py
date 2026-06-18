from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from loguru import logger

class ScriptOutput(BaseModel):
    title: str = Field(description="Engaging, clickable YouTube title.")
    hook: str = Field(description="A hook for the first 5-10 seconds to keep viewers watching.")
    full_script: str = Field(description="The complete written narration script for the video.")

class ScriptAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, topic: str) -> ScriptOutput:
        """Generates a viral YouTube script, title, and hook based on a topic."""
        logger.info(f"ScriptAgent: Generating script for topic: '{topic}'")
        
        system_prompt = (
            "You are an expert viral YouTube scriptwriter. Your goal is to write a script "
            "designed to maximize audience retention, featuring a high-retention hook, "
            "clear and engaging storytelling, and a satisfying conclusion. "
            "Output must be optimized for text-to-speech audio reading."
        )
        
        prompt = (
            f"Write a script about the following topic: '{topic}'. "
            f"Ensure the hook is extremely engaging. The full script should read naturally "
            f"and contain enough details for a complete video. Avoid visual directions "
            f"in the script itself, only provide the voiceover narration text."
        )

        try:
            script_data = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=ScriptOutput,
                system_prompt=system_prompt
            )
            logger.info(f"ScriptAgent: Successfully generated script: '{script_data.title}'")
            return script_data
        except Exception as e:
            logger.error(f"ScriptAgent failed: {e}")
            raise e
