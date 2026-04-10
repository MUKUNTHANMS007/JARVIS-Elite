import asyncio, json, time
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Manages all WebSocket connections with heartbeat + reconnect support."""
    
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.metadata: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active[client_id] = websocket
        self.metadata[client_id] = {
            "connected_at": time.time(),
            "batman_mode": False
        }
        print(f"[WS Manager] Client connected: {client_id} | Total: {len(self.active)}")
    
    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)
        self.metadata.pop(client_id, None)
        print(f"[WS Manager] Client disconnected: {client_id} | Remaining: {len(self.active)}")
    
    async def send_json(self, client_id: str, data: dict):
        ws = self.active.get(client_id)
        if ws and ws.client_state.name == "CONNECTED":
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"[WS Manager] Send failed for {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_bytes(self, client_id: str, data: bytes):
        ws = self.active.get(client_id)
        if ws and ws.client_state.name == "CONNECTED":
            try:
                await ws.send_bytes(data)
            except Exception as e:
                print(f"[WS Manager] Byte send failed for {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, data: dict, exclude: str = None):
        """Send to all connected clients."""
        dead = []
        for client_id, ws in self.active.items():
            if client_id == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(client_id)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()
