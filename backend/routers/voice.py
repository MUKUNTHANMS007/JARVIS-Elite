from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from voice.tts import synthesize_speech_payload

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str


@router.post("/speak")
async def speak(request: SpeakRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    audio_bytes, media_type = await synthesize_speech_payload(text)
    if not audio_bytes:
        raise HTTPException(status_code=503, detail="speech synthesis unavailable")

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )
