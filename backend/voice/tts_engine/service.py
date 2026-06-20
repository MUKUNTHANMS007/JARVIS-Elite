import asyncio
import io
import logging
from typing import AsyncGenerator, Optional
from pathlib import Path
from pydub import AudioSegment

from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.cache import AudioCache
from voice.tts_engine.config import TTS_DEFAULT_PROVIDER
from voice.tts_engine.providers.kokoro_provider import KokoroProvider
from voice.tts_engine.providers.edge_provider import EdgeProvider
from voice.tts_engine.providers.openai_provider import OpenAIProvider
from voice.tts_engine.providers.elevenlabs_provider import ElevenLabsProvider

logger = logging.getLogger("JARVIS-TTS-SERVICE")

class TTSService:
    """
    Main Service orchestrating the Text-to-Speech pipeline.
    Implements file caching, fallback routing, and output transcoding.
    """

    def __init__(
        self,
        provider: Optional[TTSProvider] = None,
        cache: Optional[AudioCache] = None
    ):
        self.cache = cache or AudioCache()
        
        # Dependency Injection / Factory Selection
        if provider:
            self.provider = provider
        else:
            self.provider = self._init_default_provider()

    def _init_default_provider(self) -> TTSProvider:
        """Instantiate the default provider configured in the environment."""
        p_name = TTS_DEFAULT_PROVIDER.strip().lower()
        logger.info(f"Initializing TTS provider factory for: '{p_name}'")
        
        if p_name == "kokoro":
            return KokoroProvider()
        elif p_name == "edge":
            return EdgeProvider()
        elif p_name == "openai":
            return OpenAIProvider()
        elif p_name == "elevenlabs":
            return ElevenLabsProvider()
        else:
            logger.warning(f"Unknown provider '{p_name}'. Falling back to local Kokoro.")
            return KokoroProvider()

    def _transcode(self, audio_bytes: bytes, from_fmt: str, to_fmt: str) -> tuple[bytes, str]:
        """Convert audio payloads between formats using pydub.
        
        Returns:
            (audio_bytes, actual_format): actual_format is 'to_fmt' on success,
            or 'from_fmt' if transcoding failed (e.g. ffmpeg missing).
        """
        from_fmt = from_fmt.lower()
        to_fmt = to_fmt.lower()
        
        if from_fmt == to_fmt:
            return audio_bytes, to_fmt

        try:
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=from_fmt)
            out_io = io.BytesIO()
            segment.export(out_io, format=to_fmt)
            return out_io.getvalue(), to_fmt
        except Exception as e:
            logger.warning(
                f"[TTS Transcode Fail] Transcode {from_fmt}→{to_fmt} failed (ffmpeg missing?): {e}. "
                f"Returning source payload in native '{from_fmt}' format."
            )
            return audio_bytes, from_fmt

    def _get_provider_native_format(self) -> str:
        """Kokoro produces WAV, cloud providers typically produce MP3."""
        if hasattr(self.provider, "native_format"):
            return getattr(self.provider, "native_format")
        if isinstance(self.provider, KokoroProvider):
            return "wav"
        return "mp3"

    def _get_mime_type(self, fmt: str) -> str:
        if fmt.lower() == "mp3":
            return "audio/mpeg"
        return "audio/wav"

    async def generateSpeech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        fmt: str = "wav"
    ) -> tuple[bytes, str]:
        """
        Main synthesis endpoint.
        Returns: (audio_bytes, mime_type)
        """
        fmt = fmt.lower()
        if fmt not in {"wav", "mp3"}:
            fmt = "wav"

        provider_name = self.provider.__class__.__name__.replace("Provider", "").lower()
        default_voice = self.provider.get_supported_voices()[0]
        selected_voice = voice if voice in self.provider.get_supported_voices() else default_voice

        # 1. Check cache hits
        cache_key = self.cache.get_hash(text, provider_name, selected_voice, speed, fmt)
        cached_data = await self.cache.get_audio_bytes(cache_key, fmt)
        if cached_data:
            logger.debug(f"[TTS Cache Hit] Key: {cache_key}")
            return cached_data, self._get_mime_type(fmt)

        # 2. Synthesize fresh audio
        logger.info(f"Synthesizing speech via {provider_name} for text: '{text[:30]}...'")
        native_format = self._get_provider_native_format()
        native_audio = await self.provider.generate_speech(text, selected_voice, speed)

        # 3. Transcode if output format differs from native; use actual_fmt for MIME
        final_audio, actual_fmt = self._transcode(native_audio, native_format, fmt)

        # 4. Save to cache filesystem (keyed by requested fmt; serves actual bytes)
        await self.cache.save_audio(
            key=cache_key,
            fmt=actual_fmt,
            audio_bytes=final_audio,
            text=text,
            provider=provider_name,
            voice=selected_voice,
            speed=speed
        )

        return final_audio, self._get_mime_type(actual_fmt)

    async def generateSpeechToFile(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        fmt: str = "wav"
    ) -> None:
        """Synthesize and write audio directly to a filesystem target."""
        audio_bytes, _ = await self.generateSpeech(text, voice, speed, fmt)
        
        def _write():
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
                
        await asyncio.to_thread(_write)
        logger.info(f"Speech file written: {output_path}")

    async def streamSpeech(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        fmt: str = "wav"
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream speech in real-time.
        Bypasses file transcoding to stream at minimal latency.
        """
        provider_name = self.provider.__class__.__name__.replace("Provider", "").lower()
        default_voice = self.provider.get_supported_voices()[0]
        selected_voice = voice if voice in self.provider.get_supported_voices() else default_voice

        # Check cache first (stream block-by-block if hit)
        cache_key = self.cache.get_hash(text, provider_name, selected_voice, speed, fmt)
        cached_data = await self.cache.get_audio_bytes(cache_key, fmt)
        if cached_data:
            chunk_size = 4096
            for i in range(0, len(cached_data), chunk_size):
                yield cached_data[i:i+chunk_size]
                await asyncio.sleep(0)
            return

        # Stream directly from active provider
        async for chunk in self.provider.stream_speech(text, selected_voice, speed):
            yield chunk
