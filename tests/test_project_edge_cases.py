# import uuid

# from faker import Faker

# faker = Faker()


# def create_project_with_member(client, member_user_id=None, member_role="member"):
#     """Helper function to create a project and optionally add a member"""
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     if member_user_id:
#         member_data = {"user_id": member_user_id, "role": member_role}
#         client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

#     return project_id


# def create_test_user(client):
#     """Helper function to create a test user"""
#     user_data = {
#         "email": faker.email(),
#         "name": faker.name(),
#     }
#     user_resp = client.post("/api/v1/users", json=user_data)
#     return user_resp.json()["data"]["id"]


# def test_project_name_validation(client):
#     """Test project name validation rules"""
#     # Test empty name
#     resp = client.post("/api/v1/projects", json={"name": ""})
#     print(
#         f"DEBUG test_project_name_validation: Empty name response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_name_validation: Empty name response body: {resp.json()}"
#     )
#     assert resp.status_code == 422

#     # Test very long name
#     long_name = "A" * 300
#     resp = client.post("/api/v1/projects", json={"name": long_name})
#     print(
#         f"DEBUG test_project_name_validation: Long name response status: {resp.status_code}"
#     )
#     print(f"DEBUG test_project_name_validation: Long name response body: {resp.json()}")
#     assert resp.status_code == 422

#     # Test name with only whitespace - should fail validation
#     resp = client.post("/api/v1/projects", json={"name": "   "})
#     print(
#         f"DEBUG test_project_name_validation: Whitespace name response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_name_validation: Whitespace name response body: {resp.json()}"
#     )
#     assert resp.status_code == 422  # Validator rejects whitespace-only names

#     # Test valid names
#     valid_names = [
#         "Project Alpha",
#         "Test_Project_123",
#         "My Project 🚀",
#         "项目名称",
#         "A",
#     ]

#     for name in valid_names:
#         resp = client.post("/api/v1/projects", json={"name": name})
#         print(
#             f"DEBUG test_project_name_validation: Valid name '{name}' response status: {resp.status_code}"
#         )
#         print(
#             f"DEBUG test_project_name_validation: Valid name '{name}' response body: {resp.json()}"
#         )
#         assert resp.status_code == 200
#         assert resp.json()["success"] is True


# def test_project_creation_edge_cases(client):
#     """Test project creation edge cases"""
#     # Test creating project with special characters
#     special_names = [
#         "Project@#$%",
#         "Test_Project_123",
#         "Project with spaces",
#         "项目名称🚀",
#         "café",
#         "naïve",
#     ]

#     for name in special_names:
#         resp = client.post("/api/v1/projects", json={"name": name})
#         assert resp.status_code == 200
#         assert resp.json()["success"] is True

#     # Test creating project with very long description
#     long_description = faker.text(max_nb_chars=5000)
#     resp = client.post(
#         "/api/v1/projects",
#         json={"name": faker.company(), "description": long_description},
#     )
#     assert resp.status_code == 200
#     assert resp.json()["success"] is True

#     # Verify long description is stored correctly (test user is automatically owner)
#     project_id = resp.json()["data"]["id"]
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     assert resp.json()["data"]["description"] == long_description


# def test_project_update_edge_cases(client):
#     """Test project update edge cases"""
#     # Create a project (test user is automatically owner)
#     project_data = {
#         "name": faker.company(),
#         "description": faker.text(max_nb_chars=200),
#     }
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Test updating with empty description (should be allowed)
#     resp = client.put(f"/api/v1/projects/{project_id}", json={"description": ""})
#     assert resp.status_code == 200
#     assert resp.json()["data"]["description"] == ""

#     # Test updating with very long description
#     long_description = faker.text(max_nb_chars=5000)
#     resp = client.put(
#         f"/api/v1/projects/{project_id}", json={"description": long_description}
#     )
#     assert resp.status_code == 200
#     assert resp.json()["data"]["description"] == long_description

#     # Test archiving via update
#     resp = client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})
#     assert resp.status_code == 200
#     assert resp.json()["data"]["is_archived"] is True

