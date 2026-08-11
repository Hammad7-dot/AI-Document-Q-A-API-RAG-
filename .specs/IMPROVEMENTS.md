# Improvement Recommendations

Ordered roughly by impact vs. effort. Items in "Fixed" were bugs found and corrected as part of
this review; the rest are suggestions.

## Fixed in this pass

- **Missing `langchain-ollama` dependency** — `app/services/ai/embeddings.py` imports it but it
  was absent from `requirements.txt`, so a real `pip install -r requirements.txt` followed by
  `uvicorn app.main:app` would crash on import before serving a single request. Added the pin.
- **bcrypt 72-byte crash** — `hash_password`/`verify_password` fed raw strings straight to bcrypt.
  Any password over 72 bytes (long passphrases, or shorter strings with multi-byte UTF-8
  characters) raised `ValueError` instead of registering/logging the user in. Now truncated
  consistently before hash and verify, matching bcrypt's own documented behavior.

## Recommended next

### Storage
- File uploads are written to local disk (`upload_dir`). This does not survive redeploys or scale
  past one instance. Move to S3-compatible object storage (S3, R2, Backblaze B2) behind a small
  storage abstraction so local disk remains an option for dev only.

### Security
- Rotate `JWT_SECRET_KEY` handling: currently a single symmetric secret in `.env`. For multi-instance
  deployments, this is fine as long as it's the same value everywhere — worth documenting explicitly
  (it already needs to be, but a comment near the setting would prevent a footgun).
- Add password strength validation server-side (length, not just presence) — currently only
  presence is enforced.
- Consider short-lived access tokens are already 15 min (good); confirm refresh token rotation
  invalidates the old refresh token (revoke-on-use) to limit replay if one leaks.
- Add per-user rate limits (currently global/IP-based via slowapi) so one user can't exhaust the
  shared limit for others behind a shared NAT/proxy.

### Reliability
- Document processing (extract → chunk → embed) happens inline in the upload request in the
  current design intent per the spec pipeline. For larger PDFs this risks request timeouts.
  Consider moving it to a background task (`BackgroundTasks` or a queue like Celery/RQ/Arq) with
  the document staying in `processing` status until done, and the frontend polling
  `GET /documents/{id}` for status.
- Add retry/backoff around the embedding API call specifically (network blips to OpenAI) — the
  `tenacity` dependency is already present, confirm it's wired into the embedding call path.

### Observability
- `/health` checks DB and Redis; consider adding a `/health/ready` vs `/health/live` split for
  Kubernetes-style orchestrators, since "ready" (can serve traffic) and "live" (process hasn't
  hung) have different failure responses.
- Structured logs exist (`structlog`) — add a request-id middleware so a single user-facing error
  can be traced through logs.

### Product
- Multi-document chat (ask across a document set, not just one) is a common ask for this kind of
  tool — currently out of scope per the spec, worth prioritizing if user demand shows up.
- Support additional formats (.docx, .txt, .md) — the pipeline already isolates text extraction
  behind one step, so this is mostly a new extractor, not a redesign.
- Source citations in the chat answer (which chunk/page the answer came from) — improves trust and
  is usually cheap to add since the retrieval step already has the chunk metadata.

### Frontend (new — see `frontend/index.html`)
- Currently a single static HTML/JS file with no framework, to keep it deployable anywhere with
  zero build step. If the product grows (multi-document chat, citations UI, streaming token-by-token
  rendering), consider migrating to a small React/Vite app — the API contract won't need to change.
- SSE streaming (`stream=true` on `/chat`) is supported by the backend but the current frontend
  uses the non-streaming path for simplicity; wiring up `EventSource`/fetch-stream reading is a
  good next increment for perceived latency.

### Testing
- Current suite runs against SQLite and covers unit/service-level behavior well. Consider adding
  a smoke test that runs against a real Postgres+pgvector (e.g. via `testcontainers`) in CI, since
  pgvector-specific query behavior (`<->` distance operators, index usage) isn't exercised by
  SQLite at all.
