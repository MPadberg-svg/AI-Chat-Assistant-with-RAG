# Code Review — AI Chat Assistant with RAG

**Reviewed:** `main` @ `9637e49` · **Date:** 2026-10-22
**Scope:** backend (FastAPI/Chroma/OpenAI), frontend (React/Vite), Docker, CI/CD, dependencies
**Method:** every file read; CI pipeline executed locally (black, flake8, pytest, `vite build`, `npm ci`); the suspected runtime defects were reproduced with executable probes against the real library versions.

---

## 1. Executive summary

The architecture is sound and the code is clean and idiomatic — formatting, lint, tests and the Docker build all pass. The problem is not style, it is that **several core behaviours are broken in ways the test suite does not detect**.

The most important discovery: the retrieval path queries ChromaDB with `query_texts=...` while documents were ingested with explicit OpenAI embeddings. Chroma therefore embeds the *query* with its own bundled `DefaultEmbeddingFunction` (all-MiniLM-L6-v2, 384 dimensions) and compares it against 1536-dimension OpenAI vectors. **The chat endpoint cannot return correct results.** I reproduced the failure locally.

| Area | Grade | Comment |
|---|---|---|
| Architecture / structure | A− | Clean separation, typed settings, good SSE design intent |
| Code quality (Python) | A− | Small functions, docstrings, type hints, no lint debt |
| **Runtime correctness** | **D** | **4 confirmed bugs that break core UX (see §3)** |
| Test coverage | C− | 6 tests, happy-path mocking only; none of the P0 bugs are covered |
| Security posture | C | No auth, 132 known Python CVEs, 13 npm advisories |
| Deployment / Docker | C+ | Non-root user breaks the Chroma volume; no `.dockerignore`; dead env var |
| CI/CD | B− | Solid foundation; missing frontend job; release workflow was stuck (fixed here) |

**Counts:** 5 × P0 (broken now) · 9 × P1 (correctness/security) · 14 × P2 (quality/ops) · 6 × P3 (polish)

---

## 2. What I verified, and how

Everything below was executed, not assumed:

```bash
python3 -m venv /tmp/be && /tmp/be/bin/pip install -r backend/requirements.txt
/tmp/be/bin/black --check backend/app backend/tests   # 14 files unchanged
/tmp/be/bin/flake8 backend/app backend/tests          # clean
OPENAI_API_KEY=test-key PYTHONPATH=backend /tmp/be/bin/pytest backend/tests -q   # 6 passed
cd frontend && npm ci && npm run build                # built in 3.7s
/tmp/be/bin/pip-audit -r backend/requirements.txt     # 132 vulns / 10 packages
npm audit --omit=dev                                  # 13 vulns / 12 high
```

Docker is unavailable in my sandbox, so image-level findings (§3 P0-5, §4 P1-6, P1-7) are from source inspection plus the CI history, not from a build I ran. Everything else was executed.

---

## 3. P0 — broken in production right now

### P0-1 · Retrieval queries with the wrong embedding function
**`backend/app/core/retriever.py:15-19`**

```python
results = get_collection().query(
    query_texts=[query],          # <-- Chroma embeds this itself
    n_results=top_k, ...)
```

Documents are embedded by OpenAI `text-embedding-3-small` (1536-dim) in `embeddings.py:95` and passed explicitly to `add()`. The collection was created without an `embedding_function`, so Chroma attaches its default:

```
$ collection._embedding_function  ->  DefaultEmbeddingFunction   # all-MiniLM-L6-v2, 384 dims
```

`query_texts` therefore embeds the question at 384 dimensions and compares against 1536-dimension vectors. In my probe the call failed outright (the ONNX model download was refused in the sandbox); with a warm model cache it fails with a dimensionality mismatch. Either way **`POST /api/chat` cannot produce a grounded answer**.

**Fix** — embed the query with the same model and pass vectors:

```python
# retriever.py
from app.core.embeddings import _get_embeddings_model, get_collection

def semantic_search(query: str, top_k: int = 5):
    if not query.strip():
        return []
    embedding = _get_embeddings_model().embed_query(query)
    results = get_collection().query(
        query_embeddings=[embedding], n_results=top_k, include=[...])
```

