<h1 align="center">RAG-TRACK</h1>

<p align="center">
  <strong>An End-to-End, Observable Retrieval-Augmented Generation (RAG) System</strong>
</p>

<p align="center">
  Built with a focus on <b>traceability, debuggability, and real-world failure analysis</b>
</p>

<p align="center">
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/issues">
    <img src="https://img.shields.io/github/issues/YogeshChopade43/RAG-TRACK" alt="issues" />
  </a>
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/network">
    <img src="https://img.shields.io/github/forks/YogeshChopade43/RAG-TRACK" alt="forks" />
  </a>
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/stargazers">
    <img src="https://img.shields.io/github/stars/YogeshChopade43/RAG-TRACK" alt="stars" />
  </a>
  <a href="https://github.com/YogeshChopade43/RAG-TRACK/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/YogeshChopade43/RAG-TRACK" alt="license" />
  </a>
</p>

<hr/>

<h2>📌 Overview</h2>

<p>
RAG-TRACK is a <b>production-oriented RAG system</b> designed to move beyond demo-level chatbots.
Instead of treating Retrieval-Augmented Generation as a black box, this project focuses on
<strong>making every step observable and inspectable</strong>.
</p>

<p>
The goal is simple: <br/>
<b>Know exactly why an answer was generated.</b>
</p>

<hr/>

<h2>❓ Why RAG-TRACK?</h2>

<p>
Most RAG applications fail silently. When an answer is wrong, it is unclear whether the issue lies in:
</p>

<ul>
  <li>Document ingestion</li>
  <li>Text cleaning pipeline</li>
  <li>Chunking strategy</li>
  <li>Embedding quality</li>
  <li>Vector retrieval</li>
  <li>Query decomposition & expansion</li>
  <li>Reranking</li>
  <li>Context assembly</li>
  <li>LLM generation</li>
</ul>

<p>
<strong>RAG-TRACK is built to expose these failure points instead of hiding them.</strong>
</p>

<hr/>

<h2>🏗️ Architecture</h2>

<pre>
User Query
   |
   v
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Query Processing Pipeline              │  │
│  │  ┌────────────────┐                             │  │
│  │  │ Query Decomp.  │──> Split complex queries    │  │
│  │  └────────────────┘                             │  │
│  │  ┌────────────────┐                             │  │
│  │  │ Multi-Query    │──> Expand for coverage      │  │
│  │  └────────────────┘                             │  │
│  │  ┌────────────────┐                             │  │
│  │  │ Query Rewrite  │──> Optimize for retrieval   │  │
│  │  └────────────────┘                             │  │
│  └──────────────────────────────────────────────────┘  │
│                         |                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Retrieval & Reranking Pipeline           │  │
│  │  ┌──────────────┐  ┌─────────────┐             │  │
│  │  │ Vector Store │─>│ Reranker    │─> Top-K     │  │
│  │  │ (FAISS)      │  │ Service     │   Chunks    │  │
│  │  └──────────────┘  └─────────────┘             │  │
│  └──────────────────────────────────────────────────┘  │
│                         |                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Generation & Observability          │  │
│  │  ┌────────────┐  ┌─────────────────────────┐   │  │
│  │  │ LLM Service │  │ Trace Storage           │   │  │
│  │  │(OpenRouter/ │─>│ (Every step logged)    │   │  │
│  │  │  Local)     │  │                         │   │  │
│  │  └────────────┘  └─────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│                         |                              │
│                    Generated Answer                     │
└─────────────────────────────────────────────────────────┘
</pre>

<p>
Each stage emits <b>structured metadata and traces</b> to support debugging and observability.
</p>

<hr/>

<h2>🛠️ Tech Stack</h2>

<h3>Backend</h3>
<ul>
  <li><b>Framework:</b> FastAPI (Python 3.11+)</li>
  <li><b>Server:</b> Uvicorn with standard workers</li>
  <li><b>Vector Database:</b> FAISS (CPU)</li>
  <li><b>Embeddings:</b> Sentence-Transformers (all-MiniLM-L6-v2)</li>
  <li><b>LLM Providers:</b> OpenRouter API / Local LLM (Ollama-compatible)</li>
  <li><b>Document Parsing:</b> pdfplumber, PyPDF, Pillow</li>
  <li><b>Rate Limiting:</b> SlowAPI</li>
  <li><b>Authentication:</b> API Key middleware</li>
  <li><b>Observability:</b> Custom trace service with storage</li>
