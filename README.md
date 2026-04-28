# Faceless YT

Multi-tenant SaaS for AI-generated faceless YouTube channel automation.

## Tech stack

- **Backend** (`apps/api`): Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, arq, Clerk JWT auth.
- **Frontend** (`apps/web`): Next.js 15 (App Router), TypeScript, Tailwind, Clerk.
- **Infra**: Postgres 16, Redis 7, MinIO (R2 stand-in for local dev).
- **Deploy target**: Railway (api, worker, web services + managed Postgres + Redis; storage on Cloudflare R2).

## Local development (requires Docker)

```bash
# 1) Bring up infra
docker compose up -d

# 2) Set up backend
cd apps/api
python -m venv .venv && . .venv/Scripts/activate    # or: source .venv/bin/activate (Unix)
pip install -e ".[dev]"
cp .env.example .env                                 # then edit ENCRYPTION_KEY etc.
alembic upgrade head

# 3) Run backend
uvicorn faceless.main:app --reload --port 8000
# (separate terminal) arq faceless.worker.WorkerSettings

# 4) Frontend
cd ../../
pnpm install
cd apps/web
cp .env.example .env.local                           # then add real Clerk dev keys
pnpm dev
```

Visit:
- http://localhost:3000 — marketing
- http://localhost:3000/dashboard — protected (requires sign-in)
- http://localhost:8000/api/docs — OpenAPI / Swagger

## Tests

```bash
cd apps/api && pytest        # backend (unit + integration; requires Postgres + Redis up)
cd apps/web && pnpm typecheck && pnpm lint && pnpm build
```

## Deploy to Railway

See `docs/deployment/railway.md`.

## Documentation

- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans, one per sub-project (P1, P2, …)
