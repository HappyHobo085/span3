"""Outomatiese kampus-uitcheck — APScheduler agtergrondtaak.

Skep een outomatiese UIT-log vir 'n nie-koshuisstudent wie se jongste
kampushek-status steeds IN is wanneer die ingestelde uitcheck-tyd bereik word.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session, aliased

import database, models


_SA_TZ = ZoneInfo("Africa/Johannesburg")


def _kry_uitcheck_tydstip(db: Session) -> str:
    """Haal die uitcheck-tydstip uit instellings."""
    instelling = db.query(models.Instelling).filter(
        models.Instelling.Sleutel == "auto_uitcheck_tydstip"
    ).first()
    return instelling.Waarde.strip() if instelling and instelling.Waarde else "22:00"


def _vind_oop_sessies(db: Session) -> list[dict]:
    """Vind nie-koshuisstudente met 'n oop kampus-IN-sessie.

    'n Sessie is oop wanneer daar ná die IN-log geen latere kampus-UIT-log vir
    dieselfde gebruiker bestaan nie. Slegs lokasies met LOK_Tipe='Kampus' tel,
    sodat klaskamer-NFC skanderings nooit deur hierdie taak geraak word nie.

    As 'n gebruiker om enige rede meer as een IN sonder 'n latere UIT het,
    gebruik ons net die jongste IN sodat hoogstens een outo-UIT geskep word.
    """
    in_log = aliased(models.ToegangsLogs)
    uit_log = aliased(models.ToegangsLogs)
    in_lokasie = aliased(models.Lokasie)
    uit_lokasie = aliased(models.Lokasie)

    latere_kampus_uit_bestaan = (
        db.query(uit_log.Log_ID)
        .join(uit_lokasie, uit_lokasie.Lokasie_ID == uit_log.Lokasie_ID)
        .filter(
            uit_log.Gebruiker_ID == in_log.Gebruiker_ID,
            uit_log.TOE_Rigting == "UIT",
            uit_log.TOE_Tydstempel > in_log.TOE_Tydstempel,
            uit_lokasie.LOK_Tipe == "Kampus",
        )
        .correlate(in_log)
        .exists()
    )

    oop_logs = (
        db.query(in_log)
        .join(in_lokasie, in_lokasie.Lokasie_ID == in_log.Lokasie_ID)
        .join(models.Student, models.Student.Gebruiker_ID == in_log.Gebruiker_ID)
        .filter(
            in_log.TOE_Rigting == "IN",
            in_lokasie.LOK_Tipe == "Kampus",
            models.Student.STU_Is_Koshuis == False,  # noqa: E712
            ~latere_kampus_uit_bestaan,
        )
        .order_by(in_log.TOE_Tydstempel.desc(), in_log.Log_ID.desc())
        .all()
    )

    # Een oop sessie per student: die jongste kampus-IN.
    jongste_per_gebruiker: dict[int, object] = {}
    for log in oop_logs:
        if log.Gebruiker_ID not in jongste_per_gebruiker:
            jongste_per_gebruiker[log.Gebruiker_ID] = log

    return [
        {
            "Gebruiker_ID": log.Gebruiker_ID,
            "Lokasie_ID": log.Lokasie_ID,
            "NFC_Tags_ID": log.NFC_Tags_ID,
            "IN_Tydstempel": log.TOE_Tydstempel,
        }
        for log in jongste_per_gebruiker.values()
    ]


def outo_uitcheck_job():
    """Skep OUT-logte vir oop kampus-sessies van nie-koshuisstudente."""
    db = database.SessionLocal()
    try:
        nou_sa = datetime.now(_SA_TZ)
        huidige_tyd = nou_sa.strftime("%H:%M")
        gestelde_tyd = _kry_uitcheck_tydstip(db)

        if huidige_tyd != gestelde_tyd:
            return

        oop_sessies = _vind_oop_sessies(db)
        if not oop_sessies:
            print(f"[Auto-Uitcheck] {huidige_tyd} — geen oop kampus-sessies nie")
            return

        aantal_geskep = 0
        nou_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        for sessie in oop_sessies:
            nuwe_log = models.ToegangsLogs(
                Gebruiker_ID=sessie["Gebruiker_ID"],
                Lokasie_ID=sessie["Lokasie_ID"],
                NFC_Tags_ID=sessie["NFC_Tags_ID"],
                TOE_Rigting="UIT",
                TOE_Metode="HANDMATIG",
                TOE_Auto_Uitgecheck=True,
                TOE_Tydstempel=nou_utc,
            )
            db.add(nuwe_log)
            aantal_geskep += 1

        if aantal_geskep:
            db.commit()
            print(
                f"[Auto-Uitcheck] {aantal_geskep} student(e) om "
                f"{huidige_tyd} SA-tyd outomaties uitgecheck"
            )

    except Exception as fout:
        db.rollback()
        print(f"[Auto-Uitcheck] Fout: {fout}")
    finally:
        db.close()


def maak_scheduler_aan() -> BackgroundScheduler:
    """Skep en begin die APScheduler met die uitcheck-taak."""
    scheduler = BackgroundScheduler(timezone=_SA_TZ)
    scheduler.add_job(
        outo_uitcheck_job,
        "interval",
        minutes=1,
        id="auto_uitcheck",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    print(
    "[Auto-Uitcheck] Scheduler gestart — loop elke minuut (Africa/Johannesburg)",
    flush=True,
    )
    return scheduler


def sluit_scheduler_af(scheduler: BackgroundScheduler):
    """Stop die scheduler by afsluiting."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Auto-Uitcheck] Scheduler gestop")
