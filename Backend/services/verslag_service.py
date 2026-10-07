"""Bywoningsverslag — bou 'n Excel-werkboek met statistiek en geskiedenis.

Die verslag word per rol afgebaken:
- Administrateur: alle gebruikers (opsioneel net een kampus).
- Kampus_Opsigter: net die kampus waaraan die opsigter gekoppel is.
- Personeel: net die studente in die personeellid se eie klasse
  (klasbywoning; geen kampus-hek geskiedenis nie).

Alle tye in die databasis is UTC-naive; die verslag wys SA-tyd.
"""

from __future__ import annotations

import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, joinedload

import models
from routers.klasse import (
    _DAE,
    _SA_TZ,
    _klas_roster_gebruiker_ids,
    _klas_scan_venster,
    resolver_personeel_rooster,
)
from services.gebruiker_service import kies_primere_rol

MAKS_DAE = 366
LAE_BYWONING = 0.75  # onder hierdie drempel word 'n persoon as "lae bywoning" gemerk

OMVANG_ALLES = "alles"
OMVANG_KAMPUS = "kampus"
OMVANG_KLASSE = "klasse"


# --------------------------------------------------------------------------- #
# Hulpfunksies
# --------------------------------------------------------------------------- #

def _na_sa(dt_utc: datetime) -> datetime:
    """UTC-naive -> SA-tyd (naive, sodat Excel dit as 'n gewone datum/tyd wys)."""
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(_SA_TZ).replace(tzinfo=None)


def _sa_dag_begin_utc(dag: date) -> datetime:
    return (
        datetime.combine(dag, datetime.min.time(), tzinfo=_SA_TZ)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )


def _werksdae(van: date, tot: date) -> list[date]:
    dae = []
    dag = van
    while dag <= tot:
        if dag.weekday() < 5:
            dae.append(dag)
        dag += timedelta(days=1)
    return dae


_DAG_NAME = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrydag", "Saterdag", "Sondag"]
_MAAND_NAME = ["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Des"]


def _dag_naam(dag: date) -> str:
    return _DAG_NAME[dag.weekday()]


def _datum_teks(dag: date) -> str:
    return f"{_dag_naam(dag)} {dag.day} {_MAAND_NAME[dag.month - 1]} {dag.year}"


def _gem_tyd(tye: list[datetime]) -> Optional[str]:
    if not tye:
        return None
    minute = sum(t.hour * 60 + t.minute for t in tye) / len(tye)
    return f"{int(minute // 60):02d}:{int(minute % 60):02d}"


def _verhouding(teller: int, noemer: int) -> Optional[float]:
    return (teller / noemer) if noemer else None


def _rol_namen(gebruiker: models.Gebruikers) -> list[str]:
    namen = [a.rol.ROL_Naam for a in (gebruiker.gebruikers_rolle or []) if a.rol is not None]
    if not namen and gebruiker.rol is not None:
        namen = [gebruiker.rol.ROL_Naam]
    return namen


def _nommer(gebruiker: models.Gebruikers) -> Optional[str]:
    for rel, veld in (
        ("student", "STU_Nommer"),
        ("personeel", "PER_Nommer"),
        ("kampus_opsigter", "KAMO_Nommer"),
        ("sekuriteit_wag", "SEK_Nommer"),
    ):
        obj = getattr(gebruiker, rel, None)
        if obj is not None:
            return getattr(obj, veld)
    return None


@dataclass
class Omvang:
    tipe: str
    beskrywing: str
    kampus_id: Optional[int] = None
    klas_ids: Optional[set[int]] = None


@dataclass
class Persoon:
    gebruiker: models.Gebruikers
    rol: str
    is_student: bool
    dae_in: set[date] = field(default_factory=set)
    aankomste: dict[date, datetime] = field(default_factory=dict)
    vertrekke: dict[date, datetime] = field(default_factory=dict)
    skanderings: int = 0
    laaste_log: Optional[models.ToegangsLogs] = None
    sessies_geskeduleer: int = 0
    sessies_bygewoon: int = 0

    @property
    def naam(self) -> str:
        return f"{self.gebruiker.GEB_Naam} {self.gebruiker.GEB_Van}".strip()


# --------------------------------------------------------------------------- #
# Omvang
# --------------------------------------------------------------------------- #

def bepaal_omvang(
    db: Session,
    gebruiker: models.Gebruikers,
    rolle: list[str],
    kampus_id: Optional[int] = None,
) -> Omvang:
    if "Administrateur" in rolle:
        if kampus_id is not None:
            kampus = db.get(models.Kampus, kampus_id)
            if kampus is None:
                raise HTTPException(status_code=404, detail="Kampus nie gevind nie")
            return Omvang(OMVANG_KAMPUS, f"Kampus: {kampus.KAM_Naam}", kampus_id=kampus_id)
        return Omvang(OMVANG_ALLES, "Alle kampusse")

    if "Kampus_Opsigter" in rolle:
        opsigter = gebruiker.kampus_opsigter
        if opsigter is None or opsigter.Kampus_ID is None:
            raise HTTPException(status_code=400, detail="Jy is nie aan 'n kampus gekoppel nie")
        kampus = db.get(models.Kampus, opsigter.Kampus_ID)
        naam = kampus.KAM_Naam if kampus else f"#{opsigter.Kampus_ID}"
        return Omvang(OMVANG_KAMPUS, f"Kampus: {naam}", kampus_id=opsigter.Kampus_ID)

    if "Personeel" in rolle:
        klas_ids = {k["Klas_ID"] for k in resolver_personeel_rooster(db, gebruiker.Gebruiker_ID)}
        return Omvang(OMVANG_KLASSE, "My klasse", klas_ids=klas_ids)

    raise HTTPException(status_code=403, detail="Jy het nie toegang tot bywoningsverslae nie")


