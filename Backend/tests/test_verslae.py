"""Toetse vir die bywoningsverslag (services/verslag_service.py + verslag_formate.py)."""

import io
import zipfile
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from openpyxl import load_workbook

import models
from services.verslag_service import bou_oorsig, genereer_verslag

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
    hek1 = models.Lokasie(LOK_Naam="Hek 1", LOK_Tipe="Kampus", Kampus_ID=k1.Kampus_ID)
    lokaal = models.Lokasie(LOK_Naam="GH117", LOK_Tipe="Klaskamer", Kampus_ID=k1.Kampus_ID)
    hek2 = models.Lokasie(LOK_Naam="Hek 2", LOK_Tipe="Kampus", Kampus_ID=k2.Kampus_ID)
    huis_lok = models.Lokasie(LOK_Naam="Huis A", LOK_Tipe="Koshuis", Kampus_ID=k1.Kampus_ID)
    db.add_all([hek1, lokaal, hek2, huis_lok])
    db.flush()
    huis = models.Koshuis(KOS_Naam="Huis A", KOS_Kapasiteit=10, Kampus_ID=k1.Kampus_ID)
    huis2 = models.Koshuis(KOS_Naam="Huis B", KOS_Kapasiteit=5, Kampus_ID=k2.Kampus_ID)
    db.add_all([huis, huis2])
    db.flush()

    admin = maak_gebruiker("Administrateur")
    dosent = maak_gebruiker("Personeel")
    db.add(models.Personeel(Gebruiker_ID=dosent.Gebruiker_ID, PER_Nommer="P001", PER_Departement="IT"))
    opsigter = maak_gebruiker("Kampus_Opsigter")
    db.add(models.Kampus_Opsigter(Gebruiker_ID=opsigter.Gebruiker_ID, KAMO_Nommer="K001", Kampus_ID=k1.Kampus_ID))

    s_in_klas = maak_gebruiker("Student")
    s_ander = maak_gebruiker("Student")
    s_kampus2 = maak_gebruiker("Student")
    db.add(models.Student(Gebruiker_ID=s_in_klas.Gebruiker_ID, STU_Nommer="S001"))
    db.add(models.Student(Gebruiker_ID=s_ander.Gebruiker_ID, STU_Nommer="S002",
                          STU_Is_Koshuis=True, Koshuis_ID=huis.Koshuis_ID))
    db.add(models.Student(Gebruiker_ID=s_kampus2.Gebruiker_ID, STU_Nommer="S003",
                          STU_Is_Koshuis=True, Koshuis_ID=huis2.Koshuis_ID))

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

    # Event op Maandag 28 Sep 08:00-10:00 SA; s_in_klas en s_ander het RSVP gedoen.
    event = models.Funksie(
        Kampus_ID=k1.Kampus_ID, FUN_Naam="Oopdag", FUN_Kapasiteit=50,
        FUN_Begin_Tyd=datetime(2026, 9, 28, 6, 0), FUN_Eind_Tyd=datetime(2026, 9, 28, 8, 0),
        FUN_Status="AKTIEF", FUN_Is_Aktief=True,
    )
    ander_event = models.Funksie(
        Kampus_ID=k2.Kampus_ID, FUN_Naam="Sportdag", FUN_Kapasiteit=50,
        FUN_Begin_Tyd=datetime(2026, 10, 1, 6, 0), FUN_Eind_Tyd=datetime(2026, 10, 1, 8, 0),
        FUN_Status="AKTIEF", FUN_Is_Aktief=True,
    )
    db.add_all([event, ander_event])
    db.flush()
    db.add(models.FunksieRSVP(Funksie_ID=event.Funksie_ID, Gebruiker_ID=s_in_klas.Gebruiker_ID, RSVP_Status="GAAN"))
    db.add(models.FunksieRSVP(Funksie_ID=event.Funksie_ID, Gebruiker_ID=s_ander.Gebruiker_ID, RSVP_Status="GAAN"))

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
    # Koshuis: s_ander teken Vrydagaand by Huis A in (tel nie as kampusbywoning nie)
    log(s_ander, huis_lok, datetime(2026, 10, 2, 17, 0))
    db.commit()
    return {
        "admin": admin, "dosent": dosent, "opsigter": opsigter,
        "s_in_klas": s_in_klas, "s_ander": s_ander, "s_kampus2": s_kampus2,
    }


def _afdeling(oorsig, sleutel):
    return next(a for a in oorsig["afdelings"] if a["sleutel"] == sleutel)


def _rye(afdeling, sleutel):
    tabel = next(t for t in afdeling["tabelle"] if t["sleutel"] == sleutel)
    koppe = [k["naam"] for k in tabel["kolomme"]]
    return [dict(zip(koppe, r)) for r in tabel["rye"]]


def _ry_vir(rye, veld, waarde):
    return next((r for r in rye if r[veld] == waarde), None)


def _syfer(afdeling, etiket):
    return next(s["waarde"] for s in afdeling["kernsyfers"] if s["etiket"] == etiket)