#     # Test unarchiving via update
#     resp = client.put(f"/api/v1/projects/{project_id}", json={"is_archived": False})
#     assert resp.status_code == 200
#     assert resp.json()["data"]["is_archived"] is False


# def test_project_access_denied_scenarios(client):
#     """Test scenarios where access should be denied"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Try to update project without being admin
#     # Note: In this test setup, the creator should be admin
#     # In a real multi-user scenario, you'd test with different users

#     # Try to delete project without being admin
#     fake_admin_id = str(uuid.uuid4())
#     # This would require admin privileges check

#     # Try to access non-existent project
#     fake_id = str(uuid.uuid4())
#     resp = client.get(f"/api/v1/projects/{fake_id}")
#     assert resp.status_code == 404


# def test_project_membership_edge_cases(client):
#     """Test edge cases in project membership"""
#     # Create a project (test user is automatically owner)
#     project_id = create_project_with_member(client)
#     print(f"DEBUG test_project_membership_edge_cases: Project ID: {project_id}")

#     # Test adding member with invalid user ID
#     fake_user_id = str(uuid.uuid4())
#     resp = client.post(
#         f"/api/v1/projects/{project_id}/members",
#         json={"user_id": fake_user_id, "role": "member"},
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Invalid user ID response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Invalid user ID response body: {resp.json()}"
#     )
#     assert resp.status_code == 400

#     # Test adding member to non-existent project
#     fake_project_id = str(uuid.uuid4())
#     user_id = create_test_user(client)
#     print(
#         f"DEBUG test_project_membership_edge_cases: Fake project ID: {fake_project_id}"
#     )
#     print(f"DEBUG test_project_membership_edge_cases: Valid user ID: {user_id}")

#     resp = client.post(
#         f"/api/v1/projects/{fake_project_id}/members",
#         json={"user_id": user_id, "role": "member"},
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Non-existent project response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Non-existent project response body: {resp.json()}"
#     )
#     assert resp.status_code == 403  # Access denied for non-existent project

#     # Test updating role of non-existent member
#     resp = client.put(
#         f"/api/v1/projects/{project_id}/members/{user_id}", json={"role": "admin"}
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Update non-existent member response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Update non-existent member response body: {resp.json()}"
#     )
#     assert resp.status_code == 404

#     # Test removing non-existent member
#     fake_member_id = str(uuid.uuid4())
#     resp = client.delete(f"/api/v1/projects/{project_id}/members/{fake_member_id}")
#     print(
#         f"DEBUG test_project_membership_edge_cases: Remove non-existent member response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_membership_edge_cases: Remove non-existent member response body: {resp.json()}"
#     )
#     assert resp.status_code == 404  # Should return 404 for non-existent member


# def test_project_cascading_operations(client):
#     """Test cascading effects of project operations"""
#     # Create a project (test user is automatically owner)
#     project_id = create_project_with_member(client)

#     # Add a user to the project
#     user_id = create_test_user(client)
#     member_data = {"user_id": user_id, "role": "member"}
#     client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

#     # Archive project via update
#     client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})

#     # Verify archived status is reflected in project data
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     project_data = resp.json()["data"]
#     assert project_data["is_archived"] is True


# def test_project_concurrent_operations(client):
#     """Test handling concurrent operations on projects"""
#     # Create multiple projects (test user is automatically owner of all)
#     project_ids = []
#     for i in range(3):  # Reduced to 3 to avoid overwhelming debug output
#         project_id = create_project_with_member(client)
#         project_ids.append(project_id)
#         print(
#             f"DEBUG test_project_concurrent_operations: Created project {i + 1}: {project_id}"
#         )
#     print(
#         f"DEBUG test_project_concurrent_operations: Total projects: {len(project_ids)}"
#     )

#     # Test concurrent-like operations on multiple projects
#     # Update multiple projects with different descriptions
#     for i, project_id in enumerate(project_ids):
#         resp = client.put(
#             f"/api/v1/projects/{project_id}",
#             json={
#                 "description": f"Updated description for project {i + 1}: {faker.text(max_nb_chars=50)}"
#             },
#         )
#         print(
#             f"DEBUG test_project_concurrent_operations: Update project {i + 1} response status: {resp.status_code}"
#         )
#         if resp.status_code != 200:
#             print(
#                 f"DEBUG test_project_concurrent_operations: Update project {i + 1} response body: {resp.json()}"
#             )
#         assert resp.status_code == 200

