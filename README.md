<h1 align="center">RAG-TRACK</h1>

<p align="center">
  <strong>Ask your documents. See every step.</strong><br/>
  An observable Retrieval-Augmented Generation system: every answer comes with citations and a full trace
  of how it was retrieved, ranked and checked.
</p>

<p align="center">
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/issues"><img src="https://img.shields.io/github/issues/YogeshChopade43/RAG-TRACK" alt="issues" /></a>
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/stargazers"><img src="https://img.shields.io/github/stars/YogeshChopade43/RAG-TRACK" alt="stars" /></a>
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/blob/main/LICENSE"><img src="https://img.shields.io/github/license/YogeshChopade43/RAG-TRACK" alt="license" /></a>
</p>

![RAG-TRACK landing page](assets/readme/landing.png)

## Why RAG-TRACK?

Most RAG apps fail silently. When an answer is wrong, you can't tell whether the problem was parsing, chunking,
retrieval, ranking or the model. RAG-TRACK records every stage of every question — timings, scores, the chunks
that reached the model, and each routing and safety decision — and shows it under the answer.

![An answer with its trace open](assets/readme/chat-trace.png)

## How a question is answered

```mermaid
flowchart LR
    Q[Question] --> A["Jev analysis<br/>split? rewrite? safe?"]
    A -->|unsafe| X[Blocked]
    A --> D[Decompose / rewrite / expand]
    D --> S["Hybrid search<br/>FAISS + BM25"]
    S --> R["Jev rerank<br/>probability per chunk"]
    R --> L["LLM answer<br/>(OpenRouter)"]
    L --> G["Jev guard<br/>harmful? unsupported?"]
    G --> T[Answer + sources + trace]
```

Documents are parsed page by page, cleaned, cut into overlapping chunks (~350 characters), embedded locally with
`all-MiniLM-L12-v2`, and stored in a FAISS HNSW index plus a BM25 keyword index.

### Jev: the decision model

Jev (`typesafe/jev-1.14` by TypeSafe, called through OpenRouter) never writes text. It answers yes/no
questions with a calibrated probability. RAG-TRACK uses it for every decision in the pipeline:

| Decision | Before Jev | With Jev |
|---|---|---|
| Split a multi-part question? | Keyword rules (*and / or / but / also*, more than one `?`) | `multi_part` ≥ 0.5 |
| Rewrite the question for search? | Word-count and pronoun rules | `needs_rewrite` ≥ 0.5 |
| Which chunks reach the LLM? | 600-line hand-tuned reranker (5 weighted signals) | One Jev call scores every chunk; keep the best 3, drop the rest under 0.1 |
| Is the question safe? | Regex input filter only | `jailbreak` / `harmful_request` ≥ 0.7 → blocked |
| Is the answer safe and grounded? | Not checked | `harmful_output` ≥ 0.7 → replaced; `unsupported` ≥ 0.85 → warning added |

Every score lands in the trace. If Jev is disabled or unreachable, each step falls back to the old heuristics,
so the pipeline keeps working.

![The pipeline and features, from the landing page](assets/readme/pipeline-features.png)

## Features

- **Hybrid retrieval** — FAISS vectors + BM25 keywords, fused per query, with query decomposition, rewriting and multi-query expansion.
- **Jev decisions** — routing, reranking and guardrails as typed probabilities (above).
- **Full traces** — per-stage timings, retrieval and rerank scores, the exact context sent to the model, and every Jev decision.
- **Citations** — every answer names its file and page.
- **Accounts and private documents** — JWT sign-in; each upload belongs to its owner.
- **Bring your own model** — users paste their OpenRouter key and model in the app; the key is tested before use and kept only in the browser session.
- **Privacy controls** — traces contain document text and are deleted after `TRACE_RETENTION_DAYS` (default 7).
- **Rate limiting** — per-client limits with SlowAPI.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11), Uvicorn, SQLAlchemy + Alembic, PostgreSQL |
| Retrieval | FAISS (HNSW), BM25, sentence-transformers `all-MiniLM-L12-v2` (local CPU) |
| Models | OpenRouter for answers; Jev (`typesafe/jev-1.14`) for decisions |
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS v4, shadcn/ui (Radix), React Router 7 |
| Quality | pytest, Ruff, MyPy, Vitest + Testing Library, ESLint |
| Delivery | Multi-stage Containerfile, Docker/Podman Compose, GitHub Actions, Fly.io |

The UI has a light theme (default) and a dark theme:

