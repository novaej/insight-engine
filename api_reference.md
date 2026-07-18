# API Reference

Summary of every endpoint: what it does, what it needs, and what it returns.
For interactive exploration use Swagger at `http://localhost:8000/docs`; for
ready-made requests import `insight_engine.postman_collection.json`.

**Authentication:** all endpoints require `Authorization: Bearer <token>` except
`GET /health`, `POST /users`, `POST /login`, and `POST /assets/analyze`.
Tokens are obtained from `POST /login` and invalidated by the next login or a
password change.

## At a glance

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness check |
| POST | `/users` | — | Register (email, password, name) |
| POST | `/login` | — | Get bearer token (rotates previous) |
| GET | `/users/me` | ✓ | Current user info |
| PATCH | `/users/me` | ✓ | Update email/name/password |
| DELETE | `/users/me` | ✓ | Delete account + all data |
| GET | `/portfolio/positions` | ✓ | List purchase lots |
| POST | `/portfolio/positions` | ✓ | Add a lot |
| PATCH | `/portfolio/positions/{id}` | ✓ | Edit a lot |
| DELETE | `/portfolio/positions/{id}` | ✓ | Remove a lot |
| POST | `/portfolio/analyze` | ✓ | Analyze portfolio (the main event) |
| GET | `/portfolio` | ✓ | Stored portfolio + latest insights |
| PUT | `/portfolio` | ✓ | Replace assets and re-analyze |
| GET | `/insights` | ✓ | Insight history with filters |
| POST | `/profile/interpret` | ✓ | Plain words → structured user profile (AI) |
| POST | `/assets/analyze` | — | Ad hoc single-ticker analysis |
| POST | `/monitoring/run` | token | Run the change-detection sweep, email digests |

## Users & authentication

### POST /users
Registers a user. Body: `email`, `password` (min 8 chars), optional `name`.
Returns the user without any token — log in to get one. 409 if the email is taken.

### POST /login
Body: `email`, `password`. Returns `{token, token_type}`. Each login generates a
new token and invalidates the previous one (single active session).

### GET /users/me
Returns the authenticated user's id, email, and name.

### PATCH /users/me
Partial update: `email` (409 if taken), `name`, and/or `password`. Changing the
password requires `current_password` and logs you out (token invalidated).

### DELETE /users/me
Deletes the account and cascades to portfolio, positions, and insight history. 204.

## Positions (purchase lots)

A position row is one **purchase lot**. Buying the same ticker twice at
different prices creates two lots; analysis aggregates lots per ticker
(summed quantity, weighted-average purchase price). Editing lots never
triggers analysis — that's always on-demand. Max 20 distinct tickers.

### GET /portfolio/positions
Lists all lots (each with its `id`), sorted by ticker.

### POST /portfolio/positions
Adds a lot: `ticker`, `quantity`, optional `purchase_price`, `purchase_date`.
Creates an empty portfolio automatically on first use. 422 beyond 20 tickers.

### PATCH /portfolio/positions/{id}
Partial update of a lot: `quantity`, `purchase_price`, `purchase_date`.

### DELETE /portfolio/positions/{id}
Removes a lot. The ticker's insight history is kept. 204.

## Portfolio analysis

### POST /portfolio/analyze
The core endpoint. Runs the full pipeline for every held ticker — market data
fetch, deterministic rules (trend/valuation/fundamentals/risk/market context →
asset state), health & profile-fit scores, news flags, one batched AI call for
explanations, and alternative suggestions where triggered. Persists a new
insight row per ticker (history accumulates).

Body:
- `user_profile` (required): `risk` (low|moderate|high), `horizon`
  (short|medium|long), `goal` (growth|income|capital_protection)
- `assets` (optional): full desired holdings — **replaces all stored lots**;
  repeat a ticker for multiple lots. Omit to analyze stored positions (400 if
  there are none).
- `use_ai` (default true): false skips OpenAI (mechanical text instead)
- `language` (optional ISO code, e.g. `es`): translates AI text via Azure

