# Database Seeding Guide

Guide for seeding the database with initial data, including admin users.

## Running the Seed Script

### Using Docker (Recommended)

```bash
# Run seed script
docker compose exec api python -m scripts.seed
```

### Direct Python Execution

```bash
# Set environment variables first
export DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/appdb"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="Admin123!"

# Run seed
python -m scripts.seed
```

## Admin User Seeding

The seed script creates an admin user with **HR role** by default.

### Default Admin Credentials

- **Email**: `admin@example.com`
- **Password**: `Admin123!`
- **Role**: `HR`
- **Name**: `Admin User`

### Customizing Admin User

Set environment variables before running the seed script:

```bash
export ADMIN_EMAIL="your-admin@example.com"
export ADMIN_PASSWORD="YourSecurePass123!"
export ADMIN_NAME="Your Admin Name"
docker compose exec api python -m scripts.seed
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_EMAIL` | `admin@example.com` | Admin user email address |
| `ADMIN_PASSWORD` | `Admin123!` | Admin user password (must meet strength requirements) |
| `ADMIN_NAME` | `Admin User` | Admin user display name |
| `SEED_ADMIN` | `true` | Set to `false` to skip admin creation |

### Disabling Admin Seed

To skip admin user creation:

```bash
export SEED_ADMIN=false
docker compose exec api python -m scripts.seed
```

## Security Questions

The admin user is created with default security questions for password reset:

1. **Question**: "What is your favorite color?"
   - **Answer**: "blue"

2. **Question**: "What city were you born in?"
   - **Answer**: "default"

⚠️ **Important**: Change these security questions after first login using the password reset flow if needed.

## Demo Data

The seed script also creates demo data (team and users) if the database is empty:

- **Team**: "Demo Team"
- **Users**:
  - Manager: `manager@example.com` (MANAGER role)
  - Team Lead: `lead@example.com` (TEAM_LEAD role)

**Note**: Demo users don't have passwords. They need to register using the registration endpoint to set passwords.

## First Login

After seeding, you can login with the admin user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "...",
    "name": "Admin User",
    "email": "admin@example.com",
    "role": "HR",
    "status": "ACTIVE",
    ...
  }
}
```

## Using the Admin Token

After login, use the token to access admin endpoints:

```bash
TOKEN="your-access-token-here"

# List all users
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN"

# Update a user's role
curl -X PATCH http://localhost:8000/api/v1/admin/users/{user_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "MANAGER"}'
```

## Seed Behavior

1. **Idempotent**: Running the seed script multiple times won't create duplicate admin users
2. **Admin Check**: If admin user with the specified email already exists, it skips creation
3. **Demo Data**: Only creates demo data if database is empty (or only contains the admin user)

## Troubleshooting

### Admin Already Exists

If you see "Admin user already exists", the admin was already seeded. You can:
- Use existing credentials to login
- Delete the user via admin API and re-seed
- Use different email via `ADMIN_EMAIL` environment variable

### Password Doesn't Meet Requirements

Admin password must meet these requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

Default password `Admin123!` meets all requirements.

### Can't Login After Seed

1. Verify the user was created:
   ```bash
   docker compose exec api python -c "
   from app.db.session import get_session
   from app.models import User
   session = next(get_session())
   admin = session.query(User).filter(User.email == 'admin@example.com').first()
   print(f'Admin exists: {admin is not None}')
   print(f'Has password: {admin.password_hash is not None if admin else False}')
   "
   ```

2. Check password hash was created correctly
3. Ensure you're using the correct email and password

## Production Considerations

⚠️ **Never use default credentials in production!**

For production:
1. Set strong, unique `ADMIN_PASSWORD`
2. Use a production email domain for `ADMIN_EMAIL`
3. Consider disabling demo data seeding
4. Change security questions after first login
5. Rotate passwords regularly

Example production seed:
```bash
export ADMIN_EMAIL="admin@yourcompany.com"
export ADMIN_PASSWORD="$(openssl rand -base64 32 | tr -d /=+ | cut -c1-16)!"
export ADMIN_NAME="System Administrator"
export SEED_ADMIN=true
python -m scripts.seed
```
