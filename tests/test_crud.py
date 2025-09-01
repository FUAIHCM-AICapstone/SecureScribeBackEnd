
def test_create_user(client):
    payload = {
        "email": "user1@example.com",
        "password": "password123",
        "name": "User One"
    }
    resp = client.post("/api/v1/users", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == payload["email"]
    assert "id" in body["data"]

def test_get_users_with_pagination(client):
    resp = client.get("/api/v1/users?page=1&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "pagination" in body
    assert "data" in body
    assert isinstance(body["data"], list)

def test_update_user(client):
    # create user first
    payload = {"email": "update@example.com", "password": "password123"}
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    resp = client.put(f"/api/v1/users/{user_id}", json={"name": "Updated"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated"

def test_delete_user(client):
    # create user first
    payload = {"email": "delete@example.com", "password": "password123"}
    user_id = client.post("/api/v1/users", json=payload).json()["data"]["id"]

    resp = client.delete(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
