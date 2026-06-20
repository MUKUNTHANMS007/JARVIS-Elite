import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from spotipy.exceptions import SpotifyException
import time
import threading

# Neural Block: MANUAL OVERRIDE IN PROGRESS...
_SPOTIFY_RESTRICTED_UNTIL = 0 
_spotify_restricted_lock = threading.Lock() 

def get_spotify_client():
    """Returns an authenticated Spotipy client using root .env configuration."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:9091/callback"),
        scope="user-modify-playback-state user-read-playback-state"
    ))

def get_target_device_id(sp) -> str | None:
    """Finds the best device to target, prioritizing 'Computer' types."""
    try:
        devices = sp.devices().get('devices', [])
        if not devices:
            return None
        
        # Priority 1: Current Active Device
        active = next((d for d in devices if d['is_active']), None)
        if active:
            return active['id']
            
        # Priority 2: Computer/PC Devices (for Study Sessions)
        computer = next((d for d in devices if d['type'].lower() == 'computer'), None)
        if computer:
            return computer['id']
            
        # Priority 3: First available device
        return devices[0]['id']
    except:
        return None

def start_spotify_playback(context_uri: str) -> str:
    """
    Play a Spotify playlist, album, or track.
    Example: start_spotify_playback('spotify:playlist:37i9dQZF1DX8NTLI2TtZa6')
    """
    try:
        sp = get_spotify_client()
        device_id = get_target_device_id(sp)
        sp.start_playback(context_uri=context_uri, device_id=device_id)
        return f"Successfully started playback on your computer, Sir."
    except Exception as e:
        err = str(e).lower()
        if "no active device" in err:
            return "Sir, I couldn't find an active Spotify session. Please ensure the app is open on your PC."
        return f"Playback error: {e}"

def pause_spotify() -> str:
    """Pause Spotify playback. Note: May fail during ads or on restricted devices."""
    try:
        sp = get_spotify_client()
        sp.pause_playback()
        return "Spotify playback paused, Sir."
    except Exception as e:
        err = str(e).lower()
        if "restriction violated" in err:
            return "Spotify Restriction: I cannot pause while an ad is playing or in a restricted session, Sir."
        if "no active device" in err:
            return "No active Spotify device found. Please initialize playback first."
        return f"Spotify Interface Drift: {e}"

def resume_spotify() -> str:
    """Resume Spotify playback from a paused state."""
    try:
        sp = get_spotify_client()
        playback = sp.current_playback()
        
        # Self-Healing Layer: Don't call resume if already playing
        if playback and playback.get('is_playing'):
            return "Sir, Spotify is already playing. No resume required."
            
        device_id = get_target_device_id(sp)
        sp.start_playback(device_id=device_id)
        return "Spotify playback resumed, Sir."
    except Exception as e:
        err = str(e).lower()
        if "restriction violated" in err:
            return "Spotify Restriction: I cannot resume at this moment due to session constraints (e.g. ad playing)."
        if "no active device" in err:
            return "Sir, I require an active Spotify session to resume. Please open the app on your PC."
        return f"Spotify Interface Drift: {e}"

def next_spotify_track() -> str:
    """Skip to the next Spotify track."""
    try:
        sp = get_spotify_client()
        sp.next_track()
        return "Skipped to the next track, Sir."
    except Exception as e:
        err = str(e).lower()
        if "restriction violated" in err:
            return "Spotify Restriction: Skipping is currently restricted (e.g. ad playing)."
        return f"Error skipping track: {e}"

def previous_spotify_track() -> str:
    """Go back to the previous Spotify track."""
    try:
        sp = get_spotify_client()
        sp.previous_track()
        return "Rewound to the previous track, Sir."
    except Exception as e:
        return f"Error rewinding: {e}"

def get_current_playback_info() -> str:
    """Retrieve detailed info about what is currently playing on Spotify."""
    try:
        sp = get_spotify_client()
        track = sp.current_user_playing_track()
        if not track or not track["is_playing"]:
            return "Nothing is currently playing on Spotify, Sir."
        
        item = track["item"]
        name = item["name"]
        artist = item["artists"][0]["name"]
        album = item["album"]["name"]
        return f"You are currently listening to '{name}' by {artist} from the album '{album}'."
    except Exception as e:
        return f"Status Error: {e}"

def get_current_track_data() -> dict:
    """Retrieve raw info about what is currently playing on Spotify for API use."""
    global _SPOTIFY_RESTRICTED_UNTIL
    
    with _spotify_restricted_lock:
        # Self-Healing: Retry every 5 minutes if Premium restriction was hit
        if _SPOTIFY_RESTRICTED_UNTIL > 0:
            if time.time() < _SPOTIFY_RESTRICTED_UNTIL:
                return {"status": "restricted"}
            else:
                print("[Spotify Tool] Cool-down expired. Re-attempting Neural Handshake...")
                _SPOTIFY_RESTRICTED_UNTIL = 0

    try:
        sp = get_spotify_client()
        track = sp.current_user_playing_track()
        if not track or not track.get("is_playing"):
            return {"status": "inactive"}
        
        item = track.get("item")
        if not item: return {"status": "inactive"}

        return {
            "status": "playing",
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "album": item["album"]["name"],
            "image_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None
        }
    except SpotifyException as e:
        if e.http_status == 403:
            print(f"[Spotify Tool] 403 Restricted (Premium Required). Blocking for 5 mins.")
            with _spotify_restricted_lock:
                _SPOTIFY_RESTRICTED_UNTIL = time.time() + 300
            return {"status": "restricted"}
        return {"status": "error"}
    except Exception as e:
        print(f"[Spotify Tool] General Interface Drift: {e}")
        return {"status": "error"}

def search_and_play_spotify(query: str) -> str:
    """
    Search for music and play it, targeting the PC automatically.
    """
    try:
        sp = get_spotify_client()
        device_id = get_target_device_id(sp)
        
        results = sp.search(q=query, limit=1, type='track,playlist,album')
        
        if results['tracks']['items']:
            track_uri = results['tracks']['items'][0]['uri']
            sp.start_playback(uris=[track_uri], device_id=device_id)
            return f"Playing track: {results['tracks']['items'][0]['name']} on your PC, Sir."
            
        if results['playlists']['items']:
            playlist_uri = results['playlists']['items'][0]['uri']
            sp.start_playback(context_uri=playlist_uri, device_id=device_id)
            return f"Playing playlist: {results['playlists']['items'][0]['name']}."
            
        return f"I couldn't find anything on Spotify for '{query}', Sir."
    except Exception as e:
        err = str(e).lower()
        if "no active device" in err:
            return "Sir, your Spotify interface is 'dormant'. Please ensure the desktop app is open so I can target it."
        return f"Spotify Error: {e}"

def get_spotify_recommendations() -> str:
    """Get music recommendations based on the currently playing track."""
    try:
        sp = get_spotify_client()
        current = sp.current_user_playing_track()
        if not current or not current['item']:
            return "I need you to be listening to something first to give recommendations, Sir."
            
        track_id = current['item']['id']
        try:
            recs = sp.recommendations(seed_tracks=[track_id], limit=5)
            res = "Based on what you're listening to, you might like:\n"
            for track in recs['tracks']:
                res += f"- {track['name']} by {track['artists'][0]['name']}\n"
            return res
        except Exception as e:
            # Fallback: Query top tracks by the current artist if recommendations API fails/404s
            try:
                artist_id = current['item']['artists'][0]['id']
                artist_name = current['item']['artists'][0]['name']
                top_tracks = sp.artist_top_tracks(artist_id, country='US')
                recs_tracks = top_tracks.get('tracks', [])[:5]
                if not recs_tracks:
                    return f"Recommendation Fallback: Could not find any top tracks for artist {artist_name}."
                res = f"Based on your current artist ({artist_name}), you might like their top tracks:\n"
                for track in recs_tracks:
                    res += f"- {track['name']} by {track['artists'][0]['name']}\n"
                return res
            except Exception as fe:
                return f"Recommendation Error: {e} (Fallback also failed: {fe})"
    except Exception as e:
        return f"Recommendation Error: {e}"