![Dark theme](assets/readme/landing-dark.png)

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 22+
- PostgreSQL (or use Docker Compose, which starts one)
- An [OpenRouter](https://openrouter.ai) API key — entered in the app, not in `.env`

### Run locally

```bash
git clone https://github.com/YogeshChopade43/RAG-TRACK.git
cd RAG-TRACK

python -m venv venv
source venv/bin/activate            # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # Windows: copy .env.example .env
# set SECRET_KEY and DATABASE_URL (e.g. postgresql://ragtrack:ragtrack_password@localhost:5432/ragtrack)

cd backend
python run.py                       # API on http://localhost:8000 (docs at /docs)
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                         # UI on http://localhost:5173 (API calls are proxied to :8000)
```

Then register, paste your OpenRouter key and model, upload a PDF and ask a question. The embedding model
downloads on first use.

### Run with Docker

```bash
cp .env.example .env                # set SECRET_KEY and DB_PASSWORD
docker compose up -d --build        # app + PostgreSQL; the API serves the built UI on :8000
```

Podman works the same way (`podman compose -f podman-compose.yml up -d --build`), and `make help` lists the
Makefile shortcuts (`make up`, `make logs`, `make migrate`, …).

## Configuration

Copy `.env.example` to `.env`. The main settings:

| Setting | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | — | JWT signing key (`openssl rand -hex 32`) |
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `ENVIRONMENT` | `development` | `production` enforces a real secret and database |
| `ALLOWED_ORIGINS` | localhost:8000, :5173 | CORS origins |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 350 / 100 | Chunking |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L12-v2` | Local embedding model |
| `OPENROUTER_API_KEY` | empty | Optional fallback; users normally enter their own key in the app |
| `LLM_MODEL` | `google/gemma-4-26b-a4b-it:free` | Fallback model when the user gives none |
| `JEV_ENABLED` / `JEV_MODEL` | `true` / `typesafe/jev-1.14` | Jev decisions (heuristics when off) |
| `JEV_MIN_RELEVANCE` | 0.1 | Reranked chunks below this are dropped (after the best 3) |
| `TRACE_RETENTION_DAYS` | 7 | Delete traces after N days (0 = keep forever) |
| `RATE_LIMIT_PER_MINUTE` | 30 | Requests per client per minute |
| `MAX_FILE_SIZE_MB` | 10 | Upload limit (PDF, TXT) |
| `API_KEY` | empty | Optional `X-API-Key` guard for the whole API |

> **Privacy:** to answer questions, parts of your document's text are sent to OpenRouter (the chat model you
> choose) and to TypeSafe (Jev). Traces, which include document text, are stored on the server until the
> retention period ends.

## Project structure

```text
RAG-TRACK/
├── backend/
│   ├── app/
│   │   ├── api/               # auth.py, ingest.py, retrieve.py (routes)
│   │   ├── core/              # config, auth (JWT), security, rate limiting, logging
│   │   ├── db/ + migrations/  # SQLAlchemy models, Alembic migrations
│   │   ├── evaluation/        # retrieval / generation evaluation pipeline
│   │   ├── services/
│   │   │   ├── jev.py         # all Jev calls: analysis, rewrite decisions, reranker, answer guard
│   │   │   ├── parsing/, text_cleaning/, chunking/, embedding/, ingestion/
│   │   │   ├── vector_store/  # FAISS index
│   │   │   ├── retrieval/     # hybrid search (FAISS + BM25)
│   │   │   ├── query/         # decomposition, rewrite, multi-query expansion
│   │   │   ├── generation/, llm/   # prompt + OpenRouter client
│   │   │   └── observability/ # trace storage and retention
│   │   └── main.py
│   ├── tests/                 # pytest (unit + integration)
│   └── run.py
├── frontend/
│   └── src/
│       ├── pages/             # Landing, Login, Register, App, NotFound
│       ├── components/        # landing/, app/, chat/, trace/, ui/ (shadcn)
│       ├── hooks/, lib/       # auth, chat, theme; API client, types
│       └── styles/            # theme tokens (+ WCAG contrast test)
├── assets/readme/             # README screenshots
├── Containerfile, docker-compose.yml, podman-compose.yml, Makefile
└── .github/workflows/         # CI + manual deploy
```

## Testing and quality

```bash
# Backend
cd backend
python -m pytest tests/unit -q      # unit tests
pytest -m "not slow"                # everything except slow tests
python -m ruff check . && python -m mypy app/

# Frontend
cd frontend
npm run lint && npm test && npm run build
```

The frontend tests include a WCAG AA contrast check for both themes.

## CI and deployment

- **`deploy.yml`** — on every push to `main`: backend unit tests and frontend lint, tests and build. The Fly.io
  deploy job runs only when the workflow is started by hand (Actions → *Deploy to Fly.io* → *Run workflow*).
- **`docker-publish.yml`** — manual: builds the image and pushes it to GitHub Container Registry.

## Roadmap

- Measure Jev against the heuristics on an evaluation set (retrieval precision, grounding)
- Bake the embedding model into the container image for fully offline start-up
- Multi-turn conversations
- More document formats (DOCX, HTML, Markdown)
- OpenTelemetry export for traces

## Contributing

Issues and pull requests are welcome: fork, create a branch, and open a PR against `main`.

## License

MIT — see [LICENSE](LICENSE).

<p align="center"><i>Built by Yogesh Chopade to show system-level thinking in GenAI, not just prompt engineering.</i></p>
