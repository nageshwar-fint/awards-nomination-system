Vamsi – Platform, Security, AWS

Scope
- Own FastAPI app skeleton, config management, logging/observability, Docker, compose.
- Own auth (JWT/SSO-ready), RBAC middleware/dependencies, error handling, rate limiting (if added), secrets handling.
- Own CI/CD, AWS infra (ECR/ECS, RDS, IAM, CloudWatch), migration runner in pipeline.

Requirements (tooling & libs to prefer)
- Python 3.11+, FastAPI latest, Uvicorn, Pydantic v2, httpx for tests.
- Auth: PyJWT or jose-compatible lib; pass-through for future SSO.
- Logging: structlog/loguru or stdlib with JSON formatter; include trace/request id.
- Docker/compose; GitHub Actions for CI/CD; AWS CLI/Terraform/CDK (choose one) for infra as code.
- Lint checks not required yet; prioritize runnable stack and auth/RBAC wiring.

Initial steps (to start)
- Create FastAPI skeleton with `/api/v1/health` and structured logging middleware.
- Add Pydantic settings module and `.env.example` draft (or note to create) aligned with SETUP.md.
- Author Dockerfile and docker-compose with Postgres + API; ensure env wiring to `DATABASE_URL`.
- Prepare auth/RBAC scaffolding (JWT dependency and role checker) and stub routes to call Nageshwar’s service interfaces when ready.

Immediate next actions
- Scaffold FastAPI with /api/v1 health; structured logging middleware.
- Pydantic settings with env layering; sample .env template.
- Dockerfile + docker-compose (API + Postgres) to run locally with Alembic.
- Wire routes to Nageshwar’s service interfaces; enforce auth/RBAC on protected endpoints.

Shared code ownership (who does what)
- models/, alembic/: Nageshwar owns; you run migrations, don’t edit.
- services/: Nageshwar owns logic; you consume via interfaces and surface via routes.
- schemas/: Nageshwar defines domain fields; you may wrap/compose for transport (errors, pagination) without altering domain contracts.
- audit context: you ensure request user/role is passed into service calls so audit logs are accurate.

Hand-offs / expectations
- After initial migration/seed: ensure compose brings up DB + API, Alembic runs.
- On new endpoints: coordinate on interface signatures before wiring; avoid breaking schema fields.
- In CI/CD: add migration step before deploy; share pipeline variables and env templates.

Definition of done
- Local `docker compose up` runs API + Postgres + applies migrations.
- Auth/RBAC enforced on all mutating routes; consistent error shape.
- Logs structured with trace/request id; health/readiness endpoints exposed.
- CI/CD builds, tests, pushes image, and runs migrations pre-deploy; AWS configs documented.
