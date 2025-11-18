# SecureScribe Backend - AI Coding Agent Instructions

## Architecture Overview

SecureScribe is a FastAPI-based meeting management and transcription platform with microservices architecture:

- **API Layer**: `app/api/endpoints/` - REST endpoints with FastAPI routers
- **Service Layer**: `app/services/` - Business logic, called directly from endpoints
- **Data Layer**: `app/models/` - SQLModel entities with PostgreSQL
- **Schema Layer**: `app/schemas/` - Pydantic request/response validation
- **Infrastructure**: Docker Compose with PostgreSQL, Redis, MinIO, Qdrant, Celery

## Critical Patterns & Conventions

### Service Layer Architecture
```python
# endpoints/project.py - Direct service calls, no business logic
@router.post("/projects", response_model=ProjectApiResponse)
def create_project_endpoint(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_project(db, project, current_user.id)

# services/project.py - All business logic here
def create_project(db: Session, project_data: ProjectCreate, created_by: uuid.UUID):
    project = Project(**project_data.dict(), created_by=created_by)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

### Database Patterns
- **UUID Primary Keys**: All entities use `uuid.UUID` with `default_factory=uuid.uuid4`
- **Audit Fields**: `created_at` (required), `updated_at` (optional) on all models
- **Relationships**: Use SQLModel `Relationship` with `back_populates`
- **Foreign Keys**: Explicit foreign key definitions with `sa_column=Column(UUID(as_uuid=True), foreign_key="table.id")`

### API Response Format
```python
# Always wrap responses in ApiResponse
from app.schemas.common import ApiResponse

@router.get("/projects/{project_id}")
def get_project(project_id: uuid.UUID) -> ApiResponse[ProjectResponse]:
    project = get_project_service(project_id)
    return ApiResponse(data=project)
```

### Authentication & Authorization
- JWT tokens via `get_current_user` dependency
- User context from `app.utils.auth.get_current_user`
- Project membership checks via `is_user_in_project()` service calls

## Developer Workflows

### Local Development
```bash
# Start full stack
docker-compose up api db redis minio qdrant

# API only with external services
docker-compose up api

# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8081
```

### Testing
```bash
# Docker testing (uses production DB - backup first!)
./run-tests.sh docker

# Local testing
./run-tests.sh local

# Direct pytest
pytest tests/ -v --tb=short
```

### Code Quality
- **Linting**: `ruff` configured in `pyproject.toml` (line-length=9999, minimal rules)
- **Imports**: Single-line imports, no aliases, only essential imports
- **Style**: Minimal coding style - single-line functions, no docstrings, compact code

## Integration Points

### External Services
- **Firebase**: Push notifications via `firebase-admin`
- **Google Calendar**: OAuth integration via `google-api-python-client`
- **Transcription**: External API at `https://s2t.wc504.io.vn/api/v1`
- **File Storage**: MinIO with public/private buckets
- **Vector Search**: Qdrant for document embeddings
- **Background Jobs**: Celery with Redis broker

### Configuration
- **Settings**: `app.core.config.Settings` with Pydantic settings
- **Environment**: Docker environment variables override defaults
- **Secrets**: Firebase keys, Google OAuth credentials in `/app/config/`

## Key Files & Examples

### Model Definition (`app/models/project.py`)
```python
class Project(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(UUID(as_uuid=True), primary_key=True))
    name: str = Field(sa_column=Column(String, nullable=False))
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    users: list["UserProject"] = Relationship(back_populates="project")
```

### Service Pattern (`app/services/project.py`)
```python
def create_project(db: Session, project_data: ProjectCreate, created_by: uuid.UUID) -> Project:
    project = Project(**project_data.dict(), created_by=created_by)
    db.add(project)
    db.commit()
    db.refresh(project)
    add_user_to_project(db, project.id, created_by, "owner")
    return project
```

### Endpoint Pattern (`app/api/endpoints/project.py`)
```python
@router.post("/projects", response_model=ProjectApiResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ApiResponse[ProjectResponse]:
    project = create_project_service(db, project, current_user.id)
    return ApiResponse(data=format_project_response(project))
```

## Common Patterns

### Database Queries
- Use `joinedload()` for relationships when needed
- Filter by project membership: `is_user_in_project(db, project_id, user_id)`
- Bulk operations via service functions

### Error Handling
- HTTPException for API errors
- Let exceptions bubble up from services to endpoints
- Custom exceptions defined in services

### File Operations
- MinIO client via `app.utils.minio`
- Public URLs for permanent links
- File metadata stored in `files` table

### Real-time Features
- WebSocket manager in `app.services.websocket_manager`
- Redis pub/sub for real-time updates
- Connection limits and cleanup intervals configured

## Testing Patterns

### Test Structure
- `tests/conftest.py` - Shared fixtures (db session, test user)
- Service layer tests in `tests/api/services/`
- API endpoint tests in `tests/api/`
- Production database testing (backup required!)

### Test Data
```python
@pytest.fixture
def test_user(db: Session):
    user = create_user(db, UserCreate(email="test@example.com", name="Test"))
    return user
```

## Deployment & Docker

### Production Stack
- API service with uvicorn
- Celery worker for background tasks
- PostgreSQL, Redis, MinIO, Qdrant
- Health checks and restart policies

### Environment Variables
- `ENV=production` for production config
- Database connection via `POSTGRES_*` vars
- External service URLs and credentials

## Security Considerations

- JWT authentication on all endpoints
- CORS configured for cross-origin requests
- File upload validation (size, type, extensions)
- User authorization checks in services
- Audit logging for sensitive operations