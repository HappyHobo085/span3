"""Toetse vir die Excel-bywoningsverslag (services/verslag_service.py)."""

import io
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from openpyxl import load_workbook

import models
from services.verslag_service import genereer_verslag

# 'n Maandag in SA-tyd; 10:00 UTC == 12:00 SA
NOU = datetime(2026, 10, 5, 10, 0)
VAN = date(2026, 9, 28)
TOT = date(2026, 10, 5)


@pytest.fixture()
def opstelling(db, maak_gebruiker):
    k1 = models.Kampus(KAM_Naam="Hoofkampus")
    k2 = models.Kampus(KAM_Naam="Ander Kampus")
    db.add_all([k1, k2])
    db.flush()
    hek1 = models.Lokasie(LOK_Naam="Hek 1", LOK_Tipe="Hek", Kampus_ID=k1.Kampus_ID)
    lokaal = models.Lokasie(LOK_Naam="GH117", LOK_Tipe="Klaskamer", Kampus_ID=k1.Kampus_ID)
    hek2 = models.Lokasie(LOK_Naam="Hek 2", LOK_Tipe="Hek", Kampus_ID=k2.Kampus_ID)
    db.add_all([hek1, lokaal, hek2])
    db.flush()

    admin = maak_gebruiker("Administrateur")
    dosent = maak_gebruiker("Personeel")
    db.add(models.Personeel(Gebruiker_ID=dosent.Gebruiker_ID, PER_Nommer="P001", PER_Departement="IT"))
    opsigter = maak_gebruiker("Kampus_Opsigter")
    db.add(models.Kampus_Opsigter(Gebruiker_ID=opsigter.Gebruiker_ID, KAMO_Nommer="K001", Kampus_ID=k1.Kampus_ID))

    s_in_klas = maak_gebruiker("Student")
    s_ander = maak_gebruiker("Student")
    s_kampus2 = maak_gebruiker("Student")
    for i, s in enumerate([s_in_klas, s_ander, s_kampus2], start=1):
        db.add(models.Student(Gebruiker_ID=s.Gebruiker_ID, STU_Nommer=f"S00{i}"))

    module = models.Module(MOD_Kode="ITRW311", MOD_Naam="Inligtingstelsels")
    db.add(module)
    db.flush()
    klas = models.Klas(
        Module_ID=module.Module_ID, Lokasie_ID=lokaal.Lokasie_ID, KLA_Lokaal="GH117",
        KLA_Dag="Maandag", KLA_Begin_Tyd="08:00", KLA_Eind_Tyd="09:00",
    )
    db.add(klas)
    db.flush()
    db.add(models.Student_Klas(Gebruiker_ID=s_in_klas.Gebruiker_ID, Klas_ID=klas.Klas_ID))
    db.add(models.Student_Klas(Gebruiker_ID=s_ander.Gebruiker_ID, Klas_ID=klas.Klas_ID))
    db.add(models.Personeel_Klas(Gebruiker_ID=dosent.Gebruiker_ID, Klas_ID=klas.Klas_ID))

    def log(g, lok, tyd, rigting="IN"):
        db.add(models.ToegangsLogs(
            Gebruiker_ID=g.Gebruiker_ID, Lokasie_ID=lok.Lokasie_ID,
            TOE_Tydstempel=tyd, TOE_Rigting=rigting, TOE_Metode="NFC",
        ))

    # Maandag 28 Sep: s_in_klas kom kampus toe en woon klas by (08:15 SA = 06:15 UTC)
    log(s_in_klas, hek1, datetime(2026, 9, 28, 5, 30))
    log(s_in_klas, lokaal, datetime(2026, 9, 28, 6, 15))
    log(s_in_klas, hek1, datetime(2026, 9, 28, 14, 0), "UIT")
    # Vandag (Maandag 5 Okt): s_in_klas is op kampus, maar mis die klas
    log(s_in_klas, hek1, datetime(2026, 10, 5, 7, 30))
    log(dosent, hek1, datetime(2026, 10, 5, 5, 0))
    # Student op die ander kampus
    log(s_kampus2, hek2, datetime(2026, 10, 1, 6, 0))
    db.commit()
    return {
        "admin": admin, "dosent": dosent, "opsigter": opsigter,
        "s_in_klas": s_in_klas, "s_ander": s_ander, "s_kampus2": s_kampus2,
    }


def _laai(inhoud: bytes):
    return load_workbook(io.BytesIO(inhoud))


def _kolom(ws, kop):
    koppe = [c.value for c in ws[1]]
    i = koppe.index(kop)
    return [r[i] for r in ws.iter_rows(min_row=2, values_only=True)]


def _ry_vir(ws, naam):
    koppe = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if naam in r:
            return dict(zip(koppe, r))
    return None


def _naam(g):
    return f"{g.GEB_Naam} {g.GEB_Van}"


