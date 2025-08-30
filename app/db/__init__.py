from sqlmodel import create_engine, Session
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine with SQLModel
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    echo=False,  # Disable SQL query logging
)

# Create SessionLocal class for SQLModel
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db():
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
def create_tables():
    """Create all database tables from SQLModel models"""
    # Import all models to register them with SQLModel
    from app.models import (
        User, UserIdentity, UserDevice,
        Project, UserProject,
        Meeting, ProjectMeeting, AudioFile, Transcript, MeetingNote, MeetingBot, MeetingBotLog,
        File,
        Tag, MeetingTag,
        Task, TaskProject,
        Notification,
        AuditLog,
        SearchDocument,
        Integration,
    )

    # Create tables using SQLModel metadata
    from app.models.base import metadata
    metadata.create_all(bind=engine)


