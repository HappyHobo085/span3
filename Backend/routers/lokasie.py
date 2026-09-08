"""Lokasie (Location) CRUD, Klas creation, and NFC-tag-to-lokasie linking."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database import get_db
import models, schemas, auth
from services.nfc_service import genereer_unieke_nfc_uid

router = APIRouter(tags=["Lokasie"])


@router.post("/lokasies", response_model=schemas.APIResponse[schemas.Lokasie], status_code=status.HTTP_201_CREATED)
def skep_lokasie(
    lokasie_in: schemas.LokasieCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    db_lokasie = models.Lokasie(**lokasie_in.dict())
    db.add(db_lokasie)
    db.commit()
    db.refresh(db_lokasie)
    return schemas.APIResponse(sukses=True, data=db_lokasie)


@router.get("/lokasies")
def lys_lokasies(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    lokasies = db.query(models.Lokasie).all()
    result = []

    for l in lokasies:
        tag = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.Lokasie_ID == l.Lokasie_ID,
            models.NFC_Tags.NFC_Is_Aktief == True
        ).first()

        if not tag:
            tag = models.NFC_Tags(
                NFC_UID=genereer_unieke_nfc_uid(db),
                Lokasie_ID=l.Lokasie_ID,
                Gebruiker_ID=None,
                NFC_Tipe="Lokasie",
                NFC_Is_Aktief=True
            )
            db.add(tag)
            db.flush()

        result.append({
            "Lokasie_ID": l.Lokasie_ID,
            "LOK_Naam": l.LOK_Naam,
            "LOK_Tipe": l.LOK_Tipe,
            "Kampus_ID": l.Kampus_ID,
            "NFC_UID": tag.NFC_UID
        })

    db.commit()
    return schemas.APIResponse(sukses=True, data=result)


@router.get("/klasse")
def lys_klasse(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Gee 'n lys van alle klasse (lokasies met LOK_Tipe == 'Klaskamer')."""
    lokasies = db.query(models.Lokasie).filter(models.Lokasie.LOK_Tipe == "Klaskamer").all()
    result = []
    for l in lokasies:
        tag = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.Lokasie_ID == l.Lokasie_ID,
            models.NFC_Tags.NFC_Is_Aktief == True
        ).first()
        result.append({
            "Lokasie_ID": l.Lokasie_ID,
            "LOK_Naam": l.LOK_Naam,
            "Kampus_ID": l.Kampus_ID,
            "NFC_UID": tag.NFC_UID if tag else None,
        })

    return schemas.APIResponse(sukses=True, data=result)


