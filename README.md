# rag-chat-assistant

Production-ready Retrieval-Augmented Generation (RAG) chat assistant built with FastAPI, LangChain, ChromaDB, OpenAI, React, and Docker.

## Quick start

1. Copy env template:
   ```bash
   cp .env.example .env
   ```
2. Set `OPENAI_API_KEY` in `.env`.
3. Start services:
   ```bash
   docker compose up --build
   ```

## Project layout

- `backend/` FastAPI API, ingestion, retrieval, and RAG streaming chain.
- `frontend/` React app with SSE chat stream, uploads, and source citations.
- `.github/workflows/ci.yml` lint, test, and docker build checks.
