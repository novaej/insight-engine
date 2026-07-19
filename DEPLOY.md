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
| `MONITORING_TOKEN` | a random secret (see below) — guards `/monitoring/run` |

`OPENAI_MODEL`, `MONITORING_ENABLED=false`, and the (blank) `AZURE_*` vars are
already declared in `render.yaml`.

### Generating `MONITORING_TOKEN`

It's just a random secret you make up — nothing registers it anywhere. Generate a
strong one with any of:

```bash
openssl rand -hex 24        # 48-char hex, e.g. 9f3c...­a1
# or
python -c "import secrets; print(secrets.token_urlsafe(32))"
# or
uuidgen
```

Use the **same value** in two places so the cron's header matches the API:
- Render env var `MONITORING_TOKEN` (this section)
- GitHub Actions secret `MONITORING_TOKEN` (step 3)

Rotate it by generating a new value and updating both. If it's left unset, the
`/monitoring/run` endpoint returns 503 and the monitoring cron can't run.

## 3. GitHub Actions — tag-based deploys

Merging a PR to `main` **does not deploy** — it only runs CI. Deploys are driven
by **git tags**, so you control when staging ships.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [ci.yml](.github/workflows/ci.yml) | push to main, PRs | ruff + pytest |
| [release-staging.yml](.github/workflows/release-staging.yml) | push a tag `v*.*.*` | fast-forwards the `staging` branch to the tag |
| [deploy-staging.yml](.github/workflows/deploy-staging.yml) | push to `staging` | triggers the Render **staging** deploy |
| [monitoring.yml](.github/workflows/monitoring.yml) | daily 09:00 UTC (+ manual) | wake the service, run the sweep |
| release-production.yml / deploy-production.yml | — | **disabled** scaffolds for later (see below) |

**The staging flow:**
```
merge PRs to main  →  CI runs (no deploy)
git tag v0.1.0 && git push origin v0.1.0
      ↓ release-staging.yml fast-forwards the `staging` branch to the tag
      ↓ deploy-staging.yml fires the Render deploy hook
staging is live
```

**One-time setup:**
1. Create the `staging` branch from `main`: `git switch -c staging main && git push -u origin staging`.
2. In Render, the blueprint creates **`insight-engine-staging`** tracking the
   `staging` branch. Copy its deploy hook (service → **Settings → Deploy Hook**).
3. Create a GitHub **environment** named `staging`
   (**Settings → Environments → New environment**) and add secret
   **`RENDER_DEPLOY_HOOK_URL`** to it.
4. Add repo-level (**Settings → Secrets and variables → Actions**):
   - Secret **`RELEASE_PUSH_TOKEN`** — a fine-grained PAT with **Contents: write**
     on this repo, so `release-staging` can push to `staging` and trigger the
     deploy (the default `GITHUB_TOKEN` can't chain workflows).
   - Variable **`APP_URL`** — your staging Render URL, e.g.
     `https://insight-engine-staging.onrender.com` (no trailing slash).
   - Secret **`MONITORING_TOKEN`** — the **same value** you set in Render.

After that, tag a known-good `main` commit to ship it to staging. Trigger a
monitoring sweep manually anytime: Actions → **Monitoring** → **Run workflow**.

### Enabling production later

`release-production.yml` and `deploy-production.yml` are pre-written but disabled.
When you provision a production service:
1. Create a `production` branch and an `insight-engine-prod` Render service (its
   own env vars + deploy hook).
2. Create a GitHub `production` environment with its own `RENDER_DEPLOY_HOOK_URL`.
3. In each production workflow: uncomment the trigger and remove the `if: false`.

Then the promotion gate is: **publish a GitHub Release** from a tag that staging
validated → production fast-forwards and deploys.

## Notes

- `MONITORING_CRON` in the app is unused on Render (the scheduler is off); change
  the schedule in `monitoring.yml`'s `cron:` instead. It's **UTC**. `APP_URL`
  currently points at staging, so the watchdog runs against staging until
  production exists.
- No CORS middleware is configured. If a browser frontend (Vestio) calls this API,
  add `fastapi.middleware.cors.CORSMiddleware` with your frontend origin.
