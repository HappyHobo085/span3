"""Lokaalgebruikvoorspelling vir die Kampus-bladsy.

Neem die komende week se rooster uit die databasis, voorspel die
skanderingskoers per sessie (services/lokaalgebruik_model.py) en bereken die
verwagte getal studente en die vulgraad per lokaal.
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy.orm import Session

import models
from services.lokaalgebruik_model import (
    METODE_ETIKETTE,
    METODE_ROOSTER,
    berei_voor,
    normaliseer_dag,
    normaliseer_tyd,
    tyd_na_minute,
    voorspel_koers,
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(
    os.getenv(
        "LOKAALGEBRUIK_MODEL_PATH",
        str(BACKEND_ROOT / "ml_models" / "lokaalgebruik_model.joblib"),
    )
)

_bundle: dict | None = None
_model_mtime: float | None = None


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
    if not isinstance(obj, dict) or obj.get("weergawe") != 2:
        raise RuntimeError("Ou of ongeldige lokaalgebruik-bundel; lei die model weer op.")

    _bundle = obj
    _model_mtime = mtime
    return _bundle


def _veilig_laai() -> tuple[dict | None, str | None]:
    try:
        return _laai_bundle(), None
    except Exception as exc:
        return None, str(exc)


def kry_ml_status() -> dict:
    bundle, fout = _veilig_laai()
    if bundle is None:
        return {
            "model_file_exists": MODEL_PATH.exists(),
            "model_loaded": False,
            "fout": fout,
        }
    return {
        "model_file_exists": True,
        "model_loaded": True,
        "databron": bundle.get("databron"),
        "metode": bundle.get("metode"),
        "keuse_rede": bundle.get("keuse_rede"),
        "metrics": bundle.get("metrics"),
        "interval": bundle.get("interval"),
        "laaste_week": bundle.get("laaste_week"),
        "voorspel_week": bundle.get("voorspel_week"),
        "trained_at": bundle.get("trained_at"),
        "rows": bundle.get("rows"),
    }


def inskrywings_per_klas(db: Session, klasse: list[models.Klas]) -> dict[int, int]:
    """Unieke studente per klas uit Student_Klas, Student_Module en groepe (gebondel)."""
    klas_ids = [k.Klas_ID for k in klasse]
    module_ids = {k.Module_ID for k in klasse}
    if not klas_ids:
        return {}

    per_klas: dict[int, set[int]] = defaultdict(set)
    for kid, gid in db.query(models.Student_Klas.Klas_ID, models.Student_Klas.Gebruiker_ID).filter(
        models.Student_Klas.Klas_ID.in_(klas_ids)
    ):
        per_klas[kid].add(gid)

    per_module: dict[int, set[int]] = defaultdict(set)
    for mid, gid in db.query(models.Student_Module.Module_ID, models.Student_Module.Gebruiker_ID).filter(
        models.Student_Module.Module_ID.in_(module_ids)
    ):
        per_module[mid].add(gid)

    klas_groepe: dict[int, set[int]] = defaultdict(set)
    for kid, grp in db.query(models.Klas_Groep.Klas_ID, models.Klas_Groep.Groep_ID).filter(
        models.Klas_Groep.Klas_ID.in_(klas_ids)
    ):
        klas_groepe[kid].add(grp)

    per_groep: dict[int, set[int]] = defaultdict(set)
    alle_groepe = set().union(*klas_groepe.values()) if klas_groepe else set()
    if alle_groepe:
        for grp, gid in db.query(models.Student_Groep.Groep_ID, models.Student_Groep.Gebruiker_ID).filter(
            models.Student_Groep.Groep_ID.in_(alle_groepe)
        ):
            per_groep[grp].add(gid)

    uitslag = {}
    for k in klasse:
        ids = set(per_klas[k.Klas_ID]) | per_module[k.Module_ID]
        for grp in klas_groepe[k.Klas_ID]:
            ids |= per_groep[grp]
        uitslag[k.Klas_ID] = len(ids)
    return uitslag


def _vlag_konflikte(gleuwe: list[dict]) -> None:
    """Merk sessies wat in dieselfde lokaal op dieselfde dag oorvleuel."""
    groepe: dict[tuple, list[dict]] = defaultdict(list)
    for g in gleuwe:
        groepe[(g["lokasie_id"], g["dag"])].append(g)
    for rye in groepe.values():
        for i, a in enumerate(rye):
            for b in rye[i + 1:]:
                if None in (a["_begin_min"], a["_einde_min"], b["_begin_min"], b["_einde_min"]):
                    continue
                if a["_begin_min"] < b["_einde_min"] and b["_begin_min"] < a["_einde_min"]:
                    a["konflik"] = b["konflik"] = True


def voorspel_vir_kampus(db: Session, kampus_id: int, dag: str | None = None) -> dict[str, Any]:
    bundle, laai_fout = _veilig_laai()

    rye = (
        db.query(models.Klas, models.Module, models.Lokasie)
        .join(models.Module, models.Module.Module_ID == models.Klas.Module_ID)
        .join(models.Lokasie, models.Lokasie.Lokasie_ID == models.Klas.Lokasie_ID)
        .filter(models.Lokasie.Kampus_ID == kampus_id)
        .all()
    )
    dag_af = normaliseer_dag(dag) if dag else None
    if dag_af:
        rye = [r for r in rye if normaliseer_dag(r[0].KLA_Dag) == dag_af]

    inskrywings = inskrywings_per_klas(db, [klas for klas, _, _ in rye])
    rooster = pd.DataFrame([
        {
            "Week": 0,
            "Sessie": str(klas.Klas_ID),
            "Klas_ID": klas.Klas_ID,
            "Vak": mod.MOD_Kode,
            "Lokaal": lok.LOK_Naam,
            "Lokasie_ID": lok.Lokasie_ID,
            "Dag": klas.KLA_Dag,
            "Begin": klas.KLA_Begin_Tyd,
            "Einde": klas.KLA_Eind_Tyd,
            "Inskrywing": inskrywings.get(klas.Klas_ID, 0),
            "Kapasiteit": lok.LOK_Kapasiteit or 0,
        }
        for klas, mod, lok in rye
    ], columns=["Week", "Sessie", "Klas_ID", "Vak", "Lokaal", "Lokasie_ID", "Dag",
                "Begin", "Einde", "Inskrywing", "Kapasiteit"])
    teiken = berei_voor(rooster).reset_index(drop=True)

    koerse, metode = voorspel_koers(bundle, teiken)
    interval = (bundle or {}).get("interval") or {}
    wys_reeks = bool(interval.get("wys")) and metode != METODE_ROOSTER

    gleuwe: list[dict] = []
    for i, ry in teiken.iterrows():
        insk = int(ry["Inskrywing"])
        kap = int(ry["Kapasiteit"]) or None
        koers = float(koerse[i])
        verwag = int(round(koers * insk))

        def vul(k: float) -> float | None:
            return round(k * insk / kap, 3) if kap else None

        reeks = None
        if wys_reeks:
            lo = min(max(koers + interval["q_lo"], 0.0), 1.0)
            hi = min(max(koers + interval["q_hi"], 0.0), 1.0)
            reeks = {
                "koers_laag": round(lo, 3), "koers_hoog": round(hi, 3),
                "getal_laag": int(round(lo * insk)), "getal_hoog": int(round(hi * insk)),
                "vulgraad_laag": vul(lo), "vulgraad_hoog": vul(hi),
            }

        vulgraad = vul(koers)
        gleuwe.append({
            "klas_id": int(ry["Klas_ID"]),
            "lokasie_id": int(ry["Lokasie_ID"]),
            "vak": ry["Vak"],
            "lokaal": ry["Lokaal"],
            "dag": ry["Dag"],
            "begin": ry["Begin"],
            "einde": normaliseer_tyd(ry["Einde"]),
            "inskrywing": insk,
            "kapasiteit": kap,
            "geskeduleerde_vulgraad": vul(1.0),
            "koers": round(koers, 3),
            "verwagte_getal": verwag,
            "vulgraad": vulgraad,
            "reeks": reeks,
            "oor_kapasiteit": vulgraad is not None and vulgraad > 1.0,
            "kan_oorloop": bool(reeks and reeks["vulgraad_hoog"] is not None and reeks["vulgraad_hoog"] > 1.0),
            "konflik": False,
            "_begin_min": tyd_na_minute(ry["Begin"]),
            "_einde_min": tyd_na_minute(ry["Einde"]),
        })

    _vlag_konflikte(gleuwe)
    for g in gleuwe:
        g.pop("_begin_min")
        g.pop("_einde_min")
    gleuwe.sort(key=lambda g: (g["dag"], g["begin"], g["lokaal"]))

    return {
        "kampus_id": kampus_id,
        "dag": dag_af,
        "voorspel_week": (bundle or {}).get("voorspel_week"),
        "laaste_data_week": (bundle or {}).get("laaste_week"),
        "metode": metode,
        "metode_etiket": METODE_ETIKETTE[metode],
        "keuse_rede": (bundle or {}).get("keuse_rede") or laai_fout
            or "Geen opgeleide model nie; slegs die rooster word gewys.",
        "databron": (bundle or {}).get("databron"),
        "metrics": (bundle or {}).get("metrics"),
        "interval": {
            "wys": wys_reeks,
            "dekking": interval.get("dekking"),
        },
        "gleuwe": gleuwe,
    }
