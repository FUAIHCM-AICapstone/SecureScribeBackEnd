"""Unit tests for file service functions"""

import uuid
from unittest.mock import patch

from faker import Faker
from sqlalchemy.orm import Session

from app.models.file import File
from app.schemas.file import FileCreate, FileFilter, FileUpdate
from app.services.file import (
    bulk_delete_files,
    check_file_access,
    create_file,
    delete_file,
    get_file,
    get_file_with_meeting_info,
    get_file_with_project_info,
    get_files,
    get_meeting_files_with_info,
    get_project_files_with_info,
    update_file,
    validate_file,
)
from tests.factories import FileFactory, MeetingFactory, ProjectFactory, UserFactory

fake = Faker()


class TestCreateFile:
    """Tests for create_file function"""

    @patch("app.services.file.upload_bytes_to_minio")
    @patch("app.services.file.generate_presigned_url")
    def test_create_file_success(self, mock_presigned_url, mock_upload, db_session: Session):
        """Test creating a file with valid data"""
        mock_upload.return_value = True
        mock_presigned_url.return_value = "https://minio.example.com/file.pdf"

        user = UserFactory.create(db_session)
        file_data = FileCreate(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_type="document",
        )
        file_bytes = b"test file content"

        file = create_file(db_session, file_data, user.id, file_bytes)

        assert file is not None
        assert file.id is not None
        assert file.filename == "test.pdf"
        assert file.mime_type == "application/pdf"
        assert file.uploaded_by == user.id
        assert file.storage_url == "https://minio.example.com/file.pdf"

    @patch("app.services.file.upload_bytes_to_minio")
    @patch("app.services.file.generate_presigned_url")
    def test_create_file_with_project(self, mock_presigned_url, mock_upload, db_session: Session):
        """Test creating a file linked to a project"""
        mock_upload.return_value = True
        mock_presigned_url.return_value = "https://minio.example.com/file.pdf"

        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user)
        file_data = FileCreate(
            filename="project_file.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            file_type="document",
            project_id=project.id,
        )
        file_bytes = b"project file content"

        file = create_file(db_session, file_data, user.id, file_bytes)

        assert file is not None
        assert file.project_id == project.id
        assert file.filename == "project_file.pdf"

    @patch("app.services.file.upload_bytes_to_minio")
    @patch("app.services.file.generate_presigned_url")
    def test_create_file_with_meeting(self, mock_presigned_url, mock_upload, db_session: Session):
        """Test creating a file linked to a meeting"""
        mock_upload.return_value = True
        mock_presigned_url.return_value = "https://minio.example.com/file.pdf"

        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user)
        file_data = FileCreate(
            filename="meeting_file.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            file_type="document",
            meeting_id=meeting.id,
        )
        file_bytes = b"meeting file content"

        file = create_file(db_session, file_data, user.id, file_bytes)

        assert file is not None
        assert file.meeting_id == meeting.id
        assert file.filename == "meeting_file.pdf"

    @patch("app.services.file.upload_bytes_to_minio")
    @patch("app.services.file.generate_presigned_url")
    def test_create_file_minio_upload_fails(self, mock_presigned_url, mock_upload, db_session: Session):
        """Test creating a file when MinIO upload fails"""
        mock_upload.return_value = False
        mock_presigned_url.return_value = None

        user = UserFactory.create(db_session)
        file_data = FileCreate(
            filename="test_minio_fail.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_type="document",
        )
        file_bytes = b"test file content"

        file = create_file(db_session, file_data, user.id, file_bytes)

        # When MinIO upload fails, the file should be deleted from database
        assert file is None
        # Verify file was not persisted to database
        persisted_file = db_session.query(File).filter(File.filename == "test_minio_fail.pdf").first()
        assert persisted_file is None

    @patch("app.services.file.upload_bytes_to_minio")
    @patch("app.services.file.generate_presigned_url")
    def test_create_file_presigned_url_fails(self, mock_presigned_url, mock_upload, db_session: Session):
        """Test creating a file when presigned URL generation fails"""
        mock_upload.return_value = True
        mock_presigned_url.return_value = None

        user = UserFactory.create(db_session)
        file_data = FileCreate(
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_type="document",
        )
        file_bytes = b"test file content"

        file = create_file(db_session, file_data, user.id, file_bytes)

        # File should still be created even if presigned URL fails
        assert file is not None
        assert file.storage_url is None


