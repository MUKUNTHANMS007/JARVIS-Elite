import os
import re
import io
import logging
import soundfile as sf
import asyncio
import numpy as np
from typing import AsyncGenerator
from datetime import datetime
from groq import Groq

logger = logging.getLogger("JARVIS-TTS")

# ==========================================
# JARVIS Production Cloud TTS (Groq API)
# ==========================================
# Uses Groq's high-speed cloud speech synthesis to save local VRAM.

VOLUME_GAIN = 1.1
SAMPLE_RATE = 24000

_client = None

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-GB-RyanNeural")
GROQ_TTS_MODEL = os.getenv("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english")
GROQ_TTS_VOICE = os.getenv("GROQ_TTS_VOICE", "troy")
GROQ_TTS_MAX_RETRIES = int(os.getenv("GROQ_TTS_MAX_RETRIES", "0"))

def _get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        _client = Groq(api_key=api_key, max_retries=GROQ_TTS_MAX_RETRIES)
    return _client

def _read_groq_speech_response(response) -> bytes | None:
    """Extract audio bytes from Groq SDK response objects."""
    if response is None:
        return None
    content = getattr(response, "content", None)
    if content:
        return content
    if hasattr(response, "read"):
        data = response.read()
        return data if data else None
    if hasattr(response, "write_to_file"):
        buf = io.BytesIO()
        response.write_to_file(buf)
        buf.seek(0)
        return buf.read() or None
    return None

async def _synthesize_groq(chunk: str) -> bytes | None:
    client = _get_groq_client()
    if client is None:
        return None

    def _generate():
        try:
            response = client.audio.speech.create(
                model=GROQ_TTS_MODEL,
                voice=GROQ_TTS_VOICE,
                input=chunk,
                response_format="wav",
            )
            return _read_groq_speech_response(response)
        except Exception as e:
            err = str(e)
            if "model_terms_required" in err:
                logger.warning(
                    "[Neural Link] Groq Orpheus terms not accepted — using edge-tts fallback. "
                    "Accept terms at: https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
                )
            else:
                logger.warning("[Neural Link] Groq TTS failed: %s", e)
            return None

    return await asyncio.to_thread(_generate)

async def _synthesize_edge(chunk: str) -> bytes | None:
    """Fallback TTS via Microsoft Edge neural voices (no API key required)."""
    try:
        import edge_tts
    except ImportError:
        logger.error("[Neural Link] edge-tts not installed.")
        return None

    voice = EDGE_TTS_VOICE

    async def _stream():
        audio = bytearray()
        communicate = edge_tts.Communicate(chunk, voice=voice)
        async for part in communicate.stream():
            if part.get("type") == "audio":
                audio.extend(part.get("data") or b"")
        return bytes(audio) if audio else None

    try:
        return await _stream()
    except Exception as e:
        logger.warning("[Neural Link] edge-tts failed: %s", e)
        return None

def _wav_to_pcm(wav_bytes: bytes) -> bytes | None:
    try:
        audio, sr = sf.read(io.BytesIO(wav_bytes))
        if audio.ndim > 1:
            audio = audio[:, 0]
        audio = resample_audio(audio, sr, SAMPLE_RATE)
        audio = np.clip(audio * VOLUME_GAIN, -1.0, 1.0)
        byte_io = io.BytesIO()
        sf.write(byte_io, audio, SAMPLE_RATE, format="RAW", subtype="PCM_16")
        return byte_io.getvalue()
    except Exception as e:
        logger.warning("[Neural Link] WAV→PCM conversion failed: %s", e)
        return None

def _wav_to_float32(wav_bytes: bytes) -> np.ndarray | None:
    try:
        audio, sr = sf.read(io.BytesIO(wav_bytes))
        if audio.ndim > 1:
            audio = audio[:, 0]
        audio = resample_audio(audio, sr, SAMPLE_RATE)
        return np.clip(audio * VOLUME_GAIN, -1.0, 1.0).astype(np.float32)
    except Exception as e:
        logger.warning("[Neural Link] WAV→Float32 conversion failed: %s", e)
        return None

