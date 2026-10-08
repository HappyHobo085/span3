from __future__ import annotations

import csv
import os
import re
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


def _normaliseer(waarde: str | None) -> str:
    """Normaliseer name net genoeg vir veilige, hoofletter-onafhanklike vergelyking."""
    teks = str(waarde or "").strip().casefold()
    teks = re.sub(r"\s*\([^)]*\)\s*$", "", teks).strip()
    teks = teks.replace("_", " ").replace("-", " ")
    return " ".join(teks.split())


def _vind_lokasie(
    db,
    *,
    kampus_id: int,
    lokaal_kode: str,
    lokaal_naam: str,
):
    """Vind die fisiese MOON-lokasie vir 'n CSV-ry.

    Prioriteit:
    1. Fisiese lokaalnaam uit `Lokaal_Naam` (bv. Bitterbessie / Bosvy).
    2. Roosterkode uit `Lokaal` (bv. LERIBA L4 / GH117 A).

    Dit hou die ML-kapasiteit-import versoenbaar met die nuwe rooster waar die
    roosterkode en die fisiese MOON-lokaalnaam nie noodwendig dieselfde is nie.
    """
    lokale = (
        db.query(Lokasie)
        .filter(
            Lokasie.Kampus_ID == kampus_id,
            func.lower(Lokasie.LOK_Tipe).in_(["klaskamer", "lokaal"]),
        )
        .all()
    )

    # Gebruik eers die fisiese naam, want dit is die gesaghebbende MOON-lokasie.
    vir_soek = []
    if lokaal_naam:
        vir_soek.append(lokaal_naam)
    if lokaal_kode and _normaliseer(lokaal_kode) not in {
        _normaliseer(x) for x in vir_soek
    }:
        vir_soek.append(lokaal_kode)

    for kandidaat in vir_soek:
        sleutel = _normaliseer(kandidaat)
        matches = [l for l in lokale if _normaliseer(l.LOK_Naam) == sleutel]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RuntimeError(
                f"Meer as een fisiese lokaal pas by '{kandidaat}' op kampus-ID {kampus_id}."
            )

    return None


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
                lokaal_naam = str(
                    ry.get("lokaal_naam", "")
                    or ry.get("lokaal naam", "")
                    or ry.get("naam", "")
                    or ""
                ).strip()
                kampus_naam = str(ry.get("kampus", "") or "").strip()
                kapasiteit_str = str(ry.get("kapasiteit", "") or "").strip()

                # Minstens een lokaal-identifiseerder is nodig.
                if not (lokaal_kode or lokaal_naam) or not kampus_naam or not kapasiteit_str:
                    continue

                try:
                    kapasiteit = int(float(kapasiteit_str))
                    if kapasiteit <= 0:
                        raise ValueError
                except ValueError:
                    foute.append(
                        f"Ry {ry_nommer}: Ongeldige kapasiteit '{kapasiteit_str}' "
                        f"vir {lokaal_kode or lokaal_naam}"
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

                try:
                    lokasie = _vind_lokasie(
                        db,
                        kampus_id=kampus.Kampus_ID,
                        lokaal_kode=lokaal_kode,
                        lokaal_naam=lokaal_naam,
                    )
                except RuntimeError as exc:
                    foute.append(f"Ry {ry_nommer}: {exc}")
                    continue

                if lokasie is None:
                    beskrywing = lokaal_kode
                    if lokaal_naam:
                        beskrywing += f" / {lokaal_naam}" if beskrywing else lokaal_naam
                    foute.append(
                        f"Ry {ry_nommer}: Klaskamer nie gevind nie - "
                        f"'{beskrywing}' op kampus '{kampus_naam}'"
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
