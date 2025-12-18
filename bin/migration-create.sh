#!/bin/bash
# Create a new database migration

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Migration message is required"
    echo "Usage: bin/migration-create.sh 'Description of the migration'"
    echo "Example: bin/migration-create.sh 'Add user authentication fields'"
    exit 1
fi

MESSAGE="$1"

echo "📝 Creating new migration: $MESSAGE"

docker compose exec api alembic revision --autogenerate -m "$MESSAGE"

echo "✅ Migration created successfully!"
echo "📋 Review the generated migration file in alembic/versions/ before applying"