# --------------------------------------------------------------------------- #
# Data-insameling
# --------------------------------------------------------------------------- #

def _klasse_in_omvang(db: Session, omvang: Omvang) -> list[models.Klas]:
    q = db.query(models.Klas).options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
    if omvang.tipe == OMVANG_KLASSE:
        if not omvang.klas_ids:
            return []
        q = q.filter(models.Klas.Klas_ID.in_(omvang.klas_ids))
    elif omvang.tipe == OMVANG_KAMPUS:
        q = q.join(models.Lokasie, models.Klas.Lokasie_ID == models.Lokasie.Lokasie_ID).filter(
            models.Lokasie.Kampus_ID == omvang.kampus_id
        )
    return q.order_by(models.Klas.Klas_ID).all()


def _klas_sessies(
    db: Session,
    klasse: list[models.Klas],
    rosters: dict[int, set[int]],
    van: date,
    tot: date,
    nou_utc: datetime,
) -> list[dict]:
    """Elke geskeduleerde klasperiode in [van, tot] wat reeds begin het."""
    sessies = []
    for klas in klasse:
        dag = van
        while dag <= tot:
            # Slegs klasse met 'n herkenbare roosterdag; onbekende dae sou
            # andersins elke dag van die tydperk as 'n klasperiode tel.
            if _DAE.get((klas.KLA_Dag or "").strip().casefold()) == dag.weekday():
                try:
                    begin_local, eind_local, begin_utc, eind_utc = _klas_scan_venster(klas, dag)
                except HTTPException:
                    break  # ongeldige rooster-tyd; slaan hierdie klas oor
                if begin_utc <= nou_utc:
                    sessies.append({
                        "klas": klas,
                        "dag": dag,
                        "begin_utc": begin_utc,
                        "eind_utc": eind_utc,
                        "begin": begin_local.strftime("%H:%M"),
                        "eind": eind_local.strftime("%H:%M"),
                        "roster": rosters.get(klas.Klas_ID, set()),
                        "teenwoordig": {},
                    })
            dag += timedelta(days=1)

    gekoppel = [s for s in sessies if s["klas"].Lokasie_ID]
    if not gekoppel:
        return sessies

    lokasie_ids = {s["klas"].Lokasie_ID for s in gekoppel}
    alle_ids = set().union(*(s["roster"] for s in gekoppel))
    if not alle_ids:
        return sessies
    logs = (
        db.query(models.ToegangsLogs)
        .filter(
            models.ToegangsLogs.Lokasie_ID.in_(lokasie_ids),
            models.ToegangsLogs.Gebruiker_ID.in_(alle_ids),
            models.ToegangsLogs.TOE_Metode == "NFC",
            models.ToegangsLogs.TOE_Tydstempel >= min(s["begin_utc"] for s in gekoppel),
            models.ToegangsLogs.TOE_Tydstempel < max(s["eind_utc"] for s in gekoppel),
        )
        .order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID)
        .all()
    )
    per_lokasie: dict[int, list[models.ToegangsLogs]] = defaultdict(list)
    for log in logs:
        per_lokasie[log.Lokasie_ID].append(log)

    for sessie in gekoppel:
        # Dieselfde reël as die lewendige register: die jongste skandering
        # binne die venster bepaal of die student teenwoordig is.
        laaste: dict[int, models.ToegangsLogs] = {}
        for log in per_lokasie.get(sessie["klas"].Lokasie_ID, []):
            if (
                sessie["begin_utc"] <= log.TOE_Tydstempel < sessie["eind_utc"]
                and log.Gebruiker_ID in sessie["roster"]
            ):
                laaste[log.Gebruiker_ID] = log
        sessie["teenwoordig"] = {
            gid: _na_sa(log.TOE_Tydstempel)
            for gid, log in laaste.items()
            if str(log.TOE_Rigting or "").upper() == "IN"
        }
    return sessies


