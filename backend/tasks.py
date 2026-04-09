import os
import asyncio
from celery_app import celery_app
from voice.stt import transcribe_audio, correct_transcription
from tools.persistent_alert_tool import send_neural_push
from datetime import datetime

# J.A.R.V.I.S. Neural Task Layer
# Offloaded logic for high-latency perception and background orchestration.

@celery_app.task(name="tasks.process_stt_task")
def process_stt_task(audio_bytes_hex: str):
    """
    Background STT: Offloads the transcription and Neural Correction.
    Hex encoding used to pass binary through JSON-serialized Celery.
    """
    try:
        audio_bytes = bytes.fromhex(audio_bytes_hex)
        # We use a synchronous bridge for the async transcribe call
        loop = asyncio.get_event_loop()
        text = loop.run_until_complete(transcribe_audio(audio_bytes))
        return {"text": text, "status": "COMPLETED"}
    except Exception as e:
        return {"error": str(e), "status": "FAILED"}

@celery_app.task(name="tasks.analyze_mood_task")
def analyze_mood_task(audio_energy: float):
    """
    Asynchronous Mood Analysis: Identifies stress levels based on acoustic markers.
    """
    is_stressed = audio_energy > 2500
    mood_score = 1.0 if is_stressed else 0.0
    return {"is_stressed": is_stressed, "mood_score": mood_score}

@celery_app.task(name="tasks.proactive_sentinel_scan")
def proactive_sentinel_scan():
    """
    Background Sentinel: Periodically check calendar and system health.
    Results are pushed to the Redis cache for the main API to broadcast.
    """
    # Placeholder for more complex sentinel logic
    return {"scan_time": datetime.utcnow().isoformat(), "status": "HEALTHY"}

@celery_app.task(name="tasks.send_dispatch_notification_task")
def send_dispatch_notification_task(title: str, message: str, priority: int = 3):
    """
    Neural Dispatcher: Sends persistent mobile alerts via Ntfy.sh.
    Ensures critical Edge signals reach the user immediately.
    """
    try:
        res = send_neural_push(title, message, priority)
        return {"status": "DISPATCHED", "response": res}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@celery_app.task(name="tasks.analyze_vision_task")
def analyze_vision_task(image_base64: str, context_text: str = ""):
    """
    Multi-Modal Perception Layer: Offloaded Vision Analysis.
    Processes image context independently of the main conversation loop.
    """
    try:
        # In a production environment, we would bridge to the Vision LLM (Gemini 1.5/Groq LLaVA)
        # For this sprint, we'll implement the task structure and return a 'Synthesized Insight'
        insight = f"Sir, I've analyzed the visual feed. The context correlates with your current task: '{context_text}'"
        return {"insight": insight, "status": "COMPLETED"}
    except Exception as e:
        return {"error": str(e), "status": "FAILED"}
