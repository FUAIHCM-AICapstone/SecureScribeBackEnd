# SecureScribe Database Context

## Overview

SecureScribe is a meeting management and transcription platform built with FastAPI, SQLModel, and PostgreSQL. This document provides comprehensive context about the database schema and relationships for AI coding agents.

## Database Schema

### Core Tables

#### 1. Users (`users`)

**Primary entity for user management**

- `id`: UUID (Primary Key)
- `email`: String (Unique, Required)
- `name`: String (Optional)
- `avatar_url`: String (Optional)
- `bio`: Text (Optional)
- `position`: String (Optional)
- `password_hash`: String (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Relationships:**

- One-to-Many: User → UserIdentity, UserDevice, Project (created), Meeting (created), File (uploaded/owned), Tag (created), Task (created/assignee), Notification, AuditLog, MeetingNote (editor), MeetingBot (created)

#### 2. User Identities (`user_identities`)

**OAuth provider identities**

- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key → users)
- `provider`: String (Required)
- `provider_user_id`: String (Required)
- `provider_email`: String (Optional)
- `provider_profile`: JSON (Optional)
- `tenant_id`: String (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Constraints:** Unique(provider, provider_user_id)

#### 3. User Devices (`user_devices`)

**Push notification device management**

- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key → users)
- `device_name`: String (Optional)
- `device_type`: String (Optional)
- `fcm_token`: Text (Required)
- `last_active_at`: Timestamp (Optional)
- `is_active`: Boolean (Default: true)
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### 4. Projects (`projects`)

**Project management**

- `id`: UUID (Primary Key)
- `name`: String (Required)
- `description`: Text (Optional)
- `is_archived`: Boolean (Default: false)
- `created_by`: UUID (Foreign Key → users)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Relationships:**

- Many-to-Many: Project ↔ User (via users_projects)
- Many-to-Many: Project ↔ Meeting (via projects_meetings)
- One-to-Many: Project → File, Task (via tasks_projects), Integration

#### 5. Meetings (`meetings`)

**Meeting records**

- `id`: UUID (Primary Key)
- `title`: String (Optional)
- `description`: Text (Optional)
- `url`: String (Optional)
- `start_time`: Timestamp (Optional)
- `created_by`: UUID (Foreign Key → users)
- `is_personal`: Boolean (Default: false)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Relationships:**

- Many-to-Many: Meeting ↔ Project (via projects_meetings)
- Many-to-Many: Meeting ↔ Tag (via meeting_tags)
- One-to-Many: Meeting → AudioFile, Task, File
- One-to-One: Meeting → Transcript, MeetingNote, MeetingBot

### File and Media Management

#### 6. Files (`files`)

**General file storage**

- `id`: UUID (Primary Key)
- `filename`: String (Optional)
- `mime_type`: String (Optional)
- `size_bytes`: BigInteger (Optional)
- `storage_url`: String (Optional)
- `file_type`: String (Optional)
- `project_id`: UUID (Foreign Key → projects, Optional)
- `meeting_id`: UUID (Foreign Key → meetings, Optional)
- `uploaded_by`: UUID (Foreign Key → users, Optional)
- `extracted_text`: Text (Optional)
- `qdrant_vector_id`: String (Optional)
- `created_at`: Timestamp

#### 7. Audio Files (`audio_files`)

**Meeting audio file management**

- `id`: UUID (Primary Key)
- `meeting_id`: UUID (Foreign Key → meetings)
- `uploaded_by`: UUID (Foreign Key → users)
- `file_url`: String (Optional)
- `seq_order`: Integer (Optional)
- `duration_seconds`: Integer (Optional)
- `is_concatenated`: Boolean (Default: false)
- `created_at`: Timestamp

### Transcription and Notes

#### 8. Transcripts (`transcripts`)

**Meeting transcription storage**

