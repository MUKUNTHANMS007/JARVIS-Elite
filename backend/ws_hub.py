import asyncio, uuid, psutil, time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
from services.cache_service import get_intelligence, update_intelligence

router = APIRouter()

@router.websocket("/ws/system")
async def system_pulse(websocket: WebSocket):
    client_id = f"hub_{uuid.uuid4()}"
    await manager.connect(websocket, client_id)
    print(f"[Hub] Handshake established for {client_id}")

    try:
        while websocket.client_state.name == "CONNECTED":
            hub = get_intelligence()
            cpu  = psutil.cpu_percent(interval=None)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Using hardware sensors for battery where available
            battery = psutil.sensors_battery()

            # 1. Fetch Proactive Alerts from Hub (Injected by Edge Sentinel)
            proactive_trigger = None
            triggers = hub.get("proactive_triggers", {})
            if triggers:
                # Pick the most recent trigger
                trigger_keys = sorted(triggers.keys(), key=lambda x: triggers[x].get("timestamp", 0))
                if trigger_keys:
                    latest_key = trigger_keys[-1]
                    t_data = triggers[latest_key]
                    proactive_trigger = {
                        "id": latest_key,
                        "type": t_data["type"],
                        "title": t_data["title"],
                        "message": t_data.get("message", ""),
                        "timestamp": t_data["timestamp"],
                        "diff": round((t_data["timestamp"] - time.time()) / 60) # mins
                    }
                    # Remove after sending to prevent repeated notifications
                    triggers.pop(latest_key)
                    update_intelligence("proactive_triggers", triggers)

            packet = {
                "type": "SYSTEM_PULSE",
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

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Hub] Error for {client_id}: {e}")
    finally:
        manager.disconnect(client_id)
