# Awards Nomination System

Employee recognition system for managing nomination cycles, criteria, nominations, approvals, and rankings.

## Overview

This system enables organizations to run structured nomination cycles where team leads, managers, and HR can nominate employees based on weighted criteria. Nominations go through an approval workflow, and final rankings are computed and finalized for each cycle.

## Features

- **Nomination Cycles Management**: Create and manage nomination cycles with start/end dates
- **Criteria Management**: Define weighted criteria for each cycle with validation
- **Nomination Submission**: Team leads and managers can submit nominations with scores
- **Approval Workflow**: Managers and HR can approve or reject nominations
- **Ranking System**: Automatic computation of weighted rankings based on criteria scores
- **Cycle Finalization**: Finalize cycles with historical snapshots
- **Role-Based Access Control (RBAC)**: Enforced at API level (EMPLOYEE, TEAM_LEAD, MANAGER, HR)
- **JWT Authentication**: Secure API access with JWT tokens
- **Audit Logging**: All actions are logged for audit purposes
- **RESTful API**: Complete CRUD operations with proper HTTP methods

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT (PyJWT)
- **Logging**: Structlog for structured JSON logging
- **Containerization**: Docker & Docker Compose
- **Validation**: Pydantic v2

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)

### Getting Started

**Quick Setup (Recommended):**
```bash
# Run the setup script (does everything automatically)
./bin/setup.sh
```

> **💡 New System?** If setting up on a fresh machine, the setup script will build containers without cache to ensure all dependencies (including slowapi and bcrypt) are properly installed. See [NEW_SYSTEM_SETUP.md](NEW_SYSTEM_SETUP.md) for detailed instructions.

**Manual Setup:**

1. **Clone the repository**
   ```bash
   git clone <repo-url> awards-nomination-system
   cd awards-nomination-system
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env and set appropriate values (especially JWT_SECRET for production)
   ```

3. **Start the services**
   ```bash
   docker compose up -d
   ```

4. **Run migrations** (if not auto-run)
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. **Seed reference data** (optional)
   ```bash
   docker compose exec api python -m scripts.seed
   ```

6. **Verify health**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

**💡 Development Scripts:** See [`bin/README.md`](bin/README.md) for helpful scripts for testing, migrations, and development tasks.

## Documentation

### For Frontend Developers

- **[Roles & Workflows Guide](ROLES_AND_WORKFLOWS.md)** - Complete guide on user roles, permissions, responsibilities, and workflows
- **[Frontend Integration Guide](FRONTEND_GUIDE.md)** - Quick start guide with TypeScript interfaces and helper functions
- **[API Reference](API_DOCS.md)** - Complete API endpoint documentation

### Interactive API Documentation

Once the API is running, interactive documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

The API runs on `http://localhost:8000` by default.

## API Endpoints

### Cycles
- `GET /api/v1/cycles` - List all cycles
- `GET /api/v1/cycles/{cycle_id}` - Get cycle details
- `POST /api/v1/cycles` - Create new cycle (Requires: TEAM_LEAD+)
- `PATCH /api/v1/cycles/{cycle_id}` - Update cycle (Requires: TEAM_LEAD+, DRAFT only)
- `DELETE /api/v1/cycles/{cycle_id}` - Delete cycle (Requires: TEAM_LEAD+, DRAFT only)

### Criteria
- `GET /api/v1/cycles/{cycle_id}/criteria` - List criteria for cycle
- `GET /api/v1/criteria/{criteria_id}` - Get criteria details
- `POST /api/v1/cycles/{cycle_id}/criteria` - Add criteria (Requires: TEAM_LEAD+)
- `PATCH /api/v1/criteria/{criteria_id}` - Update criteria (Requires: TEAM_LEAD+)
- `DELETE /api/v1/criteria/{criteria_id}` - Delete criteria (Requires: TEAM_LEAD+, unused only)

### Nominations
- `GET /api/v1/nominations` - List nominations (with filters)
- `GET /api/v1/nominations/{nomination_id}` - Get nomination details
- `POST /api/v1/nominations` - Submit nomination (Requires: TEAM_LEAD+)

### Approvals
- `GET /api/v1/nominations/{nomination_id}/approvals` - List approvals for nomination
- `POST /api/v1/approvals/approve` - Approve nomination (Requires: MANAGER+)
- `POST /api/v1/approvals/reject` - Reject nomination (Requires: MANAGER+)

### Rankings
- `GET /api/v1/cycles/{cycle_id}/rankings` - Get rankings for cycle
- `POST /api/v1/cycles/{cycle_id}/rankings/compute` - Compute rankings (Requires: MANAGER+)
- `POST /api/v1/cycles/{cycle_id}/finalize` - Finalize cycle (Requires: MANAGER+)

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

