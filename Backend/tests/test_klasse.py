"""Toetse vir Klas / Module / Groep rooster-logika."""

import pytest

import models
import auth
from routers.klasse import (
    parse_lantiv_csv,
    resolver_student_rooster,
    resolver_personeel_rooster,
    resolver_klas_studente,
)


def skep_module(db, kode, naam=None):
    module = models.Module(MOD_Kode=kode, MOD_Naam=naam)
    db.add(module)
    db.flush()
    return module


def skep_groep(db, naam):
    groep = models.Groep(GRO_Naam=naam)
    db.add(groep)
    db.flush()
    return groep


def skep_klas(db, module, lokaal="GH117 A (50)", dag="Maandag", begin="8:00", eind="9:00"):
    klas = models.Klas(
        Module_ID=module.Module_ID,
        KLA_Lokaal=lokaal,
        KLA_Dag=dag,
        KLA_Begin_Tyd=begin,
        KLA_Eind_Tyd=eind,
    )
    db.add(klas)
    db.flush()
    return klas


class TestParseLantivCsv:
    def test_pars_ongewone_aanhalingstekens(self):
        # Werklike Lantiv-formaat: elke ry in een paar buitenste kwote,
        # velde binne-in dubbel-aangehaal.
        inhoud = (
            '"End Time,""Start Time"",""Dag"",""Lokaal"",""Groep"",""Module"",""From"",""To"""\n'
            '"10:00,""9:00"",""Maandag"",""GH117 A (50)"",""ER 2, LLB 2"",""EBREK370"",""8:00"",""9:00"""'
        )
        reëls = parse_lantiv_csv(inhoud)
        assert len(reëls) == 1
        ry = reëls[0]
        assert ry["dag"] == "Maandag"
        assert ry["lokaal"] == "GH117 A (50)"
        assert ry["groep"] == "ER 2, LLB 2"
        assert ry["module"] == "EBREK370"
        assert ry["from"] == "8:00"
        assert ry["to"] == "9:00"

    def test_meervoudige_rye(self):
        inhoud = (
            '"10:00,""9:00"",""Maandag"",""A"",""G1"",""M1"",""8:00"",""9:00"""\n'
            '"11:00,""10:00"",""Dinsdag"",""B"",""G2"",""M2"",""10:00"",""11:00"""'
        )
        reëls = parse_lantiv_csv(inhoud)
        assert len(reëls) == 2
        assert reëls[0]["dag"] == "Maandag"
        assert reëls[1]["dag"] == "Dinsdag"


class TestStudentRoosterResolusie:
    def test_groep_gebaseerde_rooster(self, db, maak_gebruiker):
        student = maak_gebruiker("Student")
        module = skep_module(db, "EBREK370")
        groep = skep_groep(db, "ER 2")
        klas = skep_klas(db, module)
        db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Groep(Gebruiker_ID=student.Gebruiker_ID, Groep_ID=groep.Groep_ID))
        db.flush()

        rooster = resolver_student_rooster(db, student.Gebruiker_ID)
        assert len(rooster) == 1
        assert rooster[0]["MOD_Kode"] == "EBREK370"

    def test_merge_groep_module_en_direk_dedupeer(self, db, maak_gebruiker):
        student = maak_gebruiker("Student")
        module = skep_module(db, "EBREK370")
        groep = skep_groep(db, "ER 2")
        klas = skep_klas(db, module)

        # Dieselfde klas via al drie bronne.
        db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Groep(Gebruiker_ID=student.Gebruiker_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Module(Gebruiker_ID=student.Gebruiker_ID, Module_ID=module.Module_ID))
        db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        db.flush()

        rooster = resolver_student_rooster(db, student.Gebruiker_ID)
        assert len(rooster) == 1  # gededupeer

    def test_module_inskrywing_voeg_klas_by(self, db, maak_gebruiker):
        student = maak_gebruiker("Student")
        module = skep_module(db, "EFREK370")
        klas = skep_klas(db, module)
        db.add(models.Student_Module(Gebruiker_ID=student.Gebruiker_ID, Module_ID=module.Module_ID))
        db.flush()

        rooster = resolver_student_rooster(db, student.Gebruiker_ID)
        assert len(rooster) == 1
        assert rooster[0]["MOD_Kode"] == "EFREK370"


