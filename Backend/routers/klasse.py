"""Klas / Module / Groep rooster-roetes (admin-toewysing + CSV-invoer)."""

import csv
import io
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/rooster", tags=["Klas / Module / Groep"])

# --- GEDEELDE ROOSTER-KONSTANTES ---
# Hou hierdie module-vlak name beskikbaar: services/verslag_service.py importeer
# hulle direk uit routers.klasse.
_SA_TZ = ZoneInfo("Africa/Johannesburg")
_DAE = {
    "maandag": 0, "monday": 0,
    "dinsdag": 1, "tuesday": 1,
    "woensdag": 2, "wednesday": 2,
    "donderdag": 3, "thursday": 3,
    "vrydag": 4, "friday": 4,
    "saterdag": 5, "saturday": 5,
    "sondag": 6, "sunday": 6,
}


# --- CSV PARSER ---

def parse_lantiv_csv(inhoud: str) -> list[dict]:
    """Pars die Lantiv-uitvoer-CSV met sy ongewone dubbelaanhalingstekens.

    Lantiv draai elke RY in een paar buitenste aanhalingstekens, met die
    velde binne-in dubbel-aangehaal, bv.:
    '"10:00,""9:00"",""Maandag"",""GH117 A (50)"",""FBR 3"",""EBREK370"",""9:00"",""10:00\"\"\"'
    Die buitenste kwote maak die hele ry een veld vir die standaard csv-leser;
    ons lees dus elke ry as een veld en parse dit dan weer om die 8 kolomme te
    kry.  Gewone CSV-rye (sonder buitenste kwote) word direk gebruik.
    """
    reëls = []
    for lyn in inhoud.splitlines():
        lyn = lyn.strip()
        if not lyn:
            continue
        try:
            rye = list(csv.reader(io.StringIO(lyn)))
            if not rye or not rye[0]:
                continue
            kolomme = rye[0]
            # As die hele ry een veld is (Lantiv se buitenste kwote), parse
            # daardie veld weer om die werklike kolomme te ontsyfer.
            if len(kolomme) < 8:
                rye2 = list(csv.reader(io.StringIO(kolomme[0])))
                if rye2 and rye2[0] and len(rye2[0]) >= 8:
                    kolomme = rye2[0]
                else:
                    continue
        except Exception:
            continue
        # Slaan die kopreeks oor (Dag-kolom is die kolomnaam "Dag").
        if kolomme[2].strip().lower() == "dag":
            continue
        # Kolomme: End Time, Start Time, Dag, Lokaal, Groep, Module, From, To
        reëls.append({
            "dag": kolomme[2].strip(),
            "lokaal": kolomme[3].strip(),
            "groep": kolomme[4].strip(),
            "module": kolomme[5].strip(),
            "from": kolomme[6].strip(),
            "to": kolomme[7].strip(),
        })
    return reëls



def parse_moon_rooster_csv(inhoud: str) -> list[dict]:
    """Pars die nuwe MOON-roosterformaat met 'n gewone kop-ry.

    Vereiste kolomme:
    Rooster_ID, Dag, Begin_Tyd, Eind_Tyd, Module, Groep,
    Lokaal, Lokaal_Naam, Kampus, Kapasiteit.

    Die importer gebruik Lokaal_Naam + Kampus om direk teen MOON se
    ``lokasie``-tabel te match. ``Lokaal`` word as die bron-/roosterkode in
    KLA_Lokaal behou vir naspeurbaarheid en backwards compatibility.
    """
    leser = csv.DictReader(io.StringIO(inhoud))
    if not leser.fieldnames:
        raise HTTPException(status_code=400, detail="Die MOON-rooster CSV het geen kop-ry nie")

    vereis = {
        "Rooster_ID", "Dag", "Begin_Tyd", "Eind_Tyd", "Module",
        "Groep", "Lokaal", "Lokaal_Naam", "Kampus", "Kapasiteit",
    }
    ontbreek = sorted(vereis - set(leser.fieldnames))
    if ontbreek:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ongeldige MOON-roosterformaat. Ontbrekende kolomme: "
                + ", ".join(ontbreek)
            ),
        )

    rye: list[dict] = []
    for ry_nr, ry in enumerate(leser, start=2):
        # Slaan heeltemal leë rye oor.
        if not any(str(v or "").strip() for v in ry.values()):
            continue
        rye.append({
            "ry": ry_nr,
            "rooster_id": str(ry.get("Rooster_ID") or "").strip(),
            "dag": str(ry.get("Dag") or "").strip(),
            "from": str(ry.get("Begin_Tyd") or "").strip(),
            "to": str(ry.get("Eind_Tyd") or "").strip(),
            "module": str(ry.get("Module") or "").strip(),
            "groep": str(ry.get("Groep") or "").strip(),
            "lokaal": str(ry.get("Lokaal") or "").strip(),
            "lokaal_naam": str(ry.get("Lokaal_Naam") or "").strip(),
            "kampus": str(ry.get("Kampus") or "").strip(),
            "kapasiteit": str(ry.get("Kapasiteit") or "").strip(),
        })
    return rye


# Kolomname (genormaliseer: kleinletters, sonder spasies/onderstrepe) wat
# die student-toewysing-CSV mag gebruik.
_STUDENT_KOLOMME = {"studentenommer", "stunommer", "studentnommer", "student", "studentnumber", "nommer"}
_EPOS_KOLOMME = {"epos", "e-pos", "email", "gebepos"}
_GROEP_KOLOMME = {"groep", "groepe", "gronaam", "group", "groups"}
_MODULE_KOLOMME = {"module", "modules", "modkode", "modulekode"}


def _normaliseer_kop(naam: str) -> str:
    return (naam or "").strip().lower().replace(" ", "").replace("_", "")


def _splits_waardes(teks: str) -> list[str]:
    """'ER 2; LLB 2' of 'ER 2, LLB 2' -> ['ER 2', 'LLB 2']."""
    if not teks:
        return []
    return [w.strip() for w in teks.replace(";", ",").split(",") if w.strip()]


def parse_student_toewysing_csv(inhoud: str) -> list[dict]:
    """Pars die student-toewysing-CSV (kop-ry + 'n ry per student).

    Verwagte kolomme (naam is buigsaam, sien _*_KOLOMME): studentenommer
    (of epos), groep, module.  Groep en module mag meer as een waarde bevat,
    geskei met ';' of ','.  Gee 'n lys van
    {"ry", "student", "epos", "groepe", "modules"} terug; 'n leë lys as die
    kop-ry geen student-/epos-kolom het nie.
    """
    leser = csv.DictReader(io.StringIO(inhoud))
    if not leser.fieldnames:
        return []
    kop = {_normaliseer_kop(k): k for k in leser.fieldnames if k}
    student_kol = next((kop[k] for k in kop if k in _STUDENT_KOLOMME), None)
    epos_kol = next((kop[k] for k in kop if k in _EPOS_KOLOMME), None)
    groep_kol = next((kop[k] for k in kop if k in _GROEP_KOLOMME), None)
    module_kol = next((kop[k] for k in kop if k in _MODULE_KOLOMME), None)
    if not student_kol and not epos_kol:
        return []

    rye = []
    for ry_nr, ry in enumerate(leser, start=2):  # ry 1 is die kop-ry
        student = (ry.get(student_kol) or "").strip() if student_kol else ""
        epos = (ry.get(epos_kol) or "").strip() if epos_kol else ""
        if not student and not epos:
            continue
        rye.append({
            "ry": ry_nr,
            "student": student,
            "epos": epos,
            "groepe": _splits_waardes(ry.get(groep_kol) or "") if groep_kol else [],
            "modules": _splits_waardes(ry.get(module_kol) or "") if module_kol else [],
        })
    return rye


# --- ROOSTER RESOLUTION HELPERS ---

def _aktiewe_lokasie_nfc_uid(lokasie: models.Lokasie | None) -> str | None:
    if lokasie is None:
        return None
    for tag in (getattr(lokasie, "nfc_tags", None) or []):
        if tag.NFC_Is_Aktief and str(tag.NFC_Tipe or "").strip().casefold() == "lokasie":
            return tag.NFC_UID
    return None


def _normaliseer_nfc_uid(value: str | None) -> str:
    """Vergelyk NFC-kodes robuust: hoofletters en skeidingstekens maak nie saak nie."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").strip().upper())


def _vind_aktiewe_nfc_tag(db: Session, uid: str) -> models.NFC_Tags | None:
    """Vind eers presies; val terug na 'n genormaliseerde vergelyking."""
    rou = str(uid or "").strip()
    if not rou:
        return None

    tag = (
        db.query(models.NFC_Tags)
        .filter(
            models.NFC_Tags.NFC_UID == rou,
            models.NFC_Tags.NFC_Is_Aktief == True,
        )
        .first()
    )
    if tag is not None:
        return tag

    gesoek = _normaliseer_nfc_uid(rou)
    if not gesoek:
        return None

    for kandidaat in (
        db.query(models.NFC_Tags)
        .filter(models.NFC_Tags.NFC_Is_Aktief == True)
        .all()
    ):
        if _normaliseer_nfc_uid(kandidaat.NFC_UID) == gesoek:
            return kandidaat
    return None


