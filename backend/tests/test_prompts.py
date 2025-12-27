import pytest
from httpx import AsyncClient

# Use existing conftest fixtures


@pytest.mark.asyncio
async def test_create_and_list_prompts(client: AsyncClient, normal_user_token_headers):
    # 1. Create a prompt
    response = await client.post(
        "/api/v1/prompts/",
        headers=normal_user_token_headers,
        json={
            "name": "Academic Translation",
            "template_type": "translation",
            "content": "Translate the following text to {{target_lang}} in an academic style:\n{{text}}",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Academic Translation"
    assert data["is_active"] is True
    prompt_id = data["id"]

    # 2. List prompts
    response = await client.get("/api/v1/prompts/", headers=normal_user_token_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    found = False
    for item in items:
        if item["id"] == prompt_id:
            found = True
            break
    assert found is True


@pytest.mark.asyncio
async def test_active_prompt_exclusivity(client: AsyncClient, normal_user_token_headers):
    # 1. Create first active prompt
    await client.post(
        "/api/v1/prompts/",
        headers=normal_user_token_headers,
        json={
            "name": "Prompt A",
            "template_type": "summary",
            "content": "Content A",
            "is_active": True,
        },
    )

    # 2. Create second active prompt of same type
    await client.post(
        "/api/v1/prompts/",
        headers=normal_user_token_headers,
        json={
            "name": "Prompt B",
            "template_type": "summary",
            "content": "Content B",
            "is_active": True,
        },
    )

    # 3. Verify list - only newest should be active
    response = await client.get(
        "/api/v1/prompts/?template_type=summary", headers=normal_user_token_headers
    )
    items = response.json()

    active_count = 0
    for item in items:
        if item["is_active"]:
            active_count += 1
            assert item["name"] == "Prompt B"

    assert active_count == 1


@pytest.mark.asyncio
async def test_update_and_delete_prompt(client: AsyncClient, normal_user_token_headers):
    # 1. Create prompt
    response = await client.post(
        "/api/v1/prompts/",
        headers=normal_user_token_headers,
        json={
            "name": "To be deleted",
            "template_type": "translation",
            "content": "Original content",
            "is_active": False,
        },
    )
    prompt_id = response.json()["id"]

    # 2. Update
    response = await client.put(
        f"/api/v1/prompts/{prompt_id}",
        headers=normal_user_token_headers,
        json={"name": "Updated Name", "content": "Updated content"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["content"] == "Updated content"

    # 3. Delete
    response = await client.delete(
        f"/api/v1/prompts/{prompt_id}", headers=normal_user_token_headers
    )
    assert response.status_code == 204

    # 4. Verify gone
    response = await client.get("/api/v1/prompts/", headers=normal_user_token_headers)
    items = response.json()
    ids = [item["id"] for item in items]
    assert prompt_id not in ids
