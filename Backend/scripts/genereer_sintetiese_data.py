from __future__ import annotations

import csv
import json
import os
import random
import re
import sys
from pathlib import Path

from sqlalchemy import func

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import SessionLocal
from models import (
    Klas,
    Lokasie,
    Kampus,
    Module,
    Student_Klas,
    Student_Module,
    Student_Groep,
    Klas_Groep,
)


DAG_MAP = {
    "monday": "Maandag", "maandag": "Maandag",
    "tuesday": "Dinsdag", "dinsdag": "Dinsdag",
    "wednesday": "Woensdag", "woensdag": "Woensdag",
    "thursday": "Donderdag", "donderdag": "Donderdag",
    "friday": "Vrydag", "vrydag": "Vrydag",
    "saturday": "Saterdag", "saterdag": "Saterdag",
    "sunday": "Sondag", "sondag": "Sondag",
}


def normaliseer_dag(value: str | None) -> str:
    sleutel = str(value or "").strip().lower()
    return DAG_MAP.get(sleutel, str(value or "").strip())


def normaliseer_tyd(value: str | None) -> str:
    teks = str(value or "").strip().replace(".", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})", teks)
    if not m:
        return teks
    return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"


def laai_konfigurasie() -> dict:
    pad = Path(__file__).with_name("synth_config.json")
    standaard = {
        "seed": 42,
        "weke": 14,
        "semester_verval_faktor": 0.02,
        "gewoonte_basis_gemiddeld": 0.8,
        "gewoonte_basis_std": 0.1,
        "ruis_swaar_stert_kans": 0.1,
        "ruis_swaar_stert_skaal": 0.3,
        "daaglikse_verstellings": {},
        "tyd_verstellings": {},
        "kampus": None,
        "lokale": [],
    }
    if not pad.exists():
        return standaard
    data = json.loads(pad.read_text(encoding="utf-8"))
    standaard.update(data or {})
    return standaard


def bereken_sessie_bywoning(
    sessie_basis: float,
    week: int,
    dag: str,
    begin_tyd: str,
    config: dict,
) -> float:
    verval = 1.0 - (week * float(config.get("semester_verval_faktor", 0.02)))
    verval = max(verval, 0.0)

    dag_faktor = float(
        (config.get("daaglikse_verstellings") or {}).get(dag, 1.0)
    )
    tyd_faktor = float(
        (config.get("tyd_verstellings") or {}).get(begin_tyd, 1.0)
    )

    verwagte_koers = sessie_basis * verval * dag_faktor * tyd_faktor

    if random.random() < float(config.get("ruis_swaar_stert_kans", 0.1)):
        ruis = random.uniform(
            -float(config.get("ruis_swaar_stert_skaal", 0.3)),
            0.1,
        )
    else:
        ruis = random.gauss(0, 0.05)

    return min(max(verwagte_koers + ruis, 0.0), 1.0)


def _klas_inskrywing(db, klas: Klas) -> int:
    """Unieke studente uit dieselfde drie bronne as die klasregister."""
    ids: set[int] = set()

    for (gid,) in (
        db.query(Student_Klas.Gebruiker_ID)
        .filter(Student_Klas.Klas_ID == klas.Klas_ID)
        .all()
    ):
        ids.add(int(gid))

    for (gid,) in (
        db.query(Student_Module.Gebruiker_ID)
        .filter(Student_Module.Module_ID == klas.Module_ID)
        .all()
    ):
        ids.add(int(gid))

    groep_ids = [
        int(gid)
        for (gid,) in (
            db.query(Klas_Groep.Groep_ID)
            .filter(Klas_Groep.Klas_ID == klas.Klas_ID)
            .all()
        )
    ]
    if groep_ids:
        for (gid,) in (
            db.query(Student_Groep.Gebruiker_ID)
            .filter(Student_Groep.Groep_ID.in_(groep_ids))
            .all()
        ):
            ids.add(int(gid))

    return len(ids)


