"""Regressietoets: die admin-blad stuur Rol_IDs (lys) sonder Rol_ID.

Die webwerf se "Skep Gebruiker"-venster (Webwerf/admin.js, submitNewUser)
stuur 'n multi-rol payload met slegs Rol_IDs. Die skema moes dit aanvaar,
maar Rol_ID (geërf van UserBase) was verpligtend — elke skep-versoek het
met 'n 422 gefaal voordat die roete-kode ooit geloop het.
"""

import models
import schemas


def _admin_blad_payload(rol_id):
    """Presies wat Webwerf/admin.js vir 'n nuwe Personeel-gebruiker stuur."""
    return {
        "GEB_Naam": "Toets",
        "GEB_Van": "Gebruiker",
        "GEB_Epos": "nuwe.gebruiker@voorbeeld.co.za",
        "GEB_Wagwoord": "Wagwoord1!",
        "Rol_IDs": [rol_id],
        "Is_Aktief": True,
        "GEB_ID_Nommer": "9999999999999",
    }


class TestSkepGebruikerMetRolIDs:
    def test_usercreate_aanvaar_rol_ids_sonder_rol_id(self, db, maak_gebruiker):
        admin = maak_gebruiker("Administrateur")
        user_in = schemas.UserCreate(**_admin_blad_payload(admin.Rol_ID))
        assert user_in.Rol_IDs == [admin.Rol_ID]
        assert user_in.Rol_ID is None

    def test_usercreate_aanvaar_ontbrekende_id_nommer(self, db, maak_gebruiker):
        # routers/gebruikers.py genereer self 'n ID-nommer as geen gegee is nie.
        admin = maak_gebruiker("Administrateur")
        payload = _admin_blad_payload(admin.Rol_ID)
        del payload["GEB_ID_Nommer"]
        user_in = schemas.UserCreate(**payload)
        assert user_in.GEB_ID_Nommer is None

    def test_skep_gebruiker_roete_met_slegs_rol_ids(self, db, maak_gebruiker):
        from routers import gebruikers

        admin = maak_gebruiker("Administrateur")
        personeel_rol = models.Rolle(ROL_Naam="Personeel")
        db.add(personeel_rol)
        db.flush()

        user_in = schemas.UserCreate(**_admin_blad_payload(personeel_rol.Rol_ID))
        resultaat = gebruikers.skep_gebruiker(
            user_in, db=db, current_user=admin, is_admin=True
        )

        assert resultaat.sukses is True
        assert resultaat.data["Rol_IDs"] == [personeel_rol.Rol_ID]
        assert resultaat.data["Rol_ID"] == personeel_rol.Rol_ID
