"""Bywoningsverslag — versamel die data en bou 'n formaat-neutrale oorsig.

Die oorsig word op twee plekke gebruik:
- Die webwerf se Verslag-blad wys dit as KPI-teëls, grafieke en lyste.
- services/verslag_formate.py skryf dit uit as Excel, PDF, Word of teks.

Die verslag word per rol afgebaken:
- Administrateur: alle kampusse (opsioneel net een kampus).
- Kampus_Opsigter: net die kampus waaraan die opsigter gekoppel is.
  Albei kry die afdelings Kampus, Koshuis en Events.
- Personeel: net die studente in die personeellid se eie klasse
  (afdeling Klas; geen kampus-hek geskiedenis nie).

Alle tye in die databasis is UTC-naive; die verslag wys SA-tyd.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
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

# Kolom-/syferformate wat elke uitvoerformaat (en die webwerf) verstaan.
TEKS = "teks"
GETAL = "getal"
PERSENT = "persent"  # 'n verhouding 0..1
DATUM = "datum"
DATUMTYD = "datumtyd"

STATUS_IN = "Op kampus (IN)"
STATUS_UIT = "Van kampus af (UIT)"
STATUS_NOOIT = "Nog nooit gescan nie"


# --------------------------------------------------------------------------- #
# Hulpfunksies
# --------------------------------------------------------------------------- #

def _na_sa(dt_utc: datetime) -> datetime:
    """UTC-naive -> SA-tyd (naive, sodat Excel dit as 'n gewone datum/tyd wys)."""
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(_SA_TZ).replace(tzinfo=None)


def _iso_na_sa(waarde: Optional[str]) -> Optional[datetime]:
    """'2026-10-05T10:00:00Z' (UTC) -> SA-tyd (naive)."""
    if not waarde:
        return None
    dt = datetime.fromisoformat(waarde.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SA_TZ).replace(tzinfo=None)


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


def _alle_dae(van: date, tot: date) -> list[date]:
    dae = []
    dag = van
    while dag <= tot:
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


def _volle_naam(gebruiker: models.Gebruikers) -> str:
    return f"{gebruiker.GEB_Naam} {gebruiker.GEB_Van}".strip()


def _is_in(log: Optional[models.ToegangsLogs]) -> bool:
    return log is not None and str(log.TOE_Rigting or "").upper() == "IN"


def _koshuis_lokasie_ids(db: Session) -> set[int]:
    """Lokasies van koshuise (LOK_Tipe 'Koshuis'); hul skanderings is nie kampus-bywoning nie."""
    return {
        l for (l,) in db.query(models.Lokasie.Lokasie_ID)
        .filter(func.lower(models.Lokasie.LOK_Tipe) == "koshuis").all()
    }


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
        return _volle_naam(self.gebruiker)


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
# Data-insameling: kampus + klasse
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
    """Kampus-hek bywoning (Admin/Opsigter) of klasbywoning (Personeel)."""
    nou_utc = nou or datetime.utcnow()
    vandag = _na_sa(nou_utc).date()
    tot_effektief = min(tot, vandag)
    van_utc = _sa_dag_begin_utc(van)
    tot_utc = min(_sa_dag_begin_utc(tot + timedelta(days=1)), nou_utc)
    klas_modus = omvang.tipe == OMVANG_KLASSE

    klasse = _klasse_in_omvang(db, omvang)
    rosters = {k.Klas_ID: _klas_roster_gebruiker_ids(db, k) for k in klasse}

    # Koshuis-skanderings is nie kampus-bywoning nie; hulle het hul eie afdeling.
    koshuis_lok = set() if klas_modus else _koshuis_lokasie_ids(db)

    # --- Wie is in die verslag? ---
    lokasie_ids: Optional[set[int]] = None
    if omvang.tipe == OMVANG_KAMPUS:
        lokasie_ids = {
            l for (l,) in db.query(models.Lokasie.Lokasie_ID)
            .filter(models.Lokasie.Kampus_ID == omvang.kampus_id).all()
        } - koshuis_lok
    elif klas_modus:
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
        if klas_modus and rol != "Student":
            continue
        persone[g.Gebruiker_ID] = Persoon(gebruiker=g, rol=rol, is_student=(rol == "Student"))

    def _beperk(q):
        if lokasie_ids is not None:
            q = q.filter(models.ToegangsLogs.Lokasie_ID.in_(lokasie_ids or {-1}))
        elif koshuis_lok:
            q = q.filter(models.ToegangsLogs.Lokasie_ID.notin_(koshuis_lok))
        return q

    logs: list[models.ToegangsLogs] = []
    daagliks: dict[date, dict] = defaultdict(
        lambda: {"studente": set(), "personeel": set(), "in": 0, "uit": 0}
    )
    if not klas_modus:
        # --- Toegangslogs in die tydperk ---
        log_q = _beperk(db.query(models.ToegangsLogs).filter(
            models.ToegangsLogs.TOE_Tydstempel >= van_utc,
            models.ToegangsLogs.TOE_Tydstempel < tot_utc,
        ))
        if omvang.tipe != OMVANG_ALLES:
            log_q = log_q.filter(models.ToegangsLogs.Gebruiker_ID.in_(set(persone) or {-1}))
        logs = log_q.order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).all()

        for log in logs:
            persoon = persone.get(log.Gebruiker_ID)
            if persoon is None:
                continue
            sa = _na_sa(log.TOE_Tydstempel)
            dag = sa.date()
            persoon.skanderings += 1
            if _is_in(log):
                daagliks[dag]["in"] += 1
                daagliks[dag]["studente" if persoon.is_student else "personeel"].add(log.Gebruiker_ID)
                persoon.dae_in.add(dag)
                if dag not in persoon.aankomste:
                    persoon.aankomste[dag] = sa
            else:
                daagliks[dag]["uit"] += 1
                persoon.vertrekke[dag] = sa

        # --- Huidige status: jongste log ooit (binne omvang) ---
        laaste_q = _beperk(db.query(models.ToegangsLogs).filter(
            models.ToegangsLogs.Gebruiker_ID.in_(set(persone) or {-1}),
            models.ToegangsLogs.TOE_Tydstempel < nou_utc,
        ))
        for log in laaste_q.order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).yield_per(1000):
            persone[log.Gebruiker_ID].laaste_log = log

    # --- Klasbywoning (net vir Personeel se Klas-afdeling) ---
    sessies = _klas_sessies(db, klasse, rosters, van, tot_effektief, nou_utc) if klas_modus else []
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
        "nou_utc": nou_utc,
        "nou_sa": _na_sa(nou_utc),
        "werksdae": _werksdae(van, tot_effektief),
        "persone": persone,
        "logs": logs,
        "lokasies": {l.Lokasie_ID: l for l in db.query(models.Lokasie).all()},
        "daagliks": daagliks,
        "klasse": klasse,
        "sessies": sessies,
    }