def versamel_verslag(
    db: Session,
    omvang: Omvang,
    van: date,
    tot: date,
    nou: Optional[datetime] = None,
) -> dict:
    nou_utc = nou or datetime.utcnow()
    vandag = _na_sa(nou_utc).date()
    tot_effektief = min(tot, vandag)
    van_utc = _sa_dag_begin_utc(van)
    tot_utc = min(_sa_dag_begin_utc(tot + timedelta(days=1)), nou_utc)

    klasse = _klasse_in_omvang(db, omvang)
    rosters = {k.Klas_ID: _klas_roster_gebruiker_ids(db, k) for k in klasse}

    # --- Wie is in die verslag? ---
    lokasie_ids: Optional[set[int]] = None
    if omvang.tipe == OMVANG_KAMPUS:
        lokasie_ids = {
            l for (l,) in db.query(models.Lokasie.Lokasie_ID)
            .filter(models.Lokasie.Kampus_ID == omvang.kampus_id).all()
        }
    elif omvang.tipe == OMVANG_KLASSE:
        lokasie_ids = {k.Lokasie_ID for k in klasse if k.Lokasie_ID}

    gebruiker_ids: set[int] = set().union(*rosters.values()) if rosters else set()
    if omvang.tipe == OMVANG_ALLES:
        gebruiker_ids |= {g for (g,) in db.query(models.Gebruikers.Gebruiker_ID).all()}
    elif omvang.tipe == OMVANG_KAMPUS and lokasie_ids:
        gebruiker_ids |= {
            g for (g,) in db.query(models.ToegangsLogs.Gebruiker_ID)
            .filter(models.ToegangsLogs.Lokasie_ID.in_(lokasie_ids))
            .distinct().all()
        }

    gebruikers = (
        db.query(models.Gebruikers)
        .filter(models.Gebruikers.Gebruiker_ID.in_(gebruiker_ids))
        .order_by(models.Gebruikers.GEB_Van, models.Gebruikers.GEB_Naam)
        .all()
    ) if gebruiker_ids else []

    persone: dict[int, Persoon] = {}
    for g in gebruikers:
        rol = kies_primere_rol(_rol_namen(g))
        if omvang.tipe == OMVANG_KLASSE and rol != "Student":
            continue
        persone[g.Gebruiker_ID] = Persoon(gebruiker=g, rol=rol, is_student=(rol == "Student"))

    # --- Toegangslogs in die tydperk ---
    log_q = db.query(models.ToegangsLogs).filter(
        models.ToegangsLogs.TOE_Tydstempel >= van_utc,
        models.ToegangsLogs.TOE_Tydstempel < tot_utc,
    )
    if lokasie_ids is not None:
        log_q = log_q.filter(models.ToegangsLogs.Lokasie_ID.in_(lokasie_ids or {-1}))
    if omvang.tipe != OMVANG_ALLES:
        log_q = log_q.filter(models.ToegangsLogs.Gebruiker_ID.in_(set(persone) or {-1}))
    logs = log_q.order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).all()

    lokasies = {l.Lokasie_ID: l for l in db.query(models.Lokasie).all()}

    daagliks: dict[date, dict] = defaultdict(
        lambda: {"studente": set(), "personeel": set(), "in": 0, "uit": 0}
    )
    for log in logs:
        persoon = persone.get(log.Gebruiker_ID)
        if persoon is None:
            continue
        sa = _na_sa(log.TOE_Tydstempel)
        dag = sa.date()
        persoon.skanderings += 1
        rigting = str(log.TOE_Rigting or "").upper()
        if rigting == "IN":
            daagliks[dag]["in"] += 1
            daagliks[dag]["studente" if persoon.is_student else "personeel"].add(log.Gebruiker_ID)
            persoon.dae_in.add(dag)
            if dag not in persoon.aankomste:
                persoon.aankomste[dag] = sa
        else:
            daagliks[dag]["uit"] += 1
            persoon.vertrekke[dag] = sa

    # --- Huidige status: jongste log ooit (binne omvang) ---
    laaste_q = db.query(models.ToegangsLogs).filter(
        models.ToegangsLogs.Gebruiker_ID.in_(set(persone) or {-1}),
        models.ToegangsLogs.TOE_Tydstempel < nou_utc,
    )
    if lokasie_ids is not None:
        laaste_q = laaste_q.filter(models.ToegangsLogs.Lokasie_ID.in_(lokasie_ids or {-1}))
    for log in laaste_q.order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).yield_per(1000):
        persone[log.Gebruiker_ID].laaste_log = log

    # --- Klasbywoning ---
    sessies = _klas_sessies(db, klasse, rosters, van, tot_effektief, nou_utc)
    for sessie in sessies:
        if not sessie["klas"].Lokasie_ID:
            continue
        for gid in sessie["roster"]:
            persoon = persone.get(gid)
            if persoon is None:
                continue
            persoon.sessies_geskeduleer += 1
            if gid in sessie["teenwoordig"]:
                persoon.sessies_bygewoon += 1

    return {
        "omvang": omvang,
        "van": van,
        "tot": tot,
        "tot_effektief": tot_effektief,
        "nou_sa": _na_sa(nou_utc),
        "werksdae": _werksdae(van, tot_effektief),
        "persone": persone,
        "logs": logs,
        "lokasies": lokasies,
        "daagliks": daagliks,
        "sessies": sessies,
    }


# --------------------------------------------------------------------------- #
# Insigte ("wat die data wys")
# --------------------------------------------------------------------------- #

