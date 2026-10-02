"""MOON Events API — eventbestuur, app-RSVP en publieke eksterne RSVP."""

from datetime import datetime, timezone, timedelta
from html import escape
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import auth
import database
import models
import schemas

router = APIRouter(prefix="/events", tags=["Events"])

# Publieke Event-RSVP skakels moet na die MOON webwerf wys, nie na die
# Flutter API-hostname nie. Railway kan dit met PUBLIC_SITE_BASE_URL oorskryf.
PUBLIC_SITE_BASE_URL = os.getenv("PUBLIC_SITE_BASE_URL", "").rstrip("/")
if not PUBLIC_SITE_BASE_URL:
    import logging
    logging.getLogger("moon").warning(
        "PUBLIC_SITE_BASE_URL is nie gestel nie — publieke RSVP-skakels sal nie werk nie"
    )


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _iso_utc(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _require_active(current_user: models.Gebruikers) -> None:
    if current_user is None or not current_user.Is_Aktief:
        raise HTTPException(status_code=403, detail="Jou gebruiker is nie aktief nie")


def _require_opsigter(db: Session, current_user: models.Gebruikers) -> None:
    """Magtekening geskied op rolle, nie op subrekords nie — so 'n gebruiker
    wie se Opsigter-rol verwyder is, verloor ook die reg, en 'n Administrateur
    sonder 'n subrekord kry steeds toegang (konsekwent met RoleChecker).

    Gebruik eager-loaded relasies — geen ekstra queries nodig nie."""
    _require_active(current_user)
    rol_namen = []
    for assignment in (current_user.gebruikers_rolle or []):
        if assignment.rol is not None:
            rol_namen.append(assignment.rol.ROL_Naam)
    if not rol_namen and current_user.rol is not None:
        rol_namen = [current_user.rol.ROL_Naam]
    if "Administrateur" not in rol_namen and "Kampus_Opsigter" not in rol_namen:
        raise HTTPException(status_code=403, detail="Slegs 'n Opsigter mag events bestuur")


def _require_rsvp_user(db: Session, current_user: models.Gebruikers) -> None:
    """Check that user is a student or personeel — use eager-loaded sub-records."""
    _require_active(current_user)
    is_student = current_user.student is not None
    is_personeel = current_user.personeel is not None
    if not is_student and not is_personeel:
        raise HTTPException(
            status_code=403,
            detail="RSVP is slegs vir studente en personeel beskikbaar",
        )


def _event_or_404(db: Session, event_id: int, *, lock: bool = False) -> models.Funksie:
    query = db.query(models.Funksie).filter(models.Funksie.Funksie_ID == event_id)
    if lock:
        query = query.with_for_update()
    event = query.first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event nie gevind nie")
    return event


def _public_event_or_404(db: Session, share_token: str, *, lock: bool = False) -> models.Funksie:
    query = db.query(models.Funksie).filter(models.Funksie.FUN_Deel_Token == share_token)
    if lock:
        query = query.with_for_update()
    event = query.first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event-skakel is ongeldig of bestaan nie meer nie")
    return event


def _app_confirmed_count(db: Session, event_id: int) -> int:
    """Count app RSVPs — uses eager-loaded rsvps if available, else falls back to query."""
    # When called from _event_dict with eager-loaded data, pass the event's rsvps directly
    return int(
        db.query(func.count(models.FunksieRSVP.Gebruiker_ID))
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.RSVP_Status == "GAAN",
        )
        .scalar() or 0
    )


def _external_confirmed_count(db: Session, event_id: int) -> int:
    """Count external RSVPs — uses eager-loaded publieke_rsvps if available."""
    return int(
        db.query(func.count(models.FunksiePubliekRSVP.Publiek_RSVP_ID))
        .filter(
            models.FunksiePubliekRSVP.Funksie_ID == event_id,
            models.FunksiePubliekRSVP.RSVP_Status == "GAAN",
        )
        .scalar() or 0
    )


def _confirmed_count(db: Session, event_id: int) -> int:
    return _app_confirmed_count(db, event_id) + _external_confirmed_count(db, event_id)


def _validate_location(db: Session, kampus_id: int, lokasie_id: Optional[int]) -> None:
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if kampus is None:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")
    if lokasie_id is None:
        return
    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if lokasie is None:
        raise HTTPException(status_code=404, detail="Lokaal/lokasie nie gevind nie")
    if lokasie.Kampus_ID != kampus_id:
        raise HTTPException(status_code=400, detail="Die gekose lokaal behoort nie aan dié kampus nie")


def _validate_times(begin_tyd: datetime, eind_tyd: datetime) -> None:
    if eind_tyd <= begin_tyd:
        raise HTTPException(status_code=400, detail="Event se eindtyd moet ná die begintyd wees")


def _my_rsvp(db: Session, event_id: int, user_id: int) -> Optional[str]:
    row = db.query(models.FunksieRSVP).filter(
        models.FunksieRSVP.Funksie_ID == event_id,
        models.FunksieRSVP.Gebruiker_ID == user_id,
    ).first()
    return row.RSVP_Status if row is not None else None


