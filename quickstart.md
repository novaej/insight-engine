# Quick Start

## Prerequisites

- Python 3.11+
- PostgreSQL (for persistence; not required for development/testing)

## Setup

```bash
# Clone and enter the project
cd insight-engine

# Create virtual environment
# Note: on macOS/Linux the command is often `python3` — if `python` returns
# "command not found", use `python3` instead (inside the venv, `python` works).
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your values:
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/insight_engine
#   OPENAI_API_KEY=sk-...
```

### Create the database

The database referenced in `DATABASE_URL` must exist before starting the server. Create it with:

```bash
psql -U postgres -c "CREATE DATABASE insight_engine;"
```

If PostgreSQL runs in Docker, execute the command inside the container instead (replace `postgres16` with your container name):

```bash
docker exec -it postgres16 psql -U postgres -c "CREATE DATABASE insight_engine;"
```

Then apply the schema:

```bash
alembic upgrade head
```

### Recreate a broken virtual environment

If the venv misbehaves (imports fail, wrong Python version, `pip` errors), delete it and start fresh:

```bash
deactivate  # only if a venv is currently active; ignore "command not found"
rm -rf venv  # Windows: rmdir /s /q venv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
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

## Users & Authentication

All portfolio, position, and insight endpoints **require** an
`Authorization: Bearer <token>` header. Register once, then log in to obtain a
token (each login rotates the previous token).

```bash
# Register
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "supersecret", "name": "Me"}'

# Login — returns the bearer token; store it for the requests below
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "supersecret"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Who am I
curl http://localhost:8000/users/me -H "Authorization: Bearer $TOKEN"

# Update account (changing the password requires current_password and re-login)
curl -X PATCH http://localhost:8000/users/me \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "New Name"}'

# Delete account (removes portfolio, positions, and insights)
curl -X DELETE http://localhost:8000/users/me -H "Authorization: Bearer $TOKEN"
```

## Managing Positions (purchase lots)

Each position row is a **purchase lot** — buying the same ticker twice at different
prices creates two lots, and analysis aggregates them per ticker (summed quantity,
weighted-average cost). Lots are edited by their `id` and edits never trigger
analysis (analysis is on-demand via `POST /portfolio/analyze`).

```bash
# List lots (each has an id)
curl http://localhost:8000/portfolio/positions -H "Authorization: Bearer $TOKEN"

# Add lots — same ticker at different prices is fine
curl -X POST http://localhost:8000/portfolio/positions \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "quantity": 2.0, "purchase_price": 180.0, "purchase_date": "2025-11-02"}'
curl -X POST http://localhost:8000/portfolio/positions \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "quantity": 1.0, "purchase_price": 210.0, "purchase_date": "2026-03-15"}'

# Update a lot by id
curl -X PATCH http://localhost:8000/portfolio/positions/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"quantity": 3.0}'

# Delete a lot by id (the ticker's insight history is kept)
curl -X DELETE http://localhost:8000/portfolio/positions/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Insight History

Every analysis run is kept, so you can track how an asset's state evolves.

```bash
# Latest 50 insights for the portfolio (newest first)
curl http://localhost:8000/insights -H "Authorization: Bearer $TOKEN"

# Filtered by ticker and date range
curl "http://localhost:8000/insights?ticker=AAPL&from=2026-06-01T00:00:00&limit=10" \
  -H "Authorization: Bearer $TOKEN"
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

`assets` is optional — omit it to analyze the stored positions (recommended once
you manage lots via `/portfolio/positions`). When provided, it **replaces** all
stored lots; repeat a ticker to express multiple lots.

```bash
# Analyze the stored positions
curl -X POST http://localhost:8000/portfolio/analyze \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "risk": "moderate",
      "horizon": "long",
      "goal": "growth"
    }
  }'

# Or provide the full asset list (replaces stored lots)
curl -X POST http://localhost:8000/portfolio/analyze \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "risk": "moderate",
      "horizon": "long",
      "goal": "growth"
    },
    "assets": [
      {"ticker": "AAPL", "quantity": 10, "purchase_price": 180.0},
      {"ticker": "AAPL", "quantity": 5, "purchase_price": 210.0},
      {"ticker": "VOO", "quantity": 20}
    ]
  }'
```

### Analyze with translation

```bash
curl -X POST http://localhost:8000/assets/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "user_profile": {
      "risk": "moderate",
      "horizon": "long",
      "goal": "growth"
    },
    "language": "es"
  }'
```

### Retrieve saved portfolio

```bash
curl http://localhost:8000/portfolio -H "Authorization: Bearer $TOKEN"
```

### Update portfolio and re-analyze

```bash
curl -X PUT http://localhost:8000/portfolio \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"ticker": "AAPL", "quantity": 15},
      {"ticker": "GOOGL", "quantity": 8}
    ],
    "language": "fr"
  }'
```

### Notes

`/assets/analyze` is the only analysis endpoint that works without authentication (it analyzes a ticker ad hoc, not your portfolio).

Both `/assets/analyze` and `/portfolio/analyze` accept an optional `use_ai` parameter (defaults to `true`). Set to `false` to skip AI-generated explanations and avoid OpenAI API calls.

All analysis endpoints accept an optional `language` parameter (ISO code, e.g. `es`, `fr`, `pt`) to translate AI-generated text. Requires Azure Translator credentials.

`POST /portfolio/analyze` persists the portfolio (positions are synced to the `assets` list). The `assets` field is optional — omit it to analyze the currently stored positions. Use `GET /portfolio` to retrieve the portfolio with the latest insight per held ticker, or `PUT /portfolio` to update assets and trigger re-analysis. Insights are never deleted; older runs are available via `GET /insights`.

## Postman Collection

Import `insight_engine.postman_collection.json` (repo root) into Postman. It covers
every endpoint with `{{base_url}}`, `{{email}}`, `{{password}}`, `{{ticker}}`, and
`{{position_id}}` variables — running **Login** stores the bearer token in
`{{token}}` automatically for all protected requests.

## Database Migrations

```bash
# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Reset the database (DROPS ALL DATA, recreates, migrates; works with
# local psql or the Docker container via PG_CONTAINER)
./scripts/reset_db.sh
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./dev.db` | Database connection string |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key for explanations |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for generating explanations |
| `AZURE_TRANSLATOR_KEY` | No | — | Azure Translator API key for multi-language support |
| `AZURE_TRANSLATOR_ENDPOINT` | No | — | Azure Translator endpoint URL |
| `AZURE_TRANSLATOR_REGION` | No | — | Azure Translator region (e.g. `westeurope`) |

*The API works without an OpenAI key but won't generate natural language explanations.
Translation requires all three Azure Translator variables. Without them, text is returned in English.
