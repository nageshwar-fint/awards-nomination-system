# Tests

This directory contains unit tests for all API endpoints.

## Running Tests

### Using Docker (Recommended)

```bash
# Run all tests
docker compose exec api pytest

# Run with coverage
docker compose exec api pytest --cov=app --cov-report=html

# Run specific test file
docker compose exec api pytest tests/test_cycles.py

# Run specific test
docker compose exec api pytest tests/test_cycles.py::test_create_cycle -v

# Run with verbose output
docker compose exec api pytest -v
```

### Local Development

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_health.py` - Health check endpoint tests
- `test_cycles.py` - Cycle CRUD endpoint tests
- `test_criteria.py` - Criteria CRUD endpoint tests
- `test_nominations.py` - Nomination endpoint tests
- `test_approvals.py` - Approval endpoint tests
- `test_rankings.py` - Ranking endpoint tests

## Test Coverage

The test suite covers:

- ✅ All GET endpoints (list and retrieve)
- ✅ All POST endpoints (create)
- ✅ All PATCH endpoints (update)
- ✅ All DELETE endpoints
- ✅ Authentication and authorization (RBAC)
- ✅ Error handling (400, 403, 404, 422)
- ✅ Business logic validation
- ✅ Edge cases and boundary conditions

## Fixtures

Common fixtures available in `conftest.py`:

- `db_session` - Fresh database session for each test
- `client` - FastAPI TestClient
- `test_team` - Test team
- `test_employee_user` - Employee user
- `test_team_lead_user` - Team lead user (DEPRECATED: mapped to a MANAGER role; retained for backwards compatibility in tests)
- `test_manager_user` - Manager user
- `test_hr_user` - HR user
- `test_cycle` - Open nomination cycle
- `test_draft_cycle` - Draft nomination cycle
- `test_criteria` - Test criteria
- `test_nomination` - Test nomination

## Helper Functions

- `create_jwt_token(user_id, email, role)` - Create JWT token for testing
- `get_auth_headers(user)` - Get authorization headers for a user