#     # Archive multiple projects via update (this replaces the non-existent /join endpoint test)
#     for i, project_id in enumerate(project_ids):
#         resp = client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})
#         print(
#             f"DEBUG test_project_concurrent_operations: Archive project {i + 1} response status: {resp.status_code}"
#         )
#         if resp.status_code != 200:
#             print(
#                 f"DEBUG test_project_concurrent_operations: Archive project {i + 1} response body: {resp.json()}"
#             )
#         assert resp.status_code == 200

#     # Test that archived projects are properly marked
#     for i, project_id in enumerate(project_ids):
#         resp = client.get(f"/api/v1/projects/{project_id}")
#         print(
#             f"DEBUG test_project_concurrent_operations: Get archived project {i + 1} response status: {resp.status_code}"
#         )
#         if resp.status_code == 200:
#             project_data = resp.json()["data"]
#             assert project_data["is_archived"] is True, (
#                 f"Project {i + 1} should be archived"
#             )


# def test_project_data_integrity(client):
#     """Test data integrity in project operations"""
#     # Create a project
#     project_data = {
#         "name": faker.company(),
#         "description": faker.text(max_nb_chars=200),
#     }
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Verify project data is stored correctly
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     retrieved = resp.json()["data"]
#     assert retrieved["name"] == project_data["name"]
#     assert retrieved["description"] == project_data["description"]
#     assert retrieved["is_archived"] is False

#     # Update project
#     updated_data = {
#         "name": faker.company(),
#         "description": faker.text(max_nb_chars=150),
#     }
#     resp = client.put(f"/api/v1/projects/{project_id}", json=updated_data)
#     assert resp.status_code == 200

#     # Verify updated data
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     retrieved = resp.json()["data"]
#     assert retrieved["name"] == updated_data["name"]
#     assert retrieved["description"] == updated_data["description"]


# def test_project_filtering_edge_cases(client):
#     """Test edge cases in project filtering"""
#     # Create projects with special characters
#     special_projects = [
#         {"name": "Project@#$%", "description": "Special chars"},
#         {"name": "Test_Project_123", "description": "Underscores"},
#         {"name": "项目名称", "description": "Unicode"},
#         {"name": "Project with spaces", "description": "Spaces"},
#     ]

#     created_projects = []
#     for project_data in special_projects:
#         resp = client.post("/api/v1/projects", json=project_data)
#         created_projects.append(resp.json()["data"])

#     # Test filtering with special characters
#     resp = client.get("/api/v1/projects?name=Project@")
#     assert resp.status_code == 200

#     # Test filtering with unicode
#     resp = client.get("/api/v1/projects?name=项目")
#     assert resp.status_code == 200

#     # Test filtering with spaces
#     resp = client.get("/api/v1/projects?name=with spaces")
#     assert resp.status_code == 200


# def test_project_bulk_error_recovery(client):
#     """Test error recovery in bulk operations"""
#     # Create a project (test user is automatically owner)
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]
#     print(f"DEBUG test_project_bulk_error_recovery: Project ID: {project_id}")

#     # Create some valid users
#     valid_users = []
#     for i in range(2):
#         user_data = {
#             "email": faker.email(),
#             "name": faker.name(),
#         }
#         resp = client.post("/api/v1/users", json=user_data)
#         valid_users.append(resp.json()["data"]["id"])
#         print(
#             f"DEBUG test_project_bulk_error_recovery: Created valid user {i + 1}: {valid_users[-1]}"
#         )

#     # Mix valid and invalid operations
#     bulk_data = {
#         "users": [
#             {"user_id": valid_users[0], "role": "member"},
#             {"user_id": valid_users[1], "role": "admin"},
#             {"user_id": str(uuid.uuid4()), "role": "member"},  # Invalid user
#             {"user_id": "invalid-uuid", "role": "admin"},  # Invalid UUID
#         ]
#     }
#     print(f"DEBUG test_project_bulk_error_recovery: Bulk data: {bulk_data}")