def test_admin_sien_alles(db, opstelling):
    inhoud, lêernaam = genereer_verslag(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU)
    assert lêernaam == "moon_bywoning_20260928_20261005.xlsx"
    wb = _laai(inhoud)
    assert wb.sheetnames == [
        "Opsomming", "Huidige Status", "Studente", "Personeel",
        "Daaglikse Bywoning", "Klasbywoning", "Klasregister", "Toegangslogs",
    ]
    studente = _kolom(wb["Studente"], "Naam")
    assert _naam(opstelling["s_kampus2"]) in studente
    assert len(_kolom(wb["Toegangslogs"], "Tyd")) == 6

    status = _ry_vir(wb["Huidige Status"], _naam(opstelling["s_in_klas"]))
    assert status["Huidige status"] == "Op kampus (IN)"

    # Twee Maandag-klasperiodes; die eerste bygewoon, die tweede gemis.
    klasbywoning = wb["Klasbywoning"]
    assert _kolom(klasbywoning, "Teenwoordig")[:2] == [1, 0]
    student = _ry_vir(wb["Studente"], _naam(opstelling["s_in_klas"]))
    assert (student["Klasse bygewoon"], student["Klasse geskeduleer"]) == (1, 2)
    assert student["Dae op kampus"] == 2

    personeel = _ry_vir(wb["Personeel"], _naam(opstelling["dosent"]))
    assert personeel["Gem. aankoms"] == "07:00"


def test_opsigter_sien_net_eie_kampus(db, opstelling):
    wb = _laai(genereer_verslag(db, opstelling["opsigter"], ["Kampus_Opsigter"], VAN, TOT, nou=NOU)[0])
    name = _kolom(wb["Huidige Status"], "Naam")
    assert _naam(opstelling["s_kampus2"]) not in name
    assert _naam(opstelling["s_in_klas"]) in name
    assert all(k == "Hoofkampus" for k in _kolom(wb["Toegangslogs"], "Kampus"))
    assert wb["Opsomming"]["B3"].value == "Kampus: Hoofkampus"


def test_personeel_sien_net_eie_klas_studente(db, opstelling):
    wb = _laai(genereer_verslag(db, opstelling["dosent"], ["Personeel"], VAN, TOT, nou=NOU)[0])
    assert "Toegangslogs" not in wb.sheetnames
    assert "Personeel" not in wb.sheetnames
    name = set(_kolom(wb["Studente"], "Naam"))
    assert name == {_naam(opstelling["s_in_klas"]), _naam(opstelling["s_ander"])}
    register = list(wb["Klasregister"].iter_rows(min_row=2, values_only=True))
    assert len(register) == 4  # 2 periodes x 2 studente


def test_student_word_geweier(db, opstelling):
    with pytest.raises(HTTPException) as fout:
        genereer_verslag(db, opstelling["s_ander"], ["Student"], VAN, TOT, nou=NOU)
    assert fout.value.status_code == 403


def test_ongeldige_tydperk(db, opstelling):
    with pytest.raises(HTTPException):
        genereer_verslag(db, opstelling["admin"], ["Administrateur"], TOT, VAN, nou=NOU)
    with pytest.raises(HTTPException):
        genereer_verslag(db, opstelling["admin"], ["Administrateur"], date(2024, 1, 1), TOT, nou=NOU)



class TestVerslagHTTP:
    """Roete-vlak: rolhek, Excel-antwoord en lêernaam-opskrif."""

    @pytest.fixture()
    def http_db(self, tmp_path):
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker
        from database import Base

        engine = create_engine(
            f"sqlite:///{tmp_path / 'test.db'}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _char_length(dbapi_conn, _):
            dbapi_conn.create_function("char_length", 1, lambda s: None if s is None else len(s))

        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()

    def _gebruiker(self, db, rol_naam, n):
        rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == rol_naam).first()
        if not rol:
            rol = models.Rolle(ROL_Naam=rol_naam)
            db.add(rol)
            db.flush()
        g = models.Gebruikers(
            GEB_Naam="Toets", GEB_Van=f"Gebruiker{n}", GEB_ID_Nommer=f"900101000000{n}",
            GEB_Epos=f"toets{n}@voorbeeld.co.za", GEB_Wagwoord="hashed", Rol_ID=rol.Rol_ID,
        )
        db.add(g)
        db.commit()
        return g

    def _client(self, db):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import auth
        import database
        from routers.verslae import router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[database.get_db] = lambda: db
        client = TestClient(app)

        def kry(gebruiker, **params):
            token = auth.create_access_token({"sub": str(gebruiker.Gebruiker_ID)})
            return client.get(
                "/verslae/bywoning/export", params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        return kry

    def test_admin_kry_xlsx(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        resp = self._client(http_db)(admin, van="2026-09-01", tot="2026-09-30")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'filename="moon_bywoning_20260901_20260930.xlsx"' in resp.headers["content-disposition"]
        assert "Opsomming" in _laai(resp.content).sheetnames

    def test_student_kry_403(self, http_db):
        student = self._gebruiker(http_db, "Student", 1)
        assert self._client(http_db)(student).status_code == 403

    def test_sekuriteitswag_kry_403(self, http_db):
        wag = self._gebruiker(http_db, "Sekuriteit_Wag", 1)
        assert self._client(http_db)(wag).status_code == 403

    def test_ongeldige_datum_400(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        assert self._client(http_db)(admin, van="nie-n-datum").status_code == 400
