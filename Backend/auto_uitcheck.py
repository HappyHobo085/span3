"""Outomatiese uitcheck — APScheduler agtergrondtaak."""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

import database, models


def _kry_uitcheck_tydstip(db: Session) -> str:
    """Haal die uitcheck-tydstip uit instellings."""
    instelling = db.query(models.Instelling).filter(
        models.Instelling.Sleutel == 'auto_uitcheck_tydstip'
    ).first()
    return instelling.Waarde if instelling else '22:00'


def _vind_oop_sessies(db: Session) -> list[dict]:
    """Vind gebruikers met oop IN-sessies (IN sonder ooreenstemmende UIT)."""
    # Kry alle IN-logte
    in_logs = db.query(models.ToegangsLogs).filter(
        models.ToegangsLogs.TOE_Rigting == "IN"
    ).all()

    oop_sessies = []
    for in_log in in_logs:
        # Kyk of daar 'n UIT-log is NA hierdie IN-log vir dieselfde gebruiker
        volgende_uit = db.query(models.ToegangsLogs).filter(
            models.ToegangsLogs.Gebruiker_ID == in_log.Gebruiker_ID,
            models.ToegangsLogs.TOE_Rigting == "UIT",
            models.ToegangsLogs.TOE_Tydstempel > in_log.TOE_Tydstempel
        ).first()

        if not volgende_uit:
            oop_sessies.append({
                'Gebruiker_ID': in_log.Gebruiker_ID,
                'Lokasie_ID': in_log.Lokasie_ID,
                'NFC_Tags_ID': in_log.NFC_Tags_ID,
                'IN_Tydstempel': in_log.TOE_Tydstempel,
            })

    return oop_sessies


def _is_koshuis_student(db: Session, gebruiker_id: int) -> bool:
    """Kyk of die gebruiker 'n koshuisstudent is."""
    student = db.query(models.Student).filter(
        models.Student.Gebruiker_ID == gebruiker_id
    ).first()
    return student is not None and student.STU_Is_Koshuis is True


def outo_uitcheck_job():
    """Hoof-taak: skep OUT-logte vir oop sessies buite koshuis."""
    db = database.SessionLocal()
    try:
        tydstip = datetime.now().strftime('%H:%M')

        gestelde_tydstip = _kry_uitcheck_tydstip(db)
        if tydstip != gestelde_tydstip:
            return

        oop_sessies = _vind_oop_sessies(db)

        aantal_geskep = 0
        for sessie in oop_sessies:
            if _is_koshuis_student(db, sessie['Gebruiker_ID']):
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
