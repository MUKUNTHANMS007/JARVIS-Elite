import os
from datetime import datetime, timedelta, timezone
from agent.memory import save_reminder, get_active_reminders_db, delete_reminder_db

async def set_reminder(text: str, time_str: str = None, minutes_delay: int = None) -> str:
    """Sets a persistent reminder in the JARVIS database (Supabase)."""
    try:
        # Determine the reminder time
        target_time = None
        if minutes_delay is not None:
            target_time = datetime.now(timezone.utc) + timedelta(minutes=int(minutes_delay))
        elif time_str:
            # Flexible parsing for 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
            try:
                if len(time_str.strip()) <= 10:
                    target_time = datetime.strptime(time_str.strip(), "%Y-%m-%d").replace(hour=10, minute=0)
                else:
                    target_time = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
            except:
                target_time = datetime.utcnow() + timedelta(hours=1)
        else:
            # PROACTIVE MODE: Assume 1 hour delay if Mukunthan just said 'sure' or 'remind me'
            target_time = datetime.now(timezone.utc) + timedelta(hours=1)
            
        await save_reminder("JARVIS_ADMIN", text, target_time)
        
        display_time = target_time.strftime("%I:%M %p")
        return f"Successfully set a reminder for {display_time}: '{text}'. Neural sync complete."
        
    except Exception as e:
        return f"Database error while setting reminder: {str(e)}"

async def get_active_reminders() -> str:
    """Fetch all pending reminders from Supabase that haven't been triggered yet."""
    try:
        reminders = await get_active_reminders_db("JARVIS_ADMIN")
        if not reminders:
            return "You have no active reminders."
            
        return "Your active reminders: \n" + "\n".join(
            f"- [{r['id']}] {r['text']} at {datetime.fromisoformat(r['reminder_time']).strftime('%I:%M %p')}" 
            for r in reminders
        )
    except Exception as e:
        return f"Error fetching reminders: {str(e)}"

async def delete_reminder(reminder_id: str) -> str:
    """Deletes a persistent reminder from Supabase using its ID."""
    try:
        if not reminder_id:
            return "Sir, I require a valid reminder ID to clear that neural path."
            
        await delete_reminder_db(reminder_id)
        return f"Reminder {reminder_id} has been successfully purged from our memory. Neural sync complete."
        
    except Exception as e:
        return f"Database error while deleting reminder: {str(e)}"
