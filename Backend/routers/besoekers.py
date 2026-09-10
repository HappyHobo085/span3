"""Besoeker API — OTP-uitnodigings vir studente, personeel en sekuriteit."""

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(prefix="/besoekers", tags=["Besoekers"])

OTP_GELDIG_URE = 24
MAX_AKTIEWE_OTPS_PER_GASHEER = 5


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _require_host_user(db: Session, current_user: models.Gebruikers) -> None:
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
            detail="Slegs studente en personeel kan besoekers nooi",
        )


def _expire_old_invites(db: Session) -> int:
    now = datetime.utcnow()
    expired = (
        db.query(models.BesoekerUitnodiging)
        .filter(
            models.BesoekerUitnodiging.BES_Status == "HANGEND",
            models.BesoekerUitnodiging.BES_Verval_Op <= now,
        )
        .all()
    )

    for invite in expired:
        invite.BES_Status = "VERVAL"
        invite.BES_Aktief_Sleutel = None
        invite.BES_Besluit_Op = now

    if expired:
        db.flush()

    return len(expired)


def _generate_otp(db: Session) -> str:
    for _ in range(100):
        otp = f"{secrets.randbelow(100_000_000):08d}"
        exists = (
            db.query(models.BesoekerUitnodiging)
            .filter(models.BesoekerUitnodiging.BES_Aktief_Sleutel == otp)
            .first()
        )
        if not exists:
            return otp

    raise HTTPException(
        status_code=503,
        detail="Kon nie nou 'n unieke OTP genereer nie. Probeer weer.",
    )


def _invite_dict(invite: models.BesoekerUitnodiging) -> dict:
    gasheer = invite.gasheer
    kampus = invite.kampus

    return {
        "uitnodiging_id": invite.Uitnodiging_ID,
        "naam": invite.BES_Naam,
        "van": invite.BES_Van,
        "volle_naam": f"{invite.BES_Naam} {invite.BES_Van}".strip(),
        "selfoon": invite.BES_Selfoon_Nr,
        "rede": invite.BES_Rede,
        "otp": invite.BES_OTP,
        "status": invite.BES_Status,
        "geskep_op": _iso_utc(invite.BES_Geskep_Op),
        "verval_op": _iso_utc(invite.BES_Verval_Op),
        "besluit_op": _iso_utc(invite.BES_Besluit_Op),
        "gasheer": {
            "gebruiker_id": gasheer.Gebruiker_ID,
            "naam": gasheer.GEB_Naam,
            "van": gasheer.GEB_Van,
            "volle_naam": f"{gasheer.GEB_Naam} {gasheer.GEB_Van}".strip(),
            "selfoon": gasheer.GEB_Selfoon_Nr,
        },
        "kampus": None
        if kampus is None
        else {
            "kampus_id": kampus.Kampus_ID,
            "naam": kampus.KAM_Naam,
        },
    }


def _get_invite_or_404(db: Session, uitnodiging_id: int) -> models.BesoekerUitnodiging:
    invite = (
        db.query(models.BesoekerUitnodiging)
        .filter(models.BesoekerUitnodiging.Uitnodiging_ID == uitnodiging_id)
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="Besoeker-uitnodiging is nie gevind nie")
    return invite


def _ensure_pending_and_valid(db: Session, invite: models.BesoekerUitnodiging) -> None:
    if invite.BES_Status != "HANGEND":
        status_messages = {
            "TOEGELAAT": "Hierdie OTP is reeds gebruik en toegang is toegestaan",
            "GEWEIER": "Hierdie OTP is reeds verwerk en toegang is geweier",
            "GEKANSELLEER": "Hierdie uitnodiging is gekanselleer",
            "VERVAL": "Hierdie OTP het verval",
        }
        raise HTTPException(
            status_code=409,
            detail=status_messages.get(invite.BES_Status, "Hierdie OTP is nie meer geldig nie"),
        )

    if invite.BES_Verval_Op <= datetime.utcnow():
        invite.BES_Status = "VERVAL"
        invite.BES_Aktief_Sleutel = None
        invite.BES_Besluit_Op = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=410, detail="Hierdie OTP het verval")


