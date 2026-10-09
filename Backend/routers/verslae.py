"""Bywoningsverslae — oorsig (JSON) en uitvoer (Excel/PDF/Word/teks) vir Admin, Kampus_Opsigter en Personeel."""

from datetime import date, datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
import models, auth
from services.verslag_service import bou_oorsig, genereer_verslag, _SA_TZ
from services.verslag_formate import MEDIA_TIPES

router = APIRouter(prefix="/verslae", tags=["Verslae"])

check_verslag = auth.RoleChecker(["Administrateur", "Kampus_Opsigter", "Personeel"])

# Die webwerf se voorskou wys hoogstens soveel rye per tabel; die aflaai kry alles.
OORSIG_MAKS_RYE = 500


def _parse_datum(waarde: Optional[str], naam: str) -> Optional[date]:
    if not waarde:
        return None
    try:
        return date.fromisoformat(waarde)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Ongeldige '{naam}'-datum; gebruik JJJJ-MM-DD")


def _tydperk(van: Optional[str], tot: Optional[str]) -> tuple[date, date]:
    vandag = datetime.now(_SA_TZ).date()
    tot_dag = _parse_datum(tot, "tot") or vandag
    van_dag = _parse_datum(van, "van") or (tot_dag - timedelta(days=29))
    return van_dag, tot_dag


def _rolle(request: Request, current_user: models.Gebruikers) -> list[str]:
    return list(getattr(request.state, "roles", []) or auth._haal_rol_names_uit_loaded(current_user))


@router.get("/bywoning/oorsig")
def bywoning_oorsig(
    request: Request,
    van: Optional[str] = Query(None, description="Begindatum (YYYY-MM-DD); verstek 30 dae terug"),
    tot: Optional[str] = Query(None, description="Einddatum (YYYY-MM-DD); verstek vandag"),
    kampus_id: Optional[int] = Query(None, description="Slegs admin: beperk tot een kampus"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(check_verslag),
):
    """Die verslag se data vir die webwerf se Verslag-blad (grafieke en lyste)."""
    van_dag, tot_dag = _tydperk(van, tot)
    oorsig = bou_oorsig(
        db, current_user, _rolle(request, current_user), van_dag, tot_dag, kampus_id,
        maks_rye=OORSIG_MAKS_RYE,
    )
    return {"sukses": True, "data": jsonable_encoder(oorsig), "fout": None}


@router.get("/bywoning/export")
def eksporteer_bywoning(
    request: Request,
    van: Optional[str] = Query(None, description="Begindatum (YYYY-MM-DD); verstek 30 dae terug"),
    tot: Optional[str] = Query(None, description="Einddatum (YYYY-MM-DD); verstek vandag"),
    kampus_id: Optional[int] = Query(None, description="Slegs admin: beperk tot een kampus"),
    formaat: Literal["xlsx", "pdf", "docx", "txt"] = Query("xlsx", description="Lêertipe"),
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(check_verslag),
):
    """Laai die verslag af as Excel, PDF, Word of teks, binne die gebruiker se omvang."""
    van_dag, tot_dag = _tydperk(van, tot)
    inhoud, lêernaam = genereer_verslag(
        db, current_user, _rolle(request, current_user), van_dag, tot_dag, kampus_id, formaat=formaat,
    )
    return Response(
        content=inhoud,
        media_type=MEDIA_TIPES[formaat],
        headers={
            "Content-Disposition": f'attachment; filename="{lêernaam}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
