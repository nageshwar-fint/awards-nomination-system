#!/bin/bash
# Run tests for the Awards Nomination System

set -e

echo "🧪 Running tests..."

# Check if running in Docker
if [ -f /.dockerenv ] || [ -n "${DOCKER_CONTAINER}" ]; then
    echo "Running tests in Docker container..."
    pytest "$@"
else
    # Run tests in Docker container
    docker compose exec api pytest "$@"
fi

echo "✅ Tests completed!"
