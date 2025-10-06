# import uuid

# import pytest
# from faker import Faker

# from app.models.tag import Tag
# from app.schemas.tag import TagCreate, TagUpdate

# faker = Faker()


# def create_test_tag(client, name=None, scope="global"):
#     """Helper function to create a test tag"""
#     tag_data = {
#         "name": name or faker.word(),
#         "scope": scope,
#     }
#     resp = client.post("/api/v1/tags", json=tag_data)
#     return resp.json()["data"]


# def test_create_tag_success(client):
#     """Test creating a new tag successfully"""
#     tag_data = {
#         "name": faker.word(),
#         "scope": "global",
#     }

#     resp = client.post("/api/v1/tags", json=tag_data)
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"]["name"] == tag_data["name"]
#     assert body["data"]["scope"] == tag_data["scope"]
#     assert body["data"]["created_by"] is not None
#     assert body["data"]["meeting_count"] == 0


# def test_create_tag_minimal_data(client):
#     """Test creating a tag with minimal data"""
#     tag_data = {"name": faker.word()}

#     resp = client.post("/api/v1/tags", json=tag_data)
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"]["name"] == tag_data["name"]
#     assert body["data"]["scope"] == "global"  # Default scope


# def test_create_tag_duplicate_name_same_scope(client):
#     """Test creating a tag with duplicate name in same scope"""
#     tag_name = faker.word()

#     # Create first tag
#     tag_data1 = {"name": tag_name, "scope": "global"}
#     resp1 = client.post("/api/v1/tags", json=tag_data1)
#     assert resp.status_code == 200

#     # Try to create second tag with same name and scope
#     tag_data2 = {"name": tag_name, "scope": "global"}
#     resp2 = client.post("/api/v1/tags", json=tag_data2)
#     # This might succeed or fail depending on validation logic
#     assert resp2.status_code in [200, 400]


# def test_create_tag_different_scopes_same_name(client):
#     """Test creating tags with same name but different scopes"""
#     tag_name = faker.word()

#     # Create first tag in global scope
#     tag_data1 = {"name": tag_name, "scope": "global"}
#     resp1 = client.post("/api/v1/tags", json=tag_data1)
#     assert resp1.status_code == 200

#     # Create second tag with same name but project scope
#     tag_data2 = {"name": tag_name, "scope": "project"}
#     resp2 = client.post("/api/v1/tags", json=tag_data2)
#     assert resp2.status_code == 200

#     body2 = resp2.json()
#     assert body2["data"]["name"] == tag_name
#     assert body2["data"]["scope"] == "project"


# def test_get_tags_empty_list(client):
#     """Test getting tags when no tags exist"""
#     resp = client.get("/api/v1/tags")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"] == []
#     assert body["pagination"]["total"] == 0


# def test_get_tags_with_pagination(client):
#     """Test getting tags with pagination"""
#     # Create multiple tags
#     for i in range(5):
#         create_test_tag(client, name=f"tag_{i}")

#     # Test default pagination
#     resp = client.get("/api/v1/tags")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert len(body["data"]) <= 20  # Default limit
#     assert body["pagination"]["total"] >= 5

#     # Test custom limit
#     resp = client.get("/api/v1/tags?limit=2")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert len(body["data"]) <= 2
#     assert body["pagination"]["limit"] == 2


# def test_get_tag_by_id(client):
#     """Test getting a specific tag by ID"""
#     # Create a tag
#     tag = create_test_tag(client)
#     tag_id = tag["id"]

#     # Get the tag by ID
#     resp = client.get(f"/api/v1/tags/{tag_id}")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"]["id"] == tag_id
#     assert body["data"]["name"] == tag["name"]
#     assert body["data"]["scope"] == tag["scope"]


# def test_get_tag_not_found(client):
#     """Test getting a non-existent tag"""
#     fake_id = str(uuid.uuid4())
#     resp = client.get(f"/api/v1/tags/{fake_id}")
#     assert resp.status_code == 404
#     body = resp.json()
#     assert body["success"] is False
#     assert "not found" in body["message"].lower()


# def test_update_tag_success(client):
#     """Test updating a tag successfully"""
#     # Create a tag
#     tag = create_test_tag(client)
#     tag_id = tag["id"]

