"""Dashboard, profile, and utility routes."""

import os
from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models, schemas, auth
from services.gebruiker_service import kies_primere_rol

router = APIRouter(tags=["Dashboard"])

UPLOAD_DIR = "uploads/profile_photos"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/rolle", response_model=schemas.APIResponse[List[schemas.Rol]])
def lees_rolle(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """Stuur 'n lys van alle rolle terug. Slegs Admin."""
    rolle = db.query(models.Rolle).all()
    return schemas.APIResponse(sukses=True, data=rolle)


@router.get("/me")
def kry_my_profiel(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    # Gebruik eager-loaded relasies (geen ekstra queries nodig nie)
    role_names = []
    for assignment in (current_user.gebruikers_rolle or []):
        if assignment.rol is not None:
            role_names.append(assignment.rol.ROL_Naam)
    if not role_names and current_user.rol is not None:
        role_names = [current_user.rol.ROL_Naam]

    return {
        "sukses": True,
        "data": {
            "gebruiker_id": current_user.Gebruiker_ID,
            "naam": current_user.GEB_Naam,
            "van": current_user.GEB_Van,
            "rol_id": current_user.Rol_ID,
            "rol": kies_primere_rol(role_names),
            "rol_namen": role_names,
            "epos": current_user.GEB_Epos,
            "selfoon": current_user.GEB_Selfoon_Nr,
            "foto_url": current_user.GEB_Profiel_Foto,
            "status": "Aktief" if current_user.Is_Aktief else "Onaktief",
            "student_nommer": current_user.student.STU_Nommer if current_user.student else None,
            "student_is_koshuis": current_user.student.STU_Is_Koshuis if current_user.student else False,
            "personeel_nommer": current_user.personeel.PER_Nommer if current_user.personeel else None,
            "departement": current_user.personeel.PER_Departement if current_user.personeel else None,
            "opsigter_nommer": current_user.kampus_opsigter.KAMO_Nommer if current_user.kampus_opsigter else None,
            "wag_nommer": current_user.sekuriteit_wag.SEK_Nommer if current_user.sekuriteit_wag else None,
            "kampus": None,
        },
    }


@router.post("/me/foto")
async def upload_my_profile_photo(
    file: UploadFile = File(...),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Slegs fotolêers word toegelaat")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Gebruik JPG, PNG of WEBP")

    filename = f"user_{current_user.Gebruiker_ID}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"Lêer te groot — maksimum {MAX_UPLOAD_BYTES // (1024*1024)} MB toegelaat")
    with open(file_path, "wb") as f:
        f.write(contents)

    foto_url = f"/uploads/profile_photos/{filename}"

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    gebruiker.GEB_Profiel_Foto = foto_url
    db.commit()
    db.refresh(gebruiker)

    return {"sukses": True, "data": {"foto_url": foto_url}}


@router.get("/dashboard")
def kry_my_dashboard(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    # Gebruik eager-loaded relasies (geen ekstra queries nodig nie)
    role_names = []
    for assignment in (current_user.gebruikers_rolle or []):
        if assignment.rol is not None:
            role_names.append(assignment.rol.ROL_Naam)
    if not role_names and current_user.rol is not None:
        role_names = [current_user.rol.ROL_Naam]

    def laaste_lokasie_log(lokasie_tipe: str, metode: str | None = None):
        """Kry die jongste IN/UIT-log vir 'n spesifieke fisiese lokasietipe.

        Belangrik: kampus/koshuis/klas word deur Lokasie.LOK_Tipe onderskei,
        nie deur QR/NFC nie. Dieselfde skandeermetode kan by verskillende
        fisiese plekke gebruik word.
        """
        query = (
            db.query(models.ToegangsLogs, models.Lokasie)
            .join(
                models.Lokasie,
                models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
            )
            .filter(
                models.ToegangsLogs.Gebruiker_ID == current_user.Gebruiker_ID,
                func.lower(models.Lokasie.LOK_Tipe) == lokasie_tipe.lower(),
                models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
            )
        )
        if metode is not None:
            query = query.filter(models.ToegangsLogs.TOE_Metode == metode)

        return (
            query
            .order_by(
                models.ToegangsLogs.TOE_Tydstempel.desc(),
                models.ToegangsLogs.Log_ID.desc(),
            )
            .first()
        )

    # Kampusstatus kom NET van 'n fisiese Kampus-lokasie.
    # 'n Koshuis QR/NFC of klas NFC kan dus nie meer OP KAMPUS verander nie.
    laaste_kampus_log = laaste_lokasie_log("kampus")

    # Laaste klas kom NET van 'n Klaskamer-lokasie en moet steeds 'n NFC-scan wees.
    laaste_klas_log = laaste_lokasie_log("klaskamer", metode="NFC")

    def log_to_dict(log_row):
        if not log_row:
            return None
        log, lokasie = log_row
        return {
            "log_id": log.Log_ID,
            "lokasie_id": log.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam if lokasie else "Onbekend",
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "tyd": log.TOE_Tydstempel.isoformat() if log.TOE_Tydstempel else None,
        }

    kampus_status = "ONBEKEND"
    if laaste_kampus_log:
        # laaste_kampus_log is 'n Row van (ToegangsLogs, Lokasie) — pak eers uit
        kampus_log = laaste_kampus_log[0]
        if kampus_log.TOE_Rigting == "IN":
            kampus_status = "OP_KAMPUS"
        elif kampus_log.TOE_Rigting == "UIT":
            kampus_status = "NIE_OP_KAMPUS"

    return {
        "sukses": True,
        "data": {
            "gebruiker_id": current_user.Gebruiker_ID,
            "naam": current_user.GEB_Naam,
            "van": current_user.GEB_Van,
            "rol": kies_primere_rol(role_names),
            "rol_namen": role_names,
            "kampus_status": kampus_status,
            "laaste_kampus": log_to_dict(laaste_kampus_log),
            "laaste_klas": log_to_dict(laaste_klas_log),
        },
    }


@router.get("/dashboard/live")
def dashboard_live(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    vandag = datetime.now(ZoneInfo("Africa/Johannesburg")).date()

    # Bepaal elke gebruiker se jongste KAMPUS-log only. Voorheen is die
    # jongste log oor alle lokasies gebruik; 'n Koshuis- of Klaskamer-log kon
    # daarom die kampustelling verkeerd verander.
    laaste_kampus_logs_subq = (
        db.query(
            models.ToegangsLogs.Gebruiker_ID,
            func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
        )
        .join(
            models.Lokasie,
            models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
        )
        .filter(
            func.lower(models.Lokasie.LOK_Tipe) == "kampus",
            models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
        )
        .group_by(models.ToegangsLogs.Gebruiker_ID)
        .subquery()
    )

    op_kampus_subq = (
        db.query(models.ToegangsLogs.Gebruiker_ID)
        .join(
            laaste_kampus_logs_subq,
            models.ToegangsLogs.Log_ID == laaste_kampus_logs_subq.c.max_log_id,
        )
        .filter(models.ToegangsLogs.TOE_Rigting == "IN")
        .subquery()
    )

    studente_op_kampus = (
        db.query(func.count(models.Student.Gebruiker_ID))
        .join(op_kampus_subq, models.Student.Gebruiker_ID == op_kampus_subq.c.Gebruiker_ID)
        .scalar()
    )

    personeel_op_kampus = (
        db.query(func.count(models.Personeel.Gebruiker_ID))
        .join(op_kampus_subq, models.Personeel.Gebruiker_ID == op_kampus_subq.c.Gebruiker_ID)
        .scalar()
    )

    dag_begin = datetime.combine(vandag, datetime.min.time())
    dag_einde = dag_begin + timedelta(days=1)
    toegange_vandag = (
        db.query(func.count(models.ToegangsLogs.Log_ID))
        .filter(
            models.ToegangsLogs.TOE_Tydstempel >= dag_begin,
            models.ToegangsLogs.TOE_Tydstempel < dag_einde,
            models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
        )
        .scalar()
    )

    return schemas.APIResponse(
        sukses=True,
        data={
            "studente_op_kampus": studente_op_kampus,
            "personeel_op_kampus": personeel_op_kampus,
            "besoekers_vandag": 0,
            "toegange_vandag": toegange_vandag,
        }
    )


@router.get("/lokasies/uid/{uid}")
def kry_lokasie_deur_uid(
    uid: str,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == uid.strip(),
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Geen lokaal vir hierdie NFC-etiket gevind nie")

    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == tag.Lokasie_ID).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

    return schemas.APIResponse(
        sukses=True,
        data={
            "Lokasie_ID": lokasie.Lokasie_ID,
            "LOK_Naam": lokasie.LOK_Naam,
            "Kampus_ID": lokasie.Kampus_ID,
            "NFC_UID": tag.NFC_UID
        }
    )


@router.get("/toegangslogs")
def lys_toegangslogs(
    skip: int = Query(0, ge=0, description="Aantal om oor te slaan"),
    limit: int = Query(50, ge=1, le=500, description="Maksimum aantal resultate"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    logs = db.query(models.ToegangsLogs)\
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    # Slaan die name van die gebruikers en lokasies in een slag op sodat die
    # Tuisblad se aktiwiteitslys name kan wys in plaas van net ID's.
    user_ids = {l.Gebruiker_ID for l in logs if l.Gebruiker_ID is not None}
    lok_ids = {l.Lokasie_ID for l in logs if l.Lokasie_ID is not None}
    gebruikers = {
        g.Gebruiker_ID: g
        for g in db.query(models.Gebruikers)
        .filter(models.Gebruikers.Gebruiker_ID.in_(user_ids)).all()
    } if user_ids else {}
    lokasies = {
        lok.Lokasie_ID: lok
        for lok in db.query(models.Lokasie)
        .filter(models.Lokasie.Lokasie_ID.in_(lok_ids)).all()
    } if lok_ids else {}

    def naam_van(l):
        g = gebruikers.get(l.Gebruiker_ID)
        return f"{g.GEB_Naam} {g.GEB_Van}".strip() if g else None

    def lokasie_naam(l):
        lok = lokasies.get(l.Lokasie_ID)
        return lok.LOK_Naam if lok else None

    return schemas.APIResponse(
        sukses=True,
        data=[
            {
                "Log_ID": l.Log_ID,
                "Gebruiker_ID": l.Gebruiker_ID,
                "Naam": naam_van(l),
                "Lokasie_ID": l.Lokasie_ID,
                "Lokasie": lokasie_naam(l),
                "Rigting": l.TOE_Rigting,
                "Metode": l.TOE_Metode,
                "Tyd": l.TOE_Tydstempel.isoformat(),
            }
            for l in logs
        ]
    )
