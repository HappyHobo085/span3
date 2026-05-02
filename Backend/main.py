from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

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

@app.get("/gebruikers", response_model=schemas.APIResponse[List[schemas.User]])
def lees_gebruikers(
    skip: int = 0, 
    limit: int = 100, 
    kampus_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_opsigter)
):
    """
    Stuur 'n lys van gebruikers terug. 
    As 'n kampus_id verskaf word, word toegang eers verifieer (F20).
    """
    query = db.query(models.Gebruikers)

    # As dit 'n opsigter is, MOET ons filter op hul kampus as hulle nie 'n spesifieke een vra nie,
    # of verifieer dat hulle toegang het tot die een wat hulle vra.
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
    
    if rol.ROL_Naam == "Kampus_Opsigter":
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        if not opsigter_info:
            raise HTTPException(status_code=403, detail="Opsigter is nie aan 'n kampus gekoppel nie.")
        
        # Filter altyd op die opsigter se eie kampus
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == opsigter_info.Kampus_ID)
    elif kampus_id:
        # Admins kan filter op enige kampus
        query = query.join(models.Kampus_Opsigter, models.Gebruikers.Gebruiker_ID == models.Kampus_Opsigter.Gebruiker_ID)\
                     .filter(models.Kampus_Opsigter.Kampus_ID == kampus_id)

    gebruikers = query.offset(skip).limit(limit).all()
    return schemas.APIResponse(sukses=True, data=gebruikers)

@app.get("/gebruikers/{user_id}", response_model=schemas.APIResponse[schemas.User])
def lees_gebruiker(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_authorized: bool = Depends(auth.check_opsigter)
):
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if gebruiker is None:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")
    
    # F20: Check of die opsigter toegang het tot hierdie spesifieke gebruiker se kampus
    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
    if rol.ROL_Naam == "Kampus_Opsigter":
        # Check of die gebruiker aan dieselfde kampus as die opsigter behoort
        opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID).first()
        gebruiker_opsigter_info = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == user_id).first()
        
        # Hierdie is 'n vereenvoudigde check - in 'n regte stelsel sal studente ook aan kampusse gekoppel wees.
        # Vir nou check ons of die gebruiker wat opgevra word, in die opsigter se kampus is (as hulle ook 'n opsigter is)
        # OF ons gooi 'n fout as die opsigter probeer om buite hul skoop te kyk.
        if gebruiker_opsigter_info and gebruiker_opsigter_info.Kampus_ID != opsigter_info.Kampus_ID:
            raise HTTPException(status_code=403, detail="Jy het nie toegang tot hierdie gebruiker nie.")

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
    Deaktiveer 'n gebruiker en hul NFC-tags. Slegs vir Admin.
    """
    gebruiker = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    try:
        gebruiker.Is_Aktief = is_aktief
        
        if not is_aktief:
            # Deaktiveer NFC tags
            db.query(models.NFC_Tags).filter(
                models.NFC_Tags.Gebruiker_ID == user_id, 
                models.NFC_Tags.NFC_Is_Aktief == True
            ).update({"NFC_Is_Aktief": False})

            # Skep waarskuwing
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
        raise HTTPException(status_code=500, detail=f"Fout tydens opdatering: {str(e)}")
