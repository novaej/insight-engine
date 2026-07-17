# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InsightEngine is a backend MVP for personal investment portfolio analysis. It provides educational and contextual analysis of stocks and ETFs—it does NOT provide financial advice, buy/sell signals, or price predictions. The frontend product name is Vestio.

**Core philosophy:** "Rules classify states, they do not give orders." All outputs are educational and contextual, never prescriptive.

## Tech Stack

- **Language:** Python
- **Framework:** FastAPI (REST API)
- **Database:** PostgreSQL
- **Validation:** Pydantic schemas
- **AI:** OpenAI API (text explanations only—never raw market data)
- **Translation:** Azure Translator (multi-language support for AI-generated text)
- **Data:** External financial data APIs
- **Scheduling:** Daily jobs for data updates

## Build & Development Commands

```bash
# Environment setup (use python3 if `python` is not on PATH)
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Recreate a broken venv
deactivate; rm -rf venv  # then repeat the setup steps above

# Create the database (must exist before starting the server)
psql -U postgres -c "CREATE DATABASE insight_engine;"
# or if PostgreSQL runs in Docker (replace container name):
docker exec -it postgres16 psql -U postgres -c "CREATE DATABASE insight_engine;"

# Apply database migrations
alembic upgrade head

# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Run the API server (http://localhost:8000, docs at /docs)
uvicorn insight_engine.main:app --reload

# Run all tests
pytest

# Run tests with coverage
pytest --cov=insight_engine

# Run a single test file
pytest tests/test_valuation_rules.py

# Run a specific test
pytest tests/test_valuation_rules.py::test_cheap_valuation -v

# Lint and format
ruff check .
ruff format .
```

## Architecture

The system uses a three-layer analysis engine with strict separation:

```
insight_engine/
├── api/          # FastAPI routes and endpoints
├── domain/       # Domain models and Pydantic schemas
├── rules/        # Deterministic business rules (no AI)
├── services/     # Orchestration (analysis, alternatives, metrics, translation)
├── ai/           # LLM prompts and handlers (interpretation only)
├── adapters/     # External integrations (Yahoo Finance, OpenAI, Azure)
├── jobs/         # Scheduled tasks (daily analysis jobs)
config/           # Static config (candidate_universe.json, benchmarks.json, discovery_etfs.json)
tests/            # Unit tests (metrics, rules, endpoints, alternatives)
```

### Layer 1: Metrics/Calculations (Technical)
Raw financial computations—moving averages, Parabolic SAR, volatility, fundamental metrics.

### Layer 2: Business Rules (Deterministic)
Non-AI logic that classifies asset states. Each asset is evaluated on five independent dimensions:

| Dimension | Possible States | Indicators |
|-----------|----------------|------------|
| Trend | bullish, sideways, bearish | SMA 50/200 + Parabolic SAR |
| Valuation | cheap, reasonable, expensive, inconclusive | P/E vs historical avg |
| Fundamentals | strong, mixed, weak | Revenue growth, margins, debt |
| Risk/Volatility | low, medium, high | Volatility, max drawdown |
| Market Context | favorable, adverse | Role benchmark index (config/benchmarks.json) vs its SMA 200 |

These synthesize into a final asset state: `healthy`, `healthy_but_expensive`, `neutral`, `risky`, or `unattractive`.

**Key synthesis rules:**
- Two or more negative signals → do not force a positive state
- High risk + adverse context → `unattractive`
- Weak fundamentals → `risky` regardless of other signals
- Conflicting signals → prioritize most conservative
- Insufficient clarity → `neutral`

### Layer 2b: Scoring & Alternatives (Deterministic)
Built on top of dimensions, computing:
- **Health Score** (0–100): Composite of trend, fundamentals, valuation, risk, and drawdown
- **Profile Fit Score** (0–100): Volatility/drawdown/horizon alignment with user profile
- **News Flags**: Keyword-based risk extraction from headlines (no AI)
- **Alternative Suggestions**: Triggered when health < 50, profile fit < 50, or news flags active (unless `include_alternatives=false` on the request). Candidates come from AI proposals, or from live role-benchmark ETF holdings (`config/discovery_etfs.json`) unioned with the `config/candidate_universe.json` fallback; all filtered by risk tolerance + profile fit ≥ 50 + not already held, ranked by health score, max 3 returned.
- **Position Context** (`rules/concentration_rules.py`): market value, portfolio weight, and unrealized gain/loss per position; 25%/40% concentration rule; overall portfolio risk weighted by position value.

