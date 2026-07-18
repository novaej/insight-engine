# Next Steps

Prioritized roadmap for evolving InsightEngine beyond the MVP. Ordered by priority:
each step builds on the previous one, so the order matters. Throughout all of it,
the core philosophy holds — **rules classify states, they do not give orders** — and
every new feature stays educational, never prescriptive.

---

## P1 — Rework persistence: users, real relations, insight history ✅ DONE (2026-07-16)

Implemented as planned, plus email/password registration with bearer tokens issued
on login (`POST /users`, `POST /login`; no header → default dev user). Remaining
from the original scope: nothing — retention policy deferred until table growth
matters.

**Why first:** everything else (positions, alerts, history views) needs a solid data
model underneath. The current model is two tables: `portfolios` stores assets as an
untyped JSON blob with no user relation, and `insights` are **deleted on every
re-analysis**, so there is no history at all.

**What to build:**

- `users` table (id, email, name, created_at). No authentication yet — endpoints
  take/derive a user id — but the schema is auth-ready for when login is added.
- `portfolios.user_id` FK → users. One portfolio per user initially, but the
  relation supports several later (e.g. "retirement" vs "trading").
- `positions` table replacing the JSON blob: portfolio_id FK, ticker, quantity,
  **purchase_price**, **purchase_date**, created_at/updated_at. Typed columns mean
  positions can be updated individually (add/remove/edit one position without
  resending the whole portfolio).
- Keep insight history: stop deleting old insights on re-analysis. Add
  `analyzed_at` and query "latest per ticker" for current state; older rows become
  the timeline ("how has AAPL's health score moved over the last 3 months?").
  Add a retention policy later if the table grows.
- New/updated endpoints: CRUD for positions (`POST/PATCH/DELETE /positions`),
  `GET /insights?ticker=&from=&to=` for history, latest-insights view for the
  dashboard.

**DB migration note:** write an Alembic migration that backfills the existing JSON
assets into the new `positions` table so current data survives.

## P2 — Position-aware analysis (cost basis, weights, concentration) ✅ DONE (2026-07-17)

Implemented as planned: weights + market values per position, unrealized
gain/loss vs weighted-average cost, 25%/40% concentration rule
(`rules/concentration_rules.py`), value-weighted overall risk, position &
portfolio context in the AI prompt, and persistence
(insights.position_context, portfolios.total_value/concentration).

**Why second:** cheap once P1 exists, and it makes every insight dramatically more
personal — the engine currently analyzes each ticker in isolation with no idea of
exposure.

**What to build:**

- **Portfolio weights:** market value per position (quantity × current price) and
  its share of the total. Surface in insights: "TSLA is 22% of your portfolio and
  its most volatile holding."
- **Concentration rule (deterministic, rules layer):** flag when one position
  exceeds a threshold (e.g. 25%) or one sector/role exceeds e.g. 40%. New states,
  not orders: `concentrated` / `diversified`.
