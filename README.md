# AI Chat Assistant with RAG

A production-ready **Retrieval-Augmented Generation** chat assistant. Upload your own documents and ask questions grounded exclusively in their content — the LLM answers only from what it finds, with inline citations and confidence scores.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.0-orange)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38BDF8?logo=tailwindcss)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![CI](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/ci.yml/badge.svg)
![CodeQL](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/codeql.yml/badge.svg)

---

## Features

- **Document ingestion** — Upload PDF, DOCX, or TXT files up to 20 MB; chunked, embedded, and persisted in ChromaDB.
- **Grounded answers** — The LLM only answers from retrieved context. If context is insufficient, it says so.
- **Streaming responses** — Token-by-token via Server-Sent Events. No waiting for the full response.
- **Inline citations** — Every answer includes `[doc_id p.N]` references; a citation panel shows confidence scores.
- **Multi-turn conversations** — Last 10 exchanges sent as history, enabling follow-up questions.
- **Markdown rendering** — Full GFM support, syntax-highlighted code blocks, and tables.
- **File size guard** — Uploads exceeding 20 MB are rejected with HTTP 413 before any processing.
- **404 on missing delete** — Deleting a non-existent document returns HTTP 404, not a silent 200.
- **Live health endpoint** — `/api/health` reports real Chroma connectivity and document count.
- **Automated releases** — Every push to `main` creates a versioned GitHub Release with changelog.
- **Security scanning** — CodeQL analyzes Python and JS/TS on every push and weekly.

---

## How It Works

```
Your document                           Your question
     │                                       │
     ▼                                       ▼
Text splitter                        Query embedding
(512-token chunks)               (text-embedding-3-small)
     │                                       │
     ▼                                       ▼
Embedding model          ──────▶    Semantic search in ChromaDB
(text-embedding-3-small)              (top-k nearest chunks)
     │                                       │
     ▼                                       ▼
ChromaDB vector store        System prompt + history + context
(persistent on disk)                         │
                                             ▼
                                    GPT-4o mini (streaming)
                                             │
                                             ▼
                              Answer tokens  →  __SOURCES__ payload
                               (SSE frames)      (doc_id, page, score)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.116 + Uvicorn |
| Vector store | ChromaDB 1.0 (persistent) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Frontend | React 18 + Vite 7 |
| Styling | Tailwind CSS 3.4 + `@tailwindcss/typography` |
| Markdown | `react-markdown` + `remark-gfm` + `rehype-highlight` |
| HTTP | Axios (REST) + native `fetch` (SSE streaming) |
| Containerization | Docker Compose (multi-stage builds, healthcheck) |
| CI | GitHub Actions — lint, test, docker build (with concurrency) |
| Security | GitHub CodeQL (Python + JS/TS, weekly scan) |
| Releases | Automated GitHub Releases with changelog generation |

---

## Project Structure

```
.
├── .env.example
├── .flake8
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml          # lint → test → docker build (concurrency cancellation)
│       ├── codeql.yml      # Security scanning (Python + JS/TS)
│       └── release.yml     # Auto-versioned GitHub Releases
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini          # asyncio_mode = auto
│   └── app/
│       ├── main.py         # FastAPI entrypoint, lifespan, CORS, health
│       ├── core/
│       │   ├── config.py   # Pydantic Settings, lru_cache, MAX_UPLOAD_BYTES
│       │   ├── embeddings.py
│       │   ├── retriever.py
│       │   └── rag_chain.py
│       ├── api/
│       │   ├── chat.py     # POST /api/chat → SSE StreamingResponse
│       │   └── documents.py # Upload (413 guard) / list / delete (404 guard)
│       └── models/
│           └── schemas.py
│
└── frontend/
    ├── Dockerfile          # node:22-alpine build → nginx:1.27-alpine
    ├── nginx.conf          # SPA routing + gzip compression
    ├── vite.config.js      # Manual chunk splitting (vendor + markdown)
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ChatWindow.jsx
        │   ├── DocumentUpload.jsx
        │   ├── Sidebar.jsx
        │   └── SourceCitations.jsx
        ├── hooks/useSSE.js
        └── services/api.js  # DRY BASE_URL constant
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

### Local development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
OPENAI_API_KEY=your-key uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
NODE_ENV=development npm ci
npm run dev
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Validated at startup. |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB persistence path. |
| `CHUNK_SIZE` | `512` | Max characters per text chunk. |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks. |
| `TOP_K` | `5` | Nearest chunks retrieved per query (1–20). |
| `CLIENT_URL` | `http://localhost:5173` | CORS-allowed frontend origin. |
| `VITE_API_URL` | `http://localhost:8000/api` | API base URL for the React app. |
| `MAX_UPLOAD_BYTES` | `20971520` | Max upload size in bytes (default 20 MB). |

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

Response — `text/event-stream`:

```
data: The main findings show...
data: ...revenue increased by 12% [report p.3].
data: __SOURCES__[{"doc_id": "report", "page": 3, "score": 0.94}]
```

### `POST /api/documents/upload`

Upload and ingest a document. Returns `{"doc_id": "...", "chunks": 24}`.
Returns **400** for unsupported formats, **413** if file exceeds 20 MB.

### `GET /api/documents`

List all ingested document IDs.

### `DELETE /api/documents/{doc_id}`

Delete a document. Returns **404** if `doc_id` does not exist.

### `GET /api/health`

```json
{ "status": "ok", "chroma": "connected", "documents": 3 }
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q
```

---

## CI / CD Pipeline

**CI** (on every push/PR to `main`, with concurrency cancellation):
```
lint          →  black --check + flake8
test          →  pytest (monkeypatched, no real API calls)
docker-build  →  docker compose build
```

**CodeQL** — Python + JS/TS, every push + weekly schedule.

**Releases** — Reads `__version__` from `config.py`, auto-increments patch, tags and publishes a GitHub Release with commit-based changelog. To bump minor/major, update `__version__` manually before pushing.

---

## License

MIT