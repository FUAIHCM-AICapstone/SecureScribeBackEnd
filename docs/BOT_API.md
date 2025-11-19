# Meeting Bot API Documentation

## Overview

The Meeting Bot API enables triggering a bot to join Google Meet meetings and receive recordings via webhook. The bot records the meeting and sends the recording back to your application for processing.

---

## Base URL

```
http://localhost:8081/api/v1
```

## Authentication

All endpoints require Bearer token authentication in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Trigger Bot to Join Meeting

**Endpoint:** `POST /meetings/{meeting_id}/bot/join`

**Status Code:** `202 Accepted`

**Description:** Triggers a bot to join a specific meeting. The bot will record the meeting and send the recording to the configured webhook URL.

#### Request

**Path Parameters:**
- `meeting_id` (UUID, required): The ID of the meeting

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Body:**
```json
{
  "meeting_url": "https://meet.google.com/abc-defg-hij",
  "immediate": true
}
```

**Body Parameters:**
- `meeting_url` (string, optional): Override the meeting URL stored in the bot config. Max 2048 characters.
- `immediate` (boolean, optional, default: false): If true, bot joins immediately. If false, uses scheduled time from bot config.

#### Response

**Success (202 Accepted):**
```json
{
  "success": true,
  "message": "Bot join triggered successfully",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "bot_id": "550e8400-e29b-41d4-a716-446655440001",
    "meeting_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "pending",
    "scheduled_start_time": null,
    "created_at": "2025-11-19T10:30:00Z"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid bearer token format or meeting URL too long
- `401 Unauthorized`: Missing or invalid authorization header
- `403 Forbidden`: User not authorized for this meeting
- `404 Not Found`: Meeting or bot not found
- `500 Internal Server Error`: Failed to queue bot join task

#### CURL Example

```bash
curl -X POST http://localhost:8081/api/v1/meetings/550e8400-e29b-41d4-a716-446655440002/bot/join \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_url": "https://meet.google.com/abc-defg-hij",
    "immediate": true
  }'
