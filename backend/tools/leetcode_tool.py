import httpx
import os
import re
import time
import asyncio
import random
from datetime import date, timedelta
from agent.memory import update_skill_level, get_leetcode_streak_db

# --- LEETCODE API (noworneverev) ---
BASE_URL = "https://leetcode-api-pied.vercel.app"
USERNAME = "MUKUNTHAN_MS"

# --- JARVIS Pulse Cache ---
_LEETCODE_CACHE = {}
_LEETCODE_LAST_UPDATE = 0

# Placement-critical tags for PSG iTech companies
PLACEMENT_TAGS = [
    {"tag": "dynamic-programming", "name": "Dynamic Programming"},
    {"tag": "graph",               "name": "Graph"},
    {"tag": "array",               "name": "Array"},
    {"tag": "string",              "name": "String"},
    {"tag": "sliding-window",      "name": "Sliding Window"},
    {"tag": "binary-search",       "name": "Binary Search"},
    {"tag": "tree",                "name": "Tree"},
    {"tag": "heap-priority-queue", "name": "Heap"},
]

async def get_enriched_daily():
    """
    2-Step Fetch:
    1. /daily  -> get slug
    2. /problems list -> search by slug for full title, difficulty, tags
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Get today's slug
            daily_res = await client.get(f"{BASE_URL}/daily")
            if daily_res.status_code != 200:
                return None
            daily_data = daily_res.json()
            link_path = daily_data.get("link", "")
            # e.g. /problems/decode-the-slanted-ciphertext/

            slug_match = re.search(r"/problems/([^/]+)/?", link_path)
            if not slug_match:
                return None
            slug = slug_match.group(1)
            full_link = f"https://leetcode.com{link_path}"

            # Step 2: Search all problems list for matching slug
            problems_res = await client.get(f"{BASE_URL}/problems")
            if problems_res.status_code != 200:
                return {
                    "id": 0,
                    "title": slug.replace("-", " ").title(),
                    "difficulty": "Medium",
                    "tags": ["Algorithm"],
                    "hint": "Analyze the constraints. Think about what data structure fits best.",
                    "link": full_link,
                    "slug": slug
                }

            all_problems = problems_res.json()
            matched = next(
                (p for p in all_problems
                 if p.get("title_slug") == slug or p.get("titleSlug") == slug),
                None
            )

            if matched:
                raw_tags = matched.get("topicTags", matched.get("topic_tags", []))
                tag_names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in raw_tags]
                return {
                    "id":         int(matched.get("frontend_id", matched.get("id", 0)) or 0),
                    "title":      matched.get("title", slug.replace("-", " ").title()),
                    "difficulty": matched.get("difficulty", "Medium"),
                    "tags":       tag_names if tag_names else ["Algorithm"],
                    "hint":       "Analyze the constraints carefully. Think about optimal substructure.",
                    "link":       full_link,
                    "slug":       slug,
                }
            else:
                return {
                    "id":         0,
                    "title":      slug.replace("-", " ").title(),
                    "difficulty": "Medium",
                    "tags":       ["Algorithm"],
                    "hint":       "Analyze the constraints. Think about what data structure fits best.",
                    "link":       full_link,
                    "slug":       slug
                }

    except Exception as e:
        print(f"[LeetCode Tool] Enriched daily fetch failed: {e}")
        return None


async def get_weak_tags_from_profile() -> list:
    """Fetches skill profile and returns weakest placement-critical tags sorted by priority."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            skill_res = await client.get(f"{BASE_URL}/user/{USERNAME}/skills")
            if skill_res.status_code != 200:
                return PLACEMENT_TAGS[:4]

            skills_data = skill_res.json()
            all_skills = (
                skills_data.get("advanced", []) +
                skills_data.get("intermediate", []) +
                skills_data.get("fundamental", [])
            )
            solved_map = {s["tagSlug"]: s["problemsSolved"] for s in all_skills}

            scored = []
            for t in PLACEMENT_TAGS:
                solved = solved_map.get(t["tag"], 0)
                scored.append({**t, "solved": solved})

            scored.sort(key=lambda x: x["solved"])
            return scored

    except Exception as e:
        print(f"[LeetCode Tool] Skill fetch failed: {e}")
        return PLACEMENT_TAGS[:4]


