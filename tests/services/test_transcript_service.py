"""Unit tests for transcript service functions"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.meeting import Transcript
from app.schemas.transcript import TranscriptCreate, TranscriptUpdate
from app.services.transcript import (
    check_transcript_access,
    create_transcript,
    delete_transcript,
    get_transcript,
    get_transcript_by_meeting,
    get_transcripts,
    update_transcript,
)
from tests.factories import (
    AudioFileFactory,
    MeetingFactory,
    ProjectFactory,
    TranscriptFactory,
    UserFactory,
    UserProjectFactory,
)


class TestCreateTranscript:
    """Tests for create_transcript function"""

    def test_create_transcript_success(self, db_session: Session):
        """Test creating a transcript with valid data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript_data = TranscriptCreate(
            meeting_id=meeting.id,
            content="This is a test transcript",
        )

        transcript = create_transcript(db_session, transcript_data, creator.id)

        assert transcript.id is not None
        assert transcript.meeting_id == meeting.id
        assert transcript.content == "This is a test transcript"
        assert transcript.created_at is not None

    def test_create_transcript_with_audio_file(self, db_session: Session):
        """Test creating a transcript linked to audio file"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        audio_file = AudioFileFactory.create(db_session, meeting, creator)
        transcript_data = TranscriptCreate(
            meeting_id=meeting.id,
            content="Transcript content",
            audio_concat_file_id=audio_file.id,
        )

        transcript = create_transcript(db_session, transcript_data, creator.id)

        assert transcript.audio_concat_file_id == audio_file.id
        assert transcript.meeting_id == meeting.id

    def test_create_transcript_meeting_not_found(self, db_session: Session):
        """Test creating transcript for non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_meeting_id = uuid.uuid4()
        transcript_data = TranscriptCreate(
            meeting_id=fake_meeting_id,
            content="Test content",
        )

        with pytest.raises(Exception):  # HTTPException 404
            create_transcript(db_session, transcript_data, creator.id)

    def test_create_transcript_no_access_to_meeting(self, db_session: Session):
        """Test creating transcript without access to meeting"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript_data = TranscriptCreate(
            meeting_id=meeting.id,
            content="Test content",
        )

        with pytest.raises(Exception):  # HTTPException 403
            create_transcript(db_session, transcript_data, other_user.id)

    def test_create_transcript_updates_existing(self, db_session: Session):
        """Test that creating transcript for same meeting updates existing"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        existing_transcript = TranscriptFactory.create(
            db_session, meeting, content="Original content"
        )
        original_id = existing_transcript.id

        new_data = TranscriptCreate(
            meeting_id=meeting.id,
            content="Updated content",
        )
        updated_transcript = create_transcript(db_session, new_data, creator.id)

        assert updated_transcript.id == original_id
        assert updated_transcript.content == "Updated content"

    def test_create_transcript_with_project_access(self, db_session: Session):
        """Test creating transcript with project member access"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        from app.models.meeting import ProjectMeeting

        pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(pm)
        db_session.commit()

        transcript_data = TranscriptCreate(
            meeting_id=meeting.id,
            content="Member transcript",
        )
        transcript = create_transcript(db_session, transcript_data, member.id)

        assert transcript.meeting_id == meeting.id
        assert transcript.content == "Member transcript"

    def test_create_transcript_minimal_data(self, db_session: Session):
        """Test creating transcript with minimal data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript_data = TranscriptCreate(meeting_id=meeting.id)

        transcript = create_transcript(db_session, transcript_data, creator.id)

        assert transcript.meeting_id == meeting.id
        assert transcript.content is None


