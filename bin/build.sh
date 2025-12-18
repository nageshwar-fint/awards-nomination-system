#!/bin/bash
# Build Docker containers

set -e

SERVICE="${1:-api}"
NO_CACHE="${2:-false}"

echo "🔨 Building Docker container: $SERVICE"

BUILD_ARGS=""
if [ "$1" = "--no-cache" ] || [ "$2" = "--no-cache" ]; then
    BUILD_ARGS="--no-cache"
    SERVICE="${1}"
    if [ "$SERVICE" = "--no-cache" ]; then
        SERVICE="api"
    fi
    echo "⚠️  Building without cache (this will take longer but ensures fresh dependencies)"
fi

if [ "$SERVICE" = "all" ]; then
    echo "Building all services..."
    docker compose build $BUILD_ARGS
else
    docker compose build $BUILD_ARGS "$SERVICE"
fi

echo ""
echo "✅ Build completed!"
echo ""

# Verify requirements are installed (for API service)
if [ "$SERVICE" = "api" ] || [ "$SERVICE" = "all" ]; then
    echo "🔍 Verifying requirements installation..."
    if docker compose run --rm api pip list | grep -q "bcrypt"; then
        echo "✅ bcrypt installed"
    else
        echo "⚠️  Warning: bcrypt not found (may need to rebuild with --no-cache)"
    fi
    
    if docker compose run --rm api pip list | grep -q "slowapi"; then
        echo "✅ slowapi installed"
    else
        echo "⚠️  Warning: slowapi not found (may need to rebuild with --no-cache)"
    fi
fi

echo ""
echo "💡 Start services with: docker compose up -d"
echo "💡 To rebuild without cache: ./bin/build.sh $SERVICE --no-cache"
