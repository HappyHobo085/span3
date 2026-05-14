#!/bin/bash
set -e

echo "⏳ Voer migrасies uit..."
alembic upgrade head

echo "🌱 Saai databasis..."
python seed.py

echo "🚀 Begin toepassing..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload