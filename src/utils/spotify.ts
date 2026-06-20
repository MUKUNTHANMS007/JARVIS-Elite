import { HUB_URL } from "./apiConfig";

/**
 * JARVIS Spotify Controller
 * Unified REST client for playback state management.
 */
export const controlSpotify = async (action: 'play' | 'pause' | 'next' | 'prev') => {
  try {
    const res = await fetch(`${HUB_URL}/api/briefing/spotify/control?action=${action}`, {
      method: 'POST'
    });
    return await res.json();
  } catch (err) {
    console.error("[Spotify Control] Sync failed:", err);
    throw err;
  }
};