#     resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
#     print(
#         f"DEBUG test_project_bulk_error_recovery: Bulk add response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_bulk_error_recovery: Bulk add response body: {resp.json()}"
#     )
#     assert resp.status_code == 200
#     body = resp.json()

#     # Should handle errors gracefully
#     assert body["total_processed"] == 4
#     assert body["total_success"] >= 2  # At least the valid ones
#     assert body["total_failed"] <= 2  # At most the invalid ones

#     # Check individual results
#     results = body["data"]
#     assert len(results) == 4

#     # Valid operations should succeed
#     valid_results = [r for r in results if r["user_id"] in valid_users]
#     for result in valid_results:
#         assert result["success"] is True

#     # Invalid operations should fail
#     invalid_results = [r for r in results if r["user_id"] not in valid_users]
#     for result in invalid_results:
#         assert result["success"] is False


# def test_project_large_description(client):
#     """Test handling large description fields"""
#     # Test with very large description
#     large_description = faker.text(max_nb_chars=10000)
#     project_data = {
#         "name": faker.company(),
#         "description": large_description,
#     }

#     resp = client.post("/api/v1/projects", json=project_data)
#     # This might fail depending on database column limits
#     if resp.status_code == 200:
#         created = resp.json()["data"]
#         assert created["description"] == large_description

#         # Verify retrieval
#         resp = client.get(f"/api/v1/projects/{created['id']}")
#         retrieved = resp.json()["data"]
#         assert retrieved["description"] == large_description


# def test_project_timestamp_handling(client):
#     """Test timestamp handling in project operations"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     created = resp.json()["data"]

#     # Verify timestamps are present
#     assert "created_at" in created
#     assert "updated_at" in created

#     # Update project
#     update_data = {"name": faker.company()}
#     resp = client.put(f"/api/v1/projects/{created['id']}", json=update_data)
#     assert resp.status_code == 200

#     # Verify updated_at changed
#     updated = resp.json()["data"]
#     assert updated["updated_at"] != created["updated_at"]


# def test_project_relationship_consistency(client):
#     """Test consistency of project relationships"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Create and add a user
#     user_data = {"email": faker.email(), "name": faker.name()}
#     user_resp = client.post("/api/v1/users", json=user_data)
#     user_id = user_resp.json()["data"]["id"]

#     # Add user to project
#     member_data = {"user_id": user_id, "role": "member"}
#     client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

#     # Verify relationship from project perspective (include_members parameter)
#     resp = client.get(f"/api/v1/projects/{project_id}?include_members=true")
#     project_data = resp.json()["data"]
#     assert len(project_data["members"]) >= 1

#     # Remove user from project (admin removing member)
#     resp = client.delete(f"/api/v1/projects/{project_id}/members/{user_id}")
#     assert resp.status_code == 200

#     # Verify relationship is removed
#     resp = client.get(f"/api/v1/projects/{project_id}?include_members=true")
#     project_data = resp.json()["data"]
#     member_ids = [m["user_id"] for m in project_data["members"]]
#     assert user_id not in member_ids


# def test_project_cascading_operations(client):
#     """Test cascading effects of project operations"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Create and add a user
#     user_data = {"email": faker.email(), "name": faker.name()}
#     user_resp = client.post("/api/v1/users", json=user_data)
#     user_id = user_resp.json()["data"]["id"]

#     member_data = {"user_id": user_id, "role": "member"}
#     client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

#     # Archive project
#     client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})

#     # Verify archived status is reflected in project data
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     project_data = resp.json()["data"]
#     assert project_data["is_archived"] is True


# def test_project_search_and_filter_performance(client):
#     """Test search and filter performance with many projects"""
#     # Create many projects
#     project_names = []
#     for i in range(20):
#         name = f"{faker.company()} {i}"
#         project_names.append(name)
#         project_data = {"name": name, "description": faker.text(max_nb_chars=100)}
#         client.post("/api/v1/projects", json=project_data)

