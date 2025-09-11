from typing import Generator

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from app.core.config import settings

# Create SQLAlchemy engine with SQLModel
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    echo=False,  # Disable SQL query logging
)

# Create SessionLocal class for SQLModel
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=Session
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Use this in FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to create all tables
def create_tables() -> None:
    """Create all database tables from SQLModel models"""
    # Import all models to register them with SQLModel
    from app.models import (
        AudioFile,
        AuditLog,  # noqa: F401
        File,  # noqa: F401
        Integration,  # noqa: F401
        Meeting,
        MeetingBot,
        MeetingBotLog,  # noqa: F401
        MeetingNote,
        MeetingTag,  # noqa: F401
        Notification,  # noqa: F401
        Project,
        ProjectMeeting,
        Tag,
        Task,
        TaskProject,  # noqa: F401
        Transcript,
        User,
        UserDevice,  # noqa: F401
        UserIdentity,
        UserProject,  # noqa: F401
    )

    # Create tables using SQLModel metadata
    from app.models.base import metadata

    metadata.create_all(bind=engine)