def genereer_data() -> int:
    config = laai_konfigurasie()
    random.seed(int(config.get("seed", 42)))
    weke = int(config.get("weke", 14))

    db = SessionLocal()
    uitset_rye: list[dict] = []

    try:
        query = (
            db.query(Klas, Module, Lokasie, Kampus)
            .join(Module, Module.Module_ID == Klas.Module_ID)
            .join(Lokasie, Lokasie.Lokasie_ID == Klas.Lokasie_ID)
            .join(Kampus, Kampus.Kampus_ID == Lokasie.Kampus_ID)
            .filter(Klas.Lokasie_ID.isnot(None))
        )

        kampus_filter = str(config.get("kampus") or "").strip()
        if kampus_filter:
            query = query.filter(func.lower(Kampus.KAM_Naam) == kampus_filter.lower())

        lokale = [
            str(x).strip().lower()
            for x in (config.get("lokale") or [])
            if str(x).strip()
        ]
        if lokale:
            query = query.filter(func.lower(Lokasie.LOK_Naam).in_(lokale))

        klasse = query.all()
        if not klasse:
            print("⚠️ Geen gemapte klasse/lokale gevind vir sintetiese data nie.")

        sessie_gewoonte: dict[int, float] = {}

        for klas, mod, lokaal, kampus in klasse:
            inskrywing = _klas_inskrywing(db, klas)
            if inskrywing <= 0:
                continue

            kapasiteit = int(getattr(lokaal, "LOK_Kapasiteit", 0) or 0)
            dag = normaliseer_dag(klas.KLA_Dag)
            begin = normaliseer_tyd(klas.KLA_Begin_Tyd)
            einde = normaliseer_tyd(klas.KLA_Eind_Tyd)

            basis = random.gauss(
                float(config.get("gewoonte_basis_gemiddeld", 0.8)),
                float(config.get("gewoonte_basis_std", 0.1)),
            )
            sessie_gewoonte[klas.Klas_ID] = min(max(basis, 0.3), 1.0)

            for week in range(1, weke + 1):
                koers = bereken_sessie_bywoning(
                    sessie_gewoonte[klas.Klas_ID],
                    week,
                    dag,
                    begin,
                    config,
                )
                skanderings = int(round(inskrywing * koers))

                uitset_rye.append({
                    "Week": week,
                    "Kampus": kampus.KAM_Naam,
                    "Vak": mod.MOD_Kode,
                    "Klas_ID": klas.Klas_ID,
                    "Lokasie_ID": lokaal.Lokasie_ID,
                    "Lokaal": lokaal.LOK_Naam,
                    "Dag": dag,
                    "Begin": begin,
                    "Einde": einde,
                    "Inskrywing": inskrywing,
                    "Kapasiteit": kapasiteit,
                    "Skanderings": skanderings,
                })
    finally:
        db.close()

    uitset_pad = BACKEND_ROOT / "ml_data" / "sintetiese_lokaalgebruik.csv"
    uitset_pad.parent.mkdir(parents=True, exist_ok=True)

    velde = [
        "Week", "Kampus", "Vak", "Klas_ID", "Lokasie_ID", "Lokaal",
        "Dag", "Begin", "Einde", "Inskrywing", "Kapasiteit", "Skanderings",
    ]
    with uitset_pad.open("w", newline="", encoding="utf-8") as f:
        skrywer = csv.DictWriter(f, fieldnames=velde)
        skrywer.writeheader()
        skrywer.writerows(uitset_rye)

    print(
        f"✅ Sintetiese lokaalgebruik-data: {len(uitset_rye)} rye "
        f"na {uitset_pad}"
    )
    return len(uitset_rye)


if __name__ == "__main__":
    try:
        aantal = genereer_data()
        raise SystemExit(0 if aantal > 0 else 2)
    except Exception as exc:
        print(f"❌ Sintetiese data-generering het misluk: {exc}")
        raise
