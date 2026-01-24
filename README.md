# InsightEngine

Backend MVP for personal investment portfolio analysis. Provides educational and contextual analysis of stocks and ETFs — never financial advice, buy/sell signals, or price predictions.

**Frontend product name:** Vestio

## Philosophy

"Rules classify states, they do not give orders." All outputs are educational and contextual, never prescriptive.

## Architecture

Three-layer analysis engine:

1. **Metrics** — Raw financial computations (SMA, volatility, P/E, margins)
2. **Rules** — Deterministic business logic classifying asset states across 5 dimensions
3. **AI Interpretation** — Natural language explanations via OpenAI (receives only processed states)

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
- Alembic for migrations

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/assets/analyze` | Analyze a single ticker |
| POST | `/portfolio/analyze` | Analyze full portfolio (max 20 assets) |
| GET | `/health` | Health check |

## Project Structure

```
insight_engine/
├── api/             # FastAPI routes and response schemas
├── domain/          # Enums, entities, ORM models
├── services/        # Data fetching, metrics, orchestration
├── rules/           # Deterministic business rules + synthesis
├── ai/              # Prompt templates and OpenAI handler
└── jobs/            # Scheduled daily analysis
```

## MVP Constraints

- Single user, single portfolio, max 20 assets
- Stocks and ETFs only
- No authentication, no broker integration
- Data may be delayed

## License

Private / experimental use.
