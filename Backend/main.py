from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, UploadFile, File
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from datetime import datetime
import uuid
import os


from typing import List, Optional, Any

from models import Gebruikers, Student, Lokasie, ToegangsLogs
from database import engine, get_db
import models, schemas, auth

# Skep alle tabelle outomaties by opstart
models.Base.metadata.create_all(bind=engine)

# Migrasie 006: create_all verander nie bestaande tabelle nie, dus word
# Kampus_ID se NOT NULL-beperking hier verwyder op databasisse wat die
# koshuis-tabel reeds met die ou skema het. Idempotent - veilig om elke keer te loop.
try:
    with engine.connect() as _conn:
        _conn.execute(text('ALTER TABLE koshuis ALTER COLUMN "Kampus_ID" DROP NOT NULL'))
        _conn.execute(text('ALTER TABLE koshuis ALTER COLUMN "KOS_Kapasiteit" DROP DEFAULT'))
        _conn.commit()
except Exception as _migrasie_fout:
    print(f"Waarskuwing: migrasie 006 (koshuis.Kampus_ID nullable) het misluk: {_migrasie_fout}")

# Migrasie 007: koppel 'n student aan 'n spesifieke koshuis. create_all voeg nie
# kolomme by bestaande tabelle nie, dus word dit hier bygevoeg. Idempotent.
try:
    with engine.connect() as _conn:
        _conn.execute(text('ALTER TABLE student ADD COLUMN IF NOT EXISTS "Koshuis_ID" INT'))
        _conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_student_koshuis'
                ) THEN
                    ALTER TABLE student
                    ADD CONSTRAINT fk_student_koshuis
                    FOREIGN KEY ("Koshuis_ID") REFERENCES koshuis("Koshuis_ID");
                END IF;
            END $$;
        """))
        _conn.commit()
except Exception as _migrasie_fout:
    print(f"Waarskuwing: migrasie 007 (student.Koshuis_ID) het misluk: {_migrasie_fout}")

app = FastAPI(
    title="MOON Admin API",
    description="Louis se Admin API vir die MOON projek.",
    version="1.0.0"
)

UPLOAD_DIR = "uploads/profile_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads",
)

# --- STANDAARD RESPONSE MIDDLEWARE & EXCEPTION HANDLERS ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.APIResponse(
            sukses=False,
            data=None,
            fout=exc.detail
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=schemas.APIResponse(
            sukses=False,
            data=None,
            fout=f"Interne bedienerfout: {str(exc)}"
        ).dict()
    )

# Voeg CORS by sodat die frontend die API kan roep
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Voeg die AuthMiddleware by (naby aan die app vir inner-exec)
app.add_middleware(auth.AuthMiddleware)

# Voeg die SessionMiddleware by vir sessie-gebaseerde auth
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.SECRET_KEY,
    session_cookie="moon_session"
)

# --- HULPFUNKSIES (Interne Kontrakte) ---

def _deaktiveer_nfc_tags_logika(db: Session, user_id: int):
    """
    Interne hulpfunksie vir deaktivering van NFC tags.
    Word gedeel tussen Louis en Steven se roetes (F1 & F13).
    """
    return db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == user_id, 
        models.NFC_Tags.NFC_Is_Aktief == True
    ).update({"NFC_Is_Aktief": False})

def _generate_unique_nfc_uid(db: Session, length: int = 8) -> str:
    while True:
        uid = uuid.uuid4().hex[:length].upper()
        exists = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.NFC_UID == uid
        ).first()
        if not exists:
            return uid

def _kry_rol(db: Session, rol_id: int) -> models.Rolle:
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == rol_id).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol bestaan nie")
    return rol

def _kontroleer_unieke_gebruiker_velde(
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

def _kontroleer_unieke_subnommer(
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

def _kontroleer_kampus(db: Session, kampus_id: Optional[int]):
    if kampus_id is None:
        return
    if not db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")

def _generate_next_per_nommer(db: Session) -> str:
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


def _is_personeel_rol(rol_naam: str) -> bool:
    return rol_naam in [
        "Administrateur",
        "Personeel",
        "Sekuriteit_Wag",
        "Kampus_Opsigter",
    ]


def _sync_gebruiker_subrekords(
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
            _kontroleer_unieke_subnommer(
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
    # Personeel, Sekuriteit_Wag, Kampus_Opsigter en Administrateur kry almal PER_Nommer.
    if _is_personeel_rol(rol_naam) or "PER_Nommer" in data or "PER_Departement" in data:
        personeel = db.query(models.Personeel).filter(
            models.Personeel.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()

        per_nommer = data.get("PER_Nommer")

        if not personeel and not per_nommer and (creating or _is_personeel_rol(rol_naam)):
            per_nommer = _generate_next_per_nommer(db)

        if per_nommer:
            _kontroleer_unieke_subnommer(
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
    # Geen KAMO_Nommer word meer vereis nie. PER_Nommer is die werknemer-identifiseerder.
    if rol_naam == "Kampus_Opsigter" or "KAMO_Nommer" in data or "Kampus_ID" in data:
        _kontroleer_kampus(db, data.get("Kampus_ID"))

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
            _kontroleer_unieke_subnommer(
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
    # Geen SEK_Nommer word meer vereis nie. PER_Nommer is die werknemer-identifiseerder.
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
            _kontroleer_unieke_subnommer(
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

def _sync_gebruiker_nfc_tag(db: Session, gebruiker_id: int, data: dict):
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

def _gebruiker_to_dict(g: models.Gebruikers) -> dict:
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

@app.get("/", response_model=schemas.APIResponse[dict])
def read_root():
    return schemas.APIResponse(sukses=True, data={"message": "Backend is working"})

# --- AUTH ROETES ---

@app.post("/token", response_model=schemas.APIResponse[dict])
def login_vir_toegang_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip()

    user = None

    # 1. As dit soos e-pos lyk, probeer eers e-pos login
    if "@" in username:
        user = db.query(models.Gebruikers).filter(
            models.Gebruikers.GEB_Epos == username
        ).first()

    # 2. Anders probeer studentenommer login
    if not user:
        student = db.query(models.Student).filter(
            models.Student.STU_Nommer == username
        ).first()

        if student:
            user = db.query(models.Gebruikers).filter(
                models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
            ).first()

    if not user or not auth.verify_password(form_data.password, user.GEB_Wagwoord):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verkeerde gebruikersnaam of wagwoord"
        )

    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == user.Rol_ID).first()
    rol_naam = rol.ROL_Naam if rol else "Onbekend"

    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.Gebruiker_ID), "rol": user.Rol_ID, "rol_naam": rol_naam}, 
        expires_delta=access_token_expires
    )

    # Sessie-gebaseerde auth: stoor in sessie-koekie
    request.session["user_id"] = user.Gebruiker_ID
    request.session["rol"] = user.Rol_ID
    request.session["rol_naam"] = rol_naam

    # JWT in HTTP-Only koekie vir sessie-ondersteuning in blaaiers
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # Kan in produksie True wees met HTTPS
    )

    return schemas.APIResponse(
        sukses=True, 
        data={"access_token": access_token, "token_type": "bearer"}
    )

@app.post("/logout", response_model=schemas.APIResponse[dict])
def logout(response: Response, request: Request):
    """
    Meld die gebruiker af deur sessie en koekies skoon te maak.
    """
    request.session.clear()
    response.delete_cookie("access_token")
    return schemas.APIResponse(sukses=True, data={"boodskap": "Suksesvol afgemeld"})

# --- GEBRUIKER ROETES ---

@app.post("/gebruikers", response_model=schemas.APIResponse[Any], status_code=status.HTTP_201_CREATED)
def skep_gebruiker(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    _kontroleer_unieke_gebruiker_velde(
        db,
        epos=str(user_in.GEB_Epos),
        id_nommer=user_in.GEB_ID_Nommer,
    )
    rol = _kry_rol(db, user_in.Rol_ID)
    rol_naam = rol.ROL_Naam
    user_data = user_in.dict(exclude_unset=True)

    try:
        db_user = models.Gebruikers(
            GEB_Naam=user_in.GEB_Naam,
            GEB_Van=user_in.GEB_Van,
            GEB_ID_Nommer=user_in.GEB_ID_Nommer,
            GEB_Epos=str(user_in.GEB_Epos),
            GEB_Wagwoord=auth.get_password_hash(user_in.GEB_Wagwoord),
            GEB_Selfoon_Nr=user_in.GEB_Selfoon_Nr,
            GEB_Profiel_Foto=user_in.GEB_Profiel_Foto,
            Rol_ID=user_in.Rol_ID,
            Is_Aktief=user_in.Is_Aktief
        )

        db.add(db_user)
        db.flush()

        _sync_gebruiker_subrekords(db, db_user, rol_naam, user_data, creating=True)
        _sync_gebruiker_nfc_tag(db, db_user.Gebruiker_ID, user_data)

        db.commit()
        db.refresh(db_user)

        return schemas.APIResponse(sukses=True, data=_gebruiker_to_dict(db_user))

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie gebruiker skep nie: {str(e)}")

@app.put("/gebruikers/{user_id}", response_model=schemas.APIResponse[Any])
def opdateer_gebruiker(
    user_id: int, 
    user_in: schemas.UserUpdate, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F2: Dateer 'n gebruiker op. Slegs vir Admin.
    """
    db_user = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    update_data = user_in.dict(exclude_unset=True)

    if "GEB_Epos" in update_data or "GEB_ID_Nommer" in update_data:
        _kontroleer_unieke_gebruiker_velde(
            db,
            epos=str(update_data["GEB_Epos"]) if "GEB_Epos" in update_data else None,
            id_nommer=update_data.get("GEB_ID_Nommer"),
            exclude_user_id=user_id,
        )

    rol = _kry_rol(db, update_data.get("Rol_ID", db_user.Rol_ID))

    gewone_velde = {
        "GEB_Naam",
        "GEB_Van",
        "GEB_ID_Nommer",
        "GEB_Epos",
        "GEB_Selfoon_Nr",
        "GEB_Profiel_Foto",
        "Rol_ID",
        "Is_Aktief",
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

        _sync_gebruiker_subrekords(db, db_user, rol.ROL_Naam, update_data)
        _sync_gebruiker_nfc_tag(db, user_id, update_data)

        db.commit()
        db.refresh(db_user)
        return schemas.APIResponse(sukses=True, data=_gebruiker_to_dict(db_user))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie gebruiker opdateer nie: {str(e)}")

@app.delete("/gebruikers/{user_id}", response_model=schemas.APIResponse[dict])
def verwyder_gebruiker(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F2: Sagte verwydering van 'n gebruiker (deaktiveer).
    """
    # 'n Admin mag nie sy eie rekening skrap nie.
    if user_id == current_user.Gebruiker_ID:
        raise HTTPException(status_code=400, detail="Jy kan nie jou eie rekening skrap nie.")

    return opdateer_gebruiker_status(user_id=user_id, is_aktief=False, db=db, current_user=current_user, is_admin=is_admin)

@app.get("/gebruikers", response_model=schemas.APIResponse[List[Any]])
def lees_gebruikers(
    skip: int = 0, 
    limit: int = 100, 
    kampus_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit) # Wagte mag nou ook lys sien
):
    """
    Stuur 'n lys van gebruikers terug. 
    F20: Kampus Opsigters word beperk tot hul eie kampus.
    F21: Sekuriteitswagte sien beperkte data.
    """
    query = db.query(models.Gebruikers)
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
    
    # F20: Kampus Opsigter Filtering
    if rol.ROL_Naam == "Kampus_Opsigter":
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        if not opsigter_info:
            raise HTTPException(status_code=403, detail="Opsigter is nie aan 'n kampus gekoppel nie.")
        
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == opsigter_info.Kampus_ID)
    elif kampus_id:
        # Admins kan op enige kampus filter
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == kampus_id)

    gebruikers = query.offset(skip).limit(limit).all()

    # F21: Data Filtering vir Sekuriteitswagte
    if rol.ROL_Naam == "Sekuriteit_Wag":
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
        data=[_gebruiker_to_dict(g) for g in gebruikers]
    )

@app.get("/gebruikers/{user_id}", response_model=schemas.APIResponse[Any])
def lees_gebruiker(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    """
    Kry 'n spesifieke gebruiker.
    F20: Check kampus skoop.
    F21: Filter velde vir Sekuriteitswagte.
    """
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if gebruiker is None:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()

    # F20: Kampus Skoop Check
    if rol.ROL_Naam == "Kampus_Opsigter":
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        # Check of die teiken gebruiker in dieselfde kampus is
        teiken_opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == user_id).first()
        
        if teiken_opsigter_info and teiken_opsigter_info.Kampus_ID != opsigter_info.Kampus_ID:
            raise HTTPException(status_code=403, detail="Jy het nie toegang tot hierdie gebruiker nie.")

    # F21: Data Filtering vir Sekuriteitswagte
    if rol.ROL_Naam == "Sekuriteit_Wag":
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

    return schemas.APIResponse(sukses=True, data=_gebruiker_to_dict(gebruiker))

@app.patch("/gebruikers/{user_id}/status", response_model=schemas.APIResponse[dict])
def opdateer_gebruiker_status(
    user_id: int, 
    is_aktief: bool, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F1: Deaktiveer 'n gebruiker en hul NFC-tags in een transaksie. 
    Slegs vir Admin.
    """
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    try:
        # Stap 1: Merk Gebruikers rekord
        gebruiker.Is_Aktief = is_aktief
        
        if not is_aktief:
            # Stap 2 & 3: Deaktiveer NFC tags via gedeelde logika (F1/F13 Integrasie)
            _deaktiveer_nfc_tags_logika(db, user_id)

            # Stap 4: Skep waarskuwing rekord (Louis se verantwoordelikheid)
            nuwe_waarskuwing = models.Waarskuwings(
                Gebruiker_ID=user_id,
                WAA_Beskrywing=f"Gebruiker handmatig deur Admin ({current_user.GEB_Naam}) onaktief gemerk",
                WAA_Status="OOP"
            )
            db.add(nuwe_waarskuwing)

        # Stap 5: Bevestig transaksie
        db.commit()
        db.refresh(gebruiker)
        
        return schemas.APIResponse(
            sukses=True, 
            data={"boodskap": "Status suksesvol opgedateer", "is_aktief": gebruiker.Is_Aktief}
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fout tydens transaksie: {str(e)}")

# --- KAMPUS & ROL ROETES ---

@app.get("/kampusse", response_model=schemas.APIResponse[List[schemas.Kampus]])
def lees_kampusse(db: Session = Depends(get_db)):
    """
    Stuur 'n lys van alle kampusse terug.
    """
    kampusse = db.query(models.Kampus).all()
    return schemas.APIResponse(sukses=True, data=kampusse)


@app.post("/kampusse", response_model=schemas.APIResponse[schemas.Kampus], status_code=status.HTTP_201_CREATED)
def skep_kampus(
    kampus_in: schemas.KampusCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Skep 'n nuwe kampus. Slegs vir Admin.
    """
    naam = kampus_in.KAM_Naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")

    bestaande = db.query(models.Kampus).filter(
        func.lower(models.Kampus.KAM_Naam) == naam.lower()
    ).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")

    kampus = models.Kampus(
        KAM_Naam=naam,
        KAM_Adres=kampus_in.KAM_Adres,
    )

    db.add(kampus)
    db.commit()
    db.refresh(kampus)

    # Skep outomaties die hoofhek vir die kampus
    hek = models.Lokasie(
        LOK_Naam=f"{kampus.KAM_Naam}-Hek",
        LOK_Tipe="Kampus",
        Kampus_ID=kampus.Kampus_ID,
    )

    db.add(hek)
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data=kampus,
    )


@app.put("/kampusse/{kampus_id}", response_model=schemas.APIResponse[schemas.Kampus])
def opdateer_kampus(
    kampus_id: int,
    kampus_in: schemas.KampusUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Dateer 'n kampus op. Slegs vir Admin.
    """
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    update_data = kampus_in.dict(exclude_unset=True)
    if "KAM_Naam" in update_data:
        naam = update_data["KAM_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Kampusnaam is verpligtend")

        bestaande = db.query(models.Kampus).filter(
            func.lower(models.Kampus.KAM_Naam) == naam.lower(),
            models.Kampus.Kampus_ID != kampus_id,
        ).first()
        if bestaande:
            raise HTTPException(status_code=400, detail="Kampusnaam reeds in gebruik")
        kampus.KAM_Naam = naam

    if "KAM_Adres" in update_data:
        kampus.KAM_Adres = update_data["KAM_Adres"]

    db.commit()
    db.refresh(kampus)
    return schemas.APIResponse(sukses=True, data=kampus)


@app.delete("/kampusse/{kampus_id}", response_model=schemas.APIResponse[dict])
def verwyder_kampus(
    kampus_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Verwyder 'n kampus. Slegs vir Admin.
    Word geblokkeer as daar nog data aan die kampus gekoppel is.
    """
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    if db.query(models.Lokasie).filter(models.Lokasie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog lokale aan hierdie kampus gekoppel")
    if db.query(models.Koshuis).filter(models.Koshuis.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog koshuise aan hierdie kampus gekoppel")
    if db.query(models.Funksie).filter(models.Funksie.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog funksies aan hierdie kampus gekoppel")
    if db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Kampus_ID == kampus_id).first():
        raise HTTPException(status_code=400, detail="Kan nie kampus verwyder nie: daar is nog opsigters aan hierdie kampus gekoppel")

    db.delete(kampus)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Kampus suksesvol verwyder"})


# --- KOSHUIS ROETES ---

@app.get("/koshuise", response_model=schemas.APIResponse[List[schemas.Koshuis]])
def lees_koshuise(db: Session = Depends(get_db)):
    """
    Stuur 'n lys van alle koshuise terug.
    """
    koshuise = db.query(models.Koshuis).all()
    return schemas.APIResponse(sukses=True, data=koshuise)


@app.post("/koshuise", response_model=schemas.APIResponse[schemas.Koshuis], status_code=status.HTTP_201_CREATED)
def skep_koshuis(
    koshuis_in: schemas.KoshuisCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Skep 'n nuwe koshuis. Slegs vir Admin.
    """
    naam = koshuis_in.KOS_Naam.strip()
    if not naam:
        raise HTTPException(status_code=400, detail="Koshuisnaam is verpligtend")

    if koshuis_in.KOS_Kapasiteit <= 0:
        raise HTTPException(status_code=400, detail="Kapasiteit moet groter as nul wees")

    if koshuis_in.Kampus_ID is not None:
        kampus_bestaan = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == koshuis_in.Kampus_ID
        ).first()
        if not kampus_bestaan:
            raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")

    bestaande = db.query(models.Koshuis).filter(
        func.lower(models.Koshuis.KOS_Naam) == naam.lower()
    ).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Koshuisnaam reeds in gebruik")

    koshuis = models.Koshuis(
        KOS_Naam=naam,
        KOS_Adres=koshuis_in.KOS_Adres,
        KOS_Kapasiteit=koshuis_in.KOS_Kapasiteit,
        Kampus_ID=koshuis_in.Kampus_ID,
    )
    db.add(koshuis)
    db.commit()
    db.refresh(koshuis)
    return schemas.APIResponse(sukses=True, data=koshuis)


@app.put("/koshuise/{koshuis_id}", response_model=schemas.APIResponse[schemas.Koshuis])
def opdateer_koshuis(
    koshuis_id: int,
    koshuis_in: schemas.KoshuisUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Dateer 'n koshuis op. Slegs vir Admin.
    """
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

    update_data = koshuis_in.dict(exclude_unset=True)

    if "KOS_Naam" in update_data:
        naam = update_data["KOS_Naam"].strip()
        if not naam:
            raise HTTPException(status_code=400, detail="Koshuisnaam is verpligtend")

        bestaande = db.query(models.Koshuis).filter(
            func.lower(models.Koshuis.KOS_Naam) == naam.lower(),
            models.Koshuis.Koshuis_ID != koshuis_id,
        ).first()
        if bestaande:
            raise HTTPException(status_code=400, detail="Koshuisnaam reeds in gebruik")
        koshuis.KOS_Naam = naam

    if "KOS_Adres" in update_data:
        koshuis.KOS_Adres = update_data["KOS_Adres"]

    if "KOS_Kapasiteit" in update_data:
        if update_data["KOS_Kapasiteit"] is None or update_data["KOS_Kapasiteit"] <= 0:
            raise HTTPException(status_code=400, detail="Kapasiteit moet groter as nul wees")
        koshuis.KOS_Kapasiteit = update_data["KOS_Kapasiteit"]

    if "Kampus_ID" in update_data:
        if update_data["Kampus_ID"] is not None:
            kampus_bestaan = db.query(models.Kampus).filter(
                models.Kampus.Kampus_ID == update_data["Kampus_ID"]
            ).first()
            if not kampus_bestaan:
                raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")
        koshuis.Kampus_ID = update_data["Kampus_ID"]

    db.commit()
    db.refresh(koshuis)
    return schemas.APIResponse(sukses=True, data=koshuis)


@app.delete("/koshuise/{koshuis_id}", response_model=schemas.APIResponse[dict])
def verwyder_koshuis(
    koshuis_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Verwyder 'n koshuis. Slegs vir Admin.
    """
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

    if db.query(models.Student).filter(models.Student.Koshuis_ID == koshuis_id).first():
        raise HTTPException(status_code=400, detail="Kan nie koshuis verwyder nie: daar is nog studente aan hierdie koshuis gekoppel")

    db.delete(koshuis)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Koshuis suksesvol verwyder"})


@app.get("/koshuise/{koshuis_id}/status", response_model=schemas.APIResponse[schemas.KoshuisDetailStatus])
def kry_koshuis_status_detail(koshuis_id: int, db: Session = Depends(get_db)):
    """
    Kry gedetailleerde inligting van die geselekteerde koshuis se studente
    wat tans in- of uitgeklok is (nuutste skandering per student).
    """
    koshuis = db.query(models.Koshuis).filter(models.Koshuis.Koshuis_ID == koshuis_id).first()
    if not koshuis:
        raise HTTPException(status_code=404, detail="Koshuis nie gevind nie")

    studente = db.query(models.Student).filter(models.Student.Koshuis_ID == koshuis_id).all()
    student_ids = [s.Gebruiker_ID for s in studente]

    scanned_in = []
    scanned_out = []

    if student_ids:
        # Nuutste log per student (enige lokaal)
        subquery = db.query(
            models.ToegangsLogs.Gebruiker_ID,
            func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
        ).filter(
            models.ToegangsLogs.Gebruiker_ID.in_(student_ids)
        ).group_by(
            models.ToegangsLogs.Gebruiker_ID
        ).subquery()

        latest_logs = db.query(models.ToegangsLogs).join(
            subquery,
            models.ToegangsLogs.Log_ID == subquery.c.max_log_id
        ).all()

        for log in latest_logs:
            gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == log.Gebruiker_ID).first()
            if not gebruiker:
                continue
            rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == gebruiker.Rol_ID).first()
            rol_naam = rol.ROL_Naam if rol else "Onbekend"

            status_obj = schemas.KampusGebruikerStatus(
                Gebruiker_ID=gebruiker.Gebruiker_ID,
                GEB_Naam=gebruiker.GEB_Naam,
                GEB_Van=gebruiker.GEB_Van,
                GEB_Epos=gebruiker.GEB_Epos,
                Rol_Naam=rol_naam,
                Tydstempel=log.TOE_Tydstempel,
                Rigting=log.TOE_Rigting,
                Metode=log.TOE_Metode
            )

            if log.TOE_Rigting == "IN":
                scanned_in.append(status_obj)
            else:
                scanned_out.append(status_obj)

    return schemas.APIResponse(
        sukses=True,
        data=schemas.KoshuisDetailStatus(
            Koshuis_ID=koshuis.Koshuis_ID,
            KOS_Naam=koshuis.KOS_Naam,
            KOS_Kapasiteit=koshuis.KOS_Kapasiteit,
            inwoner_count=len(studente),
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out),
            scanned_in=scanned_in,
            scanned_out=scanned_out
        )
    )


@app.get("/kampusse/status", response_model=schemas.APIResponse[List[schemas.KampusSummaryStatus]])
def kry_kampus_status_opsomming(db: Session = Depends(get_db)):
    """
    Kry die status-opsomming (scanned in en scanned out tellings) vir alle kampusse.
    """
    kampusse = db.query(models.Kampus).all()
    resultate = []
    for k in kampusse:
        # Latest log per gebruiker vir hierdie kampus
        subquery = db.query(
            models.ToegangsLogs.Gebruiker_ID,
            func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
        ).join(models.Lokasie).filter(
            models.Lokasie.Kampus_ID == k.Kampus_ID
        ).group_by(
            models.ToegangsLogs.Gebruiker_ID
        ).subquery()

        latest_logs = db.query(models.ToegangsLogs).join(
            subquery,
            models.ToegangsLogs.Log_ID == subquery.c.max_log_id
        ).all()

        scanned_in_count = sum(1 for log in latest_logs if log.TOE_Rigting == "IN")
        scanned_out_count = sum(1 for log in latest_logs if log.TOE_Rigting == "UIT")

        resultate.append(schemas.KampusSummaryStatus(
            Kampus_ID=k.Kampus_ID,
            KAM_Naam=k.KAM_Naam,
            KAM_Adres=k.KAM_Adres,
            scanned_in_count=scanned_in_count,
            scanned_out_count=scanned_out_count
        ))

    return schemas.APIResponse(sukses=True, data=resultate)


@app.get("/kampusse/{kampus_id}/status", response_model=schemas.APIResponse[schemas.KampusDetailStatus])
def kry_kampus_status_detail(kampus_id: int, db: Session = Depends(get_db)):
    """
    Kry gedetailleerde inligting van gebruikers wat tans in- of uitgeklok is op 'n spesifieke kampus.
    """
    kampus = db.query(models.Kampus).filter(models.Kampus.Kampus_ID == kampus_id).first()
    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    # Latest log per gebruiker vir hierdie kampus
    subquery = db.query(
        models.ToegangsLogs.Gebruiker_ID,
        func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
    ).join(models.Lokasie).filter(
        models.Lokasie.Kampus_ID == kampus_id
    ).group_by(
        models.ToegangsLogs.Gebruiker_ID
    ).subquery()

    latest_logs = db.query(models.ToegangsLogs).join(
        subquery,
        models.ToegangsLogs.Log_ID == subquery.c.max_log_id
    ).all()

    scanned_in = []
    scanned_out = []

    for log in latest_logs:
        gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == log.Gebruiker_ID).first()
        if not gebruiker:
            continue
        rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == gebruiker.Rol_ID).first()
        rol_naam = rol.ROL_Naam if rol else "Onbekend"

        status_obj = schemas.KampusGebruikerStatus(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            GEB_Naam=gebruiker.GEB_Naam,
            GEB_Van=gebruiker.GEB_Van,
            GEB_Epos=gebruiker.GEB_Epos,
            Rol_Naam=rol_naam,
            Tydstempel=log.TOE_Tydstempel,
            Rigting=log.TOE_Rigting,
            Metode=log.TOE_Metode
        )

        if log.TOE_Rigting == "IN":
            scanned_in.append(status_obj)
        else:
            scanned_out.append(status_obj)

    return schemas.APIResponse(
        sukses=True,
        data=schemas.KampusDetailStatus(
            Kampus_ID=kampus.Kampus_ID,
            KAM_Naam=kampus.KAM_Naam,
            scanned_in_count=len(scanned_in),
            scanned_out_count=len(scanned_out),
            scanned_in=scanned_in,
            scanned_out=scanned_out
        )
    )


