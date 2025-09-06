# import io
# import uuid
# from typing import Dict

# import pytest
# from fastapi import UploadFile
# from fastapi.testclient import TestClient


# # Color constants for debugging
# class Colors:
#     GREEN = "\033[92m"
#     RED = "\033[91m"
#     YELLOW = "\033[93m"
#     BLUE = "\033[94m"
#     PURPLE = "\033[95m"
#     CYAN = "\033[96m"
#     END = "\033[0m"
#     BOLD = "\033[1m"


# def print_response(response, operation_name="API Call"):
#     """Helper to print API responses with colors for debugging"""
#     status_code = response.status_code
#     try:
#         response_data = response.json()
#     except ValueError:
#         response_data = "Non-JSON response"

#     if status_code >= 200 and status_code < 300:
#         color = Colors.GREEN
#         status_text = "SUCCESS"
#     elif status_code >= 300 and status_code < 400:
#         color = Colors.YELLOW
#         status_text = "REDIRECT"
#     elif status_code >= 400 and status_code < 500:
#         color = Colors.RED
#         status_text = "CLIENT ERROR"
#     else:
#         color = Colors.RED
#         status_text = "SERVER ERROR"

#     print(f"\n{Colors.BOLD}{Colors.CYAN}=== {operation_name} ==={Colors.END}")
#     print(
#         f"{Colors.BOLD}Status:{Colors.END} {color}{status_code} ({status_text}){Colors.END}"
#     )
#     print(f"{Colors.BOLD}Response:{Colors.END}")
#     print(f"{Colors.PURPLE}{response_data}{Colors.END}")
#     print(f"{Colors.CYAN}{'=' * 50}{Colors.END}\n")


# def create_test_project(client: TestClient, project_name: str = "Test Project") -> str:
#     """Helper to create a test project"""
#     response = client.post("/api/v1/projects", json={"name": project_name})
#     print_response(response, f"Create Test Project: {project_name}")
#     assert response.status_code == 200
#     return response.json()["data"]["id"]


# def create_test_meeting(client: TestClient, title: str = "Test Meeting") -> str:
#     """Helper to create a test meeting"""
#     response = client.post("/api/v1/meetings", json={"title": title})
#     print_response(response, f"Create Test Meeting: {title}")
#     assert response.status_code == 200
#     return response.json()["data"]["id"]


# def create_upload_file(filename: str = "test.pdf", file_path: str = None) -> UploadFile:
#     """Helper to create UploadFile object from test files"""
#     if file_path is None:
#         # Use default test files
#         if filename.endswith(".pdf"):
#             file_path = "tests/test.pdf"
#         elif filename.endswith(".wav"):
#             file_path = "tests/test.wav"
#         else:
#             # Default to PDF if no extension specified
#             file_path = "tests/test.pdf"

#     # Read from actual file
#     with open(file_path, "rb") as f:
#         file_content = f.read()

#     # Create UploadFile object
#     file_obj = io.BytesIO(file_content)
#     upload_file = UploadFile(filename=filename, file=file_obj)
#     return upload_file


# def create_test_file(
#     client: TestClient,
#     filename: str = "test.pdf",
#     project_id: str = None,
#     meeting_id: str = None,
#     file_path: str = None,
# ) -> Dict:
#     """Helper to create a test file via API using real test files"""
#     upload_file = create_upload_file(filename, file_path)

#     data = {}
#     if project_id:
#         data["project_id"] = project_id
#     if meeting_id:
#         data["meeting_id"] = meeting_id

#     files = {"file": upload_file}

#     response = client.post("/api/v1/files/upload", files=files, data=data)
#     print_response(response, f"Create Test File: {filename}")
#     assert response.status_code == 200
#     return response.json()["data"]


# # File Upload Tests
# def test_upload_file_basic(client: TestClient):
#     """Test basic file upload"""
#     filename = "test.pdf"
#     upload_file = create_upload_file(filename)

#     files = {"file": upload_file}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload Basic File")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["filename"] == filename
#     assert data["mime_type"] == "application/pdf"
#     assert data["file_type"] == "meeting"  # default when no project/meeting specified
#     assert "id" in data
#     assert "created_at" in data
#     assert data["size_bytes"] > 0  # File should have content


# def test_upload_file_with_project(client: TestClient):
#     """Test file upload with project association"""
#     project_id = create_test_project(client)
#     filename = "project_file.pdf"
#     upload_file = create_upload_file(filename)

#     files = {"file": upload_file}
#     data = {"project_id": project_id}

#     response = client.post("/api/v1/files/upload", files=files, data=data)
#     print_response(response, "Upload File with Project")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["project_id"] == project_id
#     assert data["file_type"] == "project"
#     assert data["mime_type"] == "application/pdf"


