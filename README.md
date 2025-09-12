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
