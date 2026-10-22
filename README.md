# AI Chat Assistant with RAG

A production-ready **Retrieval-Augmented Generation** chat assistant. Upload your own documents and ask questions grounded exclusively in their content — the LLM answers only from what it finds, with inline citations and confidence scores.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.159-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5-orange?logo=chromadb)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38BDF8?logo=tailwindcss)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![CI](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/ci.yml/badge.svg)
![CodeQL](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/codeql.yml/badge.svg)

---

## Features

- **Document ingestion** — Upload PDF, DOCX or TXT files up to 20 MB; chunked, embedded and persisted in ChromaDB. DOCX table content is extracted too.
- **Duplicate detection** — Re-uploading identical content returns the existing document instead of creating a duplicate.
- **Grounded answers** — The LLM only answers from retrieved context. If the context is insufficient, it says so.
- **Streaming responses** — Token-by-token over Server-Sent Events, with newlines preserved so markdown renders correctly.
- **Inline citations** — Every answer references `[filename p.N]`; a citation panel shows cosine similarity.
- **Multi-turn conversations** — The last 10 exchanges are sent as history (configurable).
- **Markdown rendering** — Full GFM support, syntax-highlighted code blocks, and tables.
- **Streaming upload guard** — The 20 MB limit is enforced while the file is being read, not after it is buffered in memory.
- **Honest health endpoint** — `/api/health` performs a live ChromaDB check and returns `503` when it is unreachable.
- **Optional hardening** — Bearer-token auth and per-client rate limiting, both off by default.
- **Automated releases** — Every push to `main` creates a versioned GitHub Release with changelog.
- **Security scanning** — CodeQL analyzes Python and JS/TS on every push and weekly.

---

## How It Works

```
Your document                           Your question
     │                                       │
     ▼                                       ▼
Recursive text splitter              Query embedding
(512-char chunks, 50 overlap)    (text-embedding-3-small)
     │                                       │
     ▼                                       ▼
Embedding model          ──────▶    Cosine search in ChromaDB
(text-embedding-3-small)              (top-k nearest chunks)
     │                                       │
     ▼                                       ▼
ChromaDB vector store        System prompt + history + context
(persistent on disk)                         │
                                             ▼
                                    GPT-4o mini (streaming)
                                             │
                                             ▼
                          SSE frames: token / sources / error
```

Both ingestion and querying use the **same** embedding model. Queries are sent to
ChromaDB as vectors, and the collection is created in **cosine space**, so
`score = 1 - distance` is a real 0–1 similarity.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.159 + Uvicorn |
| Vector store | ChromaDB 1.5 (persistent) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Chunking | Built-in recursive character splitter (`app/core/splitter.py`) |
| Frontend | React 18 + Vite 7 |
| Styling | Tailwind CSS 3.4 + `@tailwindcss/typography` |
| Markdown | `react-markdown` + `remark-gfm` + `rehype-highlight` |
| HTTP | Axios (REST) + native `fetch` (SSE streaming) |
| Containerization | Docker Compose (multi-stage builds, non-root, healthchecks) |
| CI | GitHub Actions — lint, tests, frontend build, docker build |
| Security | GitHub CodeQL + advisory dependency audit |
| Tests | pytest + Vitest |

---

## Project Structure

```
.
├── .env.example
├── .flake8
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml          # lint → test → frontend → docker build → audit
│       ├── codeql.yml      # Security scanning (Python + JS/TS)
│       └── release.yml     # Auto-versioned GitHub Releases
│
├── backend/
│   ├── Dockerfile          # multi-stage, non-root, healthcheck
│   ├── requirements.txt    # runtime dependencies only
│   ├── requirements-dev.txt
│   ├── pytest.ini          # asyncio_mode = auto
│   ├── app/
│   │   ├── main.py         # FastAPI entrypoint, lifespan, CORS, health, access control
│   │   ├── core/
│   │   │   ├── config.py   # Pydantic Settings, lru_cache, validation
│   │   │   ├── splitter.py # recursive character splitter
│   │   │   ├── embeddings.py
│   │   │   ├── retriever.py
│   │   │   ├── rag_chain.py
│   │   │   └── security.py # optional token auth + rate limiter
│   │   ├── api/
│   │   │   ├── chat.py     # POST /api/chat → SSE StreamingResponse
│   │   │   └── documents.py # Upload / list / delete
│   │   └── models/
│   │       └── schemas.py
│   └── tests/              # 66 tests
│
└── frontend/
    ├── Dockerfile          # node:22-alpine build → nginx:1.27-alpine
    ├── nginx.conf          # SPA routing, /api proxy, SSE-safe, gzip
    ├── vite.config.js      # dev proxy + manual chunk splitting
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ChatWindow.jsx
        │   ├── DocumentUpload.jsx
        │   ├── Sidebar.jsx
        │   └── SourceCitations.jsx
        ├── hooks/useSSE.js
        ├── lib/sse.js      # dependency-free SSE parser
        └── services/api.js
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone and configure

```bash
git clone https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG.git
cd AI-Chat-Assistant-with-RAG

cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

The frontend is served by nginx, which proxies `/api` to the backend, so the
browser only ever talks to one origin.

### Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
OPENAI_API_KEY=your-key uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`, so no environment variables are
needed for local development.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Validated at startup. |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat completion model. |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model, used for both ingestion and queries. |
| `EMBEDDING_BATCH_SIZE` | `128` | Inputs per embeddings request (API max is 2048). |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB persistence path. |
| `CHROMA_COLLECTION` | `documents_v2` | Collection name (cosine space). |
| `CHUNK_SIZE` | `512` | Max characters per text chunk. |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks. |
| `TOP_K` | `5` | Nearest chunks retrieved per query (1–20). |
| `MIN_RELEVANCE_SCORE` | `0` | Drop chunks below this cosine similarity (0 disables). |
| `MAX_HISTORY_MESSAGES` | `20` | History messages sent to the model (2 = 1 exchange). |
| `MAX_UPLOAD_BYTES` | `20971520` | Max upload size in bytes (default 20 MB). |
| `CLIENT_URL` | `http://localhost:5173` | Primary CORS-allowed origin. |
| `EXTRA_CLIENT_URLS` | — | Comma-separated additional CORS origins. |
| `API_TOKEN` | — | If set, requires `Authorization: Bearer <token>` on all API routes except `/api/health`. |
| `RATE_LIMIT_PER_MINUTE` | `0` | Per-client request limit; `0` disables. |
| `VITE_API_URL` | `/api` | Frontend API base URL (build-time). Leave empty to use the nginx proxy. |

---

## API Reference

### `POST /api/chat`

Stream a context-grounded answer as Server-Sent Events.

```json
{
  "question": "What are the main findings?",
  "top_k": 5,
  "history": [
    { "role": "user", "content": "Summarize the report." },
    { "role": "assistant", "content": "It highlights revenue growth." }
  ]
}
```

Response — `text/event-stream`. Three event types are emitted:

```
event: token
data: The main findings show revenue increased

event: token
data: by 12% [report.pdf p.3].

event: sources
data: [{"doc_id":"a1b2_report","page":3,"score":0.94}]
```

Errors mid-stream are delivered as `event: error` with `{"message": "..."}`,
so the client can surface them instead of showing a truncated answer.

Every physical line of a payload is a separate `data:` field, which is how
newlines survive the transport and markdown stays intact.

### `POST /api/documents/upload`

Upload and ingest a document.

```json
{ "doc_id": "a1b2c3_report", "filename": "report.pdf", "chunks": 24, "duplicate": false }
```

Returns **400** for unsupported formats, **400** when no text can be extracted,
**413** when the file exceeds the size limit (enforced while streaming).

### `GET /api/documents`

```json
[{ "doc_id": "a1b2c3_report", "filename": "report.pdf", "chunks": 24 }]
```

### `DELETE /api/documents/{doc_id}`

Delete a document. Returns **404** if `doc_id` does not exist.

### `GET /api/health`

```json
{ "status": "ok", "chroma": "connected", "chunks": 42, "version": "1.2.0" }
```

Returns **503** with `"status": "degraded"` when ChromaDB cannot be reached.

---

## Running Tests

```bash
# Backend — 66 tests
cd backend
pip install -r requirements-dev.txt
OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q

# Frontend — 17 tests
cd frontend
npm ci
npm test
```

---

## CI / CD Pipeline

**CI** (on every push/PR to `main`, with concurrency cancellation and dependency caching):
```
lint           →  black --check + flake8
test           →  pytest (mocked, no real API calls)
frontend       →  npm ci + vitest + vite build
docker-build   →  docker compose build
security-audit →  pip-audit + npm audit  (advisory, non-blocking)
```

**CodeQL** — Python + JS/TS, every push + weekly schedule.

**Releases** — Publishes a GitHub Release on every push to `main`. The next version is derived from `__version__` in `config.py` *and* every existing `vX.Y.Z` tag and release:

- If `__version__` is **higher** than anything already released, it is used as-is — bump it to `1.3.0` to cut a minor release.
- Otherwise the patch of the highest released version is incremented.
- An existing tag is never reused, so a run that is replayed or retried simply moves to the next free patch number.
- If the current commit has already been released, the job exits successfully without publishing anything.

The changelog is generated from the latest reachable tag and attached via a notes file. Releases can also be triggered by hand from **Actions → Release → Run workflow** (`workflow_dispatch`).

---

## Upgrading from 1.1

Version 1.2 fixes the retrieval pipeline. It uses a new cosine collection
(`CHROMA_COLLECTION=documents_v2`); on first start the backend copies any
existing chunks from the legacy `documents` collection, preserving the stored
embeddings so nothing has to be re-embedded. The old collection is left
untouched and can be deleted once you are satisfied.

---

## License

MIT — see [LICENSE](LICENSE).
