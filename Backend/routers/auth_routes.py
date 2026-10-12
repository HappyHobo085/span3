"""Auth routes — /token (login) and /logout."""

from fastapi import APIRouter, Depends, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
import models, schemas, auth
from services.gebruiker_service import get_user_role_names, kies_primere_rol
from tempo_beperking import beperk_versoeke

router = APIRouter(tags=["Auth"])


@router.post("/token", response_model=schemas.APIResponse[dict])
def login_vir_toegang_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip()

    # MOON-SEC-016: beperk brute-force pogings per IP, plus per IP+gebruikersnaam.
    beperk_versoeke(
        request,
        bucket="login-ip",
        limiet=10,
        venster_sekondes=60,
        boodskap="Te veel aanmeldpogings. Wag asseblief 'n minuut en probeer weer.",
    )
    beperk_versoeke(
        request,
        bucket="login-gebruiker",
        limiet=5,
        venster_sekondes=60,
        subject=username,
        boodskap="Te veel aanmeldpogings. Wag asseblief 'n minuut en probeer weer.",
    )

    user = None

    if "@" in username:
        user = db.query(models.Gebruikers).filter(
            models.Gebruikers.GEB_Epos == username
        ).first()

    if not user:
        student = db.query(models.Student).filter(
            models.Student.STU_Nommer == username
        ).first()

        if student:
            kandidaat = db.query(models.Gebruikers).filter(
                models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
            ).first()
            # Slegs 'n gebruiker wat tans nog die Student-rol het mag met sy
            # studentenommer aanmeld (voormalige studente val deur na 401).
            if kandidaat and "Student" in get_user_role_names(db, kandidaat):
                user = kandidaat

    if not auth.verify_password_of_skyn(form_data.password, user):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verkeerde gebruikersnaam of wagwoord"
        )

    role_names = get_user_role_names(db, user)

    # Gebruikers sonder enige rol (bv. voormalige studente wie se Student-rol
    # verwyder is) mag nie aanmeld nie.
    if not role_names:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verkeerde gebruikersnaam of wagwoord"
        )

    rol_naam = kies_primere_rol(role_names)

    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.Gebruiker_ID), "rol": user.Rol_ID, "rol_naam": rol_naam, "roles": role_names},
        expires_delta=access_token_expires
    )

    request.session["user_id"] = user.Gebruiker_ID
    request.session["rol"] = user.Rol_ID
    request.session["rol_naam"] = rol_naam
    request.session["roles"] = role_names

    import os
    is_production = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=is_production,
    )

    return schemas.APIResponse(
        sukses=True,
        data={"access_token": access_token, "token_type": "bearer"}
    )


@router.post("/logout", response_model=schemas.APIResponse[dict])
def logout(response: Response, request: Request):
    request.session.clear()
    response.delete_cookie("access_token")
    return schemas.APIResponse(sukses=True, data={"boodskap": "Suksesvol afgemeld"})