- **Unrealized gain/loss context:** current price vs purchase_price per position.
  Guardrail: a paper loss produces *context* ("30% below cost basis, in a bearish
  trend"), never sell language. Feed it to the AI prompt as one more state.
- Portfolio-level summary gains a real overview: total value, weight table,
  aggregate risk weighted by position size instead of a simple count.

## P3 — Sector/role-aware market context benchmarks ✅ DONE (2026-07-17)

Implemented: `config/benchmarks.json` role→index map (GROWTH_TECH → QQQ,
DIVIDEND_INCOME → VYM, DEFENSIVE → XLP, EMERGING_MARKETS → EEM,
BONDS_STABILITY → AGG, US_LARGE_CAP_CORE → ^GSPC), market context judged against
the role benchmark only (no S&P fallback — per user decision), full transparency
(`benchmark_ticker` + `benchmark_above_sma200` in every insight's metrics; `null`
when data unavailable so the default is visible), and a request-scoped
thread-safe cache (`adapters/caching.py`) replacing the ^GSPC prefetch.

## P3b — Dynamic candidate discovery ✅ DONE (2026-07-17)

Implemented: candidates are the live top holdings of each role's benchmark ETF
(`config/discovery_etfs.json`: SPY/QQQ/VYM/XLP) via yfinance
`funds_data.top_holdings` (`MarketDataProvider.fetch_holdings`), unioned with the
static `config/candidate_universe.json` and run through the same validation chain.
Discovery augments (never replaces): bonds/emerging-markets roles and any fetch
failure fall back to the static list; foreign listings are filtered to US symbols.
Also added the `include_alternatives` request flag to skip alternatives entirely.
(Deferred: sector-screen discovery for roles without a clean holdings ETF — the
data source there is still unresolved.)

## P4 — Active monitoring & email alerts ("the watchdog") ✅ DONE (2026-07-17)

Implemented: in-process APScheduler (opt-in via `MONITORING_ENABLED`, cron
`MONITORING_CRON`) + `POST /monitoring/run` (guarded by `MONITORING_TOKEN`) +
`python -m insight_engine.jobs.monitoring`. Deterministic change detection
(`rules/change_rules.py`) compares each holding to its last stored insight and
detects state downgrades, health drops ≥15, SMA-200 / Parabolic-SAR bearish
crosses, drawdown-tolerance breaches, and new news flags. One Mailgun digest per
user with changes; per-user opt-out via `alerts_enabled`; baseline run sends
nothing. No AI on this path. Persisted `news_flags` on insights to support news
transitions. Detects both adverse and favorable (upside) moves so the user can
spot strength as well as deterioration. **Deferred (future):** LLM news-relevance
filtering, per-event dedup beyond consecutive-run comparison.

<details><summary>Original P4 notes</summary>

**Why:** the highest-value feature — "I can't watch this all the time" is exactly
the problem to solve — but it depends on P1 (history/state memory) and gets much
better with P2 (weights tell it which positions matter most).

**What to build:**

- **Change detection with memory:** persist each asset's last known state/scores
  (P1's insight history provides this). A scheduled job re-analyzes holdings and
  triggers only on *transitions*:
  - asset state degrades (e.g. healthy → risky)
  - health score drops sharply (e.g. −15 points since last run)
  - price crosses SMA 200, or Parabolic SAR flips
  - a new news flag appears (regulatory, earnings, management, litigation)
  - drawdown breaches the user's risk-profile threshold
- **Smarter news relevance:** keyword matching fires on any headline containing
  "lawsuit". Add a batched LLM call that classifies fetched headlines per ticker
  as relevant/irrelevant + severity, keeping the deterministic flags as the
  trigger of record and the LLM as a false-alarm filter.
- **Email adapter** (`adapters/` pattern, SMTP or a provider like Resend/SES) with
  an `AlertNotifier` port. One digest email per run listing what changed, why, and
  what it means — educational tone, never "take action now."
- **Dedup/state tracking:** record what was last notified per (user, ticker,
  trigger type) so the same event doesn't re-alert daily; re-notify only on
  further change.
- Job cadence: start daily, move to intraday later if needed. MVP explicitly
  excluded real-time alerts — this deliberately relaxes that.

</details>

## P4b — Wire the investment objective (goal) into deterministic scoring

**Why:** audit on 2026-07-17 found `goal` (growth | income | capital_protection)
is only used in the AI prompt's user-context line — no deterministic rule
consumes it. An income investor and a growth investor currently get identical
scores and alternative suggestions.

**What to build (needs its own design pass on weights):**

- `income` → add a dividend-yield component to the Profile Fit Score and prefer
  DIVIDEND_INCOME-role candidates when ranking alternatives.
- `capital_protection` → tighten the volatility/drawdown thresholds a notch
  (e.g. treat one risk level stricter) and prefer DEFENSIVE/BONDS_STABILITY
  candidates.
- `growth` → current behavior (baseline).
- Document the new weights in `business_rules.md` §9.3 and update
  `calculations.md`.

## P5 — Hardening & cleanup (ongoing, fits between steps)

- Fix the 42 pre-existing ruff lint errors; enforce lint in CI.
- Remove `requirements.txt` / `requirements-dev.txt` if `pyproject.toml [dev]` is
  the source of truth (docs already point only to pyproject).
- Basic auth (even a static API key per user) before anything is exposed beyond
  localhost.
- Rate limiting / retry-with-backoff on Yahoo Finance calls now that fetches run
  concurrently.
- Integration test that exercises the full portfolio analyze flow with mocked
  providers, including the batched AI path.

---

## Suggested sequencing

| Step | Depends on | Rough size | Status |
|------|-----------|------------|--------|
| P1 persistence rework | — | large | ✅ done |
| P2 position-aware analysis | P1 | medium | ✅ done |
| P3 benchmark map | — (parallel-friendly) | small | ✅ done |
| P3b dynamic candidate discovery | — | medium | ✅ done |
| P4 watchdog + email | P1, better with P2 | large | ✅ done |
| P4b goal-aware scoring | — (parallel-friendly) | medium | open |
| P5 hardening | — | small, continuous | ongoing |

Remaining work is P3b, P4, P4b, and P5 — all independent of each other. P4
(the watchdog) is the highest-value remaining feature.
