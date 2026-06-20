import io
import re
import asyncio
import logging
from typing import AsyncGenerator
import soundfile as sf
import httpx
from pathlib import Path

from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.config import (
    KOKORO_MODEL_PATH,
    KOKORO_VOICES_PATH,
    KOKORO_AUTO_DOWNLOAD,
    KOKORO_MODEL_URL,
    KOKORO_VOICES_URL,
)

logger = logging.getLogger("JARVIS-KOKORO-PROVIDER")

class KokoroProvider(TTSProvider):
    """
    Local-first neural TTS provider powered by Kokoro-82M using ONNX Runtime.
    Includes automated self-provisioning of weights.
    """

    def __init__(self):
        self._kokoro = None
        self._lock = asyncio.Lock()
        self._supported_voices = [
            "af_bella", "af_sarah", "af_nicole", "af_sky",
            "am_adam", "am_michael",
            "bf_emma", "bf_isabella",
            "bm_george", "bm_lewis"
        ]

    def get_supported_voices(self) -> list[str]:
        return self._supported_voices

    async def _ensure_models_exist(self) -> None:
        """Download model and voice binary files if they are missing."""
        model_path = Path(KOKORO_MODEL_PATH)
        voices_path = Path(KOKORO_VOICES_PATH)

        downloads = []
        if not model_path.exists():
            if KOKORO_AUTO_DOWNLOAD:
                downloads.append((KOKORO_MODEL_URL, model_path))
            else:
                raise FileNotFoundError(f"Kokoro model not found at {model_path} and auto-download is disabled.")

        if not voices_path.exists():
            if KOKORO_AUTO_DOWNLOAD:
                downloads.append((KOKORO_VOICES_URL, voices_path))
            else:
                raise FileNotFoundError(f"Kokoro voices not found at {voices_path} and auto-download is disabled.")

        if downloads:
            logger.info("Initializing self-provisioning for Kokoro ONNX model weights...")
            for url, dest in downloads:
                dest.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Downloading {url} -> {dest}")
                
                async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        temp_file = dest.with_suffix(".tmp")
                        with open(temp_file, "wb") as f:
                            async for chunk in response.iter_bytes(chunk_size=16384):
                                f.write(chunk)
                        temp_file.rename(dest)
                logger.info(f"Successfully downloaded {dest.name}")

    async def _get_engine(self):
        """Lazy load the ONNX model in a thread-safe manner."""
        if self._kokoro is not None:
            return self._kokoro

        async with self._lock:
            if self._kokoro is not None:
                return self._kokoro

            await self._ensure_models_exist()
            
            def _load():
                from kokoro_onnx import Kokoro as ONNXKokoro
                # Initialize Kokoro using soundfile/numpy execution paths
                return ONNXKokoro(str(KOKORO_MODEL_PATH), str(KOKORO_VOICES_PATH))

            # Load model weights on a separate thread to prevent FastAPI thread blocks
            self._kokoro = await asyncio.to_thread(_load)
            logger.info("Kokoro ONNX Engine initialized successfully.")
            return self._kokoro

    def _choose_lang(self, voice: str) -> str:
        """Determine language pack dynamically depending on US/UK voice keys."""
        voice = voice.lower()
        if voice.startswith("bf") or voice.startswith("bm"):
            return "en-gb"
        return "en-us"

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences to stream block-by-block."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize text using local Kokoro ONNX and return WAV bytes."""
        if not voice or voice not in self._supported_voices:
            voice = "af_bella"

        engine = await self._get_engine()
        lang = self._choose_lang(voice)

        def _synthesize():
            samples, sample_rate = engine.create(
                text=text,
                voice=voice,
                speed=speed,
                lang=lang
            )
            byte_io = io.BytesIO()
            sf.write(byte_io, samples, sample_rate, format="WAV", subtype="PCM_16")
            return byte_io.getvalue()

        return await asyncio.to_thread(_synthesize)

    async def stream_speech(self, text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
        """Stream synthesised audio sentence by sentence."""
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if not sentence:
                continue
            chunk_bytes = await self.generate_speech(sentence, voice, speed)
            if chunk_bytes:
                yield chunk_bytes
            await asyncio.sleep(0) # Yield execution control