def _event_dict(db: Session, event: models.Funksie, current_user_id: Optional[int] = None) -> dict:
    """Build event dict from eagerly-loaded relationships (geen ekstra queries nie).

    Met selectinload op Funksie.rsvps, Funksie.publieke_rsvps,
    Funksie.kampus, Funksie.lokasie, Funksie.geskep_deur word
    alles in een slag gelaai.
    """
    # Count from loaded RSVP collections (no extra queries)
    app_count = sum(1 for r in (event.rsvps or []) if r.RSVP_Status == "GAAN")
    external_count = sum(1 for r in (event.publieke_rsvps or []) if r.RSVP_Status == "GAAN")
    rsvp_count = app_count + external_count
    capacity = int(event.FUN_Kapasiteit or 0)

    # My RSVP from loaded collection
    my_status = None
    if current_user_id is not None:
        for r in (event.rsvps or []):
            if r.Gebruiker_ID == current_user_id:
                my_status = r.RSVP_Status
                break
    return {
        "event_id": event.Funksie_ID,
        "naam": event.FUN_Naam,
        "kampus_id": event.Kampus_ID,
        "kampus_naam": event.kampus.KAM_Naam if event.kampus else "Onbekende kampus",
        "lokasie_id": event.Lokasie_ID,
        "lokasie_naam": event.lokasie.LOK_Naam if event.lokasie else None,
        "begin_tyd": _iso_utc(event.FUN_Begin_Tyd),
        "eind_tyd": _iso_utc(event.FUN_Eind_Tyd),
        "beskrywing": event.FUN_Beskrywing,
        "kapasiteit": capacity,
        "rsvp_aantal": rsvp_count,
        "app_rsvp_aantal": app_count,
        "eksterne_rsvp_aantal": external_count,
        "plekke_oor": max(capacity - rsvp_count, 0),
        "vol": rsvp_count >= capacity if capacity > 0 else True,
        "status": event.FUN_Status or ("AKTIEF" if event.FUN_Is_Aktief else "GEKANSELLEER"),
        "is_aktief": bool(event.FUN_Is_Aktief),
        "my_rsvp": my_status,
        "het_deel_skakel": bool(event.FUN_Deel_Token),
        "geskep_op": _iso_utc(event.Geskep_Op),
        "geskep_deur": None if event.geskep_deur is None else {
            "gebruiker_id": event.geskep_deur.Gebruiker_ID,
            "volle_naam": f"{event.geskep_deur.GEB_Naam} {event.geskep_deur.GEB_Van}".strip(),
        },
    }



def _event_attendance_window(event: models.Funksie) -> tuple[datetime, datetime]:
    """Breë hekvenster vir app-RSVP gebruikers wat via normale kampushek scan."""
    start = event.FUN_Begin_Tyd - timedelta(hours=4)
    end = event.FUN_Eind_Tyd + timedelta(hours=6)
    return start, end


def _last_direction(logs) -> Optional[str]:
    usable = [row for row in logs if row.TOE_Rigting in {"IN", "UIT"}]
    return usable[-1].TOE_Rigting if usable else None


