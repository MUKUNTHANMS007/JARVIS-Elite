import unittest
import sys
import os

# Adjust paths
sys.path.append(os.getcwd())

from agent.core import get_tool_subset, GROQ_TOOLS

class TestAgentRouting(unittest.TestCase):

    def test_routing_gmail(self):
        """Test that Gmail keywords trigger Gmail tools."""
        subset = get_tool_subset("Check my email")
        # Gmail tools are at indices 0, 1, 2
        tool_names = [t['function']['name'] for t in subset]
        self.assertIn("check_gmail_inbox", tool_names)
        self.assertIn("get_gmail_briefing", tool_names)
        self.assertIn("get_smart_email_notifications", tool_names)

    def test_routing_spotify(self):
        """Test that Spotify keywords trigger Spotify tools."""
        subset = get_tool_subset("Play some music on Spotify")
        # Spotify tools are at indices 3:11
        tool_names = [t['function']['name'] for t in subset]
        self.assertIn("start_spotify_playback", tool_names)
        self.assertIn("get_current_playback_info", tool_names)
        self.assertIn("search_and_play_spotify", tool_names)
        self.assertIn("get_spotify_recommendations", tool_names)

    def test_routing_reminder(self):
        """Test that reminder keywords trigger reminder tools."""
        subset = get_tool_subset("Remind me to buy milk")
        # Reminder tools are at the end (indices 11:)
        tool_names = [t['function']['name'] for t in subset]
        self.assertIn("set_reminder", tool_names)
        self.assertIn("get_active_reminders", tool_names)

    def test_routing_fallback(self):
        """Test that unrelated prompts return all tools as fallback."""
        subset = get_tool_subset("Hello")
        self.assertEqual(len(subset), len(GROQ_TOOLS))

if __name__ == "__main__":
    unittest.main()
