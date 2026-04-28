# Deploying Faceless YT to Railway

This guide walks you from a fresh repo to three running Railway services (`api`, `worker`, `web`) backed by Railway-managed Postgres and Redis, with assets stored in Cloudflare R2.

## Prerequisites you must obtain yourself

1. **Railway account** — sign up at https://railway.com
2. **GitHub repo** — push this codebase to a GitHub repo Railway can pull from.
3. **Cloudflare R2 bucket + API token** — for asset storage. Sign up at https://dash.cloudflare.com → R2 → Create bucket + Manage API tokens (give it Object Read & Write on your bucket). Note the S3-compatible endpoint URL like `https://<account-id>.r2.cloudflarestorage.com`.
4. **Clerk application** — sign up at https://clerk.com → create an app → grab `pk_test_*` (publishable) and `sk_test_*` (secret) keys. From the JWT settings, note the **Issuer URL** (looks like `https://<app-id>.clerk.accounts.dev`) and decide your **Audience** (typically your front-end origin URL once it's deployed, e.g., `https://web-production-xxxx.up.railway.app`).
5. **Generate `ENCRYPTION_KEY`** — a base64-encoded 32-byte secret used to encrypt OAuth tokens at rest:
   ```bash
   python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
   ```

## Step 1 — Push to GitHub

```bash
cd faceless-yt
gh repo create faceless-yt --private --source=. --push
# OR manually:
# git remote add origin git@github.com:<you>/faceless-yt.git
# git push -u origin master
```

## Step 2 — Create Railway project + database addons

Using the Railway CLI (install: `npm i -g @railway/cli`, then `railway login`):

```bash
# From inside the cloned repo
railway init        # create a new project; pick a name
railway link        # link the current dir to the project
```

In the Railway dashboard for your new project:
1. Click **+ New** → **Database** → **Add PostgreSQL**.
2. Click **+ New** → **Database** → **Add Redis**.

Railway exposes their connection strings as service variables (`postgres.DATABASE_URL`, `redis.REDIS_URL`) that other services reference.

## Step 3 — Create the `api` service

1. **+ New** → **GitHub Repo** → pick `faceless-yt`.
2. In the new service's **Settings**:
   - **Root Directory**: leave at `/` (we want the Dockerfile context to include packages/, lockfile, etc.)
   - **Config-as-code**: set **Config Path** to `apps/api/railway.json`. (This tells Railway to use that service-specific config.)
3. **Variables** tab — set:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   S3_BUCKET=<your R2 bucket name>
   S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
   S3_ACCESS_KEY=<R2 API token access key>
   S3_SECRET_KEY=<R2 API token secret>
   S3_REGION=auto
   CLERK_JWT_ISSUER=https://<app-id>.clerk.accounts.dev
   CLERK_JWT_AUDIENCE=https://<your web service URL once known>
   ENCRYPTION_KEY=<from prereq step 5>
   ENVIRONMENT=prod
   LOG_LEVEL=info
   CORS_ALLOW_ORIGINS=https://<your web service URL once known>
   ```
   The `${{...}}` references pull live from the Postgres/Redis service variables.
4. **Networking** → **Generate Domain** to expose the service publicly. Note the URL (e.g. `https://api-production-abcd.up.railway.app`).
5. Trigger a deploy (push a commit, or click **Deploy**). Watch the build logs — `start-api.sh` runs `alembic upgrade head` before `uvicorn`, so the first deploy migrates the database automatically.
6. Once green, hit `https://<api-url>/api/v1/health` — expect `{"status":"ok","version":"0.0.0"}`.

## Step 4 — Create the `worker` service

Same repo, **separate service** so it scales independently.

1. **+ New** → **Empty Service** → name it `worker`.
2. **Settings** → **Source** → connect the same GitHub repo `faceless-yt`.
3. **Settings** → **Config Path** → `apps/api/railway.worker.json` (this overrides the start command to run arq instead of uvicorn).
4. **Variables** — copy the same variables you set on `api`. The fastest path: in Railway's dashboard, on the api service, copy variables, then paste into worker.
5. Deploy. Worker's start command will be `arq faceless.worker.WorkerSettings`. It does not expose an HTTP port. Logs should show `worker.startup`.

## Step 5 — Create the `web` service

1. **+ New** → **GitHub Repo** → pick `faceless-yt` again.
2. **Settings** → **Config Path** → `apps/web/railway.json`.
3. **Variables**:
   ```
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<Clerk pk_test_...>
   CLERK_SECRET_KEY=<Clerk sk_test_...>
   NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
   NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
   NEXT_PUBLIC_API_BASE_URL=https://<your api URL>/api/v1
   ```
4. **Networking** → **Generate Domain** → note the web URL.
5. Now go back to the **api** service and update `CLERK_JWT_AUDIENCE` and `CORS_ALLOW_ORIGINS` to use the web URL.
6. Redeploy api so the new env vars take effect.

## Step 6 — Verify end-to-end

- `https://<api-url>/api/v1/health` → `{"status":"ok"}`
- `https://<api-url>/api/docs` → Swagger UI
- `https://<web-url>/` → marketing page
- `https://<web-url>/sign-up` → Clerk sign-up
- After signing up: `https://<web-url>/dashboard` → "Signed in as user_..."
- Manual `/me` test:
  ```bash
  # In Clerk dashboard, generate a test JWT for your user via the "Sessions" page
  # OR copy the __session cookie from a logged-in browser and decode the JWT
  curl -H "Authorization: Bearer <token>" https://<api-url>/api/v1/me
  # Expect: {"id":"...","email":"...","credit_balance":0}
  ```

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `alembic upgrade head` fails on first deploy with "could not connect" | DATABASE_URL not yet propagated | Wait for Postgres addon to finish provisioning, redeploy |
| `pip install` fails on `asyncpg`/`cryptography` wheel | wheel missing for build platform | Already on `python:3.12-slim` which has wheels — if it still fails, bump versions in `apps/api/pyproject.toml` |
| `web` build fails: "Couldn't find Clerk publishable key" | NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY not set as a build-time arg | Already wired via Dockerfile ARG, but Railway sets vars as runtime env. Add it to **Service Variables** with name prefixed `NIXPACKS_` if needed, or pass via Railway build args (Settings → Build → Build Args) |
| 401 from `/me` with valid Clerk token | `CLERK_JWT_AUDIENCE` mismatch | Confirm the audience claim in your JWT matches the env var on api |
| Worker doesn't pick up jobs | `REDIS_URL` not shared between api and worker | Both services must reference `${{Redis.REDIS_URL}}` |

## Cost expectations (rough, post-trial)

- Postgres + Redis (small): ~$10/mo combined
- 3 services (api/worker/web) each <512MB RAM idle: ~$5/mo each = $15/mo
- Total Railway floor: **~$25/mo idle**, scales with usage
- Cloudflare R2: $0.015/GB stored, **$0 egress** — typically <$1/mo until significant volume

## What's still missing (filled in by later sub-projects)

- Stripe billing → P2
- AI provider keys (OpenAI, Kling, ElevenLabs) → P3
- YouTube OAuth credentials + refresh-token storage → P4
- Sentry DSN, Prometheus/Grafana → P7
