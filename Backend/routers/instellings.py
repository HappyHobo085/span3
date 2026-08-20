"""Instellings (Settings) — Admin-only endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models, schemas, auth

router = APIRouter(tags=["Instellings"])


@router.get("/instellings", response_model=schemas.APIResponse[List[schemas.InstellingRead]])
def kry_instellings(
    db: Session = Depends(get_db),
    is_admin: bool = Depends(auth.check_admin)
):
    instellings = db.query(models.Instelling).all()
    return schemas.APIResponse(sukses=True, data=instellings)


@router.get("/instellings/{sleutel}", response_model=schemas.APIResponse[schemas.InstellingRead])
def kry_instelling(
    sleutel: str,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(auth.check_admin)
):
    instelling = db.query(models.Instelling).filter(
        models.Instelling.Sleutel == sleutel
    ).first()

    if not instelling:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instelling '{sleutel}' nie gevind nie"
        )

    return schemas.APIResponse(sukses=True, data=instelling)


@router.put("/instellings/{sleutel}", response_model=schemas.APIResponse[schemas.InstellingRead])
def werk_instelling_by(
    sleutel: str,
    instelling_in: schemas.InstellingUpdate,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(auth.check_admin)
):
    instelling = db.query(models.Instelling).filter(
        models.Instelling.Sleutel == sleutel
    ).first()

    if not instelling:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instelling '{sleutel}' nie gevind nie"
        )

    instelling.Waarde = instelling_in.Waarde
    if instelling_in.Beskrywing is not None:
        instelling.Beskrywing = instelling_in.Beskrywing

    db.commit()
    db.refresh(instelling)

    return schemas.APIResponse(sukses=True, data=instelling)
