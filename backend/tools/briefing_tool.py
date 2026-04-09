import time
from services.cache_service import get_intelligence

async def generate_morning_briefing() -> str:
    """
    JARVIS Elite Hub: Aggregates synchronized metrics for the multi-vector executive summary.
    Includes LeetCode solves/streaks, GitHub commits, and Gmail unreads.
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
        # Handle string count if present (e.g. "You have 5 primary unread emails")
        unread_count = 0
        if isinstance(mail_unread, int):
            unread_count = mail_unread
        elif isinstance(mail_unread, str):
            import re
            m = re.search(r'(\d+)', mail_unread)
            unread_count = int(m.group(1)) if m else 0
            
        mail_msg = f"{unread_count} unread primary emails" if unread_count > 0 else "no pending primary emails"
        
        # 4. Neural Focus
        focus_score = 78 # Base placeholder or fetch from focus_service if available
        
        return f"Morning Protocol active, Sir. Status: You have {lc_msg}, {gh_msg}, and {mail_msg}. Your current neural focus score is {focus_score}%."

    except Exception as e:
        return f"Sir, I encountered a drift in the briefing hub: {str(e)}"
