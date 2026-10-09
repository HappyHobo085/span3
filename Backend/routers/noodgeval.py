"""MOON Noodgeval API — persistence + MQTT publishing."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas
from mqtt_service import publish_json, topic_for_campus


router = APIRouter(prefix="/noodgeval", tags=["Noodgeval"])


def _utcnow_naive() -> datetime:
    return datetime.utcnow()


def _current_role_names(db: Session, user: models.Gebruikers) -> set[str]:
    role_ids: set[int] = set()
    if getattr(user, "Rol_ID", None):
        role_ids.add(int(user.Rol_ID))

    extra = (
        db.query(models.GebruikersRolle.Rol_ID)
        .filter(models.GebruikersRolle.Gebruiker_ID == user.Gebruiker_ID)
        .all()
    )
    role_ids.update(int(row[0]) for row in extra)

    if not role_ids:
        return set()

    rows = (
        db.query(models.Rolle.ROL_Naam)
        .filter(models.Rolle.Rol_ID.in_(role_ids))
        .all()
    )
    return {str(row[0]) for row in rows}


def _require_sender_for_campus(db: Session, user: models.Gebruikers, kampus_id: int) -> None:
    roles = _current_role_names(db, user)

    if "Administrateur" in roles:
        return

    if "Kampus_Opsigter" not in roles:
        raise HTTPException(
            status_code=403,
            detail="Slegs 'n administrateur of kampusopsigter mag 'n noodgeval beheer.",
        )

    opsigter = (
        db.query(models.Kampus_Opsigter)
        .filter(models.Kampus_Opsigter.Gebruiker_ID == user.Gebruiker_ID)
        .first()
    )
    if not opsigter or opsigter.Kampus_ID != kampus_id:
        raise HTTPException(
            status_code=403,
            detail="Die kampusopsigter mag net noodgevalle vir sy/haar eie kampus beheer.",
        )


def _get_noodgeval(db: Session, noodgeval_id: int) -> models.Noodgeval:
    row = (
        db.query(models.Noodgeval)
        .filter(models.Noodgeval.Noodgeval_ID == noodgeval_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Noodgeval nie gevind nie.")
    return row


def _mqtt_payload(row: models.Noodgeval) -> dict:
    return {
        "boodskap_id": row.NOO_Boodskap_ID,
        "tipe": row.NOO_Tipe,
        "status": row.NOO_Status,
        "noodgeval_id": row.Noodgeval_ID,
        "kampus_id": row.Kampus_ID,
        "titel": row.NOO_Titel,
        "boodskap": row.NOO_Boodskap,
        "tyd": (
            row.NOO_Begin_Op.replace(tzinfo=timezone.utc).isoformat()
            if row.NOO_Begin_Op
            else datetime.now(timezone.utc).isoformat()
        ),
    }


def _publish_current_state(row: models.Noodgeval) -> dict:
    topic = topic_for_campus(row.Kampus_ID)
    payload = _mqtt_payload(row)
    publish_json(topic, payload, qos=1, retain=False)
    return {"topic": topic, "qos": 1, "retain": False, "boodskap": payload}


@router.post("/mqtt/toets", response_model=schemas.APIResponse[dict])
def mqtt_toets(
    payload: schemas.NoodgevalMqttToetsRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_sender_for_campus(db, current_user, payload.kampus_id)
    topic = topic_for_campus(payload.kampus_id)
    message = {
        "boodskap_id": str(uuid4()),
        "tipe": "TOETS",
        "status": "TOETS",
        "kampus_id": payload.kampus_id,
        "titel": payload.titel.strip(),
        "boodskap": payload.boodskap.strip(),
        "tyd": datetime.now(timezone.utc).isoformat(),
        "gestuur_deur_id": current_user.Gebruiker_ID,
    }
    try:
        publish_json(topic, message, qos=1, retain=False)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MQTT-bediener is nie beskikbaar nie: {exc}") from exc

    return schemas.APIResponse(
        sukses=True,
        data={"topic": topic, "qos": 1, "retain": False, "boodskap": message},
        fout=None,
    )


@router.post("", response_model=schemas.APIResponse[dict])
def skep_noodgeval(
    payload: schemas.NoodgevalCreateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_sender_for_campus(db, current_user, payload.kampus_id)

    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == payload.kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie.")

    existing = (
        db.query(models.Noodgeval)
        .filter(
            models.Noodgeval.Kampus_ID == payload.kampus_id,
            models.Noodgeval.NOO_Status == "AKTIEF",
        )
        .order_by(models.Noodgeval.NOO_Begin_Op.desc())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Daar is reeds 'n aktiewe noodgeval vir hierdie kampus (ID {existing.Noodgeval_ID}). Sluit dit eers.",
        )

    row = models.Noodgeval(
        Kampus_ID=payload.kampus_id,
        Geskep_Deur_ID=current_user.Gebruiker_ID,
        NOO_Tipe=payload.tipe.strip().upper(),
        NOO_Titel=payload.titel.strip(),
        NOO_Boodskap=payload.boodskap.strip(),
        NOO_Status="AKTIEF",
        NOO_Boodskap_ID=str(uuid4()),
        NOO_Begin_Op=_utcnow_naive(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    try:
        mqtt_result = _publish_current_state(row)
        row.NOO_Mqtt_Gestuur_Op = _utcnow_naive()
        db.commit()
        db.refresh(row)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Noodgeval ID {row.Noodgeval_ID} is gestoor, maar MQTT het misluk: {exc}. "
                "Gebruik /herstuur nadat die broker herstel is."
            ),
        ) from exc

    return schemas.APIResponse(
        sukses=True,
        data={"noodgeval": schemas.NoodgevalRead.model_validate(row).model_dump(), "mqtt": mqtt_result},
        fout=None,
    )


@router.post("/{noodgeval_id}/sluit", response_model=schemas.APIResponse[dict])
def sluit_noodgeval(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    row = _get_noodgeval(db, noodgeval_id)
    _require_sender_for_campus(db, current_user, row.Kampus_ID)

    if row.NOO_Status == "GESLUIT":
        return schemas.APIResponse(
            sukses=True,
            data={"noodgeval": schemas.NoodgevalRead.model_validate(row).model_dump(), "reeds_gesluit": True},
            fout=None,
        )

    row.NOO_Status = "GESLUIT"
    row.Gesluit_Deur_ID = current_user.Gebruiker_ID
    row.NOO_Gesluit_Op = _utcnow_naive()
    db.commit()
    db.refresh(row)

    try:
        mqtt_result = _publish_current_state(row)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Noodgeval ID {row.Noodgeval_ID} is in die databasis gesluit, "
                f"maar die MQTT stop-boodskap het misluk: {exc}. Gebruik /herstuur."
            ),
        ) from exc

    return schemas.APIResponse(
        sukses=True,
        data={"noodgeval": schemas.NoodgevalRead.model_validate(row).model_dump(), "mqtt": mqtt_result},
        fout=None,
    )


@router.post("/{noodgeval_id}/herstuur", response_model=schemas.APIResponse[dict])
def herstuur_noodgeval_status(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    row = _get_noodgeval(db, noodgeval_id)
    _require_sender_for_campus(db, current_user, row.Kampus_ID)

    try:
        mqtt_result = _publish_current_state(row)
        if row.NOO_Status == "AKTIEF":
            row.NOO_Mqtt_Gestuur_Op = _utcnow_naive()
            db.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Herstuur via MQTT het misluk: {exc}") from exc

    return schemas.APIResponse(sukses=True, data=mqtt_result, fout=None)


@router.post("/{noodgeval_id}/ontvang", response_model=schemas.APIResponse[schemas.NoodgevalKennisnameRead])
def merk_ontvang(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _get_noodgeval(db, noodgeval_id)

    row = (
        db.query(models.NoodgevalKennisname)
        .filter(
            models.NoodgevalKennisname.Noodgeval_ID == noodgeval_id,
            models.NoodgevalKennisname.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    now = _utcnow_naive()

    if row is None:
        row = models.NoodgevalKennisname(
            Noodgeval_ID=noodgeval_id,
            Gebruiker_ID=current_user.Gebruiker_ID,
            NOK_Status="ONTVANG",
            NOK_Ontvang_Op=now,
        )
        db.add(row)
    elif row.NOK_Ontvang_Op is None:
        row.NOK_Ontvang_Op = now

    db.commit()
    db.refresh(row)
    return schemas.APIResponse(
        sukses=True,
        data=schemas.NoodgevalKennisnameRead.model_validate(row),
        fout=None,
    )


@router.post("/{noodgeval_id}/kennisname", response_model=schemas.APIResponse[schemas.NoodgevalKennisnameRead])
def kennisname(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    emergency = _get_noodgeval(db, noodgeval_id)
    if emergency.NOO_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie noodgeval is reeds gesluit.")

    row = (
        db.query(models.NoodgevalKennisname)
        .filter(
            models.NoodgevalKennisname.Noodgeval_ID == noodgeval_id,
            models.NoodgevalKennisname.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    now = _utcnow_naive()

    if row is None:
        row = models.NoodgevalKennisname(
            Noodgeval_ID=noodgeval_id,
            Gebruiker_ID=current_user.Gebruiker_ID,
            NOK_Status="KENNIS_GENEEM",
            NOK_Ontvang_Op=now,
            NOK_Kennis_Geneem_Op=now,
        )
        db.add(row)
    else:
        if row.NOK_Ontvang_Op is None:
            row.NOK_Ontvang_Op = now
        row.NOK_Status = "KENNIS_GENEEM"
        if row.NOK_Kennis_Geneem_Op is None:
            row.NOK_Kennis_Geneem_Op = now

    db.commit()
    db.refresh(row)
    return schemas.APIResponse(
        sukses=True,
        data=schemas.NoodgevalKennisnameRead.model_validate(row),
        fout=None,
    )




def _current_campus_presence(
    db: Session,
    user: models.Gebruikers,
) -> dict:
    """Bepaal die gebruiker se huidige kampus uit sy/haar jongste kampus-heklog.

    Slegs lokasies met LOK_Tipe='Kampus' tel. Die jongste heklog word oor ALLE
    kampusse bepaal, sodat 'n gebruiker nie gelyktydig op twee kampusse kan tel nie.
    Log_ID is die finale tie-breaker indien twee logs dieselfde timestamp het.
    """
    latest = (
        db.query(
            models.ToegangsLogs,
            models.Lokasie,
            models.Kampus,
        )
        .join(
            models.Lokasie,
            models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
        )
        .join(
            models.Kampus,
            models.Kampus.Kampus_ID == models.Lokasie.Kampus_ID,
        )
        .filter(
            models.ToegangsLogs.Gebruiker_ID == user.Gebruiker_ID,
            func.lower(models.Lokasie.LOK_Tipe) == "kampus",
        )
        .order_by(
            models.ToegangsLogs.TOE_Tydstempel.desc(),
            models.ToegangsLogs.Log_ID.desc(),
        )
        .first()
    )

    if latest is None:
        return {
            "op_kampus": False,
            "kampus_id": None,
            "kampus_naam": None,
            "laaste_rigting": None,
            "laaste_tyd": None,
            "laaste_log_id": None,
        }

    gate_log, lokasie, kampus = latest
    is_in = str(gate_log.TOE_Rigting or "").strip().upper() == "IN"

    return {
        "op_kampus": is_in,
        "kampus_id": kampus.Kampus_ID if is_in else None,
        "kampus_naam": kampus.KAM_Naam if is_in else None,
        "laaste_rigting": gate_log.TOE_Rigting,
        "laaste_tyd": (
            gate_log.TOE_Tydstempel.isoformat()
            if gate_log.TOE_Tydstempel is not None
            else None
        ),
        "laaste_log_id": gate_log.Log_ID,
    }


@router.get("/my-campus", response_model=schemas.APIResponse[dict])
def my_emergency_campus(
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Gee die kampus waarop die ingelogde gebruiker tans fisies ingeskandeer is."""
    return schemas.APIResponse(
        sukses=True,
        data=_current_campus_presence(db, current_user),
        fout=None,
    )