@app.get("/rolle", response_model=schemas.APIResponse[List[schemas.Rol]])
def lees_rolle(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    Stuur 'n lys van alle rolle terug. Slegs Admin.
    """
    rolle = db.query(models.Rolle).all()
    return schemas.APIResponse(sukses=True, data=rolle)

# --- LOKASIE ROETES (Louis) ---

@app.post("/lokasies", response_model=schemas.APIResponse[schemas.Lokasie], status_code=status.HTTP_201_CREATED)
def skep_lokasie(
    lokasie_in: schemas.LokasieCreate, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    Stap 2: Skep 'n nuwe klaskamer/lokasie.
    """
    db_lokasie = models.Lokasie(**lokasie_in.dict())
    db.add(db_lokasie)
    db.commit()
    db.refresh(db_lokasie)
    return schemas.APIResponse(sukses=True, data=db_lokasie)

@app.get("/lokasies")
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
                NFC_UID=_generate_unique_nfc_uid(db),
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

    return schemas.APIResponse(
        sukses=True,
        data=result
    )
    
@app.put("/lokasies/{lokasie_id}", response_model=schemas.APIResponse[schemas.Lokasie])
def opdateer_lokasie(
    lokasie_id: int,
    lokasie_in: schemas.LokasieUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Dateer 'n lokasie op. Slegs vir Admin.
    """
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
            kampus_bestaan = db.query(models.Kampus).filter(
                models.Kampus.Kampus_ID == update_data["Kampus_ID"]
            ).first()
            if not kampus_bestaan:
                raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")
        lokasie.Kampus_ID = update_data["Kampus_ID"]

    db.commit()
    db.refresh(lokasie)
    return schemas.APIResponse(sukses=True, data=lokasie)


@app.delete("/lokasies/{lokasie_id}", response_model=schemas.APIResponse[dict])
def verwyder_lokasie(
    lokasie_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Verwyder 'n lokasie en sy NFC-tags. Slegs vir Admin.
    Word geblokkeer as daar toegangslogs vir die lokaal bestaan (oudit-geskiedenis).
    """
    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

    if db.query(models.ToegangsLogs).filter(models.ToegangsLogs.Lokasie_ID == lokasie_id).first():
        raise HTTPException(status_code=400, detail="Kan nie lokaal verwyder nie: daar is toegangslogs vir hierdie lokaal")

    # Elke lokaal kry outomaties 'n NFC-tag; verwyder dit saam met die lokaal.
    db.query(models.NFC_Tags).filter(models.NFC_Tags.Lokasie_ID == lokasie_id).delete()
    db.delete(lokasie)
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "Lokaal suksesvol verwyder"})