def _naam(g):
    return f"{g.GEB_Naam} {g.GEB_Van}"


def _laai(inhoud: bytes):
    return load_workbook(io.BytesIO(inhoud))


# --------------------------------------------------------------------------- #
# Oorsig (data)
# --------------------------------------------------------------------------- #

def test_admin_kry_kampus_koshuis_events(db, opstelling):
    oorsig = bou_oorsig(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU)
    assert [a["titel"] for a in oorsig["afdelings"]] == ["Kampus", "Koshuis", "Geleenthede"]

    kampus = _afdeling(oorsig, "kampus")
    persone = _rye(kampus, "persone")
    assert _ry_vir(persone, "Naam", _naam(opstelling["s_kampus2"])) is not None
    status = _ry_vir(persone, "Naam", _naam(opstelling["s_in_klas"]))
    assert status["Huidige status"] == "Op kampus (IN)"
    assert status["Dae op kampus"] == 2
    assert _ry_vir(persone, "Naam", _naam(opstelling["dosent"]))["Gem. aankoms"] == "07:00"
    # Die koshuis-skandering tel nie as 'n kampus-toegangslog nie.
    assert len(_rye(kampus, "toegangslogs")) == 6

    koshuis = _afdeling(oorsig, "koshuis")
    assert _syfer(koshuis, "Koshuise") == 2
    assert _syfer(koshuis, "Inwoners") == 2
    inwoner = _ry_vir(_rye(koshuis, "inwoners"), "Naam", _naam(opstelling["s_ander"]))
    assert inwoner["Huidige status"] == "Ingeteken"
    assert inwoner["Koshuis"] == "Huis A"

    events = _afdeling(oorsig, "events")
    assert _syfer(events, "Geleenthede in tydperk") == 2
    oopdag = _ry_vir(_rye(events, "events"), "Event", "Oopdag")
    assert (oopdag["RSVP's"], oopdag["Aangekom"]) == (2, 1)
    assert oopdag["Status"] == "Afgehandel"


def test_opsigter_sien_net_eie_kampus(db, opstelling):
    oorsig = bou_oorsig(db, opstelling["opsigter"], ["Kampus_Opsigter"], VAN, TOT, nou=NOU)
    assert oorsig["meta"]["omvang"] == "Kampus: Hoofkampus"

    kampus = _afdeling(oorsig, "kampus")
    name = {r["Naam"] for r in _rye(kampus, "persone")}
    assert _naam(opstelling["s_kampus2"]) not in name
    assert _naam(opstelling["s_in_klas"]) in name
    assert all(r["Kampus"] == "Hoofkampus" for r in _rye(kampus, "toegangslogs"))

    koshuis = _afdeling(oorsig, "koshuis")
    assert [r["Koshuis"] for r in _rye(koshuis, "koshuise")] == ["Huis A"]

    events = _afdeling(oorsig, "events")
    assert [r["Event"] for r in _rye(events, "events")] == ["Oopdag"]


def test_personeel_kry_net_klas(db, opstelling):
    oorsig = bou_oorsig(db, opstelling["dosent"], ["Personeel"], VAN, TOT, nou=NOU)
    assert [a["titel"] for a in oorsig["afdelings"]] == ["Klas"]

    klas = _afdeling(oorsig, "klas")
    studente = _rye(klas, "studente")
    assert {r["Naam"] for r in studente} == {_naam(opstelling["s_in_klas"]), _naam(opstelling["s_ander"])}
    student = _ry_vir(studente, "Naam", _naam(opstelling["s_in_klas"]))
    assert (student["Klasse bygewoon"], student["Klasse geskeduleer"]) == (1, 2)
    # Twee Maandag-klasperiodes; die eerste bygewoon, die tweede gemis.
    assert [r["Teenwoordig"] for r in _rye(klas, "klasperiodes")] == [1, 0]
    assert len(_rye(klas, "klasregister")) == 4  # 2 periodes x 2 studente


def test_maks_rye_kap_tabelle_maar_hou_totaal(db, opstelling):
    oorsig = bou_oorsig(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU, maks_rye=2)
    logs = next(t for t in _afdeling(oorsig, "kampus")["tabelle"] if t["sleutel"] == "toegangslogs")
    assert len(logs["rye"]) == 2
    assert logs["totaal"] == 6


def test_student_word_geweier(db, opstelling):
    with pytest.raises(HTTPException) as fout:
        bou_oorsig(db, opstelling["s_ander"], ["Student"], VAN, TOT, nou=NOU)
    assert fout.value.status_code == 403


def test_ongeldige_tydperk(db, opstelling):
    with pytest.raises(HTTPException):
        bou_oorsig(db, opstelling["admin"], ["Administrateur"], TOT, VAN, nou=NOU)
    with pytest.raises(HTTPException):
        bou_oorsig(db, opstelling["admin"], ["Administrateur"], date(2024, 1, 1), TOT, nou=NOU)


# --------------------------------------------------------------------------- #
# Lêerformate
# --------------------------------------------------------------------------- #