@router.get("/aktief", response_model=schemas.APIResponse[list[schemas.NoodgevalRead]])
def aktiewe_noodgevalle(
    kampus_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    q = db.query(models.Noodgeval).filter(models.Noodgeval.NOO_Status == "AKTIEF")
    if kampus_id is not None:
        q = q.filter(models.Noodgeval.Kampus_ID == kampus_id)
    rows = q.order_by(models.Noodgeval.NOO_Begin_Op.desc()).all()
    return schemas.APIResponse(
        sukses=True,
        data=[schemas.NoodgevalRead.model_validate(row) for row in rows],
        fout=None,
    )


@router.get("/{noodgeval_id}/opsomming", response_model=schemas.APIResponse[dict])
def noodgeval_opsomming(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    row = _get_noodgeval(db, noodgeval_id)
    _require_sender_for_campus(db, current_user, row.Kampus_ID)

    ontvang = (
        db.query(func.count(models.NoodgevalKennisname.Kennisname_ID))
        .filter(models.NoodgevalKennisname.Noodgeval_ID == noodgeval_id)
        .scalar()
        or 0
    )
    kennis = (
        db.query(func.count(models.NoodgevalKennisname.Kennisname_ID))
        .filter(
            models.NoodgevalKennisname.Noodgeval_ID == noodgeval_id,
            models.NoodgevalKennisname.NOK_Status == "KENNIS_GENEEM",
        )
        .scalar()
        or 0
    )

    return schemas.APIResponse(
        sukses=True,
        data={
            "noodgeval": schemas.NoodgevalRead.model_validate(row).model_dump(),
            "toestelle_wat_gerapporteer_het": int(ontvang),
            "kennis_geneem": int(kennis),
        },
        fout=None,
    )
