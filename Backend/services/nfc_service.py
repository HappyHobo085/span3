"""NFC tag business logic — extracted from main.py helpers."""

import uuid

from sqlalchemy.orm import Session

import models


def deaktiveer_nfc_tags(db: Session, user_id: int):
    """Deactivate all active NFC tags for a user. Returns update count."""
    return db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == user_id,
        models.NFC_Tags.NFC_Is_Aktief == True
    ).update({"NFC_Is_Aktief": False})


def genereer_unieke_nfc_uid(db: Session, length: int = 8) -> str:
    """Generate a unique NFC UID that doesn't exist in the database."""
    while True:
        uid = uuid.uuid4().hex[:length].upper()
        exists = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.NFC_UID == uid
        ).first()
        if not exists:
            return uid
