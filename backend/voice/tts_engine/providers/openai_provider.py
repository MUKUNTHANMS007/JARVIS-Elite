import logging
from typing import AsyncGenerator
import httpx

from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.config import OPENAI_API_KEY

logger = logging.getLogger("JARVIS-OPENAI-PROVIDER")

class OpenAIProvider(TTSProvider):
    """
    Cloud TTS provider powered by OpenAI's Audio API (tts-1 model).
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self):
        self._supported_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def get_supported_voices(self) -> list[str]:
        return self._supported_voices

    async def _get_headers(self) -> dict:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is not configured.")
        return {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize text using OpenAI tts-1 and return MP3 audio bytes."""
        if not voice or voice not in self._supported_voices:
            voice = "alloy"

        headers = await self._get_headers()
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": speed
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.content

    async def stream_speech(self, text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
        """Stream chunks of synthesized MP3 audio directly from OpenAI API."""
        if not voice or voice not in self._supported_voices:
            voice = "alloy"

        headers = await self._get_headers()
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": speed
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for chunk in response.iter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk
