# Quick Start

## Prerequisites

- Python 3.11+
- PostgreSQL (for persistence; not required for development/testing)

## Setup

```bash
# Clone and enter the project
cd insight-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your values:
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/insight_engine
#   OPENAI_API_KEY=sk-...
```

## Run the Server

```bash
uvicorn insight_engine.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=insight_engine

# Single module
pytest tests/test_synthesis.py -v
```

## Lint

```bash
ruff check .
ruff format .
```

## Example Requests

### Analyze a single asset

```bash
curl -X POST http://localhost:8000/assets/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "user_profile": {
      "risk": "moderate",
      "horizon": "long",
      "goal": "growth"
    }
  }'
```

### Analyze without AI (skip OpenAI call)

```bash
curl -X POST http://localhost:8000/assets/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "use_ai": false
  }'
```

### Analyze a portfolio

```bash
curl -X POST http://localhost:8000/portfolio/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "risk": "moderate",
      "horizon": "long",
      "goal": "growth"
    },
    "assets": [
      {"ticker": "AAPL", "quantity": 10},
      {"ticker": "MSFT", "quantity": 5},
      {"ticker": "VOO", "quantity": 20}
    ]
  }'
```

Both `/assets/analyze` and `/portfolio/analyze` accept an optional `use_ai` parameter (defaults to `true`). Set to `false` to skip AI-generated explanations and avoid OpenAI API calls.

## Database Migrations

```bash
# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./dev.db` | Database connection string |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key for explanations |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for generating explanations |

*The API works without an OpenAI key but won't generate natural language explanations.
