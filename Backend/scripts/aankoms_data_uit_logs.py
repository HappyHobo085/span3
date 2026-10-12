"""Bou Saamry-opleidingsdata uit onlangse kampushek-skanderings.

Vir elke Saamry-gebruiker en elke weeksdag met klasse:
- eerste IN-skandering by 'n kampushek op daardie datum (SA-tyd);
- vroegste klas van die gebruiker op daardie weeksdag;
- offset = vroegste klas − aankoms (minute vroeg), afgekap tot 0–60 soos in
  die oorspronklike opname.

Per (gebruiker, weeksdag) word die mediaan oor die dae geneem, sodat een
persoon met baie skanderings nie die data oorheers nie. Die uitset bevat geen
name nie; `groep` (Gebruiker_ID) word net vir groep-bewuste kruisvalidasie
gebruik en nie in die model gestoor nie.

Dieselfde reëls as `bou_student_saamry_data_van_db` word gebruik (slegs
KAMPUSHEK-logs, Student_Klas + Personeel_Klas, Saamry-kampus filter), sodat
die model leer wat die stelsel later voorspel.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

import pandas as pd
from sqlalchemy import func

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import models  # noqa: E402
from services.compatibiliteit_service import (  # noqa: E402
    DAG_INDEKS_NAAM,
    _na_sa_tyd,
    _parse_tyd_na_minute,
)

LOG_DAE = int(os.getenv("SAAMRY_LOG_DAE", "90"))
# Aankomste buite hierdie venster het waarskynlik niks met die eerste klas te doen nie
# (bv. iemand wat net vir 'n middagklas kom of eers ná die klas opdaag).
MIN_OFFSET, MAKS_OFFSET = -30, 180
KOLOMME = ["groep", "klas_begin_minuut", "voorstad", "rol", "is_koshuis", "offset_tipies"]


def _vroegste_klas_per_dag(db, gebruiker_ids, kampus_van) -> dict[tuple[int, str], int]:
    """(Gebruiker_ID, dagnaam) → vroegste klas-beginminuut."""
    vroegste: dict[tuple[int, str], int] = {}
    for koppel in (models.Student_Klas, models.Personeel_Klas):
        rye = (
            db.query(koppel.Gebruiker_ID, models.Klas, models.Lokasie.Kampus_ID)
            .join(models.Klas, models.Klas.Klas_ID == koppel.Klas_ID)
            .outerjoin(models.Lokasie, models.Lokasie.Lokasie_ID == models.Klas.Lokasie_ID)
            .filter(koppel.Gebruiker_ID.in_(gebruiker_ids))
            .all()
        )
        for gid, klas, klas_kampus in rye:
            kampus = kampus_van.get(gid)
            if kampus is not None and klas_kampus is not None and klas_kampus != kampus:
                continue
            begin = _parse_tyd_na_minute(klas.KLA_Begin_Tyd)
            dag = (klas.KLA_Dag or "").strip().capitalize()
            if begin is None or dag not in DAG_INDEKS_NAAM.values():
                continue
            sleutel = (gid, dag)
            vroegste[sleutel] = min(begin, vroegste.get(sleutel, begin))
    return vroegste


def bou_opleidingsdata(db=None, nou: datetime | None = None) -> pd.DataFrame:
    eie_sessie = db is None
    if eie_sessie:
        from database import SessionLocal
        db = SessionLocal()
    try:
        profiele = db.query(models.SaamryProfiel).all()
        if not profiele:
            return pd.DataFrame(columns=KOLOMME)
        profiel_van = {p.Gebruiker_ID: p for p in profiele}
        kampus_van = {p.Gebruiker_ID: p.Kampus_ID for p in profiele}
        ids = list(profiel_van)

        koshuis = {
            gid for (gid,) in db.query(models.Student.Gebruiker_ID)
            .filter(models.Student.Gebruiker_ID.in_(ids), models.Student.STU_Is_Koshuis.is_(True))
        }

        vanaf = (nou or datetime.utcnow()) - timedelta(days=LOG_DAE)
        logs = (
            db.query(models.ToegangsLogs.Gebruiker_ID, models.ToegangsLogs.TOE_Tydstempel,
                     models.Lokasie.Kampus_ID)
            .join(models.Lokasie, models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID)
            .filter(
                models.ToegangsLogs.Gebruiker_ID.in_(ids),
                models.ToegangsLogs.TOE_Tydstempel >= vanaf,
                models.ToegangsLogs.TOE_Rigting == "IN",
                func.lower(func.trim(models.Lokasie.LOK_Tipe)) == "kampus",
            )
            .all()
        )

        # Eerste IN per gebruiker per kalenderdag (SA-tyd).
        eerste_in: dict[tuple[int, object], int] = {}
        dag_van_datum: dict[object, str] = {}
        for gid, ts, log_kampus in logs:
            kampus = kampus_van.get(gid)
            if kampus is not None and log_kampus != kampus:
                continue
            plaaslik = _na_sa_tyd(ts)
            dag = DAG_INDEKS_NAAM.get(plaaslik.weekday())
            if dag is None:
                continue
            datum = plaaslik.date()
            dag_van_datum[datum] = dag
            minuut = plaaslik.hour * 60 + plaaslik.minute
            sleutel = (gid, datum)
            eerste_in[sleutel] = min(minuut, eerste_in.get(sleutel, minuut))

        vroegste = _vroegste_klas_per_dag(db, ids, kampus_van)

        offsets: dict[tuple[int, str], list[int]] = defaultdict(list)
        for (gid, datum), aankoms in eerste_in.items():
            dag = dag_van_datum[datum]
            klas = vroegste.get((gid, dag))
            if klas is None:
                continue
            offset = klas - aankoms
            if MIN_OFFSET <= offset <= MAKS_OFFSET:
                offsets[(gid, dag)].append(min(max(offset, 0), 60))

        rye = []
        for (gid, dag), waardes in offsets.items():
            p = profiel_van[gid]
            rye.append({
                "groep": gid,
                "klas_begin_minuut": vroegste[(gid, dag)],
                "voorstad": p.Voorstad or "",
                "rol": p.Rol_Tipe or "BEIDE",
                "is_koshuis": int(gid in koshuis),
                "offset_tipies": float(median(waardes)),
            })
        return pd.DataFrame(rye, columns=KOLOMME)
    finally:
        if eie_sessie:
            db.close()
