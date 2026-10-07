from datetime import datetime, timedelta

import models
from services import ml_service
from services.compatibiliteit_service import (
    DagSkedule,
    StudentSaamryData,
    bou_student_saamry_data_van_db,
    bereken_saamry_versoenbaarheid,
)


def _rol(db, naam):
    r = models.Rolle(ROL_Naam=naam)
    db.add(r)
    db.flush()
    return r


def _user(db, rol, idx, naam="Toets"):
    u = models.Gebruikers(
        GEB_Naam=naam,
        GEB_Van=f"User{idx}",
        GEB_ID_Nommer=f"90010150000{idx:02d}"[-13:],
        GEB_Epos=f"reco{idx}@example.com",
        GEB_Wagwoord="hash",
        Rol_ID=rol.Rol_ID,
        Is_Aktief=True,
    )
    db.add(u)
    db.flush()
    return u


def test_personeel_rooster_word_ingesluit(db):
    rol = _rol(db, "Personeel")
    gebruiker = _user(db, rol, 1, "Piet")
    db.add(models.Personeel(Gebruiker_ID=gebruiker.Gebruiker_ID, PER_Nommer="P001"))

    kampus = models.Kampus(KAM_Naam="Pretoria", KAM_Adres="Test")
    db.add(kampus)
    db.flush()
    lokaal = models.Lokasie(LOK_Naam="Klas 1", LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID)
    module = models.Module(MOD_Kode="REC101", MOD_Naam="Reco")
    db.add_all([lokaal, module])
    db.flush()
    klas = models.Klas(
        Module_ID=module.Module_ID,
        Lokasie_ID=lokaal.Lokasie_ID,
        KLA_Lokaal="K1",
        KLA_Dag="Maandag",
        KLA_Begin_Tyd="08:00",
        KLA_Eind_Tyd="10:00",
    )
    db.add(klas)
    db.flush()
    db.add(models.Personeel_Klas(Gebruiker_ID=gebruiker.Gebruiker_ID, Klas_ID=klas.Klas_ID))
    db.commit()
    db.expire_all()

    gebruiker = db.query(models.Gebruikers).filter_by(Gebruiker_ID=gebruiker.Gebruiker_ID).one()
    data = bou_student_saamry_data_van_db(db, gebruiker)

    assert data.skedule_per_dag["Maandag"].het_aktiwiteit is True
    assert data.skedule_per_dag["Maandag"].aankoms_minuut == 450  # 08:00 - mediaan 30 min
    assert data.skedule_per_dag["Maandag"].bron == "MEDIAAN"


def test_slegs_kampus_logs_en_sa_tyd_word_gebruik(db):
    rol = _rol(db, "Student")
    gebruiker = _user(db, rol, 2, "Anna")
    db.add(models.Student(Gebruiker_ID=gebruiker.Gebruiker_ID, STU_Nommer="S002", STU_Is_Koshuis=True))

    kampus = models.Kampus(KAM_Naam="Pretoria", KAM_Adres="Test")
    db.add(kampus)
    db.flush()
    hek = models.Lokasie(LOK_Naam="Hoofhek", LOK_Tipe="Kampus", Kampus_ID=kampus.Kampus_ID)
    koshuis = models.Lokasie(LOK_Naam="Koshuishek", LOK_Tipe="Koshuis", Kampus_ID=kampus.Kampus_ID)
    db.add_all([hek, koshuis])
    db.flush()

    # Drie Maandae: 06:00 UTC = 08:00 in Suid-Afrika. Koshuis-scans op 02:00 UTC
    # moet heeltemal geïgnoreer word deur die recommendation skedule.
    now = datetime.utcnow()
    this_monday = (now - timedelta(days=now.weekday())).replace(hour=6, minute=0, second=0, microsecond=0)
    for w in (0, 1, 2):
        campus_ts = this_monday - timedelta(weeks=w)
        dorm_ts = campus_ts.replace(hour=2)
        db.add(models.ToegangsLogs(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            Lokasie_ID=hek.Lokasie_ID,
            TOE_Tydstempel=campus_ts,
            TOE_Rigting="IN",
            TOE_Metode="NFC",
        ))
        db.add(models.ToegangsLogs(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            Lokasie_ID=koshuis.Lokasie_ID,
            TOE_Tydstempel=dorm_ts,
            TOE_Rigting="IN",
            TOE_Metode="NFC",
        ))
    db.commit()
    db.expire_all()

    gebruiker = db.query(models.Gebruikers).filter_by(Gebruiker_ID=gebruiker.Gebruiker_ID).one()
    data = bou_student_saamry_data_van_db(db, gebruiker)
    maandag = data.skedule_per_dag["Maandag"]

    assert maandag.bron == "LOGS"
    assert maandag.aankoms_minuut == 8 * 60
    assert maandag.aantal_monsters == 3


def test_enige_geskatte_gemeenskaplike_dag_dwing_40_betroubaarheid():
    a = StudentSaamryData(
        gebruiker_id=1,
        naam="A",
        van="Een",
        saamry_rol="BESTUURDER",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag={
            "Maandag": DagSkedule("Maandag", True, 480, 960, 10, 5, "LOGS"),
            "Dinsdag": DagSkedule("Dinsdag", True, 480, 960, 10, 5, "LOGS"),
        },
    )
    b = StudentSaamryData(
        gebruiker_id=2,
        naam="B",
        van="Twee",
        saamry_rol="PASSASIER",
        voorstad="Centurion",
        kampus_id=1,
        skedule_per_dag={
            "Maandag": DagSkedule("Maandag", True, 480, 960, 10, 5, "LOGS"),
            "Dinsdag": DagSkedule("Dinsdag", True, 480, 960, 0, 22.2, "MEDIAAN"),
        },
    )

    resultaat = bereken_saamry_versoenbaarheid(a, b)
    assert resultaat.faktore["betroubaarheid_telling"] == 40.0


def test_ml_load_failure_gebruik_navorsingsmediaan(monkeypatch):
    monkeypatch.setattr(ml_service, "_model_loaded", False)
    monkeypatch.setattr(ml_service, "_model", None)
    monkeypatch.setattr(ml_service, "_model_load_failed", True)
    offset, sigma, bron = ml_service.voorspel_aankomstyd_offset(480, "oos", "BEIDE", 0)
    assert offset == 30
    assert sigma == 22.2
    assert bron == "MEDIAAN"