def _insigte(data: dict, stats: dict) -> list[str]:
    insigte: list[str] = []
    omvang = data["omvang"]

    if omvang.tipe != OMVANG_KLASSE and stats["daaglikse_studente"]:
        dae = stats["daaglikse_studente"]
        beste = max(dae, key=lambda d: d[1])
        swakste = min(dae, key=lambda d: d[1])
        insigte.append(
            f"Gemiddelde daaglikse studentebywoning op werksdae was "
            f"{stats['gem_student_bywoning']:.0%}."
        )
        insigte.append(
            f"Hoogste bywoning: {_datum_teks(beste[0])} ({beste[1]} studente). "
            f"Laagste: {_datum_teks(swakste[0])} ({swakste[1]} studente)."
        )
        if len(dae) >= 4:
            helfte = len(dae) // 2
            eerste = sum(v for _, v in dae[:helfte]) / helfte
            tweede = sum(v for _, v in dae[helfte:]) / (len(dae) - helfte)
            if eerste:
                verandering = (tweede - eerste) / eerste
                rigting = "gestyg" if verandering > 0.02 else "gedaal" if verandering < -0.02 else "stabiel gebly"
                insigte.append(
                    f"Bywoning het in die tweede helfte van die tydperk {rigting} "
                    f"({verandering:+.0%} teenoor die eerste helfte)."
                )

    if stats["klas_bywoning"] is not None:
        insigte.append(
            f"Algehele klasbywoning was {stats['klas_bywoning']:.0%} oor "
            f"{stats['sessies_gemeet']} gemete klasperiodes."
        )
        if stats["swakste_module"]:
            m, p = stats["swakste_module"]
            insigte.append(f"Module met die laagste klasbywoning: {m} ({p:.0%}).")
    if stats["sessies_ongekoppel"]:
        insigte.append(
            f"{stats['sessies_ongekoppel']} klasperiodes kon nie gemeet word nie omdat die "
            f"lokaal nie aan 'n NFC-lokasie gekoppel is nie."
        )

    if stats["lae_bywoning"]:
        insigte.append(
            f"{len(stats['lae_bywoning'])} student(e) het bywoning onder {LAE_BYWONING:.0%} "
            f"(sien die 'Studente' blad, rooi gemerk)."
        )
    elif stats["aantal_studente"]:
        insigte.append(f"Geen student het bywoning onder {LAE_BYWONING:.0%} nie.")

    if omvang.tipe != OMVANG_KLASSE:
        insigte.append(
            f"Tans op kampus: {stats['tans_in_studente']} studente en "
            f"{stats['tans_in_personeel']} personeel (volgens hul jongste skandering)."
        )
    if not data["logs"] and not data["sessies"]:
        insigte.append("Geen bywoningsdata is vir hierdie tydperk aangeteken nie.")
    return insigte


def _bereken_statistiek(data: dict) -> dict:
    persone: dict[int, Persoon] = data["persone"]
    werksdae = data["werksdae"]
    studente = [p for p in persone.values() if p.is_student]
    personeel = [p for p in persone.values() if not p.is_student]
    werksdag_stel = set(werksdae)
    gebruik_klas = data["omvang"].tipe == OMVANG_KLASSE

    def bywoning(p: Persoon) -> Optional[float]:
        if gebruik_klas:
            return _verhouding(p.sessies_bygewoon, p.sessies_geskeduleer)
        return _verhouding(len(p.dae_in & werksdag_stel), len(werksdae))

    daaglikse_studente = [(d, len(data["daagliks"][d]["studente"])) for d in werksdae]
    daaglikse_personeel = [(d, len(data["daagliks"][d]["personeel"])) for d in werksdae]
    gem_student = (
        sum(v for _, v in daaglikse_studente) / (len(werksdae) * len(studente))
        if werksdae and studente else 0.0
    )
    gem_personeel = (
        sum(v for _, v in daaglikse_personeel) / (len(werksdae) * len(personeel))
        if werksdae and personeel else 0.0
    )

    gemeet = [s for s in data["sessies"] if s["klas"].Lokasie_ID and s["roster"]]
    totaal_geregistreer = sum(len(s["roster"]) for s in gemeet)
    totaal_teenwoordig = sum(len(s["teenwoordig"]) for s in gemeet)

    per_module: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for s in gemeet:
        kode = s["klas"].module.MOD_Kode if s["klas"].module else "?"
        per_module[kode][0] += len(s["teenwoordig"])
        per_module[kode][1] += len(s["roster"])
    module_pers = {m: t / r for m, (t, r) in per_module.items() if r}
    swakste = min(module_pers.items(), key=lambda kv: kv[1]) if len(module_pers) > 1 else None

    def is_tans_in(p: Persoon) -> bool:
        return p.laaste_log is not None and str(p.laaste_log.TOE_Rigting or "").upper() == "IN"

    lae = [p for p in studente if (b := bywoning(p)) is not None and b < LAE_BYWONING]

    stats = {
        "bywoning": bywoning,
        "aantal_studente": len(studente),
        "aantal_personeel": len(personeel),
        "tans_in_studente": sum(1 for p in studente if is_tans_in(p)),
        "tans_in_personeel": sum(1 for p in personeel if is_tans_in(p)),
        "daaglikse_studente": daaglikse_studente,
        "gem_student_bywoning": gem_student,
        "gem_personeel_bywoning": gem_personeel,
        "klas_bywoning": _verhouding(totaal_teenwoordig, totaal_geregistreer),
        "sessies_gemeet": len(gemeet),
        "sessies_ongekoppel": sum(1 for s in data["sessies"] if not s["klas"].Lokasie_ID),
        "module_pers": module_pers,
        "swakste_module": swakste,
        "lae_bywoning": lae,
        "is_tans_in": is_tans_in,
    }
    stats["insigte"] = _insigte(data, stats)
    return stats


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #

