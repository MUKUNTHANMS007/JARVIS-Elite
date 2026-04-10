import asyncio
import re
from fastapi import APIRouter
from agent.memory import get_calendar_events_db, get_today_focus_db
from tools.leetcode_tool import get_leetcode_streak
from tools.gmail_tool import check_gmail_inbox
from tools.spotify_tool import get_current_playback_info, pause_spotify
from services.cache_service import INTELLIGENCE_HUB
from datetime import datetime, timezone

router = APIRouter()

async def safe_fetch(func, *args, default=None, **kwargs):
    """Utility to prevent one failing tool from crashing the whole dashboard."""
    try:
        # If the tool is not async, run it in a thread to prevent blocking
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return await asyncio.to_thread(func, *args, **kwargs)
    except Exception as e:
        print(f"[Jarvis Core] Task {func.__name__} failed: {e}")
        return default

@router.get("/stats")
async def get_core_dashboard_stats(user_id: str = "JARVIS_ADMIN"):
    """
    Aggregates stats concurrently for the Bento Grid.
    Uses parallel execution for sub-500ms response times.
    """
    
    # Run only fast local DB tasks in parallel
    tasks = [
        get_calendar_events_db(user_id),
        get_today_focus_db()
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Destructure results
    raw_events, focus_stats = results
    
    # Access Intelligence Hub for synced/slow data
    hub = INTELLIGENCE_HUB

    # 1. Process LeetCode (from Cache)
    leetcode_data = hub.get("leetcode", {})
    streak = leetcode_data.get("streak", 0)

    # 2. Process Academic Radar (Live DB)
    academic_events = []
    # Use timezone-aware local date
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Filter and sort: Only upcoming events
    upcoming = sorted(
        [e for e in raw_events if e.get("event_date", "") >= today_str],
        key=lambda x: x.get("event_date", "")
    )

    for event in upcoming[:3]:
        raw_date = event.get("event_date", "")
        try:
            # Extract just the day number for the Bento UI
            day_str = str(datetime.strptime(raw_date, "%Y-%m-%d").day)
        except (ValueError, TypeError):
            day_str = "??"
            
        academic_events.append({
            "title": event.get("title", "Scheduled Event"),
            "date": day_str,
            "task_type": event.get("category", "Task")
        })

    # 3. Process Gmail Pulse (from Cache)
    gmail_count = hub.get("gmail_unread", 0)

    # 4. Process Spotify Status (Live for immediate feedback)
    spotify_res = await safe_fetch(get_current_playback_info, default="Inactive")
    
    if any(word in str(spotify_res) for word in ["Nothing", "Inactive", "Disconnected"]):
        spotify_status = "Inactive"
    else:
        # Efficient cleaning: Remove common fluff words
        spotify_status = (
            str(spotify_res).replace("You are currently listening to '", "")
            .replace("'", "")
            .replace("Sir.", "")
            .split(" - ")[0] # Optional: Get just the song name, ignore artist for space
            .strip()
        )

    return {
        "leetcode_streak": streak,
        "academic": academic_events,
        "focus": focus_stats,
        "gmail_count": gmail_count,
        "spotify_status": spotify_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/spotify/pause")
async def pause_spotify_playback():
    """Direct-path endpoint for 'Auto-Duck' functionality."""
    return await safe_fetch(pause_spotify, default="Failed to pause")
@router.post("/focus")
async def start_focus_routine(user_id: str = "JARVIS_ADMIN"):
    """
    Initializes the morning focus routine.
    Fetches focus tasks and prepares a verbal briefing.
    """
    focus_stats = await get_today_focus_db()
    
    # Construct a high-fidelity greeting
    now = datetime.now()
    hour = now.hour
    greeting = "Good evening" if hour >= 18 else "Good afternoon" if hour >= 12 else "Good morning"
    
    # Check for Batman Mode
    is_batman = INTELLIGENCE_HUB.get(f"batman_mode_{user_id}", False)
    if is_batman:
        briefing = f"Good evening, Master Wayne. The Batcomputer is initialized. Gotham requires your attention. Your focus for tonight is: {focus_stats.get('task', 'maintaining the mission')}."
    else:
        briefing = f"{greeting}, Sir. I've initialized the neural core. Your focus for today is logged as: {focus_stats.get('task', 'unassigned')}. Ready for your instruction."
        
    return {
        "status": "initialized",
        "audio_briefing": briefing,
        "focus_data": focus_stats
    }
