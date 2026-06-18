from typing import List
from pydantic import BaseModel, Field
from services.openai_service import OpenAIService
from services.tts_service import TTSService
from loguru import logger

class VoiceOutput(BaseModel):
    scene_id: int = Field(description="The matching scene index/number.")
    voice_text: str = Field(description="The finalized voiceover script text for narration, formatted for natural speech.")
    emotion: str = Field(description="The target emotion/tone for delivery (e.g., enthusiastic, corporate, serious, curious).")
    pause_points: List[float] = Field(description="List of float seconds representing pauses to insert between phrases for natural pacing.")

class VoiceAgent:
    """Agent 4: Voice Narration Agent - Responsible for formatting raw text, adding pacing, emotion, and pauses."""
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def execute(self, scene_id: int, raw_voice_text: str) -> VoiceOutput:
        """Processes the voice narration text for a scene, adding emotion and pacing/pause points."""
        logger.info(f"VoiceAgent: Styling voice narration for scene {scene_id}")

        system_prompt = (
            "You are an expert audio director and voiceover coach. Your job is to format raw narration text "
            "for text-to-speech engine consumption. Identify the ideal emotional delivery tone (e.g. dramatic, energetic, calm) "
            "and suggest logical pause points (in seconds) between major clauses or sentences to keep narration engaging."
        )

        prompt = (
            f"Analyze and format the voiceover text for Scene ID: {scene_id}.\n"
            f"Voice text: '{raw_voice_text}'\n"
            f"Decide the emotion and place natural pauses in seconds (e.g., 0.5s pause after full sentences)."
        )

        try:
            voice_data = await self.openai_service.generate_structured_json(
                prompt=prompt,
                response_model=VoiceOutput,
                system_prompt=system_prompt
            )
            voice_data.scene_id = scene_id
            logger.info(f"VoiceAgent: Stylized voice text for scene {scene_id} with emotion {voice_data.emotion}")
            return voice_data
        except Exception as e:
            logger.error(f"VoiceAgent failed for scene {scene_id}: {e}")
            raise e


class VoiceGenerationAgent:
    """Agent 6: Voice Generation Agent - Responsible for generating actual voice audio files using TTS services."""
    def __init__(self, tts_service: TTSService):
        self.tts_service = tts_service

    async def generate_audio(self, text: str, dest_path: str, provider: str = "openai", voice: str = "alloy", emotion: str = "neutral", duration: float = 5.0) -> None:
        """Generate audio file for a given text block and save to destination."""
        logger.info(f"VoiceGenerationAgent: Generating voice-over using '{provider}' for text: '{text[:30]}...'")
        try:
            await self.tts_service.generate_audio(
                text=text,
                dest_path=dest_path,
                provider=provider,
                voice=voice,
                emotion=emotion,
                duration=duration
            )
            logger.info(f"VoiceGenerationAgent: Saved voice-over audio to {dest_path}")
        except Exception as e:
            logger.error(f"VoiceGenerationAgent failed: {e}")
            raise e

    async def save_audio(self, audio_data: bytes, dest_path: str) -> None:
        """Save raw bytes to audio path if generated directly."""
        try:
            import asyncio
            def write_file():
                with open(dest_path, "wb") as f:
                    f.write(audio_data)
            await asyncio.to_thread(write_file)
            logger.info(f"VoiceGenerationAgent: Manually saved audio bytes to {dest_path}")
        except Exception as e:
            logger.error(f"VoiceGenerationAgent save_audio failed: {e}")
            raise e