# --------------------------------------------------------------------------- #
# Boublokke van 'n afdeling
# --------------------------------------------------------------------------- #

def _syfer(etiket: str, waarde, formaat: str = GETAL) -> dict:
    return {"etiket": etiket, "waarde": waarde, "formaat": formaat}


def _tabel(sleutel: str, titel: str, kolomme: list[tuple[str, str]], rye: list[list],
           maks_rye: Optional[int] = None) -> dict:
    return {
        "sleutel": sleutel,
        "titel": titel,
        "kolomme": [{"naam": n, "formaat": f} for n, f in kolomme],
        "rye": rye if maks_rye is None else rye[:maks_rye],
        "totaal": len(rye),
    }


def _sirkel(titel: str, segmente: list[tuple[str, int]]) -> dict:
    return {"tipe": "sirkel", "titel": titel,
            "segmente": [{"etiket": e, "waarde": w} for e, w in segmente]}


def _balk(titel: str, items: list[tuple[str, float]], formaat: str = GETAL) -> dict:
    return {"tipe": "balk", "titel": titel, "formaat": formaat,
            "items": [{"etiket": e, "waarde": w} for e, w in items]}


def _lyn(titel: str, etikette: list[date], reekse: list[tuple[str, list]], formaat: str = GETAL) -> dict:
    return {"tipe": "lyn", "titel": titel, "formaat": formaat, "etikette": etikette,
            "reekse": [{"etiket": e, "waardes": w} for e, w in reekse]}


def _tendens_insig(dae: list[tuple[date, int]], wat: str) -> Optional[str]:
    if len(dae) < 4:
        return None
    helfte = len(dae) // 2
    eerste = sum(v for _, v in dae[:helfte]) / helfte
    tweede = sum(v for _, v in dae[helfte:]) / (len(dae) - helfte)
    if not eerste:
        return None
    verandering = (tweede - eerste) / eerste
    rigting = "gestyg" if verandering > 0.02 else "gedaal" if verandering < -0.02 else "stabiel gebly"
    return (f"{wat} het in die tweede helfte van die tydperk {rigting} "
            f"({verandering:+.0%} teenoor die eerste helfte).")


# --------------------------------------------------------------------------- #
# Afdeling: Kampus
# --------------------------------------------------------------------------- #

