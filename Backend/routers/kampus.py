"""Kampus (Campus) CRUD + status routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
import models, schemas, auth
from services.status_service import haal_laatste_logs_per_gebruiker

router = APIRouter(prefix="/kampusse", tags=["Kampus"])


@router.get("", response_model=schemas.APIResponse[List[schemas.Kampus]])
def lees_kampusse(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()
    return schemas.APIResponse(sukses=True, data=kampusse)


@router.post("", response_model=schemas.APIResponse[schemas.Kampus], status_code=status.HTTP_201_CREATED)
def skep_kampus(
    kampus_in: schemas.KampusCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    naam = kampus_in.KAM_Naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")

    bestaande = db.query(models.Kampus).filter(
        func.lower(models.Kampus.KAM_Naam) == naam.lower()
    ).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")

    kampus = models.Kampus(KAM_Naam=naam, KAM_Adres=kampus_in.KAM_Adres)
    db.add(kampus)
    db.commit()
    db.refresh(kampus)

    hek = models.Lokasie(
        LOK_Naam=f"{kampus.KAM_Naam}-Hek",
        LOK_Tipe="Kampus",
        Kampus_ID=kampus.Kampus_ID,
    )
    db.add(hek)
    db.commit()

    return schemas.APIResponse(sukses=True, data=kampus)


@router.put("/{kampus_id}", response_model=schemas.APIResponse[schemas.Kampus])
def opdateer_kampus(
    kampus_id: int,
    kampus_in: schemas.KampusUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    update_data = kampus_in.dict(exclude_unset=True)
    if "KAM_Naam" in update_data:
        naam = update_data["KAM_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")
        bestaande = db.query(models.Kampus).filter(
            func.lower(models.Kampus.KAM_Naam) == naam.lower(),
            models.Kampus.Kampus_ID != kampus_id,
        ).first()
        if bestaande:
            raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")
        kampus.KAM_Naam = naam

    if "KAM_Adres" in update_data:
        kampus.KAM_Adres = update_data["KAM_Adres"]

    db.commit()
    db.refresh(kampus)
    return schemas.APIResponse(sukses=True, data=kampus)


@router.delete("/{kampus_id}", response_model=schemas.APIResponse[dict])
def verwyder_kampus(
    kampus_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    if db.query(models.Lokasie).filter(models.Lokasie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog lokale aan hierdie kampus gekoppel")
    if db.query(models.Koshuis).filter(models.Koshuis.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog koshuise aan hierdie kampus gekoppel")
    if db.query(models.Funksie).filter(models.Funksie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog funksies aan hierdie kampus gekoppel")
    if db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog opsigters aan hierdie kampus gekoppel")

    db.delete(kampus)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Kampus suksesvol verwyder"})


@router.get("/status", response_model=schemas.APIResponse[List[schemas.KampusSummaryStatus]])
def kry_kampus_status_opsomming(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()
    resultate = []
    for k in kampusse:
        scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, kampus_id=k.Kampus_ID)
        resultate.append(schemas.KampusSummaryStatus(
            Kampus_ID=k.Kampus_ID,
            KAM_Naam=k.KAM_Naam,
            KAM_Adres=k.KAM_Adres,
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out)
        ))
    return schemas.APIResponse(sukses=True, data=resultate)


@router.get("/{kampus_id}/status", response_model=schemas.APIResponse[schemas.KampusDetailStatus])
def kry_kampus_status_detail(kampus_id: int, db: Session = Depends(get_db)):
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, kampus_id=kampus_id)

    return schemas.APIResponse(
        sukses=True,
        data=schemas.KampusDetailStatus(
            Kampus_ID=kampus.Kampus_ID,
            KAM_Naam=kampus.KAM_Naam,
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out),
            scanned_in=scanned_in,
            scanned_out=scanned_out
        )
    )
