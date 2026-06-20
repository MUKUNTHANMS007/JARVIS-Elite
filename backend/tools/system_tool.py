import subprocess
import pyautogui
import os
import webbrowser
import shutil

# ---------------------------------------------------------------------------
# Approved application allowlist.
# Only executables whose resolved path matches one of these stems (case-
# insensitive on Windows) may be launched. This prevents LLM-influenced
# tool arguments from reaching arbitrary shell commands.
# ---------------------------------------------------------------------------
_ALLOWED_STEMS = {
    "notepad", "notepad++", "code", "code.cmd", "explorer",
    "mspaint", "calc", "taskmgr", "msedge", "chrome",
    "spotify", "whatsapp", "vlc", "steam", "discord",
}


def _is_allowed(executable: str) -> bool:
    """Return True only if the executable basename (without extension) is allowlisted."""
    stem = os.path.splitext(os.path.basename(executable))[0].lower()
    return stem in _ALLOWED_STEMS


def browse_url(url: str) -> str:
    """
    Opens the specified URL in the system's default web browser.
    Example: browse_url('https://gmail.google.com')
    """
    # Restrict to http/https schemes to prevent file://, javascript: etc.
    if not url.lower().startswith(("http://", "https://")):
        return f"Refused to open '{url}': only http/https URLs are permitted."
    try:
        webbrowser.open(url)
        return f"Successfully commanded Windows to open browser at {url}."
    except Exception as e:
        return f"Failed to open browser at {url}: {e}"


def open_app(app_name_or_path: str) -> str:
    """
    Opens a Windows application by name (if in PATH) or absolute path.
    Only allowlisted applications may be launched.
    Example: open_app('notepad.exe') or open_app('code')
    """
    try:
        lower_name = app_name_or_path.lower().strip()

        # URI Protocol Fallbacks for Windows Apps (no shell=True needed)
        if lower_name in ("spotify", "spotify.exe"):
            subprocess.Popen(["cmd", "/c", "start", "spotify:"], shell=False)
            return "Successfully commanded Windows to open Spotify."
        if lower_name in ("whatsapp", "whatsapp.exe"):
            subprocess.Popen(["cmd", "/c", "start", "whatsapp:"], shell=False)
            return "Successfully commanded Windows to open WhatsApp."
        if lower_name in ("chrome", "chrome.exe", "google chrome"):
            chrome_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:/Program Files"), "Google/Chrome/Application/chrome.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), "Google/Chrome/Application/chrome.exe"),
                os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
            ]
            for p in chrome_paths:
                if os.path.exists(p):
                    # shell=False, list form — no shell injection possible
                    subprocess.Popen([p], shell=False)
                    return f"Successfully commanded Windows to open Chrome via {p}."
            # Fallback: use explicit cmd /c start, still no shell=True on Popen
            subprocess.Popen(["cmd", "/c", "start", "chrome"], shell=False)
            return "Successfully commanded Windows to open Google Chrome."

        # Resolve the executable path
        executable = shutil.which(app_name_or_path) or (
            app_name_or_path if os.path.isfile(app_name_or_path) else None
        )

        if not executable:
            return (
                f"Application '{app_name_or_path}' not found on this system. "
                "For services like Gmail, please use 'browse_url' instead."
            )

        # Allowlist gate — reject anything not explicitly permitted
        if not _is_allowed(executable):
            return (
                f"Refused to launch '{executable}': not in the approved application list. "
                "Ask the user to add it to the allowlist in system_tool.py if intentional."
            )

        # Popen is non-blocking; shell=False + list form prevents shell injection
        subprocess.Popen([executable], shell=False)
        return f"Successfully commanded Windows to open {executable}."
    except Exception as e:
        return f"Failed to open {app_name_or_path}: {e}"


def type_text(text: str) -> str:
    """
    Types the specified text into the currently active window using PyAutoGUI.
    """
    try:
        pyautogui.write(text, interval=0.05)
        return f"Typed '{text}' into the active window."
    except Exception as e:
        return f"Error while typing text: {e}"


def press_hotkey(keys: str) -> str:
    """
    Presses a combination of keys (e.g., 'ctrl', 's').
    Input should be comma-separated if multiple keys are needed.
    """
    try:
        key_list = [k.strip() for k in keys.split(',')]
        pyautogui.hotkey(*key_list)
        return f"Pressed keys: {keys}."
    except Exception as e:
        return f"Error pressing keys {keys}: {e}"


def list_files(directory: str = ".") -> str:
    """Lists files in the specified directory."""
    try:
        files = os.listdir(directory)
        return f"Files in {directory}: " + ", ".join(files)
    except Exception as e:
        return f"Error listing files: {e}"
