import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserConfig


@pytest.mark.asyncio
async def test_get_user_config_returns_keys(
    client: AsyncClient, normal_user_token_headers, db: AsyncSession, normal_user: User
):
    """Test accessing config returns the keys map"""
    # Ensure config exists with some keys
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == normal_user.id))
    config = result.scalar_one_or_none()
    if not config:
        config = UserConfig(user_id=normal_user.id)
        db.add(config)

    config.stt_groq_api_key = "gsk_test_key"
    config.stt_deepgram_api_key = "deepgram_test_key"
    config.llm_groq_api_key = "gsk_llm_key"
    await db.commit()

    response = await client.get("/api/v1/users/me/config", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()

    assert "stt" in data
    assert "keys" in data["stt"]
    assert data["stt"]["keys"]["groq"] == "***"  # Masked
    assert data["stt"]["keys"]["deepgram"] == "***"  # Masked
    assert data["stt"]["keys"]["siliconflow"] is None

    assert "llm" in data
    assert "keys" in data["llm"]
    assert data["llm"]["keys"]["groq"] == "***"
    assert data["llm"]["keys"]["siliconflow"] is None


@pytest.mark.asyncio
async def test_update_user_config_keys(
    client: AsyncClient, normal_user_token_headers, db: AsyncSession, normal_user: User
):
    """Test updating keys via PUT /me/config"""

    payload = {
        "stt": {
            "provider": "Deepgram",
            "model": "nova-2",
            "keys": {"deepgram": "new_deepgram_key", "groq": "new_groq_key"},
        },
        "llm": {"provider": "SiliconFlow", "keys": {"siliconflow": "new_silicon_key"}},
    }

    response = await client.put(
        "/api/v1/users/me/config", json=payload, headers=normal_user_token_headers
    )
    assert response.status_code == 200

    # Verify DB update
    await db.refresh(normal_user)
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == normal_user.id))
    config = result.scalar_one()

    assert config.stt_deepgram_api_key == "new_deepgram_key"
    assert config.stt_groq_api_key == "new_groq_key"
    assert config.llm_siliconflow_api_key == "new_silicon_key"

    # Verify response reflects active key masking
    data = response.json()
    # Active STT is Deepgram
    assert data["stt"]["provider"] == "Deepgram"
    assert data["stt"]["api_key"] == "***"  # Should be masked

    # Active LLM is SiliconFlow
    assert data["llm"]["provider"] == "SiliconFlow"
    assert data["llm"]["api_key"] == "***"


@pytest.mark.asyncio
async def test_legacy_api_key_update_handled(
    client: AsyncClient, normal_user_token_headers, db: AsyncSession, normal_user: User
):
    """Test that setting legacy api_key field still works and updates the provider-specific key"""

    # Set provider to Groq first
    pre_payload = {
        "stt": {"provider": "groq"}
    }  # Lowercase provider to match backend expectation if it is case sensitive?
    # Backend users.py: if api_config.stt_provider == "groq": ...
    # API allows string.
    # We should set it to what creates the match.
    # Let's assume user sets "groq".

    await client.put("/api/v1/users/me/config", json=pre_payload, headers=normal_user_token_headers)

    # Now update api_key
    payload = {"stt": {"api_key": "legacy_update_key"}}

    response = await client.put(
        "/api/v1/users/me/config", json=payload, headers=normal_user_token_headers
    )
    assert response.status_code == 200

    # Check DB
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == normal_user.id))
    config = result.scalar_one()

    assert config.stt_groq_api_key == "legacy_update_key"
    # assert config.stt_api_key == "legacy_update_key" # The legacy field is also updated in my implementation