def _afdeling_kampus(data: dict, maks_rye: Optional[int]) -> dict:
    persone: dict[int, Persoon] = data["persone"]
    werksdae = data["werksdae"]
    werksdag_stel = set(werksdae)
    lokasies = data["lokasies"]
    studente = [p for p in persone.values() if p.is_student]
    personeel = [p for p in persone.values() if not p.is_student]

    def bywoning(p: Persoon) -> Optional[float]:
        return _verhouding(len(p.dae_in & werksdag_stel), len(werksdae))

    def status(p: Persoon) -> str:
        if p.laaste_log is None:
            return STATUS_NOOIT
        return STATUS_IN if _is_in(p.laaste_log) else STATUS_UIT

    tans_in_stu = sum(1 for p in studente if _is_in(p.laaste_log))
    tans_in_per = sum(1 for p in personeel if _is_in(p.laaste_log))
    status_tel = defaultdict(int)
    for p in persone.values():
        status_tel[status(p)] += 1

    daaglikse_stu = [(d, len(data["daagliks"][d]["studente"])) for d in werksdae]
    daaglikse_per = [(d, len(data["daagliks"][d]["personeel"])) for d in werksdae]
    gem_stu = (sum(v for _, v in daaglikse_stu) / (len(werksdae) * len(studente))
               if werksdae and studente else None)
    gem_per = (sum(v for _, v in daaglikse_per) / (len(werksdae) * len(personeel))
               if werksdae and personeel else None)
    lae = [p for p in studente if (b := bywoning(p)) is not None and b < LAE_BYWONING]

    kernsyfers = [
        _syfer("Studente in verslag", len(studente)),
        _syfer("Personeel in verslag", len(personeel)),
        _syfer("Studente tans op kampus", tans_in_stu),
        _syfer("Personeel tans op kampus", tans_in_per),
        _syfer("Gem. daaglikse studentebywoning", gem_stu, PERSENT),
        _syfer("Gem. daaglikse personeelbywoning", gem_per, PERSENT),
        _syfer("Toegangskanderings in tydperk", len(data["logs"])),
        _syfer(f"Studente onder {LAE_BYWONING:.0%} bywoning", len(lae)),
    ]

    insigte: list[str] = []
    if daaglikse_stu and gem_stu is not None:
        beste = max(daaglikse_stu, key=lambda d: d[1])
        swakste = min(daaglikse_stu, key=lambda d: d[1])
        insigte.append(f"Gemiddelde daaglikse studentebywoning op werksdae was {gem_stu:.0%}.")
        insigte.append(
            f"Hoogste bywoning: {_datum_teks(beste[0])} ({beste[1]} studente). "
            f"Laagste: {_datum_teks(swakste[0])} ({swakste[1]} studente)."
        )
        if (t := _tendens_insig(daaglikse_stu, "Studentebywoning")):
            insigte.append(t)
    if lae:
        insigte.append(f"{len(lae)} student(e) het kampusbywoning onder {LAE_BYWONING:.0%}.")
    elif studente:
        insigte.append(f"Geen student het kampusbywoning onder {LAE_BYWONING:.0%} nie.")
    insigte.append(
        f"Tans op kampus: {tans_in_stu} studente en {tans_in_per} personeel "
        f"(volgens hul jongste skandering)."
    )
    if not data["logs"]:
        insigte.append("Geen kampusskanderings is vir hierdie tydperk aangeteken nie.")

    # --- Grafieke ---
    alle_dae = _alle_dae(data["van"], data["tot_effektief"])
    leeg = {"studente": set(), "personeel": set(), "in": 0, "uit": 0}
    per_plek: dict[str, int] = defaultdict(int)
    for log in data["logs"]:
        if log.Gebruiker_ID not in persone:
            continue
        lok = lokasies.get(log.Lokasie_ID)
        if data["omvang"].tipe == OMVANG_ALLES:
            sleutel = lok.kampus.KAM_Naam if lok and lok.kampus else "Onbekend"
        else:
            sleutel = lok.LOK_Naam if lok else "Onbekend"
        per_plek[sleutel] += 1
    plek_titel = ("Skanderings per kampus" if data["omvang"].tipe == OMVANG_ALLES
                  else "Skanderings per lokasie")

    grafieke = [
        _sirkel("Huidige status", [
            ("Op kampus", status_tel[STATUS_IN]),
            ("Van kampus af", status_tel[STATUS_UIT]),
            ("Nog nooit gescan", status_tel[STATUS_NOOIT]),
        ]),
        _sirkel("Samestelling", [("Studente", len(studente)), ("Personeel", len(personeel))]),
        _lyn("Daaglikse bywoning (unieke persone)", alle_dae, [
            ("Studente", [len(data["daagliks"].get(d, leeg)["studente"]) for d in alle_dae]),
            ("Personeel", [len(data["daagliks"].get(d, leeg)["personeel"]) for d in alle_dae]),
        ]),
        _balk(plek_titel, sorted(per_plek.items(), key=lambda kv: -kv[1])[:10]),
    ]

    # --- Tabelle ---
    persoon_rye = []
    for p in sorted(persone.values(), key=lambda p: (not p.is_student, p.gebruiker.GEB_Van, p.gebruiker.GEB_Naam)):
        dae = len(p.dae_in & werksdag_stel)
        laaste_outo = bool(
            p.laaste_log is not None
            and getattr(p.laaste_log, "TOE_Auto_Uitgecheck", False)
        )
        persoon_rye.append([
            p.naam, _nommer(p.gebruiker), "Student" if p.is_student else p.rol,
            dae, len(werksdae), bywoning(p),
            _gem_tyd(list(p.aankomste.values())), _gem_tyd(list(p.vertrekke.values())),
            p.skanderings,
            _na_sa(p.laaste_log.TOE_Tydstempel) if p.laaste_log else None,
            status(p),
            "⚠ Outo-uitcheck" if laaste_outo else "",
        ])

    dag_rye = []
    for d in alle_dae:
        dd = data["daagliks"].get(d, leeg)
        dag_rye.append([
            d, _dag_naam(d), "Ja" if d.weekday() < 5 else "Naweek",
            len(dd["studente"]), _verhouding(len(dd["studente"]), len(studente)),
            len(dd["personeel"]), _verhouding(len(dd["personeel"]), len(personeel)),
            dd["in"], dd["uit"],
        ])

    log_rye = []
    for log in reversed(data["logs"]):  # nuutste eerste
        p = persone.get(log.Gebruiker_ID)
        if p is None:
            continue
        lok = lokasies.get(log.Lokasie_ID)
        log_rye.append([
            _na_sa(log.TOE_Tydstempel), p.naam, _nommer(p.gebruiker),
            "Student" if p.is_student else p.rol,
            lok.LOK_Naam if lok else None,
            lok.kampus.KAM_Naam if lok and lok.kampus else None,
            log.TOE_Rigting, log.TOE_Metode,
            "⚠ Outo-uitcheck" if getattr(log, "TOE_Auto_Uitgecheck", False) else "",
        ])

    tabelle = [
        _tabel("persone", "Persone", [
            ("Naam", TEKS), ("Nommer", TEKS), ("Rol", TEKS), ("Dae op kampus", GETAL),
            ("Werksdae", GETAL), ("Bywoning %", PERSENT), ("Gem. aankoms", TEKS),
            ("Gem. vertrek", TEKS), ("Skanderings", GETAL), ("Laaste skandering", DATUMTYD),
            ("Huidige status", TEKS), ("Waarskuwing", TEKS),
        ], persoon_rye, maks_rye),
        _tabel("daagliks", "Daaglikse bywoning", [
            ("Datum", DATUM), ("Dag", TEKS), ("Werksdag", TEKS), ("Studente teenwoordig", GETAL),
            ("Studente %", PERSENT), ("Personeel teenwoordig", GETAL), ("Personeel %", PERSENT),
            ("IN skanderings", GETAL), ("UIT skanderings", GETAL),
        ], dag_rye, maks_rye),
        _tabel("toegangslogs", "Toegangslogs", [
            ("Tyd", DATUMTYD), ("Naam", TEKS), ("Nommer", TEKS), ("Rol", TEKS),
            ("Lokasie", TEKS), ("Kampus", TEKS), ("Rigting", TEKS), ("Metode", TEKS),
            ("Waarskuwing", TEKS),
        ], log_rye, maks_rye),
    ]

    return {
        "sleutel": "kampus",
        "titel": "Kampus",
        "beskrywing": "Kampus-hek bywoning van studente en personeel.",
        "kernsyfers": kernsyfers,
        "insigte": insigte,
        "grafieke": grafieke,
        "tabelle": tabelle,
    }


