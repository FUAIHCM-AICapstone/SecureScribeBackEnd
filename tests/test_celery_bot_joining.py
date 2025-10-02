import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.jobs.tasks import schedule_meeting_bot_task
from app.services.meeting import create_meeting
from app.schemas.meeting import MeetingCreate
from app.models.meeting import Meeting
from app.core.config import settings


@pytest.fixture
def mock_bot_response():
    """Mock successful bot service response"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"success": True, "bot_id": "Bot123"}
    return response


@pytest.fixture
def mock_bot_error_response():
    """Mock failed bot service response"""
    response = MagicMock()
    response.status_code = 500
    response.json.return_value = {"success": False, "error": "service unavailable"}
    return response


@pytest.fixture
def future_meeting_data():
    """Meeting data with future start time"""
    return MeetingCreate(
        title="Team Standup",
        description="Daily standup meeting",
        url="https://meet.google.com/test-meeting",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        is_personal=False,
        project_ids=[]
    )


@pytest.fixture
def past_meeting_data():
    """Meeting data with past start time"""
    return MeetingCreate(
        title="Old Meeting",
        description="Meeting in the past",
        url="https://meet.google.com/old-meeting",
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
        is_personal=False,
        project_ids=[]
    )


def test_schedule_meeting_bot_task_direct_success():
    """Test Celery task directly with successful bot API response"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-jwt-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=456), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        assert result["success"] == True
        assert result["bot_id"] == "Bot456"
        assert result["meeting_id"] == meeting_id
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == f"{settings.BOT_SERVICE_URL}/google/join"
        assert kwargs["json"]["bearerToken"] == bearer_token
        assert kwargs["json"]["url"] == meeting_url
        assert kwargs["json"]["teamId"] == meeting_id
        assert kwargs["json"]["userId"] == user_id
        assert kwargs["json"]["botId"] == "Bot456"
        assert kwargs["json"]["name"] == "Meeting Notetaker"
        assert kwargs["json"]["timezone"] == "UTC"
        assert kwargs["timeout"] == 30


def test_schedule_meeting_bot_task_direct_failure():
    """Test Celery task directly with failed bot API response"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-jwt-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=789), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"success": False, "error": "invalid url"}
        mock_post.return_value = mock_response
        
        result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        assert result["success"] == False
        assert result["error"] == "invalid url"


def test_schedule_meeting_bot_task_direct_exception():
    """Test Celery task directly with network exception"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-jwt-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=999), \
         patch("app.jobs.tasks.requests.post", side_effect=Exception("connection timeout")):
        
        result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        assert result["success"] == False
        assert result["error"] == "connection timeout"
        assert result["meeting_id"] == meeting_id


def test_schedule_meeting_bot_task_accepted_response():
    """Test Celery task with 202 Accepted response"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-jwt-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=202), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response
        
        result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        assert result["success"] == True
        assert result["bot_id"] == "Bot202"


@patch("app.jobs.tasks.schedule_meeting_bot_task.apply_async")
def test_create_meeting_schedules_bot_future_time(mock_apply_async, db: Session, test_user, future_meeting_data):
    """Test meeting creation schedules bot for future meeting"""
    bearer_token = "test-jwt-token"
    
    meeting = create_meeting(db, future_meeting_data, test_user.id, bearer_token)
    
    assert meeting.id is not None
    mock_apply_async.assert_called_once()
    call_args = mock_apply_async.call_args
    assert call_args[1]["args"] == [str(meeting.id), str(test_user.id), bearer_token, future_meeting_data.url]
    assert call_args[1]["eta"] == future_meeting_data.start_time


@patch("app.jobs.tasks.schedule_meeting_bot_task.apply_async")
def test_create_meeting_no_schedule_past_time(mock_apply_async, db: Session, test_user, past_meeting_data):
    """Test meeting creation does not schedule bot for past meeting"""
    bearer_token = "test-jwt-token"
    
    meeting = create_meeting(db, past_meeting_data, test_user.id, bearer_token)
    
    assert meeting.id is not None
    mock_apply_async.assert_not_called()


@patch("app.jobs.tasks.schedule_meeting_bot_task.apply_async")
def test_create_meeting_no_schedule_no_url(mock_apply_async, db: Session, test_user):
    """Test meeting creation does not schedule bot without URL"""
    meeting_data = MeetingCreate(
        title="No URL Meeting",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        is_personal=False,
        project_ids=[]
    )
    
    meeting = create_meeting(db, meeting_data, test_user.id, "test-token")
    
    assert meeting.id is not None
    mock_apply_async.assert_not_called()


@patch("app.jobs.tasks.schedule_meeting_bot_task.apply_async")
def test_create_meeting_no_schedule_no_token(mock_apply_async, db: Session, test_user, future_meeting_data):
    """Test meeting creation does not schedule bot without bearer token"""
    meeting = create_meeting(db, future_meeting_data, test_user.id, None)
    
    assert meeting.id is not None
    mock_apply_async.assert_not_called()


@patch("app.jobs.tasks.schedule_meeting_bot_task.apply_async")
def test_create_meeting_no_schedule_no_start_time(mock_apply_async, db: Session, test_user):
    """Test meeting creation does not schedule bot without start time"""
    meeting_data = MeetingCreate(
        title="No Start Time Meeting",
        url="https://meet.google.com/test",
        is_personal=False,
        project_ids=[]
    )
    
    meeting = create_meeting(db, meeting_data, test_user.id, "test-token")
    
    assert meeting.id is not None
    mock_apply_async.assert_not_called()


def test_schedule_meeting_bot_task_random_bot_id():
    """Test bot ID generation uses random number"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-jwt-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=555), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        assert result["bot_id"] == "Bot555"
        
        # Verify bot ID in API call
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["botId"] == "Bot555"


def test_schedule_meeting_bot_task_payload_structure():
    """Test exact payload structure sent to bot API"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
    meeting_url = "https://meet.google.com/xyz-abc-def"

    with patch("app.jobs.tasks.random.randint", return_value=100), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        args, kwargs = mock_post.call_args
        expected_payload = {
            "bearerToken": bearer_token,
            "url": meeting_url,
            "name": "Meeting Notetaker",
            "teamId": meeting_id,
            "timezone": "UTC",
            "userId": user_id,
            "botId": "Bot100"
        }
        assert kwargs["json"] == expected_payload
        assert kwargs["headers"] == {"Content-Type": "application/json"}


def test_schedule_meeting_bot_task_http_error_codes():
    """Test various HTTP error response codes"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-token"
    meeting_url = "https://meet.google.com/test"
    
    error_codes = [400, 401, 403, 404, 500, 502, 503]
    
    for error_code in error_codes:
        with patch("app.jobs.tasks.random.randint", return_value=123), \
             patch("app.jobs.tasks.requests.post") as mock_post:
            
            mock_response = MagicMock()
            mock_response.status_code = error_code
            mock_response.json.return_value = {"error": f"HTTP {error_code}"}
            mock_post.return_value = mock_response
            
            result = schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
            
            assert result == {"error": f"HTTP {error_code}"}


def test_schedule_meeting_bot_task_request_timeout():
    """Test request timeout configuration"""
    meeting_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    bearer_token = "test-token"
    meeting_url = "https://meet.google.com/test"

    with patch("app.jobs.tasks.random.randint", return_value=333), \
         patch("app.jobs.tasks.requests.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        schedule_meeting_bot_task.run(meeting_id, user_id, bearer_token, meeting_url)
        
        args, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 30