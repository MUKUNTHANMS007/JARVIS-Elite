import json
import os
import time
from datetime import datetime

HABIT_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "habit_learning.json")

def log_habit_data(activity: str):
    """Logs a timestamped activity to the learning engine."""
    try:
        if not os.path.exists(os.path.dirname(HABIT_FILE)):
            os.makedirs(os.path.dirname(HABIT_FILE))
            
        data = []
        if os.path.exists(HABIT_FILE):
            with open(HABIT_FILE, "r") as f:
                data = json.load(f)
        
        data.append({
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%H:%M"),
            "day": datetime.now().strftime("%A"),
            "activity": activity
        })
        
        # Keep only last 500 entries
        data = data[-500:]
        
        with open(HABIT_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return "Habit logged to neural memory, Sir."
    except Exception as e:
        return f"Learning failure: {e}"

def get_habit_insights():
    """Analyzes logged data to predict deep work slots."""
    try:
        if not os.path.exists(HABIT_FILE):
            return "No habit data available for analysis, Sir."
            
        with open(HABIT_FILE, "r") as f:
            data = json.load(f)
            
        # Very simple frequency analysis: Which hour is most common for 'deep_work'?
        hours = {}
        for entry in data:
            if entry["activity"] == "deep_work":
                hr = entry["time_str"].split(":")[0]
                hours[hr] = hours.get(hr, 0) + 1
        
        if not hours:
            return "Insufficient focus data to provide a baseline, Sir."
            
        top_hour = max(hours, key=hours.get)
        return f"Based on your neural patterns, you typically initiate deep work at {top_hour}:00. I recommend scheduling focus blocks during this window."
    except Exception as e:
        return f"Insight drift: {e}"
