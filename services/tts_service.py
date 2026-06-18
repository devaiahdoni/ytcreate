import os
import wave
import struct
import httpx
import asyncio
from pathlib import Path
from config.settings import settings
from loguru import logger
from openai import AsyncOpenAI

class TTSService:
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "mock-key")
        self.eleven_key = settings.ELEVENLABS_API_KEY or os.environ.get("ELEVENLABS_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=self.openai_key)
        self.is_mocked = self.openai_key == "mock-key"

        if self.is_mocked:
            logger.warning("No TTS provider API keys found. TTSService will run in MOCK mode generating silent WAVs.")

    async def generate_audio(self, text: str, dest_path: str, provider: str = "openai", voice: str = "alloy", emotion: str = "neutral", duration: float = 5.0) -> None:
        """Generate voice audio file for the narration text and save to dest_path."""
        dest_dir = Path(dest_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if self.is_mocked:
            await self._generate_mock_wav(dest_path, duration)
            return

        # Handle ElevenLabs provider
        if provider.lower() == "elevenlabs" and self.eleven_key:
            await self._generate_elevenlabs(text, dest_path, voice)
            return

        # Handle OpenAI TTS (default)
        # We fall back to OpenAI if ElevenLabs is selected but key is missing
        await self._generate_openai(text, dest_path, voice)

    async def _generate_openai(self, text: str, dest_path: str, voice: str) -> None:
        """Call OpenAI TTS API to generate audio."""
        try:
            logger.info(f"Generating OpenAI TTS for text: '{text[:30]}...' with voice: {voice}")
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,  # alloy, echo, fable, onyx, nova, shimmer
                input=text
            )
            # Response audio contents are saved directly
            await asyncio.to_thread(response.stream_to_file, dest_path)
            logger.info(f"OpenAI TTS audio saved to {dest_path}")
        except Exception as e:
            logger.error(f"Failed to generate OpenAI TTS: {e}")
            raise e

    async def _generate_elevenlabs(self, text: str, dest_path: str, voice_id: str) -> None:
        """Call ElevenLabs TTS API to generate audio."""
        # Standard voice ID fallback if a generic voice is passed
        # e.g., 'rachel' style ID: '21m00Tcm4TlvDq8ikWAM'
        actual_voice_id = voice_id if len(voice_id) > 10 else "21m00Tcm4TlvDq8ikWAM"
        
        headers = {
            "xi-api-key": self.eleven_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            logger.info(f"Generating ElevenLabs TTS for text: '{text[:30]}...' with voice: {actual_voice_id}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{actual_voice_id}",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(response.content)
            logger.info(f"ElevenLabs TTS audio saved to {dest_path}")
        except Exception as e:
            logger.error(f"Failed to generate ElevenLabs TTS: {e}")
            # Fallback to OpenAI if possible
            if self.openai_key != "mock-key":
                logger.info("ElevenLabs failed. Falling back to OpenAI TTS...")
                await self._generate_openai(text, dest_path, "alloy")
            else:
                raise e

    async def _generate_mock_wav(self, dest_path: str, duration: float) -> None:
        """Create a silent WAV file using pure Python's wave module."""
        logger.info(f"[Mock] Creating a silent WAV audio track at {dest_path} for duration {duration}s")
        
        def write_wav():
            sample_rate = 22050  # Lower sample rate for smaller file size
            num_samples = int(duration * sample_rate)
            
            with wave.open(dest_path, 'wb') as wav_file:
                # 1 channel, 2 bytes per sample (16-bit), sample_rate, num_samples
                wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
                # Write quiet samples (value 0)
                zero_sample = struct.pack('<h', 0)
                # Batch write to be fast
                wav_file.writeframesraw(zero_sample * num_samples)

        await asyncio.to_thread(write_wav)
        logger.info(f"[Mock] Silent audio created: {dest_path}")
