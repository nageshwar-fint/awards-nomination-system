#!/bin/bash
# Build Docker containers

set -e

SERVICE="${1:-api}"

echo "🔨 Building Docker container: $SERVICE"

if [ "$SERVICE" = "all" ]; then
    echo "Building all services..."
    docker compose build
else
    docker compose build "$SERVICE"
fi

echo "✅ Build completed!"
echo "💡 Start services with: docker compose up -d"
