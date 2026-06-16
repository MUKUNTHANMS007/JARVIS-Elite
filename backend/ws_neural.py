import asyncio
import json
import uuid
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
from agent.core import get_agent_response_stream
from services.cache_service import get_intelligence, update_intelligence
from voice.tts import synthesize_speech_stream

router = APIRouter()

BATMAN_TRIGGER = "gotham needs batman"
BATMAN_DEACTIVATE = "gotham is safe now"

# TTS speech mode config: sentence (default), entire, or chunk (legacy)
TTS_SPEECH_MODE = os.getenv("TTS_SPEECH_MODE", "sentence").lower()


# --- Tag Stripper Stream ---
async def strip_function_tags_stream(async_gen):
    buffer = ""
    async for chunk in async_gen:
        buffer += chunk
        while True:
            tag_start = buffer.find("<function=")
            if tag_start == -1:
                possible_idx = -1
                for i in range(len(buffer) - 1, max(-1, len(buffer) - 11), -1):
                    sub = buffer[i:]
                    if "<function=".startswith(sub):
                        possible_idx = i
                        break
                if possible_idx != -1:
                    if possible_idx > 0:
                        yield buffer[:possible_idx]
                        buffer = buffer[possible_idx:]
                    break
                else:
                    yield buffer
                    buffer = ""
                    break
            else:
                if tag_start > 0:
                    yield buffer[:tag_start]
                    buffer = buffer[tag_start:]
                
                tag_end = buffer.find("</function>")
                if tag_end == -1:
                    break
                else:
                    buffer = buffer[tag_end + len("</function>"):]
    if buffer:
        yield buffer


# --- TTS Bridge Worker ---
async def bridge_tts_worker(client_id: str, queue: asyncio.Queue):
    """Feeds audio chunks to client with safety guards."""
    while True:
        try:
            sentence = await queue.get()
            if sentence is None:
                break
            async for fragment in synthesize_speech_stream(sentence.strip()):
                if fragment:
                    await manager.send_bytes(client_id, fragment)
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[TTS Worker Error] {e}")
            break


# --- Agent Pipeline ---
async def run_agent(
    client_id: str,
    text: str,
    image: str | None,
) -> None:
    """
    Run the LLM and stream TEXT_CHUNK events to the client.
    """
    normalised = "".join(c for c in text.lower() if c.isalnum() or c.isspace())

    if BATMAN_TRIGGER.replace(" ", "") in normalised.replace(" ", ""):
        reply = (
            "Shadow Protocol active. Master Wayne, the terminal is at your "
            "command. Access level: Sigma-9."
        )
        try:
            update_intelligence("batman_mode", True)
        except Exception as exc:
            print(f"[Agent] update_intelligence error: {exc}")

        await _send_turn(client_id, reply)
        return

    if BATMAN_DEACTIVATE.replace(" ", "") in normalised.replace(" ", ""):
        reply = "Standby mode restored. Hello, Sir. J.A.R.V.I.S. is back online."
        try:
            update_intelligence("batman_mode", False)
        except Exception as exc:
            print(f"[Agent] update_intelligence error: {exc}")

        await _send_turn(client_id, reply)
        return

    await manager.send_json(client_id, {"type": "TURN_START"})
    tts_queue = asyncio.Queue()
    tts_task = asyncio.create_task(bridge_tts_worker(client_id, tts_queue))

    # Support runtime environment overrides for the TTS mode
    speech_mode = os.getenv("TTS_SPEECH_MODE", TTS_SPEECH_MODE).lower()

    sentence_buffer = ""
    token_count = 0
    first_chunk = True

    try:
        async for token in strip_function_tags_stream(get_agent_response_stream(text, image_base64=image)):
            ws = manager.active.get(client_id)
            if ws is None or ws.client_state.name != "CONNECTED":
                return

            await manager.send_json(client_id, {"type": "TEXT_CHUNK", "text": token})
            sentence_buffer += token
            token_count += 1

            if speech_mode == "entire":
                # Wait until LLM has finished streaming completely before feeding TTS
                continue

            elif speech_mode == "chunk":
                # Legacy 4-6 token micro-chunking logic
                is_punctuation = any(sentence_buffer.endswith(p) for p in [". ", "? ", "! ", "\n", ", ", "; "])
                threshold = 6 if first_chunk else 4
                if is_punctuation or token_count >= threshold:
                    clean = sentence_buffer.strip()
                    if len(clean) > 1:
                        await tts_queue.put(clean)
                        first_chunk = False
                        sentence_buffer = ""
                        token_count = 0

            else:
                # Optimized 'sentence' mode
                is_boundary = False
                # Split at actual sentence terminators followed by a space/newline
                if any(sentence_buffer.endswith(p) for p in [". ", "? ", "! ", "\n", ".\n", "?\n", "!\n"]):
                    is_boundary = True
                # Pause at commas/semicolons only if the chunk has enough length to sound natural
                elif token_count >= 15 and any(sentence_buffer.endswith(p) for p in [", ", "; ", " - ", "—"]):
                    is_boundary = True
                # Run-on fallback to prevent infinite delay on long prose or code lists
                elif token_count >= 25 and token.isspace():
                    is_boundary = True

                if is_boundary:
                    clean = sentence_buffer.strip()
                    if len(clean) > 1:
                        await tts_queue.put(clean)
                        first_chunk = False
                        sentence_buffer = ""
                        token_count = 0

        if sentence_buffer.strip():
            await tts_queue.put(sentence_buffer.strip())

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"[Agent] Error for {client_id}: {exc}")
    finally:
        await tts_queue.put(None)
        try:
            await tts_task
        except Exception:
            pass
        ws = manager.active.get(client_id)
        if ws is not None and ws.client_state.name == "CONNECTED":
            await manager.send_json(client_id, {"type": "TURN_COMPLETE"})


