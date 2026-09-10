"""Outomatiese uitcheck — APScheduler agtergrondtaak."""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import and_

import database, models


def _kry_uitcheck_tydstip(db: Session) -> str:
    """Haal die uitcheck-tydstip uit instellings."""
    instelling = db.query(models.Instelling).filter(
        models.Instelling.Sleutel == 'auto_uitcheck_tydstip'
    ).first()
    return instelling.Waarde if instelling else '22:00'


def _vind_oop_sessies(db: Session) -> list[dict]:
    """Vind gebruikers met oop IN-sessies (IN sonder ooreenstemmende UIT).

    Geoptimaliseer: gebruik NOT EXISTS subquery in plaas van per-gebruiker queries.
    """
    # Vind IN-logte waar daar GEEN volgende UIT-log is nie
    # Dit is 'n korrekte anti-join patroon wat die N+1 probleem oplos
    uit_subq = (
        db.query(models.ToegangsLogs.Log_ID)
        .filter(
            models.ToegangsLogs.Gebruiker_ID == models.ToegangsLogs.Gebruiker_ID,
            models.ToegangsLogs.TOE_Rigting == "UIT",
            models.ToegangsLogs.TOE_Tydstempel > models.ToegangsLogs.TOE_Tydstempel,
        )
        .correlate(models.ToegangsLogs)
        .exists()
    )

    oop_logs = (
        db.query(models.ToegangsLogs)
        .filter(
            models.ToegangsLogs.TOE_Rigting == "IN",
            ~uit_subq,
        )
        .all()
    )

    return [
        {
            'Gebruiker_ID': log.Gebruiker_ID,
            'Lokasie_ID': log.Lokasie_ID,
            'NFC_Tags_ID': log.NFC_Tags_ID,
            'IN_Tydstempel': log.TOE_Tydstempel,
        }
        for log in oop_logs
    ]


def _is_koshuis_student(db: Session, gebruiker_ids: list[int]) -> set[int]:
    """Kyk watter gebruikers koshuisstudente is — een query vir almal."""
    if not gebruiker_ids:
        return set()
    rows = (
        db.query(models.Student.Gebruiker_ID)
        .filter(
            models.Student.Gebruiker_ID.in_(gebruiker_ids),
            models.Student.STU_Is_Koshuis == True,
        )
        .all()
    )
    return {row.Gebruiker_ID for row in rows}


def outo_uitcheck_job():
    """Hoof-taak: skep OUT-logte vir oop sessies buite koshuis."""
    db = database.SessionLocal()
    try:
        tydstip = datetime.now().strftime('%H:%M')

        gestelde_tydstip = _kry_uitcheck_tydstip(db)
        if tydstip != gestelde_tydstip:
            return

        oop_sessies = _vind_oop_sessies(db)
        if not oop_sessies:
            return

        # Haal koshuisstudente in een slag op (een query)
        alle_gebruiker_ids = list({s['Gebruiker_ID'] for s in oop_sessies})
        koshuis_ids = _is_koshuis_student(db, alle_gebruiker_ids)

        aantal_geskep = 0
        for sessie in oop_sessies:
            if sessie['Gebruiker_ID'] in koshuis_ids:
                continue

            nuwe_log = models.ToegangsLogs(
                Gebruiker_ID=sessie['Gebruiker_ID'],
                Lokasie_ID=sessie['Lokasie_ID'],
                NFC_Tags_ID=sessie['NFC_Tags_ID'],
                TOE_Rigting="UIT",
                TOE_Metode="HANDMATIG",
                TOE_Auto_Uitgecheck=True,
                TOE_Tydstempel=datetime.utcnow(),
            )
            db.add(nuwe_log)
            aantal_geskep += 1

        if aantal_geskep > 0:
            db.commit()
            print(f"[Auto-Uitcheck] {aantal_geskep} outomatiese UIT-logte geskep")

    except Exception as fout:
        db.rollback()
        print(f"[Auto-Uitcheck] Fout: {fout}")
    finally:
        db.close()


def maak_scheduler_aan() -> BackgroundScheduler:
    """Skep en begin die APScheduler met die uitcheck-taak."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        outo_uitcheck_job,
        'interval',
        minutes=1,
        id='auto_uitcheck',
        replace_existing=True,
    )
    scheduler.start()
    print("[Auto-Uitcheck] Scheduler gestart — loop elke minuut")
    return scheduler


def sluit_scheduler_af(scheduler: BackgroundScheduler):
    """Stop die scheduler by afsluiting."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Auto-Uitcheck] Scheduler gestop")
