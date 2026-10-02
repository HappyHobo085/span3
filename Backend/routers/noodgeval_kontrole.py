"""MOON Noodgeval Step 7 — Opsigter DAAR / NIE DAAR NIE verification.

This router stores the opsigter's manual emergency roll-call decision separately from
MQTT delivery/acknowledgement. That distinction is important:

* ONTVANG / KENNIS_GENEEM = what the person's phone reported.
* DAAR / NIE_DAAR = what the opsigter physically verified.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas
from routers.noodgeval import _get_noodgeval, _require_sender_for_campus


router = APIRouter(prefix="/noodgeval", tags=["Noodgeval Kontrole"])


def _utcnow_naive() -> datetime:
    return datetime.utcnow()


def _get_active_emergency_for_control(
    db: Session,
    noodgeval_id: int,
    current_user: models.Gebruikers,
) -> models.Noodgeval:
    emergency = _get_noodgeval(db, noodgeval_id)
    _require_sender_for_campus(db, current_user, emergency.Kampus_ID)
    if emergency.NOO_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie noodgeval is reeds gesluit.")
    return emergency


def _get_target_user(db: Session, gebruiker_id: int) -> models.Gebruikers:
    user = (
        db.query(models.Gebruikers)
        .filter(
            models.Gebruikers.Gebruiker_ID == gebruiker_id,
            models.Gebruikers.Is_Aktief.is_(True),
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Aktiewe gebruiker nie gevind nie.")
    return user


def _mark_status(
    *,
    db: Session,
    noodgeval_id: int,
    gebruiker_id: int,
    status: str,
    current_user: models.Gebruikers,
) -> dict:
    emergency = _get_active_emergency_for_control(db, noodgeval_id, current_user)
    target = _get_target_user(db, gebruiker_id)
    now = _utcnow_naive()

    row = db.execute(
        text('''
            INSERT INTO noodgeval_kontrole
                ("Noodgeval_ID", "Gebruiker_ID", "Gemerk_Deur_ID",
                 "NKK_Status", "NKK_Gemerk_Op", "Gewysig_Op")
            VALUES
                (:noodgeval_id, :gebruiker_id, :gemerk_deur_id,
                 :status, :nou, :nou)
            ON CONFLICT ("Noodgeval_ID", "Gebruiker_ID")
            DO UPDATE SET
                "Gemerk_Deur_ID" = EXCLUDED."Gemerk_Deur_ID",
                "NKK_Status" = EXCLUDED."NKK_Status",
                "NKK_Gemerk_Op" = EXCLUDED."NKK_Gemerk_Op",
                "Gewysig_Op" = EXCLUDED."Gewysig_Op"
            RETURNING
                "Kontrole_ID", "Noodgeval_ID", "Gebruiker_ID",
                "Gemerk_Deur_ID", "NKK_Status", "NKK_Gemerk_Op"
        '''),
        {
            "noodgeval_id": noodgeval_id,
            "gebruiker_id": gebruiker_id,
            "gemerk_deur_id": current_user.Gebruiker_ID,
            "status": status,
            "nou": now,
        },
    ).mappings().one()
    db.commit()

    return {
        **dict(row),
        "kampus_id": emergency.Kampus_ID,
        "volle_naam": f"{target.GEB_Naam} {target.GEB_Van}".strip(),
    }


@router.post("/{noodgeval_id}/kontrole/{gebruiker_id}/daar", response_model=schemas.APIResponse[dict])
def merk_daar(
    noodgeval_id: int,
    gebruiker_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Opsigter het die persoon fisies bevestig — remove from the working list."""
    result = _mark_status(
        db=db,
        noodgeval_id=noodgeval_id,
        gebruiker_id=gebruiker_id,
        status="DAAR",
        current_user=current_user,
    )
    return schemas.APIResponse(sukses=True, data=result, fout=None)


@router.post("/{noodgeval_id}/kontrole/{gebruiker_id}/nie-daar", response_model=schemas.APIResponse[dict])
def merk_nie_daar(
    noodgeval_id: int,
    gebruiker_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Opsigter could not physically find the person — move to the bottom list."""
    result = _mark_status(
        db=db,
        noodgeval_id=noodgeval_id,
        gebruiker_id=gebruiker_id,
        status="NIE_DAAR",
        current_user=current_user,
    )
    return schemas.APIResponse(sukses=True, data=result, fout=None)


@router.post("/{noodgeval_id}/kontrole/{gebruiker_id}/herstel", response_model=schemas.APIResponse[dict])
def herstel_kontrole(
    noodgeval_id: int,
    gebruiker_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Remove a manual decision so the person returns to the working list."""
    emergency = _get_active_emergency_for_control(db, noodgeval_id, current_user)
    _get_target_user(db, gebruiker_id)

    result = db.execute(
        text('''
            DELETE FROM noodgeval_kontrole
            WHERE "Noodgeval_ID" = :noodgeval_id
              AND "Gebruiker_ID" = :gebruiker_id
            RETURNING "Kontrole_ID"
        '''),
        {"noodgeval_id": noodgeval_id, "gebruiker_id": gebruiker_id},
    ).first()
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={
            "noodgeval_id": noodgeval_id,
            "kampus_id": emergency.Kampus_ID,
            "gebruiker_id": gebruiker_id,
            "herstel": True,
            "het_bestaan": result is not None,
        },
        fout=None,
    )


@router.get("/{noodgeval_id}/kontrole", response_model=schemas.APIResponse[list[dict]])
def lys_kontrole(
    noodgeval_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    emergency = _get_noodgeval(db, noodgeval_id)
    _require_sender_for_campus(db, current_user, emergency.Kampus_ID)

    rows = db.execute(
        text('''
            SELECT
                nk."Kontrole_ID",
                nk."Noodgeval_ID",
                nk."Gebruiker_ID",
                nk."Gemerk_Deur_ID",
                nk."NKK_Status",
                nk."NKK_Gemerk_Op",
                g."GEB_Naam",
                g."GEB_Van"
            FROM noodgeval_kontrole nk
            JOIN gebruikers g ON g."Gebruiker_ID" = nk."Gebruiker_ID"
            WHERE nk."Noodgeval_ID" = :noodgeval_id
            ORDER BY nk."NKK_Gemerk_Op" DESC, nk."Kontrole_ID" DESC
        '''),
        {"noodgeval_id": noodgeval_id},
    ).mappings().all()

    data = []
    for row in rows:
        item = dict(row)
        item["volle_naam"] = f"{item.pop('GEB_Naam')} {item.pop('GEB_Van')}".strip()
        data.append(item)

    return schemas.APIResponse(sukses=True, data=data, fout=None)
