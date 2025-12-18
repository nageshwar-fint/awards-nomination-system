#!/bin/bash
# Run database migrations

set -e

if [ "$1" = "up" ] || [ -z "$1" ]; then
    echo "⬆️  Running migrations (upgrade to head)..."
    docker compose exec api alembic upgrade head
    echo "✅ Migrations applied successfully!"
elif [ "$1" = "down" ]; then
    if [ -z "$2" ]; then
        echo "⚠️  Usage: bin/migrate.sh down <revision>"
        echo "Example: bin/migrate.sh down -1"
        exit 1
    fi
    echo "⬇️  Rolling back migrations..."
    docker compose exec api alembic downgrade "$2"
    echo "✅ Migrations rolled back successfully!"
elif [ "$1" = "current" ]; then
    echo "📋 Current migration version:"
    docker compose exec api alembic current
elif [ "$1" = "history" ]; then
    echo "📜 Migration history:"
    docker compose exec api alembic history
else
    echo "Usage: bin/migrate.sh [up|down <revision>|current|history]"
    exit 1
fi
