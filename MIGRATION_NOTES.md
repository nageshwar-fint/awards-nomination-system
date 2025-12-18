# Database Migration Notes

## Authentication Implementation Migration

This document describes the database changes needed for the authentication implementation.

### Changes Required

1. **Add `password_hash` column to `users` table**
   - Column: `password_hash` (VARCHAR(255), NULLABLE)
   - Existing users will have NULL password_hash (they can't login until password is set)
   - New registrations will require password_hash

2. **Create `security_questions` table**
   - Columns:
     - `id` (UUID, PRIMARY KEY)
     - `user_id` (UUID, FOREIGN KEY to users.id, NOT NULL)
     - `question_text` (VARCHAR(500), NOT NULL)
     - `answer_hash` (VARCHAR(255), NOT NULL) - Hashed answer using bcrypt
     - `question_order` (INTEGER, NOT NULL) - Order of question (1, 2, 3, etc.)
     - `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
     - `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
   - Indexes:
     - Index on `user_id`
     - Unique constraint on (`user_id`, `question_text`) - Prevent duplicate questions per user
   - Foreign key constraint on `user_id` referencing `users.id`
   - Cascade delete when user is deleted

3. **Create `password_reset_tokens` table** (optional, kept for future use)
   - Columns:
     - `id` (UUID, PRIMARY KEY)
     - `user_id` (UUID, FOREIGN KEY to users.id, NOT NULL)
     - `token_hash` (VARCHAR(255), UNIQUE, NOT NULL)
     - `expires_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
     - `used_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)
     - `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
     - `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
   - Indexes:
     - Index on `token_hash`
     - Index on `user_id`
   - Foreign key constraint on `user_id` referencing `users.id`
   - Cascade delete when user is deleted

### Alembic Migration Command

After implementing the changes in models, run:

```bash
# Generate migration
docker compose exec api alembic revision --autogenerate -m "Add authentication password_hash and password_reset_tokens"

# Review the generated migration file
# Then apply it
docker compose exec api alembic upgrade head
```

### Migration SQL (Manual Reference)

If creating migration manually:

```sql
-- Add password_hash to users table
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);

-- Create security_questions table
CREATE TABLE security_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    question_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_question UNIQUE (user_id, question_text)
);

-- Create indexes for security_questions
CREATE INDEX ix_security_questions_user_id ON security_questions(user_id);

-- Create password_reset_tokens table (optional, kept for future use)
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for password_reset_tokens
CREATE INDEX ix_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens(user_id);
```

### Notes

- `password_hash` is nullable to allow existing users to exist without passwords
- Existing users cannot login until they reset their password or admin sets their password
- Security questions are required during registration (minimum 2, maximum 5)
- Answers are hashed using bcrypt (same as passwords) for security
- Answers are normalized (lowercase, trimmed) before hashing for consistency
- Duplicate questions are not allowed per user
- Password reset uses security questions instead of email tokens
