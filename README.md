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

- **Document ingestion** — Upload PDF, DOCX, or TXT files; they are chunked, embedded, and stored in a persistent ChromaDB vector store.
- **Grounded answers** — The LLM only answers from retrieved context. If the context is insufficient, it says so.
- **Streaming responses** — Answers are streamed token-by-token via Server-Sent Events. No waiting for the full response.
- **Inline citations** — Every answer includes `[doc_id p.N]` source references; a citation panel shows confidence scores.
- **Multi-turn conversations** — The last 10 exchanges are sent as history on every request, enabling follow-up questions.
- **Markdown rendering** — Assistant messages render with full GFM support, syntax-highlighted code blocks, and tables.
- **Automated releases** — Every push to `main` creates a versioned GitHub Release with a generated changelog.
- **Security scanning** — CodeQL analyzes both Python and JavaScript/TypeScript on every push and on a weekly schedule.

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

The backend streams tokens via SSE. A custom `__SOURCES__` marker at the end of the stream carries a JSON array of cited documents — no extra HTTP round-trip needed.

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
| Containerization | Docker Compose (multi-stage builds) |
| CI | GitHub Actions — lint, test, docker build |
| Security | GitHub CodeQL (Python + JS/TS, weekly scan) |
| Releases | Automated GitHub Releases with changelog generation |

---

## Project Structure

```
.
├── .env.example                        # All environment variables with defaults
├── .flake8                             # Flake8 config (max-line-length = 88)
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml                      # lint → test → docker build
│       ├── codeql.yml                  # Security scanning (Python + JS/TS)
│       └── release.yml                 # Auto-versioned GitHub Releases
│
├── backend/
│   ├── Dockerfile                      # python:3.11-slim, non-root user
│   ├── requirements.txt
│   ├── pytest.ini                      # asyncio_mode = auto
│   └── app/
│       ├── main.py                     # FastAPI entrypoint, lifespan, CORS
│       ├── core/
│       │   ├── config.py               # Pydantic Settings, lru_cache, __version__
│       │   ├── embeddings.py           # Ingest, chunk, embed, store, delete
│       │   ├── retriever.py            # Semantic search + score normalization
│       │   └── rag_chain.py            # OpenAI streaming, history, __SOURCES__
│       ├── api/
│       │   ├── chat.py                 # POST /api/chat → SSE StreamingResponse
│       │   └── documents.py            # Upload / list / delete
│       └── models/
│           └── schemas.py              # ChatRequest, Message, DocumentInfo
│
└── frontend/
    ├── Dockerfile                      # node:20-alpine build → nginx:1.27-alpine
    ├── nginx.conf                      # SPA routing (try_files fallback)
    └── src/
        ├── App.jsx                     # Root — state orchestration + history
        ├── components/
        │   ├── ChatWindow.jsx          # Messages, typing indicator, markdown
        │   ├── DocumentUpload.jsx      # Upload with progress
        │   ├── Sidebar.jsx             # Document list + delete
        │   └── SourceCitations.jsx     # Citation panel with scores
        ├── hooks/
        │   └── useSSE.js               # SSE reader + __SOURCES__ buffer parser
        └── services/
            └── api.js                  # Axios wrappers + raw fetch for SSE
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

### 3. Use it

1. Upload a PDF, DOCX, or TXT file from the sidebar.
2. Type a question in the chat input.
3. The assistant streams a grounded answer with inline citations. Ask follow-up questions — conversation history is maintained automatically.

### Local development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
OPENAI_API_KEY=your-key uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

All variables are defined in `.env.example`. Copy it to `.env` before running.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI API key. Validated at startup. |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Path where ChromaDB persists vector data. |
| `CHUNK_SIZE` | `512` | Max characters per text chunk. |
| `CHUNK_OVERLAP` | `50` | Character overlap between consecutive chunks. |
| `TOP_K` | `5` | Number of nearest chunks retrieved per query (1–20). |
| `CLIENT_URL` | `http://localhost:5173` | CORS-allowed origin for the frontend. |
| `VITE_API_URL` | `http://localhost:8000/api` | API base URL used by the React app. |

> **Production note:** Override `CLIENT_URL` and `VITE_API_URL` with your real domain before deploying.

---

## API Reference

### `POST /api/chat`

Stream a context-grounded answer as Server-Sent Events.

**Request body**

```json
{
  "question": "What are the main findings?",
  "top_k": 5,
  "history": [
    { "role": "user", "content": "Summarize the report." },
    { "role": "assistant", "content": "It highlights revenue growth and customer retention." }
  ]
}
```

`history` is optional. When provided, the last 10 messages are included in the prompt for multi-turn context.

**Response** — `text/event-stream`

Each SSE frame carries one token. The final frame carries the sources payload:

```
data: The main findings show...

data: ...that revenue increased by 12% [annual_report p.3].

data: __SOURCES__[{"doc_id": "annual_report", "page": 3, "score": 0.94}]
```

---

### `POST /api/documents/upload`

Upload and ingest a document into the vector store.

**Request** — `multipart/form-data`, field `file`. Accepted: `.pdf`, `.docx`, `.txt`.

**Response**

```json
{
  "doc_id": "a3f1c2b0_annual_report",
  "chunks": 24
}
```

---

### `GET /api/documents`

List all ingested document IDs.

**Response**

```json
["a3f1c2b0_annual_report", "b9d4e1f2_user_manual"]
```

---

### `DELETE /api/documents/{doc_id}`

Remove a document and all its chunks from the vector store.

**Response**

```json
{
  "status": "deleted",
  "doc_id": "a3f1c2b0_annual_report"
}
```

---

### `GET /api/health`

```json
{ "status": "ok", "chroma": "connected" }
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q
```

Tests use monkeypatching — no real OpenAI API calls or ChromaDB writes are made during the test suite.

---

## CI / CD Pipeline

### Continuous Integration

On every push and pull request to `main`:

```
lint          →  black --check + flake8
test          →  pytest with monkeypatched dependencies
docker-build  →  docker compose build (verifies both images)
```

### Security Scanning

CodeQL analyzes Python and JavaScript/TypeScript on every push and weekly (Mondays at 08:00 UTC), with results reported in the Security tab.

### Automated Releases

Every push to `main` that changes source files triggers the release workflow:

1. Reads `__version__` from `backend/app/core/config.py`
2. Increments the patch number automatically
3. Creates a signed git tag
4. Publishes a GitHub Release with a generated changelog from commit messages

To bump a **minor** or **major** version, update `__version__` in `config.py` manually before pushing.

---

## License

MIT
