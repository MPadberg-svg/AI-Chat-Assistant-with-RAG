# AI Chat Assistant with RAG

A production-ready **Retrieval-Augmented Generation** chat assistant. Upload your own documents and ask questions grounded exclusively in their content — the LLM answers only from what it finds, with inline citations and confidence scores.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.159-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5-orange?logo=chromadb)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38BDF8?logo=tailwindcss)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/ci.yml/badge.svg)
![CodeQL](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/codeql.yml/badge.svg)

---

## Features

- **Hybrid retrieval** — vector similarity fused with BM25 keyword search via reciprocal rank fusion, so exact identifiers (error codes, names, part numbers) are not lost to semantic blur.
- **Document ingestion** — Upload PDF, DOCX or TXT files up to 20 MB; chunked, embedded and persisted in ChromaDB. DOCX table content is extracted too.
- **Duplicate detection** — Re-uploading identical content returns the existing document instead of creating a duplicate.
- **Grounded answers** — The LLM only answers from retrieved context. If the context is insufficient, it says so.
- **Streaming responses** — Token-by-token over Server-Sent Events, with newlines preserved so markdown renders correctly.
- **Inline citations** — Every answer references `[filename p.N]`; a citation panel shows cosine similarity.
- **Multi-turn conversations** — The last 10 exchanges are sent as history (configurable).
- **Markdown rendering** — Full GFM support, syntax-highlighted code blocks, and tables.
- **Streaming upload guard** — The 20 MB limit is enforced while the file is being read, not after it is buffered in memory.
- **Honest health endpoint** — `/api/health` performs a live ChromaDB check and returns `503` when it is unreachable.
- **Request tracing** — Every response carries `X-Request-ID`, and all log lines emitted while handling a request are tagged with it.
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
     ▼                                       │
Embedding model                              │
(text-embedding-3-small)                     │
     │                                       │
     ▼                                       ▼
ChromaDB vector store  ──────────▶   Cosine search ─┐
(persistent on disk)                                │
     │                                              ├─▶ Reciprocal rank
     └── BM25 keyword index ──────▶  Lexical search ┘      fusion
                                                              │
                                                              ▼
                                    System prompt + history + top-k context
                                                              │
                                                              ▼
                                                    GPT-4o mini (streaming)
                                                              │
                                                              ▼
                                       SSE frames: token / sources / error
```

Both ingestion and querying use the **same** embedding model. The collection is
created in **cosine space**, so the reported `score` is always a real 0–1
similarity, and every returned chunk carries its true cosine score — even when
it was retrieved by the keyword side.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.159 + Uvicorn |
| Vector store | ChromaDB 1.5 (persistent, cosine space) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Retrieval | Cosine similarity + BM25, fused with reciprocal rank fusion |
| Chunking | Built-in recursive character splitter (`app/core/splitter.py`) |
| Frontend | React 18 + Vite 7 |
| Styling | Tailwind CSS 3.4 + `@tailwindcss/typography` |
| Markdown | `react-markdown` + `remark-gfm` + `rehype-highlight` |
| HTTP | Axios (REST) + native `fetch` (SSE streaming) |
| Containerization | Docker Compose (multi-stage builds, non-root, healthchecks) |
| CI | GitHub Actions — lint, tests, coverage, frontend lint/format/test/build, docker smoke test |
| Security | GitHub CodeQL + advisory dependency audit + Dependabot |
| Tests | pytest (108) + Vitest (20) |

---

## Project Structure

```
.
├── .env.example            # every supported variable, documented
├── .coveragerc             # coverage configuration
├── .editorconfig
├── .flake8                 # Black-compatible lint rules
├── docker-compose.yml
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── README.md
│
├── .github/
│   ├── dependabot.yml      # weekly pip/npm updates, monthly actions
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       ├── ci.yml          # lint → test+cov → frontend → docker smoke → audit
│       ├── codeql.yml      # Security scanning (Python + JS/TS)
│       └── release.yml     # Auto-versioned GitHub Releases
│
├── backend/
│   ├── Dockerfile          # multi-stage, non-root, healthcheck
│   ├── requirements.txt    # runtime dependencies only
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py         # entrypoint: lifespan, CORS, health, access control, request ids
│   │   ├── core/
│   │   │   ├── config.py   # Pydantic Settings, lru_cache, validation
│   │   │   ├── splitter.py # recursive character splitter
│   │   │   ├── bm25.py     # BM25 index + reciprocal rank fusion
│   │   │   ├── embeddings.py
│   │   │   ├── retriever.py  # hybrid retrieval
│   │   │   ├── rag_chain.py
│   │   │   ├── security.py # optional token auth + rate limiter
│   │   │   └── logging.py  # request-scoped logging
│   │   ├── api/
│   │   │   ├── chat.py     # POST /api/chat → SSE StreamingResponse
│   │   │   └── documents.py # Upload / list / delete
│   │   └── models/
│   │       └── schemas.py
│   └── tests/              # 108 tests
│
└── frontend/
    ├── Dockerfile          # node:22-alpine build → nginx:1.27-alpine
    ├── nginx.conf          # SPA routing, /api proxy, SSE-safe, gzip
    ├── eslint.config.js
    ├── .prettierrc.json
    ├── vite.config.js      # dev proxy + manual chunk splitting
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ChatWindow.jsx
        │   ├── DocumentUpload.jsx
        │   ├── ErrorBoundary.jsx
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
| `HYBRID_SEARCH` | `true` | Fuse BM25 keyword results with vector results. Set to `false` for vector-only retrieval. |
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

