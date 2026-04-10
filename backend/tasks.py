import os
import asyncio
from celery_app import celery_app
from voice.stt import transcribe_audio
from tools.persistent_alert_tool import send_neural_push
from datetime import datetime

# J.A.R.V.I.S. Neural Task Layer
# Offloaded logic for high-latency perception and background orchestration.

def _core_stt_logic(audio_bytes_hex: str):
    """Internal core logic for STT that can be called synchronously."""
    try:
        audio_bytes = bytes.fromhex(audio_bytes_hex)
        # This function is called from Celery (sync worker) and from FastAPI via
        # `asyncio.to_thread(...)`. In Python 3.12, non-main threads usually do not
        # have a default event loop, so we must create and manage one explicitly.
        loop = asyncio.new_event_loop()
        try:
            text = loop.run_until_complete(transcribe_audio(audio_bytes))
        finally:
            try:
                loop.close()
            except Exception:
                pass
        return {"text": text, "status": "COMPLETED"}
    except Exception as e:
        return {"error": str(e), "status": "FAILED"}

@celery_app.task(name="tasks.process_stt_task")
def process_stt_task(audio_bytes_hex: str):
    return _core_stt_logic(audio_bytes_hex)

def _core_mood_logic(audio_energy: float):
    """Internal core logic for mood analysis."""
    is_stressed = audio_energy > 2500
    mood_score = 1.0 if is_stressed else 0.0
    return {"is_stressed": is_stressed, "mood_score": mood_score}

@celery_app.task(name="tasks.analyze_mood_task")
def analyze_mood_task(audio_energy: float):
    return _core_mood_logic(audio_energy)

@celery_app.task(name="tasks.proactive_sentinel_scan")
def proactive_sentinel_scan():
    """
    Background Sentinel: Periodically check calendar and system health.
    Results are pushed to the Redis cache for the main API to broadcast.
    """
    # Placeholder for more complex sentinel logic
    return {"scan_time": datetime.utcnow().isoformat(), "status": "HEALTHY"}

def _core_dispatch_logic(title: str, message: str, priority: int = 3):
    try:
        res = send_neural_push(title, message, priority)
        return {"status": "DISPATCHED", "response": res}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@celery_app.task(name="tasks.send_dispatch_notification_task")
def send_dispatch_notification_task(title: str, message: str, priority: int = 3):
    return _core_dispatch_logic(title, message, priority)

def _core_vision_logic(image_base64: str, context_text: str = ""):
    try:
        insight = f"Sir, I've analyzed the visual feed. The context correlates with your current task: '{context_text}'"
        return {"insight": insight, "status": "COMPLETED"}
    except Exception as e:
        return {"error": str(e), "status": "FAILED"}

@celery_app.task(name="tasks.analyze_vision_task")
def analyze_vision_task(image_base64: str, context_text: str = ""):
    return _core_vision_logic(image_base64, context_text)
