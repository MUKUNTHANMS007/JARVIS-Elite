/**
 * J.A.R.V.I.S. Distributed API Configuration
 * SPLIT: 
 * - Neural Core (Port 8000): Heavy AI, Voice, Agent Logic
 * - Intelligence Hub (Port 8001): Data, Dashboard, Telemetry, Routers
 */

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

// Base URLs
export const NEURAL_URL = isLocal 
  ? "http://127.0.0.1:8000" 
  : `https://neural.${window.location.hostname}`; // Placeholder for Cloudflare subdomains

export const HUB_URL = isLocal 
  ? "http://127.0.0.1:8000" 
  : `https://hub.${window.location.hostname}`; // Placeholder for Cloudflare subdomains

// WebSocket Bases
export const NEURAL_WS = isLocal 
  ? "ws://127.0.0.1:8000" 
  : `wss://neural.${window.location.hostname}`;

export const HUB_WS = isLocal 
  ? "ws://127.0.0.1:8000" 
  : `wss://hub.${window.location.hostname}`;

// Helper and specific endpoints
export const API_ENDPOINTS = {
  VOICE_SPEAK: `${NEURAL_URL}/api/voice/speak`,
  VOICE_WS: `${NEURAL_WS}/ws/voice`,
  SYSTEM_WS: `${HUB_WS}/ws/system`,
  SYNC: `${HUB_URL}/api/sync`,
  STATUS: `${HUB_URL}/api/status`,
  BRIEFING: `${HUB_URL}/api/briefing`,
  CALENDAR: `${HUB_URL}/api/calendar`,
  EVOLUTION: `${HUB_URL}/api/evolution`,
  WORK: `${HUB_URL}/api/work`,
  CORE: `${HUB_URL}/api/routine`, // Assuming core/routine router path
};
