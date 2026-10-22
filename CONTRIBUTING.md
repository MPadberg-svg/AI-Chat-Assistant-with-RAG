# Contributing

Thanks for taking the time to contribute. This project is small enough that a
short guide is all you need.

## Development setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
OPENAI_API_KEY=your-key uvicorn app.main:app --reload

# Frontend (second terminal)
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`, so no extra configuration is
needed.

## Before opening a pull request

Run the same checks CI runs:

```bash
# Backend
cd backend
black --check app tests        # or: black app tests
flake8 app tests
PYTHONPATH=. OPENAI_API_KEY=test-key pytest -q

# Frontend
cd frontend
npm run lint
npm run format:check           # or: npm run format
npm test
npm run build
```

All of these must pass. `black` and `flake8` are configured to agree, so you can
format freely.

## Conventions

- **Python**: type hints on public functions, docstrings on modules and
  functions, `from __future__ import annotations` at the top.
- **JavaScript**: function components, hooks, no class components except
  `ErrorBoundary`.
- **Tests**: every behaviour change needs a test. Regression tests for bugs are
  expected — name them after the failure, not the fix.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `chore:`, `docs:`, `ci:`, `test:`, `refactor:`). The release
  changelog is generated from them.
- **Dependencies**: keep runtime dependencies small; add dev-only packages to
  `requirements-dev.txt` or `devDependencies`.

## Project layout

| Path | Purpose |
|---|---|
| `backend/app/core/` | Configuration, splitter, embeddings, retrieval, RAG chain |
| `backend/app/api/` | HTTP routes |
| `backend/app/models/` | Pydantic schemas |
| `frontend/src/components/` | UI components |
| `frontend/src/hooks/`, `frontend/src/lib/` | Stateful logic and pure helpers |
| `.github/workflows/` | CI, CodeQL and release automation |

## Releasing

Versioning is automatic. On every push to `main` the Release workflow publishes
the next version derived from `__version__` in `backend/app/core/config.py` and
all existing tags. To cut a minor or major release, raise `__version__` in the
same pull request. See the README for the full rules.