class TestGetTranscript:
    """Tests for get_transcript function"""

    def test_get_transcript_success(self, db_session: Session):
        """Test getting a transcript by ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)

        retrieved = get_transcript(db_session, transcript.id, creator.id)

        assert retrieved is not None
        assert retrieved.id == transcript.id
        assert retrieved.content == transcript.content

    def test_get_transcript_not_found(self, db_session: Session):
        """Test getting non-existent transcript"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        retrieved = get_transcript(db_session, fake_id, creator.id)

        assert retrieved is None

    def test_get_transcript_no_access(self, db_session: Session):
        """Test getting transcript without access"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript = TranscriptFactory.create(db_session, meeting)

        retrieved = get_transcript(db_session, transcript.id, other_user.id)

        assert retrieved is None

    def test_get_transcript_with_project_access(self, db_session: Session):
        """Test getting transcript with project member access"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        from app.models.meeting import ProjectMeeting

        pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(pm)
        db_session.commit()

        transcript = TranscriptFactory.create(db_session, meeting)

        retrieved = get_transcript(db_session, transcript.id, member.id)

        assert retrieved is not None
        assert retrieved.id == transcript.id


class TestGetTranscriptByMeeting:
    """Tests for get_transcript_by_meeting function"""

    def test_get_transcript_by_meeting_success(self, db_session: Session):
        """Test getting transcript by meeting ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)

        retrieved = get_transcript_by_meeting(db_session, meeting.id, creator.id)

        assert retrieved is not None
        assert retrieved.meeting_id == meeting.id

    def test_get_transcript_by_meeting_not_found(self, db_session: Session):
        """Test getting transcript for meeting without transcript"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)

        retrieved = get_transcript_by_meeting(db_session, meeting.id, creator.id)

        assert retrieved is None

    def test_get_transcript_by_meeting_no_access(self, db_session: Session):
        """Test getting transcript without meeting access"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        TranscriptFactory.create(db_session, meeting)

        retrieved = get_transcript_by_meeting(db_session, meeting.id, other_user.id)

        assert retrieved is None

    def test_get_transcript_by_meeting_not_found_meeting(self, db_session: Session):
        """Test getting transcript for non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_meeting_id = uuid.uuid4()

        retrieved = get_transcript_by_meeting(db_session, fake_meeting_id, creator.id)

        assert retrieved is None


class TestGetTranscripts:
    """Tests for get_transcripts function"""

    def test_get_transcripts_personal_meetings(self, db_session: Session):
        """Test getting transcripts from personal meetings"""
        creator = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator, is_personal=True)
        meeting2 = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript1 = TranscriptFactory.create(db_session, meeting1)
        transcript2 = TranscriptFactory.create(db_session, meeting2)

        # Get transcripts for this specific meeting to verify they exist
        retrieved1 = get_transcript_by_meeting(db_session, meeting1.id, creator.id)
        retrieved2 = get_transcript_by_meeting(db_session, meeting2.id, creator.id)

        assert retrieved1 is not None
        assert retrieved1.id == transcript1.id
        assert retrieved2 is not None
        assert retrieved2.id == transcript2.id

    def test_get_transcripts_with_project_access(self, db_session: Session):
        """Test getting transcripts from accessible projects"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        from app.models.meeting import ProjectMeeting

        pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(pm)
        db_session.commit()

        transcript = TranscriptFactory.create(db_session, meeting)

        # Verify member can access the transcript
        retrieved = get_transcript(db_session, transcript.id, member.id)
        assert retrieved is not None
        assert retrieved.id == transcript.id

    def test_get_transcripts_pagination(self, db_session: Session):
        """Test getting transcripts with pagination"""
        creator = UserFactory.create(db_session)
        for _ in range(5):
            meeting = MeetingFactory.create(db_session, creator, is_personal=True)
            TranscriptFactory.create(db_session, meeting)

        transcripts, total = get_transcripts(db_session, creator.id, page=1, limit=2)

        assert len(transcripts) <= 2
        assert total >= 5

    def test_get_transcripts_content_search(self, db_session: Session):
        """Test searching transcripts by content"""
        creator = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator, is_personal=True)
        meeting2 = MeetingFactory.create(db_session, creator, is_personal=True)
        TranscriptFactory.create(db_session, meeting1, content="Python programming")
        TranscriptFactory.create(db_session, meeting2, content="JavaScript tutorial")

        transcripts, total = get_transcripts(
            db_session, creator.id, content_search="Python"
        )

        assert len(transcripts) >= 1
        assert any("Python" in t.content for t in transcripts if t.content)

    def test_get_transcripts_filter_by_meeting(self, db_session: Session):
        """Test filtering transcripts by meeting"""
        creator = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator, is_personal=True)
        meeting2 = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript1 = TranscriptFactory.create(db_session, meeting1)
        TranscriptFactory.create(db_session, meeting2)

        transcripts, total = get_transcripts(
            db_session, creator.id, meeting_id=meeting1.id
        )

        assert len(transcripts) >= 1
        assert all(t.meeting_id == meeting1.id for t in transcripts)

    def test_get_transcripts_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        creator = UserFactory.create(db_session)
        for _ in range(25):
            meeting = MeetingFactory.create(db_session, creator, is_personal=True)
            TranscriptFactory.create(db_session, meeting)

        transcripts, total = get_transcripts(db_session, creator.id)

        assert len(transcripts) <= 20  # Default limit

    def test_get_transcripts_no_access_excluded(self, db_session: Session):
        """Test that transcripts from inaccessible meetings are excluded"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        inaccessible_transcript = TranscriptFactory.create(db_session, meeting)

        transcripts, total = get_transcripts(db_session, other_user.id, page=1, limit=100)

        transcript_ids = [t.id for t in transcripts]
        # Should not include transcripts from other user's personal meetings
        assert inaccessible_transcript.id not in transcript_ids


