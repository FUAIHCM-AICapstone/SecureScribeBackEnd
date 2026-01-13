import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import AudioFile, Meeting, ProjectMeeting
from app.models.project import Project, UserProject


def crud_create_meeting(db: Session, **meeting_data) -> Meeting:
    meeting = Meeting(**meeting_data)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def crud_get_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[Meeting]:
    return (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.id == meeting_id, Meeting.is_deleted == False)
        .first()
    )


def crud_get_meetings(
    db: Session,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    is_personal: Optional[bool] = None,
    created_by: Optional[uuid.UUID] = None,
    start_time_gte: Optional[str] = None,
    start_time_lte: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    tag_ids: Optional[List[uuid.UUID]] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Meeting], int]:
    base_query = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.is_deleted == False)
    )

    personal_meetings = db.query(Meeting.id).filter(Meeting.is_personal == True, Meeting.created_by == user_id).subquery()
    accessible_projects = db.query(ProjectMeeting.meeting_id).join(UserProject, and_(UserProject.project_id == ProjectMeeting.project_id, UserProject.user_id == user_id)).subquery()

    query = base_query.filter(or_(Meeting.id.in_(personal_meetings), Meeting.id.in_(accessible_projects)))

    if title:
        query = query.filter(Meeting.title.ilike(f"%{title}%"))
    if description:
        query = query.filter(Meeting.description.ilike(f"%{description}%"))
    if status:
        query = query.filter(Meeting.status == status)
    if is_personal is not None:
        query = query.filter(Meeting.is_personal == is_personal)
    if created_by:
        query = query.filter(Meeting.created_by == created_by)
    if start_time_gte:
        query = query.filter(Meeting.start_time >= start_time_gte)
    if start_time_lte:
        query = query.filter(Meeting.start_time <= start_time_lte)

    if project_id:
        user_is_member = db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id == project_id).first() is not None
        if not user_is_member:
            return [], 0
        query = query.join(ProjectMeeting).filter(ProjectMeeting.project_id == project_id)

    if tag_ids:
        from app.models.meeting import MeetingTag

        query = query.join(MeetingTag).filter(MeetingTag.tag_id.in_(tag_ids))

    total = query.count()
    meetings = query.order_by(Meeting.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return meetings, total


def crud_update_meeting(db: Session, meeting_id: uuid.UUID, **updates) -> Optional[Meeting]:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        return None
    for key, value in updates.items():
        if hasattr(meeting, key):
            setattr(meeting, key, value)
    db.commit()
    db.refresh(meeting)
    return meeting


def crud_soft_delete_meeting(db: Session, meeting_id: uuid.UUID) -> bool:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        return False
    meeting.is_deleted = True
    db.commit()
    return True


def crud_link_meeting_to_project(db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    existing = db.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting_id, ProjectMeeting.project_id == project_id).first()
    if existing:
        return True
    project_meeting = ProjectMeeting(project_id=project_id, meeting_id=meeting_id)
    db.add(project_meeting)
    db.commit()
    return True


def crud_unlink_meeting_from_project(db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    project_meeting = db.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting_id, ProjectMeeting.project_id == project_id).first()
    if not project_meeting:
        return False
    db.delete(project_meeting)
    db.commit()
    return True


def crud_get_meeting_associated_files(db: Session, meeting_id: uuid.UUID):
    from app.models.file import File

    return db.query(File).filter(File.meeting_id == meeting_id).all()


def crud_get_next_audio_file_seq_order(db: Session, meeting_id: uuid.UUID) -> int:
    last = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id, AudioFile.is_deleted == False).order_by(AudioFile.seq_order.desc().nullslast(), AudioFile.created_at.desc()).first()
    if not last or last.seq_order is None:
        return 1
    return int(last.seq_order) + 1


def crud_create_audio_file(db: Session, meeting_id: uuid.UUID, uploaded_by: uuid.UUID, seq_order: int) -> AudioFile:
    audio = AudioFile(meeting_id=meeting_id, uploaded_by=uploaded_by, seq_order=seq_order)
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


def crud_update_audio_file_url(db: Session, audio_id: uuid.UUID, file_url: str) -> Optional[AudioFile]:
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        return None
    audio.file_url = file_url
    db.commit()
    db.refresh(audio)
    return audio


def crud_delete_audio_file(db: Session, audio_id: uuid.UUID) -> bool:
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        return False
    db.delete(audio)
    db.commit()
    return True


def crud_get_meeting_audio_files(db: Session, meeting_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[AudioFile], int]:
    q = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id, AudioFile.is_deleted == False)
    q = q.order_by(AudioFile.seq_order.asc().nullslast(), AudioFile.created_at.asc())
    total = q.count()
    rows = q.offset((page - 1) * limit).limit(limit).all()
    return rows, total


def crud_check_project_exists(db: Session, project_id: uuid.UUID) -> bool:
    return db.query(Project).filter(Project.id == project_id).first() is not None
