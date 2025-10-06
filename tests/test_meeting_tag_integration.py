# import uuid

# import pytest
# from faker import Faker

# from app.models.tag import Tag
# from app.schemas.tag import TagCreate

# faker = Faker()


# def create_test_tag(client, name=None, scope="global"):
#     """Helper function to create a test tag"""
#     tag_data = {
#         "name": name or faker.word(),
#         "scope": scope,
#     }
#     resp = client.post("/api/v1/tags", json=tag_data)
#     return resp.json()["data"]


# def create_test_meeting_with_tags(client, tag_ids=None, **meeting_data):
#     """Helper function to create a test meeting"""
#     default_data = {
#         "title": faker.sentence(nb_words=4),
#         "description": faker.text(max_nb_chars=300),
#         "url": faker.url(),
#         "is_personal": False,
#     }
#     meeting_data.update(default_data)

#     # For now, we'll create meetings without direct tag association
#     # since we need to understand how tags are associated with meetings
#     resp = client.post("/api/v1/meetings", json=meeting_data)
#     return resp.json()["data"]


# def test_meeting_response_includes_tags(client):
#     """Test that meeting responses include tags"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get the meeting by ID
#     resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body
#     meeting_data = body["data"]

#     # Check that tags field exists in response
#     assert "tags" in meeting_data
#     assert isinstance(meeting_data["tags"], list)


# def test_meeting_list_includes_tags(client):
#     """Test that meeting list responses include tags"""
#     # Create a meeting
#     create_test_meeting_with_tags(client)

#     # Get meetings list
#     resp = client.get("/api/v1/meetings")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body

#     # Check that each meeting in the list has tags
#     for meeting in body["data"]:
#         assert "tags" in meeting
#         assert isinstance(meeting["tags"], list)


# def test_meeting_filter_by_tag_ids(client):
#     """Test filtering meetings by tag IDs"""
#     # Create some tags first
#     tag1 = create_test_tag(client, name="urgent")
#     tag2 = create_test_tag(client, name="weekly")

#     # Create meetings (without tags for now, since we need to understand
#     # how to associate tags with meetings)

#     # Test filtering with tag IDs (comma-separated string)
#     tag_ids_param = f"{tag1['id']},{tag2['id']}"
#     resp = client.get(f"/api/v1/meetings?tag_ids={tag_ids_param}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body
#     assert isinstance(body["data"], list)

#     # The response should be valid even if no meetings match the tag filter


# def test_meeting_filter_by_single_tag_id(client):
#     """Test filtering meetings by a single tag ID"""
#     # Create a tag
#     tag = create_test_tag(client, name="single_tag")

#     # Test filtering with single tag ID
#     resp = client.get(f"/api/v1/meetings?tag_ids={tag['id']}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body
#     assert isinstance(body["data"], list)


# def test_meeting_filter_by_invalid_tag_id(client):
#     """Test filtering meetings by invalid tag ID"""
#     # Use a fake UUID that doesn't exist
#     fake_tag_id = str(uuid.uuid4())
#     resp = client.get(f"/api/v1/meetings?tag_ids={fake_tag_id}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     # Should return empty list or handle gracefully
#     assert isinstance(body["data"], list)


# def test_meeting_filter_by_empty_tag_ids(client):
#     """Test filtering meetings with empty tag_ids parameter"""
#     resp = client.get("/api/v1/meetings?tag_ids=")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert isinstance(body["data"], list)


# def test_meeting_response_structure_with_tags(client):
#     """Test that meeting response structure properly includes tag information"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get meeting details
#     resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#     assert resp.status_code == 200
#     body = resp.json()
#     meeting_data = body["data"]

#     # Verify expected fields are present
#     expected_fields = ["id", "title", "description", "url", "start_time", "created_by", "is_personal", "status", "is_deleted", "created_at", "updated_at", "projects", "tags", "can_access"]

#     for field in expected_fields:
#         assert field in meeting_data, f"Missing field: {field}"

#     # Verify tags field structure
#     assert isinstance(meeting_data["tags"], list)
#     if meeting_data["tags"]:  # If there are any tags
#         for tag in meeting_data["tags"]:
#             # Each tag should have expected fields
#             tag_fields = ["id", "name", "scope", "created_by", "created_at", "updated_at", "meeting_count"]
#             for field in tag_fields:
#                 assert field in tag, f"Tag missing field: {field}"


# def test_meeting_list_response_structure_with_tags(client):
#     """Test that meeting list response structure properly includes tag information"""
#     # Create a meeting
#     create_test_meeting_with_tags(client)

#     # Get meetings list
#     resp = client.get("/api/v1/meetings")
#     assert resp.status_code == 200
#     body = resp.json()
#     meetings_data = body["data"]

