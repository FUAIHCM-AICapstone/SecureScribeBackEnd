# """
# Simple tag tests that don't require full application initialization
# These tests use direct database access and service calls
# """

# import uuid

# import pytest
# from faker import Faker
# from sqlalchemy.orm import Session

# from app.db import SessionLocal, create_tables
# from app.models.tag import Tag
# from app.models.user import User
# from app.schemas.tag import TagCreate, TagUpdate
# from app.services.tag import create_tag, delete_tag, get_tag, get_tags, update_tag
# from app.services.user import create_user

# faker = Faker()


# @pytest.fixture(scope="function")
# def db():
#     """Create test database session"""
#     create_tables()
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @pytest.fixture(scope="function")
# def test_user(db: Session):
#     """Create a test user"""
#     user_data = {
#         "email": "test@example.com",
#         "name": "Test User",
#         "avatar_url": "https://example.com/avatar.jpg",
#         "bio": "Test user for automated testing",
#         "position": "Software Engineer",
#     }
#     return create_user(db, **user_data)


# def test_create_tag_direct(db: Session, test_user: User):
#     """Test creating a tag directly using service"""
#     tag_data = TagCreate(name="test_tag", scope="global")
#     tag = create_tag(db, tag_data, test_user.id)

#     assert tag.id is not None
#     assert tag.name == "test_tag"
#     assert tag.scope == "global"
#     assert tag.created_by == test_user.id
#     assert tag.is_deleted is False


# def test_get_tags_direct(db: Session, test_user: User):
#     """Test getting tags directly using service"""
#     # Create some tags
#     tag1 = create_tag(db, TagCreate(name="tag1", scope="global"), test_user.id)
#     tag2 = create_tag(db, TagCreate(name="tag2", scope="project"), test_user.id)

#     # Get all tags
#     tags, total = get_tags(db, None, test_user.id, 1, 10)

#     assert total >= 2
#     assert len(tags) >= 2

#     # Check that our tags are in the results
#     tag_names = [tag.name for tag in tags]
#     assert "tag1" in tag_names
#     assert "tag2" in tag_names


# def test_get_tag_by_id_direct(db: Session, test_user: User):
#     """Test getting a specific tag by ID"""
#     # Create a tag
#     tag = create_tag(db, TagCreate(name="specific_tag", scope="global"), test_user.id)

#     # Get the tag by ID
#     retrieved_tag = get_tag(db, tag.id, test_user.id)

#     assert retrieved_tag is not None
#     assert retrieved_tag.id == tag.id
#     assert retrieved_tag.name == "specific_tag"


# def test_update_tag_direct(db: Session, test_user: User):
#     """Test updating a tag directly"""
#     # Create a tag
#     tag = create_tag(db, TagCreate(name="update_test", scope="global"), test_user.id)

#     # Update the tag
#     update_data = TagUpdate(name="updated_tag", scope="project")
#     updated_tag = update_tag(db, tag.id, update_data, test_user.id)

#     assert updated_tag.name == "updated_tag"
#     assert updated_tag.scope == "project"
#     assert updated_tag.id == tag.id


# def test_delete_tag_direct(db: Session, test_user: User):
#     """Test soft deleting a tag directly"""
#     # Create a tag
#     tag = create_tag(db, TagCreate(name="delete_test", scope="global"), test_user.id)

#     # Delete the tag
#     result = delete_tag(db, tag.id, test_user.id)
#     assert result is True

#     # Verify tag is soft deleted (should not be found in normal queries)
#     retrieved_tag = get_tag(db, tag.id, test_user.id)
#     assert retrieved_tag is None


# def test_tag_model_creation():
#     """Test creating a Tag model instance directly"""
#     tag_id = uuid.uuid4()
#     user_id = uuid.uuid4()

#     tag = Tag(id=tag_id, name="model_test", scope="global", created_by=user_id, is_deleted=False)

#     assert tag.id == tag_id
#     assert tag.name == "model_test"
#     assert tag.scope == "global"
#     assert tag.created_by == user_id
#     assert tag.is_deleted is False


# def test_tag_filter_functionality(db: Session, test_user: User):
#     """Test tag filtering functionality"""
#     # Create tags with different properties
#     create_tag(db, TagCreate(name="urgent", scope="global"), test_user.id)
#     create_tag(db, TagCreate(name="meeting", scope="project"), test_user.id)
#     create_tag(db, TagCreate(name="weekly", scope="global"), test_user.id)

#     from app.schemas.tag import TagFilter

#     # Test filtering by scope
#     filters = TagFilter(scope="global")
#     tags, total = get_tags(db, filters, test_user.id, 1, 10)

#     assert total >= 2  # Should find at least urgent and weekly
#     for tag in tags:
#         assert tag.scope == "global"

