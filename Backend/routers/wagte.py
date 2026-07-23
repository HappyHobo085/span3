"""Wagte (Guard) and Sekuriteit routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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
