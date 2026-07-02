# JARVIS-Elite

JARVIS (Just A Rather Very Intelligent System) is a personal AI assistant built for a placement/SDE context. It accepts voice or text commands over a WebSocket, routes them through a Groq-powered function-calling agent that can invoke ~31 real integrations, and synthesizes spoken responses using a cloud+local TTS pipeline — all streamed in real time to a React dashboard and a React Native mobile companion app, with a background sentinel that pushes proactive alerts to your phone when something actually changes.

---

## Architecture Overview

```
┌──────────────────────── JARVIS Architecture ────────────────────────────┐
│                                                                          │
│  Frontend (React/Vite)          Mobile (Expo / React Native)             │
│  ┌───────────────────────────┐  ┌──────────────────────────────────┐   │
│  │  Dashboard Bento Grid      │  │  VAD-gated voice capture         │   │
│  │  Global mic button on      │  │  Sync dashboard (LeetCode/focus/  │   │
│  │    every page (Recorder)   │  │    Spotify) + push notifications │   │
│  │  WebSocket client          │  │  Same /ws/voice contract         │   │
│  │  AudioContext (PCM play)   │  │                                   │   │
│  └────────────┬───────────────┘  └────────────────┬─────────────────┘   │
│               │                                    │                    │
│               └─────────────────┬──────────────────┘                   │
│                            /ws/voice │              /ws/system          │
│  Backend (FastAPI + uvicorn, port 8000)                │                │
│  ┌─────────────────────────▼──────────┐  ┌────────────▼─────────────┐ │
│  │        ws_neural.py                │  │       ws_hub.py           │ │
│  │  WebSocket voice pipeline          │  │  System Pulse broadcaster │ │
│  │  - Audio decode                    │  │  - CPU/RAM/disk every 5s  │ │
│  │  - STT dispatch                    │  │  - Spotify/LeetCode state  │ │
│  │  - Agent stream                    │  └───────────────────────────┘ │
│  │  - TTS bridge worker               │  ┌───────────────────────────┐ │
│  └──────────┬─────────────────────────┘  │   sentinel_service.py      │ │
│             │                            │  Diffs Gmail/GitHub/       │ │
│             │                            │  LeetCode/Spotify state    │ │
│             │                            │  against last-seen —       │ │
│             │                            │  pushes a phone alert only │ │
│             │                            │  on genuine change         │ │
│             │                            └───────────────────────────┘ │
│             │                                                            │
│  ┌──────────▼──────────────────────────────────────────────────────┐   │
│  │  VOICE PIPELINE                                                   │   │
│  │  voice/stt.py                voice/tts.py                        │   │
│  │  1. Groq Whisper (cloud)     1. Groq Orpheus (cloud, WAV/PCM)   │   │
│  │  2. faster-whisper (local)   2. edge-tts (MS neural, fallback)  │   │
│  └──────────┬──────────────────────────────────────────────────────┘   │
│             │                                                            │
│  ┌──────────▼──────────────────────────────────────────────────────┐   │
│  │  AGENT LAYER  (agent/core.py)                                    │   │
│  │  Model: Groq llama-3.3-70b-versatile  (vision: llama-3.2-11b)  │   │
│  │  Fallback: Ollama local LLM (OLLAMA_HOST)                       │   │
│  │  - Load history: Redis (L1, 30 min) → Supabase (L2)            │   │
│  │  - System prompt (JARVIS / Batman mode)                          │   │
│  │  - Native function-calling + text-tag fallback parser            │   │
│  │  - Up to 5 tool-resolution iterations per turn                  │   │
│  └──────────┬──────────────────────────────────────────────────────┘   │
│             │                                                            │
│  ┌──────────▼──────────────────────────────────────────────────────┐   │
│  │  TOOL REGISTRY  (31 callable handlers / 13 in Groq schema)      │   │
│  │  Redis cache check (5-min TTL) → API call → cache result        │   │
│  │  Gmail │ Spotify │ GitHub │ Calendar │ LeetCode │ Ntfy │ ...   │   │
│  └──────────┬──────────────────────────────────────────────────────┘   │
│             │                                                            │
│  ┌──────────▼──────────────────────────────────────────────────────┐   │
│  │  PERSISTENCE & INFRA                                             │   │
│  │  Supabase (Postgres): messages, reminders, calendar_events,     │   │
│  │    skill_mastery, leetcode_daily, project_vault                 │   │
│  │  Redis: tool result cache, semantic history cache               │   │
│  │  Celery + Redis broker: STT offload, mobile dispatch tasks      │   │
│  │  services/cache_service.py: in-memory Intelligence Hub          │   │
│  │    (thread-safe, atomic disk persistence for crash recovery)    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Voice Command Flow (end-to-end)

```
Mic input
   │  audio/webm or audio/mp4 (base64, via MediaRecorder)
   ▼