# --------------------------------------------------------------------------- #
# Afdeling: Koshuis
# --------------------------------------------------------------------------- #

KOS_IN = "Ingeteken"
KOS_UIT = "Uitgeteken"


def _afdeling_koshuis(db: Session, omvang: Omvang, van: date, tot_effektief: date,
                      nou_utc: datetime, maks_rye: Optional[int]) -> dict:
    van_utc = _sa_dag_begin_utc(van)
    tot_utc = min(_sa_dag_begin_utc(tot_effektief + timedelta(days=1)), nou_utc)

    q = db.query(models.Koshuis)
    if omvang.tipe == OMVANG_KAMPUS:
        q = q.filter(models.Koshuis.Kampus_ID == omvang.kampus_id)
    koshuise = q.order_by(models.Koshuis.KOS_Naam).all()
    koshuis_ids = {k.Koshuis_ID for k in koshuise}

    inwoners = (
        db.query(models.Student)
        .options(joinedload(models.Student.gebruiker))
        .filter(models.Student.Koshuis_ID.in_(koshuis_ids or {-1}))
        .all()
    )
    inwoner_ids = {s.Gebruiker_ID for s in inwoners}

    # Elke koshuis het 'n eie Lokasie (LOK_Tipe 'Koshuis', dieselfde naam en kampus).
    lok_q = db.query(models.Lokasie).filter(func.lower(models.Lokasie.LOK_Tipe) == "koshuis")
    if omvang.tipe == OMVANG_KAMPUS:
        lok_q = lok_q.filter(models.Lokasie.Kampus_ID == omvang.kampus_id)
    koshuis_lok_ids = {l.Lokasie_ID for l in lok_q.all()}

    def _logs(q):
        return q.filter(
            models.ToegangsLogs.Gebruiker_ID.in_(inwoner_ids or {-1}),
            models.ToegangsLogs.Lokasie_ID.in_(koshuis_lok_ids or {-1}),
        )

    periode_logs = _logs(db.query(models.ToegangsLogs)).filter(
        models.ToegangsLogs.TOE_Tydstempel >= van_utc,
        models.ToegangsLogs.TOE_Tydstempel < tot_utc,
    ).order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).all()

    laaste: dict[int, models.ToegangsLogs] = {}
    for log in _logs(db.query(models.ToegangsLogs)).filter(
        models.ToegangsLogs.TOE_Tydstempel < nou_utc,
    ).order_by(models.ToegangsLogs.TOE_Tydstempel, models.ToegangsLogs.Log_ID).yield_per(1000):
        laaste[log.Gebruiker_ID] = log

    skanderings: dict[int, int] = defaultdict(int)
    dae_in: dict[int, set[date]] = defaultdict(set)
    daagliks_in: dict[date, set[int]] = defaultdict(set)
    for log in periode_logs:
        skanderings[log.Gebruiker_ID] += 1
        if _is_in(log):
            dag = _na_sa(log.TOE_Tydstempel).date()
            dae_in[log.Gebruiker_ID].add(dag)
            daagliks_in[dag].add(log.Gebruiker_ID)

    def status(gid: int) -> str:
        log = laaste.get(gid)
        if log is None:
            return STATUS_NOOIT
        return KOS_IN if _is_in(log) else KOS_UIT

    per_koshuis: dict[int, dict] = {
        k.Koshuis_ID: {KOS_IN: 0, KOS_UIT: 0, STATUS_NOOIT: 0, "inwoners": 0} for k in koshuise
    }
    for s in inwoners:
        tel = per_koshuis[s.Koshuis_ID]
        tel["inwoners"] += 1
        tel[status(s.Gebruiker_ID)] += 1

    totaal_kap = sum(k.KOS_Kapasiteit or 0 for k in koshuise)
    tans_in = sum(t[KOS_IN] for t in per_koshuis.values())
    tans_uit = sum(t[KOS_UIT] for t in per_koshuis.values())
    nooit = sum(t[STATUS_NOOIT] for t in per_koshuis.values())

    kernsyfers = [
        _syfer("Koshuise", len(koshuise)),
        _syfer("Inwoners", len(inwoners)),
        _syfer("Totale kapasiteit", totaal_kap),
        _syfer("Besetting", _verhouding(len(inwoners), totaal_kap), PERSENT),
        _syfer("Tans ingeteken", tans_in),
        _syfer("Tans uitgeteken", tans_uit),
        _syfer("Nog nooit gescan", nooit),
        _syfer("Koshuis-skanderings in tydperk", len(periode_logs)),
    ]

    insigte: list[str] = []
    if not koshuise:
        insigte.append("Daar is geen koshuise binne hierdie omvang nie.")
    else:
        insigte.append(
            f"{len(inwoners)} inwoners in {len(koshuise)} koshuis(e) — "
            f"{_verhouding(len(inwoners), totaal_kap) or 0:.0%} van die totale kapasiteit van {totaal_kap}."
        )
        vol = [k for k in koshuise if k.KOS_Kapasiteit and per_koshuis[k.Koshuis_ID]["inwoners"] >= k.KOS_Kapasiteit]
        if vol:
            insigte.append("Vol of oor kapasiteit: " + ", ".join(k.KOS_Naam for k in vol) + ".")
        insigte.append(f"Tans ingeteken: {tans_in}; uitgeteken: {tans_uit} (volgens hul jongste koshuis-skandering).")
        if nooit:
            insigte.append(f"{nooit} inwoner(s) is nog nooit by 'n koshuis gescan nie.")
        if not koshuis_lok_ids:
            insigte.append("Geen koshuis-skandeerplek is nog opgestel nie, so daar is geen koshuis-skanderings nie.")
        dae = [(d, len(daagliks_in.get(d, ()))) for d in _alle_dae(van, tot_effektief)]
        if (t := _tendens_insig(dae, "Koshuis-inteken")):
            insigte.append(t)

    alle_dae = _alle_dae(van, tot_effektief)
    grafieke = [
        _sirkel("Huidige status van inwoners", [
            (KOS_IN, tans_in), (KOS_UIT, tans_uit), ("Nog nooit gescan", nooit),
        ]),
        _balk("Besetting per koshuis", [
            (k.KOS_Naam, _verhouding(per_koshuis[k.Koshuis_ID]["inwoners"], k.KOS_Kapasiteit or 0) or 0)
            for k in koshuise
        ], PERSENT),
        _lyn("Inwoners ingeteken per dag", alle_dae, [
            ("Inwoners", [len(daagliks_in.get(d, ())) for d in alle_dae]),
        ]),
    ]

    koshuis_rye = []
    for k in koshuise:
        t = per_koshuis[k.Koshuis_ID]
        koshuis_rye.append([
            k.KOS_Naam, k.kampus.KAM_Naam if k.kampus else None, k.KOS_Kapasiteit,
            t["inwoners"], _verhouding(t["inwoners"], k.KOS_Kapasiteit or 0),
            t[KOS_IN], t[KOS_UIT], t[STATUS_NOOIT],
        ])

    kos_naam = {k.Koshuis_ID: k.KOS_Naam for k in koshuise}

    # Veiligheidswaarskuwing: ná 22:00 SA-tyd moet 'n koshuisinwoner se
    # jongste koshuis-skandering IN wees.  UIT of geen skandering word rooi
    # gemerk op die web-verslag deur die waarskuwing-teks hieronder.
    koshuis_afsny_aktief = _na_sa(nou_utc).hour >= 22

    inwoner_rye = []
    for s in sorted(inwoners, key=lambda s: (kos_naam.get(s.Koshuis_ID, ""), s.gebruiker.GEB_Van, s.gebruiker.GEB_Naam)):
        log = laaste.get(s.Gebruiker_ID)
        huidige_status = status(s.Gebruiker_ID)
        koshuis_warning = (
            "⚠ Koshuis: nie teen 22:00 ingeskandeer nie"
            if koshuis_afsny_aktief and huidige_status != KOS_IN
            else ""
        )
        inwoner_rye.append([
            _volle_naam(s.gebruiker), s.STU_Nommer, kos_naam.get(s.Koshuis_ID),
            huidige_status, _na_sa(log.TOE_Tydstempel) if log else None,
            len(dae_in.get(s.Gebruiker_ID, ())), skanderings.get(s.Gebruiker_ID, 0),
            koshuis_warning,
        ])

    student_per_id = {s.Gebruiker_ID: s for s in inwoners}
    log_rye = []
    for log in reversed(periode_logs):
        s = student_per_id.get(log.Gebruiker_ID)
        log_rye.append([
            _na_sa(log.TOE_Tydstempel),
            _volle_naam(s.gebruiker) if s else None,
            s.STU_Nommer if s else None,
            kos_naam.get(s.Koshuis_ID) if s else None,
            log.TOE_Rigting, log.TOE_Metode,
        ])

    tabelle = [
        _tabel("koshuise", "Koshuise", [
            ("Koshuis", TEKS), ("Kampus", TEKS), ("Kapasiteit", GETAL), ("Inwoners", GETAL),
            ("Besetting %", PERSENT), ("Ingeteken", GETAL), ("Uitgeteken", GETAL),
            ("Nog nooit gescan", GETAL),
        ], koshuis_rye, maks_rye),
        _tabel("inwoners", "Inwoners", [
            ("Naam", TEKS), ("Studentenommer", TEKS), ("Koshuis", TEKS), ("Huidige status", TEKS),
            ("Laaste skandering", DATUMTYD), ("Dae ingeteken", GETAL), ("Skanderings", GETAL),
            ("Waarskuwing", TEKS),
        ], inwoner_rye, maks_rye),
        _tabel("koshuis_logs", "Koshuis-skanderings", [
            ("Tyd", DATUMTYD), ("Naam", TEKS), ("Studentenommer", TEKS), ("Koshuis", TEKS),
            ("Rigting", TEKS), ("Metode", TEKS),
        ], log_rye, maks_rye),
    ]

    return {
        "sleutel": "koshuis",
        "titel": "Koshuis",
        "beskrywing": "Koshuise, hul inwoners en wie tans in- of uitgeteken is.",
        "kernsyfers": kernsyfers,
        "insigte": insigte,
        "grafieke": grafieke,
        "tabelle": tabelle,
    }


