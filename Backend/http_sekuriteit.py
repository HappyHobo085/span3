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


# --- MOON-SEC-009: grootte-limiete op oplaaie ---------------------------------
# Ruim verstekwaardes (verstelbaar met omgewingsveranderlikes) sodat 'n volle,
# regte uitvoer nooit geweier word nie, maar 'n zip-bom die bediener nie platstoot nie.

_MB = 1024 * 1024
MAKS_CSV_BYTES = int(os.getenv("MAKS_CSV_MB", "20")) * _MB
MAKS_ZIP_BYTES = int(os.getenv("MAKS_ZIP_MB", "50")) * _MB
MAKS_ZIP_ONGEKOMPRIMEER_BYTES = int(os.getenv("MAKS_ZIP_ONGEKOMPRIMEER_MB", "500")) * _MB
MAKS_ZIP_LEERS = int(os.getenv("MAKS_ZIP_LEERS", "200"))


def _te_groot(maks: int):
    from fastapi import HTTPException
    return HTTPException(status_code=413, detail=f"Lêer te groot — maksimum {maks // _MB} MB toegelaat")


async def lees_beperk(upload, maks: int) -> bytes:
    """Lees 'n oplaai, maar nooit meer as `maks` grepe in die geheue nie."""
    data = await upload.read(maks + 1)
    if len(data) > maks:
        raise _te_groot(maks)
    return data


def lees_beperk_sync(lêer, maks: int) -> bytes:
    data = lêer.read(maks + 1)
    if len(data) > maks:
        raise _te_groot(maks)
    return data


def kontroleer_zip(zf) -> None:
    """Weier 'n ZIP met te veel lêers of te veel ongekomprimeerde data, vóór uitpak."""
    from fastapi import HTTPException
    inligting = zf.infolist()
    if len(inligting) > MAKS_ZIP_LEERS:
        raise HTTPException(status_code=413, detail=f"ZIP bevat te veel lêers (maksimum {MAKS_ZIP_LEERS})")
    if sum(i.file_size for i in inligting) > MAKS_ZIP_ONGEKOMPRIMEER_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Ongekomprimeerde ZIP-inhoud te groot (maksimum {MAKS_ZIP_ONGEKOMPRIMEER_BYTES // _MB} MB)",
        )


def foto_tipe(data: bytes) -> str | None:
    """Herken JPG, PNG of WEBP aan die lêer se inhoud, nie aan die naam nie."""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None
