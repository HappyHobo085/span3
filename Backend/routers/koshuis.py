"""Koshuis (Dormitory) CRUD + status routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
import models, schemas, auth
from services.status_service import haal_laatste_logs_per_gebruiker

router = APIRouter(prefix="/koshuise", tags=["Koshuis"])


@router.get("", response_model=schemas.APIResponse[List[schemas.Koshuis]])
def lees_koshuise(db: Session = Depends(get_db)):
    koshuise = db.query(models.Koshuis).all()
    return schemas.APIResponse(sukses=True, data=koshuise)


@router.post("", response_model=schemas.APIResponse[schemas.Koshuis], status_code=status.HTTP_201_CREATED)
def skep_koshuis(
    koshuis_in: schemas.KoshuisCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    naam = koshuis_in.KOS_Naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Koshuisnaam is verpligtend")
    if koshuis_in.KOS_Kapasiteit <= 0:
        raise HTTPException(status_code=400, detail="Kapasiteit moet groter as nul wees")
    if koshuis_in.Kampus_ID is not None:
        kampus_bestaan = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == koshuis_in.Kampus_ID).first()
        if not kampus_bestaan:
            raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")

    bestaande = db.query(models.Koshuis).filter(func.lower(models.Koshuis.KOS_Naam) == naam.lower()).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Koshuisnaam reeds in gebruik")

    koshuis = models.Koshuis(
        KOS_Naam=naam, KOS_Adres=koshuis_in.KOS_Adres,
        KOS_Kapasiteit=koshuis_in.KOS_Kapasiteit, Kampus_ID=koshuis_in.Kampus_ID,
    )
    db.add(koshuis)
    db.commit()
    db.refresh(koshuis)
    return schemas.APIResponse(sukses=True, data=koshuis)


@router.put("/{koshuis_id}", response_model=schemas.APIResponse[schemas.Koshuis])
def opdateer_koshuis(
    koshuis_id: int,
    koshuis_in: schemas.KoshuisUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

    update_data = koshuis_in.dict(exclude_unset=True)

    if "KOS_Naam" in update_data:
        naam = update_data["KOS_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Koshuisnaam is verpligtend")
        bestaande = db.query(models.Koshuis).filter(
            func.lower(models.Koshuis.KOS_Naam) == naam.lower(),
            models.Koshuis.Koshuis_ID != koshuis_id,
        ).first()
        if bestaande:
            raise HTTPException(status_code=400, detail="Koshuisnaam reeds in gebruik")
        koshuis.KOS_Naam = naam

    if "KOS_Adres" in update_data:
        koshuis.KOS_Adres = update_data["KOS_Adres"]
    if "KOS_Kapasiteit" in update_data:
        if update_data["KOS_Kapasiteit"] is None or update_data["KOS_Kapasiteit"] <= 0:
            raise HTTPException(status_code=400, detail="Kapasiteit moet groter as nul wees")
        koshuis.KOS_Kapasiteit = update_data["KOS_Kapasiteit"]
    if "Kampus_ID" in update_data:
        if update_data["Kampus_ID"] is not None:
            kampus_bestaan = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == update_data["Kampus_ID"]).first()
            if not kampus_bestaan:
                raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")
        koshuis.Kampus_ID = update_data["Kampus_ID"]

    db.commit()
    db.refresh(koshuis)
    return schemas.APIResponse(sukses=True, data=koshuis)


@router.delete("/{koshuis_id}", response_model=schemas.APIResponse[dict])
def verwyder_koshuis(
    koshuis_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")
    if db.query(models.Student).filter(models.Student.Koshuis_ID == koshuis_id).first():
        raise HTTPException(status_code=400, detail="Kan nie koshuis verwyder nie: daar is nog studente aan hierdie koshuis gekoppel")
    db.delete(koshuis)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Koshuis suksesvol verwyder"})


@router.get("/{koshuis_id}/status", response_model=schemas.APIResponse[schemas.KoshuisDetailStatus])
def kry_koshuis_status_detail(
    koshuis_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_sekuriteit),
):
    """Name, e-posse en intydse bewegings: slegs sekuriteitsrolle (MOON-SEC-003)."""
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

    studente = db.query(models.Student).filter(models.Student.Koshuis_ID == koshuis_id).all()
    scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, koshuis_id=koshuis_id)

    return schemas.APIResponse(
        sukses=True,
        data=schemas.KoshuisDetailStatus(
            Koshuis_ID=koshuis.Koshuis_ID,
            KOS_Naam=koshuis.KOS_Naam,
            KOS_Kapasiteit=koshuis.KOS_Kapasiteit,
            inwoner_count=len(studente),
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out),
            scanned_in=scanned_in,
            scanned_out=scanned_out
        )
    )
