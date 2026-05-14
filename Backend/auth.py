from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import database, models

load_dotenv()

# Konfigurasie
SECRET_KEY = os.getenv("SECRET_KEY", "jou-geheime-sleutel-vir-toetsing")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 dag

# Span-toetsing / Docker: stel DISABLE_AUTH=1 om JWT- en roltoetsing te omseil (moet AF wees in produksie).
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "").strip().lower() in ("1", "true", "yes", "on")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=not DISABLE_AUTH)


# def _dev_fallback_user(db: Session) -> models.Gebruikers:
#     """Eerste Administrateur in DB, anders enige gebruiker — slegs vir DISABLE_AUTH."""
#     admin_rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Administrateur").first()
#     if admin_rol:
#         user = (
#             db.query(models.Gebruikers)
#             .filter(models.Gebruikers.Rol_ID == admin_rol.Rol_ID)
#             .first()
#         )
#         if user:
#             return user
#     user = db.query(models.Gebruikers).first()
#     if user:
#         return user
#     raise HTTPException(
#         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#         detail="DISABLE_AUTH is aan maar die databasis het geen gebruikers nie.",
#     )


def _dev_fallback_user(db: Session) -> models.Gebruikers:
    admin_rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Administrateur").first()

    if admin_rol:
        user = (
            db.query(models.Gebruikers)
            .filter(models.Gebruikers.Rol_ID == admin_rol.Rol_ID)
            .first()
        )
        if user:
            return user

    user = db.query(models.Gebruikers).first()
    if user:
        return user

    return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    if DISABLE_AUTH:
        return _dev_fallback_user(db)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kon nie geloofsbriewe verifieer nie",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# --- ROL MIDDLEWARE ---

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, 
        current_user: models.Gebruikers = Depends(get_current_user), 
        db: Session = Depends(database.get_db)
    ):
        if DISABLE_AUTH:
            return True

        rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
        if not rol:
            raise HTTPException(status_code=403, detail="Gebruiker het geen geldige rol nie")

        # Admins het universele toegang
        if rol.ROL_Naam == "Administrateur":
            return True

        # Check of die rol in die toegelate lys is
        if rol.ROL_Naam not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Toegang geweier. Benodig een van: {self.allowed_roles}"
            )

        return True

async def verifieer_kampus_toegang(
    kampus_id: int, 
    current_user: models.Gebruikers = Depends(get_current_user), 
    db: Session = Depends(database.get_db)
):
    """
    Check of 'n gebruiker toegang het tot 'n spesifieke kampus.
    Word gebruik as 'n addisionele check vir Kampus_Opsigters.
    """
    if DISABLE_AUTH:
        return True

    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
    
    if rol.ROL_Naam == "Administrateur":
        return True
    
    if rol.ROL_Naam == "Kampus_Opsigter":
        opsigter_rekord = db.query(models.Kampus_Opsigter).filter(
            models.Kampus_Opsigter.Gebruiker_ID == current_user.Gebruiker_ID,
            models.Kampus_Opsigter.Kampus_ID == kampus_id
        ).first()
        
        if opsigter_rekord:
            return True
            
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Jy het nie toestemming om data vir hierdie kampus te sien of te verander nie."
    )

# Voorafgedefinieerde dependencies vir maklike gebruik in routes
check_admin = RoleChecker(["Administrateur"])
check_opsigter = RoleChecker(["Administrateur", "Kampus_Opsigter"])
check_sekuriteit = RoleChecker(["Administrateur", "Kampus_Opsigter", "Sekuriteit_Wag"])
