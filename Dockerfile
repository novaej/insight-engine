FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; pandas/numpy ship manylinux wheels.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
COPY insight_engine ./insight_engine
COPY alembic ./alembic
COPY alembic.ini ./
COPY config ./config

# Editable install keeps the source tree in place so the config/ JSON files
# resolve via their relative paths at runtime.
RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "insight_engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
