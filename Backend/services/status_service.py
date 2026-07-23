"""Shared status query logic — deduplicates kampus/koshuis status endpoints."""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

import models, schemas


def haal_laatste_logs_per_gebruiker(
    db: Session,
    kampus_id: Optional[int] = None,
    koshuis_id: Optional[int] = None,
) -> tuple:
    """
    Fetch the latest access log per user, filtered by kampus or koshuis.
    Returns (scanned_in: list[schemas.KampusGebruikerStatus], scanned_out: list[...]).
    """
    # Build base query for latest log per user
    base_q = db.query(
        models.ToegangsLogs.Gebruiker_ID,
        func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
    )

    if kampus_id is not None:
        base_q = base_q.join(models.Lokasie).filter(
            models.Lokasie.Kampus_ID == kampus_id
        )
    elif koshuis_id is not None:
        # For koshuis: filter by students linked to this koshuis
        student_ids = [
            s.Gebruiker_ID for s in
            db.query(models.Student).filter(models.Student.Koshuis_ID == koshuis_id).all()
        ]
        if not student_ids:
            return [], []
        base_q = base_q.filter(models.ToegangsLogs.Gebruiker_ID.in_(student_ids))

    subquery = base_q.group_by(
        models.ToegangsLogs.Gebruiker_ID
    ).subquery()

    latest_logs = db.query(models.ToegangsLogs).join(
        subquery,
        models.ToegangsLogs.Log_ID == subquery.c.max_log_id
    ).all()

    scanned_in = []
    scanned_out = []

    for log in latest_logs:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.Gebruiker_ID == log.Gebruiker_ID
        ).first()
        if not gebruiker:
            continue
        rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == gebruiker.Rol_ID).first()
        rol_naam = rol.ROL_Naam if rol else "Onbekend"

        status_obj = schemas.KampusGebruikerStatus(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            GEB_Naam=gebruiker.GEB_Naam,
            GEB_Van=gebruiker.GEB_Van,
            GEB_Epos=gebruiker.GEB_Epos,
            Rol_Naam=rol_naam,
            Tydstempel=log.TOE_Tydstempel,
            Rigting=log.TOE_Rigting,
            Metode=log.TOE_Metode
        )

        if log.TOE_Rigting == "IN":
            scanned_in.append(status_obj)
        else:
            scanned_out.append(status_obj)

    return scanned_in, scanned_out