#     # Update the tag
#     update_data = {"name": "updated_tag_name", "scope": "project"}

#     resp = client.put(f"/api/v1/tags/{tag_id}", json=update_data)
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"]["name"] == update_data["name"]
#     assert body["data"]["scope"] == update_data["scope"]


# def test_update_tag_partial(client):
#     """Test partial update of a tag"""
#     # Create a tag
#     tag = create_test_tag(client)
#     tag_id = tag["id"]
#     original_scope = tag["scope"]

#     # Update only the name
#     update_data = {"name": "partially_updated_tag"}

#     resp = client.put(f"/api/v1/tags/{tag_id}", json=update_data)
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"]["name"] == update_data["name"]
#     assert body["data"]["scope"] == original_scope  # Should remain unchanged


# def test_update_tag_not_found(client):
#     """Test updating a non-existent tag"""
#     fake_id = str(uuid.uuid4())
#     update_data = {"name": "nonexistent_tag"}

#     resp = client.put(f"/api/v1/tags/{fake_id}", json=update_data)
#     assert resp.status_code == 404


# def test_delete_tag_success(client):
#     """Test soft deleting a tag successfully"""
#     # Create a tag
#     tag = create_test_tag(client)
#     tag_id = tag["id"]

#     # Delete the tag
#     resp = client.delete(f"/api/v1/tags/{tag_id}")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True

#     # Verify tag is soft deleted (should not appear in normal queries)
#     resp = client.get(f"/api/v1/tags/{tag_id}")
#     assert resp.status_code == 404


# def test_delete_tag_not_found(client):
#     """Test deleting a non-existent tag"""
#     fake_id = str(uuid.uuid4())
#     resp = client.delete(f"/api/v1/tags/{fake_id}")
#     assert resp.status_code == 404


# def test_bulk_create_tags_success(client):
#     """Test bulk creating tags successfully"""
#     tags_data = [{"name": f"bulk_tag_{i}", "scope": "global"} for i in range(3)]

#     bulk_data = {"tags": tags_data}
#     resp = client.post("/api/v1/tags/bulk", json={"action": "create", "bulk_data": bulk_data})

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert len(body["data"]) == 3

#     # Verify all tags were created
#     for tag_data in tags_data:
#         resp = client.get(f"/api/v1/tags?name={tag_data['name']}")
#         assert resp.status_code == 200
#         search_body = resp.json()
#         assert len(search_body["data"]) >= 1


# def test_bulk_update_tags_success(client):
#     """Test bulk updating tags successfully"""
#     # Create some tags first
#     tags = [create_test_tag(client) for _ in range(3)]
#     tag_ids = [tag["id"] for tag in tags]

#     # Prepare bulk update data
#     updates_data = [
#         {"id": tag_ids[0], "name": "updated_name_0"},
#         {"id": tag_ids[1], "name": "updated_name_1"},
#     ]

#     resp = client.post("/api/v1/tags/bulk", json={"action": "update", "bulk_data": {"updates": updates_data}})

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert len(body["data"]) == 2

#     # Verify updates
#     for update in updates_data:
#         resp = client.get(f"/api/v1/tags/{update['id']}")
#         assert resp.status_code == 200
#         tag_body = resp.json()
#         assert tag_body["data"]["name"] == update["name"]


# def test_bulk_delete_tags_success(client):
#     """Test bulk deleting tags successfully"""
#     # Create some tags first
#     tags = [create_test_tag(client) for _ in range(3)]
#     tag_ids = [tag["id"] for tag in tags]

#     # Delete tags in bulk
#     resp = client.post("/api/v1/tags/bulk", json={"action": "delete", "bulk_data": {"tag_ids": tag_ids}})

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True

#     # Verify all tags are deleted
#     for tag_id in tag_ids:
#         resp = client.get(f"/api/v1/tags/{tag_id}")
#         assert resp.status_code == 404


# def test_search_tags_success(client):
#     """Test searching tags by name"""
#     # Create tags with specific names
#     tag_names = ["urgent", "meeting", "project", "urgent_meeting"]
#     for name in tag_names:
#         create_test_tag(client, name=name)

