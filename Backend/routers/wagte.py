"""Wagte (Guard) and Sekuriteit routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
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
def wagte_kampusse(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    query = db.query(models.Kampus)
    rolle = auth._haal_rol_names_uit_loaded(current_user)
    if "Administrateur" not in rolle and "Sekuriteit_Wag" not in rolle:
        # 'n Opsigter bestuur net sy eie kampus (MOON-SEC-008); die app se
        # opsigter- en noodgevalskerms begin op die eerste kampus in hierdie lys.
        koppeling = current_user.kampus_opsigter
        eie_kampus = koppeling.Kampus_ID if koppeling is not None else None
        query = query.filter(models.Kampus.Kampus_ID == eie_kampus)
    kampusse = query.all()
    return schemas.APIResponse(
        sukses=True,
        data=[
            {"kampus_id": k.Kampus_ID, "naam": k.KAM_Naam, "adres": k.KAM_Adres}
            for k in kampusse
        ],
    )


def _ensure_kampus_lokasie(db: Session, kampus):
    """Kry (of skep eenmalig) die fisiese kampushek-lokasie."""
    lokasie = (
        db.query(models.Lokasie)
        .filter(
            models.Lokasie.Kampus_ID == kampus.Kampus_ID,
            func.lower(models.Lokasie.LOK_Tipe) == "kampus",
        )
        .first()
    )
    created = False
    if lokasie is None:
        lokasie = models.Lokasie(
            LOK_Naam=kampus.KAM_Naam,
            LOK_Tipe="Kampus",
            Kampus_ID=kampus.Kampus_ID,
        )
        db.add(lokasie)
        db.flush()
        created = True
    return lokasie, created


def _ensure_koshuis_lokasie(db: Session, koshuis):
    """
    Elke koshuis kry sy eie Lokasie met LOK_Tipe='Koshuis'.
    Dit laat ToegangsLogs die koshuis onafhanklik van die kampus log.
    """
    if koshuis.Kampus_ID is None:
        raise HTTPException(
            status_code=409,
            detail=f"Koshuis '{koshuis.KOS_Naam}' het nog nie 'n Kampus_ID nie",
        )

    lokasie = (
        db.query(models.Lokasie)
        .filter(
            models.Lokasie.Kampus_ID == koshuis.Kampus_ID,
            func.lower(models.Lokasie.LOK_Tipe) == "koshuis",
            models.Lokasie.LOK_Naam == koshuis.KOS_Naam,
        )
        .first()
    )
    created = False
    if lokasie is None:
        lokasie = models.Lokasie(
            LOK_Naam=koshuis.KOS_Naam,
            LOK_Tipe="Koshuis",
            Kampus_ID=koshuis.Kampus_ID,
        )
        db.add(lokasie)
        db.flush()
        created = True
    return lokasie, created


@router.get("/wagte/skandeerplekke", response_model=schemas.APIResponse[List[dict]])
def wagte_skandeerplekke(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    """
    Een vlak vir die wag:
      - KAMPUS
      - KOSHUIS

    Die onderliggende koshuis-lokasie is steeds 'n aparte Lokasie_ID,
    daarom verander 'n koshuis scan nooit die kampus se eie IN/UIT log nie.
    """
    data = []
    created_any = False

    for kampus in db.query(models.Kampus).order_by(models.Kampus.KAM_Naam.asc()).all():
        lokasie, created = _ensure_kampus_lokasie(db, kampus)
        created_any = created_any or created
        data.append({
            "tipe": "KAMPUS",
            "naam": kampus.KAM_Naam,
            "adres": kampus.KAM_Adres,
            "lokasie_id": lokasie.Lokasie_ID,
            "kampus_id": kampus.Kampus_ID,
            "koshuis_id": None,
        })

    for koshuis in db.query(models.Koshuis).order_by(models.Koshuis.KOS_Naam.asc()).all():
        lokasie, created = _ensure_koshuis_lokasie(db, koshuis)
        created_any = created_any or created
        data.append({
            "tipe": "KOSHUIS",
            "naam": koshuis.KOS_Naam,
            "adres": koshuis.KOS_Adres,
            "lokasie_id": lokasie.Lokasie_ID,
            "kampus_id": koshuis.Kampus_ID,
            "koshuis_id": koshuis.Koshuis_ID,
        })

    if created_any:
        db.commit()

    data.sort(key=lambda x: (0 if x["tipe"] == "KAMPUS" else 1, (x["naam"] or "").lower()))
    return schemas.APIResponse(sukses=True, data=data)


def _resolve_wagte_scanplek(
    db: Session,
    *,
    lokasie_id=None,
    kampus_id=None,
    koshuis_id=None,
):
    """
    Resolveer die gekose scanplek server-side.
    Ou kampus-kliënte kan nog net kampus_id stuur.
    """
    if lokasie_id is None:
        if kampus_id is None:
            raise HTTPException(status_code=400, detail="Geen skandeerplek/lokasie is gekies nie")

        kampus = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == kampus_id
        ).first()
        if kampus is None:
            raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

        lokasie = (
            db.query(models.Lokasie)
            .filter(
                models.Lokasie.Kampus_ID == kampus_id,
                func.lower(models.Lokasie.LOK_Tipe) == "kampus",
            )
            .first()
        )
        if lokasie is None:
            raise HTTPException(
                status_code=404,
                detail="Geen kampus-lokasie vir hierdie kampus gevind nie",
            )
        return lokasie, kampus, None, "KAMPUS"

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Lokasie_ID == lokasie_id
    ).first()
    if lokasie is None:
        raise HTTPException(status_code=404, detail="Skandeerplek-lokasie nie gevind nie")

    tipe = (lokasie.LOK_Tipe or "").strip().upper()
    if tipe == "KAMPUS":
        kampus = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == lokasie.Kampus_ID
        ).first()
        if kampus is None:
            raise HTTPException(status_code=404, detail="Kampus nie gevind nie")
        return lokasie, kampus, None, "KAMPUS"

    if tipe == "KOSHUIS":
        query = db.query(models.Koshuis)
        if koshuis_id is not None:
            query = query.filter(models.Koshuis.Koshuis_ID == koshuis_id)
        else:
            query = query.filter(
                models.Koshuis.Kampus_ID == lokasie.Kampus_ID,
                models.Koshuis.KOS_Naam == lokasie.LOK_Naam,
            )

        koshuis = query.first()
        if koshuis is None:
            raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

        if (
            koshuis.Kampus_ID != lokasie.Kampus_ID
            or koshuis.KOS_Naam != lokasie.LOK_Naam
        ):
            raise HTTPException(status_code=400, detail="Koshuis en skandeerplek stem nie ooreen nie")

        kampus = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == lokasie.Kampus_ID
        ).first()
        return lokasie, kampus, koshuis, "KOSHUIS"

    raise HTTPException(
        status_code=400,
        detail="Hierdie lokasie is nie 'n geldige kampus- of koshuisskandeerplek nie",
    )


def _validate_koshuis_inwoner(db: Session, gebruiker_id: int, koshuis):
    student = db.query(models.Student).filter(
        models.Student.Gebruiker_ID == gebruiker_id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=403,
            detail="Koshuis-skandering is net vir studente",
        )

    if not student.STU_Is_Koshuis or student.Koshuis_ID != koshuis.Koshuis_ID:
        raise HTTPException(
            status_code=403,
            detail=f"Toegang geweier - student is nie 'n inwoner van {koshuis.KOS_Naam} nie",
        )

    return student


@router.get("/wagte/nommer/check")
def wagte_nommer_check(
    nommer: str,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
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
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_opsigter),
):
    """Besoekers wat vandag by die gekose kampus toegelaat is."""
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    # 'n Opsigter sien net sy eie kampus se besoekers (name en selfoonnommers).
    if "Administrateur" not in auth._haal_rol_names_uit_loaded(current_user):
        koppeling = current_user.kampus_opsigter
        if koppeling is None or koppeling.Kampus_ID != kampus_id:
            raise HTTPException(status_code=403, detail="Jy het nie toegang tot hierdie kampus se besoekers nie")

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
    # Elke ry is 'n Row van (BesoekerUitnodiging, Gebruikers) — pak uit
    for item, gasheer in besoekers:
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
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    scan = data.scan_kode.strip()
    gebruiker = None

    student = db.query(models.Student).filter(models.Student.STU_Nommer == scan).first()
    if student:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
        ).first()

    if not gebruiker:
        personeel = db.query(models.Personeel).filter(
            models.Personeel.PER_Nommer == scan
        ).first()
        if personeel:
            gebruiker = db.query(models.Gebruikers).filter(
                models.Gebruikers.Gebruiker_ID == personeel.Gebruiker_ID
            ).first()

    if not gebruiker:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.GEB_ID_Nommer == scan
        ).first()

    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    if not gebruiker.Is_Aktief:
        raise HTTPException(status_code=403, detail="Gebruiker is gedeaktiveer en mag nie skandeer nie")

    lokasie = None
    koshuis = None
    scanplek_tipe = None

    if data.lokasie_id is not None:
        lokasie, _kampus, koshuis, scanplek_tipe = _resolve_wagte_scanplek(
            db,
            lokasie_id=data.lokasie_id,
            koshuis_id=data.koshuis_id,
        )

        if scanplek_tipe == "KOSHUIS":
            _validate_koshuis_inwoner(db, gebruiker.Gebruiker_ID, koshuis)

        # IN/UIT is PER GEKOSE PLEK. 'n Koshuis log kan dus nie die kampus
        # se voorgestelde rigting verander nie, en andersom.
        laaste_log = (
            db.query(models.ToegangsLogs)
            .filter(
                models.ToegangsLogs.Gebruiker_ID == gebruiker.Gebruiker_ID,
                models.ToegangsLogs.Lokasie_ID == lokasie.Lokasie_ID,
                models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
            )
            .order_by(
                models.ToegangsLogs.TOE_Tydstempel.desc(),
                models.ToegangsLogs.Log_ID.desc(),
            )
            .first()
        )
    else:
        # Backwards compatibility vir 'n ou kliënt wat nog geen lokasie_id stuur nie.
        laaste_log = (
            db.query(models.ToegangsLogs)
            .filter(
                models.ToegangsLogs.Gebruiker_ID == gebruiker.Gebruiker_ID,
                models.ToegangsLogs.TOE_Rigting.in_(["IN", "UIT"]),
            )
            .order_by(
                models.ToegangsLogs.TOE_Tydstempel.desc(),
                models.ToegangsLogs.Log_ID.desc(),
            )
            .first()
        )

    voorgestelde_rigting = (
        "UIT" if laaste_log is not None and laaste_log.TOE_Rigting == "IN" else "IN"
    )

    return schemas.APIResponse(
        sukses=True,
        data={
            "gebruiker_id": gebruiker.Gebruiker_ID,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "id_nommer": gebruiker.GEB_ID_Nommer,
            "foto_url": gebruiker.GEB_Profiel_Foto,
            "voorgestelde_rigting": voorgestelde_rigting,
            "scanplek_tipe": scanplek_tipe,
            "lokasie_id": lokasie.Lokasie_ID if lokasie else None,
            "koshuis_id": koshuis.Koshuis_ID if koshuis else None,
        },
    )


@router.post("/wagte/profile/verify")
def wagte_profile_verify(
    data: schemas.WagteProfileVerifyRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
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

    lokasie, kampus, koshuis, scanplek_tipe = _resolve_wagte_scanplek(
        db,
        lokasie_id=data.lokasie_id,
        kampus_id=data.kampus_id,
        koshuis_id=data.koshuis_id,
    )

    if scanplek_tipe == "KOSHUIS":
        _validate_koshuis_inwoner(db, gebruiker.Gebruiker_ID, koshuis)

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
            "scanplek_tipe": scanplek_tipe,
            "kampus_id": kampus.Kampus_ID if kampus else None,
            "kampus": kampus.KAM_Naam if kampus else None,
            "koshuis_id": koshuis.Koshuis_ID if koshuis else None,
            "koshuis": koshuis.KOS_Naam if koshuis else None,
            "lokasie_id": lokasie.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam,
            "tyd": log.TOE_Tydstempel.isoformat(),
        },
    )


@router.post("/wagte/profile/decline")
def decline_profile_access(
    data: schemas.WagteProfileDeclineRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit),
):
    if data.metode not in ["NFC", "QR", "HANDMATIG"]:
        raise HTTPException(status_code=400, detail="Metode moet NFC, QR of HANDMATIG wees")

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == data.gebruiker_id,
        models.Gebruikers.Is_Aktief == True,
    ).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind of nie aktief nie")

    lokasie, kampus, koshuis, scanplek_tipe = _resolve_wagte_scanplek(
        db,
        lokasie_id=data.lokasie_id,
        kampus_id=data.kampus_id,
        koshuis_id=data.koshuis_id,
    )

    # Selfs 'n WEIER by 'n koshuis word teen DIE KOSHUIS se lokasie gelog.
    if scanplek_tipe == "KOSHUIS":
        _validate_koshuis_inwoner(db, gebruiker.Gebruiker_ID, koshuis)

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
            "scanplek_tipe": scanplek_tipe,
            "kampus_id": kampus.Kampus_ID if kampus else None,
            "kampus": kampus.KAM_Naam if kampus else None,
            "koshuis_id": koshuis.Koshuis_ID if koshuis else None,
            "koshuis": koshuis.KOS_Naam if koshuis else None,
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
        raise HTTPException(status_code=400, detail="Geleentheid-QR-kode is leeg of ongeldig")

    rsvp = db.query(models.FunksiePubliekRSVP).filter(
        models.FunksiePubliekRSVP.QR_Token == token
    ).first()
    if rsvp is None:
        raise HTTPException(status_code=404, detail="Geleentheid-QR-kode word nie herken nie")
    return rsvp


def _validate_event_guest_access(db: Session, rsvp, kampus_id: int):
    if rsvp.RSVP_Status != "GAAN":
        raise HTTPException(status_code=403, detail="Hierdie RSVP vir die geleentheid is gekanselleer; die QR-kode is ongeldig")

    event = db.query(models.Funksie).filter(
        models.Funksie.Funksie_ID == rsvp.Funksie_ID
    ).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Geleentheid bestaan nie meer nie")
    if not event.FUN_Is_Aktief or event.FUN_Status != "AKTIEF":
        raise HTTPException(status_code=403, detail="Hierdie geleentheid is nie meer aktief nie")
    if event.Kampus_ID != kampus_id:
        raise HTTPException(status_code=403, detail="Hierdie geleentheid-QR-kode is vir 'n ander kampus")

    now = datetime.utcnow()
    if now < event.FUN_Begin_Tyd - timedelta(hours=4):
        raise HTTPException(status_code=403, detail="Dit is nog te vroeg vir toegang tot hierdie geleentheid")
    if now > event.FUN_Eind_Tyd + timedelta(hours=6):
        raise HTTPException(status_code=403, detail="Hierdie geleentheid se toegangstyd is reeds verby")

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
        raise HTTPException(status_code=404, detail="Eksterne RSVP vir geleentheid nie gevind nie")
    event, kampus = _validate_event_guest_access(db, rsvp, data.kampus_id)
    last = _last_event_guest_gate_log(db, rsvp.Publiek_RSVP_ID, event.Funksie_ID)

    if rigting == "IN" and last is not None and last.Rigting == "IN":
        raise HTTPException(status_code=409, detail="Hierdie geleentheidsgas is reeds IN")
    if rigting == "UIT" and (last is None or last.Rigting != "IN"):
        raise HTTPException(status_code=409, detail="Hierdie geleentheidsgas is nie tans IN nie")

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
        raise HTTPException(status_code=404, detail="Eksterne RSVP vir geleentheid nie gevind nie")
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
