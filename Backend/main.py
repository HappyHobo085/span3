from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, UploadFile, File
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import uuid
import os

from typing import List, Optional, Any

from models import Gebruikers, Student, Lokasie, ToegangsLogs
from database import engine, get_db
import models, schemas, auth

# Skep alle tabelle outomaties by opstart
models.Base.metadata.create_all(bind=engine)

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

    if getattr(g, "personeel", None):
        data["PER_Nommer"] = g.personeel.PER_Nommer
        data["PER_Departement"] = g.personeel.PER_Departement

    if getattr(g, "kampus_opsigter", None):
        data["KAMO_Nommer"] = g.kampus_opsigter.KAMO_Nommer

    if getattr(g, "sekuriteit_wag", None):
        data["SEK_Nommer"] = g.sekuriteit_wag.SEK_Nommer

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
    if db.query(models.Gebruikers).filter(models.Gebruikers.GEB_Epos == user_in.GEB_Epos).first():
        raise HTTPException(status_code=400, detail="E-pos reeds geregistreer")

    if db.query(models.Gebruikers).filter(models.Gebruikers.GEB_ID_Nommer == user_in.GEB_ID_Nommer).first():
        raise HTTPException(status_code=400, detail="ID Nommer reeds in gebruik")

    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == user_in.Rol_ID).first()
    if not rol:
        raise HTTPException(status_code=400, detail="Rol bestaan nie")

    rol_naam = rol.ROL_Naam

    if rol_naam == "Student" and not user_in.STU_Nommer:
        raise HTTPException(status_code=400, detail="Studentenommer is verpligtend")

    if rol_naam == "Personeel" and not user_in.PER_Nommer:
        raise HTTPException(status_code=400, detail="Personeelnommer is verpligtend")

    if rol_naam == "Kampus_Opsigter" and not user_in.KAMO_Nommer:
        raise HTTPException(status_code=400, detail="Opsigternommer is verpligtend")

    if rol_naam == "Sekuriteit_Wag" and not user_in.SEK_Nommer:
        raise HTTPException(status_code=400, detail="Wagnommer is verpligtend")

    try:
        db_user = models.Gebruikers(
            GEB_Naam=user_in.GEB_Naam,
            GEB_Van=user_in.GEB_Van,
            GEB_ID_Nommer=user_in.GEB_ID_Nommer,
            GEB_Epos=user_in.GEB_Epos,
            GEB_Wagwoord=auth.get_password_hash(user_in.GEB_Wagwoord),
            GEB_Selfoon_Nr=user_in.GEB_Selfoon_Nr,
            GEB_Profiel_Foto=user_in.GEB_Profiel_Foto,
            Rol_ID=user_in.Rol_ID,
            Is_Aktief=user_in.Is_Aktief
        )

        db.add(db_user)
        db.flush()

        if rol_naam == "Student":
            if db.query(models.Student).filter(models.Student.STU_Nommer == user_in.STU_Nommer).first():
                raise HTTPException(status_code=400, detail="Studentenommer reeds in gebruik")
            db.add(models.Student(
                Gebruiker_ID=db_user.Gebruiker_ID,
                STU_Nommer=user_in.STU_Nommer
            ))

        elif rol_naam == "Personeel":
            if db.query(models.Personeel).filter(models.Personeel.PER_Nommer == user_in.PER_Nommer).first():
                raise HTTPException(status_code=400, detail="Personeelnommer reeds in gebruik")
            db.add(models.Personeel(
                Gebruiker_ID=db_user.Gebruiker_ID,
                PER_Nommer=user_in.PER_Nommer,
                PER_Departement=None
            ))

        elif rol_naam == "Kampus_Opsigter":
            if db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.KAMO_Nommer == user_in.KAMO_Nommer).first():
                raise HTTPException(status_code=400, detail="Opsigternommer reeds in gebruik")
            db.add(models.Kampus_Opsigter(
                Gebruiker_ID=db_user.Gebruiker_ID,
                KAMO_Nommer=user_in.KAMO_Nommer
            ))

        elif rol_naam == "Sekuriteit_Wag":
            if db.query(models.Sekuriteit_Wag).filter(models.Sekuriteit_Wag.SEK_Nommer == user_in.SEK_Nommer).first():
                raise HTTPException(status_code=400, detail="Wagnommer reeds in gebruik")
            db.add(models.Sekuriteit_Wag(
                Gebruiker_ID=db_user.Gebruiker_ID,
                SEK_Nommer=user_in.SEK_Nommer
            ))

        db.commit()
        db.refresh(db_user)

        return schemas.APIResponse(sukses=True, data=_gebruiker_to_dict(db_user))

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kon nie gebruiker skep nie: {str(e)}")

@app.put("/gebruikers/{user_id}", response_model=schemas.APIResponse[schemas.User])
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
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return schemas.APIResponse(sukses=True, data=_gebruiker_to_dict(db_user))

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


