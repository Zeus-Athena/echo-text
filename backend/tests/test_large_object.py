"""
Large Object Storage Tests
测试大对象存储功能（PostgreSQL Large Object 和 SQLite BLOB 回退）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestIsPostgres:
    """测试数据库类型检测"""

    def test_is_postgres_true(self):
        """测试 PostgreSQL 检测"""
        from app.utils.large_object import is_postgres

        with patch("app.utils.large_object.settings") as mock_settings:
            mock_settings.DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
            assert is_postgres() is True

    def test_is_postgres_false_sqlite(self):
        """测试 SQLite 检测"""
        from app.utils.large_object import is_postgres

        with patch("app.utils.large_object.settings") as mock_settings:
            mock_settings.DATABASE_URL = "sqlite+aiosqlite:///./test.db"
            assert is_postgres() is False


class TestSaveAudioData:
    """测试保存音频数据"""

    @pytest.mark.asyncio
    async def test_save_audio_data_sqlite(self):
        """测试 SQLite BLOB 保存"""
        from app.utils.large_object import save_audio_data

        db = AsyncMock()
        audio_bytes = b"test audio data"

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._save_blob", new_callable=AsyncMock) as mock_save,
        ):
            mock_save.return_value = "blob-123"
            oid, blob_id = await save_audio_data(db, audio_bytes)

        assert oid is None
        assert blob_id == "blob-123"
        mock_save.assert_called_once_with(db, audio_bytes)

    @pytest.mark.asyncio
    async def test_save_audio_data_postgres(self):
        """测试 PostgreSQL Large Object 保存"""
        from app.utils.large_object import save_audio_data

        db = AsyncMock()
        audio_bytes = b"test audio data"

        with (
            patch("app.utils.large_object.is_postgres", return_value=True),
            patch("app.utils.large_object._save_large_object", new_callable=AsyncMock) as mock_save,
        ):
            mock_save.return_value = 12345
            oid, blob_id = await save_audio_data(db, audio_bytes)

        assert oid == 12345
        assert blob_id is None
        mock_save.assert_called_once_with(db, audio_bytes)


class TestReadAudioData:
    """测试读取音频数据"""

    @pytest.mark.asyncio
    async def test_read_audio_data_sqlite(self):
        """测试 SQLite BLOB 读取"""
        from app.utils.large_object import read_audio_data

        db = AsyncMock()
        expected_data = b"audio content"

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._read_blob", new_callable=AsyncMock) as mock_read,
        ):
            mock_read.return_value = expected_data
            data = await read_audio_data(db, blob_id="blob-123")

        assert data == expected_data
        mock_read.assert_called_once_with(db, "blob-123", 0, -1)

    @pytest.mark.asyncio
    async def test_read_audio_data_postgres(self):
        """测试 PostgreSQL Large Object 读取"""
        from app.utils.large_object import read_audio_data

        db = AsyncMock()
        expected_data = b"audio content"

        with (
            patch("app.utils.large_object.is_postgres", return_value=True),
            patch("app.utils.large_object._read_large_object", new_callable=AsyncMock) as mock_read,
        ):
            mock_read.return_value = expected_data
            data = await read_audio_data(db, oid=12345)

        assert data == expected_data
        mock_read.assert_called_once_with(db, 12345, 0, -1)

    @pytest.mark.asyncio
    async def test_read_audio_data_with_range(self):
        """测试带范围的读取"""
        from app.utils.large_object import read_audio_data

        db = AsyncMock()
        expected_data = b"partial"

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._read_blob", new_callable=AsyncMock) as mock_read,
        ):
            mock_read.return_value = expected_data
            data = await read_audio_data(db, blob_id="blob-123", offset=100, length=50)

        assert data == expected_data
        mock_read.assert_called_once_with(db, "blob-123", 100, 50)

    @pytest.mark.asyncio
    async def test_read_audio_data_no_id_raises(self):
        """测试无 ID 时抛出异常"""
        from app.utils.large_object import read_audio_data

        db = AsyncMock()

        with patch("app.utils.large_object.is_postgres", return_value=False):
            with pytest.raises(ValueError) as exc:
                await read_audio_data(db)
            assert "must be provided" in str(exc.value)


class TestDeleteAudioData:
    """测试删除音频数据"""

    @pytest.mark.asyncio
    async def test_delete_audio_data_sqlite(self):
        """测试 SQLite BLOB 删除"""
        from app.utils.large_object import delete_audio_data

        db = AsyncMock()

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._delete_blob", new_callable=AsyncMock) as mock_delete,
        ):
            mock_delete.return_value = True
            result = await delete_audio_data(db, blob_id="blob-123")

        assert result is True
        mock_delete.assert_called_once_with(db, "blob-123")

    @pytest.mark.asyncio
    async def test_delete_audio_data_postgres(self):
        """测试 PostgreSQL Large Object 删除"""
        from app.utils.large_object import delete_audio_data

        db = AsyncMock()

        with (
            patch("app.utils.large_object.is_postgres", return_value=True),
            patch(
                "app.utils.large_object._delete_large_object", new_callable=AsyncMock
            ) as mock_delete,
        ):
            mock_delete.return_value = True
            result = await delete_audio_data(db, oid=12345)

        assert result is True
        mock_delete.assert_called_once_with(db, 12345)

    @pytest.mark.asyncio
    async def test_delete_audio_data_no_id(self):
        """测试无 ID 时返回 False"""
        from app.utils.large_object import delete_audio_data

        db = AsyncMock()

        with patch("app.utils.large_object.is_postgres", return_value=False):
            result = await delete_audio_data(db)

        assert result is False


class TestGetAudioSize:
    """测试获取音频大小"""

    @pytest.mark.asyncio
    async def test_get_audio_size_sqlite(self):
        """测试 SQLite BLOB 大小获取"""
        from app.utils.large_object import get_audio_size

        db = AsyncMock()

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._get_blob_size", new_callable=AsyncMock) as mock_size,
        ):
            mock_size.return_value = 1024
            size = await get_audio_size(db, blob_id="blob-123")

        assert size == 1024
        mock_size.assert_called_once_with(db, "blob-123")

    @pytest.mark.asyncio
    async def test_get_audio_size_postgres(self):
        """测试 PostgreSQL Large Object 大小获取"""
        from app.utils.large_object import get_audio_size

        db = AsyncMock()

        with (
            patch("app.utils.large_object.is_postgres", return_value=True),
            patch("app.utils.large_object._get_lo_size", new_callable=AsyncMock) as mock_size,
        ):
            mock_size.return_value = 2048
            size = await get_audio_size(db, oid=12345)

        assert size == 2048
        mock_size.assert_called_once_with(db, 12345)

    @pytest.mark.asyncio
    async def test_get_audio_size_no_id(self):
        """测试无 ID 时返回 0"""
        from app.utils.large_object import get_audio_size

        db = AsyncMock()

        with patch("app.utils.large_object.is_postgres", return_value=False):
            size = await get_audio_size(db)

        assert size == 0


class TestStreamAudioChunks:
    """测试流式读取音频块"""

    @pytest.mark.asyncio
    async def test_stream_audio_chunks_sqlite(self):
        """测试 SQLite BLOB 流式读取"""
        from app.utils.large_object import stream_audio_chunks

        db = AsyncMock()
        # Mock db.execute to return chunks
        mock_results = [
            MagicMock(scalar=MagicMock(return_value=b"chunk1")),
            MagicMock(scalar=MagicMock(return_value=b"chunk2")),
            MagicMock(scalar=MagicMock(return_value=None)),
        ]
        db.execute = AsyncMock(side_effect=mock_results)

        with (
            patch("app.utils.large_object.is_postgres", return_value=False),
            patch("app.utils.large_object._get_blob_size", new_callable=AsyncMock) as mock_size,
        ):
            mock_size.return_value = 200  # Small size for 2 chunks

            chunks = []
            async for chunk in stream_audio_chunks(db, blob_id="blob-123", chunk_size=100):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == b"chunk1"

    @pytest.mark.asyncio
    async def test_stream_audio_chunks_no_id_raises(self):
        """测试无 ID 时抛出异常"""
        from app.utils.large_object import stream_audio_chunks

        db = AsyncMock()

        with patch("app.utils.large_object.is_postgres", return_value=False):
            with pytest.raises(ValueError) as exc:
                async for _ in stream_audio_chunks(db):
                    pass
            assert "must be provided" in str(exc.value)


class TestAudioBlob:
    """测试 AudioBlob 模型"""

    def test_audio_blob_model(self):
        """测试 AudioBlob 模型定义"""
        from app.utils.large_object import AudioBlob

        assert AudioBlob.__tablename__ == "audio_blobs"


class TestSaveBlobInternal:
    """测试内部 _save_blob 函数"""

    @pytest.mark.asyncio
    async def test_save_blob_creates_entry(self):
        """测试 _save_blob 创建条目"""
        from app.utils.large_object import _save_blob

        db = AsyncMock()
        data = b"test data"

        # 需要 mock AudioBlob 来避免实际数据库操作
        with patch("app.utils.large_object.AudioBlob") as MockAudioBlob:
            mock_blob = MagicMock()
            mock_blob.id = "test-uuid-123"
            MockAudioBlob.return_value = mock_blob

            blob_id = await _save_blob(db, data)

        # The function creates an AudioBlob and calls db.add
        db.add.assert_called_once_with(mock_blob)
        db.flush.assert_called_once()
        # blob_id should be the mocked id
        assert blob_id == "test-uuid-123"


class TestReadBlobInternal:
    """测试内部 _read_blob 函数"""

    @pytest.mark.asyncio
    async def test_read_blob_full(self):
        """测试 _read_blob 完整读取"""
        from app.utils.large_object import _read_blob

        db = AsyncMock()
        mock_blob = MagicMock()
        mock_blob.data = b"full audio data"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_blob
        db.execute.return_value = mock_result

        data = await _read_blob(db, "blob-123")

        assert data == b"full audio data"

    @pytest.mark.asyncio
    async def test_read_blob_with_offset_and_length(self):
        """测试 _read_blob 带偏移和长度"""
        from app.utils.large_object import _read_blob

        db = AsyncMock()
        mock_blob = MagicMock()
        mock_blob.data = b"0123456789"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_blob
        db.execute.return_value = mock_result

        data = await _read_blob(db, "blob-123", offset=2, length=4)

        assert data == b"2345"

    @pytest.mark.asyncio
    async def test_read_blob_with_offset_only(self):
        """测试 _read_blob 仅带偏移"""
        from app.utils.large_object import _read_blob

        db = AsyncMock()
        mock_blob = MagicMock()
        mock_blob.data = b"0123456789"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_blob
        db.execute.return_value = mock_result

        data = await _read_blob(db, "blob-123", offset=5)

        assert data == b"56789"

    @pytest.mark.asyncio
    async def test_read_blob_not_found_raises(self):
        """测试 _read_blob 找不到时抛出异常"""
        from app.utils.large_object import _read_blob

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc:
            await _read_blob(db, "nonexistent")
        assert "not found" in str(exc.value)


class TestDeleteBlobInternal:
    """测试内部 _delete_blob 函数"""

    @pytest.mark.asyncio
    async def test_delete_blob_success(self):
        """测试 _delete_blob 成功删除"""
        from app.utils.large_object import _delete_blob

        db = AsyncMock()
        mock_blob = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_blob
        db.execute.return_value = mock_result

        result = await _delete_blob(db, "blob-123")

        assert result is True
        db.delete.assert_called_once_with(mock_blob)

    @pytest.mark.asyncio
    async def test_delete_blob_not_found(self):
        """测试 _delete_blob 找不到时返回 False"""
        from app.utils.large_object import _delete_blob

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await _delete_blob(db, "nonexistent")

        assert result is False


class TestGetBlobSizeInternal:
    """测试内部 _get_blob_size 函数"""

    @pytest.mark.asyncio
    async def test_get_blob_size_success(self):
        """测试 _get_blob_size 成功获取大小"""
        from app.utils.large_object import _get_blob_size

        db = AsyncMock()
        mock_blob = MagicMock()
        mock_blob.data = b"12345"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_blob
        db.execute.return_value = mock_result

        size = await _get_blob_size(db, "blob-123")

        assert size == 5

    @pytest.mark.asyncio
    async def test_get_blob_size_not_found(self):
        """测试 _get_blob_size 找不到时返回 0"""
        from app.utils.large_object import _get_blob_size

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        size = await _get_blob_size(db, "nonexistent")

        assert size == 0
