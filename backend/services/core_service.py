from datetime import datetime
from agent.memory import get_academic_radar_db, get_today_focus_db

from tools.spotify_tool import search_and_play_spotify
from tools.leetcode_tool import sync_leetcode_intelligence

async def get_academic_radar():
    """Fetch academic radar events from Supabase."""
    return await get_academic_radar_db()

def update_academic_event(title: str, date: str, task_type: str = "Review"):
    """Mock for updating academic events (future integration)."""
    return {"status": "success", "event": title}

async def get_today_focus():
    """Fetch today's focus stats from Supabase."""
    return await get_today_focus_db()

def add_focus_time(hours: float):
    """Mock for adding focus time (future integration)."""
    return {"status": "success", "total_hours": 4.2 + hours}

async def initiate_focus_routine():
    """
    JARVIS Protocol: 'Focus Mode'. 
    Blends environmental control with placement intelligence.
    """
    # 1. Start the Environment (Non-blocking search and play)
    # We use 'lofi hip hop for coding' as the gold standard for your PSG iTech sprints
    music_status = search_and_play_spotify("lofi hip hop for coding")
    
    # 2. Sync Placement Intelligence (Verified 250 Status)
    leetcode_intel = await sync_leetcode_intelligence()
    
    # Extract focus areas with high-fidelity safety
    focus_areas = leetcode_intel.get("focus_areas", [])
    focus_topic = focus_areas[0] if focus_areas else "Data Structures"
    
    # 250 Verified Baseline
    total = leetcode_intel.get("total", 250)
    
    # 3. Formulate the JARVIS briefing (Conversational & Tactical)
    briefing = (
        f"Focus Mode initiated, Sir. Acoustic environment synchronized. "
        f"You are currently at {total} LeetCode problems. To close the placement gap, "
        f"I recommend we focus on {focus_topic} patterns today."
    )
    
    return {
        "audio_briefing": briefing,
        "music_status": music_status,
        "suggested_tag": focus_topic,
        "total_solved": total
    }
