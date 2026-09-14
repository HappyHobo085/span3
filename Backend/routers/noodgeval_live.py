"""MOON Noodgeval — live WebSocket feed for the Kampus Opsigter dashboard.

Step 6 deliberately keeps the WebSocket read-only. The existing REST endpoints remain
responsible for creating, closing, receiving and acknowledging emergencies.

The feed sends a fresh snapshot immediately, then checks the shared PostgreSQL database
at a short interval and only pushes again when the snapshot changes. This works even when
Uvicorn runs with multiple worker processes because PostgreSQL remains the shared source
of truth; no in-memory cross-worker event bus is required for this phase.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

import auth
import database
import models
from routers.noodgeval import _require_sender_for_campus


router = APIRouter(prefix="/noodgeval", tags=["Noodgeval Live"])

# 1 second is responsive enough for the capstone dashboard without hammering PostgreSQL.
WS_INTERVAL_SECONDS = max(
    0.5,
    float(os.getenv("NOODGEVAL_WS_INTERVAL_SECONDS", "1.0")),
)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    # Existing MOON DateTime columns are stored as naive UTC values.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _extract_ws_token(websocket: WebSocket) -> str | None:
    """Accept Bearer header first; query token is convenient for local testing."""
    auth_header = websocket.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    token = websocket.query_params.get("token")
    return token.strip() if token else None


def _authenticate_ws(websocket: WebSocket, db: Session) -> models.Gebruikers | None:
    if getattr(auth, "DISABLE_AUTH", False):
        # Local-only developer mode already used elsewhere by MOON.
        fallback = getattr(auth, "_dev_fallback_user", None)
        return fallback(db) if callable(fallback) else db.query(models.Gebruikers).first()

    token = _extract_ws_token(websocket)
    if not token:
        return None

    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return (
            db.query(models.Gebruikers)
            .filter(
                models.Gebruikers.Gebruiker_ID == int(user_id),
                models.Gebruikers.Is_Aktief.is_(True),
            )
            .first()
        )
    except (JWTError, TypeError, ValueError):
        return None


def _latest_gate_logs_for_campus(db: Session, kampus_id: int) -> list[models.ToegangsLogs]:
    """Return users whose latest *campus gate* log says they are IN at this campus.

    Classroom / residence scans are intentionally excluded from deciding campus presence.
    The latest gate log is calculated across all campuses first, then filtered to the
    selected campus. This avoids one person appearing simultaneously on two campuses.
    """

    latest_gate = (
        db.query(
            models.ToegangsLogs.Gebruiker_ID.label("gebruiker_id"),
            func.max(models.ToegangsLogs.TOE_Tydstempel).label("laaste_tyd"),
        )
        .join(
            models.Lokasie,
            models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
        )
        .filter(models.Lokasie.LOK_Tipe == "Kampus")
        .group_by(models.ToegangsLogs.Gebruiker_ID)
        .subquery()
    )

    return (
        db.query(models.ToegangsLogs)
        .join(
            latest_gate,
            and_(
                models.ToegangsLogs.Gebruiker_ID == latest_gate.c.gebruiker_id,
                models.ToegangsLogs.TOE_Tydstempel == latest_gate.c.laaste_tyd,
            ),
        )
        .join(
            models.Lokasie,
            models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID,
        )
        .filter(
            models.Lokasie.LOK_Tipe == "Kampus",
            models.Lokasie.Kampus_ID == kampus_id,
            models.ToegangsLogs.TOE_Rigting == "IN",
        )
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())
        .all()
    )


def _persoon_payload(user: models.Gebruikers, gate_log: models.ToegangsLogs) -> dict[str, Any]:
    if getattr(user, "student", None) is not None:
        tipe = "Student"
        nommer = user.student.STU_Nommer
    elif getattr(user, "personeel", None) is not None:
        tipe = "Personeel"
        nommer = user.personeel.PER_Nommer
    else:
        tipe = getattr(getattr(user, "rol", None), "ROL_Naam", None) or "Gebruiker"
        nommer = user.GEB_ID_Nommer

    return {
        "gebruiker_id": user.Gebruiker_ID,
        "naam": user.GEB_Naam,
        "van": user.GEB_Van,
        "volle_naam": f"{user.GEB_Naam} {user.GEB_Van}".strip(),
        "tipe": tipe,
        "nommer": nommer,
        "foto_url": user.GEB_Profiel_Foto,
        "laaste_hek_scan": _iso(gate_log.TOE_Tydstempel),
        "laaste_hek_metode": gate_log.TOE_Metode,
    }


def _build_snapshot(kampus_id: int) -> dict[str, Any]:
    db = database.SessionLocal()
    try:
        kampus = (
            db.query(models.Kampus)
            .filter(models.Kampus.Kampus_ID == kampus_id)
            .first()
        )
        if kampus is None:
            return {
                "tipe": "FOUT",
                "kampus_id": kampus_id,
                "fout": "Kampus nie gevind nie.",
            }

        emergency = (
            db.query(models.Noodgeval)
            .filter(
                models.Noodgeval.Kampus_ID == kampus_id,
                models.Noodgeval.NOO_Status == "AKTIEF",
            )
            .order_by(models.Noodgeval.NOO_Begin_Op.desc())
            .first()
        )

        gate_logs = _latest_gate_logs_for_campus(db, kampus_id)
        people: list[dict[str, Any]] = []
        people_ids: list[int] = []

        # A tie on an identical timestamp could produce a duplicate row; keep one per user.
        seen_user_ids: set[int] = set()
        for gate_log in gate_logs:
            user = gate_log.gebruiker
            if user is None or not user.Is_Aktief or user.Gebruiker_ID in seen_user_ids:
                continue
            seen_user_ids.add(user.Gebruiker_ID)
            people_ids.append(user.Gebruiker_ID)
            people.append(_persoon_payload(user, gate_log))

        ack_by_user: dict[int, models.NoodgevalKennisname] = {}
        if emergency is not None and people_ids:
            ack_rows = (
                db.query(models.NoodgevalKennisname)
                .filter(
                    models.NoodgevalKennisname.Noodgeval_ID == emergency.Noodgeval_ID,
                    models.NoodgevalKennisname.Gebruiker_ID.in_(people_ids),
                )
                .all()
            )
            ack_by_user = {row.Gebruiker_ID: row for row in ack_rows}

        ontvang = 0
        kennis = 0
        for person in people:
            ack = ack_by_user.get(person["gebruiker_id"])
            if emergency is None:
                status = "GEEN_AKTIEWE_NOODGEVAL"
                ontvang_op = None
                kennis_op = None
            elif ack is None:
                status = "WAG_OP_ONTVANG"
                ontvang_op = None
                kennis_op = None
            else:
                ontvang += 1
                ontvang_op = _iso(ack.NOK_Ontvang_Op)
                kennis_op = _iso(ack.NOK_Kennis_Geneem_Op)
                if ack.NOK_Status == "KENNIS_GENEEM":
                    kennis += 1
                    status = "KENNIS_GENEEM"
                else:
                    status = "ONTVANG"

            person["noodgeval_status"] = status
            person["ontvang_op"] = ontvang_op
            person["kennis_geneem_op"] = kennis_op

        # Name order is useful for the later mobile search/list screen.
        people.sort(key=lambda p: (p["van"].casefold(), p["naam"].casefold(), p["gebruiker_id"]))

        active_payload = None
        if emergency is not None:
            active_payload = {
                "noodgeval_id": emergency.Noodgeval_ID,
                "tipe": emergency.NOO_Tipe,
                "titel": emergency.NOO_Titel,
                "boodskap": emergency.NOO_Boodskap,
                "status": emergency.NOO_Status,
                "boodskap_id": emergency.NOO_Boodskap_ID,
                "begin_op": _iso(emergency.NOO_Begin_Op),
                "mqtt_gestuur_op": _iso(emergency.NOO_Mqtt_Gestuur_Op),
            }

        total = len(people)
        return {
            "tipe": "NOODGEVAL_LIVE_SNAPSHOT",
            "server_tyd": datetime.now(timezone.utc).isoformat(),
            "kampus": {
                "kampus_id": kampus.Kampus_ID,
                "naam": kampus.KAM_Naam,
            },
            "aktiewe_noodgeval": active_payload,
            "stats": {
                "op_kampus": total,
                "ontvang": ontvang,
                "kennis_geneem": kennis,
                "wag_op_ontvang": max(total - ontvang, 0) if emergency is not None else 0,
                "wag_op_kennisname": max(ontvang - kennis, 0) if emergency is not None else 0,
            },
            "mense_op_kampus": people,
        }
    finally:
        db.close()


def _snapshot_signature(snapshot: dict[str, Any]) -> str:
    """Ignore server_tyd when deciding whether visible dashboard data changed."""
    comparable = dict(snapshot)
    comparable.pop("server_tyd", None)
    return json.dumps(comparable, sort_keys=True, ensure_ascii=False, default=str)


@router.websocket("/ws/kampus/{kampus_id}")
async def noodgeval_live_ws(websocket: WebSocket, kampus_id: int):
    # Authenticate and authorise before accepting the socket.
    db = database.SessionLocal()
    try:
        user = _authenticate_ws(websocket, db)
        if user is None:
            await websocket.close(code=4401, reason="Ongeldige of ontbrekende token")
            return
        try:
            _require_sender_for_campus(db, user, kampus_id)
        except Exception:
            await websocket.close(code=4403, reason="Geen toegang tot hierdie kampus nie")
            return
    finally:
        db.close()

    await websocket.accept()

    last_signature: str | None = None
    try:
        while True:
            snapshot = await asyncio.to_thread(_build_snapshot, kampus_id)
            signature = _snapshot_signature(snapshot)
            if signature != last_signature:
                await websocket.send_json(snapshot)
                last_signature = signature
            await asyncio.sleep(WS_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        # If the socket is still writable, provide a final machine-readable error.
        try:
            await websocket.send_json(
                {
                    "tipe": "FOUT",
                    "kampus_id": kampus_id,
                    "fout": f"WebSocket feed fout: {exc}",
                }
            )
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
