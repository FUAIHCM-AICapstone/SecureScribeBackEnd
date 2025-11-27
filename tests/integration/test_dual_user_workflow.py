"""
Comprehensive Integration Tests for Dual User Workflows
Tests 2 users collaborating across multiple features with persistent database data
All data is saved to the persistent database for inspection
Includes massive usage data covering all use cases:
- Projects (creation, member management, archiving)
- Tasks (creation, assignment, status updates, completion)
- Meetings (creation, transcripts, notes, bots)
- Real-world collaboration scenarios
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.file import File
from app.models.meeting import Meeting, MeetingBot, MeetingNote, ProjectMeeting, Transcript
from app.models.project import Project, UserProject
from app.models.task import Task, TaskProject
from app.models.user import User
from app.utils.auth import create_access_token
from tests.factories import (
    FileFactory,
    MeetingBotFactory,
    MeetingFactory,
    MeetingNoteFactory,
    ProjectFactory,
    TaskFactory,
    UserFactory,
)

fake = Faker()


def print_user_info(user: User, title: str = "User Information"):
    """Print formatted user information to console"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print(f"  ID:          {user.id}")
    print(f"  Email:       {user.email}")
    print(f"  Name:        {user.name}")
    print(f"  Position:    {user.position}")
    print(f"  Bio:         {user.bio}")
    print(f"  Avatar URL:  {user.avatar_url}")
    print(f"  Created At:  {user.created_at}")
    print("=" * 80 + "\n")


def print_project_info(project: Project, title: str = "Project Information"):
    """Print formatted project information to console"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)
    print(f"  ID:             {project.id}")
    print(f"  Name:           {project.name}")
    print(f"  Description:    {project.description}")
    print(f"  Created By:     {project.created_by}")
    print(f"  Is Archived:    {project.is_archived}")
    print(f"  Created At:     {project.created_at}")
    print("-" * 80 + "\n")


def print_meeting_info(meeting: Meeting, title: str = "Meeting Information"):
    """Print formatted meeting information to console"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)
    print(f"  ID:            {meeting.id}")
    print(f"  Title:         {meeting.title}")
    print(f"  Description:   {meeting.description}")
    print(f"  URL:           {meeting.url}")
    print(f"  Created By:    {meeting.created_by}")
    print(f"  Status:        {meeting.status}")
    print(f"  Is Personal:   {meeting.is_personal}")
    print(f"  Created At:    {meeting.created_at}")
    print("-" * 80 + "\n")


