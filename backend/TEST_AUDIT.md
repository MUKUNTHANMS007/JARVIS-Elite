# Test Suite Audit

**Actual count:** 24 test functions, 18 subtests = 42 as reported by pytest + subtest plugin.  
**Result:** 24 passed, 0 failed (verified 2026-06-28).

This audit categorizes each test honestly so you can describe what is actually tested if an interviewer asks.

---

## Meaningful Tests (test real logic, edge cases, or failure modes)

### test_agent_routing.py

**`test_all_expected_tools_present`**  
Asserts that 13 specific tool names are present in `GROQ_TOOLS`. This is a regression guard — if you rename or delete a tool during refactoring, this test fails immediately instead of you discovering it when the LLM starts returning "tool not found" errors at runtime.

**`test_each_tool_has_required_schema_fields`** *(13 subtests)*  
For every entry in `GROQ_TOOLS`, validates that `type == "function"`, and that `function.name`, `function.description`, and `function.parameters` are present and non-empty. A missing `description` or wrong `type` would cause a Groq API 400 error at runtime but would be completely silent in local dev since the dict is just Python.

**`test_tool_names_are_unique`**  
Checks for duplicate names in `GROQ_TOOLS`. Groq's API rejects schemas with duplicate function names, and this is easy to introduce when adding tools quickly. The test catches this before it hits the API.

**`test_required_fields_are_lists`** *(5 subtests — tools with `required` arrays)*  
Verifies that where a `required` key exists in a tool's parameter schema, it is a `list` not a `str`. A `required: "context_uri"` (string) passes Python construction but causes schema validation failures at the Groq API.

---

### test_parallel_system.py

**`test_dashboard_parallelism`** *(most valuable test in the suite)*  
Uses `time.perf_counter()` to mathematically verify that the dashboard endpoint (`/api/routine`) runs Spotify and database fetches in parallel. The test configures Spotify to take 0.4s and the DB to take 0.1s, then asserts that the DB call *starts before* Spotify ends (`db_start < spotify_end`). If someone converts `asyncio.gather()` to sequential `await` calls, this test fails. This tests a real performance property — not just "it runs."

**`test_error_isolation`**  
Injects a `401 Unauthorized` exception from the Spotify mock and verifies that the dashboard still returns a valid response with `spotify_status == "Inactive"`. Tests the `safe_fetch()` wrapper behavior — one failing service must not prevent other services from loading.

**`test_tts_speech_modes`**  
Tests all three TTS buffering modes (`sentence`, `entire`, `chunk`) by tracking what text gets put into the TTS queue during a full agent run. In `sentence` mode, verifies the exact sentences produced by the tokenizer ("Hello, Sir." and "I have generated a briefing which has stats." as two separate queue items). In `entire` mode, verifies the full text is queued as one item. This directly tests the sentence-boundary detection logic in `run_agent()`.

**`test_neural_link_stability`**  
Simulates a client WebSocket disconnecting (`client_state.name = "DISCONNECTED"`) mid-stream and verifies that `bridge_tts_worker` exits cleanly without raising an unhandled exception. Tests the resilience guard on line 83 of `ws_neural.py`.

---

### test_tts_system.py

**`test_tts_service_cache_flow`**  
End-to-end cache test: calls `TTSService.generateSpeech()` twice on the same text, verifies the first call writes a file to disk, then overwrites the file with known bytes, and verifies the second call returns those cached bytes without re-synthesizing. Tests two distinct behaviors: write-on-miss and read-on-hit.

**`test_audio_cache_hashing`**  
Tests two specific properties of `AudioCache.get_hash()`: (1) whitespace and casing normalization — `"Test cache normalization string."` and `"  Test cache   normalization  string.  "` produce the same hash; (2) provider isolation — changing `provider` from `"kokoro"` to `"edge"` produces a different hash. Catches regressions in cache key generation.

**`test_api_tts_stream_endpoint`**  
Integration test against the `/api/tts/stream` FastAPI endpoint via `TestClient`. Mocks `TTSService.streamSpeech` to yield two known chunks and verifies the streaming response concatenates them correctly. Tests the streaming response path, not just the controller.

---

### test_voice_pipeline.py

**`test_synthesize_speech_stream_prefers_groq`**  
Patches both Groq and edge-tts, makes Groq return audio, and asserts that `edge_mock.assert_not_called()`. Verifies the priority ordering: when Groq works, edge-tts is never invoked.

**`test_synthesize_speech_stream_falls_back_to_edge`**  
Makes Groq return `None` and verifies that edge-tts output (`b"edge-mp3"`) is what gets yielded. Tests the critical fallback path.

**`test_run_audio_turn_emits_transcription_and_dispatches_agent`**  
Patches `transcribe_audio` to return `"Hello Sir"` and asserts two things in order: (1) `send_json` is called with `{"type": "TRANSCRIPTION", "text": "Hello Sir"}`, (2) `run_agent` is called with the transcribed text. Verifies the exact contract between the audio turn handler and both the WebSocket emitter and the agent dispatcher.

