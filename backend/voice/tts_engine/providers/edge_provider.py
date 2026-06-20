import logging
from typing import AsyncGenerator
import edge_tts

from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.config import EDGE_TTS_VOICE

logger = logging.getLogger("JARVIS-EDGE-PROVIDER")

class EdgeProvider(TTSProvider):
    """
    Cloud TTS provider powered by Microsoft Edge neural voice web sockets.
    Does not require API keys, runs remotely.
    """

    def __init__(self):
        self._supported_voices = [
            "en-GB-RyanNeural", "en-GB-SoniaNeural",
            "en-US-GuyNeural", "en-US-AriaNeural", "en-US-JennyNeural"
        ]

    def get_supported_voices(self) -> list[str]:
        return self._supported_voices

    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize text using edge-tts and return MP3 audio bytes."""
        if not voice or voice not in self._supported_voices:
            voice = EDGE_TTS_VOICE

        # Format rate parameter for edge-tts (e.g. "+0%" or "+10%" or "-5%")
        rate_percent = int((speed - 1.0) * 100)
        rate_str = f"{rate_percent:+d}%" if rate_percent != 0 else "+0%"

        audio_bytes = bytearray()
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str)
            async for part in communicate.stream():
                if part.get("type") == "audio":
                    audio_bytes.extend(part.get("data") or b"")
            return bytes(audio_bytes)
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            raise e

    async def stream_speech(self, text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
        """Stream chunks of synthesized MP3 audio directly from edge-tts web socket."""
        if not voice or voice not in self._supported_voices:
            voice = EDGE_TTS_VOICE

        rate_percent = int((speed - 1.0) * 100)
        rate_str = f"{rate_percent:+d}%" if rate_percent != 0 else "+0%"

        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str)
            async for part in communicate.stream():
                if part.get("type") == "audio":
                    chunk = part.get("data")
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f"Edge-TTS streaming error: {e}")
            raise e
