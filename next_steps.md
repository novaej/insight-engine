# Next Steps

The MVP (P1–P5) is complete and deployed to staging. Nothing from the original
scope is outstanding — this file tracks **nice-to-haves and gaps** for after 0.1.0.
Nothing here is scheduled.

## Before a browser frontend / wider use

- **CORS** — no middleware yet. Add `fastapi.middleware.cors.CORSMiddleware` with
  the Vestio frontend origin before a browser calls the API directly.
- **Rate limiting** — none per client. Add basic throttling if the API is exposed
  beyond personal use.
- **Enable production** — `release-production.yml` / `deploy-production.yml` are
  scaffolded but disabled; provision an `insight-engine-prod` Render service + a
  `production` GitHub environment, then flip them on (see `DEPLOY.md`).

## Quality-of-life

- **DATABASE_URL normalization** — auto-rewrite a pasted `postgresql://…?sslmode=require`
  to the `postgresql+asyncpg://…?ssl=require` form the async driver needs, so a raw
  Neon/Heroku URL "just works" (a ~10-line change in `config`/`database.py`).

## Analysis enhancements

- **Smarter news relevance** — replace keyword matching with a batched LLM
  classification of headlines (relevance + severity). Adds AI cost to the news
  path, so gate it.
- **Dynamic discovery for bonds / emerging markets** — those roles fall back to the
  static list because their ETF holdings aren't usable equity tickers; a sector
  screen or maintained constituent list would widen them.
- **Richer monitoring insights** — the watchdog writes no-AI insights, so after a
  nightly run `GET /portfolio` shows no AI narrative / weights. Optionally compute
  the cheap position weights in monitoring, or don't overwrite a recent manual AI
  insight as "latest".

## Testing / ops

- **Batched-AI integration test** — the AI path is always mocked; an integration
  test that exercises `generate_batch_explanations` against a stubbed LLM provider
  would cover the prompt/parse wiring end-to-end.
