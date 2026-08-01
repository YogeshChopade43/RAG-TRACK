## Render.com Deployment Configuration

### Build Command
```
pip install -r requirements.txt
```

### Start Command
```
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (or see trial key below) | API key for OpenRouter LLM provider |
| `OPENROUTER_MODEL` | No | Default model (optional — can be overridden per-request via `X-User-OpenRouter-Model` header) |
| `ALLOWED_ORIGINS` | No | CORS origins (default: `["*"]`). For production, set to your frontend URL(s) |
| `DATABASE_URL` | No | Required if using auth features. If set, migrations run automatically on startup |
| `SECRET_KEY` | Yes (if using auth) | JWT secret for token signing |
| `DEBUG` | No | Default: `false` |
| `CHUNK_SIZE` | No | Default: `500` |
| `CHUNK_OVERLAP` | No | Default: `200` |
| `TOP_K_RETRIEVAL` | No | Default: `8` |

### Important Notes

1. **Static files**: The React frontend build is served from `frontend/dist/` via FastAPI's `StaticFiles` mount

2. **Health check**: Render should use `GET /health` as the health check endpoint

3. **Port**: The start command uses `$PORT` (Render's dynamically-assigned port) — no hardcoded port needed

4. **Trial API key verification**: The `/auth/test-api-key` endpoint validates keys via a trial LLM call through OpenRouter's chat completions endpoint

5. **Docker alternative**: If Render's native build is problematic, use the `Containerfile` in the repo root — Render supports Docker deploys natively

6. **File uploads**: Maximum upload size is 50MB by default (`MAX_UPLOAD_SIZE`)

### One-click Docker Deploy Commands

If using Docker on Render:
- **Build Command**: `echo 'Docker build'` (Render Docker builds use the Containerfile)
- **Start Command**: (not needed — uses CMD in Containerfile)
- Select "Environment" → "Docker" instead of "Python"
