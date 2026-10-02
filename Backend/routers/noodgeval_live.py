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
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import and_, func, text
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


def _internal_event_context(
    db: Session,
    kampus_id: int,
    people_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """Merk MOON-gebruikers wat tans as interne Event-gaste kwalifiseer.

    Hulle word NIE 'n tweede keer by die noodlys gevoeg nie. Hulle gewone
    kampus-IN log hou hulle reeds in die mense-op-kampus lys; hierdie helper
    voeg net Event-konteks by.
    """
    if not people_ids:
        return {}

    now = datetime.utcnow()
    events = (
        db.query(models.Funksie)
        .filter(
            models.Funksie.Kampus_ID == kampus_id,
            models.Funksie.FUN_Is_Aktief.is_(True),
            models.Funksie.FUN_Status == "AKTIEF",
            models.Funksie.FUN_Begin_Tyd <= now + timedelta(hours=4),
            models.Funksie.FUN_Eind_Tyd >= now - timedelta(hours=6),
        )
        .all()
    )
    if not events:
        return {}

    event_by_id = {event.Funksie_ID: event for event in events}
    rows = (
        db.query(models.FunksieRSVP)
        .filter(
            models.FunksieRSVP.Funksie_ID.in_(list(event_by_id)),
            models.FunksieRSVP.Gebruiker_ID.in_(people_ids),
            models.FunksieRSVP.RSVP_Status == "GAAN",
        )
        .all()
    )

    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        event = event_by_id.get(row.Funksie_ID)
        if event is None:
            continue
        bucket = result.setdefault(
            int(row.Gebruiker_ID),
            {"event_ids": [], "event_names": []},
        )
        bucket["event_ids"].append(int(event.Funksie_ID))
        bucket["event_names"].append(event.FUN_Naam)
    return result


def _external_event_guests_in_campus(db: Session, kampus_id: int) -> list[dict[str, Any]]:
    """Eksterne Event-gaste wie se jongste Event-heklog tans IN is."""
    latest_access = (
        db.query(
            models.FunksiePubliekToegang.Publiek_RSVP_ID.label("publiek_rsvp_id"),
            func.max(models.FunksiePubliekToegang.Toegang_ID).label("latest_toegang_id"),
        )
        .filter(models.FunksiePubliekToegang.Kampus_ID == kampus_id)
        .group_by(models.FunksiePubliekToegang.Publiek_RSVP_ID)
        .subquery()
    )

    rows = (
        db.query(
            models.FunksiePubliekToegang,
            models.FunksiePubliekRSVP,
            models.Funksie,
        )
        .join(
            latest_access,
            models.FunksiePubliekToegang.Toegang_ID == latest_access.c.latest_toegang_id,
        )
        .join(
            models.FunksiePubliekRSVP,
            models.FunksiePubliekRSVP.Publiek_RSVP_ID
            == models.FunksiePubliekToegang.Publiek_RSVP_ID,
        )
        .join(
            models.Funksie,
            models.Funksie.Funksie_ID == models.FunksiePubliekRSVP.Funksie_ID,
        )
        .filter(
            models.FunksiePubliekToegang.Kampus_ID == kampus_id,
            models.FunksiePubliekToegang.Rigting == "IN",
            models.FunksiePubliekRSVP.RSVP_Status == "GAAN",
            models.Funksie.Kampus_ID == kampus_id,

            # 'n Eksterne gas mag slegs deel van die noodlys wees terwyl
            # sy/haar Event self nog aktief is en binne die Event-hekvenster val.
            # Dit beskerm ook teen ou legacy RSVP's wat voor hierdie fix as
            # "GAAN" agtergebly het nadat 'n Event gekanselleer is.
            models.Funksie.FUN_Is_Aktief.is_(True),
            models.Funksie.FUN_Status == "AKTIEF",
            models.Funksie.FUN_Begin_Tyd <= datetime.utcnow() + timedelta(hours=4),
            models.Funksie.FUN_Eind_Tyd >= datetime.utcnow() - timedelta(hours=6),
        )
        .all()
    )

    guests: list[dict[str, Any]] = []
    for access, rsvp, event in rows:
        guests.append(
            {
                "persoon_sleutel": f"event_external:{rsvp.Publiek_RSVP_ID}",
                "gebruiker_id": None,
                "publiek_rsvp_id": int(rsvp.Publiek_RSVP_ID),
                "naam": rsvp.Naam,
                "van": rsvp.Van,
                "volle_naam": f"{rsvp.Naam} {rsvp.Van}".strip(),
                "tipe": "Event-gas (ekstern)",
                "nommer": rsvp.Selfoon or "",
                "foto_url": None,
                "laaste_hek_scan": _iso(access.Tydstempel),
                "laaste_hek_metode": access.Metode,
                "event_gas": True,
                "event_gas_tipe": "EKSTERN",
                "event_ids": [int(event.Funksie_ID)],
                "event_names": [event.FUN_Naam],
                "event_name": event.FUN_Naam,
            }
        )
    return guests


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
            payload = _persoon_payload(user, gate_log)
            payload["persoon_sleutel"] = f"user:{user.Gebruiker_ID}"
            payload["publiek_rsvp_id"] = None
            payload["event_gas"] = False
            payload["event_gas_tipe"] = None
            payload["event_ids"] = []
            payload["event_names"] = []
            payload["event_name"] = None
            people.append(payload)

        # Interne Event-gaste is reeds gewone MOON-gebruikers in die lys.
        internal_context = _internal_event_context(db, kampus_id, people_ids)
        internal_event_guest_count = 0
        for person in people:
            context = internal_context.get(int(person["gebruiker_id"]))
            if context is None:
                continue
            internal_event_guest_count += 1
            person["event_gas"] = True
            person["event_gas_tipe"] = "INTERN"
            person["event_ids"] = context["event_ids"]
            person["event_names"] = context["event_names"]
            person["event_name"] = " / ".join(context["event_names"])

        # Eksterne Event-gaste het geen Gebruiker_ID nie en moet apart bygevoeg word.
        external_guests = _external_event_guests_in_campus(db, kampus_id)
        external_event_guest_count = len(external_guests)
        people.extend(external_guests)

        # Slegs MOON-gebruikers kan telefoon ONTVANG / KENNIS_GENEEM hê.
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

        # Manual opsigter roll-call for normal MOON users.
        control_by_user: dict[int, dict[str, Any]] = {}
        control_by_guest: dict[int, dict[str, Any]] = {}
        if emergency is not None:
            control_rows = db.execute(
                text("""
                    SELECT
                        nk.\"Gebruiker_ID\",
                        nk.\"Gemerk_Deur_ID\",
                        nk.\"NKK_Status\",
                        nk.\"NKK_Gemerk_Op\"
                    FROM noodgeval_kontrole nk
                    WHERE nk.\"Noodgeval_ID\" = :noodgeval_id
                """),
                {"noodgeval_id": emergency.Noodgeval_ID},
            ).mappings().all()
            control_by_user = {int(row["Gebruiker_ID"]): dict(row) for row in control_rows}

            guest_control_rows = db.execute(
                text("""
                    SELECT
                        ngk.\"Publiek_RSVP_ID\",
                        ngk.\"Gemerk_Deur_ID\",
                        ngk.\"NKK_Status\",
                        ngk.\"NKK_Gemerk_Op\"
                    FROM noodgeval_event_gas_kontrole ngk
                    WHERE ngk.\"Noodgeval_ID\" = :noodgeval_id
                """),
                {"noodgeval_id": emergency.Noodgeval_ID},
            ).mappings().all()
            control_by_guest = {
                int(row["Publiek_RSVP_ID"]): dict(row) for row in guest_control_rows
            }

        ontvang = 0
        kennis = 0
        daar_count = 0
        nie_daar_count = 0
        for person in people:
            gebruiker_id = person.get("gebruiker_id")
            publiek_rsvp_id = person.get("publiek_rsvp_id")

            if gebruiker_id is None:
                # Eksterne Event-gaste het nie die MOON app / device ACK nie.
                status = "GEEN_TOESTEL" if emergency is not None else "GEEN_AKTIEWE_NOODGEVAL"
                ontvang_op = None
                kennis_op = None
                control = (
                    control_by_guest.get(int(publiek_rsvp_id))
                    if publiek_rsvp_id is not None
                    else None
                )
            else:
                ack = ack_by_user.get(int(gebruiker_id))
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
                control = control_by_user.get(int(gebruiker_id))

            if emergency is None:
                control_status = "GEEN_AKTIEWE_NOODGEVAL"
                control_marked_at = None
                control_marked_by = None
            elif control is None:
                control_status = "WAG"
                control_marked_at = None
                control_marked_by = None
            else:
                control_status = str(control["NKK_Status"])
                control_marked_at = _iso(control["NKK_Gemerk_Op"])
                control_marked_by = control["Gemerk_Deur_ID"]
                if control_status == "DAAR":
                    daar_count += 1
                elif control_status == "NIE_DAAR":
                    nie_daar_count += 1

            person["noodgeval_status"] = status
            person["ontvang_op"] = ontvang_op
            person["kennis_geneem_op"] = kennis_op
            person["kontrole_status"] = control_status
            person["kontrole_gemerk_op"] = control_marked_at
            person["kontrole_gemerk_deur_id"] = control_marked_by

        # Name order is useful for mobile search/list screen.
        people.sort(
            key=lambda p: (
                (p.get("van") or "").casefold(),
                (p.get("naam") or "").casefold(),
                int(p.get("gebruiker_id") or 0),
                int(p.get("publiek_rsvp_id") or 0),
            )
        )

        # UI-ready sections:
        # - DAAR disappears from the working list.
        # - NIE_DAAR moves to the bottom list.
        # - WAG stays in the main working list.
        wag_vir_kontrole = (
            [p for p in people if p["kontrole_status"] == "WAG"]
            if emergency is not None
            else []
        )
        nie_daar_nie = (
            [p for p in people if p["kontrole_status"] == "NIE_DAAR"]
            if emergency is not None
            else []
        )
        nie_daar_nie.sort(
            key=lambda p: p.get("kontrole_gemerk_op") or "",
            reverse=True,
        )

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
        device_people_total = len(people_ids)
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
                # Eksterne Event-gaste het geen device ACK nie en mag dus nie
                # hierdie twee telefoon-statistieke kunsmatig verhoog nie.
                "wag_op_ontvang": (
                    max(device_people_total - ontvang, 0)
                    if emergency is not None
                    else 0
                ),
                "wag_op_kennisname": (
                    max(ontvang - kennis, 0) if emergency is not None else 0
                ),
                "wag_vir_kontrole": len(wag_vir_kontrole) if emergency is not None else 0,
                "daar": daar_count if emergency is not None else 0,
                "nie_daar": nie_daar_count if emergency is not None else 0,
                "event_gaste": internal_event_guest_count + external_event_guest_count,
                "event_gaste_intern": internal_event_guest_count,
                "event_gaste_ekstern": external_event_guest_count,
            },
            "mense_op_kampus": people,
            "wag_vir_kontrole": wag_vir_kontrole,
            "nie_daar_nie": nie_daar_nie,
        }
    finally:
        db.close()

