"""Bywoningsverslae — Excel-uitvoer vir Admin, Kampus_Opsigter en Personeel."""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
import models, auth
from services.verslag_service import genereer_verslag, _SA_TZ

router = APIRouter(prefix="/verslae", tags=["Verslae"])

check_verslag = auth.RoleChecker(["Administrateur", "Kampus_Opsigter", "Personeel"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _parse_datum(waarde: Optional[str], naam: str) -> Optional[date]:
    if not waarde:
        return None
    try:
        return date.fromisoformat(waarde)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Ongeldige '{naam}'-datum; gebruik YYYY-MM-DD")


@router.get("/bywoning/export")
def eksporteer_bywoning(
    request: Request,
    van: Optional[str] = Query(None, description="Begindatum (YYYY-MM-DD); verstek 30 dae terug"),
    tot: Optional[str] = Query(None, description="Einddatum (YYYY-MM-DD); verstek vandag"),
    kampus_id: Optional[int] = Query(None, description="Slegs admin: beperk tot een kampus"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(check_verslag),
):
    """Laai 'n Excel-verslag af met huidige en historiese bywoning binne die gebruiker se omvang."""
    vandag = datetime.now(_SA_TZ).date()
    tot_dag = _parse_datum(tot, "tot") or vandag
    van_dag = _parse_datum(van, "van") or (tot_dag - timedelta(days=29))
    rolle = list(getattr(request.state, "roles", []) or auth._haal_rol_names_uit_loaded(current_user))

    inhoud, lêernaam = genereer_verslag(db, current_user, rolle, van_dag, tot_dag, kampus_id)
    return Response(
        content=inhoud,
        media_type=XLSX_MEDIA,
        headers={
            "Content-Disposition": f'attachment; filename="{lêernaam}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
