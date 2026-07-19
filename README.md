# InsightEngine

Backend MVP for personal investment portfolio analysis. Provides educational and contextual analysis of stocks and ETFs — never financial advice, buy/sell signals, or price predictions.

**Frontend product name:** Vestio

## Philosophy

"Rules classify states, they do not give orders." All outputs are educational and contextual, never prescriptive.

## Architecture

Three-layer analysis engine:

1. **Metrics** — Raw financial computations (SMA, Parabolic SAR, volatility, P/E, margins)
2. **Rules** — Deterministic business logic classifying asset states across 5 dimensions
3. **AI Interpretation** — Natural language explanations via OpenAI (receives only processed states)
4. **Translation** — Optional multi-language output via Azure Translator

### Five Dimensions

| Dimension | States |
|-----------|--------|
| Trend | bullish, sideways, bearish |
| Valuation | cheap, reasonable, expensive, inconclusive |
| Fundamentals | strong, mixed, weak |
| Risk/Volatility | low, medium, high |
| Market Context | favorable, adverse |

These synthesize into a final asset state: `healthy`, `healthy_but_expensive`, `neutral`, `risky`, or `unattractive`.

## Tech Stack

- Python + FastAPI
- PostgreSQL + SQLAlchemy (async)
- yfinance for market data
- OpenAI API for text explanations
- Azure Translator for multi-language support
- Mailgun for email alerts + APScheduler for the monitoring watchdog
- Alembic for migrations

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/users` | — | Register (email, password) |
| POST | `/login` | — | Get bearer token |
| GET/PATCH/DELETE | `/users/me` | ✓ | Account management |
| GET/POST | `/portfolio/positions` | ✓ | List / add purchase lots |
| PATCH/DELETE | `/portfolio/positions/{id}` | ✓ | Edit / remove a lot |
| POST | `/portfolio/analyze` | ✓ | Analyze portfolio (stored positions or provided assets) |
| GET | `/portfolio` | ✓ | Saved portfolio + latest insight per ticker |
| PUT | `/portfolio` | ✓ | Replace assets and re-analyze |
| GET | `/insights` | ✓ | Insight history (filter by ticker/date) |
| POST | `/profile/interpret` | ✓ | Plain words → structured user profile (AI) |
| POST | `/monitoring/run` | token | Run the change-detection sweep, email digests |
| POST | `/assets/analyze` | — | Analyze a single ticker ad hoc |
| GET | `/health` | — | Health check |

All analysis endpoints accept an optional `language` parameter (ISO code, e.g. `es`, `fr`, `pt`) to translate AI-generated text into the target language. See `api_reference.md` for details and `insight_engine.postman_collection.json` for ready-made requests.

## Project Structure

```
insight_engine/
├── api/             # FastAPI routes, auth dependency, response schemas
├── domain/          # Enums, entities, ORM models
├── services/        # Metrics, analysis orchestration, alternatives, translation
├── rules/           # Deterministic business rules + synthesis
├── ai/              # Prompt templates and LLM handlers
├── adapters/        # Yahoo Finance (+ caching/retry), OpenAI, Azure, Mailgun
└── jobs/            # Monitoring watchdog CLI entrypoint
```

CI (`.github/workflows/ci.yml`) runs `ruff check` + `pytest` on every push and PR.

## MVP Constraints

- Multi-user with bearer-token auth; one portfolio per user
- Max 20 distinct tickers (multiple purchase lots per ticker allowed)
- Stocks and ETFs only
- No broker integration
- Data may be delayed

## License

Private / experimental use.
