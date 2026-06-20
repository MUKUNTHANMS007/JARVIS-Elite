import sys
import os
# Dynamically add the backend/ directory to sys.path to resolve imports in all environments
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
import pytest
from pathlib import Path
import shutil
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from voice.tts_engine.config import TTS_CACHE_DIR
from voice.tts_engine.cache import AudioCache
from voice.tts_engine.interface import TTSProvider
from voice.tts_engine.service import TTSService

client = TestClient(app)

# 1. Standalone Mock Provider for Offline Service Testing
class MockTTSProvider(TTSProvider):
    def __init__(self):
        self.voices = ["mock_voice_1", "mock_voice_2"]
        self.native_format = "wav"
        
    def get_supported_voices(self) -> list[str]:
        return self.voices

    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        # Return a simple mock byte string mimicking audio data
        return b"MOCK-AUDIO-PAYLOAD-WAV"

    async def stream_speech(self, text: str, voice: str, speed: float):
        yield b"MOCK-CHUNK-1"
        yield b"MOCK-CHUNK-2"


def test_audio_cache_hashing():
    """Verify that AudioCache generates consistent SHA-256 hashes."""
    cache = AudioCache()
    text = "Test cache normalization string."
    
    hash1 = cache.get_hash(text, "kokoro", "af_bella", 1.0, "wav")
    hash2 = cache.get_hash("  Test cache   normalization  string.  ", "KOKORO", "af_bella", 1.0, "wav")
    hash3 = cache.get_hash(text, "edge", "af_bella", 1.0, "wav") # different provider
    
    assert hash1 == hash2, "Cache hash should be whitespace/casing normalized."
    assert hash1 != hash3, "Cache hash should differ depending on the provider."


@pytest.mark.asyncio
async def test_tts_service_cache_flow(tmp_path):
    """Test that TTSService writes to cache on first call, and reads it on the second."""
    # Use a temporary cache dir to isolate test
    cache = AudioCache()
    cache.cache_dir = tmp_path
    cache.metadata_file = tmp_path / "metadata.json"
    
    mock_provider = MockTTSProvider()
    service = TTSService(provider=mock_provider, cache=cache)
    
    text = "Hello J.A.R.V.I.S. system core"
    voice = "mock_voice_1"
    
    # First call - should trigger synthesis (Mock)
    audio_bytes, mime = await service.generateSpeech(text, voice, 1.0, "wav")
    assert audio_bytes == b"MOCK-AUDIO-PAYLOAD-WAV"
    assert mime == "audio/wav"
    
    # Verify file was written to the temporary directory
    cache_key = cache.get_hash(text, "mocktts", voice, 1.0, "wav")
    cache_file = tmp_path / f"{cache_key}.wav"
    assert cache_file.exists(), "Audio payload should be saved to file cache."
    
    # Second call - should return cached bytes (we alter the file to check if it reads cache)
    with open(cache_file, "wb") as f:
        f.write(b"MOCK-CACHED-PAYLOAD")
        
    cached_bytes, _ = await service.generateSpeech(text, voice, 1.0, "wav")
    assert cached_bytes == b"MOCK-CACHED-PAYLOAD", "Cache hit should return stored bytes without synthesizing."


def test_api_tts_voices_endpoint():
    """Verify the /api/tts/voices metadata list endpoint returns support maps."""
    response = client.get("/api/tts/voices")
    assert response.status_code == 200
    payload = response.json()
    assert "kokoro" in payload
    assert "edge" in payload
    assert isinstance(payload["kokoro"], list)


def test_api_tts_post_endpoint():
    """Test standard POST /api/tts endpoint via mocked service response."""
    # We patch generateSpeech to avoid making actual HTTP/ONNX calls during client requests
    mock_response = (b"DUMMY-WAV-BYTES", "audio/wav")
    
    with patch("voice.tts_engine.service.TTSService.generateSpeech", return_value=mock_response):
        response = client.post("/api/tts", json={
            "text": "Hello world endpoint test",
            "provider": "edge",
            "voice": "en-GB-SoniaNeural",
            "speed": 1.0,
            "format": "wav"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "audio_url" in data
        assert "cache_key" in data
        assert data["format"] == "wav"
        assert data["size_bytes"] == len(b"DUMMY-WAV-BYTES")
        assert "/static/tts/" in data["audio_url"]


def test_api_tts_stream_endpoint():
    """Test POST /api/tts/stream endpoint via mocked service response."""
    async def mock_stream(*args, **kwargs):
        yield b"CHUNK-1"
        yield b"CHUNK-2"

    with patch("voice.tts_engine.service.TTSService.streamSpeech", side_effect=mock_stream):
        response = client.post("/api/tts/stream", json={
            "text": "Streaming voice text",
            "provider": "edge",
            "voice": "en-GB-SoniaNeural"
        })
        
        assert response.status_code == 200
        # Check streaming content
        chunks = list(response.iter_bytes())
        assert b"".join(chunks) == b"CHUNK-1CHUNK-2"