@router.post("/uitnodigings", status_code=status.HTTP_201_CREATED)
def create_visitor_invite(
    payload: schemas.BesoekerUitnodigingCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_host_user(db, current_user)
    _expire_old_invites(db)

    naam = payload.naam.strip()
    van = payload.van.strip()
    selfoon = payload.selfoon.strip()
    rede = (payload.rede or "Besoek").strip() or "Besoek"

    if not naam or not van or not selfoon:
        raise HTTPException(status_code=400, detail="Naam, van en selfoon is verpligtend")
    if len(naam) > 100 or len(van) > 100:
        raise HTTPException(status_code=400, detail="Naam of van is te lank")
    if len(selfoon) < 7 or len(selfoon) > 20:
        raise HTTPException(status_code=400, detail="Vul 'n geldige selfoonnommer in")
    if len(rede) > 250:
        raise HTTPException(status_code=400, detail="Rede mag nie langer as 250 karakters wees nie")

    active_count = (
        db.query(models.BesoekerUitnodiging)
        .filter(
            models.BesoekerUitnodiging.Gasheer_ID == current_user.Gebruiker_ID,
            models.BesoekerUitnodiging.BES_Status == "HANGEND",
            models.BesoekerUitnodiging.BES_Verval_Op > datetime.utcnow(),
        )
        .count()
    )
    if active_count >= MAX_AKTIEWE_OTPS_PER_GASHEER:
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Jy het reeds 5 aktiewe besoeker-OTP's. Kanselleer een of wag dat dit verval.",
        )

    otp = _generate_otp(db)
    now = datetime.utcnow()
    invite = models.BesoekerUitnodiging(
        Gasheer_ID=current_user.Gebruiker_ID,
        BES_Naam=naam,
        BES_Van=van,
        BES_Selfoon_Nr=selfoon,
        BES_Rede=rede,
        BES_OTP=otp,
        BES_Aktief_Sleutel=otp,
        BES_Status="HANGEND",
        BES_Geskep_Op=now,
        BES_Verval_Op=now + timedelta(hours=OTP_GELDIG_URE),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return schemas.APIResponse(sukses=True, data=_invite_dict(invite))


@router.get("/uitnodigings/my")
def get_my_visitor_invites(
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_host_user(db, current_user)
    changed = _expire_old_invites(db)
    if changed:
        db.commit()

    invites = (
        db.query(models.BesoekerUitnodiging)
        .filter(models.BesoekerUitnodiging.Gasheer_ID == current_user.Gebruiker_ID)
        .order_by(models.BesoekerUitnodiging.BES_Geskep_Op.desc())
        .limit(50)
        .all()
    )

    return schemas.APIResponse(sukses=True, data=[_invite_dict(item) for item in invites])


@router.post("/uitnodigings/{uitnodiging_id}/kanselleer")
def cancel_visitor_invite(
    uitnodiging_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    _require_host_user(db, current_user)
    invite = _get_invite_or_404(db, uitnodiging_id)

    if invite.Gasheer_ID != current_user.Gebruiker_ID:
        raise HTTPException(status_code=403, detail="Jy mag nie hierdie uitnodiging kanselleer nie")

    _ensure_pending_and_valid(db, invite)
    invite.BES_Status = "GEKANSELLEER"
    invite.BES_Aktief_Sleutel = None
    invite.BES_Besluit_Op = datetime.utcnow()
    db.commit()
    db.refresh(invite)

    return schemas.APIResponse(sukses=True, data=_invite_dict(invite))


@router.post("/verifieer")
def verify_visitor_otp(
    payload: schemas.BesoekerOtpVerifyRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_sekuriteit),
):
    del current_user
    otp = payload.otp.strip()
    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="OTP moet presies 6 syfers wees")

    changed = _expire_old_invites(db)
    if changed:
        db.commit()

    invite = (
        db.query(models.BesoekerUitnodiging)
        .filter(models.BesoekerUitnodiging.BES_Aktief_Sleutel == otp)
        .first()
    )

    if invite is None:
        previous = (
            db.query(models.BesoekerUitnodiging)
            .filter(models.BesoekerUitnodiging.BES_OTP == otp)
            .order_by(models.BesoekerUitnodiging.BES_Geskep_Op.desc())
            .first()
        )
        if previous is not None:
            status_messages = {
                "TOEGELAAT": "Hierdie OTP is reeds gebruik",
                "GEWEIER": "Hierdie OTP is reeds geweier",
                "GEKANSELLEER": "Hierdie uitnodiging is gekanselleer",
                "VERVAL": "Hierdie OTP het verval",
            }
            raise HTTPException(
                status_code=409,
                detail=status_messages.get(previous.BES_Status, "Hierdie OTP is nie meer geldig nie"),
            )
        raise HTTPException(status_code=404, detail="Geen geldige besoeker vir hierdie OTP gevind nie")

    _ensure_pending_and_valid(db, invite)
    return schemas.APIResponse(sukses=True, data=_invite_dict(invite))


@router.post("/uitnodigings/{uitnodiging_id}/toelaat")
def allow_visitor_entry(
    uitnodiging_id: int,
    payload: schemas.BesoekerBesluitRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_sekuriteit),
):
    invite = _get_invite_or_404(db, uitnodiging_id)
    _ensure_pending_and_valid(db, invite)

    kampus = (
        db.query(models.Kampus)
        .filter(models.Kampus.Kampus_ID == payload.kampus_id)
        .first()
    )
    if kampus is None:
        raise HTTPException(status_code=404, detail="Kampus is nie gevind nie")

    invite.BES_Status = "TOEGELAAT"
    invite.BES_Aktief_Sleutel = None
    invite.BES_Besluit_Op = datetime.utcnow()
    invite.Verwerk_Deur_ID = current_user.Gebruiker_ID
    invite.Kampus_ID = payload.kampus_id
    db.commit()
    db.refresh(invite)

    return schemas.APIResponse(sukses=True, data=_invite_dict(invite))


@router.post("/uitnodigings/{uitnodiging_id}/weier")
def deny_visitor_entry(
    uitnodiging_id: int,
    payload: schemas.BesoekerBesluitRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_sekuriteit),
):
    invite = _get_invite_or_404(db, uitnodiging_id)
    _ensure_pending_and_valid(db, invite)

    kampus = (
        db.query(models.Kampus)
        .filter(models.Kampus.Kampus_ID == payload.kampus_id)
        .first()
    )
    if kampus is None:
        raise HTTPException(status_code=404, detail="Kampus is nie gevind nie")

    invite.BES_Status = "GEWEIER"
    invite.BES_Aktief_Sleutel = None
    invite.BES_Besluit_Op = datetime.utcnow()
    invite.Verwerk_Deur_ID = current_user.Gebruiker_ID
    invite.Kampus_ID = payload.kampus_id
    db.commit()
    db.refresh(invite)

    return schemas.APIResponse(sukses=True, data=_invite_dict(invite))
