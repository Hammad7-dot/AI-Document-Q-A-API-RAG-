# Roadmap: hardening Docket for real use

This is a working RAG backend, not a toy. Auth, background processing,
provider-swapping, and a handful of gnarly production bugs are already
handled. What's below is what's left before it's something you'd trust with
real users and real documents, ordered by how much it'll hurt if you skip it.

Each item says **why it matters**, not just what to do — skip anything whose
reasoning doesn't apply to how you're actually running this.

---

## 1. Data loss risk: uploaded PDFs are not persisted on Railway

**The problem.** `UPLOAD_DIR` (`./storage/documents`) is a plain path inside
the container's filesystem. `docker-compose.yml` mounts a named volume for
it locally, but nothing in the Railway deployment attaches persistent
storage to that path. Every redeploy — including every `git push` to `main`,
since that's your deploy trigger — gives the container a fresh filesystem.

**The consequence.** The Postgres rows and pgvector embeddings for a
document survive redeploys (managed Postgres is separate storage), but the
original PDF file does not. Anything that ever needs to re-read the source
file — reprocessing after a provider switch, OCR added later, "view
original document," audit — will find nothing there. Given how many
redeploys happened during this session alone, it's likely every PDF
uploaded so far is already gone even though the app still lists them as
`ready`.

**The fix.** Move uploads to object storage: Cloudflare R2 (pairs naturally
since your frontend's already on Workers), S3, or Railway's own volume
feature if you want to stay filesystem-based. This is a real code change
(swap local file I/O for a storage client in `document_service.py`), not a
config flag — budget time for it accordingly.

---

## 2. No CI/CD

**The problem.** There's no `.github/workflows` directory. Every push to
`main` goes straight to production with nothing checking it first — not
even that the app imports cleanly, let alone that the test suite passes.
This session shipped several multi-file fixes directly to `main`; that
worked because I was testing manually against the live API each time, but
that doesn't scale and won't be available once I'm not in the loop.

**The fix.** A single GitHub Actions workflow that runs `pytest` (and
ideally `ruff`/`mypy` if you want them) on every push and PR is most of the
value here. Add branch protection requiring it to pass before merging to
`main` once it exists.

---

## 3. Test suite gaps

**What exists today.** `tests/` covers auth against an in-memory SQLite DB
(per `conftest.py`, deliberately — pgvector's `Vector` type isn't supported
on SQLite) and has service-level unit tests for documents/chat with mocked
repositories.

**What's untested.**
- The background-task upload flow added this session (`BackgroundTasks`,
  the fresh-session pattern in `process_document_background`).
- The per-route rate-limit decorators that replaced `SlowAPIMiddleware`.
- The two startup checks (`validate_embedding_dimension`, the JWT
  production guard) — both are exactly the kind of logic that should have
  a test locking in the exact failure message and trigger condition.
- Anything that actually touches pgvector, since the test DB can't run it.
  A real integration test suite needs a Postgres+pgvector service (a
  `docker-compose.test.yml` or a service container in CI) rather than
  SQLite.

**Also worth knowing:** I could not run the existing suite during this
session — the shared local Python environment had a hard version conflict
between this project's `langchain==0.3.x` pin and other `langgraph`-based
tooling already installed there. If you or a contributor hits the same
thing, it means this project needs its own virtualenv, not that the code
is broken.

---

## 4. Provider resilience

**What's live now.** `EMBEDDING_PROVIDER=cohere` on a trial key that's
already exhausted its quota mid-session. There's no fallback — when the
configured provider is down or rate-limited, every upload and every
question fails.

**What's dead code.** The Google Gemini embedding provider
(`GoogleEmbeddingProvider`) is wired up but non-functional: Google's newer
`AQ.`-prefixed AI Studio keys don't authenticate correctly against
`langchain-google-genai`'s current (deprecated `google-generativeai`)
backend, confirmed against Google's own SDK, not just this app's code. It'll
stay broken until either `langchain-google-genai` moves to the new
`google-genai` SDK or Google fixes the compatibility gap. Either fix it
properly at that point, or remove it and the `google-genai` docs to stop it
looking like a working option.

**The fix, in order of value:**
1. A paid key (any provider) so quota isn't a recurring fire drill.
2. A fallback chain — if the primary embedding/LLM provider errors, try a
   secondary before failing the document. This is the highest-leverage
   change here: it turns "provider had a bad day" from a user-facing outage
   into a non-event.
3. Per-user or global usage tracking, so a single large upload can't run up
   an unbounded provider bill.

---

## 5. Refresh token reuse detection

**What's already right.** Refresh tokens do rotate — each `/auth/refresh`
call revokes the used token and issues a new pair
(`auth_service.py::refresh`). That part's solid.

**What's missing.** If a revoked (already-used) refresh token is presented
again — the standard signal that a token was stolen and both the attacker
and the legitimate user are now racing to use it — the current code just
returns 401 for that one request. It doesn't revoke the rest of that user's
active sessions. Real reuse detection would: on catching a revoked-token
reuse, revoke every other outstanding refresh token for that user and force
re-login everywhere. Low urgency for a demo project, real gap for anything
with actual user accounts.

---

## 6. Rate limiter behind Railway's proxy

**The question, not yet the confirmed answer:** `slowapi`'s
`get_remote_address` reads `request.client.host`, and nothing in the
Dockerfile's `uvicorn` command (`--proxy-headers`,
`--forwarded-allow-ips`) tells it to trust `X-Forwarded-For` from Railway's
edge proxy. If Railway doesn't already rewrite the peer address
transparently, every request looks like it's coming from the same
internal IP, and the per-client rate limit effectively becomes one shared
global limit across every user. Worth confirming directly (log
`request.client.host` for a few real requests) before assuming either way
— I flagged it as a risk here rather than a fix because I haven't verified
Railway's actual proxy behavior.