def _snapshot_signature(snapshot: dict[str, Any]) -> str:
    """Ignore server_tyd when deciding whether visible dashboard data changed."""
    comparable = dict(snapshot)
    comparable.pop("server_tyd", None)
    return json.dumps(comparable, sort_keys=True, ensure_ascii=False, default=str)


def _latest_external_guest_gate_log(
    db: Session,
    publiek_rsvp_id: int,
    kampus_id: int,
) -> models.FunksiePubliekToegang | None:
    return (
        db.query(models.FunksiePubliekToegang)
        .filter(
            models.FunksiePubliekToegang.Publiek_RSVP_ID == publiek_rsvp_id,
            models.FunksiePubliekToegang.Kampus_ID == kampus_id,
            models.FunksiePubliekToegang.Rigting.in_(["IN", "UIT"]),
        )
        .order_by(
            models.FunksiePubliekToegang.Tydstempel.desc(),
            models.FunksiePubliekToegang.Toegang_ID.desc(),
        )
        .first()
    )


@router.post("/{noodgeval_id}/event-gas/{publiek_rsvp_id}/kontrole/{action}")
def event_gas_kontrole(
    noodgeval_id: int,
    publiek_rsvp_id: int,
    action: str,
    db: Session = Depends(database.get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
):
    emergency = (
        db.query(models.Noodgeval)
        .filter(models.Noodgeval.Noodgeval_ID == noodgeval_id)
        .first()
    )
    if emergency is None:
        raise HTTPException(status_code=404, detail="Noodgeval nie gevind nie")
    if emergency.NOO_Status != "AKTIEF":
        raise HTTPException(status_code=409, detail="Hierdie noodgeval is nie meer aktief nie")

    _require_sender_for_campus(db, current_user, emergency.Kampus_ID)

    rsvp = (
        db.query(models.FunksiePubliekRSVP)
        .filter(models.FunksiePubliekRSVP.Publiek_RSVP_ID == publiek_rsvp_id)
        .first()
    )
    if rsvp is None:
        raise HTTPException(status_code=404, detail="Eksterne Event-gas nie gevind nie")

    event = (
        db.query(models.Funksie)
        .filter(models.Funksie.Funksie_ID == rsvp.Funksie_ID)
        .first()
    )
    if event is None or event.Kampus_ID != emergency.Kampus_ID:
        raise HTTPException(status_code=403, detail="Hierdie Event-gas behoort nie aan dié kampus nie")

    latest = _latest_external_guest_gate_log(db, publiek_rsvp_id, emergency.Kampus_ID)
    if latest is None or latest.Rigting != "IN":
        raise HTTPException(
            status_code=409,
            detail="Hierdie Event-gas is nie meer as IN op hierdie kampus aangeteken nie",
        )

    clean_action = (action or "").strip().lower()
    if clean_action == "herstel":
        db.execute(
            text("""
                DELETE FROM noodgeval_event_gas_kontrole
                WHERE \"Noodgeval_ID\" = :noodgeval_id
                  AND \"Publiek_RSVP_ID\" = :publiek_rsvp_id
            """),
            {
                "noodgeval_id": noodgeval_id,
                "publiek_rsvp_id": publiek_rsvp_id,
            },
        )
        db.commit()
        return {
            "sukses": True,
            "data": {
                "publiek_rsvp_id": publiek_rsvp_id,
                "kontrole_status": "WAG",
            },
            "fout": None,
        }

    status_map = {
        "daar": "DAAR",
        "nie-daar": "NIE_DAAR",
        "nie_daar": "NIE_DAAR",
    }
    status_value = status_map.get(clean_action)
    if status_value is None:
        raise HTTPException(status_code=400, detail="Kontrole-aksie moet daar, nie-daar of herstel wees")

    db.execute(
        text("""
            INSERT INTO noodgeval_event_gas_kontrole (
                \"Noodgeval_ID\",
                \"Publiek_RSVP_ID\",
                \"Gemerk_Deur_ID\",
                \"NKK_Status\",
                \"NKK_Gemerk_Op\",
                \"Gewysig_Op\"
            ) VALUES (
                :noodgeval_id,
                :publiek_rsvp_id,
                :gemerk_deur_id,
                :status,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (\"Noodgeval_ID\", \"Publiek_RSVP_ID\")
            DO UPDATE SET
                \"Gemerk_Deur_ID\" = EXCLUDED.\"Gemerk_Deur_ID\",
                \"NKK_Status\" = EXCLUDED.\"NKK_Status\",
                \"NKK_Gemerk_Op\" = CURRENT_TIMESTAMP,
                \"Gewysig_Op\" = CURRENT_TIMESTAMP
        """),
        {
            "noodgeval_id": noodgeval_id,
            "publiek_rsvp_id": publiek_rsvp_id,
            "gemerk_deur_id": current_user.Gebruiker_ID,
            "status": status_value,
        },
    )
    db.commit()
    return {
        "sukses": True,
        "data": {
            "publiek_rsvp_id": publiek_rsvp_id,
            "kontrole_status": status_value,
        },
        "fout": None,
    }


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
