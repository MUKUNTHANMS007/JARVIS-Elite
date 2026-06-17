import tempfile
import os
import asyncio
from pathlib import Path
import httpx
from groq import AsyncGroq

# --- Configuration ---
STT_PROVIDER = (os.environ.get("STT_PROVIDER") or "").strip().lower()
LOCAL_STT_MODEL = os.environ.get("LOCAL_STT_MODEL", "small.en")
LOCAL_STT_DEVICE = os.environ.get("LOCAL_STT_DEVICE", "auto")
LOCAL_STT_COMPUTE_TYPE = os.environ.get("LOCAL_STT_COMPUTE_TYPE", "auto")
GROQ_STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3-turbo")

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
        try:
            _local_whisper_model = WhisperModel(
                LOCAL_STT_MODEL,
                device=LOCAL_STT_DEVICE,
                compute_type=LOCAL_STT_COMPUTE_TYPE,
                cpu_threads=4
            )
        except Exception:
            # Self-heal for Windows hosts where CUDA is detected but unusable.
            _local_whisper_model = WhisperModel(
                LOCAL_STT_MODEL,
                device="cpu",
                compute_type="int8",
                cpu_threads=4
            )
        return _local_whisper_model
    except ImportError:
        raise RuntimeError("faster-whisper not installed.")

def warm_up_stt():
    """Warm the configured STT provider when prewarming is enabled."""
    provider = _choose_provider()
    if provider == "local":
        try:
            _get_local_whisper_model()
            print("[Neural Link] Local Whisper warmed and ready.")
        except Exception as e:
            print(f"[Neural Link] STT warm-up drift: {e}")
    else:
        print("[Neural Link] Cloud STT selected. Warm-up skipped.")

def _choose_provider() -> str:
    if STT_PROVIDER in {"groq", "local"}:
        return STT_PROVIDER
    return "groq" if os.environ.get("GROQ_API_KEY") else "local"

def _suffix_from_mime(mime_type: str | None, file_name: str | None = None) -> str:
    if file_name:
        suffix = Path(file_name).suffix
        if suffix:
            return suffix

    mime_map = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
    }
    return mime_map.get((mime_type or "").split(";")[0].strip().lower(), ".webm")

async def _transcribe_with_groq(audio_bytes: bytes, suffix: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return ""

    files = {
        "file": (f"audio{suffix}", audio_bytes, "application/octet-stream"),
    }
    data = {
        "model": GROQ_STT_MODEL,
        "language": "en",
        "response_format": "verbose_json",
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0)) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers=headers,
            data=data,
            files=files,
        )
        response.raise_for_status()
        payload = response.json()
        return (payload.get("text") or "").strip()

async def _transcribe_with_local(audio_bytes: bytes, suffix: str) -> str:
    def _run() -> str:
        model = _get_local_whisper_model()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            segments, _info = model.transcribe(
                temp_path,
                language="en",
                beam_size=1,
                vad_filter=True,
            )
            return " ".join(segment.text.strip() for segment in segments if segment.text).strip()
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    return await asyncio.to_thread(_run)

async def transcribe_audio(audio_bytes: bytes, mime_type: str | None = None, file_name: str | None = None) -> str:
    """Transcribe uploaded voice audio using the configured STT provider."""
    if not audio_bytes:
        return ""

    suffix = _suffix_from_mime(mime_type, file_name)
    provider = _choose_provider()

    if provider == "groq":
        try:
            text = await _transcribe_with_groq(audio_bytes, suffix)
            if text:
                return text
        except Exception as e:
            print(f"[Neural Link] Groq STT drift: {e}. Falling back to local Whisper.")
        try:
            return await _transcribe_with_local(audio_bytes, suffix)
        except Exception as e:
            print(f"[Neural Link] Local STT drift: {e}")
            return ""

    try:
        text = await _transcribe_with_local(audio_bytes, suffix)
        if text:
            return text
    except Exception as e:
        print(f"[Neural Link] Local STT drift: {e}. Falling back to Groq STT.")

    try:
        return await _transcribe_with_groq(audio_bytes, suffix)
    except Exception as e:
        print(f"[Neural Link] Groq STT drift after local failure: {e}")
        return ""

if __name__ == "__main__":
    print(asyncio.run(transcribe_audio(b"")))
