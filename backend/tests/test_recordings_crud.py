"""
Recordings CRUD 测试
Test recordings management (CRUD, Folders, Tags, Batch ops)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db


@pytest.fixture
def mock_rec_detail():
    rec = MagicMock()
    rec.id = uuid4()
    rec.title = "Test"
    rec.duration_seconds = 60
    rec.source_lang = "en"
    rec.target_lang = "zh"
    rec.status = "completed"
    rec.source_type = "realtime"
    rec.folder_id = None
    rec.tags = []
    rec.transcript = None
    rec.translation = None
    rec.ai_summary = None
    rec.created_at = datetime.now()
    rec.updated_at = datetime.now()
    rec.s3_key = None
    rec.audio_url = None
    rec.audio_format = "opus"
    rec.audio_size = 1000
    rec.audio_oid = None
    rec.audio_blob_id = None
    return rec


@pytest.mark.asyncio
async def test_list_recordings_pagination(mock_user, mock_db, mock_rec_detail):
    """验证：录音列表分页"""
    from app.api.v1.recordings import list_recordings

    mock_rec_detail.user_id = mock_user.id

    async def mock_execute(query):
        m = MagicMock()
        q_str = str(query).lower()
        if "count" in q_str:
            m.scalar.return_value = 10
        else:
            m.scalars.return_value.all.return_value = [mock_rec_detail]
        return m

    mock_db.execute.side_effect = mock_execute

    response = await list_recordings(skip=0, limit=10, current_user=mock_user, db=mock_db)

    assert len(response) == 1
    assert response[0].id == mock_rec_detail.id


@pytest.mark.asyncio
async def test_create_recording_success(mock_user, mock_db):
    """验证：创建录音成功"""
    from app.api.v1.recordings import create_recording
    from app.schemas.recording import RecordingCreate

    data = RecordingCreate(title="Test Recording", source_lang="en", target_lang="zh")

    # Mock Recording class to return a MagicMock instead of real SQLAlchemy model
    # This avoids issues with uninitialized attributes or validation
    with patch("app.api.v1.recordings.Recording") as MockRecording:
        mock_instance = MagicMock()
        mock_instance.id = uuid4()
        mock_instance.title = "Test Recording"
        mock_instance.duration_seconds = 60
        mock_instance.source_lang = "en"
        mock_instance.target_lang = "zh"
        mock_instance.status = "uploaded"
        mock_instance.source_type = "upload"
        mock_instance.folder_id = None
        mock_instance.tags = []
        mock_instance.transcript = None
        mock_instance.translation = None
        mock_instance.ai_summary = None
        mock_instance.created_at = datetime.now()
        mock_instance.updated_at = datetime.now()
        mock_instance.s3_key = None
        mock_instance.audio_url = None
        mock_instance.audio_format = "opus"
        mock_instance.audio_size = 1024
        mock_instance.audio_oid = 1
        mock_instance.audio_blob_id = 1

        MockRecording.return_value = mock_instance

        # Also mock audio utils to avoid file processing issues
        with (
            patch("app.utils.audio_utils.get_audio_duration", return_value=60),
            patch("app.utils.large_object.save_audio_data", return_value=(1, 1)),
        ):
            result = await create_recording(data, mock_user, mock_db)

            mock_db.add.assert_called()
            mock_db.commit.assert_called()
            assert result.title == "Test Recording"


@pytest.mark.asyncio
async def test_get_recording_success(mock_user, mock_db, mock_rec_detail):
    """验证：获取录音详情成功"""
    from app.api.v1.recordings import get_recording

    mock_rec_detail.user_id = mock_user.id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rec_detail
    mock_db.execute.return_value = mock_result

    result = await get_recording(mock_rec_detail.id, mock_user, mock_db)

    assert result.id == mock_rec_detail.id


@pytest.mark.asyncio
async def test_update_recording_title(mock_user, mock_db, mock_rec_detail):
    """验证：更新录音标题"""
    from app.api.v1.recordings import update_recording
    from app.schemas.recording import RecordingUpdate

    mock_rec_detail.user_id = mock_user.id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rec_detail
    mock_db.execute.return_value = mock_result

    update_data = RecordingUpdate(title="New Title")

    await update_recording(mock_rec_detail.id, update_data, mock_user, mock_db)

    assert mock_rec_detail.title == "New Title"
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_delete_recording_cleanup(mock_user, mock_db):
    """验证：删除录音并清理资源"""
    from app.api.v1.recordings import delete_recording

    rec_id = uuid4()
    mock_rec = MagicMock()
    mock_rec.id = rec_id
    mock_rec.user_id = mock_user.id
    mock_rec.audio_oid = 123
    mock_rec.audio_blob_id = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_rec
    mock_db.execute.return_value = mock_result

    with patch(
        "app.utils.large_object.delete_audio_data", new_callable=AsyncMock
    ) as mock_delete_obj:
        await delete_recording(rec_id, mock_user, mock_db)

        mock_delete_obj.assert_called_with(mock_db, oid=123, blob_id=None)
        mock_db.delete.assert_called_with(mock_rec)
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_batch_delete_success(mock_user, mock_db):
    """验证：批量删除"""
    from app.api.v1.recordings import batch_delete_recordings
    from app.schemas.recording import BatchDeleteRequest

    ids = [uuid4(), uuid4()]
    request = BatchDeleteRequest(ids=ids)

    await batch_delete_recordings(request, mock_user, mock_db)

    mock_db.execute.assert_called()
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_list_folders(mock_user, mock_db):
    """验证：列出文件夹"""
    from app.api.v1.recordings import list_folders

    mock_folder = MagicMock()
    mock_folder.name = "Test Folder"
    mock_folder.id = uuid4()
    mock_folder.parent_id = None
    mock_folder.source_type = "realtime"
    mock_folder.created_at = datetime.now()

    async def mock_execute(query):
        m = MagicMock()
        # Configure both scalar() and scalars().all() to suffice for all queries
        m.scalar.return_value = 5
        m.__iter__.return_value = [(mock_folder, 2)]  # For iteration
        m.scalars.return_value.all.return_value = [
            (mock_folder, 2)
        ]  # For scalars().all() (though logic uses execute result iteration for folders)
        return m

    mock_db.execute.side_effect = mock_execute

    response = await list_folders(current_user=mock_user, db=mock_db)

    # response is a dict, not pydantic model in the function return
    assert len(response["folders"]) == 1
    assert response["total_recordings"] == 5


@pytest.mark.asyncio
async def test_create_folder(mock_user, mock_db):
    """验证：创建文件夹"""
    from app.api.v1.recordings import create_folder
    from app.schemas.recording import FolderCreate

    data = FolderCreate(name="New Folder")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    def mock_add(folder):
        folder.id = uuid4()
        folder.created_at = datetime.now()
        folder.recording_count = 0

    mock_db.add.side_effect = mock_add

    result = await create_folder(data, mock_user, mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    assert result.name == "New Folder"


@pytest.mark.asyncio
async def test_create_tag(mock_user, mock_db):
    """验证：创建标签"""
    from app.api.v1.recordings import create_tag
    from app.schemas.recording import TagCreate

    data = TagCreate(name="New Tag", color="#FF0000")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    def mock_add(tag):
        tag.id = uuid4()

    mock_db.add.side_effect = mock_add

    result = await create_tag(data, mock_user, mock_db)

    mock_db.add.assert_called()
    assert result.name == "New Tag"
