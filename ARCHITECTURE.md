# Architecture — a code-path walkthrough

A guided tour of how the system is wired, following the actual code. Read this
top-to-bottom to understand where a request goes and why. File links are
clickable.

## Layers & dependency direction

```
HTTP  →  api/ (routes, auth, schemas)
              │  orchestrates
              ▼
         services/ (analysis, alternatives, monitoring, translation, insight_store)
              │  calls
              ▼
         rules/ (pure deterministic logic)  +  domain/ (entities, enums, ORM models)
              │  needs data via
              ▼
         ports.py (Protocols)  ◄── implemented by ──  adapters/ (Yahoo, OpenAI, Azure, Mailgun)
```

The **rules** layer is pure (no I/O, no AI) — it only transforms data. **services**
orchestrate rules + adapters. **api** handles HTTP, auth, and serialization.
Adapters are hidden behind `Protocol` interfaces in
[insight_engine/ports.py](insight_engine/ports.py) and constructed in
[insight_engine/providers.py](insight_engine/providers.py), so the whole engine is
testable with mocks.

## The module map

| Package | Responsibility |
|---------|----------------|
| [api/](insight_engine/api/) | FastAPI routers, the auth dependency ([deps.py](insight_engine/api/deps.py)), Pydantic request/response schemas ([schemas.py](insight_engine/api/schemas.py)) |
| [services/](insight_engine/services/) | Orchestration: [analysis.py](insight_engine/services/analysis.py), [alternatives.py](insight_engine/services/alternatives.py), [metrics.py](insight_engine/services/metrics.py), [monitoring.py](insight_engine/services/monitoring.py), [translator.py](insight_engine/services/translator.py), [insight_store.py](insight_engine/services/insight_store.py) |
| [rules/](insight_engine/rules/) | Pure logic: the five dimensions, [synthesis.py](insight_engine/rules/synthesis.py), [scoring_rules.py](insight_engine/rules/scoring_rules.py), [concentration_rules.py](insight_engine/rules/concentration_rules.py), [change_rules.py](insight_engine/rules/change_rules.py), benchmark/candidate maps |
| [ai/](insight_engine/ai/) | [prompts.py](insight_engine/ai/prompts.py) + [handlers.py](insight_engine/ai/handlers.py) (the only place OpenAI is called) |
| [adapters/](insight_engine/adapters/) | External integrations + [caching.py](insight_engine/adapters/caching.py) + [retry.py](insight_engine/adapters/retry.py) |
| [domain/](insight_engine/domain/) | [entities.py](insight_engine/domain/entities.py) (dataclasses), [enums.py](insight_engine/domain/enums.py), [models.py](insight_engine/domain/models.py) (SQLAlchemy tables) |

## App startup

[insight_engine/main.py](insight_engine/main.py) builds the FastAPI app, includes
every router, and in `lifespan` optionally starts the APScheduler monitoring job
(only when `MONITORING_ENABLED=true` — off in the Render deployment, where a cron
drives it instead).

## Path 1 — Authentication

- `POST /users` and `POST /login` live in [api/user_routes.py](insight_engine/api/user_routes.py).
  Passwords are PBKDF2-hashed ([deps.py](insight_engine/api/deps.py) `hash_password`);
  login generates a token, stores its SHA-256 hash on the user (rotating any prior
  one), and returns the raw token once.
- Every protected route depends on `get_current_user`
  ([deps.py](insight_engine/api/deps.py)): it reads the `Authorization: Bearer`
  header, SHA-256s the token, and looks up the matching user — 401 otherwise.

## Path 2 — `POST /portfolio/analyze` (the core pipeline)

Entry: `analyze_portfolio_endpoint` in
[api/portfolio_routes.py](insight_engine/api/portfolio_routes.py).

1. **Resolve the user & portfolio** (`get_current_user`, `get_user_portfolio`).
2. **Positions** — if `assets` is provided it **replaces** the stored lots
   (`_sync_positions`); otherwise the stored lots are loaded. Lots are collapsed to
   one entry per ticker (`_aggregate_lots`: summed quantity, weighted-avg cost).
3. **`_run_analysis`** wraps the market-data provider in a request-scoped
   [CachingMarketDataProvider](insight_engine/adapters/caching.py) and analyzes
   each ticker concurrently (`asyncio.to_thread` + a semaphore). Per ticker it runs
   **`analyze_asset`** (see Path 5) then **`prepare_alternatives_context`**
   ([services/alternatives.py](insight_engine/services/alternatives.py)), which
   computes health & profile-fit scores, classifies the news flags, and decides
   whether alternatives should trigger.
4. **Position context** — `compute_position_contexts`
   ([rules/concentration_rules.py](insight_engine/rules/concentration_rules.py))
   sets each insight's market value / weight / unrealized gain and returns the
   portfolio total; `evaluate_concentration` flags 25%/40% breaches.
5. **AI (optional)** — `generate_batch_explanations`
   ([ai/handlers.py](insight_engine/ai/handlers.py)) makes **one** OpenAI call for
   the whole portfolio, keyed by ticker, filling scenario/risks/explanation (+
   alternative suggestions where triggered). Skipped when `use_ai=false`.
6. **Alternatives resolution** — for triggered assets, `resolve_alternatives`
   validates AI-proposed candidates (or discovers them, Path 6) and ranks them.
