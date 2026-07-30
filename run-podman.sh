#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

POD_NAME="ragtrack-pod"
COMPOSE_FILE="podman-compose.yml"
ENV_FILE=".env.podman"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: $COMPOSE_FILE not found in $SCRIPT_DIR" >&2
    exit 1
fi

cmd="${1:-up}"

case "$cmd" in
    up)
        echo "Starting RAG-TRACK Podman pod..."
        if ! command -v podman &>/dev/null; then
            echo "Error: podman is not installed or not in PATH" >&2
            exit 1
        fi

        if [ -f "$ENV_FILE" ]; then
            echo "Loading environment from $ENV_FILE"
            export $(grep -v '^#' "$ENV_FILE" | xargs)
        fi

        podman pod rm -f "$POD_NAME" 2>/dev/null || true
        podman compose -f "$COMPOSE_FILE" up -d --build

        echo ""
        echo "RAG-TRACK is running."
        echo "API: http://localhost:8000"
        echo "Docs: http://localhost:8000/docs"
        echo ""
        echo "View logs: podman compose -f $COMPOSE_FILE logs -f"
        echo "Stop: podman compose -f $COMPOSE_FILE down"
        ;;

    down)
        echo "Stopping RAG-TRACK Podman pod..."
        podman compose -f "$COMPOSE_FILE" down 2>/dev/null || true
        podman pod rm -f "$POD_NAME" 2>/dev/null || true
        echo "RAG-TRACK stopped."
        ;;

    restart)
        echo "Restarting RAG-TRACK Podman pod..."
        podman compose -f "$COMPOSE_FILE" down 2>/dev/null || true
        podman compose -f "$COMPOSE_FILE" up -d --build
        echo "RAG-TRACK restarted."
        ;;

    logs)
        podman compose -f "$COMPOSE_FILE" logs -f "${2:-}"
        ;;

    status)
        echo "=== Pod Status ==="
        podman pod inspect "$POD_NAME" 2>/dev/null || echo "Pod '$POD_NAME' not running"
        echo ""
        echo "=== Container Status ==="
        podman ps --filter "name=$POD_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;

    build)
        echo "Building RAG-TRACK image..."
        podman build -t ragtrack:latest -f Containerfile .
        ;;

    *)
        echo "Usage: $0 {up|down|restart|logs|status|build}"
        echo ""
        echo "Commands:"
        echo "  up        Build and start the RAG-TRACK podman pod"
        echo "  down      Stop and remove the pod and containers"
        echo "  restart   Stop, rebuild, and restart the pod"
        echo "  logs      Stream container logs (optionally filter by service name)"
        echo "  status    Show pod and container status"
        echo "  build     Build the ragtrack image without starting"
        echo ""
        echo "Environment file: .env.podman  (copy from .env.podman.example)"
        exit 1
        ;;
esac