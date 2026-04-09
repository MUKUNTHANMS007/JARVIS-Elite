import os, sys, json, asyncio, random, time, psutil, re, logging, hmac, hashlib
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

# --- LOGGING & DIAGNOSTICS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JARVIS-CORE")

load_dotenv()

# Internal Imports
from voice.stt import transcribe_audio
from voice.tts import synthesize_speech_stream, synthesize_speech, close_tts_client
from agent.core import get_agent_response_stream
from routers.briefing import router as briefing_router
from routers.work import router as work_router
from routers.calendar import router as calendar_router
from routers.core import router as core_router
from routers.evolution import router as evolution_router
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
from tasks import process_stt_task, analyze_mood_task, send_dispatch_notification_task, analyze_vision_task

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
            except Exception: pass
            await asyncio.sleep(300)

    async def sync_leetcode():
        while True:
            try:
                stats = await get_leetcode_stats(user_lc, sync=True)
                update_intelligence("leetcode", stats)
            except Exception: pass
            await asyncio.sleep(300)

    async def sync_github():
        while True:
            try:
                pulse = await asyncio.wait_for(asyncio.to_thread(get_github_pulse), timeout=15)
                update_intelligence("github", pulse)
            except Exception: pass
            await asyncio.sleep(300)

    async def sync_calendar_sentinel():
        while True:
            try:
                calendar_data = await get_calendar_events_db(user_id)
                reminders_data = await get_active_reminders_db(user_id)
                update_intelligence("calendar", calendar_data)
                update_intelligence("active_reminders", reminders_data)
                
                now = time.time()
                today_str = datetime.now().strftime("%Y-%m-%d")
                for event in calendar_data:
                    if event.get("event_date") == today_str:
                        e_time = event.get("event_time")
                        if e_time:
                            ev_dt = datetime.strptime(f"{today_str} {e_time}", "%Y-%m-%d %H:%M:%S")
                            diff = (ev_dt.timestamp() - now) / 60
                            if 0 < diff <= 15:
                                current_triggers = get_intelligence().get("proactive_triggers", {})
                                if event.get("title") not in current_triggers:
                                    current_triggers[event.get("title")] = {
                                        "type": "MEETING_ALERT", "title": event.get("title"), "diff": round(diff), "timestamp": now
                                    }
                                    update_intelligence("proactive_triggers", current_triggers)
            except Exception: pass
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

    # Spawn all as independent background tasks
    await asyncio.gather(
        sync_gmail(),
        sync_leetcode(),
        sync_github(),
        sync_calendar_sentinel(),
        sync_cloud_mirror()
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    await init_db()
    hub_task = asyncio.create_task(refresh_intelligence_hub())
    logger.info("[Neural Core] Unified Intelligence Online.")
    yield
    # SHUTDOWN
    hub_task.cancel()
    await close_tts_client()
    logger.info("[Neural Core] Shutting down.")

app = FastAPI(title="JARVIS Neural Core", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# --- NEURAL FIREWALL: Trusted Host Filtering ---
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.trycloudflare.com", "0.0.0.0"]
)

# --- NEURAL FIREWALL: Security Headers ---
class NeuralSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
        return response

app.add_middleware(NeuralSecurityMiddleware)

# --- NEURAL GATEWAY: Restricted CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:3000", 
        "http://localhost:3001", 
        "http://127.0.0.1:3001"
    ],
    allow_origin_regex=r"https://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- NEURAL WORKERS ---

def calculate_audio_energy(audio_data: bytes) -> float:
    import numpy as np
    try:
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        if len(audio_np) == 0: return 0.0
        return np.sqrt(np.mean(audio_np.astype(np.float32)**2))
    except Exception: return 0.0

async def bridge_tts_worker(websocket: WebSocket, queue: asyncio.Queue):
    """Feeds audio chunks to client with safety guards."""
    while True:
        try:
            sentence = await queue.get()
            if sentence is None: break
            async for fragment in synthesize_speech_stream(sentence.strip()):
                try:
                    await websocket.send_bytes(fragment)
                except Exception: break 
            queue.task_done()
        except Exception: break

