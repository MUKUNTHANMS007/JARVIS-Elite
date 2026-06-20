import asyncio, uuid, psutil, time, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
from services.cache_service import get_intelligence, update_intelligence
from services.focus_service import get_focus_session_data

router = APIRouter()

@router.websocket("/ws/system")
async def system_pulse(websocket: WebSocket):
    # Secure connection
    import os
    token = os.environ.get("WS_AUTH_TOKEN")
    if token:
        provided = websocket.query_params.get("token", "")
        if provided != token:
            await websocket.accept()
            await websocket.close(code=4401, reason="Unauthorized")
            return
    else:
        client = websocket.client
        if client is None or client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            await websocket.accept()
            await websocket.close(code=4401, reason="Unauthorized")
            return

    client_id = f"hub_{uuid.uuid4()}"
    await manager.connect(websocket, client_id)
    print(f"[Hub] Handshake established for {client_id}")

    # Background sender task
    async def sender():
        try:
            while websocket.client_state.name == "CONNECTED":
                hub = get_intelligence()
                cpu  = psutil.cpu_percent(interval=None)
                ram  = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                battery = psutil.sensors_battery()

                # Fetch Focus Session data (War-Room)
                try:
                    focus_data = await get_focus_session_data()
                except Exception as fe:
                    print(f"[Hub] Focus fetch error: {fe}")
                    focus_data = None

                # Fetch ALL Proactive Alerts from Hub and drain them in one pulse
                proactive_triggers_list = []
                triggers = hub.get("proactive_triggers", {})
                if triggers:
                    for t_key, t_data in list(triggers.items()):
                        # Use .get() with safe defaults — bare indexing caused KeyError
                        # crashes in the sender loop if a trigger was missing a field.
                        proactive_triggers_list.append({
                            "id": t_key,
                            "type": t_data.get("type", "ALERT"),
                            "title": t_data.get("title", "Incoming Alert"),
                            "message": t_data.get("message", ""),
                            "timestamp": t_data.get("timestamp", 0),
                            "diff": round((t_data.get("timestamp", 0) - time.time()) / 60)
                        })
                        triggers.pop(t_key)
                    update_intelligence("proactive_triggers", triggers)

                # For backward-compat the dashboard key sends the first/only trigger
                proactive_trigger = proactive_triggers_list[0] if proactive_triggers_list else None

                packet = {
                    "type": "SYSTEM_PULSE",
                    "focus": focus_data,
                    "dashboard": {
                        "unread_mail":   hub.get("gmail_unread", 0),
                        "briefing":      hub.get("gmail_briefing", ""),
                        "leetcode":      hub.get("leetcode", {}),
                        "github":        hub.get("github", {}),
                        "spotify_track": hub.get("spotify_track", "Standby"),
                        "spotify_image": hub.get("spotify_image", None),
                        "is_batman_mode": hub.get("batman_mode", False),
                        "last_synced":   hub.get("last_synced", ""),
                        "proactive_trigger": proactive_trigger
                    },
                    "status": {
                        "cpu":    round(cpu, 1),
                        "ram":    round(ram, 1),
                        "disk":   round(disk, 1),
                        "energy": round(battery.percent if battery else 100, 1),
                        "uptime": f"{int((time.time() - psutil.boot_time()) // 3600)}h",
                    },
                    "ts": time.time()
                }

                await manager.send_json(client_id, packet)
                await asyncio.sleep(5)
        except Exception as e:
            print(f"[Hub Sender] Error for {client_id}: {e}")

    sender_task = asyncio.create_task(sender())

    # Guard: if the sender task dies unexpectedly (e.g. malformed proactive trigger),
    # close the WebSocket so the receiver loop doesn't silently idle with no pulses.
    def _on_sender_done(task: asyncio.Task):
        if not task.cancelled() and task.exception() is not None:
            exc = task.exception()
            logging.getLogger("JARVIS-HUB").error(
                f"[Hub Sender] Task died unexpectedly for {client_id}: {exc!r}. "
                "Closing WebSocket to prevent stale connection."
            )
            # Schedule close without blocking the callback
            asyncio.create_task(websocket.close(1011))

    sender_task.add_done_callback(_on_sender_done)

    try:
        # Keep connection open and listen for close frames or messages
        while websocket.client_state.name == "CONNECTED":
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Hub] Connection error for {client_id}: {e}")
    finally:
        sender_task.cancel()
        if client_id in manager.active:
            manager.disconnect(client_id, reason="Connection closed or lost")