#     # Test filtering by name
#     filters = TagFilter(name="meeting")
#     tags, total = get_tags(db, filters, test_user.id, 1, 10)

#     assert total >= 1  # Should find the meeting tag
#     for tag in tags:
#         assert "meeting" in tag.name


# def test_tag_statistics_functionality(db: Session, test_user: User):
#     """Test tag statistics functionality"""
#     # Create tags
#     tag1 = create_tag(db, TagCreate(name="stats_tag1", scope="global"), test_user.id)
#     tag2 = create_tag(db, TagCreate(name="stats_tag2", scope="global"), test_user.id)

#     from app.services.tag import get_tag_statistics

#     # Get statistics for specific tags
#     stats = get_tag_statistics(db, [tag1.id, tag2.id])

#     assert isinstance(stats, dict)
#     # Should include our tags (meeting count should be 0 since no meetings are associated)
#     assert str(tag1.id) in stats
#     assert str(tag2.id) in stats


# def test_user_tags_functionality(db: Session, test_user: User):
#     """Test getting tags created by a user"""
#     # Create tags for the user
#     create_tag(db, TagCreate(name="user_tag1", scope="global"), test_user.id)
#     create_tag(db, TagCreate(name="user_tag2", scope="project"), test_user.id)

#     from app.services.tag import get_user_tags

#     # Get user's tags
#     user_tags = get_user_tags(db, test_user.id)

#     assert isinstance(user_tags, list)
#     assert len(user_tags) >= 2

#     # Check that tags belong to the user
#     for tag in user_tags:
#         assert tag.created_by == test_user.id


# def test_tag_search_functionality(db: Session, test_user: User):
#     """Test tag search functionality"""
#     # Create tags with searchable names
#     create_tag(db, TagCreate(name="urgent_meeting", scope="global"), test_user.id)
#     create_tag(db, TagCreate(name="weekly_standup", scope="project"), test_user.id)
#     create_tag(db, TagCreate(name="project_review", scope="global"), test_user.id)

#     from app.schemas.tag import TagFilter
#     from app.services.tag import search_tags

#     # Search for "urgent"
#     filters = TagFilter()
#     results = search_tags(db, "urgent", filters, test_user.id)

#     assert isinstance(results, list)
#     assert len(results) >= 1

#     # Should find the urgent_meeting tag
#     found_urgent = False
#     for tag in results:
#         if tag.name == "urgent_meeting":
#             found_urgent = True
#             break
#     assert found_urgent


# def test_tag_bulk_operations(db: Session, test_user: User):
#     """Test bulk tag operations"""
#     from app.services.tag import bulk_create_tags, bulk_delete_tags, bulk_update_tags

#     # Test bulk create
#     tags_data = [
#         TagCreate(name="bulk1", scope="global"),
#         TagCreate(name="bulk2", scope="project"),
#         TagCreate(name="bulk3", scope="global"),
#     ]

#     created_tags = bulk_create_tags(db, tags_data, test_user.id)
#     assert len(created_tags) == 3

#     # Test bulk update
#     updates = [
#         {"id": created_tags[0].id, "name": "updated_bulk1"},
#         {"id": created_tags[1].id, "name": "updated_bulk2"},
#     ]

#     updated_tags = bulk_update_tags(db, updates, test_user.id)
#     assert len(updated_tags) == 2
#     assert updated_tags[0].name == "updated_bulk1"
#     assert updated_tags[1].name == "updated_bulk2"

#     # Test bulk delete
#     tag_ids = [tag.id for tag in created_tags]
#     result = bulk_delete_tags(db, tag_ids, test_user.id)
#     assert result is True

#     # Verify all tags are deleted
#     for tag in created_tags:
#         retrieved = get_tag(db, tag.id, test_user.id)
#         assert retrieved is None


# def test_tag_crud_complete_lifecycle(db: Session, test_user: User):
#     """Test complete CRUD lifecycle of a tag"""
#     # Create
#     tag_data = TagCreate(name="lifecycle_test", scope="project")
#     tag = create_tag(db, tag_data, test_user.id)

#     assert tag.name == "lifecycle_test"
#     assert tag.scope == "project"

#     # Read
#     retrieved_tag = get_tag(db, tag.id, test_user.id)
#     assert retrieved_tag is not None
#     assert retrieved_tag.name == "lifecycle_test"

#     # Update
#     update_data = TagUpdate(name="updated_lifecycle")
#     updated_tag = update_tag(db, tag.id, update_data, test_user.id)
#     assert updated_tag.name == "updated_lifecycle"

#     # Delete
#     result = delete_tag(db, tag.id, test_user.id)
#     assert result is True

#     # Verify deletion
#     final_tag = get_tag(db, tag.id, test_user.id)
#     assert final_tag is None

