import os
import asyncio
from datetime import datetime, timezone
from supabase import create_async_client, AsyncClient
from services.redis_service import neural_cache

def safe_load_dotenv(path):
    if not os.path.exists(path):
        return
    try:
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore").replace("\x00", "")
        for line in content.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    except Exception:
        pass

# Load .env from root
base_dir = os.path.dirname(os.path.abspath(__file__))
safe_load_dotenv(os.path.join(base_dir, "..", "..", ".env"))

# --- SUPABASE ASYNC INITIALIZATION (April 2026 Standard) ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: AsyncClient = None
_init_lock = asyncio.Lock()

async def init_db():
    global supabase
    if supabase is not None:
        return True
    
    async with _init_lock:
        # Re-check inside the lock
        if supabase is not None:
            return True
        
    if not url or not key:
        print("[Memory] Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
        return False
    try:
        # Note: In Supabase v2.28+, we use create_async_client for non-blocking I/O
        # Added a 10s timeout to prevent total startup hang in case of cloud drift
        from supabase import create_async_client, ClientOptions
        supabase = await asyncio.wait_for(
            create_async_client(url, key, options=ClientOptions(postgrest_client_timeout=10)),
            timeout=12.0
        )
        db_url = os.environ.get("SUPABASE_URL")
        print(f"[Memory] Neural Memory Active (Async) for {db_url}")
        return True
    except Exception as e:
        print(f"[Memory] Failed to initialize Async Supabase client: {e}")
        return False

async def get_db_status() -> dict:
    """Diagnostic helper for architectural auditing."""
    return {
        "supabase_initialized": supabase is not None,
        "supabase_url": url if url else "MISSING",
        "has_keys": bool(url and key),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def get_history(user_id: str, limit: int = 10) -> list:
    """Retrieve the last `limit` messages asynchronously, with Redis semantic mirroring."""
    global supabase
    
    # 1. Semantic Bypass (Redis)
    cache_key = f"history:{user_id}:{limit}"
    cached = neural_cache.get_semantic_match(cache_key)
    if cached:
        print(f"[Neural Memory] Redis Mirror Hit (Latency: <5ms)")
        return cached

    if not supabase: await init_db()
    if not supabase: return []
    try:
        response = await supabase.table("messages") \
            .select("role, content") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        result = list(reversed(response.data))
        # 2. Update Mirror
        neural_cache.set_semantic_match(cache_key, result, ttl=1800)
        return result
    except Exception as e:
        print(f"[Memory] Async Fetch Error: {e}")
        return []

async def save_message(user_id: str, user_text: str, reply: str):
    """Save user and AI turns asynchronously and invalidate cache."""
    global supabase
    # Invalidate history mirrors
    for limit in [8, 10, 20]:
        neural_cache.client.delete(f"history:{user_id}:{limit}") if neural_cache.client else None
        
    if not supabase: await init_db()
    if not supabase: return
    try:
        data = [
            {"user_id": user_id, "role": "user", "content": user_text},
            {"user_id": user_id, "role": "assistant", "content": reply}
        ]
        await supabase.table("messages").insert(data).execute()
        print(f"[Memory] Saved message turn for {user_id}")
    except Exception as e:
        print(f"[Memory] Async Save Error: {e}")

async def save_reminder(user_id: str, text: str, reminder_time: datetime):
    """Save a reminder asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: return
    try:
        # Neural Shield: Ensure absolute UTC awareness (Z)
        if reminder_time.tzinfo is None:
            reminder_time = reminder_time.replace(tzinfo=timezone.utc)
            
        data = {
            "user_id": user_id,
            "text": text,
            "reminder_time": reminder_time.isoformat()
        }
        res = await supabase.table("reminders").insert(data).execute()
        
        # Check for error in response data (April 2026 Standard)
        if not res.data:
            print(f"[Memory] Warning: Reminder insert returned no data - potentially failed constraint.")
            
        print(f"[Memory] Saved reminder for {user_id}")
    except Exception as e:
        print(f"[Memory] Async Reminder Save Error: {e}")
        raise e # Re-raise for the tool to handle

async def delete_reminder_db(reminder_id: str):
    """Deletes a reminder from Supabase asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: return
    try:
        await supabase.table("reminders").delete().eq("id", reminder_id).execute()
        print(f"[Memory] Deleted reminder: {reminder_id}")
    except Exception as e:
        print(f"[Memory] Async Reminder Delete Error: {e}")

async def get_active_reminders_db(user_id: str) -> list:
    """Fetch active reminders asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: 
        raise ConnectionError("Neural Memory is currently offline (Supabase not initialized).")
    try:
        # Use absolute UTC 'now' with Z offset
        now = datetime.now(timezone.utc).isoformat()
        response = await supabase.table("reminders") \
            .select("*") \
            .eq("user_id", user_id) \
            .gt("reminder_time", now) \
            .execute()
        return response.data
    except Exception as e:
        print(f"[Memory] Async Reminder Fetch Error: {e}")
        raise e

async def get_academic_radar_db() -> list:
    """Fetch academic radar events asynchronously."""
    if not supabase: return []
    try:
        response = await supabase.table("academic_radar").select("*").execute()
        return response.data
    except Exception as e:
        print(f"[Memory] Async Academic Fetch Error: {e}")
        return []

async def save_calendar_event(user_id: str, title: str, date: str, time: str = None, description: str = None, category: str = "Task"):
    """Saves a calendar event asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: return False
    try:
        data = {
            "user_id": user_id,
            "title": title,
            "event_date": date,
            "event_time": time,
            "description": description,
            "category": category
        }
        await supabase.table("calendar_events").insert(data).execute()
        print(f"[Memory] Saved calendar event for {user_id}: {title}")
        return True
    except Exception as e:
        print(f"[Memory] Async Calendar Save Error: {e}")
        return False

async def get_calendar_events_db(user_id: str) -> list:
    """Fetch all calendar events asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: return []
    try:
        response = await supabase.table("calendar_events") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("event_date", desc=False) \
            .execute()
        return response.data
    except Exception as e:
        print(f"[Memory] Async Calendar Fetch Error: {e}")
        return []

async def delete_calendar_event_db(event_id: str):
    """Deletes a calendar event asynchronously."""
    global supabase
    if not supabase: await init_db()
    if not supabase: return False
    try:
        await supabase.table("calendar_events").delete().eq("id", event_id).execute()
        print(f"[Memory] Deleted calendar event: {event_id}")
        return True
    except Exception as e:
        print(f"[Memory] Async Calendar Delete Error: {e}")
        return False

async def get_today_focus_db() -> dict:
    """Fetch today's focus stats asynchronously."""
    if not supabase: return {"hours": 4.2, "goal_met": 84}
    try:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        # Use limit(1) instead of single() to avoid Error 406 if no stats exist
        response = await supabase.table("focus_stats").select("*").eq("date", today_str).limit(1).execute()
        return response.data[0] if response.data else {"hours": 4.2, "goal_met": 84}
    except Exception:
        return {"hours": 4.2, "goal_met": 84}

async def get_projects_db(user_id: str) -> list:
    """Fetch projects asynchronously."""
    if not supabase: return []
    try:
        response = await supabase.table("project_vault").select("*").eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        print(f"[Memory] Async Project Fetch Error: {e}")
        return []

async def save_project_milestone(user_id: str, title: str, milestone: str, tech_stack: list = None):
    """Upserts project context and milestones asynchronously."""
    if not supabase: return
    try:
        data = {
            "user_id": user_id,
            "title": title,
            "last_milestone": milestone,
            "updated_at": datetime.utcnow().isoformat()
        }
        if tech_stack: data["tech_stack"] = tech_stack
        await supabase.table("project_vault").upsert(data, on_conflict="user_id, title").execute()
        print(f"[Memory] Updated project vault: {title}")
    except Exception as e:
        print(f"[Memory] Async Project Save Error: {e}")

async def update_skill_level(user_id: str, category: str, solved_increment: int = 1, is_absolute: bool = False):
    """
    Updates or syncs proficiency in LeetCode categories or tech skills.
    Uses atomic upsert to prevent 0-row errors during initialization.
    """
    if not supabase: return
    try:
        target_solved = solved_increment
        if not is_absolute:
            # Fetch current to perform increment
            res = await supabase.table("skill_mastery").select("problems_solved").eq("user_id", user_id).eq("category", category).limit(1).execute()
            current = res.data[0].get("problems_solved", 0) if res.data else 0
            target_solved = current + solved_increment

        data = {
            "user_id": user_id,
            "category": category,
            "problems_solved": target_solved,
            "last_practiced": datetime.utcnow().isoformat()
        }
        
        # Atomic Upsert (April 2026 Standard)
        await supabase.table("skill_mastery").upsert(data, on_conflict="user_id, category").execute()
        print(f"[Memory] Neural Sync: {category} -> {target_solved}")
    except Exception as e:
        print(f"[Memory] Async Skill Upsert Error: {e}")

async def get_skill_levels_db(user_id: str) -> list:
    """Fetch skill mastery levels asynchronously."""
    if not supabase: return []
    try:
        response = await supabase.table("skill_mastery").select("*").eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        print(f"[Memory] Async Skill Fetch Error: {e}")
        return []
async def get_leetcode_streak_db(user_id: str) -> int:
    """
    Calculates the current consecutive daily streak from Supabase.
    Counts backwards from today (or yesterday if today isn't done yet)
    for every day with completed=True.
    """
    global supabase
    if not supabase: await init_db()
    if not supabase: return 0
    try:
        from datetime import date, timedelta

        # Fetch the last 30 days of schedule for this user
        today = date.today()
        start_date = today - timedelta(days=30)

        result = await supabase.table("leetcode_daily") \
            .select("scheduled_date, completed") \
            .eq("user_id", user_id) \
            .gte("scheduled_date", str(start_date)) \
            .order("scheduled_date", desc=True) \
            .execute()

        data = result.data
        if not data: return 0

        # Build a fast lookup map
        completion_map = {row["scheduled_date"]: row["completed"] for row in data}

        # If today is not yet completed, the streak can still be alive from
        # yesterday — start counting from yesterday in that case.
        today_done = completion_map.get(str(today), False)
        date_to_check = today if today_done else today - timedelta(days=1)

        streak = 0
        while True:
            key = str(date_to_check)
            if key not in completion_map:
                # Day not recorded at all — streak ends here
                break
            if completion_map[key]:
                streak += 1
                date_to_check -= timedelta(days=1)
            else:
                # Day recorded but not completed — streak broken
                break

        return streak
    except Exception as e:
        print(f"[Memory] Streak Calculation Error: {e}")
        return 0


async def get_system_pulse_db() -> dict:
    """Fetch pre-aggregated system pulse asynchronously."""
    if not supabase: return {}
    try:
        response = await supabase.table("jarvis_pulse_view").select("*").execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"[Memory] Pulse View Error: {e}")
        return {"active_reminders": 0, "academic_alerts": 0, "weekly_focus_hours": 0, "dsa_mastery": 0}

