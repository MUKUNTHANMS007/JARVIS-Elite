import asyncio
import base64
import json
import os
import sys
import threading
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))


def test_groq_client_disables_sdk_retries_for_tts():
    from voice import tts

    original_client = tts._client
    tts._client = None

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "GROQ_TTS_MAX_RETRIES": "0"}), \
         patch("voice.tts.Groq", autospec=True) as groq_cls:
        tts._get_groq_client()

    groq_cls.assert_called_once_with(api_key="test-key", max_retries=0)
    tts._client = original_client


@pytest.mark.asyncio
async def test_synthesize_speech_stream_prefers_groq():
    from voice import tts

    wav_bytes = b"wav-bytes"

    with patch("voice.tts._get_groq_client", return_value=object()), \
         patch("voice.tts._synthesize_groq", new=AsyncMock(return_value=wav_bytes)), \
         patch("voice.tts._wav_to_pcm", return_value=b"pcm-bytes"), \
         patch("voice.tts._synthesize_edge", new=AsyncMock(return_value=b"edge-bytes")) as edge_mock:

        result = [chunk async for chunk in tts.synthesize_speech_stream("Hello there.")]

    assert result == [b"pcm-bytes"]
    edge_mock.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_speech_stream_falls_back_to_edge():
    from voice import tts

    with patch("voice.tts._get_groq_client", return_value=object()), \
         patch("voice.tts._synthesize_groq", new=AsyncMock(return_value=None)), \
         patch("voice.tts._synthesize_edge", new=AsyncMock(return_value=b"edge-mp3")):

        result = [chunk async for chunk in tts.synthesize_speech_stream("Hello there.")]

    assert result == [b"edge-mp3"]


def test_speak_route_returns_audio_response():
    from routers.voice import router as voice_router

    app = FastAPI()
    app.include_router(voice_router, prefix="/api/voice")

    with patch("routers.voice.synthesize_speech_payload", new=AsyncMock(return_value=(b"audio", "audio/mpeg"))):
        with TestClient(app) as client:
            response = client.post("/api/voice/speak", json={"text": "Hello"})

    assert response.status_code == 200
    assert response.content == b"audio"
    assert response.headers["content-type"].startswith("audio/mpeg")


@pytest.mark.asyncio
async def test_run_audio_turn_emits_transcription_and_dispatches_agent():
    from ws_neural import run_audio_turn, manager

    send_json_mock = AsyncMock()
    run_agent_mock = AsyncMock()

    with patch("ws_neural.transcribe_audio", new=AsyncMock(return_value="Hello Sir")), \
         patch.object(manager, "send_json", send_json_mock), \
         patch("ws_neural.run_agent", run_agent_mock):

        await run_audio_turn("test-client", b"audio-bytes", "audio/webm", image="frame-data", file_name="voice.webm")

    send_json_mock.assert_awaited_once_with("test-client", {"type": "TRANSCRIPTION", "text": "Hello Sir"})
    run_agent_mock.assert_awaited_once_with("test-client", "Hello Sir", "frame-data")


def test_voice_websocket_accepts_text_and_audio_messages():
    from ws_neural import router as voice_router

    app = FastAPI()
    app.include_router(voice_router)

    text_called = threading.Event()
    audio_called = threading.Event()
    audio_calls = []

    async def mock_run_agent(*args, **kwargs):
        text_called.set()

    async def mock_run_audio_turn(*args, **kwargs):
        audio_calls.append((args, kwargs))
        audio_called.set()

    payload = base64.b64encode(b"audio").decode()

    with patch("ws_neural.run_agent", new=mock_run_agent), \
         patch("ws_neural.run_audio_turn", new=mock_run_audio_turn):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/voice") as websocket:
                websocket.send_text(json.dumps({"type": "text_input", "text": "hello"}))
                assert text_called.wait(1.0)

                websocket.send_text(json.dumps({
                    "type": "audio_input",
                    "data": payload,
                    "mime_type": "audio/webm",
                    "file_name": "browser-recording.webm",
                }))
                assert audio_called.wait(1.0)
                time.sleep(0.05)

                audio_called.clear()
                websocket.send_text(json.dumps({"type": "AUDIO_START", "data": payload}))
                assert audio_called.wait(1.0)
                time.sleep(0.05)

    assert len(audio_calls) == 2
    assert audio_calls[0][0][1] == b"audio"
    assert audio_calls[0][0][2] == "audio/webm"
    assert audio_calls[1][0][2] == "audio/mp4"
