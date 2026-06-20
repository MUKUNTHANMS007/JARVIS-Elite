import time
import os
import json
import threading
import tempfile
from typing import Dict, Any

# Setup Logs Dir
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)
COMM_LOG = os.path.join(LOGS_DIR, "communication.log")
SYNC_FILE = os.path.join(LOGS_DIR, "intelligence_sync.json")

# Maximum size for the communication log before rotation (5 MB)
_COMM_LOG_MAX_BYTES = 5 * 1024 * 1024

# Thread lock protecting all writes to INTELLIGENCE_HUB and the sync file.
# A single RLock is sufficient because all callers are in the same process.
_hub_lock = threading.RLock()


def notify_communication(source: str, target: str, latency: float, metadata: Dict = None):
    """Logs internal/external communication events for neural auditing.
    Rotates the log file when it exceeds _COMM_LOG_MAX_BYTES.
    """
    event = {
        "timestamp": time.time(),
        "source": source,
        "target": target,
        "latency_ms": round(latency * 1000, 2),
        "metadata": metadata or {}
    }
    try:
        # Rotate if over size limit
        if os.path.exists(COMM_LOG) and os.path.getsize(COMM_LOG) >= _COMM_LOG_MAX_BYTES:
            rotated = COMM_LOG + ".1"
            if os.path.exists(rotated):
                os.remove(rotated)
            os.rename(COMM_LOG, rotated)
        with open(COMM_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[Cache Comm Log] Write error: {e}")


# --- NEURAL STATE (Intelligence Cache) ---
# Pure in-memory dict — the single source of truth at runtime.
# Written to disk only on update (for crash recovery), NOT read on every get().
# The disk file is loaded once at startup via _load_from_disk_once().

INTELLIGENCE_HUB: Dict[str, Any] = {
    "gmail_unread": 0,
    "gmail_briefing": "Sir, I'm currently scanning your communication layer...",
    "leetcode": {
        "total": 0, "easy": 0, "medium": 0, "hard": 0, "streak": 0,
        "message": "Initializing DSA intelligence sync..."
    },
    "github": [],
    "calendar": [],
    "last_synced": 0,
    "status": "initializing",
    "agent_state": "IDLE",
    "mood_score": 0.0
}

_disk_loaded = False


def _load_from_disk_once():
    """Load persisted state from disk exactly once at startup.
    Subsequent calls are no-ops — hot-path callers always use the in-memory dict.
    """
    global _disk_loaded
    if _disk_loaded:
        return
    with _hub_lock:
        if _disk_loaded:
            return
        if os.path.exists(SYNC_FILE):
            try:
                with open(SYNC_FILE, "r") as f:
                    data = json.load(f)
                INTELLIGENCE_HUB.update(data)
                print("[Cache] Restored intelligence state from disk.")
            except Exception as e:
                print(f"[Cache] Could not restore state from disk: {e}")
        _disk_loaded = True


def _persist_to_disk():
    """Atomic write: write to a temp file, then rename over the target.
    Rename is atomic on POSIX; on Windows it replaces the target atomically
    since Python 3.3+ (os.replace).
    Must be called while _hub_lock is held.
    """
    try:
        dir_ = os.path.dirname(SYNC_FILE)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_, suffix=".tmp", delete=False
        ) as tf:
            json.dump(INTELLIGENCE_HUB, tf, indent=2, default=str)
            tmp_path = tf.name
        os.replace(tmp_path, SYNC_FILE)
    except Exception as e:
        print(f"[Cache Sync Error] Write failure: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# Eagerly load from disk when this module is first imported.
_load_from_disk_once()


def get_intelligence() -> Dict[str, Any]:
    """Return the in-memory intelligence hub.
    No disk I/O — safe to call from async hot paths."""
    return INTELLIGENCE_HUB


def update_intelligence(key: str, data: Any):
    """Atomically update a single intelligence node and persist to disk."""
    with _hub_lock:
        INTELLIGENCE_HUB[key] = data
        INTELLIGENCE_HUB["last_synced"] = time.time()
        INTELLIGENCE_HUB["status"] = "online"
        _persist_to_disk()