def _klas_na_dict(klas: models.Klas) -> dict:
    lokasie = getattr(klas, "lokasie", None)
    return {
        "Klas_ID": klas.Klas_ID,
        "Module_ID": klas.Module_ID,
        "MOD_Kode": klas.module.MOD_Kode if klas.module else None,
        "MOD_Naam": klas.module.MOD_Naam if klas.module else None,
        "KLA_Lokaal": klas.KLA_Lokaal,
        "KLA_Dag": klas.KLA_Dag,
        "KLA_Begin_Tyd": klas.KLA_Begin_Tyd,
        "KLA_Eind_Tyd": klas.KLA_Eind_Tyd,
        "Lokasie_ID": getattr(klas, "Lokasie_ID", None),
        "LOK_Naam": lokasie.LOK_Naam if lokasie else None,
        "NFC_UID": _aktiewe_lokasie_nfc_uid(lokasie),
        "NFC_Gekoppel": bool(lokasie and _aktiewe_lokasie_nfc_uid(lokasie)),
    }


def _normaliseer_lokaal_naam(naam: str | None) -> str:
    """Normaliseer rooster/lokasie-name; bv. 'GH117 A (50)' -> 'gh117 a'."""
    teks = (naam or "").strip().casefold()
    teks = re.sub(r"\s*\([^)]*\)\s*$", "", teks)
    return " ".join(teks.split())


def _vind_klaskamer_lokasie(db: Session, lokaal_naam: str | None) -> models.Lokasie | None:
    """Vind 'n unieke Klaskamer-lokasie wat by die rooster se lokaalnaam pas."""
    normaal = _normaliseer_lokaal_naam(lokaal_naam)
    if not normaal:
        return None
    kandidate = (
        db.query(models.Lokasie)
        .filter(func.lower(models.Lokasie.LOK_Tipe) == "klaskamer")
        .all()
    )
    matches = [l for l in kandidate if _normaliseer_lokaal_naam(l.LOK_Naam) == normaal]
    return matches[0] if len(matches) == 1 else None


def _vind_moon_klaskamer_lokasie(
    db: Session,
    lokaal_naam: str | None,
    kampus_naam: str | None,
    lokaal_kode: str | None = None,
) -> models.Lokasie | None:
    """Vind presies een MOON-klaskamer volgens lokaalnaam + kampus.

    ``Lokaal_Naam`` uit die nuwe MOON CSV is die primêre match. ``Lokaal``
    (die bronkode, bv. GH117 A) word slegs as 'n veilige fallback gebruik.
    Die kampus moet altyd match, sodat gelyknamige lokale op verskillende
    kampusse nie per ongeluk gekruis word nie.
    """
    naam = _normaliseer_lokaal_naam(lokaal_naam)
    kode = _normaliseer_lokaal_naam(lokaal_kode)
    kampus = _normaliseer_lokaal_naam(kampus_naam)
    if not kampus or (not naam and not kode):
        return None

    kandidate = (
        db.query(models.Lokasie)
        .options(joinedload(models.Lokasie.kampus))
        .filter(func.lower(models.Lokasie.LOK_Tipe) == "klaskamer")
        .all()
    )

    def kampus_match(lokasie: models.Lokasie) -> bool:
        rel = getattr(lokasie, "kampus", None)
        return bool(rel and _normaliseer_lokaal_naam(getattr(rel, "KAM_Naam", None)) == kampus)

    primêr = [
        l for l in kandidate
        if kampus_match(l) and _normaliseer_lokaal_naam(l.LOK_Naam) == naam
    ]
    if len(primêr) == 1:
        return primêr[0]
    if len(primêr) > 1:
        return None

    # Backwards-compatible fallback indien die DB nog die rooster-/lokaalkode
    # as LOK_Naam gebruik eerder as die vriendelike naam.
    if kode:
        fallback = [
            l for l in kandidate
            if kampus_match(l) and _normaliseer_lokaal_naam(l.LOK_Naam) == kode
        ]
        if len(fallback) == 1:
            return fallback[0]
    return None


def _probeer_bind_klas_lokasie(db: Session, klas: models.Klas) -> bool:
    """Koppel 'n nog-ongekoppelde roosterklas outomaties wanneer lokaalnaam uniek match."""
    if getattr(klas, "Lokasie_ID", None):
        return False
    lokasie = _vind_klaskamer_lokasie(db, klas.KLA_Lokaal)
    if lokasie is None:
        return False
    klas.Lokasie_ID = lokasie.Lokasie_ID
    return True


def _kry_rooster_lokaal_mapping(db: Session, lokaal_naam: str | None) -> models.Rooster_Lokaal_Koppeling | None:
    naam = (lokaal_naam or "").strip()
    if not naam:
        return None
    return (
        db.query(models.Rooster_Lokaal_Koppeling)
        .options(joinedload(models.Rooster_Lokaal_Koppeling.lokasie))
        .filter(models.Rooster_Lokaal_Koppeling.KLA_Lokaal == naam)
        .first()
    )


def _pas_rooster_lokaal_mapping_toe(db: Session, klas: models.Klas) -> bool:
    """Gebruik slegs 'n eksplisiete Admin mapping; moenie nuwe name outomaties raai nie."""
    mapping = _kry_rooster_lokaal_mapping(db, klas.KLA_Lokaal)
    if mapping is None:
        return False
    if klas.Lokasie_ID == mapping.Lokasie_ID:
        return False
    klas.Lokasie_ID = mapping.Lokasie_ID
    return True


