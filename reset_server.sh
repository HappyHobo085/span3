#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is not installed or not available on PATH."
  exit 1
fi

echo "Pulling latest project changes..."
git pull --ff-only

echo "Stopping and removing existing containers..."
"${COMPOSE[@]}" down --remove-orphans

echo "Rebuilding and starting containers..."
"${COMPOSE[@]}" up --build

echo "Server reset complete."
