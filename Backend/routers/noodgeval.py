"""MOON Noodgeval — MQTT Step 1 test publisher."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas
from mqtt_service import publish_json, topic_for_campus


router = APIRouter(prefix="/noodgeval", tags=["Noodgeval"])


def _current_role_names(db: Session, user: models.Gebruikers) -> set[str]:
    """Resolve both legacy primary role and multi-role assignments."""
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


def _require_test_sender(db: Session, user: models.Gebruikers) -> None:
    roles = _current_role_names(db, user)
    if not roles.intersection({"Administrateur", "Kampus_Opsigter"}):
        raise HTTPException(
            status_code=403,
            detail="Slegs 'n Administrateur of Kampus Opsigter mag die MQTT-toets stuur.",
        )


@router.post("/mqtt/toets", response_model=schemas.APIResponse[dict])
def mqtt_toets(
    payload: schemas.NoodgevalMqttToetsRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """
    Step 1 only:
    publish a harmless MQTT test message to one campus topic.

    This does NOT create a real emergency record and does NOT start an alarm.
    """
    _require_test_sender(db, current_user)

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
        # QoS 1 = at least once. retain=False so an old TEST never triggers later.
        publish_json(topic, message, qos=1, retain=False)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"MQTT broker is nie beskikbaar nie: {exc}",
        ) from exc

    return schemas.APIResponse(
        sukses=True,
        data={
            "topic": topic,
            "qos": 1,
            "retain": False,
            "boodskap": message,
        },
        fout=None,
    )
