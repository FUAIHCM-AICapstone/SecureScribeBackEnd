"""Test data factories for creating test objects"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from faker import Faker
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.meeting import AudioFile, Meeting, MeetingBot, MeetingNote, ProjectMeeting, Transcript
from app.models.project import Project, UserProject
from app.models.task import Task, TaskProject
from app.models.user import User, UserDevice, UserIdentity

fake = Faker()


class UserFactory:
    """Factory for creating test User objects"""

    @staticmethod
    def create(
        db: Session,
        email: Optional[str] = None,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
        position: Optional[str] = None,
    ) -> User:
        """Create a test user"""
        from app.services.user import create_user

        # Generate unique email if not provided
        if email is None:
            email = fake.email()
            # Ensure uniqueness by checking existing emails
            counter = 1
            base_email = email
            while db.query(User).filter(User.email == email).first() is not None:
                # Extract username and domain
                username, domain = email.split('@', 1)
                email = f"{username}{counter}@{domain}"
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    email = f"testuser{counter}@{domain}"

        user_data = {
            "email": email,
            "name": name or fake.name(),
            "avatar_url": avatar_url or fake.image_url(),
            "bio": bio or fake.text(max_nb_chars=100),
            "position": position or fake.job(),
        }

        return create_user(db, **user_data)

    @staticmethod
    def create_batch(db: Session, count: int = 5) -> list[User]:
        """Create multiple test users"""
        users = []
        for _ in range(count):
            user = UserFactory.create(db)
            users.append(user)
        return users


class UserIdentityFactory:
    """Factory for creating test UserIdentity objects"""

    @staticmethod
    def create(
        db: Session,
        user: User,
        provider: str = "google",
        provider_user_id: Optional[str] = None,
    ) -> UserIdentity:
        """Create a test user identity"""
        identity = UserIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id or fake.uuid4(),
            provider_email=fake.email(),
        )
        db.add(identity)
        db.commit()
        db.refresh(identity)
        return identity


class UserDeviceFactory:
    """Factory for creating test UserDevice objects"""

    @staticmethod
    def create(
        db: Session,
        user: User,
        device_name: Optional[str] = None,
        device_type: str = "mobile",
    ) -> UserDevice:
        """Create a test user device"""
        device = UserDevice(
            user_id=user.id,
            device_name=device_name or fake.word(),
            device_type=device_type,
            fcm_token=fake.sha256(),
            is_active=True,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device


class ProjectFactory:
    """Factory for creating test Project objects"""

    @staticmethod
    def create(
        db: Session,
        created_by: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: bool = False,
    ) -> Project:
        """Create a test project"""
        from app.schemas.project import ProjectCreate
        from app.services.project import create_project

        project_data = ProjectCreate(
            name=name or fake.word(),
            description=description or fake.text(max_nb_chars=200),
        )
        return create_project(db, project_data, created_by.id)

    @staticmethod
    def create_batch(db: Session, created_by: User, count: int = 5) -> list[Project]:
        """Create multiple test projects"""
        projects = []
        for _ in range(count):
            project = ProjectFactory.create(db, created_by)
            projects.append(project)
        return projects


class UserProjectFactory:
    """Factory for creating test UserProject relationships"""

    @staticmethod
    def create(
        db: Session,
        user: User,
        project: Project,
        role: str = "member",
    ) -> UserProject:
        """Create a test user-project relationship"""
        from app.services.project import add_user_to_project

        # Use the service function which handles duplicates properly
        return add_user_to_project(db, project.id, user.id, role)


class MeetingFactory:
    """Factory for creating test Meeting objects"""

    @staticmethod
    def create(
        db: Session,
        created_by: User,
        title: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        is_personal: bool = False,
        status: str = "active",
    ) -> Meeting:
        """Create a test meeting"""
        meeting = Meeting(
            title=title or fake.sentence(),
            description=description or fake.text(max_nb_chars=200),
            url=url or fake.url(),
            created_by=created_by.id,
            is_personal=is_personal,
            status=status,
            start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting

    @staticmethod
    def create_batch(db: Session, created_by: User, count: int = 5) -> list[Meeting]:
        """Create multiple test meetings"""
        meetings = []
        for _ in range(count):
            meeting = MeetingFactory.create(db, created_by)
            meetings.append(meeting)
        return meetings


class ProjectMeetingFactory:
    """Factory for creating test ProjectMeeting relationships"""

    @staticmethod
    def create(
        db: Session,
        project: Project,
        meeting: Meeting,
    ) -> ProjectMeeting:
        """Create a test project-meeting relationship"""
        project_meeting = ProjectMeeting(
            project_id=project.id,
            meeting_id=meeting.id,
        )
        db.add(project_meeting)
        db.commit()
        db.refresh(project_meeting)
        return project_meeting


class AudioFileFactory:
    """Factory for creating test AudioFile objects"""

    @staticmethod
    def create(
        db: Session,
        meeting: Meeting,
        uploaded_by: User,
        file_url: Optional[str] = None,
        duration_seconds: int = 3600,
    ) -> AudioFile:
        """Create a test audio file"""
        audio_file = AudioFile(
            meeting_id=meeting.id,
            uploaded_by=uploaded_by.id,
            file_url=file_url or fake.url(),
            duration_seconds=duration_seconds,
            is_concatenated=False,
        )
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        return audio_file


class TranscriptFactory:
    """Factory for creating test Transcript objects"""

    @staticmethod
    def create(
        db: Session,
        meeting: Meeting,
        content: Optional[str] = None,
        audio_concat_file: Optional[AudioFile] = None,
    ) -> Transcript:
        """Create a test transcript"""
        transcript = Transcript(
            meeting_id=meeting.id,
            content=content or fake.text(max_nb_chars=500),
            audio_concat_file_id=audio_concat_file.id if audio_concat_file else None,
            extracted_text_for_search=content or fake.text(max_nb_chars=500),
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        return transcript


class MeetingNoteFactory:
    """Factory for creating test MeetingNote objects"""

    @staticmethod
    def create(
        db: Session,
        meeting: Meeting,
        content: Optional[str] = None,
        last_editor: Optional[User] = None,
    ) -> MeetingNote:
        """Create a test meeting note"""
        note = MeetingNote(
            meeting_id=meeting.id,
            content=content or fake.text(max_nb_chars=500),
            last_editor_id=last_editor.id if last_editor else None,
            last_edited_at=datetime.now(timezone.utc),
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note


class MeetingBotFactory:
    """Factory for creating test MeetingBot objects"""

    @staticmethod
    def create(
        db: Session,
        meeting: Meeting,
        created_by: User,
        status: str = "pending",
        meeting_url: Optional[str] = None,
    ) -> MeetingBot:
        """Create a test meeting bot"""
        bot = MeetingBot(
            meeting_id=meeting.id,
            created_by=created_by.id,
            status=status,
            meeting_url=meeting_url or fake.url(),
            scheduled_start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(bot)
        db.commit()
        db.refresh(bot)
        return bot


class TaskFactory:
    """Factory for creating test Task objects"""

    @staticmethod
    def create(
        db: Session,
        creator: User,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[User] = None,
        status: str = "todo",
        priority: str = "Trung bình",
        meeting: Optional[Meeting] = None,
    ) -> Task:
        """Create a test task"""
        task = Task(
            title=title or fake.sentence(),
            description=description or fake.text(max_nb_chars=200),
            creator_id=creator.id,
            assignee_id=assignee.id if assignee else None,
            status=status,
            priority=priority,
            meeting_id=meeting.id if meeting else None,
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def create_batch(db: Session, creator: User, count: int = 5) -> list[Task]:
        """Create multiple test tasks"""
        tasks = []
        for _ in range(count):
            task = TaskFactory.create(db, creator)
            tasks.append(task)
        return tasks


class TaskProjectFactory:
    """Factory for creating test TaskProject relationships"""

    @staticmethod
    def create(
        db: Session,
        task: Task,
        project: Project,
    ) -> TaskProject:
        """Create a test task-project relationship"""
        task_project = TaskProject(
            task_id=task.id,
            project_id=project.id,
        )
        db.add(task_project)
        db.commit()
        db.refresh(task_project)
        return task_project


class FileFactory:
    """Factory for creating test File objects"""

    @staticmethod
    def create(
        db: Session,
        uploaded_by: User,
        filename: Optional[str] = None,
        mime_type: str = "application/pdf",
        size_bytes: int = 1024,
        file_type: str = "document",
        project: Optional[Project] = None,
        meeting: Optional[Meeting] = None,
    ) -> File:
        """Create a test file"""
        file = File(
            filename=filename or fake.file_name(),
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_url=fake.url(),
            file_type=file_type,
            project_id=project.id if project else None,
            meeting_id=meeting.id if meeting else None,
            uploaded_by=uploaded_by.id,
        )
        db.add(file)
        db.commit()
        db.refresh(file)
        return file

    @staticmethod
    def create_batch(db: Session, uploaded_by: User, count: int = 5) -> list[File]:
        """Create multiple test files"""
        files = []
        for _ in range(count):
            file = FileFactory.create(db, uploaded_by)
            files.append(file)
        return files
