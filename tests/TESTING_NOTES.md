# Testing Notes

## Installing Dependencies

After adding new dependencies to `requirements.txt`, you need to rebuild the Docker container:

```bash
docker compose build api
docker compose up -d
```

Or, to install dependencies in the running container (temporary):

```bash
docker compose exec api pip install -r requirements.txt
```

## Running Tests

```bash
# All tests
docker compose exec api pytest

# With coverage
docker compose exec api pytest --cov=app --cov-report=html

# Specific test file
docker compose exec api pytest tests/test_cycles.py -v
```

## Test Database

Tests use SQLite in-memory database for speed. The test configuration automatically handles PostgreSQL-specific types (JSONB, UUID) by converting them to SQLite-compatible types.

For more accurate testing that matches production, you could use PostgreSQL in tests, but it requires additional setup.