_KOP_VUL = PatternFill("solid", fgColor="1F3A5F")
_KOP_FONT = Font(bold=True, color="FFFFFF")
_TITEL_FONT = Font(bold=True, size=16, color="1F3A5F")
_SUB_FONT = Font(bold=True, size=12, color="1F3A5F")
_ROOI_VUL = PatternFill("solid", fgColor="F8D7DA")
_GROEN_VUL = PatternFill("solid", fgColor="D4EDDA")
_DUN = Side(style="thin", color="D0D7DE")
_RAND = Border(left=_DUN, right=_DUN, top=_DUN, bottom=_DUN)
_DATUM = "yyyy-mm-dd"
_DATUMTYD = "yyyy-mm-dd hh:mm"
_PERSENT = "0%"


def _tabel(ws, begin_ry: int, koppe: list[str], rye: list[list], formate: dict[int, str] | None = None,
           wydtes: list[int] | None = None) -> int:
    """Skryf 'n tabel met 'n gestileerde kopry, filters en vaste kopry. Gee die laaste ry terug."""
    for k, kop in enumerate(koppe, start=1):
        sel = ws.cell(row=begin_ry, column=k, value=kop)
        sel.fill = _KOP_VUL
        sel.font = _KOP_FONT
        sel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sel.border = _RAND
    for r, ry in enumerate(rye, start=begin_ry + 1):
        for k, waarde in enumerate(ry, start=1):
            sel = ws.cell(row=r, column=k, value=waarde)
            sel.border = _RAND
            if formate and k in formate:
                sel.number_format = formate[k]
    laaste = begin_ry + len(rye)
    ws.auto_filter.ref = f"A{begin_ry}:{get_column_letter(len(koppe))}{max(laaste, begin_ry)}"
    ws.freeze_panes = ws.cell(row=begin_ry + 1, column=1)
    for k, kop in enumerate(koppe, start=1):
        wydte = (wydtes[k - 1] if wydtes and k - 1 < len(wydtes) else None) or max(12, len(kop) + 4)
        ws.column_dimensions[get_column_letter(k)].width = wydte
    return laaste


def _merk_persentasie(ws, kolom: int, eerste: int, laaste: int):
    if laaste < eerste:
        return
    bereik = f"{get_column_letter(kolom)}{eerste}:{get_column_letter(kolom)}{laaste}"
    ws.conditional_formatting.add(bereik, CellIsRule(operator="lessThan", formula=[str(LAE_BYWONING)], fill=_ROOI_VUL))
    ws.conditional_formatting.add(bereik, CellIsRule(operator="greaterThanOrEqual", formula=["0.9"], fill=_GROEN_VUL))


def _status_teks(p: Persoon, is_tans_in) -> str:
    if p.laaste_log is None:
        return "Nog nooit gescan nie"
    return "Op kampus (IN)" if is_tans_in(p) else "Van kampus af (UIT)"