---

## 7. Frontend leaves working backend features unused

The backend already supports two things the frontend never uses:
- **SSE streaming** (`stream: true` on `/chat`) — the frontend always
  sends `stream: false` and waits for the full answer. Wiring up the
  `EventSource`/fetch-stream path would make answers feel much faster to
  start reading.
- **Chat history** (`GET /chat/history`, `GET /chat/{id}/messages`) — fully
  implemented server-side, not surfaced in the UI at all. Right now every
  document selection starts a fresh conversation with no way to revisit an
  old one.

Both are additive frontend work against existing, tested endpoints — no
backend changes needed.

---

## 8. Smaller items worth a pass

- **pgvector index tuning.** `ivfflat ... WITH (lists = 100)` is a fixed
  guess. The standard heuristic is `lists ≈ sqrt(row_count)` for smaller
  tables; revisit once there's a realistic amount of data, since a
  mistuned `lists` value hurts both index build time and query recall.
- **OCR.** Scanned/image-only PDFs currently fail cleanly with "no
  extractable text found" rather than silently indexing nothing — that
  part's fine — but there's no path to actually handle them. Worth a
  decision on whether that's in scope at all before building it.
- **Chunk sizing is character-based, not token-based.** `chunk_text()`
  approximates tokens as `chars / 4`. Fine for English prose, drifts for
  code-heavy or non-English documents. A real tokenizer-based splitter
  would be more precise if chunk quality ever becomes a visible problem.
- **Alembic runs on every container boot** (`alembic upgrade head &&
  uvicorn ...` in the Dockerfile `CMD`). Fine at one replica; if this ever
  scales to multiple instances restarting concurrently, migrations should
  move to a separate release step instead of racing inside every
  container's startup.
- **`ENVIRONMENT` isn't set to `production` on Railway.** The JWT
  placeholder-secret guard added this session only fires when
  `ENVIRONMENT=production` — right now it's dev-mode by default and
  therefore inert. Set it (after confirming `JWT_SECRET_KEY` is already a
  real secret, since the app will refuse to boot otherwise).
- **No centralized error tracking.** Every bug this session was diagnosed
  by pasting raw Railway logs into chat. A Sentry (or similar) integration
  would surface the same tracebacks automatically, with request context,
  the moment they happen — not the next time someone thinks to check logs.

---

## Suggested order of attack

If tackled roughly in priority order: **(1) object storage** first, since
it's actual data loss happening right now on every deploy. Then **(2) CI**
before making more changes, since it's what makes every fix after this one
safer to ship. Then **(4) provider fallback**, since a single exhausted
trial key currently means total downtime. Everything else is real but not
urgent — pick based on whether you're optimizing for a demo, a portfolio
piece, or an actual multi-user deployment, since that changes which of the
smaller items (6, 7, 8) actually matter.
