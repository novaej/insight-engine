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
# Environment setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run the API server
uvicorn insight_engine.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_valuation_rules.py

# Run a specific test
pytest tests/test_valuation_rules.py::test_cheap_valuation -v
```

## Architecture

The system uses a three-layer analysis engine with strict separation:

```
insight_engine/
├── api/          # FastAPI routes and endpoints
├── domain/       # Domain models and Pydantic schemas
├── rules/        # Deterministic business rules (no AI)
├── ai/           # LLM prompts and handlers (interpretation only)
├── jobs/         # Scheduled tasks (daily analysis jobs)
tests/            # Unit tests (metrics, rules, endpoints)
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
| Market Context | favorable, adverse | S&P 500 vs SMA 200 |

These synthesize into a final asset state: `healthy`, `healthy_but_expensive`, `neutral`, `risky`, or `unattractive`.

**Key synthesis rules:**
- Two or more negative signals → do not force a positive state
- High risk + adverse context → `unattractive`
- Weak fundamentals → `risky` regardless of other signals
- Conflicting signals → prioritize most conservative
- Insufficient clarity → `neutral`

### Layer 3: AI Interpretation (LLM)
Receives only processed states and metrics. Explains and contextualizes results in natural language. Cannot issue orders or price targets. Maximum 3 signals or risks per insight.

### Translation Layer
AI-generated text (scenario, explanation, risks, summary) can be translated into any supported language via Azure Translator. Activated by passing a `language` parameter (ISO code) to analysis endpoints. English is the default and skips translation.

## Domain Concepts

- **User Profile:** risk (low|moderate|high) + horizon (short|medium|long) + objective (growth|income|capital_protection). Modulates interpretation, not base rules.
- **Portfolio:** Persisted set of assets. Upserted on `POST /portfolio/analyze`, retrievable via `GET /portfolio`, updatable via `PUT /portfolio`. Stores overall risk and summary alongside linked insights.
- **Insight:** The minimum unit of value—includes asset state, scenario, horizon, risks, and natural language explanation.
- **Scenario:** Narrative of likely behavior without price predictions or timing.
- **Alternative:** Comparable asset more aligned with the user's profile (not a recommendation).
- **Parabolic SAR:** Trend-confirming indicator (Wilder's algorithm, AF 0.02→0.20). Confirms or moderates SMA-based trend signals.

## MVP Constraints

- Single user, single portfolio, max 20 assets
- Stocks and ETFs only
- No authentication, no broker integration, no real-time alerts
- Data may be delayed; tolerance for imperfect data

## Reference Documents

- `business_rules.md` – Complete business rule specifications and state synthesis logic
- `domain_language.md` – Terminology definitions used consistently throughout the system
- `mvp_scope.md` – MVP boundaries, assumptions, and success criteria
- `architect_prompt.md` – Architectural specification and naming conventions

## Naming Conventions

- Python modules: lowercase with underscores (`portfolio_analysis.py`)
- Pydantic schemas: `schemas.py` or grouped by domain (`asset_schemas.py`)
- Rules: `valuation_rules.py`, `trend_rules.py`
- AI prompts: `prompts.py` or `asset_prompts.py`
