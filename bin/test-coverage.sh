#!/bin/bash
# Run tests with coverage report

set -e

echo "🧪 Running tests with coverage..."

# Check if running in Docker
if [ -f /.dockerenv ] || [ -n "${DOCKER_CONTAINER}" ]; then
    echo "Running tests in Docker container..."
    pytest --cov=app --cov-report=html --cov-report=term "$@"
else
    # Run tests in Docker container
    docker compose exec api pytest --cov=app --cov-report=html --cov-report=term "$@"
fi

echo ""
echo "✅ Coverage report generated!"
echo "📊 View HTML report: htmlcov/index.html"