</ul>

<h3>Frontend</h3>
<ul>
  <li><b>Framework:</b> React 19 with Vite</li>
  <li><b>Styling:</b> CSS Modules + Framer Motion animations</li>
  <li><b>Components:</b> ChatInterface, AnswerDisplay, HeroSection, PremiumFileUpload</li>
</ul>

<h3>DevOps & Quality</h3>
<ul>
  <li>Docker & Docker Compose</li>
  <li>pytest with coverage reporting</li>
  <li>Ruff (linting) & MyPy (type checking)</li>
  <li>Environment-based configuration (.env)</li>
</ul>

<hr/>

<h2>✨ Core Features</h2>

<h3>1️⃣ Document Ingestion & Parsing</h3>
<ul>
  <li>PDF and TXT file support</li>
  <li>Original files stored separately for traceability</li>
  <li>Page-aware parsing with pdfplumber</li>
  <li>No loss of source context</li>
</ul>

<h3>2️⃣ Text Cleaning Pipeline</h3>
<ul>
  <li>8-step cleaning process</li>
  <li>Page number association maintained</li>
  <li>Configurable cleaning rules</li>
</ul>

<h3>3️⃣ Chunking & Embedding</h3>
<ul>
  <li>Page-aware chunking with overlap</li>
  <li>Deterministic chunking strategy</li>
  <li>Chunk-level metadata (source, offsets, IDs)</li>
  <li>Sentence-transformers embeddings</li>
</ul>

<h3>4️⃣ Advanced Query Processing</h3>
<ul>
  <li><b>Query Decomposition:</b> Split complex multi-intent queries</li>
  <li><b>Multi-Query Expansion:</b> Generate query variants for better coverage</li>
  <li><b>Query Rewriting:</b> Optimize queries for retrieval</li>
  <li>Chunk deduplication across query variants</li>
</ul>

<h3>5️⃣ Vector Retrieval & Reranking</h3>
<ul>
  <li>FAISS-based similarity search</li>
  <li>Configurable top-k retrieval</li>
  <li><b>Reranking service</b> for improved relevance</li>
  <li>Retrieval scores exposed for inspection</li>
</ul>

<h3>6️⃣ Context Assembly & Generation</h3>
<ul>
  <li>Explicit control over chunk count</li>
  <li>Token-aware context assembly</li>
  <li>Pluggable LLM providers (OpenRouter / Local)</li>
  <li>Configurable model selection</li>
</ul>

<h3>7️⃣ Observability (Core Focus 🚨)</h3>
<ul>
  <li><b>Full query traces:</b> Every step recorded</li>
  <li>Retrieved chunks per query with scores</li>
  <li>Retrieval vs generation error separation</li>
  <li>Context sent to the LLM visible</li>
  <li>Answer grounding against sources</li>
  <li>Trace storage for post-hoc analysis</li>
</ul>

<hr/>

<h2>📂 Project Structure</h2>

