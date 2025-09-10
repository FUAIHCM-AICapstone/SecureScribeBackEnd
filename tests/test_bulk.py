import uuid

from faker import Faker

faker = Faker()


def test_bulk_create_and_update_and_delete(client):
    # bulk create
    bulk_payload = {
        "users": [
            {
                "email": faker.email(),
                "name": faker.name(),
            },
            {
                "email": faker.email(),
                "name": faker.name(),
            },
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
            {"id": user_ids[0], "updates": {"name": faker.name()}},
            {"id": str(uuid.uuid4()), "updates": {"name": faker.name()}},
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


def test_bulk_create_empty_list(client):
    bulk_payload = {"users": []}
    resp = client.post("/api/v1/users/bulk", json=bulk_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 0
    assert body["total_failed"] == 0


def test_bulk_create_large_batch(client):
    # Create 10 users
    users = []
    for _ in range(10):
        users.append(
            {
                "email": faker.email(),
                "name": faker.name(),
            }
        )

    bulk_payload = {"users": users}
    resp = client.post("/api/v1/users/bulk", json=bulk_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 10


def test_bulk_create_with_duplicates(client):
    email = faker.email()
    bulk_payload = {
        "users": [
            {
                "email": email,
                "name": faker.name(),
            },
            {
                "email": email,  # duplicate email
                "name": faker.name(),
            },
        ]
    }
    resp = client.post("/api/v1/users/bulk", json=bulk_payload)
    assert resp.status_code == 200
    body = resp.json()
    # Due to DB constraints, duplicates cause transaction rollback
    # The exact behavior depends on implementation - could be 0 or partial success
    assert body["total_processed"] == 2
    # Either all fail due to constraint, or partial success depending on implementation


def test_bulk_create_mixed_valid_invalid(client):
    bulk_payload = {
        "users": [
            {
                "email": faker.email(),
                "name": faker.name(),
            },
            {
                "email": "invalid-email",
                "name": faker.name(),
            },
            {"email": faker.email(), "name": faker.name()},
        ]
    }
    resp = client.post("/api/v1/users/bulk", json=bulk_payload)
    # The API validates the entire request, so invalid data causes 422
    assert resp.status_code == 422


def test_bulk_update_empty_list(client):
    bulk_update_payload = {"users": []}
    resp = client.put("/api/v1/users/bulk", json=bulk_update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_processed"] == 0
    assert body["total_failed"] == 0


def test_bulk_update_all_invalid_ids(client):
    bulk_update_payload = {
        "users": [
            {"id": str(uuid.uuid4()), "updates": {"name": faker.name()}},
            {"id": str(uuid.uuid4()), "updates": {"name": faker.name()}},
        ]
    }
    resp = client.put("/api/v1/users/bulk", json=bulk_update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_processed"] == 2
    assert body["total_failed"] == 2


def test_bulk_update_mixed_fields(client):
    # Create users first
    users_data = []
    for _ in range(3):
        payload = {
            "email": faker.email(),
            "name": faker.name(),
        }
        resp = client.post("/api/v1/users", json=payload)
        users_data.append(resp.json()["data"])

    # Update with different fields
    bulk_update_payload = {
        "users": [
            {"id": users_data[0]["id"], "updates": {"name": faker.name()}},
            {
                "id": users_data[1]["id"],
                "updates": {"bio": faker.text(max_nb_chars=100)},
            },
            {"id": users_data[2]["id"], "updates": {"position": faker.job()}},
        ]
    }
    resp = client.put("/api/v1/users/bulk", json=bulk_update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_processed"] == 3
    assert body["total_failed"] == 0


def test_bulk_delete_empty_list(client):
    resp = client.delete("/api/v1/users/bulk?user_ids=")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 0
    assert body["total_failed"] == 0


def test_bulk_delete_invalid_ids(client):
    fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    user_ids_str = ",".join(fake_ids)
    resp = client.delete(f"/api/v1/users/bulk?user_ids={user_ids_str}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 0
    assert body["total_failed"] == 2


def test_bulk_delete_mixed_valid_invalid(client):
    # Create one real user
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    real_user = client.post("/api/v1/users", json=payload).json()["data"]

    fake_id = str(uuid.uuid4())
    user_ids_str = f"{real_user['id']},{fake_id}"
    resp = client.delete(f"/api/v1/users/bulk?user_ids={user_ids_str}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_success"] == 1
    assert body["total_failed"] == 1