# --------------------------------------------------------------------------- #
# Afdeling: Events
# --------------------------------------------------------------------------- #

_BYWONER_STATUS = {"IN": "Binne", "UIT": "Het vertrek", "NOG_NIE": "Nie aangekom nie"}


def _event_status(event: models.Funksie, nou_utc: datetime) -> str:
    if not event.FUN_Is_Aktief or (event.FUN_Status or "AKTIEF").upper() != "AKTIEF":
        return "Gekanselleer"
    if event.FUN_Eind_Tyd < nou_utc:
        return "Afgehandel"
    if event.FUN_Begin_Tyd > nou_utc:
        return "Komende"
    return "Aan die gang"


def _afdeling_events(db: Session, omvang: Omvang, van: date, tot: date,
                     nou_utc: datetime, maks_rye: Optional[int]) -> dict:
    # Laat import: routers.events trek die hele events-roete in.
    from routers.events import _attendance_payload

    q = db.query(models.Funksie).filter(
        models.Funksie.FUN_Begin_Tyd >= _sa_dag_begin_utc(van),
        models.Funksie.FUN_Begin_Tyd < _sa_dag_begin_utc(tot + timedelta(days=1)),
    )
    if omvang.tipe == OMVANG_KAMPUS:
        q = q.filter(models.Funksie.Kampus_ID == omvang.kampus_id)
    events = q.order_by(models.Funksie.FUN_Begin_Tyd).all()

    event_rye, bywoner_rye = [], []
    opkoms_items: list[tuple[str, float]] = []
    status_tel: dict[str, int] = defaultdict(int)
    rsvp_tot = aangekom_tot = no_show_tot = app_tot = ekstern_tot = 0
    gemeet_rsvp = gemeet_aangekom = 0

    for e in events:
        status = _event_status(e, nou_utc)
        status_tel[status] += 1
        begin_sa = _na_sa(e.FUN_Begin_Tyd)
        rsvp = aangekom = nie = None
        if status != "Gekanselleer":
            payload = _attendance_payload(db, e)
            som = payload["summary"]
            rsvp, aangekom = som["rsvp"], som["aangekom"]
            nie = som["nog_nie_gekom"]
            rsvp_tot += rsvp
            app_tot += som["app_rsvp"]
            ekstern_tot += som["eksterne_rsvp"]
            if status in ("Afgehandel", "Aan die gang"):
                aangekom_tot += aangekom
                gemeet_rsvp += rsvp
                gemeet_aangekom += aangekom
                if rsvp:
                    opkoms_items.append((e.FUN_Naam, aangekom / rsvp))
            if status == "Afgehandel":
                no_show_tot += som["no_show"]
            for a in payload["attendees"]:
                a_status = _BYWONER_STATUS.get(a["status"], a["status"])
                if a["status"] == "NOG_NIE" and status == "Afgehandel":
                    a_status = "Nie opgedaag nie"
                bywoner_rye.append([
                    e.FUN_Naam, begin_sa.date(), a["volle_naam"], a["rol"].title(),
                    a["nommer"] or None, a_status, _iso_na_sa(a["eerste_in"]),
                ])
        event_rye.append([
            e.FUN_Naam, e.kampus.KAM_Naam if e.kampus else None,
            e.lokasie.LOK_Naam if e.lokasie else None,
            begin_sa, _na_sa(e.FUN_Eind_Tyd), status, e.FUN_Kapasiteit,
            rsvp, aangekom, nie, _verhouding(aangekom or 0, rsvp or 0) if rsvp else None,
        ])

    gem_opkoms = _verhouding(gemeet_aangekom, gemeet_rsvp)
    kernsyfers = [
        _syfer("Events in tydperk", len(events)),
        _syfer("Afgehandel", status_tel["Afgehandel"]),
        _syfer("Komende", status_tel["Komende"]),
        _syfer("Gekanselleer", status_tel["Gekanselleer"]),
        _syfer("Totale RSVP's", rsvp_tot),
        _syfer("Aangekom", aangekom_tot),
        _syfer("Nie opgedaag nie", no_show_tot),
        _syfer("Gem. opkoms", gem_opkoms, PERSENT),
    ]

    insigte: list[str] = []
    if not events:
        insigte.append("Geen events het in hierdie tydperk plaasgevind of is geskeduleer nie.")
    else:
        insigte.append(
            f"{len(events)} event(s) in die tydperk: {status_tel['Afgehandel']} afgehandel, "
            f"{status_tel['Komende']} komende, {status_tel['Gekanselleer']} gekanselleer."
        )
        if gem_opkoms is not None:
            insigte.append(f"Gemiddelde opkoms by events was {gem_opkoms:.0%} van die RSVP's.")
        if opkoms_items:
            beste = max(opkoms_items, key=lambda kv: kv[1])
            swakste = min(opkoms_items, key=lambda kv: kv[1])
            if len(opkoms_items) > 1:
                insigte.append(
                    f"Beste opkoms: {beste[0]} ({beste[1]:.0%}). Swakste opkoms: {swakste[0]} ({swakste[1]:.0%})."
                )
        if ekstern_tot:
            insigte.append(f"{ekstern_tot} van die {rsvp_tot} RSVP's was eksterne gaste.")

    grafieke = [
        _sirkel("Opkoms (afgehandelde en lopende events)", [
            ("Aangekom", gemeet_aangekom), ("Nie aangekom nie", gemeet_rsvp - gemeet_aangekom),
        ]),
        _sirkel("RSVP-bron", [("App-gebruikers", app_tot), ("Eksterne gaste", ekstern_tot)]),
        _balk("Opkoms per event", opkoms_items[-12:], PERSENT),
    ]

    tabelle = [
        _tabel("events", "Events", [
            ("Event", TEKS), ("Kampus", TEKS), ("Lokaal", TEKS), ("Begin", DATUMTYD),
            ("Einde", DATUMTYD), ("Status", TEKS), ("Kapasiteit", GETAL), ("RSVP's", GETAL),
            ("Aangekom", GETAL), ("Nie aangekom nie", GETAL), ("Opkoms %", PERSENT),
        ], event_rye, maks_rye),
        _tabel("bywoners", "Bywoners", [
            ("Event", TEKS), ("Datum", DATUM), ("Naam", TEKS), ("Rol", TEKS),
            ("Nommer", TEKS), ("Status", TEKS), ("Eerste IN", DATUMTYD),
        ], bywoner_rye, maks_rye),
    ]

    return {
        "sleutel": "events",
        "titel": "Events",
        "beskrywing": "Events in die tydperk, hul RSVP's en wie werklik opgedaag het.",
        "kernsyfers": kernsyfers,
        "insigte": insigte,
        "grafieke": grafieke,
        "tabelle": tabelle,
    }


