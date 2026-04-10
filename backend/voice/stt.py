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

def _choose_provider() -> str:
    if STT_PROVIDER in {"groq", "local"}:
        return STT_PROVIDER
    return "groq" if os.environ.get("GROQ_API_KEY") else "local"

async def transcribe_audio(audio_bytes: bytes) -> str:
    if not audio_bytes or len(audio_bytes) < 1000:
        return ""

    # 1. Format Detection
    suffix = ".webm"
    if audio_bytes.startswith(b'\x1a\x45\xdf\xa3'): suffix = ".webm"
    elif audio_bytes.startswith(b'OggS'): suffix = ".ogg"
    elif audio_bytes.startswith(b'fLaC'): suffix = ".flac"
    elif audio_bytes.startswith(b'RIFF'): suffix = ".wav"

    start_time = datetime.now()
    tmp_path = None
    
    try:
        # 2. Critical Fix: Close the file handle BEFORE passing path to model
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        provider = _choose_provider()

        if provider == "local":
            model = _get_local_whisper_model()
            def _run_local():
                # Fix: Convert segments generator to a list to force execution
                segments, _ = model.transcribe(tmp_path, language="en", vad_filter=True)
                return " ".join(seg.text.strip() for seg in segments).strip()
            raw_text = await asyncio.to_thread(_run_local)
        
        else:
            client = _get_groq_client()
            if not client: return ""
            
            with open(tmp_path, "rb") as f:
                response = await asyncio.wait_for(
                    client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=(tmp_path, f),
                        language="en",
                        prompt="JARVIS, Mukunthan, LeetCode, GitHub, Spotify, FastAPI, React.",
                        response_format="json",
                        temperature=0.0
                    ),
                    timeout=10.0
                )
                # Fix: Properly handle Groq's response object
                raw_text = response.text.strip() if hasattr(response, 'text') else response.get('text', '')

        duration = (datetime.now() - start_time).total_seconds()
        print(f"[STT] {provider.upper()} Success: \"{raw_text[:40]}...\" ({duration:.2f}s)")
        return raw_text

    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    print(asyncio.run(transcribe_audio(b"")))
