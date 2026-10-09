"""MOON Noodgeval Step 10 — scoped background/device authentication.

The device token intentionally has a very small permission surface:
- report ONTVANG
- report KENNIS_GENEEM
- read its own device-auth status

It cannot create, resend, close, or read general protected MOON data.
"""

from datetime import datetime, timedelta
import hashlib
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

import auth
import database
import models
import schemas


router = APIRouter(prefix="/noodgeval/device", tags=["Noodgeval Device Auth"])

DEVICE_TOKEN_DAYS = max(1, int(os.getenv("MOON_DEVICE_TOKEN_DAYS", "180")))
DEVICE_HEADER = "X-MOON-Device-Token"


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=4, max_length=255)
    device_name: str | None = Field(default=None, max_length=255)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    return str(value)


def _device_identity(
    db: Session,
    raw_token: str | None,
) -> dict:
    token = (raw_token or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Toesteltoken ontbreek.",
        )

    row = db.execute(
        text('''
            SELECT
                d."DeviceAuth_ID",
                d."Gebruiker_ID",
                d."NDA_Device_ID",
                d."NDA_Device_Name",
                d."NDA_Is_Aktief",
                d."NDA_Verval_Op",
                g."Is_Aktief" AS "Gebruiker_Is_Aktief"
            FROM noodgeval_device_auth d
            JOIN gebruikers g
              ON g."Gebruiker_ID" = d."Gebruiker_ID"
            WHERE d."NDA_Token_Hash" = :token_hash
            LIMIT 1
        '''),
        {"token_hash": _hash_token(token)},
    ).mappings().first()

    if not row or not row["NDA_Is_Aktief"] or not row["Gebruiker_Is_Aktief"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Toesteltoken is ongeldig of gedeaktiveer.",
        )

    expiry = row["NDA_Verval_Op"]
    if expiry is None or expiry <= _utcnow():
        db.execute(
            text('''
                UPDATE noodgeval_device_auth
                SET "NDA_Is_Aktief" = FALSE
                WHERE "DeviceAuth_ID" = :device_auth_id
            '''),
            {"device_auth_id": row["DeviceAuth_ID"]},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Toesteltoken het verval. Meld weer aan om dit te hernu.",
        )

    db.execute(
        text('''
            UPDATE noodgeval_device_auth
            SET "NDA_Laas_Gebruik_Op" = :now
            WHERE "DeviceAuth_ID" = :device_auth_id
        '''),
        {"now": _utcnow(), "device_auth_id": row["DeviceAuth_ID"]},
    )
    db.commit()
    return dict(row)


