AI Document Q&A API — Specification
Version: 2.0 Status: Active Supersedes: 1.0 (Draft)

0. Changelog from v1.0
Fixed: app/services/ai/embeddings.py imported langchain_ollama.OllamaEmbeddings but the package was never declared in requirements.txt, so any real install crashed on startup (ModuleNotFoundError). Added langchain-ollama==0.2.0 to requirements.
Fixed: hash_password / verify_password passed raw strings straight into bcrypt. bcrypt hard-caps input at 72 bytes and passlib ≥1.7.4 raises ValueError instead of truncating, so any password/passphrase over 72 bytes (easy to hit with passphrases or non-ASCII input) crashed registration and login. Both functions now truncate to 72 bytes before hashing/verifying.
Confirmed bcrypt==4.0.1 pin in requirements is required — bcrypt ≥4.1 removed the __about__ attribute that passlib 1.7.4 reads, breaking backend detection at import time.
Added a frontend (/frontend) — none existed before.
Added deployment guidance beyond Hugging Face Spaces (Section 9).

1. Goal
Production-ready Retrieval Augmented Generation (RAG) backend that lets an authenticated user upload PDF documents, and ask natural-language questions answered from those documents' content, with citations back to source chunks where possible.

2. Tech Stack (as-built)
Layer
Choice
API framework
FastAPI (async), Python 3.12
ORM / DB driver
SQLAlchemy 2.0 (async) + asyncpg
Database
PostgreSQL + pgvector extension
Cache / session store
Redis
AI orchestration
LangChain
LLM/embeddings providers
OpenAI (default), Ollama (local/self-hosted, optional)
Auth
JWT access + refresh tokens, bcrypt password hashing
Migrations
Alembic
Rate limiting
slowapi
Packaging
Docker + docker-compose
Frontend
Static single-page app (vanilla JS, no build step) — frontend/index.html


3. Functional Requirements
3.1 Authentication
POST /auth/register — create account (email + password).
POST /auth/login — returns {access_token, refresh_token}.
POST /auth/refresh — rotates refresh token, returns new pair.
POST /auth/logout — revokes a refresh token.
GET /users/me — current user profile.
Every route except register/login/refresh/health requires a valid Bearer access token.
Passwords are hashed with bcrypt (input truncated to 72 bytes per bcrypt's own limit, applied consistently at hash and verify time).
3.2 Document Upload
POST /documents/upload — multipart PDF upload.
Accepted type: PDF only.
Max size: 25MB (rejected with 4xx above that, enforced both client-side in the frontend and server-side).
Pipeline on upload: store file → extract text → chunk → embed → write vectors to pgvector → mark document ready (or failed with a reason).
GET /documents — paginated list of the current user's documents.
GET /documents/{id} — single document metadata.
DELETE /documents/{id} — removes the document, its chunks, and its embeddings.
3.3 Chat / Q&A
POST /chat — body {document_id, question, chat_id?, stream?}.
stream=false (default): returns {chat_id, answer, ...} as JSON.
stream=true: returns text/event-stream SSE, one data: {"token": "..."} event per generated token, terminated by an event: done.
GET /chat/history — paginated list of the user's chat conversations.
GET /chat/{chat_id}/messages — full message history for one conversation.
Answers are grounded via top-k similarity search (top_k, default 5) against the target document's chunks; the LLM is instructed to answer only from retrieved context.
3.4 Health
GET /health — checks DB connectivity and Redis connectivity independently, returns ok / degraded plus per-dependency status. Used for container orchestrators' liveness/readiness probes and by the frontend's status pill.

4. Non-Functional Requirements
Rate limiting: configurable requests/minute per client (rate_limit_per_minute, default 60) via slowapi, returns 429 with Retry-After.
CORS: explicit allow-list via cors_origins env var (comma-separated). Must include the frontend's deployed origin in production — wildcard * is not safe with allow_credentials=True and is rejected by browsers in that combination anyway.
Structured logging: structlog, JSON in production, human-readable in debug mode.
Errors: all handled exceptions return a consistent {detail: "..."} JSON body via app/api/error_handlers.py; unhandled exceptions are logged and return a generic 500 (no stack traces leaked to clients).
Config: all runtime configuration via environment variables / .env, no secrets committed.
Migrations: schema changes go through Alembic; alembic upgrade head must be run before first boot against a fresh database.

5. Data Model (high level)
users — id, email (unique), hashed_password, timestamps.
refresh_tokens — id, user_id, token hash, expires_at, revoked_at.
documents — id, owner_id, filename, status (processing/ready/failed), size, timestamps.
document_chunks (pgvector) — id, document_id, content, embedding vector, chunk_index.
chats — id, owner_id, document_id, title, timestamps.
messages — id, chat_id, role (user/assistant), content, timestamps.

6. Document Processing Pipeline
Upload (PDF, <=25MB)
  -> Validate MIME + size
  -> Store file (local disk in dev; object storage recommended in prod, see Section 9)
  -> Extract text (pypdf)
  -> Chunk (chunk_size=500, chunk_overlap=100, configurable)
  -> Embed each chunk (OpenAI text-embedding-3-small, or Ollama nomic-embed-text)
  -> Upsert vectors into pgvector
  -> Mark document ready

Failure at any stage marks the document failed and stores a reason; it does not leave a partially-embedded document in a ready state.

7. AI Provider Configuration
llm_provider / embedding_provider env vars select openai or ollama independently.
OpenAI path needs openai_api_key.
Ollama path needs a reachable ollama_base_url (defaults to a ollama service hostname, which only resolves inside the bundled docker-compose network — see Section 9 for standalone hosting).

8. Testing
pytest with pytest-asyncio, SQLite (aiosqlite) as the test DB — no live Postgres/Redis required to run the suite.
Current coverage: auth (register/login/refresh/logout/me), password hashing round-trip, chat service, document service, text processing/chunking.
All 21 tests pass as of this revision (python -m pytest -q).

9. Deployment (see docs/DEPLOYMENT.md for full walkthroughs)
Supported targets, in order of how closely they match the existing Docker/Postgres/Redis architecture:
Railway — one-click from docker-compose.yml-equivalent services; managed Postgres + Redis add-ons; simplest lift-and-shift from Hugging Face.
Render — Docker web service + managed Postgres + managed Redis (or Upstash Redis).
Fly.io — fly launch against the existing Dockerfile; Fly Postgres or external managed Postgres; good for low-latency multi-region.
AWS (ECS Fargate / App Runner) — for teams already on AWS; RDS Postgres (with pgvector) + ElastiCache Redis.
A VPS (Hetzner/DigitalOcean) + the existing docker-compose.yml — cheapest, most control, most ops burden; this is the only option that runs the repo's compose file essentially unmodified.
Frontend: static, so it can be hosted anywhere that serves a single HTML file — Vercel, Netlify, Cloudflare Pages, GitHub Pages, or the same VPS/Nginx as the API. It only needs the API's base URL, entered in-app or via a build-time env substitution.

10. Out of Scope (v2.0)
Multi-document / cross-document Q&A in a single chat.
Non-PDF formats (docx, txt, html).
Team/workspace accounts (current model is single-user ownership only).
Admin dashboard.

