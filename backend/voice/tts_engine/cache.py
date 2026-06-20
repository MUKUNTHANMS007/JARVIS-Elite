import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
import asyncio

from voice.tts_engine.config import TTS_CACHE_DIR

logger = logging.getLogger("JARVIS-TTS-CACHE")

class AudioCache:
    """
    Manages local file caching and metadata indexing for generated speech payloads.
    Provides <5ms resolution for identical repeats.
    """

    def __init__(self):
        self.cache_dir = Path(TTS_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self._lock = asyncio.Lock()

    def get_hash(self, text: str, provider: str, voice: str, speed: float, fmt: str) -> str:
        """Generate a unique SHA-256 hash based on request params."""
        normalized_text = " ".join(text.strip().lower().split())
        data_string = f"{normalized_text}|{provider.lower()}|{voice.lower()}|{speed:.2f}|{fmt.lower()}"
        return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

    async def get_cached_filepath(self, key: str, fmt: str) -> Path | None:
        """Check if a cache file exists and return its path."""
        file_path = self.cache_dir / f"{key}.{fmt.lower()}"
        if file_path.exists():
            return file_path
        return None

    async def get_audio_bytes(self, key: str, fmt: str) -> bytes | None:
        """Retrieve cached audio bytes from disk."""
        file_path = await self.get_cached_filepath(key, fmt)
        if not file_path:
            return None
        
        def _read():
            with open(file_path, "rb") as f:
                return f.read()
                
        return await asyncio.to_thread(_read)

    async def save_audio(self, key: str, fmt: str, audio_bytes: bytes, text: str, provider: str, voice: str, speed: float) -> Path:
        """Save audio payload and append metadata description to metadata.json."""
        file_path = self.cache_dir / f"{key}.{fmt.lower()}"
        
        def _write():
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
                
        await asyncio.to_thread(_write)

        # Update metadata.json registry
        async with self._lock:
            metadata = {}
            if self.metadata_file.exists():
                try:
                    with open(self.metadata_file, "r") as f:
                        metadata = json.load(f)
                except Exception:
                    pass

            metadata[key] = {
                "text": text,
                "provider": provider,
                "voice": voice,
                "speed": speed,
                "format": fmt,
                "size_bytes": len(audio_bytes),
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            def _write_meta():
                with open(self.metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

            await asyncio.to_thread(_write_meta)
            
        logger.info(f"Cached generated audio: {file_path.name} ({len(audio_bytes)} bytes)")
        return file_path
