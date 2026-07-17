#!/usr/bin/env bash
# Reset the InsightEngine database: DROP, CREATE, and apply all migrations.
#
# DESTROYS ALL DATA. Asks for confirmation unless run with --yes.
#
# Usage:
#   ./scripts/reset_db.sh [--yes]
#
# Configuration via environment variables (defaults match QUICKSTART):
#   DB_NAME       database name        (default: insight_engine)
#   DB_USER       postgres superuser   (default: postgres)
#   PG_CONTAINER  docker container     (default: postgres16; used when psql
#                                       is not on the PATH)

set -euo pipefail

DB_NAME="${DB_NAME:-insight_engine}"
DB_USER="${DB_USER:-postgres}"
PG_CONTAINER="${PG_CONTAINER:-postgres16}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Pick how to reach postgres: local psql, or the docker container
if command -v psql >/dev/null 2>&1; then
    run_sql() { psql -U "$DB_USER" -d postgres -c "$1"; }
    echo "Using local psql as $DB_USER"
elif command -v docker >/dev/null 2>&1; then
    run_sql() { docker exec -i "$PG_CONTAINER" psql -U "$DB_USER" -d postgres -c "$1"; }
    echo "Using docker container '$PG_CONTAINER'"
else
    echo "Error: neither psql nor docker found on PATH" >&2
    exit 1
fi

if [[ "${1:-}" != "--yes" ]]; then
    read -r -p "This will DELETE ALL DATA in database '$DB_NAME'. Continue? [y/N] " answer
    case "$answer" in
        [yY]|[yY][eE][sS]) ;;
        *) echo "Aborted."; exit 1 ;;
    esac
fi

echo "Dropping database '$DB_NAME'..."
run_sql "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"

echo "Creating database '$DB_NAME'..."
run_sql "CREATE DATABASE $DB_NAME;"

echo "Applying migrations..."
cd "$PROJECT_DIR"
if [[ -x "venv/bin/alembic" ]]; then
    venv/bin/alembic upgrade head
else
    alembic upgrade head
fi

echo "Done. Database '$DB_NAME' is empty and fully migrated."
echo "Next: register a user (POST /users) and log in (POST /login)."
