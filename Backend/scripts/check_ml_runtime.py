"""Railway startup smoke check vir MOON se Saamry ML runtime.

Hierdie script:
- bevestig dat aankoms_model.joblib bestaan;
- bevestig dat joblib dit kan laai;
- toets services/ml_service.py se runtime prediction;
- verlaat met exit code 1 indien enigiets fout is.

Geen training en geen databasis-skryfwerk word hier gedoen nie.
"""

from __future__ import annotations

import os
import sys

# Wanneer hierdie file as "python scripts/check_ml_runtime.py" loop,
# is /app/scripts die eerste import-pad. Voeg die backend root (/app) by.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from services.ml_service import (
    kry_ml_runtime_status,
    voorspel_aankomstyd_offset,
)


def main() -> int:
    print("🧠 Toets Saamry ML runtime...")

    status = kry_ml_runtime_status()

    if not status["model_file_exists"]:
        print("❌ ML model file ontbreek: ml_models/aankoms_model.joblib")
        return 1

    if not status["model_loaded"]:
        print("❌ ML model kon nie met joblib gelaai word nie")
        return 1

    # Toets die presiese prediction-pad wat die Saamry recommender gebruik.
    offset, sigma, bron = voorspel_aankomstyd_offset(
        vroegste_klas_minuut=8 * 60,
        kluster="oos",
        rol="BEIDE",
        is_koshuis=0,
    )

    if not isinstance(offset, int):
        print("❌ ML prediction het 'n ongeldige offset teruggegee")
        return 1
    if not isinstance(sigma, (int, float)) or sigma <= 0:
        print("❌ ML prediction het 'n ongeldige onsekerheidswaarde teruggegee")
        return 1
    if bron not in {"ML_MODEL", "MEDIAAN"}:
        print("❌ ML prediction het 'n onbekende bron teruggegee")
        return 1

    print(
        "✅ Saamry ML runtime is gereed "
        f"(model: {status.get('model_type') or 'ONBEKEND'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
