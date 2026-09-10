"""Shared status query logic — deduplicates kampus/koshuis status endpoints."""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

import models, schemas
from services.gebruiker_service import kies_primere_rol


def _haal_rol_names_vir_gebruiker(gebruiker: models.Gebruikers) -> list:
    """Haal rolname uit die eager-loaded relasies sonder ekstra queries.

    Met selectinload op Gebruikers.rol en Gebruikers.gebruikers_rolle
    plus GebruikersRolle.rol is alles reeds gelaai — geen DB-navraag nodig nie.
    """
    role_names = []
    for assignment in (gebruiker.gebruikers_rolle or []):
        if assignment.rol is not None:
            role_names.append(assignment.rol.ROL_Naam)
    if not role_names and gebruiker.rol is not None:
        role_names = [gebruiker.rol.ROL_Naam]
    return role_names


def haal_laatste_logs_per_gebruiker(
    db: Session,
    kampus_id: Optional[int] = None,
    koshuis_id: Optional[int] = None,
) -> tuple:
    """
    Fetch the latest access log per user, filtered by kampus or koshuis.
    Returns (scanned_in: list[schemas.KampusGebruikerStatus], scanned_out: list[...]).

    Optimizations:
    - Single subquery for latest log per user (no per-user queries)
    - Eager-loaded relationships (selectinload on ToegangsLogs.gebruiker, Gebruikers.rol, etc.)
    - Role resolution from loaded data (no extra queries)
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
        # Use a subquery instead of fetching all students first
        koshuis_student_subq = (
            db.query(models.Student.Gebruiker_ID)
            .filter(models.Student.Koshuis_ID == koshuis_id)
            .subquery()
        )
        base_q = base_q.filter(
            models.ToegangsLogs.Gebruiker_ID.in_(koshuis_student_subq)
        )

    subquery = base_q.group_by(
        models.ToegangsLogs.Gebruiker_ID
    ).subquery()

    # Eager-loaded: gebruiker (with rol, gebruikers_rolle, student, personeel)
    latest_logs = db.query(models.ToegangsLogs).join(
        subquery,
        models.ToegangsLogs.Log_ID == subquery.c.max_log_id
    ).join(
        models.Gebruikers,
        models.Gebruikers.Gebruiker_ID == models.ToegangsLogs.Gebruiker_ID,
    ).all()

    if not latest_logs:
        return [], []

    scanned_in = []
    scanned_out = []

    for log in latest_logs:
        # geen ekstra query nodig nie — eagerly loaded via selectinload
        gebruiker = log.gebruiker
        if not gebruiker:
            continue

        role_names = _haal_rol_names_vir_gebruiker(gebruiker)
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
