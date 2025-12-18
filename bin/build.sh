#!/bin/bash
# Build Docker containers

set -e

SERVICE="${1:-api}"
NO_CACHE_FLAG=false

# Parse arguments
if [ "$1" = "--no-cache" ]; then
    NO_CACHE_FLAG=true
    SERVICE="${2:-api}"
elif [ "$2" = "--no-cache" ]; then
    NO_CACHE_FLAG=true
fi

echo "🔨 Building Docker container: $SERVICE"

BUILD_ARGS=""
if [ "$NO_CACHE_FLAG" = "true" ]; then
    BUILD_ARGS="--no-cache"
    echo "⚠️  Building without cache (this will take longer but ensures fresh dependencies)"
fi

# If building API and not using --no-cache, check if requirements changed
if [ "$SERVICE" = "api" ] && [ "$NO_CACHE_FLAG" = "false" ] && [ "$SERVICE" != "all" ]; then
    HASH_FILE=".requirements_hash"
    if [ -f "$HASH_FILE" ]; then
        CURRENT_HASH=$(shasum -a 256 requirements.txt 2>/dev/null || sha256sum requirements.txt 2>/dev/null | cut -d' ' -f1)
        OLD_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
        if [ "$CURRENT_HASH" != "$OLD_HASH" ]; then
            echo "⚠️  requirements.txt has changed since last build"
            echo "💡 Rebuilding requirements layer to ensure new packages are installed..."
            BUILD_ARGS="--no-cache"
        fi
    else
        echo "💡 First build detected - building without cache to ensure all dependencies"
        BUILD_ARGS="--no-cache"
    fi
fi

if [ "$SERVICE" = "all" ]; then
    echo "Building all services..."
    docker compose build $BUILD_ARGS
else
    docker compose build $BUILD_ARGS "$SERVICE"
fi

# Save requirements hash after successful build
if [ "$SERVICE" = "api" ] || [ "$SERVICE" = "all" ]; then
    CURRENT_HASH=$(shasum -a 256 requirements.txt 2>/dev/null || sha256sum requirements.txt 2>/dev/null | cut -d' ' -f1)
    echo "$CURRENT_HASH" > .requirements_hash
fi

echo ""
echo "✅ Build completed!"
echo ""

# Verify requirements are installed (for API service)
if [ "$SERVICE" = "api" ] || [ "$SERVICE" = "all" ]; then
    echo "🔍 Verifying critical packages..."
    
    # Check for recently added packages
    MISSING=0
    for pkg in bcrypt slowapi; do
        if docker compose run --rm api pip list 2>/dev/null | grep -qi "^$pkg "; then
            VERSION=$(docker compose run --rm api pip show $pkg 2>/dev/null | grep "^Version:" | cut -d' ' -f2 || echo "unknown")
            echo "✅ $pkg: $VERSION"
        else
            echo "❌ $pkg: NOT FOUND"
            MISSING=$((MISSING + 1))
        fi
    done
    
    if [ $MISSING -gt 0 ]; then
        echo ""
        echo "⚠️  Some packages are missing!"
        echo "💡 Rebuild with: ./bin/build.sh $SERVICE --no-cache"
    fi
fi

echo ""
echo "💡 Start services with: docker compose up -d"
echo "💡 To force rebuild without cache: ./bin/build.sh $SERVICE --no-cache"
