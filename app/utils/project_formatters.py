from app.models.project import Project, UserProject
from app.schemas.project import ProjectResponse, ProjectWithMembers, UserProjectResponse


def format_project_response(project: Project) -> ProjectResponse:
    member_count = len(project.users) if hasattr(project, "users") else None
    return ProjectResponse(id=project.id, name=project.name, description=project.description, is_archived=project.is_archived, created_by=project.created_by, created_at=project.created_at, updated_at=project.updated_at, member_count=member_count)


def format_project_with_members_response(project: Project) -> ProjectWithMembers:
    base_response = format_project_response(project)
    members = []
    if hasattr(project, "users"):
        for user_project in project.users:
            members.append(UserProjectResponse(user_id=user_project.user_id, project_id=user_project.project_id, role=user_project.role, joined_at=user_project.joined_at, user={"id": user_project.user.id, "email": user_project.user.email, "name": user_project.user.name, "avatar_url": user_project.user.avatar_url, "position": user_project.user.position} if user_project.user else None))
    return ProjectWithMembers(**base_response.model_dump(), members=members)


def format_user_project_response(user_project: UserProject) -> UserProjectResponse:
    return UserProjectResponse(user_id=user_project.user_id, project_id=user_project.project_id, role=user_project.role, joined_at=user_project.joined_at, user={"id": user_project.user.id, "email": user_project.user.email, "name": user_project.user.name, "avatar_url": user_project.user.avatar_url, "position": user_project.user.position} if user_project.user else None)