@app.post("/toegang/handmatig", response_model=schemas.APIResponse[List[schemas.ToegangHandmatigResult]])
def handmatige_toegangsvalidering(
    req: schemas.ToegangHandmatigRequest,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_sekuriteit)
):
    """
    POST /toegang/handmatig
    Naam/ID soek vir wagte. Stuur profielfoto, naam, rol en toegangstatus terug.
    """
    soek_term = req.soek_term.strip()
    if not soek_term:
        raise HTTPException(status_code=400, detail="Soekterm mag nie leeg wees nie")

    filters = [
        models.Gebruikers.GEB_Naam.ilike(f"%{soek_term}%"),
        models.Gebruikers.GEB_Van.ilike(f"%{soek_term}%"),
        models.Gebruikers.GEB_ID_Nommer.ilike(f"%{soek_term}%")
    ]

    # As die soekterm 'n getal is, soek ook op Gebruiker_ID
    if soek_term.isdigit():
        filters.append(models.Gebruikers.Gebruiker_ID == int(soek_term))

    gebruikers = db.query(models.Gebruikers).filter(or_(*filters)).limit(50).all()

    resultate = []
    for g in gebruikers:
        rol_naam = g.rol.ROL_Naam if g.rol else "Onbekend"
        toegang_verleen = g.Is_Aktief
        boodskap = "Toegang Verleen" if toegang_verleen else "Toegang Geweier: Gebruiker is deaktiveer"
        
        resultate.append(
            schemas.ToegangHandmatigResult(
                Gebruiker_ID=g.Gebruiker_ID,
                GEB_Naam=g.GEB_Naam,
                GEB_Van=g.GEB_Van,
                GEB_ID_Nommer=g.GEB_ID_Nommer,
                GEB_Profiel_Foto=g.GEB_Profiel_Foto,
                Rol_Naam=rol_naam,
                Is_Aktief=g.Is_Aktief,
                Toegang_Verleen=toegang_verleen,
                Boodskap=boodskap
            )
        )

    return schemas.APIResponse(sukses=True, data=resultate)


# --- WAGTE ROETES (F20) ---
@app.get("/wagte/kampusse")
def wagte_kampusse(db: Session = Depends(get_db)):
    kampusse = db.query(models.Kampus).all()

    return {
        "sukses": True,
        "data": [
            {
                "kampus_id": k.Kampus_ID,
                "naam": k.KAM_Naam,
                "adres": k.KAM_Adres,
            }
            for k in kampusse
        ],
    }


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

@app.post("/wagte/student/scan")
def wagte_student_scan(data: WagteStudentScanRequest, db: Session = Depends(get_db)):
    if data.rigting not in ["IN", "UIT"]:
        raise HTTPException(status_code=400, detail="Rigting moet IN of UIT wees")

    if data.metode not in ["NFC", "QR", "HANDMATIG"]:
        raise HTTPException(status_code=400, detail="Metode moet NFC, QR of HANDMATIG wees")

    lokasie = db.query(Lokasie).filter(
        Lokasie.Lokasie_ID == data.lokasie_id
    ).first()

    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokasie nie gevind nie")

    student = db.query(Student).filter(
        Student.STU_Nommer == data.student_nom_or_id.strip()
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student nie gevind nie")

    gebruiker = db.query(Gebruikers).filter(
        Gebruikers.Gebruiker_ID == student.Gebruiker_ID,
        Gebruikers.Is_Aktief == True
    ).first()

    if not gebruiker:
        raise HTTPException(status_code=403, detail="Student is nie aktief nie")

    log = ToegangsLogs(
        Gebruiker_ID=student.Gebruiker_ID,
        Lokasie_ID=data.lokasie_id,
        NFC_Tags_ID=None,
        TOE_Rigting=data.rigting,
        TOE_Metode=data.metode,
        TOE_Auto_Uitgecheck=False,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "sukses": True,
        "message": "Student skandering suksesvol",
        "data": {
            "log_id": log.Log_ID,
            "student_id": student.Gebruiker_ID,
            "student_nommer": student.STU_Nommer,
            "naam": gebruiker.GEB_Naam,
            "van": gebruiker.GEB_Van,
            "foto_url": gebruiker.GEB_Profiel_Foto,
            "lokasie": lokasie.LOK_Naam,
            "rigting": log.TOE_Rigting,
            "metode": log.TOE_Metode,
            "tyd": log.TOE_Tydstempel.isoformat() if log.TOE_Tydstempel else None,
        },
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

    current_user.GEB_Profiel_Foto = foto_url
    db.commit()
    db.refresh(current_user)

    return {
        "sukses": True,
        "data": {
            "foto_url": foto_url,
        },
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
    
    
    
    
    
    