The investment `goal` now shapes analysis: it adds an objective component to each
insight's profile fit score (income rewards dividend yield, growth rewards revenue
growth, capital_protection rewards low risk) and biases alternative ranking toward
goal-matching roles. Metrics include a normalized `dividend_yield` (a fraction).

Market context is evaluated against the asset's **role benchmark** (e.g. QQQ
for GROWTH_TECH; map in `config/benchmarks.json`). Each insight's metrics
expose `benchmark_ticker` and `benchmark_above_sma200` so it's always visible
what the asset was judged against; a `null` signal means benchmark data was
unavailable and the dimension defaulted to favorable.

Alternative suggestions are filtered by the user's risk tolerance **and**
profile fit (≥ 50), never include tickers already held in the portfolio, and
draw from the live holdings of the role's benchmark ETF unioned with the config
candidate universe. Each suggestion carries its health score and profile fit
score. Pass `include_alternatives: false` to skip alternatives entirely (faster,
fewer fetches); role and scores still populate each insight.

Returns per-asset insights plus portfolio-level `overall_risk`, `summary`,
`total_value`, and `concentration` (state + flagged tickers/roles). Each insight
includes a `position` object when analyzed as part of a portfolio: quantity,
market value, weight (0–1 share of portfolio value), average purchase price, and
unrealized gain/loss vs cost. Overall risk is weighted by position value.

### GET /portfolio
Returns the stored portfolio: profile, all lots, overall risk, summary, total
value, concentration, and the **latest insight per currently held ticker**
(including its position context). No external calls — instant.

### PUT /portfolio
Same as analyze-with-assets (replaces lots, re-analyzes) but keeps the stored
`user_profile` unless one is provided. 404 if no portfolio exists yet.

## Insights

### GET /insights
Insight history for your portfolio, newest first. Every analysis run adds rows,
so this shows how an asset's state/scores evolved over time. Query params, all
optional: `ticker`, `from` / `to` (ISO datetimes), `limit` (1–500, default 50).

## Profile

### POST /profile/interpret
Maps a plain-words description of what you want from your investments
(`{"text": "..."}`, 10–1000 chars) to a structured profile via one small AI
call: `{risk, horizon, goal, rationale}`, strictly validated against the domain
values. The result is a **proposal** — review it and pass it as `user_profile`
to the analyze endpoints; it is never applied automatically. When the text
gives no signal for a field, the most conservative value is chosen and the
rationale says so. 502 if the AI is unavailable or returns something invalid.

## Assets

### POST /assets/analyze
Analyzes any single ticker ad hoc — same pipeline, but not tied to a user or
portfolio (no auth). Body: `ticker` (required), optional `user_profile`,
`use_ai`, `language`.

## Monitoring (watchdog)

### POST /monitoring/run
Re-analyzes every alert-enabled user's holdings, detects both adverse and
favorable (upside) changes vs. the last stored insight per ticker, and emails a
plain-language digest via Mailgun grouped into "Positive moves" and "Potential
concerns".
Deterministic (no AI). Authorized by the `X-Monitoring-Token` header matching the
`MONITORING_TOKEN` env var — **not** a user bearer token, so an unattended
cron/scheduler can call it. Unset token → 503; wrong token → 403. Returns
`{users_swept, emails_sent, changes_detected}`.

The server also runs this automatically when `MONITORING_ENABLED=true` (in-process
APScheduler on `MONITORING_CRON`, default daily 09:00). Run one scheduler process
to avoid duplicate emails. Manual one-off: `python -m insight_engine.jobs.monitoring`.

Per-user opt-out: `PATCH /users/me {"alerts_enabled": false}` (also in `GET /users/me`).
The first sweep of a ticker sets a baseline and sends nothing.

## Error conventions

- `401` — missing/invalid token, wrong credentials, wrong current password
- `404` — no portfolio yet, unknown position id
- `409` — email already registered
- `422` — validation errors (bad email, >20 tickers, quantity ≤ 0, …)
- `500` — analysis failure for a ticker (detail names the ticker)
