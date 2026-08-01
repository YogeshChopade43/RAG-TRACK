# syntax=docker/dockerfile:1

# ===== Stage 1: Build Frontend =====
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
ARG VITE_API_URL=http://localhost:8000
RUN npm run build

# ===== Stage 2: Install Python Dependencies =====
FROM python:3.11-slim AS backend-deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# ===== Stage 3: Runtime Image =====
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies + create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 1000 -m -s /bin/bash ragtrack

# Copy Python dependencies from builder stage (packages + console scripts)
COPY --from=backend-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-deps /usr/local/bin /usr/local/bin

# --- Application environment ---
# PYTHONPATH=/app/backend so that `app.main:app` resolves to backend/app/main.py
ENV PYTHONPATH=/app/backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY backend/ ./backend/

# Copy environment defaults (runtime env vars override these via compose)
COPY .env.example .env

# Copy frontend build output (served as static files by FastAPI StaticFiles)
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy alembic config for DB migrations at startup
COPY alembic.ini ./alembic.ini

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create data directories
RUN mkdir -p \
    data/raw \
    data/vector_store \
    data/parsed \
    data/embeddings \
    data/traces \
    && chown -R ragtrack:ragtrack /app

# Switch to non-root user
USER ragtrack

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