<pre>
RAG-TRACK/
│
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── ingest.py     # Document ingestion endpoints
│   │   │   └── retrieve.py   # Query endpoints
│   │   ├── core/             # Core configuration & utilities
│   │   │   ├── auth.py       # API key authentication
│   │   │   ├── config.py     # Environment-based settings
│   │   │   ├── logging.py    # Structured logging
│   │   │   ├── paths.py      # Directory path management
│   │   │   └── ratelimit.py  # Rate limiting setup
│   │   ├── services/         # Business logic layer
│   │   │   ├── chunking/     # Text chunking service
│   │   │   ├── embedding/    # Embedding generation
│   │   │   ├── generation/   # LLM response generation
│   │   │   ├── generic/      # Shared utilities & parsers
│   │   │   ├── ingestion/   # Document ingestion pipeline
│   │   │   ├── llm/          # LLM service (OpenRouter/Local)
│   │   │   ├── observability/# Trace & monitoring services
│   │   │   ├── parsing/      # Document parsing service
│   │   │   ├── query/        # Query processing (decomp/rewrite/multi)
│   │   │   ├── reranking/    # Result reranking service
│   │   │   ├── retrieval/    # Vector similarity search
│   │   │   ├── text_cleaning/# Text cleaning pipeline
│   │   │   └── vector_store/ # FAISS vector store
│   │   ├── tests/            # pytest test suite
│   │   ├── traces/           # Query trace storage
│   │   └── main.py           # FastAPI application entry
│   ├── Dockerfile
│   ├── pytest.ini
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnswerDisplay/
│   │   │   ├── ChatInterface/
│   │   │   ├── HeroSection/
│   │   │   └── PremiumFileUpload/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── data/                      # Runtime data directory
│   ├── raw/                   # Original uploaded files
│   ├── parsed/                # Parsed text output
│   ├── embeddings/            # Generated embeddings
│   └── vector_store/          # FAISS index storage
│
├── .env.example               # Configuration template
├── .gitignore
├── docker-compose.yml         # Multi-container setup
├── requirements.txt           # Python dependencies
├── ruff.toml                  # Linting configuration
├── mypy.ini                   # Type checking configuration
├── LICENSE
└── README.md
</pre>

<hr/>

<h2>🚀 Getting Started</h2>

<h3>Prerequisites</h3>
<ul>
  <li>Python 3.11+</li>
  <li>Node.js 18+ (for frontend)</li>
  <li>OpenRouter API key (or local LLM setup)</li>
</ul>

<h3>Backend Setup</h3>
<pre>
# Clone the repository
git clone https://github.com/YogeshChopade43/RAG-TRACK.git
cd RAG-TRACK

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env   # Windows
# cp .env.example .env    # Linux/Mac

# Choose your LLM provider:

## Option 1: Cloud API (OpenRouter)
# Edit .env and add your OPENROUTER_API_KEY

## Option 2: Local LLM (Ollama - completely free)
# Uncomment Ollama settings in .env:
# USE_LOCAL_LLM=true
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2:1b
# Then install Ollama and pull a model:
# ollama pull llama3.2:1b

# Run the server
cd backend
python run.py
</pre>

<p>
Swagger UI available at: <code>http://localhost:8000/docs</code><br/>
ReDoc available at: <code>http://localhost:8000/redoc</code>
</p>

<h3>Frontend Setup</h3>
<pre>
cd frontend
npm install
npm run dev
</pre>

<p>
Frontend available at: <code>http://localhost:5173</code>
</p>

<h3>Docker Deployment</h3>
<pre>
# Build and run with docker-compose
docker-compose up -d

# Or build manually
docker build -f backend/Dockerfile -t rag-track .
docker run -p 8000:8000 --env-file .env rag-track
</pre>

<hr/>

<h2>⚙️ Configuration</h2>

<p>
Copy <code>.env.example</code> to <code>.env</code> and configure:
</p>

<table>
<tr><th>Category</th><th>Key</th><th>Description</th></tr>
<tr><td>App</td><td><code>APP_NAME</code></td><td>Application name</td></tr>
<tr><td>Server</td><td><code>HOST</code>, <code>PORT</code></td><td>Server bind address</td></tr>
<tr><td>CORS</td><td><code>ALLOWED_ORIGINS</code></td><td>Comma-separated allowed origins</td></tr>
<tr><td>Rate Limit</td><td><code>RATE_LIMIT_ENABLED</code></td><td>Enable/disable rate limiting</td></tr>
<tr><td>Files</td><td><code>MAX_FILE_SIZE_MB</code></td><td>Maximum upload file size</td></tr>
<tr><td>Chunking</td><td><code>CHUNK_SIZE</code>, <code>CHUNK_OVERLAP</code></td><td>Chunking parameters</td></tr>
<tr><td>Embedding</td><td><code>EMBEDDING_MODEL</code></td><td>Sentence-transformers model</td></tr>
<tr><td>LLM (Cloud)</td><td><code>OPENROUTER_API_KEY</code>, <code>LLM_MODEL</code></td><td>OpenRouter API config</td></tr>
<tr><td>LLM (Local)</td><td><code>USE_LOCAL_LLM</code>, <code>OLLAMA_BASE_URL</code>, <code>OLLAMA_MODEL</code></td><td>Ollama local LLM config</td></tr>
<tr><td>Retrieval</td><td><code>TOP_K_RETRIEVAL</code></td><td>Number of chunks to retrieve</td></tr>
<tr><td>Observability</td><td><code>TRACE_ENABLED</code></td><td>Enable query tracing</td></tr>
</table>