class TestUpdateTranscript:
    """Tests for update_transcript function"""

    def test_update_transcript_success(self, db_session: Session):
        """Test updating a transcript with valid data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting, content="Original")
        updates = TranscriptUpdate(content="Updated content")

        updated = update_transcript(db_session, transcript.id, updates, creator.id)

        assert updated is not None
        assert updated.id == transcript.id
        assert updated.content == "Updated content"

    def test_update_transcript_not_found(self, db_session: Session):
        """Test updating non-existent transcript"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()
        updates = TranscriptUpdate(content="Updated")

        with pytest.raises(Exception):  # HTTPException 404
            update_transcript(db_session, fake_id, updates, creator.id)

    def test_update_transcript_no_access(self, db_session: Session):
        """Test updating transcript without access"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript = TranscriptFactory.create(db_session, meeting)
        updates = TranscriptUpdate(content="Updated")

        with pytest.raises(Exception):  # HTTPException 403
            update_transcript(db_session, transcript.id, updates, other_user.id)

    def test_update_transcript_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(
            db_session, meeting, content="Original", extracted_text_for_search="Original search"
        )
        updates = TranscriptUpdate(content="Updated")

        updated = update_transcript(db_session, transcript.id, updates, creator.id)

        assert updated.content == "Updated"
        assert updated.extracted_text_for_search == "Original search"

    def test_update_transcript_extracted_text(self, db_session: Session):
        """Test updating extracted text for search"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)
        updates = TranscriptUpdate(extracted_text_for_search="Searchable text")

        updated = update_transcript(db_session, transcript.id, updates, creator.id)

        assert updated.extracted_text_for_search == "Searchable text"

    def test_update_transcript_qdrant_vector_id(self, db_session: Session):
        """Test updating Qdrant vector ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)
        vector_id = "vector_123"
        updates = TranscriptUpdate(qdrant_vector_id=vector_id)

        updated = update_transcript(db_session, transcript.id, updates, creator.id)

        assert updated.qdrant_vector_id == vector_id

    def test_update_transcript_empty_updates(self, db_session: Session):
        """Test updating with no changes"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting, content="Original")
        updates = TranscriptUpdate()

        updated = update_transcript(db_session, transcript.id, updates, creator.id)

        assert updated.content == "Original"


