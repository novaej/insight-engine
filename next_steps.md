# Next Steps

Prioritized roadmap for evolving InsightEngine beyond the MVP. Ordered by priority:
each step builds on the previous one, so the order matters. Throughout all of it,
the core philosophy holds — **rules classify states, they do not give orders** — and
every new feature stays educational, never prescriptive.

---

## P1 — Rework persistence: users, real relations, insight history

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

## P2 — Position-aware analysis (cost basis, weights, concentration)

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

## P3 — Sector/role-aware market context benchmarks

**Why:** the S&P 500 vs SMA 200 check is a blunt instrument — an energy stock, a
financials ETF, and a bond fund all get judged against the same "market weather."

**What to build:**

- Benchmark map keyed by portfolio role (already classified in `role_rules.py`),
  with sector as fallback: GROWTH_TECH → QQQ, DIVIDEND_INCOME → VYM,
  DEFENSIVE → XLP, EMERGING_MARKETS → EEM, BONDS_STABILITY → AGG,
  US_LARGE_CAP_CORE → ^GSPC (unchanged). Config file, not hardcoded.
- Market context dimension compares the asset's benchmark vs its own SMA 200,
  reusing the existing comparison code — it's parameterizing the ticker.
- Keep the S&P 500 check as a second, overall-regime signal (favorable/adverse
  becomes two-part: broad market + asset's neighborhood).
- Cache benchmark fetches per analysis run (same pattern as the ^GSPC fix).

## P4 — Active monitoring & email alerts ("the watchdog")

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
- Job cadence: start daily (extend `jobs/daily_analysis.py`), move to intraday
  later if needed. MVP explicitly excluded real-time alerts — this deliberately
  relaxes that.

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

| Step | Depends on | Rough size |
|------|-----------|------------|
| P1 persistence rework | — | large (schema + migration + endpoints) |
| P2 position-aware analysis | P1 | medium |
| P3 benchmark map | — (parallel-friendly) | small |
| P4 watchdog + email | P1, better with P2 | large |
| P5 hardening | — | small, continuous |

P3 is independent and small — it can be slotted in anytime as a break from the
bigger work.
