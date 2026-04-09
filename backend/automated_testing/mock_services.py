import unittest.mock
from unittest.mock import MagicMock

def get_mock_gmail_service():
    """
    Improved Mock Gmail service.
    Follows the Google API client's nested builder pattern strictly.
    This allows testing multiple calls and deeper nesting with realistic chaining.
    """
    mock_service = MagicMock()
    
    # 1. Setup the Chain: service.users().messages().list().execute()
    # Using return_value on each step ensures the chain works like the real library
    mock_list_call = mock_service.users.return_value.messages.return_value.list
    mock_list_call.return_value.execute.return_value = {
        'messages': [{'id': 'msg_123', 'threadId': 'thread_abc'}],
        'resultSizeEstimate': 1
    }

    # 2. Setup the Chain: service.users().messages().get().execute()
    mock_get_call = mock_service.users.return_value.messages.return_value.get
    mock_get_call.return_value.execute.return_value = {
        'snippet': 'Test snippet for automated evaluation.',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Automated Test'},
                {'name': 'From', 'value': 'Tester <test@example.com>'}
            ]
        }
    }
    
    return mock_service

def get_mock_spotify_client(is_playing=True):
    """
    Mock Spotify client with toggleable playback state.
    Handles the 'None' case for Inactive status (204 No Content simulation).
    """
    mock_sp = MagicMock()
    
    # Mock current playing (Handle the 'None' case for Inactive status)
    if not is_playing:
        mock_sp.current_user_playing_track.return_value = None
    else:
        mock_sp.current_user_playing_track.return_value = {
            'is_playing': True,
            'item': {
                'id': 'spotify_track_id',
                'name': 'Mockingbird',
                'artists': [{'name': 'Eminem'}],
                'album': {'name': 'Curtain Call'}
            }
        }

    # Mock Search Results
    mock_sp.search.return_value = {
        'tracks': {
            'items': [{
                'uri': 'spotify:track:mock', 
                'name': 'Mock Search Results', 
                'artists': [{'name': 'Search Artist'}]
            }]
        },
        'playlists': {'items': []},
        'albums': {'items': []}
    }
    
    # Mock Recommendations
    mock_sp.recommendations.return_value = {
        'tracks': [
            {'name': 'Mock Song 1', 'artists': [{'name': 'Artist A'}]},
            {'name': 'Mock Song 2', 'artists': [{'name': 'Artist B'}]}
        ]
    }
    
    return mock_sp