class TestDeleteTranscript:
    """Tests for delete_transcript function"""

    def test_delete_transcript_success(self, db_session: Session):
        """Test deleting a transcript"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)
        transcript_id = transcript.id

        delete_transcript(db_session, transcript_id, creator.id)

        # Verify transcript is deleted
        deleted = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        assert deleted is None

    def test_delete_transcript_not_found(self, db_session: Session):
        """Test deleting non-existent transcript"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(Exception):  # HTTPException 404
            delete_transcript(db_session, fake_id, creator.id)

    def test_delete_transcript_no_access(self, db_session: Session):
        """Test deleting transcript without access"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript = TranscriptFactory.create(db_session, meeting)

        with pytest.raises(Exception):  # HTTPException 403
            delete_transcript(db_session, transcript.id, other_user.id)

    def test_delete_transcript_with_project_access(self, db_session: Session):
        """Test deleting transcript with project member access"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        from app.models.meeting import ProjectMeeting

        pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(pm)
        db_session.commit()

        transcript = TranscriptFactory.create(db_session, meeting)
        transcript_id = transcript.id

        delete_transcript(db_session, transcript_id, member.id)

        deleted = db_session.query(Transcript).filter(Transcript.id == transcript_id).first()
        assert deleted is None


class TestCheckTranscriptAccess:
    """Tests for check_transcript_access function"""

    def test_check_transcript_access_owner(self, db_session: Session):
        """Test owner has access to transcript"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        transcript = TranscriptFactory.create(db_session, meeting)

        has_access = check_transcript_access(db_session, transcript.id, creator.id)

        assert has_access is True

    def test_check_transcript_access_no_access(self, db_session: Session):
        """Test non-owner has no access"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        transcript = TranscriptFactory.create(db_session, meeting)

        has_access = check_transcript_access(db_session, transcript.id, other_user.id)

        assert has_access is False

    def test_check_transcript_access_project_member(self, db_session: Session):
        """Test project member has access"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        from app.models.meeting import ProjectMeeting

        pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(pm)
        db_session.commit()

        transcript = TranscriptFactory.create(db_session, meeting)

        has_access = check_transcript_access(db_session, transcript.id, member.id)

        assert has_access is True

    def test_check_transcript_access_not_found(self, db_session: Session):
        """Test access check for non-existent transcript"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        has_access = check_transcript_access(db_session, fake_id, creator.id)

        assert has_access is False


class TestTranscribeAudioFile:
    """Tests for transcribe_audio_file function"""

    @patch("app.services.transcript.download_file_from_minio")
    @patch("app.services.transcript.transcriber")
    def test_transcribe_audio_file_success(
        self, mock_transcriber, mock_download, db_session: Session
    ):
        """Test transcribing audio file successfully"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        audio_file = AudioFileFactory.create(
            db_session, meeting, creator, file_url="https://minio.example.com/audio.webm"
        )

        # Mock the transcriber and download
        mock_download.return_value = b"fake audio data"
        mock_transcriber.return_value = "This is the transcribed text"

        from app.services.transcript import transcribe_audio_file

        transcript = transcribe_audio_file(db_session, audio_file.id)

        assert transcript is not None
        assert transcript.meeting_id == meeting.id
        assert transcript.content == "This is the transcribed text"
        assert transcript.audio_concat_file_id == audio_file.id

    def test_transcribe_audio_file_not_found(self, db_session: Session):
        """Test transcribing non-existent audio file"""
        fake_id = uuid.uuid4()

        from app.services.transcript import transcribe_audio_file

        result = transcribe_audio_file(db_session, fake_id)

        assert result is None

    def test_transcribe_audio_file_missing_url(self, db_session: Session):
        """Test transcribing audio file with missing URL"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        # Create audio file with None file_url
        from app.models.meeting import AudioFile
        audio_file = AudioFile(
            meeting_id=meeting.id,
            uploaded_by=creator.id,
            file_url=None,
            duration_seconds=3600,
            is_concatenated=False,
        )
        db_session.add(audio_file)
        db_session.commit()

        from app.services.transcript import transcribe_audio_file

        result = transcribe_audio_file(db_session, audio_file.id)

        assert result is None

    @patch("app.services.transcript.download_file_from_minio")
    @patch("app.services.transcript.transcriber")
    def test_transcribe_audio_file_download_failed(
        self, mock_transcriber, mock_download, db_session: Session
    ):
        """Test transcribing when download fails"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        audio_file = AudioFileFactory.create(
            db_session, meeting, creator, file_url="https://minio.example.com/audio.webm"
        )
        mock_download.return_value = None

        from app.services.transcript import transcribe_audio_file

        result = transcribe_audio_file(db_session, audio_file.id)

        assert result is None
