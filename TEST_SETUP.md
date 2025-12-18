# Test Setup for Authentication

## Fixing slowapi Module Error

If you see `ModuleNotFoundError: No module named 'slowapi'`, you need to rebuild the Docker container to install new dependencies.

### Solution 1: Rebuild Docker Container (Recommended)

```bash
# Rebuild the API container with new dependencies
docker compose build api

# Restart containers
docker compose up -d

# Verify slowapi is installed
docker compose exec api pip list | grep slowapi
```

### Solution 2: Install Dependencies in Running Container (Temporary)

If you can't rebuild right now, install dependencies in the running container:

```bash
# Install slowapi and bcrypt in running container
docker compose exec api pip install slowapi>=0.1.9 bcrypt>=4.0.0

# Then run tests
docker compose exec api pytest tests/test_auth.py -v
```

**Note:** This is temporary - dependencies will be lost when container restarts. Always rebuild for permanent fix.

## Running Authentication Tests

After dependencies are installed:

```bash
# Run all auth tests
docker compose exec api pytest tests/test_auth.py -v

# Run with coverage
docker compose exec api pytest tests/test_auth.py --cov=app.api.v1.auth --cov=app.auth.password -v

# Run specific test
docker compose exec api pytest tests/test_auth.py::test_register_user -v

# Run all tests
docker compose exec api pytest -v
```

## Test Coverage

The authentication tests cover:

- ✅ User registration with security questions
- ✅ Login with email/password
- ✅ Password reset with security questions
- ✅ Password strength validation
- ✅ Security question validation
- ✅ Error handling and edge cases
- ✅ Password hashing utilities

All tests use the test database (SQLite in-memory) and don't affect production data.
