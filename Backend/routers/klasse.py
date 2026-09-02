"""Klas / Module / Groep rooster-roetes (admin-toewysing + CSV-invoer)."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

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


# --- ROOSTER RESOLUTION HELPERS ---

def _klas_na_dict(klas: models.Klas) -> dict:
    return {
        "Klas_ID": klas.Klas_ID,
        "Module_ID": klas.Module_ID,
        "MOD_Kode": klas.module.MOD_Kode if klas.module else None,
        "MOD_Naam": klas.module.MOD_Naam if klas.module else None,
        "KLA_Lokaal": klas.KLA_Lokaal,
        "KLA_Dag": klas.KLA_Dag,
        "KLA_Begin_Tyd": klas.KLA_Begin_Tyd,
        "KLA_Eind_Tyd": klas.KLA_Eind_Tyd,
    }


def resolver_student_rooster(db: Session, gebruiker_id: int) -> list[dict]:
    """Merg (dedupeer) die student se rooster uit 3 bronne."""
    gesien: set[int] = set()
    resultaat: list[dict] = []

    def voeg_by(klas: models.Klas):
        if klas is None or klas.Klas_ID in gesien:
            return
        gesien.add(klas.Klas_ID)
        resultaat.append(_klas_na_dict(klas))

    # 1. Groep-gebaseer (verstek): Student_Groep -> Klas_Groep -> Klas
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
        for (kid,) in klas_ids:
            voeg_by(db.query(models.Klas).filter(models.Klas.Klas_ID == kid).first())

    # 2. Module-inskrywing: Student_Module -> Klas
    module_ids = [
        m[0]
        for m in db.query(models.Student_Module.Module_ID)
        .filter(models.Student_Module.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if module_ids:
        for klas in (
            db.query(models.Klas)
            .filter(models.Klas.Module_ID.in_(module_ids))
            .all()
        ):
            voeg_by(klas)

    # 3. Direkte toewysing: Student_Klas -> Klas
    direkte_ids = [
        k[0]
        for k in db.query(models.Student_Klas.Klas_ID)
        .filter(models.Student_Klas.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if direkte_ids:
        for klas in (
            db.query(models.Klas)
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

    # 1. Module-inskrywing: Personeel_Module -> Klas
    module_ids = [
        m[0]
        for m in db.query(models.Personeel_Module.Module_ID)
        .filter(models.Personeel_Module.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if module_ids:
        for klas in (
            db.query(models.Klas)
            .filter(models.Klas.Module_ID.in_(module_ids))
            .all()
        ):
            voeg_by(klas)

    # 2. Direkte toewysing: Personeel_Klas -> Klas
    direkte_ids = [
        k[0]
        for k in db.query(models.Personeel_Klas.Klas_ID)
        .filter(models.Personeel_Klas.Gebruiker_ID == gebruiker_id)
        .all()
    ]
    if direkte_ids:
        for klas in (
            db.query(models.Klas)
            .filter(models.Klas.Klas_ID.in_(direkte_ids))
            .all()
        ):
            voeg_by(klas)

    return resultaat


def resolver_klas_studente(db: Session, klas_id: int) -> list[dict]:
    """Studente wat 'n spesifieke klas moet bywoon (gededupeer uit 3 bronne).

    Spieëlbeeld van resolver_student_rooster: groep-lidmaatskap via
    Klas_Groep -> Student_Groep, module-inskrywing via Student_Module op die
    klas se module, en direkte toewysing via Student_Klas.
    """
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == klas_id).first()
    if klas is None:
        return []

    gebruiker_ids: set[int] = set()

    # 1. Groep-gebaseer: Klas_Groep -> Student_Groep
    groep_ids = [
        g[0]
        for g in db.query(models.Klas_Groep.Groep_ID)
        .filter(models.Klas_Groep.Klas_ID == klas_id)
        .all()
    ]
    if groep_ids:
        for (gid,) in (
            db.query(models.Student_Groep.Gebruiker_ID)
            .filter(models.Student_Groep.Groep_ID.in_(groep_ids))
            .all()
        ):
            gebruiker_ids.add(gid)

    # 2. Module-inskrywing: Student_Module op die klas se module
    for (gid,) in (
        db.query(models.Student_Module.Gebruiker_ID)
        .filter(models.Student_Module.Module_ID == klas.Module_ID)
        .all()
    ):
        gebruiker_ids.add(gid)

    # 3. Direkte toewysing: Student_Klas
    for (gid,) in (
        db.query(models.Student_Klas.Gebruiker_ID)
        .filter(models.Student_Klas.Klas_ID == klas_id)
        .all()
    ):
        gebruiker_ids.add(gid)

    if not gebruiker_ids:
        return []

    rye = (
        db.query(models.Gebruikers, models.Student)
        .outerjoin(models.Student, models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
        .filter(models.Gebruikers.Gebruiker_ID.in_(gebruiker_ids))
        .order_by(models.Gebruikers.GEB_Van, models.Gebruikers.GEB_Naam)
        .all()
    )
    return [
        {
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "STU_Nommer": student.STU_Nommer if student else None,
        }
        for gebruiker, student in rye
    ]


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
    klasse = db.query(models.Klas).order_by(models.Klas.KLA_Dag).all()
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
    klas = models.Klas(
        Module_ID=data.Module_ID,
        KLA_Lokaal=data.KLA_Lokaal,
        KLA_Dag=data.KLA_Dag,
        KLA_Begin_Tyd=data.KLA_Begin_Tyd,
        KLA_Eind_Tyd=data.KLA_Eind_Tyd,
    )
    db.add(klas)
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


@router.get("/klasse/{klas_id}/studente")
def klas_studente(
    klas_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Klasregister: die studente wat hierdie klas moet bywoon.

    Admin sien enige klas; personeel sien net klasse op hul eie rooster.
    """
    klas = db.query(models.Klas).filter(models.Klas.Klas_ID == klas_id).first()
    if not klas:
        raise HTTPException(status_code=404, detail="Klas nie gevind nie")

    rolle = list(getattr(request.state, "roles", []) or [])
    if "Administrateur" not in rolle:
        eie_rooster = resolver_personeel_rooster(db, current_user.Gebruiker_ID)
        if not any(k["Klas_ID"] == klas_id for k in eie_rooster):
            raise HTTPException(status_code=403, detail="Jy mag net jou eie klasse se register sien")

    return schemas.APIResponse(sukses=True, data=resolver_klas_studente(db, klas_id))


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