Also cache the embeddings client (`@lru_cache`), otherwise a new `OpenAIEmbeddings` is built on every upload *and* every query.

### P0-2 · Similarity scores are meaningless and render as negative percentages
**`backend/app/core/embeddings.py:36-38`, `retriever.py:34`, `SourceCitations.jsx:13`**

The collection is created with no `metadata`, so Chroma defaults to **squared L2** distance. The code then reports `score = round(1 - distance, 3)` as if it were a 0–1 confidence.

Reproduced with 1536-dim vectors:

```
raw distances       : [247.07, 259.48, 259.72, 264.83]
app 'score'         : [-246.073, -258.477, -258.72, -263.834]
rendered in the UI  : ['-24607%', '-25848%', '-25872%', '-26383%']
```

**Fix** — create the collection in cosine space (verified working: distances `0.248 … 0.262` → scores `75% … 74%`):

```python
_collection = get_chroma_client().get_or_create_collection(
    name=_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
```

⚠️ **Migration:** an existing collection keeps its original space. Bump the collection name (`documents_v2`) or re-ingest; Chroma will not convert in place.

### P0-3 · Every newline is dropped from streamed answers — markdown collapses
**`backend/app/api/chat.py:20` + `frontend/src/hooks/useSSE.js:71-79`**

`yield f"data: {chunk}\n\n"` breaks when a token *is* a newline, which OpenAI emits constantly for paragraphs, lists and code fences. The token `"\n"` produces the frame `"data: \n\n"`, the client splits on `\n\n`, gets an empty payload, and discards it (`if (payload)`).

Executed reproduction of both sides:

```
sent: 'Here is a\nlist'                got: 'Here is alist'                <<< CORRUPTED
sent: 'Item one.\n\nItem two.'         got: 'Item one.Item two.'           <<< CORRUPTED
sent: '```python\nx = 1\n```'          got: '```pythonx = 1```'            <<< CORRUPTED
```

Markdown rendering can never work while this is in place.

**Fix** — emit one `data:` line per physical line (SSE allows multi-line data; the client already rejoins with `\n`):

```python
# chat.py
for line in chunk.split("\n"):
    yield f"data: {line}\n"
yield "\n"
```

Add a regression test that streams a token containing `\n`.

### P0-4 · Code blocks render as nested `<pre>` and inline code is treated as a block
**`frontend/src/components/ChatWindow.jsx:15-30`**

The component destructures `inline` from `code` props. `react-markdown` **removed that prop in v9** (this repo is on 10.1.0), so `inline` is always `undefined` → falsy → every code span takes the block branch. Real render output:

```html
<p>Inline <pre>npm install</pre> here.</p>
<pre><pre class="language-js">const x = 1;</pre></pre>
```

**Fix** — branch on the class name, or style blocks via the `pre` override instead:

```jsx
components={{
  pre: ({ children }) => (
    <pre className="block overflow-x-auto rounded-lg bg-gray-900 p-3 text-sm text-green-400">
      {children}
    </pre>
  ),
  code: ({ className, children, ...props }) => (
    <code className={className || "rounded bg-gray-100 px-1 font-mono text-sm"} {...props}>
      {children}
    </code>
  ),
}}
```

### P0-5 · `VITE_API_URL` is dead config — the deployed frontend always calls `localhost`
**`docker-compose.yml:23`, `frontend/Dockerfile:4`, `frontend/src/services/api.js:3`**

Vite inlines `import.meta.env.*` **at build time**. Compose passes `VITE_API_URL` as a *runtime* environment variable to the nginx container, and the Dockerfile declares no `ARG`. The value is silently ignored, so the bundle is frozen to `http://localhost:8000/api`. That works on a laptop only because the browser and Docker share a host — on any real deployment every request goes to the visitor's own machine.

**Fix (preferred)** — proxy `/api` through nginx and use a relative base URL; this also removes the CORS dependency:

```nginx
location /api/ {
  proxy_pass http://backend:8000/api/;
  proxy_http_version 1.1;
  proxy_set_header Connection "";
  proxy_buffering off;          # required for SSE
  proxy_read_timeout 3600s;
}
```

