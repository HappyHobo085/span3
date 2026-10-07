from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db
from services.lokaalgebruik_ml_service import (
    kry_ml_status,
    voorspel_vir_kampus_en_dag,
)

router = APIRouter(prefix="/lokaalgebruik", tags=["Lokaalgebruik ML"])


@router.get("/voorspellings")
def lokaalgebruik_voorspellings(
    kampus_id: int = Query(..., ge=1),
    dag: str = Query(..., min_length=3, max_length=20),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    data = voorspel_vir_kampus_en_dag(db, kampus_id, dag)
    return schemas.APIResponse(sukses=True, data=data)


@router.get("/ml-status")
def lokaalgebruik_ml_status(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    return schemas.APIResponse(sukses=True, data=kry_ml_status())
