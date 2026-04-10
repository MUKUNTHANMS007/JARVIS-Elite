/**
 * J.A.R.V.I.S. Unified Neural Core Configuration
 * PROD-READY: Centralized port 8000 for all Neural/Hub services.
 */

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

// Base URLs (Unified Port 8000)
export const BASE_URL = isLocal 
  ? "http://127.0.0.1:8000" 
  : `https://api.${window.location.hostname}`;

// WebSocket Bases (Unified Port 8000)
export const BASE_WS = isLocal 
  ? "ws://127.0.0.1:8000" 
  : `wss://api.${window.location.hostname}`;

// J.A.R.V.I.S. Legacy Aliases for backward compatibility
export const NEURAL_URL = BASE_URL;
export const HUB_URL = BASE_URL;
export const NEURAL_WS = BASE_WS;
export const HUB_WS = BASE_WS;

export const API_ENDPOINTS = {
  // Voice & Agent
  VOICE_WS: `${BASE_WS}/ws/voice`,
  VOICE_SPEAK: `${BASE_URL}/api/voice/speak`,
  
  // Dashboard & Telemetry
  SYSTEM_WS: `${BASE_WS}/ws/system`,
  SYNC: `${BASE_URL}/api/sync`,
  STATUS: `${BASE_URL}/api/status`,
  
  // High-Level Services
  BRIEFING: `${BASE_URL}/api/briefing`,
  CALENDAR: `${BASE_URL}/api/calendar`,
  EVOLUTION: `${BASE_URL}/api/evolution`,
  WORK: `${BASE_URL}/api/work`,
  CORE: `${BASE_URL}/api/routine`,
};
