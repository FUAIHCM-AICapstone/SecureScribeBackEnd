import uuid


def test_bulk_create_and_update_and_delete(client):
    # bulk create
    bulk_payload = {
        "users": [
            {"email": "bulk1@example.com", "password": "password123", "name": "Bulk1"},
            {"email": "bulk2@example.com", "password": "password123", "name": "Bulk2"},
        ]
    }
    resp = client.post("/api/v1/users/bulk", json=bulk_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 2

    user_ids = [r["id"] for r in body["data"] if r["success"]]

    # bulk update (mixed success: 1 valid, 1 invalid id)
    bulk_update_payload = {
        "users": [
            {"id": user_ids[0], "updates": {"name": "Bulk1 Updated"}},
            {"id": str(uuid.uuid4()), "updates": {"name": "NonExist"}},
        ]
    }
    resp = client.put("/api/v1/users/bulk", json=bulk_update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_processed"] == 2
    assert body["total_failed"] == 1

    # bulk delete - use query parameters instead of body
    user_ids_str = ",".join(str(uid) for uid in user_ids)
    resp = client.delete(f"/api/v1/users/bulk?user_ids={user_ids_str}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == len(user_ids)