# --------------------------------------------------------------------------- #
# Afdeling: Klas (Personeel)
# --------------------------------------------------------------------------- #

def _afdeling_klas(data: dict, maks_rye: Optional[int]) -> dict:
    persone: dict[int, Persoon] = data["persone"]
    studente = [p for p in persone.values() if p.is_student]
    sessies = sorted(data["sessies"], key=lambda s: (s["dag"], s["begin"]))
    gemeet = [s for s in sessies if s["klas"].Lokasie_ID and s["roster"]]
    ongekoppel = sum(1 for s in sessies if not s["klas"].Lokasie_ID)

    totaal_geregistreer = sum(len(s["roster"]) for s in gemeet)
    totaal_teenwoordig = sum(len(s["teenwoordig"]) for s in gemeet)
    klas_bywoning = _verhouding(totaal_teenwoordig, totaal_geregistreer)

    def bywoning(p: Persoon) -> Optional[float]:
        return _verhouding(p.sessies_bygewoon, p.sessies_geskeduleer)

    lae = [p for p in studente if (b := bywoning(p)) is not None and b < LAE_BYWONING]

    per_module: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    per_dag: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    for s in gemeet:
        kode = s["klas"].module.MOD_Kode if s["klas"].module else "?"
        per_module[kode][0] += len(s["teenwoordig"])
        per_module[kode][1] += len(s["roster"])
        per_dag[s["dag"]][0] += len(s["teenwoordig"])
        per_dag[s["dag"]][1] += len(s["roster"])
    module_pers = {m: t / r for m, (t, r) in sorted(per_module.items()) if r}

    kernsyfers = [
        _syfer("Klasse in rooster", len(data["klasse"])),
        _syfer("Studente", len(studente)),
        _syfer("Klasperiodes gemeet", len(gemeet)),
        _syfer("Algehele klasbywoning", klas_bywoning, PERSENT),
        _syfer(f"Studente onder {LAE_BYWONING:.0%} bywoning", len(lae)),
        _syfer("Periodes sonder NFC-koppeling", ongekoppel),
    ]

    insigte: list[str] = []
    if klas_bywoning is not None:
        insigte.append(f"Algehele klasbywoning was {klas_bywoning:.0%} oor {len(gemeet)} gemete klasperiodes.")
        if len(module_pers) > 1:
            m, p = min(module_pers.items(), key=lambda kv: kv[1])
            insigte.append(f"Module met die laagste klasbywoning: {m} ({p:.0%}).")
        dae = sorted(per_dag.items())
        if (t := _tendens_insig([(d, t / r if r else 0) for d, (t, r) in dae], "Klasbywoning")):
            insigte.append(t)
    if ongekoppel:
        insigte.append(
            f"{ongekoppel} klasperiodes kon nie gemeet word nie omdat die lokaal nie aan "
            f"'n NFC-lokasie gekoppel is nie."
        )
    if lae:
        insigte.append(f"{len(lae)} student(e) het klasbywoning onder {LAE_BYWONING:.0%}.")
    elif studente and klas_bywoning is not None:
        insigte.append(f"Geen student het klasbywoning onder {LAE_BYWONING:.0%} nie.")
    if not sessies:
        insigte.append("Geen klasperiodes het in hierdie tydperk plaasgevind nie.")

    dae = sorted(per_dag)
    grafieke = [
        _sirkel("Teenwoordig teenoor afwesig", [
            ("Teenwoordig", totaal_teenwoordig), ("Afwesig", totaal_geregistreer - totaal_teenwoordig),
        ]),
        _sirkel("Studente volgens bywoning", [
            (f"{LAE_BYWONING:.0%} of meer", sum(1 for p in studente if (b := bywoning(p)) is not None and b >= LAE_BYWONING)),
            (f"Onder {LAE_BYWONING:.0%}", len(lae)),
            ("Geen gemete klasse", sum(1 for p in studente if bywoning(p) is None)),
        ]),
        _balk("Bywoning per module", list(module_pers.items()), PERSENT),
        _lyn("Klasbywoning per dag", dae, [
            ("Bywoning", [per_dag[d][0] / per_dag[d][1] if per_dag[d][1] else 0 for d in dae]),
        ], PERSENT),
    ]

    student_rye = []
    for p in sorted(studente, key=lambda p: (p.gebruiker.GEB_Van, p.gebruiker.GEB_Naam)):
        b = bywoning(p)
        student_rye.append([
            p.naam, _nommer(p.gebruiker), p.sessies_bygewoon, p.sessies_geskeduleer, b,
            "Lae bywoning" if b is not None and b < LAE_BYWONING else "",
        ])

    sessie_rye, register_rye = [], []
    for s in sessies:
        klas = s["klas"]
        gekoppel = bool(klas.Lokasie_ID)
        geregistreer = len(s["roster"])
        teenwoordig = len(s["teenwoordig"]) if gekoppel else None
        lokaal = klas.lokasie.LOK_Naam if klas.lokasie else klas.KLA_Lokaal
        kode = klas.module.MOD_Kode if klas.module else None
        sessie_rye.append([
            s["dag"], _dag_naam(s["dag"]), f"{s['begin']}-{s['eind']}", kode,
            klas.module.MOD_Naam if klas.module else None, lokaal,
            geregistreer, teenwoordig,
            (geregistreer - teenwoordig) if gekoppel else None,
            _verhouding(teenwoordig, geregistreer) if gekoppel else None,
            "" if gekoppel else "Lokaal nie aan NFC gekoppel nie",
        ])
        if not gekoppel:
            continue
        for p in sorted((persone[g] for g in s["roster"] if g in persone),
                        key=lambda p: (p.gebruiker.GEB_Van, p.gebruiker.GEB_Naam)):
            tyd = s["teenwoordig"].get(p.gebruiker.Gebruiker_ID)
            register_rye.append([
                s["dag"], f"{s['begin']}-{s['eind']}", kode, lokaal, p.naam, _nommer(p.gebruiker),
                "Teenwoordig" if tyd else "Afwesig", tyd,
            ])

    tabelle = [
        _tabel("studente", "Studente", [
            ("Naam", TEKS), ("Studentenommer", TEKS), ("Klasse bygewoon", GETAL),
            ("Klasse geskeduleer", GETAL), ("Klasbywoning %", PERSENT), ("Let op", TEKS),
        ], student_rye, maks_rye),
        _tabel("klasperiodes", "Klasperiodes", [
            ("Datum", DATUM), ("Dag", TEKS), ("Tyd", TEKS), ("Module", TEKS), ("Modulenaam", TEKS),
            ("Lokaal", TEKS), ("Geregistreer", GETAL), ("Teenwoordig", GETAL), ("Afwesig", GETAL),
            ("Bywoning %", PERSENT), ("Nota", TEKS),
        ], sessie_rye, maks_rye),
        _tabel("klasregister", "Klasregister", [
            ("Datum", DATUM), ("Tyd", TEKS), ("Module", TEKS), ("Lokaal", TEKS), ("Student", TEKS),
            ("Studentenommer", TEKS), ("Status", TEKS), ("Ingescan", DATUMTYD),
        ], register_rye, maks_rye),
    ]

    return {
        "sleutel": "klas",
        "titel": "Klas",
        "beskrywing": "Klasbywoning van die studente in jou eie klasse.",
        "kernsyfers": kernsyfers,
        "insigte": insigte,
        "grafieke": grafieke,
        "tabelle": tabelle,
    }


