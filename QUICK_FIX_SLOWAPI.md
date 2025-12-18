# Quick Fix: slowapi Not Found Error

If you're seeing `ModuleNotFoundError: No module named 'slowapi'` on a new system, the container needs to be rebuilt.

## Immediate Fix

Run these commands on the system where you're getting the error:

```bash
# 1. Stop containers
docker compose down

# 2. Rebuild API container without cache (ensures all dependencies are installed)
docker compose build --no-cache api

# 3. Start services
docker compose up -d

# 4. Verify slowapi is installed
docker compose exec api pip show slowapi
```

Or use the helper script:

```bash
./bin/build.sh api --no-cache
docker compose up -d
./bin/list-packages.sh slowapi
```

## Why This Happens

- Docker caches layers, including the `pip install` layer
- If the container was built before `slowapi` was added to `requirements.txt`, it won't be installed
- Even if `requirements.txt` changes, Docker may use the cached pip install layer

## Prevention

When setting up on a **new system**, always build without cache on first build:

```bash
docker compose build --no-cache
```

The `setup.sh` script now does this automatically.

## Verification

After rebuilding, verify all dependencies:

```bash
# Check all packages
./bin/list-packages.sh --requirements

# Check specific packages
./bin/list-packages.sh slowapi
./bin/list-packages.sh bcrypt
```

You should see:
```
✅ slowapi: 0.1.9 (or similar version)
✅ bcrypt: 4.x.x (or similar version)
```
