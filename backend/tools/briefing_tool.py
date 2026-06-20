import time
import re
from services.cache_service import get_intelligence

async def generate_morning_briefing() -> str:
    """
    JARVIS Elite Hub: Aggregates synchronized metrics for the multi-vector executive summary.
    Includes LeetCode solves/streaks, GitHub commits, Gmail unreads, and live focus score.
    """
    try:
        intel = get_intelligence()

        # 1. LeetCode Analysis
        lc = intel.get("leetcode", {})
        lc_solved = lc.get("total_solved", 0)
        lc_streak = lc.get("streak", 0)
        lc_msg = f"solved {lc_solved} problems with a {lc_streak}-day streak" if lc_solved > 0 else "awaiting today's solve"

        # 2. GitHub Pulse
        gh = intel.get("github", [])
        gh_count = len(gh)
        gh_msg = f"monitored {gh_count} active repositories" if gh_count > 0 else "repositories are stable"

        # 3. Gmail Inbox
        mail_unread = intel.get("gmail_unread", 0)
        unread_count = 0
        if isinstance(mail_unread, int):
            unread_count = mail_unread
        elif isinstance(mail_unread, str):
            m = re.search(r'(\d+)', mail_unread)
            unread_count = int(m.group(1)) if m else 0

        mail_msg = f"{unread_count} unread primary emails" if unread_count > 0 else "no pending primary emails"

        # 4. Neural Focus — fetch live data instead of using a hardcoded placeholder.
        focus_score = None
        try:
            from services.focus_service import get_focus_session_data
            focus_data = await get_focus_session_data()
            if focus_data:
                focus_score = focus_data.get("goal_met") or focus_data.get("focus_score")
        except Exception:
            pass

        if focus_score is not None:
            focus_msg = f"Your current neural focus score is {focus_score}%."
        else:
            focus_msg = "Focus data is currently syncing."

        return (
            f"Morning Protocol active, Sir. Status: You have {lc_msg}, "
            f"{gh_msg}, and {mail_msg}. {focus_msg}"
        )

    except Exception as e:
        return f"Sir, I encountered a drift in the briefing hub: {str(e)}"