<hr/>

<h2>🧪 Testing</h2>

<pre>
# Run all tests with coverage
cd backend
pytest

# Run with HTML coverage report
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests
</pre>

<hr/>

<h2>📊 Code Quality</h2>

<pre>
# Linting with Ruff
ruff check backend/

# Type checking with MyPy
mypy backend/

# Format code
ruff format backend/
</pre>

<hr/>

<h2>📈 Project Status</h2>

<ul>
  <li>✅ FastAPI backend with modular architecture</li>
  <li>✅ Document ingestion (PDF, TXT)</li>
  <li>✅ Text cleaning pipeline (8-step)</li>
  <li>✅ Page-aware chunking strategy</li>
  <li>✅ Embedding generation with sentence-transformers</li>
  <li>✅ FAISS vector store integration</li>
  <li>✅ Query decomposition & multi-query expansion</li>
  <li>✅ Reranking service</li>
  <li>✅ Pluggable LLM providers (OpenRouter + Local)</li>
  <li>✅ API key authentication</li>
  <li>✅ Rate limiting middleware</li>
  <li>✅ Full observability & trace storage</li>
  <li>✅ React frontend with modern UI</li>
  <li>✅ Docker containerization</li>
  <li>🚧 Comprehensive test coverage (in progress)</li>
  <li>🚧 Evaluation metrics & failure analysis</li>
  <li>🚧 Hallucination detection signals</li>
</ul>

<hr/>

<h2>🛣️ Roadmap</h2>

<ul>
  <li>Advanced evaluation metrics (retrieval precision, grounding scores)</li>
  <li>Hallucination detection & confidence scoring</li>
  <li>Conversation memory & multi-turn dialogue</li>
  <li>Support for more document formats (DOCX, HTML, Markdown)</li>
  <li>Web UI for trace visualization & debugging</li>
  <li>Production-grade logging hooks (OpenTelemetry)</li>
  <li>Redis caching layer</li>
  <li>Database persistence for metadata</li>
  <li>Pluggable vector stores (Chroma, Pinecone, Weaviate)</li>
</ul>

<hr/>

<h2>🧠 What Makes This Different</h2>

<ul>
  <li>Not a notebook demo</li>
  <li>Not a black-box LangChain wrapper</li>
  <li>Every step is observable, traced, and debuggable</li>
  <li>Designed for debugging and inspection</li>
  <li>Built with real-world RAG failure modes in mind</li>
  <li>Production-grade architecture from day one</li>
  <li>Modular services with clear separation of concerns</li>
</ul>

<hr/>

<h2>🤝 Contributing</h2>

<p>
Contributions are welcome! Please feel free to submit a Pull Request.
</p>

<ol>
  <li>Fork the repository</li>
  <li>Create your feature branch (<code>git checkout -b feature/AmazingFeature</code>)</li>
  <li>Commit your changes (<code>git commit -m 'Add some AmazingFeature'</code>)</li>
  <li>Push to the branch (<code>git push origin feature/AmazingFeature</code>)</li>
  <li>Open a Pull Request</li>
</ol>

<hr/>

<h2>📄 License</h2>

<p>
MIT License — free to use, modify, and extend.
</p>

<hr/>

<h2>📬 Contact & Support</h2>

<ul>
  <li>GitHub Issues: <a href="https://github.com/YogeshChopade43/RAG-TRACK/issues">Report bugs or request features</a></li>
  <li>Discussions: <a href="https://github.com/YogeshChopade43/RAG-TRACK/discussions">Join the conversation</a></li>
</ul>

<hr/>

<p align="center">
  <i>
  This project is built to demonstrate system-level thinking in GenAI,
  not just prompt engineering.
  </i>
</p>
