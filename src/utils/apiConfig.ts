/**
 * J.A.R.V.I.S. Unified Neural Core Configuration
 * PROD-READY: Centralized port 8000 for all Neural/Hub services.
 *
 * Override detection order:
 *   1. VITE_API_BASE_URL env var  → use that directly (tunnels, staging, etc.)
 *   2. localhost / 127.0.0.1      → local dev (http)
 *   3. LAN IP (192.168.x / 10.x) → local network access (http)
 *   4. Anything else              → assume prod reverse-proxy (https://api.<hostname>)
 */

const { hostname } = window.location;

// Allow an explicit override for ngrok / cloudflare tunnel / staging
const _envOverride = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

const _isLocal =
  !_envOverride &&
  (hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname.startsWith("192.168.") ||
    hostname.startsWith("10.") ||
    hostname.startsWith("172.16.") ||
    hostname.startsWith("172.17.") ||
    hostname.startsWith("172.18.") ||
    hostname.startsWith("172.19.") ||
    hostname.startsWith("172.2") ||
    hostname.startsWith("172.30.") ||
    hostname.startsWith("172.31."));

const _localApiHost = hostname === "localhost" || hostname === "127.0.0.1" ? "127.0.0.1" : hostname;

// Base URLs (Unified Port 8000)
export const BASE_URL = _envOverride
  ? _envOverride
  : _isLocal
  ? `http://${_localApiHost}:8000`
  : window.location.origin;

// WebSocket Bases (Unified Port 8000)
export const BASE_WS = _envOverride
  ? _envOverride.replace(/^http/, "ws")
  : _isLocal
  ? `ws://${_localApiHost}:8000`
  : window.location.origin.replace(/^http/, "ws");

// J.A.R.V.I.S. Legacy Aliases for backward compatibility
export const NEURAL_URL = BASE_URL;
export const HUB_URL = BASE_URL;
export const NEURAL_WS = BASE_WS;
export const HUB_WS = BASE_WS;

// Optional WebSocket auth token — set VITE_WS_AUTH_TOKEN in your frontend .env
// to match WS_AUTH_TOKEN on the backend. Leave unset for localhost dev.
const _wsToken = (import.meta.env.VITE_WS_AUTH_TOKEN as string | undefined) ?? "";
const _wsTokenSuffix = _wsToken ? `?token=${encodeURIComponent(_wsToken)}` : "";

export const API_ENDPOINTS = {
  // Voice & Agent
  VOICE_WS: `${BASE_WS}/ws/voice${_wsTokenSuffix}`,
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