class TestGetFile:
    """Tests for get_file function"""

    def test_get_file_success(self, db_session: Session):
        """Test getting a file by ID"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        retrieved_file = get_file(db_session, file.id)

        assert retrieved_file is not None
        assert retrieved_file.id == file.id
        assert retrieved_file.filename == file.filename

    def test_get_file_not_found(self, db_session: Session):
        """Test getting non-existent file"""
        fake_id = uuid.uuid4()

        file = get_file(db_session, fake_id)

        assert file is None


class TestGetFiles:
    """Tests for get_files function"""

    def test_get_files_all(self, db_session: Session):
        """Test getting all files"""
        user = UserFactory.create(db_session)
        FileFactory.create_batch(db_session, uploaded_by=user, count=3)

        files, total = get_files(db_session)

        assert len(files) >= 3
        assert total >= 3

    def test_get_files_with_pagination(self, db_session: Session):
        """Test getting files with pagination"""
        user = UserFactory.create(db_session)
        FileFactory.create_batch(db_session, uploaded_by=user, count=5)

        files, total = get_files(db_session, page=1, limit=2)

        assert len(files) <= 2
        assert total >= 5

    def test_get_files_filter_by_filename(self, db_session: Session):
        """Test filtering files by filename"""
        user = UserFactory.create(db_session)
        search_filename = "test_document.pdf"
        file = FileFactory.create(db_session, uploaded_by=user, filename=search_filename)

        filters = FileFilter(filename="test_document")
        files, total = get_files(db_session, filters=filters)

        assert len(files) >= 1
        assert any(f.id == file.id for f in files)

    def test_get_files_filter_by_mime_type(self, db_session: Session):
        """Test filtering files by mime type"""
        user = UserFactory.create(db_session)
        mime_type = "application/pdf"
        file = FileFactory.create(db_session, uploaded_by=user, mime_type=mime_type)

        filters = FileFilter(mime_type=mime_type)
        files, total = get_files(db_session, filters=filters, user_id=user.id)

        assert len(files) >= 1
        assert any(f.id == file.id for f in files)

    def test_get_files_filter_by_file_type(self, db_session: Session):
        """Test filtering files by file type"""
        user = UserFactory.create(db_session)
        file_type = "document"
        file = FileFactory.create(db_session, uploaded_by=user, file_type=file_type)

        filters = FileFilter(file_type=file_type)
        files, total = get_files(db_session, filters=filters, user_id=user.id)

        assert len(files) >= 1
        assert any(f.id == file.id for f in files)

    def test_get_files_filter_by_project(self, db_session: Session):
        """Test filtering files by project"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user)
        file = FileFactory.create(db_session, uploaded_by=user, project=project)

        filters = FileFilter(project_id=project.id)
        files, total = get_files(db_session, filters=filters)

        assert len(files) >= 1
        assert any(f.id == file.id for f in files)

    def test_get_files_filter_by_meeting(self, db_session: Session):
        """Test filtering files by meeting"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user)
        file = FileFactory.create(db_session, uploaded_by=user, meeting=meeting)

        filters = FileFilter(meeting_id=meeting.id)
        files, total = get_files(db_session, filters=filters)

        assert len(files) >= 1
        assert any(f.id == file.id for f in files)

    def test_get_files_filter_by_uploaded_by(self, db_session: Session):
        """Test filtering files by uploader"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user1)
        FileFactory.create(db_session, uploaded_by=user2)

        filters = FileFilter(uploaded_by=user1.id)
        files, total = get_files(db_session, filters=filters)

        assert len(files) >= 1
        assert all(f.uploaded_by == user1.id for f in files)

    def test_get_files_access_control(self, db_session: Session):
        """Test that get_files respects access control"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user1)

        # User1 uploads file to project
        file = FileFactory.create(db_session, uploaded_by=user1, project=project)

        # User2 should not see the file (not in project)
        files, total = get_files(db_session, user_id=user2.id)

        assert not any(f.id == file.id for f in files)

    def test_get_files_user_can_see_own_files(self, db_session: Session):
        """Test that user can see their own files"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        files, total = get_files(db_session, user_id=user.id)

        assert any(f.id == file.id for f in files)

    def test_get_files_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        user = UserFactory.create(db_session)
        FileFactory.create_batch(db_session, uploaded_by=user, count=25)

        files, total = get_files(db_session)

        assert len(files) <= 20  # Default limit is 20