def _ensure_emergency(db: Session, noodgeval_id: int, *, must_be_active: bool) -> dict:
    row = db.execute(
        text('''
            SELECT "Noodgeval_ID", "NOO_Status"
            FROM noodgeval
            WHERE "Noodgeval_ID" = :noodgeval_id
            LIMIT 1
        '''),
        {"noodgeval_id": noodgeval_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Noodgeval nie gevind nie.")
    if must_be_active and row["NOO_Status"] != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie noodgeval is reeds gesluit.")
    return dict(row)


def _read_ack(db: Session, noodgeval_id: int, gebruiker_id: int) -> dict:
    row = db.execute(
        text('''
            SELECT
                "Kennisname_ID",
                "Noodgeval_ID",
                "Gebruiker_ID",
                "NOK_Status",
                "NOK_Ontvang_Op",
                "NOK_Kennis_Geneem_Op",
                "Gewysig_Op"
            FROM noodgeval_kennisname
            WHERE "Noodgeval_ID" = :noodgeval_id
              AND "Gebruiker_ID" = :gebruiker_id
            LIMIT 1
        '''),
        {"noodgeval_id": noodgeval_id, "gebruiker_id": gebruiker_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail="Kennisname kon nie teruggelees word nie.")

    data = dict(row)
    for key in ("NOK_Ontvang_Op", "NOK_Kennis_Geneem_Op", "Gewysig_Op"):
        data[key] = _iso(data.get(key))
    return data


@router.post("/register", response_model=schemas.APIResponse[dict])
def register_device(
    payload: DeviceRegisterRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    if not getattr(current_user, "Is_Aktief", False):
        raise HTTPException(status_code=403, detail="Gebruiker is nie aktief nie.")

    device_id = payload.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="Toestel-ID ontbreek.")

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    now = _utcnow()
    expiry = now + timedelta(days=DEVICE_TOKEN_DAYS)

    row = db.execute(
        text('''
            INSERT INTO noodgeval_device_auth (
                "Gebruiker_ID",
                "NDA_Device_ID",
                "NDA_Device_Name",
                "NDA_Token_Hash",
                "NDA_Is_Aktief",
                "NDA_Geskep_Op",
                "NDA_Laas_Gebruik_Op",
                "NDA_Verval_Op"
            ) VALUES (
                :gebruiker_id,
                :device_id,
                :device_name,
                :token_hash,
                TRUE,
                :now,
                :now,
                :expiry
            )
            ON CONFLICT ("Gebruiker_ID", "NDA_Device_ID")
            DO UPDATE SET
                "NDA_Device_Name" = EXCLUDED."NDA_Device_Name",
                "NDA_Token_Hash" = EXCLUDED."NDA_Token_Hash",
                "NDA_Is_Aktief" = TRUE,
                "NDA_Laas_Gebruik_Op" = EXCLUDED."NDA_Laas_Gebruik_Op",
                "NDA_Verval_Op" = EXCLUDED."NDA_Verval_Op"
            RETURNING "DeviceAuth_ID"
        '''),
        {
            "gebruiker_id": current_user.Gebruiker_ID,
            "device_id": device_id,
            "device_name": (payload.device_name or "").strip() or None,
            "token_hash": token_hash,
            "now": now,
            "expiry": expiry,
        },
    ).mappings().first()
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={
            "device_auth_id": row["DeviceAuth_ID"],
            "gebruiker_id": current_user.Gebruiker_ID,
            "device_id": device_id,
            "device_token": raw_token,
            "verval_op": _iso(expiry),
            "scope": ["NOODGEVAL_ONTVANG", "NOODGEVAL_KENNISNAME"],
        },
        fout=None,
    )


@router.get("/status", response_model=schemas.APIResponse[dict])
def device_status(
    x_moon_device_token: str | None = Header(default=None, alias=DEVICE_HEADER),
    db: Session = Depends(database.get_db),
):
    identity = _device_identity(db, x_moon_device_token)
    return schemas.APIResponse(
        sukses=True,
        data={
            "device_auth_id": identity["DeviceAuth_ID"],
            "gebruiker_id": identity["Gebruiker_ID"],
            "device_id": identity["NDA_Device_ID"],
            "device_name": identity["NDA_Device_Name"],
            "verval_op": _iso(identity["NDA_Verval_Op"]),
            "scope": ["NOODGEVAL_ONTVANG", "NOODGEVAL_KENNISNAME"],
        },
        fout=None,
    )


@router.post("/{noodgeval_id}/ontvang", response_model=schemas.APIResponse[dict])
def device_ontvang(
    noodgeval_id: int,
    x_moon_device_token: str | None = Header(default=None, alias=DEVICE_HEADER),
    db: Session = Depends(database.get_db),
):
    identity = _device_identity(db, x_moon_device_token)
    _ensure_emergency(db, noodgeval_id, must_be_active=False)
    gebruiker_id = int(identity["Gebruiker_ID"])
    now = _utcnow()

    db.execute(
        text('''
            INSERT INTO noodgeval_kennisname (
                "Noodgeval_ID",
                "Gebruiker_ID",
                "NOK_Status",
                "NOK_Ontvang_Op",
                "NOK_Kennis_Geneem_Op",
                "Gewysig_Op"
            ) VALUES (
                :noodgeval_id,
                :gebruiker_id,
                'ONTVANG',
                :now,
                NULL,
                :now
            )
            ON CONFLICT ("Noodgeval_ID", "Gebruiker_ID")
            DO UPDATE SET
                "NOK_Status" = CASE
                    WHEN noodgeval_kennisname."NOK_Status" = 'KENNIS_GENEEM'
                    THEN 'KENNIS_GENEEM'
                    ELSE 'ONTVANG'
                END,
                "NOK_Ontvang_Op" = COALESCE(
                    noodgeval_kennisname."NOK_Ontvang_Op",
                    EXCLUDED."NOK_Ontvang_Op"
                ),
                "Gewysig_Op" = EXCLUDED."Gewysig_Op"
        '''),
        {"noodgeval_id": noodgeval_id, "gebruiker_id": gebruiker_id, "now": now},
    )
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data=_read_ack(db, noodgeval_id, gebruiker_id),
        fout=None,
    )


@router.post("/{noodgeval_id}/kennisname", response_model=schemas.APIResponse[dict])
def device_kennisname(
    noodgeval_id: int,
    x_moon_device_token: str | None = Header(default=None, alias=DEVICE_HEADER),
    db: Session = Depends(database.get_db),
):
    identity = _device_identity(db, x_moon_device_token)
    _ensure_emergency(db, noodgeval_id, must_be_active=True)
    gebruiker_id = int(identity["Gebruiker_ID"])
    now = _utcnow()

    db.execute(
        text('''
            INSERT INTO noodgeval_kennisname (
                "Noodgeval_ID",
                "Gebruiker_ID",
                "NOK_Status",
                "NOK_Ontvang_Op",
                "NOK_Kennis_Geneem_Op",
                "Gewysig_Op"
            ) VALUES (
                :noodgeval_id,
                :gebruiker_id,
                'KENNIS_GENEEM',
                :now,
                :now,
                :now
            )
            ON CONFLICT ("Noodgeval_ID", "Gebruiker_ID")
            DO UPDATE SET
                "NOK_Status" = 'KENNIS_GENEEM',
                "NOK_Ontvang_Op" = COALESCE(
                    noodgeval_kennisname."NOK_Ontvang_Op",
                    EXCLUDED."NOK_Ontvang_Op"
                ),
                "NOK_Kennis_Geneem_Op" = COALESCE(
                    noodgeval_kennisname."NOK_Kennis_Geneem_Op",
                    EXCLUDED."NOK_Kennis_Geneem_Op"
                ),
                "Gewysig_Op" = EXCLUDED."Gewysig_Op"
        '''),
        {"noodgeval_id": noodgeval_id, "gebruiker_id": gebruiker_id, "now": now},
    )
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data=_read_ack(db, noodgeval_id, gebruiker_id),
        fout=None,
    )
