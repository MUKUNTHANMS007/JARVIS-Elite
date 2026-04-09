import os
import subprocess

def get_project_activity(directory: str = "D:/JARVIS") -> str:
    """Read the last 3 commit messages to see recent work activity in a specified project."""
    # Ensure directory is absolute and canonicalized
    abs_path = os.path.abspath(directory)
    if not os.path.exists(abs_path):
        return f"Directory '{directory}' does not exist on your computer."
    
    # Check if directory is a git repo
    try:
        # Run git log and capture the output
        # Use subprocess to run 'git log -n 3 --pretty=format:"%s"'
        result = subprocess.run(
            ["git", "-C", abs_path, "log", "-n", "3", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            check=True
        )
        commits = result.stdout.splitlines()
        if not commits:
             return f"No recent git activity found in {directory}."
            
        return f"The last 3 commits in {directory} were: \n" + "\n".join(f"- {c}" for c in commits)
    except subprocess.CalledProcessError:
        # FALLBACK: Not a git repo? List the 5 most recently modified files/folders
        try:
            items = []
            for entry in os.scandir(abs_path):
                if entry.name.startswith('.') or entry.name == 'node_modules':
                    continue
                items.append((entry.name, entry.stat().st_mtime))
            
            # Sort by modification time descending
            items.sort(key=lambda x: x[1], reverse=True)
            top_items = [name for name, _ in items[:5]]
            
            if not top_items:
                return f"I checked {directory}, but it appears to be empty."
                
            return f"Directory '{directory}' is not a Git repository, but I see these were updated recently: \n" + "\n".join(f"- {n}" for n in top_items)
        except:
            return f"Directory '{directory}' is not a valid Git repository and I couldn't scan its files."
    except Exception as e:
        return f"Failed to read project activity: {str(e)}"
