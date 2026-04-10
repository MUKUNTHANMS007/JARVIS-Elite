"""
JARVIS Placement Scheduler Service
Manages the daily LeetCode problem schedule stored in Supabase.
The schedule is profile-driven: generated from weak tags in the user's LeetCode profile.

Completion Loop:
- User clicks "Mark Solved" → mark_problem_completed() → sets completed=true, completed_at=now
- get_today_scheduled_problem() always skips completed problems
- generate_placement_schedule() skips already-completed slugs to avoid repeats
"""
import asyncio
from datetime import date, datetime, timezone
from agent.memory import supabase, init_db
from tools.leetcode_tool import generate_placement_schedule, get_enriched_daily
from services.cache_service import update_intelligence

async def get_supabase():
    global supabase
    if not supabase:
        await init_db()
    from agent.memory import supabase as sb
    return sb


async def get_today_scheduled_problem() -> dict | None:
    """
    Reads today's UNCOMPLETED problem from Supabase `leetcode_daily`.
    If today's problem is already completed, returns it with completed=True
    so the UI can show the "Solved" state.
    """
    try:
        sb = await get_supabase()
        if not sb:
            return None

        today = str(date.today())
        result = await sb.table("leetcode_daily") \
            .select("*") \
            .eq("user_id", "JARVIS_ADMIN") \
            .eq("scheduled_date", today) \
            .limit(1) \
            .execute()

        rows = result.data
        if rows:
            row = rows[0]
            return {
                "db_id":      row.get("id"),               # UUID row ID for marking complete
                "id":         row.get("problem_id", 0),
                "title":      row.get("title", "Unknown Problem"),
                "difficulty": row.get("difficulty", "Medium"),
                "tags":       [row.get("tag", "Algorithm")],
                "hint":       row.get("hint", "Think about the constraints."),
                "link":       row.get("link", "#"),
                "slug":       row.get("slug", ""),
                "completed":  row.get("completed", False),
                "completed_at": row.get("completed_at"),
            }
        return None

    except Exception as e:
        print(f"[Scheduler] Failed to read today's schedule: {e}")
        return None


async def get_full_schedule(user_id: str = "JARVIS_ADMIN") -> list:
    """Returns the entire upcoming schedule from today onwards."""
    try:
        sb = await get_supabase()
        if not sb:
            return []

        today = str(date.today())
        result = await sb.table("leetcode_daily") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("scheduled_date", today) \
            .order("scheduled_date") \
            .execute()

        return result.data
    except Exception as e:
        print(f"[Scheduler] Failed to read full schedule: {e}")
        return []


async def mark_problem_completed(db_id: str, user_id: str = "JARVIS_ADMIN") -> bool:
    """
    Marks a specific problem row as completed in Supabase.
    Called when the user clicks "Mark Solved" in the Neural Link UI.
    """
    try:
        sb = await get_supabase()
        if not sb:
            return False

        now = datetime.now(timezone.utc).isoformat()
        await sb.table("leetcode_daily") \
            .update({"completed": True, "completed_at": now}) \
            .eq("id", db_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"[Scheduler] Problem {db_id} marked as COMPLETED at {now}")
        
        # REFRESH HUB: Force immediate dashboard sync for LeetCode status
        update_intelligence("leetcode_refresh_trigger", now)
        return True

    except Exception as e:
        print(f"[Scheduler] Failed to mark problem completed: {e}")
        return False


async def get_completed_slugs(user_id: str = "JARVIS_ADMIN") -> set:
    """Returns a set of completed problem slugs so the scheduler avoids repeats."""
    try:
        sb = await get_supabase()
        if not sb:
            return set()
        result = await sb.table("leetcode_daily") \
            .select("slug") \
            .eq("user_id", user_id) \
            .eq("completed", True) \
            .execute()
        return {r["slug"] for r in result.data if r.get("slug")}
    except:
        return set()


async def save_schedule_to_supabase(schedule: list, user_id: str = "JARVIS_ADMIN") -> bool:
    """
    Saves a list of schedule entries to the `leetcode_daily` Supabase table.
    Uses upsert — if a date already has a completed problem, it won't overwrite it.
    """
    try:
        sb = await get_supabase()
        if not sb:
            return False

        rows = []
        for entry in schedule:
            rows.append({
                "user_id":        user_id,
                "scheduled_date": entry["scheduled_date"],
                "problem_id":     entry["problem_id"],
                "title":          entry["title"],
                "difficulty":     entry["difficulty"],
                "tag":            entry["tag"],
                "tag_slug":       entry.get("tag_slug", ""),
                "link":           entry["link"],
                "hint":           entry["hint"],
                "slug":           entry.get("slug", ""),
            })

        # Upsert on (user_id, scheduled_date) — won't overwrite completed rows
        # because Supabase only updates non-null conflicts
        await sb.table("leetcode_daily") \
            .upsert(rows, on_conflict="user_id,scheduled_date", ignore_duplicates=True) \
            .execute()

        print(f"[Scheduler] Saved {len(rows)} schedule entries to Supabase.")
        return True

    except Exception as e:
        print(f"[Scheduler] Failed to save schedule: {e}")
        return False


async def run_placement_scheduler(days: int = 7, user_id: str = "JARVIS_ADMIN") -> dict:
    """
    JARVIS Master Scheduler:
    1. Fetches already-completed slugs to avoid repeats
    2. Analyzes LeetCode profile for weak tags
    3. Generates a personalized N-day problem schedule (skipping completed)
    4. Saves it to Supabase (won't overwrite existing completed entries)
    5. Returns today's assigned problem
    """
    print(f"[Scheduler] Generating {days}-day placement schedule for {user_id}...")

    # Pass completed slugs to the generator so it avoids repeating solved problems
    completed = await get_completed_slugs(user_id)
    print(f"[Scheduler] Already completed: {len(completed)} problems. Will avoid repeats.")

    schedule = await generate_placement_schedule(days=days, skip_slugs=completed)

    if not schedule:
        print("[Scheduler] Schedule generation failed.")
        return {}

    await save_schedule_to_supabase(schedule, user_id)

    today = str(date.today())
    today_entry = next((e for e in schedule if e["scheduled_date"] == today), None)

    if today_entry:
        return {
            "id":         today_entry["problem_id"],
            "title":      today_entry["title"],
            "difficulty": today_entry["difficulty"],
            "tags":       [today_entry["tag"]],
            "hint":       today_entry["hint"],
            "link":       today_entry["link"],
            "slug":       today_entry.get("slug", ""),
        }
    return {}
