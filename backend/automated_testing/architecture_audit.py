import requests
import asyncio
import json
import time
import websockets
from datetime import datetime

# J.A.R.V.I.S. Production Architecture Audit (2026)
# Verification of Unified Core, WebSockets, and DB Status.

API_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

async def test_websocket(path: str, name: str):
    url = f"{WS_URL}{path}"
    print(f"[Audit] Testing WebSocket Handshake: {name} ({url})...", end="", flush=True)
    try:
        async with websockets.connect(url, open_timeout=5) as ws:
            # Wait for initial packet if it's the Hub
            if "system" in path:
                packet = await asyncio.wait_for(ws.recv(), timeout=6)
                data = json.loads(packet)
                if data.get("type") == "SYSTEM_PULSE":
                    print(" PASS (Pulse Verified)")
                else:
                    print(f" PASS (Handshake OK, Packet Type: {data.get('type')})")
            else:
                print(" PASS")
    except Exception as e:
        print(f" FAIL: {e}")

def test_endpoint(path: str, name: str):
    url = f"{API_URL}{path}"
    print(f"[Audit] Testing REST Endpoint: {name} ({url})...", end="", flush=True)
    try:
        start = time.time()
        resp = requests.get(url, timeout=5)
        latency = (time.time() - start) * 1000
        if resp.status_code == 200:
            print(f" PASS ({latency:.1f}ms)")
            return resp.json()
        else:
            print(f" FAIL (HTTP {resp.status_code})")
    except Exception as e:
        print(f" FAIL: {e}")
    return None

async def run_audit():
    print(f"\n{'='*50}")
    print(f" J.A.R.V.I.S. ARCHITECTURE AUDIT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # 1. REST Connectivity
    test_endpoint("/", "Root Gateway")
    test_endpoint("/api/status", "Core Health")
    sync_data = test_endpoint("/api/sync", "Initial Sync API")
    
    # 2. Database Status (Via Internal Sync)
    if sync_data and "system" in sync_data:
        print(f"[Audit] Database Status: {'ONLINE' if sync_data['system'].get('status') == 'online' else 'OFFLINE'}")

    # 3. WebSocket Handshaking
    await test_websocket("/ws/system", "Intelligence Hub (System)")
    await test_websocket("/ws/voice", "Neural Core (Voice)")

    print(f"\n{'='*50}")
    print(" AUDIT COMPLETED")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    asyncio.run(run_audit())
