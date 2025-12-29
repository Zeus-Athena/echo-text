import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.audio_processors import BaseAudioProcessor, TranscriptEvent

# === Mocks ===


class MockAudioProcessor(BaseAudioProcessor):
    def __init__(self, config, on_transcript, on_error):
        # Store callbacks to trigger them later
        self.config = config
        self.on_transcript = on_transcript
        self.on_error = on_error

    async def start(self):
        # BaseAudioProcessor.start calls _on_start
        await self._on_start()

    async def stop(self):
        # BaseAudioProcessor.stop calls _on_stop
        await self._on_stop()

    async def process_audio(self, audio_data: bytes):
        # BaseAudioProcessor.process_audio calls _process_chunk
        await self._process_chunk(audio_data)

    async def _on_start(self):
        pass

    async def _on_stop(self):
        pass

    async def _process_chunk(self, chunk: bytes):
        # Simulate recognizing text from audio
        # decode bytes to see what 'event' to trigger
        # We'll use a simple convention: b"event:Text"
        if chunk.startswith(b"event:"):
            text = chunk[6:].decode("utf-8")
            event = TranscriptEvent(
                text=text, is_final=True, start_time=0.0, end_time=1.0, speaker="Me"
            )
            # Call the callback provided by ws_v2.py
            await self.on_transcript(event)

    async def pause(self, on_auto_stop):
        pass

    async def resume(self):
        pass


@pytest.fixture
def client():
    # Use allow_hosting_policy checks if needed, but TestClient serves app directly
    return TestClient(app)


@pytest.fixture
def mock_token():
    return "mock_token"


@pytest.fixture
def mock_deps():
    # Patch all dependencies to avoid DB/Redis connection requirements
    with (
        patch("app.api.deps.verify_token") as mock_verify,
        patch("app.api.v1.ws_v2.async_session") as mock_session_cls,
        patch("app.api.v1.ws_v2.LLMService"),
        patch("app.api.v1.ws_v2.STTService"),
        patch("app.api.v1.ws_v2.AudioSaver"),
        patch("app.api.deps.get_effective_config") as mock_get_config,
        patch("app.api.v1.ws_v2.append_transcript_to_db"),
    ):
        # 1. Token
        mock_verify.return_value = {"sub": "user_123"}

        # 2. Database (Async Session)
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # User query result
        mock_user = MagicMock()
        mock_user.id = "user_123"
        mock_user.stt_provider = "Deepgram"

        # Config query result
        mock_config = MagicMock()
        mock_config.audio_buffer_duration = 6.0
        mock_config.silence_threshold = 30
        mock_config.stt_deepgram_api_key = "test_key"

        # Flexible side effect to return User then Config
        def db_execute_side_effect(*args, **kwargs):
            mock_res = MagicMock()
            query_str = str(args[0])
            if "user" in query_str.lower() and "user_config" not in query_str.lower():
                mock_res.scalar_one_or_none.return_value = mock_user
            else:
                mock_res.scalar_one_or_none.return_value = mock_config
            return mock_res

        mock_session.execute.side_effect = db_execute_side_effect

        # Configure get_effective_config to return our mock_config
        mock_get_config.return_value = mock_config

        yield


def test_websocket_non_blocking_translation(client, mock_token, mock_deps):
    """
    Critical Test: Ensure slow translation does NOT block WebSocket commands (e.g. Ping).

    Scenario:
    1. Client starts recording.
    2. Client sends Audio causing a Transcript Event.
    3. Server receives Transcript -> sends Transcript back -> Triggers Translation (Mocked to be SLOW).
    4. Client IMMEDIATELY sends Ping.
    5. If NON-BLOCKING: Client receives Ping Response (Pong) QUICKLY (before translation finishes).
    6. If BLOCKING: Client receives Pong only AFTER the slow translation finishes.
    """

    SLOW_DELAY = 1.0  # 1 second translation delay

    with (
        patch("app.api.v1.ws_v2.ProcessorFactory.create") as mock_factory,
        patch("app.api.v1.ws_v2.TranslationHandler") as MockTranslationHandler,
    ):
        # 1. Setup Mock Processor
        # We need to capture the 'on_transcript' callback passed to create()
        # So we return a MockAudioProcessor which calls it.
        def create_processor(config, stt_service, on_transcript, on_error):
            return MockAudioProcessor(config, on_transcript, on_error)

        mock_factory.side_effect = create_processor

        # 2. Setup Slow Mock Translator
        mock_translator_instance = MockTranslationHandler.return_value

        async def slow_translate(text, is_final):
            # Simulate heavy lifting / network lag
            await asyncio.sleep(SLOW_DELAY)
            return {"text": f"Translated: {text}", "is_final": is_final}

        mock_translator_instance.handle_transcript = AsyncMock(side_effect=slow_translate)
        mock_translator_instance.flush = AsyncMock(return_value=None)

        # 3. Connect Client
        with client.websocket_connect(f"/api/v1/ws/transcribe/v2/{mock_token}") as ws:
            # Start Recording
            ws.send_json(
                {
                    "action": "start",
                    "recording_id": "test_rec",
                    "source_lang": "en",
                    "target_lang": "zh",
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "status", f"Unexpected response: {resp}"

            # 4. Trigger the Slow Operation
            # Send audio bytes that trigger a 'transcript' mock event
            ws.send_bytes(b"event:Hello World")

            # Expect immediate Transcript response (echo)
            # This confirms the server processed the audio and called on_transcript
            resp1 = ws.receive_json()
            assert resp1["type"] == "transcript"
            assert resp1["text"] == "Hello World"

            # At this point, 'translation_worker' should have picked up the task
            # and started 'await slow_translate()'.

            # 5. Send Ping IMMEDIATELY
            t0 = time.time()
            ws.send_json({"action": "ping"})

            # 6. Expect Pong Response
            # If the main loop is BLOCKED by translation, receive_json() will timeout or take > SLOW_DELAY
            # We want it to be fast.
            resp2 = ws.receive_json()
            t1 = time.time()

            assert resp2["type"] == "pong"

            elapsed = t1 - t0
            print(f"Ping took {elapsed:.4f}s during translation")

            # Assert it was fast (much faster than the delay)
            assert elapsed < (SLOW_DELAY / 2), (
                f"Pong took {elapsed}s, which is too slow (Translation delay is {SLOW_DELAY}s). Main loop blocked!"
            )

            # 7. Eventually we should get the translation
            # Note: TestClient context might close/cancel background tasks when exiting block?
            # We can wait for it if we want to be sure it arrives.
            # But the primary goal is proving responsiveness.

            # Let's clean up
            ws.send_json({"action": "stop"})