```js
const BASE_URL = import.meta.env.VITE_API_URL || "/api";
```

**Fix (minimal)** — `ARG VITE_API_URL` + `ENV VITE_API_URL=$VITE_API_URL` before `npm run build`, and `build: args:` in compose.

---

## 4. P1 — correctness, security, deployment

### P1-1 · Chat errors are invisible to the user
`chat.py` has no `try/except` and `rag_chain.py:59-64` lets OpenAI exceptions escape. Because `StreamingResponse` has already sent `200 OK` headers, the frontend's `if (!response.ok)` check (`useSSE.js:54`) never fires — the stream just stops mid-sentence with no message.

**Fix:** catch inside the generator, emit a terminal `data: {"error": ...}` frame (or `event: error`), and render it. Add a `try/except` around `client.chat.completions.create`.

### P1-2 · Blocking I/O inside an async generator stalls the whole server
`rag_chain.py:22` calls the synchronous `semantic_search` (Chroma query + OpenAI HTTP call) from async context, as does `ingest_document`'s embedding call from the upload route. While a query runs, every other request — including `/api/health` — is blocked.

**Fix:** `from starlette.concurrency import run_in_threadpool` / `anyio.to_thread.run_sync`, or use `AsyncOpenAI` embeddings and an async Chroma client.

### P1-3 · Uploads are fully buffered before the size check
`documents.py:28-34` does `await file.read()` and only then compares `len(content)` to the limit. A 20 MB cap therefore allows unbounded memory use per concurrent upload, and the 413 arrives after the whole body is in RAM.

**Fix:** stream to the temp file in chunks and abort at the limit (`UploadFile.read(chunk_size)` loop), or enforce `client_max_body_size` at the proxy. Note `python-multipart 0.0.20` (this parser) carries 6 published advisories — upgrade to ≥0.0.31.

### P1-4 · Unbatched embedding requests will fail on large documents
`embeddings.py:95` sends **all** chunks in one `embed_documents` call. The OpenAI embeddings API accepts at most **2048 inputs per request**; a 20 MB text file produces far more than that, so large uploads fail with a 400 after the whole file has been parsed.

**Fix:** chunk into batches of ≤512 and concatenate.

### P1-5 · The non-root container user cannot write the Chroma volume
`backend/Dockerfile:16-17` creates `appuser` and switches to it, but `/app` is still owned by root and no `/app/chroma_db` directory exists in the image. A fresh named volume is created `root:root 0755`, so `PersistentClient` cannot create its SQLite files.

**Fix:**

```dockerfile
RUN useradd --create-home appuser \
 && mkdir -p /app/chroma_db \
 && chown -R appuser:appuser /app
```

### P1-6 · No `.dockerignore` — and `COPY . .` overwrites `node_modules`
Neither context has a `.dockerignore`. `frontend/node_modules` is **77 MB** and is copied into the build context, then `COPY . .` (Dockerfile:5) replaces the modules that `npm ci` just installed with host-built ones — a classic source of the native-binding flakiness that an earlier commit tried to patch with `NODE_ENV=development npm ci`. A stray `backend/.env` would also be baked into the image.

**Fix:** add `.dockerignore` files (`node_modules`, `dist`, `.env`, `__pycache__`, `*.pyc`, `.pytest_cache`, `chroma_db`).

### P1-7 · No authentication, no rate limiting, no abuse controls
Every endpoint is public: anyone who can reach the port can upload (billing your OpenAI account), delete any document, and query. `doc_id` values are not secret. If this is deployed anywhere reachable, add at minimum a shared token / reverse-proxy auth and per-IP rate limits.

### P1-8 · 132 known vulnerabilities in 10 Python packages
`pip-audit -r backend/requirements.txt`:

| Package | Installed | Advisories | Fix available |
|---|---|---|---|
| pypdf | 6.0.0 | 20+ (PDF parsing — directly reachable via upload) | 6.21.1 |
| python-multipart | 0.0.20 | 6 (multipart parser — directly reachable) | 0.0.31 |
| starlette | 0.47.3 | 6 | constrained by FastAPI |
| langchain-core | 0.3.86 | 2 | 1.2.22 |
| langchain / -openai / -text-splitters | 0.3.x | 4 | 1.x / 1.1.14 / 1.1.2 |
| chromadb | 1.0.20 | 4 | none published |
| pytest, black | 8.4.2, 25.1.0 | 3 | 9.0.3, 26.3.1 |