- `id`: UUID (Primary Key)
- `meeting_id`: UUID (Foreign Key → meetings, Unique)
- `content`: Text (Optional)
- `audio_concat_file_id`: UUID (Foreign Key → audio_files, Optional)
- `extracted_text_for_search`: Text (Optional)
- `qdrant_vector_id`: String (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### 9. Meeting Notes (`meeting_notes`)

**Meeting notes and summaries**

- `id`: UUID (Primary Key)
- `meeting_id`: UUID (Foreign Key → meetings, Unique)
- `content`: Text (Optional)
- `last_editor_id`: UUID (Foreign Key → users, Optional)
- `last_edited_at`: Timestamp (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

### Task Management

#### 10. Tasks (`tasks`)

**Task tracking and assignment**

- `id`: UUID (Primary Key)
- `title`: String (Required)
- `description`: Text (Optional)
- `creator_id`: UUID (Foreign Key → users)
- `assignee_id`: UUID (Foreign Key → users, Optional)
- `status`: String (Default: 'todo')
- `meeting_id`: UUID (Foreign Key → meetings, Optional)
- `due_date`: Timestamp (Optional)
- `reminder_at`: Timestamp (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Relationships:**

- Many-to-Many: Task ↔ Project (via tasks_projects)

### Tagging System

#### 11. Tags (`tags`)

**Flexible tagging system**

- `id`: UUID (Primary Key)
- `name`: String (Required)
- `created_by`: UUID (Foreign Key → users)
- `scope`: String (Default: 'global')
- `created_at`: Timestamp

**Relationships:**

- Many-to-Many: Tag ↔ Meeting (via meeting_tags)

### Automation and Integration

#### 12. Meeting Bots (`meeting_bots`)

**Automated meeting management**

- `id`: UUID (Primary Key)
- `meeting_id`: UUID (Foreign Key → meetings)
- `scheduled_start_time`: Timestamp (Optional)
- `actual_start_time`: Timestamp (Optional)
- `actual_end_time`: Timestamp (Optional)
- `status`: String (Default: 'pending')
- `meeting_url`: String (Optional)
- `retry_count`: Integer (Default: 0)
- `last_error`: Text (Optional)
- `created_by`: UUID (Foreign Key → users)
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### 13. Meeting Bot Logs (`meeting_bot_logs`)

**Bot activity logging**

- `id`: UUID (Primary Key)
- `meeting_bot_id`: UUID (Foreign Key → meeting_bots)
- `action`: String (Optional)
- `message`: Text (Optional)
- `created_at`: Timestamp

#### 14. Integrations (`integrations`)

**Third-party service integrations**

- `id`: UUID (Primary Key)
- `project_id`: UUID (Foreign Key → projects)
- `type`: String (Optional)
- `credentials_meta`: JSON (Optional)
- `created_at`: Timestamp

### System and Audit

#### 15. Notifications (`notifications`)

**User notification system**

- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key → users)
- `type`: String (Optional)
- `payload`: JSON (Optional)
- `is_read`: Boolean (Default: false)
- `channel`: String (Optional)
- `created_at`: Timestamp

#### 16. Audit Logs (`audit_logs`)

**System audit trail**

- `id`: UUID (Primary Key)
- `actor_user_id`: UUID (Foreign Key → users)
- `action`: String (Optional)
- `target_type`: String (Optional)
- `target_id`: String (Optional)
- `metadata`: JSON (Optional)
- `created_at`: Timestamp

#### 17. Search Documents (`search_documents`)

**Search indexing for vector search**

- `id`: UUID (Primary Key)
- `owner_type`: String (Optional)
- `owner_id`: UUID (Optional)
- `content_text`: Text (Optional)
- `qdrant_vector_id`: String (Optional)
- `indexed_at`: Timestamp (Optional)

### Junction Tables

#### 18. Users Projects (`users_projects`)

**Many-to-many: Users ↔ Projects**

- `user_id`: UUID (Primary Key, Foreign Key → users)
- `project_id`: UUID (Primary Key, Foreign Key → projects)
- `role`: String (Default: 'member')
- `joined_at`: Timestamp

#### 19. Projects Meetings (`projects_meetings`)

**Many-to-many: Projects ↔ Meetings**

- `project_id`: UUID (Primary Key, Foreign Key → projects)
- `meeting_id`: UUID (Primary Key, Foreign Key → meetings)

#### 20. Meeting Tags (`meeting_tags`)

**Many-to-many: Meetings ↔ Tags**

- `meeting_id`: UUID (Primary Key, Foreign Key → meetings)
- `tag_id`: UUID (Primary Key, Foreign Key → tags)

#### 21. Tasks Projects (`tasks_projects`)

**Many-to-many: Tasks ↔ Projects**

- `task_id`: UUID (Primary Key, Foreign Key → tasks)
- `project_id`: UUID (Primary Key, Foreign Key → projects)

## Key Relationships Overview

### User-Centric Relationships

```
User
├── identities (1:N)
├── devices (1:N)
├── projects_created (1:N)
├── meetings_created (1:N)
├── files_uploaded (1:N)
├── files_owned (1:N)
├── tags_created (1:N)
├── tasks_created (1:N)
├── tasks_assigned (1:N)
├── notifications (1:N)
├── audit_logs (1:N)
├── notes_edited (1:N)
└── bots_created (1:N)
```

### Meeting-Centric Relationships

```
Meeting
├── projects (N:M via projects_meetings)
├── audio_files (1:N)
├── transcript (1:1)
├── notes (1:1)
├── files (1:N)
├── tags (N:M via meeting_tags)
├── tasks (1:N)
└── bot (1:1)
```

### Project-Centric Relationships

```
Project
├── creator (N:1)
├── users (N:M via users_projects)
├── meetings (N:M via projects_meetings)
├── files (1:N)
├── tasks (N:M via tasks_projects)
└── integrations (1:N)
```

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Authentication**: JWT + OAuth providers
- **File Storage**: External storage (URLs)
- **Search**: Qdrant vector database
- **Notifications**: FCM (Firebase Cloud Messaging)

## Common Patterns

1. **UUID Primary Keys**: All entities use UUID for primary keys
2. **Timestamps**: `created_at` and `updated_at` on most tables
3. **Soft Deletes**: Some tables may use `is_archived` or similar flags
4. **JSON Fields**: Used for flexible metadata storage
5. **Vector Search**: Integration with Qdrant for semantic search
6. **Audit Trail**: Comprehensive audit logging
7. **Role-Based Access**: User roles in project contexts

## Development Notes

- Use `app/db/__init__.py` for database connections
- Use `app/models/__init__.py` to import all models
- Use `BaseDatabaseModel` for common fields and methods
- Use `get_db()` dependency in FastAPI routes
- Run `create_tables()` to initialize database schema

This context provides the foundation for understanding and working with the SecureScribe database schema.
