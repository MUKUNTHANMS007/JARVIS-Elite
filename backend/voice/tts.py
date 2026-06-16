import os
import re
import io
import soundfile as sf
import asyncio
import numpy as np
from typing import AsyncGenerator
from datetime import datetime
from groq import Groq

# ==========================================
# JARVIS Production Cloud TTS (Groq API)
# ==========================================
# Uses Groq's high-speed cloud speech synthesis to save local VRAM.

VOLUME_GAIN = 1.1
SAMPLE_RATE = 24000

_client = None

def _get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        _client = Groq(api_key=api_key)
    return _client

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
    Asynchronous Groq Neural Streaming:
    - Splits text into short chunks.
    - Synthesizes speech using Groq API.
    - Yields RAW PCM_16 bytes for gapless browser playback.
    """
    cleaned = clean_text(text)
    if not cleaned:
        yield b""
        return

    start_time = datetime.now()
    client = _get_groq_client()
    chunks = chunk_text(cleaned)
    first_byte = True

    for chunk in chunks:
        if not chunk.strip():
            continue

        def _generate():
            try:
                # Call Groq's speech endpoint
                response = client.audio.speech.create(
                    model="canopylabs/orpheus-v1-english",
                    voice="troy",
                    input=chunk,
                    response_format="wav"
                )
                return response.content
            except Exception as e:
                print(f"[Neural Link] Groq TTS API Error: {e}")
                return None

        try:
            # Offload synchronous network API call to thread pool
            wav_bytes = await asyncio.to_thread(_generate)
            if not wav_bytes:
                continue

            # Load WAV in soundfile
            audio, sr = sf.read(io.BytesIO(wav_bytes))
            if audio.ndim > 1:
                audio = audio[:, 0]  # Convert to mono

            # Resample to 24000 Hz if necessary
            audio = resample_audio(audio, sr, SAMPLE_RATE)

            # Apply volume gain and clipping protection
            audio = np.clip(audio * VOLUME_GAIN, -1.0, 1.0)

            # Convert to RAW PCM 16-bit
            byte_io = io.BytesIO()
            sf.write(byte_io, audio, SAMPLE_RATE, format='RAW', subtype='PCM_16')
            audio_bytes = byte_io.getvalue()

            if first_byte:
                delta = (datetime.now() - start_time).total_seconds()
                print(f"[Neural Link] First Byte (Groq Speech) Produced in {delta:.4f}s")
                first_byte = False

            yield audio_bytes
            await asyncio.sleep(0)

        except Exception as e:
            print(f"[Neural Link] Groq TTS Processing Error: {e}")
            yield b""

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
