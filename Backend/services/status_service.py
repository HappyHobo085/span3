"""Shared status query logic — deduplicates kampus/koshuis status endpoints."""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

import models, schemas
from services.gebruiker_service import kies_primere_rol


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
        base_q = base_q.join(
            models.Student,
            models.Student.Gebruiker_ID == models.ToegangsLogs.Gebruiker_ID,
        ).filter(models.Student.Koshuis_ID == koshuis_id)

    subquery = base_q.group_by(
        models.ToegangsLogs.Gebruiker_ID
    ).subquery()

    latest_logs = db.query(models.ToegangsLogs, models.Gebruikers).join(
        subquery,
        models.ToegangsLogs.Log_ID == subquery.c.max_log_id
    ).join(
        models.Gebruikers,
        models.Gebruikers.Gebruiker_ID == models.ToegangsLogs.Gebruiker_ID,
    ).all()

    gebruiker_ids = [gebruiker.Gebruiker_ID for _, gebruiker in latest_logs]
    if not gebruiker_ids:
        return [], []

    role_assignments = db.query(models.GebruikersRolle).filter(
        models.GebruikersRolle.Gebruiker_ID.in_(gebruiker_ids)
    ).all()
    role_ids = {
        gebruiker.Rol_ID for _, gebruiker in latest_logs if gebruiker.Rol_ID is not None
    }
    role_ids.update(assignment.Rol_ID for assignment in role_assignments)
    roles = db.query(models.Rolle).filter(models.Rolle.Rol_ID.in_(role_ids)).all()
    role_names_by_id = {role.Rol_ID: role.ROL_Naam for role in roles}
    role_names_by_user = {user_id: [] for user_id in gebruiker_ids}
    for assignment in role_assignments:
        role_name = role_names_by_id.get(assignment.Rol_ID)
        if role_name:
            role_names_by_user[assignment.Gebruiker_ID].append(role_name)
    for _, gebruiker in latest_logs:
        primary_role_name = role_names_by_id.get(gebruiker.Rol_ID)
        if primary_role_name and primary_role_name not in role_names_by_user[gebruiker.Gebruiker_ID]:
            role_names_by_user[gebruiker.Gebruiker_ID].append(primary_role_name)

    scanned_in = []
    scanned_out = []

    for log, gebruiker in latest_logs:
        role_names = role_names_by_user[gebruiker.Gebruiker_ID]
        rol_naam = kies_primere_rol(role_names)

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
