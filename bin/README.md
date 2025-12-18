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
  ./bin/build.sh              # Build API service (default, auto-detects requirements changes)
  ./bin/build.sh api          # Build API service
  ./bin/build.sh all          # Build all services
  ./bin/build.sh api --no-cache  # Force rebuild without cache (ensures fresh dependencies)
  ```
  **Smart rebuild**: The script automatically detects if `requirements.txt` has changed and rebuilds without cache when needed. Use `--no-cache` to force a full rebuild.

- **`bin/rebuild-requirements.sh [service]`** - Rebuild when requirements.txt changes
  ```bash
  ./bin/rebuild-requirements.sh api  # Check and rebuild if requirements changed
  ```
  This script compares the hash of `requirements.txt` with the last build and rebuilds if it has changed. Useful when you've added new packages.

- **`bin/install-requirements.sh`** - Quick install requirements in running container
  ```bash
  ./bin/install-requirements.sh
  ```
  ⚠️ This is temporary - requirements will be lost when container restarts. Use `build.sh --no-cache` for permanent installation.

- **`bin/fix-dependencies.sh`** - Fix missing dependencies and verify installation
  ```bash
  ./bin/fix-dependencies.sh
  ```
  Installs all packages from requirements.txt and verifies key packages (bcrypt, slowapi). Useful when packages are missing after build.

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
  ./bin/dev.sh status        # Show service status
  ./bin/dev.sh packages      # List installed packages
  ./bin/dev.sh check-packages bcrypt  # Check specific package
  ```

- **`bin/list-packages.sh [options]`** - List installed packages
  ```bash
  ./bin/list-packages.sh              # List all packages
  ./bin/list-packages.sh --requirements  # Check packages from requirements.txt
  ./bin/list-packages.sh bcrypt       # Check specific package
  ./bin/list-packages.sh --format json   # Output in JSON format
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

- **`bin/seed.sh`** - Seed database with admin user and demo data
  ```bash
  # Run with default admin credentials
  ./bin/seed.sh

  # Customize admin credentials
  ADMIN_EMAIL="admin@company.com" ADMIN_PASSWORD="SecurePass123!" ./bin/seed.sh

  # Skip admin creation (only demo data)
  SEED_ADMIN=false ./bin/seed.sh
  ```
  Seeds the database with:
  - Admin user (HR role) - default: `admin@example.com` / `Admin123!`
  - Demo team and users (if database is empty)
  
  See [SEEDING.md](../SEEDING.md) for full documentation.

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
