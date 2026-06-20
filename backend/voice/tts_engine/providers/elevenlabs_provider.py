import logging
from typing import AsyncGenerator
import httpx

from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.config import ELEVENLABS_API_KEY

logger = logging.getLogger("JARVIS-ELEVENLABS-PROVIDER")

class ElevenLabsProvider(TTSProvider):
    """
    Cloud TTS provider powered by ElevenLabs API.
    Requires ELEVENLABS_API_KEY environment variable.
    """

    def __init__(self):
        # Maps user-friendly voice keys to ElevenLabs Voice IDs
        # Default: Rachel (21m00Tcm4TlvDq8ikWAM)
        self._voice_map = {
            "rachel": "21m00Tcm4TlvDq8ikWAM",
            "domi": "AZnzlk1XvdvUeBnXmlld",
            "bella": "EXAVITQu4vr4xnSDxMaL",
            "antoni": "ErXwobaYiN019PkySvjV",
        }
        self._supported_voices = list(self._voice_map.keys())

    def get_supported_voices(self) -> list[str]:
        return self._supported_voices

    async def _get_headers(self) -> dict:
        if not ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY environment variable is not configured.")
        return {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize text using ElevenLabs and return MP3 audio bytes."""
        if not voice or voice not in self._supported_voices:
            voice = "rachel"

        voice_id = self._voice_map[voice]
        headers = await self._get_headers()
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        # Query parameters to enforce format output
        params = {"output_format": "mp3_44100_128"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.content

    async def stream_speech(self, text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
        """Stream chunks of synthesized MP3 audio directly from ElevenLabs API."""
        if not voice or voice not in self._supported_voices:
            voice = "rachel"

        voice_id = self._voice_map[voice]
        headers = await self._get_headers()
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        params = {"output_format": "mp3_44100_128"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                headers=headers,
                json=payload,
                params=params
            ) as response:
                response.raise_for_status()
                async for chunk in response.iter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk
