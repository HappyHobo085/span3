"""MOON Events API — eventbestuur en RSVP vir studente/personeel."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(prefix="/events", tags=["Events"])


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


def _require_opsigter(db: Session, current_user: models.Gebruikers) -> models.Kampus_Opsigter:
    _require_active(current_user)
    opsigter = (
        db.query(models.Kampus_Opsigter)
        .filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID)
        .first()
    )
    if opsigter is None:
        raise HTTPException(status_code=403, detail="Slegs 'n Opsigter mag events bestuur")
    return opsigter


def _require_rsvp_user(db: Session, current_user: models.Gebruikers) -> None:
    _require_active(current_user)
    is_student = (
        db.query(models.Student)
        .filter(models.Student.Gebruiker_ID == current_user.Gebruiker_ID)
        .first()
        is not None
    )
    is_personeel = (
        db.query(models.Personeel)
        .filter(models.Personeel.Gebruiker_ID == current_user.Gebruiker_ID)
        .first()
        is not None
    )
    if not is_student and not is_personeel:
        raise HTTPException(
            status_code=403,
            detail="RSVP is slegs vir studente en personeel beskikbaar",
        )


def _event_or_404(db: Session, event_id: int) -> models.Funksie:
    event = (
        db.query(models.Funksie)
        .filter(models.Funksie.Funksie_ID == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event nie gevind nie")
    return event


def _confirmed_count(db: Session, event_id: int) -> int:
    return int(
        db.query(func.count(models.FunksieRSVP.Gebruiker_ID))
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.RSVP_Status == "GAAN",
        )
        .scalar()
        or 0
    )


def _validate_location(db: Session, kampus_id: int, lokasie_id: Optional[int]) -> None:
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if kampus is None:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    if lokasie_id is None:
        return

    lokasie = (
        db.query(models.Lokasie)
        .filter(models.Lokasie.Lokasie_ID == lokasie_id)
        .first()
    )
    if lokasie is None:
        raise HTTPException(status_code=404, detail="Lokaal/lokasie nie gevind nie")
    if lokasie.Kampus_ID != kampus_id:
        raise HTTPException(status_code=400, detail="Die gekose lokaal behoort nie aan dié kampus nie")


def _validate_times(begin_tyd: datetime, eind_tyd: datetime) -> None:
    if eind_tyd <= begin_tyd:
        raise HTTPException(status_code=400, detail="Event se eindtyd moet ná die begintyd wees")


def _my_rsvp(db: Session, event_id: int, user_id: int) -> Optional[str]:
    row = (
        db.query(models.FunksieRSVP)
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.Gebruiker_ID == user_id,
        )
        .first()
    )
    return row.RSVP_Status if row is not None else None


def _event_dict(db: Session, event: models.Funksie, current_user_id: int) -> dict:
    rsvp_count = _confirmed_count(db, event.Funksie_ID)
    capacity = int(event.FUN_Kapasiteit or 0)
    campus = event.kampus
    location = event.lokasie
    creator = event.geskep_deur
    my_status = _my_rsvp(db, event.Funksie_ID, current_user_id)

    return {
        "event_id": event.Funksie_ID,
        "naam": event.FUN_Naam,
        "kampus_id": event.Kampus_ID,
        "kampus_naam": campus.KAM_Naam if campus else "Onbekende kampus",
        "lokasie_id": event.Lokasie_ID,
        "lokasie_naam": location.LOK_Naam if location else None,
        "begin_tyd": _iso_utc(event.FUN_Begin_Tyd),
        "eind_tyd": _iso_utc(event.FUN_Eind_Tyd),
        "beskrywing": event.FUN_Beskrywing,
        "kapasiteit": capacity,
        "rsvp_aantal": rsvp_count,
        "plekke_oor": max(capacity - rsvp_count, 0),
        "vol": rsvp_count >= capacity if capacity > 0 else True,
        "status": event.FUN_Status or ("AKTIEF" if event.FUN_Is_Aktief else "GEKANSELLEER"),
        "is_aktief": bool(event.FUN_Is_Aktief),
        "my_rsvp": my_status,
        "geskep_op": _iso_utc(event.Geskep_Op),
        "geskep_deur": None if creator is None else {
            "gebruiker_id": creator.Gebruiker_ID,
            "volle_naam": f"{creator.GEB_Naam} {creator.GEB_Van}".strip(),
        },
    }


@router.get("")
def list_events(
    view: str = Query("komende"),
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_active(current_user)
    view = view.strip().lower()
    if view not in {"komende", "my", "vorige"}:
        raise HTTPException(status_code=400, detail="Ongeldige event-filter")

    now = datetime.utcnow()
    query = db.query(models.Funksie)

    if view == "komende":
        query = query.filter(
            models.Funksie.FUN_Is_Aktief.is_(True),
            models.Funksie.FUN_Status == "AKTIEF",
            models.Funksie.FUN_Eind_Tyd >= now,
        )
    elif view == "vorige":
        query = query.filter(models.Funksie.FUN_Eind_Tyd < now)
    else:
        query = (
            query.join(
                models.FunksieRSVP,
                models.FunksieRSVP.Funksie_ID == models.Funksie.Funksie_ID,
            )
            .filter(
                models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
                models.FunksieRSVP.RSVP_Status == "GAAN",
                models.Funksie.FUN_Status == "AKTIEF",
                models.Funksie.FUN_Eind_Tyd >= now,
            )
        )

    events = query.order_by(models.Funksie.FUN_Begin_Tyd.asc()).all()
    return {
        "sukses": True,
        "data": [_event_dict(db, event, current_user.Gebruiker_ID) for event in events],
        "fout": None,
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

    return {
        "sukses": True,
        "data": _event_dict(db, event, current_user.Gebruiker_ID),
        "fout": None,
    }


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
    # Die Flutter edit-vorm stuur altyd kampus_id. Indien lokasie_id dan null is,
    # beteken dit doelbewus “geen lokaal/area”.
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
            raise HTTPException(
                status_code=400,
                detail=f"Kapasiteit kan nie laer as die huidige {confirmed} bevestigde RSVP's wees nie",
            )
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

    return {
        "sukses": True,
        "data": _event_dict(db, event, current_user.Gebruiker_ID),
        "fout": None,
    }


@router.post("/{event_id}/kanselleer")
def cancel_event(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)
    event.FUN_Status = "GEKANSELLEER"
    event.FUN_Is_Aktief = False
    event.Gewysig_Op = datetime.utcnow()
    db.commit()
    db.refresh(event)

    return {
        "sukses": True,
        "data": _event_dict(db, event, current_user.Gebruiker_ID),
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
    event = _event_or_404(db, event_id)

    if payload.status.strip().upper() != "GAAN":
        raise HTTPException(status_code=400, detail="Gebruik GAAN vir 'n bevestigde RSVP")
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF":
        raise HTTPException(status_code=400, detail="Hierdie event is nie meer aktief nie")
    if event.FUN_Eind_Tyd < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Hierdie event is reeds verby")

    existing = (
        db.query(models.FunksieRSVP)
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )

    if existing is not None and existing.RSVP_Status == "GAAN":
        return {
            "sukses": True,
            "data": _event_dict(db, event, current_user.Gebruiker_ID),
            "fout": None,
        }

    confirmed = _confirmed_count(db, event_id)
    if confirmed >= int(event.FUN_Kapasiteit or 0):
        raise HTTPException(status_code=409, detail="Event is vol")

    if existing is None:
        existing = models.FunksieRSVP(
            Funksie_ID=event_id,
            Gebruiker_ID=current_user.Gebruiker_ID,
            RSVP_Status="GAAN",
            RSVP_Tyd=datetime.utcnow(),
        )
        db.add(existing)
    else:
        existing.RSVP_Status = "GAAN"
        existing.RSVP_Tyd = datetime.utcnow()
        existing.Gewysig_Op = datetime.utcnow()

    db.commit()

    return {
        "sukses": True,
        "data": _event_dict(db, event, current_user.Gebruiker_ID),
        "fout": None,
    }


@router.delete("/{event_id}/rsvp")
def cancel_rsvp(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_rsvp_user(db, current_user)
    event = _event_or_404(db, event_id)

    row = (
        db.query(models.FunksieRSVP)
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    if row is None or row.RSVP_Status != "GAAN":
        raise HTTPException(status_code=400, detail="Jy het nie 'n aktiewe RSVP vir hierdie event nie")

    row.RSVP_Status = "GEKANSELLEER"
    row.Gewysig_Op = datetime.utcnow()
    db.commit()

    return {
        "sukses": True,
        "data": _event_dict(db, event, current_user.Gebruiker_ID),
        "fout": None,
    }


@router.get("/{event_id}/rsvps")
def event_rsvps(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_opsigter(db, current_user)
    event = _event_or_404(db, event_id)

    rows = (
        db.query(models.FunksieRSVP, models.Gebruikers)
        .join(models.Gebruikers, models.Gebruikers.Gebruiker_ID == models.FunksieRSVP.Gebruiker_ID)
        .filter(
            models.FunksieRSVP.Funksie_ID == event_id,
            models.FunksieRSVP.RSVP_Status == "GAAN",
        )
        .order_by(models.FunksieRSVP.RSVP_Tyd.asc())
        .all()
    )

    items = []
    for rsvp, user in rows:
        if user.student is not None:
            role = "Student"
            number = user.student.STU_Nommer
        elif user.personeel is not None:
            role = "Personeel"
            number = user.personeel.PER_Nommer
        else:
            role = "Gebruiker"
            number = ""
        items.append({
            "gebruiker_id": user.Gebruiker_ID,
            "volle_naam": f"{user.GEB_Naam} {user.GEB_Van}".strip(),
            "rol": role,
            "nommer": number,
            "rsvp_tyd": _iso_utc(rsvp.RSVP_Tyd),
        })

    return {
        "sukses": True,
        "data": {
            "event": _event_dict(db, event, current_user.Gebruiker_ID),
            "rsvps": items,
            "rsvp_aantal": len(items),
        },
        "fout": None,
    }
