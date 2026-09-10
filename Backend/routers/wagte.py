"""Wagte (Guard) and Sekuriteit routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone

from database import get_db
import models, schemas, auth

router = APIRouter(tags=["Wagte"])


@router.get("/sekuriteit/toegang")
def sekuriteit_toegang_toets(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    return schemas.APIResponse(sukses=True, data={"boodskap": "Toegang bevestig vir Sekuriteit"})


@router.get("/wagte/kampusse", response_model=schemas.APIResponse[List[dict]])
def wagte_kampusse(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()
    return schemas.APIResponse(
        sukses=True,
        data=[
            {"kampus_id": k.Kampus_ID, "naam": k.KAM_Naam, "adres": k.KAM_Adres}
            for k in kampusse
        ],
    )


@router.get("/wagte/nommer/check")
def wagte_nommer_check(
    nommer: str,
    db: Session = Depends(get_db),
):
    """Ligte live-validasie vir handmatige wag-invoer."""
    scan = nommer.strip()
    if not scan:
        return schemas.APIResponse(
            sukses=True,
            data={"bestaan": False, "tipe": None, "aktief": False},
        )

    student = db.query(models.Student).filter(models.Student.STU_Nommer == scan).first()
    if student:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
        ).first()
        return schemas.APIResponse(
            sukses=True,
            data={
                "bestaan": gebruiker is not None,
                "tipe": "STUDENT",
                "aktief": bool(gebruiker and gebruiker.Is_Aktief),
                "naam": gebruiker.GEB_Naam if gebruiker else "",
                "van": gebruiker.GEB_Van if gebruiker else "",
            },
        )

    personeel = db.query(models.Personeel).filter(models.Personeel.PER_Nommer == scan).first()
    if personeel:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.Gebruiker_ID == personeel.Gebruiker_ID
        ).first()
        return schemas.APIResponse(
            sukses=True,
            data={
                "bestaan": gebruiker is not None,
                "tipe": "PERSONEEL",
                "aktief": bool(gebruiker and gebruiker.Is_Aktief),
                "naam": gebruiker.GEB_Naam if gebruiker else "",
                "van": gebruiker.GEB_Van if gebruiker else "",
            },
        )

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.GEB_ID_Nommer == scan
    ).first()
    if gebruiker:
        return schemas.APIResponse(
            sukses=True,
            data={
                "bestaan": True,
                "tipe": "ID",
                "aktief": bool(gebruiker.Is_Aktief),
                "naam": gebruiker.GEB_Naam,
                "van": gebruiker.GEB_Van,
            },
        )

    return schemas.APIResponse(
        sukses=True,
        data={"bestaan": False, "tipe": None, "aktief": False},
    )


@router.get("/opsigter/kampusse/{kampus_id}/besoekers")
def opsigter_kampus_besoekers(
    kampus_id: int,
    db: Session = Depends(get_db),
):
    """Besoekers wat vandag by die gekose kampus toegelaat is."""
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    # Gebruik SA se kalenderdag, maar vergelyk teen die bestaande UTC-naive DB-tye.
    sa_tz = timezone(timedelta(hours=2))
    now_sa = datetime.now(sa_tz)
    start_sa = now_sa.replace(hour=0, minute=0, second=0, microsecond=0)
    end_sa = start_sa + timedelta(days=1)
    start_utc = start_sa.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_sa.astimezone(timezone.utc).replace(tzinfo=None)

    besoekers = (
        db.query(models.BesoekerUitnodiging, models.Gebruikers)
        .join(
            models.Gebruikers,
            models.Gebruikers.Gebruiker_ID == models.BesoekerUitnodiging.Gasheer_ID,
        )
        .filter(
            models.BesoekerUitnodiging.Kampus_ID == kampus_id,
            models.BesoekerUitnodiging.BES_Status == "TOEGELAAT",
            models.BesoekerUitnodiging.BES_Besluit_Op >= start_utc,
            models.BesoekerUitnodiging.BES_Besluit_Op < end_utc,
        )
        .order_by(models.BesoekerUitnodiging.BES_Besluit_Op.desc())
        .all()
    )

    data = []
    for item in besoekers:
        # Gebruik eager-loaded gasheer relationship (geen ekstra query nodig nie)
        gasheer = item.gasheer
        gasheer_naam = ""
        if gasheer:
            gasheer_naam = f"{gasheer.GEB_Naam or ''} {gasheer.GEB_Van or ''}".strip()

        data.append({
            "uitnodiging_id": item.Uitnodiging_ID,
            "naam": item.BES_Naam,
            "van": item.BES_Van,
            "selfoon": item.BES_Selfoon_Nr,
            "rede": item.BES_Rede,
            "status": item.BES_Status,
            "besluit_op": f"{item.BES_Besluit_Op.isoformat()}Z" if item.BES_Besluit_Op else None,
            "gasheer_id": item.Gasheer_ID,
            "gasheer_naam": gasheer_naam,
            "kampus_id": kampus_id,
            "kampus_naam": kampus.KAM_Naam,
        })

    return schemas.APIResponse(sukses=True, data=data)


@router.post("/wagte/profile/scan")
def wagte_profile_scan(
    data: schemas.WagteProfileScanRequest,
    db: Session = Depends(get_db),
):
    scan = data.scan_kode.strip()
    gebruiker = None

    student = db.query(models.Student).filter(models.Student.STU_Nommer == scan).first()
    if student:
        gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID).first()

    if not gebruiker:
        personeel = db.query(models.Personeel).filter(models.Personeel.PER_Nommer == scan).first()
        if personeel:
            gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == personeel.Gebruiker_ID).first()

    if not gebruiker:
        gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.GEB_ID_Nommer == scan).first()

    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    if not gebruiker.Is_Aktief:
        raise HTTPException(status_code=403, detail="Gebruiker is gedeaktiveer en mag nie scan nie")

    laaste_log = (
        db.query(models.ToegangsLogs)
        .filter(models.ToegangsLogs.Gebruiker_ID == gebruiker.Gebruiker_ID)
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())
        .first()
    )

    if laaste_log is None:
        voorgestelde_rigting = "IN"
    elif laaste_log.TOE_Rigting == "IN":
        voorgestelde_rigting = "UIT"
    else:
        voorgestelde_rigting = "IN"

    return schemas.APIResponse(
        sukses=True,
        data={
            "gebruiker_id": gebruiker.Gebruiker_ID,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "id_nommer": gebruiker.GEB_ID_Nommer,
            "foto_url": gebruiker.GEB_Profiel_Foto,
            "voorgestelde_rigting": voorgestelde_rigting,
        },
    )


@router.post("/wagte/profile/verify")
def wagte_profile_verify(
    data: schemas.WagteProfileVerifyRequest,
    db: Session = Depends(get_db),
):
    if data.rigting not in ["IN", "UIT"]:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")
    if data.metode not in ["NFC", "QR", "HANDMATIG"]:
        raise HTTPException(status_code=400, detail="Metode moet NFC, QR of HANDMATIG wees")

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == data.gebruiker_id,
        models.Gebruikers.Is_Aktief == True,
    ).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind of nie aktief nie")

    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == data.kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Kampus_ID == data.kampus_id,
        models.Lokasie.LOK_Tipe == "Kampus",
    ).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Geen kampus-lokasie vir hierdie kampus gevind nie")

    log = models.ToegangsLogs(
        Gebruiker_ID=data.gebruiker_id,
        Lokasie_ID=lokasie.Lokasie_ID,
        NFC_Tags_ID=None,
        TOE_Rigting=data.rigting,
        TOE_Metode=data.metode,
        TOE_Auto_Uitgecheck=False,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "log_id": log.Log_ID,
            "gebruiker_id": gebruiker.Gebruiker_ID,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "kampus_id": kampus.Kampus_ID,
            "kampus": kampus.KAM_Naam,
            "lokasie_id": lokasie.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam,
            "tyd": log.TOE_Tydstempel.isoformat(),
        },
    )


@router.post("/wagte/profile/decline")
def decline_profile_access(
    data: schemas.WagteProfileDeclineRequest,
    db: Session = Depends(get_db),
):
    if data.metode not in ["NFC", "QR", "HANDMATIG"]:
        raise HTTPException(status_code=400, detail="Metode moet NFC, QR of HANDMATIG wees")

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == data.gebruiker_id,
        models.Gebruikers.Is_Aktief == True,
    ).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind of nie aktief nie")

    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == data.kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Kampus_ID == data.kampus_id,
        models.Lokasie.LOK_Tipe == "Kampus",
    ).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Geen kampus-lokasie vir hierdie kampus gevind nie")

    log = models.ToegangsLogs(
        Gebruiker_ID=data.gebruiker_id,
        Lokasie_ID=lokasie.Lokasie_ID,
        NFC_Tags_ID=None,
        TOE_Rigting="GEWEIER",
        TOE_Metode=data.metode,
        TOE_Auto_Uitgecheck=False,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "message": "Toegang geweier",
            "log_id": log.Log_ID,
            "gebruiker_id": gebruiker.Gebruiker_ID,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "kampus_id": kampus.Kampus_ID,
            "kampus": kampus.KAM_Naam,
            "lokasie_id": lokasie.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam,
            "tyd": log.TOE_Tydstempel.isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Eksterne Event-gaste — dieselfde Kampus Skandeer vloei
# ---------------------------------------------------------------------------

def _event_guest_from_scan(db: Session, scan_kode: str):
    clean = (scan_kode or "").strip()
    if clean.upper().startswith("MOON-EVENT:"):
        token = clean.split(":", 1)[1].strip()
    else:
        token = clean
    if not token:
        raise HTTPException(status_code=400, detail="Event QR is leeg of ongeldig")

    rsvp = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.QR_Token == token
    ).first()
    if rsvp is None:
        raise HTTPException(status_code=404, detail="Event QR word nie herken nie")
    return rsvp


def _validate_event_guest_access(db: Session, rsvp, kampus_id: int):
    if rsvp.RSVP_Status != "GAAN":
        raise HTTPException(status_code=403, detail="Hierdie Event RSVP is gekanselleer; QR is ongeldig")

    event = db.query(models.Funksie).filter(
        models.Funksie.Funksie_ID == rsvp.Funksie_ID
    ).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event bestaan nie meer nie")
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF":
        raise HTTPException(status_code=403, detail="Hierdie Event is nie meer aktief nie")
    if event.Kampus_ID != kampus_id:
        raise HTTPException(status_code=403, detail="Hierdie Event QR is vir 'n ander kampus")

    now = datetime.utcnow()
    if now < event.FUN_Begin_Tyd - timedelta(hours=4):
        raise HTTPException(status_code=403, detail="Dit is nog te vroeg vir hierdie Event se toegang")
    if now > event.FUN_Eind_Tyd + timedelta(hours=6):
        raise HTTPException(status_code=403, detail="Hierdie Event se toegangstyd is reeds verby")

    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if kampus is None:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")
    return event, kampus


def _last_event_guest_gate_log(db: Session, publiek_rsvp_id: int, event_id: int):
    return (
        db.query(models.FunksiePubliekToegang)
        .filter(
            models.FunksiePubliekToegang.Publiek_RSVP_ID == publiek_rsvp_id,
            models.FunksiePubliekToegang.Funksie_ID == event_id,
            models.FunksiePubliekToegang.Rigting.in_(["IN", "UIT"]),
        )
        .order_by(models.FunksiePubliekToegang.Tydstempel.desc())
        .first()
    )


@router.post("/wagte/event/scan")
def wagte_event_guest_scan(
    data: schemas.WagteEventGuestScanRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    if not current_user.Is_Aktief:
        raise HTTPException(status_code=403, detail="Wag-gebruiker is nie aktief nie")

    rsvp = _event_guest_from_scan(db, data.scan_kode)
    event, kampus = _validate_event_guest_access(db, rsvp, data.kampus_id)
    last = _last_event_guest_gate_log(db, rsvp.Publiek_RSVP_ID, event.Funksie_ID)
    voorgestelde = "UIT" if last is not None and last.Rigting == "IN" else "IN"

    return schemas.APIResponse(
        sukses=True,
        data={
            "publiek_rsvp_id": rsvp.Publiek_RSVP_ID,
            "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
            "selfoon": rsvp.Selfoon,
            "epos": rsvp.Epos,
            "event_id": event.Funksie_ID,
            "event_naam": event.FUN_Naam,
            "kampus_id": kampus.Kampus_ID,
            "kampus_naam": kampus.KAM_Naam,
            "begin_tyd": event.FUN_Begin_Tyd.isoformat() + "Z",
            "eind_tyd": event.FUN_Eind_Tyd.isoformat() + "Z",
            "voorgestelde_rigting": voorgestelde,
            "laaste_rigting": last.Rigting if last else None,
            "laaste_tyd": last.Tydstempel.isoformat() + "Z" if last else None,
        },
    )


@router.post("/wagte/event/confirm")
def wagte_event_guest_confirm(
    data: schemas.WagteEventGuestConfirmRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    rigting = (data.rigting or "").strip().upper()
    metode = (data.metode or "QR").strip().upper()
    if rigting not in {"IN", "UIT"}:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")
    if metode not in {"QR", "HANDMATIG"}:
        raise HTTPException(status_code=400, detail="Metode moet QR of HANDMATIG wees")

    rsvp = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.Publiek_RSVP_ID == data.publiek_rsvp_id
    ).first()
    if rsvp is None:
        raise HTTPException(status_code=404, detail="Eksterne Event RSVP nie gevind nie")
    event, kampus = _validate_event_guest_access(db, rsvp, data.kampus_id)
    last = _last_event_guest_gate_log(db, rsvp.Publiek_RSVP_ID, event.Funksie_ID)

    if rigting == "IN" and last is not None and last.Rigting == "IN":
        raise HTTPException(status_code=409, detail="Hierdie Event-gas is reeds IN")
    if rigting == "UIT" and (last is None or last.Rigting != "IN"):
        raise HTTPException(status_code=409, detail="Hierdie Event-gas is nie tans IN nie")

    log = models.FunksiePubliekToegang(
        Publiek_RSVP_ID=rsvp.Publiek_RSVP_ID,
        Funksie_ID=event.Funksie_ID,
        Kampus_ID=kampus.Kampus_ID,
        Wag_ID=current_user.Gebruiker_ID,
        Rigting=rigting,
        Metode=metode,
        Tydstempel=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "toegang_id": log.Toegang_ID,
            "publiek_rsvp_id": rsvp.Publiek_RSVP_ID,
            "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
            "event_id": event.Funksie_ID,
            "event_naam": event.FUN_Naam,
            "kampus_id": kampus.Kampus_ID,
            "kampus_naam": kampus.KAM_Naam,
            "rigting": rigting,
            "metode": metode,
            "tyd": log.Tydstempel.isoformat() + "Z",
        },
    )


@router.post("/wagte/event/decline")
def wagte_event_guest_decline(
    data: schemas.WagteEventGuestDeclineRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    metode = (data.metode or "QR").strip().upper()
    if metode not in {"QR", "HANDMATIG"}:
        raise HTTPException(status_code=400, detail="Metode moet QR of HANDMATIG wees")

    rsvp = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.Publiek_RSVP_ID == data.publiek_rsvp_id
    ).first()
    if rsvp is None:
        raise HTTPException(status_code=404, detail="Eksterne Event RSVP nie gevind nie")
    event, kampus = _validate_event_guest_access(db, rsvp, data.kampus_id)

    log = models.FunksiePubliekToegang(
        Publiek_RSVP_ID=rsvp.Publiek_RSVP_ID,
        Funksie_ID=event.Funksie_ID,
        Kampus_ID=kampus.Kampus_ID,
        Wag_ID=current_user.Gebruiker_ID,
        Rigting="GEWEIER",
        Metode=metode,
        Tydstempel=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "toegang_id": log.Toegang_ID,
            "publiek_rsvp_id": rsvp.Publiek_RSVP_ID,
            "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
            "event_id": event.Funksie_ID,
            "event_naam": event.FUN_Naam,
            "rigting": "GEWEIER",
            "tyd": log.Tydstempel.isoformat() + "Z",
        },
    )