#     # Test search performance
#     search_term = project_names[0].split()[0]  # First word of first project
#     resp = client.get(f"/api/v1/projects?name={search_term}")
#     assert resp.status_code == 200
#     results = resp.json()["data"]
#     assert len(results) >= 1

#     # Test pagination with many results
#     resp = client.get("/api/v1/projects?page=1&limit=5")
#     assert resp.status_code == 200
#     paginated = resp.json()
#     assert len(paginated["data"]) <= 5
#     assert paginated["pagination"]["total"] >= 20


# def test_project_concurrent_operations(client):
#     """Test handling concurrent operations on projects"""
#     # Create multiple projects (test user is automatically owner of all)
#     project_ids = []
#     for _ in range(5):
#         project_data = {"name": faker.company()}
#         resp = client.post("/api/v1/projects", json=project_data)
#         project_ids.append(resp.json()["data"]["id"])

#     # Test concurrent-like operations on multiple projects
#     # Update multiple projects
#     for project_id in project_ids:
#         update_data = {
#             "name": faker.company(),
#             "description": faker.text(max_nb_chars=100),
#         }
#         resp = client.put(f"/api/v1/projects/{project_id}", json=update_data)
#         assert resp.status_code == 200

#     # Archive multiple projects via update (replaces non-existent /archive endpoint)
#     for project_id in project_ids:
#         resp = client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})
#         assert resp.status_code == 200


# def test_project_data_integrity(client):
#     """Test data integrity in project operations"""
#     # Create a project
#     project_data = {
#         "name": faker.company(),
#         "description": faker.text(max_nb_chars=200),
#     }
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Verify project data is stored correctly
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     retrieved = resp.json()["data"]
#     assert retrieved["name"] == project_data["name"]
#     assert retrieved["description"] == project_data["description"]
#     assert retrieved["is_archived"] is False

#     # Update project
#     updated_data = {
#         "name": faker.company(),
#         "description": faker.text(max_nb_chars=150),
#     }
#     resp = client.put(f"/api/v1/projects/{project_id}", json=updated_data)
#     assert resp.status_code == 200

#     # Verify updated data
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     retrieved = resp.json()["data"]
#     assert retrieved["name"] == updated_data["name"]
#     assert retrieved["description"] == updated_data["description"]


# def test_project_filtering_edge_cases(client):
#     """Test edge cases in project filtering"""
#     # Create projects with special characters
#     special_projects = [
#         {"name": "Project@#$%", "description": "Special chars"},
#         {"name": "Test_Project_123", "description": "Underscores"},
#         {"name": "项目名称", "description": "Unicode"},
#         {"name": "Project with spaces", "description": "Spaces"},
#     ]

#     created_projects = []
#     for project_data in special_projects:
#         resp = client.post("/api/v1/projects", json=project_data)
#         created_projects.append(resp.json()["data"])

#     # Test filtering with special characters
#     resp = client.get("/api/v1/projects?name=Project@")
#     assert resp.status_code == 200

#     # Test filtering with unicode
#     resp = client.get("/api/v1/projects?name=项目")
#     assert resp.status_code == 200

#     # Test filtering with spaces
#     resp = client.get("/api/v1/projects?name=with spaces")
#     assert resp.status_code == 200


# def test_project_bulk_error_recovery(client):
#     """Test error recovery in bulk operations"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Create some valid users
#     valid_users = []
#     for _ in range(2):
#         user_data = {
#             "email": faker.email(),
#             "name": faker.name(),
#         }
#         resp = client.post("/api/v1/users", json=user_data)
#         valid_users.append(resp.json()["data"]["id"])

#     # Mix valid and invalid operations
#     bulk_data = {
#         "users": [
#             {"user_id": valid_users[0], "role": "member"},
#             {"user_id": "invalid-id", "role": "admin"},
#             {"user_id": valid_users[1], "role": "member"},
#             {"user_id": "", "role": "admin"},  # Empty ID
#         ]
#     }

