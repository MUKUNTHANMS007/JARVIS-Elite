print("[Neural Core] Booting JARVIS Sentinel Protocol...")
import os, sys, json, asyncio, random, time, psutil, re, logging, hmac, hashlib, uuid, traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from celery_app import check_redis_connectivity

# --- LOGGING & DIAGNOSTICS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JARVIS-CORE")

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)
# Load repo-root .env first (what you're using), then backend/.env if present.
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=False)
load_dotenv(os.path.join(_BACKEND_DIR, ".env"), override=False)

# Internal Imports
from voice.stt import transcribe_audio, warm_up_stt
from voice.tts import synthesize_speech_stream, synthesize_speech, close_tts_client, warm_up_tts
from agent.core import get_agent_response_stream
from routers.briefing import router as briefing_router
from routers.work import router as work_router
from routers.calendar import router as calendar_router
from routers.core import router as core_router
from routers.evolution import router as evolution_router
from routers.voice import router as voice_router
from routers.tts import router as tts_router
from routers.schedule import router as schedule_router
from ws_neural import router as neural_ws_router
from ws_hub import router as hub_ws_router
from services.core_service import get_academic_radar, get_today_focus
from tools.leetcode_tool import get_leetcode_stats
from tools.gmail_tool import check_gmail_inbox, get_unread_count_raw, get_gmail_briefing
from tools.spotify_tool import get_current_track_data, resume_spotify
from tools.github_tool import get_github_pulse
from agent.memory import get_active_reminders_db, init_db, get_calendar_events_db, supabase
from services.focus_service import get_focus_session_data
from services.event_service import focus_connections, broadcast_timer_event
from services.cache_service import INTELLIGENCE_HUB, update_intelligence, notify_communication, get_intelligence
from models.protocol import NeuralPacket as PydanticPacket, Telemetry as PydanticTelemetry, DashboardMetrics as PydanticDashboard, ProactiveAlert as PydanticAlert
import models.neural_protocol_pb2 as pb
from tasks import (
    process_stt_task, analyze_mood_task, send_dispatch_notification_task, analyze_vision_task,
    _core_stt_logic, _core_mood_logic, _core_dispatch_logic, _core_vision_logic
)

# --- NEURAL HUB WORKER (Unified Sentinel) ---

