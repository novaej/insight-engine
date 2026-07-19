# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Deploys are tag-based. To cut a release: bump `version` in `pyproject.toml`, move
the `[Unreleased]` items under a new `[x.y.z] - YYYY-MM-DD` heading, then
`git tag vX.Y.Z && git push origin vX.Y.Z` (ships to staging; the tag must match
the pyproject version or the release fails — see `DEPLOY.md`).

## [Unreleased]

_Nothing yet — changes land here until the next tagged release._

## [0.1.0] - 2026-07-19

Initial backend MVP — the full analysis engine, persistence, monitoring, and
deployment pipeline. Tagged for staging; promoted to production later via a
published GitHub Release. Highlights:

### Added
- **Accounts & auth** — email/password registration, bearer token issued on
  login (rotates per login), account management (`/users/me`), per-user opt-out
  for alerts.
- **Portfolio & positions** — one portfolio per user; positions stored as
  purchase lots (multiple lots per ticker, cost basis), CRUD without triggering
  analysis; max 20 distinct tickers.
- **Analysis engine** — five deterministic dimensions (trend, valuation,
  fundamentals, risk, market context) synthesized into an asset state; Health and
  Profile Fit scores (the latter objective-aware: income→yield, growth→revenue
  growth, capital_protection→low risk); news-flag keyword extraction.
- **Market context by role benchmark** — each asset judged against its portfolio
  role's benchmark ETF (QQQ, VYM, XLP, …) vs its 200-day SMA, with the benchmark
  ticker exposed for transparency.
- **Alternatives** — triggered on low scores/news; candidates discovered from the
  role benchmark ETF's live holdings unioned with a curated universe, filtered by
  risk tolerance + profile fit ≥ 50 + not held, ranked by goal role-match then
  health.
- **Position-aware analysis** — market value, portfolio weight, unrealized
  gain/loss, 25%/40% concentration rule, value-weighted overall risk.
- **AI layer** — one batched OpenAI call per portfolio for explanations
  (opt-out via `use_ai`); `POST /profile/interpret` maps plain words to a
  structured profile; Azure translation of AI text.
- **Insight history** — insights are appended, never overwritten; queryable via
  `GET /insights`; single-asset re-analysis via
  `POST /portfolio/positions/{ticker}/analyze`.
- **Monitoring watchdog** — scheduled sweep detects adverse and favorable changes
  vs. the last insight (state, health, SMA-200/SAR crosses, drawdown, news) and
  emails a deterministic Mailgun digest; `POST /monitoring/run` guarded by
  `MONITORING_TOKEN`.
- **Ops** — Render + Neon deployment, tag-based staging deploys and disabled
  production scaffolds, GitHub Actions CI (ruff + pytest) and a warm-up monitoring
  cron, retry/backoff on market-data fetches.
