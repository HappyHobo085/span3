"""MOON Admin API — App factory."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

logger = logging.getLogger("moon")

import auth, schemas
from database import engine
import models
from migrations import run_pre_migrations, run_migrations

from routers import (
    auth_routes, gebruikers, kampus, koshuis, lokasie,
    nfc, wagte, student, dashboard, admin, saamry, besoekers, events, noodgeval,
)

# Rename legacy misspelled event tables BEFORE SQLAlchemy checks/creates tables.
run_pre_migrations(engine)

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
    logger.exception("Onverwagte fout: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=schemas.APIResponse(sukses=False, data=None, fout="Interne bedienerfout").dict()
    )

# --- Middleware ---

# CORS: explicit origins — no wildcard with credentials
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:80,http://localhost:8000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(auth.AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.SESSION_SECRET_KEY,
    session_cookie="moon_session",
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
app.include_router(noodgeval.router)

# --- Root ---

@app.get("/", response_model=schemas.APIResponse[dict])
def read_root():
    return schemas.APIResponse(sukses=True, data={"message": "Backend is working"})