def resolver_student_rooster(db: Session, gebruiker_id: int) -> list[dict]:
    """Merg (dedupeer) die student se rooster uit 3 bronne."""
    gesien: set[int] = set()
    resultaat: list[dict] = []

    def voeg_by(klas: models.Klas):
        if klas is None or klas.Klas_ID in gesien:
            return
        gesien.add(klas.Klas_ID)
        resultaat.append(_klas_na_dict(klas))

    groepe = (
        db.query(models.Student_Groep.Groep_ID)
        .filter(models.Student_Groep.Gebruiker_ID == gebruiker_id)
        .all()
    )
    groep_ids = [g[0] for g in groepe]
    if groep_ids:
        klas_ids = (
            db.query(models.Klas_Groep.Klas_ID)
            .filter(models.Klas_Groep.Groep_ID.in_(groep_ids))
            .all()
        )
        groepeer_klasse = (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Klas_ID.in_([kid for (kid,) in klas_ids]))
            .all()
        )
        for klas in groepeer_klasse:
            voeg_by(klas)

    module_ids = [
        m[0]
        for m in db.query(models.Student_Module.Module_ID)
        .filter(models.Student_Module.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if module_ids:
        for klas in (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Module_ID.in_(module_ids))
            .all()
        ):
            voeg_by(klas)

    direkte_ids = [
        k[0]
        for k in db.query(models.Student_Klas.Klas_ID)
        .filter(models.Student_Klas.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if direkte_ids:
        for klas in (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Klas_ID.in_(direkte_ids))
            .all()
        ):
            voeg_by(klas)

    return resultaat


def resolver_personeel_rooster(db: Session, gebruiker_id: int) -> list[dict]:
    """Merg (dedupeer) die personeellid se rooster uit 2 bronne."""
    gesien: set[int] = set()
    resultaat: list[dict] = []

    def voeg_by(klas: models.Klas):
        if klas is None or klas.Klas_ID in gesien:
            return
        gesien.add(klas.Klas_ID)
        resultaat.append(_klas_na_dict(klas))

    module_ids = [
        m[0]
        for m in db.query(models.Personeel_Module.Module_ID)
        .filter(models.Personeel_Module.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if module_ids:
        for klas in (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Module_ID.in_(module_ids))
            .all()
        ):
            voeg_by(klas)

    direkte_ids = [
        k[0]
        for k in db.query(models.Personeel_Klas.Klas_ID)
        .filter(models.Personeel_Klas.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if direkte_ids:
        for klas in (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Klas_ID.in_(direkte_ids))
            .all()
        ):
            voeg_by(klas)

    return resultaat


def _parse_klas_tyd(value: str) -> time:
    teks = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%H.%M"):
        try:
            return datetime.strptime(teks, fmt).time()
        except ValueError:
            pass
    raise HTTPException(status_code=400, detail=f"Ongeldige klas-tyd: '{value}'")


def _klas_scan_venster(klas: models.Klas, dag: date) -> tuple[datetime, datetime, datetime, datetime]:
    """Gee die presiese geskeduleerde klasvenster in SA-tyd en UTC-naive.

    Ons gebruik doelbewus die rooster se begin/eind sonder vroeë/laat overlap,
    sodat twee opeenvolgende klasse in dieselfde lokaal nie dieselfde NFC-scan
    kan erf nie.
    """
    begin_local = datetime.combine(dag, _parse_klas_tyd(klas.KLA_Begin_Tyd), tzinfo=_SA_TZ)
    eind_local = datetime.combine(dag, _parse_klas_tyd(klas.KLA_Eind_Tyd), tzinfo=_SA_TZ)
    if eind_local <= begin_local:
        eind_local += timedelta(days=1)
    venster_begin_local = begin_local
    venster_eind_local = eind_local
    begin_utc = venster_begin_local.astimezone(timezone.utc).replace(tzinfo=None)
    eind_utc = venster_eind_local.astimezone(timezone.utc).replace(tzinfo=None)
    return venster_begin_local, venster_eind_local, begin_utc, eind_utc


def _klas_dag_match(klas: models.Klas, dag: date) -> bool:
    indeks = _DAE.get((klas.KLA_Dag or "").strip().casefold())
    return indeks is None or indeks == dag.weekday()


def _klas_roster_gebruiker_ids(db: Session, klas: models.Klas) -> set[int]:
    gebruiker_ids: set[int] = set()
    groep_ids = [
        g[0]
        for g in db.query(models.Klas_Groep.Groep_ID)
        .filter(models.Klas_Groep.Klas_ID == klas.Klas_ID)
        .all()
    ]
    if groep_ids:
        for (gid,) in (
            db.query(models.Student_Groep.Gebruiker_ID)
            .filter(models.Student_Groep.Groep_ID.in_(groep_ids))
            .all()
        ):
            gebruiker_ids.add(gid)

    for (gid,) in (
        db.query(models.Student_Module.Gebruiker_ID)
        .filter(models.Student_Module.Module_ID == klas.Module_ID)
        .all()
    ):
        gebruiker_ids.add(gid)

    for (gid,) in (
        db.query(models.Student_Klas.Gebruiker_ID)
        .filter(models.Student_Klas.Klas_ID == klas.Klas_ID)
        .all()
    ):
        gebruiker_ids.add(gid)
    return gebruiker_ids


def _klas_scan_statusse(
    db: Session,
    klas: models.Klas,
    gebruiker_ids: set[int],
    dag: date,
) -> tuple[dict[int, dict], dict]:
    """Jongste klaskamer-NFC scan binne hierdie roosterperiode per student."""
    venster_begin_local, venster_eind_local, begin_utc, eind_utc = _klas_scan_venster(klas, dag)
    meta = {
        "begin": venster_begin_local.isoformat(),
        "eind": venster_eind_local.isoformat(),
        "rooster_dag_match": _klas_dag_match(klas, dag),
    }
    if not gebruiker_ids or not getattr(klas, "Lokasie_ID", None) or not meta["rooster_dag_match"]:
        return {}, meta

    logs = (
        db.query(models.ToegangsLogs)
        .filter(
            models.ToegangsLogs.Gebruiker_ID.in_(gebruiker_ids),
            models.ToegangsLogs.Lokasie_ID == klas.Lokasie_ID,
            models.ToegangsLogs.TOE_Metode == "NFC",
            models.ToegangsLogs.TOE_Tydstempel >= begin_utc,
            models.ToegangsLogs.TOE_Tydstempel < eind_utc,
        )
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc(), models.ToegangsLogs.Log_ID.desc())
        .all()
    )
    resultaat: dict[int, dict] = {}
    for log in logs:
        if log.Gebruiker_ID in resultaat:
            continue
        local_dt = log.TOE_Tydstempel.replace(tzinfo=timezone.utc).astimezone(_SA_TZ)
        resultaat[log.Gebruiker_ID] = {
            "lokaal": klas.lokasie.LOK_Naam if getattr(klas, "lokasie", None) else klas.KLA_Lokaal,
            "lokasie_id": klas.Lokasie_ID,
            "tyd": local_dt.isoformat(),
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "teenwoordig": str(log.TOE_Rigting or "").upper() == "IN",
        }
    return resultaat, meta


def resolver_klas_studente(db: Session, klas_id: int, dag: Optional[date] = None) -> list[dict]:
    """Klasregister + klas-spesifieke NFC-status vir 'n roosterperiode."""
    klas = (
        db.query(models.Klas)
        .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
        .filter(models.Klas.Klas_ID == klas_id)
        .first()
    )
    if klas is None:
        return []

    gebruiker_ids = _klas_roster_gebruiker_ids(db, klas)
    if not gebruiker_ids:
        return []

    rye = (
        db.query(models.Gebruikers, models.Student)
        .outerjoin(models.Student, models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
        .filter(models.Gebruikers.Gebruiker_ID.in_(gebruiker_ids))
        .order_by(models.Gebruikers.GEB_Van, models.Gebruikers.GEB_Naam)
        .all()
    )
    dag = dag or datetime.now(_SA_TZ).date()
    skanderings, _ = _klas_scan_statusse(db, klas, gebruiker_ids, dag)
    resultaat = []
    for gebruiker, student in rye:
        scan = skanderings.get(gebruiker.Gebruiker_ID)
        resultaat.append({
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
            "STU_Nommer": student.STU_Nommer if student else None,
            "Teenwoordig": bool(scan and scan["teenwoordig"]),
            "Ingescan_Tyd": scan["tyd"] if scan and scan["teenwoordig"] else None,
            "Laaste_Rigting": scan["rigting"] if scan else None,
            "Laaste_Skandering": scan,
        })
    return resultaat


# --- ADMIN LYS-EINDPUNTE ---

@router.get("/modules")
def lys_modules(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    modules = db.query(models.Module).order_by(models.Module.MOD_Kode).all()
    return schemas.APIResponse(
        sukses=True,
        data=[
            {"Module_ID": m.Module_ID, "MOD_Kode": m.MOD_Kode, "MOD_Naam": m.MOD_Naam}
            for m in modules
        ],
    )


@router.get("/groepe")
def lys_groepe(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    groepe = db.query(models.Groep).order_by(models.Groep.GRO_Naam).all()
    return schemas.APIResponse(
        sukses=True,
        data=[{"Groep_ID": g.Groep_ID, "GRO_Naam": g.GRO_Naam} for g in groepe],
    )


@router.get("/klasse")
def lys_klasse(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    klasse = (
        db.query(models.Klas)
        .options(joinedload(models.Klas.module))
        .order_by(models.Klas.KLA_Dag)
        .all()
    )
    return schemas.APIResponse(
        sukses=True,
        data=[_klas_na_dict(k) for k in klasse],
    )


# --- ROOSTER-LOKAAL MAPPING (admin) ---

@router.get("/lokaal-koppelings")
def lys_rooster_lokaal_koppelings(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Wys unieke fisiese roosterlokale volgens die werklike Klas.Lokasie_ID.

    Ou Lantiv-name soos ``GH117 A (50)`` en nuwe MOON-name soos ``GH117 A``
    word as dieselfde bronlokaal gegroepeer. Die direkte Lokasie_ID op Klas is
    nou die primêre waarheid; Rooster_Lokaal_Koppeling is slegs 'n legacy
    fallback vir ou data wat nog geen direkte koppeling het nie.
    """
    klasse = (
        db.query(models.Klas)
        .options(
            joinedload(models.Klas.lokasie).joinedload(models.Lokasie.kampus),
            joinedload(models.Klas.lokasie).joinedload(models.Lokasie.nfc_tags),
        )
        .filter(models.Klas.KLA_Lokaal.isnot(None))
        .all()
    )

    mappings = {
        _normaliseer_lokaal_naam(m.KLA_Lokaal): m
        for m in (
            db.query(models.Rooster_Lokaal_Koppeling)
            .options(
                joinedload(models.Rooster_Lokaal_Koppeling.lokasie)
                .joinedload(models.Lokasie.kampus),
                joinedload(models.Rooster_Lokaal_Koppeling.lokasie)
                .joinedload(models.Lokasie.nfc_tags),
            )
            .all()
        )
    }

    gegroepeer: dict[str, list[models.Klas]] = {}
    for klas in klasse:
        sleutel = _normaliseer_lokaal_naam(klas.KLA_Lokaal)
        if sleutel:
            gegroepeer.setdefault(sleutel, []).append(klas)

    data = []
    for sleutel in sorted(gegroepeer):
        groep_klasse = gegroepeer[sleutel]
        # Verkies die skoon naam sonder die ou kapasiteit-agtervoegsel.
        skoon_name = [
            k.KLA_Lokaal for k in groep_klasse
            if _normaliseer_lokaal_naam(k.KLA_Lokaal) == sleutel
            and not re.search(r"\s*\([^)]*\)\s*$", k.KLA_Lokaal or "")
        ]
        bron_lokaal = skoon_name[0] if skoon_name else re.sub(
            r"\s*\([^)]*\)\s*$", "", groep_klasse[0].KLA_Lokaal or ""
        ).strip()

        lokasie_ids = {k.Lokasie_ID for k in groep_klasse if getattr(k, "Lokasie_ID", None)}
        lokasie = None
        if len(lokasie_ids) == 1:
            lokasie_id = next(iter(lokasie_ids))
            lokasie = next(
                (k.lokasie for k in groep_klasse if k.Lokasie_ID == lokasie_id and k.lokasie),
                None,
            )
        elif not lokasie_ids:
            # Legacy fallback vir data wat nog nie deur die MOON importer herstel is nie.
            mapping = mappings.get(sleutel)
            lokasie = mapping.lokasie if mapping else None

        data.append({
            "KLA_Lokaal": bron_lokaal,
            "Klas_Aantal": len(groep_klasse),
            "Gekoppel": bool(lokasie),
            "Lokasie_ID": lokasie.Lokasie_ID if lokasie else None,
            "LOK_Naam": lokasie.LOK_Naam if lokasie else None,
            "Kampus_ID": lokasie.Kampus_ID if lokasie else None,
            "KAM_Naam": lokasie.kampus.KAM_Naam if lokasie and lokasie.kampus else None,
            "NFC_UID": _aktiewe_lokasie_nfc_uid(lokasie),
            "NFC_Gekoppel": bool(lokasie and _aktiewe_lokasie_nfc_uid(lokasie)),
            "Konflik": len(lokasie_ids) > 1,
        })

    return schemas.APIResponse(sukses=True, data=data)


class KlasDuplikaatKonsolideerRequest(BaseModel):
    bevestig: bool = False


def _skuif_klas_koppeling(
    db: Session,
    model,
    gebruiker_of_groep_kolom,
    bron_klas_id: int,
    teiken_klas_id: int,
) -> int:
    """Skuif composite-PK Klas-koppelings sonder om duplicates te skep."""
    rye = db.query(model).filter(model.Klas_ID == bron_klas_id).all()
    geskuif = 0
    for ry in rye:
        ander_id = getattr(ry, gebruiker_of_groep_kolom)
        bestaande = db.query(model).filter(
            model.Klas_ID == teiken_klas_id,
            getattr(model, gebruiker_of_groep_kolom) == ander_id,
        ).first()
        if bestaande:
            db.delete(ry)
        else:
            ry.Klas_ID = teiken_klas_id
        geskuif += 1
    return geskuif


def _klas_duplikaat_sleutel(klas: models.Klas) -> tuple:
    return (
        klas.Module_ID,
        _normaliseer_lokaal_naam(klas.KLA_Lokaal),
        (klas.KLA_Dag or "").strip().casefold(),
        (klas.KLA_Begin_Tyd or "").strip(),
        (klas.KLA_Eind_Tyd or "").strip(),
    )


def _kies_kanonieke_klas(klasse: list[models.Klas]) -> models.Klas:
    """Verkies direkte Lokasie_ID, dan 'n skoon MOON-lokaalnaam, dan laagste ID."""
    def rang(klas: models.Klas):
        het_lokasie = 1 if getattr(klas, "Lokasie_ID", None) else 0
        skoon_naam = 0 if re.search(r"\s*\([^)]*\)\s*$", klas.KLA_Lokaal or "") else 1
        return (het_lokasie, skoon_naam, -int(klas.Klas_ID or 0))
    return max(klasse, key=rang)


@router.post("/klasse/konsolideer-duplikate")
def konsolideer_klas_duplikate(
    data: KlasDuplikaatKonsolideerRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Preview of merge ou Lantiv/MOON duplicate klasse.

    'n Duplicate beteken dieselfde module + genormaliseerde lokaal + dag +
    begin/eind-tyd. ``bevestig=false`` verander niks en gee slegs 'n preview.
    Met ``bevestig=true`` word Klas_Groep, Student_Klas en Personeel_Klas
    veilig na die kanonieke Klas_ID geskuif voordat die duplicate Klas verwyder word.
    """
    klasse = db.query(models.Klas).order_by(models.Klas.Klas_ID).all()
    groepe: dict[tuple, list[models.Klas]] = {}
    for klas in klasse:
        sleutel = _klas_duplikaat_sleutel(klas)
        if sleutel[1]:
            groepe.setdefault(sleutel, []).append(klas)

    duplikaat_groepe = [g for g in groepe.values() if len(g) > 1]
    preview = []
    totaal_verwyder = 0
    totaal_klas_groep = 0
    totaal_student_klas = 0
    totaal_personeel_klas = 0

    try:
        for duplikate in duplikaat_groepe:
            kanoniek = _kies_kanonieke_klas(duplikate)

            # Indien net een van die duplicates reeds 'n Lokasie_ID het, dra dit oor.
            lokasie_ids = {k.Lokasie_ID for k in duplikate if getattr(k, "Lokasie_ID", None)}
            if len(lokasie_ids) == 1 and not kanoniek.Lokasie_ID:
                kanoniek.Lokasie_ID = next(iter(lokasie_ids))

            skoon_naam = re.sub(r"\s*\([^)]*\)\s*$", "", kanoniek.KLA_Lokaal or "").strip()
            if skoon_naam:
                kanoniek.KLA_Lokaal = skoon_naam

            verwyder_ids = [k.Klas_ID for k in duplikate if k.Klas_ID != kanoniek.Klas_ID]
            preview.append({
                "Kanonieke_Klas_ID": kanoniek.Klas_ID,
                "Module_ID": kanoniek.Module_ID,
                "KLA_Lokaal": kanoniek.KLA_Lokaal,
                "KLA_Dag": kanoniek.KLA_Dag,
                "KLA_Begin_Tyd": kanoniek.KLA_Begin_Tyd,
                "KLA_Eind_Tyd": kanoniek.KLA_Eind_Tyd,
                "Lokasie_ID": kanoniek.Lokasie_ID,
                "Verwyder_Klas_IDs": verwyder_ids,
            })

            if not data.bevestig:
                continue

            for oud in duplikate:
                if oud.Klas_ID == kanoniek.Klas_ID:
                    continue
                totaal_klas_groep += _skuif_klas_koppeling(
                    db, models.Klas_Groep, "Groep_ID", oud.Klas_ID, kanoniek.Klas_ID
                )
                totaal_student_klas += _skuif_klas_koppeling(
                    db, models.Student_Klas, "Gebruiker_ID", oud.Klas_ID, kanoniek.Klas_ID
                )
                totaal_personeel_klas += _skuif_klas_koppeling(
                    db, models.Personeel_Klas, "Gebruiker_ID", oud.Klas_ID, kanoniek.Klas_ID
                )
                db.flush()
                db.delete(oud)
                totaal_verwyder += 1

        if data.bevestig:
            db.commit()
        else:
            db.rollback()  # Preview mag geen naam/Lokasie verandering behou nie.
    except Exception:
        db.rollback()
        raise

    return schemas.APIResponse(
        sukses=True,
        data={
            "Preview": not data.bevestig,
            "Duplikaat_Groepe": len(duplikaat_groepe),
            "Klasse_Saamgevoeg": totaal_verwyder,
            "Klas_Groep_Koppelings_Verwerk": totaal_klas_groep,
            "Student_Klas_Koppelings_Verwerk": totaal_student_klas,
            "Personeel_Klas_Koppelings_Verwerk": totaal_personeel_klas,
            "Groep_Detail": preview,
        },
    )


@router.post("/lokaal-koppelings")
def stoor_rooster_lokaal_koppeling(
    data: schemas.RoosterLokaalKoppelingUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    bron_lokaal = data.KLA_Lokaal.strip()
    if not bron_lokaal:
        raise HTTPException(status_code=400, detail="Lantiv-lokaal is verpligtend")

    mapping = db.query(models.Rooster_Lokaal_Koppeling).filter(
        models.Rooster_Lokaal_Koppeling.KLA_Lokaal == bron_lokaal
    ).first()

    if data.Lokasie_ID is None:
        if mapping:
            db.delete(mapping)
        verander = (
            db.query(models.Klas)
            .filter(models.Klas.KLA_Lokaal == bron_lokaal)
            .update({models.Klas.Lokasie_ID: None}, synchronize_session=False)
        )
        db.commit()
        return schemas.APIResponse(
            sukses=True,
            data={
                "KLA_Lokaal": bron_lokaal,
                "Lokasie_ID": None,
                "Gekoppel": False,
                "Klasse_Bygewerk": int(verander or 0),
            },
        )

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Lokasie_ID == data.Lokasie_ID
    ).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="MOON-lokaal nie gevind nie")
    if str(lokasie.LOK_Tipe or "").strip().casefold() != "klaskamer":
        raise HTTPException(status_code=400, detail="Jy kan net 'n Klaskamer-lokasie aan 'n roosterlokaal koppel")

    if mapping:
        mapping.Lokasie_ID = lokasie.Lokasie_ID
        mapping.Gewysig_Op = datetime.utcnow()
    else:
        mapping = models.Rooster_Lokaal_Koppeling(
            KLA_Lokaal=bron_lokaal,
            Lokasie_ID=lokasie.Lokasie_ID,
        )
        db.add(mapping)

    verander = (
        db.query(models.Klas)
        .filter(models.Klas.KLA_Lokaal == bron_lokaal)
        .update({models.Klas.Lokasie_ID: lokasie.Lokasie_ID}, synchronize_session=False)
    )
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={
            "KLA_Lokaal": bron_lokaal,
            "Lokasie_ID": lokasie.Lokasie_ID,
            "LOK_Naam": lokasie.LOK_Naam,
            "Kampus_ID": lokasie.Kampus_ID,
            "NFC_UID": _aktiewe_lokasie_nfc_uid(lokasie),
            "Gekoppel": True,
            "Klasse_Bygewerk": int(verander or 0),
        },
    )


# --- SKEP-EINDPUNTE (admin) ---

@router.post("/modules")
def skep_module(
    data: schemas.ModuleCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    bestaande = db.query(models.Module).filter(models.Module.MOD_Kode == data.MOD_Kode).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Module bestaan reeds")
    module = models.Module(MOD_Kode=data.MOD_Kode, MOD_Naam=data.MOD_Naam)
    db.add(module)
    db.commit()
    db.refresh(module)
    return schemas.APIResponse(
        sukses=True,
        data={"Module_ID": module.Module_ID, "MOD_Kode": module.MOD_Kode, "MOD_Naam": module.MOD_Naam},
    )


@router.post("/groepe")
def skep_groep(
    data: schemas.GroepCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    bestaande = db.query(models.Groep).filter(models.Groep.GRO_Naam == data.GRO_Naam).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Groep bestaan reeds")
    groep = models.Groep(GRO_Naam=data.GRO_Naam)
    db.add(groep)
    db.commit()
    db.refresh(groep)
    return schemas.APIResponse(
        sukses=True,
        data={"Groep_ID": groep.Groep_ID, "GRO_Naam": groep.GRO_Naam},
    )


@router.post("/klasse")
def skep_klas(
    data: schemas.KlasCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    module = db.query(models.Module).filter(models.Module.Module_ID == data.Module_ID).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module nie gevind nie")
    lokasie_id = data.Lokasie_ID
    if lokasie_id is not None:
        lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
        if not lokasie or str(lokasie.LOK_Tipe or "").casefold() != "klaskamer":
            raise HTTPException(status_code=400, detail="Lokasie_ID moet na 'n geldige Klaskamer-lokasie verwys")
    else:
        lokasie = _vind_klaskamer_lokasie(db, data.KLA_Lokaal)
        lokasie_id = lokasie.Lokasie_ID if lokasie else None
    klas = models.Klas(
        Module_ID=data.Module_ID,
        Lokasie_ID=lokasie_id,
        KLA_Lokaal=data.KLA_Lokaal,
        KLA_Dag=data.KLA_Dag,
        KLA_Begin_Tyd=data.KLA_Begin_Tyd,
        KLA_Eind_Tyd=data.KLA_Eind_Tyd,
    )
    db.add(klas)
    db.commit()
    db.refresh(klas)
    return schemas.APIResponse(sukses=True, data=_klas_na_dict(klas))



@router.delete("/klasse/{klas_id}")
def verwyder_klas(
    klas_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Verwyder 'n roosterklas veilig nadat direkte Klas_ID-koppelings skoongemaak is."""
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == klas_id).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")

    klas_groep_aantal = (
        db.query(models.Klas_Groep)
        .filter(models.Klas_Groep.Klas_ID == klas_id)
        .delete(synchronize_session=False)
    )
    student_klas_aantal = (
        db.query(models.Student_Klas)
        .filter(models.Student_Klas.Klas_ID == klas_id)
        .delete(synchronize_session=False)
    )
    personeel_klas_aantal = (
        db.query(models.Personeel_Klas)
        .filter(models.Personeel_Klas.Klas_ID == klas_id)
        .delete(synchronize_session=False)
    )

    detail = _klas_na_dict(klas)
    db.delete(klas)
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={
            "Verwyder": True,
            "Klas_ID": klas_id,
            "Klas": detail,
            "Klas_Groep_Koppelings_Verwyder": int(klas_groep_aantal or 0),
            "Student_Klas_Koppelings_Verwyder": int(student_klas_aantal or 0),
            "Personeel_Klas_Koppelings_Verwyder": int(personeel_klas_aantal or 0),
        },
    )


@router.put("/klasse/{klas_id}/lokasie")
def koppel_lokasie_aan_roosterklas(
    klas_id: int,
    data: schemas.KlasLokasieAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Bind 'n rooster-Klas_ID aan die fisiese Klaskamer/NFC-lokasie."""
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == klas_id).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")
    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == data.Lokasie_ID).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokasie nie gevind nie")
    if str(lokasie.LOK_Tipe or "").strip().casefold() != "klaskamer":
        raise HTTPException(status_code=400, detail="Net 'n Klaskamer-lokasie kan aan 'n roosterklas gekoppel word")
    klas.Lokasie_ID = lokasie.Lokasie_ID
    db.commit()
    db.refresh(klas)
    return schemas.APIResponse(sukses=True, data=_klas_na_dict(klas))


@router.post("/klasse/{klas_id}/groepe")
def koppel_groep_aan_klas(
    klas_id: int,
    data: schemas.KlasGroepAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == klas_id).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")
    groep = db.query(models.Groep).filter(models.Groep.Groep_ID == data.Groep_ID).first()
    if not groep:
        raise HTTPException(status_code=404, detail="Groep nie gevind nie")
    bestaande = db.query(models.Klas_Groep).filter(
        models.Klas_Groep.Klas_ID == klas_id,
        models.Klas_Groep.Groep_ID == data.Groep_ID,
    ).first()
    if not bestaande:
        db.add(models.Klas_Groep(Klas_ID=klas_id, Groep_ID=data.Groep_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Klas_ID": klas_id, "Groep_ID": data.Groep_ID})


# --- STUDENT-TOEWYSING (admin) ---

@router.post("/studente/{gebruiker_id}/groepe")
def ken_student_groep_toe(
    gebruiker_id: int,
    data: schemas.StudentGroepAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == gebruiker_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    groep = db.query(models.Groep).filter(models.Groep.Groep_ID == data.Groep_ID).first()
    if not groep:
        raise HTTPException(status_code=404, detail="Groep nie gevind nie")
    bestaande = db.query(models.Student_Groep).filter(
        models.Student_Groep.Gebruiker_ID == gebruiker_id,
        models.Student_Groep.Groep_ID == data.Groep_ID,
    ).first()
    if not bestaande:
        db.add(models.Student_Groep(Gebruiker_ID=gebruiker_id, Groep_ID=data.Groep_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Groep_ID": data.Groep_ID})


@router.post("/studente/{gebruiker_id}/modules")
def ken_student_module_toe(
    gebruiker_id: int,
    data: schemas.StudentModuleAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == gebruiker_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    module = db.query(models.Module).filter(models.Module.Module_ID == data.Module_ID).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module nie gevind nie")
    bestaande = db.query(models.Student_Module).filter(
        models.Student_Module.Gebruiker_ID == gebruiker_id,
        models.Student_Module.Module_ID == data.Module_ID,
    ).first()
    if not bestaande:
        db.add(models.Student_Module(Gebruiker_ID=gebruiker_id, Module_ID=data.Module_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Module_ID": data.Module_ID})


@router.post("/studente/{gebruiker_id}/klasse")
def ken_student_klas_toe(
    gebruiker_id: int,
    data: schemas.StudentKlasAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == gebruiker_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == data.Klas_ID).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")
    bestaande = db.query(models.Student_Klas).filter(
        models.Student_Klas.Gebruiker_ID == gebruiker_id,
        models.Student_Klas.Klas_ID == data.Klas_ID,
    ).first()
    if not bestaande:
        db.add(models.Student_Klas(Gebruiker_ID=gebruiker_id, Klas_ID=data.Klas_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Klas_ID": data.Klas_ID})


# --- PERSONEEL-TOEWYSING (admin) ---

@router.get("/studente-toewysings")
def lys_student_toewysings(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Alle student-groep- en student-module-toewysings (vir die admin-skerm)."""
    groep_rye = (
        db.query(models.Student_Groep, models.Groep)
        .join(models.Groep, models.Groep.Groep_ID == models.Student_Groep.Groep_ID)
        .order_by(models.Student_Groep.Gebruiker_ID, models.Groep.GRO_Naam)
        .all()
    )
    module_rye = (
        db.query(models.Student_Module, models.Module)
        .join(models.Module, models.Module.Module_ID == models.Student_Module.Module_ID)
        .order_by(models.Student_Module.Gebruiker_ID, models.Module.MOD_Kode)
        .all()
    )
    return schemas.APIResponse(
        sukses=True,
        data={
            "groepe": [
                {"Gebruiker_ID": sg.Gebruiker_ID, "Groep_ID": g.Groep_ID, "GRO_Naam": g.GRO_Naam}
                for sg, g in groep_rye
            ],
            "modules": [
                {
                    "Gebruiker_ID": sm.Gebruiker_ID,
                    "Module_ID": m.Module_ID,
                    "MOD_Kode": m.MOD_Kode,
                    "MOD_Naam": m.MOD_Naam,
                }
                for sm, m in module_rye
            ],
        },
    )


@router.delete("/studente/{gebruiker_id}/groepe/{groep_id}")
def verwyder_student_groep(
    gebruiker_id: int,
    groep_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    koppeling = db.query(models.Student_Groep).filter(
        models.Student_Groep.Gebruiker_ID == gebruiker_id,
        models.Student_Groep.Groep_ID == groep_id,
    ).first()
    if not koppeling:
        raise HTTPException(status_code=404, detail="Toewysing nie gevind nie")
    db.delete(koppeling)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Groep_ID": groep_id})


@router.delete("/studente/{gebruiker_id}/modules/{module_id}")
def verwyder_student_module(
    gebruiker_id: int,
    module_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    koppeling = db.query(models.Student_Module).filter(
        models.Student_Module.Gebruiker_ID == gebruiker_id,
        models.Student_Module.Module_ID == module_id,
    ).first()
    if not koppeling:
        raise HTTPException(status_code=404, detail="Toewysing nie gevind nie")
    db.delete(koppeling)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Module_ID": module_id})


@router.post("/personeel/{gebruiker_id}/modules")
def ken_personeel_module_toe(
    gebruiker_id: int,
    data: schemas.PersoneelModuleAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == gebruiker_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    module = db.query(models.Module).filter(models.Module.Module_ID == data.Module_ID).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module nie gevind nie")
    bestaande = db.query(models.Personeel_Module).filter(
        models.Personeel_Module.Gebruiker_ID == gebruiker_id,
        models.Personeel_Module.Module_ID == data.Module_ID,
    ).first()
    if not bestaande:
        db.add(models.Personeel_Module(Gebruiker_ID=gebruiker_id, Module_ID=data.Module_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Module_ID": data.Module_ID})


@router.get("/personeel-modules")
def lys_personeel_modules(
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Alle dosent-module-toewysings in een lys (vir die admin-skerm)."""
    rye = (
        db.query(models.Personeel_Module, models.Module)
        .join(models.Module, models.Module.Module_ID == models.Personeel_Module.Module_ID)
        .order_by(models.Personeel_Module.Gebruiker_ID, models.Module.MOD_Kode)
        .all()
    )
    return schemas.APIResponse(
        sukses=True,
        data=[
            {
                "Gebruiker_ID": pm.Gebruiker_ID,
                "Module_ID": m.Module_ID,
                "MOD_Kode": m.MOD_Kode,
                "MOD_Naam": m.MOD_Naam,
            }
            for pm, m in rye
        ],
    )


@router.delete("/personeel/{gebruiker_id}/modules/{module_id}")
def verwyder_personeel_module(
    gebruiker_id: int,
    module_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Haal 'n module van 'n personeellid af (verwyder die toewysing)."""
    koppeling = db.query(models.Personeel_Module).filter(
        models.Personeel_Module.Gebruiker_ID == gebruiker_id,
        models.Personeel_Module.Module_ID == module_id,
    ).first()
    if not koppeling:
        raise HTTPException(status_code=404, detail="Toewysing nie gevind nie")
    db.delete(koppeling)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Module_ID": module_id})


@router.post("/personeel/{gebruiker_id}/klasse")
def ken_personeel_klas_toe(
    gebruiker_id: int,
    data: schemas.PersoneelKlasAssign,
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == gebruiker_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == data.Klas_ID).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")
    bestaande = db.query(models.Personeel_Klas).filter(
        models.Personeel_Klas.Gebruiker_ID == gebruiker_id,
        models.Personeel_Klas.Klas_ID == data.Klas_ID,
    ).first()
    if not bestaande:
        db.add(models.Personeel_Klas(Gebruiker_ID=gebruiker_id, Klas_ID=data.Klas_ID))
        db.commit()
    return schemas.APIResponse(sukses=True, data={"Gebruiker_ID": gebruiker_id, "Klas_ID": data.Klas_ID})


@router.get("/studente/my-koshuis-status")
def kry_my_koshuis_status(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Gee slegs die aangemelde student se eie koshuis-IN/UIT status.

    Nie-koshuisstudente kry ``is_koshuis_student = False`` en die Flutter UI
    wys dan glad nie 'n Koshuis-kaart nie.  Vir 'n koshuisstudent word die
    jongste IN/UIT log NET by sy/haar toegewysde koshuis se Lokasie_ID gelees,
    sodat kampus- of klaskamerskanderings nooit die koshuisstatus kan verander nie.
    """
    student = (
        db.query(models.Student)
        .filter(models.Student.Gebruiker_ID == current_user.Gebruiker_ID)
        .first()
    )
    if not student:
        raise HTTPException(status_code=403, detail="Net studente het 'n koshuisstatus")

    if not bool(student.STU_Is_Koshuis) or not student.Koshuis_ID:
        return schemas.APIResponse(
            sukses=True,
            data={
                "is_koshuis_student": False,
                "koshuis_id": None,
                "koshuis_naam": None,
                "status": None,
                "laaste_scan": None,
            },
        )

    koshuis = (
        db.query(models.Koshuis)
        .filter(models.Koshuis.Koshuis_ID == student.Koshuis_ID)
        .first()
    )
    if not koshuis:
        return schemas.APIResponse(
            sukses=True,
            data={
                "is_koshuis_student": True,
                "koshuis_id": student.Koshuis_ID,
                "koshuis_naam": "Onbekende koshuis",
                "status": "ONBEKEND",
                "lokasie_gekoppel": False,
                "laaste_scan": None,
            },
        )

    lokasie = (
        db.query(models.Lokasie)
        .filter(
            models.Lokasie.Kampus_ID == koshuis.Kampus_ID,
            func.lower(models.Lokasie.LOK_Tipe) == "koshuis",
            models.Lokasie.LOK_Naam == koshuis.KOS_Naam,
        )
        .first()
    )

    if not lokasie:
        return schemas.APIResponse(
            sukses=True,
            data={
                "is_koshuis_student": True,
                "koshuis_id": koshuis.Koshuis_ID,
                "koshuis_naam": koshuis.KOS_Naam,
                "status": "ONBEKEND",
                "lokasie_gekoppel": False,
                "laaste_scan": None,
            },
        )

    laaste_log = (
        db.query(models.ToegangsLogs)
        .filter(
            models.ToegangsLogs.Gebruiker_ID == current_user.Gebruiker_ID,
            models.ToegangsLogs.Lokasie_ID == lokasie.Lokasie_ID,
            models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
        )
        .order_by(
            models.ToegangsLogs.TOE_Tydstempel.desc(),
            models.ToegangsLogs.Log_ID.desc(),
        )
        .first()
    )

    laaste_scan = None
    status = "NOG_NIE_GESCAN"
    if laaste_log:
        status = laaste_log.TOE_Rigting
        laaste_scan = {
            "log_id": laaste_log.Log_ID,
            "lokasie_id": lokasie.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam,
            "rigting": laaste_log.TOE_Rigting,
            "metode": laaste_log.TOE_Metode,
            "tyd": (
                laaste_log.TOE_Tydstempel.isoformat()
                if laaste_log.TOE_Tydstempel
                else None
            ),
        }

    return schemas.APIResponse(
        sukses=True,
        data={
            "is_koshuis_student": True,
            "koshuis_id": koshuis.Koshuis_ID,
            "koshuis_naam": koshuis.KOS_Naam,
            "status": status,
            "lokasie_gekoppel": True,
            "laaste_scan": laaste_scan,
        },
    )


class StudentKlasNfcValideerRequest(BaseModel):
    nfc_uid: str


def bepaal_huidige_klas_vir_nfc(db: Session, current_user: models.Gebruikers, nfc_uid: str) -> dict:
    """Los 'n klaskamer-tag op na die student se klas wat nou in daardie lokaal is.

    Die backend, nie die foon nie, besluit op grond van SA-tyd en Lokasie_ID.
    Gooi HTTPException (403/404/409) as die student nie nou 'n klas daar het nie.
    Word deur die valideer-stap én deur /student/scan-klas gebruik (MOON-SEC-006),
    sodat bywoning nie sonder 'n geldige roosterklas aangeteken kan word nie.
    """
    student = (
        db.query(models.Student)
        .filter(models.Student.Gebruiker_ID == current_user.Gebruiker_ID)
        .first()
    )
    if not student:
        raise HTTPException(status_code=403, detail="Net studente kan klas-NFC valideer")

    tag = _vind_aktiewe_nfc_tag(db, nfc_uid)
    if not tag or not tag.Lokasie_ID:
        raise HTTPException(status_code=404, detail="Geen lokaal vir hierdie NFC-etiket gevind nie")

    lokasie = (
        db.query(models.Lokasie)
        .filter(models.Lokasie.Lokasie_ID == tag.Lokasie_ID)
        .first()
    )
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

    nou = datetime.now(_SA_TZ)
    vandag = nou.date()
    rooster = resolver_student_rooster(db, current_user.Gebruiker_ID)

    huidige_klasse: list[models.Klas] = []
    for item in rooster:
        klas_id = item.get("Klas_ID")
        if not klas_id:
            continue
        klas = (
            db.query(models.Klas)
            .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
            .filter(models.Klas.Klas_ID == klas_id)
            .first()
        )
        if klas is None or not _klas_dag_match(klas, vandag):
            continue
        begin_local, eind_local, _, _ = _klas_scan_venster(klas, vandag)
        if begin_local <= nou < eind_local:
            huidige_klasse.append(klas)

    if not huidige_klasse:
        raise HTTPException(
            status_code=409,
            detail="Jy het nie tans 'n geskeduleerde klas om in te skandeer nie",
        )

    vir_lokaal = [
        klas for klas in huidige_klasse
        if getattr(klas, "Lokasie_ID", None) == tag.Lokasie_ID
    ]
    if not vir_lokaal:
        verwag = ", ".join(
            sorted({
                (klas.lokasie.LOK_Naam if getattr(klas, "lokasie", None) else klas.KLA_Lokaal)
                for klas in huidige_klasse
            })
        )
        raise HTTPException(
            status_code=409,
            detail=f"Verkeerde lokaal. Jou huidige klas is in: {verwag}",
        )

    return {"student": student, "tag": tag, "lokasie": lokasie, "klas": vir_lokaal[0], "nou": nou}


@router.post("/studente/klas-nfc/valideer")
def valideer_student_klas_nfc(
    data: StudentKlasNfcValideerRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Valideer 'n fisiese klaskamer-tag teen die student se huidige roosterklas.

    Geen ToegangsLogs word hier geskryf nie; dit is net die fail-closed pre-check.
    """
    r = bepaal_huidige_klas_vir_nfc(db, current_user, data.nfc_uid)
    return schemas.APIResponse(
        sukses=True,
        data={
            "NFC_UID": r["tag"].NFC_UID,
            "Lokasie_ID": r["tag"].Lokasie_ID,
            "LOK_Naam": r["lokasie"].LOK_Naam,
            "Klas": _klas_na_dict(r["klas"]),
            "Bediener_Tyd": r["nou"].isoformat(),
        },
    )


# --- ROOSTER-LEES (eie + admin) ---

@router.get("/studente/{gebruiker_id}/rooster")
def student_rooster(
    gebruiker_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    if current_user.Gebruiker_ID != gebruiker_id:
        # Nie-admin mag net hul eie rooster sien.
        rolle = list(getattr(request.state, "roles", []) or [])
        if "Administrateur" not in rolle:
            raise HTTPException(status_code=403, detail="Jy mag net jou eie rooster sien")
    rooster = resolver_student_rooster(db, gebruiker_id)
    return schemas.APIResponse(sukses=True, data=rooster)


@router.get("/personeel/{gebruiker_id}/rooster")
def personeel_rooster(
    gebruiker_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    if current_user.Gebruiker_ID != gebruiker_id:
        rolle = list(getattr(request.state, "roles", []) or [])
        if "Administrateur" not in rolle:
            raise HTTPException(status_code=403, detail="Jy mag net jou eie rooster sien")
    rooster = resolver_personeel_rooster(db, gebruiker_id)
    return schemas.APIResponse(sukses=True, data=rooster)


def _require_klas_register_toegang(
    klas_id: int,
    request: Request,
    db: Session,
    current_user: models.Gebruikers,
) -> models.Klas:
    klas = (
        db.query(models.Klas)
        .options(joinedload(models.Klas.module), joinedload(models.Klas.lokasie))
        .filter(models.Klas.Klas_ID == klas_id)
        .first()
    )
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")
    rolle = list(getattr(request.state, "roles", []) or [])
    if "Administrateur" not in rolle:
        eie_rooster = resolver_personeel_rooster(db, current_user.Gebruiker_ID)
        if not any(k["Klas_ID"] == klas_id for k in eie_rooster):
            raise HTTPException(status_code=403, detail="Jy mag net jou eie klasse se register sien")
    return klas


@router.get("/klasse/{klas_id}/studente")
def klas_studente(
    klas_id: int,
    request: Request,
    datum: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Klasregister met huidige klas-spesifieke NFC-status per student."""
    _require_klas_register_toegang(klas_id, request, db, current_user)
    dag = None
    if datum:
        try:
            dag = date.fromisoformat(datum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Ongeldige datum; gebruik JJJJ-MM-DD")
    return schemas.APIResponse(sukses=True, data=resolver_klas_studente(db, klas_id, dag))


@router.get("/klasse/{klas_id}/bywoning")
def klas_bywoning(
    klas_id: int,
    request: Request,
    datum: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Refresh-vriendelike bywoning vir een geskeduleerde klas/NFC-lokasie."""
    klas = _require_klas_register_toegang(klas_id, request, db, current_user)
    if datum:
        try:
            dag = date.fromisoformat(datum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Ongeldige datum; gebruik JJJJ-MM-DD")
    else:
        dag = datetime.now(_SA_TZ).date()

    gebruiker_ids = _klas_roster_gebruiker_ids(db, klas)
    studente = resolver_klas_studente(db, klas_id, dag)
    _, venster = _klas_scan_statusse(db, klas, gebruiker_ids, dag)
    present = [s for s in studente if s["Teenwoordig"]]
    absent = [s for s in studente if not s["Teenwoordig"]]
    return schemas.APIResponse(
        sukses=True,
        data={
            "Klas": _klas_na_dict(klas),
            "Datum": dag.isoformat(),
            "Lokasie_Gekoppel": bool(getattr(klas, "Lokasie_ID", None)),
            "Scan_Venster": venster,
            "Total_Students": len(studente),
            "Present_Count": len(present),
            "Absent_Count": len(absent),
            "Present": present,
            "Absent": absent,
        },
    )


# --- CSV-INVOER (admin) ---

@router.post("/klasse/import")
async def importeer_klasse(
    lêer: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Voer die nuwe MOON-rooster CSV direk in.

    Flow per ry:
    MOON CSV -> lokaal+kampus vind -> module kry/skep -> bestaande klas
    hergebruik of skep -> Lokasie_ID direk stel -> groep kry/skep ->
    Klas_Groep koppel.

    Hierdie nuwe importpad gebruik nie ``parse_lantiv_csv`` of
    ``Rooster_Lokaal_Koppeling`` nie. Die ou helpers/endpoints bly egter in
    plek vir backwards compatibility met bestaande data en admin-skerms.
    """
    inhoud = (await lêer.read()).decode("utf-8-sig", errors="replace")
    reëls = parse_moon_rooster_csv(inhoud)

    resultaat = schemas.KlasImportResult()
    geskep_module_kodes: set[str] = set()
    geskep_groep_name: set[str] = set()

    for ry in reëls:
        ry_nr = ry["ry"]
        try:
            module_kode = ry["module"]
            if not module_kode:
                raise ValueError("Module is leeg")
            if not ry["dag"] or not ry["from"] or not ry["to"]:
                raise ValueError("Dag, Begin_Tyd en Eind_Tyd is verpligtend")
            if not ry["lokaal_naam"] or not ry["kampus"]:
                raise ValueError("Lokaal_Naam en Kampus is verpligtend")

            # Fail closed: 'n roosterklas moet 'n presiese MOON-lokasie hê,
            # want NFC/bywoning vertrou op die korrekte Lokasie_ID.
            lokasie = _vind_moon_klaskamer_lokasie(
                db,
                lokaal_naam=ry["lokaal_naam"],
                kampus_naam=ry["kampus"],
                lokaal_kode=ry["lokaal"],
            )
            if lokasie is None:
                raise ValueError(
                    "Geen unieke MOON-klaskamer gevind vir "
                    f"Lokaal_Naam='{ry['lokaal_naam']}', Kampus='{ry['kampus']}' "
                    f"(Lokaal='{ry['lokaal']}')"
                )

            module = (
                db.query(models.Module)
                .filter(func.lower(models.Module.MOD_Kode) == module_kode.lower())
                .first()
            )
            if not module:
                module = models.Module(MOD_Kode=module_kode)
                db.add(module)
                db.flush()
                if module_kode.casefold() not in geskep_module_kodes:
                    resultaat.modules_geskep += 1
                    geskep_module_kodes.add(module_kode.casefold())

            # Die identiteit van 'n klas is nou die werklike MOON-lokasie,
            # plus module/dag/tyd. Dit laat 'n ou reeds-gemapte klas hergebruik
            # selfs al verskil sy KLA_Lokaal-teks van die nuwe CSV.
            klas = (
                db.query(models.Klas)
                .filter(
                    models.Klas.Module_ID == module.Module_ID,
                    models.Klas.Lokasie_ID == lokasie.Lokasie_ID,
                    models.Klas.KLA_Dag == (ry["dag"] or None),
                    models.Klas.KLA_Begin_Tyd == (ry["from"] or None),
                    models.Klas.KLA_Eind_Tyd == (ry["to"] or None),
                )
                .first()
            )

            # Backwards-compatible fallback: 'n bestaande klas kan nog 'n
            # ou Lantiv-naam soos "GH117 A (50)" hê en nog geen Lokasie_ID nie.
            # Soek dus eers op module/dag/tyd en vergelyk die GENORMALISEERDE
            # lokaalnaam, sodat die nuwe CSV nie 'n tweede klas skep nie.
            if not klas:
                tyd_kandidate = (
                    db.query(models.Klas)
                    .filter(
                        models.Klas.Module_ID == module.Module_ID,
                        models.Klas.KLA_Dag == (ry["dag"] or None),
                        models.Klas.KLA_Begin_Tyd == (ry["from"] or None),
                        models.Klas.KLA_Eind_Tyd == (ry["to"] or None),
                    )
                    .all()
                )
                verlangde_lokaal = _normaliseer_lokaal_naam(
                    ry["lokaal"] or ry["lokaal_naam"]
                )
                matches = [
                    kandidaat for kandidaat in tyd_kandidate
                    if _normaliseer_lokaal_naam(kandidaat.KLA_Lokaal) == verlangde_lokaal
                ]
                if len(matches) == 1:
                    klas = matches[0]

            if not klas:
                klas = models.Klas(
                    Module_ID=module.Module_ID,
                    Lokasie_ID=lokasie.Lokasie_ID,
                    KLA_Lokaal=ry["lokaal"] or ry["lokaal_naam"] or None,
                    KLA_Dag=ry["dag"] or None,
                    KLA_Begin_Tyd=ry["from"] or None,
                    KLA_Eind_Tyd=ry["to"] or None,
                )
                db.add(klas)
                db.flush()
                resultaat.klasse_geskep += 1
            else:
                # Her-invoer herstel ook ou klasse wat nog nie direk gekoppel was nie
                # en skoon die ou kapasiteit-agtervoegsel uit KLA_Lokaal op.
                if klas.Lokasie_ID != lokasie.Lokasie_ID:
                    klas.Lokasie_ID = lokasie.Lokasie_ID
                nuwe_lokaal = ry["lokaal"] or ry["lokaal_naam"] or None
                if nuwe_lokaal and _normaliseer_lokaal_naam(klas.KLA_Lokaal) == _normaliseer_lokaal_naam(nuwe_lokaal):
                    klas.KLA_Lokaal = nuwe_lokaal

            # Koppel elke groep aan dieselfde klas sonder duplicate Klas_Groep-rye.
            groepe = [g.strip() for g in ry["groep"].replace(";", ",").split(",") if g.strip()]
            for gro_naam in groepe:
                groep = (
                    db.query(models.Groep)
                    .filter(func.lower(models.Groep.GRO_Naam) == gro_naam.lower())
                    .first()
                )
                if not groep:
                    groep = models.Groep(GRO_Naam=gro_naam)
                    db.add(groep)
                    db.flush()
                    if gro_naam.casefold() not in geskep_groep_name:
                        resultaat.groepe_geskep += 1
                        geskep_groep_name.add(gro_naam.casefold())

                bestaande = (
                    db.query(models.Klas_Groep)
                    .filter(
                        models.Klas_Groep.Klas_ID == klas.Klas_ID,
                        models.Klas_Groep.Groep_ID == groep.Groep_ID,
                    )
                    .first()
                )
                if not bestaande:
                    db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))

            # Elke ry onafhanklik, sodat een fout nie ander geldige rye terugrol nie.
            db.commit()
        except Exception as e:  # noqa: BLE001
            db.rollback()
            resultaat.foute.append(f"Ry {ry_nr}: {e}")

    return schemas.APIResponse(sukses=True, data=resultaat.model_dump())


@router.post("/studente/import")
async def importeer_student_toewysings(
    lêer: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: bool = Depends(auth.check_admin),
):
    """Grootmaat-toewysing van studente aan groepe en/of modules via CSV.

    Kop-ry met kolomme studentenommer (of epos), groep, module.  Meer as een
    groep/module per student word met ';' geskei.  Onbekende groepe word
    geskep (soos by die Lantiv-invoer); onbekende modules en studente word
    as foute gerapporteer.  Elke ry word onafhanklik gecommit.
    """
    inhoud = (await lêer.read()).decode("utf-8-sig", errors="replace")
    rye = parse_student_toewysing_csv(inhoud)

    resultaat = schemas.StudentToewysingImportResult()
    if not rye:
        resultaat.foute.append(
            "Geen rye gevind nie. Die kop-ry moet 'n 'studentenommer' (of 'epos') kolom hê, "
            "plus 'groep' en/of 'module'."
        )
        return schemas.APIResponse(sukses=True, data=resultaat.model_dump())

    geskep_groep_name: set[str] = set()

    for ry in rye:
        try:
            gebruiker = None
            if ry["student"]:
                student = (
                    db.query(models.Student)
                    .filter(func.lower(models.Student.STU_Nommer) == ry["student"].lower())
                    .first()
                )
                if student:
                    gebruiker = student.gebruiker
            if gebruiker is None and ry["epos"]:
                gebruiker = (
                    db.query(models.Gebruikers)
                    .filter(func.lower(models.Gebruikers.GEB_Epos) == ry["epos"].lower())
                    .first()
                )
            if gebruiker is None:
                resultaat.foute.append(
                    f"Ry {ry['ry']}: student '{ry['student'] or ry['epos']}' nie gevind nie"
                )
                continue

            for gro_naam in ry["groepe"]:
                groep = db.query(models.Groep).filter(models.Groep.GRO_Naam == gro_naam).first()
                if not groep:
                    groep = models.Groep(GRO_Naam=gro_naam)
                    db.add(groep)
                    db.flush()
                    if gro_naam not in geskep_groep_name:
                        resultaat.groepe_geskep += 1
                        geskep_groep_name.add(gro_naam)
                bestaande = db.query(models.Student_Groep).filter(
                    models.Student_Groep.Gebruiker_ID == gebruiker.Gebruiker_ID,
                    models.Student_Groep.Groep_ID == groep.Groep_ID,
                ).first()
                if not bestaande:
                    db.add(models.Student_Groep(Gebruiker_ID=gebruiker.Gebruiker_ID, Groep_ID=groep.Groep_ID))
                    resultaat.groep_koppelings += 1

            for mod_kode in ry["modules"]:
                module = db.query(models.Module).filter(func.lower(models.Module.MOD_Kode) == mod_kode.lower()).first()
                if not module:
                    resultaat.foute.append(f"Ry {ry['ry']}: module '{mod_kode}' bestaan nie (laai eers die rooster op)")
                    continue
                bestaande = db.query(models.Student_Module).filter(
                    models.Student_Module.Gebruiker_ID == gebruiker.Gebruiker_ID,
                    models.Student_Module.Module_ID == module.Module_ID,
                ).first()
                if not bestaande:
                    db.add(models.Student_Module(Gebruiker_ID=gebruiker.Gebruiker_ID, Module_ID=module.Module_ID))
                    resultaat.module_koppelings += 1

            db.commit()
            resultaat.studente_verwerk += 1
        except Exception as e:  # noqa: BLE001
            db.rollback()
            resultaat.foute.append(f"Ry {ry['ry']}: {e}")

    return schemas.APIResponse(sukses=True, data=resultaat.model_dump())
