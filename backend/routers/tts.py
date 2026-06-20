import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from voice.tts_engine.service import TTSService
from voice.tts_engine.providers.kokoro_provider import KokoroProvider
from voice.tts_engine.providers.edge_provider import EdgeProvider
from voice.tts_engine.providers.openai_provider import OpenAIProvider
from voice.tts_engine.providers.elevenlabs_provider import ElevenLabsProvider

logger = logging.getLogger("JARVIS-TTS-ROUTER")
router = APIRouter()

# Default global service instance using default provider
_default_service = TTSService()

# Request and Response schemas
class TTSRequest(BaseModel):
    text: str = Field(..., description="Text payload to synthesize into speech.")
    provider: Optional[str] = Field(None, description="TTS engine provider (kokoro, edge, openai, elevenlabs).")
    voice: Optional[str] = Field(None, description="Voice identifier. Default to first supported voice if unset.")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speed scaling factor (0.5 to 2.0).")
    format: Optional[str] = Field("wav", description="Target audio file format ('wav' or 'mp3').")

class TTSResponse(BaseModel):
    audio_url: str = Field(..., description="Direct link to serve the generated cache file.")
    cache_key: str = Field(..., description="Computed unique SHA-256 identifier.")
    size_bytes: int = Field(..., description="Size of the generated file.")
    provider: str = Field(..., description="Active TTS provider.")
    voice: str = Field(..., description="Synthesized voice key.")
    speed: float = Field(..., description="Synthesis speed.")
    format: str = Field(..., description="Audio format.")
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")

def get_service_for_request(provider_name: Optional[str]) -> TTSService:
    """Dependency resolution factory mapping requested providers."""
    if not provider_name:
        return _default_service

    p_name = provider_name.strip().lower()
    if p_name == "kokoro":
        return TTSService(provider=KokoroProvider())
    elif p_name == "edge":
        return TTSService(provider=EdgeProvider())
    elif p_name == "openai":
        return TTSService(provider=OpenAIProvider())
    elif p_name == "elevenlabs":
        return TTSService(provider=ElevenLabsProvider())
    else:
        logger.warning(f"Unknown request provider override: '{provider_name}'. Using default.")
        return _default_service


@router.post("", response_model=TTSResponse)
async def generate_tts(request: Request, payload: TTSRequest):
    """
    Generate speech files.
    First checks disk cache. Returns a direct audio download URL.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    fmt = (payload.format or "wav").strip().lower()
    if fmt not in {"wav", "mp3"}:
        fmt = "wav"

    try:
        service = get_service_for_request(payload.provider)
        
        # Resolve voice
        p_name = service.provider.__class__.__name__.replace("Provider", "").lower()
        default_voice = service.provider.get_supported_voices()[0]
        selected_voice = payload.voice if payload.voice in service.provider.get_supported_voices() else default_voice

        # Generate / Retrieve audio bytes
        audio_bytes, mime_type = await service.generateSpeech(
            text=text,
            voice=payload.voice,
            speed=payload.speed or 1.0,
            fmt=fmt
        )

        # Compute static audio URL reference
        cache_key = service.cache.get_hash(text, p_name, selected_voice, payload.speed or 1.0, fmt)
        
        # Build clean URL pointing to the static cache directory mount
        base_url = str(request.base_url)
        audio_url = f"{base_url.rstrip('/')}/static/tts/{cache_key}.{fmt}"

        return TTSResponse(
            audio_url=audio_url,
            cache_key=cache_key,
            size_bytes=len(audio_bytes),
            provider=p_name,
            voice=selected_voice,
            speed=payload.speed or 1.0,
            format=fmt,
            created_at=datetime.now(timezone.utc).isoformat()
        )

    except Exception as e:
        logger.error(f"TTS REST endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_tts(payload: TTSRequest):
    """
    Stream speech blocks real-time.
    Returns StreamingResponse chunks.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    fmt = (payload.format or "wav").strip().lower()
    if fmt not in {"wav", "mp3"}:
        fmt = "wav"

    try:
        service = get_service_for_request(payload.provider)
        mime_type = service._get_mime_type(fmt)

        async def _generator():
            async for chunk in service.streamSpeech(
                text=text,
                voice=payload.voice,
                speed=payload.speed or 1.0,
                fmt=fmt
            ):
                yield chunk

        return StreamingResponse(
            _generator(),
            media_type=mime_type,
            headers={"Cache-Control": "no-cache"}
        )

    except Exception as e:
        logger.error(f"TTS Streaming endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def list_voices(provider: Optional[str] = None):
    """Return all voice identifiers supported by active providers."""
    results = {}
    
    providers_to_check = []
    if provider:
        p_name = provider.strip().lower()
        if p_name in {"kokoro", "edge", "openai", "elevenlabs"}:
            providers_to_check.append(p_name)
    else:
        providers_to_check = ["kokoro", "edge", "openai", "elevenlabs"]

    for p in providers_to_check:
        try:
            service = get_service_for_request(p)
            results[p] = service.provider.get_supported_voices()
        except Exception:
            results[p] = []

    return results