#     # Check each meeting in the list
#     for meeting in meetings_data:
#         # Verify expected fields are present
#         expected_fields = ["id", "title", "description", "url", "start_time", "created_by", "is_personal", "status", "is_deleted", "created_at", "updated_at", "projects", "tags", "can_access"]

#         for field in expected_fields:
#             assert field in meeting, f"Meeting missing field: {field}"

#         # Verify tags field structure
#         assert isinstance(meeting["tags"], list)


# def test_meeting_pagination_with_tag_filtering(client):
#     """Test pagination works correctly with tag filtering"""
#     # Create multiple meetings
#     for i in range(5):
#         create_test_meeting_with_tags(client, title=f"Meeting {i}")

#     # Create some tags for filtering
#     tag1 = create_test_tag(client, name="pagination_test")

#     # Test pagination with tag filter
#     resp = client.get(f"/api/v1/meetings?tag_ids={tag1['id']}&page=1&limit=2")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "pagination" in body
#     assert "data" in body

#     # Check pagination metadata
#     pagination = body["pagination"]
#     assert pagination["page"] == 1
#     assert pagination["limit"] == 2
#     assert "total" in pagination
#     assert isinstance(pagination["total"], int)


# def test_meeting_tags_in_response_metadata(client):
#     """Test that meeting responses include proper metadata about tags"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get meeting details
#     resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#     assert resp.status_code == 200
#     body = resp.json()
#     meeting_data = body["data"]

#     # The response should include project_count and member_count
#     # as seen in the meeting endpoint code
#     assert "project_count" in meeting_data
#     assert "member_count" in meeting_data
#     assert isinstance(meeting_data["project_count"], int)
#     assert isinstance(meeting_data["member_count"], int)


# def test_meeting_filter_combination_with_tags(client):
#     """Test filtering meetings with combination of parameters including tags"""
#     # Create some meetings with different properties
#     personal_meeting = create_test_meeting_with_tags(client, is_personal=True, title="Personal Meeting")
#     project_meeting = create_test_meeting_with_tags(client, is_personal=False, title="Project Meeting")

#     # Create a tag for filtering
#     tag = create_test_tag(client, name="combo_test")

#     # Test filtering by personal flag and tag IDs
#     resp = client.get(f"/api/v1/meetings?is_personal=true&tag_ids={tag['id']}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert isinstance(body["data"], list)

#     # Test filtering by status and tag IDs
#     resp = client.get(f"/api/v1/meetings?status=active&tag_ids={tag['id']}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert isinstance(body["data"], list)


# def test_meeting_tag_relationship_validation(client):
#     """Test that tag relationships in meeting responses are properly validated"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get meeting details multiple times to ensure consistency
#     for i in range(3):
#         resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#         assert resp.status_code == 200
#         body = resp.json()
#         meeting_data = body["data"]

#         # Ensure tags field is always present and consistent type
#         assert "tags" in meeting_data
#         assert isinstance(meeting_data["tags"], list)

#         # Ensure each tag has required fields if present
#         for tag in meeting_data["tags"]:
#             required_tag_fields = ["id", "name", "scope", "created_by"]
#             for field in required_tag_fields:
#                 assert field in tag, f"Tag missing required field: {field}"


# def test_meeting_response_can_access_with_tags(client):
#     """Test that can_access field works correctly with tag-related queries"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get meeting details
#     resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#     assert resp.status_code == 200
#     body = resp.json()
#     meeting_data = body["data"]

#     # Verify can_access field is present and is boolean
#     assert "can_access" in meeting_data
#     assert isinstance(meeting_data["can_access"], bool)
#     assert meeting_data["can_access"] is True  # Should be accessible to creator


# def test_meeting_tag_count_in_response(client):
#     """Test that tag count information is properly included in meeting responses"""
#     # Create a meeting
#     meeting = create_test_meeting_with_tags(client)

#     # Get meeting details
#     resp = client.get(f"/api/v1/meetings/{meeting['id']}")
#     assert resp.status_code == 200
#     body = resp.json()
#     meeting_data = body["data"]

#     # Check that tags are included
#     assert "tags" in meeting_data
#     tags = meeting_data["tags"]

#     # Each tag should have a meeting_count field (even if 0)
#     for tag in tags:
#         assert "meeting_count" in tag
#         assert isinstance(tag["meeting_count"], int)


# def test_meeting_tag_search_integration(client):
#     """Test that tag search functionality works in meeting context"""
#     # Create tags with searchable names
#     urgent_tag = create_test_tag(client, name="urgent_meeting")
#     weekly_tag = create_test_tag(client, name="weekly_standup")

#     # Search for tags
#     resp = client.get("/api/v1/tags/search?q=urgent")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True

#     # Should find the urgent tag
#     found_urgent = False
#     for tag in body["data"]:
#         if tag["name"] == "urgent_meeting":
#             found_urgent = True
#             break
#     assert found_urgent, "Should find urgent_meeting tag in search results"

