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

def _get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        _client = Groq(api_key=api_key)
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
                model="canopylabs/orpheus-v1-english",
                voice="troy",
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

def clean_text(text: str) -> str:
    """Strip markdown and normalize whitespace."""
    text = re.sub(r'(\*\*|\*|#|`|\[|\]|<[^>]+>)', '', text)
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

async def synthesize_speech_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    Synthesize speech in sentence chunks.
    - Primary: Groq Orpheus (PCM_16 @ 24 kHz)
    - Fallback: edge-tts (MP3 — browser decodes via decodeAudioData)
    """
    cleaned = clean_text(text)
    if not cleaned:
        return

    start_time = datetime.now()
    chunks = chunk_text(cleaned)
    first_byte = True
    groq_available = _get_groq_client() is not None
    used_groq = False

    for chunk in chunks:
        if not chunk.strip():
            continue

        audio_bytes: bytes | None = None
        wav_bytes: bytes | None = None

        if groq_available:
            wav_bytes = await _synthesize_groq(chunk)
            if wav_bytes:
                audio_bytes = _wav_to_pcm(wav_bytes)
                used_groq = True
            else:
                groq_available = False

        if not audio_bytes:
            audio_bytes = await _synthesize_edge(chunk)

        if not audio_bytes:
            continue

        if first_byte:
            delta = (datetime.now() - start_time).total_seconds()
            provider = "Groq" if used_groq else "edge-tts"
            logger.info("[Neural Link] First audio byte in %.4fs (%s)", delta, provider)
            first_byte = False

        yield audio_bytes
        await asyncio.sleep(0)

async def synthesize_speech(text: str) -> bytes:
    """Legacy support for full blobs (Adds a single WAV Header)."""
    chunks = []
    async for chunk in synthesize_speech_stream(text):
        if chunk:
            chunks.append(chunk)
    
    if not chunks:
        return b""
        
    combined = np.frombuffer(b"".join(chunks), dtype=np.int16)
    byte_io = io.BytesIO()
    sf.write(byte_io, combined, SAMPLE_RATE, format='WAV')
    return byte_io.getvalue()

def warm_up_tts():
    """Neural Pre-warming: Bypassed for high-speed client-side SpeechSynthesis."""
    print("[Neural Link] Cloud TTS Warm-up Bypassed.")

async def close_tts_client():
    """Cleanup logic if models need explicit release."""
    pass