def _attendance_payload(
    db: Session,
    event: models.Funksie,
    current_user_id: Optional[int] = None,
) -> dict:
    """Een bron vir Opsigter se live/finale Event-bywoning."""
    app_rows = (
        db.query(models.FunksieRSVP, models.Gebruikers)
        .join(
            models.Gebruikers,
            models.Gebruikers.Gebruiker_ID == models.FunksieRSVP.Gebruiker_ID,
        )
        .filter(
            models.FunksieRSVP.Funksie_ID == event.Funksie_ID,
            models.FunksieRSVP.RSVP_Status == "GAAN",
        )
        .order_by(models.FunksieRSVP.RSVP_Tyd.asc())
        .all()
    )
    external_rows = (
        db.query(models.FunksiePubliekRSVP)
        .filter(
            models.FunksiePubliekRSVP.Funksie_ID == event.Funksie_ID,
            models.FunksiePubliekRSVP.RSVP_Status == "GAAN",
        )
        .order_by(models.FunksiePubliekRSVP.RSVP_Tyd.asc())
        .all()
    )

    start, end = _event_attendance_window(event)
    now = datetime.utcnow()
    query_end = min(end, now)

    app_user_ids = [user.Gebruiker_ID for _, user in app_rows]
    logs_by_user = {uid: [] for uid in app_user_ids}
    if app_user_ids and query_end >= start:
        app_logs = (
            db.query(models.ToegangsLogs)
            .join(
                models.Lokasie,
                models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
            )
            .filter(
                models.ToegangsLogs.Gebruiker_ID.in_(app_user_ids),
                models.Lokasie.Kampus_ID == event.Kampus_ID,
                models.Lokasie.LOK_Tipe == "Kampus",
                models.ToegangsLogs.TOE_Tydstempel >= start,
                models.ToegangsLogs.TOE_Tydstempel <= query_end,
                models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
            )
            .order_by(models.ToegangsLogs.TOE_Tydstempel.asc())
            .all()
        )
        for row in app_logs:
            logs_by_user.setdefault(row.Gebruiker_ID, []).append(row)

    ext_ids = [row.Publiek_RSVP_ID for row in external_rows]
    ext_logs_by_id = {rid: [] for rid in ext_ids}
    if ext_ids:
        ext_logs = (
            db.query(models.FunksiePubliekToegang)
            .filter(
                models.FunksiePubliekToegang.Funksie_ID == event.Funksie_ID,
                models.FunksiePubliekToegang.Publiek_RSVP_ID.in_(ext_ids),
                models.FunksiePubliekToegang.Rigting.in_(["IN", "UIT"]),
            )
            .order_by(models.FunksiePubliekToegang.Tydstempel.asc())
            .all()
        )
        for row in ext_logs:
            ext_logs_by_id.setdefault(row.Publiek_RSVP_ID, []).append(row)

    attendees = []
    in_scans = 0
    out_scans = 0

    for rsvp, user in app_rows:
        logs = logs_by_user.get(user.Gebruiker_ID, [])
        in_scans += sum(1 for row in logs if row.TOE_Rigting == "IN")
        out_scans += sum(1 for row in logs if row.TOE_Rigting == "UIT")
        first_in = next((row for row in logs if row.TOE_Rigting == "IN"), None)
        last = logs[-1] if logs else None
        last_dir = _last_direction(logs)
        arrived = first_in is not None
        status = last_dir if arrived and last_dir in {"IN", "UIT"} else "NOG_NIE"
        if user.student is not None:
            role, number = "STUDENT", user.student.STU_Nommer
        elif user.personeel is not None:
            role, number = "PERSONEEL", user.personeel.PER_Nommer
        else:
            role, number = "GEBRUIKER", ""
        attendees.append({
            "attendee_key": f"app:{user.Gebruiker_ID}",
            "gebruiker_id": user.Gebruiker_ID,
            "publiek_rsvp_id": None,
            "volle_naam": f"{user.GEB_Naam} {user.GEB_Van}".strip(),
            "rol": role,
            "nommer": number,
            "selfoon": user.GEB_Selfoon_Nr,
            "epos": user.GEB_Epos,
            "ekstern": False,
            "status": status,
            "aangekom": arrived,
            "eerste_in": _iso_utc(first_in.TOE_Tydstempel) if first_in else None,
            "laaste_aksie": _iso_utc(last.TOE_Tydstempel) if last else None,
            "laaste_rigting": last_dir,
            "rsvp_tyd": _iso_utc(rsvp.RSVP_Tyd),
        })

    for rsvp in external_rows:
        logs = ext_logs_by_id.get(rsvp.Publiek_RSVP_ID, [])
        in_scans += sum(1 for row in logs if row.Rigting == "IN")
        out_scans += sum(1 for row in logs if row.Rigting == "UIT")
        first_in = next((row for row in logs if row.Rigting == "IN"), None)
        last = logs[-1] if logs else None
        last_dir = last.Rigting if last and last.Rigting in {"IN", "UIT"} else None
        arrived = first_in is not None
        status = last_dir if arrived and last_dir in {"IN", "UIT"} else "NOG_NIE"
        attendees.append({
            "attendee_key": f"external:{rsvp.Publiek_RSVP_ID}",
            "gebruiker_id": None,
            "publiek_rsvp_id": rsvp.Publiek_RSVP_ID,
            "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
            "rol": "EKSTERNE GAS",
            "nommer": rsvp.Selfoon,
            "selfoon": rsvp.Selfoon,
            "epos": rsvp.Epos,
            "ekstern": True,
            "status": status,
            "aangekom": arrived,
            "eerste_in": _iso_utc(first_in.Tydstempel) if first_in else None,
            "laaste_aksie": _iso_utc(last.Tydstempel) if last else None,
            "laaste_rigting": last_dir,
            "rsvp_tyd": _iso_utc(rsvp.RSVP_Tyd),
        })

    order = {"IN": 0, "UIT": 1, "NOG_NIE": 2}
    attendees.sort(
        key=lambda item: (
            order.get(item["status"], 9),
            -(datetime.fromisoformat(item["laaste_aksie"].replace("Z", "+00:00")).timestamp()
              if item.get("laaste_aksie") else 0),
            item["volle_naam"].lower(),
        )
    )

    arrived_count = sum(1 for item in attendees if item["aangekom"])
    inside_count = sum(1 for item in attendees if item["status"] == "IN")
    out_count = sum(1 for item in attendees if item["status"] == "UIT")
    not_arrived = len(attendees) - arrived_count
    final_stats = now > event.FUN_Eind_Tyd

    return {
        "event": _event_dict(db, event, current_user_id),
        "summary": {
            "rsvp": len(attendees),
            "aangekom": arrived_count,
            "tans_binne": inside_count,
            "uit": out_count,
            "nog_nie_gekom": not_arrived,
            "no_show": not_arrived if final_stats else 0,
            "in_skanderings": in_scans,
            "uit_skanderings": out_scans,
            "app_rsvp": len(app_rows),
            "eksterne_rsvp": len(external_rows),
        },
        "final": final_stats,
        "attendees": attendees,
    }