### Layer 3: AI Interpretation (LLM)
Receives only processed states and metrics. Explains and contextualizes results in natural language. Cannot issue orders or price targets. Maximum 3 signals or risks per insight. When alternatives are triggered, a merged prompt requests both explanation and candidate suggestions in one call.

### Translation Layer
AI-generated text (scenario, explanation, risks, summary) can be translated into any supported language via Azure Translator. Activated by passing a `language` parameter (ISO code) to analysis endpoints. English is the default and skips translation.

## Domain Concepts

- **User:** Registered account (email/password). All portfolio/position/insight endpoints require `Authorization: Bearer <token>` from `POST /login`. `POST /profile/interpret` maps a plain-words description to a structured profile via AI (proposal only, never auto-applied).
- **User Profile:** risk (low|moderate|high) + horizon (short|medium|long) + objective (growth|income|capital_protection). Modulates interpretation, not base rules. Note: objective currently only flavors AI text (see next_steps.md P4b).
- **Position (Lot):** One purchase of a ticker (quantity, optional purchase price/date). Multiple lots per ticker allowed; analysis aggregates per ticker (summed quantity, weighted-average cost). CRUD via `/portfolio/positions/{id}`, no auto-analysis.
- **Portfolio:** One per user. `POST /portfolio/analyze` analyzes stored positions (or syncs+analyzes a provided `assets` list — which **replaces** stored lots). Stores overall risk (value-weighted), summary, total value, and concentration. Insights are appended, never deleted — history via `GET /insights`.
- **Insight:** The minimum unit of value—includes asset state, scenario, horizon, risks, explanation, plus optional scores, alternatives, and position context (weight, market value, unrealized gain/loss).
- **Concentration:** `concentrated` when a position > 25% of value or a role > 40% combined; else `diversified`.
- **Scenario:** Narrative of likely behavior without price predictions or timing.
- **Portfolio Role:** Classification of an asset's function (US_LARGE_CAP_CORE, GROWTH_TECH, DIVIDEND_INCOME, DEFENSIVE, EMERGING_MARKETS, BONDS_STABILITY). Used for candidate discovery.
- **Health Score / Profile Fit Score:** Deterministic 0–100 scores measuring asset quality and user-profile alignment respectively.
- **News Flags:** Binary risk signals (regulatory, earnings, management, litigation) extracted from headlines via keyword matching.
- **Alternative:** Comparable asset more aligned with the user's profile (not a recommendation). Triggered by low scores or news flags, resolved via AI candidates (validated) or JSON config fallback.
- **Parabolic SAR:** Trend-confirming indicator (Wilder's algorithm, AF 0.02→0.20). Confirms or moderates SMA-based trend signals.

## MVP Constraints

- Multi-user (email/password registration, bearer token issued on login; token rotates per login)
- One portfolio per user, max 20 distinct tickers (a ticker may have multiple purchase lots)
- Stocks and ETFs only
- No broker integration, no real-time alerts
- Data may be delayed; tolerance for imperfect data

## Reference Documents

- `business_rules.md` – Complete business rule specifications and state synthesis logic
- `calculations.md` – Plain-language explanation and formula for every metric/indicator (SMA, Parabolic SAR, volatility, drawdown, P/E benchmark, fundamentals, market context)
- `api_reference.md` – Endpoint summary: auth rules, request/response shapes, error conventions
- `domain_language.md` – Terminology definitions used consistently throughout the system
- `mvp_scope.md` – MVP boundaries, assumptions, and success criteria
- `architect_prompt.md` – Architectural specification and naming conventions
- `next_steps.md` – Prioritized post-MVP roadmap (multi-user persistence, position-aware analysis, sector benchmarks, monitoring/alerts)

## Naming Conventions

- Python modules: lowercase with underscores (`portfolio_analysis.py`)
- Pydantic schemas: `schemas.py` or grouped by domain (`asset_schemas.py`)
- Rules: `valuation_rules.py`, `trend_rules.py`
- AI prompts: `prompts.py` or `asset_prompts.py`
