"""Integration tests for file workflows"""

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.file import File
from app.utils.auth import create_access_token
from tests.factories import FileFactory, MeetingFactory, ProjectFactory, UserFactory

fake = Faker()


class TestFileUploadAndStorage:
    """Integration tests for file upload and storage workflow"""

    def test_file_creation_creates_database_record(self, db_session: Session):
        """Test that file creation creates a record in the database"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename=fake.file_name(extension="pdf"),
            mime_type="application/pdf",
            file_type="document",
        )
        db_session.commit()

        # Assert
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.filename == "test_document.pdf"
            assert db_file.uploaded_by == uploader.id
            assert db_file.file_type == "document"
            assert db_file.mime_type == "application/pdf"
        finally:
            fresh_session.close()

    def test_file_creation_with_project_association(self, db_session: Session):
        """Test that file creation with project association persists correctly"""
        # Arrange
        uploader = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        db_session.commit()

        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            project=project,
            filename=fake.file_name(extension="pdf"),
            mime_type="application/pdf",
            file_type="document",
        )
        db_session.commit()

        # Assert
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.project_id == project.id
        finally:
            fresh_session.close()

    def test_file_creation_with_meeting_association(self, db_session: Session):
        """Test that file creation with meeting association persists correctly"""
        # Arrange
        uploader = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=uploader)
        db_session.commit()

        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            meeting=meeting,
            filename=fake.file_name(extension="pdf"),
            mime_type="application/pdf",
            file_type="document",
        )
        db_session.commit()

        # Assert
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.meeting_id == meeting.id
        finally:
            fresh_session.close()

    def test_file_creation_stores_metadata(self, db_session: Session):
        """Test that file creation stores all metadata correctly"""
        # Arrange
        uploader = UserFactory.create(db_session)
        db_session.commit()

        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename=fake.file_name(extension="pdf"),
            mime_type="application/pdf",
            file_type="document",
            size_bytes=2048,
        )
        db_session.commit()

        # Assert
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.filename == "metadata_test.pdf"
            assert db_file.mime_type == "application/pdf"
            assert db_file.file_type == "document"
            assert db_file.uploaded_by == uploader.id
            assert db_file.created_at is not None
            assert db_file.size_bytes == 2048
        finally:
            fresh_session.close()


class TestFileAccessControlAndDeletion:
    """Integration tests for file access control and deletion workflow"""

    def test_file_access_control_owner_can_access(self, db_session: Session):
        """Test that file owner can access their file"""
        # Arrange
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader)
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == str(file.id)

    def test_file_access_control_project_member_can_access(self, db_session: Session):
        """Test that project member can access project files"""
        # Arrange
        uploader = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        db_session.commit()

        # Add member to project
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, member.id, "member")

        file = FileFactory.create(db_session, uploaded_by=uploader, project=project)
        db_session.commit()

        access_token = create_access_token({"sub": str(member.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == str(file.id)

    def test_file_deletion_removes_from_database(self, db_session: Session):
        """Test that file deletion removes file from database"""
        # Arrange
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader)
        file_id = file.id
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/files/{file_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted from database with fresh session
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is None
        finally:
            fresh_session.close()

    def test_file_deletion_by_owner(self, db_session: Session):
        """Test that file owner can delete their file"""
        # Arrange
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader)
        file_id = file.id
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/files/{file_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is None
        finally:
            fresh_session.close()

    def test_file_deletion_by_project_admin(self, db_session: Session):
        """Test that project admin can delete project files"""
        # Arrange
        creator = UserFactory.create(db_session)
        uploader = UserFactory.create(db_session)
        admin = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add admin to project
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, admin.id, "admin")

        file = FileFactory.create(db_session, uploaded_by=uploader, project=project)
        file_id = file.id
        db_session.commit()

        access_token = create_access_token({"sub": str(admin.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/files/{file_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is None
        finally:
            fresh_session.close()

    def test_file_deletion_by_non_owner_fails(self, db_session: Session):
        """Test that non-owner cannot delete file"""
        # Arrange
        uploader = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader)
        db_session.commit()

        access_token = create_access_token({"sub": str(other_user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 403

        # Verify file still exists
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
        finally:
            fresh_session.close()


class TestDocumentProcessingAndIndexing:
    """Integration tests for document processing and indexing workflow"""

    def test_file_metadata_update_persists(self, db_session: Session):
        """Test that file metadata updates persist to database"""
        # Arrange
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader, filename="original.pdf")
        db_session.commit()

        update_data = {
            "filename": "updated.pdf",
        }

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/files/{file.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["filename"] == "updated.pdf"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.filename == "updated.pdf"
        finally:
            fresh_session.close()

    def test_file_type_persists_correctly(self, db_session: Session):
        """Test that file type is stored correctly in database"""
        # Arrange
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=uploader, file_type="document")
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["file_type"] == "document"

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.file_type == "document"
        finally:
            fresh_session.close()

    def test_file_retrieval_with_project_info(self, db_session: Session):
        """Test that file retrieval includes project information"""
        # Arrange
        uploader = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        file = FileFactory.create(db_session, uploaded_by=uploader, project=project)
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["project_id"] == str(project.id)

    def test_file_retrieval_with_meeting_info(self, db_session: Session):
        """Test that file retrieval includes meeting information"""
        # Arrange
        uploader = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=uploader)
        file = FileFactory.create(db_session, uploaded_by=uploader, meeting=meeting)
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.get(f"/api/v1/files/{file.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["meeting_id"] == str(meeting.id)


class TestFileWorkflowDataPersistence:
    """Integration tests for file workflow data persistence"""

    def test_file_data_persists_across_sessions(self, db_session: Session):
        """Test that file data persists across database sessions"""
        # Arrange: Create file in one session
        uploader = UserFactory.create(db_session)
        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            filename="persistence_test.pdf",
            mime_type="application/pdf",
            file_type="document",
        )
        file_id = file.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve file in new session
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()

            # Assert
            assert db_file is not None
            assert db_file.filename == "persistence_test.pdf"
            assert db_file.mime_type == "application/pdf"
            assert db_file.file_type == "document"
        finally:
            fresh_session.close()

    def test_file_project_association_persists(self, db_session: Session):
        """Test that file project association persists correctly"""
        # Arrange: Create file with project
        uploader = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        file = FileFactory.create(db_session, uploaded_by=uploader, project=project)
        file_id = file.id
        project_id = project.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()

            # Assert
            assert db_file is not None
            assert db_file.project_id == project_id
        finally:
            fresh_session.close()

    def test_file_meeting_association_persists(self, db_session: Session):
        """Test that file meeting association persists correctly"""
        # Arrange: Create file with meeting
        uploader = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=uploader)
        file = FileFactory.create(db_session, uploaded_by=uploader, meeting=meeting)
        file_id = file.id
        meeting_id = meeting.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()

            # Assert
            assert db_file is not None
            assert db_file.meeting_id == meeting_id
        finally:
            fresh_session.close()

    def test_complete_file_workflow_persistence(self, db_session: Session):
        """Test complete file workflow: create, update metadata, verify persistence"""
        # Arrange
        uploader = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        db_session.commit()

        # Act 1: Create file
        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            project=project,
            filename="complete_workflow.pdf",
            mime_type="application/pdf",
            file_type="document",
        )
        db_session.commit()
        file_id = file.id

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 2: Update metadata
        update_response = client.put(
            f"/api/v1/files/{file_id}",
            json={"filename": "updated_workflow.pdf"},
        )
        assert update_response.status_code == 200

        # Assert: Verify all data persisted correctly
        fresh_session = SessionLocal()
        try:
            # Verify file
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is not None
            assert db_file.filename == "updated_workflow.pdf"
            assert db_file.mime_type == "application/pdf"
            assert db_file.file_type == "document"
            assert db_file.project_id == project.id
            assert db_file.uploaded_by == uploader.id
        finally:
            fresh_session.close()

    def test_file_list_retrieval_shows_all_created_files(self, db_session: Session):
        """Test that file list retrieval shows all created files"""
        # Arrange: Create user and multiple files
        uploader = UserFactory.create(db_session)
        db_session.commit()

        # Act: Create files
        created_ids = []
        for i in range(3):
            file = FileFactory.create(
                db_session,
                uploaded_by=uploader,
                filename=f"list_file_{i}.pdf",
                mime_type="application/pdf",
                file_type="document",
            )
            db_session.commit()
            created_ids.append(str(file.id))

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Retrieve file list
        list_response = client.get("/api/v1/files?limit=100")

        # Assert
        assert list_response.status_code == 200
        files = list_response.json()["data"]
        retrieved_ids = [f["id"] for f in files]
        for created_id in created_ids:
            assert created_id in retrieved_ids

    def test_file_retrieval_by_project_filter(self, db_session: Session):
        """Test that file retrieval with project filter works correctly"""
        # Arrange: Create files in different projects
        uploader = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, created_by=uploader)
        project2 = ProjectFactory.create(db_session, created_by=uploader)
        db_session.commit()

        # Create files in different projects
        for project in [project1, project2]:
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                project=project,
                filename=f"file_in_project_{project.id}.pdf",
                mime_type="application/pdf",
                file_type="document",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Retrieve files for project1
        response = client.get(f"/api/v1/files?project_id={project1.id}&limit=100")

        # Assert
        assert response.status_code == 200
        files = response.json()["data"]
        assert len(files) >= 1
        for file in files:
            assert file["project_id"] == str(project1.id)

    def test_file_retrieval_by_meeting_filter(self, db_session: Session):
        """Test that file retrieval with meeting filter works correctly"""
        # Arrange: Create files in different meetings
        uploader = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, created_by=uploader)
        meeting2 = MeetingFactory.create(db_session, created_by=uploader)
        db_session.commit()

        # Create files in different meetings
        for meeting in [meeting1, meeting2]:
            FileFactory.create(
                db_session,
                uploaded_by=uploader,
                meeting=meeting,
                filename=f"file_in_meeting_{meeting.id}.pdf",
                mime_type="application/pdf",
                file_type="document",
            )
        db_session.commit()

        access_token = create_access_token({"sub": str(uploader.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Retrieve files for meeting1
        response = client.get(f"/api/v1/files?meeting_id={meeting1.id}&limit=100")

        # Assert
        assert response.status_code == 200
        files = response.json()["data"]
        assert len(files) >= 1
        for file in files:
            assert file["meeting_id"] == str(meeting1.id)

    def test_file_metadata_and_associations_persist_correctly(self, db_session: Session):
        """Test that file metadata and associations persist correctly throughout workflow"""
        # Arrange
        uploader = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=uploader)
        meeting = MeetingFactory.create(db_session, created_by=uploader)
        db_session.commit()

        # Act: Create file with full metadata
        file = FileFactory.create(
            db_session,
            uploaded_by=uploader,
            project=project,
            meeting=meeting,
            filename="full_metadata.pdf",
            mime_type="application/pdf",
            file_type="document",
        )
        db_session.commit()
        file_id = file.id

        # Assert: Verify all metadata and associations persisted
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is not None
            assert db_file.filename == "full_metadata.pdf"
            assert db_file.mime_type == "application/pdf"
            assert db_file.file_type == "document"
            assert db_file.project_id == project.id
            assert db_file.meeting_id == meeting.id
            assert db_file.uploaded_by == uploader.id
            assert db_file.created_at is not None
        finally:
            fresh_session.close()
