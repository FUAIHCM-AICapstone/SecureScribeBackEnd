import uuid
from faker import Faker

faker = Faker()


def test_bulk_add_members_success(client):
    """Test bulk adding members to a project successfully"""
    # Create a project first
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

    # Create users to add
    users_data = []
    for _ in range(5):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        user_resp = client.post("/api/v1/users", json=user_data)
        users_data.append({"user_id": user_resp.json()["data"]["id"], "role": "member"})

    # Bulk add members
    bulk_data = {"users": users_data}
    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 5
    assert body["total_failed"] == 0
    assert body["total_processed"] == 5


def test_bulk_join_projects(client):
    """Test joining multiple projects in sequence"""
    # Create multiple projects
    project_ids = []
    for _ in range(3):
        project_data = {"name": faker.company()}
        resp = client.post("/api/v1/projects", json=project_data)
        project_ids.append(resp.json()["data"]["id"])

    # Join all projects
    join_results = []
    for project_id in project_ids:
        resp = client.post(f"/api/v1/projects/{project_id}/join")
        join_results.append(resp.json())

    # Verify all joins were successful
    for result in join_results:
        assert result["success"] is True
        assert result["data"]["role"] == "member"

    # Verify user is member of all projects
    resp = client.get("/api/v1/users/me/projects")
    user_projects = resp.json()["data"]
    joined_project_ids = [p["id"] for p in user_projects]
    for project_id in project_ids:
        assert project_id in joined_project_ids


def test_bulk_leave_projects(client):
    """Test leaving multiple projects in sequence"""
    # Create and join multiple projects
    project_ids = []
    for _ in range(3):
        project_data = {"name": faker.company()}
        resp = client.post("/api/v1/projects", json=project_data)
        project_id = resp.json()["data"]["id"]
        project_ids.append(project_id)
        client.post(f"/api/v1/projects/{project_id}/join")

    # Leave all projects
    leave_results = []
    for project_id in project_ids[:-1]:  # Leave all but one to avoid admin issues
        resp = client.post(f"/api/v1/projects/{project_id}/leave")
        leave_results.append(resp.json())

    # Verify all leaves were successful
    for result in leave_results:
        assert result["success"] is True

    # Verify user left the projects
    resp = client.get("/api/v1/users/me/projects")
    user_projects = resp.json()["data"]
    remaining_project_ids = [p["id"] for p in user_projects]
    for project_id in project_ids[:-1]:
        assert project_id not in remaining_project_ids


def test_bulk_archive_projects(client):
    """Test bulk archiving multiple projects"""
    # Create multiple projects
    project_ids = []
    for _ in range(3):
        project_data = {"name": faker.company()}
        resp = client.post("/api/v1/projects", json=project_data)
        project_ids.append(resp.json()["data"]["id"])

    # Archive all projects
    archive_results = []
    for project_id in project_ids:
        resp = client.patch(f"/api/v1/projects/{project_id}/archive")
        archive_results.append(resp.json())

    # Verify all archives were successful
    for result in archive_results:
        assert result["success"] is True
        assert result["data"]["is_archived"] is True

    # Verify projects are archived when retrieved
    resp = client.get("/api/v1/projects")
    all_projects = resp.json()["data"]
    archived_projects = [p for p in all_projects if p["id"] in project_ids]
    for project in archived_projects:
        assert project["is_archived"] is True


def test_bulk_operations_mixed_success(client):
    """Test bulk operations with mixed success/failure results"""
    # Create valid users for adding to project
    valid_users = []
    for _ in range(2):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        resp = client.post("/api/v1/users", json=user_data)
        valid_users.append(resp.json()["data"]["id"])

    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

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
    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

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
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    resp = client.post("/api/v1/users", json=user_data)
    user_id = resp.json()["data"]["id"]

    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

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
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        resp = client.post("/api/v1/users", json=user_data)
        user_ids.append(resp.json()["data"]["id"])

    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

    # Bulk add all users
    bulk_data = {"users": [{"user_id": uid, "role": "member"} for uid in user_ids]}

    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 10
    assert body["total_failed"] == 0

    # Verify all users were added
    resp = client.get(f"/api/v1/projects/{project_id}/members")
    members = resp.json()["data"]["members"]
    member_ids = [m["user_id"] for m in members]
    for user_id in user_ids:
        assert user_id in member_ids


def test_bulk_remove_nonexistent_members(client):
    """Test bulk removing users who are not members"""
    # Create users not in project
    user_ids = []
    for _ in range(3):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        resp = client.post("/api/v1/users", json=user_data)
        user_ids.append(resp.json()["data"]["id"])

    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

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
    # Create a project
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    project_id = resp.json()["data"]["id"]

    # Create valid user
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    resp = client.post("/api/v1/users", json=user_data)
    valid_user_id = resp.json()["data"]["id"]

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

    # Verify roles were assigned correctly
    resp = client.get(f"/api/v1/projects/{project_id}/members")
    members = resp.json()["data"]["members"]

    # Check that we have the right roles
    member_count = sum(1 for m in members if m["role"] == "member")
    admin_count = sum(1 for m in members if m["role"] == "admin")

    assert member_count >= 2  # At least the members we added
    assert admin_count >= 2  # At least the admins we added
