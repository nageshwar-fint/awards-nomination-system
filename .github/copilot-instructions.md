# Copilot instructions — Awards Nomination System (API)

Purpose: Give an AI coding agent the concrete, project-specific facts it needs to be productive quickly.

## Big picture
- FastAPI backend (app/) + React UI (awards-nomination-ui/). API base path: `/api/v1`.
- Core responsibilities:
  - `app/services/` — business logic (nomination cycles, criteria, nominations, rankings)
  - `app/models/` + SQLAlchemy + Alembic — domain model & migrations
  - `app/api/v1/` — HTTP endpoints that call services and convert SQLAlchemy objects to Pydantic
  - `awards-nomination-ui/src/api/*` — client-side expectations (error shape, auth header, uploads)

## Key patterns & conventions (do this, not this)
- Pydantic v2 is used. Convert DB models to schemas with: `MySchema.model_validate(db_obj)` and `model_dump()` for partial edits.
  - Example: `UserRead.model_validate(user).model_dump()` in `app/api/v1/admin.py`.
- Services raise built-in exceptions for business logic (ValueError, PermissionError). FastAPI-level handlers format consistent error JSON (see `app/core/errors.py`).
  - Do not return raw exceptions; throw AppError in endpoints when you need to control status/details.
- Authentication is JWT-based: token created with `JWTPayload.create_token(...)` (see `app/auth/jwt.py`).
  - Clients send header: `Authorization: Bearer <token>`; login/register endpoints explicitly avoid adding Authorization header on client-side.
- RBAC via dependencies in `app/auth/rbac.py`: `RequireTeamLead`, `RequireManager`, `RequireHR` and `require_any_role(...)`. Use these in endpoints, not ad-hoc checks.
- Structured logging with request/trace IDs is required. Use `structlog` context (request_id, trace_id); see `app/middleware/logging.py` to preserve `X-Request-ID` headers and include IDs in responses.
- Rate limiting is applied with `slowapi` in `app/api/v1/auth.py` (e.g., login/register). Follow existing limiter usage for endpoints that are sensitive to abuse.
- File uploads expect FormData; server validates extension/content-type and returns `{url, filename, size, content_type}` (see `app/api/v1/uploads.py`).

## Error / response shape
- Standard error response (guaranteed):
  {
    "error": { "message": "...", "type": "...", "details": {...} },
    "request_id": "..."
  }
- Validation errors from FastAPI are 422 with an array in `detail` (client code maps these to field messages).
- Frontend expects the `err.error?.message` property and treats 401 specially (client auto-logs out on 401).

## Developer workflows & commands (copy-paste)
- Full local setup (recommended):
  ./bin/setup.sh
- Common development commands:
  ./bin/dev.sh start|stop|logs|shell
  ./bin/build.sh api [--no-cache]
- Tests
  ./bin/test.sh                 # run tests
  ./bin/test-coverage.sh        # coverage
- Migrations (ownership rules below):
  ./bin/migration-create.sh "Description"
  ./bin/migrate.sh up
- Direct Docker alternatives are available in `bin/README.md` (we prefer using `bin/*` wrappers).

## Project-specific rules & ownership
- Migrations: only the model owner (see `nageshwar.md`) should create/modify migrations. After creating, review the autogen file in `alembic/versions/` before applying.
- Do not change API contracts without coordinating with API owners (routes under `app/api/v1` are consumed by the frontend).
- Use seeding for local dev: `./bin/seed.sh` (force admin credentials with env vars if needed).

## Testing hints
- Use `tests/conftest.py` fixtures — tests use an in-memory SQLite DB with a JSONB adapter; follow its approach when adding tests that touch JSON fields.
- Create JWTs in tests with `JWTPayload.create_token` or helper fixtures like `get_auth_headers()`.
- Override `get_session` using `app.dependency_overrides` (see `tests/conftest.py`).

## Where to look (quick references)
- App entrypoint & middleware: `app/main.py`, `app/middleware/logging.py`
- Config & env: `app/config.py`, `.env.example`, `docker-compose.yml`
- Authentication & RBAC: `app/auth/jwt.py`, `app/auth/rbac.py`
- Business logic: `app/services/*.py` (e.g., `nomination_service.py`)
- Error handlers: `app/core/errors.py`
- Uploads: `app/api/v1/uploads.py` and client `awards-nomination-ui/src/api/client.js`
- Scripts & common developer tasks: `bin/` and `bin/README.md`
- Tests: `tests/` and `tests/README.md`

If anything above is ambiguous or missing examples you'd like included, tell me which area to expand and I'll iterate. Thanks!