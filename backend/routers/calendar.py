import asyncio
from fastapi import APIRouter, HTTPException
from agent.memory import get_calendar_events_db, save_calendar_event, delete_calendar_event_db
from services.cache_service import INTELLIGENCE_HUB, update_intelligence
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CalendarEvent(BaseModel):
    title: str
    event_date: str
    event_time: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = "Task"

@router.get("/")
async def get_calendar(user_id: str = "JARVIS_ADMIN"):
    """Fetches accelerated calendar events for the dashboard."""
    try:
        # SERVE FROM HIGH-SPEED CACHE
        events = INTELLIGENCE_HUB.get("calendar", [])
        
        # Fallback to DB only if cache is initializing
        if not events and INTELLIGENCE_HUB.get("status") == "initializing":
            return await get_calendar_events_db(user_id)
            
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def add_event(event: CalendarEvent, user_id: str = "JARVIS_ADMIN"):
    """Adds a new calendar event and proactively refreshes the cache."""
    try:
        await save_calendar_event(
            user_id, 
            event.title, 
            event.event_date, 
            event.event_time, 
            event.description, 
            event.category
        )
        
        # PROACTIVE CACHE-UPDATE
        async def background_sync():
            new_events = await get_calendar_events_db(user_id)
            update_intelligence("calendar", new_events)
        asyncio.create_task(background_sync())
        
        return {"status": "success", "message": f"Event '{event.title}' recorded and synchronized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{event_id}")
async def delete_event(event_id: str, user_id: str = "JARVIS_ADMIN"):
    """Deletes an event and purges it from the cache instantly."""
    try:
        await delete_calendar_event_db(event_id)
        
        # PROACTIVE CACHE-UPDATE
        async def background_sync():
            new_events = await get_calendar_events_db(user_id)
            update_intelligence("calendar", new_events)
        asyncio.create_task(background_sync())
        
        return {"status": "success", "message": "Event expunged and cache synchronized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
