"""
Share API Tests (Minimal Stable)
"""

import secrets
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.share import (
    CreateShareRequest,
    create_share_link,
    revoke_share_link,
)


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    return u


@pytest.fixture
def mock_recording():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        title="Test Recording",
        duration_seconds=60,
        source_lang="en",
        target_lang="zh",
        transcript=None,
        translation=None,
        ai_summary=None,
        audio_oid=None,
        audio_blob_id=None,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_share_link(mock_recording):
    sl = SimpleNamespace(
        id=uuid4(),
        recording_id=mock_recording.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(hours=168),
        max_views=None,
        view_count=0,
        include_audio=True,
        include_translation=True,
        include_summary=True,
        password_hash=None,
        created_by=uuid4(),
        created_at=datetime.utcnow(),
        recording=mock_recording,
    )
    return sl


@pytest.mark.asyncio
async def test_create_share_link_success(mock_user, mock_recording):
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = mock_recording

    mock_request = MagicMock()
    mock_request.headers = {"Host": "localhost:8000"}

    req_body = CreateShareRequest(recording_id=mock_recording.id, expires_in_hours=24)

    with patch("app.api.v1.share.ShareLink") as MockSL:
        mock_sl = MagicMock()
        mock_sl.id = uuid4()
        mock_sl.token = "test_token"
        mock_sl.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_sl.max_views = None
        mock_sl.view_count = 0
        mock_sl.include_audio = True
        mock_sl.include_translation = True
        mock_sl.include_summary = True
        mock_sl.created_at = datetime.utcnow()
        MockSL.return_value = mock_sl

        res = await create_share_link(req_body, mock_request, mock_user, db)
        assert res.token == "test_token"


@pytest.mark.asyncio
async def test_revoke_share_link_success(mock_user, mock_share_link):
    db = AsyncMock()
    mock_share_link.created_by = mock_user.id
    db.execute.return_value.scalar_one_or_none.return_value = mock_share_link

    res = await revoke_share_link(mock_share_link.id, mock_user, db)
    assert res["message"] == "分享链接已撤销"
