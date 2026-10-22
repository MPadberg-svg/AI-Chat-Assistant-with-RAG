# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.2.x | ✅ |
| < 1.2 | ❌ (retrieval was broken; please upgrade) |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Use GitHub's [private vulnerability reporting](https://github.com/MPadberg-svg/AI-Chat-Assistant-with-RAG/security/advisories/new)
if it is enabled for this repository, or contact the maintainer directly.
Include:

- a description of the issue and its impact,
- steps to reproduce,
- the affected version (`/api/health` reports it),
- any suggested remediation.

You can expect an acknowledgement within a few days.

## Deployment notes

The application ships **without authentication** by default, because it is
designed to run locally. Before exposing it to a network:

1. Set `API_TOKEN` to require `Authorization: Bearer <token>` on every API
   route except `/api/health`.
2. Set `RATE_LIMIT_PER_MINUTE` to bound per-client request volume.
3. Set `CLIENT_URL` (and `EXTRA_CLIENT_URLS`) to your real origin so CORS does
   not have to be widened.
4. Terminate TLS in front of the `frontend` container.

Note that `API_TOKEN` is a single shared secret and the rate limiter is
in-process; for multi-replica deployments put auth and rate limiting in a
reverse proxy or gateway.

## Dependency advisories

`pip-audit` and `npm audit` run on every CI build in an advisory job.
`chromadb` currently carries published advisories with **no fix version
available**; it is the vector store and cannot be removed. The frontend
advisories that remain are development-only transitive packages inside the
Tailwind/PostCSS toolchain and never ship in the bundle.
