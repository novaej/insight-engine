# Deployment (Render + Neon)

The API deploys to **Render** (free web service) with **Neon** free managed
Postgres. GitHub Actions gates deploys behind CI and drives the monitoring
watchdog.

Because Render's free web service **sleeps after ~15 min of inactivity**, the
in-process scheduler is disabled and monitoring is triggered by a scheduled
GitHub Action that first wakes the service, then runs the sweep.

## 1. Database — Neon

1. Create a Neon project (provisions Postgres).
2. Copy the **direct** connection string (host **without** `-pooler` — the pooled
   endpoint's PgBouncer breaks asyncpg's prepared statements).
3. Convert it for SQLAlchemy's async driver:
   - scheme `postgresql://` → `postgresql+asyncpg://`
   - replace `?sslmode=require` with `?ssl=require`

   ```
   postgresql+asyncpg://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/DBNAME?ssl=require
   ```
   Used by both the app and Alembic migrations.

## 2. App — Render

Create the service from the blueprint: Render dashboard → **New → Blueprint** →
pick this repo. [render.yaml](render.yaml) defines a free Python web service that
installs with `pip install -e .` and starts with
`alembic upgrade head && uvicorn …` (migrations run at start since the free tier
has no pre-deploy hook).

Then set the secret env vars (dashboard → the service → **Environment**):

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | the Neon URL from step 1 |
| `OPENAI_API_KEY` | your OpenAI key (blank ⇒ no AI explanations) |
| `MAILGUN_API_KEY` / `MAILGUN_DOMAIN` / `MAILGUN_FROM_EMAIL` | for alert emails |
| `MONITORING_TOKEN` | `openssl rand -hex 24` — guards `/monitoring/run` |

`OPENAI_MODEL`, `MONITORING_ENABLED=false`, and the (blank) `AZURE_*` vars are
already declared in `render.yaml`.

## 3. GitHub Actions

Three workflows:

| Workflow | Trigger | Needs | Purpose |
|----------|---------|-------|---------|
| [ci.yml](.github/workflows/ci.yml) | push to main, PRs | — | ruff + pytest |
| [deploy.yml](.github/workflows/deploy.yml) | after CI succeeds on main | secret `RENDER_DEPLOY_HOOK_URL` | trigger a Render deploy |
| [monitoring.yml](.github/workflows/monitoring.yml) | daily 09:00 UTC (+ manual) | var `APP_URL`, secret `MONITORING_TOKEN` | wake the service, run the sweep |

Set these in GitHub → **Settings → Secrets and variables → Actions**:

- **Secret `RENDER_DEPLOY_HOOK_URL`** — Render dashboard → the service →
  **Settings → Deploy Hook** → copy the URL. Deploy stays off on push
  (`autoDeploy: false`), so this GitHub-Actions-after-CI path is the only deploy
  trigger.
- **Variable `APP_URL`** — your Render URL, e.g. `https://insight-engine.onrender.com`
  (no trailing slash).
- **Secret `MONITORING_TOKEN`** — the **same value** you set in Render, so the
  cron's `X-Monitoring-Token` header matches.

After that: push to `main` → CI runs → if green → Render deploys. The monitoring
cron runs daily, waking the service (polls `/health` for up to ~5 min) before
POSTing `/monitoring/run`.

Trigger a sweep manually anytime: Actions tab → **Monitoring** → **Run workflow**.

## Notes

- `MONITORING_CRON` in the app is unused on Render (the scheduler is off); change
  the schedule in `monitoring.yml`'s `cron:` instead. It's **UTC**.
- No CORS middleware is configured. If a browser frontend (Vestio) calls this API,
  add `fastapi.middleware.cors.CORSMiddleware` with your frontend origin.
- Prefer Render's own auto-deploy instead of the CI-gated hook? Set
  `autoDeploy: true` in `render.yaml`, connect the repo in Render, and delete
  `deploy.yml`. You lose the "don't deploy unless tests pass" guarantee.