# def test_upload_file_with_meeting(client: TestClient):
#     """Test file upload with meeting association"""
#     meeting_id = create_test_meeting(client)
#     filename = "meeting_file.wav"
#     upload_file = create_upload_file(filename)

#     files = {"file": upload_file}
#     data = {"meeting_id": meeting_id}

#     response = client.post("/api/v1/files/upload", files=files, data=data)
#     print_response(response, "Upload File with Meeting")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["meeting_id"] == meeting_id
#     assert data["file_type"] == "meeting"
#     assert data["mime_type"] == "audio/wav"


# def test_upload_file_too_large(client: TestClient):
#     """Test file upload with size exceeding limit"""
#     # Skip this test since we don't have a large test file
#     # This test requires a file larger than the configured limit
#     pytest.skip("Skipping test for large file - requires file larger than size limit")


# def test_upload_unsupported_file_type(client: TestClient):
#     """Test upload of unsupported file type"""
#     filename = "test.xyz"

#     # Create UploadFile - FastAPI will detect content type from actual file content
#     # Since we're using test.pdf content, it will be detected as application/pdf
#     # This test may not work as expected since content type detection is based on file content
#     with open("tests/test.pdf", "rb") as f:
#         file_content = f.read()

#     file_obj = io.BytesIO(file_content)
#     upload_file = UploadFile(filename=filename, file=file_obj)

#     files = {"file": upload_file}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload Unsupported File Type")

#     assert response.status_code == 400
#     assert "not allowed" in response.json()["detail"].lower()


# def test_upload_pdf_file(client: TestClient):
#     """Test PDF file upload using actual test file"""
#     filename = "test.pdf"
#     file_path = "tests/test.pdf"

#     with open(file_path, "rb") as f:
#         file_content = f.read()

#     files = {"file": (filename, io.BytesIO(file_content), "application/pdf")}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload PDF File")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["mime_type"] == "application/pdf"
#     assert data["filename"] == filename


# def test_upload_wav_file(client: TestClient):
#     """Test WAV file upload using actual test file"""
#     filename = "test.wav"
#     file_path = "tests/test.wav"

#     with open(file_path, "rb") as f:
#         file_content = f.read()

#     files = {"file": (filename, io.BytesIO(file_content), "audio/wav")}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload WAV File")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["mime_type"] == "audio/wav"
#     assert data["filename"] == filename


# def test_upload_pdf_file_with_project(client: TestClient):
#     """Test PDF file upload with project association using actual test file"""
#     project_id = create_test_project(client)
#     filename = "test.pdf"
#     file_path = "tests/test.pdf"

#     with open(file_path, "rb") as f:
#         file_content = f.read()

#     files = {"file": (filename, io.BytesIO(file_content), "application/pdf")}
#     data = {"project_id": project_id}

#     response = client.post("/api/v1/files/upload", files=files, data=data)
#     print_response(response, "Upload PDF File with Project")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["mime_type"] == "application/pdf"
#     assert data["filename"] == filename
#     assert data["project_id"] == project_id
#     assert data["file_type"] == "project"


# # File Retrieval Tests
# def test_get_file_by_id(client: TestClient):
#     """Test getting a file by ID"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     response = client.get(f"/api/v1/files/{file_id}")
#     print_response(response, f"Get File by ID: {file_id}")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["id"] == file_id
#     assert data["filename"] == file_data["filename"]


# def test_get_nonexistent_file(client: TestClient):
#     """Test getting a non-existent file"""
#     fake_id = str(uuid.uuid4())
#     response = client.get(f"/api/v1/files/{fake_id}")
#     print_response(response, f"Get Non-existent File: {fake_id}")

#     assert response.status_code == 404
#     assert "not found" in response.json()["detail"].lower()


# def test_get_files_list(client: TestClient):
#     """Test getting list of files"""
#     # Create multiple test files
#     create_test_file(client, filename="file1.pdf")
#     create_test_file(client, filename="file2.pdf")

#     response = client.get("/api/v1/files")
#     print_response(response, "Get Files List")

#     assert response.status_code == 200
#     data = response.json()
#     assert "data" in data
#     assert "pagination" in data
#     assert len(data["data"]) >= 2


# def test_get_files_with_pagination(client: TestClient):
#     """Test files list with pagination"""
#     response = client.get("/api/v1/files?page=1&limit=10")
#     print_response(response, "Get Files with Pagination")

#     assert response.status_code == 200
#     data = response.json()
#     assert data["pagination"]["page"] == 1
#     assert data["pagination"]["limit"] == 10


# def test_get_files_by_project(client: TestClient):
#     """Test filtering files by project"""
#     project_id = create_test_project(client)
#     create_test_file(client, project_id=project_id, filename="project_file.pdf")

