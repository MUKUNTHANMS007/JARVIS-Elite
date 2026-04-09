import asyncio
from tools.leetcode_tool import get_enriched_daily
from agent.memory import get_today_focus_db
from services.scheduler_service import get_today_scheduled_problem
from services.cache_service import INTELLIGENCE_HUB

# Map DSA tags to premium illustrations in /public/assets/dsa/
THEME_MAP = {
    "dynamic-programming": {"id": "dp",     "theme": "Dynamic Programming", "img": "/assets/dsa/dp.png"},
    "graph":               {"id": "graph",  "theme": "Graph Theory",        "img": "/assets/dsa/graph.png"},
    "tree":                {"id": "tree",   "theme": "Tree Structures",     "img": "/assets/dsa/tree.png"},
    "binary-tree":         {"id": "tree",   "theme": "Binary Trees",        "img": "/assets/dsa/tree.png"},
    "array":               {"id": "array",  "theme": "Arrays & Hashing",    "img": "/assets/dsa/array.png"},
    "string":              {"id": "string", "theme": "String Manipulation", "img": "/assets/dsa/string.png"},
    "heap-priority-queue": {"id": "heap",   "theme": "Heaps & Priority",    "img": "/assets/dsa/heap.png"},
    "matrix":              {"id": "matrix", "theme": "Matrix Operations",   "img": "/assets/dsa/dp.png"},
    "topological-sort":    {"id": "graph",  "theme": "Topological Ordering","img": "/assets/dsa/graph.png"},
    "math":                {"id": "math",   "theme": "Mathematical Logic",  "img": "/assets/dsa/dp.png"},
    "recursion":           {"id": "dp",     "theme": "Recursive Engine",    "img": "/assets/dsa/dp.png"},
    "bit-manipulation":    {"id": "math",   "theme": "Bitwise Operations",  "img": "/assets/dsa/dp.png"},
    "sliding-window":      {"id": "array",  "theme": "Sliding Window",      "img": "/assets/dsa/array.png"},
}

DEFAULT_THEME = {"id": "array", "theme": "Core Algorithm", "img": "/assets/dsa/array.png"}

# Mock complexity mapping for common patterns (to be improved by JARVIS LLM eventually)
COMPLEXITY_MAP = {
    "dynamic-programming": {"time": "O(N*M)", "space": "O(N*M)"},
    "graph":               {"time": "O(V + E)", "space": "O(V)"},
    "tree":                {"time": "O(N)", "space": "O(H)"},
    "heap-priority-queue": {"time": "O(log N)", "space": "O(1)"},
    "array":               {"time": "O(N)", "space": "O(1)"},
    "string":              {"time": "O(N)", "space": "O(N)"},
}

async def get_focus_session_data():
    """
    Generates the live state for the Neural Link (War-Room) page.
    Utilizes INTELLIGENCE_HUB cache for zero-latency dashboard pulses.
    """
    # 1. Access Centralized Intelligence (Instant)
    hub = INTELLIGENCE_HUB
    leetcode_stats = hub.get("leetcode", {})
    
    # 2. Fetch local focus metrics (fast DB query)
    focus_db = await get_today_focus_db()
    
    # 3. Handle problem scheduling (Cached via hub if possible)
    active_problem = leetcode_stats.get("daily_problem")
    if not active_problem:
        # Fallback to direct fetch if hub is cold
        active_problem = await get_today_scheduled_problem()
        if not active_problem:
            active_problem = await get_enriched_daily()

    if not active_problem:
        active_problem = {
            "title": "Placement Pulse Audit",
            "difficulty": "Medium",
            "tags": ["Algorithm"],
            "hint": "Ensure your neural connection is stable, Sir.",
            "link": "https://leetcode.com/problems/course-schedule-ii/"
        }

    # Dynamic Theming
    tags = active_problem.get("tags", ["Algorithm"])
    tag_slug = tags[0].lower().replace(" ", "-") if tags else "array"
    theme = THEME_MAP.get(tag_slug, DEFAULT_THEME)
    
    # Complexity Analysis
    complexity = COMPLEXITY_MAP.get(tag_slug, {"time": "O(N)", "space": "O(1)"})

    return {
        "topic":     theme["theme"],
        "sub_topic": active_problem.get("title", "Daily Problem"),
        "theme_id":  theme["id"],
        "theme_img": theme["img"],
        "complexity_analysis": {
            "time":  complexity["time"],
            "space": complexity["space"],
            "note":  f"Optimizing {theme['theme']} for placement-ready benchmarks."
        },
        "active_problem":  active_problem,
        "deep_work_hours": focus_db.get("hours", 0) if focus_db else 0,
        "streak":          leetcode_stats.get("streak", 0),
        "goal_met":        focus_db.get("goal_met", 0) if focus_db else 0,
    }
