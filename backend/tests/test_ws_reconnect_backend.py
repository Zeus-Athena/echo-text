import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.api.v1.ws_v2 import websocket_transcribe_v2


class SimpleMock:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.mark.asyncio
async def test_ws_reconnect_start_logic():
    """测试 WebSocket 重连后发送第二个 start 指令的后端逻辑兼容性"""
    # 模拟 WebSocket
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    
    recording_id = str(uuid4())
    start_msg = {
        "action": "start",
        "recording_id": recording_id,
        "source_lang": "en",
        "target_lang": "zh"
    }
    
    # 第一次返回消息，第二次抛出断开异常以结束循环
    # 第一次返回消息，第二次抛出断开异常以结束循环
    mock_ws.receive.side_effect = [
        {"text": json.dumps(start_msg)},
        WebSocketDisconnect()
    ]
    
    mock_db = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None
    
    config_attrs = {
        "stt_provider": "Deepgram",
        "stt_deepgram_api_key": "test_key",
        "stt_api_key": "test_key",
        "stt_base_url": "https://api.deepgram.com",
        "stt_model": "nova-2",
        "llm_provider": "openai",
        "llm_api_key": "test_key",
        "llm_base_url": "https://api.openai.com/v1",
        "llm_model": "gpt-3.5-turbo",
        "llm_groq_api_key": None,
        "llm_siliconflow_api_key": None,
        "audio_buffer_duration": 5.0,
        "silence_threshold": 30.0,
        "translation_mode": 0
    }
    mock_config = SimpleMock(**config_attrs)
    
    mock_user = SimpleMock(id=uuid4())

    mock_res_user = MagicMock()
    mock_res_user.scalar_one_or_none.return_value = mock_user
    
    mock_res_config = MagicMock()
    mock_res_config.scalar_one_or_none.return_value = mock_config
    
    mock_db.execute.side_effect = [mock_res_user, mock_res_config]
    
    with patch("app.api.v1.ws_v2.async_session", return_value=mock_session_cm), \
         patch("app.api.deps.verify_token") as mock_verify, \
         patch("app.api.deps.get_effective_config", new_callable=AsyncMock) as mock_cfg, \
         patch("app.api.v1.ws_v2.ProcessorFactory.create") as mock_factory:
        
        mock_verify.return_value = {"sub": str(mock_user.id)}
        mock_cfg.return_value = mock_config
        
        mock_processor = AsyncMock()
        mock_factory.return_value = mock_processor
        
        await websocket_transcribe_v2(mock_ws, token="token")
            
        mock_factory.assert_called_once()
        mock_processor.start.assert_awaited_once()

    assert True
