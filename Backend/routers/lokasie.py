"""Lokasie (Location) CRUD, Klas creation, and NFC-tag-to-lokasie linking."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
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
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_opsigter),
):
    """Lokasies met hul NFC-UID's: slegs Admin en Kampus_Opsigter (MOON-SEC-006)."""
    # selectinload on Lokasie.nfc_tags means tags are loaded in the same query
    lokasies = db.query(models.Lokasie).all()
    result = []
    created_tag = False

    for l in lokasies:
        # Gebruik eager-loaded nfc_tags relationship (geen ekstra query nodig nie)
        aktiewe_tags = [t for t in (l.nfc_tags or []) if t.NFC_Is_Aktief]
        tag = aktiewe_tags[0] if aktiewe_tags else None

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
            created_tag = True

        result.append({
            "Lokasie_ID": l.Lokasie_ID,
            "LOK_Naam": l.LOK_Naam,
            "LOK_Tipe": l.LOK_Tipe,
            "Kampus_ID": l.Kampus_ID,
            "NFC_UID": tag.NFC_UID
        })

    if created_tag:
        db.commit()
    return schemas.APIResponse(sukses=True, data=result)


@router.get("/klasse")
def lys_klasse(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    _: bool = Depends(auth.check_opsigter),
):
    """Gee 'n lys van alle klasse (lokasies met LOK_Tipe == 'Klaskamer').

    Bevat NFC-UID's, dus slegs Admin en Kampus_Opsigter (MOON-SEC-006).
    """
    # selectinload on Lokasie.nfc_tags means tags are loaded in the same query
    lokasies = (
        db.query(models.Lokasie)
        .filter(models.Lokasie.LOK_Tipe == "Klaskamer")
        .all()
    )
    result = []
    for l in lokasies:
        # Gebruik eager-loaded nfc_tags (geen ekstra query nodig nie)
        aktiewe_tags = [t for t in (l.nfc_tags or []) if t.NFC_Is_Aktief]
        tag = aktiewe_tags[0] if aktiewe_tags else None
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
    _: bool = Depends(auth.check_opsigter),
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
    _: bool = Depends(auth.check_opsigter),
):
    """Gee bywoningdata vir 'n klas op 'n gegewe datum.

    Response bevat: total_students (est), present_count, present list (met tyd), absent list.
    """
    from datetime import datetime, timedelta

    if date:
        try:
            day = datetime.fromisoformat(date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Ongeldige datumformaat — gebruik JJJJ-MM-DD")
    else:
        day = datetime.utcnow().date()

    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    # Select the latest IN scan per student in one query.
    latest_in = (
        db.query(
            models.ToegangsLogs.Gebruiker_ID,
            func.max(models.ToegangsLogs.TOE_Tydstempel).label("latest_scan"),
        )
        .filter(
            models.ToegangsLogs.Lokasie_ID == lokasie_id,
            models.ToegangsLogs.TOE_Tydstempel >= day_start,
            models.ToegangsLogs.TOE_Tydstempel < day_end,
            models.ToegangsLogs.TOE_Rigting == "IN",
        )
        .group_by(models.ToegangsLogs.Gebruiker_ID)
        .subquery()
    )

    present_rows = (
        db.query(models.Gebruikers, models.Student, models.ToegangsLogs)
        .join(
            latest_in,
            models.Gebruikers.Gebruiker_ID == latest_in.c.Gebruiker_ID,
        )
        .outerjoin(
            models.Student,
            models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID,
        )
        .join(
            models.ToegangsLogs,
            and_(
                models.ToegangsLogs.Gebruiker_ID == latest_in.c.Gebruiker_ID,
                models.ToegangsLogs.TOE_Tydstempel == latest_in.c.latest_scan,
                models.ToegangsLogs.Lokasie_ID == lokasie_id,
                models.ToegangsLogs.TOE_Rigting == "IN",
            ),
        )
        .all()
    )

    present_ids = [gebruiker.Gebruiker_ID for gebruiker, _, _ in present_rows]

    # Roster = distinct users who have ever scanned at this lokasie (best-effort)
    roster_rows = (
        db.query(models.ToegangsLogs.Gebruiker_ID)
        .filter(models.ToegangsLogs.Lokasie_ID == lokasie_id)
        .distinct()
        .all()
    )
    roster_ids = [r[0] for r in roster_rows]

    # --- Batch fetch all user+student records at once (geen N+1 nie) ---
    all_user_ids = list(set(present_ids) | set(roster_ids))
    user_map = {}
    if all_user_ids:
        rows = (
            db.query(models.Gebruikers, models.Student)
            .outerjoin(models.Student, models.Student.Gebruiker_ID == models.Gebruikers.Gebruiker_ID)
            .filter(models.Gebruikers.Gebruiker_ID.in_(all_user_ids))
            .all()
        )
        for gebruiker, student in rows:
            user_map[gebruiker.Gebruiker_ID] = (gebruiker, student)

    # --- Batch fetch last-in timestamps for present users ---
    last_in_map = {}
    if present_ids:
        last_in_rows = (
            db.query(
                models.ToegangsLogs.Gebruiker_ID,
                func.max(models.ToegangsLogs.TOE_Tydstempel).label("laaste_in")
            )
            .filter(
                models.ToegangsLogs.Gebruiker_ID.in_(present_ids),
                models.ToegangsLogs.Lokasie_ID == lokasie_id,
                func.date(models.ToegangsLogs.TOE_Tydstempel) == day,
                models.ToegangsLogs.TOE_Rigting == "IN",
            )
            .group_by(models.ToegangsLogs.Gebruiker_ID)
            .all()
        )
        last_in_map = {row.Gebruiker_ID: row.laaste_in for row in last_in_rows}

    present = []
    for uid in present_ids:
        entry = user_map.get(uid)
        if not entry:
            continue
        gebruiker, student = entry
        tyd = last_in_map.get(uid)
        present.append({
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
            "STU_Nommer": student.STU_Nommer if student else None,
            "Tyd": tyd.isoformat() if tyd else None,
        })

    roster_users = []
    for uid in roster_ids:
        entry = user_map.get(uid)
        if not entry:
            continue
        gebruiker, student = entry
        roster_users.append({
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
            "STU_Nommer": student.STU_Nommer if student else None,
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

        gevraagde_uid = (klas_in.NFC_UID or "").strip()
        if gevraagde_uid and gevraagde_uid.upper() != "TEMP":
            bestaande = db.query(models.NFC_Tags).filter(
                models.NFC_Tags.NFC_UID == gevraagde_uid
            ).first()
            if bestaande:
                raise HTTPException(
                    status_code=409,
                    detail=f"NFC-UID '{gevraagde_uid}' is reeds aan 'n ander tag gekoppel",
                )
            generated_uid = gevraagde_uid
        else:
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


@router.put("/lokasies/{lokasie_id}/nfc-tag", response_model=schemas.APIResponse[schemas.NFCTag])
def stel_lokasie_nfc_tag(
    lokasie_id: int,
    tag_in: schemas.LokasieNFCTagUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """Hernoem die lokaal se aktiewe Lokasie-tag na 'n fisiese UID (bv. "L4").

    Doelbewus nie die generiese POST /nfc-tags-upsert nie: dié sou stilweg
    'n ander lokaal se tag kon skuif. Hier valideer ons eers uniekheid.
    """
    nuwe_uid = (tag_in.NFC_UID or "").strip()
    if not nuwe_uid:
        raise HTTPException(status_code=400, detail="NFC_UID mag nie leeg wees nie")

    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokasie nie gevind nie")

    aktiewe = [t for t in (lokasie.nfc_tags or []) if t.NFC_Is_Aktief]
    tag = aktiewe[0] if aktiewe else None

    bestaande = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == nuwe_uid).first()
    if bestaande and (tag is None or bestaande.NFC_Tags_ID != tag.NFC_Tags_ID):
        raise HTTPException(
            status_code=409,
            detail=f"NFC-UID '{nuwe_uid}' is reeds aan 'n ander tag gekoppel",
        )

    if tag is None:
        tag = models.NFC_Tags(
            NFC_UID=nuwe_uid,
            Lokasie_ID=lokasie_id,
            NFC_Tipe="Lokasie",
            NFC_Is_Aktief=True,
        )
        db.add(tag)
    else:
        tag.NFC_UID = nuwe_uid
    db.commit()
    db.refresh(tag)
    return schemas.APIResponse(sukses=True, data=tag)


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
