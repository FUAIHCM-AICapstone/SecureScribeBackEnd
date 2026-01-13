# Minimal Coding Style Rules

## Project Context

**SecureScribe Backend** - FastAPI-based meeting management and transcription platform

- **Tech Stack**: FastAPI, SQLModel, PostgreSQL, Pydantic
- **Architecture**: Service layer pattern with clean separation
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Features**: User management, OAuth, meetings, transcription, file management, notifications

## Project Structure

```
SecureScribeBackEnd/
├── app/                          # Main application
│   ├── api/                      # API layer
│   │   ├── endpoints/           # Route handlers
│   │   └── dependencies/        # Dependency injection
│   ├── core/                    # Core configuration
│   ├── crud/                    # Database operations layer
│   ├── models/                  # SQLModel database models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic layer
│   └── utils/                   # Utility functions
├── tests/                       # Test files
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
└── Dockerfile                  # Container configuration
```

## Core Principles

- Write minimal, concise code with zero overhead
- No docstrings or comments - code should be self-explanatory
- No trailing logic or unnecessary operations
- Single responsibility per line, no compound statements
- Eliminate redundant code and duplicate logic
- Use shortest possible syntax and naming
- Remove all non-essential elements and abstractions

## Function Rules

- One line functions when possible: `def get_user(id): return db.query(User).filter(User.id==id).first()`
- No intermediate variables: Direct returns without assignments
- Chain operations in single expressions: `users.filter(active=True).order_by(created_at.desc())`
- Use lambda for simple operations: `map(lambda x: x.name, users)`
- No function if logic can be inline: Use ternary or direct expressions
- **kwargs for flexible parameters**: `def get_users(**filters): return query.filter_by(**filters)`

## Class Rules

- Minimal field definitions: Only essential attributes
- No unnecessary methods: Remove getters/setters unless required
- Use dataclasses when possible: `@dataclass class User: id: int; name: str`
- Remove all optional fields: Use required fields only
- No inheritance unless required: Prefer composition
- Inline property definitions: No separate property methods

## Schema Rules

- Minimal field sets: Only include required fields
- No optional fields unless critical: Use required types
- Remove all validation constraints: No min_length, max_length
- Use basic types only: str, int, bool instead of EmailStr, constr
- No nested schemas: Flatten all relationships
- Direct field definitions: No computed properties

## Endpoint Rules

- Single line route handlers: `@app.get("/users") def get_users(): return get_users_service()`
- No intermediate processing: Direct service calls
- Direct service calls: No wrapper functions
- Minimal parameter validation: Basic type hints only
- No response formatting: Return raw data
- Inline error handling: Let exceptions bubble up

## Database Rules

- All database operations must be in crud folder
- Minimal query operations: Single table queries when possible
- No eager loading unless required: Use lazy loading
- Direct SQL when ORM is verbose: `db.query(text("SELECT * FROM users"))`
- No transaction management: Let framework handle transactions
- Inline database calls: No repository pattern
- Remove all relationship loading: Query only needed data

## Import Rules

- Only essential imports: Import only what's used
- No unused imports: Remove all unused modules
- Single line import statements: `from fastapi import FastAPI, APIRouter`
- No import aliases: Use full module names
- Direct module imports: `import sqlalchemy.orm`
- Remove all utility imports: No helper libraries

## Logging Rules

- Use logger from app.utils.logging instead of print statements
- Import logger: `from app.utils.logging import logger`
- Use appropriate log levels: logger.info(), logger.warning(), logger.error(), logger.debug()
- No print statements: Replace all print() with logger calls
- Structured logging: Include relevant context in log messages

## Development Workflow

- Code only: When requested for code, provide code only
- No commands: Do not run any terminal commands, tests, or compilation
- No validation: Skip all testing, linting, and validation steps
- Direct delivery: Deliver code changes immediately without verification
- Pure code: Focus solely on code implementation without execution

## Code Structure

- No empty lines between statements: Compact all code
- No line breaks in expressions: Single line expressions
- Single statement per line: No compound statements
- No indentation beyond required: Minimal nesting
- Remove all whitespace: No extra spaces or tabs
- Compact all code blocks: No unnecessary blocks

## Error Handling

- No try-except blocks: Let exceptions propagate
- Let exceptions bubble up: No error catching
- No custom error classes: Use built-in exceptions
- Remove all error handling: No error management
- Direct exception propagation: No error wrapping
- No error logging: No logging statements

## Performance Rules

- No caching layers: Direct database calls
- No optimization code: No performance tuning
- Direct database calls: No caching abstractions
- No connection pooling: Use default connections
- Remove all performance code: No optimization logic
- Inline all operations: No performance wrappers

## Testing Rules

- No test files: Pure production code only
- No test functions: No unit or integration tests
- Remove all test code: No test utilities
- No test fixtures: No test data setup
- No test utilities: No testing frameworks
- Pure production code only: No test-related code

## Configuration

- No configuration files: Hardcode all values
- Hardcode all values: No external configuration
- No environment variables: Direct value assignments
- Direct value assignments: `DB_URL = "postgresql://..."`
- Remove all config code: No configuration management
- Inline all settings: No settings modules

## Database Schema Context

**Core Entities:**

- Users: Authentication, profiles, OAuth identities, devices
- Projects: Team collaboration spaces with member roles
- Meetings: Online meetings with transcripts and notes
- Files: Document and audio file management
- Tasks: Project and meeting task tracking
- Notifications: In-app, email, and push notifications

**Key Relationships:**

- User → Projects (many-to-many via users_projects)
- Project → Meetings (many-to-many via projects_meetings)
- Meeting → AudioFiles, Transcripts, Notes (one-to-many)
- User → Files, Tasks, Notifications (one-to-many)

**Business Rules:**

- Users can join multiple projects with different roles
- Meetings can belong to multiple projects
- Files inherit permissions from parent project/meeting
- Tasks can be assigned to users within project context
- Notifications support multiple channels (in-app, email, push)

## Codebase Patterns

**Service Layer Pattern:**

- Business logic in dedicated service modules
- Database operations abstracted from endpoints
- Clean separation between routes and logic
- Dependency injection for database sessions

**Schema Patterns:**

- Separate request/response schemas
- Relationship serialization with from_attributes
- Pagination metadata in responses
- Generic response wrappers for consistency

**Database Patterns:**

- SQLModel for type-safe database models
- Relationship definitions with proper foreign keys
- Composite primary keys for junction tables
- Timestamp fields for audit trails