def test_excel_bladsye_vir_admin_en_opsigter(db, opstelling):
    inhoud, lêernaam = genereer_verslag(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU)
    assert lêernaam == "moon_bywoning_20260928_20261005.xlsx"
    assert _laai(inhoud).sheetnames == ["Kampus", "Koshuis", "Geleenthede"]

    inhoud, _ = genereer_verslag(db, opstelling["opsigter"], ["Kampus_Opsigter"], VAN, TOT, nou=NOU)
    assert _laai(inhoud).sheetnames == ["Kampus", "Koshuis", "Geleenthede"]


def test_excel_bladsy_vir_personeel(db, opstelling):
    inhoud, _ = genereer_verslag(db, opstelling["dosent"], ["Personeel"], VAN, TOT, nou=NOU)
    wb = _laai(inhoud)
    assert wb.sheetnames == ["Klas"]
    waardes = {c for ry in wb["Klas"].iter_rows(values_only=True) for c in ry if c is not None}
    assert _naam(opstelling["s_in_klas"]) in waardes


@pytest.mark.parametrize("rol_sleutel,rol", [("admin", "Administrateur"), ("dosent", "Personeel")])
def test_pdf(db, opstelling, rol_sleutel, rol):
    inhoud, lêernaam = genereer_verslag(db, opstelling[rol_sleutel], [rol], VAN, TOT, nou=NOU, formaat="pdf")
    assert lêernaam.endswith(".pdf")
    assert inhoud.startswith(b"%PDF")


@pytest.mark.parametrize("rol_sleutel,rol", [("admin", "Administrateur"), ("dosent", "Personeel")])
def test_word(db, opstelling, rol_sleutel, rol):
    from docx import Document

    inhoud, lêernaam = genereer_verslag(db, opstelling[rol_sleutel], [rol], VAN, TOT, nou=NOU, formaat="docx")
    assert lêernaam.endswith(".docx")
    assert zipfile.is_zipfile(io.BytesIO(inhoud))
    opskrifte = [p.text for p in Document(io.BytesIO(inhoud)).paragraphs if p.style.name.startswith("Heading 1")]
    assert opskrifte == (["Kampus", "Koshuis", "Geleenthede"] if rol == "Administrateur" else ["Klas"])


def test_teks(db, opstelling):
    inhoud, lêernaam = genereer_verslag(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU, formaat="txt")
    assert lêernaam.endswith(".txt")
    teks = inhoud.decode("utf-8")
    for kop in (" KAMPUS ", " KOSHUIS ", " EVENTS "):
        assert kop in teks
    assert _naam(opstelling["s_kampus2"]) in teks


def test_onbekende_formaat(db, opstelling):
    with pytest.raises(HTTPException) as fout:
        genereer_verslag(db, opstelling["admin"], ["Administrateur"], VAN, TOT, nou=NOU, formaat="csv")
    assert fout.value.status_code == 400


class TestVerslagHTTP:
    """Roete-vlak: rolhek, lêer-antwoorde, lêernaam-opskrif en die JSON-oorsig."""

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

    def _client(self, db, pad="/verslae/bywoning/export"):
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
            return client.get(pad, params=params, headers={"Authorization": f"Bearer {token}"})
        return kry

    def test_admin_kry_xlsx(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        resp = self._client(http_db)(admin, van="2026-09-01", tot="2026-09-30")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert 'filename="moon_bywoning_20260901_20260930.xlsx"' in resp.headers["content-disposition"]
        assert _laai(resp.content).sheetnames == ["Kampus", "Koshuis", "Geleenthede"]

    @pytest.mark.parametrize("formaat,tipe", [
        ("pdf", "application/pdf"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("txt", "text/plain"),
    ])
    def test_admin_kry_ander_formate(self, http_db, formaat, tipe):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        resp = self._client(http_db)(admin, van="2026-09-01", tot="2026-09-30", formaat=formaat)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(tipe)
        assert f'filename="moon_bywoning_20260901_20260930.{formaat}"' in resp.headers["content-disposition"]

    def test_ongeldige_formaat_422(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        assert self._client(http_db)(admin, formaat="csv").status_code == 422

    def test_oorsig_json(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        resp = self._client(http_db, "/verslae/bywoning/oorsig")(admin, van="2026-09-01", tot="2026-09-30")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["meta"]["van"] == "2026-09-01"
        assert [a["sleutel"] for a in data["afdelings"]] == ["kampus", "koshuis", "events"]

    def test_student_kry_403(self, http_db):
        student = self._gebruiker(http_db, "Student", 1)
        assert self._client(http_db)(student).status_code == 403
        assert self._client(http_db, "/verslae/bywoning/oorsig")(student).status_code == 403

    def test_sekuriteitswag_kry_403(self, http_db):
        wag = self._gebruiker(http_db, "Sekuriteit_Wag", 1)
        assert self._client(http_db)(wag).status_code == 403

    def test_ongeldige_datum_400(self, http_db):
        admin = self._gebruiker(http_db, "Administrateur", 1)
        assert self._client(http_db)(admin, van="nie-n-datum").status_code == 400
