from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.user import RecordingConfig, UserConfigResponse, UserConfigUpdate


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    u.role = "user"
    return u

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db

class SimpleMock:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.mark.asyncio
async def test_recording_config_schema_new_fields():
    config_data = {
        "audio_buffer_duration": 1, 
        "vad_threshold": 0.3,
        "segment_soft_threshold": 60,
        "segment_hard_threshold": 120,
        "translation_mode": 1
    }
    config = RecordingConfig(**config_data)
    assert config.segment_soft_threshold == 60
    assert config.segment_hard_threshold == 120
    assert config.translation_mode == 1

@pytest.mark.asyncio
async def test_update_user_config_with_new_fields(mock_user, mock_db):
    from app.api.v1.users import update_user_config
    
    mock_config = MagicMock()
    mock_config.id = uuid4()
    mock_config.segment_soft_threshold = 50
    mock_config.segment_hard_threshold = 100
    mock_config.translation_mode = 0
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_config
    mock_db.execute.return_value = mock_res
    
    update_data = UserConfigUpdate(
        recording=RecordingConfig(
            segment_soft_threshold=80,
            segment_hard_threshold=150,
            translation_mode=2
        )
    )
    
    with patch("app.api.v1.users.get_user_config", new_callable=AsyncMock) as mock_get_resp:
        mock_get_resp.return_value = MagicMock(spec=UserConfigResponse)
        await update_user_config(update_data, mock_user, mock_db)
    
    assert mock_config.segment_soft_threshold == 80
    assert mock_config.segment_hard_threshold == 150
    assert mock_config.translation_mode == 2

@pytest.mark.asyncio
async def test_get_user_config_returns_new_fields(mock_user, mock_db):
    from app.api.v1.users import get_user_config
    
    config_attrs = {
        "id": uuid4(),
        "llm_provider": "openai",
        "llm_api_key": "test",
        "llm_base_url": "https://test.com",
        "llm_model": "test",
        "llm_groq_api_key": None,
        "llm_siliconflow_api_key": None,
        "llm_siliconflowglobal_api_key": None,  # New field
        "llm_fireworks_api_key": None,      # New field
        "llm_urls": None,  # 新增字段
        "stt_provider": "Deepgram",
        "stt_api_key": "test",
        "stt_base_url": "https://test.com",
        "stt_model": "test",
        "stt_groq_api_key": None,
        "stt_deepgram_api_key": None,
        "stt_openai_api_key": None,
        "stt_siliconflow_api_key": None,
        "stt_urls": None,  # 新增字段
        "tts_provider": "edge",
        "tts_api_key": None,
        "tts_voice": "zh-CN-XiaoxiaoNeural",
        "tts_base_url": None,
        "tts_urls": None,  # 新增字段
        "dict_provider": "llm",
        "dict_api_key": None,
        "theme": "dark",
        "default_source_lang": "zh",
        "default_target_lang": "en",
        "audio_buffer_duration": 5,
        "silence_threshold": 30,
        "silence_mode": "manual",
        "silence_prefer_source": "current",
        "silence_threshold_source": "default",
        "segment_soft_threshold": 77,
        "segment_hard_threshold": 88,
        "translation_mode": 3
    }
    mock_config = SimpleMock(**config_attrs)
    
    def execute_mock(query):
        q_str = str(query)
        res = MagicMock()
        if "user_config" in q_str.lower():
            res.scalar_one_or_none.return_value = mock_config
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute = AsyncMock(side_effect=execute_mock)
    
    response = await get_user_config(mock_user, mock_db)
    
    assert response.recording.segment_soft_threshold == 77
    assert response.recording.segment_hard_threshold == 88
    assert response.recording.translation_mode == 3