```

#### Response Example

```json
{
  "success": true,
  "message": "Bot join triggered successfully",
  "data": {
    "task_id": "abc123def456",
    "bot_id": "550e8400-e29b-41d4-a716-446655440001",
    "meeting_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "pending",
    "scheduled_start_time": null,
    "created_at": "2025-11-19T10:30:00Z"
  }
}
```

---

### 2. Bot Webhook - Receive Recording

**Endpoint:** `POST /bot/webhook/recording`

**Status Code:** `202 Accepted`

**Description:** Webhook endpoint that receives the bot recording after the meeting ends. This endpoint is called by the bot service, not by the frontend.

#### Request

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Form Data:**
- `recording` (file, required): Binary video/webm file from the bot
- `botId` (string, required): ID of the bot that recorded
- `meetingUrl` (string, required): URL of the meeting that was recorded
- `status` (string, required): Status of the recording (e.g., "completed")
- `teamId` (string, required): Team ID from the bot service
- `timestamp` (string, required): ISO 8601 timestamp of when recording completed
- `userId` (string, required): User ID (ignored, uses bearer token user instead)

#### Response

**Success (202 Accepted):**
```json
{
  "success": true,
  "message": "Recording received and queued for processing",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440003",
    "audio_file_id": "550e8400-e29b-41d4-a716-446655440004"
  }
}
```

**On Processing Failure (202 Accepted with retry):**
```json
{
  "success": true,
  "message": "Recording received, queued for retry",
  "data": {
    "retry_task_id": "550e8400-e29b-41d4-a716-446655440005"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid bearer token format or empty recording file
- `401 Unauthorized`: Missing or invalid authorization header
- `404 Not Found`: Meeting not found by URL
- `500 Internal Server Error`: Failed to store audio file

#### CURL Example

```bash
curl -X POST http://localhost:8081/api/v1/bot/webhook/recording \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "recording=@/path/to/recording.webm" \
  -F "botId=Bot123" \
  -F "meetingUrl=https://meet.google.com/abc-defg-hij" \
  -F "status=completed" \
  -F "teamId=team123" \
  -F "timestamp=2025-11-19T11:30:00Z" \
  -F "userId=user123"
```

#### Response Example

```json
{
  "success": true,
  "message": "Recording received and queued for processing",
  "data": {
    "task_id": "abc123def456",
    "audio_file_id": "550e8400-e29b-41d4-a716-446655440004"
  }
}
```

---

## Data Models

### MeetingBotJoinRequest

```json
{
  "meeting_url": "string (optional, max 2048 chars)",
  "immediate": "boolean (optional, default: false)"
}
```

### MeetingBotJoinResponse

```json
{
  "task_id": "string (UUID)",
  "bot_id": "string (UUID)",
  "meeting_id": "string (UUID)",
  "status": "string (pending|scheduled|completed|failed)",
  "scheduled_start_time": "string (ISO 8601 datetime, nullable)",
  "created_at": "string (ISO 8601 datetime)"
}
```

### BotWebhookCallback

```json
{
  "botId": "string",
  "meetingUrl": "string",
  "status": "string",
  "teamId": "string",
  "timestamp": "string (ISO 8601 datetime)",
  "userId": "string"
}
```

### AudioFile (Created from webhook)

```json
{
  "id": "string (UUID)",
  "meeting_id": "string (UUID)",
  "uploaded_by": "string (UUID)",
  "file_url": "string (presigned MinIO URL)",
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime, nullable)"
}
```

---

## Workflow

### Complete Bot Recording Flow

1. **Frontend triggers bot join:**
   ```
   POST /meetings/{meeting_id}/bot/join
   ```
   - Returns `task_id` and `bot_id`
   - Bot service receives webhook URL in the request payload

2. **Bot joins meeting and records:**
   - Bot service joins the Google Meet
   - Records the entire meeting
   - Saves recording as video/webm

3. **Bot sends recording to webhook:**
   ```
   POST /bot/webhook/recording
   ```
   - Sends multipart form data with recording file
   - Includes metadata (botId, meetingUrl, status, etc.)

4. **Backend processes recording:**
   - Stores audio file in MinIO
   - Creates AudioFile record in database
   - Queues `process_audio_task` Celery task
   - Returns 202 Accepted with task_id

5. **Audio processing (async):**
   - Transcribes audio to text
   - Chunks text and generates embeddings
   - Stores vectors in Qdrant
   - Updates transcript in database

---

## Error Handling

### Common Error Scenarios

**Missing Authorization Header:**
```bash
curl -X POST http://localhost:8081/api/v1/meetings/550e8400-e29b-41d4-a716-446655440002/bot/join
```
Response: `401 Unauthorized - Authorization header required`

**Invalid Bearer Token Format:**
```bash
curl -X POST http://localhost:8081/api/v1/meetings/550e8400-e29b-41d4-a716-446655440002/bot/join \
  -H "Authorization: InvalidToken"
```
Response: `400 Bad Request - Invalid bearer token format`

**Meeting Not Found:**
```bash
curl -X POST http://localhost:8081/api/v1/meetings/00000000-0000-0000-0000-000000000000/bot/join \
  -H "Authorization: Bearer <token>"
```
Response: `404 Not Found - Meeting not found`

**User Not Authorized:**
```bash
# User is not the meeting creator and not a project member
curl -X POST http://localhost:8081/api/v1/meetings/550e8400-e29b-41d4-a716-446655440002/bot/join \
  -H "Authorization: Bearer <other_user_token>"
```
Response: `403 Forbidden - Not authorized to trigger bot for this meeting`

---

## Configuration

### Environment Variables

Add to `.env`:

```env
# Bot Service Configuration
BOT_SERVICE_URL=http://host.docker.internal:3000
BOT_WEBHOOK_URL=http://localhost:8081/api/v1/bot/webhook/recording
```

The `BOT_WEBHOOK_URL` is automatically included in the bot join request payload sent to the bot service.

---

## Testing

### Test with cURL

**1. Get JWT Token:**
```bash
curl -X POST http://localhost:8081/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**2. Trigger Bot Join:**
```bash
TOKEN="<jwt_token_from_step_1>"
MEETING_ID="550e8400-e29b-41d4-a716-446655440002"

curl -X POST http://localhost:8081/api/v1/meetings/$MEETING_ID/bot/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_url": "https://meet.google.com/abc-defg-hij",
    "immediate": true
  }'
```

**3. Simulate Webhook (from bot service):**
```bash
TOKEN="<jwt_token>"

curl -X POST http://localhost:8081/api/v1/bot/webhook/recording \
  -H "Authorization: Bearer $TOKEN" \
  -F "recording=@recording.webm" \
  -F "botId=Bot123" \
  -F "meetingUrl=https://meet.google.com/abc-defg-hij" \
  -F "status=completed" \
  -F "teamId=team123" \
  -F "timestamp=2025-11-19T11:30:00Z" \
  -F "userId=user123"
```

---

## Response Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 202 | Accepted | Task queued successfully (async operation) |
| 400 | Bad Request | Invalid input, validation error |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | User lacks permission |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error, check logs |

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- All IDs are UUIDs
- The webhook endpoint is called by the bot service, not the frontend
- Audio files are stored in MinIO and processing is async via Celery
- Bearer tokens should be included in all requests
- The bot service must be configured with the correct webhook URL
