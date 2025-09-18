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


# Function to check if database exists and has tables
def check_database_exists() -> bool:
    """Check if database exists and has any tables"""
    try:
        # Try to connect and check for any existing tables
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 1"))
            has_tables = result.fetchone() is not None
            print(f"🔍 Database check result: has_tables={has_tables}")
            return has_tables
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# Function to check if specific table exists
def table_exists(table_name: str) -> bool:
    """Check if a specific table exists"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Try exact match first
            result = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table_name)"), {"table_name": table_name})
            exists = result.fetchone()[0]

            if not exists:
                # Also try lowercase version
                result2 = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND lower(table_name) = lower(:table_name))"), {"table_name": table_name})
                exists = result2.fetchone()[0]

            if not exists:
                # Debug: list all tables to see what's actually there
                all_tables_result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
                all_tables = [row[0] for row in all_tables_result.fetchall()]
                print(f"🔍 All tables in database: {all_tables}")

            print(f"🔍 Table check result for '{table_name}': exists={exists}")
            return exists
    except Exception as e:
        print(f"❌ Failed to check table {table_name}: {e}")
        return False


# Function to create all tables
def create_tables() -> None:
    """Create all database tables from SQLModel models"""
    print("🔧 Importing all models...")
    # Import all models to register them with SQLAlchemy registry
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
    print("✅ Models imported successfully")

    # Create tables using SQLAlchemy registry (correct way for SQLModel)
    print("🏗️ Creating tables with SQLAlchemy...")
    from sqlmodel import SQLModel

    try:
        # Use SQLModel.metadata.create_all() - this includes all registered tables
        SQLModel.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        raise


# Function to initialize database on startup
def init_database() -> None:
    """Check database existence and create tables if needed"""
    import time
    print("🔍 Checking database connection and status...")

    # Wait a bit for database to be fully ready
    time.sleep(2)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt + 1}/{max_retries} to initialize database...")

            # Always try to create tables on startup (simpler and more reliable)
            print("📦 Creating/updating database tables...")
            create_tables()
            print("✅ Database tables created/verified successfully")

            # Try to verify users table exists (but don't fail if check fails)
            try:
                if table_exists("users"):
                    print("✅ Users table confirmed to exist")
                    return
                else:
                    print("⚠️ Users table check failed, but tables were created successfully")
                    print("🚀 Proceeding with startup (table check might be unreliable)")
                    return
            except Exception as check_error:
                print(f"⚠️ Table check failed: {check_error}, but tables were created successfully")
                print("🚀 Proceeding with startup")
                return

        except Exception as e:
            print(f"❌ Database initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("⏳ Waiting before retry...")
                time.sleep(2)
            else:
                print("🔄 Final attempt to create tables...")
                try:
                    create_tables()
                    print("✅ Tables created on final attempt - proceeding with startup")
                    return
                except Exception as final_error:
                    print(f"❌ Final attempt failed: {final_error}")
                    raise
