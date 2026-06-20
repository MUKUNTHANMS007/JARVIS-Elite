from services.core_service import get_academic_radar, get_today_focus, update_academic_event, add_focus_time

async def get_academic_radar_tool():
    """Returns the list of upcoming exams and academic milestones."""
    events = await get_academic_radar()
    event_strs = []
    for r in events:
        title = r.get('title', 'Exam')
        date_val = r.get('date', '')
        event_strs.append(f"{title} on day {date_val}")
    return f"Upcoming Exams: {', '.join(event_strs)}"

async def get_focus_stats_tool():
    """Returns today's deep work hours and goal progress."""
    stats = await get_today_focus()
    hours = stats.get('hours', 0)
    goal_met = stats.get('goal_met', 0)
    return f"Today's Deep Work: {hours}h ({goal_met}% of goal met)."

def add_academic_event_tool(title: str, date: str, task_type: str = "Review"):
    """Adds a new academic event to the radar."""
    update_academic_event(title, date, task_type)
    return f"Successfully added {title} to the academic radar for day {date}."

def log_focus_time_tool(hours: float):
    """Logs deep work hours for today."""
    add_focus_time(hours)
    return f"Logged {hours} hours of deep work. Keep it up!"
