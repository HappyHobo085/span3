#!/bin/sh
set -e

echo "⏳ Skep of werk databasis-tabelle by..."
python -c "from main import models; from database import engine; models.Base.metadata.create_all(bind=engine)"

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "🌱 Saai databasis..."
  python seed.py
fi

echo "🚀 Begin toepassing..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2