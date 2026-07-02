# Design Decisions: Interview Defense Guide

These are the 6 most likely "why did you choose X over Y" questions this architecture invites, with honest technical justifications grounded in what is actually in the code.

---

## 1. Why Groq over OpenAI (or Gemini, which is what the template used)?

**The short answer:** Token generation speed is the primary bottleneck in a voice assistant, and Groq's LPU hardware closes the gap.

**The honest technical answer:**

The AI Studio template used Gemini. The entire backend was rewritten around Groq for one concrete reason: voice requires a spoken response within 1–2 seconds of the user finishing speaking. The bottleneck is usually not STT (300–600 ms) but LLM generation — GPT-4o generates at roughly 80–100 tokens/sec via the OpenAI API; Groq's `llama-3.3-70b-versatile` runs at ~280–320 tokens/sec on their LPU hardware. A 100-token response (a typical short voice reply) takes ~1.2 seconds on OpenAI and ~0.35 seconds on Groq. That difference matters because the TTS pipeline cannot start until tokens arrive.

A second reason: Groq provides both LLM and Whisper STT in a single API. Using one provider for the full pipeline (Whisper → LLM → Orpheus TTS) means one API key, one rate limit to monitor, and one billing line. The code reflects this — `groq_client` in `voice/stt.py` and `_client` in `voice/tts.py` both use `GROQ_API_KEY`.

The tradeoff: Groq's model selection is smaller than OpenAI's. For vision-based requests the code falls back to `llama-3.2-11b-vision-preview` which is less capable than GPT-4o Vision — this is an acknowledged limitation handled by the vision keyword gate in `core.py`.

---

## 2. Why function-calling over a different routing pattern (intent classification, JSON prompting, or a routing model)?

**The short answer:** The model handles disambiguation; the code doesn't need a separate classification step.

**The honest technical answer:**

Three alternatives were considered:
- **Intent classification model**: a small model first labels the intent, then a handler is called. Adds a second API round-trip and requires a maintained taxonomy of intents.
- **JSON output prompting**: ask the LLM to output `{"tool": "...", "args": {...}}` in its text and parse it with regex. Fragile — models hallucinate field names, and the parsing breaks on nested quotes.
- **Native function-calling** (what is implemented): pass `GROQ_TOOLS` schema to the API; the model emits structured `tool_calls` that the SDK parses. Schema validation happens inside the API call, not in application code.

The code actually implements a hybrid: native function-calling is primary, but `core.py` lines 425–433 add a text-tag fallback parser that catches `<function=name>{args}</function>` patterns. This is not a paranoia measure — some Groq model versions occasionally emit tool calls as text tags instead of native `tool_calls` objects. The fallback means the system degrades gracefully rather than silently dropping tool invocations.

One concrete advantage of function-calling over JSON prompting: `manage_calendar` takes an `action` enum (`"add" | "list" | "delete" | "send_to_phone"`) with optional dependent fields. The schema enforces this structure; the LLM generates valid calls. With JSON prompting you'd need manual validation on every call.

---

## 3. Why Redis? What is it actually caching here?

**The short answer:** Two distinct caching layers that prevent redundant API calls, with a security constraint built into the client.

**The honest technical answer:**

Redis serves two separate purposes in this system:

**Layer 1 — Tool result cache (5-minute TTL):** In `core.py` `run_tool()`, before every tool invocation the code calls `neural_cache.get_tool_result(fn_name, args)`. If a cache hit is found, the API call is skipped. This matters for conversational patterns like "what's my GitHub status" asked twice in a session, or a morning briefing that touches Gmail + LeetCode + GitHub — the second tool invocation within 5 minutes returns in under 5ms instead of making 3 separate API calls. Errors are not cached (the `not res_str.startswith("Error:")` guard on line 479).

**Layer 2 — Conversation history cache (30-minute TTL):** `memory.py` `get_history()` checks `neural_cache.get_semantic_match(cache_key)` before hitting Supabase. On consecutive messages in the same session, history comes from Redis not Postgres. This reduces Supabase read costs and eliminates a 50–200ms DB round-trip on every turn.

**Layer 3 — Celery broker:** Redis also serves as the Celery message broker for background tasks. This is standard Celery configuration, not a custom design decision.

The `redis_service.py` private-network enforcement (RFC1918 check on `REDIS_HOST`) is worth mentioning: if someone accidentally sets `REDIS_HOST` to a public IP (misconfiguration, CI environment variable bleed), the client initializes as `None` and all cache operations silently no-op rather than connecting to an exposed Redis instance.

