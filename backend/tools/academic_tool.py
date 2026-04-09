from services.core_service import get_academic_radar, get_today_focus, update_academic_event, add_focus_time

def get_academic_radar_tool():
    """Returns the list of upcoming exams and academic milestones."""
    events = get_academic_radar()
    return f"Upcoming Exams: {', '.join([f'{r['title']} on day {r['date']}' for r in events])}"

def get_focus_stats_tool():
    """Returns today's deep work hours and goal progress."""
    stats = get_today_focus()
    return f"Today's Deep Work: {stats['hours']}h ({stats['goal_met']}% of goal met)."

def add_academic_event_tool(title: str, date: str, task_type: str = "Review"):
    """Adds a new academic event to the radar."""
    update_academic_event(title, date, task_type)
    return f"Successfully added {title} to the academic radar for day {date}."

def log_focus_time_tool(hours: float):
    """Logs deep work hours for today."""
    add_focus_time(hours)
    return f"Logged {hours} hours of deep work. Keep it up!"
