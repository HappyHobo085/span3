"""MOON Admin API — App factory."""

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import http_sekuriteit
import schemas
import models

from database import engine
from migrations import run_pre_migrations, run_migrations
from noodgeval_kontrole_migration import run_noodgeval_kontrole_migration
from noodgeval_device_migration import run_noodgeval_device_migration

# Outo-uitcheck scheduler
from auto_uitcheck import maak_scheduler_aan, sluit_scheduler_af

from routers import (
    auth_routes,
    gebruikers,
    kampus,
    koshuis,
    lokasie,
    nfc,
    wagte,
    student,
    dashboard,
    admin,
    saamry,
    besoekers,
    events,
    noodgeval,
    noodgeval_live,
    noodgeval_kontrole,
    noodgeval_device,
    instellings,
    klasse,
    verslae,
    lokaalgebruik_ml,
)


logger = logging.getLogger("moon")


# =====================================================================
# DATABASE / MIGRATIONS
# =====================================================================

# Rename legacy misspelled event tables BEFORE SQLAlchemy checks/creates tables.
run_pre_migrations(engine)

# Skep alle tabelle outomaties by opstart.
models.Base.metadata.create_all(bind=engine)

# Idempotent startup migrations.
run_migrations(engine)
run_noodgeval_kontrole_migration(engine)
run_noodgeval_device_migration(engine)


# =====================================================================
# APP LIFESPAN
# =====================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Begin agtergrond-dienste wanneer FastAPI start
    en stop hulle veilig wanneer die toepassing afsluit.
    """

    auto_uitcheck_scheduler = None

    try:
        # Begin die outomatiese kampus-uitcheck scheduler.
        auto_uitcheck_scheduler = maak_scheduler_aan()

        logger.info("MOON backend gestart")
        logger.info("Auto-uitcheck scheduler gestart")

        yield

    finally:
        # Stop scheduler veilig wanneer Railway/FastAPI afsluit.
        if auto_uitcheck_scheduler is not None:
            sluit_scheduler_af(auto_uitcheck_scheduler)

        logger.info("MOON backend gestop")


# =====================================================================
# FASTAPI APP
# =====================================================================

app = FastAPI(
    title="MOON Admin API",
    description="Louis se Admin API vir die MOON projek.",
    version="1.0.0",
    lifespan=lifespan,
    # MOON-SEC-017: geen publieke API-dokumentasie in produksie nie.
    **http_sekuriteit.dokumentasie_urls(),
)


# =====================================================================
# STATIC FILES
# =====================================================================

UPLOAD_DIR = "uploads/profile_photos"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads",
)


# =====================================================================
# EXCEPTION HANDLERS
# =====================================================================

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.APIResponse(
            sukses=False,
            data=None,
            fout=exc.detail,
        ).dict(),
        # Behou bv. Retry-After vir HTTP 429 tempo-beperkings.
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Onverwagte fout: %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content=schemas.APIResponse(
            sukses=False,
            data=None,
            fout="Interne bedienerfout",
        ).dict(),
    )


# =====================================================================
# MIDDLEWARE
# =====================================================================

# CORS: explicit origins — no wildcard with credentials.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost,http://localhost:80,http://localhost:8000",
    ).split(",")
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


# MOON-SEC-018: standaard HTTP-sekuriteitsopskrifte op elke antwoord.
app.middleware("http")(http_sekuriteit.voeg_sekuriteitsopskrifte_by)


app.add_middleware(
    SessionMiddleware,
    secret_key=auth.SESSION_SECRET_KEY,
    session_cookie="moon_session",
)


# =====================================================================
# REGISTER ROUTERS
# =====================================================================

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
app.include_router(noodgeval_live.router)
app.include_router(noodgeval_kontrole.router)
app.include_router(noodgeval_device.router)
app.include_router(instellings.router)
app.include_router(klasse.router)
app.include_router(verslae.router)
app.include_router(lokaalgebruik_ml.router)


# =====================================================================
# ROOT
# =====================================================================

@app.get("/", response_model=schemas.APIResponse[dict])
def read_root():
    return schemas.APIResponse(
        sukses=True,
        data={
            "message": "Backend werk",
        },
    )