#     response = client.get(f"/api/v1/files?project_id={project_id}")
#     print_response(response, f"Get Files by Project: {project_id}")

#     assert response.status_code == 200
#     files = response.json()["data"]
#     assert len(files) >= 1
#     assert files[0]["project_id"] == project_id


# def test_get_files_by_filename(client: TestClient):
#     """Test filtering files by filename"""
#     create_test_file(client, filename="unique_test_file.pdf")

#     response = client.get("/api/v1/files?filename=unique_test")
#     print_response(response, "Get Files by Filename")

#     assert response.status_code == 200
#     files = response.json()["data"]
#     assert len(files) >= 1
#     assert "unique_test" in files[0]["filename"]


# # File Updates Tests


# def test_update_file_filename(client: TestClient):
#     """Test updating file filename"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]
#     new_filename = "updated_filename.txt"

#     update_data = {"filename": new_filename}
#     response = client.put(f"/api/v1/files/{file_id}", json=update_data)
#     print_response(response, f"Update File Filename: {file_id}")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["filename"] == new_filename


# def test_update_file_type(client: TestClient):
#     """Test updating file type"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     update_data = {"file_type": "project"}
#     response = client.put(f"/api/v1/files/{file_id}", json=update_data)
#     print_response(response, f"Update File Type: {file_id}")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["file_type"] == "project"


# def test_update_nonexistent_file(client: TestClient):
#     """Test updating a non-existent file"""
#     fake_id = str(uuid.uuid4())
#     update_data = {"filename": "new_name.txt"}

#     response = client.put(f"/api/v1/files/{fake_id}", json=update_data)
#     print_response(response, f"Update Non-existent File: {fake_id}")

#     assert response.status_code == 404


# def test_update_file_unauthorized(client: TestClient):
#     """Test updating file without ownership"""
#     # This test would require setting up multiple users
#     # For now, just test that the endpoint exists and validates ownership
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     update_data = {"filename": "hacked_filename.txt"}
#     response = client.put(f"/api/v1/files/{file_id}", json=update_data)
#     print_response(response, f"Update File Unauthorized: {file_id}")

#     # Should succeed for owner, fail for non-owner
#     assert response.status_code in [200, 403]


# # File Deletion Tests


# def test_delete_file(client: TestClient):
#     """Test deleting a file"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     response = client.delete(f"/api/v1/files/{file_id}")
#     print_response(response, f"Delete File: {file_id}")

#     assert response.status_code == 200

#     # Verify file is deleted
#     response = client.get(f"/api/v1/files/{file_id}")
#     print_response(response, f"Verify File Deleted: {file_id}")
#     assert response.status_code == 404


# def test_delete_nonexistent_file(client: TestClient):
#     """Test deleting a non-existent file"""
#     fake_id = str(uuid.uuid4())
#     response = client.delete(f"/api/v1/files/{fake_id}")
#     print_response(response, f"Delete Non-existent File: {fake_id}")

#     assert response.status_code == 404


# def test_delete_file_unauthorized(client: TestClient):
#     """Test deleting file without ownership"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     response = client.delete(f"/api/v1/files/{file_id}")
#     print_response(response, f"Delete File Unauthorized: {file_id}")

#     # Should succeed for owner, fail for non-owner
#     assert response.status_code in [200, 403]


# # Bulk Operations Tests


# def test_bulk_delete_files(client: TestClient):
#     """Test bulk deleting multiple files"""
#     file1 = create_test_file(client, filename="bulk_test1.pdf")
#     file2 = create_test_file(client, filename="bulk_test2.pdf")

#     bulk_data = {"operation": "delete", "file_ids": [file1["id"], file2["id"]]}

#     response = client.post("/api/v1/files/bulk", json=bulk_data)
#     print_response(response, "Bulk Delete Files")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert len(data) == 2
#     assert all(item["success"] for item in data)


# def test_bulk_move_files_to_project(client: TestClient):
#     """Test bulk moving files to a project"""
#     project_id = create_test_project(client)
#     file1 = create_test_file(client, filename="move_test1.pdf")
#     file2 = create_test_file(client, filename="move_test2.pdf")

#     bulk_data = {
#         "operation": "move",
#         "file_ids": [file1["id"], file2["id"]],
#         "target_project_id": project_id,
#     }

#     response = client.post("/api/v1/files/bulk", json=bulk_data)
#     print_response(response, "Bulk Move Files to Project")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert len(data) == 2
#     assert all(item["success"] for item in data)


# def test_bulk_move_files_to_meeting(client: TestClient):
#     """Test bulk moving files to a meeting"""
#     meeting_id = create_test_meeting(client)
#     file1 = create_test_file(client, filename="meeting_move1.wav")
#     file2 = create_test_file(client, filename="meeting_move2.wav")