def _new_unique_share_token(db: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(32)
        if db.query(models.Funksie).filter(models.Funksie.FUN_Deel_Token == token).first() is None:
            return token
    raise HTTPException(status_code=500, detail="Kon nie 'n veilige deel-skakel skep nie")


def _new_unique_qr_token(db: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(36)
        if db.query(models.FunksiePubliekRSVP).filter(models.FunksiePubliekRSVP.QR_Token == token).first() is None:
            return token
    raise HTTPException(status_code=500, detail="Kon nie 'n veilige QR-token skep nie")


def _normalise_phone(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")


@router.get("")
def list_events(
    view: str = Query("komende"),
    skip: int = Query(0, ge=0, description="Aantal om oor te slaan"),
    limit: int = Query(100, ge=1, le=500, description="Maksimum aantal resultate"),
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_active(current_user)
    view = view.strip().lower()
    if view not in {"komende", "my", "vorige"}:
        raise HTTPException(status_code=400, detail="Ongeldige event-filter")
    now = datetime.utcnow()
    query = db.query(models.Funksie).options(
        joinedload(models.Funksie.kampus),
        joinedload(models.Funksie.lokasie),
        joinedload(models.Funksie.geskep_deur),
        joinedload(models.Funksie.rsvps),
        joinedload(models.Funksie.publieke_rsvps),
    )
    if view == "komende":
        query = query.filter(
            models.Funksie.FUN_Is_Aktief.is_(True),
            models.Funksie.FUN_Status == "AKTIEF",
            models.Funksie.FUN_Eind_Tyd >= now,
        )
    elif view == "vorige":
        query = query.filter(models.Funksie.FUN_Eind_Tyd < now)
    else:
        query = query.join(
            models.FunksieRSVP,
            models.FunksieRSVP.Funksie_ID == models.Funksie.Funksie_ID,
        ).filter(
            models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
            models.FunksieRSVP.RSVP_Status == "GAAN",
            models.Funksie.FUN_Status == "AKTIEF",
            models.Funksie.FUN_Eind_Tyd >= now,
        )
    # Tel totaal vir pagination (een count query)
    total = query.count()

    # Pas pagination toe op SQL-vlak (nie in Python nie)
    events = query.order_by(models.Funksie.FUN_Begin_Tyd.asc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    return {
        "sukses": True,
        "data": [_event_dict(db, e, current_user.Gebruiker_ID) for e in events],
        "fout": None,
        "totaal": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("")
def create_event(
    payload: schemas.EventCreateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    naam = payload.naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Event naam is verpligtend")
    if payload.kapasiteit < 1:
        raise HTTPException(status_code=400, detail="Kapasiteit moet minstens 1 wees")
    begin = _utc_naive(payload.begin_tyd)
    einde = _utc_naive(payload.eind_tyd)
    _validate_times(begin, einde)
    _validate_location(db, payload.kampus_id, payload.lokasie_id)
    event = models.Funksie(
        Kampus_ID=payload.kampus_id,
        Lokasie_ID=payload.lokasie_id,
        Geskep_Deur_ID=current_user.Gebruiker_ID,
        FUN_Naam=naam,
        FUN_Begin_Tyd=begin,
        FUN_Eind_Tyd=einde,
        FUN_Beskrywing=(payload.beskrywing or "").strip() or None,
        FUN_Kapasiteit=payload.kapasiteit,
        FUN_Status="AKTIEF",
        FUN_Is_Aktief=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"sukses": True, "data": _event_dict(db, event, current_user.Gebruiker_ID), "fout": None}


@router.put("/{event_id}")
def update_event(
    event_id: int,
    payload: schemas.EventUpdateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    new_kampus_id = payload.kampus_id if payload.kampus_id is not None else event.Kampus_ID
    new_lokasie_id = payload.lokasie_id if payload.kampus_id is not None else event.Lokasie_ID
    _validate_location(db, new_kampus_id, new_lokasie_id)
    new_begin = _utc_naive(payload.begin_tyd) if payload.begin_tyd is not None else event.FUN_Begin_Tyd
    new_end = _utc_naive(payload.eind_tyd) if payload.eind_tyd is not None else event.FUN_Eind_Tyd
    _validate_times(new_begin, new_end)
    if payload.kapasiteit is not None:
        if payload.kapasiteit < 1:
            raise HTTPException(status_code=400, detail="Kapasiteit moet minstens 1 wees")
        confirmed = _confirmed_count(db, event_id)
        if payload.kapasiteit < confirmed:
            raise HTTPException(status_code=400, detail=f"Kapasiteit kan nie laer as die huidige {confirmed} bevestigde RSVP's wees nie")
        event.FUN_Kapasiteit = payload.kapasiteit
    if payload.naam is not None:
        naam = payload.naam.strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Event naam mag nie leeg wees nie")
        event.FUN_Naam = naam
    event.Kampus_ID = new_kampus_id
    event.Lokasie_ID = new_lokasie_id
    event.FUN_Begin_Tyd = new_begin
    event.FUN_Eind_Tyd = new_end
    if payload.beskrywing is not None:
        event.FUN_Beskrywing = payload.beskrywing.strip() or None
    event.Gewysig_Op = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return {"sukses": True, "data": _event_dict(db, event, current_user.Gebruiker_ID), "fout": None}


@router.post("/{event_id}/kanselleer")
def cancel_event(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)

    # Wanneer 'n Event gekanselleer word, moet geen aktiewe RSVP daarvan
    # oorbly nie. Dit maak ook eksterne QR-kodes onmiddellik ongeldig omdat
    # die wag se Event-scan slegs RSVP_Status == "GAAN" aanvaar.
    now = datetime.utcnow()

    db.query(models.FunksieRSVP).filter(
        models.FunksieRSVP.Funksie_ID == event_id,
        models.FunksieRSVP.RSVP_Status == "GAAN",
    ).update(
        {
            models.FunksieRSVP.RSVP_Status: "GEKANSELLEER",
            models.FunksieRSVP.Gewysig_Op: now,
        },
        synchronize_session="fetch",
    )

    db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.Funksie_ID == event_id,
        models.FunksiePubliekRSVP.RSVP_Status == "GAAN",
    ).update(
        {
            models.FunksiePubliekRSVP.RSVP_Status: "GEKANSELLEER",
            models.FunksiePubliekRSVP.Gewysig_Op: now,
        },
        synchronize_session="fetch",
    )

    event.FUN_Status = "GEKANSELLEER"
    event.FUN_Is_Aktief = False
    event.Gewysig_Op = now

    db.commit()

    # _event_dict tel uit die relationship-collections. Expire hulle sodat
    # die response onmiddellik die gekanselleerde RSVP-statusse reflekteer.
    db.expire(event, ["rsvps", "publieke_rsvps"])
    db.refresh(event)

    return {"sukses": True, "data": _event_dict(db, event, current_user.Gebruiker_ID), "fout": None}


@router.post("/{event_id}/share")
def share_event(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    if not event.FUN_Deel_Token:
        event.FUN_Deel_Token = _new_unique_share_token(db)
        event.Gewysig_Op = datetime.utcnow()
        db.commit()
        db.refresh(event)
    share_url = f"{PUBLIC_SITE_BASE_URL}/event.html?token={event.FUN_Deel_Token}"
    return {
        "sukses": True,
        "data": {
            "event_id": event.Funksie_ID,
            "share_token": event.FUN_Deel_Token,
            "share_url": share_url,
            "event": _event_dict(db, event, current_user.Gebruiker_ID),
        },
        "fout": None,
    }


@router.post("/{event_id}/rsvp")
def rsvp_event(
    event_id: int,
    payload: schemas.EventRsvpRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_rsvp_user(db, current_user)
    event = _event_or_404(db, event_id, lock=True)
    if payload.status.strip().upper() != "GAAN":
        raise HTTPException(status_code=400, detail="Gebruik GAAN vir 'n bevestigde RSVP")
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF":
        raise HTTPException(status_code=400, detail="Hierdie event is nie meer aktief nie")
    if event.FUN_Eind_Tyd < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Hierdie event is reeds verby")
    existing = db.query(models.FunksieRSVP).filter(
        models.FunksieRSVP.Funksie_ID == event_id,
        models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
    ).first()
    if existing is not None and existing.RSVP_Status == "GAAN":
        data = _event_dict(db, event, current_user.Gebruiker_ID)
        db.rollback()
        return {"sukses": True, "data": data, "fout": None}
    confirmed = _confirmed_count(db, event_id)
    if confirmed >= int(event.FUN_Kapasiteit or 0):
        db.rollback()
        raise HTTPException(status_code=409, detail="Event is vol")
    if existing is None:
        db.add(models.FunksieRSVP(
            Funksie_ID=event_id,
            Gebruiker_ID=current_user.Gebruiker_ID,
            RSVP_Status="GAAN",
            RSVP_Tyd=datetime.utcnow(),
        ))
    else:
        existing.RSVP_Status = "GAAN"
        existing.RSVP_Tyd = datetime.utcnow()
        existing.Gewysig_Op = datetime.utcnow()
    db.commit()
    return {"sukses": True, "data": _event_dict(db, event, current_user.Gebruiker_ID), "fout": None}


@router.delete("/{event_id}/rsvp")
def cancel_rsvp(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_rsvp_user(db, current_user)
    event = _event_or_404(db, event_id)
    row = db.query(models.FunksieRSVP).filter(
        models.FunksieRSVP.Funksie_ID == event_id,
        models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
    ).first()
    if row is None or row.RSVP_Status != "GAAN":
        raise HTTPException(status_code=400, detail="Jy het nie 'n aktiewe RSVP vir hierdie event nie")
    row.RSVP_Status = "GEKANSELLEER"
    row.Gewysig_Op = datetime.utcnow()
    db.commit()
    return {"sukses": True, "data": _event_dict(db, event, current_user.Gebruiker_ID), "fout": None}


@router.get("/{event_id}/rsvps")
def event_rsvps(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    app_rows = db.query(models.FunksieRSVP, models.Gebruikers).join(
        models.Gebruikers,
        models.Gebruikers.Gebruiker_ID == models.FunksieRSVP.Gebruiker_ID,
    ).filter(
        models.FunksieRSVP.Funksie_ID == event_id,
        models.FunksieRSVP.RSVP_Status == "GAAN",
    ).order_by(models.FunksieRSVP.RSVP_Tyd.asc()).all()
    items = []
    for rsvp, user in app_rows:
        if user.student is not None:
            role, number = "Student", user.student.STU_Nommer
        elif user.personeel is not None:
            role, number = "Personeel", user.personeel.PER_Nommer
        else:
            role, number = "Gebruiker", ""
        items.append({
            "gebruiker_id": user.Gebruiker_ID,
            "publiek_rsvp_id": None,
            "volle_naam": f"{user.GEB_Naam} {user.GEB_Van}".strip(),
            "rol": role,
            "nommer": number,
            "selfoon": user.GEB_Selfoon_Nr,
            "epos": user.GEB_Epos,
            "ekstern": False,
            "rsvp_tyd": _iso_utc(rsvp.RSVP_Tyd),
        })
    external_rows = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.Funksie_ID == event_id,
        models.FunksiePubliekRSVP.RSVP_Status == "GAAN",
    ).order_by(models.FunksiePubliekRSVP.RSVP_Tyd.asc()).all()
    for rsvp in external_rows:
        items.append({
            "gebruiker_id": None,
            "publiek_rsvp_id": rsvp.Publiek_RSVP_ID,
            "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
            "rol": "Eksterne Gas",
            "nommer": rsvp.Selfoon,
            "selfoon": rsvp.Selfoon,
            "epos": rsvp.Epos,
            "ekstern": True,
            "rsvp_tyd": _iso_utc(rsvp.RSVP_Tyd),
        })
    items.sort(key=lambda item: item.get("rsvp_tyd") or "")
    return {
        "sukses": True,
        "data": {
            "event": _event_dict(db, event, current_user.Gebruiker_ID),
            "rsvps": items,
            "rsvp_aantal": len(items),
            "app_rsvp_aantal": len(app_rows),
            "eksterne_rsvp_aantal": len(external_rows),
        },
        "fout": None,
    }



@router.get("/{event_id}/attendance")
def event_attendance(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    return {
        "sukses": True,
        "data": _attendance_payload(db, event, current_user.Gebruiker_ID),
        "fout": None,
    }


@router.delete("/{event_id}/public-rsvps/{publiek_rsvp_id}")
def cancel_public_rsvp_by_opsigter(
    event_id: int,
    publiek_rsvp_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    row = (
        db.query(models.FunksiePubliekRSVP)
        .filter(
            models.FunksiePubliekRSVP.Publiek_RSVP_ID == publiek_rsvp_id,
            models.FunksiePubliekRSVP.Funksie_ID == event_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Eksterne RSVP nie gevind nie")
    if row.RSVP_Status != "GAAN":
        return {
            "sukses": True,
            "data": {"gekanselleer": True, "reeds_gekanselleer": True},
            "fout": None,
        }
    row.RSVP_Status = "GEKANSELLEER"
    row.Gewysig_Op = datetime.utcnow()
    db.commit()
    return {
        "sukses": True,
        "data": {
            "gekanselleer": True,
            "reeds_gekanselleer": False,
            "event": _event_dict(db, event, current_user.Gebruiker_ID),
        },
        "fout": None,
    }


@router.get("/public/{share_token}/data")
def public_event_data(
    share_token: str,
    db: Session = Depends(database.get_db),
):
    """Publieke JSON-data vir die aparte MOON website se event.html."""
    event = _public_event_or_404(db, share_token)
    data = _event_dict(db, event)
    disabled = (
        data["status"] != "AKTIEF"
        or not data["is_aktief"]
        or event.FUN_Eind_Tyd < datetime.utcnow()
    )
    return {
        "sukses": True,
        "data": {
            "naam": data["naam"],
            "kampus_naam": data["kampus_naam"],
            "lokasie_naam": data["lokasie_naam"],
            "begin_tyd": data["begin_tyd"],
            "eind_tyd": data["eind_tyd"],
            "beskrywing": data["beskrywing"],
            "kapasiteit": data["kapasiteit"],
            "rsvp_aantal": data["rsvp_aantal"],
            "plekke_oor": data["plekke_oor"],
            "status": data["status"],
            "is_aktief": data["is_aktief"],
            "rsvp_oop": not disabled,
        },
        "fout": None,
    }


@router.get("/public/{share_token}", response_class=HTMLResponse)
def public_event_page(share_token: str, db: Session = Depends(database.get_db)):
    event = _public_event_or_404(db, share_token)
    data = _event_dict(db, event)
    naam = escape(data["naam"] or "Event")
    kampus = escape(data["kampus_naam"] or "")
    lokasie = escape(data["lokasie_naam"] or "")
    beskrywing = escape(data["beskrywing"] or "")
    begin_iso = escape(data["begin_tyd"] or "")
    end_iso = escape(data["eind_tyd"] or "")
    disabled = data["status"] != "AKTIEF" or not data["is_aktief"] or event.FUN_Eind_Tyd < datetime.utcnow()
    disabled_attr = "disabled" if disabled else ""
    status_text = "Hierdie event is nie meer oop vir RSVP nie." if disabled else f"{data['plekke_oor']} plekke oor"
    location_text = f" · {lokasie}" if lokasie else ""
    storage_key = escape(f"moon_event_rsvp_{share_token}")

    page = f'''<!doctype html>
<html lang="af"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOON Event RSVP</title><style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,Arial,sans-serif;background:#070b14;color:#f8fafc}}
.wrap{{max-width:620px;margin:0 auto;padding:24px 16px 48px}}.brand{{font-size:13px;font-weight:900;letter-spacing:2px;color:#22d3ee;margin-bottom:12px}}
.card{{background:#111827;border:1px solid #263244;border-radius:20px;padding:22px;box-shadow:0 18px 55px rgba(0,0,0,.35)}}h1{{margin:0 0 10px;font-size:28px}}
.muted{{color:#94a3b8;font-size:14px;line-height:1.5}}.meta{{display:grid;gap:10px;margin:18px 0}}.meta div{{background:#0f172a;border:1px solid #243247;border-radius:13px;padding:12px 14px}}
label{{display:block;margin:14px 0 6px;color:#cbd5e1;font-size:12px;font-weight:800}}input{{width:100%;padding:13px 14px;border-radius:12px;border:1px solid #334155;background:#0b1220;color:#fff;font-size:16px}}
button{{width:100%;margin-top:20px;border:0;border-radius:13px;padding:14px 16px;background:#22d3ee;color:#02141b;font-weight:900;font-size:15px;cursor:pointer}}button:disabled{{opacity:.45;cursor:not-allowed}}
.status{{margin-top:14px;font-size:13px;color:#94a3b8}}.err{{color:#f87171;margin-top:12px;font-weight:700}}#confirm{{display:none;text-align:center}}#qr{{width:260px;height:260px;margin:22px auto 10px;background:#fff;border-radius:14px;padding:10px}}
#qr img,#qr canvas{{width:100%!important;height:100%!important}}.ok{{color:#4ade80;font-weight:900;font-size:22px}}.token{{word-break:break-all;color:#64748b;font-size:10px;margin-top:12px}}
.restore{{display:none;margin-bottom:14px;padding:11px 13px;border-radius:12px;background:#0f172a;border:1px solid #334155;color:#cbd5e1;font-size:13px}}
</style></head><body><div class="wrap"><div class="brand">MOON</div>
<div id="restoreStatus" class="restore">Jou bestaande RSVP word gelaai...</div>
<div class="card" id="formCard"><h1>{naam}</h1><div class="muted">{beskrywing}</div><div class="meta">
<div><strong>Kampus:</strong> {kampus}{location_text}</div><div><strong>Datum/Tyd:</strong> <span id="eventTime" data-start="{begin_iso}" data-end="{end_iso}"></span></div>
<div><strong>RSVP:</strong> {data['rsvp_aantal']} / {data['kapasiteit']} · {escape(status_text)}</div></div>
<form id="rsvpForm"><label>Naam</label><input name="naam" maxlength="100" autocomplete="given-name" required {disabled_attr}><label>Van</label><input name="van" maxlength="100" autocomplete="family-name" required {disabled_attr}>
<label>Selfoon</label><input name="selfoon" maxlength="30" inputmode="tel" autocomplete="tel" required {disabled_attr}><label>E-pos (opsioneel)</label><input name="epos" maxlength="255" type="email" autocomplete="email" {disabled_attr}>
<button type="submit" {disabled_attr}>RSVP – EK GAAN</button><div class="status">{escape(status_text)}</div><div class="err" id="error"></div></form></div>
<div class="card" id="confirm"><div class="ok">✓ RSVP BEVESTIG</div><h1 id="guestName" style="margin-top:12px"></h1><div class="muted">Wys hierdie QR by die event se toegangspunt.</div>
<div id="qr"></div><div class="muted">{naam}</div><div class="token" id="tokenFallback"></div></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script><script>
const storageKey={storage_key!r};
const timeEl=document.getElementById('eventTime');try{{const s=new Date(timeEl.dataset.start),e=new Date(timeEl.dataset.end);timeEl.textContent=s.toLocaleString([],{{dateStyle:'medium',timeStyle:'short'}})+' – '+e.toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}})}}catch(_){{timeEl.textContent='Tyd nie beskikbaar nie'}}
function showQr(d){{document.getElementById('guestName').textContent=d.volle_naam;document.getElementById('formCard').style.display='none';document.getElementById('confirm').style.display='block';document.getElementById('qr').innerHTML='';document.getElementById('tokenFallback').textContent='Toegangstoken: '+d.qr_token;if(window.QRCode){{new QRCode(document.getElementById('qr'),{{text:d.qr_value,width:240,height:240,correctLevel:QRCode.CorrectLevel.M}})}}else{{document.getElementById('qr').innerHTML='<div style="color:#111;padding:40px 10px">QR kon nie laai nie. Gebruik die toegangstoken hieronder.</div>'}}}}
async function restoreSaved(){{const saved=localStorage.getItem(storageKey);if(!saved)return;const box=document.getElementById('restoreStatus');box.style.display='block';try{{const res=await fetch(window.location.pathname+'/rsvp/'+encodeURIComponent(saved));const body=await res.json();if(!res.ok||body.sukses!==true)throw new Error(body.detail||body.fout||'Bestaande RSVP kon nie laai nie');showQr(body.data);box.style.display='none'}}catch(err){{localStorage.removeItem(storageKey);box.textContent=err.message||String(err);box.style.color='#f87171'}}}}
document.getElementById('rsvpForm').addEventListener('submit',async(ev)=>{{ev.preventDefault();const error=document.getElementById('error');error.textContent='';const form=new FormData(ev.target);const payload={{naam:String(form.get('naam')||'').trim(),van:String(form.get('van')||'').trim(),selfoon:String(form.get('selfoon')||'').trim(),epos:String(form.get('epos')||'').trim()||null}};const btn=ev.target.querySelector('button');btn.disabled=true;btn.textContent='BESIG...';try{{const res=await fetch(window.location.pathname+'/rsvp',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const body=await res.json();if(!res.ok||body.sukses!==true)throw new Error(body.detail||body.fout||'RSVP het misluk');const d=body.data;localStorage.setItem(storageKey,d.qr_token);showQr(d)}}catch(err){{error.textContent=err.message||String(err);btn.disabled=false;btn.textContent='RSVP – EK GAAN'}}}});
restoreSaved();
</script></body></html>'''
    return HTMLResponse(content=page)


@router.get("/public/{share_token}/rsvp/{qr_token}")
def restore_public_event_rsvp(
    share_token: str,
    qr_token: str,
    db: Session = Depends(database.get_db),
):
    event = _public_event_or_404(db, share_token)
    row = (
        db.query(models.FunksiePubliekRSVP)
        .filter(
            models.FunksiePubliekRSVP.Funksie_ID == event.Funksie_ID,
            models.FunksiePubliekRSVP.QR_Token == qr_token,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bestaande RSVP kon nie gevind word nie")
    if row.RSVP_Status != "GAAN":
        raise HTTPException(status_code=410, detail="Hierdie RSVP is gekanselleer en die QR is nie meer geldig nie")
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF" or event.FUN_Eind_Tyd < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Hierdie Event is nie meer aktief nie")
    return {
        "sukses": True,
        "data": {
            "publiek_rsvp_id": row.Publiek_RSVP_ID,
            "volle_naam": f"{row.Naam} {row.Van}".strip(),
            "qr_token": row.QR_Token,
            "qr_value": f"MOON-EVENT:{row.QR_Token}",
            "reeds_bestaan": True,
        },
        "fout": None,
    }


@router.post("/public/{share_token}/rsvp")
def public_event_rsvp(
    share_token: str,
    payload: schemas.PublicEventRsvpRequest,
    db: Session = Depends(database.get_db),
):
    event = _public_event_or_404(db, share_token, lock=True)
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF":
        db.rollback()
        raise HTTPException(status_code=400, detail="Hierdie event is nie meer oop vir RSVP nie")
    if event.FUN_Eind_Tyd < datetime.utcnow():
        db.rollback()
        raise HTTPException(status_code=400, detail="Hierdie event is reeds verby")

    naam = payload.naam.strip()
    van = payload.van.strip()
    selfoon = _normalise_phone(payload.selfoon)
    epos = str(payload.epos).strip().lower() if payload.epos is not None else None
    if not naam or not van:
        db.rollback()
        raise HTTPException(status_code=400, detail="Naam en van is verpligtend")
    if len(selfoon.replace("+", "")) < 7:
        db.rollback()
        raise HTTPException(status_code=400, detail="Voer 'n geldige selfoonnommer in")
    if epos and ("@" not in epos or "." not in epos.rsplit("@", 1)[-1]):
        db.rollback()
        raise HTTPException(status_code=400, detail="Voer 'n geldige e-posadres in of los dit leeg")

    identity_query = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.Funksie_ID == event.Funksie_ID,
        models.FunksiePubliekRSVP.Selfoon == selfoon,
        func.lower(models.FunksiePubliekRSVP.Naam) == naam.lower(),
        func.lower(models.FunksiePubliekRSVP.Van) == van.lower(),
    )
    existing = identity_query.order_by(models.FunksiePubliekRSVP.Publiek_RSVP_ID.desc()).first()
    if existing is not None:
        if existing.RSVP_Status != "GAAN":
            db.rollback()
            raise HTTPException(
                status_code=403,
                detail="Hierdie RSVP is deur die event-organiseerder gekanselleer. Kontak asseblief die organiseerder.",
            )
        data = {
            "publiek_rsvp_id": existing.Publiek_RSVP_ID,
            "volle_naam": f"{existing.Naam} {existing.Van}".strip(),
            "qr_token": existing.QR_Token,
            "qr_value": f"MOON-EVENT:{existing.QR_Token}",
            "reeds_bestaan": True,
        }
        db.rollback()
        return {"sukses": True, "data": data, "fout": None}

    if _confirmed_count(db, event.Funksie_ID) >= int(event.FUN_Kapasiteit or 0):
        db.rollback()
        raise HTTPException(status_code=409, detail="Event is vol")

    row = models.FunksiePubliekRSVP(
        Funksie_ID=event.Funksie_ID,
        Naam=naam,
        Van=van,
        Selfoon=selfoon,
        Epos=epos,
        QR_Token=_new_unique_qr_token(db),
        RSVP_Status="GAAN",
        RSVP_Tyd=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "sukses": True,
        "data": {
            "publiek_rsvp_id": row.Publiek_RSVP_ID,
            "volle_naam": f"{row.Naam} {row.Van}".strip(),
            "qr_token": row.QR_Token,
            "qr_value": f"MOON-EVENT:{row.QR_Token}",
            "reeds_bestaan": False,
        },
        "fout": None,
    }

