# One-Time Setup (Local)

## Prerequisites
- Python 3.11+ (for tooling/tests)
- Docker + Docker Compose plugin
- `psql` client (optional, for DB inspection)
- `make` (optional, for future shortcuts)

## 1) Clone and enter the project
```bash
git clone <repo-url> awards-nomination-system
cd awards-nomination-system
```

## 2) Create environment file
Create `.env` in the repo root (copy from `.env.example` when it exists). Suggested defaults for local:
```
APP_ENV=local
APP_PORT=8000
DATABASE_URL=postgresql+psycopg://app:app@db:5432/appdb
JWT_SECRET=replace_me_with_long_random
JWT_ISSUER=awards-nomination-system
JWT_AUDIENCE=awards-nomination-system
LOG_LEVEL=INFO
CORS_ORIGINS=*
IDEMPOTENCY_TTL_SECONDS=300
SEED_ON_START=true
```

## 3) Bring up local stack (Docker-first)
```bash
docker compose build
docker compose up -d
```
- Services expected: `api`, `db`.
- Check logs if anything fails: `docker compose logs -f api db`.

## 4) Run migrations (once available)
```bash
docker compose exec api alembic upgrade head
```
- Nageshwar owns migrations; consume, don’t modify if you’re not the owner.

## 5) Seed reference data (once seed script exists)
```bash
docker compose exec api python -m scripts.seed
```
- Seeds roles/teams to keep dev environments aligned.

## 6) Verify health
```bash
curl http://localhost:8000/api/v1/health
```
- Expect 200 and basic payload.

## 7) (Optional) Local venv workflow (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # when available
uvicorn app.main:app --reload --port 8000
```
- You’ll need a running Postgres and `DATABASE_URL` pointing to it.

## Ownership reminders
- `models/`, `alembic/`, core services: Nageshwar owns.
- App wiring, auth/RBAC, infra/CI/CD, Docker/compose: Vamsi owns.
- Coordinate before changing shared contracts (schemas/interfaces).

## Quick checks after setup
- `docker compose ps` shows api + db healthy.
- `alembic current` runs inside the api container without errors.
- Health endpoint returns 200.
