from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.kies_en_vul_lokasies import vul_lokasies
from scripts.genereer_sintetiese_data import genereer_data
from scripts.train_lokaalgebruik_model import train


def _true(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "ja", "on"}


def main() -> int:
    if not _true("LOKAALGEBRUIK_AUTO_TRAIN", True):
        print("ℹ️ LOKAALGEBRUIK_AUTO_TRAIN=false — bootstrap oorgeslaan.")
        return 0

    strict = _true("LOKAALGEBRUIK_ML_STRICT", False)

    print("🏫 Begin lokaalgebruik ML bootstrap...")

    try:
        vul_lokasies()
        rye = genereer_data()

        if rye <= 0:
            msg = (
                "Geen sintetiese training data is gegenereer nie. "
                "Kontroleer klas-lokasie mappings, inskrywings en kapasiteite."
            )
            if strict:
                raise RuntimeError(msg)
            print(f"⚠️ {msg}")
            return 0

        train()
        print("✅ Lokaalgebruik ML bootstrap voltooi.")
        return 0
    except Exception as exc:
        print(f"❌ Lokaalgebruik ML bootstrap fout: {exc}")
        if strict:
            return 1
        print("⚠️ Backend mag voortgaan omdat LOKAALGEBRUIK_ML_STRICT=false.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
