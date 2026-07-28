"""Gebruiker (User) business logic — extracted from main.py helpers."""

import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


def kry_rol(db: Session, rol_id: int) -> models.Rolle:
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == rol_id).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol bestaan nie")
    return rol


def is_personeel_rol(rol_naam: str) -> bool:
    return rol_naam in [
        "Administrateur",
        "Personeel",
        "Sekuriteit_Wag",
        "Kampus_Opsigter",
    ]


def kontroleer_kampus(db: Session, kampus_id: Optional[int]):
    if kampus_id is None:
        return
    if not db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")


def kontroleer_unieke_gebruiker_velde(
    db: Session,
    *,
    epos: Optional[str] = None,
    id_nommer: Optional[str] = None,
    exclude_user_id: Optional[int] = None,
):
    if epos:
        query = db.query(models.Gebruikers).filter(models.Gebruikers.GEB_Epos == epos)
        if exclude_user_id is not None:
            query = query.filter(models.Gebruikers.Gebruiker_ID != exclude_user_id)
        if query.first():
            raise HTTPException(status_code=400, detail="E-pos reeds geregistreer")

    if id_nommer:
        query = db.query(models.Gebruikers).filter(models.Gebruikers.GEB_ID_Nommer == id_nommer)
        if exclude_user_id is not None:
            query = query.filter(models.Gebruikers.Gebruiker_ID != exclude_user_id)
        if query.first():
            raise HTTPException(status_code=400, detail="ID Nommer reeds in gebruik")


def kontroleer_unieke_subnommer(
    db: Session,
    model,
    field_name: str,
    value: Optional[str],
    exclude_user_id: Optional[int] = None,
    detail: str = "Nommer reeds in gebruik",
):
    if not value:
        return

    query = db.query(model).filter(getattr(model, field_name) == value)
    if exclude_user_id is not None:
        query = query.filter(model.Gebruiker_ID != exclude_user_id)
    if query.first():
        raise HTTPException(status_code=400, detail=detail)


def generate_next_per_nommer(db: Session) -> str:
    last = (
        db.query(models.Personeel)
        .filter(models.Personeel.PER_Nommer.like("PER%"))
        .order_by(models.Personeel.PER_Nommer.desc())
        .first()
    )

    if not last or not last.PER_Nommer:
        return "PER0001"

    try:
        next_num = int(last.PER_Nommer.replace("PER", "")) + 1
    except ValueError:
        next_num = 1

    return f"PER{next_num:04d}"


