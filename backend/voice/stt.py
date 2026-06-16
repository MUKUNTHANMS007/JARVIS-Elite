import tempfile
import os
import asyncio
from datetime import datetime
from groq import AsyncGroq

# --- Configuration ---
STT_PROVIDER = (os.environ.get("STT_PROVIDER") or "").strip().lower()
LOCAL_STT_MODEL = os.environ.get("LOCAL_STT_MODEL", "small.en")
LOCAL_STT_DEVICE = os.environ.get("LOCAL_STT_DEVICE", "auto")
LOCAL_STT_COMPUTE_TYPE = os.environ.get("LOCAL_STT_COMPUTE_TYPE", "auto")

def _get_groq_client() -> AsyncGroq | None:
    api_key = os.environ.get("GROQ_API_KEY")
    return AsyncGroq(api_key=api_key) if api_key else None

_local_whisper_model = None
def _get_local_whisper_model():
    global _local_whisper_model
    if _local_whisper_model is not None:
        return _local_whisper_model
    try:
        from faster_whisper import WhisperModel
        # Setting cpu_threads for speed on local systems
        _local_whisper_model = WhisperModel(
            LOCAL_STT_MODEL,
            device=LOCAL_STT_DEVICE,
            compute_type=LOCAL_STT_COMPUTE_TYPE,
            cpu_threads=4 
        )
        return _local_whisper_model
    except ImportError:
        raise RuntimeError("faster-whisper not installed.")

def warm_up_stt():
    """Neural Pre-warming: Bypassed for text-only operation."""
    print("[Neural Link] STT Pre-warming bypassed (Text-Only Mode active).")

def _choose_provider() -> str:
    if STT_PROVIDER in {"groq", "local"}:
        return STT_PROVIDER
    return "groq" if os.environ.get("GROQ_API_KEY") else "local"

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Voice STT deactivated."""
    return ""

if __name__ == "__main__":
    print(asyncio.run(transcribe_audio(b"")))
