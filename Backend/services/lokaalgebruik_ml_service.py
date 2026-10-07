from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy.orm import Session

import models

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(
    os.getenv(
        "LOKAALGEBRUIK_MODEL_PATH",
        str(BACKEND_ROOT / "ml_models" / "lokaalgebruik_model.joblib"),
    )
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

_bundle: dict | None = None
_model_mtime: float | None = None


def normaliseer_dag(value: str | None) -> str:
    key = str(value or "").strip().lower()
    return DAG_MAP.get(key, str(value or "").strip())


def _tyd_na_minute(value: str | None) -> int:
    text = str(value or "").strip().replace(".", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})", text)
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def _laai_bundle() -> dict | None:
    global _bundle, _model_mtime

    if not MODEL_PATH.exists():
        _bundle = None
        _model_mtime = None
        return None

    mtime = MODEL_PATH.stat().st_mtime
    if _bundle is not None and _model_mtime == mtime:
        return _bundle

    obj = joblib.load(MODEL_PATH)
    if not isinstance(obj, dict) or "model" not in obj:
        raise RuntimeError("Ongeldige lokaalgebruik model bundle.")

    _bundle = obj
    _model_mtime = mtime
    return _bundle


def kry_ml_status() -> dict:
    try:
        bundle = _laai_bundle()
        if bundle is None:
            return {
                "runtime_ok": False,
                "model_file_exists": False,
                "model_loaded": False,
                "bron": None,
                "model_type": None,
                "metrics": None,
            }
        return {
            "runtime_ok": True,
            "model_file_exists": True,
            "model_loaded": True,
            "bron": bundle.get("bron"),
            "model_type": bundle.get("type"),
            "metrics": bundle.get("metrics"),
            "trained_at": bundle.get("trained_at"),
            "rows": bundle.get("rows"),
        }
    except Exception as exc:
        return {
            "runtime_ok": False,
            "model_file_exists": MODEL_PATH.exists(),
            "model_loaded": False,
            "fout": str(exc),
        }


def _klas_inskrywing(db: Session, klas: models.Klas) -> int:
    ids: set[int] = set()

    for (gid,) in (
        db.query(models.Student_Klas.Gebruiker_ID)
        .filter(models.Student_Klas.Klas_ID == klas.Klas_ID)
        .all()
    ):
        ids.add(int(gid))

    for (gid,) in (
        db.query(models.Student_Module.Gebruiker_ID)
        .filter(models.Student_Module.Module_ID == klas.Module_ID)
        .all()
    ):
        ids.add(int(gid))

    groep_ids = [
        int(gid)
        for (gid,) in (
            db.query(models.Klas_Groep.Groep_ID)
            .filter(models.Klas_Groep.Klas_ID == klas.Klas_ID)
            .all()
        )
    ]
    if groep_ids:
        for (gid,) in (
            db.query(models.Student_Groep.Gebruiker_ID)
            .filter(models.Student_Groep.Groep_ID.in_(groep_ids))
            .all()
        ):
            ids.add(int(gid))

    return len(ids)


def voorspel_vir_kampus_en_dag(
    db: Session,
    kampus_id: int,
    dag: str,
) -> dict[str, Any]:
    bundle = _laai_bundle()
    dag_af = normaliseer_dag(dag)

    if bundle is None:
        return {
            "dag": dag_af,
            "bron": None,
            "model_beskikbaar": False,
            "voorspellings": [],
        }

    rye = (
        db.query(models.Klas, models.Module, models.Lokasie, models.Kampus)
        .join(models.Module, models.Module.Module_ID == models.Klas.Module_ID)
        .join(models.Lokasie, models.Lokasie.Lokasie_ID == models.Klas.Lokasie_ID)
        .join(models.Kampus, models.Kampus.Kampus_ID == models.Lokasie.Kampus_ID)
        .filter(
            models.Lokasie.Kampus_ID == kampus_id,
            models.Klas.Lokasie_ID.isnot(None),
        )
        .all()
    )

    model = bundle["model"]
    resultate: list[dict] = []

    for klas, module, lokasie, kampus in rye:
        if normaliseer_dag(klas.KLA_Dag) != dag_af:
            continue

        inskrywing = _klas_inskrywing(db, klas)
        if inskrywing <= 0:
            continue

        kapasiteit = int(getattr(lokasie, "LOK_Kapasiteit", 0) or 0)

        semester_week = int(os.getenv("LOKAALGEBRUIK_SEMESTER_WEEK", "7") or "7")
        semester_week = max(1, min(14, semester_week))

        X = pd.DataFrame([{
            "Week": semester_week,
            "Kampus": kampus.KAM_Naam,
            "Vak": module.MOD_Kode,
            "Lokaal": lokasie.LOK_Naam,
            "Dag": dag_af,
            "BeginMinuut": _tyd_na_minute(klas.KLA_Begin_Tyd),
            "Inskrywing": inskrywing,
            "Kapasiteit": kapasiteit,
        }])

        koers = float(model.predict(X)[0])
        koers = min(max(koers, 0.0), 1.0)
        voorspelde_bywoning = int(round(koers * inskrywing))
        vulgraad = (
            round((voorspelde_bywoning / kapasiteit) * 100.0, 1)
            if kapasiteit > 0
            else None
        )

        resultate.append({
            "klas_id": klas.Klas_ID,
            "lokasie_id": lokasie.Lokasie_ID,
            "kampus": kampus.KAM_Naam,
            "vak": module.MOD_Kode,
            "lokaal": lokasie.LOK_Naam,
            "dag": dag_af,
            "begin": klas.KLA_Begin_Tyd,
            "einde": klas.KLA_Eind_Tyd,
            "inskrywing": inskrywing,
            "kapasiteit": kapasiteit,
            "voorspelde_bywoning": voorspelde_bywoning,
            "voorspelde_bywoning_pct": round(koers * 100.0, 1),
            "vulgraad_pct": vulgraad,
            "bron": bundle.get("bron", "SINTETIES/ML"),
        })

    resultate.sort(
        key=lambda x: (
            x["begin"] or "",
            -(x["vulgraad_pct"] if x["vulgraad_pct"] is not None else -1),
            x["lokaal"] or "",
        )
    )

    return {
        "dag": dag_af,
        "bron": bundle.get("bron", "SINTETIES/ML"),
        "model_beskikbaar": True,
        "voorspellings": resultate,
    }
