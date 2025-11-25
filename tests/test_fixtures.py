"""Test to verify test fixtures and factories are working correctly"""

from tests.factories import (
    FileFactory,
    MeetingFactory,
    ProjectFactory,
    TaskFactory,
    UserFactory,
)
from tests.mocks import (
    MockMinIOClient,
    MockQdrantClient,
    MockRedisClient,
)


def test_user_factory(db_session):
    """Test that UserFactory creates valid users"""
    user = UserFactory.create(db_session)
    assert user.id is not None
    assert user.email is not None
    assert user.name is not None


def test_user_factory_batch(db_session):
    """Test that UserFactory can create multiple users"""
    users = UserFactory.create_batch(db_session, count=3)
    assert len(users) == 3
    assert all(user.id is not None for user in users)


def test_project_factory(db_session):
    """Test that ProjectFactory creates valid projects"""
    user = UserFactory.create(db_session)
    project = ProjectFactory.create(db_session, created_by=user)
    assert project.id is not None
    assert project.name is not None
    assert project.created_by == user.id


def test_meeting_factory(db_session):
    """Test that MeetingFactory creates valid meetings"""
    user = UserFactory.create(db_session)
    meeting = MeetingFactory.create(db_session, created_by=user)
    assert meeting.id is not None
    assert meeting.title is not None
    assert meeting.created_by == user.id


def test_task_factory(db_session):
    """Test that TaskFactory creates valid tasks"""
    user = UserFactory.create(db_session)
    task = TaskFactory.create(db_session, creator=user)
    assert task.id is not None
    assert task.title is not None
    assert task.creator_id == user.id


def test_file_factory(db_session):
    """Test that FileFactory creates valid files"""
    user = UserFactory.create(db_session)
    file = FileFactory.create(db_session, uploaded_by=user)
    assert file.id is not None
    assert file.filename is not None
    assert file.uploaded_by == user.id


def test_mock_minio_client():
    """Test MockMinIOClient functionality"""
    client = MockMinIOClient()

    # Test put_object
    client.put_object("test-bucket", "test-file.txt", b"test data")

    # Test get_object
    response = client.get_object("test-bucket", "test-file.txt")
    assert response.data == b"test data"

    # Test list_objects
    objects = client.list_objects("test-bucket")
    assert len(objects) == 1

    # Test remove_object
    client.remove_object("test-bucket", "test-file.txt")
    objects = client.list_objects("test-bucket")
    assert len(objects) == 0


def test_mock_qdrant_client():
    """Test MockQdrantClient functionality"""
    client = MockQdrantClient()

    # Test recreate_collection
    client.recreate_collection("test-collection", {"size": 384, "distance": "Cosine"})
    assert client.collection_exists("test-collection")

    # Test upsert
    client.upsert("test-collection", [{"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"text": "test"}}])

    # Test search
    results = client.search("test-collection", [0.1, 0.2, 0.3], limit=10)
    assert len(results) > 0


def test_mock_redis_client():
    """Test MockRedisClient functionality"""
    client = MockRedisClient()

    # Test set/get
    client.set("test-key", "test-value")
    assert client.get("test-key") == "test-value"

    # Test delete
    deleted_count = client.delete("test-key")
    assert deleted_count == 1
    assert client.get("test-key") is None

    # Test exists
    client.set("key1", "value1")
    assert client.exists("key1") == 1
    assert client.exists("key2") == 0

    # Test incr/decr
    client.set("counter", 0)
    assert client.incr("counter") == 1
    assert client.decr("counter") == 0

    # Test list operations
    client.rpush("list", "a", "b", "c")
    result = client.lrange("list", 0, -1)
    assert result == ["a", "b", "c"]

    # Test hash operations
    client.hset("hash", {"field1": "value1", "field2": "value2"})
    assert client.hget("hash", "field1") == "value1"
    hash_all = client.hgetall("hash")
    assert hash_all == {"field1": "value1", "field2": "value2"}
