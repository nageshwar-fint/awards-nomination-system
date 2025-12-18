#!/bin/bash
# List installed Python packages in the API container

set -e

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "List installed Python packages in the API container"
    echo ""
    echo "Usage: bin/list-packages.sh [options]"
    echo ""
    echo "Options:"
    echo "  --requirements  Show only packages from requirements.txt"
    echo "  --format json   Output in JSON format"
    echo "  <package-name>  Check if specific package is installed"
    exit 0
fi

if [ "$1" = "--requirements" ]; then
    echo "📦 Checking packages from requirements.txt..."
    echo ""
    
    # Check if container is running
    if ! docker compose ps api | grep -q "Up"; then
        echo "⚠️  API container is not running. Starting it..."
        docker compose up -d api
        sleep 2
    fi
    
    # List packages from requirements.txt
    MISSING_COUNT=0
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]]; then
            continue
        fi
        
        # Extract package name (remove version constraints and brackets)
        package_name=$(echo "$line" | sed 's/[>=<!=].*//' | sed 's/\[.*\]//' | xargs)
        
        if [ -n "$package_name" ]; then
            # Check if package is installed
            installed=$(docker compose exec -T api pip show "$package_name" 2>/dev/null | grep "^Version:" | awk '{print $2}' || echo "")
            if [ -n "$installed" ]; then
                echo "✅ $package_name: $installed"
            else
                echo "❌ $package_name: NOT INSTALLED"
                MISSING_COUNT=$((MISSING_COUNT + 1))
            fi
        fi
    done < requirements.txt
    
    echo ""
    if [ $MISSING_COUNT -gt 0 ]; then
        echo "⚠️  $MISSING_COUNT package(s) missing!"
        echo "💡 Run: ./bin/fix-dependencies.sh (temporary fix)"
        echo "💡 Or: ./bin/build.sh api --no-cache (permanent fix)"
    else
        echo "✅ All packages from requirements.txt are installed!"
    fi
    
elif [ -n "$1" ] && [ "$1" != "--format" ]; then
    # Check specific package
    PACKAGE="$1"
    echo "🔍 Checking package: $PACKAGE"
    
    if ! docker compose ps api | grep -q "Up"; then
        echo "⚠️  API container is not running. Starting it..."
        docker compose up -d api
        sleep 2
    fi
    
    docker compose exec api pip show "$PACKAGE" || echo "❌ Package '$PACKAGE' is not installed"
    
elif [ "$1" = "--format" ] && [ "$2" = "json" ]; then
    # JSON format
    if ! docker compose ps api | grep -q "Up"; then
        echo "⚠️  API container is not running. Starting it..."
        docker compose up -d api
        sleep 2
    fi
    
    docker compose exec api pip list --format=json
    
else
    # List all packages
    echo "📦 Installed Python packages in API container:"
    echo ""
    
    if ! docker compose ps api | grep -q "Up"; then
        echo "⚠️  API container is not running. Starting it..."
        docker compose up -d api
        sleep 2
    fi
    
    docker compose exec api pip list
fi
