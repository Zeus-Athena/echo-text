"""
Tests for websocket/audio_saver.py
音频保存测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAudioSaver:
    """AudioSaver 单元测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def audio_saver(self, mock_db):
        """创建 AudioSaver 实例"""
        from app.services.websocket.audio_saver import AudioSaver

        return AudioSaver(mock_db, timeout=60)

    @pytest.fixture
    def mock_processor(self):
        """Mock 音频处理器"""
        processor = MagicMock()
        # 返回 header 和 audio data
        processor.stop = AsyncMock(return_value=(b"header", b"audio_data"))
        return processor

    # === save 方法测试 ===

    @pytest.mark.asyncio
    async def test_save_returns_dict(self, audio_saver, mock_processor, mock_db):
        """save 返回字典"""
        with (
            patch(
                "app.services.websocket.audio_saver.save_audio_data",
                new=AsyncMock(return_value=(1, "blob_id")),
            ),
            patch(
                "app.services.websocket.audio_saver.convert_webm_to_wav",
                return_value=b"wav_data",
            ),
            patch(
                "app.services.websocket.audio_saver.compress_to_opus",
                return_value=b"opus_data",
            ),
        ):
            # Mock Recording 查询
            mock_recording = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_recording
            mock_db.execute.return_value = mock_result

            result = await audio_saver.save(mock_processor, "recording_123")

            assert isinstance(result, dict)
            assert "success" in result

    @pytest.mark.asyncio
    async def test_save_no_audio_returns_error(self, audio_saver, mock_db):
        """无音频数据返回错误"""
        processor = MagicMock()
        processor.stop = AsyncMock(return_value=(None, None))

        result = await audio_saver.save(processor, "recording_123")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_save_empty_audio_returns_error(self, audio_saver, mock_db):
        """空音频数据返回错误"""
        processor = MagicMock()
        processor.stop = AsyncMock(return_value=(b"header", b""))

        result = await audio_saver.save(processor, "recording_123")

        assert result["success"] is False

    # === _convert 方法测试 ===

    @pytest.mark.asyncio
    async def test_convert_success(self, audio_saver):
        """转码成功"""
        with (
            patch(
                "app.services.websocket.audio_saver.convert_webm_to_wav",
                return_value=b"wav_data",
            ),
            patch(
                "app.services.websocket.audio_saver.compress_to_opus",
                return_value=b"opus_data",
            ),
        ):
            wav_data, final_audio, audio_format = await audio_saver._convert(b"raw_audio")

            assert wav_data == b"wav_data"
            assert final_audio == b"opus_data"
            assert audio_format == "opus"

    @pytest.mark.asyncio
    async def test_convert_timeout_fallback_to_webm(self, audio_saver):
        """转码超时回退到 WebM"""
        import asyncio

        audio_saver.timeout = 0.01  # 极短超时

        async def slow_convert(data):
            await asyncio.sleep(10)
            return b"result"

        with patch(
            "app.services.websocket.audio_saver.convert_webm_to_wav",
            side_effect=TimeoutError(),
        ):
            wav_data, final_audio, audio_format = await audio_saver._convert(b"raw_audio")

            assert audio_format == "webm"
            assert final_audio == b"raw_audio"

    @pytest.mark.asyncio
    async def test_convert_error_fallback_to_webm(self, audio_saver):
        """转码错误回退到 WebM"""
        with patch(
            "app.services.websocket.audio_saver.convert_webm_to_wav",
            side_effect=Exception("Conversion failed"),
        ):
            wav_data, final_audio, audio_format = await audio_saver._convert(b"raw_audio")

            assert audio_format == "webm"
            assert final_audio == b"raw_audio"

    # === _get_duration 方法测试 ===

    @pytest.mark.asyncio
    async def test_get_duration_no_wav_returns_zero(self, audio_saver):
        """无 WAV 数据返回 0"""
        duration = await audio_saver._get_duration(None)
        assert duration == 0

    @pytest.mark.asyncio
    async def test_get_duration_with_wav(self, audio_saver):
        """有 WAV 数据返回时长"""
        # 创建一个简单的 WAV 文件
        import io
        import wave

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            # 1秒的静音
            wav.writeframes(b"\x00" * 32000)

        wav_data = buffer.getvalue()

        with patch("app.services.websocket.audio_saver.get_audio_duration", return_value=1.0):
            duration = await audio_saver._get_duration(wav_data)
            assert duration == 1

    @pytest.mark.asyncio
    async def test_get_duration_error_returns_zero(self, audio_saver):
        """获取时长出错返回 0"""
        with patch(
            "app.services.websocket.audio_saver.get_audio_duration",
            side_effect=Exception("Error"),
        ):
            duration = await audio_saver._get_duration(b"invalid_wav")
            assert duration == 0

    # === _update_recording 方法测试 ===

    @pytest.mark.asyncio
    async def test_update_recording_success(self, audio_saver, mock_db):
        """更新录音记录成功"""
        mock_recording = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        await audio_saver._update_recording(
            recording_id="123",
            audio_oid=1,
            audio_blob_id="blob_id",
            audio_size=1024,
            audio_format="opus",
            duration=60,
        )

        assert mock_recording.audio_oid == 1
        assert mock_recording.audio_blob_id == "blob_id"
        assert mock_recording.audio_size == 1024
        assert mock_recording.audio_format == "opus"
        assert mock_recording.duration_seconds == 60
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_recording_not_found(self, audio_saver, mock_db):
        """录音记录不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # 应该不报错
        await audio_saver._update_recording(
            recording_id="123",
            audio_oid=1,
            audio_blob_id="blob_id",
            audio_size=1024,
            audio_format="opus",
            duration=60,
        )

        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_recording_zero_duration_not_set(self, audio_saver, mock_db):
        """duration 为 0 时不设置"""
        mock_recording = MagicMock()
        mock_recording.duration_seconds = 30  # 原始值
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        await audio_saver._update_recording(
            recording_id="123",
            audio_oid=1,
            audio_blob_id="blob_id",
            audio_size=1024,
            audio_format="opus",
            duration=0,
        )

        # duration_seconds 不应该被更新为 0
        assert mock_recording.duration_seconds == 30
