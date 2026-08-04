# AI Document Q&A API (RAG)

A production-ready Retrieval Augmented Generation (RAG) backend built with FastAPI. Upload PDF documents, ask questions about them, and get context-aware answers with cited sources.

## Stack

- **API**: FastAPI (async), Python 3.12+
- **AI**: LangChain, OpenAI API (default) or local Llama via Ollama
- **Database**: PostgreSQL + pgvector
- **Cache**: Redis
- **Auth**: JWT (access + refresh tokens)
- **Deployment**: Docker / Docker Compose

## Architecture

Clean architecture, enforced top to bottom:

```
Routes (app/api)        -> HTTP only, no business logic
   |
Services (app/services) -> business logic, orchestration
   |
Repositories (app/repositories) -> database access only
   |
Models (app/models)     -> SQLAlchemy ORM
```

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY (or switch LLM_PROVIDER/EMBEDDING_PROVIDER to ollama)

docker compose up --build
```

This starts:
- `api` on http://localhost:8000 (docs at `/docs`)
- `postgres` (with pgvector) on 5432
- `redis` on 6379
- `ollama` (optional, `--profile local-llm`) on 11434

The API container runs `alembic upgrade head` automatically before starting.

To run with local models instead of OpenAI:

```bash
docker compose --profile local-llm up --build
# then set LLM_PROVIDER=ollama and EMBEDDING_PROVIDER=ollama in .env
# and pull models inside the ollama container:
docker exec -it rag_ollama ollama pull llama3
docker exec -it rag_ollama ollama pull nomic-embed-text
```

## Local development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# point DATABASE_URL / REDIS_URL at local instances

alembic upgrade head
uvicorn app.main:app --reload
```

Requires a local PostgreSQL with the `pgvector` extension available, and Redis.

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create a new user |
| POST | `/auth/login` | No | Get access/refresh tokens |
| POST | `/auth/refresh` | No | Rotate refresh token |
| POST | `/auth/logout` | No | Revoke a refresh token |
| GET | `/users/me` | Yes | Current user profile |
| POST | `/documents/upload` | Yes | Upload a PDF (multipart) |
| GET | `/documents` | Yes | List documents (paginated) |
| GET | `/documents/{id}` | Yes | Document metadata |
| DELETE | `/documents/{id}` | Yes | Delete a document |
| POST | `/chat` | Yes | Ask a question (`stream: true` for SSE) |
| GET | `/chat/history` | Yes | List conversations |
| GET | `/chat/{chat_id}/messages` | Yes | Full message history for a chat |
| GET | `/health` | No | Liveness/dependency check |

Full interactive docs (OpenAPI) are served at `/docs` once the API is running.

## RAG pipeline

```
Upload PDF -> Extract text -> Chunk (500 tokens, 100 overlap)
           -> Generate embeddings -> Store in pgvector -> Ready for search
```

On `/chat`:
1. Question is embedded with the same embedding model.
2. Top-k (default 5) chunks are retrieved via cosine similarity in pgvector.
3. A prompt is built from the retrieved chunks (temperature 0).
4. The LLM answer, along with the source chunks and similarity scores, is returned. Streaming answers use Server-Sent Events.

## Configuration

All configuration is via environment variables — see `.env.example`. Key knobs:

- `LLM_PROVIDER` / `EMBEDDING_PROVIDER`: `openai` or `ollama`
- `CHUNK_SIZE` / `CHUNK_OVERLAP`: chunking parameters (tokens)
- `TOP_K`: number of chunks retrieved per question
- `MAX_UPLOAD_SIZE_MB`: upload limit (default 25MB, PDF only)
- `RATE_LIMIT_PER_MINUTE`: per-client rate limit

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

Unit tests cover services with mocked repositories/AI providers; integration tests exercise the API with an in-memory-style test database session.

## Security notes

- Passwords hashed with bcrypt, never stored in plaintext.
- JWT access tokens expire in 15 minutes; refresh tokens in 7 days and are rotated + revocable on refresh/logout.
- All document, chat, and embedding access is scoped to the authenticated user (multi-tenant isolation) at the repository query level.
- Uploads are validated for content type, extension, and size before processing.
- Rate limiting is applied per client IP.
- Secrets are read from environment variables only — never hardcoded.

## Project docs

The original specification, engineering rules, architecture decisions, and blocker tracking that this build follows are in `.specs/`.

## Known limitations / future work

See `.specs/spec.md` "Future Features" and `.specs/blocked.md` for the full list, including: DOCX/OCR support, hybrid search, multi-document chat, background job processing for very large PDFs, admin dashboard, and OpenTelemetry-based monitoring.