#     # Search for "urgent"
#     resp = client.get("/api/v1/tags/search?q=urgent")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert len(body["data"]) >= 2  # Should find "urgent" and "urgent_meeting"

#     # Verify all returned tags contain "urgent"
#     for tag in body["data"]:
#         assert "urgent" in tag["name"]


# def test_search_tags_no_results(client):
#     """Test searching tags with no matching results"""
#     # Create some tags
#     create_test_tag(client, name="meeting")
#     create_test_tag(client, name="project")

#     # Search for something that doesn't exist
#     resp = client.get("/api/v1/tags/search?q=nonexistent")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert body["data"] == []


# def test_get_tag_statistics(client):
#     """Test getting tag statistics"""
#     # Create tags
#     tag1 = create_test_tag(client, name="tag1")
#     tag2 = create_test_tag(client, name="tag2")

#     # Get statistics for specific tags
#     tag_ids = f"{tag1['id']},{tag2['id']}"
#     resp = client.get(f"/api/v1/tags/statistics?tag_ids={tag_ids}")

#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body
#     # Statistics should include meeting counts for the tags
#     assert isinstance(body["data"], dict)


# def test_get_user_tags(client):
#     """Test getting tags created by current user"""
#     # Create some tags
#     tag1 = create_test_tag(client, name="user_tag1")
#     tag2 = create_test_tag(client, name="user_tag2")

#     # Get user tags
#     resp = client.get("/api/v1/users/me/tags")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True
#     assert "data" in body
#     assert isinstance(body["data"], list)

#     # Should include the tags we created
#     tag_names = [tag["name"] for tag in body["data"]]
#     assert "user_tag1" in tag_names
#     assert "user_tag2" in tag_names


# def test_tag_filter_by_scope(client):
#     """Test filtering tags by scope"""
#     # Create tags with different scopes
#     create_test_tag(client, name="global_tag", scope="global")
#     create_test_tag(client, name="project_tag", scope="project")

#     # Filter by global scope
#     resp = client.get("/api/v1/tags?scope=global")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True

#     # All returned tags should be global scope
#     for tag in body["data"]:
#         assert tag["scope"] == "global"


# def test_tag_filter_by_name(client):
#     """Test filtering tags by name"""
#     # Create tags
#     create_test_tag(client, name="important_meeting")
#     create_test_tag(client, name="project_review")

#     # Filter by name containing "meeting"
#     resp = client.get("/api/v1/tags?name=meeting")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True

#     # Should find the tag with "meeting" in name
#     assert len(body["data"]) >= 1
#     for tag in body["data"]:
#         assert "meeting" in tag["name"]


# def test_tag_filter_by_usage_count(client):
#     """Test filtering tags by usage count"""
#     # This test would require actual meetings with tags
#     # For now, just test that the endpoint accepts the parameters
#     resp = client.get("/api/v1/tags?min_usage_count=0&max_usage_count=10")
#     assert resp.status_code == 200
#     body = resp.json()
#     assert body["success"] is True


# def test_tag_crud_full_lifecycle(client):
#     """Test complete CRUD lifecycle of a tag"""
#     # Create
#     tag_data = {"name": "lifecycle_test", "scope": "project"}
#     create_resp = client.post("/api/v1/tags", json=tag_data)
#     assert create_resp.status_code == 200
#     tag_id = create_resp.json()["data"]["id"]

#     # Read
#     read_resp = client.get(f"/api/v1/tags/{tag_id}")
#     assert read_resp.status_code == 200
#     assert read_resp.json()["data"]["name"] == "lifecycle_test"

#     # Update
#     update_data = {"name": "updated_lifecycle_test"}
#     update_resp = client.put(f"/api/v1/tags/{tag_id}", json=update_data)
#     assert update_resp.status_code == 200
#     assert update_resp.json()["data"]["name"] == "updated_lifecycle_test"

#     # Delete
#     delete_resp = client.delete(f"/api/v1/tags/{tag_id}")
#     assert delete_resp.status_code == 200

#     # Verify deletion
#     final_read_resp = client.get(f"/api/v1/tags/{tag_id}")
#     assert final_read_resp.status_code == 404

