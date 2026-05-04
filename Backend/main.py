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
    
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.Gebruiker_ID), "rol": user.Rol_ID}, 
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

# --- NFC ROETES (Steven se verantwoordelikheid, maar Louis integreer hiermee) ---

@app.patch("/nfc-tags/{user_id}/deaktiveer", response_model=schemas.APIResponse[dict])
def deaktiveer_nfc_tags(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user)
):
    """
    F13: Steven se eindpunt om NFC tags te deaktiveer.
    Word deur Louis se F1 logika aangeroep.
    """
    db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == user_id, 
        models.NFC_Tags.NFC_Is_Aktief == True
    ).update({"NFC_Is_Aktief": False})
    
    # Steven skep NIE die waarskuwing nie - dit is Louis se werk.
    db.commit()
    return schemas.APIResponse(sukses=True, data={"boodskap": "NFC tags gedeaktiveer"})

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
            # Stap 2 & 3: Roep Steven se F13 eindpunt aan (F1/F13 Integrasie)
            # In 'n microservice argitektuur sou dit 'n HTTP PATCH wees.
            # Hier simuleer ons dit deur die funksie direk te roep.
            deaktiveer_nfc_tags(user_id=user_id, db=db, current_user=current_user)

            # Stap 4: Skep waarskuwing rekord met spesifieke beskrywing (Louis se verantwoordelikheid)
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
        # Rol terug as enige stap misluk
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fout tydens transaksie: {str(e)}")
