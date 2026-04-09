import asyncio
import json
from tools.spotify_tool import pause_spotify
from tools.github_tool import get_github_pulse
from agent.core import start_focus_timer
from tools.persistent_alert_tool import send_neural_push

async def main():
    try:
        # Step 1: Acoustic Environment Muting
        spotify_res = await asyncio.to_thread(pause_spotify)
        
        # Step 2: Focal Pulse Initiation (45 mins)
        timer_msg = await start_focus_timer(45)
        
        # Step 3: Neural Link Push
        push_msg = send_neural_push("Deep Work Protocol", "Neural Link synchronized. Mobile Bridge Muted. Precision focus active.")
        
        # Step 4: GitHub Synchronization
        github_pulse = await asyncio.to_thread(get_github_pulse)
        
        print(json.dumps({
            "spotify": spotify_res,
            "timer": timer_msg,
            "push": push_msg,
            "github": github_pulse
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