**Frontend:** 13 advisories (12 high), including **axios@1.16.1 prototype pollution** and `form-data` CRLF injection — both direct runtime dependencies. `npm audit fix` (non-breaking) resolves a subset; the rest need `--force` / upgrades.

### P1-9 · Health check always reports `ok`
`main.py:44-56` returns `"status": "ok"` unconditionally, and `chroma_status` is only written during startup, so it stays `"connected"` forever even after Chroma dies. `list_document_ids()` is also called on every probe (the compose healthcheck runs every 30 s) and loads **all** chunk metadata to count documents — O(corpus) per health check.

**Fix:** query Chroma per request, return `503` when it is unreachable, and use `collection.count()` grouped by `doc_id` (or a small metadata collection) instead of scanning everything.

---

## 5. P2 — quality, consistency, operations

| # | Finding | Where |
|---|---|---|
| P2-1 | **README says "last 10 exchanges"; code keeps 10 *messages* (5 exchanges).** | `README.md:22` vs `rag_chain.py:14` |
| P2-2 | DEV dependencies ship in the production image (`pytest`, `flake8`, `black`, `pytest-asyncio`). Split into `requirements-dev.txt`. | `requirements.txt:13-16` |
| P2-3 | `settings.top_k` is never read — the request default (`5`) wins, so `TOP_K` in `.env` does nothing. | `config.py:18` |
| P2-4 | `delete_document` ends with `os.makedirs(persist_dir)` after deleting — dead code. | `embeddings.py:115-116` |
| P2-5 | `ChatResponse` / `SourceInfo` schemas are unused (the endpoint streams instead). | `schemas.py:25-37` |
| P2-6 | Temp file hardcoded to `dir="/tmp"`; use `tempfile.gettempdir()` / default. | `documents.py:36` |
| P2-7 | Re-uploading the same file is allowed and creates an unrelated new `doc_id` (no dedupe); the file input is never reset, so picking the *same* file twice does nothing. | `documents.py:40`, `DocumentUpload.jsx:36-41` |
| P2-8 | DOCX **tables are ignored**; scanned/image PDFs produce 0 chunks and still return `200 {chunks: 0}` with no warning. | `embeddings.py:62-65` |
| P2-9 | Whitespace-only questions pass validation (`min_length=1`) and still bill an LLM call. | `schemas.py:20` |
| P2-10 | No similarity threshold: low-relevance chunks are always injected, so answers can cite irrelevant pages. | `retriever.py:26-36` |
| P2-11 | Retrieved document text is concatenated into the prompt unescaped (prompt-injection surface if you ever ingest untrusted docs). | `rag_chain.py:55` |
| P2-12 | Docker: no restart policy, no frontend healthcheck, backend healthcheck lacks `start_period`. | `docker-compose.yml` |
| P2-13 | `lifespan` re-raises (`except Exception: raise`) — the app refuses to start if Chroma is momentarily unavailable instead of starting degraded. | `main.py:21-25` |
| P2-14 | No `LICENSE` file although the README declares MIT. | repo root |

---

## 6. P3 — polish

- `MAX_HISTORY_MESSAGES` is named for messages but documented as exchanges (P2-1) — rename to `MAX_HISTORY_MESSAGES` + docstring, or make it configurable.
- Version drift: `config.py` says `1.1.0`, `frontend/package.json` says `1.0.0`, latest release is `v1.1.1`. Pick one source of truth.
- `.env.example` is duplicated at the root and in `frontend/`, with different keys.
- No ESLint / Prettier config, no frontend tests, no coverage reporting.
- `README.md` project tree omits `frontend/.env.example`, `.github/workflows/release.yml` behaviour and the new CI jobs.
- `useSSE` never flushes the remainder of `sseBuffer` after the stream ends — a truncated final frame loses the sources payload.

---

## 7. Test coverage gaps

