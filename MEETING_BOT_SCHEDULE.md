# Meeting Bot Scheduling Implementation

## Overview

This implementation adds automatic bot scheduling functionality when creating meetings. When a meeting is created with a `start_time`, `url`, and valid bearer token, the system will automatically schedule a bot to join the meeting at the specified time.

## How It Works

### 1. Meeting Creation Flow

When a meeting is created via `POST /api/v1/meetings`:

1. The endpoint extracts the user's bearer token
2. Calls `create_meeting()` service function with the token
3. If the meeting has `start_time`, `url`, and `bearer_token` (and start_time is in the future):
   - Schedules a Celery task to execute at the meeting's `start_time`
   - The task will make an HTTP POST request to the bot service

### 2. Bot API Call Structure

The scheduled task makes a POST request to:

```
POST http://localhost:3000/google/join
Content-Type: application/json
```

With payload:

```json
{
	"bearerToken": "user's_jwt_token",
	"url": "https://meet.google.com/meeting-link",
	"name": "Meeting Notetaker",
	"teamId": "meeting_uuid",
	"timezone": "UTC",
	"userId": "user_uuid",
	"botId": "Bot123"
}
```

### 3. Field Mapping

- `bearerToken`: The user's JWT access token
- `url`: The meeting URL (Google Meet link)
- `name`: Always "Meeting Notetaker"
- `teamId`: The meeting UUID
- `timezone`: Always "UTC"
- `userId`: The creator's user UUID
- `botId`: Randomly generated (Bot123, Bot456, etc.)

## Implementation Details

### Files Modified

1. **`app/jobs/tasks.py`**

   - Added `schedule_meeting_bot_task()` Celery task
   - Handles HTTP request to bot service
   - Generates random bot ID
   - Includes error handling and logging

2. **`app/services/meeting.py`**

   - Modified `create_meeting()` to accept optional `bearer_token`
   - Added scheduling logic with timezone-aware time checking
   - Uses `apply_async()` with `eta` parameter for precise timing

3. **`app/api/endpoints/meeting.py`**
   - Modified endpoint to extract bearer token using `jwt_bearer` dependency
   - Passes token to service function

### Key Features

- **Timezone Aware**: Uses `datetime.now(timezone.utc)` for proper comparison
- **Future Time Validation**: Only schedules for meetings in the future
- **Error Handling**: Comprehensive error handling in the Celery task
- **Random Bot IDs**: Generates unique bot identifiers (Bot100-Bot999)
- **Flexible Scheduling**: Uses Celery's `eta` parameter for precise execution timing

### Example Usage

Creating a meeting that will automatically schedule a bot:

```bash
curl -X POST "http://localhost:8000/api/v1/meetings" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Standup",
    "description": "Daily standup meeting",
    "url": "https://meet.google.com/xyz-abc-def",
    "start_time": "2025-09-23T15:30:00+00:00",
    "is_personal": false,
    "project_ids": ["project-uuid"]
  }'
```

The bot will automatically be scheduled to join at 15:30 UTC.

### Time Format

The `start_time` should be in ISO 8601 format with timezone:

```
2025-09-23T10:53:51.944130+00:00
```

This matches the database timestamp format mentioned in the requirements.

## Error Handling

The system handles various error scenarios:

1. **HTTP Request Failures**: Task logs error and returns failure status
2. **Invalid Times**: Past meeting times are ignored (no scheduling)
3. **Missing Parameters**: Bot scheduling is skipped if any required field is missing
4. **Network Issues**: Request timeout set to 30 seconds

## Monitoring

The Celery task provides comprehensive logging:

- Success: Logs bot ID and meeting ID
- Failure: Logs HTTP status codes and error messages
- Returns structured result with success status

## Dependencies

- **Celery**: For task scheduling and execution
- **requests**: For HTTP calls to bot service
- **JWT**: For bearer token handling

This implementation follows the minimal coding style rules while providing robust bot scheduling functionality.