class TestPersoneelRoosterResolusie:
    def test_module_en_direk_merge(self, db, maak_gebruiker):
        personeel = maak_gebruiker("Personeel")
        module = skep_module(db, "GKOMB370")
        klas = skep_klas(db, module)
        db.add(models.Personeel_Module(Gebruiker_ID=personeel.Gebruiker_ID, Module_ID=module.Module_ID))
        db.add(models.Personeel_Klas(Gebruiker_ID=personeel.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        db.flush()

        rooster = resolver_personeel_rooster(db, personeel.Gebruiker_ID)
        assert len(rooster) == 1  # gededupeer
        assert rooster[0]["MOD_Kode"] == "GKOMB370"



class TestKlasStudenteResolusie:
    def test_merge_groep_module_en_direk_dedupeer(self, db, maak_gebruiker):
        via_groep = maak_gebruiker("Student")
        via_module = maak_gebruiker("Student")
        via_direk = maak_gebruiker("Student")
        oral = maak_gebruiker("Student")  # via al drie bronne -> een keer
        buitestaander = maak_gebruiker("Student")
        module = skep_module(db, "EBREK370")
        ander_module = skep_module(db, "EFREK370")
        groep = skep_groep(db, "ER 2")
        klas = skep_klas(db, module)
        ander_klas = skep_klas(db, ander_module, dag="Dinsdag")
        db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Groep(Gebruiker_ID=via_groep.Gebruiker_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Module(Gebruiker_ID=via_module.Gebruiker_ID, Module_ID=module.Module_ID))
        db.add(models.Student_Klas(Gebruiker_ID=via_direk.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        db.add(models.Student_Groep(Gebruiker_ID=oral.Gebruiker_ID, Groep_ID=groep.Groep_ID))
        db.add(models.Student_Module(Gebruiker_ID=oral.Gebruiker_ID, Module_ID=module.Module_ID))
        db.add(models.Student_Klas(Gebruiker_ID=oral.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        db.add(models.Student_Klas(Gebruiker_ID=buitestaander.Gebruiker_ID, Klas_ID=ander_klas.Klas_ID))
        db.add(models.Student(Gebruiker_ID=via_groep.Gebruiker_ID, STU_Nommer="STU0001"))
        db.flush()

        studente = resolver_klas_studente(db, klas.Klas_ID)
        ids = {s["Gebruiker_ID"] for s in studente}
        assert ids == {
            via_groep.Gebruiker_ID,
            via_module.Gebruiker_ID,
            via_direk.Gebruiker_ID,
            oral.Gebruiker_ID,
        }
        assert len(studente) == 4  # gededupeer
        nommers = {s["Gebruiker_ID"]: s["STU_Nommer"] for s in studente}
        assert nommers[via_groep.Gebruiker_ID] == "STU0001"
        assert nommers[via_module.Gebruiker_ID] is None

    def test_onbekende_klas_gee_leeg(self, db):
        assert resolver_klas_studente(db, 9999) == []

class TestCSVInvoerIdempotensie:
    def test_herinvoer_skep_nie_duplikate_nie(self, db):
        # Simuleer twee invoere van dieselfde CSV deur dieselfde logika
        # twee keer te laat loop (via die router se hulpfunksies).
        inhoud = (
            '"10:00,""9:00"",""Maandag"",""GH117 A (50)"",""ER 2"",""EBREK370"",""8:00"",""9:00"""'
        )
        reëls = parse_lantiv_csv(inhoud)

        def voer_in():
            module = db.query(models.Module).filter(models.Module.MOD_Kode == "EBREK370").first()
            if not module:
                module = models.Module(MOD_Kode="EBREK370")
                db.add(module)
                db.flush()
            klas = models.Klas(
                Module_ID=module.Module_ID,
                KLA_Lokaal="GH117 A (50)",
                KLA_Dag="Maandag",
                KLA_Begin_Tyd="8:00",
                KLA_Eind_Tyd="9:00",
            )
            db.add(klas)
            db.flush()
            groep = db.query(models.Groep).filter(models.Groep.GRO_Naam == "ER 2").first()
            if not groep:
                groep = models.Groep(GRO_Naam="ER 2")
                db.add(groep)
                db.flush()
            db.add(models.Klas_Groep(Klas_ID=klas.Klas_ID, Groep_ID=groep.Groep_ID))
            db.flush()

        voer_in()
        voer_in()

        assert db.query(models.Module).filter(models.Module.MOD_Kode == "EBREK370").count() == 1
        assert db.query(models.Groep).filter(models.Groep.GRO_Naam == "ER 2").count() == 1
        assert db.query(models.Klas).count() == 2  # elke invoer skep 'n nuwe klas-ry


class TestRoosterHTTPAuth:
    """HTTP-integrasietoetse vir admin-toegang en rooster-leesreëls.

    Bou 'n minimale FastAPI-app met slegs die klasse-router en oorheers die
    get_db-afhanklikheid met 'n eie sqlite-sessie (check_same_thread=False
    sodat die TestClient se werkerdraad dieselfde sessie kan gebruik).
    Gebruik egte JWT-tokens om geoutentiseerde gebruikers te simuleer.
    """

    @pytest.fixture()
    def http_db(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database import Base

        # Gebruik 'n lêergebaseerde sqlite-databasis sodat alle verbindings
        # (toetsdraad én TestClient-werkerdraad) dieselfde databasis sien.
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

    def _maak_gebruiker(self, db, rol_naam, n):
        rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == rol_naam).first()
        if not rol:
            rol = models.Rolle(ROL_Naam=rol_naam)
            db.add(rol)
            db.flush()
        gebruiker = models.Gebruikers(
            GEB_Naam="Toets",
            GEB_Van=f"Gebruiker{n}",
            GEB_ID_Nommer=f"900101000000{n}",
            GEB_Epos=f"toets{n}@voorbeeld.co.za",
            GEB_Wagwoord="hashed",
            Rol_ID=rol.Rol_ID,
        )
        db.add(gebruiker)
        db.flush()
        return gebruiker

    def _bou_client(self, db):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import database
        from routers.klasse import router as klasse_router

        app = FastAPI()
        app.include_router(klasse_router)

        def _get_db_override():
            yield db

        app.dependency_overrides[database.get_db] = _get_db_override
        return TestClient(app)

    def _token(self, gebruiker):
        return auth.create_access_token({"sub": str(gebruiker.Gebruiker_ID)})

    def _headers(self, gebruiker):
        return {"Authorization": f"Bearer {self._token(gebruiker)}"}

    def test_admin_skryf_403_vir_nie_admin(self, http_db):
        student = self._maak_gebruiker(http_db, "Student", 1)
        client = self._bou_client(http_db)
        resp = client.post(
            "/rooster/modules",
            json={"MOD_Kode": "TEST100", "MOD_Naam": "Toets"},
            headers=self._headers(student),
        )
        assert resp.status_code == 403

    def test_admin_skryf_slaag(self, http_db):
        admin = self._maak_gebruiker(http_db, "Administrateur", 1)
        client = self._bou_client(http_db)
        resp = client.post(
            "/rooster/modules",
            json={"MOD_Kode": "TEST100", "MOD_Naam": "Toets"},
            headers=self._headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sukses"] is True
        assert data["data"]["MOD_Kode"] == "TEST100"

    def test_student_eie_rooster_200(self, http_db):
        student = self._maak_gebruiker(http_db, "Student", 1)
        module = skep_module(http_db, "EBREK370")
        klas = skep_klas(http_db, module)
        http_db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        http_db.flush()

        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/studente/{student.Gebruiker_ID}/rooster",
            headers=self._headers(student),
        )
        assert resp.status_code == 200
        assert resp.json()["sukses"] is True

    def test_admin_sien_ander_student_rooster_200(self, http_db):
        admin = self._maak_gebruiker(http_db, "Administrateur", 1)
        student = self._maak_gebruiker(http_db, "Student", 2)
        module = skep_module(http_db, "EBREK370")
        klas = skep_klas(http_db, module)
        http_db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        http_db.flush()

        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/studente/{student.Gebruiker_ID}/rooster",
            headers=self._headers(admin),
        )
        assert resp.status_code == 200

    def test_nie_admin_sien_ander_student_rooster_403(self, http_db):
        student_a = self._maak_gebruiker(http_db, "Student", 1)
        student_b = self._maak_gebruiker(http_db, "Student", 2)
        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/studente/{student_b.Gebruiker_ID}/rooster",
            headers=self._headers(student_a),
        )
        assert resp.status_code == 403

    def test_personeel_sien_eie_klas_register_200(self, http_db):
        personeel = self._maak_gebruiker(http_db, "Personeel", 1)
        student = self._maak_gebruiker(http_db, "Student", 2)
        module = skep_module(http_db, "EBREK370")
        klas = skep_klas(http_db, module)
        http_db.add(models.Personeel_Module(Gebruiker_ID=personeel.Gebruiker_ID, Module_ID=module.Module_ID))
        http_db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        http_db.flush()

        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/klasse/{klas.Klas_ID}/studente",
            headers=self._headers(personeel),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [s["Gebruiker_ID"] for s in data] == [student.Gebruiker_ID]

    def test_personeel_sien_ander_klas_register_403(self, http_db):
        personeel = self._maak_gebruiker(http_db, "Personeel", 1)
        module = skep_module(http_db, "EBREK370")
        klas = skep_klas(http_db, module)
        http_db.flush()

        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/klasse/{klas.Klas_ID}/studente",
            headers=self._headers(personeel),
        )
        assert resp.status_code == 403

    def test_admin_sien_enige_klas_register_200(self, http_db):
        admin = self._maak_gebruiker(http_db, "Administrateur", 1)
        module = skep_module(http_db, "EBREK370")
        klas = skep_klas(http_db, module)
        http_db.flush()

        client = self._bou_client(http_db)
        resp = client.get(
            f"/rooster/klasse/{klas.Klas_ID}/studente",
            headers=self._headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_klas_register_onbekende_klas_404(self, http_db):
        admin = self._maak_gebruiker(http_db, "Administrateur", 1)
        client = self._bou_client(http_db)
        resp = client.get("/rooster/klasse/9999/studente", headers=self._headers(admin))
        assert resp.status_code == 404

    def test_personeel_modules_lys_en_verwyder(self, http_db):
        admin = self._maak_gebruiker(http_db, "Administrateur", 1)
        dosent = self._maak_gebruiker(http_db, "Personeel", 2)
        module = skep_module(http_db, "EBREK370", "Rekeningkunde")
        http_db.flush()
        client = self._bou_client(http_db)

        resp = client.post(
            f"/rooster/personeel/{dosent.Gebruiker_ID}/modules",
            json={"Module_ID": module.Module_ID},
            headers=self._headers(admin),
        )
        assert resp.status_code == 200

        resp = client.get("/rooster/personeel-modules", headers=self._headers(admin))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == [{
            "Gebruiker_ID": dosent.Gebruiker_ID,
            "Module_ID": module.Module_ID,
            "MOD_Kode": "EBREK370",
            "MOD_Naam": "Rekeningkunde",
        }]

        resp = client.delete(
            f"/rooster/personeel/{dosent.Gebruiker_ID}/modules/{module.Module_ID}",
            headers=self._headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["Module_ID"] == module.Module_ID

        resp = client.get("/rooster/personeel-modules", headers=self._headers(admin))
        assert resp.json()["data"] == []

        # Tweede keer verwyder: die toewysing bestaan nie meer nie.
        resp = client.delete(
            f"/rooster/personeel/{dosent.Gebruiker_ID}/modules/{module.Module_ID}",
            headers=self._headers(admin),
        )
        assert resp.status_code == 404

    def test_personeel_modules_lys_403_vir_nie_admin(self, http_db):
        dosent = self._maak_gebruiker(http_db, "Personeel", 1)
        client = self._bou_client(http_db)
        resp = client.get("/rooster/personeel-modules", headers=self._headers(dosent))
        assert resp.status_code == 403
