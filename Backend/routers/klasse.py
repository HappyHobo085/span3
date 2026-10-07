"""Klas / Module / Groep rooster-roetes (admin-toewysing + CSV-invoer)."""

import csv
import io
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/rooster", tags=["Klas / Module / Groep"])


# --- CSV PARSER ---

def parse_lantiv_csv(inhoud: str) -> list[dict]:
    """Pars die Lantiv-uitvoer-CSV met sy ongewone dubbelaanhalingstekens.

    Lantiv draai elke RY in een paar buitenste aanhalingstekens, met die
    velde binne-in dubbel-aangehaal, bv.:
    '"10:00,""9:00"",""Maandag"",""GH117 A (50)"",""FBR 3"",""EBREK370"",""9:00"",""10:00\"\"\"'
    Die buitenste kwote maak die hele ry een veld vir die standaard csv-leser;
    ons lees dus elke ry as een veld en parse dit dan weer om die 8 kolomme te
    kry.  Gewone CSV-rye (sonder buitenste kwote) word direk gebruik.
    """
    reëls = []
    for lyn in inhoud.splitlines():
        lyn = lyn.strip()
        if not lyn:
            continue
        try:
            rye = list(csv.reader(io.StringIO(lyn)))
            if not rye or not rye[0]:
                continue
            kolomme = rye[0]
            # As die hele ry een veld is (Lantiv se buitenste kwote), parse
            # daardie veld weer om die werklike kolomme te ontsyfer.
            if len(kolomme) < 8:
                rye2 = list(csv.reader(io.StringIO(kolomme[0])))
                if rye2 and rye2[0] and len(rye2[0]) >= 8:
                    kolomme = rye2[0]
                else:
                    continue
        except Exception:
            continue
        # Slaan die kopreeks oor (Dag-kolom is die kolomnaam "Dag").
        if kolomme[2].strip().lower() == "dag":
            continue
        # Kolomme: End Time, Start Time, Dag, Lokaal, Groep, Module, From, To
        reëls.append({
            "dag": kolomme[2].strip(),
            "lokaal": kolomme[3].strip(),
            "groep": kolomme[4].strip(),
            "module": kolomme[5].strip(),
            "from": kolomme[6].strip(),
            "to": kolomme[7].strip(),
        })
    return reëls



def parse_moon_rooster_csv(inhoud: str) -> list[dict]:
    """Pars die nuwe MOON-roosterformaat met 'n gewone kop-ry.

    Vereiste kolomme:
    Rooster_ID, Dag, Begin_Tyd, Eind_Tyd, Module, Groep,
    Lokaal, Lokaal_Naam, Kampus, Kapasiteit.

    Die importer gebruik Lokaal_Naam + Kampus om direk teen MOON se
    ``lokasie``-tabel te match. ``Lokaal`` word as die bron-/roosterkode in
    KLA_Lokaal behou vir naspeurbaarheid en backwards compatibility.
    """
    leser = csv.DictReader(io.StringIO(inhoud))
    if not leser.fieldnames:
        raise HTTPException(status_code=400, detail="Die MOON-rooster CSV het geen kop-ry nie")

    vereis = {
        "Rooster_ID", "Dag", "Begin_Tyd", "Eind_Tyd", "Module",
        "Groep", "Lokaal", "Lokaal_Naam", "Kampus", "Kapasiteit",
    }
    ontbreek = sorted(vereis - set(leser.fieldnames))
    if ontbreek:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ongeldige MOON-roosterformaat. Ontbrekende kolomme: "
                + ", ".join(ontbreek)
            ),
        )