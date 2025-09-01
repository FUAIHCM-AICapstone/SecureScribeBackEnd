from sqlalchemy import MetaData

# global metadata
metadata = MetaData()


# Database compatibility helpers
def get_uuid_column():
    """Get UUID column type compatible with current database"""
    try:
        from sqlalchemy.dialects.postgresql import UUID

        return UUID(as_uuid=True)
    except ImportError:
        from sqlalchemy import String

        return String


def get_json_column():
    """Get JSON column type compatible with current database"""
    try:
        from sqlalchemy.dialects.postgresql import JSON

        return JSON
    except ImportError:
        from sqlalchemy import JSON as SQLiteJSON

        return SQLiteJSON
