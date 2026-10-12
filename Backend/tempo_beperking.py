"""MOON tempo-beperking vir sensitiewe API-roetes.

In-memory is doelbewus vir die huidige enkele Uvicorn-werker.
As MOON later na meer werkers/replicas skuif, vervang die store met Redis.
"""

from __future__ import annotations

from collections import deque
import hashlib
import ipaddress
import logging
import math
import os
import threading
import time
from typing import Optional

from fastapi import HTTPException, Request, status


logger = logging.getLogger("moon.security")
_lock = threading.Lock()
_buckets: dict[str, deque[float]] = {}
_last_cleanup = 0.0

_DEFAULT_WINDOW_SECONDS = 60
_STALE_BUCKET_SECONDS = 10 * 60


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _geldige_ip(value: str | None) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip().strip('"')
    # X-Forwarded-For bevat normaalweg nie poorte nie. Laat IPv6 se ":" dus
    # onaangeraak en aanvaar net waardes wat ipaddress kan valideer.
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def kry_klient_ip(request: Request) -> str:
    """Kry die kliënt-IP sonder om arbitrêre proxy headers plaaslik te vertrou.

    Produksie op Railway vertrou X-Forwarded-For. Ons kies vanaf regs volgens
    TRUSTED_PROXY_HOPS om 'n self-gespoofte linkerwaarde nie blind te vertrou nie.
    Standaard: 1 (Railway se randproxy). Indien nog 'n betroubare proxy voor
    Railway bykom, stel TRUSTED_PROXY_HOPS=2.
    """

    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    is_production = env in {"production", "prod"}
    trust_proxy = _is_true(
        os.getenv("TRUST_PROXY_HEADERS", "1" if is_production else "0")
    )

    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        forwarded_ips = [
            ip
            for ip in (_geldige_ip(part) for part in forwarded.split(","))
            if ip is not None
        ]
        if forwarded_ips:
            try:
                trusted_hops = max(
                    1,
                    int(os.getenv("TRUSTED_PROXY_HOPS", "1")),
                )
            except ValueError:
                trusted_hops = 1

            index_from_right = min(trusted_hops, len(forwarded_ips))
            return forwarded_ips[-index_from_right]

        real_ip = _geldige_ip(request.headers.get("x-real-ip"))
        if real_ip:
            return real_ip

    if request.client and request.client.host:
        return _geldige_ip(request.client.host) or request.client.host

    return "unknown"


def _subject_hash(subject: str | int | None) -> str:
    if subject is None:
        return "-"
    raw = str(subject).strip().casefold().encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:20]


def _cleanup_locked(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 60 and len(_buckets) < 5000:
        return

    for key, timestamps in list(_buckets.items()):
        while timestamps and now - timestamps[0] > _STALE_BUCKET_SECONDS:
            timestamps.popleft()
        if not timestamps:
            _buckets.pop(key, None)

    _last_cleanup = now


def beperk_versoeke(
    request: Request,
    *,
    bucket: str,
    limiet: int,
    venster_sekondes: int = _DEFAULT_WINDOW_SECONDS,
    subject: str | int | None = None,
    boodskap: str = "Te veel versoeke. Probeer asseblief oor 'n minuut weer.",
) -> None:
    """Dwing 'n vaste-venster-agtige sliding rate limit af.

    Sleutel = roete-bucket + kliënt-IP + gehashte opsionele subject.
    Die subject is nuttig vir bv. gebruiker-ID of gebruikersnaam en word nooit
    in rou vorm in die in-memory sleutel gestoor nie.
    """

    if limiet <= 0 or venster_sekondes <= 0:
        raise ValueError("limiet en venster_sekondes moet groter as nul wees")

    ip = kry_klient_ip(request)
    key = f"{bucket}|{ip}|{_subject_hash(subject)}"
    now = time.monotonic()

    with _lock:
        _cleanup_locked(now)
        timestamps = _buckets.setdefault(key, deque())

        while timestamps and now - timestamps[0] >= venster_sekondes:
            timestamps.popleft()

        if len(timestamps) >= limiet:
            retry_after = max(
                1,
                math.ceil(venster_sekondes - (now - timestamps[0])),
            )
            logger.warning(
                "Tempo-limiet bereik: bucket=%s ip=%s retry_after=%ss",
                bucket,
                ip,
                retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=boodskap,
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)


def _reset_rate_limits_for_tests() -> None:
    """Net vir pytest/regressietoetse."""
    global _last_cleanup
    with _lock:
        _buckets.clear()
        _last_cleanup = 0.0
