import uuid
from typing import List, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project


def crud_search_dynamic(
    db: Session,
    search_term: str,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    project_id: uuid.UUID = None,
    meeting_id: uuid.UUID = None,
) -> Tuple[List[dict], int]:
    user_projects_query = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id))
    user_project_ids = [p.id for p in user_projects_query.all()]

    if project_id:
        user_project_ids = [project_id] if project_id in user_project_ids else []

    project_meetings_query = db.query(Meeting.id).join(ProjectMeeting, Meeting.id == ProjectMeeting.meeting_id).filter(ProjectMeeting.project_id.in_(user_project_ids))
    personal_meetings_query = db.query(Meeting.id).filter(and_(Meeting.is_personal == True, Meeting.created_by == user_id))
    user_meetings_query = project_meetings_query.union(personal_meetings_query)
    user_meeting_ids = [m.id for m in user_meetings_query.all()]

    if meeting_id:
        user_meeting_ids = [meeting_id] if meeting_id in user_meeting_ids else []

    meetings = db.query(Meeting.id, Meeting.title, Meeting.created_at).filter(Meeting.title.ilike(f"%{search_term}%"), Meeting.is_deleted == False).filter(Meeting.id.in_(user_meeting_ids)).all()

    projects = db.query(Project.id, Project.name, Project.created_at).filter(Project.name.ilike(f"%{search_term}%"), Project.is_archived == False).filter(Project.id.in_(user_project_ids)).all()

    files = (
        db.query(File.id, File.filename, File.created_at)
        .filter(File.filename.ilike(f"%{search_term}%"))
        .filter(
            or_(
                File.uploaded_by == user_id,
                File.project_id.in_(user_project_ids),
                File.meeting_id.in_(user_meeting_ids),
            )
        )
        .all()
    )

    results = []
    for m in meetings:
        results.append(
            {
                "id": str(m.id),
                "name": m.title,
                "created_at": m.created_at,
                "type": "meeting",
            }
        )
    for p in projects:
        results.append(
            {
                "id": str(p.id),
                "name": p.name,
                "created_at": p.created_at,
                "type": "project",
            }
        )
    for f in files:
        results.append(
            {
                "id": str(f.id),
                "name": f.filename,
                "created_at": f.created_at,
                "type": "file",
            }
        )

    def get_relevance(item):
        name = item["name"]
        if name == search_term:
            return 3
        elif search_term.lower() in name.lower():
            return 2
        else:
            return 1

    results.sort(key=lambda x: (-get_relevance(x), x["created_at"].timestamp() if x["created_at"] else 0))

    for result in results:
        result["created_at"] = result["created_at"].isoformat() if result["created_at"] else None

    start = (page - 1) * limit
    end = start + limit
    paginated_results = results[start:end]
    total = len(results)

    return paginated_results, total
