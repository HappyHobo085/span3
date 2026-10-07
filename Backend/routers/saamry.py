"""MOON Saamry API — permanente groepe, eenmalige rit-events en chat.

Kernreëls:
- 'n SaamryGroep is permanent en kan herhaaldelik gebruik word.
- Die huidige Bestuurder is die groep se Admin.
- Net die huidige Bestuurder kan die Driver/Admin-rol aan 'n aanvaarde lid oorgee.
- 'n SaamryEvent is 'n eenmalige groepsrit. Geen tydvenster bepaal die event nie.
- Sodra die Driver se hek-scan suksesvol gecommit is, word die event VOLTOOI.
- Daarna val alle lede terug na normale individuele kampus-skandering.
- Privaat chat is slegs vir aanvaarde vriende; groepchat slegs vir aanvaarde groepslede.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError, jwt
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas
from services.compatibiliteit_service import (
    vind_saamry_voorstelle,
    bou_student_saamry_data_van_db,
    bereken_saamry_versoenbaarheid,
)


router = APIRouter(prefix="/saamry", tags=["Saamry"])
CHAT_WS_INTERVAL_SECONDS = 1.0


# ---------------------------------------------------------------------------
# Algemene helpers
# ---------------------------------------------------------------------------

def _require_saamry_user(db: Session, current_user: models.Gebruikers) -> None:
    """Saamry is beskikbaar vir aktiewe studente en personeel."""
    if current_user is None or not current_user.Is_Aktief:
        raise HTTPException(status_code=403, detail="Jou gebruiker is nie aktief nie")

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
            detail="Saamry is slegs vir studente en personeel beskikbaar",
        )


def _user_dict(user: models.Gebruikers, *, include_contact: bool = False) -> dict:
    student = user.student
    personeel = user.personeel
    if student is not None:
        rol = "Student"
        nommer = student.STU_Nommer
    elif personeel is not None:
        rol = "Personeel"
        nommer = personeel.PER_Nommer
    else:
        rol = "Gebruiker"
        nommer = ""

    data = {
        "gebruiker_id": user.Gebruiker_ID,
        "naam": user.GEB_Naam,
        "van": user.GEB_Van,
        "volle_naam": f"{user.GEB_Naam} {user.GEB_Van}".strip(),
        "nommer": nommer,
        "rol": rol,
        "foto_url": user.GEB_Profiel_Foto,
    }
    if include_contact:
        data["selfoon"] = user.GEB_Selfoon_Nr
        data["epos"] = user.GEB_Epos
    return data


def _friendship_between(
    db: Session,
    user_a_id: int,
    user_b_id: int,
) -> Optional[models.SaamryVriendskap]:
    return (
        db.query(models.SaamryVriendskap)
        .filter(
            or_(
                and_(
                    models.SaamryVriendskap.Versoeker_ID == user_a_id,
                    models.SaamryVriendskap.Ontvanger_ID == user_b_id,
                ),
                and_(
                    models.SaamryVriendskap.Versoeker_ID == user_b_id,
                    models.SaamryVriendskap.Ontvanger_ID == user_a_id,
                ),
            )
        )
        .first()
    )


def _friendship_status(
    friendship: Optional[models.SaamryVriendskap],
    current_user_id: int,
) -> str:
    if friendship is None:
        return "GEEN"
    if friendship.SAA_Status == "AANVAAR":
        return "VRIEND"
    if friendship.SAA_Status == "HANGEND":
        return (
            "HANGEND_UIT"
            if friendship.Versoeker_ID == current_user_id
            else "HANGEND_IN"
        )
    return friendship.SAA_Status


def _require_accepted_friend(
    db: Session,
    current_user_id: int,
    friend_id: int,
) -> models.SaamryVriendskap:
    friendship = _friendship_between(db, current_user_id, friend_id)
    if friendship is None or friendship.SAA_Status != "AANVAAR":
        raise HTTPException(
            status_code=403,
            detail="Privaat Saamry-boodskappe is slegs tussen aanvaarde vriende beskikbaar",
        )
    return friendship


def _viewer_is_accepted_member(group: models.SaamryGroep, viewer_id: int) -> bool:
    if group.Bestuurder_ID == viewer_id:
        return True
    return any(
        member.Gebruiker_ID == viewer_id and member.SAA_Status == "AANVAAR"
        for member in group.lede
    )


def _require_group_member(
    group: models.SaamryGroep,
    viewer_id: int,
) -> None:
    if not _viewer_is_accepted_member(group, viewer_id):
        raise HTTPException(status_code=403, detail="Jy behoort nie aan hierdie Saamrygroep nie")


def _get_group_or_404(db: Session, group_id: int) -> models.SaamryGroep:
    group = (
        db.query(models.SaamryGroep)
        .filter(models.SaamryGroep.Groep_ID == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Saamrygroep is nie gevind nie")
    return group


def _pickup_profile_for_user(
    db: Session,
    user_id: int,
) -> Optional[models.SaamryPickupProfiel]:
    return (
        db.query(models.SaamryPickupProfiel)
        .filter(models.SaamryPickupProfiel.Gebruiker_ID == user_id)
        .first()
    )


def _pickup_profile_dict(profile: models.SaamryPickupProfiel) -> dict:
    return {
        "gebruiker_id": profile.Gebruiker_ID,
        "latitude": profile.Pickup_Latitude,
        "longitude": profile.Pickup_Longitude,
        "beskrywing": profile.Pickup_Beskrywing,
        "gewysig_op": profile.Gewysig_Op.isoformat() if profile.Gewysig_Op else None,
    }


def _upsert_pickup_profile(
    db: Session,
    user_id: int,
    latitude: float,
    longitude: float,
    beskrywing: str,
) -> models.SaamryPickupProfiel:
    clean = beskrywing.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="'n Geldige pickup-adres is nodig")
    profile = _pickup_profile_for_user(db, user_id)
    now = datetime.utcnow()
    if profile is None:
        profile = models.SaamryPickupProfiel(
            Gebruiker_ID=user_id,
            Pickup_Latitude=latitude,
            Pickup_Longitude=longitude,
            Pickup_Beskrywing=clean,
            Geskep_Op=now,
            Gewysig_Op=now,
        )
        db.add(profile)
    else:
        profile.Pickup_Latitude = latitude
        profile.Pickup_Longitude = longitude
        profile.Pickup_Beskrywing = clean
        profile.Gewysig_Op = now
    return profile


def _accepted_passenger_count(group: models.SaamryGroep) -> int:
    return sum(
        1
        for member in group.lede
        if member.Gebruiker_ID != group.Bestuurder_ID
        and member.SAA_Status == "AANVAAR"
    )


def _active_event_for_group(db: Session, group_id: int) -> Optional[models.SaamryEvent]:
    return (
        db.query(models.SaamryEvent)
        .filter(
            models.SaamryEvent.Groep_ID == group_id,
            models.SaamryEvent.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryEvent.Event_ID.desc())
        .first()
    )


def _active_event_for_driver(db: Session, driver_id: int) -> Optional[models.SaamryEvent]:
    return (
        db.query(models.SaamryEvent)
        .filter(
            models.SaamryEvent.Bestuurder_ID == driver_id,
            models.SaamryEvent.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryEvent.Event_ID.desc())
        .first()
    )


def _active_event_for_user(db: Session, user_id: int) -> Optional[models.SaamryEvent]:
    return (
        db.query(models.SaamryEvent)
        .join(
            models.SaamryEventLid,
            models.SaamryEventLid.Event_ID == models.SaamryEvent.Event_ID,
        )
        .filter(
            models.SaamryEventLid.Gebruiker_ID == user_id,
            models.SaamryEvent.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryEvent.Event_ID.desc())
        .first()
    )


def _event_dict(event: models.SaamryEvent, viewer_id: int) -> dict:
    viewer_is_participant = any(
        event_member.Gebruiker_ID == viewer_id
        for event_member in event.lede
    )
    members = []
    pickup_ready = 0
    for event_member in event.lede:
        if event_member.gebruiker is None:
            continue
        pickup_available = (
            event_member.Pickup_Latitude is not None
            and event_member.Pickup_Longitude is not None
        )
        pickup_set = bool(pickup_available and event_member.Pickup_Bevestig)
        if pickup_set:
            pickup_ready += 1

        # 'n Passasier mag sy/haar eie vooraf-ingevulde gewone adres sien om dit
        # te bevestig/verander. Die Driver sien 'n passasier se presiese adres
        # eers nadat daardie passasier dit vir die event bevestig het.
        can_view_pin = bool(
            pickup_available
            and viewer_is_participant
            and (
                event_member.Gebruiker_ID == viewer_id
                or (
                    event_member.Gebruiker_ID == event.Bestuurder_ID
                    and event_member.Pickup_Bevestig
                )
                or (
                    viewer_id == event.Bestuurder_ID
                    and event_member.Pickup_Bevestig
                )
            )
        )
        members.append(
            {
                "is_bestuurder": event_member.Gebruiker_ID == event.Bestuurder_ID,
                "is_myne": event_member.Gebruiker_ID == viewer_id,
                "pickup_gestel": pickup_set,
                "pickup_latitude": (
                    event_member.Pickup_Latitude if can_view_pin else None
                ),
                "pickup_longitude": (
                    event_member.Pickup_Longitude if can_view_pin else None
                ),
                "pickup_beskrywing": (
                    event_member.Pickup_Beskrywing if can_view_pin else None
                ),
                "pickup_gewysig_op": (
                    event_member.Pickup_Gewysig_Op.isoformat()
                    if can_view_pin and event_member.Pickup_Gewysig_Op
                    else None
                ),
                "gebruiker": _user_dict(event_member.gebruiker, include_contact=True),
            }
        )
    members.sort(
        key=lambda item: (
            not item["is_bestuurder"],
            item["gebruiker"]["volle_naam"].lower(),
        )
    )
    return {
        "event_id": event.Event_ID,
        "groep_id": event.Groep_ID,
        "bestuurder_id": event.Bestuurder_ID,
        "status": event.SAA_Status,
        "is_bestuurder": event.Bestuurder_ID == viewer_id,
        "is_deelnemer": viewer_is_participant,
        "pickup_gereed": pickup_ready,
        "pickup_totaal": len(members),
        "geskep_op": event.Geskep_Op.isoformat() if event.Geskep_Op else None,
        "voltooi_op": event.Voltooi_Op.isoformat() if event.Voltooi_Op else None,
        "voltooi_rigting": event.Voltooi_Rigting,
        "voltooi_kampus_id": event.Voltooi_Kampus_ID,
        "lede": members,
    }


def _read_message_ids_for_user(
    db: Session,
    message_ids: list[int],
    user_id: int,
) -> set[int]:
    if not message_ids:
        return set()
    rows = (
        db.query(models.SaamryBoodskapGelees.Boodskap_ID)
        .filter(
            models.SaamryBoodskapGelees.Gebruiker_ID == user_id,
            models.SaamryBoodskapGelees.Boodskap_ID.in_(message_ids),
        )
        .all()
    )
    return {int(row[0]) for row in rows}


def _unread_private_count(db: Session, viewer_id: int, friend_id: int) -> int:
    rows = (
        db.query(models.SaamryBoodskap.Boodskap_ID)
        .filter(
            models.SaamryBoodskap.Groep_ID.is_(None),
            models.SaamryBoodskap.Stuurder_ID == friend_id,
            models.SaamryBoodskap.Ontvanger_ID == viewer_id,
        )
        .all()
    )
    ids = [int(row[0]) for row in rows]
    read_ids = _read_message_ids_for_user(db, ids, viewer_id)
    return len([message_id for message_id in ids if message_id not in read_ids])


def _unread_group_count(db: Session, viewer_id: int, group_id: int) -> int:
    rows = (
        db.query(models.SaamryBoodskap.Boodskap_ID)
        .filter(
            models.SaamryBoodskap.Groep_ID == group_id,
            models.SaamryBoodskap.Stuurder_ID != viewer_id,
        )
        .all()
    )
    ids = [int(row[0]) for row in rows]
    read_ids = _read_message_ids_for_user(db, ids, viewer_id)
    return len([message_id for message_id in ids if message_id not in read_ids])


def _group_dict(db: Session, group: models.SaamryGroep, viewer_id: int) -> dict:
    viewer_accepted = _viewer_is_accepted_member(group, viewer_id)
    my_member = next(
        (member for member in group.lede if member.Gebruiker_ID == viewer_id),
        None,
    )
    visible_members = [
        member
        for member in group.lede
        if member.SAA_Status in ("HANGEND", "AANVAAR")
    ]
    reserved_count = sum(
        1
        for member in group.lede
        if member.Gebruiker_ID != group.Bestuurder_ID
        and member.SAA_Status in ("HANGEND", "AANVAAR")
    )
    active_event = _active_event_for_group(db, group.Groep_ID) if viewer_accepted else None

    return {
        "groep_id": group.Groep_ID,
        "naam": group.SAA_Naam,
        # Legacy velde word teruggestuur vir ou kliënte, maar is nie meer die rit nie.
        "vertrekpunt": group.SAA_Vertrekpunt,
        "bestemming": group.SAA_Bestemming,
        "vertrek_tyd": group.SAA_Vertrek_Tyd.isoformat() if group.SAA_Vertrek_Tyd else None,
        "sitplekke": group.SAA_Sitplekke,
        "beskikbare_sitplekke": max(group.SAA_Sitplekke - reserved_count, 0),
        "status": group.SAA_Status,
        "is_bestuurder": group.Bestuurder_ID == viewer_id,
        "my_status": "AANVAAR" if group.Bestuurder_ID == viewer_id else (
            my_member.SAA_Status if my_member else None
        ),
        "bestuurder": _user_dict(group.bestuurder, include_contact=viewer_accepted),
        "lede": [
            {
                "status": member.SAA_Status,
                "is_bestuurder": member.Gebruiker_ID == group.Bestuurder_ID,
                "gebruiker": _user_dict(
                    member.gebruiker,
                    include_contact=viewer_accepted,
                ),
            }
            for member in visible_members
            if member.gebruiker is not None
        ],
        "aktiewe_event": _event_dict(active_event, viewer_id) if active_event else None,
        "ongelees": _unread_group_count(db, viewer_id, group.Groep_ID) if viewer_accepted else 0,
    }


# ---------------------------------------------------------------------------
# Dashboard/status
# ---------------------------------------------------------------------------

@router.get("/status")
def get_saamry_status(
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    user_id = current_user.Gebruiker_ID

    friendships = (
        db.query(models.SaamryVriendskap)
        .filter(
            or_(
                models.SaamryVriendskap.Versoeker_ID == user_id,
                models.SaamryVriendskap.Ontvanger_ID == user_id,
            )
        )
        .order_by(models.SaamryVriendskap.Geskep_Op.desc())
        .all()
    )

    friends = []
    incoming_requests = []
    outgoing_requests = []
    for friendship in friendships:
        other = (
            friendship.ontvanger
            if friendship.Versoeker_ID == user_id
            else friendship.versoeker
        )
        item = {
            "vriendskap_id": friendship.Vriendskap_ID,
            "status": friendship.SAA_Status,
            "gebruiker": _user_dict(other),
            "ongelees": (
                _unread_private_count(db, user_id, other.Gebruiker_ID)
                if friendship.SAA_Status == "AANVAAR"
                else 0
            ),
        }
        if friendship.SAA_Status == "AANVAAR":
            friends.append(item)
        elif friendship.SAA_Status == "HANGEND":
            if friendship.Ontvanger_ID == user_id:
                incoming_requests.append(item)
            else:
                outgoing_requests.append(item)

    groups = (
        db.query(models.SaamryGroep)
        .join(
            models.SaamryGroepLid,
            models.SaamryGroepLid.Groep_ID == models.SaamryGroep.Groep_ID,
        )
        .filter(
            models.SaamryGroepLid.Gebruiker_ID == user_id,
            models.SaamryGroepLid.SAA_Status == "AANVAAR",
            models.SaamryGroep.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryGroep.Geskep_Op.desc())
        .all()
    )

    group_invite_members = (
        db.query(models.SaamryGroepLid)
        .join(models.SaamryGroep)
        .filter(
            models.SaamryGroepLid.Gebruiker_ID == user_id,
            models.SaamryGroepLid.SAA_Status == "HANGEND",
            models.SaamryGroep.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryGroepLid.Geskep_Op.desc())
        .all()
    )

    group_dicts = [_group_dict(db, group, user_id) for group in groups]
    return schemas.APIResponse(
        sukses=True,
        data={
            "friends": friends,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
            "group_invites": [
                _group_dict(db, member.groep, user_id)
                for member in group_invite_members
            ],
            "groups": group_dicts,
            # Backwards compatibility vir die ou enkel-groep Flutter DTO.
            "my_group": group_dicts[0] if group_dicts else None,
        },
    )


# ---------------------------------------------------------------------------
# Vriende
# ---------------------------------------------------------------------------

@router.get("/gebruikers/search")
def search_saamry_users(
    q: str = Query(..., min_length=2, max_length=100),
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    clean = q.strip()

    users = (
        db.query(models.Gebruikers)
        .outerjoin(models.Student)
        .outerjoin(models.Personeel)
        .filter(
            models.Gebruikers.Is_Aktief.is_(True),
            models.Gebruikers.Gebruiker_ID != current_user.Gebruiker_ID,
            or_(
                models.Student.Gebruiker_ID.isnot(None),
                models.Personeel.Gebruiker_ID.isnot(None),
            ),
            or_(
                models.Gebruikers.GEB_Naam.ilike(f"%{clean}%"),
                models.Gebruikers.GEB_Van.ilike(f"%{clean}%"),
                models.Gebruikers.GEB_ID_Nommer.ilike(f"%{clean}%"),
                models.Student.STU_Nommer.ilike(f"%{clean}%"),
                models.Personeel.PER_Nommer.ilike(f"%{clean}%"),
            ),
        )
        .order_by(models.Gebruikers.GEB_Naam, models.Gebruikers.GEB_Van)
        .limit(30)
        .all()
    )

    data = []
    for user in users:
        friendship = _friendship_between(
            db,
            current_user.Gebruiker_ID,
            user.Gebruiker_ID,
        )
        item = _user_dict(user)
        item["vriendskap_status"] = _friendship_status(
            friendship,
            current_user.Gebruiker_ID,
        )
        item["vriendskap_id"] = friendship.Vriendskap_ID if friendship else None
        data.append(item)

    return schemas.APIResponse(sukses=True, data=data)


@router.post("/vriende/versoek", status_code=status.HTTP_201_CREATED)
def send_friend_request(
    payload: schemas.SaamryVriendVersoekCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    if payload.ontvanger_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy kan nie jouself byvoeg nie")

    receiver = (
        db.query(models.Gebruikers)
        .filter(
            models.Gebruikers.Gebruiker_ID == payload.ontvanger_id,
            models.Gebruikers.Is_Aktief.is_(True),
        )
        .first()
    )
    if not receiver:
        raise HTTPException(status_code=404, detail="Gebruiker is nie gevind nie")
    if receiver.student is None and receiver.personeel is None:
        raise HTTPException(status_code=400, detail="Gebruiker kan nie Saamry gebruik nie")

    friendship = _friendship_between(
        db,
        current_user.Gebruiker_ID,
        payload.ontvanger_id,
    )
    if friendship:
        if friendship.SAA_Status == "AANVAAR":
            raise HTTPException(status_code=409, detail="Hierdie gebruiker is reeds jou vriend")
        if friendship.SAA_Status == "HANGEND":
            raise HTTPException(status_code=409, detail="Daar is reeds 'n hangende versoek")
        friendship.Versoeker_ID = current_user.Gebruiker_ID
        friendship.Ontvanger_ID = payload.ontvanger_id
        friendship.SAA_Status = "HANGEND"
        friendship.Gewysig_Op = datetime.utcnow()
    else:
        friendship = models.SaamryVriendskap(
            Versoeker_ID=current_user.Gebruiker_ID,
            Ontvanger_ID=payload.ontvanger_id,
            SAA_Status="HANGEND",
        )
        db.add(friendship)

    db.commit()
    db.refresh(friendship)
    return schemas.APIResponse(
        sukses=True,
        data={
            "vriendskap_id": friendship.Vriendskap_ID,
            "boodskap": "Vriendskapversoek is gestuur",
        },
    )


@router.post("/vriende/{vriendskap_id}/aanvaar")
def accept_friend_request(
    vriendskap_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    friendship = (
        db.query(models.SaamryVriendskap)
        .filter(models.SaamryVriendskap.Vriendskap_ID == vriendskap_id)
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="Vriendskapversoek is nie gevind nie")
    if friendship.Ontvanger_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Jy mag nie hierdie versoek aanvaar nie")
    if friendship.SAA_Status != "HANGEND":
        raise HTTPException(status_code=409, detail="Hierdie versoek is nie meer hangend nie")
    friendship.SAA_Status = "AANVAAR"
    friendship.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Vriend aanvaar"})


@router.post("/vriende/{vriendskap_id}/weier")
def decline_friend_request(
    vriendskap_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    friendship = (
        db.query(models.SaamryVriendskap)
        .filter(models.SaamryVriendskap.Vriendskap_ID == vriendskap_id)
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="Vriendskapversoek is nie gevind nie")
    if friendship.Ontvanger_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Jy mag nie hierdie versoek weier nie")
    friendship.SAA_Status = "GEWEIER"
    friendship.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Versoek geweier"})


@router.delete("/vriende/{vriend_id}")
def remove_friend(
    vriend_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    friendship = _friendship_between(db, current_user.Gebruiker_ID, vriend_id)
    if not friendship or friendship.SAA_Status != "AANVAAR":
        raise HTTPException(status_code=404, detail="Vriendskap is nie gevind nie")
    db.delete(friendship)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Vriend verwyder"})


# ---------------------------------------------------------------------------
# Permanente groepe
# ---------------------------------------------------------------------------

@router.post("/groepe", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: schemas.SaamryGroepCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group_name = (payload.naam or "").strip()
    if not group_name:
        raise HTTPException(status_code=400, detail="Gee die permanente Saamrygroep 'n naam")

    # Die bestaande DB-kolomme bly vir backwards compatibility, maar 'n permanente
    # groep se ritbesonderhede leef voortaan in SaamryEvent, nie op die groep nie.
    group = models.SaamryGroep(
        Bestuurder_ID=current_user.Gebruiker_ID,
        SAA_Naam=group_name,
        SAA_Vertrekpunt=(payload.vertrekpunt or "-").strip() or "-",
        SAA_Bestemming=(payload.bestemming or "-").strip() or "-",
        SAA_Vertrek_Tyd=payload.vertrek_tyd or datetime.utcnow(),
        SAA_Sitplekke=payload.sitplekke,
        SAA_Status="AKTIEF",
    )
    db.add(group)
    db.flush()
    db.add(
        models.SaamryGroepLid(
            Groep_ID=group.Groep_ID,
            Gebruiker_ID=current_user.Gebruiker_ID,
            Genooi_Deur_ID=current_user.Gebruiker_ID,
            SAA_Status="AANVAAR",
        )
    )
    db.commit()
    db.refresh(group)
    return schemas.APIResponse(
        sukses=True,
        data=_group_dict(db, group, current_user.Gebruiker_ID),
    )


@router.post("/groepe/{groep_id}/nooi", status_code=status.HTTP_201_CREATED)
def invite_friend_to_group(
    groep_id: int,
    payload: schemas.SaamryGroepNooiCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)
    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Slegs die Driver/Admin kan vriende nooi")
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie groep is nie meer aktief nie")
    if payload.gebruiker_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy is reeds die Driver/Admin")

    friendship = _friendship_between(
        db,
        current_user.Gebruiker_ID,
        payload.gebruiker_id,
    )
    if not friendship or friendship.SAA_Status != "AANVAAR":
        raise HTTPException(status_code=400, detail="Jy kan net 'n aanvaarde vriend nooi")

    existing_member = (
        db.query(models.SaamryGroepLid)
        .filter(
            models.SaamryGroepLid.Groep_ID == groep_id,
            models.SaamryGroepLid.Gebruiker_ID == payload.gebruiker_id,
        )
        .first()
    )
    if existing_member and existing_member.SAA_Status in ("HANGEND", "AANVAAR"):
        raise HTTPException(status_code=409, detail="Hierdie persoon is reeds genooi")

    occupied_or_pending = sum(
        1
        for member in group.lede
        if member.Gebruiker_ID != group.Bestuurder_ID
        and member.SAA_Status in ("HANGEND", "AANVAAR")
    )
    if occupied_or_pending >= group.SAA_Sitplekke:
        raise HTTPException(status_code=409, detail="Die permanente groep is reeds vol")

    if existing_member:
        existing_member.SAA_Status = "HANGEND"
        existing_member.Genooi_Deur_ID = current_user.Gebruiker_ID
        existing_member.Gewysig_Op = datetime.utcnow()
    else:
        db.add(
            models.SaamryGroepLid(
                Groep_ID=groep_id,
                Gebruiker_ID=payload.gebruiker_id,
                Genooi_Deur_ID=current_user.Gebruiker_ID,
                SAA_Status="HANGEND",
            )
        )
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Saamry-uitnodiging gestuur"})


@router.post("/groepe/{groep_id}/aanvaar")
def accept_group_invite(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)
    member = (
        db.query(models.SaamryGroepLid)
        .filter(
            models.SaamryGroepLid.Groep_ID == groep_id,
            models.SaamryGroepLid.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    if not member or member.SAA_Status != "HANGEND":
        raise HTTPException(status_code=404, detail="Uitnodiging is nie gevind nie")
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie groep is nie meer aktief nie")
    if _accepted_passenger_count(group) >= group.SAA_Sitplekke:
        raise HTTPException(status_code=409, detail="Die groep is reeds vol")
    member.SAA_Status = "AANVAAR"
    member.Gewysig_Op = datetime.utcnow()

    # 'n Nuwe groepslid moet nie ou groepchat-boodskappe as ongelees erf nie.
    existing_messages = (
        db.query(models.SaamryBoodskap)
        .filter(models.SaamryBoodskap.Groep_ID == groep_id)
        .all()
    )
    existing_read = _read_message_ids_for_user(
        db,
        [message.Boodskap_ID for message in existing_messages],
        current_user.Gebruiker_ID,
    )
    for message in existing_messages:
        if (
            message.Stuurder_ID == current_user.Gebruiker_ID
            or message.Boodskap_ID in existing_read
        ):
            continue
        db.add(
            models.SaamryBoodskapGelees(
                Boodskap_ID=message.Boodskap_ID,
                Gebruiker_ID=current_user.Gebruiker_ID,
            )
        )

    db.commit()
    db.refresh(group)
    return schemas.APIResponse(
        sukses=True,
        data=_group_dict(db, group, current_user.Gebruiker_ID),
    )


@router.post("/groepe/{groep_id}/weier")
def decline_group_invite(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    member = (
        db.query(models.SaamryGroepLid)
        .filter(
            models.SaamryGroepLid.Groep_ID == groep_id,
            models.SaamryGroepLid.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    if not member or member.SAA_Status != "HANGEND":
        raise HTTPException(status_code=404, detail="Uitnodiging is nie gevind nie")
    member.SAA_Status = "GEWEIER"
    member.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Uitnodiging geweier"})


@router.post("/groepe/{groep_id}/bestuurder")
def transfer_driver_admin(
    groep_id: int,
    payload: schemas.SaamryBestuurderOordragRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)
    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(
            status_code=403,
            detail="Net die huidige Driver/Admin kan die rol oorgee",
        )
    if payload.nuwe_bestuurder_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy is reeds die Driver/Admin")

    target_member = (
        db.query(models.SaamryGroepLid)
        .filter(
            models.SaamryGroepLid.Groep_ID == groep_id,
            models.SaamryGroepLid.Gebruiker_ID == payload.nuwe_bestuurder_id,
            models.SaamryGroepLid.SAA_Status == "AANVAAR",
        )
        .first()
    )
    if target_member is None:
        raise HTTPException(
            status_code=400,
            detail="Die nuwe Driver/Admin moet 'n aanvaarde lid van die groep wees",
        )

    event = _active_event_for_group(db, groep_id)
    if event is not None:
        other_event = _active_event_for_driver(db, payload.nuwe_bestuurder_id)
        if other_event is not None and other_event.Event_ID != event.Event_ID:
            raise HTTPException(
                status_code=409,
                detail="Hierdie lid is reeds Driver van 'n ander aktiewe Saamry-event",
            )
        # Die huidige aktiewe event volg die nuwe Driver/Admin.
        event.Bestuurder_ID = payload.nuwe_bestuurder_id
        event.Gewysig_Op = datetime.utcnow()
        event_member = (
            db.query(models.SaamryEventLid)
            .filter(
                models.SaamryEventLid.Event_ID == event.Event_ID,
                models.SaamryEventLid.Gebruiker_ID == payload.nuwe_bestuurder_id,
            )
            .first()
        )
        if event_member is None:
            db.add(
                models.SaamryEventLid(
                    Event_ID=event.Event_ID,
                    Gebruiker_ID=payload.nuwe_bestuurder_id,
                )
            )

    group.Bestuurder_ID = payload.nuwe_bestuurder_id
    group.Gewysig_Op = datetime.utcnow()
    db.commit()
    db.refresh(group)
    return schemas.APIResponse(
        sukses=True,
        data={
            "boodskap": "Driver/Admin is suksesvol oorgedra",
            "groep": _group_dict(db, group, current_user.Gebruiker_ID),
        },
    )


@router.post("/groepe/{groep_id}/sluit")
def close_group(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)
    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Slegs die Driver/Admin kan die groep sluit")
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie groep is reeds gesluit")

    event = _active_event_for_group(db, groep_id)
    if event is not None:
        event.SAA_Status = "GEKANSELLEER"
        event.Voltooi_Op = datetime.utcnow()
        event.Gewysig_Op = datetime.utcnow()

    group.SAA_Status = "GESLUIT"
    group.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Permanente Saamrygroep is gesluit"})


@router.post("/groepe/{groep_id}/verlaat")
def leave_group(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)
    if group.Bestuurder_ID == current_user.Gebruiker_ID:
        raise HTTPException(
            status_code=400,
            detail="Gee eers die Driver/Admin-rol aan 'n ander lid oor of sluit die groep",
        )
    member = (
        db.query(models.SaamryGroepLid)
        .filter(
            models.SaamryGroepLid.Groep_ID == groep_id,
            models.SaamryGroepLid.Gebruiker_ID == current_user.Gebruiker_ID,
            models.SaamryGroepLid.SAA_Status == "AANVAAR",
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Jy behoort nie aan hierdie groep nie")

    event = _active_event_for_group(db, groep_id)
    if event is not None:
        event_member = (
            db.query(models.SaamryEventLid)
            .filter(
                models.SaamryEventLid.Event_ID == event.Event_ID,
                models.SaamryEventLid.Gebruiker_ID == current_user.Gebruiker_ID,
            )
            .first()
        )
        if event_member is not None:
            db.delete(event_member)
            db.flush()
            remaining = (
                db.query(models.SaamryEventLid)
                .filter(models.SaamryEventLid.Event_ID == event.Event_ID)
                .count()
            )
            if remaining <= 1:
                event.SAA_Status = "GEKANSELLEER"
                event.Voltooi_Op = datetime.utcnow()
                event.Gewysig_Op = datetime.utcnow()

    member.SAA_Status = "VERLAAT"
    member.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Jy het die permanente groep verlaat"})


# ---------------------------------------------------------------------------
# Gewone/default pickup-profiel
# ---------------------------------------------------------------------------

@router.get("/pickup-profiel")
def get_saamry_pickup_profile(
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    profile = _pickup_profile_for_user(db, current_user.Gebruiker_ID)
    return schemas.APIResponse(
        sukses=True,
        data=_pickup_profile_dict(profile) if profile is not None else None,
    )


@router.put("/pickup-profiel")
def save_saamry_pickup_profile(
    payload: schemas.SaamryPickupProfielUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    profile = _upsert_pickup_profile(
        db,
        current_user.Gebruiker_ID,
        payload.latitude,
        payload.longitude,
        payload.beskrywing,
    )
    db.commit()
    db.refresh(profile)
    return schemas.APIResponse(sukses=True, data=_pickup_profile_dict(profile))


# ---------------------------------------------------------------------------
# Eenmalige Saamry-events
# ---------------------------------------------------------------------------

@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_saamry_event(
    payload: schemas.SaamryEventCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, payload.groep_id)
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie permanente groep is nie aktief nie")
    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(
            status_code=403,
            detail="Net die huidige Driver/Admin kan 'n Saamry-event skep",
        )
    if _active_event_for_group(db, group.Groep_ID) is not None:
        raise HTTPException(status_code=409, detail="Hierdie groep het reeds 'n aktiewe Saamry-event")
    if _active_event_for_driver(db, current_user.Gebruiker_ID) is not None:
        raise HTTPException(status_code=409, detail="Jy is reeds Driver van 'n ander aktiewe Saamry-event")

    accepted_member_ids = {
        member.Gebruiker_ID
        for member in group.lede
        if member.SAA_Status == "AANVAAR"
    }
    accepted_member_ids.add(group.Bestuurder_ID)

    selected_ids = list(dict.fromkeys(int(user_id) for user_id in payload.gebruiker_ids))
    selected_ids = [user_id for user_id in selected_ids if user_id != group.Bestuurder_ID]
    if not selected_ids:
        raise HTTPException(
            status_code=400,
            detail="Kies minstens een passasier vir die Saamry-event",
        )
    invalid = [user_id for user_id in selected_ids if user_id not in accepted_member_ids]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail="Een of meer gekose passasiers is nie aanvaarde lede van hierdie groep nie",
        )

    for user_id in [group.Bestuurder_ID, *selected_ids]:
        existing_event = _active_event_for_user(db, user_id)
        if existing_event is not None:
            raise HTTPException(
                status_code=409,
                detail="Een van die gekose persone is reeds deel van 'n ander aktiewe Saamry-event",
            )

    event = models.SaamryEvent(
        Groep_ID=group.Groep_ID,
        Bestuurder_ID=group.Bestuurder_ID,
        SAA_Status="AKTIEF",
    )
    db.add(event)
    db.flush()
    # Driver gebruik óf die adres wat vir hierdie event gestuur is, óf sy
    # gewone/default pickup-profiel. Om die event te skep bevestig die Driver
    # hierdie beginadres implisiet.
    driver_profile = _pickup_profile_for_user(db, group.Bestuurder_ID)
    has_driver_lat = payload.driver_latitude is not None
    has_driver_lon = payload.driver_longitude is not None
    if has_driver_lat != has_driver_lon:
        raise HTTPException(
            status_code=400,
            detail="Driver latitude en longitude moet saam gestuur word",
        )

    if has_driver_lat and has_driver_lon:
        driver_latitude = payload.driver_latitude
        driver_longitude = payload.driver_longitude
        driver_beskrywing = (payload.driver_pickup_beskrywing or '').strip()
        if not driver_beskrywing:
            raise HTTPException(status_code=400, detail="Driver se beginadres is nodig")
        if payload.stoor_driver_as_verstek:
            _upsert_pickup_profile(
                db,
                group.Bestuurder_ID,
                driver_latitude,
                driver_longitude,
                driver_beskrywing,
            )
    elif driver_profile is not None:
        driver_latitude = driver_profile.Pickup_Latitude
        driver_longitude = driver_profile.Pickup_Longitude
        driver_beskrywing = driver_profile.Pickup_Beskrywing
    else:
        raise HTTPException(
            status_code=400,
            detail="Stel eers die Driver se beginadres",
        )

    now = datetime.utcnow()
    db.add(
        models.SaamryEventLid(
            Event_ID=event.Event_ID,
            Gebruiker_ID=group.Bestuurder_ID,
            Pickup_Latitude=driver_latitude,
            Pickup_Longitude=driver_longitude,
            Pickup_Beskrywing=driver_beskrywing,
            Pickup_Gewysig_Op=now,
            Pickup_Bevestig=True,
        )
    )

    # Passasiers se gewone pickup-adresse word slegs as 'n voorstel gekopieer.
    # Dit bly privaat vir die Driver totdat die passasier dit bevestig.
    for user_id in selected_ids:
        profile = _pickup_profile_for_user(db, user_id)
        db.add(
            models.SaamryEventLid(
                Event_ID=event.Event_ID,
                Gebruiker_ID=user_id,
                Pickup_Latitude=profile.Pickup_Latitude if profile else None,
                Pickup_Longitude=profile.Pickup_Longitude if profile else None,
                Pickup_Beskrywing=profile.Pickup_Beskrywing if profile else None,
                Pickup_Gewysig_Op=profile.Gewysig_Op if profile else None,
                Pickup_Bevestig=False,
            )
        )
    db.commit()
    db.refresh(event)
    return schemas.APIResponse(sukses=True, data=_event_dict(event, current_user.Gebruiker_ID))


@router.put("/events/{event_id}/pickup")
def update_saamry_pickup(
    event_id: int,
    payload: schemas.SaamryPickupUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    event = (
        db.query(models.SaamryEvent)
        .filter(models.SaamryEvent.Event_ID == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Saamry-event is nie gevind nie")
    if event.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie Saamry-event is nie meer aktief nie")

    event_member = (
        db.query(models.SaamryEventLid)
        .filter(
            models.SaamryEventLid.Event_ID == event_id,
            models.SaamryEventLid.Gebruiker_ID == current_user.Gebruiker_ID,
        )
        .first()
    )
    if event_member is None:
        raise HTTPException(
            status_code=403,
            detail="Jy is nie deel van hierdie Saamry-event nie",
        )

    clean_address = (payload.beskrywing or '').strip()
    if not clean_address:
        raise HTTPException(status_code=400, detail="Kies eers 'n geldige pickup-adres")

    event_member.Pickup_Latitude = payload.latitude
    event_member.Pickup_Longitude = payload.longitude
    event_member.Pickup_Beskrywing = clean_address
    event_member.Pickup_Gewysig_Op = datetime.utcnow()
    event_member.Pickup_Bevestig = True

    if payload.stoor_as_verstek:
        _upsert_pickup_profile(
            db,
            current_user.Gebruiker_ID,
            payload.latitude,
            payload.longitude,
            clean_address,
        )

    db.commit()
    db.refresh(event)

    return schemas.APIResponse(
        sukses=True,
        data=_event_dict(event, current_user.Gebruiker_ID),
    )


@router.post("/events/{event_id}/kanselleer")
def cancel_saamry_event(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    event = db.query(models.SaamryEvent).filter(models.SaamryEvent.Event_ID == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Saamry-event is nie gevind nie")
    group = _get_group_or_404(db, event.Groep_ID)
    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Net die Driver/Admin kan die event kanselleer")
    if event.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie event is nie meer aktief nie")
    event.SAA_Status = "GEKANSELLEER"
    event.Voltooi_Op = datetime.utcnow()
    event.Gewysig_Op = datetime.utcnow()
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Saamry-event is gekanselleer"})


# ---------------------------------------------------------------------------
# Chat helpers + REST
# ---------------------------------------------------------------------------

def _message_dict(message: models.SaamryBoodskap, viewer_id: int) -> dict:
    return {
        "boodskap_id": message.Boodskap_ID,
        "stuurder_id": message.Stuurder_ID,
        "ontvanger_id": message.Ontvanger_ID,
        "groep_id": message.Groep_ID,
        "boodskap": message.SAA_Boodskap,
        "geskep_op": message.Geskep_Op.isoformat() if message.Geskep_Op else None,
        "is_myne": message.Stuurder_ID == viewer_id,
        "stuurder": _user_dict(message.stuurder) if message.stuurder else None,
    }


def _mark_messages_read(db: Session, messages: list[models.SaamryBoodskap], viewer_id: int) -> None:
    incoming = [message for message in messages if message.Stuurder_ID != viewer_id]
    if not incoming:
        return
    message_ids = [message.Boodskap_ID for message in incoming]
    existing = _read_message_ids_for_user(db, message_ids, viewer_id)
    changed = False
    for message in incoming:
        if message.Boodskap_ID in existing:
            continue
        db.add(
            models.SaamryBoodskapGelees(
                Boodskap_ID=message.Boodskap_ID,
                Gebruiker_ID=viewer_id,
            )
        )
        changed = True
    if changed:
        db.commit()


def _private_messages(db: Session, viewer_id: int, friend_id: int, limit: int = 200):
    rows = (
        db.query(models.SaamryBoodskap)
        .filter(
            models.SaamryBoodskap.Groep_ID.is_(None),
            or_(
                and_(
                    models.SaamryBoodskap.Stuurder_ID == viewer_id,
                    models.SaamryBoodskap.Ontvanger_ID == friend_id,
                ),
                and_(
                    models.SaamryBoodskap.Stuurder_ID == friend_id,
                    models.SaamryBoodskap.Ontvanger_ID == viewer_id,
                ),
            ),
        )
        .order_by(models.SaamryBoodskap.Boodskap_ID.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def _group_messages(db: Session, group_id: int, limit: int = 200):
    rows = (
        db.query(models.SaamryBoodskap)
        .filter(models.SaamryBoodskap.Groep_ID == group_id)
        .order_by(models.SaamryBoodskap.Boodskap_ID.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@router.get("/chat/vriend/{friend_id}")
def get_friend_chat(
    friend_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    _require_accepted_friend(db, current_user.Gebruiker_ID, friend_id)
    friend = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == friend_id).first()
    if friend is None:
        raise HTTPException(status_code=404, detail="Vriend is nie gevind nie")
    messages = _private_messages(db, current_user.Gebruiker_ID, friend_id)
    _mark_messages_read(db, messages, current_user.Gebruiker_ID)
    return schemas.APIResponse(
        sukses=True,
        data={
            "tipe": "VRIEND",
            "teiken": _user_dict(friend, include_contact=True),
            "boodskappe": [_message_dict(message, current_user.Gebruiker_ID) for message in messages],
        },
    )


@router.post("/chat/vriend/{friend_id}", status_code=status.HTTP_201_CREATED)
def send_friend_chat(
    friend_id: int,
    payload: schemas.SaamryBoodskapCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    _require_accepted_friend(db, current_user.Gebruiker_ID, friend_id)
    clean = payload.boodskap.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Boodskap mag nie leeg wees nie")
    message = models.SaamryBoodskap(
        Stuurder_ID=current_user.Gebruiker_ID,
        Ontvanger_ID=friend_id,
        Groep_ID=None,
        SAA_Boodskap=clean,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return schemas.APIResponse(sukses=True, data=_message_dict(message, current_user.Gebruiker_ID))


@router.get("/chat/groep/{group_id}")
def get_group_chat(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, group_id)
    _require_group_member(group, current_user.Gebruiker_ID)
    messages = _group_messages(db, group_id)
    _mark_messages_read(db, messages, current_user.Gebruiker_ID)
    return schemas.APIResponse(
        sukses=True,
        data={
            "tipe": "GROEP",
            "teiken": {"groep_id": group.Groep_ID, "naam": group.SAA_Naam},
            "boodskappe": [_message_dict(message, current_user.Gebruiker_ID) for message in messages],
        },
    )


@router.post("/chat/groep/{group_id}", status_code=status.HTTP_201_CREATED)
def send_group_chat(
    group_id: int,
    payload: schemas.SaamryBoodskapCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, group_id)
    _require_group_member(group, current_user.Gebruiker_ID)
    clean = payload.boodskap.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Boodskap mag nie leeg wees nie")
    message = models.SaamryBoodskap(
        Stuurder_ID=current_user.Gebruiker_ID,
        Ontvanger_ID=None,
        Groep_ID=group_id,
        SAA_Boodskap=clean,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return schemas.APIResponse(sukses=True, data=_message_dict(message, current_user.Gebruiker_ID))


# ---------------------------------------------------------------------------
# Chat WebSockets — PostgreSQL bly die gedeelde bron oor workers/devices
# ---------------------------------------------------------------------------

def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    header = websocket.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    token = websocket.query_params.get("token")
    return token.strip() if token else None


def _authenticate_ws(websocket: WebSocket, db: Session) -> Optional[models.Gebruikers]:
    if getattr(auth, "DISABLE_AUTH", False):
        fallback = getattr(auth, "_dev_fallback_user", None)
        return fallback(db) if callable(fallback) else db.query(models.Gebruikers).first()
    token = _extract_ws_token(websocket)
    if not token:
        return None
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return (
            db.query(models.Gebruikers)
            .filter(
                models.Gebruikers.Gebruiker_ID == int(user_id),
                models.Gebruikers.Is_Aktief.is_(True),
            )
            .first()
        )
    except (JWTError, TypeError, ValueError):
        return None


def _friend_chat_snapshot(viewer_id: int, friend_id: int) -> dict[str, Any]:
    db = database.SessionLocal()
    try:
        _require_accepted_friend(db, viewer_id, friend_id)
        messages = _private_messages(db, viewer_id, friend_id)
        _mark_messages_read(db, messages, viewer_id)
        return {
            "tipe": "SAAMRY_CHAT",
            "konteks": "VRIEND",
            "boodskappe": [_message_dict(message, viewer_id) for message in messages],
        }
    finally:
        db.close()


def _group_chat_snapshot(viewer_id: int, group_id: int) -> dict[str, Any]:
    db = database.SessionLocal()
    try:
        group = _get_group_or_404(db, group_id)
        _require_group_member(group, viewer_id)
        messages = _group_messages(db, group_id)
        _mark_messages_read(db, messages, viewer_id)
        return {
            "tipe": "SAAMRY_CHAT",
            "konteks": "GROEP",
            "boodskappe": [_message_dict(message, viewer_id) for message in messages],
        }
    finally:
        db.close()


def _chat_signature(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)


async def _run_chat_socket(
    websocket: WebSocket,
    viewer_id: int,
    snapshot_builder,
) -> None:
    await websocket.accept()
    last_signature: Optional[str] = None
    try:
        while True:
            snapshot = await asyncio.to_thread(snapshot_builder)
            signature = _chat_signature(snapshot)
            if signature != last_signature:
                await websocket.send_json(snapshot)
                last_signature = signature
            await asyncio.sleep(CHAT_WS_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"tipe": "FOUT", "fout": str(exc)})
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.websocket("/chat/ws/vriend/{friend_id}")
async def friend_chat_ws(websocket: WebSocket, friend_id: int):
    db = database.SessionLocal()
    try:
        user = _authenticate_ws(websocket, db)
        if user is None:
            await websocket.close(code=4401, reason="Ongeldige token")
            return
        try:
            _require_saamry_user(db, user)
            _require_accepted_friend(db, user.Gebruiker_ID, friend_id)
        except Exception:
            await websocket.close(code=4403, reason="Geen toegang tot hierdie chat nie")
            return
        viewer_id = user.Gebruiker_ID
    finally:
        db.close()
    await _run_chat_socket(
        websocket,
        viewer_id,
        lambda: _friend_chat_snapshot(viewer_id, friend_id),
    )


@router.websocket("/chat/ws/groep/{group_id}")
async def group_chat_ws(websocket: WebSocket, group_id: int):
    db = database.SessionLocal()
    try:
        user = _authenticate_ws(websocket, db)
        if user is None:
            await websocket.close(code=4401, reason="Ongeldige token")
            return
        try:
            _require_saamry_user(db, user)
            group = _get_group_or_404(db, group_id)
            _require_group_member(group, user.Gebruiker_ID)
        except Exception:
            await websocket.close(code=4403, reason="Geen toegang tot hierdie groepchat nie")
            return
        viewer_id = user.Gebruiker_ID
    finally:
        db.close()
    await _run_chat_socket(
        websocket,
        viewer_id,
        lambda: _group_chat_snapshot(viewer_id, group_id),
    )


# ---------------------------------------------------------------------------
# Sekuriteitshek — slegs 'n AKTIEWE EVENT word as Saamry behandel
# ---------------------------------------------------------------------------

def _require_security_guard(_allowed: bool = Depends(auth.check_sekuriteit)) -> None:
    return None


def _campus_gate_location(db: Session, kampus_id: int) -> models.Lokasie:
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus is nie gevind nie")

    location = (
        db.query(models.Lokasie)
        .filter(
            models.Lokasie.Kampus_ID == kampus_id,
            models.Lokasie.LOK_Tipe == "Kampus",
        )
        .order_by(models.Lokasie.Lokasie_ID)
        .first()
    )
    if location is None:
        location = (
            db.query(models.Lokasie)
            .filter(models.Lokasie.Kampus_ID == kampus_id)
            .order_by(models.Lokasie.Lokasie_ID)
            .first()
        )
    if location is None:
        raise HTTPException(status_code=409, detail="Hierdie kampus het nog geen hek-lokasie nie")
    return location


def _latest_campus_log(
    db: Session,
    gebruiker_id: int,
    kampus_id: int,
) -> Optional[models.ToegangsLogs]:
    return (
        db.query(models.ToegangsLogs)
        .join(models.Lokasie, models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID)
        .filter(
            models.ToegangsLogs.Gebruiker_ID == gebruiker_id,
            models.Lokasie.Kampus_ID == kampus_id,
            models.Lokasie.LOK_Tipe == "Kampus",
        )
        .order_by(
            models.ToegangsLogs.TOE_Tydstempel.desc(),
            models.ToegangsLogs.Log_ID.desc(),
        )
        .first()
    )


def _user_is_on_campus(
    db: Session,
    gebruiker_id: int,
    kampus_id: int,
) -> tuple[bool, Optional[models.ToegangsLogs]]:
    latest = _latest_campus_log(db, gebruiker_id, kampus_id)
    return (latest is not None and latest.TOE_Rigting == "IN", latest)


def _event_gate_members(event: models.SaamryEvent) -> list[models.Gebruikers]:
    users = [member.gebruiker for member in event.lede if member.gebruiker is not None]
    by_id = {user.Gebruiker_ID: user for user in users}
    if event.bestuurder is not None:
        by_id[event.Bestuurder_ID] = event.bestuurder
    driver = by_id.get(event.Bestuurder_ID)
    if driver is None:
        return []
    passengers = sorted(
        [user for user_id, user in by_id.items() if user_id != event.Bestuurder_ID],
        key=lambda user: ((user.GEB_Naam or "").lower(), (user.GEB_Van or "").lower()),
    )
    return [driver, *passengers]


@router.post("/wagte/hek/preview")
def gate_group_preview(
    payload: schemas.SaamryHekPreviewRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _security: None = Depends(_require_security_guard),
):
    rigting = payload.rigting.strip().upper()
    if rigting not in ("IN", "UIT"):
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")
    _campus_gate_location(db, payload.kampus_id)

    event = _active_event_for_driver(db, payload.bestuurder_id)
    if event is None:
        passenger_event = _active_event_for_user(db, payload.bestuurder_id)
        if passenger_event is not None and passenger_event.Bestuurder_ID != payload.bestuurder_id:
            passenger_group = _get_group_or_404(db, passenger_event.Groep_ID)
            return schemas.APIResponse(
                sukses=True,
                data={
                    "has_group": False,
                    "blocked_by_event": True,
                    "event_id": passenger_event.Event_ID,
                    "groep_id": passenger_group.Groep_ID,
                    "groep_naam": passenger_group.SAA_Naam,
                    "bestuurder_id": passenger_event.Bestuurder_ID,
                    "rede": (
                        "Hierdie persoon is 'n passasier in 'n aktiewe Saamry-event. "
                        "Die Driver moet die voertuigscan voltooi. Daarna kan die persoon weer individueel scan."
                    ),
                },
            )
        return schemas.APIResponse(
            sukses=True,
            data={
                "has_group": False,
                "blocked_by_event": False,
                "rede": "Geen aktiewe Saamry-event vir hierdie Driver nie",
            },
        )
    group = _get_group_or_404(db, event.Groep_ID)
    if group.SAA_Status != "AKTIEF" or group.Bestuurder_ID != payload.bestuurder_id:
        return schemas.APIResponse(
            sukses=True,
            data={"has_group": False, "rede": "Die Saamry-event se Driver/Admin is nie meer geldig nie"},
        )

    members = _event_gate_members(event)
    if len(members) <= 1:
        return schemas.APIResponse(
            sukses=True,
            data={"has_group": False, "rede": "Die Saamry-event het geen passasiers nie"},
        )

    member_data = []
    for user in members:
        op_kampus, latest = _user_is_on_campus(db, user.Gebruiker_ID, payload.kampus_id)
        user_data = _user_dict(user)
        user_data.update(
            {
                "is_bestuurder": user.Gebruiker_ID == event.Bestuurder_ID,
                "op_kampus": op_kampus,
                "laaste_rigting": latest.TOE_Rigting if latest else None,
                "laaste_tyd": latest.TOE_Tydstempel.isoformat() if latest else None,
                "geselekteer": (
                    user.Gebruiker_ID == event.Bestuurder_ID
                    or (rigting == "IN" and not op_kampus)
                    or (rigting == "UIT" and op_kampus)
                ),
            }
        )
        member_data.append(user_data)

    return schemas.APIResponse(
        sukses=True,
        data={
            "has_group": True,
            "blocked_by_event": False,
            "event_id": event.Event_ID,
            "groep_id": group.Groep_ID,
            "groep_naam": group.SAA_Naam,
            "bestuurder_id": event.Bestuurder_ID,
            "rigting": rigting,
            "kampus_id": payload.kampus_id,
            "lede": member_data,
        },
    )


@router.post("/wagte/hek/bevestig")
def confirm_group_at_gate(
    payload: schemas.SaamryHekBevestigRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _security: None = Depends(_require_security_guard),
):
    rigting = payload.rigting.strip().upper()
    metode = payload.metode.strip().upper()
    if rigting not in ("IN", "UIT"):
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")
    if metode not in ("QR", "NFC", "HANDMATIG"):
        raise HTTPException(status_code=400, detail="Bestuurdermetode moet QR, NFC of HANDMATIG wees")

    group = _get_group_or_404(db, payload.groep_id)
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Die permanente Saamrygroep is nie meer aktief nie")
    event = _active_event_for_group(db, group.Groep_ID)
    if event is None:
        raise HTTPException(status_code=409, detail="Hierdie groep het nie meer 'n aktiewe Saamry-event nie")
    if payload.event_id is not None and payload.event_id != event.Event_ID:
        raise HTTPException(status_code=409, detail="Die Saamry-event het intussen verander")
    if event.Bestuurder_ID != group.Bestuurder_ID:
        raise HTTPException(status_code=409, detail="Die event se Driver/Admin stem nie meer met die groep ooreen nie")

    gate_location = _campus_gate_location(db, payload.kampus_id)
    event_users = _event_gate_members(event)
    accepted_by_id = {user.Gebruiker_ID: user for user in event_users}

    selected_ids = list(dict.fromkeys(payload.gebruiker_ids))
    if event.Bestuurder_ID not in selected_ids:
        raise HTTPException(status_code=400, detail="Die Driver moet altyd saam bevestig word")
    invalid_ids = [user_id for user_id in selected_ids if user_id not in accepted_by_id]
    if invalid_ids:
        raise HTTPException(status_code=400, detail="Een of meer gekose persone is nie deel van hierdie Saamry-event nie")

    driver_on_campus, _ = _user_is_on_campus(db, event.Bestuurder_ID, payload.kampus_id)
    driver_already_matches = (rigting == "IN" and driver_on_campus) or (
        rigting == "UIT" and not driver_on_campus
    )
    if driver_already_matches:
        raise HTTPException(
            status_code=409,
            detail=(
                "Die Driver is reeds op kampus"
                if rigting == "IN"
                else "Die Driver is reeds van kampus af"
            ),
        )

    processed = []
    skipped = []
    driver_log = None
    ordered_ids = [event.Bestuurder_ID] + [
        user_id for user_id in selected_ids if user_id != event.Bestuurder_ID
    ]

    try:
        for user_id in ordered_ids:
            op_kampus, _latest = _user_is_on_campus(db, user_id, payload.kampus_id)
            state_matches = (rigting == "IN" and op_kampus) or (
                rigting == "UIT" and not op_kampus
            )
            if state_matches:
                skipped.append(
                    {
                        "gebruiker_id": user_id,
                        "volle_naam": _user_dict(accepted_by_id[user_id])["volle_naam"],
                        "rede": "Reeds op kampus" if rigting == "IN" else "Reeds van kampus af",
                    }
                )
                continue

            is_driver = user_id == event.Bestuurder_ID
            log = models.ToegangsLogs(
                Gebruiker_ID=user_id,
                Lokasie_ID=gate_location.Lokasie_ID,
                TOE_Tydstempel=datetime.utcnow(),
                TOE_Rigting=rigting,
                TOE_Metode=metode if is_driver else "SAAMRY",
                TOE_Auto_Uitgecheck=False,
                Saamry_Groep_ID=group.Groep_ID,
                Saamry_Bestuurder_Log_ID=(
                    None if is_driver else driver_log.Log_ID if driver_log else None
                ),
            )
            db.add(log)
            db.flush()
            if is_driver:
                driver_log = log

            processed.append(
                {
                    "log_id": log.Log_ID,
                    "gebruiker_id": user_id,
                    "volle_naam": _user_dict(accepted_by_id[user_id])["volle_naam"],
                    "is_bestuurder": is_driver,
                    "metode": log.TOE_Metode,
                    "rigting": rigting,
                }
            )

        if driver_log is None:
            raise HTTPException(
                status_code=409,
                detail="Die Driver se scan is nie verwerk nie; die Saamry-event bly aktief",
            )

        # Kritieke reël: die event verdwyn eers nadat die Driver-log suksesvol geskryf is.
        event.SAA_Status = "VOLTOOI"
        event.Voltooi_Rigting = rigting
        event.Voltooi_Kampus_ID = payload.kampus_id
        event.Bestuurder_Log_ID = driver_log.Log_ID
        event.Voltooi_Op = datetime.utcnow()
        event.Gewysig_Op = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    return schemas.APIResponse(
        sukses=True,
        data={
            "event_id": event.Event_ID,
            "event_voltooi": True,
            "groep_id": group.Groep_ID,
            "rigting": rigting,
            "verwerk_count": len(processed),
            "oorgeslaan_count": len(skipped),
            "verwerk": processed,
            "oorgeslaan": skipped,
            "boodskap": (
                f"{len(processed)} persoon/persone is as {rigting} bevestig; "
                "Saamry-event is voltooi"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Saamry Profiel & Versoenbaarheidsalgoritme (Saamry-Algo)
# ---------------------------------------------------------------------------

@router.get("/profiel", response_model=schemas.APIResponse[schemas.SaamryProfielOut])
def kry_saamry_profiel(
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Haal die huidige gebruiker se saamryprofiel op (skep verstek indien nog nie bestaan)."""
    _require_saamry_user(db, current_user)

    profiel = db.query(models.SaamryProfiel).filter(
        models.SaamryProfiel.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    if not profiel:
        from services.compatibiliteit_service import herlei_geslag_uit_id
        geslag = herlei_geslag_uit_id(current_user.GEB_ID_Nommer)
        profiel = models.SaamryProfiel(
            Gebruiker_ID=current_user.Gebruiker_ID,
            Rol_Tipe="BEIDE",
            Geslag=geslag,
            Geslag_Voorkeur="ENIGE",
            Maks_Ompad_Minute=15,
            Is_Aktief_Saamryer=True,
        )
        db.add(profiel)
        db.commit()
        db.refresh(profiel)

    return schemas.APIResponse(sukses=True, data=profiel)


@router.put("/profiel", response_model=schemas.APIResponse[schemas.SaamryProfielOut])
def werk_saamry_profiel_by(
    payload: schemas.SaamryProfielUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Dateer die huidige gebruiker se saamryprofiel en voorkeure op."""
    _require_saamry_user(db, current_user)

    profiel = db.query(models.SaamryProfiel).filter(
        models.SaamryProfiel.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    if not profiel:
        profiel = models.SaamryProfiel(Gebruiker_ID=current_user.Gebruiker_ID)
        db.add(profiel)

    data = payload.dict(exclude_unset=True)

    if "rol_tipe" in data and data["rol_tipe"]:
        rol = data["rol_tipe"].strip().upper()
        if rol not in ("BESTUURDER", "PASSASIER", "BEIDE"):
            raise HTTPException(status_code=400, detail="Ongeldige rol_tipe. Kies BESTUURDER, PASSASIER of BEIDE.")
        profiel.Rol_Tipe = rol

    if "voorstad" in data:
        profiel.Voorstad = data["voorstad"].strip() if data["voorstad"] else None

    if "sone_kode" in data:
        profiel.Sone_Kode = data["sone_kode"].strip() if data["sone_kode"] else None

    if "kampus_id" in data:
        if data["kampus_id"] is not None:
            kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == data["kampus_id"]).first()
            if not kampus:
                raise HTTPException(status_code=400, detail="Kampus bestaan nie")
        profiel.Kampus_ID = data["kampus_id"]

    if "geslag" in data and data["geslag"]:
        profiel.Geslag = data["geslag"].strip().upper()

    if "geslag_voorkeur" in data and data["geslag_voorkeur"]:
        voorkeur = data["geslag_voorkeur"].strip().upper()
        if voorkeur not in ("ENIGE", "DIESELFDE"):
            raise HTTPException(status_code=400, detail="Ongeldige geslag_voorkeur. Kies ENIGE of DIESELFDE.")
        profiel.Geslag_Voorkeur = voorkeur

    if "maks_ompad_minute" in data and data["maks_ompad_minute"] is not None:
        if data["maks_ompad_minute"] < 0 or data["maks_ompad_minute"] > 120:
            raise HTTPException(status_code=400, detail="Maksimum ompad moet tussen 0 en 120 minute wees.")
        profiel.Maks_Ompad_Minute = data["maks_ompad_minute"]

    if "is_aktief_saamryer" in data and data["is_aktief_saamryer"] is not None:
        profiel.Is_Aktief_Saamryer = bool(data["is_aktief_saamryer"])

    profiel.Gewysig_Op = datetime.utcnow()
    db.commit()
    db.refresh(profiel)

    return schemas.APIResponse(sukses=True, data=profiel)


@router.get("/voorstelle")
def kry_saamry_voorstelle(
    limiet: int = Query(default=10, ge=1, le=50),
    min_telling: float = Query(default=50.0, ge=0.0, le=100.0),
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Vind en rangskik versoenbare saamrymaats volgens die Saamry-Algo."""
    _require_saamry_user(db, current_user)
    voorstelle = vind_saamry_voorstelle(db, current_user, limiet=limiet, min_telling=min_telling)
    return schemas.APIResponse(sukses=True, data={"voorstelle": voorstelle, "totaal": len(voorstelle)})


@router.get("/versoenbaarheid/{kandidaat_id}")
def kry_kandidaat_versoenbaarheid(
    kandidaat_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Bereken 'n volledige wiskundige en per-dag afbreking vir 'n spesifieke student."""
    _require_saamry_user(db, current_user)

    kandidaat = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == kandidaat_id,
        models.Gebruikers.Is_Aktief == True,
    ).first()

    if not kandidaat:
        raise HTTPException(status_code=404, detail="Kandidaat nie gevind nie")

    student_data = bou_student_saamry_data_van_db(db, current_user)
    kandidaat_data = bou_student_saamry_data_van_db(db, kandidaat)

    res = bereken_saamry_versoenbaarheid(student_data, kandidaat_data)

    friendship = _friendship_between(db, current_user.Gebruiker_ID, kandidaat.Gebruiker_ID)
    is_vriend = friendship is not None and friendship.SAA_Status == "AANVAAR"

    data = {
        "gebruiker_id": kandidaat.Gebruiker_ID,
        "naam": kandidaat.GEB_Naam,
        "van": kandidaat.GEB_Van,
        "foto_url": kandidaat.GEB_Profiel_Foto,
        "saamry_rol": kandidaat_data.saamry_rol,
        "voorstad": kandidaat_data.voorstad or "Onbekend",
        "totale_telling": res.totale_telling,
        "gehalte": res.gehalte,
        "is_geskik": res.is_geskik,
        "gemeenskaplike_dae": res.gemeenskaplike_dae,
        "beste_dag": res.beste_dag,
        "is_reeds_vriend": is_vriend,
        "faktore": res.faktore,
        "per_dag_afbreking": res.per_dag_afbreking,
        "aanbeveling_teks": res.aanbeveling_teks,
    }

    return schemas.APIResponse(sukses=True, data=data)


