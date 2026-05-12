from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from database import engine, get_db
import models, schemas, auth

# Skep alle tabelle outomaties by opstart
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MOON Admin API",
    description="Louis se Admin API vir die MOON projek.",
    version="1.0.0"
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

@app.get("/", response_model=schemas.APIResponse[dict])
def read_root():
    return schemas.APIResponse(sukses=True, data={"message": "Backend is working"})

# --- AUTH ROETES ---

@app.post("/token", response_model=schemas.APIResponse[dict])
def login_vir_toegang_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Gebruikers).filter(models.Gebruikers.GEB_Epos == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.GEB_Wagwoord):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verkeerde e-pos of wagwoord"
        )
    
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == user.Rol_ID).first()
    rol_naam = rol.ROL_Naam if rol else "Onbekend"

    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.Gebruiker_ID), "rol": user.Rol_ID, "rol_naam": rol_naam}, 
        expires_delta=access_token_expires
    )
    return schemas.APIResponse(
        sukses=True, 
        data={"access_token": access_token, "token_type": "bearer"}
    )

# --- GEBRUIKER ROETES ---

@app.post("/gebruikers", response_model=schemas.APIResponse[schemas.User], status_code=status.HTTP_201_CREATED)
def skep_gebruiker(
    user_in: schemas.UserCreate, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    """
    F2: Skep 'n nuwe gebruiker. Slegs vir Admin.
    """
    # Check vir bestaande e-pos
    if db.query(models.Gebruikers).filter(models.Gebruikers.GEB_Epos == user_in.GEB_Epos).first():
        raise HTTPException(status_code=400, detail="E-pos reeds geregistreer")
    
    # Check vir bestaande ID nommer
    if db.query(models.Gebruikers).filter(models.Gebruikers.GEB_ID_Nommer == user_in.GEB_ID_Nommer).first():
        raise HTTPException(status_code=400, detail="ID Nommer reeds in gebruik")

    db_user = models.Gebruikers(
        GEB_Naam=user_in.GEB_Naam,
        GEB_Van=user_in.GEB_Van,
        GEB_ID_Nommer=user_in.GEB_ID_Nommer,
        GEB_Epos=user_in.GEB_Epos,
        GEB_Wagwoord=auth.get_password_hash(user_in.GEB_Wagwoord), # Hash wagwoord (F2)
        GEB_Selfoon_Nr=user_in.GEB_Selfoon_Nr,
        GEB_Profiel_Foto=user_in.GEB_Profiel_Foto,
        Rol_ID=user_in.Rol_ID,
        Is_Aktief=user_in.Is_Aktief
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return schemas.APIResponse(sukses=True, data=db_user)

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
    return schemas.APIResponse(sukses=True, data=db_user)

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
            data=[schemas.UserSecurityRead.from_orm(g) for g in gebruikers]
        )

    return schemas.APIResponse(sukses=True, data=gebruikers)

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
        return schemas.APIResponse(sukses=True, data=schemas.UserSecurityRead.from_orm(gebruiker))

    return schemas.APIResponse(sukses=True, data=gebruiker)

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

@app.get("/rolle", response_model=schemas.APIResponse[List[schemas.Rol]])
def lees_rolle(db: Session = Depends(get_db)):
    """
    Stuur 'n lys van alle rolle terug.
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

@app.get("/lokasies", response_model=schemas.APIResponse[List[schemas.Lokasie]])
def lys_lokasies(
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    """
    Stap 2: Lys alle klaskamers.
    """
    lokasies = db.query(models.Lokasie).all()
    return schemas.APIResponse(sukses=True, data=lokasies)

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
    bestaande_nfc = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == klas_in.nfc_uid.strip()
    ).first()
    if bestaande_nfc:
        raise HTTPException(status_code=400, detail="Hierdie NFC UID is reeds geregistreer")

    if klas_in.kampus_id is not None:
        kampus_bestaan = db.query(models.Kampus).filter(
            models.Kampus.Kampus_ID == klas_in.kampus_id
        ).first()
        if not kampus_bestaan:
            raise HTTPException(status_code=400, detail="Kampus_ID bestaan nie in die databasis nie")

    try:
        db_lokasie = models.Lokasie(
            naam=klas_in.naam.strip(),
            beskrywing=(klas_in.beskrywing or "").strip() or None,
            kampus_id=klas_in.kampus_id,
        )
        db.add(db_lokasie)
        db.flush()

        db_tag = models.NFC_Tags(
            NFC_UID=klas_in.nfc_uid.strip(),
            Gebruiker_ID=None,
            Lokasie_ID=db_lokasie.id,
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