async def _send_turn(
    client_id: str,
    reply: str,
) -> None:
    """Send a single-reply turn with TTS (used for Batman-mode shortcuts)."""
    await manager.send_json(client_id, {"type": "TURN_START"})
    await manager.send_json(client_id, {"type": "TEXT_CHUNK", "text": reply})

    tts_queue: asyncio.Queue = asyncio.Queue()
    tts_task = asyncio.create_task(bridge_tts_worker(client_id, tts_queue))
    await tts_queue.put(reply)
    await tts_queue.put(None)
    try:
        await tts_task
    except Exception:
        pass

    ws = manager.active.get(client_id)
    if ws is not None and ws.client_state.name == "CONNECTED":
        await manager.send_json(client_id, {"type": "TURN_COMPLETE"})


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket) -> None:
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    voice_task: asyncio.Task | None = None

    async def cancel_voice_task() -> None:
        nonlocal voice_task
        if voice_task and not voice_task.done():
            voice_task.cancel()
            try:
                await voice_task
            except (asyncio.CancelledError, Exception):
                pass
        voice_task = None

    try:
        while websocket.client_state.name == "CONNECTED":
            try:
                data = await asyncio.wait_for(websocket.receive(), timeout=60)
            except asyncio.TimeoutError:
                if websocket.client_state.name == "CONNECTED":
                    await manager.send_json(client_id, {"type": "PING"})
                continue
            except (WebSocketDisconnect, RuntimeError):
                break

            if "text" in data:
                try:
                    msg = json.loads(data["text"])
                except json.JSONDecodeError:
                    continue

                m_type = msg.get("type")

                if m_type == "PONG":
                    continue

                elif m_type == "text_input":
                    text = msg.get("text", "").strip()
                    if not text:
                        continue
                    image = msg.get("image")
                    await cancel_voice_task()
                    voice_task = asyncio.create_task(
                        run_agent(client_id, text, image)
                    )

    except WebSocketDisconnect as exc:
        print(f"[Neural Link] Client {client_id} disconnected (code {exc.code}).")
        manager.disconnect(client_id, reason=f"WebSocketDisconnect({exc.code})")
    except Exception as exc:
        print(f"[Neural Link] Runtime error for {client_id}: {exc}")
        manager.disconnect(client_id, reason=f"RuntimeError: {exc}")
    finally:
        await cancel_voice_task()
        if client_id in manager.active:
            manager.disconnect(client_id, reason="Session ended")
