import subprocess
import pyautogui
import os
import webbrowser
import shutil

def browse_url(url: str) -> str:
    """
    Opens the specified URL in the system's default web browser.
    Example: browse_url('https://gmail.google.com')
    """
    try:
        webbrowser.open(url)
        return f"Successfully commanded Windows to open browser at {url}."
    except Exception as e:
        return f"Failed to open browser at {url}: {e}"

def open_app(app_name_or_path: str) -> str:
    """
    Opens a Windows application by name (if in PATH) or absolute path.
    Example: open_app('notepad.exe') or open_app('C:/Program Files/Google/Chrome/Application/chrome.exe')
    """
    try:
        lower_name = app_name_or_path.lower().strip()
        
        # URI Protocol Fallbacks for Windows Apps
        if lower_name in ("spotify", "spotify.exe"):
            os.system("start spotify:")
            return "Successfully commanded Windows to open Spotify."
        if lower_name in ("whatsapp", "whatsapp.exe"):
            os.system("start whatsapp:")
            return "Successfully commanded Windows to open WhatsApp."
        if lower_name in ("chrome", "chrome.exe", "google chrome"):
            # Check for common Chrome paths if not in PATH
            chrome_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:/Program Files"), "Google/Chrome/Application/chrome.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), "Google/Chrome/Application/chrome.exe"),
                os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe")
            ]
            for p in chrome_paths:
                if os.path.exists(p):
                    subprocess.Popen(p, shell=True)
                    return f"Successfully commanded Windows to open Chrome via {p}."
            # Fallback to start command
            os.system("start chrome")
            return "Successfully commanded Windows to open Google Chrome."
            
        # Reliability Check: Verify if app exists in PATH or at specified path
        executable = shutil.which(app_name_or_path) or (app_name_or_path if os.path.exists(app_name_or_path) else None)
        
        if not executable:
            return f"Application '{app_name_or_path}' not found on this system. For services like Gmail, please use 'browse_url' instead."
            
        # Popen is non-blocking
        subprocess.Popen(executable, shell=True)
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
