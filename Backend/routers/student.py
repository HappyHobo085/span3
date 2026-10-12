"""Student scan and search routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
import models, schemas, auth

router = APIRouter(tags=["Student"])


def _escape_like(value: str) -> str:
    """Escapeer LIKE-wildcards (% en _) om SQL-inspuiting te voorkom."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post("/student/scan-klas")
def student_scan_klas(
    data: schemas.StudentKlasScanRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    if data.rigting not in ["IN", "UIT"]:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")

    # MOON-SEC-006: die bediener dwing self af dat die student nou 'n roosterklas
    # in hierdie lokaal het; 'n skandering buite die klas skryf geen bywoning nie.
    from routers.klasse import bepaal_huidige_klas_vir_nfc

    huidig = bepaal_huidige_klas_vir_nfc(db, current_user, data.nfc_uid)
    student, tag, lokasie = huidig["student"], huidig["tag"], huidig["lokasie"]

    log = models.ToegangsLogs(
        NFC_Tags_ID=tag.NFC_Tags_ID,
        Gebruiker_ID=current_user.Gebruiker_ID,
        Lokasie_ID=lokasie.Lokasie_ID,
        TOE_Rigting=data.rigting,
        TOE_Metode="NFC",
        TOE_Auto_Uitgecheck=False,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "Log_ID": log.Log_ID,
            "Student_Nommer": student.STU_Nommer,
            "Lokasie_ID": lokasie.Lokasie_ID,
            "LOK_Naam": lokasie.LOK_Naam,
            "Kampus_ID": lokasie.Kampus_ID,
            "NFC_UID": tag.NFC_UID,
            "Rigting": log.TOE_Rigting,
            "Tyd": log.TOE_Tydstempel.isoformat(),
        }
    )


@router.get("/studente/search")
def soek_studente(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    search = q.strip()

    if len(search) < 2:
        return {"sukses": True, "data": []}

    resultate = (
        db.query(models.Student, models.Gebruikers)
        .join(
            models.Gebruikers,
            models.Gebruikers.Gebruiker_ID == models.Student.Gebruiker_ID,
        )
        .filter(
            models.Gebruikers.Is_Aktief == True,
            or_(
                models.Gebruikers.GEB_Naam.ilike(f"%{_escape_like(search)}%", escape="\\"),
                models.Gebruikers.GEB_Van.ilike(f"%{_escape_like(search)}%", escape="\\"),
                models.Student.STU_Nommer.ilike(f"%{_escape_like(search)}%", escape="\\"),
            ),
        )
        .limit(20)
        .all()
    )

    return {
        "sukses": True,
        "data": [
            {
                "gebruiker_id": gebruiker.Gebruiker_ID,
                "student_nommer": student.STU_Nommer,
                "student_is_koshuis": student.STU_Is_Koshuis,
                "naam": gebruiker.GEB_Naam,
                "van": gebruiker.GEB_Van,
                "foto_url": gebruiker.GEB_Profiel_Foto,
            }
            for student, gebruiker in resultate
            if gebruiker.Gebruiker_ID != current_user.Gebruiker_ID
        ],
    }
