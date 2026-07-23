"""Auth routes — /token (login) and /logout."""

from fastapi import APIRouter, Depends, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
import models, schemas, auth

router = APIRouter(tags=["Auth"])


@router.post("/token", response_model=schemas.APIResponse[dict])
def login_vir_toegang_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip()

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
            user = db.query(models.Gebruikers).filter(
                models.Gebruikers.Gebruiker_ID == student.Gebruiker_ID
            ).first()

    if not user or not auth.verify_password(form_data.password, user.GEB_Wagwoord):
        from fastapi import HTTPException
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

    request.session["user_id"] = user.Gebruiker_ID
    request.session["rol"] = user.Rol_ID
    request.session["rol_naam"] = rol_naam

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
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
