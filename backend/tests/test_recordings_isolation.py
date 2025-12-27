import pytest

from app.models.recording import Folder, Recording


@pytest.mark.asyncio
async def test_recordings_isolation_by_source_type(
    client, db, normal_user, normal_user_token_headers
):
    """
    Verify that list_recordings endpoint correctly filters by source_type.
    """
    # 1. Create mixed recordings for the user
    realtime_rec = Recording(
        user_id=normal_user.id,
        title="Realtime Recording",
        source_type="realtime",
        status="completed",
        duration_seconds=10,
    )
    upload_rec = Recording(
        user_id=normal_user.id,
        title="Uploaded Recording",
        source_type="upload",
        status="completed",
        duration_seconds=20,
    )

    db.add(realtime_rec)
    db.add(upload_rec)
    await db.commit()

    # 2. Test fetching ALL
    response = await client.get("/api/v1/recordings/", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    ids = [r["id"] for r in data]
    assert str(realtime_rec.id) in ids
    assert str(upload_rec.id) in ids

    # 3. Test fetching ONLY realtime
    response = await client.get(
        "/api/v1/recordings/?source_type=realtime", headers=normal_user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    # Should contain realtime_rec but NOT upload_rec
    ids = [r["id"] for r in data]
    assert str(realtime_rec.id) in ids
    assert str(upload_rec.id) not in ids
    # Verify all returned items are actually realtime
    for r in data:
        assert r["source_type"] == "realtime"

    # 4. Test fetching ONLY upload
    response = await client.get(
        "/api/v1/recordings/?source_type=upload", headers=normal_user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    # Should contain upload_rec but NOT realtime_rec
    ids = [r["id"] for r in data]
    assert str(upload_rec.id) in ids
    assert str(realtime_rec.id) not in ids
    # Verify all returned items are actually upload
    for r in data:
        assert r["source_type"] == "upload"


@pytest.mark.asyncio
async def test_folders_isolation_by_source_type(client, db, normal_user, normal_user_token_headers):
    """
    Verify that list_folders endpoint correctly filters by source_type.
    """
    # 1. Create mixed folders manually
    realtime_folder = Folder(user_id=normal_user.id, name="Realtime Folder", source_type="realtime")
    upload_folder = Folder(user_id=normal_user.id, name="Upload Folder", source_type="upload")
    db.add(realtime_folder)
    db.add(upload_folder)
    await db.commit()

    # 2. Test list_folders with realtime
    response = await client.get(
        "/api/v1/recordings/folders?source_type=realtime", headers=normal_user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    folder_ids = [f["id"] for f in data["folders"]]
    assert str(realtime_folder.id) in folder_ids
    assert str(upload_folder.id) not in folder_ids

    # 3. Test list_folders with upload
    response = await client.get(
        "/api/v1/recordings/folders?source_type=upload", headers=normal_user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    folder_ids = [f["id"] for f in data["folders"]]
    assert str(upload_folder.id) in folder_ids
    assert str(realtime_folder.id) not in folder_ids

    # 4. Test creation via API automatically sets source_type
    # Create strictly for upload
    create_payload = {"name": "API Upload Folder", "source_type": "upload"}
    res = await client.post(
        "/api/v1/recordings/folders", json=create_payload, headers=normal_user_token_headers
    )
    assert res.status_code == 201
    new_folder_id = res.json()["id"]

    # Verify it appears in upload list
    response = await client.get(
        "/api/v1/recordings/folders?source_type=upload", headers=normal_user_token_headers
    )
    folder_ids = [f["id"] for f in response.json()["folders"]]
    assert new_folder_id in folder_ids

    # Verify it does NOT appear in realtime list
    response = await client.get(
        "/api/v1/recordings/folders?source_type=realtime", headers=normal_user_token_headers
    )
    folder_ids = [f["id"] for f in response.json()["folders"]]
    assert new_folder_id not in folder_ids
