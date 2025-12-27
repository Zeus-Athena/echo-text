from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import UserConfig
from app.services.stt_service import STTService


@pytest.fixture
def mock_user_config():
    config = MagicMock(spec=UserConfig)
    config.stt_provider = "openai"
    config.stt_api_key = "test-key"
    config.stt_model = "whisper-1"
    config.stt_base_url = "https://api.openai.com/v1"

    # Provider keys
    config.stt_deepgram_api_key = "deepgram-key"
    config.stt_groq_api_key = "groq-key"
    config.stt_openai_api_key = "openai-key"
    config.stt_siliconflow_api_key = "silicon-key"

    return config


@pytest.mark.asyncio
async def test_stt_init_openai(mock_user_config):
    mock_user_config.stt_provider = "openai"
    service = STTService(mock_user_config)

    assert service.provider == "openai"
    assert service.api_key == "openai-key"
    assert service.client is not None


@pytest.mark.asyncio
async def test_stt_init_deepgram(mock_user_config):
    mock_user_config.stt_provider = "deepgram"
    service = STTService(mock_user_config)

    assert service.provider == "deepgram"
    assert service.api_key == "deepgram-key"
    # Client should be None for Deepgram as we use httpx directly
    assert service.client is None


@pytest.mark.asyncio
async def test_transcribe_openai_compatible(mock_user_config):
    mock_user_config.stt_provider = "openai"
    service = STTService(mock_user_config)

    # Mock the client
    mock_response = MagicMock()
    mock_response.text = "Hello world"
    mock_response.segments = [
        {"start": 0.0, "end": 1.0, "text": "Hello"},
        {"start": 1.0, "end": 2.0, "text": "world"},
    ]
    mock_response.language = "en"

    service.client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

    audio_data = b"fake-audio-data"
    result = await service.transcribe(audio_data, language="en")

    assert result["text"] == "Hello world"
    assert len(result["segments"]) == 2
    assert result["language"] == "en"

    service.client.audio.transcriptions.create.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.stt_service.httpx.AsyncClient")
async def test_transcribe_deepgram_native(mock_client_cls, mock_user_config):
    mock_user_config.stt_provider = "deepgram"
    service = STTService(mock_user_config)

    # Mock httpx client response
    mock_client = AsyncMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": "Hello Deepgram. How are you?",
                            "paragraphs": {
                                "paragraphs": [
                                    {
                                        "sentences": [
                                            {"text": "Hello Deepgram.", "start": 0.1, "end": 0.5},
                                            {"text": "How are you?", "start": 0.6, "end": 1.2},
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
                }
            ]
        },
        "metadata": {"language": "en"},
    }
    mock_client.post.return_value = mock_response

    audio_data = b"fake-audio-data"
    result = await service.transcribe(audio_data, language="en")

    assert result["text"] == "Hello Deepgram. How are you?"
    assert len(result["segments"]) == 1
    assert result["segments"][0]["text"] == "Hello Deepgram. How are you?"
    assert result["language"] == "en"

    # Verify proper URL and headers
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://api.deepgram.com/v1/listen"
    assert call_args[1]["headers"]["Authorization"] == "Token deepgram-key"
    assert call_args[1]["params"]["model"] == "whisper-1"  # Mock sets this