Every response includes an `X-Request-ID` header — echoed from the request when
you supply one, generated otherwise. Use it to correlate a failure with the
server log line for that request. CORS preflight and `/api/health` are exempt
from authentication.

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
so the client can surface them instead of showing a truncated answer. A blank
question returns **422**.

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
{ "status": "ok", "chroma": "connected", "chunks": 42, "version": "1.3.0" }
```

Returns **503** with `"status": "degraded"` when ChromaDB cannot be reached.

---

## Running Tests

```bash
# Backend — 108 tests, 94% coverage
cd backend
pip install -r requirements-dev.txt
OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q

# with coverage (what CI enforces, threshold 85%)
OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q --cov=app --cov-report=term-missing

# Frontend — 20 tests
cd frontend
npm ci
npm test
npm run lint
npm run format:check
```

All tests run offline and need no API key. Most replace the OpenAI client and
ChromaDB with fakes; `test_openai_contract.py` goes further and drives the
**real** OpenAI SDK with a mocked HTTP transport, so an SDK upgrade that changes
the client surface fails the build instead of production.

---

## CI / CD Pipeline

**CI** (on every push/PR to `main`, with concurrency cancellation and dependency caching):

```
lint           →  black --check + flake8
test           →  pytest with coverage (fails under 85%)
frontend       →  eslint + prettier --check + vitest + vite build
docker-build   →  docker compose build, then boot the stack and smoke test it
security-audit →  pip-audit + npm audit  (advisory, non-blocking)
```

The Docker job does not just build: it starts the compose stack with a dummy
key, waits for `/api/health`, checks that nginx serves the SPA, checks the `/api`
proxy, and verifies ChromaDB is writable by the non-root container user.

**CodeQL** — Python + JS/TS, every push + weekly schedule.

**Dependabot** — weekly pip/npm updates (grouped, minor and patch) and monthly
Actions updates.

**Releases** — Publishes a GitHub Release on every push to `main`. The next version is derived from `__version__` in `config.py` *and* every existing `vX.Y.Z` tag and release:

- If `__version__` is **higher** than anything already released, it is used as-is — bump it to `1.4.0` to cut a minor release.
- Otherwise the patch of the highest released version is incremented.
- An existing tag is never reused, so a run that is replayed or retried simply moves to the next free patch number.
- If the current commit has already been released, the job exits successfully without publishing anything.

The changelog is generated from the latest reachable tag and attached via a notes file. Releases can also be triggered by hand from **Actions → Release → Run workflow** (`workflow_dispatch`).

---

## Limitations

Worth knowing before deploying this for other people:

- **No per-user isolation.** All documents live in one collection and any client
  can list, query and delete them. `API_TOKEN` is a single shared secret, not
  accounts. Run one instance per tenant.
- **The rate limiter is in-process.** With multiple replicas each has its own
  counter; move limiting to a gateway for horizontal scaling.
- **Ingestion is synchronous.** The upload request stays open while chunks are
  embedded; a large PDF can take tens of seconds.
- **No OCR.** Scanned, image-only PDFs yield no extractable text and return 400.
- **The BM25 index is built in memory** from the collection on first query and
  cached until the corpus changes — fine for thousands of chunks, not millions.
- **Single collection name.** Changing `CHROMA_COLLECTION` starts from an empty
  corpus (the legacy migration only runs from `documents`).
- **`chromadb` carries published advisories with no upstream fix.** It is the
  vector store and cannot be removed; see `SECURITY.md`.

## Roadmap

Ideas that would add the most value next:

- Per-user collections and real accounts.
- Background ingestion with job status polling.
- Cross-encoder reranking on top of the fused results.
- OCR fallback for scanned PDFs.
- Persistent conversations (history currently lives in browser memory).
- Evaluation harness with a labelled question set to measure retrieval quality.

---

## Upgrading from 1.1

Version 1.2 fixed the retrieval pipeline. It uses a new cosine collection
(`CHROMA_COLLECTION=documents_v2`); on first start the backend copies any
existing chunks from the legacy `documents` collection, preserving the stored
embeddings so nothing has to be re-embedded. The old collection is left
untouched and can be deleted once you are satisfied.

Version 1.3 changed the streaming protocol from a `__SOURCES__` text marker to
typed SSE events. If you wrote your own client against the old format, update it
to listen for `token`, `sources` and `error`. The bundled frontend already does.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the checks CI runs, and
conventions. Security issues: [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
