#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Load .env if it exists
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: $COMPOSE_FILE not found in $SCRIPT_DIR" >&2
    exit 1
fi

# Detect runtime
if command -v docker &>/dev/null; then
    COMPOSE="docker compose -f $COMPOSE_FILE"
    RUNTIME="docker"
elif command -v podman &>/dev/null; then
    COMPOSE="podman compose -f $COMPOSE_FILE"
    RUNTIME="podman"
else
    echo "Error: Neither docker nor podman is installed" >&2
    exit 1
fi

echo "Using $RUNTIME compose"

cmd="${1:-up}"

case "$cmd" in
    up)
        echo "Starting RAG-TRACK..."
        $COMPOSE up -d --build
        echo ""
        echo "RAG-TRACK is running."
        echo "API:     http://localhost:8000"
        echo "Docs:    http://localhost:8000/docs"
        echo "DB:      localhost:5432 (postgres:ragtrack)"
        echo ""
        echo "View logs:  $0 logs"
        echo "Stop:       $0 down"
        ;;

    down)
        echo "Stopping RAG-TRACK..."
        $COMPOSE down 2>/dev/null || true
        echo "RAG-TRACK stopped."
        ;;

    restart)
        echo "Restarting RAG-TRACK..."
        $COMPOSE down 2>/dev/null || true
        $COMPOSE up -d --build
        echo "RAG-TRACK restarted."
        ;;

    logs)
        $COMPOSE logs -f "${2:-}"
        ;;

    status)
        $COMPOSE ps
        ;;

    build)
        echo "Building RAG-TRACK image with $RUNTIME..."
        $COMPOSE build
        ;;

    migrate)
        echo "Running database migrations..."
        $COMPOSE exec api python3 -m alembic upgrade head
         ;;

    *)
        echo "Usage: $0 {up|down|restart|logs|status|build|migrate}"
        echo ""
        echo "Commands:"
        echo "  up        Build and start RAG-TRACK containers"
        echo "  down      Stop and remove all containers and networks"
        echo "  restart   Stop, rebuild, and restart containers"
        echo "  logs      Stream container logs (optionally filter by service)"
        echo "  status    Show container status"
        echo "  build     Build the ragtrack image without starting"
        echo "  migrate   Run database migrations"
        echo ""
        echo "Environment file: .env  (copy from .env.example)"
        exit 1
        ;;
esac
