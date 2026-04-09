import webbrowser

def search_youtube(query: str) -> str:
    """
    Search and open YouTube results in your default browser.
    """
    try:
        url = f"https://www.youtube.com/results?search_query={query}"
        webbrowser.open(url)
        return f"Searched YouTube for '{query}' and opened the results in your browser."
    except Exception as e:
        return f"Failed to search YouTube: {e}"

def play_video(video_id: str) -> str:
    """
    Directly play a YouTube video in your browser by ID.
    Example: play_video('dQw4w9WgXcQ')
    """
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        webbrowser.open(url)
        return f"Playing YouTube video '{video_id}' in your browser."
    except Exception as e:
        return f"Failed to play video: {e}"
