"""Lokasie (Location) CRUD, Klas creation, and NFC-tag-to-lokasie linking."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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
            "Kampus_ID": l.Kampus_ID,
            "NFC_UID": tag.NFC_UID
        })

    db.commit()
    return schemas.APIResponse(sukses=True, data=result)


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
