# syntax=docker/dockerfile:1

FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM python:3.11-slim AS backend-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2+cpu && \
    pip install --no-cache-dir --default-timeout=300 -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /app/requirements.txt .

COPY backend/ ./backend/
COPY .env.example .env

COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p data/raw data/vector_store data/parsed data/embeddings

RUN pip install --no-cache-dir aiofiles==23.3.1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]