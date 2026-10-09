"""NFC tag management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models, schemas, auth
from services.nfc_service import deaktiveer_nfc_tags

router = APIRouter(prefix="/nfc-tags", tags=["NFC"])


@router.post("/registreer", response_model=schemas.APIResponse[schemas.NFCTag])
def registreer_nfc_tag(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    bestaande_tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == tag_in.NFC_UID).first()
    if bestaande_tag:
        raise HTTPException(status_code=400, detail="NFC-etiket reeds geregistreer")

    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == tag_in.Gebruiker_ID).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    deaktiveer_nfc_tags(db, tag_in.Gebruiker_ID)

    nuwe_tag = models.NFC_Tags(**tag_in.dict())
    db.add(nuwe_tag)
    db.commit()
    db.refresh(nuwe_tag)

    return schemas.APIResponse(sukses=True, data=nuwe_tag)


@router.patch("/{user_id}/deaktiveer", response_model=schemas.APIResponse[dict])
def deaktiveer_gebruiker_nfc_tags(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    updated_count = deaktiveer_nfc_tags(db, user_id)

    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Geen aktiewe NFC-etikette vir hierdie gebruiker gevind nie")

    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "NFC-etikette suksesvol gedeaktiveer"})


@router.get("/{uid}", response_model=schemas.APIResponse[dict])
def kry_lokasie_deur_nfc_uid(
    uid: str,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == uid,
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="NFC-etiket nie gevind of nie aktief nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Lokasie_ID == tag.Lokasie_ID
    ).first()

    if not lokasie:
        raise HTTPException(status_code=404, detail="Geen klaskamer aan hierdie tag gekoppel nie")

    return schemas.APIResponse(
        sukses=True,
        data={
            "uid": tag.NFC_UID,
            "lokasie": {
                "id": lokasie.Lokasie_ID,
                "naam": lokasie.LOK_Naam
            }
        }
    )
