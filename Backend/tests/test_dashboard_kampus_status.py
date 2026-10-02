"""Regressietoets: GET /dashboard het 500 (KeyError) gegee sodra die
gebruiker 'n QR-toegangslog gehad het, omdat die joined Row nie uitgepak
is voordat TOE_Rigting gelees is nie."""

from datetime import datetime, timedelta

import models
from routers import dashboard


def _maak_log(db, gebruiker, lokasie, rigting, metode, tyd):
    db.add(models.ToegangsLogs(
        Gebruiker_ID=gebruiker.Gebruiker_ID,
        Lokasie_ID=lokasie.Lokasie_ID,
        TOE_Rigting=rigting,
        TOE_Metode=metode,
        TOE_Tydstempel=tyd,
    ))
    db.flush()


def test_dashboard_wys_op_kampus_na_qr_inskandering(db, maak_gebruiker):
    gebruiker = maak_gebruiker("Student")
    hek = models.Lokasie(LOK_Naam="Hoofhek", LOK_Tipe="Ingang", Kampus_ID=1)
    db.add(hek)
    db.flush()

    _maak_log(db, gebruiker, hek, "IN", "QR", datetime.utcnow())

    resultaat = dashboard.kry_my_dashboard(current_user=gebruiker, db=db)

    assert resultaat["sukses"] is True
    assert resultaat["data"]["kampus_status"] == "OP_KAMPUS"
    assert resultaat["data"]["laaste_kampus"]["rigting"] == "IN"
    assert resultaat["data"]["laaste_kampus"]["lokasie"] == "Hoofhek"


def test_dashboard_wys_nie_op_kampus_na_qr_uitskandering(db, maak_gebruiker):
    gebruiker = maak_gebruiker("Student")
    hek = models.Lokasie(LOK_Naam="Hoofhek", LOK_Tipe="Ingang", Kampus_ID=1)
    db.add(hek)
    db.flush()

    nou = datetime.utcnow()
    _maak_log(db, gebruiker, hek, "IN", "QR", nou - timedelta(hours=1))
    _maak_log(db, gebruiker, hek, "UIT", "QR", nou)

    resultaat = dashboard.kry_my_dashboard(current_user=gebruiker, db=db)

    assert resultaat["data"]["kampus_status"] == "NIE_OP_KAMPUS"
    assert resultaat["data"]["laaste_kampus"]["rigting"] == "UIT"
