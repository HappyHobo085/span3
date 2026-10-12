#!/bin/sh
set -e

# Die twee ML-modele is onafhanklik: Saamry (aankomstyd, aankoms_model.joblib)
# en Lokaalgebruik (vulgraad, lokaalgebruik_model.joblib). Albei stappe loop
# altyd; die streng-vlae word eers aan die einde toegepas, sodat die een se
# fout nie keer dat die ander opgelei of gekontroleer word nie.

echo "🧠 Kontroleer Saamry ML runtime..."
SAAMRY_ML_OK=true
if python scripts/check_ml_runtime.py; then
  echo "✅ Saamry ML runtime kontrole geslaag"
else
  SAAMRY_ML_OK=false
  echo "❌ Saamry ML runtime kontrole het misluk"
fi

echo "⏳ Skep of werk databasis-tabelle by..."
python -c "from main import models; from database import engine; models.Base.metadata.create_all(bind=engine)"

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "🌱 Saai databasis..."
  python seed.py
fi

echo "🏫 Berei lokaalgebruik ML voor..."
LOKAALGEBRUIK_ML_OK=true
if python scripts/bootstrap_lokaalgebruik_ml.py; then
  echo "✅ Lokaalgebruik ML bootstrap klaar"
else
  LOKAALGEBRUIK_ML_OK=false
  echo "❌ Lokaalgebruik ML bootstrap het misluk"
fi

if [ "$SAAMRY_ML_OK" = "false" ]; then
  if [ "${ML_STRICT_STARTUP:-true}" = "true" ]; then
    echo "🛑 ML_STRICT_STARTUP=true — backend gaan nie met 'n gebreekte Saamry ML runtime begin nie"
    exit 1
  fi
  echo "⚠️ ML_STRICT_STARTUP=false — Saamry begin met die bestaande fallback gedrag"
fi

if [ "$LOKAALGEBRUIK_ML_OK" = "false" ]; then
  if [ "${LOKAALGEBRUIK_ML_STRICT:-false}" = "true" ]; then
    exit 1
  fi
  echo "⚠️ Backend begin sonder lokaalgebruik ML predictions"
fi

echo "🚀 Begin toepassing..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
