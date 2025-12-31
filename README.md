<h1 align="center">RAG-TRACK</h1>

<p align="center">
  <strong>An End-to-End, Observable Retrieval-Augmented Generation (RAG) System</strong>
</p>

<p align="center">
  Built with a focus on <b>traceability, debuggability, and real-world failure analysis</b>
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
  <li>Chunking strategy</li>
  <li>Embedding quality</li>
  <li>Vector retrieval</li>
  <li>Reranking</li>
  <li>Context assembly</li>
  <li>LLM generation</li>
</ul>

<p>
<strong>RAG-TRACK is built to expose these failure points instead of hiding them.</strong>
</p>

<hr/>

<h2>🏗️ High-Level Architecture</h2>

<pre>
User Query
   |
   v
FastAPI Backend
   |
   |-- Retriever (Vector DB)
   |      -> Retrieved Chunks + Scores
   |
   |-- (Planned) Reranker
   |      -> Reranked Context
   |
   |-- Context Assembler
   |      -> Final Prompt
   |
   `-- LLM
          -> Generated Answer
</pre>

<p>
Each stage emits <b>structured metadata</b> to support debugging and observability.
</p>

<hr/>

<h2>🛠️ Tech Stack</h2>

<h3>Backend</h3>
<ul>
  <li>FastAPI</li>
  <li>Python</li>
  <li>Vector Database (pluggable)</li>
  <li>Embedding Models (pluggable)</li>
  <li>Swagger / OpenAPI</li>
  <li>CORS-enabled APIs</li>
</ul>

<h3>Frontend</h3>
<ul>
  <li>React (minimal UI, functionality-first)</li>
</ul>

<hr/>

<h2>✨ Core Features</h2>

<h3>1️⃣ Raw Document Ingestion</h3>
<ul>
  <li>Original files stored separately</li>
  <li>No loss of source context</li>
</ul>

<h3>2️⃣ Chunking & Embedding</h3>
<ul>
  <li>Deterministic chunking</li>
  <li>Chunk-level metadata (source, offsets, IDs)</li>
</ul>

<h3>3️⃣ Vector Retrieval</h3>
<ul>
  <li>Similarity-based retrieval</li>
  <li>Retrieval scores exposed for inspection</li>
</ul>

<h3>4️⃣ Context Assembly</h3>
<ul>
  <li>Explicit control over chunk count</li>
  <li>Ordering and token limits</li>
</ul>

<h3>5️⃣ Observability (Core Focus 🚨)</h3>
<ul>
  <li>Retrieved chunks per query</li>
  <li>Retrieval vs generation error separation</li>
  <li>Context sent to the LLM</li>
  <li>Answer grounding against sources</li>
</ul>

<hr/>

<h2>📂 Project Structure</h2>

<pre>
RAG-TRACK/
│
├── backend/
│   ├── app/
│   ├── api/
│   ├── services/
│   ├── ingestion/
│   ├── retrieval/
│   └── main.py
│
├── frontend/
│   ├── src/
│   └── public/
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── OBSERVABILITY_PLAN.md
│
├── README.md
└── LICENSE
</pre>

<hr/>

<h2>🚀 Running Locally</h2>

<h3>Backend</h3>
<pre>
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
</pre>

<p>
Swagger UI available at:
<code>http://localhost:8000/docs</code>
</p>

<h3>Frontend</h3>
<pre>
cd frontend
npm install
npm start
</pre>

<hr/>

<h2>📊 Project Status</h2>

<ul>
  <li>✅ FastAPI backend scaffold</li>
  <li>✅ File ingestion pipeline</li>
  <li>✅ Metadata-first design</li>
  <li>🚧 Retrieval & reranking refinement</li>
  <li>🚧 RAG observability layer</li>
  <li>🚧 Evaluation & failure analysis</li>
</ul>

<p>
This project is intentionally built <b>incrementally</b>, mirroring real production systems.
</p>

<hr/>

<h2>🧠 What Makes This Different</h2>

<ul>
  <li>Not a notebook demo</li>
  <li>Not a black-box LangChain wrapper</li>
  <li>Designed for debugging and inspection</li>
  <li>Built with real-world RAG failure modes in mind</li>
</ul>

<hr/>

<h2>🛣️ Roadmap</h2>

<ul>
  <li>Query-level execution traces</li>
  <li>Reranking integration</li>
  <li>Hallucination detection signals</li>
  <li>Evaluation metrics (retrieval precision, grounding)</li>
  <li>Pluggable LLM providers</li>
  <li>Production-grade logging hooks</li>
</ul>

<hr/>

<h2>📄 License</h2>

<p>
MIT License — free to use, modify, and extend.
</p>

<hr/>

<p align="center">
  <i>
  This project is built to demonstrate system-level thinking in GenAI,
  not just prompt engineering.
  </i>
</p>
