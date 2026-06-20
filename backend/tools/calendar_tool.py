import os, asyncio
from datetime import datetime, timedelta
from agent.memory import save_calendar_event, get_calendar_events_db, delete_calendar_event_db
from services.cache_service import get_intelligence, update_intelligence
from tools.persistent_alert_tool import send_neural_push

async def manage_calendar(action: str, title: str = None, date: str = None, time: str = None, description: str = None, category: str = "Task", event_id: str = None) -> str:
    """
    Manages the J.A.R.V.I.S. Neural Calendar with Intelligence Hub acceleration.
    - action: 'add', 'list', or 'delete'
    """
    try:
        user_id = "JARVIS_ADMIN"
        intelligence = get_intelligence()
        
        if action == "add":
            if not title or not date:
                return "Error: Title and Date (YYYY-MM-DD) are required to add an event."
            
            # --- DATE NORMALIZATION LAYER ---
            # Handles relative dates: 'today', 'tomorrow'
            # Use word-split matching to avoid "day after tomorrow" matching "tomorrow".
            normalized_date = date.lower().strip()
            date_words = normalized_date.split()
            today_obj = datetime.now()

            if "today" in date_words:
                date = today_obj.strftime("%Y-%m-%d")
            elif date_words == ["tomorrow"] or normalized_date == "tomorrow":
                date = (today_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            # --- END NORMALIZATION ---
            
            success = await save_calendar_event(user_id, title, date, time, description, category)
            
            if success:
                # PROACTIVE CACHE-UPDATE: Trigger async refresh immediately
                async def background_sync():
                    new_events = await get_calendar_events_db(user_id)
                    update_intelligence("calendar", new_events)
                asyncio.create_task(background_sync())
                
                return f"Understood, Sir. I've recorded '{title}' in your Neural Core for {date}."
            else:
                return f"Error: Failed to synchronize '{title}' with your Neural Memory, Sir."

        elif action == "list":
            # ACCELERATED PATH: Serve from high-speed synchronized cache
            events = intelligence.get("calendar", [])
            
            if not events:
                # Cache empty: attempt live DB fetch before claiming the calendar is clear.
                # This avoids falsely reporting "no events" when the cache just hasn't
                # synced yet or when Supabase was temporarily unavailable.
                try:
                    events = await get_calendar_events_db(user_id)
                except Exception:
                    return "Sir, I was unable to reach Neural Memory right now. Please try again in a moment."
                if not events:
                    return "Your calendar is currently clear, Sir. Operative efficiency is at 100%."
            
            output = "Your Upcoming Schedule, Sir:\n"
            for e in events:
                time_str = f" at {e['event_time']}" if e.get('event_time') else ""
                # Include ID in output for the AI to handle deletions
                output += f"- [ID: {e['id']}] [{e['category']}] {e['event_date']}{time_str}: {e['title']}\n"
            return output

        elif action == "send_to_phone":
            # SYNCED PUSH: Integrated Retrieval + Delivery Loop
            events = intelligence.get("calendar", [])
            
            # Fallback to DB if cache is initializing
            if not events and intelligence.get("status") == "initializing":
                events = await get_calendar_events_db(user_id)
            
            if not events:
                return "The calendar is currently clear, Sir. There is no schedule to synchronize."
            
            # Formatting for professional mobile delivery
            push_content = "Neural Schedule Update:\n"
            for e in events:
                time_str = f" at {e['event_time']}" if e.get('event_time') else ""
                push_content += f"• {e['event_date']}{time_str}: {e['title']}\n"
            
            # Atomic Dispatch via Push Bridge
            result = send_neural_push(
                title="Operational Schedule",
                message=push_content,
                priority=4 # Elevate priority for scheduling
            )
            
            return f"Synchronized, Sir. {result}. I have also updated your local display."

        elif action == "delete":
            if not event_id:
                return "I require a specific event_id to purge that entry, Sir."
            
            success = await delete_calendar_event_db(event_id)
            
            if success:
                # PROACTIVE CACHE-UPDATE
                async def background_sync():
                    new_events = await get_calendar_events_db(user_id)
                    update_intelligence("calendar", new_events)
                asyncio.create_task(background_sync())
                
                return f"Protocol complete. Event {event_id} has been expunged from the legacy."
            else:
                return f"Error: I was unable to purge event {event_id} from your Neural Memory, Sir."

        return f"Sir, '{action}' is not in my scheduling logic."

    except Exception as e:
        return f"Sir, my neural link failed during calendar management: {str(e)}"