class TestUpdateFile:
    """Tests for update_file function"""

    def test_update_file_success(self, db_session: Session):
        """Test updating a file with valid data"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user, filename="original.pdf")

        updated_filename = "updated.pdf"
        updates = FileUpdate(filename=updated_filename)
        updated_file = update_file(db_session, file.id, updates, actor_user_id=user.id)

        assert updated_file is not None
        assert updated_file.filename == updated_filename
        assert updated_file.id == file.id

    def test_update_file_not_found(self, db_session: Session):
        """Test updating non-existent file"""
        fake_id = uuid.uuid4()
        updates = FileUpdate(filename="new.pdf")

        updated_file = update_file(db_session, fake_id, updates)

        assert updated_file is None

    def test_update_file_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        user = UserFactory.create(db_session)
        original_file_type = "document"
        file = FileFactory.create(db_session, uploaded_by=user, filename="test.pdf", file_type=original_file_type)

        updated_filename = "updated.pdf"
        updates = FileUpdate(filename=updated_filename)
        updated_file = update_file(db_session, file.id, updates, actor_user_id=user.id)

        assert updated_file.filename == updated_filename
        assert updated_file.file_type == original_file_type

    def test_update_file_with_actor(self, db_session: Session):
        """Test updating file with actor_user_id for audit"""
        user = UserFactory.create(db_session)
        actor = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        updates = FileUpdate(filename="updated.pdf")
        updated_file = update_file(db_session, file.id, updates, actor_user_id=actor.id)

        assert updated_file.filename == "updated.pdf"

    def test_update_file_empty_updates(self, db_session: Session):
        """Test updating file with no changes"""
        user = UserFactory.create(db_session)
        original_filename = "test.pdf"
        file = FileFactory.create(db_session, uploaded_by=user, filename=original_filename)

        updates = FileUpdate()
        updated_file = update_file(db_session, file.id, updates, actor_user_id=user.id)

        assert updated_file.filename == original_filename
        assert updated_file.id == file.id


class TestDeleteFile:
    """Tests for delete_file function"""

    @patch("app.services.file.delete_file_from_minio")
    def test_delete_file_success(self, mock_delete_minio, db_session: Session):
        """Test deleting a file"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)
        file_id = file.id

        result = delete_file(db_session, file_id, actor_user_id=user.id)

        assert result is True
        # Verify file is deleted from database
        deleted_file = db_session.query(File).filter(File.id == file_id).first()
        assert deleted_file is None
        # Verify MinIO delete was called
        mock_delete_minio.assert_called_once()

    @patch("app.services.file.delete_file_from_minio")
    def test_delete_file_not_found(self, mock_delete_minio, db_session: Session):
        """Test deleting non-existent file"""
        fake_id = uuid.uuid4()

        result = delete_file(db_session, fake_id)

        assert result is False
        # MinIO delete should not be called
        mock_delete_minio.assert_not_called()

    @patch("app.services.file.delete_file_from_minio")
    def test_delete_file_with_actor(self, mock_delete_minio, db_session: Session):
        """Test deleting file with actor_user_id for audit"""
        user = UserFactory.create(db_session)
        actor = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        result = delete_file(db_session, file.id, actor_user_id=actor.id)

        assert result is True


