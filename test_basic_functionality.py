#!/usr/bin/env python3
"""
Basic functionality test script that doesn't use pytest or full app initialization
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test that basic modules can be imported"""
    try:
        from app.models.tag import Tag
        from app.models.user import User
        from app.schemas.tag import TagCreate, TagUpdate
        from app.services.user import create_user
        print("Basic imports successful")
        return True
    except Exception as e:
        print(f"Basic imports failed: {e}")
        return False


def test_model_creation():
    """Test creating model instances"""
    try:
        import uuid
        from app.models.tag import Tag

        tag_id = uuid.uuid4()
        user_id = uuid.uuid4()

        tag = Tag(
            id=tag_id,
            name="test_tag",
            scope="global",
            created_by=user_id,
            is_deleted=False
        )

        assert tag.id == tag_id
        assert tag.name == "test_tag"
        assert tag.scope == "global"
        assert tag.created_by == user_id
        assert tag.is_deleted is False

        print("Model creation successful")
        return True
    except Exception as e:
        print(f"Model creation failed: {e}")
        return False


def test_schema_creation():
    """Test creating schema instances"""
    try:
        from app.schemas.tag import TagCreate, TagUpdate

        tag_create = TagCreate(name="schema_test", scope="global")
        assert tag_create.name == "schema_test"
        assert tag_create.scope == "global"

        tag_update = TagUpdate(name="updated_name")
        assert tag_update.name == "updated_name"
        assert tag_update.scope is None

        print("Schema creation successful")
        return True
    except Exception as e:
        print(f"Schema creation failed: {e}")
        return False


def test_database_connection():
    """Test basic database connection"""
    try:
        from app.db import SessionLocal, create_tables

        # Create tables
        create_tables()

        # Test connection
        db = SessionLocal()
        db.close()

        print("Database connection successful")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def main():
    """Run all basic tests"""
    print("Running basic functionality tests...")

    tests = [
        test_basic_imports,
        test_model_creation,
        test_schema_creation,
        test_database_connection,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("All basic functionality tests passed!")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
