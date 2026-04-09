import os
from github import Github
from dotenv import load_dotenv
import time

# Neural Cache: To prevent overloading GitHub API (Limited to 5 min pulse)
_PULSE_CACHE = []
_PULSE_LAST_UPDATE = 0

# Load .env - check both locations
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "..", "..", ".env"))
load_dotenv(os.path.join(base_dir, "..", ".env"))

def get_github_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[GitHub Tool] Error: GITHUB_TOKEN not found.")
        return None
    return Github(token)

def list_my_repositories():
    """Lists the names of all repositories the user has access to."""
    g = get_github_client()
    if not g: return "Error: GitHub not configured."
    try:
        repos = [repo.name for repo in g.get_user().get_repos()]
        return {"status": "success", "repositories": repos[:20]} # Limit to top 20
    except Exception as e:
        return f"Error: {e}"

def get_repo_summary(repo_name: str):
    """Fetches a detailed summary of a specific repository."""
    g = get_github_client()
    if not g: return "Error: GitHub not configured."
    try:
        user = g.get_user()
        repo = user.get_repo(repo_name)
        
        # Get latest commit
        commits = repo.get_commits()
        last_commit = commits[0].commit.message if commits.totalCount > 0 else "No commits yet"
        
        return {
            "name": repo.name,
            "description": repo.description,
            "stars": repo.stargazers_count,
            "language": repo.language,
            "last_commit": last_commit,
            "open_issues": repo.open_issues_count,
            "latest_sha": commits[0].sha[:7] if commits.totalCount > 0 else None
        }
    except Exception as e:
        return f"Error: {e}"

def get_github_pulse(repo_names=None):
    """Aggregates pulse data for multiple repositories with a 5-minute cache."""
    global _PULSE_CACHE, _PULSE_LAST_UPDATE
    
    # Neural Shield: Check if cache is fresh (10 minute window)
    if time.time() - _PULSE_LAST_UPDATE < 600 and _PULSE_CACHE:
        print(f"[GitHub Pulse] Using cached pulse data (Age: {int(time.time() - _PULSE_LAST_UPDATE)}s)")
        return _PULSE_CACHE

    print(f"[GitHub Pulse] Initializing fresh pulse check...")
    g = get_github_client()
    if not g: 
        print("[GitHub Pulse] Error: No client configured.")
        return {"error": "GitHub not configured."}
    
    pulse_data = []
    try:
        user = g.get_user()
        
        # If no names provided, fetch the 3 most recently updated repos
        if not repo_names:
            print("[GitHub Pulse] No repository names provided. Fetching most recent 3...")
            repos = user.get_repos(sort="updated", direction="desc")
            target_repos = [r.name for r in repos[:3]]
        else:
            target_repos = repo_names
            
        for name in target_repos:
            print(f"[GitHub Pulse] Scanning repository: {name}")
            try:
                # Use get_user().get_repo() because they might be in an org
                repo = user.get_repo(name)
                commits = repo.get_commits()
                last_commit = commits[0].commit.message if commits.totalCount > 0 else "No commits"
                pulse_data.append({
                    "name": repo.name,
                    "stars": repo.stargazers_count,
                    "issues": repo.open_issues_count,
                    "last_commit": (last_commit[:35] + "..") if len(last_commit) > 35 else last_commit,
                    "sha": commits[0].sha[:7] if commits.totalCount > 0 else None
                })
                print(f"[GitHub Pulse] Successfully synchronized: {name}")
            except Exception as re: 
                print(f"[GitHub Pulse] Failed to sync '{name}': {re}")
                continue
        print(f"[GitHub Pulse] Completed pulse with {len(pulse_data)} updates.")
        
        # Update Cache
        _PULSE_CACHE = pulse_data
        _PULSE_LAST_UPDATE = time.time()
        
        return pulse_data
    except Exception as e:
        print(f"[GitHub Pulse] Critical Failure: {e}")
        return {"error": str(e)}

def create_github_issue(repo_name: str, title: str, body: str = None):
    """Creates a new issue in the specified repository."""
    g = get_github_client()
    if not g: return "Error: GitHub not configured."
    try:
        repo = g.get_user().get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body or "Created via JARVIS Voice")
        return f"Success, Sir. Issue #{issue.number} has been opened in '{repo_name}'."
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    # Internal test
    print(list_my_repositories())
