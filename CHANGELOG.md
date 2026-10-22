# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

GitHub Releases are generated automatically from commit messages; this file
records the notable, user-facing changes.

## [1.3.2] - 2026-10-22

### Changed

- **React 18.3 -> 19.3.** The component tree renders unchanged; a new
  application-level render test covers it.
- **Vite 7.3 -> 8.3 and @vitejs/plugin-react 5 -> 6.** Vite 8 bundles with
  Rolldown, which rejects the object form of `manualChunks`; the chunk split is
  now expressed as a function (portable back to Rollup).
- **GitHub Actions modernised**: `checkout` v4 -> v7, `setup-node` v4 -> v7,
  `setup-python` v5 -> v7, `action-gh-release` v2 -> v3. These are the ESM /
  Node 24 runtimes; no inputs used by this repository were removed.
- `package.json` declares `engines.node >=20.19.0`, the floor Vite 8 requires.

### Added

- `frontend/src/App.test.jsx`: renders the whole application tree and asserts
  the `ErrorBoundary` contract, so a framework upgrade that breaks rendering
  fails the build.

### Not upgraded

- **ESLint stays on 9.** `eslint-plugin-react@7.37.5` only declares support up
  to ESLint 9; ESLint 10 installs only by overriding that peer requirement.

## [1.3.1] - 2026-10-22

### Changed

- **OpenAI SDK upgraded from 1.102.0 to 3.35.1.** The application surface is
  unchanged (`client.embeddings.create`, `client.chat.completions.create` with
  `stream=True`, `response.data[].index/.embedding`,
  `chunk.choices[0].delta.content`), verified against the real SDK rather than
  assumed.
- The `AsyncOpenAI` client is now created once per process instead of once per
  chat request. The previous behaviour leaked an `httpx` connection pool on
  every message.
- Provider failures are classified with the SDK's error hierarchy
  (`RateLimitError`, `APIConnectionError`, `APIError`) and reported with
  specific messages instead of a generic one, and expected API errors are
  logged without a stack trace.

### Added

- `backend/tests/test_openai_contract.py`: contract tests that drive the **real**
  SDK with a mocked HTTP transport, covering request serialisation, response
  parsing, batching, streaming and error mapping. The existing tests replace the
  client classes, so they would have passed on any SDK version; these fail if
  the surface the application relies on changes.

## [1.3.0] - 2026-10-22

### Added

- Hybrid retrieval: BM25 keyword search fused with vector search via reciprocal
  rank fusion. Exact identifiers such as error codes and names are no longer
  lost. Toggle with `HYBRID_SEARCH`.
- Request-scoped logging: every response carries `X-Request-ID` and all log
  lines emitted while handling a request are tagged with it.
- ESLint (React, hooks, refresh rules) and Prettier for the frontend, enforced
  in CI.
- `ErrorBoundary` so a render error shows a recoverable message instead of a
  blank page.
- Community files: `SECURITY.md`, `CONTRIBUTING.md`, Dependabot configuration,
  pull request and issue templates, `.editorconfig`.

### Changed

- The in-flight answer is rendered live by `ChatWindow` instead of being copied
  into the transcript by an effect, removing a re-render per streamed token.
- CI now runs frontend lint, formatting and tests, and reports backend
  coverage.

### Removed

- `CODE_REVIEW.md` (a one-off audit, superseded by this changelog and the code).
- `frontend/.env.example` (duplicated the root `.env.example`).

## [1.2.0] - 2026-10-22

### Fixed

- **Retrieval never worked.** Queries were sent as text, so ChromaDB embedded
  them with its bundled 384-dimension model and compared them against
  1536-dimension OpenAI vectors. Queries are now embedded with the ingestion
  model and sent as vectors.
- **Confidence scores were negative.** The collection defaulted to squared L2
  distance while the code reported `1 - distance`. The collection now uses
  cosine space and scores are clamped to 0..1.
- **Every newline was dropped from streamed answers**, collapsing markdown
  paragraphs, lists and code fences. SSE frames now emit one `data:` line per
  payload line, and a dedicated parser reassembles them.
- **Code blocks rendered as nested `<pre>`.** `react-markdown` v10 removed the
  `inline` prop; block and inline code are now styled via separate overrides.
- **`VITE_API_URL` was ignored**, because Vite inlines it at build time while
  Compose passed it at runtime. It is now a build arg, and nginx proxies `/api`
  so the default configuration is same-origin.
- Chat failures mid-stream now surface as an `error` event instead of silently
  truncating the answer.
- Uploads are streamed to disk and abort at the size limit instead of being
  buffered in memory.
- The container's non-root user can now write the ChromaDB volume.

### Changed

- SSE protocol changed from a `__SOURCES__` text marker to typed events
  (`token`, `sources`, `error`).
- LangChain removed; a small tested recursive splitter replaces it.
- Embedding requests are batched.
- Python dependencies upgraded: 132 known advisories → 5 (all in `chromadb`,
  which has no published fix).
- Frontend production advisories: 12 high → 0.

### Added

- Optional bearer-token authentication (`API_TOKEN`) and per-client rate
  limiting (`RATE_LIMIT_PER_MINUTE`), both off by default.
- `MIN_RELEVANCE_SCORE` to drop weak chunks.
- SHA-256 duplicate detection, DOCX table extraction, filename and chunk counts
  in the sidebar.
- Automatic migration of the pre-1.2 collection into the cosine collection.
- 66 backend tests and 17 frontend tests (from 6 and 0).
- Docker smoke test in CI that boots the compose stack.

## [1.1.1] - 2026-06-04

### Fixed

- Frontend image build hardened around `npm ci`.

## [1.1.0] - 2026-06-04

### Added

- Initial public release: streaming RAG chat, document upload, inline citations,
  Docker Compose deployment, CI, CodeQL and automated releases.
