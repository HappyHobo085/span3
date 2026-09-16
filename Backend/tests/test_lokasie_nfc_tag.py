"""Toetse vir PUT /lokasies/{id}/nfc-tag en POST /klasse se UID-hantering."""

import pytest

import models
import auth


# --- Module-vlak fixture en helpers (gedeel deur albei toetsklasse) ---

@pytest.fixture()
def http_db(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def maak_gebruiker(db, rol_naam, n):
    rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == rol_naam).first()
    if not rol:
        rol = models.Rolle(ROL_Naam=rol_naam)
        db.add(rol)
        db.flush()
    gebruiker = models.Gebruikers(
        GEB_Naam="Toets",
        GEB_Van=f"Gebruiker{n}",
        GEB_ID_Nommer=f"900101000020{n}",
        GEB_Epos=f"lokasietag{n}@voorbeeld.co.za",
        GEB_Wagwoord="hashed",
        Rol_ID=rol.Rol_ID,
    )
    db.add(gebruiker)
    db.flush()
    return gebruiker


def bou_client(db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import database
    from routers.lokasie import router as lokasie_router

    app = FastAPI()
    app.include_router(lokasie_router)

    def _get_db_override():
        yield db

    app.dependency_overrides[database.get_db] = _get_db_override
    return TestClient(app)


def headers_vir(gebruiker):
    token = auth.create_access_token({"sub": str(gebruiker.Gebruiker_ID)})
    return {"Authorization": f"Bearer {token}"}


def maak_kampus(db):
    kampus = db.query(models.Kampus).first()
    if not kampus:
        kampus = models.Kampus(KAM_Naam="Hoofkampus")
        db.add(kampus)
        db.flush()
    return kampus


def maak_lokaal(db, naam, uid):
    kampus = maak_kampus(db)
    lokaal = models.Lokasie(LOK_Naam=naam, LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID)
    db.add(lokaal)
    db.flush()
    db.add(models.NFC_Tags(
        NFC_UID=uid, Lokasie_ID=lokaal.Lokasie_ID,
        NFC_Tipe="Lokasie", NFC_Is_Aktief=True,
    ))
    db.flush()
    return lokaal


class TestLokasieNFCTag:
    """HTTP-toetse met die lokasie-router en egte JWT-tokens."""

    def test_hernoem_tag_slaag(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 1)
        lokaal = maak_lokaal(http_db, "Bitterbessie", "OU-UID-1")
        client = bou_client(http_db)

        resp = client.put(
            f"/lokasies/{lokaal.Lokasie_ID}/nfc-tag",
            json={"NFC_UID": "  L4  "},
            headers=headers_vir(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["NFC_UID"] == "L4"
        tag = http_db.query(models.NFC_Tags).filter(
            models.NFC_Tags.Lokasie_ID == lokaal.Lokasie_ID
        ).first()
        assert tag.NFC_UID == "L4"

    def test_uid_botsing_gee_409(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 2)
        maak_lokaal(http_db, "Ander Lokaal", "L4")
        lokaal = maak_lokaal(http_db, "Bitterbessie", "OU-UID-2")
        client = bou_client(http_db)

        resp = client.put(
            f"/lokasies/{lokaal.Lokasie_ID}/nfc-tag",
            json={"NFC_UID": "L4"},
            headers=headers_vir(admin),
        )
        assert resp.status_code == 409

    def test_selfde_uid_is_geen_botsing_nie(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 3)
        lokaal = maak_lokaal(http_db, "Bitterbessie", "L4")
        client = bou_client(http_db)

        resp = client.put(
            f"/lokasies/{lokaal.Lokasie_ID}/nfc-tag",
            json={"NFC_UID": "L4"},
            headers=headers_vir(admin),
        )
        assert resp.status_code == 200

    def test_lee_uid_gee_400(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 4)
        lokaal = maak_lokaal(http_db, "Bitterbessie", "OU-UID-4")
        client = bou_client(http_db)

        resp = client.put(
            f"/lokasies/{lokaal.Lokasie_ID}/nfc-tag",
            json={"NFC_UID": "   "},
            headers=headers_vir(admin),
        )
        assert resp.status_code == 400

    def test_onbekende_lokasie_gee_404(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 5)
        client = bou_client(http_db)

        resp = client.put(
            "/lokasies/99999/nfc-tag",
            json={"NFC_UID": "L4"},
            headers=headers_vir(admin),
        )
        assert resp.status_code == 404

    def test_nie_admin_gee_403(self, http_db):
        student = maak_gebruiker(http_db, "Student", 6)
        lokaal = maak_lokaal(http_db, "Bitterbessie", "OU-UID-6")
        client = bou_client(http_db)

        resp = client.put(
            f"/lokasies/{lokaal.Lokasie_ID}/nfc-tag",
            json={"NFC_UID": "L4"},
            headers=headers_vir(student),
        )
        assert resp.status_code == 403
