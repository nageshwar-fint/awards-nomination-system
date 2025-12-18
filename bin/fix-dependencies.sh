#!/bin/bash
# Fix missing dependencies - installs packages from requirements.txt in running container

set -e

echo "🔧 Fixing missing dependencies..."
echo ""

# Check if container is running
if ! docker compose ps api | grep -q "Up"; then
    echo "⚠️  API container is not running. Starting it..."
    docker compose up -d api
    sleep 3
fi

echo "📦 Installing/updating packages from requirements.txt..."
docker compose exec api pip install --upgrade pip
docker compose exec api pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "🔍 Verifying key packages..."

# Check critical packages
for pkg in bcrypt slowapi; do
    if docker compose exec api pip show "$pkg" > /dev/null 2>&1; then
        VERSION=$(docker compose exec api pip show "$pkg" | grep "^Version:" | awk '{print $2}')
        echo "✅ $pkg: $VERSION"
    else
        echo "❌ $pkg: NOT INSTALLED"
    fi
done

echo ""
echo "⚠️  Note: This fix is temporary - packages will be lost when container restarts."
echo "💡 For permanent fix, rebuild container: ./bin/build.sh api --no-cache"
