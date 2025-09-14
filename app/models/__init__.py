# Import base first
from .base import BaseDatabaseModel
from .audit import AuditLog
from .file import File
from .integration import Integration
from .meeting import (
    AudioFile,
    Meeting,
    MeetingBot,
    MeetingBotLog,
    MeetingNote,
    MeetingStatus,
    ProjectMeeting,
    Transcript,
)
from .notification import Notification
from .project import Project, UserProject
from .search import SearchDocument
from .tag import MeetingTag, Tag
from .task import Task, TaskProject

# Import models in dependency order (from least dependent to most dependent)
from .user import User, UserDevice, UserIdentity

__all__ = [
    "BaseDatabaseModel",
    "User",
    "UserIdentity",
    "UserDevice",
    "Project",
    "UserProject",
    "Meeting",
    "MeetingStatus",
    "ProjectMeeting",
    "AudioFile",
    "Transcript",
    "MeetingNote",
    "MeetingBot",
    "MeetingBotLog",
    "File",
    "Tag",
    "MeetingTag",
    "Task",
    "TaskProject",
    "Notification",
    "AuditLog",
    "SearchDocument",
    "Integration",
]
