# AI Chat Assistant with RAG

A production-ready **Retrieval-Augmented Generation** chat assistant. Upload your own documents and ask questions grounded exclusively in their content — the LLM never hallucinates beyond what it finds.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.0-orange)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![CI](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/actions/workflows/ci.yml/badge.svg)

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
ChromaDB vector store            Prompt: context + question
                                           │
                                           ▼
                                   GPT-4o mini (streaming)
                                           │
                                           ▼
                                 Answer + inline citations
```

The system streams the answer token-by-token via **Server-Sent Events**, then appends a `__SOURCES__` marker payload with document IDs, page numbers, and confidence scores.

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
| HTTP client | Axios + native `fetch` (SSE) |
| Containerization | Docker Compose |
| CI | GitHub Actions (lint → test → docker build) |

---

## Project Structure

```
.
├── .env.example
├── docker-compose.yml
├── .github/
│   └── workflows/ci.yml
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── app/
│       ├── main.py              # FastAPI entrypoint, lifespan, CORS
│       ├── core/
│       │   ├── config.py        # Pydantic Settings with lru_cache
│       │   ├── embeddings.py    # Ingest, chunk, embed, store, delete
│       │   ├── retriever.py     # Semantic search + score normalization
│       │   └── rag_chain.py     # OpenAI streaming + __SOURCES__ protocol
│       ├── api/
│       │   ├── chat.py          # POST /api/chat → SSE StreamingResponse
│       │   └── documents.py     # Upload / list / delete documents
│       └── models/
│           └── schemas.py       # Pydantic request/response schemas
│
└── frontend/
    ├── Dockerfile + nginx.conf
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ChatWindow.jsx
        │   ├── DocumentUpload.jsx
        │   ├── Sidebar.jsx
        │   └── SourceCitations.jsx
        ├── hooks/
        │   └── useSSE.js        # SSE reader + sources buffer parser
        └── services/
            └── api.js           # Axios wrappers + raw fetch for SSE
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
# Open .env and set OPENAI_API_KEY=your-key-here
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

### 3. Use it

1. Upload a PDF, DOCX, or TXT file from the sidebar.
2. Type a question in the chat input.
3. The assistant streams an answer grounded only in your document, with inline source citations.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI API key. |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Path where ChromaDB stores vectors. |
| `CHUNK_SIZE` | `512` | Max tokens per text chunk. |
| `CHUNK_OVERLAP` | `50` | Token overlap between consecutive chunks. |
| `TOP_K` | `5` | Number of nearest chunks retrieved per query. |
| `CLIENT_URL` | `http://localhost:5173` | Allowed CORS origin for the frontend. |
| `VITE_API_URL` | `http://localhost:8000/api` | API base URL used by the React app. |

---

## API Reference

### `POST /api/chat`

Stream a context-grounded answer as Server-Sent Events.

**Request body**

```json
{
  "question": "What are the main findings?",
  "top_k": 5
}
```

**Response** — `text/event-stream`

Each SSE frame carries one token. The final frame carries the sources payload:

```
data: The main findings show...

data: ...that revenue increased by 12%.

data: __SOURCES__[{"doc_id": "abc_report", "page": 3, "score": 0.94}]
```

---

### `POST /api/documents/upload`

Upload and ingest a document into the vector store.

**Request** — `multipart/form-data`, field `file`. Accepted formats: `.pdf`, `.docx`, `.txt`.

**Response**

```json
{
  "doc_id": "a3f1c2b0_report",
  "chunks": 24
}
```

---

### `GET /api/documents`

List all ingested document IDs.

**Response**

```json
["a3f1c2b0_report", "b9d4e1f2_manual"]
```

---

### `DELETE /api/documents/{doc_id}`

Remove a document and all its chunks from the vector store.

**Response**

```json
{
  "status": "deleted",
  "doc_id": "a3f1c2b0_report"
}
```

---

### `GET /api/health`

```json
{ "status": "ok", "chroma": "connected" }
```

---

## Running Tests Locally

```bash
cd backend
pip install -r requirements.txt

OPENAI_API_KEY=test-key PYTHONPATH=. pytest -q
```

Tests use monkeypatching — no real API calls or ChromaDB writes are made.

---

## CI Pipeline

On every push or pull request to `main`, GitHub Actions runs three parallel jobs:

```
lint          → black --check + flake8
test          → pytest (monkeypatched, no real API calls)
docker-build  → docker compose build
```

---

## License

MIT