# --------------------------------------------------------------------------- #
# Publieke ingang
# --------------------------------------------------------------------------- #

def valideer_tydperk(van: date, tot: date) -> None:
    if tot < van:
        raise HTTPException(status_code=400, detail="'Tot'-datum moet na die 'van'-datum wees")
    if (tot - van).days + 1 > MAKS_DAE:
        raise HTTPException(status_code=400, detail=f"Tydperk mag hoogstens {MAKS_DAE} dae wees")


def bou_oorsig(
    db: Session,
    gebruiker: models.Gebruikers,
    rolle: list[str],
    van: date,
    tot: date,
    kampus_id: Optional[int] = None,
    nou: Optional[datetime] = None,
    maks_rye: Optional[int] = None,
) -> dict:
    """Bou die volledige verslag as afdelings met kernsyfers, insigte, grafieke en tabelle.

    maks_rye beperk elke tabel se rye (vir die webwerf se voorskou); elke tabel
    hou steeds sy volle 'totaal'.
    """
    valideer_tydperk(van, tot)
    omvang = bepaal_omvang(db, gebruiker, rolle, kampus_id)
    nou_utc = nou or datetime.utcnow()
    data = versamel_verslag(db, omvang, van, tot, nou_utc)

    if omvang.tipe == OMVANG_KLASSE:
        afdelings = [_afdeling_klas(data, maks_rye)]
    else:
        afdelings = [
            _afdeling_kampus(data, maks_rye),
            _afdeling_koshuis(db, omvang, van, data["tot_effektief"], nou_utc, maks_rye),
            _afdeling_events(db, omvang, van, tot, nou_utc, maks_rye),
        ]

    return {
        "titel": "MOON Bywoningsverslag",
        "meta": {
            "omvang": omvang.beskrywing,
            "omvang_tipe": omvang.tipe,
            "van": van,
            "tot": tot,
            "werksdae": len(data["werksdae"]),
            "gegenereer_op": data["nou_sa"],
            "gegenereer_deur": _volle_naam(gebruiker),
            "rol": kies_primere_rol(rolle),
        },
        "afdelings": afdelings,
    }


def genereer_verslag(
    db: Session,
    gebruiker: models.Gebruikers,
    rolle: list[str],
    van: date,
    tot: date,
    kampus_id: Optional[int] = None,
    nou: Optional[datetime] = None,
    formaat: str = "xlsx",
) -> tuple[bytes, str]:
    """Gee (lêer-bytes, lêernaam) terug in die gevraagde formaat."""
    from services.verslag_formate import skryf_verslag

    oorsig = bou_oorsig(db, gebruiker, rolle, van, tot, kampus_id, nou)
    inhoud = skryf_verslag(oorsig, formaat)
    lêernaam = f"moon_bywoning_{van:%Y%m%d}_{tot:%Y%m%d}.{formaat}"
    return inhoud, lêernaam
