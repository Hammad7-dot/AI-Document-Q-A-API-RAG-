# Deployment Guide (non–Hugging Face)

The app is a standard Dockerized FastAPI service with Postgres (pgvector) + Redis. Any host that
runs Docker containers and gives you a Postgres instance with the `vector` extension works.
Below are four good options, cheapest/simplest first.

## Prerequisites (all options)

- A Postgres 15+ database with the `pgvector` extension available (`CREATE EXTENSION vector;`).
- A Redis instance.
- An OpenAI API key (or a reachable Ollama server if you're going fully local).
- Env vars from `.env.example`, filled in for production — at minimum:
  `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY` (generate with `openssl rand -hex 32`),
  `OPENAI_API_KEY`, `CORS_ORIGINS` (your frontend's real origin).

Run migrations once against the target DB before first traffic:
```bash
alembic upgrade head
```

---

## Option 1 — Railway (easiest)

1. Push this repo to GitHub.
2. In Railway: New Project → Deploy from GitHub repo → select this repo (it will detect the
   `Dockerfile`).
3. Add a **PostgreSQL** plugin (Railway's Postgres supports pgvector via `CREATE EXTENSION`).
4. Add a **Redis** plugin.
5. In the API service's Variables tab, set the env vars above, using Railway's reference syntax
   to pull `DATABASE_URL` / `REDIS_URL` from the plugins automatically.
6. Add a one-off "Run command" deploy or a pre-deploy hook: `alembic upgrade head`.
7. Railway assigns a public HTTPS URL — set that as the frontend's API base.

## Option 2 — Render

1. New → Web Service → connect the repo → Render detects the `Dockerfile`.
2. New → PostgreSQL (enable pgvector: Render's managed Postgres supports it; run
   `CREATE EXTENSION IF NOT EXISTS vector;` via their SQL shell).
3. New → Redis (or use Upstash Redis and paste its URL into `REDIS_URL`).
4. Set env vars in the web service's Environment tab.
5. Add a "Pre-Deploy Command": `alembic upgrade head`.
6. Render gives you a `*.onrender.com` HTTPS URL.

## Option 3 — Fly.io

```bash
fly launch            # detects the Dockerfile, creates fly.toml
fly postgres create   # or bring your own managed Postgres with pgvector
fly redis create       # Upstash-backed Redis via Fly
fly secrets set JWT_SECRET_KEY=... OPENAI_API_KEY=... DATABASE_URL=... REDIS_URL=... CORS_ORIGINS=...
fly deploy
fly ssh console -C "alembic upgrade head"
```
Good choice if you want the container close to users in a specific region.

## Option 4 — Your own VPS (Hetzner / DigitalOcean) with the existing docker-compose.yml

This is the only option that runs the repo essentially unmodified — same Postgres+Redis+API
topology as local dev.

```bash
# on the server
git clone <your fork>
cd AI-Document-Q-A-API-RAG-
cp .env.example .env   # fill in real secrets
docker compose up -d --build
docker compose exec api alembic upgrade head
```
Put Nginx or Caddy in front for TLS (Caddy is one line: `caddy reverse-proxy --to :8000`).

---

## Frontend hosting

`frontend/index.html` is static and has no build step. Any of these work:

- **Vercel / Netlify / Cloudflare Pages**: drag-and-drop the `frontend/` folder, or connect the
  repo and set the root directory to `frontend`.
- **GitHub Pages**: enable Pages on the repo, point it at `frontend/`.
- Same VPS as the API: serve it as a static file via Nginx alongside the reverse proxy.

The frontend has no build-time config — the API base URL is set in the UI itself (top-right
field, persisted in `localStorage`), so the same static build works against any backend.

---

## Production checklist

- [ ] `JWT_SECRET_KEY` is a real random secret, not the `change-me` default.
- [ ] `DEBUG=false`, `ENVIRONMENT=production`.
- [ ] `CORS_ORIGINS` is your exact frontend origin, not `*`.
- [ ] Postgres has the `vector` extension created.
- [ ] `alembic upgrade head` has been run against the target DB.
- [ ] File storage: local disk (`upload_dir`) does not persist across redeploys on most PaaS —
  for Railway/Render/Fly, mount a persistent volume or switch to object storage (S3-compatible)
  before relying on uploaded files surviving a redeploy.
- [ ] Rate limit and CORS values reviewed for your real traffic.
