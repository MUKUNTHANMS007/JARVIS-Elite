from fastapi import APIRouter
import os
from services.mock_services import get_unread_count, get_notification_count, get_update_count
from services.spotify_service import get_now_playing, get_spotify_client
from services.groq_service import summarize_inbox
from tools.gmail_tool import get_unread_count_raw as get_real_gmail_count
from tools.leetcode_tool import get_leetcode_stats, get_leetcode_streak

router = APIRouter()

# ── LEFT CARD ──────────────────────────────────────────

@router.get("/inbox/count")
async def inbox_count():
    gmail   = get_real_gmail_count()
    github  = await get_notification_count()
    leetcode = get_leetcode_stats()
    
    total = gmail + github + (leetcode.get('total_solved', 0) if isinstance(leetcode, dict) else 0)

    return {
        "total": total,
        "breakdown": {
            "gmail": gmail,
            "github": github,
            "leetcode": leetcode
        },
        "has_new": total > 0
    }

# ── RIGHT CARD ─────────────────────────────────────────

@router.get("/spotify/now-playing")
async def now_playing():
    track = await get_now_playing()
    if not track or not track.get("item"):
        return {"status": "offline", "track": None}

    return {
        "status": "syncing" if track.get("is_playing") else "paused",
        "track": {
            "name": track["item"]["name"],
            "artist": track["item"]["artists"][0]["name"],
            "album_art": track["item"]["album"]["images"][0]["url"],
            "progress_ms": track.get("progress_ms", 0),
            "duration_ms": track["item"]["duration_ms"],
            "progress_pct": round((track.get("progress_ms", 0) / track["item"]["duration_ms"]) * 100) if track["item"].get("duration_ms") else 0
        }
    }

@router.post("/spotify/control")
async def spotify_control(action: str):
    try:
        sp = get_spotify_client()
        if action == "play":    sp.start_playback()
        elif action == "pause":   sp.pause_playback()
        elif action == "next":    sp.next_track()
        elif action == "prev":    sp.previous_track()
        return {"status": "ok", "action": action}
    except Exception as e:
        return {"status": "error", "error": str(e)}