---

## 4. Why Celery instead of just using asyncio background tasks?

**The short answer:** Celery gives persistent task state, worker isolation, and retry semantics that asyncio tasks don't have — and it degrades gracefully when Redis is unavailable.

**The honest technical answer:**

Looking at what Celery is actually used for in this codebase (`tasks.py`):

- `send_dispatch_notification_task`: fires when the HMAC-signed edge endpoint receives a trigger. This needs to be fast (the edge endpoint returns in milliseconds) and reliable (if the Ntfy push fails, it should retry). An asyncio task would share the FastAPI event loop — if the main process is busy with a long voice turn, the push notification would be delayed.

- `process_stt_task`: runs `transcribe_audio()` in a fresh event loop in a thread. This is needed because Celery workers are synchronous — you cannot `await` in a Celery task body. The explicit `asyncio.new_event_loop()` / `loop.close()` in `_core_stt_logic()` is a direct consequence of this constraint.

The honest caveat: in the current codebase, most real-time voice processing goes through the direct WebSocket path (`ws_neural.py`), not through Celery. Celery's main value here is the mobile push dispatch and the architectural pattern — demonstrating that heavy/retriable background work is isolated from the main event loop. The eager mode fallback (`task_always_eager=True` when Redis is down) means the app works without Redis for Celery while still preserving the `.delay()` call convention.

---

## 5. Why the dual local/cloud STT fallback, and why is this self-healing?

**The short answer:** Cloud STT is faster but can fail; local STT preserves function during outages and handles privacy-sensitive commands. The self-heal removes a class of deployment-environment errors automatically.

**The honest technical answer:**

`voice/stt.py` implements bidirectional fallback, not just "local backup for cloud":

- **Cloud primary (default when `GROQ_API_KEY` is set):** Groq Whisper is faster (~300–600ms for a typical voice command). If it fails (network error, rate limit, 500), the code falls back to local faster-whisper. If local also fails, the function returns `""` and the client gets an error message — it does not throw.

- **Local primary (when `STT_PROVIDER=local` or no API key):** faster-whisper runs first. If it fails (model not downloaded, CUDA error), the code falls back to Groq. This mode is useful for sensitive commands where you don't want audio leaving the machine.

The **CUDA self-heal** (lines 35–41 in `stt.py`) addresses a specific Windows deployment issue: `faster-whisper` detects a GPU but the driver version or ONNX runtime doesn't support it. Rather than crashing the STT system, the code catches the exception and retries with `device="cpu", compute_type="int8"`. This was not over-engineering — it was added after encountering this exact failure on an RTX 3050 Ti laptop with an older cuDNN version.

The `beam_size=1` setting for local transcription is a conscious speed-vs-accuracy tradeoff: beam search with higher widths improves word error rate slightly but adds latency. For short voice commands (3–10 words), beam_size=1 produces acceptable accuracy at lower latency.

---

## 6. Why Supabase over raw PostgreSQL (or SQLite, or just Redis as the store)?

**The short answer:** The async client, hosted infrastructure, and schema-per-table flexibility matched rapid development needs better than managing a Postgres instance or using a schema-less store.

**The honest technical answer:**

This is a case where the honest answer includes tradeoffs:

**Why not SQLite:** conversation history and reminders are shared across sessions (multiple browser tabs, mobile WebSocket connections). SQLite with WAL mode can handle concurrent reads but is not suited for a system where multiple async coroutines write concurrently — `memory.py` has 7+ background workers that write to Supabase simultaneously.

**Why not raw Postgres:** requires running a local Postgres instance, managing connection pooling, and writing raw SQL. Supabase provides a hosted instance plus a generated REST API and the `supabase-py` async client. During rapid development, being able to `supabase.table("skill_mastery").upsert(data, on_conflict="user_id, category").execute()` without writing SQL or managing a migration runner was a real productivity advantage.

**Why not just Redis as the persistent store:** Redis is used for ephemeral caching. If the Redis process restarts, all cached data is lost — that is acceptable for a 5-minute tool result cache. Reminders, calendar events, and conversation history need to survive restarts. Using Redis as primary storage would require RDB/AOF configuration and memory sizing, and would lose the relational query capabilities used in `memory.py` (e.g. the LeetCode streak calculation queries `leetcode_daily` ordered by date with `completed=True` filtering).

**The honest tradeoff:** Supabase is a SaaS dependency. The system will not work without internet access to the Supabase project. A fully offline deployment would need to replace `memory.py` with a local Postgres or SQLite implementation.
