"""Regressietoets: GET /opsigter/kampusse/{id}/besoekers het 500 gegee
sodra daar 'n toegelate besoeker was, omdat die joined Row van
(BesoekerUitnodiging, Gebruikers) nie uitgepak is voordat velde gelees
is nie (AttributeError: gasheer)."""

from datetime import datetime, timedelta

import models
from routers import wagte


def test_opsigter_besoekers_lys_toegelate_besoeker(db, maak_gebruiker):
    opsigter = maak_gebruiker("Kampus_Opsigter")
    gasheer = maak_gebruiker("Student")

    kampus = models.Kampus(KAM_Naam="Hoofkampus", KAM_Adres="Straat 1")
    db.add(kampus)
    db.flush()

    nou = datetime.utcnow()
    db.add(models.BesoekerUitnodiging(
        Gasheer_ID=gasheer.Gebruiker_ID,
        BES_Naam="Jane",
        BES_Van="Doe",
        BES_Selfoon_Nr="0812345678",
        BES_Rede="Besoek",
        BES_OTP="123456",
        BES_Status="TOEGELAAT",
        BES_Verval_Op=nou + timedelta(hours=4),
        BES_Besluit_Op=nou,
        Kampus_ID=kampus.Kampus_ID,
    ))
    db.flush()

    resultaat = wagte.opsigter_kampus_besoekers(
        kampus_id=kampus.Kampus_ID,
        db=db,
        current_user=opsigter,
        is_authorized=True,
    )

    assert resultaat.sukses is True
    assert len(resultaat.data) == 1
    besoeker = resultaat.data[0]
    assert besoeker["naam"] == "Jane"
    assert besoeker["gasheer_id"] == gasheer.Gebruiker_ID
    assert besoeker["gasheer_naam"] == f"{gasheer.GEB_Naam} {gasheer.GEB_Van}"
    assert besoeker["kampus_naam"] == "Hoofkampus"


def test_opsigter_besoekers_leeg_sonder_toegelate_besoekers(db, maak_gebruiker):
    opsigter = maak_gebruiker("Kampus_Opsigter")
    kampus = models.Kampus(KAM_Naam="Leë Kampus", KAM_Adres="Straat 2")
    db.add(kampus)
    db.flush()

    resultaat = wagte.opsigter_kampus_besoekers(
        kampus_id=kampus.Kampus_ID,
        db=db,
        current_user=opsigter,
        is_authorized=True,
    )

    assert resultaat.sukses is True
    assert resultaat.data == []
