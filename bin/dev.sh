#!/bin/bash
# Development helper script - common development tasks

set -e

COMMAND="${1:-help}"

case "$COMMAND" in
    start)
        echo "🚀 Starting development environment..."
        docker compose up -d
        echo "✅ Services started!"
        echo "📋 View logs: docker compose logs -f"
        ;;
    
    stop)
        echo "🛑 Stopping development environment..."
        docker compose down
        echo "✅ Services stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting development environment..."
        docker compose restart
        echo "✅ Services restarted!"
        ;;
    
    logs)
        SERVICE="${2:-api}"
        echo "📋 Viewing logs for: $SERVICE"
        docker compose logs -f "$SERVICE"
        ;;
    
    shell)
        echo "🐚 Opening shell in API container..."
        docker compose exec api /bin/bash
        ;;
    
    db-shell)
        echo "🐚 Opening PostgreSQL shell..."
        docker compose exec db psql -U app -d appdb
        ;;
    
    clean)
        echo "🧹 Cleaning up Docker resources..."
        docker compose down -v
        echo "✅ Cleanup completed!"
        ;;
    
    status)
        echo "📊 Service status:"
        docker compose ps
        echo ""
        echo "🔍 API Health:"
        curl -s http://localhost:8000/api/v1/health | jq . || echo "API not responding"
        ;;
    
    packages)
        echo "📦 Listing installed packages..."
        docker compose exec api pip list
        ;;
    
    check-packages)
        echo "🔍 Checking packages from requirements.txt..."
        if [ -n "$2" ]; then
            docker compose exec api pip show "$2" || echo "❌ Package '$2' is not installed"
        else
            echo "Usage: bin/dev.sh check-packages <package-name>"
            echo "Example: bin/dev.sh check-packages bcrypt"
        fi
        ;;
    
    help|--help|-h)
        echo "Development helper script"
        echo ""
        echo "Usage: bin/dev.sh <command>"
        echo ""
        echo "Commands:"
        echo "  start          - Start all services"
        echo "  stop           - Stop all services"
        echo "  restart        - Restart all services"
        echo "  logs           - View logs (optionally specify service: api, db)"
        echo "  shell          - Open shell in API container"
        echo "  db-shell       - Open PostgreSQL shell"
        echo "  clean          - Stop services and remove volumes"
        echo "  status         - Show service status and health"
        echo "  packages       - List all installed Python packages"
        echo "  check-packages <name> - Check if specific package is installed"
        echo "  help           - Show this help message"
        echo ""
        echo "See also: bin/list-packages.sh for more package listing options"
        ;;
    
    *)
        echo "❌ Unknown command: $COMMAND"
        echo "Run 'bin/dev.sh help' for usage"
        exit 1
        ;;
esac
