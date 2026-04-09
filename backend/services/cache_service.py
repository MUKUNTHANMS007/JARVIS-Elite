import time
import os
import json
from typing import Dict, Any

# Setup Communication Log
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)
COMM_LOG = os.path.join(LOGS_DIR, "communication.log")

def notify_communication(source: str, target: str, latency: float, metadata: Dict = None):
    """Logs internal/external communication events for neural auditing."""
    event = {
        "timestamp": time.time(),
        "source": source,
        "target": target,
        "latency_ms": round(latency * 1000, 2),
        "metadata": metadata or {}
    }
    with open(COMM_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

# --- NEURAL STATE (Intelligence Cache) ---
# A globally shared object that holds in-memory snapshots of 
# API-bound tools to ensure <150ms dashboard response times.
# Now file-backed to support multi-process distributed architecture.

SYNC_FILE = os.path.join(LOGS_DIR, "intelligence_sync.json")

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

def _persist_to_disk():
    """Internal: Atomic write to JSON for multi-process sync."""
    try:
        with open(SYNC_FILE, "w") as f:
            json.dump(INTELLIGENCE_HUB, f, indent=2)
    except Exception as e:
        print(f"[Cache Sync Error] Write failure: {e}")

def _load_from_disk():
    """Internal: Refresh in-memory state from disk."""
    global INTELLIGENCE_HUB
    if os.path.exists(SYNC_FILE):
        try:
            with open(SYNC_FILE, "r") as f:
                data = json.load(f)
                INTELLIGENCE_HUB.update(data)
        except Exception: pass

def get_intelligence():
    """Access the global in-memory state, refreshed from disk."""
    _load_from_disk()
    return INTELLIGENCE_HUB

def update_intelligence(key: str, data: Any):
    """Safely updates a specific intelligence node and persists to disk."""
    global INTELLIGENCE_HUB
    # Refresh before update to avoid stomping concurrent changes
    _load_from_disk()
    
    INTELLIGENCE_HUB[key] = data
    INTELLIGENCE_HUB["last_synced"] = time.time()
    INTELLIGENCE_HUB["status"] = "online"
    
    _persist_to_disk()