The suite is 6 tests, all happy-path with mocks. **None of the four P0 bugs would be caught.** Highest-value additions:

1. `retriever.semantic_search` — asserts `query_embeddings` (not `query_texts`) and that scores lie in `[0, 1]`.
2. SSE framing — round-trip a token containing `\n\n` through backend frame + client parser.
3. Upload success path (currently only the 413 branch is tested).
4. `POST /api/chat` end-to-end with a fake OpenAI stream, asserting `text/event-stream` and the `__SOURCES__` terminator.
5. `/api/health` when Chroma raises.
6. Frontend: a Vitest + React Testing Library test for code-block rendering (would have caught P0-4).

Recommendation: add `pytest-cov` with a `--cov-fail-under=80` gate once the P0s are fixed.

---

## 8. CI/CD — status and changes made in this branch

**Before this branch:**

| Workflow | Status | Cause |
|---|---|---|
| CI (lint, test, docker-build) | ✅ passing | — |
| CodeQL | ✅ passing | — |
| **Release** | ❌ **failing on every push to `main`** | `__version__` frozen at `1.1.0` → computes `v1.1.1` → tag already exists → `git tag` aborts |

**Changed on this branch:**

1. **`release.yml` rewritten** — version now derived from `__version__` *and* all tags/releases, with collision-skip; changelog written to a file (no heredoc injection); "already released" is a green no-op; `workflow_dispatch` added; `cancel-in-progress` disabled so a release can't be killed mid-flight. Verified end-to-end: `v1.1.2` → no-op → `v1.1.3`.
2. **`ci.yml` hardened** — added a **frontend** job (`npm ci` + `vite build`, previously only exercised inside the Docker build), an **advisory dependency-audit** job (pip-audit + npm audit), pip/npm caching, per-job timeouts and `workflow_dispatch`.
3. **`README.md`** — CI/CD section updated to match reality.

**Still recommended:** `dependabot.yml` (weekly, pip + npm + actions), branch protection requiring the `test` and `frontend` checks, and flipping the audit job from advisory to blocking once §4 P1-8 is addressed.

---

## 9. Suggested order of work

| Priority | Work | Effort |
|---|---|---|
| 1 | Fix P0-1 + P0-2 (retrieval + cosine space) and re-ingest; this is the difference between "works" and "does not work" | ~1 h |
| 2 | Fix P0-3 + P0-4 (SSE framing + react-markdown v10) — makes answers readable | ~1 h |
| 3 | Fix P0-5 (build-time API URL or nginx `/api` proxy) — required for any real deployment | ~30 min |
| 4 | Add the six regression tests in §7 so these cannot silently return | ~2 h |
| 5 | P1-5 / P1-6 (Docker volume permissions, `.dockerignore`) | ~30 min |
| 6 | P1-8 dependency upgrades (pypdf, python-multipart, axios first — directly reachable) | ~2 h |
| 7 | P1-1 / P1-2 / P1-3 / P1-4 (error surfacing, threadpool, streaming upload, batching) | ~3 h |
| 8 | P1-7 auth + rate limiting, then P2 sweep | ~1 day |

---

## 10. Reproduce it yourself

```bash
# P0-1 / P0-2 — wrong embedding function, L2 distances
python - <<'PY'
import chromadb
col = chromadb.PersistentClient(path="/tmp/x").get_or_create_collection("documents")
print(type(col._embedding_function).__name__, "| space:", col.metadata or "l2 (default)")
PY

# P0-3 — newline loss
python - <<'PY'
MARKER="__SOURCES__"; import re
def f(c): return f"data: {c}\n\n"
buf = f("a") + f("\n") + f("b")
out=""
while "\n\n" in buf:
    frame, buf = buf.split("\n\n",1)
    p="\n".join(re.sub(r"^data:\s?","",l) for l in frame.split("\n") if l.startswith("data:"))
    if p: out+=p
print(repr(out), "expected 'a\nb'")
PY

# P0-5 — dead build env
grep -c ARG frontend/Dockerfile          # -> 0

# P1-8 — advisories
pip-audit -r backend/requirements.txt | head -5
cd frontend && npm audit --omit=dev | tail -5
```
