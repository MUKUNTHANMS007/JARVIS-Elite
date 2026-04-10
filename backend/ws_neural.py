import asyncio, json, uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws_manager import manager
from voice.stt import transcribe_audio
from voice.tts import synthesize_speech_stream
from agent.core import get_agent_response_stream
from services.cache_service import get_intelligence, update_intelligence

router = APIRouter()

BATMAN_TRIGGER = "gotham needs batman"
BATMAN_DEACTIVATE = "gotham is safe now"

# --- TTS Worker ---
async def tts_worker(client_id: str, queue: asyncio.Queue):
    while True:
        try:
            sentence = await asyncio.wait_for(queue.get(), timeout=30)
            if sentence is None:
                break
            ws = manager.active.get(client_id)
            if not ws or ws.client_state.name != "CONNECTED":
                break
            async for fragment in synthesize_speech_stream(sentence.strip()):
                await manager.send_bytes(client_id, fragment)
            queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"[TTS Worker] {client_id}: {e}")

# --- Agent Pipeline ---
async def run_agent(client_id: str, text: str, image: str, tts_queue: asyncio.Queue):
    try:
        msg_lower = text.lower().strip()
        is_activation = BATMAN_TRIGGER in msg_lower
        is_deactivation = BATMAN_DEACTIVATE in msg_lower

        if is_activation or is_deactivation:
            new_state = is_activation
            update_intelligence("batman_mode", new_state)
            
            if new_state:
                reply = "Shadow Protocol active. Master Wayne, the terminal is at your command. Access level: Sigma-9."
            else:
                reply = "Standby mode restored. Hello, Sir. J.A.R.V.I.S. is back online."
            
            await manager.send_json(client_id, {"type": "TURN_START"})
            await manager.send_json(client_id, {"type": "TEXT_CHUNK", "text": reply})
            await tts_queue.put(reply)
            await manager.send_json(client_id, {"type": "TURN_COMPLETE"})
            return

        await manager.send_json(client_id, {"type": "TURN_START"})

        buffer = ""
        token_count = 0
        first_chunk = True

        async for token in get_agent_response_stream(text, image_base64=image):
            ws = manager.active.get(client_id)
            if not ws or ws.client_state.name != "CONNECTED":
                break

            await manager.send_json(client_id, {"type": "TEXT_CHUNK", "text": token})
            buffer += token
            token_count += 1

            # --- RAPID RESPONSE PROTOCOL ---
            # Fast-track the first chunk for sub-2s TTFB.
            # Subsequent chunks use a slightly larger buffer for better prosody.
            threshold = 4 if first_chunk else 12
            
            # Split on major punctuation to get fragments out even faster
            is_fragment_end = any(buffer.endswith(p) for p in [", ", "; ", ": ", " - "])
            is_sentence_end = any(buffer.endswith(p) for p in [". ", "? ", "! ", "\n"])

            if is_sentence_end or is_fragment_end or token_count >= threshold:
                clean = buffer.strip()
                if len(clean) > 2:
                    await tts_queue.put(clean)
                    first_chunk = False
                buffer = ""
                token_count = 0

        if buffer.strip():
            await tts_queue.put(buffer.strip())

    except Exception as e:
        print(f"[Agent] Error for {client_id}: {e}")
    finally:
        ws = manager.active.get(client_id)
        if ws and ws.client_state.name == "CONNECTED":
            await manager.send_json(client_id, {"type": "TURN_COMPLETE"})

# --- Main Voice WebSocket ---
@router.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)

    tts_queue: asyncio.Queue = asyncio.Queue()
    worker = asyncio.create_task(tts_worker(client_id, tts_queue))

    audio_buffer = bytearray()
    image_data = None

    try:
        while websocket.client_state.name == "CONNECTED":
            try:
                # Use a combined wait for receive and state check
                data = await asyncio.wait_for(websocket.receive(), timeout=60)
            except asyncio.TimeoutError:
                if websocket.client_state.name == "CONNECTED":
                    await manager.send_json(client_id, {"type": "PING"})
                continue
            except (WebSocketDisconnect, RuntimeError):
                break

            if "bytes" in data:
                audio_buffer.extend(data["bytes"])

            elif "text" in data:
                msg = json.loads(data["text"])
                m_type = msg.get("type")

                if m_type == "PONG":
                    continue

                elif m_type == "AUDIO_START":
                    image_data = msg.get("image")
                    audio_buffer.clear()

                elif m_type == "stop_recording":
                    captured = bytes(audio_buffer)
                    audio_buffer.clear()

                    async def process_voice(audio: bytes):
                        try:
                            text = await transcribe_audio(audio)
                            if text:
                                await manager.send_json(client_id, {
                                    "type": "TRANSCRIPTION",
                                    "text": text
                                })
                                await run_agent(client_id, text, image_data, tts_queue)
                            else:
                                await manager.send_json(client_id, {"type": "TURN_COMPLETE"})
                        except Exception as e:
                            print(f"[Voice] Processing error: {e}")
                            await manager.send_json(client_id, {"type": "ERROR", "message": str(e)})

                    asyncio.create_task(process_voice(captured))

                elif m_type == "text_input":
                    text = msg.get("text", "").strip()
                    image = msg.get("image") or image_data
                    if text:
                        asyncio.create_task(run_agent(client_id, text, image, tts_queue))

    except WebSocketDisconnect:
        print(f"[Neural Link] Client {client_id} disconnected cleanly.")
    except Exception as e:
        print(f"[Neural Link] Runtime error for {client_id}: {e}")
    finally:
        await tts_queue.put(None)
        worker.cancel()
        manager.disconnect(client_id)
