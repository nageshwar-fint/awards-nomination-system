# Migration Steps for Authentication Changes

This guide walks you through running the database migrations for the authentication implementation.

## Prerequisites

1. **Docker containers must be running:**
   ```bash
   docker compose up -d
   ```

2. **Verify containers are healthy:**
   ```bash
   docker compose ps
   ```

## Step 1: Generate Migration

Generate a new Alembic migration that will detect the new fields and tables:

```bash
docker compose exec api alembic revision --autogenerate -m "Add authentication password_hash and security_questions"
```

This will create a new migration file in `alembic/versions/` (e.g., `0003_add_authentication_password_hash_and_security_questions.py`).

## Step 2: Review the Generated Migration

**IMPORTANT:** Always review the generated migration before applying it!

Check the generated migration file:
```bash
# View the latest migration file
ls -lt alembic/versions/ | head -1
```

Or view it in your editor. The migration should include:
- Adding `password_hash` column to `users` table (nullable)
- Creating `security_questions` table
- Creating `password_reset_tokens` table (optional, if you want to keep it)
- Appropriate indexes and foreign keys

## Step 3: Apply the Migration

Once you've reviewed and are satisfied with the migration:

```bash
docker compose exec api alembic upgrade head
```

This will apply all pending migrations.

## Step 4: Verify Migration Success

Check that the migration was applied successfully:

```bash
# Check current migration version
docker compose exec api alembic current

# Check migration history
docker compose exec api alembic history

# Verify tables exist (optional - using psql)
docker compose exec db psql -U app -d appdb -c "\dt"
```

You should see:
- `users` table with `password_hash` column
- `security_questions` table
- `password_reset_tokens` table

## Troubleshooting

### Migration Fails with "Table already exists" Error

If you get errors about tables/columns already existing:
1. Check if you've already run migrations manually
2. Check current database state:
   ```bash
   docker compose exec db psql -U app -d appdb -c "\d users"
   docker compose exec db psql -U app -d appdb -c "\d security_questions"
   ```

### Migration Generation Shows No Changes

If `alembic revision --autogenerate` shows no changes:
1. Ensure models are imported correctly
2. Check that `alembic/env.py` imports all models
3. Verify Docker container has latest code:
   ```bash
   docker compose restart api
   ```

### Rollback Migration (if needed)

If you need to rollback:
```bash
# Rollback one migration
docker compose exec api alembic downgrade -1

# Rollback to specific version
docker compose exec api alembic downgrade <revision_id>
```

## Manual SQL (Alternative)

If you prefer to run SQL manually instead of using Alembic, see `MIGRATION_NOTES.md` for the SQL statements.

**Note:** Manual SQL should only be used if Alembic migrations are not available or you need custom changes.

## Quick Commands Summary

```bash
# 1. Start containers (if not running)
docker compose up -d

# 2. Generate migration
docker compose exec api alembic revision --autogenerate -m "Add authentication password_hash and security_questions"

# 3. Review the generated file in alembic/versions/

# 4. Apply migration
docker compose exec api alembic upgrade head

# 5. Verify
docker compose exec api alembic current
```

## Next Steps After Migration

1. **Test registration endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test User",
       "email": "test@example.com",
       "password": "TestPass123!",
       "security_questions": [
         {"question_text": "What is your favorite color?", "answer": "Blue"},
         {"question_text": "What city were you born in?", "answer": "New York"}
       ]
     }'
   ```

2. **Test login:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "TestPass123!"
     }'
   ```
