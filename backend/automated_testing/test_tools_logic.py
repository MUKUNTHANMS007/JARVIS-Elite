import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Adjust paths to match project structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the tools to be tested
from tools.gmail_tool import get_smart_email_notifications
from tools.spotify_tool import search_and_play_spotify, get_spotify_recommendations
from automated_testing.mock_services import get_mock_gmail_service, get_mock_spotify_client


class TestJarvisTools(unittest.TestCase):

    @patch('tools.gmail_tool.get_gmail_service')
    def test_gmail_smart_notifications_returns_string(self, mock_get_service):
        """
        get_smart_email_notifications must return a non-empty string.
        The exact text depends on Gemini availability; we test structural invariants only.
        The function delegates to get_jarvis_email_briefing() which calls Gemini or returns
        a GREETING|-prefixed fallback — both are valid string responses.
        """
        mock_get_service.return_value = get_mock_gmail_service()

        result = get_smart_email_notifications(limit=1)

        self.assertIsInstance(result, str, "Result must be a string")
        self.assertGreater(len(result.strip()), 0, "Result must not be empty")

    @patch('tools.gmail_tool.get_gmail_service')
    def test_gmail_returns_auth_error_when_no_service(self, mock_get_service):
        """When Gmail service is unavailable, the function returns a meaningful error string."""
        mock_get_service.return_value = None

        result = get_smart_email_notifications(limit=1)

        self.assertIsInstance(result, str)
        # The function returns a GREETING|-formatted fallback when not authenticated
        self.assertGreater(len(result.strip()), 0)

    @patch('tools.spotify_tool.get_spotify_client')
    def test_spotify_search_track(self, mock_get_client):
        """Test that Spotify search returns a string containing the track name."""
        mock_get_client.return_value = get_mock_spotify_client()

        result = search_and_play_spotify("Mock Query")

        # Current format: "Playing track: <name> on your PC, Sir."
        self.assertIn("Playing track:", result)
        self.assertIn("Mock Search Results", result)

    @patch('tools.spotify_tool.get_spotify_client')
    def test_spotify_recommendations_format(self, mock_get_client):
        """Test that Spotify recommendations return a correctly formatted string."""
        mock_get_client.return_value = get_mock_spotify_client()

        result = get_spotify_recommendations()

        # Current format starts with this header line
        self.assertIn("Based on what you're listening to, you might like:", result)
        self.assertIn("Mock Song 1", result)
        self.assertIn("Artist A", result)


if __name__ == "__main__":
    unittest.main()