async def refresh_intelligence_hub():
    """Neural Pulse Worker: High-concurrency task orchestration."""
    logger.info("[Neural Hub] Unified sentinel worker initiated (Concurrent Mode).")
    
    user_lc = os.getenv("LEETCODE_USERNAME", "MUKUNTHAN_MS")
    user_id = os.getenv("JARVIS_USER_ID", "JARVIS_ADMIN")

    async def sync_gmail():
        while True:
            try:
                count = await asyncio.wait_for(asyncio.to_thread(get_unread_count_raw), timeout=15)
                update_intelligence("gmail_unread", count)
            except Exception as e:
                logger.debug(f"[Neural Hub] Gmail sync drift: {e}")
            await asyncio.sleep(30)

    async def sync_gmail_briefing():
        """
        Gmail executive briefing is heavier (Gemini) so we update it less frequently.
        Also write to both keys for frontend compatibility.
        """
        while True:
            try:
                briefing = await asyncio.wait_for(asyncio.to_thread(get_gmail_briefing), timeout=25)
                update_intelligence("gmail_briefing", briefing)
                update_intelligence("intelligence_briefing", briefing)
            except Exception as e:
                logger.debug(f"[Neural Hub] Gmail briefing drift: {e}")
            await asyncio.sleep(180)

    async def sync_leetcode():
        while True:
            try:
                stats = await get_leetcode_stats(user_lc, sync=True)
                update_intelligence("leetcode", stats)
            except Exception as e:
                logger.debug(f"[Neural Hub] LeetCode sync drift: {e}")
            await asyncio.sleep(300)

    async def sync_github():
        while True:
            try:
                pulse = await asyncio.wait_for(asyncio.to_thread(get_github_pulse), timeout=15)
                update_intelligence("github", pulse)
            except Exception as e:
                logger.debug(f"[Neural Hub] GitHub pulse drift: {e}")
            await asyncio.sleep(300)

    async def sync_calendar_sentinel():
        while True:
            try:
                calendar_data = await get_calendar_events_db(user_id)
                reminders_data = await get_active_reminders_db(user_id)
                academic_raw = await get_academic_radar()
                
                # Pre-process academic data for Bento UI consistency
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                upcoming = sorted(
                    [e for e in academic_raw if e.get("event_date", "") >= today_str],
                    key=lambda x: x.get("event_date", "")
                )
                academic_radar = []
                for event in upcoming[:3]:
                    try: 
                        day_str = str(datetime.strptime(event.get("event_date", ""), "%Y-%m-%d").day)
                    except (ValueError, TypeError): day_str = "??"
                    academic_radar.append({
                        "title": event.get("title", "Scheduled Event"),
                        "date": day_str,
                        "task_type": event.get("category", "Task")
                    })

                update_intelligence("calendar", calendar_data)
                update_intelligence("active_reminders", reminders_data)
                update_intelligence("academic_radar", academic_radar)
                
                now = time.time()
                for event in calendar_data:
                    if event.get("event_date") == today_str:
                        e_time = event.get("event_time")
                        if e_time:
                            # Support range strings like "10:30:00 - 11:30:00"
                            start_time_part = e_time.split(" - ")[0].strip()
                            try:
                                ev_dt = datetime.strptime(f"{today_str} {start_time_part}", "%Y-%m-%d %H:%M:%S")
                                diff = (ev_dt.timestamp() - now) / 60
                                if 0 < diff <= 15:
                                    current_triggers = get_intelligence().get("proactive_triggers", {})
                                    if event.get("title") not in current_triggers:
                                        current_triggers[event.get("title")] = {
                                            "type": "MEETING_ALERT", "title": event.get("title"), "diff": round(diff), "timestamp": now
                                        }
                                        update_intelligence("proactive_triggers", current_triggers)
                            except ValueError:
                                logger.debug(f"[Neural Hub] Failed to parse event time string: {e_time}")
            except Exception as e:
                logger.debug(f"[Neural Hub] Calendar sync drift: {e}")
            await asyncio.sleep(60)

    async def sync_cloud_mirror():
        while True:
            if supabase:
                try:
                    mirror_data = {
                        "user_id": user_id,
                        "state_json": json.loads(json.dumps(get_intelligence(), default=str)),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    await supabase.table("neural_sentinel").upsert(mirror_data, on_conflict="user_id").execute()
                except Exception: pass
            await asyncio.sleep(300)

    async def sync_spotify():
        while True:
            try:
                data = await asyncio.wait_for(asyncio.to_thread(get_current_track_data), timeout=10)
                status = data.get("status")
                if status == "playing":
                    update_intelligence("spotify_track", data.get("name"))
                    update_intelligence("spotify_image", data.get("image_url"))
                elif status == "restricted":
                    update_intelligence("spotify_track", "Premium Required")
                    update_intelligence("spotify_image", None)
                else: # inactive or error
                    update_intelligence("spotify_track", "Inactive")
                    update_intelligence("spotify_image", None)
            except Exception as e:
                logger.debug(f"[Neural Hub] Spotify sync drift: {e}")
            await asyncio.sleep(5)

    # Spawn all as independent background tasks
    await asyncio.gather(
        sync_gmail(),
        sync_gmail_briefing(),
        sync_leetcode(),
        sync_github(),
        sync_calendar_sentinel(),
        sync_cloud_mirror(),
        sync_spotify()
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    # --- NEURAL WARMING: Pre-load models to VRAM to kill cold-start lag ---
    if os.getenv("NEURAL_PREWARM") == "true":
        logger.info("[Neural Link] Igniting Engines... (VRAM Optimization Active)")
        try:
            # Run warming concurrently to save boot time
            await asyncio.gather(
                asyncio.to_thread(warm_up_stt),
                asyncio.to_thread(warm_up_tts)
            )
            logger.info("[Neural Link] RTX 3050 Ti Loaded & Ready.")
        except Exception as e:
            logger.error(f"[Neural Link] Handshake Drift during warming: {e}")

    # --- NON-BLOCKING BOOT: Prevent Supabase/Net hangs from blocking port 8000 ---
    asyncio.create_task(init_db())
    hub_task = asyncio.create_task(refresh_intelligence_hub())
    logger.info("[Neural Core] Unified Intelligence Online.")
    yield
    # SHUTDOWN
    hub_task.cancel()
    await close_tts_client()
    logger.info("[Neural Core] Shutting down.")

app = FastAPI(title="JARVIS Neural Core", lifespan=lifespan)

from fastapi.staticfiles import StaticFiles
from voice.tts_engine.config import TTS_CACHE_DIR
app.mount("/static/tts", StaticFiles(directory=str(TTS_CACHE_DIR)), name="tts_cache")
# app.add_middleware(GZipMiddleware, minimum_size=1000) # Disabled for binary WS stability

# --- NEURAL FIREWALL: Trusted Host Filtering (Broadened for Loopback Stability) ---
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

# --- NEURAL FIREWALL: Security Headers (@app.middleware skips WebSockets by default) ---
@app.middleware("http")
async def neural_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# --- NEURAL GATEWAY: Restricted CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WEBSOCKET ROUTERS ---
app.include_router(neural_ws_router)
app.include_router(hub_ws_router)


# --- REST API ROUTES ---

app.include_router(briefing_router, prefix="/api/briefing")
app.include_router(work_router, prefix="/api/work")
app.include_router(calendar_router, prefix="/api/calendar")
app.include_router(core_router, prefix="/api/routine")
app.include_router(evolution_router, prefix="/api/evolution")
app.include_router(voice_router, prefix="/api/voice")
app.include_router(tts_router, prefix="/api/tts")
app.include_router(schedule_router, prefix="/api/schedule")

def _system_status_snapshot(hub: dict) -> dict:
    """Builds a compact system status object for initial sync/UI."""
    try:
        battery = psutil.sensors_battery()
        b_percent = battery.percent if battery else 100
        is_plugged = battery.power_plugged if battery else True
        
        return {
            "status": "online",
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "temp": 0,
            "uptime": f"{int((time.time() - psutil.boot_time()) // 3600)}h",
            "energy": b_percent,
            "battery_percent": b_percent,
            "power_plugged": is_plugged,
            "services": []
        }
    except Exception:
        return {"status": "online", "cpu": 0, "ram": 0, "disk": 0, "temp": 0, "uptime": "0m", "energy": 0, "services": []}

# --- INITIAL SYNC (Frontend bootstrap) ---
@app.get("/api/sync")
async def sync():
    hub = get_intelligence()
    system = _system_status_snapshot(hub)
    # Focus is computed elsewhere; returned for forward-compat without breaking current UI.
    try:
        focus = await get_focus_session_data()
    except Exception:
        focus = None
    return {"intelligence": hub, "system": system, "focus": focus}

# --- NEURAL EDGE: Proactive Sentinel Receiver ---
# Validate the secret is set at module load time — fail closed if missing.
_NEURAL_EDGE_SECRET = os.environ.get("NEURAL_EDGE_SECRET")
if not _NEURAL_EDGE_SECRET:
    raise RuntimeError(
        "[Neural Edge] NEURAL_EDGE_SECRET environment variable is not set. "
        "Add it to your .env file. Server will not start without it."
    )

@app.post("/api/neural/edge-trigger")
async def edge_trigger(request: Request):
    """
    Sub-millisecond Edge-to-Core Trigger.
    Verifies the HMAC-SHA256 signature from the Sentinel Edge Worker.
    """
    signature = request.headers.get("X-Neural-Signature")
    payload = await request.body()

    # --- SIGNATURE VERIFICATION (uses module-level validated secret) ---
    expected_mac = hmac.new(_NEURAL_EDGE_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected_mac):
        logger.warning(f"[Neural Edge] Trigger Denied: Invalid signature from {request.client.host}")
        return Response(status_code=403)

    try:
        data = json.loads(payload)
        t_type = data.get("type")
        
        if t_type == "PROACTIVE_TRIGGER":
            title = data.get("title", "Incoming Task")
            logger.info(f"[Neural Edge] VALIDATED TRIGGER: {title}")
            
            # Injection: Direct to Intelligence Hub
            hub = get_intelligence()
            current_triggers = hub.get("proactive_triggers", {})
            
            timestamp = time.time()
            trigger_id = str(uuid.uuid4())
            current_triggers[trigger_id] = {
                "type": "MEETING_ALERT",
                "title": title,
                "message": f"Pre-detected by Edge Sentinel: {title}",
                "timestamp": timestamp,
                "priority": "HIGH"
            }
            update_intelligence("proactive_triggers", current_triggers)
            
            # --- NEURAL DISPATCHER: Async Mobile Push ---
            try:
                send_dispatch_notification_task.delay(
                    title=f"Sentinel Trigger: {title}",
                    message=f"I've detected a high-priority event approaching: {title}",
                    priority=4 # High priority
                )
            except Exception:
                # Fallback to direct push if Celery is down
                _core_dispatch_logic(
                    title=f"Sentinel Trigger: {title}",
                    message=f"I've detected a high-priority event approaching: {title}",
                    priority=4
                )
            
            # Real-time Broadcast: Notify all system socket listeners
            return {"status": "INJECTED", "id": trigger_id, "dispatched": True}
            
    except Exception as e:
        logger.error(f"[Neural Edge] Pulse Drift: {e}")
        return Response(status_code=400)

@app.get("/api/status")
async def status():
    return {"status": "online", "cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent}

@app.get("/")
async def root():
    """Neural Gateway Status: Returns JSON to identify port 8000 as the Unified API."""
    return JSONResponse(
        content={
            "status": "online",
            "service": "JARVIS Neural Core API",
            "version": "2.0.0-Elite",
            "documentation": "/docs",
            "timestamp": time.time()
        },
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