async def generate_placement_schedule(days: int = 7, skip_slugs: set = None) -> list:
    """
    JARVIS Intelligence: Analyze LeetCode profile -> build personalized N-day problem schedule.
    skip_slugs: set of already-completed slugs to avoid repeating.
    """
    if skip_slugs is None:
        skip_slugs = set()
    else:
        skip_slugs = set(skip_slugs)  # copy to avoid mutating caller's set

    weak_tags = await get_weak_tags_from_profile()
    schedule = []

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            problems_res = await client.get(f"{BASE_URL}/problems")
            all_problems = problems_res.json() if problems_res.status_code == 200 else []

        today = date.today()
        tag_cycle = (weak_tags * ((days // len(weak_tags)) + 1))[:days]

        for i, tag_info in enumerate(tag_cycle):
            target_date = today + timedelta(days=i)
            tag_slug = tag_info["tag"]

            # Filter by tag slug match — skip already completed
            tag_problems = []
            for p in all_problems:
                p_slug = p.get("title_slug", p.get("titleSlug", ""))
                if p_slug in skip_slugs:
                    continue
                raw_tags = p.get("topicTags", p.get("topic_tags", []))
                slugs = [t.get("slug", t.get("tagSlug", "")) if isinstance(t, dict) else str(t) for t in raw_tags]
                if tag_slug in slugs and p.get("difficulty", "") in ["Medium", "Hard"]:
                    tag_problems.append(p)

            if not tag_problems:
                # Fallback: any medium not yet scheduled/completed
                tag_problems = [
                    p for p in all_problems
                    if p.get("difficulty") == "Medium"
                    and p.get("title_slug", p.get("titleSlug", "")) not in skip_slugs
                ]

            if not tag_problems:
                continue

            picked = random.choice(tag_problems[:50])
            slug = picked.get("title_slug", picked.get("titleSlug", ""))
            skip_slugs.add(slug)  # prevent same problem appearing twice in this schedule

            schedule.append({
                "scheduled_date": str(target_date),
                "tag":            tag_info["name"],
                "tag_slug":       tag_slug,
                "problem_id":     int(picked.get("frontend_id", picked.get("id", 0)) or 0),
                "title":          picked.get("title", slug.replace("-", " ").title()),
                "difficulty":     picked.get("difficulty", "Medium"),
                "link":           f"https://leetcode.com/problems/{slug}/",
                "hint":           "Focus on optimal substructure. What can be reused or cached?",
                "slug":           slug
            })

    except Exception as e:
        print(f"[LeetCode Tool] Schedule generation failed: {e}")

    return schedule


async def sync_leetcode_intelligence(sync: bool = False):
    """
    JARVIS Deep-Scan: Fetches granular stats.
    sync=True: Commits results to Supabase (update_skill_level).
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        try:
            user_res = await client.get(f"{BASE_URL}/user/{USERNAME}")
            if user_res.status_code != 200:
                return {"error": f"API Status {user_res.status_code}"}

            data = user_res.json()
            submit_stats = data.get("submitStats", {}).get("acSubmissionNum", [])

            total_solved  = next((i["count"] for i in submit_stats if i["difficulty"] == "All"),    0)
            easy_solved   = next((i["count"] for i in submit_stats if i["difficulty"] == "Easy"),   0)
            medium_solved = next((i["count"] for i in submit_stats if i["difficulty"] == "Medium"), 0)
            hard_solved   = next((i["count"] for i in submit_stats if i["difficulty"] == "Hard"),   0)

            if sync:
                await update_skill_level("JARVIS_ADMIN", "DSA", total_solved, is_absolute=True)

            weak = await get_weak_tags_from_profile()
            focus_tags = [t["name"] for t in weak[:3]]
            focus_msg = f"focus on: {', '.join(focus_tags)}" if focus_tags else "mastering Hard patterns"

            local_streak = await get_leetcode_streak_db("JARVIS_ADMIN")
            streak_res = await client.get(f"{BASE_URL}/user/{USERNAME}/streak")
            external_streak = streak_res.json().get("streak", 0) if streak_res.status_code == 200 else 0
            streak = max(local_streak, external_streak)
            
            # --- Daily Challenge Enrichment ---
            daily_problem = await get_enriched_daily()
            streak_alert = " Your streak has reset in the War-Room. Regain momentum immediately." if streak == 0 else ""

            return {
                "total": total_solved, "easy": easy_solved,
                "medium": medium_solved, "hard": hard_solved,
                "streak": streak, "focus_areas": focus_tags,
                "daily_problem": daily_problem,
                "message": f"Sir, solved: {total_solved}. Recommend we {focus_msg}.{streak_alert}"
            }
        except Exception as e:
            return {"error": f"Intelligence Sync Failed: {str(e)}"}


async def get_leetcode_stats(username: str = USERNAME, sync: bool = False) -> dict:
    global _LEETCODE_CACHE, _LEETCODE_LAST_UPDATE
    
    # Neural Pulse Cache: 15-minute window for LeetCode stats
    if time.time() - _LEETCODE_LAST_UPDATE < 900 and _LEETCODE_CACHE and not sync:
        return _LEETCODE_CACHE

    intel = await sync_leetcode_intelligence(sync=sync)
    if "error" in intel:
        return {
            "total_solved": 0, "easy": 0, "medium": 0,
            "hard": 0, "streak": 0, "message": intel["error"]
        }
    
    stats = {
        "total_solved": intel["total"], "easy":   intel["easy"],
        "medium":       intel["medium"], "hard":  intel["hard"],
        "streak":       intel["streak"], "message": intel["message"]
    }
    
    # Update cache if it's the main username
    if username == USERNAME:
        _LEETCODE_CACHE = stats
        _LEETCODE_LAST_UPDATE = time.time()
        
    return stats


async def get_placement_roadmap() -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(f"{BASE_URL}/problems?difficulty=Hard")
            problems = res.json()
            if isinstance(problems, list) and problems:
                p = random.choice(problems[:20])
                return f"For your next sprint, I've selected: '{p.get('title')}'."
    except:
        pass
    return "I recommend mastering 'Course Schedule II' for your Zoho session."


async def get_leetcode_streak(username: str = USERNAME) -> int:
    stats = await get_leetcode_stats(username)
    return stats.get("streak", 0)


async def mark_today_solved() -> str:
    """
    JARVIS Placement Tracker: Marks today's scheduled LeetCode problem as COMPLETED.
    No arguments needed — automatically finds today's row in Supabase by date.
    Returns a confirmation message for JARVIS to speak.
    """
    try:
        from agent.memory import supabase, init_db
        from datetime import date, datetime, timezone

        if not supabase:
            await init_db()
        from agent.memory import supabase as sb

        if not sb:
            return "Sir, the neural memory is offline. I cannot update the schedule at this time."

        today = str(date.today())

        # Find today's uncompleted row
        result = await sb.table("leetcode_daily") \
            .select("id, title, completed") \
            .eq("scheduled_date", today) \
            .eq("user_id", "JARVIS_ADMIN") \
            .limit(1) \
            .execute()

        rows = result.data
        if not rows:
            return "Sir, I couldn't find a scheduled problem for today. Try running 'Generate Schedule' first."

        row = rows[0]
        if row.get("completed"):
            return f"Sir, '{row.get('title')}' was already marked as solved today. Excellent efficiency."

        # Mark as completed
        now = datetime.now(timezone.utc).isoformat()
        await sb.table("leetcode_daily") \
            .update({"completed": True, "completed_at": now}) \
            .eq("id", row["id"]) \
            .execute()

        # Update Skill Mastery Level in Supabase Core
        # This keeps the Dashboard Pulse synchronized without waiting for a re-scan.
        await update_skill_level("JARVIS_ADMIN", "DSA", solved_increment=1)

        title = row.get("title", "today's problem")
        return f"Outstanding, Sir. '{title}' has been marked as solved and removed from your pending queue. The schedule will auto-advance to the next problem tomorrow. Placement training is on track."

    except Exception as e:
        return f"Sir, I encountered an error updating the schedule: {str(e)}"


async def analyze_recent_submissions() -> str:
    """
    Neural Performance Monitor: Scans recent history and providing architectural critiques.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(f"{BASE_URL}/user/{USERNAME}/submissions")
            if res.status_code != 200:
                return "Neural Sync Error: Unable to fetch submission telemetry."
            
            submissions = res.json()
            latest_ac = next((s for s in submissions if s.get("statusDisplay") == "Accepted"), None)
            
            if not latest_ac:
                return "Sir, I detect no recent 'Accepted' submissions on your profile. The War-Room requires active problem-solving for evaluation."
            
            title = latest_ac.get("title")
            slug = latest_ac.get("titleSlug")
            difficulty = "Medium" # Default fallback
            
            # Architect Insights mapping
            insights = {
                "rotate-image": "Rotating a matrix in-place requires O(1) space. Sir, ensure you utilized the Transpose + Reverse pattern rather than a temporary buffer to maintain architectural efficiency.",
                "3sum": "For 3Sum, the O(n²) Two-Pointer approach is the elite standard. Avoid nested Maps that could regresses into O(n³) in high-cardinality edge cases.",
                "two-sum": "A fundamental exercise. I assume you utilized the single-pass Hash Map for O(n) performance, Sir.",
                "container-with-most-water": "A classic Greedy Two-Pointer problem. Convergence is optimal when moving the shorter boundary, Sir."
            }
            
            default_insight = f"Sir, I see you've successfully cleared '{title}'. I am analyzing your submission logic. For {difficulty} challenges, focus on minimizing space complexity to O(1) where possible."
            architect_critique = insights.get(slug, default_insight)
            
            return f"Strategic Audit Complete: Recent Solve: {title}. {architect_critique}"

    except Exception as e:
        return f"Neural Pulse Failure: {str(e)}"
