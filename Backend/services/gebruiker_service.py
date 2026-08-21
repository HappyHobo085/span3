"""Gebruiker (User) business logic — extracted from main.py helpers."""

import uuid
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models

# Kanonieke prioriteitsvolgorde wanneer 'n enkele primêre rol gekies word.
ROL_PRIORITEIT = ["Administrateur", "Kampus_Opsigter", "Sekuriteit_Wag", "Personeel", "Student"]


def kies_primere_rol(rol_namen):
    """Kies 'n deterministiese primêre rol volgens prioriteit."""
    for rol in ROL_PRIORITEIT:
        if rol in rol_namen:
            return rol
    return rol_namen[0] if rol_namen else "Onbekend"


def kry_rol(db: Session, rol_id: int) -> models.Rolle:
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == rol_id).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol bestaan nie")
    return rol


def get_user_role_ids(db: Session, gebruiker: models.Gebruikers) -> List[int]:
    role_assignments = (
        db.query(models.GebruikersRolle)
        .filter(models.GebruikersRolle.Gebruiker_ID == gebruiker.Gebruiker_ID)
        .all()
    )
    role_ids = [assignment.Rol_ID for assignment in role_assignments]
    if not role_ids and getattr(gebruiker, "Rol_ID", None) is not None:
        role_ids = [gebruiker.Rol_ID]
    return role_ids


def get_user_role_names(db: Session, gebruiker: models.Gebruikers) -> List[str]:
    role_ids = get_user_role_ids(db, gebruiker)
    if not role_ids:
        return []

    roles = (
        db.query(models.Rolle)
        .filter(models.Rolle.Rol_ID.in_(role_ids))
        .all()
    )
    role_map = {role.Rol_ID: role.ROL_Naam for role in roles}
    return [role_map[role_id] for role_id in role_ids if role_id in role_map]


def sync_gebruiker_roles(
    db: Session,
    gebruiker: models.Gebruikers,
    role_ids: List[int],
    *,
    primary_role_id: Optional[int] = None,
):
    role_ids = [role_id for role_id in role_ids if role_id is not None]
    if not role_ids:
        raise HTTPException(status_code=400, detail="Ten minste een rol moet verskaf word")

    roles = db.query(models.Rolle).filter(models.Rolle.Rol_ID.in_(role_ids)).all()
    available_role_ids = {role.Rol_ID for role in roles}
    if len(available_role_ids) != len(set(role_ids)):
        raise HTTPException(status_code=400, detail="Een of meer rolle bestaan nie")

    db.query(models.GebruikersRolle).filter(
        models.GebruikersRolle.Gebruiker_ID == gebruiker.Gebruiker_ID
    ).delete(synchronize_session=False)

    for role_id in role_ids:
        db.add(models.GebruikersRolle(Gebruiker_ID=gebruiker.Gebruiker_ID, Rol_ID=role_id))

    primary_role = primary_role_id or role_ids[0]
    if primary_role not in role_ids:
        primary_role = role_ids[0]
    gebruiker.Rol_ID = primary_role


def is_personeel_rol(role_names) -> bool:
    if isinstance(role_names, str):
        role_names = [role_names]
    return any(rol in [
        "Administrateur",
        "Personeel",
        "Sekuriteit_Wag",
        "Kampus_Opsigter",
    ] for rol in role_names)


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


def generate_next_subnommer(db: Session, model, field_name: str, prefix: str) -> str:
    field = getattr(model, field_name)
    last = (
        db.query(model)
        .filter(field.like(f"{prefix}%"))
        .order_by(field.desc())
        .first()
    )

    last_value = getattr(last, field_name, None) if last else None
    if not last_value:
        return f"{prefix}0001"

    try:
        next_num = int(last_value.replace(prefix, "")) + 1
    except ValueError:
        next_num = 1

    return f"{prefix}{next_num:04d}"


def generate_next_per_nommer(db: Session) -> str:
    return generate_next_subnommer(db, models.Personeel, "PER_Nommer", "PER")


def generate_next_kamo_nommer(db: Session) -> str:
    return generate_next_subnommer(db, models.Kampus_Opsigter, "KAMO_Nommer", "KAMO")


def generate_next_sek_nommer(db: Session) -> str:
    return generate_next_subnommer(db, models.Sekuriteit_Wag, "SEK_Nommer", "SEK")


def sync_gebruiker_subrekords(
    db: Session,
    gebruiker: models.Gebruikers,
    role_names: List[str],
    data: dict,
    *,
    creating: bool = False,
):
    role_name_set = set(role_names or [])
    is_student = "Student" in role_name_set
    is_personeel = is_personeel_rol(role_name_set)
    is_opsigter = "Kampus_Opsigter" in role_name_set
    is_sekuriteit = "Sekuriteit_Wag" in role_name_set

    # --- Student ---
    if is_student or "STU_Nommer" in data or "STU_Is_Koshuis" in data or "Koshuis_ID" in data:
        student = db.query(models.Student).filter(
            models.Student.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        stu_nommer = data.get("STU_Nommer")

        if not student and not stu_nommer:
            if creating or is_student:
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
    if is_personeel or "PER_Nommer" in data or "PER_Departement" in data:
        personeel = db.query(models.Personeel).filter(
            models.Personeel.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        per_nommer = data.get("PER_Nommer")

        if not personeel and not per_nommer and (creating or is_personeel):
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
    if is_opsigter or "KAMO_Nommer" in data or "Kampus_ID" in data:
        kontroleer_kampus(db, data.get("Kampus_ID"))

        opsigter = db.query(models.Kampus_Opsigter).filter(
            models.Kampus_Opsigter.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        kamo_nommer = data.get("KAMO_Nommer")

        if not opsigter and not kamo_nommer and (creating or is_opsigter):
            kamo_nommer = generate_next_kamo_nommer(db)

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
    if is_sekuriteit or "SEK_Nommer" in data:
        wag = db.query(models.Sekuriteit_Wag).filter(
            models.Sekuriteit_Wag.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        sek_nommer = data.get("SEK_Nommer")

        if not wag and not sek_nommer and (creating or is_sekuriteit):
            sek_nommer = generate_next_sek_nommer(db)

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
    role_assignments = getattr(g, "gebruikers_rolle", None) or []
    role_names = [
        assignment.rol.ROL_Naam
        for assignment in role_assignments
        if getattr(assignment, "rol", None) is not None
    ]
    role_ids = [assignment.Rol_ID for assignment in role_assignments]

    if not role_names and getattr(g, "rol", None) is not None:
        role_names = [g.rol.ROL_Naam]
    if not role_ids and getattr(g, "Rol_ID", None) is not None:
        role_ids = [g.Rol_ID]

    data = {
        "Gebruiker_ID": g.Gebruiker_ID,
        "GEB_Naam": g.GEB_Naam,
        "GEB_Van": g.GEB_Van,
        "GEB_ID_Nommer": g.GEB_ID_Nommer,
        "GEB_Epos": g.GEB_Epos,
        "GEB_Selfoon_Nr": g.GEB_Selfoon_Nr,
        "GEB_Profiel_Foto": g.GEB_Profiel_Foto,
        "Rol_ID": g.Rol_ID,
        "Rol_IDs": role_ids,
        "Rol_Naam": kies_primere_rol(role_names) if role_names else None,
        "Rol_Namen": role_names,
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