@router.get("/klasse/{lokasie_id}/roster")
def kry_klas_roster(
    lokasie_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Gee die lys van studente wat ooit by hierdie lokaal ingeskandeer het (unikale gebruikers)."""
    # Join with toegangs_logs to find distinct gebruikers for this lokasie
    resultate = (
        db.query(models.Gebruikers, models.Student)
        .join(models.Student, models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
        .join(models.ToegangsLogs, models.ToegangsLogs.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
        .filter(models.ToegangsLogs.Lokasie_ID == lokasie_id)
        .distinct(models.Gebruikers.Gebruiker_ID)
        .all()
    )

    roster = []
    for gebruiker, student in resultate:
        if not gebruiker:
            continue
        roster.append({
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
            "STU_Nommer": student.STU_Nommer if student else None,
        })

    return schemas.APIResponse(sukses=True, data=roster)


@router.get("/klasse/{lokasie_id}/bywoning")
def kry_klas_bywoning(
    lokasie_id: int,
    date: Optional[str] = None,  # ISO date string YYYY-MM-DD; defaults to today
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    """Gee bywoningdata vir 'n klas op 'n gegewe datum.

    Response bevat: total_students (est), present_count, present list (met tyd), absent list.
    """
    from datetime import datetime, date as _date

    if date:
        try:
            day = datetime.fromisoformat(date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Ongeldige datumformaat — gebruik YYYY-MM-DD")
    else:
        day = datetime.utcnow().date()

    # Students who scanned IN on that day for this lokasie
    present_rows = (
        db.query(models.ToegangsLogs.Gebruiker_ID)
        .filter(
            models.ToegangsLogs.Lokasie_ID == lokasie_id,
            func.date(models.ToegangsLogs.TOE_Tydstempel) == day,
            models.ToegangsLogs.TOE_Rigting == "IN",
        )
        .distinct()
        .all()
    )

    present_ids = [r[0] for r in present_rows]

    # Roster = distinct users who have ever scanned at this lokasie (best-effort)
    roster_rows = (
        db.query(models.ToegangsLogs.Gebruiker_ID)
        .filter(models.ToegangsLogs.Lokasie_ID == lokasie_id)
        .distinct()
        .all()
    )
    roster_ids = [r[0] for r in roster_rows]

    # Fetch user details for present and roster
    present = []
    if present_ids:
        for uid in present_ids:
            gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == uid).first()
            if not gebruiker:
                continue
            last_in = (
                db.query(models.ToegangsLogs)
                .filter(
                    models.ToegangsLogs.Gebruiker_ID == uid,
                    models.ToegangsLogs.Lokasie_ID == lokasie_id,
                    func.date(models.ToegangsLogs.TOE_Tydstempel) == day,
                    models.ToegangsLogs.TOE_Rigting == "IN",
                )
                .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())
                .first()
            )
            tyd = None
            if last_in is not None and getattr(last_in, "TOE_Tydstempel", None) is not None:
                tyd = last_in.TOE_Tydstempel.isoformat()

            present.append({
                "Gebruiker_ID": gebruiker.Gebruiker_ID,
                "GEB_Naam": gebruiker.GEB_Naam,
                "GEB_Van": gebruiker.GEB_Van,
                "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
                "STU_Nommer": db.query(models.Student.STU_Nommer).filter(models.Student.Gebruiker_ID == gebruiker.Gebruiker_ID).scalar(),
                "Tyd": tyd,
            })

    roster_users = []
    if roster_ids:
        users = (
            db.query(models.Gebruikers, models.Student)
            .join(models.Student, models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
            .filter(models.Gebruikers.Gebruiker_ID.in_(roster_ids))
            .all()
        )
        for gebruiker, student in users:
            roster_users.append({
                "Gebruiker_ID": gebruiker.Gebruiker_ID,
                "GEB_Naam": gebruiker.GEB_Naam,
                "GEB_Van": gebruiker.GEB_Van,
                "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
                "STU_Nommer": student.STU_Nommer,
            })

    absent = [u for u in roster_users if u["Gebruiker_ID"] not in present_ids]

    total_students = len(roster_users)
    present_count = len(present)

    percent = round((present_count / total_students) * 100) if total_students > 0 else 0

    return schemas.APIResponse(
        sukses=True,
        data={
            "Lokasie_ID": lokasie_id,
            "Datum": day.isoformat(),
            "Total_Students": total_students,
            "Present_Count": present_count,
            "Present": present,
            "Absent": absent,
            "Percent": percent,
        }
    )


@router.put("/lokasies/{lokasie_id}", response_model=schemas.APIResponse[schemas.Lokasie])
def opdateer_lokasie(
    lokasie_id: int,
    lokasie_in: schemas.LokasieUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

    update_data = lokasie_in.dict(exclude_unset=True)

    if "LOK_Naam" in update_data:
        naam = update_data["LOK_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Lokaalnaam is verpligtend")
        lokasie.LOK_Naam = naam
    if "LOK_Tipe" in update_data:
        lokasie.LOK_Tipe = update_data["LOK_Tipe"]
    if "Kampus_ID" in update_data:
        if update_data["Kampus_ID"] is not None:
            kampus_bestaan = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == update_data["Kampus_ID"]).first()
            if not kampus_bestaan:
                raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")
        lokasie.Kampus_ID = update_data["Kampus_ID"]

    db.commit()
    db.refresh(lokasie)
    return schemas.APIResponse(sukses=True, data=lokasie)


@router.delete("/lokasies/{lokasie_id}", response_model=schemas.APIResponse[dict])
def verwyder_lokasie(
    lokasie_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")
    if db.query(models.ToegangsLogs).filter(models.ToegangsLogs.Lokasie_ID == lokasie_id).first():
        raise HTTPException(status_code=400, detail="Kan nie lokaal verwyder nie: daar is toegangslogs vir hierdie lokaal")
    db.query(models.NFC_Tags).filter(models.NFC_Tags.Lokasie_ID == lokasie_id).delete()
    db.delete(lokasie)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Lokaal suksesvol verwyder"})


@router.post("/klasse", response_model=schemas.APIResponse[schemas.KlasSkepResult], status_code=status.HTTP_201_CREATED)
def skep_klas_met_nfc(
    klas_in: schemas.KlasSkep,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    if klas_in.Kampus_ID is not None:
        kampus_bestaan = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == klas_in.Kampus_ID).first()
        if not kampus_bestaan:
            raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")

    try:
        db_lokasie = models.Lokasie(
            LOK_Naam=klas_in.LOK_Naam.strip(),
            LOK_Tipe="Klaskamer",
            Kampus_ID=klas_in.Kampus_ID,
        )
        db.add(db_lokasie)
        db.flush()

        generated_uid = genereer_unieke_nfc_uid(db)

        db_tag = models.NFC_Tags(
            NFC_UID=generated_uid,
            Lokasie_ID=db_lokasie.Lokasie_ID,
            NFC_Tipe="Lokasie",
            NFC_Is_Aktief=True,
        )
        db.add(db_tag)
        db.commit()
        db.refresh(db_lokasie)
        db.refresh(db_tag)

        result = schemas.KlasSkepResult(
            lokasie=schemas.Lokasie.from_orm(db_lokasie),
            nfc_tag=schemas.NFCTag.from_orm(db_tag),
        )
        return schemas.APIResponse(sukses=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie klas skep nie: {str(e)}")


@router.post("/nfc-tags", response_model=schemas.APIResponse[schemas.NFCTag])
def koppel_nfc_tag_aan_lokasie(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    db_tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == tag_in.NFC_UID).first()

    if db_tag:
        for key, value in tag_in.dict(exclude_unset=True).items():
            setattr(db_tag, key, value)
    else:
        db_tag = models.NFC_Tags(**tag_in.dict())
        db.add(db_tag)

    db.commit()
    db.refresh(db_tag)
    return schemas.APIResponse(sukses=True, data=db_tag)
