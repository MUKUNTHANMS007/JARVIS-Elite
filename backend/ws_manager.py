import asyncio, json, time
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Manages all WebSocket connections with heartbeat + reconnect support."""
    
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.metadata: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active[client_id] = websocket
        self.locks[client_id] = asyncio.Lock()
        self.metadata[client_id] = {
            "connected_at": time.time(),
            "batman_mode": False
        }
        print(f"[WS Manager] Client connected: {client_id} | Total: {len(self.active)}")
    
    def disconnect(self, client_id: str, reason: str = "Unknown"):
        self.active.pop(client_id, None)
        self.locks.pop(client_id, None)
        self.metadata.pop(client_id, None)
        print(f"[WS Manager] Client disconnected: {client_id} | Reason: {reason} | Remaining: {len(self.active)}")
    
    async def send_json(self, client_id: str, data: dict):
        ws = self.active.get(client_id)
        lock = self.locks.get(client_id)
        if ws and ws.client_state.name == "CONNECTED" and lock:
            async with lock:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    print(f"[WS Manager] Send failed for {client_id}: {e}")
                    self.disconnect(client_id, reason=f"SendJsonError: {e}")
    
    async def send_bytes(self, client_id: str, data: bytes):
        ws = self.active.get(client_id)
        lock = self.locks.get(client_id)
        if ws and ws.client_state.name == "CONNECTED" and lock:
            async with lock:
                try:
                    await ws.send_bytes(data)
                except Exception as e:
                    # Do NOT disconnect on a single audio-chunk failure — just skip the chunk.
                    # Disconnecting here was causing the entire voice session to die after
                    # one TTS error, making all subsequent turns silently ignored.
                    print(f"[WS Manager] Byte send failed for {client_id} (chunk skipped): {e}")
    
    async def broadcast(self, data: dict, exclude: str = None):
        """Send to all connected clients."""
        dead = []
        clients = list(self.active.keys())
        for client_id in clients:
            if client_id == exclude:
                continue
            ws = self.active.get(client_id)
            lock = self.locks.get(client_id)
            if ws and ws.client_state.name == "CONNECTED" and lock:
                async with lock:
                    try:
                        await ws.send_json(data)
                    except Exception:
                        dead.append(client_id)
        for d in dead:
            self.disconnect(d, reason="Broadcast failure")

manager = ConnectionManager()