/ws/voice  (ws_neural.py)
   │
   ├─► STT  (voice/stt.py)
   │    ├─ PRIMARY:  Groq Whisper-large-v3-turbo  (cloud, ~300–600 ms)
   │    └─ FALLBACK: faster-whisper small.en      (local CPU, ~800 ms–2 s)
   │                  Self-heals: CUDA→CPU int8 on detection errors
   │
   ├─► TRANSCRIPTION event sent to client over WebSocket
   │
   ▼
Agent  (agent/core.py: get_agent_response_stream)
   │  History: Redis L1 → Supabase L2 (on cold start only)
   │  Model:   llama-3.3-70b-versatile via Groq API (streaming)
   │  Tools:   GROQ_TOOLS schema (13 entries) + text-tag parser fallback
   │  Loop:    up to 5 iterations to resolve chained tool calls
   │
   ├─► Tool call detected → AVAILABLE_TOOLS registry (31 handlers)
   │    ├─ Redis cache hit?  →  return cached (< 5 ms)
   │    └─ Cache miss  →  real API call  →  cache result (5-min TTL)
   │                        (async tools awaited; sync tools via to_thread)
   │
   ├─► TEXT_CHUNK tokens streamed to client as they arrive
   │
   ▼
TTS bridge  (ws_neural.py: bridge_tts_worker)
   │  Sentence-level buffering (configurable: sentence / entire / chunk)
   │
   ├─► voice/tts.py
   │    ├─ PRIMARY:  Groq Orpheus (canopylabs/orpheus-v1-english)
   │    │             WAV → PCM_16 @ 24 kHz, next chunk prefetched while
   │    │             the current one sends, to overlap synthesis latency
   │    └─ FALLBACK: edge-tts  (Microsoft neural en-GB-RyanNeural)
   │                  Both connections pre-warmed at boot so the first
   │                  reply of a session skips the DNS/TLS handshake cost;
   │                  a failed chunk gets one retry before being dropped
   │
   ▼
Browser AudioContext (PCMProcessor AudioWorklet)
   │  120s ring buffer sized for a full multi-sentence reply arriving
   │  faster than real time; on overflow it drops the oldest queued
   │  samples instead of resetting, so an in-flight reply is never
   │  wiped mid-turn
   ▼
Spoken response
```

---

## Tool Integrations

| Tool | File | What it does |
|------|------|--------------|
| Gmail (inbox) | `tools/gmail_tool.py` | Reads unread count, fetches email snippets/headers via Google API |
| Gmail (briefing) | `tools/gmail_tool.py` | Generates an executive Gemini-summarized email briefing |
| Gmail (smart notify) | `tools/gmail_tool.py` | Scans inbox for priority senders and flags time-sensitive emails |
| Spotify (playback control) | `tools/spotify_tool.py` | Play/pause/resume/skip via Spotipy (Spotify Web API OAuth) |
| Spotify (search & play) | `tools/spotify_tool.py` | Searches tracks/albums/playlists by query and starts playback |
| Spotify (recommendations) | `tools/spotify_tool.py` | Fetches seed-based recommendations from currently playing track |
| Reminders | `tools/reminder_tool.py` | Set/list/delete time-based reminders persisted in Supabase |
| Calendar | `tools/calendar_tool.py` | Add/list/delete calendar events; push schedule to mobile via Ntfy |
| LeetCode stats | `tools/leetcode_tool.py` | Fetches solve count, streak, category breakdown via LeetCode GraphQL |
| LeetCode tracking | `tools/leetcode_tool.py` | Marks today solved, logs to Supabase `leetcode_daily`, updates skill_mastery |
| GitHub repos | `tools/github_tool.py` | Lists repositories and commit activity via PyGitHub |
| GitHub issues | `tools/github_tool.py` | Creates issues on a specified repository |
| Mobile push (Ntfy) | `tools/persistent_alert_tool.py` | Broadcasts push notifications to phone via self-hosted Ntfy topic |
| System (open app) | `tools/system_tool.py` | Opens desktop applications via `subprocess` |
| System (browse URL) | `tools/system_tool.py` | Opens URLs in the default browser |
| Morning briefing | `tools/briefing_tool.py` | Aggregates LeetCode + GitHub + Gmail into a single morning summary |
| Workflow execution | `tools/workflow_tool.py` | Runs multi-step CLI workflows (git init, deploy, etc.) with safety handshake |
| Habit tracking | `tools/learning_tool.py` | Logs habit data and retrieves insights from Supabase `skill_mastery` |
| Focus timer | `agent/core.py` (inline) | Broadcasts start/stop/reset timer events to all WebSocket clients |
| MCP fallback | `tools/mcp_tool.py` | Catches unrecognized tool names and routes to FastMCP if registered |

**Registered callable handlers:** 31 (`AVAILABLE_TOOLS`)  
**LLM-facing schema (Groq function-calling):** 13 (`GROQ_TOOLS`)  
The remaining 18 handlers are invokable via text-tag fallback or direct code paths.

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- Node.js 18+
- Redis (local: `redis-server`, or set `REDIS_URL`)
- A Groq API key (get one free at console.groq.com)
- Supabase project with the required tables (see schema below)

### 1. Clone and install

```bash
# Frontend
npm install

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
# Core (required)
GROQ_API_KEY=gsk_...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
NEURAL_EDGE_SECRET=any-random-long-string   # HMAC key for edge trigger endpoint

