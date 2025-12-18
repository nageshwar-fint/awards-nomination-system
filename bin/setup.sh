#!/bin/bash
# Initial setup script for Awards Nomination System

set -e

echo "🚀 Setting up Awards Nomination System..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  Please edit .env and set JWT_SECRET and other required values"
    else
        echo "⚠️  .env.example not found. Creating basic .env file..."
        cat > .env << EOF
APP_ENV=local
APP_PORT=8000
DATABASE_URL=postgresql+psycopg://app:app@db:5432/appdb
JWT_SECRET=$(openssl rand -hex 32)
JWT_ISSUER=awards-nomination-system
JWT_AUDIENCE=awards-nomination-system
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
CORS_ORIGINS=*
IDEMPOTENCY_TTL_SECONDS=300
SEED_ON_START=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@awards-system.com
SMTP_USE_TLS=true
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1
FRONTEND_BASE_URL=http://localhost:3000
EOF
        echo "✅ .env file created with generated JWT_SECRET"
    fi
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🔨 Building Docker containers..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

echo ""
echo "📦 Running database migrations..."
docker compose exec api alembic upgrade head

echo ""
echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo "  1. Verify services are running: docker compose ps"
echo "  2. Check API health: curl http://localhost:8000/api/v1/health"
echo "  3. View API docs: http://localhost:8000/docs"
echo ""
echo "📚 Useful commands:"
echo "  - Run tests: bin/test.sh"
echo "  - View logs: docker compose logs -f api"
echo "  - Stop services: docker compose down"
echo ""
