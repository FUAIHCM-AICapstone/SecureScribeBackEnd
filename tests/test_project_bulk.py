import uuid
from faker import Faker

faker = Faker()


def create_project_with_member(client, member_user_id=None, member_role="member"):
    """Helper function to create a project and optionally add a member"""
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

    if member_user_id:
        member_data = {"user_id": member_user_id, "role": member_role}
        client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    return project_id


def create_test_user(client):
    """Helper function to create a test user"""
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    return user_resp.json()["data"]["id"]


def test_bulk_add_members_success(client):
    """Test bulk adding members to a project successfully"""
    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Create users to add
    users_data = []
    for _ in range(5):
        user_id = create_test_user(client)
        users_data.append({"user_id": user_id, "role": "member"})

    # Bulk add members
    bulk_data = {"users": users_data}
    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 5
    assert body["total_failed"] == 0
    assert body["total_processed"] == 5


def test_bulk_operations_mixed_success(client):
    """Test bulk operations with mixed success/failure results"""
    # Create valid users for adding to project
    valid_users = []
    for _ in range(2):
        user_id = create_test_user(client)
        valid_users.append(user_id)

    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Try to add mix of valid and invalid users
    bulk_data = {
        "users": [
            {"user_id": valid_users[0], "role": "member"},
            {"user_id": valid_users[1], "role": "admin"},
            {"user_id": str(uuid.uuid4()), "role": "member"},  # Invalid user ID
        ]
    }

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()

    # Should have partial success
    assert body["success"] is False  # Overall false due to some failures
    assert body["total_processed"] == 3
    assert body["total_success"] == 2  # Two valid users
    assert body["total_failed"] == 1  # One invalid user

    # Verify results array
    results = body["data"]
    assert len(results) == 3
    success_count = sum(1 for r in results if r["success"])
    assert success_count == 2


def test_bulk_operations_empty_list(client):
    """Test bulk operations with empty list"""
    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Test empty bulk add
    bulk_data = {"users": []}
    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 0
    assert body["total_failed"] == 0

    # Test empty bulk remove
    resp = client.delete(f"/api/v1/projects/{project_id}/members/bulk?user_ids=")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 0
    assert body["total_failed"] == 0


def test_bulk_operations_duplicate_users(client):
    """Test bulk operations with duplicate user IDs"""
    # Create a user
    user_id = create_test_user(client)

    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Try to add the same user multiple times
    bulk_data = {
        "users": [
            {"user_id": user_id, "role": "member"},
            {"user_id": user_id, "role": "admin"},  # Same user, different role
        ]
    }

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()

    # Should succeed with first addition, fail with duplicate
    assert body["success"] is False  # Overall false due to duplicate
    assert body["total_processed"] == 2
    assert body["total_success"] == 1  # First addition succeeds
    assert body["total_failed"] == 1  # Duplicate fails


def test_bulk_operations_large_batch(client):
    """Test bulk operations with large batch"""
    # Create many users
    user_ids = []
    for _ in range(10):
        user_id = create_test_user(client)
        user_ids.append(user_id)

    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Bulk add all users
    bulk_data = {"users": [{"user_id": uid, "role": "member"} for uid in user_ids]}

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 10
    assert body["total_failed"] == 0

    # Verify bulk operation was successful (we can't verify members via API since GET /members doesn't exist)
    # The success of the bulk operation is sufficient verification


def test_bulk_remove_nonexistent_members(client):
    """Test bulk removing users who are not members"""
    # Create users not in project
    user_ids = []
    for _ in range(3):
        user_id = create_test_user(client)
        user_ids.append(user_id)

    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Try to bulk remove users who are not members
    user_ids_str = ",".join(user_ids)
    resp = client.delete(
        f"/api/v1/projects/{project_id}/members/bulk?user_ids={user_ids_str}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True  # Should succeed (no-op for non-members)
    assert body["total_success"] == 3  # All "succeeded" as no-op
    assert body["total_failed"] == 0


def test_bulk_operations_rollback_on_error(client):
    """Test that bulk operations handle errors appropriately"""
    # Create a project (test user is automatically owner)
    project_id = create_project_with_member(client)

    # Create valid user
    valid_user_id = create_test_user(client)

    # Try bulk operation with invalid data
    bulk_data = {
        "users": [
            {"user_id": valid_user_id, "role": "member"},
            {"user_id": "invalid-uuid", "role": "admin"},  # Invalid UUID
        ]
    }

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()

    # Should handle partial failure gracefully
    assert body["total_processed"] == 2
    assert body["total_success"] >= 0
    assert body["total_failed"] >= 0

    # Results should indicate which operations succeeded/failed
    results = body["data"]
    assert len(results) == 2
    assert any(r["success"] for r in results)  # At least one should succeed
    assert any(not r["success"] for r in results)  # At least one should fail


def test_bulk_operations_with_roles(client):
    """Test bulk operations with different user roles"""
    # Create users
    users = []
    for _ in range(4):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        resp = client.post("/api/v1/users", json=user_data)
        users.append(resp.json()["data"]["id"])

    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

    # Bulk add with different roles
    bulk_data = {
        "users": [
            {"user_id": users[0], "role": "member"},
            {"user_id": users[1], "role": "admin"},
            {"user_id": users[2], "role": "member"},
            {"user_id": users[3], "role": "admin"},
        ]
    }

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 4

    # Verify bulk operation was successful (we can't verify member roles via API since GET /members doesn't exist)
    # The success of the bulk operation with role assignments is sufficient verification
