#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
TABLE_NAME="toegangs_logs"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

DB_USER="${DB_USER:-${POSTGRES_USER:-postgres}}"
DB_NAME="${DB_NAME:-${POSTGRES_DB:-MOON}}"
DB_CONTAINER="${DB_CONTAINER:-moon_db}"

if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
  echo "Container $DB_CONTAINER is not running."
  exit 1
fi

echo "Listing databases in $DB_CONTAINER..."
docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c '\l'

echo

echo "Checking $TABLE_NAME in database $DB_NAME..."
if docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT to_regclass('public.$TABLE_NAME')" | grep -q "$TABLE_NAME"; then
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT * FROM $TABLE_NAME;"
else
  echo "Table public.$TABLE_NAME does not exist yet."
fi