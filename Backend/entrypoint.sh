#!/bin/sh
set -e

echo "⏳ Skep of werk databasis-tabelle by..."
python -c "from main import models; from database import engine; models.Base.metadata.create_all(bind=engine)"

echo "🌱 Saai databasis..."
python seed.py

echo "🚀 Begin toepassing..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload