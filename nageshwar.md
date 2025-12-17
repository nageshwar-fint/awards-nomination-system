Nageshwar – Backend & Business Logic

Scope
- Own data model (SQLAlchemy), Alembic migrations, seed data.
- Own core services: cycles, criteria, nominations, approvals, ranking/finalization, history/archive, audit-log writer.
- Define Pydantic I/O schemas for domain objects; keep stable contracts for API layer.

Requirements (tooling & libs to prefer)
- Python 3.11+, SQLAlchemy 2.x, Alembic latest, psycopg[binary].
- Pydantic v2 for schemas; pytest for tests.
- Prefer UUID primary keys; UTC timestamps; JSONB for audit payloads.
- Enforce lint/format later (ruff/black) once added.
- Lint checks are not required right now; focus on migrations/services.

Initial steps (to start)
- Initialize Alembic with base migration folder; create `db/session.py` and Base mixin.
- Draft first migration with core tables (users, teams, cycles, criteria, nominations, approvals, audit_logs).
- Sketch Pydantic domain schemas (request/response) and share interface signatures for services.
- Add a seed script stub and a minimal test for migration sanity (alembic upgrade + basic inserts).

Immediate next actions
- Lay down models/, db/session.py, Base mixin, and initial Alembic migration.
- Add seed script for roles/teams; share migration + seed steps with Vamsi.
- Draft service interfaces for nominations, approvals, ranking (pure Python, DB-backed) and share signatures.
- Add unit tests for rules: windows, role gates, uniqueness, weight sum = 1.0, scoring formula.

Shared code ownership (who does what)
- models/, alembic/: you own; Vamsi only runs migrations.
- services/: you own implementation; Vamsi wires routes to your interfaces.
- schemas/: you define domain schemas; Vamsi may extend request/response wrappers (without changing your fields).
- audit logs: you emit via service helper; Vamsi ensures middleware passes user context into services.

Hand-offs / expectations
- End Phase 1: provide models/ + first migration + seed instructions.
- Phase 2 start: provide service interfaces + Pydantic schemas; keep backward compatible.
- If a breaking change is needed, flag in advance and ship migration + schema note.

Definition of done
- Migrations run clean locally and in CI.
- Services enforce rules and are unit-tested.
- Ranking/finalization is idempotent and writes history tables.
- Audit log is called on every mutating service.