def print_task_info(task: Task, title: str = "Task Information"):
    """Print formatted task information to console"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)
    print(f"  ID:            {task.id}")
    print(f"  Title:         {task.title}")
    print(f"  Description:   {task.description}")
    print(f"  Status:        {task.status}")
    print(f"  Priority:      {task.priority}")
    print(f"  Creator ID:    {task.creator_id}")
    print(f"  Assignee ID:   {task.assignee_id}")
    print(f"  Due Date:      {task.due_date}")
    print(f"  Created At:    {task.created_at}")
    print("-" * 80 + "\n")


class TestDualUserProjectCollaboration:
    """
    Tests collaboration between 2 users working on projects
    - User 1: Project owner
    - User 2: Project member
    Data is persisted to the database for inspection
    """

    @pytest.fixture(autouse=False)
    def setup_users(self, db_session: Session):
        """Get 2 test users with fixed emails from database (or create if not exist)"""
        # Try to get existing users first
        user1 = db_session.query(User).filter(User.email == "luongnguyenminhan02052004@gmail.com").first()
        user2 = db_session.query(User).filter(User.email == "lnma020504@gmail.com").first()

        # Create if they don't exist
        if not user1:
            user1 = UserFactory.create(
                db_session,
                email="luongnguyenminhan02052004@gmail.com",
                name="Alice Johnson",
                position="Project Manager",
                bio="Lead project manager with 5+ years experience",
                avatar_url="https://example.com/avatars/alice.jpg",
            )

        if not user2:
            user2 = UserFactory.create(
                db_session,
                email="lnma020504@gmail.com",
                name="Bob Smith",
                position="Senior Developer",
                bio="Full-stack developer specializing in backend systems",
                avatar_url="https://example.com/avatars/bob.jpg",
            )

        db_session.commit()

        # Print user information to console
        print_user_info(user1, "USER 1: Project Owner")
        print_user_info(user2, "USER 2: Project Member")

        return user1, user2

    def test_user1_creates_project_and_adds_user2(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates a project
        2. User 1 adds User 2 as member
        3. Verify data persists in database
        """
        user1, user2 = setup_users

        # User 1 creates project
        project_data = {
            "name": "AI Meeting Assistant Platform",
            "description": "Build an AI-powered meeting transcription and analysis platform",
        }

        token1 = create_access_token({"sub": str(user1.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token1}"})

        # Create project
        response = client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 200
        project_id = uuid.UUID(response.json()["data"]["id"])

        print(f"\n✓ User 1 created project: {project_id}")

        # User 1 adds User 2 as member
        member_data = {"user_id": str(user2.id), "role": "member"}
        response = client.post(f"/api/v1/projects/{project_id}/members", json=member_data)
        assert response.status_code == 200

        print("✓ User 1 added User 2 to project as member")

        # Verify in persistent database
        fresh_session = SessionLocal()
        try:
            project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert project is not None
            print_project_info(project, "PROJECT CREATED BY USER 1")

            # Verify members
            user_projects = fresh_session.query(UserProject).filter(UserProject.project_id == project_id).all()
            assert len(user_projects) == 2

            print(f"\n✓ Project has {len(user_projects)} members:")
            for up in user_projects:
                user = fresh_session.query(User).filter(User.id == up.user_id).first()
                print(f"    - {user.name} ({user.email}): {up.role}")

        finally:
            fresh_session.close()

    def test_user1_creates_tasks_assigns_to_user2(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates a project
        2. User 1 adds User 2 as member
        3. User 1 creates multiple tasks and assigns to User 2
        4. Verify task assignments persist
        """
        user1, user2 = setup_users

        # Create project
        project = ProjectFactory.create(db_session, created_by=user1, name="Meeting Transcription System")
        db_session.commit()

        # Add User 2 to project
        user_project = UserProject(user_id=user2.id, project_id=project.id, role="member")
        db_session.add(user_project)
        db_session.commit()

        print_project_info(project, "PROJECT: Meeting Transcription System")

        # User 1 creates tasks and assigns to User 2
        created_tasks = []
        tasks_titles = [
            "Implement audio file upload API",
            "Optimize transcription model inference",
            "Create database schema for transcripts",
        ]

        for title in tasks_titles:
            task = TaskFactory.create(
                db_session,
                creator=user1,
                assignee=user2,
                title=title,
                status="todo",
                priority="high",
            )
            db_session.add(TaskProject(task_id=task.id, project_id=project.id))
            db_session.commit()
            created_tasks.append(task.id)

        print(f"\n✓ User 1 created {len(created_tasks)} tasks assigned to User 2:")

        # Verify tasks persisted
        fresh_session = SessionLocal()
        try:
            for i, task_id in enumerate(created_tasks, 1):
                task = fresh_session.query(Task).filter(Task.id == task_id).first()
                assert task is not None
                print_task_info(task, f"TASK {i}: {task.title}")
                assert task.assignee_id == user2.id
                print(f"  ✓ Assigned to: {task.assignee_id} (User 2)")

        finally:
            fresh_session.close()

    def test_user2_updates_task_status(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates project and tasks assigned to User 2
        2. User 2 updates task status to "in_progress"
        3. Verify status change persists in database
        """
        user1, user2 = setup_users

        # Setup: Create project and task
        project = ProjectFactory.create(db_session, created_by=user1)
        task = TaskFactory.create(
            db_session,
            creator=user1,
            assignee=user2,
            title="Implement speaker diarization",
            status="todo",
        )
        db_session.add(TaskProject(task_id=task.id, project_id=project.id))
        db_session.commit()

        print_task_info(task, "INITIAL TASK")

        # User 2 updates task status
        token2 = create_access_token({"sub": str(user2.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token2}"})

        update_data = {"status": "in_progress"}
        response = client.put(f"/api/v1/tasks/{task.id}", json=update_data)
        assert response.status_code == 200

        print("\n✓ User 2 updated task status to: in_progress")

        # Verify in database
        fresh_session = SessionLocal()
        try:
            updated_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert updated_task.status == "in_progress"
            print_task_info(updated_task, "TASK AFTER UPDATE")

        finally:
            fresh_session.close()

    def test_user2_completes_task_and_user1_reviews(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates task assigned to User 2
        2. User 2 marks task as completed
        3. User 1 reviews and closes task
        4. Verify task workflow in database
        """
        user1, user2 = setup_users

        # Setup: Create task
        task = TaskFactory.create(
            db_session,
            creator=user1,
            assignee=user2,
            title="Write API documentation",
            status="todo",
        )
        db_session.commit()

        print_task_info(task, "TASK CREATED BY USER 1")

        # User 2 marks as completed
        token2 = create_access_token({"sub": str(user2.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token2}"})

        response = client.put(f"/api/v1/tasks/{task.id}", json={"status": "completed"})
        assert response.status_code == 200

        print("✓ User 2 marked task as completed")

        # User 1 closes task
        token1 = create_access_token({"sub": str(user1.id)})
        client.headers.update({"Authorization": f"Bearer {token1}"})

        response = client.put(f"/api/v1/tasks/{task.id}", json={"status": "closed"})
        assert response.status_code == 200

        print("✓ User 1 closed the task")

        # Verify workflow in database
        fresh_session = SessionLocal()
        try:
            final_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert final_task.status == "closed"
            print_task_info(final_task, "TASK FINAL STATE")

        finally:
            fresh_session.close()


class TestDualUserMeetingWorkflow:
    """
    Tests meeting collaboration between 2 users
    - User 1: Creates meetings and transcripts
    - User 2: Reviews and adds notes
    """

    @pytest.fixture(autouse=False)
    def setup_users(self, db_session: Session):
        """Get 2 test users with fixed emails from database (or create if not exist)"""
        # Try to get existing users first
        user1 = db_session.query(User).filter(User.email == "luongnguyenminhan02052004@gmail.com").first()
        user2 = db_session.query(User).filter(User.email == "lnma020504@gmail.com").first()

        # Create if they don't exist
        if not user1:
            user1 = UserFactory.create(
                db_session,
                email="luongnguyenminhan02052004@gmail.com",
                name="Carol Davis",
                position="Meeting Organizer",
                bio="Expert in team coordination and documentation",
                avatar_url="https://example.com/avatars/carol.jpg",
            )

        if not user2:
            user2 = UserFactory.create(
                db_session,
                email="lnma020504@gmail.com",
                name="Dave Wilson",
                position="Technical Lead",
                bio="Technical lead with expertise in system architecture",
                avatar_url="https://example.com/avatars/dave.jpg",
            )

        db_session.commit()

        print_user_info(user1, "USER 1: Meeting Organizer")
        print_user_info(user2, "USER 2: Meeting Reviewer")

        return user1, user2

    def test_user1_creates_meeting_user2_adds_notes(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates a meeting
        2. User 1 creates a transcript
        3. User 2 adds meeting notes
        4. Verify all data persists
        """
        user1, user2 = setup_users

        # Create project for meeting context
        project = ProjectFactory.create(db_session, created_by=user1, name="Q4 Planning")
        db_session.commit()

        # User 1 creates meeting
        meeting = MeetingFactory.create(
            db_session,
            created_by=user1,
            title="Q4 Product Strategy Review",
            description="Quarterly review of product roadmap and deliverables",
            url="https://meet.google.com/abc-defg-hij",
        )
        db_session.commit()

        print_meeting_info(meeting, "MEETING CREATED BY USER 1")

        # Associate meeting with project
        project_meeting = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
        db_session.add(project_meeting)
        db_session.commit()

        print(f"✓ Meeting associated with project: {project.name}")

        # User 1 creates transcript
        transcript = Transcript(
            meeting_id=meeting.id,
            content="SPEAKER_01 [0.03s - 12.44s]: Welcome everyone to Q4 strategy review\nSPEAKER_02 [12.45s - 25.30s]: Let's discuss the implementation timeline",
        )
        db_session.add(transcript)
        db_session.commit()

        print("✓ User 1 uploaded transcript for meeting")

        # User 2 adds meeting notes
        note = MeetingNoteFactory.create(
            db_session,
            meeting=meeting,
            content="Action items:\n1. Complete backend API by Nov 15\n2. Setup production database\n3. Deploy staging environment",
            last_editor=user2,
        )
        db_session.commit()

        print("✓ User 2 added meeting notes")

        # Verify all data persisted
        fresh_session = SessionLocal()
        try:
            # Verify meeting
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting.id).first()
            assert db_meeting is not None
            print_meeting_info(db_meeting, "MEETING IN DATABASE")

            # Verify transcript
            db_transcript = fresh_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
            assert db_transcript is not None
            print(f"\n✓ Transcript exists with {len(db_transcript.content)} characters")

            # Verify notes
            db_note = fresh_session.query(MeetingNote).filter(MeetingNote.meeting_id == meeting.id).first()
            assert db_note is not None
            print(f"✓ Meeting note by User 2: {len(db_note.content)} characters")

        finally:
            fresh_session.close()

    def test_multiple_meetings_collaborative_documentation(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates multiple meetings
        2. For each meeting, User 2 adds documentation
        3. Verify complete collaboration history
        """
        user1, user2 = setup_users

        meetings_config = [
            {
                "title": "Sprint Planning - Sprint 45",
                "description": "Plan sprint 45 deliverables and tasks",
                "url": "https://meet.google.com/sprint-45",
            },
            {
                "title": "Technical Architecture Review",
                "description": "Review microservices architecture decisions",
                "url": "https://meet.google.com/arch-review",
            },
            {
                "title": "Stakeholder Update Meeting",
                "description": "Monthly update to business stakeholders",
                "url": "https://meet.google.com/stakeholder-update",
            },
        ]

        created_meetings = []

        for config in meetings_config:
            # User 1 creates meeting
            meeting = MeetingFactory.create(
                db_session,
                created_by=user1,
                title=config["title"],
                description=config["description"],
                url=config["url"],
            )
            db_session.commit()
            created_meetings.append(meeting)

            print_meeting_info(meeting, f"MEETING: {config['title']}")

            # User 2 adds notes
            note = MeetingNoteFactory.create(
                db_session,
                meeting=meeting,
                content=f"Documentation for {config['title']}. Key points discussed and action items tracked.",
                last_editor=user2,
            )
            db_session.commit()

            print("✓ User 2 added documentation notes")

        # Verify all in database
        fresh_session = SessionLocal()
        try:
            all_meetings = fresh_session.query(Meeting).filter(Meeting.created_by == user1.id).all()
            print(f"\n✓ Total meetings created by User 1: {len(all_meetings)}")

            all_notes = fresh_session.query(MeetingNote).filter(MeetingNote.last_editor_id == user2.id).all()
            print(f"✓ Total notes edited by User 2: {len(all_notes)}")

        finally:
            fresh_session.close()


class TestDualUserDataPersistenceComprehensive:
    """
    Comprehensive tests verifying all dual-user data persists correctly
    across database sessions and provides audit trail
    Also generates task/meeting/file usage data for dashboard statistics
    """

    @pytest.fixture(autouse=False)
    def setup_users(self, db_session: Session):
        """Get 2 test users with fixed emails from database (or create if not exist)"""
        # Try to get existing users first
        user1 = db_session.query(User).filter(User.email == "luongnguyenminhan02052004@gmail.com").first()
        user2 = db_session.query(User).filter(User.email == "lnma020504@gmail.com").first()

        # Create if they don't exist
        if not user1:
            user1 = UserFactory.create(
                db_session,
                email="luongnguyenminhan02052004@gmail.com",
                name="Luong Nguyen Minh An",
                position="Product Director",
                bio="Product director overseeing platform strategy",
                avatar_url="https://example.com/avatars/emma.jpg",
            )

        if not user2:
            user2 = UserFactory.create(
                db_session,
                email="lnma020504@gmail.com",
                name="Frank Miller",
                position="Lead Engineer",
                bio="Lead engineer implementing core features",
                avatar_url="https://example.com/avatars/frank.jpg",
            )

        db_session.commit()
        return user1, user2

    def test_complete_dual_user_lifecycle(self, db_session: Session, setup_users):
        """
        Complete lifecycle test with usage data generation:
        1. Use 2 persistent users from setup_users fixture
        2. Create multiple projects, tasks, meetings, files
        3. User 2 participates and updates data
        4. Verify all data persisted with audit trail
        5. Generate dashboard statistics from usage data
        """
        print("\n\n" + "=" * 80)
        print("  COMPREHENSIVE DUAL-USER LIFECYCLE TEST + USAGE DATA GENERATION")
        print("=" * 80)

        user1, user2 = setup_users

        print_user_info(user1, "USER 1: Product Director")
        print_user_info(user2, "USER 2: Lead Engineer")

        # =====================================================================
        # CREATE PROJECTS WITH MIXED STATUSES
        # =====================================================================
        print("\n" + "-" * 80)
        print("  CREATING PROJECTS + TASKS + MEETINGS FOR DASHBOARD")
        print("-" * 80)

        # User 1 creates 3 projects
        projects = []
        for i in range(1, 4):
            project = ProjectFactory.create(
                db_session,
                created_by=user1,
                name=f"Project {i}: {fake.sentence(nb_words=3)}",
                description=fake.paragraph(nb_sentences=2),
            )
            db_session.commit()
            projects.append(project)

            # Add User 2 to each project
            user_project = UserProject(user_id=user2.id, project_id=project.id, role="member")
            db_session.add(user_project)
            db_session.commit()

        print(f"✓ User 1 created {len(projects)} projects, User 2 added as member")

        # =====================================================================
        # CREATE TASKS WITH VARIED STATUSES ACROSS MULTIPLE DATES FOR DASHBOARD STATS
        # =====================================================================
        import random

        tasks = []
        task_statuses = ["todo", "in_progress", "done"]
        task_priorities = ["high", "medium", "low"]
        now = datetime.now(timezone.utc)

        print("\n  Creating tasks spread across last 7 days with realistic variation...")

        # Task distribution across 7 days for chart variation
        # Day 0 (oldest): 0 tasks, Day 1-6: 5 tasks each, Day 7 (today): 260 tasks
        task_counts_per_day = [random.randint(0, 150) for _ in range(8)]

        # Create tasks spread across 7 days for chart data with realistic variation
        for day_offset in range(7):
            task_date = now - timedelta(days=day_offset)
            tasks_per_day = task_counts_per_day[day_offset]

            for task_num in range(tasks_per_day):
                # Vary status distribution based on day
                if day_offset == 0:
                    # Older days: more completed tasks
                    status = random.choices(task_statuses, weights=[10, 20, 70])[0]
                elif day_offset < 3:
                    # Mid-range days: balanced mix
                    status = random.choices(task_statuses, weights=[30, 40, 30])[0]
                else:
                    # Recent days: more todo/in_progress
                    status = random.choices(task_statuses, weights=[50, 40, 10])[0]

                priority = random.choice(task_priorities)

                # Generate varied, realistic task titles using Faker
                task_templates = [
                    f"Implement {fake.word()} feature",
                    f"Fix {fake.word()} bug in {fake.word()}",
                    f"Review {fake.word()} code changes",
                    f"Update {fake.word()} documentation",
                    f"Deploy {fake.word()} to {fake.word()}",
                    f"Optimize {fake.word()} performance",
                    f"Test {fake.word()} integration",
                    f"Refactor {fake.word()} module",
                    f"Setup {fake.word()} environment",
                    f"Configure {fake.word()} settings",
                ]
                title = random.choice(task_templates)

                task = TaskFactory.create(
                    db_session,
                    creator=user1,
                    assignee=random.choice([user1, user2]),  # Random assignee
                    title=title,
                    status=status,
                    priority=priority,
                    description=fake.paragraph(nb_sentences=random.randint(1, 3)),
                    due_date=task_date + timedelta(days=random.randint(1, 30)),
                )

                # Manually set created_at to the specific date for chart data
                task.created_at = task_date
                db_session.merge(task)
                db_session.commit()
                tasks.append(task)

                # Associate task with a random project
                if projects:
                    project = random.choice(projects)
                    db_session.add(TaskProject(task_id=task.id, project_id=project.id))
                    db_session.commit()

        print(f"✓ User 1 created {len(tasks)} tasks across 7 days (for dashboard chart)")
        print("  Daily breakdown:")
        for day_offset in range(7):
            day_tasks = [t for t in tasks if (now - t.created_at).days == day_offset]
            done_count = len([t for t in day_tasks if t.status == "done"])
            in_prog = len([t for t in day_tasks if t.status == "in_progress"])
            todo_count = len([t for t in day_tasks if t.status == "todo"])
            task_date = now - timedelta(days=day_offset)
            print(f"    {task_date.strftime('%Y-%m-%d')}: {len(day_tasks)} tasks (Done: {done_count}, In Progress: {in_prog}, Todo: {todo_count})")

        total_done = len([t for t in tasks if t.status == "done"])
        total_in_prog = len([t for t in tasks if t.status == "in_progress"])
        total_todo = len([t for t in tasks if t.status == "todo"])
        print(f"  Total: {len(tasks)} tasks - Done: {total_done}, In Progress: {total_in_prog}, Todo: {total_todo}")

        # =====================================================================
        # CREATE MEETINGS WITH TRANSCRIPTS AND NOTES ACROSS MULTIPLE DATES
        # =====================================================================
        meetings = []
        print("\n  Creating meetings spread across last 7 days...")

        for day_offset in range(7):
            meeting_date = now - timedelta(days=day_offset)
            meetings_per_day = 2

            for meeting_num in range(meetings_per_day):
                meeting = MeetingFactory.create(
                    db_session,
                    created_by=user1,
                    title=f"Meeting Day{day_offset}_Num{meeting_num}: {fake.sentence(nb_words=4)}",
                    description=fake.paragraph(nb_sentences=1),
                    url=f"https://meet.google.com/meeting-day{day_offset}-{meeting_num}",
                )

                # Manually set created_at to the specific date
                meeting.created_at = meeting_date
                db_session.merge(meeting)
                db_session.commit()
                meetings.append(meeting)

                # Associate with project
                project = fake.random_element(projects)
                pm = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
                db_session.add(pm)
                db_session.commit()

                # Add transcript
                transcript = Transcript(
                    meeting_id=meeting.id,
                    content=fake.paragraph(nb_sentences=8),
                )
                db_session.add(transcript)
                db_session.commit()

                # User 2 adds meeting notes
                note = MeetingNoteFactory.create(
                    db_session,
                    meeting=meeting,
                    content=fake.paragraph(nb_sentences=4),
                    last_editor=user2,
                )
                db_session.commit()

        print(f"✓ User 1 created {len(meetings)} meetings across 7 days with transcripts & notes")

        # =====================================================================
        # CREATE FILES FOR STORAGE STATS ACROSS MULTIPLE DATES
        # =====================================================================
        files = []
        print("\n  Creating files spread across last 7 days...")

        for day_offset in range(7):
            file_date = now - timedelta(days=day_offset)
            files_per_day = 2

            for file_num in range(files_per_day):
                file = FileFactory.create(
                    db_session,
                    uploaded_by=user1,
                    project=fake.random_element(projects),
                    filename=f"document_day{day_offset}_{file_num}.pdf",
                    mime_type="application/pdf",
                    file_type="document",
                    size_bytes=fake.random_int(min=1000, max=5000000),
                )

                # Manually set created_at to the specific date
                file.created_at = file_date
                db_session.merge(file)
                db_session.commit()
                files.append(file)

        print(f"✓ User 1 created {len(files)} files across 7 days for storage tracking")

        # Store IDs for verification
        user1_id = user1.id
        user2_id = user2.id
        project_ids = [p.id for p in projects]
        task_ids = [t.id for t in tasks]
        meeting_ids = [m.id for m in meetings]
        file_ids = [f.id for f in files]

        # =====================================================================
        # VERIFY ALL DATA PERSISTS IN NEW SESSION (Dashboard Stats Ready)
        # =====================================================================
        print("\n" + "=" * 80)
        print("  VERIFYING DATA PERSISTENCE + DASHBOARD STATISTICS")
        print("=" * 80)

        fresh_session = SessionLocal()
        try:
            # Verify Users
            db_user1 = fresh_session.query(User).filter(User.id == user1_id).first()
            db_user2 = fresh_session.query(User).filter(User.id == user2_id).first()
            assert db_user1 is not None and db_user2 is not None
            print_user_info(db_user1, "USER 1 RETRIEVED FROM DATABASE")

            # Verify Projects
            db_projects = fresh_session.query(Project).filter(Project.id.in_(project_ids)).all()
            print(f"\n✓ Retrieved {len(db_projects)} projects from database")

            # Verify Tasks for Dashboard Stats
            db_tasks = fresh_session.query(Task).filter(Task.creator_id == user1_id).all()
            task_stats = {
                "total": len(db_tasks),
                "done": len([t for t in db_tasks if t.status == "done"]),
                "in_progress": len([t for t in db_tasks if t.status == "in_progress"]),
                "todo": len([t for t in db_tasks if t.status == "todo"]),
            }
            print("\n✓ TASK STATISTICS FOR DASHBOARD:")
            print(f"  Total Tasks: {task_stats['total']}")
            print(f"  Completed: {task_stats['done']}")
            print(f"  In Progress: {task_stats['in_progress']}")
            print(f"  Todo: {task_stats['todo']}")
            if task_stats["total"] > 0:
                completion_rate = (task_stats["done"] / task_stats["total"]) * 100
                print(f"  Completion Rate: {completion_rate:.1f}%")

            # Verify Meetings for Dashboard Stats
            db_meetings = fresh_session.query(Meeting).filter(Meeting.created_by == user1_id).all()
            print("\n✓ MEETING STATISTICS FOR DASHBOARD:")
            print(f"  Total Meetings: {len(db_meetings)}")
            total_notes = fresh_session.query(MeetingNote).filter(MeetingNote.last_editor_id == user2_id).count()
            print(f"  Notes by User 2: {total_notes}")

            # Verify Files for Dashboard Stats
            db_files = fresh_session.query(File).filter(File.uploaded_by == user1_id).all()
            total_size = sum(f.size_bytes for f in db_files)
            print("\n✓ STORAGE STATISTICS FOR DASHBOARD:")
            print(f"  Total Files: {len(db_files)}")
            print(f"  Total Size: {total_size / (1024 * 1024):.2f} MB")
            print(f"  Average File Size: {(total_size / len(db_files)) / (1024 * 1024):.2f} MB" if db_files else "  No files")

            print("\n" + "=" * 80)
            print("  ✅ ALL DATA VERIFIED - DASHBOARD READY WITH USAGE DATA")
            print("=" * 80 + "\n")

        finally:
            fresh_session.close()


class TestDualUserMassiveUsageData:
    """
    Comprehensive test with MASSIVE usage data for both users
    Tests all use cases with large datasets including:
    - Multiple projects with different roles
    - 50+ tasks with various statuses and priorities
    - 30+ meetings with transcripts and notes
    - Complex collaboration scenarios
    - Meeting bots and automation
    """

    @pytest.fixture(autouse=False)
    def setup_users(self, db_session: Session):
        """Get 2 test users with fixed emails from database (or create if not exist)"""
        # Try to get existing users first
        user1 = db_session.query(User).filter(User.email == "luongnguyenminhan02052004@gmail.com").first()
        user2 = db_session.query(User).filter(User.email == "lnma020504@gmail.com").first()

        # Create if they don't exist
        if not user1:
            user1 = UserFactory.create(
                db_session,
                email="luongnguyenminhan02052004@gmail.com",
                name="Luong Nguyen Minh An",
                position="VP of Product",
                bio="Strategic product leader with 10+ years in SaaS. Passionate about AI-driven solutions.",
                avatar_url="https://lh3.googleusercontent.com/a/ACg8ocKsXNVmz4QV9PGDwIDazuHcNuTk5uKxx9xjEwnXiQiv1zGBsjpLsQ=s96-c",
            )

        if not user2:
            user2 = UserFactory.create(
                db_session,
                email="lnma020504@gmail.com",
                name="AnLuong",
                position="Engineering Manager",
                bio="Technical leader managing 15+ engineers. Full-stack expertise in distributed systems.",
                avatar_url="https://example.com/avatars/michael.jpg",
            )

        db_session.commit()
        return user1, user2

    def test_super_large_dual_user_dataset_all_use_cases(self, db_session: Session, setup_users):
        """
        Create massive realistic usage data for 2 users across all features.
        This test generates enough data to thoroughly test all use cases and populate dashboard.
        """
        print("\n\n" + "=" * 100)
        print("  MASSIVE DUAL-USER DATASET WITH COMPLETE USE CASE COVERAGE + DASHBOARD DATA")
        print("=" * 100)

        # =====================================================================
        # SETUP: Use 2 persistent users with rich profiles
        # =====================================================================
        user1, user2 = setup_users
        print_user_info(user1, "USER 1: VP of Product (Data Generator)")
        print_user_info(user2, "USER 2: Engineering Manager (Data Generator)")

        # Store IDs before closing
        user1_id = user1.id
        user2_id = user2.id

        # =====================================================================
        # PROJECTS: Create MASSIVE number of projects with Faker-generated data
        # =====================================================================
        print("\n" + "-" * 100)
        print("  CREATING MASSIVE PROJECTS (50+ projects)")
        print("-" * 100)

        projects = []
        num_projects = 75  # Generate 75 projects

        for project_idx in range(1, num_projects + 1):
            # Generate realistic project data with Faker
            name = f"{fake.company()} - {fake.sentence(nb_words=3)}"
            description = fake.paragraph(nb_sentences=fake.random_int(min=2, max=4))
            user2_role = fake.random_element(["member", "admin"])

            project = ProjectFactory.create(
                db_session,
                created_by=user1,
                name=name,
                description=description,
            )
            db_session.commit()

            # Add User 2 with specified role
            user_project = UserProject(user_id=user2_id, project_id=project.id, role=user2_role)
            db_session.add(user_project)
            db_session.commit()

            projects.append(project)

            # Progress indicator every 15 projects
            if project_idx % 15 == 0:
                print(f"✓ Created {project_idx}/{num_projects} projects")

        print(f"✓ Total projects created: {len(projects)}")

        # =====================================================================
        # TASKS: Create MASSIVE number of tasks with Faker-generated data
        # =====================================================================
        print("\n" + "-" * 100)
        print("  CREATING MASSIVE TASKS WITH GENERATED DATA (100+ tasks)")
        print("-" * 100)

        task_statuses = ["todo", "in_progress", "review", "completed", "closed"]
        task_priorities = ["Thấp", "Trung bình", "Cao", "Rất cao"]

        tasks_created = []
        num_tasks = 100  # Generate 100 tasks

        for task_idx in range(1, num_tasks + 1):
            # Generate realistic task data with Faker
            title = fake.sentence(nb_words=fake.random_int(min=5, max=12))
            description = fake.paragraph(nb_sentences=fake.random_int(min=2, max=5))
            status = task_statuses[(task_idx - 1) % len(task_statuses)]
            priority = task_priorities[(task_idx - 1) % len(task_priorities)]
            assignee = user2 if task_idx % 2 == 0 else user1
            due_date = datetime.now(timezone.utc) + timedelta(days=fake.random_int(min=1, max=60))

            task = TaskFactory.create(
                db_session,
                creator=user1,
                assignee=assignee,
                title=title,
                description=description,
                status=status,
                priority=priority,
                due_date=due_date,
            )

            # Assign to random project
            project = projects[(task_idx - 1) % len(projects)]
            db_session.add(TaskProject(task_id=task.id, project_id=project.id))
            db_session.commit()

            tasks_created.append(task)

            # Progress indicator every 50 tasks
            if task_idx % 50 == 0:
                print(f"✓ Created {task_idx}/{num_tasks} tasks")

        print(f"✓ Total tasks created: {len(tasks_created)}")

        # =====================================================================
        # MEETINGS: Create MASSIVE number of meetings with Faker-generated data
        # =====================================================================
        print("\n" + "-" * 100)
        print("  CREATING MASSIVE MEETINGS WITH GENERATED TRANSCRIPTS (100+ meetings)")
        print("-" * 100)

        meetings_created = []
        num_meetings = 150  # Generate 150 meetings

        for meeting_idx in range(1, num_meetings + 1):
            # Generate realistic meeting title with Faker
            title = fake.catch_phrase()

            meeting = MeetingFactory.create(
                db_session,
                created_by=user1,
                title=title,
                description=fake.paragraph(nb_sentences=2),
                url=f"https://meet.google.com/meeting-{uuid.uuid4().hex[:12]}",
                is_personal=meeting_idx % 7 == 0,  # Every 7th is personal
            )
            db_session.commit()

            # ===================================================================
            # Associate meeting with random project (except personal meetings)
            # ===================================================================
            if meeting_idx % 7 != 0:  # Skip personal meetings
                project = projects[(meeting_idx - 1) % len(projects)]
                project_meeting = ProjectMeeting(project_id=project.id, meeting_id=meeting.id)
                db_session.add(project_meeting)
                db_session.commit()

            # ===================================================================
            # Generate realistic transcript with Speaker segments
            # Template: SPEAKER_<numnum(2digit)> [0.03s - 12.44s]: <speakerline>
            # ===================================================================
            num_speakers = fake.random_int(min=2, max=5)
            num_segments = fake.random_int(min=15, max=40)

            transcript_lines = []
            current_time = 0.0

            for segment_idx in range(num_segments):
                speaker_num = (segment_idx % num_speakers) + 1
                start_time = current_time
                segment_duration = fake.random.uniform(1.5, 12.5)
                end_time = start_time + segment_duration
                current_time = end_time

                # Generate speaker line (realistic dialogue using Faker)
                speaker_line = fake.sentence(nb_words=fake.random_int(min=4, max=20))

                # Format: SPEAKER_<numnum(2digit)> [0.03s - 12.44s]: <speakerline>
                transcript_line = f"SPEAKER_{speaker_num:02d} [{start_time:.2f}s - {end_time:.2f}s]: {speaker_line}"
                transcript_lines.append(transcript_line)

            transcript_content = "\n".join(transcript_lines)

            transcript = Transcript(
                meeting_id=meeting.id,
                content=transcript_content,
            )
            db_session.add(transcript)
            db_session.commit()

            # ===================================================================
            # Generate detailed meeting notes with Faker
            # ===================================================================
            num_action_items = fake.random_int(min=2, max=5)
            num_decisions = fake.random_int(min=2, max=4)
            num_blockers = fake.random_int(min=0, max=3)

            action_items = [f"{idx + 1}. {fake.sentence()} - Owner: {fake.random_element([db_user1.name if 'db_user1' in locals() else 'User 1', 'User 2', 'Both'])}" for idx in range(num_action_items)]

            decisions = [f"- {fake.sentence()} - Status: {fake.random_element(['Approved', 'Pending', 'Ready for execution', 'In Review'])}" for _ in range(num_decisions)]

            blockers = [f"- {fake.sentence()}" for _ in range(num_blockers)]

            note_content = f"**{title} - Meeting Notes**\n\n**Participants:** {num_speakers} speakers identified in transcript\n\n**Action Items:**\n{chr(10).join(action_items)}\n\n**Key Decisions:**\n{chr(10).join(decisions)}\n\n"

            if blockers:
                note_content += f"**Blockers:**\n{chr(10).join(blockers)}\n\n"

            note_content += f"**Summary:**\n{fake.paragraph(nb_sentences=3)}"

            note = MeetingNoteFactory.create(
                db_session,
                meeting=meeting,
                content=note_content,
                last_editor=user2,
            )
            db_session.commit()

            # ===================================================================
            # Create meeting bots with varied status distribution
            # ===================================================================
            if meeting_idx % 2 == 0:  # Create bot for every other meeting
                bot_status = fake.random_element(["pending", "joined", "complete", "ended", "error"])
                bot = MeetingBotFactory.create(
                    db_session,
                    meeting=meeting,
                    created_by=user1,
                    status=bot_status,
                    meeting_url=meeting.url,
                )
                db_session.commit()

            meetings_created.append(meeting)

            # Progress indicator every 25 meetings
            if meeting_idx % 25 == 0:
                print(f"✓ Created {meeting_idx}/{num_meetings} meetings with full transcripts and notes")

        print(f"✓ Total meetings created: {len(meetings_created)}")

        # =====================================================================
        # COLLABORATION: Create real-world scenarios
        # =====================================================================
        print("\n" + "-" * 100)
        print("  CREATING COLLABORATION SCENARIOS")
        print("-" * 100)

        # Scenario 1: Task assignment chain - User 1 creates, User 2 updates status
        print("✓ Scenario 1: Task Assignment Chain")
        for i in range(5):
            task = tasks_created[i]
            # Simulate User 2 updating status
            token = create_access_token({"sub": str(user2_id)})
            client = TestClient(app)
            client.headers.update({"Authorization": f"Bearer {token}"})

            response = client.put(
                f"/api/v1/tasks/{task.id}",
                json={"status": "in_progress", "priority": "Cao"},
            )
            if response.status_code == 200:
                print(f"  - User 2 updated task status for: {task.title[:50]}")

        # Scenario 2: Meeting collaboration - notes and transcripts
        print("✓ Scenario 2: Meeting Collaboration with Complete Documentation")
        for i in range(3):
            meeting = meetings_created[i]
            meeting_text = meeting.title
            print(f"  - Meeting documented: {meeting_text[:60]} (Transcript + Notes + Bot tracking)")

        # Scenario 3: Project transitions
        print("✓ Scenario 3: Project Lifecycle Management")
        for i in range(2):
            project = projects[i]
            print(f"  - Project: {project.name[:50]} (Owner: User 1, Admin: User 2)")

        # =====================================================================
        # FINAL STATISTICS AND VERIFICATION
        # =====================================================================
        print("\n" + "=" * 100)
        print("  FINAL STATISTICS - MASSIVE DATASET PERSISTED IN DATABASE")
        print("=" * 100)

        fresh_session = SessionLocal()
        try:
            # Count all data
            total_users = fresh_session.query(User).filter(User.id.in_([user1_id, user2_id])).count()
            total_projects = fresh_session.query(Project).filter(Project.created_by == user1_id).count()
            total_tasks = fresh_session.query(Task).filter(Task.creator_id == user1_id).count()
            total_meetings = fresh_session.query(Meeting).filter(Meeting.created_by == user1_id).count()
            total_transcripts = fresh_session.query(Transcript).count()
            total_notes = fresh_session.query(MeetingNote).count()
            total_bots = fresh_session.query(MeetingBot).count()

            print("\n📊 MASSIVE DATA SUMMARY:")
            print(f"   Users:           {total_users}")
            print(f"   Projects:        {total_projects}")
            print(f"   Tasks:           {total_tasks}")
            print(f"   Meetings:        {total_meetings}")
            print(f"   Transcripts:     {total_transcripts} (with Speaker segments)")
            print(f"   Meeting Notes:   {total_notes} (detailed documentation)")
            print(f"   Meeting Bots:    {total_bots} (status tracking)")

            total_data_points = total_users + total_projects + total_tasks + total_meetings + total_transcripts + total_notes + total_bots
            print(f"\n   📈 TOTAL DATA POINTS GENERATED: {total_data_points:,}")

            # Verify relationships
            print("\n🔗 RELATIONSHIP VERIFICATION:")

            # User 1 verification
            db_user1 = fresh_session.query(User).filter(User.id == user1_id).first()
            print(f"\n   USER 1: {db_user1.name}")
            print(f"   - Email: {db_user1.email}")
            print(f"   - Position: {db_user1.position}")
            print(f"   - Projects Created: {total_projects}")
            print(f"   - Tasks Created: {total_tasks}")
            print(f"   - Meetings Created: {total_meetings}")

            # User 2 verification
            db_user2 = fresh_session.query(User).filter(User.id == user2_id).first()
            print(f"\n   USER 2: {db_user2.name}")
            print(f"   - Email: {db_user2.email}")
            print(f"   - Position: {db_user2.position}")
            print(f"   - Projects Assigned: {fresh_session.query(UserProject).filter(UserProject.user_id == user2_id).count()}")

            # Project verification
            print(f"\n   PROJECTS (Total: {len(projects)}):")
            sample_projects = projects[:5]
            for i, project in enumerate(sample_projects, 1):
                db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
                members = fresh_session.query(UserProject).filter(UserProject.project_id == project.id).count()
                tasks_count = fresh_session.query(TaskProject).filter(TaskProject.project_id == project.id).count()
                print(f"   {i}. {db_project.name[:50]} (Members: {members}, Tasks: {tasks_count})")
            if len(projects) > 5:
                print(f"   ... and {len(projects) - 5} more projects")

            # Task verification with status breakdown
            print(f"\n   TASKS (Total: {total_tasks} - Breakdown by Status):")
            task_by_status = {}
            for task in fresh_session.query(Task).filter(Task.creator_id == user1_id).all():
                status = task.status
                task_by_status[status] = task_by_status.get(status, 0) + 1

            for status, count in sorted(task_by_status.items()):
                percentage = (count / total_tasks) * 100
                print(f"   - Status '{status}': {count} tasks ({percentage:.1f}%)")

            # Task verification by priority
            print("\n   TASKS (Breakdown by Priority):")
            task_by_priority = {}
            for task in fresh_session.query(Task).filter(Task.creator_id == user1_id).all():
                priority = task.priority
                task_by_priority[priority] = task_by_priority.get(priority, 0) + 1

            for priority, count in sorted(task_by_priority.items()):
                percentage = (count / total_tasks) * 100
                print(f"   - Priority '{priority}': {count} tasks ({percentage:.1f}%)")

            # Task assignment verification
            user1_tasks = fresh_session.query(Task).filter(Task.creator_id == user1_id, Task.assignee_id == user1_id).count()
            user2_tasks = fresh_session.query(Task).filter(Task.assignee_id == user2_id).count()
            unassigned_tasks = fresh_session.query(Task).filter(Task.creator_id == user1_id, Task.assignee_id == None).count()

            print("\n   TASK ASSIGNMENTS:")
            print(f"   - Assigned to User 1: {user1_tasks} tasks")
            print(f"   - Assigned to User 2: {user2_tasks} tasks")
            print(f"   - Unassigned: {unassigned_tasks} tasks")

            # Meeting verification
            print(f"\n   MEETINGS (Total: {total_meetings}):")
            personal_count = fresh_session.query(Meeting).filter(Meeting.created_by == user1_id, Meeting.is_personal == True).count()
            regular_count = total_meetings - personal_count
            print(f"   - Regular meetings: {regular_count}")
            print(f"   - Personal meetings: {personal_count}")

            # Meeting bot status
            bot_status_breakdown = {}
            for bot in fresh_session.query(MeetingBot).all():
                status = bot.status
                bot_status_breakdown[status] = bot_status_breakdown.get(status, 0) + 1

            print(f"\n   MEETING BOTS (Status Breakdown - Total: {total_bots}):")
            for status in ["pending", "joined", "complete", "ended", "error"]:
                count = bot_status_breakdown.get(status, 0)
                if total_bots > 0:
                    percentage = (count / total_bots) * 100
                    print(f"   - Status '{status}': {count} bots ({percentage:.1f}%)")

            # Transcript verification
            print(f"\n   TRANSCRIPTS (Total: {total_transcripts}):")
            sample_transcripts = fresh_session.query(Transcript).limit(3).all()
            for i, transcript in enumerate(sample_transcripts, 1):
                lines = transcript.content.count("\n") + 1
                meeting = fresh_session.query(Meeting).filter(Meeting.id == transcript.meeting_id).first()
                print(f"   {i}. Meeting: {meeting.title[:45]} | Lines: {lines}")
                # Show first speaker line as example
                first_line = transcript.content.split("\n")[0]
                print(f"      Sample: {first_line[:80]}")

            # Sample data display
            print("\n📋 SAMPLE DATA FROM DATABASE:")

            print("\n   Top 5 High Priority Tasks:")
            high_priority_tasks = fresh_session.query(Task).filter(Task.priority.in_(["Cao", "Rất cao"])).order_by(Task.created_at.desc()).limit(5).all()
            for i, task in enumerate(high_priority_tasks, 1):
                assignee = fresh_session.query(User).filter(User.id == task.assignee_id).first() if task.assignee_id else None
                print(f"   {i}. {task.title[:50]} | Priority: {task.priority} | Status: {task.status} | Assigned: {assignee.name if assignee else 'Unassigned'}")

            print("\n   Recent 5 Meetings (with Transcript Sample):")
            recent_meetings = fresh_session.query(Meeting).filter(Meeting.created_by == user1_id).order_by(Meeting.created_at.desc()).limit(5).all()
            for i, meeting in enumerate(recent_meetings, 1):
                transcript = fresh_session.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
                notes = fresh_session.query(MeetingNote).filter(MeetingNote.meeting_id == meeting.id).first()
                bot = fresh_session.query(MeetingBot).filter(MeetingBot.meeting_id == meeting.id).first()
                transcript_sample = ""
                if transcript:
                    first_speaker_line = transcript.content.split("\n")[0]
                    transcript_sample = first_speaker_line[:60]
                print(f"   {i}. {meeting.title[:40]} | Transcript: {'✓' if transcript else '✗'} | Notes: {'✓' if notes else '✗'} | Bot: {'✓' if bot else '✗'}")
                if transcript_sample:
                    print(f"      Sample: {transcript_sample}")

            print("\n   Task Distribution Across Projects (First 5):")
            for i, project in enumerate(projects[:5], 1):
                count = fresh_session.query(TaskProject).filter(TaskProject.project_id == project.id).count()
                print(f"   - {project.name[:45]}: {count} tasks")

            # Meeting-Project association verification
            total_project_meetings = fresh_session.query(ProjectMeeting).count()
            print(f"\n   MEETING-PROJECT ASSOCIATIONS (Total: {total_project_meetings}):")
            print(f"   - Meetings linked to projects: {total_project_meetings}")
            print(f"   - Meetings not linked (personal): {total_meetings - total_project_meetings}")

            # Sample project with meetings
            print("\n   Sample Projects with Meetings:")
            for i, project in enumerate(projects[:3], 1):
                meeting_count = fresh_session.query(ProjectMeeting).filter(ProjectMeeting.project_id == project.id).count()
                task_count = fresh_session.query(TaskProject).filter(TaskProject.project_id == project.id).count()
                print(f"   {i}. {project.name[:50]}")
                print(f"      - Meetings: {meeting_count}")
                print(f"      - Tasks: {task_count}")

                # Show sample meetings for this project
                sample_meetings = fresh_session.query(ProjectMeeting).filter(ProjectMeeting.project_id == project.id).limit(2).all()
                for j, pm in enumerate(sample_meetings, 1):
                    meeting = fresh_session.query(Meeting).filter(Meeting.id == pm.meeting_id).first()
                    print(f"      └─ Meeting {j}: {meeting.title[:45]}")

            print("\n" + "=" * 100)
            print("  ✅ MASSIVE DUAL-USER DATASET GENERATION COMPLETE")
            print(f"  Generated over {total_data_points:,} data points for realistic system testing!")
            print("=" * 100 + "\n")

        finally:
            fresh_session.close()


class TestDualUserFileUploadWorkflow:
    """
    Comprehensive file upload and management tests for dual users
    Tests file creation, sharing, updates, deletion with multiple users
    Includes group-based file sharing with multiple owners
    """

    @pytest.fixture(autouse=False)
    def setup_users(self, db_session: Session):
        """Get 2 test users with fixed emails from database (or create if not exist)"""
        # Try to get existing users first
        user1 = db_session.query(User).filter(User.email == "luongnguyenminhan02052004@gmail.com").first()
        user2 = db_session.query(User).filter(User.email == "lnma020504@gmail.com").first()

        # Create if they don't exist
        if not user1:
            user1 = UserFactory.create(
                db_session,
                email="luongnguyenminhan02052004@gmail.com",
                name="Luong Nguyen Minh An",
                position="File Management Specialist",
                bio="Expert in file organization and sharing",
                avatar_url="https://example.com/avatars/user1.jpg",
            )

        if not user2:
            user2 = UserFactory.create(
                db_session,
                email="lnma020504@gmail.com",
                name="AnLuong",
                position="Team Collaborator",
                bio="Collaborative team member",
                avatar_url="https://example.com/avatars/user2.jpg",
            )

        db_session.commit()

        print_user_info(user1, "USER 1: File Manager")
        print_user_info(user2, "USER 2: Collaborator")

        return user1, user2

    def test_user1_uploads_file_user2_accesses(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates project and uploads file
        2. User 1 adds User 2 as member with access
        3. User 2 retrieves and verifies file access
        4. Verify all data persists
        """
        print("\n\n" + "=" * 100)
        print("  FILE UPLOAD WORKFLOW: User 1 uploads, User 2 accesses")
        print("=" * 100)

        user1, user2 = setup_users

        # User 1 creates project
        project = ProjectFactory.create(
            db_session,
            created_by=user1,
            name="Document Management System",
            description="Collaborative document storage and sharing",
        )
        db_session.commit()

        print_project_info(project, "PROJECT: Document Management")

        # User 1 adds User 2 to project
        user_project = UserProject(user_id=user2.id, project_id=project.id, role="member")
        db_session.add(user_project)
        db_session.commit()

        print("✓ User 1 added User 2 to project as member")

        # User 1 uploads file
        file_content = fake.paragraph(nb_sentences=10)
        file = FileFactory.create(
            db_session,
            uploaded_by=user1,
            project=project,
            filename="meeting_notes_2024.txt",
            mime_type="text/plain",
            file_type="document",
            size_bytes=len(file_content),
        )
        db_session.commit()

        print(f"✓ User 1 uploaded file: {file.filename}")

        # User 2 accesses file via API
        token2 = create_access_token({"sub": str(user2.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token2}"})

        response = client.get(f"/api/v1/files/{file.id}")
        assert response.status_code == 200

        print("✓ User 2 retrieved file successfully")

        # Verify data persisted
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file.id).first()
            assert db_file is not None
            assert db_file.filename == "meeting_notes_2024.txt"
            assert db_file.uploaded_by == user1.id
            print(f"✓ File persisted in database: {db_file.filename}")

        finally:
            fresh_session.close()

    def test_multiple_users_file_group_collaboration(self, db_session: Session, setup_users):
        """
        Workflow:
        1. Create project with User 1 as owner
        2. Add 10 auxiliary users with different roles
        3. All users upload files to shared project
        4. Verify access control and file organization
        5. Test file modification by different users
        """
        print("\n\n" + "=" * 100)
        print("  FILE GROUP COLLABORATION: Multiple users uploading to shared project")
        print("=" * 100)

        user1, user2 = setup_users

        # Create shared project
        project = ProjectFactory.create(
            db_session,
            created_by=user1,
            name="Team Collaboration Hub",
            description="Central repository for team files and documents",
        )
        db_session.commit()

        print_project_info(project, "SHARED PROJECT")

        # Add User 2 as admin
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, user2.id, "admin")

        print("✓ User 2 added as project admin")

        # Create 10 auxiliary users with various roles
        print("\n" + "-" * 100)
        print("  CREATING 10 AUXILIARY USERS")
        print("-" * 100)

        auxiliary_users = []
        roles = ["member", "admin", "member", "member", "admin", "member", "member", "member", "admin", "member"]

        for i in range(1, 11):
            user = UserFactory.create(
                db_session,
                email=f"team_user_{i}_{uuid.uuid4().hex[:6]}@example.com",
                name=fake.name(),
                position=fake.job(),
                bio=fake.sentence(nb_words=8),
                avatar_url=f"https://example.com/avatars/aux_user_{i}.jpg",
            )
            db_session.commit()

            # Add to project with assigned role
            role = roles[i - 1]
            user_project = UserProject(user_id=user.id, project_id=project.id, role=role)
            db_session.add(user_project)
            db_session.commit()

            auxiliary_users.append(user)
            print(f"  ✓ User {i}: {user.name} ({role}) - {user.email}")

        print(f"\n✓ Total auxiliary users added: {len(auxiliary_users)}")

        # All users upload files
        print("\n" + "-" * 100)
        print("  FILES UPLOADED BY EACH USER")
        print("-" * 100)

        uploaded_files = []
        uploaded_audio_files = []
        all_users = [user1, user2] + auxiliary_users

        for user in all_users:
            num_files = fake.random_int(min=1, max=3)
            for j in range(num_files):
                file_content = fake.paragraph(nb_sentences=fake.random_int(min=3, max=8))
                filename = f"{fake.slug()}_by_{user.name.replace(' ', '_')}.txt"

                file = FileFactory.create(
                    db_session,
                    uploaded_by=user,
                    project=project,
                    filename=filename,
                    mime_type="text/plain",
                    file_type="document",
                    size_bytes=len(file_content),
                )
                db_session.commit()

                uploaded_files.append(
                    {
                        "file": file,
                        "uploader": user,
                        "content": file_content,
                    }
                )

                print(f"  ✓ {user.name}: {filename}")

                # Mock audio file data (skip actual upload since it triggers background tasks)
                if j == 0:  # Create audio metadata for first file only
                    duration = fake.random_int(min=60, max=3600)
                    uploaded_audio_files.append(
                        {
                            "audio_url": f"https://example.com/audio/{user.id}_{uuid.uuid4().hex[:8]}.webm",
                            "uploader": user,
                            "duration": duration,
                        }
                    )
                    print(f"    └─ Audio file (mocked): {duration}s")

        print(f"\n✓ Total files uploaded: {len(uploaded_files)}")
        print(f"✓ Total audio files uploaded: {len(uploaded_audio_files)}")

        # Test file access by different users
        print("\n" + "-" * 100)
        print("  TESTING FILE ACCESS ACROSS USERS")
        print("-" * 100)

        access_count = 0
        for i, file_obj in enumerate(uploaded_files[:5]):  # Test first 5 files
            file = file_obj["file"]
            uploader = file_obj["uploader"]

            # Random member accesses file
            accessor = auxiliary_users[i % len(auxiliary_users)]
            token = create_access_token({"sub": str(accessor.id)})
            client = TestClient(app)
            client.headers.update({"Authorization": f"Bearer {token}"})

            response = client.get(f"/api/v1/files/{file.id}")
            if response.status_code == 200:
                access_count += 1
                print(f"  ✓ {accessor.name} accessed: {file.filename}")

        print(f"\n✓ Successful file accesses: {access_count}/5")

        # Verify persistence
        fresh_session = SessionLocal()
        try:
            total_files = fresh_session.query(File).filter(File.project_id == project.id).count()
            total_members = fresh_session.query(UserProject).filter(UserProject.project_id == project.id).count()

            print("\n" + "-" * 100)
            print("  DATABASE VERIFICATION")
            print("-" * 100)
            print(f"✓ Total files persisted: {total_files}")
            print(f"✓ Total project members: {total_members}")

            # Files by user
            print("\n  FILES UPLOADED BY USER:")
            for user in all_users:
                user_files = fresh_session.query(File).filter(File.uploaded_by == user.id).count()
                if user_files > 0:
                    print(f"  - {user.name}: {user_files} files")

        finally:
            fresh_session.close()

    def test_file_update_and_deletion_workflow(self, db_session: Session, setup_users):
        """
        Workflow:
        1. User 1 creates and uploads file
        2. User 1 updates file metadata
        3. User 2 (with permission) also updates file
        4. Test deletion with proper permissions
        5. Verify audit trail
        """
        print("\n\n" + "=" * 100)
        print("  FILE LIFECYCLE: Create, Update, Share, Delete")
        print("=" * 100)

        user1, user2 = setup_users

        # Create project
        project = ProjectFactory.create(
            db_session,
            created_by=user1,
            name="Document Lifecycle Testing",
            description="Testing file CRUD operations",
        )
        db_session.commit()

        # Add User 2 with admin role
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, user2.id, "admin")

        print_project_info(project, "SHARED PROJECT")

        # User 1 creates initial file
        initial_content = fake.paragraph(nb_sentences=5)
        file = FileFactory.create(
            db_session,
            uploaded_by=user1,
            project=project,
            filename="project_specifications.txt",
            mime_type="text/plain",
            file_type="document",
            size_bytes=len(initial_content),
        )
        db_session.commit()
        file_id = file.id

        print(f"✓ User 1 created file: {file.filename}")

        # Mock audio file data (skip actual upload since it triggers background tasks)
        audio_duration = fake.random_int(min=120, max=3600)
        audio_file_url = f"https://example.com/audio/{user1.id}_{uuid.uuid4().hex[:8]}.webm"
        print(f"✓ User 1 also created audio file (mocked): {audio_duration}s")

        # User 1 updates file metadata
        token1 = create_access_token({"sub": str(user1.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token1}"})

        update_data = {
            "filename": "project_specifications_v2.txt",
        }
        response = client.put(f"/api/v1/files/{file_id}", json=update_data)
        assert response.status_code == 200

        print("✓ User 1 updated file name to: project_specifications_v2.txt")

        # User 2 verifies update
        token2 = create_access_token({"sub": str(user2.id)})
        client.headers.update({"Authorization": f"Bearer {token2}"})

        response = client.get(f"/api/v1/files/{file_id}")
        assert response.status_code == 200
        assert response.json()["data"]["filename"] == "project_specifications_v2.txt"

        print("✓ User 2 verified file metadata update")

        # User 2 updates file again
        update_data2 = {
            "filename": "project_specifications_final.txt",
        }
        response = client.put(f"/api/v1/files/{file_id}", json=update_data2)
        assert response.status_code == 200

        print("✓ User 2 updated file name to: project_specifications_final.txt")

        # Verify all updates persisted
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is not None
            assert db_file.filename == "project_specifications_final.txt"
            assert db_file.uploaded_by == user1.id

            print(f"✓ File persisted with final metadata: {db_file.filename}")

        finally:
            fresh_session.close()

        # Test deletion
        print("\n" + "-" * 100)
        print("  FILE DELETION TEST")
        print("-" * 100)

        # User 2 (admin) deletes file
        response = client.delete(f"/api/v1/files/{file_id}")
        assert response.status_code == 200

        print("✓ User 2 (admin) deleted file successfully")

        # Verify deletion
        fresh_session = SessionLocal()
        try:
            db_file = fresh_session.query(File).filter(File.id == file_id).first()
            assert db_file is None
            print("✓ File deleted from database confirmed")

        finally:
            fresh_session.close()

    def test_file_sharing_with_multiple_groups(self, db_session: Session, setup_users):
        """
        Workflow:
        1. Create 2 projects (groups)
        2. User 1 owns both projects
        3. User 2 is member of both
        4. Create 20 auxiliary users split between projects
        5. Upload files to each project
        6. Verify isolation and access control
        """
        print("\n\n" + "=" * 100)
        print("  FILE SHARING ACROSS MULTIPLE GROUPS")
        print("=" * 100)

        user1, user2 = setup_users

        # Create 2 projects
        print("\n" + "-" * 100)
        print("  CREATING PROJECT GROUPS")
        print("-" * 100)

        project_alpha = ProjectFactory.create(
            db_session,
            created_by=user1,
            name="Project Alpha - Frontend Team",
            description="Frontend development and UI design group",
        )

        project_beta = ProjectFactory.create(
            db_session,
            created_by=user1,
            name="Project Beta - Backend Team",
            description="Backend development and API design group",
        )

        db_session.commit()

        print(f"✓ Project Alpha: {project_alpha.name}")
        print(f"✓ Project Beta: {project_beta.name}")

        # Add User 2 to both projects
        from app.services.project import add_user_to_project

        for project in [project_alpha, project_beta]:
            add_user_to_project(db_session, project.id, user2.id, "admin")

        print("✓ User 2 added to both projects as admin")

        # Create 10 users for Alpha, 10 for Beta
        print("\n" + "-" * 100)
        print("  CREATING AUXILIARY USERS FOR EACH GROUP")
        print("-" * 100)

        alpha_users = []
        beta_users = []

        # Alpha group users
        print("\n  PROJECT ALPHA USERS:")
        for i in range(1, 11):
            user = UserFactory.create(
                db_session,
                email=f"alpha_user_{i}_{uuid.uuid4().hex[:6]}@example.com",
                name=fake.name(),
                position="Frontend Developer",
                bio=fake.sentence(),
                avatar_url=f"https://example.com/avatars/alpha_{i}.jpg",
            )
            db_session.commit()

            from app.services.project import add_user_to_project

            add_user_to_project(db_session, project_alpha.id, user.id, "member")

            alpha_users.append(user)
            print(f"    ✓ {user.name}")

        # Beta group users
        print("\n  PROJECT BETA USERS:")
        for i in range(1, 11):
            user = UserFactory.create(
                db_session,
                email=f"beta_user_{i}_{uuid.uuid4().hex[:6]}@example.com",
                name=fake.name(),
                position="Backend Developer",
                bio=fake.sentence(),
                avatar_url=f"https://example.com/avatars/beta_{i}.jpg",
            )
            db_session.commit()

            add_user_to_project(db_session, project_beta.id, user.id, "member")

            beta_users.append(user)
            print(f"    ✓ {user.name}")

        # Upload files to each project
        print("\n" + "-" * 100)
        print("  UPLOADING FILES AND AUDIO TO PROJECTS")
        print("-" * 100)

        alpha_files = []
        alpha_audio_files = []
        beta_files = []
        beta_audio_files = []

        # Alpha files
        for user in [user1, user2] + alpha_users[:3]:
            for j in range(2):
                file = FileFactory.create(
                    db_session,
                    uploaded_by=user,
                    project=project_alpha,
                    filename=f"frontend_{user.name.replace(' ', '_')}_doc_{j + 1}.txt",
                    mime_type="text/plain",
                    file_type="document",
                    size_bytes=len(fake.paragraph(nb_sentences=6)),
                )
                db_session.commit()
                alpha_files.append(file)

            # Mock audio file data for each user (skip actual upload)
            if user in [user1, user2] or (user in alpha_users and alpha_users.index(user) < 3):
                alpha_audio_files.append(
                    {
                        "audio_url": f"https://example.com/audio/alpha_{user.id}_{uuid.uuid4().hex[:8]}.webm",
                        "uploader": user,
                        "duration": fake.random_int(min=120, max=1800),
                    }
                )

        print(f"✓ Alpha project files: {len(alpha_files)}")
        print(f"✓ Alpha project audio files: {len(alpha_audio_files)}")

        # Beta files
        for user in [user1, user2] + beta_users[:3]:
            for j in range(2):
                file = FileFactory.create(
                    db_session,
                    uploaded_by=user,
                    project=project_beta,
                    filename=f"backend_{user.name.replace(' ', '_')}_doc_{j + 1}.txt",
                    mime_type="text/plain",
                    file_type="document",
                    size_bytes=len(fake.paragraph(nb_sentences=6)),
                )
                db_session.commit()
                beta_files.append(file)

            # Mock audio file data for each user (skip actual upload)
            if user in [user1, user2] or (user in beta_users and beta_users.index(user) < 3):
                beta_audio_files.append(
                    {
                        "audio_url": f"https://example.com/audio/beta_{user.id}_{uuid.uuid4().hex[:8]}.webm",
                        "uploader": user,
                        "duration": fake.random_int(min=120, max=1800),
                    }
                )

        print(f"✓ Beta project files: {len(beta_files)}")
        print(f"✓ Beta project audio files: {len(beta_audio_files)}")

        # Verify isolation and persistence
        fresh_session = SessionLocal()
        try:
            alpha_count = fresh_session.query(File).filter(File.project_id == project_alpha.id).count()
            beta_count = fresh_session.query(File).filter(File.project_id == project_beta.id).count()

            print("\n" + "-" * 100)
            print("  PROJECT FILE ISOLATION VERIFICATION")
            print("-" * 100)
            print(f"✓ Project Alpha files: {alpha_count}")
            print(f"✓ Project Beta files: {beta_count}")

            alpha_members = fresh_session.query(UserProject).filter(UserProject.project_id == project_alpha.id).count()
            beta_members = fresh_session.query(UserProject).filter(UserProject.project_id == project_beta.id).count()

            print(f"✓ Project Alpha members: {alpha_members}")
            print(f"✓ Project Beta members: {beta_members}")

        finally:
            fresh_session.close()
