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
            # Stap 2 & 3: Soek en deaktiveer NFC tags (F1/F13 Integrasie)
            # Nota: In 'n produksie-omgewing met microservices sou hierdie 'n API-oproep na Steven se diens wees.
            db.query(models.NFC_Tags).filter(
                models.NFC_Tags.Gebruiker_ID == user_id, 
                models.NFC_Tags.NFC_Is_Aktief == True
            ).update({"NFC_Is_Aktief": False})

            # Stap 4: Skep waarskuwing rekord met spesifieke beskrywing
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


@app.post("/nfc/register", response_model=schemas.APIResponse[schemas.NFCTag])
def registreer_nfc_tag(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    # Check of tag reeds bestaan
    if db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == tag_in.NFC_UID).first():
        raise HTTPException(status_code=400, detail="Tag reeds geregistreer")

    # Check of user reeds 'n aktiewe tag het
    existing = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == tag_in.Gebruiker_ID,
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Gebruiker het reeds 'n aktiewe tag")

    new_tag = models.NFC_Tags(**tag_in.dict())
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)

    return schemas.APIResponse(sukses=True, data=new_tag)


@app.put("/nfc/deactivate/{tag_id}", response_model=schemas.APIResponse[dict])
def deactivate_nfc(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_Tags_ID == tag_id).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag nie gevind nie")

    tag.NFC_Is_Aktief = False
    db.commit()

    return schemas.APIResponse(sukses=True, data={"boodskap": "Tag gedeaktiveer"})


@app.get("/sekuriteit/toegang")
def sekuriteit_toegang(
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_sekuriteit: bool = Depends(auth.check_sekuriteit)
):
    return schemas.APIResponse(
        sukses=True,
        data={"boodskap": "Sekuriteit toegang bevestig"}
    )
    
    

@app.post("/nfc-tags/registreer", response_model=schemas.APIResponse[schemas.NFCTag])
def registreer_nfc_tag(
    tag_in: schemas.NFCTagCreate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    # 1. Check of NFC_UID reeds bestaan
    bestaande_tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.NFC_UID == tag_in.NFC_UID
    ).first()

    if bestaande_tag:
        raise HTTPException(status_code=400, detail="NFC tag reeds geregistreer")

    # 2. Check of gebruiker bestaan
    gebruiker = db.query(models.Gebruikers).filter(
        models.Gebruikers.Gebruiker_ID == tag_in.Gebruiker_ID
    ).first()

    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker nie gevind nie")

    # 3. Maak ou aktiewe tag onaktief
    db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == tag_in.Gebruiker_ID,
        models.NFC_Tags.NFC_Is_Aktief == True
    ).update({"NFC_Is_Aktief": False})

    # 4. Skep nuwe aktiewe tag
    nuwe_tag = models.NFC_Tags(
        NFC_UID=tag_in.NFC_UID,
        Gebruiker_ID=tag_in.Gebruiker_ID,
        NFC_Tipe=tag_in.NFC_Tipe,
        NFC_Is_Aktief=True
    )

    db.add(nuwe_tag)
    db.commit()
    db.refresh(nuwe_tag)

    return schemas.APIResponse(sukses=True, data=nuwe_tag)


@app.patch("/nfc-tags/{gebruiker_id}/deaktiveer", response_model=schemas.APIResponse[dict])
def deaktiveer_gebruiker_nfc_tag(
    gebruiker_id: int,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin)
):
    aktiewe_tag = db.query(models.NFC_Tags).filter(
        models.NFC_Tags.Gebruiker_ID == gebruiker_id,
        models.NFC_Tags.NFC_Is_Aktief == True
    ).first()

    if not aktiewe_tag:
        raise HTTPException(status_code=404, detail="Geen aktiewe NFC tag vir hierdie gebruiker gevind nie")

    aktiewe_tag.NFC_Is_Aktief = False
    db.commit()

    return schemas.APIResponse(
        sukses=True,
        data={"boodskap": "Aktiewe NFC tag suksesvol gedeaktiveer"}
    )