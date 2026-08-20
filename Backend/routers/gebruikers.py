"""Gebruikers (Users) CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional

from database import get_db
import models, schemas, auth
from services.gebruiker_service import (
    sync_gebruiker_subrekords,
    sync_gebruiker_nfc_tag,
    sync_gebruiker_roles,
    gebruiker_to_dict,
    kontroleer_unieke_gebruiker_velde,
    kry_rol,
    get_user_role_names,
)
from services.nfc_service import deaktiveer_nfc_tags

router = APIRouter(prefix="/gebruikers", tags=["Gebruikers"])


@router.post("", response_model=schemas.APIResponse[Any], status_code=status.HTTP_201_CREATED)
def skep_gebruiker(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    kontroleer_unieke_gebruiker_velde(
        db,
        epos=str(user_in.GEB_Epos),
        id_nommer=user_in.GEB_ID_Nommer,
    )
    user_data = user_in.dict(exclude_unset=True)
    role_ids = user_data.get("Rol_IDs") or ([user_data["Rol_ID"]] if user_data.get("Rol_ID") is not None else [])
    if not role_ids:
        raise HTTPException(status_code=400, detail="Ten minste een rol moet verskaf word")
    primary_role_id = user_data.get("Rol_ID") or role_ids[0]

    try:
        db_user = models.Gebruikers(
            GEB_Naam=user_in.GEB_Naam,
            GEB_Van=user_in.GEB_Van,
            GEB_ID_Nommer=user_in.GEB_ID_Nommer,
            GEB_Epos=str(user_in.GEB_Epos),
            GEB_Wagwoord=auth.get_password_hash(user_in.GEB_Wagwoord),
            GEB_Selfoon_Nr=user_in.GEB_Selfoon_Nr,
            GEB_Profiel_Foto=user_in.GEB_Profiel_Foto,
            Rol_ID=primary_role_id,
            Is_Aktief=user_in.Is_Aktief
        )

        db.add(db_user)
        db.flush()

        sync_gebruiker_roles(db, db_user, role_ids, primary_role_id=primary_role_id)
        db.flush()
        sync_gebruiker_subrekords(db, db_user, get_user_role_names(db, db_user), user_data, creating=True)
        sync_gebruiker_nfc_tag(db, db_user.Gebruiker_ID, user_data)

        db.commit()
        db.refresh(db_user)

        return schemas.APIResponse(sukses=True, data=gebruiker_to_dict(db_user))

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie gebruiker skep nie: {str(e)}")


@router.put("/{user_id}", response_model=schemas.APIResponse[Any])
def opdateer_gebruiker(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    db_user = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    update_data = user_in.dict(exclude_unset=True)

    if "GEB_Epos" in update_data or "GEB_ID_Nommer" in update_data:
        kontroleer_unieke_gebruiker_velde(
            db,
            epos=str(update_data["GEB_Epos"]) if "GEB_Epos" in update_data else None,
            id_nommer=update_data.get("GEB_ID_Nommer"),
            exclude_user_id=user_id,
        )

    role_ids = None
    if "Rol_IDs" in update_data:
        role_ids = update_data.pop("Rol_IDs")
    elif "Rol_ID" in update_data:
        role_ids = [update_data["Rol_ID"]]

    gewone_velde = {
        "GEB_Naam", "GEB_Van", "GEB_ID_Nommer", "GEB_Epos",
        "GEB_Selfoon_Nr", "GEB_Profiel_Foto", "Rol_ID", "Is_Aktief",
    }

    try:
        for key, value in update_data.items():
            if key not in gewone_velde:
                continue
            if key == "GEB_Epos" and value is not None:
                value = str(value)
            setattr(db_user, key, value)

        if "GEB_Wagwoord" in update_data and update_data["GEB_Wagwoord"]:
            db_user.GEB_Wagwoord = auth.get_password_hash(update_data["GEB_Wagwoord"])

        if role_ids is not None:
            sync_gebruiker_roles(
                db,
                db_user,
                role_ids,
                primary_role_id=update_data.get("Rol_ID") or role_ids[0],
            )

        role_names = get_user_role_names(db, db_user)
        sync_gebruiker_subrekords(db, db_user, role_names, update_data)
        sync_gebruiker_nfc_tag(db, user_id, update_data)

        db.commit()
        db.refresh(db_user)
        return schemas.APIResponse(sukses=True, data=gebruiker_to_dict(db_user))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie gebruiker opdateer nie: {str(e)}")


@router.delete("/{user_id}", response_model=schemas.APIResponse[dict])
def verwyder_gebruiker(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    if user_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy kan nie jou eie rekening skrap nie.")

    return opdateer_gebruiker_status(user_id=user_id, is_aktief=False, db=db, current_user=current_user, is_admin=is_admin)


@router.get("", response_model=schemas.APIResponse[List[Any]])
def lees_gebruikers(
    skip: int = 0,
    limit: int = 100,
    kampus_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    query = db.query(models.Gebruikers)
    role_names = get_user_role_names(db, current_user)
    is_admin = "Administrateur" in role_names

    if not is_admin and "Kampus_Opsigter" in role_names:
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        if not opsigter_info:
            raise HTTPException(status_code=403, detail="Opsigter is nie aan 'n kampus gekoppel nie.")
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == opsigter_info.Kampus_ID)
    elif not is_admin and kampus_id:
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == kampus_id)

    gebruikers = query.offset(skip).limit(limit).all()

    if not is_admin and "Sekuriteit_Wag" in role_names:
        return schemas.APIResponse(
            sukses=True,
            data=[
                {
                    "Gebruiker_ID": g.Gebruiker_ID,
                    "GEB_Naam": g.GEB_Naam,
                    "GEB_Van": g.GEB_Van,
                    "GEB_ID_Nommer": g.GEB_ID_Nommer,
                    "GEB_Profiel_Foto": g.GEB_Profiel_Foto,
                    "Is_Aktief": g.Is_Aktief,
                }
                for g in gebruikers
            ]
        )

    return schemas.APIResponse(
        sukses=True,
        data=[gebruiker_to_dict(g) for g in gebruikers]
    )


@router.get("/{user_id}", response_model=schemas.APIResponse[Any])
def lees_gebruiker(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if gebruiker is None:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    role_names = get_user_role_names(db, current_user)
    is_admin = "Administrateur" in role_names

    if not is_admin and "Kampus_Opsigter" in role_names:
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        teiken_opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == user_id).first()
        if teiken_opsigter_info and teiken_opsigter_info.Kampus_ID != opsigter_info.Kampus_ID:
            raise HTTPException(status_code=403, detail="Jy het nie toegang tot hierdie gebruiker nie.")

    if not is_admin and "Sekuriteit_Wag" in role_names:
        return schemas.APIResponse(
            sukses=True,
            data={
                "Gebruiker_ID": gebruiker.Gebruiker_ID,
                "GEB_Naam": gebruiker.GEB_Naam,
                "GEB_Van": gebruiker.GEB_Van,
                "GEB_ID_Nommer": gebruiker.GEB_ID_Nommer,
                "GEB_Profiel_Foto": gebruiker.GEB_Profiel_Foto,
                "Is_Aktief": gebruiker.Is_Aktief,
            }
        )

    return schemas.APIResponse(sukses=True, data=gebruiker_to_dict(gebruiker))


@router.patch("/{user_id}/status", response_model=schemas.APIResponse[dict])
def opdateer_gebruiker_status(
    user_id: int,
    is_aktief: bool,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    try:
        gebruiker.Is_Aktief = is_aktief

        if not is_aktief:
            deaktiveer_nfc_tags(db, user_id)

            nuwe_waarskuwing = models.Waarskuwings(
                Gebruiker_ID=user_id,
                WAA_Beskrywing=f"Gebruiker handmatig deur Admin ({current_user.GEB_Naam}) onaktief gemerk",
                WAA_Status="OOP"
            )
            db.add(nuwe_waarskuwing)

        db.commit()
        db.refresh(gebruiker)

        return schemas.APIResponse(
            sukses=True,
            data={"boodskap": "Status suksesvol opgedateer", "is_aktief": gebruiker.Is_Aktief}
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fout tydens transaksie: {str(e)}")