@app.post("/klasse", response_model=schemas.APIResponse[schemas.KlasSkepResult], status_code=status.HTTP_201_CREATED)
def skep_klas_met_nfc(
    klas_in: schemas.KlasSkep,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """
    Skep 'n nuwe klas (lokasie/saal) en koppel die NFC-tag daaraan in een databasis-transaksie.
    """

    if klas_in.Kampus_ID is not None:
        kampus_bestaan = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == klas_in.Kampus_ID
        ).first()
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
        
        generated_uid = _generate_unique_nfc_uid(db)
        
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


@app.post("/nfc-tags", response_model=schemas.APIResponse[schemas.NFCTag])
def koppel_nfc_tag_aan_lokasie(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    Stap 2: Koppel 'n NFC-tag aan 'n klaskamer.
    """
    # Check of NFC_UID reeds bestaan
    db_tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == tag_in.NFC_UID).first()
    
    if db_tag:
        # Update bestaande tag
        for key, value in tag_in.dict(exclude_unset=True).items():
            setattr(db_tag, key, value)
    else:
        # Skep nuwe tag
        db_tag = models.NFC_Tags(**tag_in.dict())
        db.add(db_tag)
    
    db.commit()
    db.refresh(db_tag)
    return schemas.APIResponse(sukses=True, data=db_tag)

# --- NFC ROETES (F13 & F1 Integrasie) ---

@app.post("/nfc-tags/registreer", response_model=schemas.APIResponse[schemas.NFCTag])
def registreer_nfc_tag(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F13: Registreer 'n nuwe NFC tag vir 'n gebruiker.
    Deaktiveer outomaties enige bestaande aktiewe tags vir daardie gebruiker.
    """
    # 1. Check of NFC_UID reeds bestaan
    bestaande_tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == tag_in.NFC_UID).first()
    if bestaande_tag:
        raise HTTPException(status_code=400, detail="NFC tag reeds geregistreer")

    # 2. Check of gebruiker bestaan
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == tag_in.Gebruiker_ID).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    # 3. Maak ou aktiewe tag onaktief (Besigheidsreël: slegs een aktiewe tag per gebruiker)
    _deaktiveer_nfc_tags_logika(db, tag_in.Gebruiker_ID)

    # 4. Skep nuwe aktiewe tag
    nuwe_tag = models.NFC_Tags(**tag_in.dict())
    db.add(nuwe_tag)
    db.commit()
    db.refresh(nuwe_tag)

    return schemas.APIResponse(sukses=True, data=nuwe_tag)

