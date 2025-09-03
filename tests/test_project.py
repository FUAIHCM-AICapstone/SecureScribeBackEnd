import uuid
from faker import Faker

faker = Faker()


def test_create_project(client):
    """Test creating a new project"""
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == project_data["name"]
    assert body["data"]["description"] == project_data["description"]
    assert "id" in body["data"]
    assert body["data"]["is_archived"] is False


def test_create_project_minimal(client):
    """Test creating a project with minimal data"""
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == project_data["name"]
    assert body["data"]["description"] is None


def test_create_project_invalid_name(client):
    """Test creating a project with invalid name"""
    project_data = {"name": ""}  # Empty name should fail
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 422  # Validation error


def test_get_projects_pagination(client):
    """Test getting projects with pagination"""
    resp = client.get("/api/v1/projects?page=1&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "pagination" in body
    assert "data" in body
    assert isinstance(body["data"], list)


def test_get_project_by_id(client):
    """Test getting a specific project by ID"""
    # Create a project first
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Get the project
    resp = client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["id"] == project_id
    assert body["data"]["name"] == project_data["name"]


def test_get_project_not_found(client):
    """Test getting a non-existent project"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/projects/{fake_id}")
    assert resp.status_code == 404


def test_update_project(client):
    """Test updating a project"""
    # Create a project first
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Update the project
    new_name = faker.company()
    update_data = {
        "name": new_name,
        "description": faker.text(max_nb_chars=100),
    }
    resp = client.put(f"/api/v1/projects/{project_id}", json=update_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == new_name


def test_archive_project_via_update(client):
    """Test archiving a project via update endpoint"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Archive the project via update
    resp = client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["is_archived"] is True


def test_update_project_not_found(client):
    """Test updating a non-existent project"""
    fake_id = str(uuid.uuid4())
    update_data = {"name": faker.company()}
    resp = client.put(f"/api/v1/projects/{fake_id}", json=update_data)
    assert resp.status_code == 404


def test_delete_project(client):
    """Test deleting a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Delete the project
    resp = client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    # Verify project is deleted
    resp = client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404


def test_add_member_to_project(client):
    """Test adding a member to a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create a user to add
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    user_id = user_resp.json()["data"]["id"]

    # Add user to project
    member_data = {"user_id": user_id, "role": "member"}
    resp = client.post(f"/api/v1/projects/{project_id}/members", json=member_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["user_id"] == user_id
    assert body["data"]["role"] == "member"


def test_leave_project(client):
    """Test leaving a project (self-removal)"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create another user and add them to the project
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    user_id = user_resp.json()["data"]["id"]

    # Add user to project
    member_data = {"user_id": user_id, "role": "member"}
    client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Try to leave the project (this should work as admin removing member)
    resp = client.delete(f"/api/v1/projects/{project_id}/members/{user_id}")
    assert resp.status_code == 200  # Admin removing member
    body = resp.json()
    assert body["success"] is True


def test_update_member_role(client):
    """Test updating a member's role in a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create a user to add
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    user_id = user_resp.json()["data"]["id"]

    # Add user to project
    member_data = {"user_id": user_id, "role": "member"}
    client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Update user role
    role_update = {"role": "admin"}
    resp = client.put(
        f"/api/v1/projects/{project_id}/members/{user_id}", json=role_update
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["role"] == "admin"


def test_get_my_project_stats(client):
    """Test getting current user's project statistics"""
    # Create and join some projects
    project_names = [faker.company() for _ in range(3)]
    for name in project_names:
        project_data = {"name": name}
        create_resp = client.post("/api/v1/projects", json=project_data)
        project_id = create_resp.json()["data"]["id"]

        # Create another user and add them to make the project have multiple members
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        user_resp = client.post("/api/v1/users", json=user_data)
        user_id = user_resp.json()["data"]["id"]

        # Add user to project
        member_data = {"user_id": user_id, "role": "member"}
        client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Get stats
    resp = client.get("/api/v1/users/me/project-stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    stats = body["data"]
    assert "total_projects" in stats
    assert "admin_projects" in stats
    assert "member_projects" in stats
    assert "active_projects" in stats
    assert "archived_projects" in stats
    assert stats["total_projects"] >= 3


def test_request_role_change(client):
    """Test requesting a role change"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create a user and add them to the project
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    user_id = user_resp.json()["data"]["id"]

    # Add user to project
    member_data = {"user_id": user_id, "role": "member"}
    client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Request role change (this would need to be done by the added user)
    role_request = {"role": "admin"}
    resp = client.post(
        f"/api/v1/projects/{project_id}/me/request-role", json=role_request
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["requested_role"] == "admin"


def test_my_projects_only_filter(client):
    """Test filtering projects to show only user's projects"""
    # Create projects
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create another user and add them to make multiple members
    user_data = {
        "email": faker.email(),
        "name": faker.name(),
    }
    user_resp = client.post("/api/v1/users", json=user_data)
    user_id = user_resp.json()["data"]["id"]

    # Add user to project
    member_data = {"user_id": user_id, "role": "member"}
    client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Get all projects (should include created and joined)
    resp = client.get("/api/v1/projects?my_projects_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1

    # Projects should include the one we created
    project_ids = [p["id"] for p in body["data"]]
    assert project_id in project_ids


def test_bulk_add_members(client):
    """Test bulk adding members to a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create users to add
    users_data = []
    for _ in range(3):
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
    assert body["total_success"] == 3
    assert body["total_failed"] == 0


def test_bulk_remove_members(client):
    """Test bulk removing members from a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create and add users
    user_ids = []
    for _ in range(2):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        user_resp = client.post("/api/v1/users", json=user_data)
        user_id = user_resp.json()["data"]["id"]
        user_ids.append(user_id)

        # Add user to project
        member_data = {"user_id": user_id, "role": "member"}
        client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Bulk remove members
    user_ids_str = ",".join(user_ids)
    resp = client.delete(
        f"/api/v1/projects/{project_id}/members/bulk?user_ids={user_ids_str}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 2


def test_project_filtering(client):
    """Test project filtering by various criteria"""
    # Create projects with different properties
    active_project = {"name": "Active Project", "description": "This is active"}
    archived_project = {"name": "Archived Project", "description": "This is archived"}

    # Create active project
    active_resp = client.post("/api/v1/projects", json=active_project)
    active_id = active_resp.json()["data"]["id"]

    # Create and archive project
    archived_resp = client.post("/api/v1/projects", json=archived_project)
    archived_id = archived_resp.json()["data"]["id"]
    client.put(f"/api/v1/projects/{archived_id}", json={"is_archived": True})

    # Filter by archived status
    resp = client.get("/api/v1/projects?is_archived=false")
    assert resp.status_code == 200
    active_projects = [p for p in resp.json()["data"] if p["id"] == active_id]
    assert len(active_projects) == 1

    # Filter by name
    resp = client.get(f"/api/v1/projects?name={active_project['name']}")
    assert resp.status_code == 200
    matching_projects = [
        p for p in resp.json()["data"] if active_project["name"] in p["name"]
    ]
    assert len(matching_projects) >= 1


def test_project_pagination_limits(client):
    """Test project pagination limits"""
    # Create multiple projects
    for _ in range(5):
        project_data = {"name": faker.company()}
        client.post("/api/v1/projects", json=project_data)

    # Test with limit
    resp = client.get("/api/v1/projects?page=1&limit=3")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) <= 3
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["limit"] == 3


def test_project_edge_cases(client):
    """Test various edge cases"""
    # Empty name (should fail)
    resp = client.post("/api/v1/projects", json={"name": ""})
    assert resp.status_code == 422

    # Very long name
    long_name = "A" * 300
    resp = client.post("/api/v1/projects", json={"name": long_name})
    assert resp.status_code == 422  # Should fail due to length limit

    # Special characters in name
    resp = client.post("/api/v1/projects", json={"name": "Project@#$%"})
    assert resp.status_code == 200  # Should work

    # Unicode characters
    resp = client.post("/api/v1/projects", json={"name": "项目名称🚀"})
    assert resp.status_code == 200  # Should work


def test_create_project(client):
    """Test creating a new project"""
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == project_data["name"]
    assert body["data"]["description"] == project_data["description"]
    assert "id" in body["data"]
    assert body["data"]["is_archived"] is False


def test_create_project_minimal(client):
    """Test creating a project with minimal data"""
    project_data = {"name": faker.company()}
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == project_data["name"]
    assert body["data"]["description"] is None


def test_create_project_invalid_name(client):
    """Test creating a project with invalid name"""
    project_data = {"name": ""}  # Empty name should fail
    resp = client.post("/api/v1/projects", json=project_data)
    assert resp.status_code == 422  # Validation error


def test_get_projects_pagination(client):
    """Test getting projects with pagination"""
    resp = client.get("/api/v1/projects?page=1&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "pagination" in body
    assert "data" in body
    assert isinstance(body["data"], list)


def test_get_project_by_id(client):
    """Test getting a specific project by ID"""
    # Create a project first
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Get the project
    resp = client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["id"] == project_id
    assert body["data"]["name"] == project_data["name"]


def test_get_project_not_found(client):
    """Test getting a non-existent project"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/projects/{fake_id}")
    assert resp.status_code == 404


def test_update_project(client):
    """Test updating a project"""
    # Create a project first
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Update the project
    new_name = faker.company()
    update_data = {
        "name": new_name,
        "description": faker.text(max_nb_chars=100),
    }
    resp = client.put(f"/api/v1/projects/{project_id}", json=update_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == new_name


def test_update_project_not_found(client):
    """Test updating a non-existent project"""
    fake_id = str(uuid.uuid4())
    update_data = {"name": faker.company()}
    resp = client.put(f"/api/v1/projects/{fake_id}", json=update_data)
    assert resp.status_code == 404


def test_archive_project(client):
    """Test archiving a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Archive the project
    resp = client.patch(f"/api/v1/projects/{project_id}/archive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["is_archived"] is True


def test_delete_project(client):
    """Test deleting a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Delete the project
    resp = client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    # Verify project is deleted
    resp = client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404


def test_join_project(client):
    """Test joining a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    resp = client.post(f"/api/v1/projects/{project_id}/join")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["role"] == "member"


def test_join_project_already_member(client):
    """Test joining a project when already a member"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project first time
    client.post(f"/api/v1/projects/{project_id}/join")

    # Try to join again
    resp = client.post(f"/api/v1/projects/{project_id}/join")
    assert resp.status_code == 400


def test_leave_project(client):
    """Test leaving a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Leave the project
    resp = client.post(f"/api/v1/projects/{project_id}/leave")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_leave_project_not_member(client):
    """Test leaving a project when not a member"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Try to leave without joining
    resp = client.post(f"/api/v1/projects/{project_id}/leave")
    assert resp.status_code == 400


def test_get_project_members(client):
    """Test getting project members"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Get members
    resp = client.get(f"/api/v1/projects/{project_id}/members")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "members" in body["data"]
    assert len(body["data"]["members"]) >= 1  # At least the creator


def test_get_my_projects(client):
    """Test getting current user's projects"""
    # Create multiple projects
    project_names = [faker.company() for _ in range(3)]
    project_ids = []

    for name in project_names:
        project_data = {"name": name}
        create_resp = client.post("/api/v1/projects", json=project_data)
        project_ids.append(create_resp.json()["data"]["id"])

    # Join some projects
    for project_id in project_ids[:2]:
        client.post(f"/api/v1/projects/{project_id}/join")

    # Get my projects
    resp = client.get("/api/v1/users/me/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    # Should include projects where user is member (joined + created)
    assert len(body["data"]) >= 2


def test_get_my_project_stats(client):
    """Test getting current user's project statistics"""
    # Create and join some projects
    project_names = [faker.company() for _ in range(3)]
    for name in project_names:
        project_data = {"name": name}
        create_resp = client.post("/api/v1/projects", json=project_data)
        project_id = create_resp.json()["data"]["id"]
        client.post(f"/api/v1/projects/{project_id}/join")

    # Get stats
    resp = client.get("/api/v1/users/me/project-stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    stats = body["data"]
    assert "total_projects" in stats
    assert "admin_projects" in stats
    assert "member_projects" in stats
    assert "active_projects" in stats
    assert "archived_projects" in stats
    assert stats["total_projects"] >= 3


def test_get_my_project_membership(client):
    """Test getting current user's membership in a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Get membership details
    resp = client.get(f"/api/v1/projects/{project_id}/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["role"] == "member"
    assert body["data"]["project_id"] == project_id


def test_request_role_change(client):
    """Test requesting a role change"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Request role change
    role_request = {"role": "admin"}
    resp = client.post(
        f"/api/v1/projects/{project_id}/me/request-role", json=role_request
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["requested_role"] == "admin"
    assert body["data"]["current_role"] == "member"


def test_request_same_role_change(client):
    """Test requesting a role change to the same role"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join the project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Request role change to same role
    role_request = {"role": "member"}
    resp = client.post(
        f"/api/v1/projects/{project_id}/me/request-role", json=role_request
    )
    assert resp.status_code == 400


def test_my_projects_only_filter(client):
    """Test filtering projects to show only user's projects"""
    # Create projects
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Join one project
    client.post(f"/api/v1/projects/{project_id}/join")

    # Get all projects (should include created and joined)
    resp = client.get("/api/v1/projects?my_projects_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1

    # Projects should include the one we joined
    project_ids = [p["id"] for p in body["data"]]
    assert project_id in project_ids


def test_bulk_add_members(client):
    """Test bulk adding members to a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create users to add
    users_data = []
    for _ in range(3):
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
    assert body["total_success"] == 3
    assert body["total_failed"] == 0


def test_bulk_add_members_invalid_user(client):
    """Test bulk adding members with invalid user IDs"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Try to add invalid user
    bulk_data = {
        "users": [
            {"user_id": str(uuid.uuid4()), "role": "member"},  # Invalid user ID
        ]
    }
    resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["total_failed"] == 1


def test_bulk_remove_members(client):
    """Test bulk removing members from a project"""
    # Create a project first
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Create and add users
    user_ids = []
    for _ in range(2):
        user_data = {
            "email": faker.email(),
            "name": faker.name(),
        }
        user_resp = client.post("/api/v1/users", json=user_data)
        user_id = user_resp.json()["data"]["id"]
        user_ids.append(user_id)

        # Add user to project
        member_data = {"user_id": user_id, "role": "member"}
        client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

    # Bulk remove members
    user_ids_str = ",".join(user_ids)
    resp = client.delete(
        f"/api/v1/projects/{project_id}/members/bulk?user_ids={user_ids_str}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["total_success"] == 2


def test_project_access_control(client):
    """Test that users can only access projects they're members of"""
    # Create a project
    project_data = {"name": faker.company()}
    create_resp = client.post("/api/v1/projects", json=project_data)
    project_id = create_resp.json()["data"]["id"]

    # Try to get project without being a member (should fail for non-members)
    # Note: This test assumes the creator is automatically a member
    # In a real scenario, you'd need to test with different users

    # Get project members (should work for creator)
    resp = client.get(f"/api/v1/projects/{project_id}/members")
    assert resp.status_code == 200


def test_project_filtering(client):
    """Test project filtering by various criteria"""
    # Create projects with different properties
    active_project = {"name": "Active Project", "description": "This is active"}
    archived_project = {"name": "Archived Project", "description": "This is archived"}

    # Create active project
    active_resp = client.post("/api/v1/projects", json=active_project)
    active_id = active_resp.json()["data"]["id"]

    # Create and archive project
    archived_resp = client.post("/api/v1/projects", json=archived_project)
    archived_id = archived_resp.json()["data"]["id"]
    client.patch(f"/api/v1/projects/{archived_id}/archive")

    # Filter by archived status
    resp = client.get("/api/v1/projects?is_archived=false")
    assert resp.status_code == 200
    active_projects = [p for p in resp.json()["data"] if p["id"] == active_id]
    assert len(active_projects) == 1

    # Filter by name
    resp = client.get(f"/api/v1/projects?name={active_project['name']}")
    assert resp.status_code == 200
    matching_projects = [
        p for p in resp.json()["data"] if active_project["name"] in p["name"]
    ]
    assert len(matching_projects) >= 1


def test_project_pagination_limits(client):
    """Test project pagination limits"""
    # Create multiple projects
    for _ in range(5):
        project_data = {"name": faker.company()}
        client.post("/api/v1/projects", json=project_data)

    # Test with limit
    resp = client.get("/api/v1/projects?page=1&limit=3")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) <= 3
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["limit"] == 3


def test_project_edge_cases(client):
    """Test various edge cases"""
    # Empty name (should fail)
    resp = client.post("/api/v1/projects", json={"name": ""})
    assert resp.status_code == 422

    # Very long name
    long_name = "A" * 300
    resp = client.post("/api/v1/projects", json={"name": long_name})
    assert resp.status_code == 422  # Should fail due to length limit

    # Special characters in name
    resp = client.post("/api/v1/projects", json={"name": "Project@#$%"})
    assert resp.status_code == 200  # Should work

    # Unicode characters
    resp = client.post("/api/v1/projects", json={"name": "项目名称🚀"})
    assert resp.status_code == 200  # Should work