class TestBulkDeleteFiles:
    """Tests for bulk_delete_files function"""

    @patch("app.services.file.delete_file_from_minio")
    def test_bulk_delete_files_success(self, mock_delete_minio, db_session: Session):
        """Test bulk deleting multiple files"""
        user = UserFactory.create(db_session)
        file1 = FileFactory.create(db_session, uploaded_by=user)
        file2 = FileFactory.create(db_session, uploaded_by=user)

        results = bulk_delete_files(db_session, [file1.id, file2.id], user_id=user.id)

        assert len(results) == 2
        assert all(r["success"] for r in results)

        # Verify files are deleted
        deleted_file1 = db_session.query(File).filter(File.id == file1.id).first()
        deleted_file2 = db_session.query(File).filter(File.id == file2.id).first()
        assert deleted_file1 is None
        assert deleted_file2 is None

    @patch("app.services.file.delete_file_from_minio")
    def test_bulk_delete_files_not_found(self, mock_delete_minio, db_session: Session):
        """Test bulk deleting with non-existent file"""
        fake_id = uuid.uuid4()

        results = bulk_delete_files(db_session, [fake_id])

        assert results[0]["success"] is False
        assert "not found" in results[0]["error"].lower()

    @patch("app.services.file.delete_file_from_minio")
    def test_bulk_delete_files_mixed_success(self, mock_delete_minio, db_session: Session):
        """Test bulk deleting with mix of valid and invalid files"""
        user = UserFactory.create(db_session)
        file1 = FileFactory.create(db_session, uploaded_by=user)
        fake_id = uuid.uuid4()

        results = bulk_delete_files(db_session, [file1.id, fake_id], user_id=user.id)

        assert results[0]["success"] is True
        assert results[1]["success"] is False

    @patch("app.services.file.delete_file_from_minio")
    def test_bulk_delete_files_empty_list(self, mock_delete_minio, db_session: Session):
        """Test bulk deleting with empty list"""
        results = bulk_delete_files(db_session, [])

        assert results == []

    @patch("app.services.file.delete_file_from_minio")
    def test_bulk_delete_files_access_denied(self, mock_delete_minio, db_session: Session):
        """Test bulk deleting files without access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user1)
        file = FileFactory.create(db_session, uploaded_by=user1, project=project)

        # User2 tries to delete file they don't have access to
        results = bulk_delete_files(db_session, [file.id], user_id=user2.id)

        assert results[0]["success"] is False
        assert "access denied" in results[0]["error"].lower()


class TestCheckFileAccess:
    """Tests for check_file_access function"""

    def test_check_file_access_owner(self, db_session: Session):
        """Test that file owner has access"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        has_access = check_file_access(db_session, file, user.id)

        assert has_access is True

    def test_check_file_access_project_member(self, db_session: Session):
        """Test that project member has access to project files"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user1)
        # Add user2 to project
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, user2.id, "member")

        file = FileFactory.create(db_session, uploaded_by=user1, project=project)

        has_access = check_file_access(db_session, file, user2.id)

        assert has_access is True

    def test_check_file_access_non_member(self, db_session: Session):
        """Test that non-member doesn't have access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user1)
        file = FileFactory.create(db_session, uploaded_by=user1, project=project)

        has_access = check_file_access(db_session, file, user2.id)

        assert has_access is False

    def test_check_file_access_personal_file(self, db_session: Session):
        """Test access to personal file (no project/meeting)"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user1)

        # User1 has access
        assert check_file_access(db_session, file, user1.id) is True

        # User2 doesn't have access
        assert check_file_access(db_session, file, user2.id) is False


class TestValidateFile:
    """Tests for validate_file function"""

    def test_validate_file_success(self, db_session: Session):
        """Test validating a valid file"""
        result = validate_file("document.pdf", "application/pdf", 1024)

        assert result is True

    def test_validate_file_size_exceeds_limit(self, db_session: Session):
        """Test validating file that exceeds size limit"""
        # Assuming MAX_FILE_SIZE_MB is set in config
        from app.core.config import settings

        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        result = validate_file("large.pdf", "application/pdf", max_size_bytes + 1)

        assert result is False

    def test_validate_file_invalid_extension(self, db_session: Session):
        """Test validating file with invalid extension"""
        result = validate_file("script.exe", "application/x-msdownload", 1024)

        assert result is False

    def test_validate_file_invalid_mime_type(self, db_session: Session):
        """Test validating file with invalid mime type"""
        result = validate_file("document.pdf", "application/x-invalid", 1024)

        assert result is False


class TestGetProjectFilesWithInfo:
    """Tests for get_project_files_with_info function"""

    def test_get_project_files_with_info_success(self, db_session: Session):
        """Test getting project files with project info"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user, name="Test Project")
        file = FileFactory.create(db_session, uploaded_by=user, project=project)

        files, project_name, total = get_project_files_with_info(db_session, project.id, user.id)

        assert len(files) >= 1
        assert project_name == "Test Project"
        assert any(f.id == file.id for f in files)

    def test_get_project_files_with_info_access_denied(self, db_session: Session):
        """Test getting project files without access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user1)

        files, project_name, total = get_project_files_with_info(db_session, project.id, user2.id)

        assert len(files) == 0
        assert project_name is None
        assert total == 0


class TestGetMeetingFilesWithInfo:
    """Tests for get_meeting_files_with_info function"""

    def test_get_meeting_files_with_info_success(self, db_session: Session):
        """Test getting meeting files with meeting info"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user, title="Test Meeting")
        file = FileFactory.create(db_session, uploaded_by=user, meeting=meeting)

        files, meeting_title, total = get_meeting_files_with_info(db_session, meeting.id, user.id)

        assert len(files) >= 1
        assert meeting_title == "Test Meeting"
        assert any(f.id == file.id for f in files)

    def test_get_meeting_files_with_info_access_denied(self, db_session: Session):
        """Test getting meeting files without access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user1)

        files, meeting_title, total = get_meeting_files_with_info(db_session, meeting.id, user2.id)

        assert len(files) == 0
        assert meeting_title is None
        assert total == 0


class TestGetFileWithProjectInfo:
    """Tests for get_file_with_project_info function"""

    def test_get_file_with_project_info_success(self, db_session: Session):
        """Test getting file with project info"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user, name="Test Project")
        file = FileFactory.create(db_session, uploaded_by=user, project=project)

        retrieved_file, project_name = get_file_with_project_info(db_session, file.id, user.id)

        assert retrieved_file is not None
        assert retrieved_file.id == file.id
        assert project_name == "Test Project"

    def test_get_file_with_project_info_no_project(self, db_session: Session):
        """Test getting file without project"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        retrieved_file, project_name = get_file_with_project_info(db_session, file.id, user.id)

        assert retrieved_file is not None
        assert project_name is None

    def test_get_file_with_project_info_access_denied(self, db_session: Session):
        """Test getting file without access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user1)

        retrieved_file, project_name = get_file_with_project_info(db_session, file.id, user2.id)

        assert retrieved_file is None
        assert project_name is None


class TestGetFileWithMeetingInfo:
    """Tests for get_file_with_meeting_info function"""

    def test_get_file_with_meeting_info_success(self, db_session: Session):
        """Test getting file with meeting info"""
        user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=user, title="Test Meeting")
        file = FileFactory.create(db_session, uploaded_by=user, meeting=meeting)

        retrieved_file, meeting_title = get_file_with_meeting_info(db_session, file.id, user.id)

        assert retrieved_file is not None
        assert retrieved_file.id == file.id
        assert meeting_title == "Test Meeting"

    def test_get_file_with_meeting_info_no_meeting(self, db_session: Session):
        """Test getting file without meeting"""
        user = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user)

        retrieved_file, meeting_title = get_file_with_meeting_info(db_session, file.id, user.id)

        assert retrieved_file is not None
        assert meeting_title is None

    def test_get_file_with_meeting_info_access_denied(self, db_session: Session):
        """Test getting file without access"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        file = FileFactory.create(db_session, uploaded_by=user1)

        retrieved_file, meeting_title = get_file_with_meeting_info(db_session, file.id, user2.id)

        assert retrieved_file is None
        assert meeting_title is None
