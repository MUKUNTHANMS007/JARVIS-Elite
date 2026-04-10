from fastapi import APIRouter
import os
import psutil
from github import Github
from datetime import datetime

router = APIRouter()

@router.get("/github")
async def github_activity():
    """Fetch the last 5 events across the user's primary repositories."""
    token = os.getenv("GITHUB_TOKEN")
    if not token or "your" in token:
        return []

    try:
        g = Github(token)
        user = g.get_user()
        events = []
        
        # Fetch events for the user (Push, PullRequest, etc.)
        for event in user.get_events():
            if len(events) >= 5:
                break
            
            # Format readable activity
            type_map = {
                "PushEvent": "commit",
                "PullRequestEvent": "merge",
                "CreateEvent": "branch",
                "IssuesEvent": "issue"
            }
            
            event_type = type_map.get(event.type, "activity")
            repo_name = event.repo.name.split("/")[-1]
            
            # Extract description
            desc = ""
            if event.type == "PushEvent":
                desc = event.payload.get("commits", [{}])[0].get("message", "Pushed changes")
            elif event.type == "PullRequestEvent":
                desc = event.payload.get("pull_request", {}).get("title", "Updated PR")
            else:
                desc = f"Action on {repo_name}"

            # Calculate "time ago" (simplified)
            created_at = event.created_at
            now = datetime.utcnow()
            diff = now - created_at
            if diff.days > 0:
                time_str = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                time_str = f"{diff.seconds // 3600}h ago"
            else:
                time_str = f"{diff.seconds // 60}m ago"

            events.append({
                "type": event_type,
                "title": f"{repo_name}: {desc[:40]}...",
                "desc": f"Activity in {repo_name}",
                "time": time_str
            })
            
        return events
    except Exception as e:
        print(f"GitHub Work Fetch Error: {e}")
        return []

@router.get("/stats")
async def work_stats():
    """Fetch real-time project health metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\' if os.name == 'nt' else '/').percent
        
        # Calculate readable uptime
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.now().timestamp() - boot_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "uptime": uptime_str
        }
    except Exception as e:
        print(f"Stats Work Fetch Error: {e}")
        return {"cpu": 0, "ram": 0, "disk": 0, "uptime": "0m"}