@app.patch("/nfc-tags/{user_id}/deaktiveer", response_model=schemas.APIResponse[dict])
def deaktiveer_gebruiker_nfc_tags(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F13: Deaktiveer alle aktiewe NFC tags vir 'n spesifieke gebruiker.
    """
    updated_count = _deaktiveer_nfc_tags_logika(db, user_id)
    
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Geen aktiewe NFC tags vir hierdie gebruiker gevind nie")

    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "NFC tags suksesvol gedeaktiveer"})

@app.get("/sekuriteit/toegang")
def sekuriteit_toegang_toets(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    """
    Eenvoudige toets-eindpunt vir Sekuriteitswag toegang.
    """
    return schemas.APIResponse(sukses=True, data={"boodskap": "Toegang bevestig vir Sekuriteit"})



@app.get("/nfc-tags/{uid}", response_model=schemas.APIResponse[dict])
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
        raise HTTPException(status_code=404, detail="NFC tag nie gevind of nie aktief nie")

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


# --- WAGTE ROETES (F20) ---
@app.get("/wagte/kampusse", response_model=schemas.APIResponse[List[dict]])
def wagte_kampusse(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()

    return schemas.APIResponse(
        sukses=True,
        data=[
            {
                "kampus_id": k.Kampus_ID,
                "naam": k.KAM_Naam,
                "adres": k.KAM_Adres,
            }
            for k in kampusse
        ],
    )


class StudentKlasScanRequest(BaseModel):
    nfc_uid: str
    rigting: str = "IN"


@app.post("/student/scan-klas")
def student_scan_klas(
    data: StudentKlasScanRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    if data.rigting not in ["IN", "UIT"]:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")

    student = db.query(models.Student).filter(
        models.Student.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    if not student:
        raise HTTPException(status_code=403, detail="Net studente kan klas scan")

    tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == data.nfc_uid.strip(),
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if not tag or not tag.Lokasie_ID:
        raise HTTPException(status_code=404, detail="Geen lokaal vir hierdie NFC tag gevind nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Lokasie_ID == tag.Lokasie_ID
    ).first()

    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

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


@app.get("/toegangslogs")
def lys_toegangslogs(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    logs = db.query(models.ToegangsLogs)\
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())\
        .limit(50)\
        .all()

    return schemas.APIResponse(
        sukses=True,
        data=[
            {
                "Log_ID": l.Log_ID,
                "Gebruiker_ID": l.Gebruiker_ID,
                "Lokasie_ID": l.Lokasie_ID,
                "Rigting": l.TOE_Rigting,
                "Metode": l.TOE_Metode,
                "Tyd": l.TOE_Tydstempel.isoformat(),
            }
            for l in logs
        ]
    )



# --- WAGTE STUDENT SCAN ROETE (F20) ---
class WagteStudentScanRequest(BaseModel):
    student_nom_or_id: str
    lokasie_id: int
    rigting: str   # IN / UIT
    metode: str    # NFC / QR


@app.post("/admin/lokasies/genereer-missing-uids")
def genereer_missing_lokasie_uids(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    lokasies = db.query(models.Lokasie).all()
    geskep = []

    for l in lokasies:
        bestaande_tag = db.query(models.NFC_Tags).filter(
            models.NFC_Tags.Lokasie_ID == l.Lokasie_ID,
            models.NFC_Tags.NFC_Is_Aktief == True
        ).first()

        if bestaande_tag:
            continue

        uid = _generate_unique_nfc_uid(db)

        nuwe_tag = models.NFC_Tags(
            NFC_UID=uid,
            Lokasie_ID=l.Lokasie_ID,
            Gebruiker_ID=None,
            NFC_Tipe="Lokasie",
            NFC_Is_Aktief=True
        )

        db.add(nuwe_tag)

        geskep.append({
            "Lokasie_ID": l.Lokasie_ID,
            "LOK_Naam": l.LOK_Naam,
            "NFC_UID": uid
        })

    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={
            "geskep_count": len(geskep),
            "geskep": geskep
        }
    )


class WagteProfileScanRequest(BaseModel):
    scan_kode: str


@app.post("/wagte/profile/scan")
def wagte_profile_scan(
    data: WagteProfileScanRequest,
    db: Session = Depends(get_db),
):
    scan = data.scan_kode.strip()

    gebruiker = None

    student = db.query(models.Student).filter(
        models.Student.STU_Nommer == scan
    ).first()

    if student:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
        ).first()

    if not gebruiker:
        personeel = db.query(models.Personeel).filter(
            models.Personeel.PER_Nommer == scan
        ).first()

        if personeel:
            gebruiker = db.query(models.Gebruikers).filter(
                models.Gebruikers.Gebruiker_ID == personeel.Gebruiker_ID
            ).first()

    if not gebruiker:
        gebruiker = db.query(models.Gebruikers).filter(
            models.Gebruikers.GEB_ID_Nommer == scan
        ).first()

    if not gebruiker:
        raise HTTPException(
            status_code=404,
            detail="Gebruiker nie gevind nie",
        )
        
    if not gebruiker.Is_Aktief:
        raise HTTPException(
        status_code=403,
        detail="Gebruiker is gedeaktiveer en mag nie scan nie",
    )
        
    laaste_log = (
    db.query(models.ToegangsLogs)
    .filter(
        models.ToegangsLogs.Gebruiker_ID == gebruiker.Gebruiker_ID
    )
    .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())
    .first()
    )

    if laaste_log is None:
        voorgestelde_rigting = "IN"
    elif laaste_log.TOE_Rigting == "IN":
        voorgestelde_rigting = "UIT"
    else:
        voorgestelde_rigting = "IN"
        
    return schemas.APIResponse(
    sukses=True,
    data={
        "gebruiker_id": gebruiker.Gebruiker_ID,
        "naam": gebruiker.GEB_Naam,
        "van": gebruiker.GEB_Van,
        "id_nommer": gebruiker.GEB_ID_Nommer,
        "foto_url": gebruiker.GEB_Profiel_Foto,
        "voorgestelde_rigting": voorgestelde_rigting,
    },
)


class WagteProfileVerifyRequest(BaseModel):
    gebruiker_id: int
    kampus_id: int
    rigting: str
    metode: str
    
@app.post("/wagte/profile/verify")
def wagte_profile_verify(
    data: WagteProfileVerifyRequest,
    db: Session = Depends(get_db),
):
    if data.rigting not in ["IN", "UIT"]:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")

    if data.metode not in ["NFC", "QR", "HANDMATIG"]:
        raise HTTPException(status_code=400, detail="Metode moet NFC, QR of HANDMATIG wees")

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == data.gebruiker_id,
        models.Gebruikers.Is_Aktief == True,
    ).first()

    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind of nie aktief nie")

    kampus = db.query(models.Kampus).filter(
        models.Kampus.Kampus_ID == data.kampus_id
    ).first()

    if not kampus:
        raise HTTPException(status_code=404, detail="Kampus nie gevind nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Kampus_ID == data.kampus_id,
        models.Lokasie.LOK_Tipe == "Kampus",
    ).first()

    if not lokasie:
        raise HTTPException(
            status_code=404,
            detail="Geen kampus-lokasie vir hierdie kampus gevind nie",
        )

    log = models.ToegangsLogs(
        Gebruiker_ID=data.gebruiker_id,
        Lokasie_ID=lokasie.Lokasie_ID,
        NFC_Tags_ID=None,
        TOE_Rigting=data.rigting,
        TOE_Metode=data.metode,
        TOE_Auto_Uitgecheck=False,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.APIResponse(
        sukses=True,
        data={
            "log_id": log.Log_ID,
            "gebruiker_id": gebruiker.Gebruiker_ID,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "kampus_id": kampus.Kampus_ID,
            "kampus": kampus.KAM_Naam,
            "lokasie_id": lokasie.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam,
            "tyd": log.TOE_Tydstempel.isoformat(),
        },
    )
    
@app.post("/wagte/profile/decline")
def decline_profile_access(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    gebruiker_id = data.get("gebruiker_id")
    kampus_id = data.get("kampus_id")
    metode = data.get("metode", "QR")

    if not gebruiker_id or not kampus_id:
        raise HTTPException(status_code=400, detail="Gebruiker en kampus is verpligtend")

    main_gate = (
        db.query(Lokasie)
        .filter(
            Lokasie.Kampus_ID == kampus_id,
            Lokasie.LOK_Tipe == "Kampus",
        )
        .first()
    )

    if not main_gate:
        raise HTTPException(status_code=404, detail="Geen kampus hek gevind nie")

    log = ToegangLog(
        Gebruiker_ID=gebruiker_id,
        Lokasie_ID=main_gate.Lokasie_ID,
        Rigting="GEWEIER",
        Metode=metode,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "sukses": True,
        "data": {
            "message": "Toegang geweier",
            "log_id": log.Log_ID,
            "rigting": "GEWEIER",
        },
        "fout": None,
    }
    

@app.get("/me")
def kry_my_profiel(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    rol = db.query(models.Rolle).filter(
        models.Rolle.Rol_ID == current_user.Rol_ID
    ).first()

    student = db.query(models.Student).filter(
        models.Student.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    personeel = db.query(models.Personeel).filter(
        models.Personeel.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    opsigter = db.query(models.Kampus_Opsigter).filter(
        models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    wag = db.query(models.Sekuriteit_Wag).filter(
        models.Sekuriteit_Wag.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    return {
        "sukses": True,
        "data": {
            "gebruiker_id": current_user.Gebruiker_ID,
            "naam": current_user.GEB_Naam,
            "van": current_user.GEB_Van,
            "rol_id": current_user.Rol_ID,
            "rol": rol.ROL_Naam if rol else "Onbekend",
            "epos": current_user.GEB_Epos,
            "selfoon": current_user.GEB_Selfoon_Nr,
            "foto_url": current_user.GEB_Profiel_Foto,
            "status": "Aktief" if current_user.Is_Aktief else "Onaktief",

            "student_nommer": student.STU_Nommer if student else None,
            "student_is_koshuis": student.STU_Is_Koshuis if student else False,
            "personeel_nommer": personeel.PER_Nommer if personeel else None,
            "departement": personeel.PER_Departement if personeel else None,
            "opsigter_nommer": opsigter.KAMO_Nommer if opsigter else None,
            "wag_nommer": wag.SEK_Nommer if wag else None,

            "kampus": None,
        },
    }
    
@app.post("/me/foto")
async def upload_my_profile_photo(
    file: UploadFile = File(...),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Slegs foto lêers word toegelaat")

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Gebruik JPG, PNG of WEBP")

    filename = f"user_{current_user.Gebruiker_ID}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    foto_url = f"/uploads/profile_photos/{filename}"

    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == current_user.Gebruiker_ID
    ).first()

    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    gebruiker.GEB_Profiel_Foto = foto_url
    db.commit()
    db.refresh(gebruiker)

    return {
        "sukses": True,
        "data": {
            "foto_url": foto_url,
        },
    }
    
@app.get("/dashboard")
def kry_my_dashboard(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    rol = db.query(models.Rolle).filter(
        models.Rolle.Rol_ID == current_user.Rol_ID
    ).first()

    laaste_kampus_log = db.query(models.ToegangsLogs).filter(
        models.ToegangsLogs.Gebruiker_ID == current_user.Gebruiker_ID,
        models.ToegangsLogs.TOE_Metode == "QR",
    ).order_by(
        models.ToegangsLogs.TOE_Tydstempel.desc()
    ).first()

    laaste_klas_log = db.query(models.ToegangsLogs).filter(
        models.ToegangsLogs.Gebruiker_ID == current_user.Gebruiker_ID,
        models.ToegangsLogs.TOE_Metode == "NFC",
    ).order_by(
        models.ToegangsLogs.TOE_Tydstempel.desc()
    ).first()

    def log_to_dict(log):
        if not log:
            return None

        lokasie = db.query(models.Lokasie).filter(
            models.Lokasie.Lokasie_ID == log.Lokasie_ID
        ).first()

        return {
            "log_id": log.Log_ID,
            "lokasie_id": log.Lokasie_ID,
            "lokasie": lokasie.LOK_Naam if lokasie else "Onbekend",
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "tyd": log.TOE_Tydstempel.isoformat() if log.TOE_Tydstempel else None,
        }

    kampus_status = "ONBEKEND"

    if laaste_kampus_log:
        if laaste_kampus_log.TOE_Rigting == "IN":
            kampus_status = "OP_KAMPUS"
        elif laaste_kampus_log.TOE_Rigting == "UIT":
            kampus_status = "NIE_OP_KAMPUS"

    return {
        "sukses": True,
        "data": {
            "gebruiker_id": current_user.Gebruiker_ID,
            "naam": current_user.GEB_Naam,
            "van": current_user.GEB_Van,
            "rol": rol.ROL_Naam if rol else "Onbekend",
            "kampus_status": kampus_status,
            "laaste_kampus": log_to_dict(laaste_kampus_log),
            "laaste_klas": log_to_dict(laaste_klas_log),
        },
    }
    
@app.get("/dashboard/live")
def dashboard_live(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    vandag = datetime.utcnow().date()

    # Kry laaste log per gebruiker
    laaste_logs_subq = (
        db.query(
            models.ToegangsLogs.Gebruiker_ID,
            func.max(models.ToegangsLogs.Log_ID).label("max_log_id")
        )
        .group_by(models.ToegangsLogs.Gebruiker_ID)
        .subquery()
    )

    laaste_logs = (
        db.query(models.ToegangsLogs)
        .join(
            laaste_logs_subq,
            models.ToegangsLogs.Log_ID == laaste_logs_subq.c.max_log_id
        )
        .all()
    )

    op_kampus_ids = [
        log.Gebruiker_ID
        for log in laaste_logs
        if log.TOE_Rigting == "IN"
    ]

    studente_op_kampus = (
        db.query(models.Student)
        .filter(models.Student.Gebruiker_ID.in_(op_kampus_ids))
        .count()
        if op_kampus_ids else 0
    )

    personeel_op_kampus = (
        db.query(models.Personeel)
        .filter(models.Personeel.Gebruiker_ID.in_(op_kampus_ids))
        .count()
        if op_kampus_ids else 0
    )

    toegange_vandag = (
        db.query(models.ToegangsLogs)
        .filter(func.date(models.ToegangsLogs.TOE_Tydstempel) == vandag)
        .count()
    )

    # Vir nou 0, want besoeker backend is nog nie volledig gekoppel nie
    besoekers_vandag = 0

    return schemas.APIResponse(
        sukses=True,
        data={
            "studente_op_kampus": studente_op_kampus,
            "personeel_op_kampus": personeel_op_kampus,
            "besoekers_vandag": besoekers_vandag,
            "toegange_vandag": toegange_vandag,
        }
    )
    
@app.get("/studente/search")
def soek_studente(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    search = q.strip()

    if len(search) < 2:
        return {
            "sukses": True,
            "data": [],
        }

    resultate = (
        db.query(models.Student, models.Gebruikers)
        .join(
            models.Gebruikers,
            models.Gebruikers.Gebruiker_ID == models.Student.Gebruiker_ID,
        )
        .filter(
            models.Gebruikers.Is_Aktief == True,
            or_(
                models.Gebruikers.GEB_Naam.ilike(f"%{search}%"),
                models.Gebruikers.GEB_Van.ilike(f"%{search}%"),
                models.Student.STU_Nommer.ilike(f"%{search}%"),
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
    
    
@app.get("/lokasies/uid/{uid}")
def kry_lokasie_deur_uid(
    uid: str,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
    ):
    tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == uid.strip(),
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Geen lokaal vir hierdie NFC tag gevind nie")

    lokasie = db.query(models.Lokasie).filter(
        models.Lokasie.Lokasie_ID == tag.Lokasie_ID
    ).first()

    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokaal nie gevind nie")

    return schemas.APIResponse(
        sukses=True,
        data={
            "Lokasie_ID": lokasie.Lokasie_ID,
            "LOK_Naam": lokasie.LOK_Naam,
            "Kampus_ID": lokasie.Kampus_ID,
            "NFC_UID": tag.NFC_UID
        }
    )
