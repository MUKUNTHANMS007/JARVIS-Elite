"""
JARVIS Sentinel: Diff-based proactive analysis layer.

The background sync loops in main.py only overwrite the latest snapshot in the
Intelligence Hub on every cycle — they never compare it to what came before.
This module holds the "what did I see last time" state for Gmail, GitHub,
LeetCode and Spotify, and only pushes a phone alert when something genuinely
changed. That's the difference between a dashboard you have to check and a
JARVIS that taps you on the shoulder.

All dispatches are notify-only — alerts may include a one-tap deep link
(e.g. "Open Gmail"), but JARVIS never sends replies, comments, or commits on
your behalf.
"""
import time
import threading
from datetime import datetime

from tools.persistent_alert_tool import send_neural_push
from services.cache_service import get_intelligence, update_intelligence

_lock = threading.Lock()


def _dispatch(title: str, message: str, priority: int = 3, action_label: str = None,
              action_url: str = None, trigger_type: str = "ALERT"):
    """Push to the phone (via Celery, falling back to a direct call) and log
    the event into the Intelligence Hub's proactive_triggers feed so the
    dashboard shows it too."""
    try:
        from tasks import send_dispatch_notification_task
        send_dispatch_notification_task.delay(
            title=title, message=message, priority=priority,
            action_label=action_label, action_url=action_url
        )
    except Exception:
        send_neural_push(title, message, priority, action_label, action_url)

    hub = get_intelligence()
    triggers = dict(hub.get("proactive_triggers", {}))
    triggers[f"{trigger_type}_{int(time.time() * 1000)}"] = {
        "type": trigger_type, "title": title, "message": message,
        "timestamp": time.time(), "priority": priority,
        "action_label": action_label, "action_url": action_url
    }
    # Keep the feed bounded so it doesn't grow forever.
    if len(triggers) > 30:
        oldest = sorted(triggers, key=lambda k: triggers[k]["timestamp"])[:len(triggers) - 30]
        for k in oldest:
            triggers.pop(k, None)
    update_intelligence("proactive_triggers", triggers)


# --- Gmail: new important mail ---
_seen_email_ids = set()
_gmail_initialized = False


def check_gmail_sentinel():
    """Diffs the unread Primary inbox against what's already been seen and
    alerts only on genuinely new mail (never the first scan after boot)."""
    global _gmail_initialized
    from tools.gmail_tool import get_new_unread_emails

    with _lock:
        new_items = get_new_unread_emails(_seen_email_ids, limit=10)
        for item in new_items:
            _seen_email_ids.add(item["id"])
        if len(_seen_email_ids) > 500:
            _seen_email_ids.clear()
            _seen_email_ids.update(i["id"] for i in new_items)

        first_run = not _gmail_initialized
        _gmail_initialized = True

    if first_run:
        return

    for item in new_items:
        _dispatch(
            title=f"New Mail: {item['sender']}",
            message=item["subject"],
            priority=3,
            action_label="Open Gmail",
            action_url="https://mail.google.com/mail/u/0/#inbox",
            trigger_type="GMAIL_NEW"
        )


# --- GitHub: new commits / new issues on tracked repos ---
_github_state = {}
_github_initialized = False


def check_github_sentinel(pulse: list):
    """Diffs commit SHAs and open-issue counts per repo against last cycle."""
    global _github_initialized
    if not isinstance(pulse, list):
        return

    with _lock:
        first_run = not _github_initialized
        _github_initialized = True

        events = []
        for repo in pulse:
            name = repo.get("name")
            if not name:
                continue
            prev = _github_state.get(name)
            sha = repo.get("sha")
            issues = repo.get("issues", 0)
            html_url = repo.get("html_url")

            if prev and not first_run:
                if sha and prev.get("sha") and sha != prev["sha"]:
                    events.append({
                        "title": f"New Commit: {name}",
                        "message": repo.get("last_commit", "Repository updated."),
                        "url": html_url
                    })
                if issues > prev.get("issues", issues):
                    events.append({
                        "title": f"New Issue Opened: {name}",
                        "message": f"Open issue count rose to {issues}.",
                        "url": f"{html_url}/issues" if html_url else None
                    })

            _github_state[name] = {"sha": sha, "issues": issues}

    for ev in events:
        _dispatch(
            title=ev["title"], message=ev["message"], priority=3,
            action_label="View on GitHub", action_url=ev["url"],
            trigger_type="GITHUB_ACTIVITY"
        )


# --- LeetCode: today's scheduled problem still unsolved as the day closes ---
_lc_alert_date = None


async def check_leetcode_deadline():
    """Once per day, after 20:00 local time, nudges if today's scheduled
    placement problem is still unsolved — before the streak breaks at midnight."""
    global _lc_alert_date
    from services.scheduler_service import get_today_scheduled_problem

    now = datetime.now()
    if now.hour < 20:
        return

    today_str = now.strftime("%Y-%m-%d")
    if _lc_alert_date == today_str:
        return

    problem = await get_today_scheduled_problem()
    if not problem or problem.get("completed"):
        return

    _lc_alert_date = today_str
    _dispatch(
        title="Placement Streak at Risk",
        message=f"Sir, '{problem.get('title')}' is still unsolved with the day closing out. Don't let the streak break.",
        priority=4,
        action_label="Solve Now",
        action_url=problem.get("link"),
        trigger_type="LEETCODE_DEADLINE"
    )


# --- Spotify: sustained deep-focus session ---
_spotify_session_start = None
_spotify_alerted = False


def check_spotify_focus(track_data: dict):
    """Reports a sustained 60+ minute uninterrupted listening session — a proxy
    for deep focus — once per session, the way Stark's JARVIS would note
    'you've been at this for an hour, Sir.'"""
    global _spotify_session_start, _spotify_alerted
    status = track_data.get("status") if track_data else None

    with _lock:
        if status == "playing":
            if _spotify_session_start is None:
                _spotify_session_start = time.time()
                _spotify_alerted = False
            elapsed = time.time() - _spotify_session_start
            should_alert = elapsed >= 3600 and not _spotify_alerted
            if should_alert:
                _spotify_alerted = True
        else:
            _spotify_session_start = None
            _spotify_alerted = False
            should_alert = False

    if should_alert:
        _dispatch(
            title="Deep Focus Detected",
            message="Sir, you've been in an uninterrupted listening session for over an hour. Solid focus streak — consider a short break.",
            priority=2,
            trigger_type="FOCUS_SESSION"
        )
