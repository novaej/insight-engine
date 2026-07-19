# Deployment (Fly.io + Neon)

The API deploys to **Fly.io** (always-on, so the in-process monitoring watchdog
runs there) with **Neon** free managed Postgres. GitHub Actions deploys on every
green push to `main`.

## Prerequisites

- A [Fly.io](https://fly.io) account + `flyctl` installed (`brew install flyctl`)
- A [Neon](https://neon.tech) account (free Postgres)
- This repo on GitHub

## 1. Database — Neon

1. Create a Neon project; it provisions a Postgres database.
2. Copy the **direct** connection string (the host **without** `-pooler` — the
   pooled endpoint uses PgBouncer, which breaks asyncpg's prepared statements).
3. Convert it for SQLAlchemy's async driver:
   - scheme `postgresql://` → `postgresql+asyncpg://`
   - replace `?sslmode=require` with `?ssl=require` (asyncpg doesn't understand
     `sslmode`)

   Final form:
   ```
   postgresql+asyncpg://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/DBNAME?ssl=require
   ```
   This one URL is used by both the app and Alembic migrations.

## 2. App — Fly.io

1. Edit [fly.toml](fly.toml): set a unique `app` name and your `primary_region`
   (`fly platform regions` lists them).
2. Create the app: `fly apps create <your-app-name>`.
3. Set secrets (never commit these):
   ```bash
   fly secrets set \
     DATABASE_URL="postgresql+asyncpg://...neon.tech/DBNAME?ssl=require" \
     OPENAI_API_KEY="sk-..." \
     OPENAI_MODEL="gpt-4o-mini" \
     AZURE_TRANSLATOR_KEY="" AZURE_TRANSLATOR_ENDPOINT="" AZURE_TRANSLATOR_REGION="" \
     MAILGUN_API_KEY="..." MAILGUN_DOMAIN="..." MAILGUN_FROM_EMAIL="alerts@yourdomain" \
     MONITORING_TOKEN="$(openssl rand -hex 24)"
   ```
   `MONITORING_ENABLED` and `MONITORING_CRON` are already set in `fly.toml`'s
   `[env]`. Azure vars can stay empty (translation just no-ops).
4. First deploy: `fly deploy`. The `[deploy] release_command` runs
   `alembic upgrade head` against Neon before the app starts.
5. `fly open` to hit `/health`, or `fly logs` to watch the scheduler start.

## 3. Continuous deployment — GitHub Actions

- [.github/workflows/ci.yml](.github/workflows/ci.yml) runs ruff + pytest on every
  push and PR.
- [.github/workflows/deploy.yml](.github/workflows/deploy.yml) runs `fly deploy`
  **after CI succeeds on `main`**.
- Give it access once: create a deploy token with `fly tokens create deploy`, then
  add it to the repo as the **`FLY_API_TOKEN`** GitHub Actions secret
  (Settings → Secrets and variables → Actions).

After that, every green push to `main` migrates + deploys automatically.

## Monitoring in production

Because Fly keeps one machine always running (`min_machines_running = 1`,
`auto_stop_machines = false`), the in-process APScheduler fires the watchdog on
`MONITORING_CRON` (default daily 09:00 UTC) — no external cron needed. Enable
Mailgun (the secrets above) so digests actually send. You can also trigger a
sweep on demand:
```bash
curl -X POST https://<your-app>.fly.dev/monitoring/run \
  -H "X-Monitoring-Token: $MONITORING_TOKEN"
```

> Cost note: an always-on `shared-cpu-1x` / 512 MB machine is inexpensive but may
> exceed Fly's free allowance. If you'd rather let the machine auto-stop, set
> `auto_stop_machines = true` / `min_machines_running = 0` and instead drive
> monitoring from a scheduled GitHub Action that curls `/monitoring/run` (the
> endpoint is built for exactly this).

## Notes

- No CORS middleware is configured. If a browser frontend (Vestio) calls this API
  directly, add `fastapi.middleware.cors.CORSMiddleware` with your frontend origin.
- The single always-on machine means one scheduler instance — correct, no
  duplicate alerts. If you scale to multiple machines, move monitoring to the
  GitHub Action approach so it doesn't fire once per machine.
