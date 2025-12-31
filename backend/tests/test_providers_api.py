"""
Tests for Provider Metadata API
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_providers_metadata(client: AsyncClient):
    """Test GET /api/v1/config/providers returns expected structure"""
    response = await client.get("/api/v1/config/providers")

    assert response.status_code == 200

    data = response.json()

    # Check top-level structure
    assert "llm" in data
    assert "stt" in data
    assert isinstance(data["llm"], list)
    assert isinstance(data["stt"], list)

    # Check LLM providers
    assert len(data["llm"]) > 0
    llm_provider = data["llm"][0]
    assert "id" in llm_provider
    assert "name" in llm_provider
    assert "base_url" in llm_provider
    assert "models" in llm_provider
    assert isinstance(llm_provider["models"], list)

    # Check model structure
    model = llm_provider["models"][0]
    assert "id" in model
    assert "name" in model
    assert "pricing" in model


@pytest.mark.asyncio
async def test_get_providers_metadata_includes_known_providers(client: AsyncClient):
    """Test that expected providers are present"""
    response = await client.get("/api/v1/config/providers")
    data = response.json()

    llm_ids = [p["id"] for p in data["llm"]]
    stt_ids = [p["id"] for p in data["stt"]]

    # Check known LLM providers
    assert "siliconflow" in llm_ids
    assert "groq" in llm_ids

    # Check known STT providers
    assert "groq" in stt_ids
    assert "deepgram" in stt_ids


@pytest.mark.asyncio
async def test_get_providers_metadata_includes_custom_provider(client: AsyncClient):
    """Test that Custom provider is available for user-defined endpoints"""
    response = await client.get("/api/v1/config/providers")
    data = response.json()

    llm_ids = [p["id"] for p in data["llm"]]
    stt_ids = [p["id"] for p in data["stt"]]

    # Custom provider should be present in both
    assert "custom" in llm_ids
    assert "custom" in stt_ids

    # Custom provider should have empty models list and empty base_url
    llm_custom = next(p for p in data["llm"] if p["id"] == "custom")
    assert llm_custom["base_url"] == ""
    assert llm_custom["models"] == []
    assert "help_text" in llm_custom

    stt_custom = next(p for p in data["stt"] if p["id"] == "custom")
    assert stt_custom["base_url"] == ""
    assert stt_custom["models"] == []
