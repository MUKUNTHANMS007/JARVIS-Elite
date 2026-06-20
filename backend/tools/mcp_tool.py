import os
from pathlib import Path
from fastmcp import FastMCP
from agent.memory import (
    get_calendar_events_db,
    save_calendar_event,
    get_projects_db,
    save_project_milestone,
    update_skill_level,
    get_skill_levels_db
)
from tools.github_tool import (
    list_my_repositories,
    get_repo_summary,
    create_github_issue
)
from tools.leetcode_tool import sync_leetcode_intelligence, get_placement_roadmap

# ---------------------------------------------------------------------------
# Safe root directory for file-inspection tools.
# Only files under this directory may be read by inspect_system_logs /
# analyze_code_error — path traversal attempts are rejected.
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent.resolve()
_LOG_ROOT = (_BACKEND_ROOT / "logs").resolve()


def _safe_backend_path(filename: str) -> Path | None:
    """
    Resolve `filename` relative to the backend root and verify it stays
    inside that root.  Returns the resolved Path, or None if the resolved
    path escapes the root (path-traversal attempt).
    """
    # Strip any directory separators — we only accept bare filenames
    safe_name = Path(filename).name  # e.g. "main.py", NOT "../.env"
    candidate = (_BACKEND_ROOT / safe_name).resolve()
    try:
        candidate.relative_to(_BACKEND_ROOT)  # raises ValueError if outside
        return candidate
    except ValueError:
        return None


# Initialize FastMCP - the "USB-C" for Jarvis Tools
mcp = FastMCP("Jarvis-Core")

@mcp.tool()
async def manage_project_vault(title: str, milestone: str, tech_stack: str = None, action: str = "update"):
    """
    Manage your PSG iTech project context.
    :param title: Project name (e.g., 'JARVIS-MCP')
    :param milestone: Current progress or snippet (e.g., 'Implemented SSE transport')
    :param tech_stack: Comma-separated list (e.g., 'Python, FastAPI, Supabase')
    :param action: 'update' or 'fetch'
    """
    if action == "fetch":
        return await get_projects_db("JARVIS_ADMIN")

    stack_list = [s.strip() for s in tech_stack.split(",")] if tech_stack else None
    await save_project_milestone("JARVIS_ADMIN", title, milestone, stack_list)
    return f"Sir, the Project Vault has been updated for '{title}'. Milestone recorded: {milestone}"

@mcp.tool()
async def track_skill_mastery(category: str, action: str = "fetch"):
    """
    Tracks proficiency in LeetCode categories or tech skills.
    :param category: Skill name (e.g., 'Graphs', 'React')
    :param action: 'update' or 'fetch'
    """
    if action == "fetch":
        return await get_skill_levels_db("JARVIS_ADMIN")

    await update_skill_level("JARVIS_ADMIN", category)
    return f"Mastery updated for {category}. Keep pushing, Sir."

@mcp.tool()
def list_github_repos():
    """Lists all repositories in your GitHub account."""
    return list_my_repositories()

@mcp.tool()
def get_github_repo_summary(repo_name: str):
    """Gets detailed info, last commit, and issues for a specific repo."""
    return get_repo_summary(repo_name)

@mcp.tool()
def open_github_issue(repo_name: str, title: str, body: str = None):
    """Opens a new issue in a specific GitHub repository."""
    return create_github_issue(repo_name, title, body)

@mcp.tool()
async def fetch_calendar(user_id: str = "JARVIS_ADMIN"):
    """
    Retrieves all scheduled events and academic tasks for the user.
    Use this to understand the user's current schedule or find free time.
    """
    return await get_calendar_events_db(user_id)

@mcp.tool()
async def add_calendar_event(title: str, date: str, time: str = None, description: str = None, category: str = "Task"):
    """
    Adds a new event or task to the calendar.
    :param title: Name of the event (e.g., 'Physics Lab', 'Lunch with Mom')
    :param date: Date in YYYY-MM-DD format
    :param time: Optional time in HH:MM format
    :param description: Optional details about the event
    :param category: Optional category like 'Exam', 'Review', or 'Task'
    """
    await save_calendar_event("JARVIS_ADMIN", title, date, time, description, category)
    return {
        "status": "success",
        "message": f"Confirmed, Sir. '{title}' has been added to your schedule for {date}."
    }

@mcp.tool()
def inspect_system_logs(lines: int = 15) -> str:
    """
    Reads the last N lines of the JARVIS agent error log to diagnose errors.
    Use this if the user asks 'What went wrong?' or 'Check the logs'.
    """
    log_path = _LOG_ROOT / "agent_error.log"
    # Verify the log file is inside the expected logs directory
    try:
        log_path.resolve().relative_to(_LOG_ROOT)
    except ValueError:
        return "Error: Log path escaped safe directory."

    try:
        if not log_path.exists():
            return "No error log found — the system appears clean."
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.readlines()
        return "".join(content[-max(1, min(lines, 200)):])  # cap at 200 lines
    except Exception as e:
        return f"Error reading log: {e}"

@mcp.tool()
def analyze_code_error(file_basename: str) -> str:
    """
    Reads the first 2000 characters of a specific backend file to help
    diagnose syntax or logic errors.
    :param file_basename: Bare filename only (e.g., 'main.py').
                          Directory separators and '..' are rejected.
    """
    safe_path = _safe_backend_path(file_basename)
    if safe_path is None:
        return (
            f"Refused to read '{file_basename}': path resolves outside the "
            "backend directory. Only bare filenames are accepted."
        )
    if not safe_path.exists():
        return f"File '{file_basename}' not found in the backend directory."
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()[:2000]
    except Exception as e:
        return f"Could not read {file_basename}: {e}"

@mcp.tool()
async def sync_and_recommend_coding():
    """
    Syncs LeetCode stats (Total/Streak) and provides PSG iTech
    placement recommendations for Amazon, Zoho, and Goldman Sachs.
    """
    intel = await sync_leetcode_intelligence()
    if "error" in intel: return f"Sir, I tried to sync your radar but: {intel['error']}"

    roadmap = await get_placement_roadmap()
    return f"{intel['message']}\n\n{roadmap}"

if __name__ == "__main__":
    # Local run capability for debugging
    mcp.run()
