import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:9091/callback"),
        scope="user-read-playback-state user-modify-playback-state"
    ))

async def get_now_playing():
    """Retrieve currently playing track from Spotify."""
    try:
        sp = get_spotify_client()
        track = sp.current_playback()
        return track
    except Exception as e:
        print(f"Spotify Read Error: {e}")
        return None
