#!/bin/bash
set -e

echo "=== RAG-TRACK Container Entrypoint ==="

# --- Ensure data directories exist (handles fresh volumes) ---
mkdir -p /app/data/raw /app/data/vector_store /app/data/parsed /app/data/embeddings /app/data/traces

# --- Database migrations (optional, only if DATABASE_URL is configured) ---
if [ -n "${DATABASE_URL:-}" ]; then
    echo "Running database migrations..."
    python3 -m alembic upgrade head || echo "WARNING: Migrations failed — continuing anyway (non-critical tables may already exist)"
else
    echo "DATABASE_URL not set — skipping migrations"
fi

# --- Start the application ---
echo "Starting RAG-TRACK API..."
exec "$@"