def bou_werkboek(data: dict, gegenereer_deur: str, rol: str) -> bytes:
    stats = _bereken_statistiek(data)
    omvang: Omvang = data["omvang"]
    persone: dict[int, Persoon] = data["persone"]
    lokasies = data["lokasies"]
    werksdae = data["werksdae"]
    klas_modus = omvang.tipe == OMVANG_KLASSE
    bywoning = stats["bywoning"]

    wb = Workbook()

    # ---------------- Opsomming ----------------
    ws = wb.active
    ws.title = "Opsomming"
    ws["A1"] = "MOON Bywoningsverslag"
    ws["A1"].font = _TITEL_FONT
    meta = [
        ("Omvang", omvang.beskrywing),
        ("Tydperk", f"{data['van']:%Y-%m-%d} tot {data['tot']:%Y-%m-%d}"),
        ("Werksdae in tydperk", len(werksdae)),
        ("Gegenereer op", data["nou_sa"]),
        ("Gegenereer deur", f"{gegenereer_deur} ({rol})"),
    ]
    for i, (k, v) in enumerate(meta, start=3):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True)
        sel = ws.cell(row=i, column=2, value=v)
        if isinstance(v, datetime):
            sel.number_format = _DATUMTYD
        sel.alignment = Alignment(horizontal="left")

    ry = 3 + len(meta) + 1
    ws.cell(row=ry, column=1, value="Kernsyfers").font = _SUB_FONT
    kern: list[tuple[str, object, Optional[str]]] = [("Studente in verslag", stats["aantal_studente"], None)]
    if not klas_modus:
        kern += [
            ("Personeel in verslag", stats["aantal_personeel"], None),
            ("Studente tans op kampus", stats["tans_in_studente"], None),
            ("Personeel tans op kampus", stats["tans_in_personeel"], None),
            ("Gem. daaglikse studentebywoning", stats["gem_student_bywoning"], _PERSENT),
            ("Gem. daaglikse personeelbywoning", stats["gem_personeel_bywoning"], _PERSENT),
            ("Toegangskanderings in tydperk", len(data["logs"]), None),
        ]
    kern += [
        ("Klasperiodes gemeet", stats["sessies_gemeet"], None),
        ("Algehele klasbywoning", stats["klas_bywoning"], _PERSENT),
        (f"Studente onder {LAE_BYWONING:.0%} bywoning", len(stats["lae_bywoning"]), None),
    ]
    for i, (k, v, fmt) in enumerate(kern, start=ry + 1):
        ws.cell(row=i, column=1, value=k)
        sel = ws.cell(row=i, column=2, value=v if v is not None else "n.v.t.")
        sel.font = Font(bold=True)
        sel.alignment = Alignment(horizontal="left")
        if fmt and v is not None:
            sel.number_format = fmt
    ry += len(kern) + 2

    ws.cell(row=ry, column=1, value="Wat die data wys").font = _SUB_FONT
    for i, insig in enumerate(stats["insigte"], start=ry + 1):
        sel = ws.cell(row=i, column=1, value=f"• {insig}")
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
        sel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 30
    ry += len(stats["insigte"]) + 2

    ws.cell(row=ry, column=1, value="Blaaie in hierdie verslag").font = _SUB_FONT
    blaaie = [
        ("Huidige Status", "Elke persoon se jongste skandering en of hulle nou in of uit is."),
        ("Studente", "Bywoningstatistiek per student; rooi = onder drempel, groen = 90%+."),
    ]
    if not klas_modus:
        blaaie += [
            ("Personeel", "Bywoning, gemiddelde aankoms- en vertrektye per personeellid."),
            ("Daaglikse Bywoning", "Unieke persone per werksdag, met 'n tendensgrafiek."),
        ]
    blaaie += [
        ("Klasbywoning", "Elke klasperiode: geregistreer, teenwoordig, afwesig en %."),
        ("Klasregister", "Teenwoordig/afwesig per student per klasperiode."),
    ]
    if not klas_modus:
        blaaie.append(("Toegangslogs", "Volledige skanderingsgeskiedenis in die tydperk."))
    for i, (naam, uitleg) in enumerate(blaaie, start=ry + 1):
        ws.cell(row=i, column=1, value=naam).font = Font(bold=True)
        ws.cell(row=i, column=2, value=uitleg)
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 70

    # ---------------- Huidige Status ----------------
    ws = wb.create_sheet("Huidige Status")
    rye = []
    for p in persone.values():
        log = p.laaste_log
        lok = lokasies.get(log.Lokasie_ID) if log else None
        rye.append([
            p.naam, _nommer(p.gebruiker), "Student" if p.is_student else p.rol,
            _status_teks(p, stats["is_tans_in"]),
            _na_sa(log.TOE_Tydstempel) if log else None,
            lok.LOK_Naam if lok else None,
            lok.kampus.KAM_Naam if lok and lok.kampus else None,
            log.TOE_Metode if log else None,
        ])
    laaste = _tabel(
        ws, 1,
        ["Naam", "Nommer", "Rol", "Huidige status", "Laaste skandering", "Lokasie", "Kampus", "Metode"],
        rye, {5: _DATUMTYD}, [28, 14, 16, 22, 20, 24, 20, 12],
    )
    if laaste > 1:
        bereik = f"D2:D{laaste}"
        ws.conditional_formatting.add(bereik, CellIsRule(operator="equal", formula=['"Op kampus (IN)"'], fill=_GROEN_VUL))

    # ---------------- Studente ----------------
    ws = wb.create_sheet("Studente")
    werksdag_stel = set(werksdae)
    rye = []
    for p in persone.values():
        if not p.is_student:
            continue
        dae = len(p.dae_in & werksdag_stel)
        ry_data = [p.naam, _nommer(p.gebruiker)]
        if not klas_modus:
            ry_data += [dae, len(werksdae), _verhouding(dae, len(werksdae)), _gem_tyd(list(p.aankomste.values()))]
        ry_data += [
            p.sessies_bygewoon, p.sessies_geskeduleer,
            _verhouding(p.sessies_bygewoon, p.sessies_geskeduleer),
            p.skanderings,
            _na_sa(p.laaste_log.TOE_Tydstempel) if p.laaste_log else None,
            "Lae bywoning" if (b := bywoning(p)) is not None and b < LAE_BYWONING else "",
        ]
        rye.append(ry_data)
    koppe = ["Naam", "Studentenommer"]
    if not klas_modus:
        koppe += ["Dae op kampus", "Werksdae", "Kampusbywoning %", "Gem. aankoms"]
    koppe += ["Klasse bygewoon", "Klasse geskeduleer", "Klasbywoning %", "Skanderings", "Laaste skandering", "Let op"]
    pers_kolomme = [koppe.index("Klasbywoning %") + 1]
    if not klas_modus:
        pers_kolomme.append(koppe.index("Kampusbywoning %") + 1)
    formate = {k: _PERSENT for k in pers_kolomme}
    formate[koppe.index("Laaste skandering") + 1] = _DATUMTYD
    laaste = _tabel(ws, 1, koppe, rye, formate, [28, 16])
    for k in pers_kolomme:
        _merk_persentasie(ws, k, 2, laaste)

    if not klas_modus:
        # ---------------- Personeel ----------------
        ws = wb.create_sheet("Personeel")
        rye = []
        for p in persone.values():
            if p.is_student:
                continue
            dae = len(p.dae_in & werksdag_stel)
            rye.append([
                p.naam, _nommer(p.gebruiker), p.rol,
                p.gebruiker.personeel.PER_Departement if p.gebruiker.personeel else None,
                dae, len(werksdae), _verhouding(dae, len(werksdae)),
                _gem_tyd(list(p.aankomste.values())), _gem_tyd(list(p.vertrekke.values())),
                p.skanderings,
                _na_sa(p.laaste_log.TOE_Tydstempel) if p.laaste_log else None,
                _status_teks(p, stats["is_tans_in"]),
            ])
        laaste = _tabel(
            ws, 1,
            ["Naam", "Nommer", "Rol", "Departement", "Dae op kampus", "Werksdae", "Bywoning %",
             "Gem. aankoms", "Gem. vertrek", "Skanderings", "Laaste skandering", "Huidige status"],
            rye, {7: _PERSENT, 11: _DATUMTYD}, [28, 14, 16, 20],
        )
        _merk_persentasie(ws, 7, 2, laaste)

        # ---------------- Daaglikse Bywoning ----------------
        ws = wb.create_sheet("Daaglikse Bywoning")
        rye = []
        dag = data["van"]
        while dag <= data["tot_effektief"]:
            d = data["daagliks"].get(dag, {"studente": set(), "personeel": set(), "in": 0, "uit": 0})
            rye.append([
                dag, _dag_naam(dag), "Ja" if dag.weekday() < 5 else "Naweek",
                len(d["studente"]), _verhouding(len(d["studente"]), stats["aantal_studente"]),
                len(d["personeel"]), _verhouding(len(d["personeel"]), stats["aantal_personeel"]),
                d["in"], d["uit"],
            ])
            dag += timedelta(days=1)
        laaste = _tabel(
            ws, 1,
            ["Datum", "Dag", "Werksdag", "Studente teenwoordig", "Studente %",
             "Personeel teenwoordig", "Personeel %", "IN skanderings", "UIT skanderings"],
            rye, {1: _DATUM, 5: _PERSENT, 7: _PERSENT}, [12, 12, 10],
        )
        if laaste > 2:
            grafiek = LineChart()
            grafiek.title = "Daaglikse bywoning"
            grafiek.y_axis.title = "Persone"
            grafiek.x_axis.title = "Datum"
            grafiek.x_axis.number_format = "dd MMM"
            grafiek.height, grafiek.width = 9, 22
            grafiek.add_data(Reference(ws, min_col=4, min_row=1, max_row=laaste), titles_from_data=True)
            grafiek.add_data(Reference(ws, min_col=6, min_row=1, max_row=laaste), titles_from_data=True)
            grafiek.set_categories(Reference(ws, min_col=1, min_row=2, max_row=laaste))
            ws.add_chart(grafiek, "K2")

    # ---------------- Klasbywoning ----------------
    ws = wb.create_sheet("Klasbywoning")
    rye = []
    for s in sorted(data["sessies"], key=lambda s: (s["dag"], s["begin"])):
        klas = s["klas"]
        gekoppel = bool(klas.Lokasie_ID)
        geregistreer = len(s["roster"])
        teenwoordig = len(s["teenwoordig"]) if gekoppel else None
        rye.append([
            s["dag"], _dag_naam(s["dag"]), f"{s['begin']}-{s['eind']}",
            klas.module.MOD_Kode if klas.module else None,
            klas.module.MOD_Naam if klas.module else None,
            klas.lokasie.LOK_Naam if klas.lokasie else klas.KLA_Lokaal,
            geregistreer, teenwoordig,
            (geregistreer - teenwoordig) if gekoppel else None,
            _verhouding(teenwoordig, geregistreer) if gekoppel else None,
            "" if gekoppel else "Lokaal nie aan NFC gekoppel nie",
        ])
    laaste = _tabel(
        ws, 1,
        ["Datum", "Dag", "Tyd", "Module", "Modulenaam", "Lokaal", "Geregistreer",
         "Teenwoordig", "Afwesig", "Bywoning %", "Nota"],
        rye, {1: _DATUM, 10: _PERSENT}, [12, 12, 13, 14, 28, 22, 13, 13, 11, 12, 32],
    )
    _merk_persentasie(ws, 10, 2, laaste)
    if stats["module_pers"]:
        begin = laaste + 3
        ws.cell(row=begin - 1, column=1, value="Bywoning per module").font = _SUB_FONT
        mod_rye = sorted(stats["module_pers"].items())
        for i, (m, p) in enumerate(mod_rye, start=begin + 1):
            ws.cell(row=i, column=1, value=m)
            ws.cell(row=i, column=2, value=p).number_format = _PERSENT
        ws.cell(row=begin, column=1, value="Module").font = Font(bold=True)
        ws.cell(row=begin, column=2, value="Bywoning %").font = Font(bold=True)
        grafiek = BarChart()
        grafiek.title = "Klasbywoning per module"
        grafiek.y_axis.number_format = "0%"
        grafiek.y_axis.scaling.min = 0
        grafiek.y_axis.scaling.max = 1
        grafiek.legend = None
        grafiek.height, grafiek.width = 8, 18
        grafiek.add_data(Reference(ws, min_col=2, min_row=begin, max_row=begin + len(mod_rye)), titles_from_data=True)
        grafiek.set_categories(Reference(ws, min_col=1, min_row=begin + 1, max_row=begin + len(mod_rye)))
        ws.add_chart(grafiek, f"D{begin}")

    # ---------------- Klasregister ----------------
    ws = wb.create_sheet("Klasregister")
    rye = []
    for s in sorted(data["sessies"], key=lambda s: (s["dag"], s["begin"])):
        klas = s["klas"]
        if not klas.Lokasie_ID:
            continue
        studente = sorted(
            (persone[g] for g in s["roster"] if g in persone),
            key=lambda p: (p.gebruiker.GEB_Van, p.gebruiker.GEB_Naam),
        )
        for p in studente:
            tyd = s["teenwoordig"].get(p.gebruiker.Gebruiker_ID)
            rye.append([
                s["dag"], f"{s['begin']}-{s['eind']}",
                klas.module.MOD_Kode if klas.module else None,
                klas.lokasie.LOK_Naam if klas.lokasie else klas.KLA_Lokaal,
                p.naam, _nommer(p.gebruiker),
                "Teenwoordig" if tyd else "Afwesig", tyd,
            ])
    laaste = _tabel(
        ws, 1,
        ["Datum", "Tyd", "Module", "Lokaal", "Student", "Studentenommer", "Status", "Ingescan"],
        rye, {1: _DATUM, 8: _DATUMTYD}, [12, 13, 14, 22, 28, 16, 14, 18],
    )
    if laaste > 1:
        ws.conditional_formatting.add(f"G2:G{laaste}", CellIsRule(operator="equal", formula=['"Afwesig"'], fill=_ROOI_VUL))

    # ---------------- Toegangslogs ----------------
    if not klas_modus:
        ws = wb.create_sheet("Toegangslogs")
        rye = []
        for log in data["logs"]:
            p = persone.get(log.Gebruiker_ID)
            if p is None:
                continue
            lok = lokasies.get(log.Lokasie_ID)
            rye.append([
                _na_sa(log.TOE_Tydstempel), p.naam, _nommer(p.gebruiker),
                "Student" if p.is_student else p.rol,
                lok.LOK_Naam if lok else None,
                lok.LOK_Tipe if lok else None,
                lok.kampus.KAM_Naam if lok and lok.kampus else None,
                log.TOE_Rigting, log.TOE_Metode,
                "Ja" if log.TOE_Auto_Uitgecheck else "",
            ])
        _tabel(
            ws, 1,
            ["Tyd", "Naam", "Nommer", "Rol", "Lokasie", "Lokasietipe", "Kampus", "Rigting", "Metode", "Outo-uitgeteken"],
            rye, {1: _DATUMTYD}, [18, 28, 14, 16, 24, 14, 20, 10, 12, 16],
        )

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def genereer_verslag(
    db: Session,
    gebruiker: models.Gebruikers,
    rolle: list[str],
    van: date,
    tot: date,
    kampus_id: Optional[int] = None,
    nou: Optional[datetime] = None,
) -> tuple[bytes, str]:
    """Gee (xlsx-bytes, lêernaam) terug."""
    if tot < van:
        raise HTTPException(status_code=400, detail="'Tot'-datum moet na die 'van'-datum wees")
    if (tot - van).days + 1 > MAKS_DAE:
        raise HTTPException(status_code=400, detail=f"Tydperk mag hoogstens {MAKS_DAE} dae wees")

    omvang = bepaal_omvang(db, gebruiker, rolle, kampus_id)
    data = versamel_verslag(db, omvang, van, tot, nou)
    rol = kies_primere_rol(rolle)
    inhoud = bou_werkboek(data, f"{gebruiker.GEB_Naam} {gebruiker.GEB_Van}".strip(), rol)
    lêernaam = f"moon_bywoning_{van:%Y%m%d}_{tot:%Y%m%d}.xlsx"
    return inhoud, lêernaam
