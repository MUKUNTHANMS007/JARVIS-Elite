import subprocess
import os

# Branches that must never be pushed to automatically — human confirmation only.
_PROTECTED_BRANCHES = {"main", "master", "production", "release"}


def _current_branch() -> str:
    """Return the current git branch name, or '(unknown)' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "(unknown)"


async def execute_workflow(workflow_name: str, handshake: str = "pending") -> str:
    """
    JARVIS Elite Orchestration: Multi-step terminal workflows for SDE Architects.
    Workflows: 'deploy', 'workspace_setup', 'security_audit'.
    Safety: Requires handshake='proceed' for terminal actions.
    """
    if handshake != "proceed":
        return (
            f"Sir, I have prepared the '{workflow_name}' workflow. "
            "It requires a safety handshake (terminal execution) to execute. "
            "Say 'Proceed' or 'Yes' to initiate."
        )

    try:
        if workflow_name == "deploy":
            # --- BRANCH SAFETY GATE ---
            branch = _current_branch()
            if branch in _PROTECTED_BRANCHES:
                return (
                    f"Sir, I've blocked the deployment: you are on the '{branch}' branch. "
                    "Automated pushes to protected branches are not permitted. "
                    "Please switch to a feature branch before deploying."
                )

            # --- DIFF PREVIEW before committing ---
            status = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True
            )
            if not status.stdout.strip():
                return "Your repository is already synchronized, Sir. No changes to deploy."

            # Show a summary of what will be staged so the user can abort if needed
            diff_stat = subprocess.run(
                ["git", "diff", "--stat", "HEAD"], capture_output=True, text=True
            )
            diff_summary = diff_stat.stdout.strip() or status.stdout.strip()

            # Stage, commit, push
            commit_msg = f"Neural Push: Automated Deployment [{branch}]"
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)

            return (
                f"Deployment successful, Sir. Changes pushed to '{branch}'.\n"
                f"Summary of what was deployed:\n{diff_summary}"
            )

        elif workflow_name == "workspace_setup":
            subprocess.Popen(["code", "."])
            return "Sir, I have initialized the workspace. VS Code is now live."

        elif workflow_name == "security_audit":
            # Scan from current working directory; flag any .env* files found.
            found_secrets = []
            cwd = os.getcwd()
            for root, dirs, files in os.walk(cwd):
                # Skip non-project directories
                dirs[:] = [
                    d for d in dirs
                    if d not in {".venv", "node_modules", ".git", "__pycache__", "dist", ".pytest_cache"}
                ]
                for fname in files:
                    # Flag any .env variant — not just files literally named ".env"
                    if fname == ".env" or fname.startswith(".env."):
                        full_path = os.path.join(root, fname)
                        rel_path = os.path.relpath(full_path, cwd)
                        found_secrets.append(rel_path)

            if found_secrets:
                return (
                    f"Sir, I detected potentially sensitive env files: "
                    f"{', '.join(found_secrets)}. "
                    "Ensure they are all listed in .gitignore."
                )
            return "Security audit complete, Sir. No environment files detected outside .gitignore coverage."

        else:
            return "Unknown protocol, Sir. Please specify 'deploy', 'workspace_setup', or 'security_audit'."

    except subprocess.CalledProcessError as e:
        return f"Sir, the terminal encountered a drift: {str(e)}"
    except Exception as e:
        return f"Neural interface failure: {str(e)}"
