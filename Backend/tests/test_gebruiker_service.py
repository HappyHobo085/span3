"""Toetse vir outogenerering van subrekord-nommers in gebruiker_service."""

import models
from services.gebruiker_service import get_user_role_ids, get_user_role_names, sync_gebruiker_subrekords


def kry_opsigter(db, gebruiker):
    return db.query(models.Kampus_Opsigter).filter(
        models.Kampus_Opsigter.Gebruiker_ID == gebruiker.Gebruiker_ID
    ).first()


def kry_wag(db, gebruiker):
    return db.query(models.Sekuriteit_Wag).filter(
        models.Sekuriteit_Wag.Gebruiker_ID == gebruiker.Gebruiker_ID
    ).first()


class TestKamoNommerOutogenerering:
    def test_opsigter_sonder_nommer_kry_outogenereerde_nommer(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Kampus_Opsigter")

        sync_gebruiker_subrekords(db, gebruiker, ["Kampus_Opsigter"], {}, creating=True)
        db.flush()

        opsigter = kry_opsigter(db, gebruiker)
        assert opsigter is not None
        assert opsigter.KAMO_Nommer == "KAMO0001"

    def test_volgende_opsigter_kry_opeenvolgende_nommer(self, db, maak_gebruiker):
        eerste = maak_gebruiker("Kampus_Opsigter")
        sync_gebruiker_subrekords(db, eerste, ["Kampus_Opsigter"], {}, creating=True)
        db.flush()

        tweede = maak_gebruiker("Kampus_Opsigter")
        sync_gebruiker_subrekords(db, tweede, ["Kampus_Opsigter"], {}, creating=True)
        db.flush()

        assert kry_opsigter(db, tweede).KAMO_Nommer == "KAMO0002"

    def test_eksplisiete_kamo_nommer_word_behou(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Kampus_Opsigter")

        sync_gebruiker_subrekords(
            db, gebruiker, ["Kampus_Opsigter"], {"KAMO_Nommer": "KAMO9000"}, creating=True
        )
        db.flush()

        assert kry_opsigter(db, gebruiker).KAMO_Nommer == "KAMO9000"


class TestVeelvuldigeRolle:
    def test_primere_rol_word_behou_saam_met_toegewysde_rolle(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Personeel")
        student_rol = models.Rolle(ROL_Naam="Student")
        db.add(student_rol)
        db.flush()
        db.add(models.GebruikersRolle(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            Rol_ID=student_rol.Rol_ID,
        ))
        db.flush()

        assert set(get_user_role_ids(db, gebruiker)) == {gebruiker.Rol_ID, student_rol.Rol_ID}
        assert set(get_user_role_names(db, gebruiker)) == {"Student", "Personeel"}


class TestSekNommerOutogenerering:
    def test_wag_sonder_nommer_kry_outogenereerde_nommer(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Sekuriteit_Wag")

        sync_gebruiker_subrekords(db, gebruiker, ["Sekuriteit_Wag"], {}, creating=True)
        db.flush()

        wag = kry_wag(db, gebruiker)
        assert wag is not None
        assert wag.SEK_Nommer == "SEK0001"

    def test_volgende_wag_kry_opeenvolgende_nommer(self, db, maak_gebruiker):
        eerste = maak_gebruiker("Sekuriteit_Wag")
        sync_gebruiker_subrekords(db, eerste, ["Sekuriteit_Wag"], {}, creating=True)
        db.flush()

        tweede = maak_gebruiker("Sekuriteit_Wag")
        sync_gebruiker_subrekords(db, tweede, ["Sekuriteit_Wag"], {}, creating=True)
        db.flush()

        assert kry_wag(db, tweede).SEK_Nommer == "SEK0002"

    def test_eksplisiete_sek_nommer_word_behou(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Sekuriteit_Wag")

        sync_gebruiker_subrekords(
            db, gebruiker, ["Sekuriteit_Wag"], {"SEK_Nommer": "SEK9000"}, creating=True
        )
        db.flush()

        assert kry_wag(db, gebruiker).SEK_Nommer == "SEK9000"


class TestPerNommerOutogenerering:
    """Bestaande gedrag — regressiewag vir die refaktorering na 'n gedeelde helper."""

    def test_personeel_sonder_nommer_kry_outogenereerde_nommer(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Personeel")

        sync_gebruiker_subrekords(db, gebruiker, ["Personeel"], {}, creating=True)
        db.flush()

        personeel = db.query(models.Personeel).filter(
            models.Personeel.Gebruiker_ID == gebruiker.Gebruiker_ID
        ).first()
        assert personeel is not None
        assert personeel.PER_Nommer == "PER0001"