JWT tokens are created with user ID, email, and role. Role-based access control (RBAC) is enforced on all mutating endpoints.

### Roles Hierarchy

- **EMPLOYEE**: Basic read access
- **TEAM_LEAD**: Can submit nominations, create cycles
- **MANAGER**: Can approve/reject nominations, compute rankings
- **HR**: Full access including all manager permissions

## Project Structure

```
awards-nomination-system/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── routes.py          # API route definitions
│   ├── auth/
│   │   ├── jwt.py                 # JWT token handling
│   │   └── rbac.py                # Role-based access control
│   ├── config.py                  # Application settings
│   ├── core/
│   │   └── errors.py              # Error handlers
│   ├── db/
│   │   ├── base.py                # Database base classes
│   │   └── session.py             # Database session management
│   ├── middleware/
│   │   └── logging.py             # Structured logging middleware
│   ├── models/
│   │   └── domain.py              # SQLAlchemy models (owned by Nageshwar)
│   ├── schemas/
│   │   └── base.py                # Pydantic schemas (owned by Nageshwar)
│   ├── services/                  # Business logic (owned by Nageshwar)
│   │   ├── approval_service.py
│   │   ├── audit.py
│   │   ├── nomination_service.py
│   │   └── ranking_service.py
│   └── main.py                    # FastAPI application entry point
├── alembic/                       # Database migrations (owned by Nageshwar)
├── scripts/
│   └── seed.py                    # Database seeding script
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # API container definition
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── SETUP.md                       # Detailed setup instructions
├── vamsi.md                       # Vamsi's responsibilities
└── nageshwar.md                   # Nageshwar's responsibilities
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: Secret key for JWT token signing (use strong random string in production)
- `JWT_ISSUER`: JWT issuer claim
- `JWT_AUDIENCE`: JWT audience claim
- `APP_ENV`: Environment (local, staging, production)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated or `*`)

## Development

**Quick Development Commands:**
```bash
./bin/dev.sh start     # Start services
./bin/dev.sh stop      # Stop services
./bin/dev.sh logs      # View logs
./bin/dev.sh shell     # Open shell in container
./bin/dev.sh status    # Check service status
```

See [`bin/README.md`](bin/README.md) for all available scripts.

### Local Development (without Docker)

1. Create virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables
   ```bash
   cp .env.example .env
   # Edit .env with local database URL
   ```

4. Run migrations
   ```bash
   alembic upgrade head
   ```

5. Run the server
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Running Tests

Comprehensive unit tests are available for all API endpoints. See [tests/README.md](tests/README.md) for details.

**Using scripts (recommended):**
```bash
# Run all tests
./bin/test.sh

# Run with coverage
./bin/test-coverage.sh

# Run specific test file
./bin/test.sh tests/test_cycles.py -v
```

**Direct Docker commands:**
```bash
# Run all tests
docker compose exec api pytest

# Run with coverage
docker compose exec api pytest --cov=app --cov-report=html

# Run specific test file
docker compose exec api pytest tests/test_cycles.py -v
```

Test coverage includes:
- All CRUD operations
- Authentication and RBAC
- Error handling
- Business logic validation
- Edge cases

## Code Ownership

This project follows a shared ownership model:

- **Nageshwar**: Owns models, schemas, services, and Alembic migrations
- **Vamsi**: Owns API routes, authentication, RBAC, middleware, Docker setup, and CI/CD

See `nageshwar.md` and `vamsi.md` for detailed responsibilities.

## Database Migrations

Migrations are managed by Alembic.

**Using scripts (recommended):**
```bash
# Create new migration
./bin/migration-create.sh "Description of changes"

# Apply migrations
./bin/migrate.sh up

# Check current version
./bin/migrate.sh current

# View history
./bin/migrate.sh history
```

**Direct Docker commands:**
```bash
docker compose exec api alembic revision --autogenerate -m "Description"
docker compose exec api alembic upgrade head
```

**Note**: Only Nageshwar should create/modify migrations. Vamsi runs migrations in CI/CD.

## Logging

The application uses structured logging with request/trace IDs. Logs are output in JSON format and include:

- Request/response metadata
- Trace IDs for request correlation
- Error details with stack traces
- Audit information

## Security Considerations

- JWT tokens expire after 30 minutes (configurable)
- Passwords/secrets should never be committed
- Use strong `JWT_SECRET` in production
- CORS origins should be restricted in production
- All mutating endpoints require authentication and appropriate roles
- Database connections use connection pooling

## Contributing

1. Coordinate with code owners before changing shared contracts (schemas, service interfaces)
2. Follow existing code patterns and structure
3. Ensure all endpoints have proper error handling
4. Include docstrings for API endpoints
5. Test changes locally before submitting

## License

[Add license information here]
