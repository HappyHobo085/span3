"""MOON Admin API — App factory."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
import os

import auth, schemas
from database import engine
import models
from migrations import run_migrations

from routers import (
    auth_routes, gebruikers, kampus, koshuis, lokasie,
    nfc, wagte, student, dashboard, admin, saamry, besoekers, events,
)

# Skep alle tabelle outomaties by opstart
models.Base.metadata.create_all(bind=engine)

# Idempotent startup migrations
run_migrations(engine)

app = FastAPI(
    title="MOON Admin API",
    description="Louis se Admin API vir die MOON projek.",
    version="1.0.0"
)

# Static files
UPLOAD_DIR = "uploads/profile_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- Exception Handlers ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.APIResponse(sukses=False, data=None, fout=exc.detail).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=schemas.APIResponse(sukses=False, data=None, fout=f"Interne bedienerfout: {str(exc)}").dict()
    )

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(auth.AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.SECRET_KEY,
    session_cookie="moon_session"
)

# --- Register Routers ---

app.include_router(auth_routes.router)
app.include_router(gebruikers.router)
app.include_router(kampus.router)
app.include_router(koshuis.router)
app.include_router(lokasie.router)
app.include_router(nfc.router)
app.include_router(wagte.router)
app.include_router(student.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(saamry.router)
app.include_router(besoekers.router)
app.include_router(events.router)

# --- Root ---

@app.get("/", response_model=schemas.APIResponse[dict])
def read_root():
    return schemas.APIResponse(sukses=True, data={"message": "Backend is working"})
