#!/bin/bash
# Install/update requirements in running container (quick fix)

set -e

echo "📦 Installing requirements in running API container..."

# Check if container is running
if ! docker compose ps api | grep -q "Up"; then
    echo "⚠️  API container is not running. Starting it..."
    docker compose up -d api
    sleep 3
fi

echo "Installing from requirements.txt..."
docker compose exec api pip install --upgrade pip
docker compose exec api pip install -r requirements.txt

echo ""
echo "✅ Requirements installed!"
echo ""
echo "⚠️  Note: This is temporary - requirements will be lost when container restarts."
echo "💡 For permanent installation, rebuild the container: ./bin/build.sh api --no-cache"
