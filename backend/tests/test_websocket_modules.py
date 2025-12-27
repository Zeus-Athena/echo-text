"""
Tests for websocket/connection_manager.py
连接管理器单元测试
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestConnectionManager:
    """ConnectionManager 单元测试"""

    @pytest.fixture
    def manager(self):
        """创建新的 ConnectionManager 实例"""
        from app.services.websocket.connection_manager import ConnectionManager

        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建 mock WebSocket"""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    # === 连接管理测试 ===

    @pytest.mark.asyncio
    async def test_connect_accepts_and_stores(self, manager, mock_websocket):
        """connect 接受并存储连接"""
        await manager.connect(mock_websocket, "client_1")

        mock_websocket.accept.assert_called_once()
        assert "client_1" in manager.active_connections
        assert manager.active_connections["client_1"] == mock_websocket

    def test_disconnect_removes_connection(self, manager, mock_websocket):
        """disconnect 移除连接"""
        manager.active_connections["client_1"] = mock_websocket

        manager.disconnect("client_1")

        assert "client_1" not in manager.active_connections

    def test_disconnect_nonexistent_client_no_error(self, manager):
        """disconnect 不存在的客户端不报错"""
        manager.disconnect("nonexistent")  # Should not raise

    def test_get_returns_connection(self, manager, mock_websocket):
        """get 返回连接"""
        manager.active_connections["client_1"] = mock_websocket

        result = manager.get("client_1")

        assert result == mock_websocket

    def test_get_returns_none_for_missing(self, manager):
        """get 对不存在的客户端返回 None"""
        result = manager.get("nonexistent")

        assert result is None

    def test_is_connected_true(self, manager, mock_websocket):
        """is_connected 对已连接客户端返回 True"""
        manager.active_connections["client_1"] = mock_websocket

        assert manager.is_connected("client_1") is True

    def test_is_connected_false(self, manager):
        """is_connected 对未连接客户端返回 False"""
        assert manager.is_connected("nonexistent") is False

    # === 消息发送测试 ===

    @pytest.mark.asyncio
    async def test_send_json_success(self, manager, mock_websocket):
        """send_json 成功发送"""
        manager.active_connections["client_1"] = mock_websocket

        result = await manager.send_json("client_1", {"type": "test"})

        assert result is True
        mock_websocket.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_json_missing_client_returns_false(self, manager):
        """send_json 对不存在的客户端返回 False"""
        result = await manager.send_json("nonexistent", {"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_json_error_disconnects_and_returns_false(self, manager, mock_websocket):
        """send_json 发送失败时断开连接并返回 False"""
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Connection closed"))
        manager.active_connections["client_1"] = mock_websocket

        result = await manager.send_json("client_1", {"type": "test"})

        assert result is False
        assert "client_1" not in manager.active_connections

    # === 便捷方法测试 ===

    @pytest.mark.asyncio
    async def test_send_transcript_formats_correctly(self, manager, mock_websocket):
        """send_transcript 格式正确"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_transcript("client_1", "Hello", is_final=True, speaker="Speaker1")

        mock_websocket.send_json.assert_called_once_with(
            {
                "type": "transcript",
                "text": "Hello",
                "is_final": True,
                "speaker": "Speaker1",
            }
        )

    @pytest.mark.asyncio
    async def test_send_transcript_without_speaker(self, manager, mock_websocket):
        """send_transcript 无 speaker 时不包含该字段"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_transcript("client_1", "Hello", is_final=False)

        call_args = mock_websocket.send_json.call_args[0][0]
        assert "speaker" not in call_args

    @pytest.mark.asyncio
    async def test_send_translation_formats_correctly(self, manager, mock_websocket):
        """send_translation 格式正确"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_translation("client_1", "你好", is_final=True)

        mock_websocket.send_json.assert_called_once_with(
            {
                "type": "translation",
                "text": "你好",
                "is_final": True,
            }
        )

    @pytest.mark.asyncio
    async def test_send_status_formats_correctly(self, manager, mock_websocket):
        """send_status 格式正确"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_status("client_1", "Recording started")

        mock_websocket.send_json.assert_called_once_with(
            {
                "type": "status",
                "message": "Recording started",
            }
        )

    @pytest.mark.asyncio
    async def test_send_error_formats_correctly(self, manager, mock_websocket):
        """send_error 格式正确"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_error("client_1", "Something went wrong")

        mock_websocket.send_json.assert_called_once_with(
            {
                "type": "error",
                "message": "Something went wrong",
            }
        )

    @pytest.mark.asyncio
    async def test_send_pong_formats_correctly(self, manager, mock_websocket):
        """send_pong 格式正确"""
        manager.active_connections["client_1"] = mock_websocket

        await manager.send_pong("client_1")

        mock_websocket.send_json.assert_called_once_with({"type": "pong"})

    # === 多客户端测试 ===

    @pytest.mark.asyncio
    async def test_multiple_clients(self, manager):
        """测试多客户端管理"""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()

        await manager.connect(ws1, "client_1")
        await manager.connect(ws2, "client_2")

        assert len(manager.active_connections) == 2
        assert manager.get("client_1") == ws1
        assert manager.get("client_2") == ws2

        manager.disconnect("client_1")

        assert len(manager.active_connections) == 1
        assert manager.get("client_1") is None
        assert manager.get("client_2") == ws2


class TestTranscriptionSession:
    """TranscriptionSession 单元测试"""

    @pytest.fixture
    def session(self):
        """创建会话实例"""
        from app.services.websocket.session import TranscriptionSession

        return TranscriptionSession(client_id="test_client", user_id="test_user")

    def test_init_defaults(self, session):
        """测试默认值"""
        assert session.client_id == "test_client"
        assert session.user_id == "test_user"
        assert session.recording_id is None
        assert session.source_lang == "en"
        assert session.target_lang == "zh"
        assert session.is_recording is False
        assert session.audio_saved is False
        assert session.translation_buffer == ""
        assert session.last_interim_word_count == 0
        assert session.buffer_duration == 6.0
        assert session.silence_threshold == 30.0

    def test_reset_translation_state(self, session):
        """测试重置翻译状态"""
        session.translation_buffer = "some text"
        session.last_interim_word_count = 10

        session.reset_translation_state()

        assert session.translation_buffer == ""
        assert session.last_interim_word_count == 0

    def test_start_recording(self, session):
        """测试开始录制"""
        session.start_recording(
            recording_id="rec_123",
            source_lang="ja",
            target_lang="en",
            silence_threshold=20.0,
        )

        assert session.is_recording is True
        assert session.audio_saved is False
        assert session.recording_id == "rec_123"
        assert session.source_lang == "ja"
        assert session.target_lang == "en"
        assert session.silence_threshold == 20.0
        assert session.translation_buffer == ""

    def test_start_recording_default_values(self, session):
        """测试开始录制默认值"""
        session.start_recording()

        assert session.is_recording is True
        assert session.source_lang == "en"
        assert session.target_lang == "zh"

    def test_start_recording_preserves_silence_threshold_if_none(self, session):
        """测试开始录制时不覆盖 silence_threshold"""
        session.silence_threshold = 50.0

        session.start_recording(silence_threshold=None)

        assert session.silence_threshold == 50.0

    def test_stop_recording(self, session):
        """测试停止录制"""
        session.is_recording = True

        session.stop_recording()

        assert session.is_recording is False

    def test_mark_audio_saved(self, session):
        """测试标记音频已保存"""
        session.audio_saved = False

        session.mark_audio_saved()

        assert session.audio_saved is True
