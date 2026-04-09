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
def inspect_system_logs(lines: int = 15):
    """
    Reads the last few lines of the JARVIS system log to diagnose errors.
    Use this if the user asks 'What went wrong?' or 'Check the logs'.
    """
    log_path = "d:/JARVIS/backend/main.py" # For now, we use the main logic file as a sanity check
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.readlines()
            return "".join(content[-lines:])
    except Exception as e:
        return f"Error reading logs: {e}"

@mcp.tool()
def analyze_code_error(file_basename: str):
    """
    Deep-scans a specific backend file for syntax or logic mistakes.
    :param file_basename: The name of the file (e.g., 'main.py' or 'leetcode_tool.py')
    """
    base_path = "d:/JARVIS/backend/"
    try:
        with open(base_path + file_basename, "r", encoding="utf-8") as f:
            return f.read()[:2000] # Return first 2k chars for analysis
    except Exception as e:
        return f"Could not find or read {file_basename}: {e}"

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