async def process_agent_turn(websocket: WebSocket, text: str, image_data: str, tts_queue: asyncio.Queue, is_stressed: bool = False, lock: asyncio.Lock = None):
    """Observer Pattern: LLM Stream -> UI Text -> TTS Queue with Turn Locking and Mood."""
    if lock: await lock.acquire()
    try:
        await websocket.send_json({"type": "TURN_START", "mood": "stressed" if is_stressed else "normal"})
        
        # --- NEURAL ORCHESTRATOR: Multi-Modal Offloading ---
        vision_context = ""
        if image_data:
            vision_job = analyze_vision_task.delay(image_data, context_text=text)
            # Parallel processing: Continue conversation while vision arrives
            # vision_res = vision_job.get(timeout=5)
            # vision_context = vision_res.get("insight", "")

        sentence_buffer = ""
        token_count = 0
        first_chunk = True
        
        async for token in get_agent_response_stream(text, image_base64=image_data, is_stressed=is_stressed):
            if websocket.client_state.name != "CONNECTED": break
            await websocket.send_json({"type": "TEXT_CHUNK", "text": token})
            sentence_buffer += token
            token_count += 1
            
            # Sentence segmenting for natural TTS flow
            is_punctuation = any(sentence_buffer.endswith(p) for p in [". ", "? ", "! ", "\n", ", ", "; "])
            threshold = 6 if first_chunk else 4
            if is_punctuation or token_count >= threshold:
                clean = sentence_buffer.strip()
                if len(clean) > 1:
                    await tts_queue.put(clean)
                    first_chunk = False
                    sentence_buffer = ""
                    token_count = 0
        if sentence_buffer.strip():
            await tts_queue.put(sentence_buffer.strip())
    except Exception as e: logger.error(f"[Turn Error] {e}")
    finally:
        if websocket.client_state.name == "CONNECTED":
            await websocket.send_json({"type": "TURN_COMPLETE"})
        if lock: lock.release()

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    tts_queue = asyncio.Queue()
    worker_task = asyncio.create_task(bridge_tts_worker(websocket, tts_queue))
    audio_buffer = bytearray()
    image_data = None
    turn_lock = asyncio.Lock()
    
    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                audio_buffer.extend(data["bytes"])
            elif "text" in data:
                msg = json.loads(data["text"])
                m_type = msg.get("type")
                if m_type == "text_input":
                    asyncio.create_task(process_agent_turn(websocket, msg.get("text"), msg.get("image") or image_data, tts_queue, lock=turn_lock))
                elif m_type == "stop_recording":
                    # --- NEURAL ORCHESTRATOR: Async Task Offloading ---
                    audio_hex = audio_buffer.hex()
                    energy = calculate_audio_energy(bytes(audio_buffer))
                    
                    # 1. Offload Mood Analysis
                    mood_job = analyze_mood_task.delay(energy)
                    
                    # 2. Offload STT Transcription
                    stt_job = process_stt_task.delay(audio_hex)
                    
                    # Wait for high-priority STT result (Simulation of Queue -> Backend flow)
                    # In true high-scale, we would use a webhook or polling
                    result = stt_job.get(timeout=10)
                    user_text = result.get("text", "")
                    
                    if user_text:
                        mood_res = mood_job.get(timeout=2)
                        is_stressed = mood_res.get("is_stressed", False)
                        
                        await websocket.send_json({"type": "TRANSCRIPTION", "text": user_text})
                        asyncio.create_task(process_agent_turn(
                            websocket, 
                            user_text, 
                            image_data, 
                            tts_queue, 
                            is_stressed=is_stressed, 
                            lock=turn_lock
                        ))
                    audio_buffer.clear()
                elif m_type == "PING":
                    await websocket.send_json({"type": "PONG", "timestamp": time.time()})
    except WebSocketDisconnect: pass
    finally:
        worker_task.cancel()
        try: await websocket.close()
        except Exception: pass

