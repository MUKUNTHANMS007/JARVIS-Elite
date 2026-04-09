from groq import AsyncGroq
import tempfile
import os
import io
import asyncio
from datetime import datetime

# Initialize Groq client — Ensure your GROQ_API_KEY is in .env
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

async def correct_transcription(raw_text: str) -> str:
    """
    Neural Correction Layer: Uses a fast LLM to 'polish' phonetic mishearings.
    Tuned to JARVIS's command set and Mukunthan's environment.
    """
    if not raw_text or len(raw_text) < 3:
        return raw_text

    system_prompt = """
    # ROLE: Neural Phonetic Corrector (J.A.R.V.I.S. Core)
    Fix common Whisper transcription errors for voice commands.
    
    # RULES:
    - STRICTLY ONLY return the corrected text.
    - No explanations, no "Corrected transcription:", no quotes.
    - Do not truncate, summarize, or shorten the input; return the full corrected sentence.
    - If it's already correct, return it exactly as is.
    - Fix phonetically similar words (e.g., 'Open home' -> 'Open Chrome', 'Meat' -> 'Meeting', 'Let code' -> 'LeetCode').
    
    # CONTEXT: 
    User: Mukunthan
    Projects: AetherPrep, Virelo, Jarvis, Bento-Grid
    Tools: LeetCode, GitHub, Spotify, Gmail, Calendar, Notion
    Commands: "Open Chrome", "What are my schedules", "Sync Hub", "Neural Link", "Pulse check"
    """
    
    try:
        completion = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Fix this transcription: {raw_text}"}
            ],
            temperature=0.0,
            max_tokens=64
        )
        corrected = completion.choices[0].message.content.strip()
        # Remove any unwanted quotes if added by the LLM
        return corrected.strip('"').strip("'")
    except Exception as e:
        print(f"[STT] Neural Correction Bypass: {e}")
        return raw_text

async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Ultra-low latency STT using Groq's Whisper-large-v3-turbo plus Neural Correction.
    Optimized for JARVIS's voice-command pipeline with direct file-handle streaming.
    """
    # 1. Noise Filter: If the clip is too short or empty, kill it early.
    if not audio_bytes or len(audio_bytes) < 1000:  
        return ""

    # 2. Advanced Format Detection (Magic Bytes)
    if audio_bytes.startswith(b'\x1a\x45\xdf\xa3'):
        suffix = ".webm"
    elif audio_bytes.startswith(b'OggS'):
        suffix = ".ogg"
    elif audio_bytes.startswith(b'fLaC'):
        suffix = ".flac"
    elif audio_bytes.startswith(b'RIFF'):
        suffix = ".wav"
    else:
        suffix = ".webm" 

    # 3. Fail-Fast Monitoring (Engineer-Level Diagnostics)
    start_time = datetime.now()
    audio_size_kb = len(audio_bytes) / 1024
    print(f"[STT] Processing {audio_size_kb:.2f} KB stream (Format: {suffix})...")

    tmp_path = None
    try:
        # Create temp file for Groq SDK
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # CRITICAL FIX: Pass the file handle directly to allow SDK-level streaming
        with open(tmp_path, "rb") as f:
            response = await asyncio.wait_for(
                client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=(tmp_path, f), # SDK handles the multipart stream from the handle
                    language="en",
                    prompt="JARVIS, AetherPrep, Virelo, Mukunthan, LeetCode, GitHub, Notion, Spotify, WhatsApp, FastAPI, React, Bento-Grid, Pulse check.",
                    response_format="json", 
                    temperature=0.0
                ),
                timeout=8.0
            )
            
        # 4. Neural Post-Correction (Contextual Awareness)
        raw_text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
        duration_whisper = (datetime.now() - start_time).total_seconds()
        
        # --- NEURAL BYPASS: Skip correction for very short or clear phrases to save ~1s ---
        if len(raw_text) < 15:
            print(f"[STT] High-Confidence Bypass: \"{raw_text}\" ({duration_whisper:.2f}s)")
            return raw_text

        corrected_text = await correct_transcription(raw_text)
        duration_total = (datetime.now() - start_time).total_seconds()
        
        print(f"[STT] Raw: \"{raw_text[:50]}\" ({duration_whisper:.2f}s)")
        print(f"[STT] Neural Corrected: \"{corrected_text[:50]}\" (Total: {duration_total:.2f}s)")
        
        return corrected_text

    except asyncio.TimeoutError:
        print("[STT] Error: Transcription timed out after 8s.")
        return ""
    except Exception as e:
        print(f"[STT] Groq Transcription Error: {e}")
        return ""
    finally:
        # Clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

if __name__ == "__main__":
    # Test with empty buffer
    import asyncio
    print(asyncio.run(transcribe_audio(b"")))
