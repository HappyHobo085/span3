from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from sqlalchemy import func

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import SessionLocal
from models import Lokasie, Kampus


def _csv_pad() -> Path:
    override = os.getenv("LOKALE_CSV_PATH", "").strip()
    if override:
        return Path(override)
    return BACKEND_ROOT / "ml_data" / "lokale.csv"


def vul_lokasies() -> int:
    csv_pad = _csv_pad()
    if not csv_pad.exists():
        print(f"ℹ️ Geen lokale.csv gevind by {csv_pad}; kapasiteit-import word oorgeslaan.")
        return 0

    db = SessionLocal()
    opgedateer = 0
    foute: list[str] = []

    try:
        with csv_pad.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            leser = csv.DictReader(f)
            if not leser.fieldnames:
                print("⚠️ lokale.csv het geen opskrifte nie.")
                return 0

            leser.fieldnames = [str(h).strip().lower() for h in leser.fieldnames]

            for ry_nommer, ry in enumerate(leser, start=2):
                lokaal_kode = str(ry.get("lokaal", "") or "").strip()
                kampus_naam = str(ry.get("kampus", "") or "").strip()
                kapasiteit_str = str(ry.get("kapasiteit", "") or "").strip()

                if not lokaal_kode or not kampus_naam or not kapasiteit_str:
                    continue

                try:
                    kapasiteit = int(kapasiteit_str)
                    if kapasiteit <= 0:
                        raise ValueError
                except ValueError:
                    foute.append(
                        f"Ry {ry_nommer}: Ongeldige kapasiteit '{kapasiteit_str}' vir {lokaal_kode}"
                    )
                    continue

                kampus = (
                    db.query(Kampus)
                    .filter(func.lower(Kampus.KAM_Naam) == kampus_naam.lower())
                    .first()
                )
                if kampus is None:
                    foute.append(
                        f"Ry {ry_nommer}: Kampus nie gevind nie - '{kampus_naam}'"
                    )
                    continue

                # Ondersteun beide huidige 'Klaskamer' en historiese 'Lokaal'.
                lokasie = (
                    db.query(Lokasie)
                    .filter(
                        func.lower(Lokasie.LOK_Naam) == lokaal_kode.lower(),
                        Lokasie.Kampus_ID == kampus.Kampus_ID,
                        func.lower(Lokasie.LOK_Tipe).in_(["klaskamer", "lokaal"]),
                    )
                    .first()
                )

                if lokasie is None:
                    foute.append(
                        f"Ry {ry_nommer}: Klaskamer nie gevind nie - "
                        f"'{lokaal_kode}' op kampus '{kampus_naam}'"
                    )
                    continue

                if not hasattr(lokasie, "LOK_Kapasiteit"):
                    raise RuntimeError(
                        "Lokasie model het nie LOK_Kapasiteit nie. "
                        "Deploy eers die LOK_Kapasiteit model/migration."
                    )

                lokasie.LOK_Kapasiteit = kapasiteit
                opgedateer += 1

        db.commit()
        print(f"✅ {opgedateer} lokale se kapasiteite is opgedateer.")

        if foute:
            print("⚠️ Sommige CSV-rye kon nie gekoppel word nie:")
            for fout in foute:
                print(f" - {fout}")

        return opgedateer
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        vul_lokasies()
    except Exception as exc:
        print(f"❌ Kapasiteit-import het misluk: {exc}")
        raise SystemExit(1)
