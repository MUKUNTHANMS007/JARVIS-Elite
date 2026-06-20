import asyncio

# Global registry for WebSocket connections that need focus updates
focus_connections = set()

async def broadcast_timer_event(event_type: str, duration: int = None):
    """
    Unified Event Bus for Focus Timer signals.
    Decouples the Agent from the FastAPI WebSocket endpoints to prevent circular imports.
    """
    payload = {"type": "TIMER_EVENT", "event": event_type}
    if duration: 
        payload["duration"] = duration
    
    dead_links = set()
    for ws in list(focus_connections):
        try:
            # Send events to all connected dashboard and neural link tabs
            await ws.send_json(payload)
        except:
            dead_links.add(ws)
            
    # Cleanup severed links
    for ws in dead_links:
        if ws in focus_connections:
            focus_connections.remove(ws)
