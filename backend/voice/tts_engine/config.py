import os
from pathlib import Path

# Base Directories
_BASE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _BASE_DIR.parent.parent

# Cache directory for audio outputs
TTS_CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", str(_BACKEND_DIR / "logs" / "tts_cache")))
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Kokoro Models configuration
KOKORO_DIR = _BASE_DIR / "models"
KOKORO_DIR.mkdir(parents=True, exist_ok=True)

KOKORO_MODEL_PATH = Path(os.getenv("KOKORO_MODEL_PATH", str(KOKORO_DIR / "kokoro-v1.0.onnx")))
KOKORO_VOICES_PATH = Path(os.getenv("KOKORO_VOICES_PATH", str(KOKORO_DIR / "voices-v1.0.bin")))

KOKORO_AUTO_DOWNLOAD = os.getenv("KOKORO_AUTO_DOWNLOAD", "true").lower() == "true"

# Download URLs for model assets
KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

# Default Provider & Fallbacks
TTS_DEFAULT_PROVIDER = os.getenv("TTS_DEFAULT_PROVIDER", "kokoro").lower()
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-GB-RyanNeural")

# Cloud Credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", None)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
