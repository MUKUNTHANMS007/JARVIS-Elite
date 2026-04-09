import requests, os
from dotenv import load_dotenv

# Ensure env is loaded for direct tool calls
load_dotenv()

def send_neural_push(title: str, message: str, priority: int = 3) -> str:
    """
    Sends a persistent push notification to Mukunthan's mobile device via Ntfy.sh.
    Topic: Configurable via .env (Default: JARVIS_MUKUNTHAN_PULSE)
    Priority: 1 (min) to 5 (max). Default 3.
    """
    topic = os.getenv("NTFY_TOPIC", "JARVIS_MUKUNTHAN_PULSE")
    url = f"https://ntfy.sh/{topic}"
    
    headers = {
        "Title": title,
        "Priority": str(priority)
    }
    
    try:
        print(f"[Push Bridge] Dispatching to topic: {topic} (Priority: {priority})")
        # Ntfy handles the message in the body as raw bytes or text
        response = requests.post(url, data=message, headers=headers)
        if response.status_code == 200:
            return f"Neural transmission confirmed: '{title}' synchronized to mobile device."
        else:
            print(f"[Push Bridge] Error: Cloud returned {response.status_code} for topic {topic}")
            return f"Push Bridge Error: Cloud returned {response.status_code}"
    except Exception as e:
        return f"Push Bridge Failure: {e}"
