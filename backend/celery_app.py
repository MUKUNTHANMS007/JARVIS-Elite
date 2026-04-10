import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# J.A.R.V.I.S. Neural Orchestrator (Worker Layer)
# Uses Redis as the primary message broker for async task offloading.

CELERY_BROKER = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "jarvis_orchestrator",
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
    include=["tasks"] # Tasks will be defined in tasks.py
)

# Configuration Tuning
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5-minute hard limit for AI processing
    worker_concurrency=4 # Optimize for multi-core parallelism
)

def check_redis_connectivity():
    """Diagnostic tool to verify the message broker for the Neural Layer."""
    import redis
    try:
        r = redis.from_url(CELERY_BROKER)
        r.ping()
        return True
    except Exception:
        return False

# Self-Diagnostic on Import
if not check_redis_connectivity():
    print(f"[Neural Warning] Redis unreachable at {CELERY_BROKER}. Falling back to Direct Path.")

if __name__ == "__main__":
    celery_app.start()
