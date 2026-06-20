import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from agent.memory import save_reminder, get_active_reminders_db, delete_reminder_db

# Use the system local timezone for user-facing times.
# Override with JARVIS_LOCAL_TZ env var (e.g. "Asia/Kolkata") for correctness
# when the server's system timezone differs from the user's location.
_LOCAL_TZ_NAME = os.environ.get("JARVIS_LOCAL_TZ", "")
try:
    _LOCAL_TZ = ZoneInfo(_LOCAL_TZ_NAME) if _LOCAL_TZ_NAME else datetime.now().astimezone().tzinfo
except ZoneInfoNotFoundError:
    print(f"[Reminder] Unknown timezone '{_LOCAL_TZ_NAME}', falling back to system local.")
    _LOCAL_TZ = datetime.now().astimezone().tzinfo


async def set_reminder(text: str, time_str: str = None, minutes_delay: int = None) -> str:
    """Sets a persistent reminder in the JARVIS database (Supabase).

    All times are stored as UTC-aware datetimes.  When the user gives an
    explicit time string it is interpreted as local time (JARVIS_LOCAL_TZ or
    system timezone), NOT as UTC, to match natural conversation.
    """
    try:
        target_time = None

        if minutes_delay is not None:
            target_time = datetime.now(timezone.utc) + timedelta(minutes=int(minutes_delay))

        elif time_str:
            # Flexible parsing for 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
            parsed_naive = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed_naive = datetime.strptime(time_str.strip(), fmt)
                    # Date-only format → default to 10:00 AM local
                    if fmt == "%Y-%m-%d":
                        parsed_naive = parsed_naive.replace(hour=10, minute=0)
                    break
                except ValueError:
                    continue

            if parsed_naive is None:
                # Parse failed — tell the user explicitly instead of silently setting
                # a reminder for "1 hour from now" with the wrong time displayed.
                return (
                    f"Sir, I couldn't parse '{time_str}' as a date/time. "
                    "Please use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format."
                )

            # Interpret the parsed time as local (not UTC) and convert to UTC for storage
            local_aware = parsed_naive.replace(tzinfo=_LOCAL_TZ)
            target_time = local_aware.astimezone(timezone.utc)

        else:
            # PROACTIVE MODE: Assume 1 hour delay if user just said 'remind me'
            target_time = datetime.now(timezone.utc) + timedelta(hours=1)

        await save_reminder("JARVIS_ADMIN", text, target_time)

        # Display time back in local timezone so the confirmation makes sense
        local_display = target_time.astimezone(_LOCAL_TZ)
        display_time = local_display.strftime("%I:%M %p")
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
            f"- [{r['id']}] {r['text']} at {datetime.fromisoformat(r['reminder_time']).astimezone(_LOCAL_TZ).strftime('%I:%M %p')}"
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
