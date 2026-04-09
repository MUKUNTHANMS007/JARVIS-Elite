import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Adjust paths to match project structure
sys.path.append(os.path.join(os.getcwd()))
sys.path.append(os.path.join(os.getcwd(), '..'))

# Import the tools to be tested
from tools.gmail_tool import get_smart_email_notifications
from tools.spotify_tool import search_and_play_spotify, get_spotify_recommendations
from automated_testing.mock_services import get_mock_gmail_service, get_mock_spotify_client

class TestJarvisTools(unittest.TestCase):

    @patch('tools.gmail_tool.get_gmail_service')
    def test_gmail_smart_notifications(self, mock_get_service):
        """Test that get_smart_email_notifications returns correct format."""
        # Setup mock
        mock_get_service.return_value = get_mock_gmail_service()
        
        # Execute
        result = get_smart_email_notifications(limit=1)
        
        # Verify
        self.assertIn("Mukunthan, I've scanned your latest 1 unread messages:", result)
        self.assertIn("SUBJECT: Automated Test", result)
        self.assertIn("SNIPPET: Test snippet", result)

    @patch('tools.spotify_tool.get_spotify_client')
    def test_spotify_search_track(self, mock_get_client):
        """Test that Spotify search returns correct track info."""
        # Setup mock
        mock_get_client.return_value = get_mock_spotify_client()
        
        # Execute
        result = search_and_play_spotify("Mock Query")
        
        # Verify
        self.assertIn("Playing track: Mock Search Results", result)
        self.assertIn("by Search Artist", result)

    @patch('tools.spotify_tool.get_spotify_client')
    def test_spotify_recommendations(self, mock_get_client):
        """Test that Spotify recommendations are formatted properly."""
        # Setup mock
        mock_get_client.return_value = get_mock_spotify_client()
        
        # Execute
        result = get_spotify_recommendations()
        
        # Verify
        self.assertIn("Based on what you're listening to, you might like:", result)
        self.assertIn("Mock Song 1 by Artist A", result)

if __name__ == "__main__":
    unittest.main()
