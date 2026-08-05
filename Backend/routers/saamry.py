"""Saamry API — vriende, saamrygroepe en uitnodigings."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(prefix="/saamry", tags=["Saamry"])


# ---------------------------------------------------------------------------
# Helpers
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


def _user_dict(
    user: models.Gebruikers,
    *,
    include_contact: bool = False,
) -> dict:
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


def _accepted_passenger_count(group: models.SaamryGroep) -> int:
    return sum(
        1
        for member in group.lede
        if member.Gebruiker_ID != group.Bestuurder_ID
        and member.SAA_Status == "AANVAAR"
    )


def _viewer_is_accepted_member(group: models.SaamryGroep, viewer_id: int) -> bool:
    if group.Bestuurder_ID == viewer_id:
        return True
    return any(
        member.Gebruiker_ID == viewer_id and member.SAA_Status == "AANVAAR"
        for member in group.lede
    )


def _group_dict(group: models.SaamryGroep, viewer_id: int) -> dict:
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

    return {
        "groep_id": group.Groep_ID,
        "naam": group.SAA_Naam,
        "vertrekpunt": group.SAA_Vertrekpunt,
        "bestemming": group.SAA_Bestemming,
        "vertrek_tyd": group.SAA_Vertrek_Tyd.isoformat(),
        "sitplekke": group.SAA_Sitplekke,
        "beskikbare_sitplekke": max(group.SAA_Sitplekke - reserved_count, 0),
        "status": group.SAA_Status,
        "is_bestuurder": group.Bestuurder_ID == viewer_id,
        "my_status": "AANVAAR" if group.Bestuurder_ID == viewer_id else (
            my_member.SAA_Status if my_member else None
        ),
        "bestuurder": _user_dict(
            group.bestuurder,
            include_contact=viewer_accepted,
        ),
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
        ],
    }


def _active_group_for_user(
    db: Session,
    user_id: int,
    *,
    exclude_group_id: Optional[int] = None,
) -> Optional[models.SaamryGroep]:
    query = (
        db.query(models.SaamryGroep)
        .outerjoin(
            models.SaamryGroepLid,
            models.SaamryGroepLid.Groep_ID == models.SaamryGroep.Groep_ID,
        )
        .filter(
            models.SaamryGroep.SAA_Status == "AKTIEF",
            or_(
                models.SaamryGroep.Bestuurder_ID == user_id,
                and_(
                    models.SaamryGroepLid.Gebruiker_ID == user_id,
                    models.SaamryGroepLid.SAA_Status == "AANVAAR",
                ),
            ),
        )
    )

    if exclude_group_id is not None:
        query = query.filter(models.SaamryGroep.Groep_ID != exclude_group_id)

    return query.first()


def _get_group_or_404(db: Session, group_id: int) -> models.SaamryGroep:
    group = (
        db.query(models.SaamryGroep)
        .filter(models.SaamryGroep.Groep_ID == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Saamrygroep is nie gevind nie")
    return group


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
        }

        if friendship.SAA_Status == "AANVAAR":
            friends.append(item)
        elif friendship.SAA_Status == "HANGEND":
            if friendship.Ontvanger_ID == user_id:
                incoming_requests.append(item)
            else:
                outgoing_requests.append(item)

    my_group = _active_group_for_user(db, user_id)

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

    return schemas.APIResponse(
        sukses=True,
        data={
            "friends": friends,
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
            "group_invites": [
                _group_dict(member.groep, user_id)
                for member in group_invite_members
            ],
            "my_group": _group_dict(my_group, user_id) if my_group else None,
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
            or_(models.Student.Gebruiker_ID.isnot(None), models.Personeel.Gebruiker_ID.isnot(None)),
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

    receiver_is_eligible = receiver.student is not None or receiver.personeel is not None
    if not receiver_is_eligible:
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

        # Laat 'n voorheen geweierde versoek weer gebruik word.
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
# Groepe
# ---------------------------------------------------------------------------

@router.post("/groepe", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: schemas.SaamryGroepCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)

    if _active_group_for_user(db, current_user.Gebruiker_ID):
        raise HTTPException(
            status_code=409,
            detail="Jy behoort reeds aan 'n aktiewe saamrygroep",
        )

    if payload.sitplekke < 1 or payload.sitplekke > 8:
        raise HTTPException(status_code=400, detail="Sitplekke moet tussen 1 en 8 wees")

    group_name = (payload.naam or "").strip()
    if not group_name:
        group_name = f"{payload.vertrekpunt.strip()} → {payload.bestemming.strip()}"

    group = models.SaamryGroep(
        Bestuurder_ID=current_user.Gebruiker_ID,
        SAA_Naam=group_name,
        SAA_Vertrekpunt=payload.vertrekpunt.strip(),
        SAA_Bestemming=payload.bestemming.strip(),
        SAA_Vertrek_Tyd=payload.vertrek_tyd,
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

    return schemas.APIResponse(sukses=True, data=_group_dict(group, current_user.Gebruiker_ID))


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
        raise HTTPException(status_code=403, detail="Slegs die bestuurder kan vriende nooi")
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie groep is nie meer aktief nie")
    if payload.gebruiker_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy is reeds die bestuurder")

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
        raise HTTPException(status_code=409, detail="Daar is nie meer beskikbare sitplekke nie")

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
    if _active_group_for_user(
        db,
        current_user.Gebruiker_ID,
        exclude_group_id=groep_id,
    ):
        raise HTTPException(status_code=409, detail="Jy behoort reeds aan 'n ander aktiewe groep")
    if _accepted_passenger_count(group) >= group.SAA_Sitplekke:
        raise HTTPException(status_code=409, detail="Die groep is reeds vol")

    member.SAA_Status = "AANVAAR"
    member.Gewysig_Op = datetime.utcnow()
    db.commit()

    db.refresh(group)
    return schemas.APIResponse(sukses=True, data=_group_dict(group, current_user.Gebruiker_ID))


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


@router.post("/groepe/{groep_id}/sluit")
def close_group(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)

    if group.Bestuurder_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Slegs die bestuurder kan die groep sluit")
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie groep is reeds gesluit")

    group.SAA_Status = "GESLUIT"
    group.Gewysig_Op = datetime.utcnow()
    db.commit()

    return schemas.APIResponse(sukses=True, data={"boodskap": "Saamrygroep is gesluit"})


@router.post("/groepe/{groep_id}/verlaat")
def leave_group(
    groep_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_saamry_user(db, current_user)
    group = _get_group_or_404(db, groep_id)

    if group.Bestuurder_ID == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Die bestuurder moet die groep sluit")

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

    member.SAA_Status = "VERLAAT"
    member.Gewysig_Op = datetime.utcnow()
    db.commit()

    return schemas.APIResponse(sukses=True, data={"boodskap": "Jy het die groep verlaat"})

# ---------------------------------------------------------------------------
# Sekuriteitshek — bestuurder skandeer vir die hele voertuig
# ---------------------------------------------------------------------------

def _require_security_guard(
    _allowed: bool = Depends(auth.check_sekuriteit),
) -> None:
    # auth.check_sekuriteit doen die werklike roltoets.
    return None


def _campus_gate_location(db: Session, kampus_id: int) -> models.Lokasie:
    kampus = (
        db.query(models.Kampus)
        .filter(models.Kampus.Kampus_ID == kampus_id)
        .first()
    )
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
        raise HTTPException(
            status_code=409,
            detail="Hierdie kampus het nog geen hek-lokasie nie",
        )

    return location


def _latest_campus_log(
    db: Session,
    gebruiker_id: int,
    kampus_id: int,
) -> Optional[models.ToegangsLogs]:
    return (
        db.query(models.ToegangsLogs)
        .join(
            models.Lokasie,
            models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
        )
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


def _accepted_gate_members(group: models.SaamryGroep) -> list[models.Gebruikers]:
    members_by_id = {
        member.gebruiker.Gebruiker_ID: member.gebruiker
        for member in group.lede
        if member.SAA_Status == "AANVAAR" and member.gebruiker is not None
    }
    members_by_id[group.Bestuurder_ID] = group.bestuurder

    # Bestuurder eerste; daarna alfabeties vir 'n stabiele wag-skerm.
    passengers = sorted(
        (
            user
            for user_id, user in members_by_id.items()
            if user_id != group.Bestuurder_ID
        ),
        key=lambda user: (user.GEB_Naam or "", user.GEB_Van or ""),
    )
    return [group.bestuurder, *passengers]


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

    group = (
        db.query(models.SaamryGroep)
        .filter(
            models.SaamryGroep.Bestuurder_ID == payload.bestuurder_id,
            models.SaamryGroep.SAA_Status == "AKTIEF",
        )
        .order_by(models.SaamryGroep.Groep_ID.desc())
        .first()
    )

    if group is None:
        return schemas.APIResponse(
            sukses=True,
            data={"has_group": False, "rede": "Geen aktiewe groep vir bestuurder nie"},
        )

    members = _accepted_gate_members(group)
    if len(members) <= 1:
        return schemas.APIResponse(
            sukses=True,
            data={
                "has_group": False,
                "rede": "Die groep het nog geen aanvaarde passasiers nie",
            },
        )

    member_data = []
    for user in members:
        op_kampus, latest = _user_is_on_campus(
            db,
            user.Gebruiker_ID,
            payload.kampus_id,
        )
        user_data = _user_dict(user)
        user_data.update(
            {
                "is_bestuurder": user.Gebruiker_ID == group.Bestuurder_ID,
                "op_kampus": op_kampus,
                "laaste_rigting": latest.TOE_Rigting if latest else None,
                "laaste_tyd": (
                    latest.TOE_Tydstempel.isoformat() if latest else None
                ),
                "geselekteer": (
                    user.Gebruiker_ID == group.Bestuurder_ID
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
            "groep_id": group.Groep_ID,
            "groep_naam": group.SAA_Naam,
            "bestuurder_id": group.Bestuurder_ID,
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
        raise HTTPException(
            status_code=400,
            detail="Bestuurdermetode moet QR, NFC of HANDMATIG wees",
        )

    group = _get_group_or_404(db, payload.groep_id)
    if group.SAA_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Die Saamrygroep is nie meer aktief nie")

    gate_location = _campus_gate_location(db, payload.kampus_id)
    accepted_users = _accepted_gate_members(group)
    accepted_by_id = {user.Gebruiker_ID: user for user in accepted_users}

    selected_ids = list(dict.fromkeys(payload.gebruiker_ids))
    if group.Bestuurder_ID not in selected_ids:
        raise HTTPException(
            status_code=400,
            detail="Die bestuurder moet altyd saam bevestig word",
        )

    invalid_ids = [user_id for user_id in selected_ids if user_id not in accepted_by_id]
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail="Een of meer gekose persone behoort nie aan hierdie groep nie",
        )

    driver_on_campus, _ = _user_is_on_campus(
        db,
        group.Bestuurder_ID,
        payload.kampus_id,
    )
    driver_already_matches = (rigting == "IN" and driver_on_campus) or (
        rigting == "UIT" and not driver_on_campus
    )
    if driver_already_matches:
        raise HTTPException(
            status_code=409,
            detail=(
                "Die bestuurder is reeds op kampus"
                if rigting == "IN"
                else "Die bestuurder is reeds van kampus af"
            ),
        )

    processed = []
    skipped = []
    driver_log = None

    # Bestuurder eerste sodat passasiers na sy log kan verwys.
    ordered_ids = [group.Bestuurder_ID] + [
        user_id for user_id in selected_ids if user_id != group.Bestuurder_ID
    ]

    try:
        for user_id in ordered_ids:
            op_kampus, latest = _user_is_on_campus(db, user_id, payload.kampus_id)
            state_matches = (rigting == "IN" and op_kampus) or (
                rigting == "UIT" and not op_kampus
            )

            if state_matches:
                skipped.append(
                    {
                        "gebruiker_id": user_id,
                        "volle_naam": _user_dict(accepted_by_id[user_id])["volle_naam"],
                        "rede": (
                            "Reeds op kampus" if rigting == "IN" else "Reeds van kampus af"
                        ),
                    }
                )
                continue

            is_driver = user_id == group.Bestuurder_ID
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

        db.commit()
    except Exception:
        db.rollback()
        raise

    return schemas.APIResponse(
        sukses=True,
        data={
            "groep_id": group.Groep_ID,
            "rigting": rigting,
            "verwerk_count": len(processed),
            "oorgeslaan_count": len(skipped),
            "verwerk": processed,
            "oorgeslaan": skipped,
            "boodskap": (
                f"{len(processed)} persoon/persone is as {rigting} bevestig"
            ),
        },
    )

