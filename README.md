# SecureScribeBE

A FastAPI project with structured layout.

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   ├── dependencies/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── utils/
├── tests/
├── requirements.txt
```

## Getting Started

### Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Docker Development

```bash
# Start the API server
docker-compose up api

# Or start with database
docker-compose up api db
```

### Running Tests

#### Docker Testing

```bash
# Run tests with Docker (uses production database)
docker compose --profile test up 

# Or run tests and keep containers running
docker-compose --profile test up --abort-on-container-exit

# Or use the test script
./run-tests.sh docker
```

#### Local Testing

```bash
# Run tests locally
pytest tests/ -v

# Or use the test script
./run-tests.sh local
```

**Note:** Tests run against the production database. Make sure your database is properly configured and backed up before running tests.

## Chat Schema Update

The chat subsystem is now session-centric and no longer joins meetings directly.

- `chat_sessions` no longer includes a `meeting_id` column; sessions are keyed to users only.
- `chat_messages` gained a non-null `mentions` JSON column for storing raw mention metadata from API requests.
- API requests accept a `mentions` array on chat messages, and responses echo the stored metadata.

### Manual Migration

Because the project does not ship with automated migrations, apply the following SQL in existing environments:

```sql
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS meeting_id;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS mentions JSONB NOT NULL DEFAULT '[]'::jsonb;
```

Reapply defaults or backfill data as needed to match your deployment requirements.