def clean_text(text: str) -> str:
    """Strip markdown and normalize whitespace.
    Preserves inline # (e.g. C#, hashtags) — only strips leading # heading markers.
    """
    # Remove markdown heading markers (# only at line start)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove other markdown formatting
    text = re.sub(r'(\*\*|\*|`|\[|\]|<[^>]+>)', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text: str, max_chars: int = 180) -> list[str]:
    """Split text into chunks that fit within the 200-character limit of Orpheus."""
    # Split by punctuation followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) + 1 <= max_chars:
            current_chunk = (current_chunk + " " + s).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single sentence is too long, split it by words
            if len(s) > max_chars:
                words = s.split()
                sub_chunk = ""
                for w in words:
                    if len(sub_chunk) + len(w) + 1 <= max_chars:
                        sub_chunk = (sub_chunk + " " + w).strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = w
                if sub_chunk:
                    current_chunk = sub_chunk
            else:
                current_chunk = s
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample 1D audio array to target sample rate using linear interpolation."""
    if orig_sr == target_sr:
        return audio_data
    duration = len(audio_data) / orig_sr
    num_target_samples = int(duration * target_sr)
    x_orig = np.linspace(0, duration, len(audio_data))
    x_target = np.linspace(0, duration, num_target_samples)
    return np.interp(x_target, x_orig, audio_data)

async def _synthesize_chunk(chunk: str, groq_available: bool) -> tuple[bytes | None, bool]:
    """Synthesize one chunk, trying Groq first then falling back to edge-tts."""
    audio_bytes: bytes | None = None
    used_groq = False

    # Per-chunk Groq attempt: do NOT disable Groq session-wide after one
    # transient error — only skip it for this individual chunk.
    if groq_available:
        wav_bytes = await _synthesize_groq(chunk)
        if wav_bytes:
            audio_bytes = _wav_to_pcm(wav_bytes)
            used_groq = True

    if not audio_bytes:
        audio_bytes = await _synthesize_edge(chunk)

    return audio_bytes, used_groq

async def synthesize_speech_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    Synthesize speech in sentence chunks.
    - Primary: Groq Orpheus (PCM_16 @ 24 kHz)
    - Fallback: edge-tts (MP3 — browser decodes via decodeAudioData)

    Synthesis of the next chunk is kicked off as soon as the current chunk's
    audio is ready, so network/synthesis latency overlaps with the time the
    caller spends sending/playing the previous chunk instead of stacking up.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return

    chunks = [c for c in chunk_text(cleaned) if c.strip()]
    if not chunks:
        return

    start_time = datetime.now()
    first_byte = True
    groq_available = _get_groq_client() is not None

    next_task = asyncio.create_task(_synthesize_chunk(chunks[0], groq_available))
    for i in range(len(chunks)):
        audio_bytes, used_groq = await next_task

        if i + 1 < len(chunks):
            next_task = asyncio.create_task(_synthesize_chunk(chunks[i + 1], groq_available))

        if not audio_bytes:
            continue

        if first_byte:
            delta = (datetime.now() - start_time).total_seconds()
            provider = "Groq" if used_groq else "edge-tts"
            logger.info("[Neural Link] First audio byte in %.4fs (%s)", delta, provider)
            first_byte = False

        yield audio_bytes
        await asyncio.sleep(0)

async def synthesize_speech_payload(text: str) -> tuple[bytes, str]:
    """
    Generate a single playable audio payload for REST clients.
    Returns (audio_bytes, media_type).
    - Groq path returns a WAV assembled from all speech chunks.
    - edge-tts fallback returns a single MP3 payload for the whole text.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return b"", "audio/wav"

    chunks = chunk_text(cleaned)
    groq_available = _get_groq_client() is not None
    groq_audio_parts: list[np.ndarray] = []

    if groq_available:
        for chunk in chunks:
            if not chunk.strip():
                continue
            wav_bytes = await _synthesize_groq(chunk)
            if not wav_bytes:
                groq_audio_parts = []
                groq_available = False
                break

            audio = _wav_to_float32(wav_bytes)
            if audio is None:
                groq_audio_parts = []
                groq_available = False
                break
            groq_audio_parts.append(audio)

    if groq_audio_parts:
        combined = np.concatenate(groq_audio_parts) if len(groq_audio_parts) > 1 else groq_audio_parts[0]
        byte_io = io.BytesIO()
        sf.write(byte_io, combined, SAMPLE_RATE, format="WAV")
        return byte_io.getvalue(), "audio/wav"

    edge_audio = await _synthesize_edge(cleaned)
    if edge_audio:
        return edge_audio, "audio/mpeg"

    return b"", "audio/wav"

async def synthesize_speech(text: str) -> bytes:
    """Legacy compatibility wrapper for clients that only need audio bytes."""
    audio_bytes, _ = await synthesize_speech_payload(text)
    return audio_bytes

def warm_up_tts():
    """Neural Pre-warming: Bypassed for high-speed client-side SpeechSynthesis."""
    print("[Neural Link] Cloud TTS Warm-up Bypassed.")

async def close_tts_client():
    """Cleanup logic if models need explicit release."""
    pass
