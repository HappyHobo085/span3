#!/bin/sh
set -e

echo "🧠 Kontroleer ML runtime..."
if python scripts/check_ml_runtime.py; then
  echo "✅ ML runtime kontrole geslaag"
else
  echo "❌ ML runtime kontrole het misluk"
  if [ "${ML_STRICT_STARTUP:-true}" = "true" ]; then
    echo "🛑 ML_STRICT_STARTUP=true — backend gaan nie met 'n gebreekte ML runtime begin nie"
    exit 1
  fi
  echo "⚠️ ML_STRICT_STARTUP=false — backend begin met die bestaande fallback gedrag"
fi

echo "⏳ Skep of werk databasis-tabelle by..."
python -c "from main import models; from database import engine; models.Base.metadata.create_all(bind=engine)"

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "🌱 Saai databasis..."
  python seed.py
fi

echo "🏫 Berei lokaalgebruik ML voor..."
if python scripts/bootstrap_lokaalgebruik_ml.py; then
  echo "✅ Lokaalgebruik ML bootstrap klaar"
else
  echo "❌ Lokaalgebruik ML bootstrap het misluk"
  if [ "${LOKAALGEBRUIK_ML_STRICT:-false}" = "true" ]; then
    exit 1
  fi
  echo "⚠️ Backend begin sonder lokaalgebruik ML predictions"
fi

echo "🚀 Begin toepassing..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1