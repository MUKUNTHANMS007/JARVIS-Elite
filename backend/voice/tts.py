import os
import re
import io
import torch
import soundfile as sf
import asyncio
import numpy as np
from typing import AsyncGenerator
from datetime import datetime

# ==========================================
# JARVIS Production Neural TTS (Kokoro-82M)
# ==========================================
# Optimized for zero-lag WebSocket performance and Docker portability.

# Audio Calibration
VOLUME_GAIN = 1.5
SAMPLE_RATE = 24000

_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        # RTX 3050 Ti Detection / CUDA Support
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[Neural Link] Initializing Kokoro Core on {device}...")
        from kokoro import KPipeline
        _pipeline = KPipeline(lang_code='b', device=device)
    return _pipeline

def clean_text(text: str) -> str:
    """Strip markdown and normalize whitespace."""
    text = re.sub(r'(\*\*|\*|#|`|\[|\]|<[^>]+>)', '', text)
    return re.sub(r'\s+', ' ', text).strip()

async def synthesize_speech_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    Asynchronous Neural Streaming:
    - Offloads inference to worker threads to prevent WebSocket heartbeat drift.
    - Yields RAW PCM_16 bytes for gapless browser playback.
    """
    cleaned = clean_text(text)
    if not cleaned:
        yield b""
        return

    start_time = datetime.now()
    pipeline = _get_pipeline()
    
    def _generate():
        # The Kokoro pipeline call itself is synchronous
        return pipeline(cleaned, voice='bm_lewis', speed=1.1, split_pattern=r'[,;.:!?]|\s+')

    try:
        # 1. Offload generator creation
        generator = await asyncio.to_thread(_generate)
        
        # 2. Truly Non-Blocking Iteration:
        # We must wrap 'next(generator)' in a thread to keep the event loop alive.
        iterator = iter(generator)
        first_byte = True

        while True:
            def _get_next():
                try:
                    return next(iterator)
                except StopIteration:
                    return None
            
            result = await asyncio.to_thread(_get_next)
            if result is None:
                break
            
            _, _, audio = result
            if audio is None: continue
            
            # --- Gain & Clipping Protection ---
            audio = np.clip(audio * VOLUME_GAIN, -1.0, 1.0)
            
            # --- Convert to RAW PCM 16-bit ---
            # Standardizing on RAW PCM prevents WAV-header 'clicks' in the browser.
            byte_io = io.BytesIO()
            sf.write(byte_io, audio, SAMPLE_RATE, format='RAW', subtype='PCM_16')
            audio_bytes = byte_io.getvalue()
            
            if first_byte:
                delta = (datetime.now() - start_time).total_seconds()
                print(f"[Neural Link] First Byte (RAW PCM) Produced in {delta:.4f}s")
                first_byte = False
                
            yield audio_bytes
            # Yield control back to the event loop between tokens
            await asyncio.sleep(0) 
            
    except Exception as e:
        print(f"[Neural Link] TTS Processing Error: {e}")
        yield b""

async def synthesize_speech(text: str) -> bytes:
    """Legacy support for full blobs (Adds a single WAV Header)."""
    chunks = []
    async for chunk in synthesize_speech_stream(text):
        if chunk:
            chunks.append(chunk)
    
    if not chunks:
        return b""
        
    # Reconstruct from RAW 16-bit PCM buffer
    combined = np.frombuffer(b"".join(chunks), dtype=np.int16)
    byte_io = io.BytesIO()
    sf.write(byte_io, combined, SAMPLE_RATE, format='WAV')
    return byte_io.getvalue()

async def close_tts_client():
    """Cleanup logic if models need explicit release."""
    pass