**`test_voice_websocket_accepts_text_and_audio_messages`**  
Integration test: opens a WebSocket connection against a test FastAPI app and sends three messages — a `text_input`, an `audio_input`, and a legacy `AUDIO_START`. Verifies that `run_agent` is called for text, `run_audio_turn` is called for both audio types, that the `audio_input` MIME type is preserved from the message (`audio/webm`) while `AUDIO_START` defaults to `audio/mp4`, and that the decoded audio bytes are correct. This tests the message routing logic in the main `while` loop of `voice_endpoint()`.

---

## Decorative / Trivial Tests

These tests pass trivially and provide limited confidence. They are not worthless — they document behavior and catch crashes — but an interviewer asking "what does this test verify?" would get an unimpressive answer.

### test_agent_routing.py

**`test_groq_tools_is_nonempty_list`**  
Asserts `isinstance(GROQ_TOOLS, list)` and `len > 0`. This would only fail if someone replaced the list with `None` or `[]`. Effectively a module-import smoke test.

---

### test_tools_logic.py

**`test_gmail_smart_notifications_returns_string`**  
Asserts the function returns a non-empty string. Since `get_smart_email_notifications` has a fallback string for every error path (Gemini unavailable, Gmail service unavailable, etc.), this would pass even if the real API is completely broken. Does not verify any meaningful behavior.

**`test_gmail_returns_auth_error_when_no_service`**  
Passes `None` as the Gmail service and asserts the result is a non-empty string. Tests that the function doesn't crash on `None`, which is a very low bar.

**`test_spotify_search_track`** and **`test_spotify_recommendations_format`**  
Test that the return string contains expected substrings (`"Playing track:"`, `"Mock Search Results"`, `"Mock Song 1"`). Since all values come from the hardcoded mock, these are format regression tests. They would catch if someone changed the output format string but would not catch any actual Spotify API contract issues.

---

### test_tts_system.py

**`test_api_tts_voices_endpoint`**  
Hits `/api/tts/voices` and checks `response.status_code == 200` and that `"kokoro"` and `"edge"` are keys in the response. Does not test any voice quality or synthesis logic.

**`test_api_tts_post_endpoint`**  
Mocks `generateSpeech` and checks that the response JSON has the expected keys (`audio_url`, `cache_key`, `format`, `size_bytes`). Tests the response schema, not the synthesis pipeline.

---

### test_voice_pipeline.py

**`test_groq_client_disables_sdk_retries_for_tts`**  
Asserts `Groq(api_key="test-key", max_retries=0)` is how the client is constructed. This verifies a constructor call with a specific argument. The reason `max_retries=0` matters is that automatic SDK retries would add multi-second delays on TTS failures — but this test verifies the constructor argument, not the actual latency behavior.

---

## Summary Table

| Test | File | Meaningful? | Why |
|------|------|-------------|-----|
| `test_all_expected_tools_present` | routing | Yes | Regression guard on tool registry |
| `test_each_tool_has_required_schema_fields` | routing | Yes | Catches runtime API schema errors early |
| `test_tool_names_are_unique` | routing | Yes | Prevents Groq schema rejection |
| `test_required_fields_are_lists` | routing | Yes | Type contract for Groq API |
| `test_groq_tools_is_nonempty_list` | routing | No | Trivial smoke test |
| `test_dashboard_parallelism` | parallel | Yes | Proves parallel execution mathematically |
| `test_error_isolation` | parallel | Yes | Tests resilience on service failure |
| `test_tts_speech_modes` | parallel | Yes | Tests sentence-splitting logic |
| `test_neural_link_stability` | parallel | Yes | Tests disconnect graceful exit |
| `test_gmail_smart_notifications_returns_string` | tools | No | Trivial — fallback always passes |
| `test_gmail_returns_auth_error_when_no_service` | tools | No | Just tests no-crash on None |
| `test_spotify_search_track` | tools | Partial | Format regression only |
| `test_spotify_recommendations_format` | tools | Partial | Format regression only |
| `test_audio_cache_hashing` | tts | Yes | Tests normalization + isolation |
| `test_tts_service_cache_flow` | tts | Yes | Tests write-on-miss, read-on-hit |
| `test_api_tts_voices_endpoint` | tts | No | Schema check only |
| `test_api_tts_post_endpoint` | tts | No | Response key check only |
| `test_api_tts_stream_endpoint` | tts | Partial | Tests streaming path, not synthesis |
| `test_groq_client_disables_sdk_retries_for_tts` | voice | No | Constructor arg assertion |
| `test_synthesize_speech_stream_prefers_groq` | voice | Yes | Verifies priority ordering |
| `test_synthesize_speech_stream_falls_back_to_edge` | voice | Yes | Tests critical fallback path |
| `test_speak_route_returns_audio_response` (not shown above) | voice | Partial | HTTP contract only |
| `test_run_audio_turn_emits_transcription_and_dispatches_agent` | voice | Yes | Verifies exact event + dispatch contract |
| `test_voice_websocket_accepts_text_and_audio_messages` | voice | Yes | Integration: routing + MIME + byte correctness |