# Optional — these enable specific integrations
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
GITHUB_TOKEN=ghp_...
NTFY_TOPIC=https://ntfy.sh/your-topic
LEETCODE_USERNAME=your_handle

# Optional — STT/TTS tuning
STT_PROVIDER=groq          # or "local" for faster-whisper
LOCAL_STT_MODEL=small.en
TTS_SPEECH_MODE=sentence   # sentence | entire | chunk
NEURAL_PREWARM=true        # pre-loads local Whisper model on startup

# Optional — local LLM fallback
OLLAMA_HOST=http://127.0.0.1:11434
LOCAL_LLM_MODEL=gemma4
```

### 3. Gmail OAuth (one-time)

```bash
cd backend
python authenticate_gmail.py
# Follow the browser prompt — writes token.json
```

### 4. Run

```bash
# Terminal 1 — Backend API
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Celery worker (optional, for background task queue)
cd backend
celery -A celery_app worker --loglevel=info

# Terminal 3 — Frontend dev server
npm run dev
```

Open `http://localhost:5173` (or the port Vite reports).

### 5. Supabase schema (required tables)

```
messages          (id, user_id, role, content, created_at)
reminders         (id, user_id, text, reminder_time)
calendar_events   (id, user_id, title, event_date, event_time, description, category)
skill_mastery     (id, user_id, category, problems_solved, last_practiced)
leetcode_daily    (id, user_id, scheduled_date, completed)
project_vault     (id, user_id, title, last_milestone, tech_stack, updated_at)
academic_radar    (id, title, event_date, category)
neural_sentinel   (id, user_id, state_json, updated_at)
```

### 6. Run tests

```bash
cd backend
pytest automated_testing/ -v
# Expected: 24 tests, 18 subtests, 0 failures
```

### 7. Mobile app (Expo / React Native)

The `mobile/` directory is a standalone Expo app that talks to the same backend over the same `/ws/voice` WebSocket and `/api/sync` REST endpoint as the web dashboard — no separate server needed.

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with Expo Go, or run `npx expo start --android` / `--ios`. On first launch, open Settings in the app and point it at your backend's LAN address or a tunnel URL (e.g. `192.168.1.5:8000` or an `https://xxxx.trycloudflare.com` tunnel) — the app derives both the `http(s)` and `ws(s)` bases from that one host string. Voice capture uses on-device VAD (silence-gated recording) instead of push-to-talk, and push notifications are delivered via `expo-notifications` for sentinel alerts and dispatch pushes.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM / STT / TTS | Groq API (llama-3.3-70b, Whisper-large-v3-turbo, Orpheus) |
| Local STT fallback | faster-whisper (CPU int8) |
| Local TTS fallback | edge-tts (Microsoft neural voices, no API key) |
| Local LLM fallback | Ollama (configurable model) |
| Backend framework | FastAPI + uvicorn |
| Real-time comms | WebSockets (ws_neural, ws_hub via ws_manager) |
| Task queue | Celery + Redis broker |
| Cache | Redis (tool results 5 min, history 30 min) |
| Persistence | Supabase (async Postgres client) |
| Frontend | React + Vite + Tailwind |
| Mobile app | Expo + React Native (VAD voice capture, `expo-notifications`) |
| Protobuf | grpcio-tools (neural_protocol.proto) |
| Mobile push | Ntfy (self-hosted or ntfy.sh) + Expo push notifications |
| Proactive alerts | `services/sentinel_service.py` — diffs Gmail/GitHub/LeetCode/Spotify state, notify-only |
