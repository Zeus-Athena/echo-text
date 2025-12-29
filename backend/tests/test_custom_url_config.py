"""
Test Custom URL Configuration
测试自定义 URL 配置功能
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_save_custom_llm_url(client: AsyncClient, normal_user_token_headers: dict):
    """Test saving custom LLM URL for a specific provider"""
    # Save custom LLM URL for GROQ
    response = await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={"llm": {"provider": "GROQ", "urls": {"groq": "https://custom-groq.example.com/v1"}}},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify the URL is returned
    assert data["llm"]["urls"]["groq"] == "https://custom-groq.example.com/v1"


@pytest.mark.asyncio
async def test_save_custom_stt_url(client: AsyncClient, normal_user_token_headers: dict):
    """Test saving custom STT URL for a specific provider"""
    # Save custom STT URL for Deepgram
    response = await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={
            "stt": {
                "provider": "Deepgram",
                "urls": {"deepgram": "https://custom-deepgram.example.com/v1"},
            }
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify the URL is returned
    assert data["stt"]["urls"]["deepgram"] == "https://custom-deepgram.example.com/v1"


@pytest.mark.asyncio
async def test_save_custom_tts_url(client: AsyncClient, normal_user_token_headers: dict):
    """Test saving custom TTS URL for a specific provider"""
    # Save custom TTS URL for OpenAI
    response = await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={
            "tts": {
                "provider": "openai",
                "urls": {"openai": "https://custom-openai-tts.example.com/v1"},
            }
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify the URL is returned
    assert data["tts"]["urls"]["openai"] == "https://custom-openai-tts.example.com/v1"


@pytest.mark.asyncio
async def test_urls_persist_across_provider_switch(
    client: AsyncClient, normal_user_token_headers: dict
):
    """Test that custom URLs persist when switching providers"""
    # Save custom URL for GROQ
    await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={
            "llm": {"provider": "GROQ", "urls": {"groq": "https://my-groq-proxy.example.com/v1"}}
        },
    )

    # Switch to SiliconFlow and save custom URL for it
    await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={
            "llm": {
                "provider": "SiliconFlow",
                "urls": {"siliconflow": "https://my-siliconflow-proxy.example.com/v1"},
            }
        },
    )

    # Verify both URLs are preserved
    response = await client.get("/api/v1/users/me/config", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()

    # GROQ URL should still be there
    assert data["llm"]["urls"]["groq"] == "https://my-groq-proxy.example.com/v1"
    # SiliconFlow URL should be there
    assert data["llm"]["urls"]["siliconflow"] == "https://my-siliconflow-proxy.example.com/v1"


@pytest.mark.asyncio
async def test_clear_custom_url_by_setting_null(
    client: AsyncClient, normal_user_token_headers: dict
):
    """Test clearing a custom URL by setting it to null"""
    # First save a custom URL
    await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={"llm": {"urls": {"groq": "https://custom-groq.example.com/v1"}}},
    )

    # Clear it by setting to null
    response = await client.put(
        "/api/v1/users/me/config",
        headers=normal_user_token_headers,
        json={"llm": {"urls": {"groq": None}}},
    )

    assert response.status_code == 200
    data = response.json()

    # URL should be null/None
    assert data["llm"]["urls"]["groq"] is None


@pytest.mark.asyncio
async def test_get_config_returns_urls(client: AsyncClient, normal_user_token_headers: dict):
    """Test that GET config returns the urls field"""
    response = await client.get("/api/v1/users/me/config", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()

    # Verify urls field exists in all configs
    assert "urls" in data["llm"]
    assert "urls" in data["stt"]
    assert "urls" in data["tts"]

    # They should be dicts (even if empty)
    assert isinstance(data["llm"]["urls"], dict)
    assert isinstance(data["stt"]["urls"], dict)
    assert isinstance(data["tts"]["urls"], dict)
