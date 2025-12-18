# Development Scripts

Collection of shell scripts to simplify common development tasks.

## Available Scripts

### Setup & Build

- **`bin/setup.sh`** - Initial project setup
  ```bash
  ./bin/setup.sh
  ```
  - Creates `.env` file if missing
  - Generates JWT_SECRET
  - Builds Docker containers
  - Starts services
  - Runs migrations

- **`bin/build.sh [service] [--no-cache]`** - Build Docker containers
  ```bash
  ./bin/build.sh              # Build API service (default)
  ./bin/build.sh api          # Build API service
  ./bin/build.sh all          # Build all services
  ./bin/build.sh api --no-cache  # Build without cache (ensures fresh dependencies)
  ```
  The `--no-cache` flag is useful when requirements.txt changes and you want to ensure all dependencies are freshly installed.

- **`bin/install-requirements.sh`** - Quick install requirements in running container
  ```bash
  ./bin/install-requirements.sh
  ```
  ⚠️ This is temporary - requirements will be lost when container restarts. Use `build.sh --no-cache` for permanent installation.

### Development

- **`bin/dev.sh <command>`** - Development helper
  ```bash
  ./bin/dev.sh start      # Start all services
  ./bin/dev.sh stop       # Stop all services
  ./bin/dev.sh restart    # Restart services
  ./bin/dev.sh logs       # View API logs
  ./bin/dev.sh logs db    # View database logs
  ./bin/dev.sh shell      # Open shell in API container
  ./bin/dev.sh db-shell   # Open PostgreSQL shell
  ./bin/dev.sh clean      # Stop and remove volumes
  ./bin/dev.sh status     # Show service status
  ```

### Testing

- **`bin/test.sh [pytest args]`** - Run tests
  ```bash
  ./bin/test.sh                           # Run all tests
  ./bin/test.sh tests/test_auth.py        # Run specific test file
  ./bin/test.sh -v                        # Verbose output
  ./bin/test.sh -k test_register          # Run tests matching pattern
  ./bin/test.sh --tb=short                # Short traceback
  ```

- **`bin/test-coverage.sh`** - Run tests with coverage
  ```bash
  ./bin/test-coverage.sh
  ```
  Generates HTML coverage report in `htmlcov/index.html`

### Database Migrations

- **`bin/migrate.sh [command]`** - Run migrations
  ```bash
  ./bin/migrate.sh up        # Upgrade to latest (default)
  ./bin/migrate.sh down -1   # Rollback one migration
  ./bin/migrate.sh current   # Show current version
  ./bin/migrate.sh history   # Show migration history
  ```

- **`bin/migration-create.sh "message"`** - Create new migration
  ```bash
  ./bin/migration-create.sh "Add user authentication fields"
  ```
  Creates a new migration file that you should review before applying.

## Quick Start

1. **First time setup:**
   ```bash
   ./bin/setup.sh
   ```

2. **Start development:**
   ```bash
   ./bin/dev.sh start
   ```

3. **Run tests:**
   ```bash
   ./bin/test.sh
   ```

4. **Create and apply migration:**
   ```bash
   ./bin/migration-create.sh "Description"
   # Review the generated file in alembic/versions/
   ./bin/migrate.sh up
   ```

## Direct Docker Commands (Alternative)

If you prefer using Docker directly:

```bash
# Tests
docker compose exec api pytest

# Migrations
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "message"

# Build
docker compose build api

# Logs
docker compose logs -f api
```

## Tips

- All scripts check for errors and exit on failure (`set -e`)
- Scripts are designed to work both inside and outside Docker containers
- Use `./bin/dev.sh help` to see available commands
- Test scripts accept all standard pytest arguments
