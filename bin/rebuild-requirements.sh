#!/bin/bash
# Rebuild Docker container when requirements.txt changes
# This script ensures new dependencies are installed by forcing a rebuild
# of the requirements installation layer

set -e

SERVICE="${1:-api}"

echo "🔍 Checking if requirements.txt has changed..."

# Calculate hash of current requirements.txt
CURRENT_HASH=$(shasum -a 256 requirements.txt 2>/dev/null || sha256sum requirements.txt 2>/dev/null | cut -d' ' -f1)

# Store hash in a file
HASH_FILE=".requirements_hash"
OLD_HASH=""
if [ -f "$HASH_FILE" ]; then
    OLD_HASH=$(cat "$HASH_FILE")
fi

# Check if requirements have changed or hash file doesn't exist
if [ "$CURRENT_HASH" != "$OLD_HASH" ] || [ ! -f "$HASH_FILE" ]; then
    echo "📦 requirements.txt has changed (or first build)"
    echo "🔨 Rebuilding $SERVICE container to install new dependencies..."
    
    # Rebuild the specific service
    docker compose build --no-cache "$SERVICE"
    
    # Save new hash
    echo "$CURRENT_HASH" > "$HASH_FILE"
    echo "✅ Hash saved: $CURRENT_HASH"
else
    echo "✅ requirements.txt unchanged, no rebuild needed"
    echo "💡 To force rebuild: ./bin/build.sh $SERVICE --no-cache"
fi

echo ""
echo "🔍 Verifying critical packages..."
docker compose run --rm "$SERVICE" pip list 2>/dev/null | grep -E "slowapi|bcrypt" || echo "⚠️  Warning: Some packages not found. Try: ./bin/build.sh $SERVICE --no-cache"
