#!/bin/bash
# Seed database with admin user and demo data

set -e

echo "🌱 Seeding database..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if services are running
if ! docker compose ps api | grep -q "Up"; then
    echo "⚠️  Warning: API service is not running."
    echo "💡 Starting services..."
    docker compose up -d api
    echo "⏳ Waiting for service to be ready..."
    sleep 3
fi

# Allow environment variables to be passed through
# Default values if not set
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123!}"
ADMIN_NAME="${ADMIN_NAME:-Admin User}"
SEED_ADMIN="${SEED_ADMIN:-true}"

echo ""
echo "📋 Seed Configuration:"
echo "   Admin Email: $ADMIN_EMAIL"
echo "   Admin Name: $ADMIN_NAME"
echo "   Seed Admin: $SEED_ADMIN"
if [ "$SEED_ADMIN" = "true" ]; then
    echo "   Admin Password: $ADMIN_PASSWORD"
fi
echo ""

# Run seed script
echo "🚀 Running seed script..."
docker compose exec -T api bash -c "
    export ADMIN_EMAIL=\"$ADMIN_EMAIL\"
    export ADMIN_PASSWORD=\"$ADMIN_PASSWORD\"
    export ADMIN_NAME=\"$ADMIN_NAME\"
    export SEED_ADMIN=\"$SEED_ADMIN\"
    python -m scripts.seed
"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Seed completed successfully!"
    echo ""
    if [ "$SEED_ADMIN" = "true" ]; then
        echo "📝 Admin credentials:"
        echo "   Email: $ADMIN_EMAIL"
        echo "   Password: $ADMIN_PASSWORD"
        echo ""
        echo "💡 You can now login with:"
        echo "   curl -X POST http://localhost:8000/api/v1/auth/login \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}'"
    fi
else
    echo ""
    echo "❌ Seed failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