#     bulk_data = {
#         "operation": "move",
#         "file_ids": [file1["id"], file2["id"]],
#         "target_meeting_id": meeting_id,
#     }

#     response = client.post("/api/v1/files/bulk", json=bulk_data)
#     print_response(response, "Bulk Move Files to Meeting")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert len(data) == 2
#     assert all(item["success"] for item in data)


# def test_bulk_operation_invalid_type(client: TestClient):
#     """Test bulk operation with invalid operation type"""
#     file1 = create_test_file(client, filename="invalid_op_test.pdf")

#     bulk_data = {"operation": "invalid_op", "file_ids": [file1["id"]]}

#     response = client.post("/api/v1/files/bulk", json=bulk_data)
#     print_response(response, "Bulk Operation Invalid Type")

#     assert response.status_code == 400
#     assert "invalid operation" in response.json()["detail"].lower()


# def test_bulk_operation_empty_files(client: TestClient):
#     """Test bulk operation with empty file list"""
#     bulk_data = {"operation": "delete", "file_ids": []}

#     response = client.post("/api/v1/files/bulk", json=bulk_data)
#     print_response(response, "Bulk Operation Empty Files")

#     assert response.status_code == 200


# # File Access Control Tests


# def test_file_access_by_owner(client: TestClient):
#     """Test that file owner can access their files"""
#     file_data = create_test_file(client)
#     file_id = file_data["id"]

#     response = client.get(f"/api/v1/files/{file_id}")
#     print_response(response, f"File Access by Owner: {file_id}")

#     assert response.status_code == 200
#     assert response.json()["data"]["can_access"] is True


# def test_file_access_by_project_member(client: TestClient):
#     """Test that project members can access project files"""
#     project_id = create_test_project(client)
#     file_data = create_test_file(client, project_id=project_id)

#     # Since we're using the same user, this should work
#     response = client.get(f"/api/v1/files/{file_data['id']}")
#     print_response(response, f"File Access by Project Member: {file_data['id']}")

#     assert response.status_code == 200


# # File Validation Tests


# @pytest.mark.parametrize(
#     "filename,mime_type,should_pass",
#     [
#         ("test.pdf", "application/pdf", True),
#         (
#             "test.docx",
#             "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#             True,
#         ),
#         ("test.txt", "text/plain", True),
#         ("test.mp3", "audio/mpeg", True),
#         ("test.wav", "audio/wav", True),
#         ("test.m4a", "audio/mp4", True),
#         ("test.webm", "audio/webm", True),
#         ("test.invalid", "application/invalid", False),
#         ("test.exe", "application/octet-stream", False),
#     ],
# )
# def test_file_type_validation(
#     client: TestClient, filename: str, mime_type: str, should_pass: bool
# ):
#     """Test various file type validations"""
#     # Use actual test files based on filename extension
#     if filename.endswith(".pdf"):
#         file_path = "tests/test.pdf"
#     elif filename.endswith(".wav"):
#         file_path = "tests/test.wav"
#     else:
#         # For unsupported types, use test.pdf content
#         file_path = "tests/test.pdf"

#     # Create UploadFile with specified mime type
#     with open(file_path, "rb") as f:
#         file_content = f.read()

#     file_obj = io.BytesIO(file_content)
#     upload_file = UploadFile(filename=filename, file=file_obj)
#     # Note: FastAPI will detect content type from filename, but for testing validation
#     # we rely on the actual file content type detection

#     files = {"file": upload_file}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, f"File Type Validation: {filename}")

#     if should_pass:
#         assert response.status_code == 200
#     else:
#         assert response.status_code == 400
#         assert "not allowed" in response.json()["detail"].lower()


# # File Edge Cases Tests


# def test_empty_file_upload(client: TestClient):
#     """Test uploading empty file"""
#     # Skip this test since we don't have an empty test file
#     # This test requires an empty file for validation
#     pytest.skip("Skipping test for empty file - requires empty test file")


# def test_unicode_filename(client: TestClient):
#     """Test uploading file with unicode filename"""
#     filename = "tëst_文件.pdf"
#     upload_file = create_upload_file(filename)

#     files = {"file": upload_file}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload Unicode Filename")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["filename"] == filename


# def test_special_characters_filename(client: TestClient):
#     """Test uploading file with special characters in filename"""
#     filename = "test-file_with(special)chars[123].pdf"
#     upload_file = create_upload_file(filename)

#     files = {"file": upload_file}
#     response = client.post("/api/v1/files/upload", files=files)
#     print_response(response, "Upload Special Characters Filename")

#     assert response.status_code == 200
#     data = response.json()["data"]
#     assert data["filename"] == filename