@app.websocket("/ws/system")
async def system_socket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async def telemetry_pusher():
        _slow_tick = 0
        try:
            while True:
                hub = get_intelligence()
                focus = await get_focus_session_data()
                _slow_tick += 1
                if _slow_tick >= 4:
                    _slow_tick = 0
                    try:
                        spotify = await asyncio.to_thread(get_current_track_data)
                        update_intelligence("spotify_track", spotify.get("name", "Standby") if isinstance(spotify, dict) else "Standby")
                    except Exception: pass

                # 1. Fetch Proactive Alerts from Hub (Injected by Edge Sentinel)
                proactive_alert = None
                triggers = hub.get("proactive_triggers", {})
                if triggers:
                    # Pick the most recent trigger
                    trigger_keys = sorted(triggers.keys(), key=lambda x: triggers[x].get("timestamp", 0))
                    if trigger_keys:
                        latest_key = trigger_keys[-1]
                        t_data = triggers[latest_key]
                        proactive_alert = PydanticAlert(
                            id=latest_key,
                            type=t_data["type"],
                            title=t_data["title"],
                            message=t_data.get("message", "High Priority System Notice"),
                            timestamp=t_data["timestamp"],
                            priority=t_data.get("priority", "NORMAL")
                        )
                        # Remove alert after sending to prevent repeated notifications
                        triggers.pop(latest_key)
                        update_intelligence("proactive_triggers", triggers)

                # Build Neural Packet (Pydantic for internal handling)
                p_packet = PydanticPacket(
                    type="NEURAL_PULSE",
                    state=hub.get("agent_state", "IDLE"),
                    telemetry=PydanticTelemetry(
                        cpu_percent=psutil.cpu_percent(),
                        ram_percent=psutil.virtual_memory().percent,
                        mood_score=hub.get("mood_score", 0.0),
                        is_online=True
                    ),
                    dashboard=PydanticDashboard(
                        unread_mail=hub.get("gmail_unread", 0),
                        spotify_track=hub.get("spotify_track", "Standby"),
                        reminder_count=len(hub.get("active_reminders", [])),
                        leetcode_status=hub.get("leetcode"),
                        github_pulse=hub.get("github")
                    ),
                    alert=proactive_alert
                )

                # 1. OPTIMIZED: Protobuf Serialization (Binary)
                try:
                    pb_packet = pb.NeuralPacket()
                    pb_packet.type = p_packet.type
                    pb_packet.timestamp = p_packet.timestamp
                    pb_packet.state = getattr(pb, p_packet.state)
                    
                    pb_packet.telemetry.cpu_percent = p_packet.telemetry.cpu_percent
                    pb_packet.telemetry.ram_percent = p_packet.telemetry.ram_percent
                    pb_packet.telemetry.mood_score = p_packet.telemetry.mood_score
                    pb_packet.telemetry.is_online = p_packet.telemetry.is_online
                    
                    pb_packet.dashboard.unread_mail = p_packet.dashboard.unread_mail
                    pb_packet.dashboard.spotify_track = p_packet.dashboard.spotify_track
                    pb_packet.dashboard.reminder_count = p_packet.dashboard.reminder_count
                    
                    if p_packet.dashboard.leetcode_status:
                        pb_packet.dashboard.leetcode_status_json = json.dumps(p_packet.dashboard.leetcode_status)
                    if p_packet.dashboard.github_pulse:
                        pb_packet.dashboard.github_pulse_json = json.dumps(p_packet.dashboard.github_pulse)
                    
                    if p_packet.active_tool:
                        pb_packet.active_tool = p_packet.active_tool
                    
                    if p_packet.alert:
                        pb_packet.alert.id = p_packet.alert.id
                        pb_packet.alert.type = p_packet.alert.type
                        pb_packet.alert.title = p_packet.alert.title
                        pb_packet.alert.message = p_packet.alert.message
                        pb_packet.alert.timestamp = p_packet.alert.timestamp
                        pb_packet.alert.priority = p_packet.alert.priority

                    # Send binary to client
                    await websocket.send_bytes(pb_packet.SerializeToString())
                except Exception as e:
                    # Fallback to JSON if Proto fails
                    logger.error(f"[Neural Protocol] Proto Drift: {e}")
                    await websocket.send_json(p_packet.dict())

                await asyncio.sleep(1) # Peak frequency
        except Exception: pass
    try: await telemetry_pusher()
    except WebSocketDisconnect: pass

# --- REST API ROUTES ---

app.include_router(briefing_router, prefix="/api/briefing")
app.include_router(work_router, prefix="/api/work")
app.include_router(calendar_router, prefix="/api/calendar")
app.include_router(core_router, prefix="/api/core")
app.include_router(evolution_router, prefix="/api/evolution")

# --- NEURAL EDGE: Proactive Sentinel Receiver ---
@app.post("/api/neural/edge-trigger")
async def edge_trigger(request: Request):
    """
    Sub-millisecond Edge-to-Core Trigger.
    Verifies the HMAC-SHA256 signature from the Sentinel Edge Worker.
    """
    signature = request.headers.get("X-Neural-Signature")
    payload = await request.body()
    secret = os.getenv("NEURAL_EDGE_SECRET", "J_SENTINEL_SECURE_2026")

    # --- SIGNATURE VERIFICATION ---
    expected_mac = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
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
            current_triggers[trigger_id] = {
                "type": "MEETING_ALERT",
                "title": title,
                "message": f"Pre-detected by Edge Sentinel: {title}",
                "timestamp": timestamp,
                "priority": "HIGH"
            }
            update_intelligence("proactive_triggers", current_triggers)
            
            # --- NEURAL DISPATCHER: Async Mobile Push ---
            send_dispatch_notification_task.delay(
                title=f"Sentinel Trigger: {title}",
                message=f"I've detected a high-priority event approaching: {title}",
                priority=4 # High priority
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
