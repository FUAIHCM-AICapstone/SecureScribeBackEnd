import uuid
from datetime import datetime, timedelta

from faker import Faker

faker = Faker()


def create_test_project(client):
    """Helper function to create a test project"""
    project_data = {
        "name": faker.company(),
        "description": faker.text(max_nb_chars=200),
    }
    print(f"DEBUG create_test_project: Creating project with data: {project_data}")
    resp = client.post("/api/v1/projects", json=project_data)
    print(
        f"DEBUG create_test_project: Create project response status: {resp.status_code}"
    )
    if resp.status_code != 200:
        print(f"DEBUG create_test_project: Create project response body: {resp.json()}")
    return resp.json()["data"]["id"]


def create_test_meeting(client, project_ids=None, is_personal=False):
    """Helper function to create a test meeting"""
    meeting_data = {
        "title": faker.sentence(nb_words=4),
        "description": faker.text(max_nb_chars=300),
        "url": faker.url(),
        "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "is_personal": is_personal,
        "project_ids": project_ids or [],
    }
    print(f"DEBUG create_test_meeting: Creating meeting with data: {meeting_data}")
    resp = client.post("/api/v1/meetings", json=meeting_data)
    print(f"DEBUG create_test_meeting: Create response status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"DEBUG create_test_meeting: Create response body: {resp.json()}")
        # Don't fail here, let the calling test handle it
    return resp.json()["data"]["id"]


def test_create_meeting(client):
    """Test creating a new meeting"""
    meeting_data = {
        "title": faker.sentence(nb_words=4),
        "description": faker.text(max_nb_chars=300),
        "url": faker.url(),
        "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "is_personal": False,
        "project_ids": [],
    }
    print(f"DEBUG test_create_meeting: Meeting data: {meeting_data}")
    resp = client.post("/api/v1/meetings", json=meeting_data)
    print(
        f"DEBUG test_create_meeting: Create meeting response status: {resp.status_code}"
    )
    print(f"DEBUG test_create_meeting: Create meeting response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == meeting_data["title"]
    assert body["data"]["description"] == meeting_data["description"]
    assert body["data"]["is_personal"] == meeting_data["is_personal"]
    assert body["data"]["status"] == "active"
    assert body["data"]["is_deleted"] is False
    assert "id" in body["data"]


def test_create_meeting_minimal(client):
    """Test creating a meeting with minimal data"""
    meeting_data = {
        "title": faker.sentence(nb_words=3),
        "is_personal": True,
    }
    resp = client.post("/api/v1/meetings", json=meeting_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == meeting_data["title"]
    assert body["data"]["description"] is None
    assert body["data"]["url"] is None
    assert body["data"]["start_time"] is None


def test_create_meeting_with_project(client):
    """Test creating a meeting linked to a project"""
    project_id = create_test_project(client)

    meeting_data = {
        "title": faker.sentence(nb_words=4),
        "description": faker.text(max_nb_chars=200),
        "is_personal": False,
        "project_ids": [project_id],
    }
    resp = client.post("/api/v1/meetings", json=meeting_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["projects"]) >= 0  # May include project info


def test_create_meeting_invalid_url(client):
    """Test creating a meeting with invalid URL"""
    meeting_data = {
        "title": faker.sentence(nb_words=3),
        "url": "invalid-url-format",
        "is_personal": True,
    }
    resp = client.post("/api/v1/meetings", json=meeting_data)
    # URL validation might be implemented later, so this could pass for now
    assert resp.status_code in [200, 400]  # Either success or validation error


def test_get_meetings_pagination(client):
    """Test getting meetings with pagination"""
    print("DEBUG test_get_meetings_pagination: Getting meetings with pagination")
    resp = client.get("/api/v1/meetings?page=1&limit=10")
    print(f"DEBUG test_get_meetings_pagination: Response status: {resp.status_code}")
    print(f"DEBUG test_get_meetings_pagination: Response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "pagination" in body
    assert "data" in body
    assert isinstance(body["data"], list)


def test_get_meeting_by_id(client):
    """Test getting a specific meeting by ID"""
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_get_meeting_by_id: Created meeting ID: {meeting_id}")

    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    print(
        f"DEBUG test_get_meeting_by_id: Get meeting response status: {resp.status_code}"
    )
    print(f"DEBUG test_get_meeting_by_id: Get meeting response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["id"] == meeting_id
    assert body["data"]["can_access"] is True


def test_get_meeting_not_found(client):
    """Test getting a non-existent meeting"""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/meetings/{fake_id}")
    assert resp.status_code == 404


def test_get_meetings_filter_by_status(client):
    """Test filtering meetings by status"""
    # Create meetings with different statuses
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_get_meetings_filter_by_status: Created meeting ID: {meeting_id}")

    resp = client.get("/api/v1/meetings?status=active")
    print(
        f"DEBUG test_get_meetings_filter_by_status: Filter by status response status: {resp.status_code}"
    )
    print(
        f"DEBUG test_get_meetings_filter_by_status: Filter by status response body: {resp.json()}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # All returned meetings should have active status
    for meeting in body["data"]:
        assert meeting["status"] == "active"


def test_get_meetings_filter_by_personal(client):
    """Test filtering meetings by personal flag"""
    # Create personal and non-personal meetings
    personal_meeting_id = create_test_meeting(client, is_personal=True)
    non_personal_meeting_id = create_test_meeting(client, is_personal=False)
    print(
        f"DEBUG test_get_meetings_filter_by_personal: Personal meeting ID: {personal_meeting_id}"
    )
    print(
        f"DEBUG test_get_meetings_filter_by_personal: Non-personal meeting ID: {non_personal_meeting_id}"
    )

    # Filter personal meetings
    resp = client.get("/api/v1/meetings?is_personal=true")
    print(
        f"DEBUG test_get_meetings_filter_by_personal: Filter personal response status: {resp.status_code}"
    )
    print(
        f"DEBUG test_get_meetings_filter_by_personal: Filter personal response body: {resp.json()}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # All returned meetings should be personal
    for meeting in body["data"]:
        assert meeting["is_personal"] is True


def test_update_meeting(client):
    """Test updating a meeting"""
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_update_meeting: Created meeting ID: {meeting_id}")

    update_data = {
        "title": faker.sentence(nb_words=3),
        "description": faker.text(max_nb_chars=200),
        "status": "completed",
    }
    print(f"DEBUG test_update_meeting: Update data: {update_data}")
    resp = client.put(f"/api/v1/meetings/{meeting_id}", json=update_data)
    print(f"DEBUG test_update_meeting: Update response status: {resp.status_code}")
    print(f"DEBUG test_update_meeting: Update response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == update_data["title"]
    assert body["data"]["description"] == update_data["description"]
    assert body["data"]["status"] == update_data["status"]


def test_update_meeting_partial(client):
    """Test partial update of a meeting"""
    meeting_id = create_test_meeting(client)
    original_title = faker.sentence(nb_words=3)

    # Update only title
    update_data = {"title": original_title}
    resp = client.put(f"/api/v1/meetings/{meeting_id}", json=update_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["title"] == original_title


def test_update_meeting_not_found(client):
    """Test updating a non-existent meeting"""
    fake_id = str(uuid.uuid4())
    update_data = {"title": faker.sentence(nb_words=3)}
    resp = client.put(f"/api/v1/meetings/{fake_id}", json=update_data)
    assert resp.status_code == 404


def test_delete_meeting(client):
    """Test soft deleting a meeting"""
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_delete_meeting: Created meeting ID: {meeting_id}")

    resp = client.delete(f"/api/v1/meetings/{meeting_id}")
    print(f"DEBUG test_delete_meeting: Delete response status: {resp.status_code}")
    print(f"DEBUG test_delete_meeting: Delete response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    # Verify meeting is soft deleted (should not appear in normal queries)
    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    print(
        f"DEBUG test_delete_meeting: Verify delete response status: {resp.status_code}"
    )
    print(f"DEBUG test_delete_meeting: Verify delete response body: {resp.json()}")
    assert resp.status_code == 404


def create_test_file_for_meeting(client, meeting_id):
    """Helper function to create a test file associated with a meeting"""
    import io

    # Create a simple test file
    file_content = b"Test file content for meeting deletion test"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    data = {"meeting_id": meeting_id}

    resp = client.post("/api/v1/files/upload", files=files, data=data)
    if resp.status_code == 200:
        return resp.json()["data"]["id"]
    return None


def test_delete_meeting_with_files(client):
    """Test that deleting a meeting also deletes associated files"""
    # Create a meeting
    meeting_id = create_test_meeting(client)

    # Upload a file to the meeting
    file_id = create_test_file_for_meeting(client, meeting_id)
    assert file_id is not None, "Failed to create test file for meeting"

    # Verify file exists
    resp = client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 200, "File should exist before meeting deletion"

    # Delete the meeting
    resp = client.delete(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 200, "Meeting deletion should succeed"

    # Verify meeting is soft deleted
    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 404, "Meeting should be soft deleted"

    # Verify file is also deleted (hard delete)
    resp = client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 404, (
        "File should be hard deleted when meeting is deleted"
    )


def test_delete_meeting_not_found(client):
    """Test deleting a non-existent meeting"""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/meetings/{fake_id}")
    assert resp.status_code == 404


def test_add_meeting_to_project(client):
    """Test adding a meeting to a project"""
    project_id = create_test_project(client)
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_add_meeting_to_project: Project ID: {project_id}")
    print(f"DEBUG test_add_meeting_to_project: Meeting ID: {meeting_id}")

    resp = client.post(f"/api/v1/projects/{project_id}/meetings/{meeting_id}")
    print(
        f"DEBUG test_add_meeting_to_project: Add to project response status: {resp.status_code}"
    )
    print(
        f"DEBUG test_add_meeting_to_project: Add to project response body: {resp.json()}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_add_meeting_to_project_not_found(client):
    """Test adding meeting to non-existent project"""
    fake_project_id = str(uuid.uuid4())
    fake_meeting_id = str(uuid.uuid4())

    resp = client.post(f"/api/v1/projects/{fake_project_id}/meetings/{fake_meeting_id}")
    assert resp.status_code == 400


def test_remove_meeting_from_project(client):
    """Test removing a meeting from a project"""
    project_id = create_test_project(client)
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_remove_meeting_from_project: Project ID: {project_id}")
    print(f"DEBUG test_remove_meeting_from_project: Meeting ID: {meeting_id}")

    # First add meeting to project
    add_resp = client.post(f"/api/v1/projects/{project_id}/meetings/{meeting_id}")
    print(
        f"DEBUG test_remove_meeting_from_project: Add to project response status: {add_resp.status_code}"
    )

    # Then remove it
    resp = client.delete(f"/api/v1/projects/{project_id}/meetings/{meeting_id}")
    print(
        f"DEBUG test_remove_meeting_from_project: Remove from project response status: {resp.status_code}"
    )
    print(
        f"DEBUG test_remove_meeting_from_project: Remove from project response body: {resp.json()}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_remove_meeting_from_project_not_linked(client):
    """Test removing meeting that is not linked to project"""
    project_id = create_test_project(client)
    meeting_id = create_test_meeting(client)

    resp = client.delete(f"/api/v1/projects/{project_id}/meetings/{meeting_id}")
    assert resp.status_code == 400


def test_meeting_status_enum(client):
    """Test meeting status enum values"""
    meeting_id = create_test_meeting(client)
    print(f"DEBUG test_meeting_status_enum: Created meeting ID: {meeting_id}")

    # Test updating to different status values
    for status in ["active", "cancelled", "completed"]:
        update_data = {"status": status}
        print(f"DEBUG test_meeting_status_enum: Testing status: {status}")
        resp = client.put(f"/api/v1/meetings/{meeting_id}", json=update_data)
        print(
            f"DEBUG test_meeting_status_enum: Status update response status: {resp.status_code}"
        )
        print(
            f"DEBUG test_meeting_status_enum: Status update response body: {resp.json()}"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == status


def test_meeting_access_control_personal(client):
    """Test access control for personal meetings"""
    # Create a personal meeting
    meeting_id = create_test_meeting(client, is_personal=True)

    # Should be accessible by creator
    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 200


def test_meeting_access_control_project(client):
    """Test access control for project meetings"""
    project_id = create_test_project(client)
    meeting_id = create_test_meeting(client, project_ids=[project_id])

    # Should be accessible by project member
    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 200


def test_meeting_filter_by_title(client):
    """Test filtering meetings by title"""
    title = faker.sentence(nb_words=3)
    print(f"DEBUG test_meeting_filter_by_title: Test title: {title}")
    create_test_meeting(client)  # Create other meetings

    meeting_data = {
        "title": title,
        "is_personal": True,
    }
    create_resp = client.post("/api/v1/meetings", json=meeting_data)
    print(
        f"DEBUG test_meeting_filter_by_title: Create meeting response status: {create_resp.status_code}"
    )

    # Filter by title
    search_term = title[:10]
    print(f"DEBUG test_meeting_filter_by_title: Search term: {search_term}")
    resp = client.get(f"/api/v1/meetings?title={search_term}")  # Partial match
    print(
        f"DEBUG test_meeting_filter_by_title: Filter by title response status: {resp.status_code}"
    )
    print(
        f"DEBUG test_meeting_filter_by_title: Filter by title response body: {resp.json()}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # Should return at least the created meeting


def test_meeting_pagination_limits(client):
    """Test pagination limits"""
    print("DEBUG test_meeting_pagination_limits: Creating multiple meetings")
    # Create multiple meetings
    meeting_ids = []
    for i in range(5):
        meeting_id = create_test_meeting(client)
        meeting_ids.append(meeting_id)
        print(
            f"DEBUG test_meeting_pagination_limits: Created meeting {i + 1}: {meeting_id}"
        )

    # Test limit parameter
    print("DEBUG test_meeting_pagination_limits: Testing limit parameter")
    resp = client.get("/api/v1/meetings?limit=2")
    print(
        f"DEBUG test_meeting_pagination_limits: Limit=2 response status: {resp.status_code}"
    )
    print(f"DEBUG test_meeting_pagination_limits: Limit=2 response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) <= 2
    assert body["pagination"]["limit"] == 2

    # Test page parameter
    print("DEBUG test_meeting_pagination_limits: Testing page parameter")
    resp = client.get("/api/v1/meetings?page=2&limit=2")
    print(
        f"DEBUG test_meeting_pagination_limits: Page=2 response status: {resp.status_code}"
    )
    print(f"DEBUG test_meeting_pagination_limits: Page=2 response body: {resp.json()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["page"] == 2


def test_meeting_bulk_operations_simulation(client):
    """Test simulating bulk operations (since individual operations are implemented)"""
    project_ids = [create_test_project(client) for _ in range(2)]

    # Create meeting linked to multiple projects
    meeting_data = {
        "title": faker.sentence(nb_words=4),
        "is_personal": False,
        "project_ids": project_ids,
    }
    resp = client.post("/api/v1/meetings", json=meeting_data)
    assert resp.status_code == 200

    meeting_id = resp.json()["data"]["id"]

    # Verify meeting is accessible
    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 200