def sync_gebruiker_subrekords(
    db: Session,
    gebruiker: models.Gebruikers,
    rol_naam: str,
    data: dict,
    *,
    creating: bool = False,
):
    # --- Student ---
    if rol_naam == "Student" or "STU_Nommer" in data or "STU_Is_Koshuis" in data or "Koshuis_ID" in data:
        student = db.query(models.Student).filter(
            models.Student.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        stu_nommer = data.get("STU_Nommer")

        if not student and not stu_nommer:
            if creating or rol_naam == "Student":
                raise HTTPException(status_code=400, detail="Studentenommer is verpligtend")

        if stu_nommer:
            kontroleer_unieke_subnommer(
                db,
                models.Student,
                "STU_Nommer",
                stu_nommer,
                exclude_user_id=gebruiker.Gebruiker_ID,
                detail="Studentenommer reeds in gebruik",
            )

            if not student:
                student = models.Student(
                    Gebruiker_ID=gebruiker.Gebruiker_ID,
                    STU_Nommer=stu_nommer,
                )
                db.add(student)
            else:
                student.STU_Nommer = stu_nommer

        if student and "STU_Is_Koshuis" in data:
            student.STU_Is_Koshuis = bool(data["STU_Is_Koshuis"])

        if student and "Koshuis_ID" in data:
            koshuis_id = data["Koshuis_ID"]
            if koshuis_id is not None:
                koshuis = db.query(models.Koshuis).filter(
                    models.Koshuis.Koshuis_ID == koshuis_id
                ).first()
                if not koshuis:
                    raise HTTPException(status_code=400, detail="Koshuis_ID bestaan nie in die databasis nie")
            student.Koshuis_ID = koshuis_id

    # --- Personeel rekord vir ALLE werknemerrolle ---
    if is_personeel_rol(rol_naam) or "PER_Nommer" in data or "PER_Departement" in data:
        personeel = db.query(models.Personeel).filter(
            models.Personeel.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        per_nommer = data.get("PER_Nommer")

        if not personeel and not per_nommer and (creating or is_personeel_rol(rol_naam)):
            per_nommer = generate_next_per_nommer(db)

        if per_nommer:
            kontroleer_unieke_subnommer(
                db,
                models.Personeel,
                "PER_Nommer",
                per_nommer,
                exclude_user_id=gebruiker.Gebruiker_ID,
                detail="Personeelnommer reeds in gebruik",
            )

            if not personeel:
                personeel = models.Personeel(
                    Gebruiker_ID=gebruiker.Gebruiker_ID,
                    PER_Nommer=per_nommer,
                )
                db.add(personeel)
            else:
                personeel.PER_Nommer = per_nommer

        if personeel and "PER_Departement" in data:
            personeel.PER_Departement = data["PER_Departement"]

    # --- Kampus Opsigter subrekord ---
    if rol_naam == "Kampus_Opsigter" or "KAMO_Nommer" in data or "Kampus_ID" in data:
        kontroleer_kampus(db, data.get("Kampus_ID"))

        opsigter = db.query(models.Kampus_Opsigter).filter(
            models.Kampus_Opsigter.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        kamo_nommer = data.get("KAMO_Nommer")

        if not opsigter and rol_naam == "Kampus_Opsigter":
            opsigter = models.Kampus_Opsigter(
                Gebruiker_ID=gebruiker.Gebruiker_ID,
                KAMO_Nommer=per_nommer,
            )
            db.add(opsigter)

        if kamo_nommer:
            kontroleer_unieke_subnommer(
                db,
                models.Kampus_Opsigter,
                "KAMO_Nommer",
                kamo_nommer,
                exclude_user_id=gebruiker.Gebruiker_ID,
                detail="Opsigternommer reeds in gebruik",
            )

            if not opsigter:
                opsigter = models.Kampus_Opsigter(
                    Gebruiker_ID=gebruiker.Gebruiker_ID,
                    KAMO_Nommer=kamo_nommer,
                )
                db.add(opsigter)
            else:
                opsigter.KAMO_Nommer = kamo_nommer

        if opsigter and "Kampus_ID" in data:
            opsigter.Kampus_ID = data["Kampus_ID"]

    # --- Sekuriteit Wag subrekord ---
    if rol_naam == "Sekuriteit_Wag" or "SEK_Nommer" in data:
        wag = db.query(models.Sekuriteit_Wag).filter(
            models.Sekuriteit_Wag.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        sek_nommer = data.get("SEK_Nommer")

        if not wag and rol_naam == "Sekuriteit_Wag":
            wag = models.Sekuriteit_Wag(
                Gebruiker_ID=gebruiker.Gebruiker_ID,
                SEK_Nommer=per_nommer,
            )
            db.add(wag)

        if sek_nommer:
            kontroleer_unieke_subnommer(
                db,
                models.Sekuriteit_Wag,
                "SEK_Nommer",
                sek_nommer,
                exclude_user_id=gebruiker.Gebruiker_ID,
                detail="Wagnommer reeds in gebruik",
            )

            if not wag:
                db.add(models.Sekuriteit_Wag(
                    Gebruiker_ID=gebruiker.Gebruiker_ID,
                    SEK_Nommer=sek_nommer,
                ))
            else:
                wag.SEK_Nommer = sek_nommer


def sync_gebruiker_nfc_tag(db: Session, gebruiker_id: int, data: dict):
    nfc_fields = {"NFC_UID", "NFC_Tipe", "NFC_Is_Aktief"}
    if not any(field in data for field in nfc_fields):
        return

    uid = data.get("NFC_UID")
    nfc_tipe = data.get("NFC_Tipe") or "Gebruiker"
    nfc_is_aktief = data.get("NFC_Is_Aktief", True)

    if uid:
        bestaande_uid = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.NFC_UID == uid,
            models.NFC_Tags.Gebruiker_ID != gebruiker_id,
        ).first()
        if bestaande_uid:
            raise HTTPException(status_code=400, detail="NFC tag reeds aan 'n ander gebruiker gekoppel")

    tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == gebruiker_id
    ).order_by(models.NFC_Tags.NFC_Is_Aktief.desc(), models.NFC_Tags.NFC_Tags_ID.desc()).first()

    if not tag and not uid:
        raise HTTPException(status_code=400, detail="NFC_UID is verpligtend wanneer 'n nuwe NFC tag geskep word")

    if not tag:
        tag = models.NFC_Tags(
            NFC_UID=uid,
            Gebruiker_ID=gebruiker_id,
            NFC_Tipe=nfc_tipe,
            NFC_Is_Aktief=bool(nfc_is_aktief),
        )
        db.add(tag)
        return

    if uid:
        tag.NFC_UID = uid
    if "NFC_Tipe" in data:
        tag.NFC_Tipe = nfc_tipe
    if "NFC_Is_Aktief" in data:
        tag.NFC_Is_Aktief = bool(nfc_is_aktief)


def gebruiker_to_dict(g: models.Gebruikers) -> dict:
    """Veilige JSON-serialisering vir Gebruikers + rol/subrol data."""
    rol_naam = g.rol.ROL_Naam if getattr(g, "rol", None) else None

    data = {
        "Gebruiker_ID": g.Gebruiker_ID,
        "GEB_Naam": g.GEB_Naam,
        "GEB_Van": g.GEB_Van,
        "GEB_ID_Nommer": g.GEB_ID_Nommer,
        "GEB_Epos": g.GEB_Epos,
        "GEB_Selfoon_Nr": g.GEB_Selfoon_Nr,
        "GEB_Profiel_Foto": g.GEB_Profiel_Foto,
        "Rol_ID": g.Rol_ID,
        "Rol_Naam": rol_naam,
        "Is_Aktief": g.Is_Aktief,
        "Geskep_Op": g.Geskep_Op.isoformat() if g.Geskep_Op else None,
        "Gewysig_Op": g.Gewysig_Op.isoformat() if g.Gewysig_Op else None,
    }

    if getattr(g, "student", None):
        data["STU_Nommer"] = g.student.STU_Nommer
        data["STU_Is_Koshuis"] = g.student.STU_Is_Koshuis
        data["Koshuis_ID"] = g.student.Koshuis_ID

    if getattr(g, "personeel", None):
        data["PER_Nommer"] = g.personeel.PER_Nommer
        data["PER_Departement"] = g.personeel.PER_Departement

    if getattr(g, "kampus_opsigter", None):
        data["KAMO_Nommer"] = g.kampus_opsigter.KAMO_Nommer
        data["Kampus_ID"] = g.kampus_opsigter.Kampus_ID

    if getattr(g, "sekuriteit_wag", None):
        data["SEK_Nommer"] = g.sekuriteit_wag.SEK_Nommer

    aktiewe_nfc = None
    nfc_tags = getattr(g, "nfc_tags", None)
    if nfc_tags:
        aktiewe_nfc = next((tag for tag in nfc_tags if tag.NFC_Is_Aktief), nfc_tags[-1])
    if aktiewe_nfc:
        data["NFC_Tags_ID"] = aktiewe_nfc.NFC_Tags_ID
        data["NFC_UID"] = aktiewe_nfc.NFC_UID
        data["NFC_Tipe"] = aktiewe_nfc.NFC_Tipe
        data["NFC_Is_Aktief"] = aktiewe_nfc.NFC_Is_Aktief

    return data
