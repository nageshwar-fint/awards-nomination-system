# Setting Up on a New System

This guide helps you set up the Awards Nomination System on a fresh machine.

## Prerequisites

- Docker & Docker Compose installed
- Git installed

## Quick Setup

```bash
# 1. Clone the repository
git clone <repo-url> awards-nomination-system
cd awards-nomination-system

# 2. Run setup script (builds containers and installs dependencies)
./bin/setup.sh

# 3. Verify everything is working
curl http://localhost:8000/api/v1/health
```

## Manual Setup

If you prefer manual setup:

```bash
# 1. Clone repository
git clone <repo-url> awards-nomination-system
cd awards-nomination-system

# 2. Create .env file
cp .env.example .env
# Edit .env and set JWT_SECRET (generate with: openssl rand -hex 32)

# 3. Build containers (IMPORTANT: Use --no-cache on first build)
docker compose build --no-cache

# 4. Start services
docker compose up -d

# 5. Run migrations
docker compose exec api alembic upgrade head

# 6. Verify dependencies are installed
./bin/list-packages.sh --requirements
```

## Verifying Installation

After setup, verify all dependencies are installed:

```bash
# Check all packages from requirements.txt
./bin/list-packages.sh --requirements

# Specifically check slowapi and bcrypt
./bin/list-packages.sh slowapi
./bin/list-packages.sh bcrypt
```

You should see:
- ✅ slowapi: [version]
- ✅ bcrypt: [version]

## If Dependencies Are Missing

If you see "slowapi not found" or "bcrypt not found" errors:

### Option 1: Rebuild Container (Recommended)

```bash
# Stop containers
docker compose down

# Rebuild without cache
docker compose build --no-cache api

# Start services
docker compose up -d
```

### Option 2: Quick Fix in Running Container (Temporary)

```bash
# Install missing dependencies
./bin/fix-dependencies.sh

# Or manually
docker compose exec api pip install slowapi>=0.1.9 bcrypt>=4.0.0
```

⚠️ **Note**: Option 2 is temporary - dependencies will be lost when container restarts. Use Option 1 for permanent fix.

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'slowapi'"

**Cause**: Container was built before slowapi was added to requirements.txt, or Docker cache was used.

**Solution**:
```bash
# Rebuild without cache
docker compose build --no-cache api
docker compose up -d api
```

### Error: "ModuleNotFoundError: No module named 'bcrypt'"

**Cause**: Same as above - container needs to be rebuilt.

**Solution**: Same as above - rebuild without cache.

### Verification Script

Run this to check if everything is set up correctly:

```bash
#!/bin/bash
echo "Checking dependencies..."
./bin/list-packages.sh --requirements

echo ""
echo "Checking API health..."
curl -s http://localhost:8000/api/v1/health | jq . || echo "API not responding"

echo ""
echo "Checking container status..."
docker compose ps
```

## Important Notes

1. **Always use `--no-cache` on first build** to ensure all dependencies are installed
2. **Check requirements.txt** - make sure slowapi and bcrypt are listed
3. **Rebuild if requirements.txt changes** - Docker caches pip install layers
4. **Verify after setup** - use `./bin/list-packages.sh --requirements` to check

## Development Workflow

After initial setup:

```bash
# Start services
./bin/dev.sh start

# Run tests
./bin/test.sh

# View logs
./bin/dev.sh logs

# Stop services
./bin/dev.sh stop
```

## Next Steps

1. ✅ Verify dependencies: `./bin/list-packages.sh --requirements`
2. ✅ Check API health: `curl http://localhost:8000/api/v1/health`
3. ✅ View API docs: http://localhost:8000/docs
4. ✅ Run tests: `./bin/test.sh`
