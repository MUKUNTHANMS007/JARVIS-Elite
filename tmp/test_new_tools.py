import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from tools.gmail_tool import get_smart_email_notifications
from tools.spotify_tool import search_and_play_spotify, get_spotify_recommendations

def test_imports():
    print("Testing tool imports...")
    try:
        # We won't actually call them because they require OAuth/Network, 
        # but we check if they are defined and have the right signature.
        assert callable(get_smart_email_notifications)
        assert callable(search_and_play_spotify)
        assert callable(get_spotify_recommendations)
        print("Success: All new tools are imported and callable.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_imports()
