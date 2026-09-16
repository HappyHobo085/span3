"""Klas / Module / Groep rooster-roetes (admin-toewysing + CSV-invoer)."""

import csv
import io
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/rooster", tags=["Klas / Module / Groep"])


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


def _probeer_bind_klas_lokasie(db: Session, klas: models.Klas) -> bool:
    """Koppel 'n nog-ongekoppelde roosterklas outomaties wanneer lokaalnaam uniek match."""
    if getattr(klas, "Lokasie_ID", None):
        return False
    lokasie = _vind_klaskamer_lokasie(db, klas.KLA_Lokaal)
    if lokasie is None:
        return False
    klas.Lokasie_ID = lokasie.Lokasie_ID
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
            raise HTTPException(status_code=400, detail="Ongeldige datum; gebruik YYYY-MM-DD")
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
            raise HTTPException(status_code=400, detail="Ongeldige datum; gebruik YYYY-MM-DD")
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
    inhoud = (await lêer.read()).decode("utf-8-sig", errors="replace")
    reëls = parse_lantiv_csv(inhoud)

    resultaat = schemas.KlasImportResult()
    geskep_module_kodes: set[str] = set()
    geskep_groep_name: set[str] = set()

    for ry_nr, ry in enumerate(reëls, start=1):
        try:
            module_kode = ry["module"]
            if not module_kode:
                continue
            module = db.query(models.Module).filter(models.Module.MOD_Kode == module_kode).first()
            if not module:
                module = models.Module(MOD_Kode=module_kode)
                db.add(module)
                db.flush()
                if module_kode not in geskep_module_kodes:
                    resultaat.modules_geskep += 1
                    geskep_module_kodes.add(module_kode)

            # Hergebruik 'n bestaande klas met dieselfde module, lokaal, dag
            # en tye sodat her-invoer nie duplikate skep nie.
            klas = (
                db.query(models.Klas)
                .filter(
                    models.Klas.Module_ID == module.Module_ID,
                    models.Klas.KLA_Lokaal == (ry["lokaal"] or None),
                    models.Klas.KLA_Dag == (ry["dag"] or None),
                    models.Klas.KLA_Begin_Tyd == (ry["from"] or None),
                    models.Klas.KLA_Eind_Tyd == (ry["to"] or None),
                )
                .first()
            )
            if not klas:
                klas = models.Klas(
                    Module_ID=module.Module_ID,
                    KLA_Lokaal=ry["lokaal"] or None,
                    KLA_Dag=ry["dag"] or None,
                    KLA_Begin_Tyd=ry["from"] or None,
                    KLA_Eind_Tyd=ry["to"] or None,
                )
                db.add(klas)
                db.flush()
                resultaat.klasse_geskep += 1

            # Bind die roosterperiode outomaties aan die fisiese Klaskamer/NFC-lokasie
            # wanneer die lokaalnaam uniek match (bv. GH117 A en GH117 A (50)).
            _probeer_bind_klas_lokasie(db, klas)

            # Koppel elke groep (komma-geskei) aan die klas.
            groepe = [g.strip() for g in ry["groep"].split(",") if g.strip()]
            for gro_naam in groepe:
                groep = db.query(models.Groep).filter(models.Groep.GRO_Naam == gro_naam).first()
                if not groep:
                    groep = models.Groep(GRO_Naam=gro_naam)
                    db.add(groep)
                    db.flush()
                    if gro_naam not in geskep_groep_name:
                        resultaat.groepe_geskep += 1
                        geskep_groep_name.add(gro_naam)
                bestaande = db.query(models.Klas_Groep).filter(
                    models.Klas_Groep.Klas_ID == klas.Klas_ID,
                    models.Klas_Groep.Groep_ID == groep.Groep_ID,
                ).first()
                if not bestaande:
                    db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))

            # Elke ry word onafhanklik gecommit sodat 'n slegte ry nie
            # goeie rye se werk terugrol nie.
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
