"""HTTP-sekuriteitsinstellings vir die FastAPI-app (MOON-SEC-017 en -018)."""

import os

from fastapi import Request


def is_produksie() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() in ("production", "prod")


def dokumentasie_urls() -> dict:
    """Geen publieke /docs, /redoc of /openapi.json in produksie nie."""
    if is_produksie():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


async def voeg_sekuriteitsopskrifte_by(request: Request, call_next):
    """Standaard HTTP-sekuriteitsopskrifte op elke antwoord."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if is_produksie():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response