#     resp = client.post(f"/api/v1/projects/{project_id}/members/bulk", json=bulk_data)
#     print(
#         f"DEBUG test_project_bulk_error_recovery: Bulk add response status: {resp.status_code}"
#     )
#     print(
#         f"DEBUG test_project_bulk_error_recovery: Bulk add response body: {resp.json()}"
#     )
#     assert resp.status_code == 422  # Should reject invalid UUIDs

#     # Test with only valid data should succeed
#     valid_bulk_data = {
#         "users": [
#             {"user_id": valid_users[0], "role": "member"},
#             {"user_id": valid_users[1], "role": "member"},
#         ]
#     }

#     resp = client.post(
#         f"/api/v1/projects/{project_id}/members/bulk", json=valid_bulk_data
#     )
#     print(
#         f"DEBUG test_project_bulk_error_recovery: Valid bulk add response status: {resp.status_code}"
#     )
#     if resp.status_code == 200:
#         body = resp.json()
#         assert body["total_processed"] == 2
#         assert body["total_success"] == 2

#     # Check individual results for valid bulk operation
#     results = body["data"]
#     assert len(results) == 2

#     # All operations should succeed (valid users)
#     for result in results:
#         assert result["success"] is True
#         assert result["user_id"] in valid_users


# def test_project_large_description(client):
#     """Test handling large description fields"""
#     # Test with very large description
#     large_description = faker.text(max_nb_chars=10000)
#     project_data = {
#         "name": faker.company(),
#         "description": large_description,
#     }

#     resp = client.post("/api/v1/projects", json=project_data)
#     # This might fail depending on database column limits
#     if resp.status_code == 200:
#         created = resp.json()["data"]
#         assert created["description"] == large_description

#         # Verify retrieval
#         resp = client.get(f"/api/v1/projects/{created['id']}")
#         retrieved = resp.json()["data"]
#         assert retrieved["description"] == large_description


# def test_project_timestamp_handling(client):
#     """Test timestamp handling in project operations"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     created = resp.json()["data"]

#     # Verify timestamps are present
#     assert "created_at" in created
#     assert "updated_at" in created

#     # Update project
#     update_data = {"name": faker.company()}
#     resp = client.put(f"/api/v1/projects/{created['id']}", json=update_data)
#     assert resp.status_code == 200

#     # Verify updated_at changed
#     updated = resp.json()["data"]
#     assert updated["updated_at"] != created["updated_at"]


# def test_project_cascading_operations(client):
#     """Test cascading effects of project operations"""
#     # Create a project
#     project_data = {"name": faker.company()}
#     resp = client.post("/api/v1/projects", json=project_data)
#     project_id = resp.json()["data"]["id"]

#     # Add a user to project
#     user_data = {"email": faker.email(), "name": faker.name()}
#     user_resp = client.post("/api/v1/users", json=user_data)
#     user_id = user_resp.json()["data"]["id"]
#     member_data = {"user_id": user_id, "role": "member"}
#     client.post(f"/api/v1/projects/{project_id}/members", json=member_data)

#     # Archive project via update
#     client.put(f"/api/v1/projects/{project_id}", json={"is_archived": True})

#     # Verify archived status in direct project query
#     resp = client.get(f"/api/v1/projects/{project_id}")
#     project_data = resp.json()["data"]
#     assert project_data["is_archived"] is True


# def test_project_search_and_filter_performance(client):
#     """Test search and filter performance with many projects"""
#     # Create many projects
#     project_names = []
#     for i in range(20):
#         name = f"{faker.company()} {i}"
#         project_names.append(name)
#         project_data = {"name": name, "description": faker.text(max_nb_chars=100)}
#         client.post("/api/v1/projects", json=project_data)

#     # Test search performance
#     search_term = project_names[0].split()[0]  # First word of first project
#     resp = client.get(f"/api/v1/projects?name={search_term}")
#     assert resp.status_code == 200
#     results = resp.json()["data"]
#     assert len(results) >= 1

#     # Test pagination with many results
#     resp = client.get("/api/v1/projects?page=1&limit=5")
#     assert resp.status_code == 200
#     paginated = resp.json()
#     assert len(paginated["data"]) <= 5
#     assert paginated["pagination"]["total"] >= 20
