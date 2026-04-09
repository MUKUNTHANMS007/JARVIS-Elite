import { useEffect, useState } from 'react';
import { HUB_URL } from '../utils/apiConfig';

export interface InboxData {
  total: number;
  breakdown: {
    gmail: number;
    github: number;
    notion?: number;
    leetcode?: any;
  };
  has_new: boolean;
}

export interface SpotifyTrack {
  status: string;
  track: {
    name: string;
    artist: string;
    album_art: string;
    progress_ms: number;
    duration_ms: number;
    progress_pct: number;
  } | null;
}

export const useInboxCount = () => {
  const [data, setData] = useState<InboxData>({
    total: 0,
    breakdown: { gmail: 0, github: 0 },
    has_new: false
  });

  useEffect(() => {
    const fetchInbox = async () => {
      try {
        const res = await fetch(`${HUB_URL}/api/inbox/count`);
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Inbox fetch failed:", err);
      }
    };
    fetchInbox();
    const interval = setInterval(fetchInbox, 60000); 
    return () => clearInterval(interval);
  }, []);

  return data;
};

export const useSpotifyNowPlaying = () => {
  const [track, setTrack] = useState<SpotifyTrack>({ status: 'offline', track: null });

  useEffect(() => {
    const fetchSpotify = async () => {
      try {
        const res = await fetch(`${HUB_URL}/api/spotify/now-playing`);
        const json = await res.json();
        setTrack(json);
      } catch (err) {
        // console.error("Spotify fetch failed:", err);
      }
    };
    fetchSpotify();
    const interval = setInterval(fetchSpotify, 5000); 
    return () => clearInterval(interval);
  }, []);

  return track;
};

export const controlSpotify = async (action: 'play' | 'pause' | 'next' | 'prev') => {
  try {
    const res = await fetch(`${HUB_URL}/api/spotify/control?action=${action}`, {
      method: 'POST'
    });
    return await res.json();
  } catch (err) {
    console.error("Spotify control failed:", err);
  }
};
