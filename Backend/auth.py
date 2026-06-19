from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
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

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Stel verstekwaardes vir request.state
        request.state.user = None
        request.state.role = None

        if DISABLE_AUTH:
            db = database.SessionLocal()
            try:
                fallback = _dev_fallback_user(db)
                if fallback:
                    request.state.user = fallback
                    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == fallback.Rol_ID).first()
                    if rol:
                        request.state.role = rol.ROL_Naam
            except Exception:
                pass
            finally:
                db.close()
            return await call_next(request)

        # 1. Probeer token kry uit Authorization Header
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # 2. Probeer token kry uit Cookies (Sessie-gebaseerde/koekie auth)
        if not token:
            token = request.cookies.get("access_token")

        # 3. Probeer user_id kry uit Starlette Sessie
        user_id = None
        if not token and "session" in request.scope and "user_id" in request.session:
            user_id = request.session.get("user_id")

        # As ons 'n token gekry het, dekodeer dit
        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
            except JWTError:
                pass  # Ongeldige token, verontagsaam

        # As ons 'n geldige user_id het, haal gebruiker en rol uit databasis
        if user_id:
            db = database.SessionLocal()
            try:
                user = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == int(user_id)).first()
                if user:
                    request.state.user = user
                    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == user.Rol_ID).first()
                    if rol:
                        request.state.role = rol.ROL_Naam
            except Exception:
                pass
            finally:
                db.close()

        response = await call_next(request)
        return response

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    if DISABLE_AUTH:
        return _dev_fallback_user(db)

    # Check of die gebruiker reeds deur die AuthMiddleware op request.state gestel is
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

    # As dit nie op request.state is nie, maar ons het wel 'n token gekry via oauth2_scheme (bvl. Swagger UI)
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = db.query(models.Gebruikers).filter(models.Gebruikers.Gebruiker_ID == int(user_id)).first()
                if user:
                    request.state.user = user
                    rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == user.Rol_ID).first()
                    if rol:
                        request.state.role = rol.ROL_Naam
                    return user
        except JWTError:
            pass

    # Indien daar geen geldige gebruiker gevind is nie, gooi ongemagtig
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kon nie geloofsbriewe verifieer nie",
        headers={"WWW-Authenticate": "Bearer"},
    )

# --- ROL MIDDLEWARE ---

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, 
        request: Request,
        current_user: models.Gebruikers = Depends(get_current_user), 
        db: Session = Depends(database.get_db)
    ):
        if DISABLE_AUTH:
            return True

        rol_naam = getattr(request.state, "role", None)
        if not rol_naam:
            rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
            if not rol:
                raise HTTPException(status_code=403, detail="Gebruiker het geen geldige rol nie")
            rol_naam = rol.ROL_Naam

        # Admins het universele toegang
        if rol_naam == "Administrateur":
            return True

        # Check of die rol in die toegelate lys is
        if rol_naam not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Toegang geweier. Benodig een van: {self.allowed_roles}"
            )

        return True

async def verifieer_kampus_toegang(
    request: Request,
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

    rol_naam = getattr(request.state, "role", None)
    if not rol_naam:
        rol = db.query(models.Rolle).filter(models.Rolle.Rol_ID == current_user.Rol_ID).first()
        rol_naam = rol.ROL_Naam if rol else None
    
    if rol_naam == "Administrateur":
        return True
    
    if rol_naam == "Kampus_Opsigter":
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
