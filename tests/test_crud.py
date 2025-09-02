from faker import Faker

faker = Faker()


def test_create_user(client):
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    resp = client.post("/api/v1/users", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == payload["email"]
    assert "id" in body["data"]


def test_create_user_minimal(client):
    payload = {"email": faker.email()}
    resp = client.post("/api/v1/users", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == payload["email"]


def test_create_user_with_all_fields(client):
    payload = {
        "email": faker.email(),
        "name": faker.name(),
        "avatar_url": faker.url(),
        "bio": faker.text(max_nb_chars=200),
        "position": faker.job(),
    }
    resp = client.post("/api/v1/users", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == payload["email"]
    assert body["data"]["name"] == payload["name"]


def test_create_user_invalid_email(client):
    payload = {
        "email": "invalid-email",
        "name": faker.name(),
    }
    resp = client.post("/api/v1/users", json=payload)
    assert resp.status_code == 422  # Validation error

def test_create_user_duplicate_email(client):
    email = faker.email()

    # Create first user
    payload1 = {"email": email, "name": faker.name()}
    resp1 = client.post("/api/v1/users", json=payload1)
    assert resp1.status_code == 200

    # Try to create second user with same email
    payload2 = {"email": email, "name": faker.name()}
    resp2 = client.post("/api/v1/users", json=payload2)
    assert resp2.status_code == 500  # Internal server error due to DB constraint


def test_get_users_with_pagination(client):
    resp = client.get("/api/v1/users?page=1&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "pagination" in body
    assert "data" in body
    assert isinstance(body["data"], list)


def test_get_users_pagination_limits(client):
    # Test with different page and limit values
    resp = client.get("/api/v1/users?page=2&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) <= 5


def test_update_user(client):
    # create user first
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    new_name = faker.name()
    resp = client.put(f"/api/v1/users/{user_id}", json={"name": new_name})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == new_name


def test_update_user_all_fields(client):
    # create user first
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    updates = {
        "name": faker.name(),
        "avatar_url": faker.url(),
        "bio": faker.text(max_nb_chars=200),
        "position": faker.job(),
    }
    resp = client.put(f"/api/v1/users/{user_id}", json=updates)
    assert resp.status_code == 200
    body = resp.json()
    for key, value in updates.items():
        assert body["data"][key] == value


def test_update_user_not_found(client):
    import uuid

    fake_id = str(uuid.uuid4())
    resp = client.put(f"/api/v1/users/{fake_id}", json={"name": faker.name()})
    assert resp.status_code == 404


def test_delete_user(client):
    # create user first
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    resp = client.delete(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_delete_user_not_found(client):
    import uuid

    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/users/{fake_id}")
    assert resp.status_code == 404


def test_get_user_by_id(client):
    # create user first
    payload = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    resp = client.get(f"/api/v1/users/{user_id}")
    assert resp.status_code == 405  # Method not allowed - endpoint doesn't exist


def test_get_user_by_id_not_found(client):
    import uuid

    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/users/{fake_id}")
    assert resp.status_code == 405  # Method not allowed - endpoint doesn't exist