7. **Translation (optional)** — `translate_insight` when `language` is set.
8. **Persist** — `save_insights` ([services/insight_store.py](insight_engine/services/insight_store.py))
   maps each `Insight` → `InsightRecord` and **appends** (history is never
   overwritten). Overall risk (`determine_weighted_risk`) and a summary are stored
   on the portfolio.
9. **Respond** — `_build_insight_response` serializes each insight.

## Path 3 — The monitoring watchdog

Entry: `run_monitoring` in [services/monitoring.py](insight_engine/services/monitoring.py),
reached via `POST /monitoring/run`
([api/monitoring_routes.py](insight_engine/api/monitoring_routes.py), guarded by
`MONITORING_TOKEN`) or the scheduler/CLI.

For each alert-enabled user with holdings, per ticker: fetch the **latest stored
insight** (the "before"), run a fresh **deterministic** analysis (no AI) to build a
"now" snapshot, and diff them with `detect_changes`
([rules/change_rules.py](insight_engine/rules/change_rules.py)) — state moves,
health ±15, SMA-200 / Parabolic-SAR crosses, drawdown breach, new news flags, each
tagged adverse/favorable. New insights are appended; if there are changes, one
Mailgun digest is sent ([adapters/mailgun_email.py](insight_engine/adapters/mailgun_email.py)).

## Path 4 — Single-asset re-analyze

`analyze_position_endpoint` in [api/portfolio_routes.py](insight_engine/api/portfolio_routes.py)
(`POST /portfolio/positions/{ticker}/analyze`) is a trimmed Path 2 for one stored
ticker: same `analyze_asset` + scores + optional AI/alternatives, computes that
lot's market value/unrealized gain, appends to history — but skips portfolio-wide
weight/concentration.

## Path 5 — Inside `analyze_asset` (the deterministic heart)

[services/analysis.py](insight_engine/services/analysis.py) `analyze_asset`:

1. Fetch the ticker's 2y history + info from the provider.
2. `classify_role(info)` ([rules/role_rules.py](insight_engine/rules/role_rules.py))
   → pick the **role benchmark** ETF (`get_benchmark_ticker`,
   [rules/benchmark_rules.py](insight_engine/rules/benchmark_rules.py)) → fetch its
   1y history.
3. `calculate_metrics` ([services/metrics.py](insight_engine/services/metrics.py))
   → SMA 50/200, Parabolic SAR, volatility, drawdown, P/E, fundamentals, dividend
   yield, benchmark-vs-SMA200 (all NaN-sanitized).
4. `evaluate_dimensions` runs the five rule modules —
   [trend_rules](insight_engine/rules/trend_rules.py),
   [valuation_rules](insight_engine/rules/valuation_rules.py),
   [fundamentals_rules](insight_engine/rules/fundamentals_rules.py),
   [risk_rules](insight_engine/rules/risk_rules.py),
   [market_context_rules](insight_engine/rules/market_context_rules.py).
5. `synthesize_state` ([rules/synthesis.py](insight_engine/rules/synthesis.py))
   collapses the five dimensions into one asset state (conservative bias).
6. `determine_horizon` ([rules/horizon_rules.py](insight_engine/rules/horizon_rules.py))
   sets the recommended horizon.

Scores (`compute_health_score`, `compute_profile_fit_score` in
[rules/scoring_rules.py](insight_engine/rules/scoring_rules.py)) are added by the
callers. The whole of Path 5 is pure/deterministic — no AI, no user data beyond the
profile.

## Path 6 — Alternative candidate discovery

When alternatives trigger, `_get_fallback_suggestions`
([services/alternatives.py](insight_engine/services/alternatives.py)) calls
`discover_candidates` ([rules/candidate_discovery.py](insight_engine/rules/candidate_discovery.py)):
the role benchmark ETF's **live top holdings** (`fetch_holdings`) unioned with the
static [config/candidate_universe.json](config/candidate_universe.json), each scored
and filtered (risk tolerance + profile fit ≥ 50 + not held), ranked by goal
role-match then health, top 3.

## Ports, caching & retry

- [ports.py](insight_engine/ports.py) defines `MarketDataProvider`, `LLMProvider`,
  `TranslatorProvider`, `EmailProvider` as `Protocol`s. Real implementations in
  [adapters/](insight_engine/adapters/); constructed in
  [providers.py](insight_engine/providers.py).
- [adapters/retry.py](insight_engine/adapters/retry.py) wraps Yahoo fetches with
  exponential backoff.
- [adapters/caching.py](insight_engine/adapters/caching.py) dedupes fetches within a
  single request (so 19 assets sharing a benchmark fetch it once).

## Data model

[domain/models.py](insight_engine/domain/models.py): `User` 1—1 `Portfolio` 1—* 
`Position` (purchase lots); `Portfolio` 1—* `InsightRecord` (append-only history).
Migrations live in [alembic/versions/](alembic/versions/).

## The AI boundary (important)

AI is confined to [ai/handlers.py](insight_engine/ai/handlers.py) and only ever
receives **processed states and metrics** — never raw market data — and can't issue
orders or price targets. Everything in `rules/` and the monitoring path is
deterministic and AI-free. That separation is the core design invariant: *rules
classify states; AI only explains them.*

## Where to start reading

`main.py` → `api/portfolio_routes.py::_run_analysis` → `services/analysis.py::analyze_asset`
→ the five `rules/*` modules → `rules/synthesis.py`. That chain is the whole engine.
