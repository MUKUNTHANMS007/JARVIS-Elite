# JARVIS Automated Test Report
Generated: 2026-06-12 21:04:35
------------------------------------------------------------
## Summary
- **Tests Run**: 5
- **Failures**: 2
- **Errors**: 2
- **Status**: FAILED

## Details
### Failures
- **test_gmail_smart_notifications (test_tools_logic.TestJarvisTools.test_gmail_smart_notifications)**: Traceback (most recent call last):
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1387, in patched
    return func(*newargs, **newkeywargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\JARVIS\backend\automated_testing\test_tools_logic.py", line 27, in test_gmail_smart_notifications
    self.assertIn("Mukunthan, I've scanned your latest 1 unread messages:", result)
AssertionError: "Mukunthan, I've scanned your latest 1 unread messages:" not found in "GREETING| I've scanned your primary communication layer, Sir.\nITEM| STATUS | No Urgent Updates Found\nITEM| INBOX | Primary Tab Pristine"

- **test_spotify_search_track (test_tools_logic.TestJarvisTools.test_spotify_search_track)**: Traceback (most recent call last):
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1387, in patched
    return func(*newargs, **newkeywargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\JARVIS\backend\automated_testing\test_tools_logic.py", line 42, in test_spotify_search_track
    self.assertIn("by Search Artist", result)
AssertionError: 'by Search Artist' not found in 'Playing track: Mock Search Results on your PC, Sir.'

### Errors
- **test_agent_routing (unittest.loader._FailedTest.test_agent_routing)**: ImportError: Failed to import test module: test_agent_routing
Traceback (most recent call last):
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 394, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 337, in _get_module_from_name
    __import__(name)
  File "d:\JARVIS\backend\automated_testing\test_agent_routing.py", line 8, in <module>
    from agent.core import get_tool_subset, GROQ_TOOLS
ImportError: cannot import name 'get_tool_subset' from 'agent.core' (D:\JARVIS\backend\agent\core.py)


- **test_parallel_system (unittest.loader._FailedTest.test_parallel_system)**: ImportError: Failed to import test module: test_parallel_system
Traceback (most recent call last):
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 394, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mukunthan\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 337, in _get_module_from_name
    __import__(name)
  File "d:\JARVIS\backend\automated_testing\test_parallel_system.py", line 5, in <module>
    from main import dashboard # Import the optimized dashboard logic from main.py
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
ImportError: cannot import name 'dashboard' from 'main' (D:\JARVIS\backend\main.py)


