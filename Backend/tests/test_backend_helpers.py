import io
import asyncio
import importlib
from types import SimpleNamespace
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException, UploadFile
from jose import jwt
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

import auth
import models
import schemas
from auto_uitcheck import (
    _is_koshuis_student,
    _kry_uitcheck_tydstip,
    _vind_oop_sessies,
    maak_scheduler_aan,
    sluit_scheduler_af,
)
from services.gebruiker_service import (
    generate_next_subnommer,
    get_user_role_ids,
    get_user_role_names,
    is_personeel_rol,
    kies_primere_rol,
    kontroleer_kampus,
    kontroleer_unieke_gebruiker_velde,
    kontroleer_unieke_subnommer,
    kry_rol,
    sync_gebruiker_nfc_tag,
    sync_gebruiker_roles,
    sync_gebruiker_subrekords,
    gebruiker_to_dict,
)
from services.nfc_service import deaktiveer_nfc_tags, genereer_unieke_nfc_uid
from services.status_service import haal_laatste_logs_per_gebruiker


class TestAuthHelpers:
    def test_password_round_trip(self):
        plain = "S3cur3Pa55!"
        hashed = auth.get_password_hash(plain)
        assert auth.verify_password(plain, hashed) is True
        assert auth.verify_password("wrong", hashed) is False
        assert auth.verify_password("plain", "not-a-bcrypt-hash") is False

    def test_database_dependency_closes_session(self, monkeypatch):
        import database

        class Session:
            def __init__(self):
                self.closed = False
            def close(self):
                self.closed = True

        session = Session()
        monkeypatch.setattr(database, "SessionLocal", lambda: session)
        dependency = database.get_db()
        assert next(dependency) is session
        with pytest.raises(StopIteration):
            next(dependency)
        assert session.closed is True

    def test_access_token_contains_expected_payload(self):
        token = auth.create_access_token({"sub": "42"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["exp"]

    def test_auth_dependencies_and_role_checks(self, db, maak_gebruiker, monkeypatch):
        user = maak_gebruiker("Student")
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}})
        token = auth.create_access_token({"sub": str(user.Gebruiker_ID)})

        resolved = asyncio.run(auth.get_current_user(request=request, token=token, db=db))
        assert resolved.Gebruiker_ID == user.Gebruiker_ID
        assert request.state.role == "Student"

        with pytest.raises(HTTPException, match="geloofsbriewe"):
            asyncio.run(auth.get_current_user(request=Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}}), token="bad", db=db))

        user.Is_Aktief = False
        db.flush()
        with pytest.raises(HTTPException, match="gedeaktiveer"):
            asyncio.run(auth.get_current_user(request=Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}}), token=token, db=db))

        request.state.roles = ["Student"]
        with pytest.raises(HTTPException, match="Toegang geweier"):
            auth.RoleChecker(["Administrateur"])(request=request, current_user=user, db=db)

        admin = maak_gebruiker("Administrateur")
        request.state.roles = ["Administrateur"]
        assert auth.RoleChecker(["Administrateur"])(request=request, current_user=admin, db=db) is True
        assert auth._dev_fallback_user(db).Gebruiker_ID == admin.Gebruiker_ID
        assert asyncio.run(auth.verifieer_kampus_toegang(request=request, kampus_id=999, current_user=admin, db=db)) is True
        request.state.roles = ["Student"]
        with pytest.raises(HTTPException, match="toestemming"):
            asyncio.run(auth.verifieer_kampus_toegang(request=request, kampus_id=999, current_user=user, db=db))

        request.state.roles = []
        monkeypatch.setattr(auth, "get_user_role_names", lambda db, user: [])
        with pytest.raises(HTTPException, match="geen geldige rol"):
            auth.RoleChecker(["Student"])(request=request, current_user=user, db=db)
        opsigter = maak_gebruiker("Kampus_Opsigter")
        campus = models.Kampus(KAM_Naam="Auth Campus", KAM_Adres="Address")
        db.add(campus)
        db.flush()
        db.add(models.Kampus_Opsigter(Gebruiker_ID=opsigter.Gebruiker_ID, KAMO_Nommer="AUTH1", Kampus_ID=campus.Kampus_ID))
        db.flush()
        request.state.roles = ["Kampus_Opsigter"]
        assert asyncio.run(auth.verifieer_kampus_toegang(request=request, kampus_id=campus.Kampus_ID, current_user=opsigter, db=db)) is True

    def test_auth_middleware_sources_and_inactive_users(self, db, maak_gebruiker, monkeypatch):
        user = maak_gebruiker("Student")
        token = auth.create_access_token({"sub": str(user.Gebruiker_ID)})

        class SessionProxy:
            def query(self, *args, **kwargs):
                return db.query(*args, **kwargs)

            def close(self):
                return None

        monkeypatch.setattr(auth.database, "SessionLocal", lambda: SessionProxy())
        middleware = auth.AuthMiddleware(lambda request: None)

        async def call_next(request):
            return "response"

        def request_with(headers=None, cookies=None, session=None):
            headers = list(headers or [])
            if cookies:
                headers.append((b"cookie", "; ".join(f"{key}={value}" for key, value in cookies.items()).encode()))
            scope = {
                "type": "http", "method": "GET", "path": "/", "headers": headers,
                "query_string": b"", "state": {},
            }
            if session is not None:
                scope["session"] = session
            return Request(scope)

        bearer_request = request_with(headers=[(b"authorization", f"Bearer {token}".encode())])
        assert asyncio.run(middleware.dispatch(bearer_request, call_next)) == "response"
        assert bearer_request.state.user.Gebruiker_ID == user.Gebruiker_ID

        cookie_request = request_with(cookies={"access_token": token})
        assert asyncio.run(middleware.dispatch(cookie_request, call_next)) == "response"
        session_request = request_with(session={"user_id": user.Gebruiker_ID})
        assert asyncio.run(middleware.dispatch(session_request, call_next)) == "response"
        invalid_request = request_with(headers=[(b"authorization", b"Bearer invalid")])
        assert asyncio.run(middleware.dispatch(invalid_request, call_next)) == "response"

        user.Is_Aktief = False
        db.flush()
        inactive_response = asyncio.run(middleware.dispatch(bearer_request, call_next))
        assert inactive_response.status_code == 401

        monkeypatch.setattr(auth, "DISABLE_AUTH", True)
        disabled_request = request_with()
        assert asyncio.run(middleware.dispatch(disabled_request, call_next)) == "response"
        monkeypatch.setattr(auth, "DISABLE_AUTH", False)

        class BrokenSession:
            def query(self, *args, **kwargs):
                raise RuntimeError("lookup failed")
            def close(self):
                return None

        monkeypatch.setattr(auth.database, "SessionLocal", lambda: BrokenSession())
        broken_request = request_with(headers=[(b"authorization", f"Bearer {token}".encode())])
        assert asyncio.run(middleware.dispatch(broken_request, call_next)) == "response"

        state_request = request_with()
        state_request.state.user = user
        assert asyncio.run(auth.get_current_user(state_request, token=None, db=db)) is user


class TestGebruikerServiceHelpers:
    def test_kies_primere_rol_uses_priority(self):
        assert kies_primere_rol(["Student", "Administrateur"]) == "Administrateur"
        assert kies_primere_rol(["Student"]) == "Student"
        assert kies_primere_rol([]) == "Onbekend"

    def test_kry_rol_raises_for_missing_record(self, db):
        with pytest.raises(HTTPException, match="Rol bestaan nie"):
            kry_rol(db, 99999)

    def test_get_user_roles_includes_primary_and_extra_roles(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Personeel")
        student_rol = models.Rolle(ROL_Naam="Student")
        db.add(student_rol)
        db.flush()
        db.add(models.GebruikersRolle(Gebruiker_ID=gebruiker.Gebruiker_ID, Rol_ID=student_rol.Rol_ID))
        db.flush()

        assert set(get_user_role_ids(db, gebruiker)) == {gebruiker.Rol_ID, student_rol.Rol_ID}
        assert set(get_user_role_names(db, gebruiker)) == {"Personeel", "Student"}

    def test_sync_gebruiker_roles_updates_primary_role(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Student")
        student_rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Student").first()
        personeel_rol = models.Rolle(ROL_Naam="Personeel")
        db.add(personeel_rol)
        db.flush()

        sync_gebruiker_roles(db, gebruiker, [student_rol.Rol_ID, personeel_rol.Rol_ID], primary_role_id=personeel_rol.Rol_ID)
        db.flush()

        assert gebruiker.Rol_ID == personeel_rol.Rol_ID
        assert set(
            row.Rol_ID for row in db.query(models.GebruikersRolle).filter(models.GebruikersRolle.Gebruiker_ID == gebruiker.Gebruiker_ID)
        ) == {student_rol.Rol_ID, personeel_rol.Rol_ID}

    def test_is_personeel_rol_accepts_multiple_role_shapes(self):
        assert is_personeel_rol(["Administrateur"]) is True
        assert is_personeel_rol("Sekuriteit_Wag") is True
        assert is_personeel_rol(["Student"]) is False

    def test_kampus_validation_and_duplicate_checks(self, db):
        with pytest.raises(HTTPException, match="Kampus_ID bestaan nie"):
            kontroleer_kampus(db, 999)

        gebruiker = models.Gebruikers(
            GEB_Naam="A",
            GEB_Van="B",
            GEB_ID_Nommer="900101000001",
            GEB_Epos="dup@example.com",
            GEB_Wagwoord="hash",
            Rol_ID=1,
        )
        db.add(gebruiker)
        db.flush()

        with pytest.raises(HTTPException, match="E-pos reeds geregistreer"):
            kontroleer_unieke_gebruiker_velde(db, epos="dup@example.com")
        with pytest.raises(HTTPException, match="ID Nommer reeds in gebruik"):
            kontroleer_unieke_gebruiker_velde(db, id_nommer="900101000001")

    def test_generate_next_subnommer_and_unique_validation(self, db):
        persisted = models.Personeel(Gebruiker_ID=1, PER_Nommer="PER0001")
        db.add(persisted)
        db.flush()

        assert generate_next_subnommer(db, models.Personeel, "PER_Nommer", "PER") == "PER0002"

        with pytest.raises(HTTPException, match="Personeelnommer reeds in gebruik"):
            kontroleer_unieke_subnommer(
                db,
                models.Personeel,
                "PER_Nommer",
                "PER0001",
                detail="Personeelnommer reeds in gebruik",
            )

    def test_sync_gebruiker_subrekords_generates_missing_numbers(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Personeel")

        sync_gebruiker_subrekords(db, gebruiker, ["Personeel"], {}, creating=True)
        db.flush()

        personeel = db.query(models.Personeel).filter(models.Personeel.Gebruiker_ID == gebruiker.Gebruiker_ID).first()
        assert personeel.PER_Nommer == "PER0001"

        gebruiker_2 = maak_gebruiker("Kampus_Opsigter")
        sync_gebruiker_subrekords(db, gebruiker_2, ["Kampus_Opsigter"], {}, creating=True)
        db.flush()

        opsigter = db.query(models.Kampus_Opsigter).filter(models.Kampus_Opsigter.Gebruiker_ID == gebruiker_2.Gebruiker_ID).first()
        assert opsigter.KAMO_Nommer == "KAMO0001"

    def test_sync_gebruiker_nfc_tag_and_user_serializer(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Student")
        sync_gebruiker_nfc_tag(db, gebruiker.Gebruiker_ID, {"NFC_UID": "ABC12345", "NFC_Tipe": "Gebruiker", "NFC_Is_Aktief": True})
        db.flush()

        tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.Gebruiker_ID == gebruiker.Gebruiker_ID).first()
        assert tag is not None
        assert tag.NFC_UID == "ABC12345"

        updated = deaktiveer_nfc_tags(db, gebruiker.Gebruiker_ID)
        assert updated == 1
        assert db.query(models.NFC_Tags).filter(models.NFC_Tags.Gebruiker_ID == gebruiker.Gebruiker_ID, models.NFC_Tags.NFC_Is_Aktief.is_(False)).count() == 1

        uid = genereer_unieke_nfc_uid(db, 8)
        assert uid
        assert db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == uid).count() == 0

        student = models.Student(Gebruiker_ID=gebruiker.Gebruiker_ID, STU_Nommer="STU0001", STU_Is_Koshuis=True, Koshuis_ID=1)
        db.add(student)
        db.flush()

        payload = gebruiker_to_dict(gebruiker)
        assert payload["STU_Nommer"] == "STU0001"
        assert payload["STU_Is_Koshuis"] is True
        assert payload["Rol_Naam"] == "Student"


class TestAutoUitcheckHelpers:
    def test_auto_uitcheck_uses_setting_and_detects_open_sessions(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Student")
        user2 = maak_gebruiker("Student")
        db.add(models.Instelling(Sleutel="auto_uitcheck_tydstip", Waarde="22:00"))

        lok = models.Lokasie(LOK_Naam="Gate A", LOK_Tipe="Ingang", Kampus_ID=1)
        db.add(lok)
        db.flush()

        db.add(models.Student(Gebruiker_ID=gebruiker.Gebruiker_ID, STU_Nommer="STU0002", STU_Is_Koshuis=False))
        db.add(models.Student(Gebruiker_ID=user2.Gebruiker_ID, STU_Nommer="STU0003", STU_Is_Koshuis=True))

        db.add(models.ToegangsLogs(Gebruiker_ID=gebruiker.Gebruiker_ID, Lokasie_ID=lok.Lokasie_ID, NFC_Tags_ID=None, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()))
        db.add(models.ToegangsLogs(Gebruiker_ID=user2.Gebruiker_ID, Lokasie_ID=lok.Lokasie_ID, NFC_Tags_ID=None, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()))
        db.flush()

        assert _kry_uitcheck_tydstip(db) == "22:00"
        assert _is_koshuis_student(db, gebruiker.Gebruiker_ID) is False
        assert _is_koshuis_student(db, user2.Gebruiker_ID) is True

        sessions = _vind_oop_sessies(db)
        assert len(sessions) == 2
        assert {row["Gebruiker_ID"] for row in sessions} == {gebruiker.Gebruiker_ID, user2.Gebruiker_ID}

    def test_scheduler_can_be_started_and_stopped(self):
        scheduler = maak_scheduler_aan()
        assert scheduler.running is True
        sluit_scheduler_af(scheduler)
        assert scheduler.running is False

    def test_auto_uitcheck_job_creates_non_dorm_checkout(self, db, maak_gebruiker, monkeypatch):
        import auto_uitcheck

        user = maak_gebruiker("Student")
        dorm_user = maak_gebruiker("Student")
        db.add(models.Instelling(Sleutel="auto_uitcheck_tydstip", Waarde="22:00"))
        location = models.Lokasie(LOK_Naam="Job Gate", LOK_Tipe="Ingang", Kampus_ID=1)
        db.add(location)
        db.flush()
        db.add_all([
            models.Student(Gebruiker_ID=user.Gebruiker_ID, STU_Nommer="JOB1", STU_Is_Koshuis=False),
            models.Student(Gebruiker_ID=dorm_user.Gebruiker_ID, STU_Nommer="JOB2", STU_Is_Koshuis=True),
            models.ToegangsLogs(Gebruiker_ID=user.Gebruiker_ID, Lokasie_ID=location.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()),
            models.ToegangsLogs(Gebruiker_ID=dorm_user.Gebruiker_ID, Lokasie_ID=location.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()),
        ])
        db.flush()

        class SessionProxy:
            def query(self, *args, **kwargs):
                return db.query(*args, **kwargs)
            def add(self, value):
                return db.add(value)
            def commit(self):
                return db.commit()
            def rollback(self):
                return db.rollback()
            def close(self):
                return None

        class FixedDateTime:
            @classmethod
            def now(cls):
                return datetime(2026, 1, 1, 22, 0)
            @classmethod
            def utcnow(cls):
                return datetime(2026, 1, 1, 22, 0)

        monkeypatch.setattr(auto_uitcheck.database, "SessionLocal", lambda: SessionProxy())
        monkeypatch.setattr(auto_uitcheck, "datetime", FixedDateTime)
        auto_uitcheck.outo_uitcheck_job()
        db.expire_all()
        created = db.query(models.ToegangsLogs).filter(
            models.ToegangsLogs.TOE_Auto_Uitgecheck.is_(True)
        ).all()
        assert len(created) == 1
        assert created[0].Gebruiker_ID == user.Gebruiker_ID

        db.query(models.Instelling).delete()
        db.add(models.Instelling(Sleutel="auto_uitcheck_tydstip", Waarde="23:00"))
        db.commit()
        auto_uitcheck.outo_uitcheck_job()

    def test_auto_uitcheck_job_rolls_back_on_error(self, monkeypatch):
        import auto_uitcheck

        class BrokenSession:
            def query(self, *args, **kwargs):
                raise RuntimeError("job failure")
            def rollback(self):
                self.rolled_back = True
            def close(self):
                self.closed = True

        session = BrokenSession()
        monkeypatch.setattr(auto_uitcheck.database, "SessionLocal", lambda: session)
        auto_uitcheck.outo_uitcheck_job()
        assert session.rolled_back is True
        assert session.closed is True


class TestStatusService:
    def test_haal_laatste_logs_per_gebruiker_filters_by_latest_access(self, db, maak_gebruiker):
        gebruiker = maak_gebruiker("Student")
        other = maak_gebruiker("Student")
        kampus = models.Kampus(KAM_Naam="Main Campus", KAM_Adres="1 Main St")
        db.add(kampus)
        db.flush()

        lokasie = models.Lokasie(LOK_Naam="Main Gate", LOK_Tipe="Ingang", Kampus_ID=kampus.Kampus_ID)
        db.add(lokasie)
        db.flush()

        db.add(models.Student(Gebruiker_ID=gebruiker.Gebruiker_ID, STU_Nommer="STU0004", STU_Is_Koshuis=False))
        db.add(models.Student(Gebruiker_ID=other.Gebruiker_ID, STU_Nommer="STU0005", STU_Is_Koshuis=False))

        now = datetime.utcnow()
        db.add(models.ToegangsLogs(Gebruiker_ID=gebruiker.Gebruiker_ID, Lokasie_ID=lokasie.Lokasie_ID, NFC_Tags_ID=None, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=now - timedelta(minutes=5)))
        db.add(models.ToegangsLogs(Gebruiker_ID=gebruiker.Gebruiker_ID, Lokasie_ID=lokasie.Lokasie_ID, NFC_Tags_ID=None, TOE_Rigting="UIT", TOE_Metode="NFC", TOE_Tydstempel=now))
        db.add(models.ToegangsLogs(Gebruiker_ID=other.Gebruiker_ID, Lokasie_ID=lokasie.Lokasie_ID, NFC_Tags_ID=None, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=now - timedelta(minutes=1)))
        db.flush()

        scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, kampus_id=kampus.Kampus_ID)
        assert {item.Gebruiker_ID for item in scanned_in} == {other.Gebruiker_ID}
        assert {item.Gebruiker_ID for item in scanned_out} == {gebruiker.Gebruiker_ID}

    def test_status_service_empty_and_koshuis_filters(self, db, maak_gebruiker):
        empty_in, empty_out = haal_laatste_logs_per_gebruiker(db, koshuis_id=99999)
        assert empty_in == [] and empty_out == []

        user = maak_gebruiker("Student")
        dorm = models.Koshuis(KOS_Naam="Status House", KOS_Adres="Address", KOS_Kapasiteit=10, Kampus_ID=None)
        db.add(dorm)
        db.flush()
        db.add(models.Student(Gebruiker_ID=user.Gebruiker_ID, STU_Nommer="STATUS1", Koshuis_ID=dorm.Koshuis_ID))
        location = models.Lokasie(LOK_Naam="Dorm Gate", LOK_Tipe="Ingang", Kampus_ID=1)
        db.add(location)
        db.flush()
        db.add(models.ToegangsLogs(Gebruiker_ID=user.Gebruiker_ID, Lokasie_ID=location.Lokasie_ID, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()))
        db.flush()
        scanned_in, scanned_out = haal_laatste_logs_per_gebruiker(db, koshuis_id=dorm.Koshuis_ID)
        assert len(scanned_in) == 1 and scanned_out == []


class TestRouterAndAdminEndpoints:
    def _make_user(self, db, rol_name="Administrateur", email_suffix="admin@example.com"):
        rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == rol_name).first()
        if rol is None:
            rol = models.Rolle(ROL_Naam=rol_name)
            db.add(rol)
            db.flush()

        user = models.Gebruikers(
            GEB_Naam="Admin",
            GEB_Van="Test",
            GEB_ID_Nommer=f"90010100000{len(db.query(models.Gebruikers).all()) + 1}",
            GEB_Epos=email_suffix,
            GEB_Wagwoord=auth.get_password_hash("secret123"),
            Rol_ID=rol.Rol_ID,
            Is_Aktief=True,
        )
        db.add(user)
        db.flush()
        return user

    def _build_client_with_db(self, app, db_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database import Base, get_db

        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        def _override_get_db():
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_get_db
        return app, SessionLocal

    def test_auth_routes_login_and_logout(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import database
        from routers import auth_routes

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(auth_routes.router)
        app, SessionLocal = self._build_client_with_db(app, tmp_path / "auth.db")

        with SessionLocal() as session:
            role = session.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Student").first()
            if role is None:
                role = models.Rolle(ROL_Naam="Student")
                session.add(role)
                session.flush()
            user = models.Gebruikers(
                GEB_Naam="Student",
                GEB_Van="User",
                GEB_ID_Nommer="900101000001",
                GEB_Epos="student@example.com",
                GEB_Wagwoord=auth.get_password_hash("secret123"),
                Rol_ID=role.Rol_ID,
                Is_Aktief=True,
            )
            session.add(user)
            session.commit()

        client = TestClient(app)
        response = client.post("/token", data={"username": "student@example.com", "password": "secret123"})
        assert response.status_code == 200
        assert response.json()["sukses"] is True
        assert "access_token" in response.json()["data"]

        logout_response = client.post("/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["sukses"] is True

    def test_kampus_and_koshuis_routes_support_crud_and_status(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import database
        import auth as auth_module
        from routers import kampus, koshuis

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(kampus.router)
        app.include_router(koshuis.router)
        app, SessionLocal = self._build_client_with_db(app, tmp_path / "kampus_koshuis.db")

        with SessionLocal() as session:
            role = session.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Administrateur").first()
            if role is None:
                role = models.Rolle(ROL_Naam="Administrateur")
                session.add(role)
                session.flush()
            admin = models.Gebruikers(
                GEB_Naam="Admin",
                GEB_Van="Test",
                GEB_ID_Nommer="900101000099",
                GEB_Epos="kampusadmin@example.com",
                GEB_Wagwoord=auth.get_password_hash("secret123"),
                Rol_ID=role.Rol_ID,
                Is_Aktief=True,
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)

        def _override_get_current_user():
            return admin

        app.dependency_overrides[auth_module.get_current_user] = _override_get_current_user

        client = TestClient(app)

        create_resp = client.post("/kampusse", json={"KAM_Naam": "Main Campus", "KAM_Adres": "1 Main Road"})
        assert create_resp.status_code == 201
        campus_id = create_resp.json()["data"]["Kampus_ID"]

        list_resp = client.get("/kampusse")
        assert list_resp.status_code == 200
        assert any(item["Kampus_ID"] == campus_id for item in list_resp.json()["data"])

        status_resp = client.get("/kampusse/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["sukses"] is True

        detail_resp = client.get(f"/kampusse/{campus_id}/status")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["Kampus_ID"] == campus_id

        update_resp = client.put(f"/kampusse/{campus_id}", json={"KAM_Naam": "Updated Campus", "KAM_Adres": "2 Main Road"})
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["KAM_Naam"] == "Updated Campus"

        koshuis_resp = client.post("/koshuise", json={"KOS_Naam": "Blue House", "KOS_Adres": "House Road", "KOS_Kapasiteit": 50, "Kampus_ID": campus_id})
        assert koshuis_resp.status_code == 201
        koshuis_id = koshuis_resp.json()["data"]["Koshuis_ID"]

        koshuis_list = client.get("/koshuise")
        assert koshuis_list.status_code == 200
        assert any(item["Koshuis_ID"] == koshuis_id for item in koshuis_list.json()["data"])

        koshuis_detail = client.get(f"/koshuise/{koshuis_id}/status")
        assert koshuis_detail.status_code == 200
        assert koshuis_detail.json()["data"]["Koshuis_ID"] == koshuis_id

        delete_resp = client.delete(f"/koshuise/{koshuis_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["sukses"] is True

        with SessionLocal() as session:
            for model in [models.Koshuis, models.Lokasie, models.Funksie, models.Kampus_Opsigter]:
                for row in session.query(model).filter(getattr(model, "Kampus_ID", None) == campus_id if hasattr(model, "Kampus_ID") else model.Gebruiker_ID == -1):
                    session.delete(row)
            session.commit()

        final_kampus_delete = client.delete(f"/kampusse/{campus_id}")
        assert final_kampus_delete.status_code == 200

    def test_instelling_routes_read_and_update(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from starlette.middleware.sessions import SessionMiddleware
        import database
        import auth as auth_module
        from routers import instellings

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(instellings.router)
        app, SessionLocal = self._build_client_with_db(app, tmp_path / "instellings.db")

        with SessionLocal() as session:
            role = session.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Administrateur").first()
            if role is None:
                role = models.Rolle(ROL_Naam="Administrateur")
                session.add(role)
                session.flush()
            admin = models.Gebruikers(
                GEB_Naam="Admin",
                GEB_Van="Test",
                GEB_ID_Nommer="900101000100",
                GEB_Epos="settingsadmin@example.com",
                GEB_Wagwoord=auth.get_password_hash("secret123"),
                Rol_ID=role.Rol_ID,
                Is_Aktief=True,
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)

        def _override_get_current_user():
            return admin

        app.dependency_overrides[auth_module.get_current_user] = _override_get_current_user

        with SessionLocal() as session:
            session.add(models.Instelling(Sleutel="auto_uitcheck_tydstip", Waarde="22:00", Beskrywing="Tydstip"))
            session.commit()

        client = TestClient(app)
        list_resp = client.get("/instellings")
        assert list_resp.status_code == 200
        assert any(item["Sleutel"] == "auto_uitcheck_tydstip" for item in list_resp.json()["data"])

        detail_resp = client.get("/instellings/auto_uitcheck_tydstip")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["Waarde"] == "22:00"

        update_resp = client.put(
            "/instellings/auto_uitcheck_tydstip",
            json={"Waarde": "23:00", "Beskrywing": "Updated description"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["Waarde"] == "23:00"

    def test_admin_csv_helpers(self, db):
        from routers import admin as admin_routes

        table = admin_routes._resolve_table("kampus")
        assert table.name == "kampus"
        assert admin_routes._normalize_import_mode("merge") == "merge"
        assert admin_routes._normalize_import_mode(None) == "merge"
        assert admin_routes._coerce_csv_value(models.Kampus.__table__.c.Kampus_ID.type, "12") == 12
        assert admin_routes._coerce_csv_value(models.Kampus.__table__.c.KAM_Naam.type, "  Test Campus  ") == "Test Campus"

        rows = admin_routes.parse_csv_rows(
            "kampus",
            "Kampus_ID,KAM_Naam,KAM_Adres\n1,Main Campus,1 Main Road\n",
        )
        assert rows[0]["KAM_Naam"] == "Main Campus"

        exported = admin_routes.export_table_csv_text(
            "kampus",
            [{"Kampus_ID": 1, "KAM_Naam": "Main Campus", "KAM_Adres": "1 Main Road"}],
        )
        assert "KAM_Naam" in exported and "Main Campus" in exported
        assert "kampus" in admin_routes.get_available_tables()
        assert len(admin_routes._get_import_order()) >= 1

        with pytest.raises(ValueError, match="Table name is required"):
            admin_routes._resolve_table("  ")
        with pytest.raises(ValueError, match="Unknown table"):
            admin_routes._resolve_table("does_not_exist")
        assert admin_routes._coerce_csv_value(models.Kampus.__table__.c.Kampus_ID.type, "") is None
        assert admin_routes._coerce_csv_value(models.Gebruikers.__table__.c.Is_Aktief.type, "yes") is True
        assert admin_routes._coerce_csv_value(models.Funksie.__table__.c.FUN_Begin_Tyd.type, "2026-01-02T03:04:05")
        assert admin_routes._topological_sort({"a": {"b"}, "b": {"a"}}) == ["a", "b"]

        student_rows = [{"STU_Nommer": None}, {"STU_Nommer": ""}]
        filled = admin_routes._fill_missing_student_numbers(student_rows, db)
        assert [row["STU_Nommer"] for row in filled] == ["1", "2"]
        hashed = admin_routes._hash_plain_passwords([{"GEB_Wagwoord": "plain"}, {"GEB_Wagwoord": "$2b$existing"}])
        assert hashed[0]["GEB_Wagwoord"].startswith("$2b$")
        assert hashed[1]["GEB_Wagwoord"] == "$2b$existing"

        report = {}
        translated = admin_routes._vertaal_verouderde_waardes("funksie", {"FUN_Status": "BEPLAN"}, report)
        assert translated["FUN_Status"] == "AKTIEF"
        assert report["aangepas"] == 1
        assert admin_routes._fout_boodskap(ValueError("bad\nsecond")) == "bad"

        table = models.Kampus.__table__
        assert admin_routes._prepare_insert_row_for_new_primary_key(table, {"Kampus_ID": 1, "KAM_Naam": "A"}, None)["Kampus_ID"] == 1
        assert admin_routes._prepare_insert_row_for_new_primary_key(
            table, {"Kampus_ID": 1, "KAM_Naam": "A"}, {"Kampus_ID": 1, "KAM_Naam": "A"}
        ) == {}
        prepared = admin_routes._prepare_insert_row_for_new_primary_key(
            table, {"Kampus_ID": 1, "KAM_Naam": "B"}, {"Kampus_ID": 1, "KAM_Naam": "A"}
        )
        assert "Kampus_ID" not in prepared
        assert admin_routes._normalize_insert_row(table, {"KAM_Naam": "A"})["KAM_Adres"] is None
        assert "KAM_Naam" not in admin_routes._normalize_insert_row(table, {"KAM_Naam": None})
        assert admin_routes._remap_foreign_keys(table, {"Kampus_ID": 1}, {}) == {"Kampus_ID": 1}
        mappings = {}
        admin_routes._remember_id_mapping(table, {"Kampus_ID": 1}, {"Kampus_ID": 4}, mappings)
        assert mappings["kampus"][1] == 4

        exported_zip = admin_routes._create_export_zip(db)
        assert exported_zip.getvalue().startswith(b"PK")
        empty_import = admin_routes._import_from_zip(
            db,
            UploadFile(filename="backup.zip", file=io.BytesIO(b"PK\x05\x06" + b"\x00" * 18)),
        )
        assert empty_import["imported"] == {}

        app = admin_routes.router
        assert app is not None

    def test_admin_csv_route_endpoints(self, db, monkeypatch):
        from routers import admin as admin_routes

        admin = self._make_user(db)
        assert admin_routes.check_csv_import_export_enabled() is True
        tables = admin_routes.list_csv_tables(current_user=admin, is_admin=True, _csv_enabled=True)
        assert tables.sukses is True
        exported = admin_routes.export_table_csv(
            table="kampus", db=db, current_user=admin, is_admin=True, _csv_enabled=True
        )
        assert exported.media_type.startswith("text/csv")

        monkeypatch.setattr(admin_routes, "_insert_csv_rows", lambda *args, **kwargs: 1)
        monkeypatch.setattr(admin_routes, "_reset_sequences", lambda *args, **kwargs: None)
        imported = asyncio.run(admin_routes.import_table_csv(
            table="kampus",
            file=None,
            text="Kampus_ID,KAM_Naam,KAM_Adres\n1,Imported,Address\n",
            mode="merge",
            db=db,
            current_user=admin,
            is_admin=True,
            _csv_enabled=True,
        ))
        assert imported.data["imported_rows"] == 1

        with pytest.raises(HTTPException, match="disabled"):
            monkeypatch.setattr(admin_routes.Config, "CSV_IMPORT_EXPORT_ENABLED", False)
            admin_routes.check_csv_import_export_enabled()
        monkeypatch.setattr(admin_routes.Config, "CSV_IMPORT_EXPORT_ENABLED", True)

    def test_main_builds_app_without_running_database_startup(self, monkeypatch):
        import migrations

        monkeypatch.setattr(migrations, "run_pre_migrations", lambda engine: None)
        monkeypatch.setattr(migrations, "run_migrations", lambda engine: None)
        monkeypatch.setattr(models.Base.metadata, "create_all", lambda bind: None)

        main_module = importlib.import_module("main")
        main_module = importlib.reload(main_module)
        assert main_module.app.title == "MOON Admin API"
        assert any(route.path == "/" for route in main_module.app.routes)

    def test_main_exception_handlers_and_root(self, monkeypatch):
        import migrations

        monkeypatch.setattr(migrations, "run_pre_migrations", lambda engine: None)
        monkeypatch.setattr(migrations, "run_migrations", lambda engine: None)
        monkeypatch.setattr(models.Base.metadata, "create_all", lambda bind: None)
        main_module = importlib.reload(importlib.import_module("main"))
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}})
        root = main_module.read_root()
        assert root.data["message"] == "Backend is working"
        http_response = asyncio.run(main_module.custom_http_exception_handler(request, HTTPException(status_code=400, detail="bad")))
        assert http_response.status_code == 400
        error_response = asyncio.run(main_module.general_exception_handler(request, RuntimeError("broken")))
        assert error_response.status_code == 500

    def test_migrations_execute_all_sql_blocks_with_fake_engine(self):
        import migrations

        class FakeConnection:
            def __init__(self):
                self.statements = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def execute(self, statement):
                self.statements.append(str(statement))

            def commit(self):
                return None

        class FakeEngine:
            def __init__(self):
                self.connection = FakeConnection()

            def begin(self):
                return self.connection

            def connect(self):
                return self.connection

        engine = FakeEngine()
        migrations.run_pre_migrations(engine)
        migrations.run_migrations(engine)
        assert len(engine.connection.statements) >= 10
        assert any("saamry_vriendskap" in statement for statement in engine.connection.statements)
        assert any("besoeker_uitnodiging" in statement for statement in engine.connection.statements)

        class FailingEngine:
            def begin(self):
                raise RuntimeError("database unavailable")

        with pytest.raises(RuntimeError, match="database unavailable"):
            migrations.run_pre_migrations(FailingEngine())

    def test_migrations_continue_when_individual_steps_fail(self):
        import migrations

        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def execute(self, statement):
                raise RuntimeError("step unavailable")

            def commit(self):
                return None

        class FailingEngine:
            def begin(self):
                return FailingConnection()

            def connect(self):
                return FailingConnection()

        migrations.run_migrations(FailingEngine())

    def test_klasse_csv_and_roster_helpers(self):
        from routers import klasse

        lantiv = "End,Start,Dag,Lokaal,Groep,Module,From,To\n10:00,09:00,Maandag,GH117,ER 2,EBREK370,09:00,10:00\n"
        assert klasse.parse_lantiv_csv(lantiv) == [{
            "dag": "Maandag", "lokaal": "GH117", "groep": "ER 2",
            "module": "EBREK370", "from": "09:00", "to": "10:00",
        }]
        assert klasse.parse_lantiv_csv('"10:00,""9:00"",""Maandag"",""GH117"",""ER 2"",""EBREK370"",""9:00"",""10:00"""')
        assert klasse.parse_lantiv_csv("bad") == []
        assert klasse._normaliseer_kop(" Student Nommer ") == "studentnommer"
        assert klasse._splits_waardes("ER 2; LLB 2, BCOM 1") == ["ER 2", "LLB 2", "BCOM 1"]
        assert klasse._splits_waardes("") == []

        assignment = klasse.parse_student_toewysing_csv(
            "Studentenommer,Groep,Module\nSTU1,ER 2,EBREK370; MATH\n,,\n"
        )
        assert assignment[0]["student"] == "STU1"
        assert assignment[0]["groepe"] == ["ER 2"]
        assert assignment[0]["modules"] == ["EBREK370", "MATH"]
        assert klasse.parse_student_toewysing_csv("Groep,Module\nER 2,MOD1\n") == []

        module = SimpleNamespace(MOD_Kode="MOD1", MOD_Naam="Module One")
        klas = SimpleNamespace(
            Klas_ID=1, Module_ID=2, module=module, KLA_Lokaal="A1",
            KLA_Dag="Maandag", KLA_Begin_Tyd="09:00", KLA_Eind_Tyd="10:00",
        )
        assert klasse._klas_na_dict(klas)["MOD_Kode"] == "MOD1"
        klas.module = None
        assert klasse._klas_na_dict(klas)["MOD_Naam"] is None

    def test_saamry_pure_helpers_cover_status_and_visibility(self):
        from routers import saamry

        student = SimpleNamespace(STU_Nommer="STU1")
        user = SimpleNamespace(
            Gebruiker_ID=1, GEB_Naam="Test", GEB_Van="User",
            GEB_Profiel_Foto=None, GEB_Selfoon_Nr="0123", GEB_Epos="test@example.com",
            student=student, personeel=None,
        )
        assert saamry._user_dict(user)["rol"] == "Student"
        assert saamry._user_dict(user, include_contact=True)["epos"] == "test@example.com"
        assert saamry._friendship_status(None, 1) == "GEEN"
        assert saamry._friendship_status(SimpleNamespace(SAA_Status="AANVAAR"), 1) == "VRIEND"
        assert saamry._friendship_status(SimpleNamespace(SAA_Status="HANGEND", Versoeker_ID=1), 1) == "HANGEND_UIT"
        assert saamry._friendship_status(SimpleNamespace(SAA_Status="HANGEND", Versoeker_ID=2), 1) == "HANGEND_IN"
        assert saamry._friendship_status(SimpleNamespace(SAA_Status="GEWEIER"), 1) == "GEWEIER"

        driver = SimpleNamespace(Gebruiker_ID=1, SAA_Status="AANVAAR", gebruiker=user)
        pending = SimpleNamespace(Gebruiker_ID=2, SAA_Status="HANGEND", gebruiker=user)
        accepted = SimpleNamespace(Gebruiker_ID=3, SAA_Status="AANVAAR", gebruiker=user)
        group = SimpleNamespace(
            Groep_ID=4, SAA_Naam="Trip", SAA_Vertrekpunt="A", SAA_Bestemming="B",
            SAA_Vertrek_Tyd=datetime.utcnow(), SAA_Sitplekke=3, SAA_Status="AKTIEF",
            Bestuurder_ID=1, bestuurder=user, lede=[driver, pending, accepted],
        )
        assert saamry._accepted_passenger_count(group) == 1
        assert saamry._viewer_is_accepted_member(group, 1) is True
        assert saamry._viewer_is_accepted_member(group, 3) is True
        assert saamry._viewer_is_accepted_member(group, 9) is False
        data = saamry._group_dict(group, 1)
        assert data["beskikbare_sitplekke"] == 1
        assert len(data["lede"]) == 3


class TestAdditionalBackendRouteCoverage:
    def _ensure_role(self, db, name):
        role = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == name).first()
        if role is None:
            role = models.Rolle(ROL_Naam=name)
            db.add(role)
            db.flush()
        return role

    def _make_user(self, db, *, name, surname, email, role_name, user_id=None, active=True):
        role = self._ensure_role(db, role_name)
        user = models.Gebruikers(
            Gebruiker_ID=user_id or None,
            GEB_Naam=name,
            GEB_Van=surname,
            GEB_ID_Nommer=f"900101000{len(db.query(models.Gebruikers).all()) + 1:04d}",
            GEB_Epos=email,
            GEB_Wagwoord=auth.get_password_hash("secret123"),
            Rol_ID=role.Rol_ID,
            Is_Aktief=active,
        )
        db.add(user)
        db.flush()
        return user

    def _response_payload(self, response):
        if response is None:
            return None
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return {
            "sukses": getattr(response, "sukses", None),
            "data": getattr(response, "data", None),
            "fout": getattr(response, "fout", None),
        }

    def test_dashboard_and_profile_routes(self, db):
        from routers import dashboard
        admin = self._make_user(db, name="Admin", surname="User", email="dash@example.com", role_name="Administrateur")
        student = self._make_user(db, name="Student", surname="User", email="studentdash@example.com", role_name="Student")
        db.add(models.Student(Gebruiker_ID=student.Gebruiker_ID, STU_Nommer="STU9001", STU_Is_Koshuis=True))
        db.flush()

        roles = dashboard.lees_rolle(db=db, current_user=admin, is_admin=True)
        roles_payload = self._response_payload(roles)
        assert roles_payload["sukses"] is True
        assert any(getattr(item, "ROL_Naam", None) == "Administrateur" for item in roles_payload["data"])

        profile = dashboard.kry_my_profiel(current_user=student, db=db)
        assert profile["sukses"] is True
        assert profile["data"]["rol"] in {"Student", "Onbekend"}

        photo = UploadFile(filename="avatar.png", file=io.BytesIO(b"png-data"), headers={"content-type": "image/png"})
        result = asyncio.run(dashboard.upload_my_profile_photo(file=photo, current_user=student, db=db))
        result_payload = self._response_payload(result)
        assert result_payload["sukses"] is True
        assert "/uploads/profile_photos/" in result_payload["data"]["foto_url"]

        activity = dashboard.kry_my_dashboard(current_user=student, db=db)
        assert activity["sukses"] is True
        assert activity["data"]["kampus_status"] in {"ONBEKEND", "OP_KAMPUS", "NIE_OP_KAMPUS"}

        live = dashboard.dashboard_live(db=db, current_user=admin)
        live_payload = self._response_payload(live)
        assert live_payload["sukses"] is True
        assert "studente_op_kampus" in live_payload["data"] or "personeel_op_kampus" in live_payload["data"]

    def test_besoeker_invite_endpoints(self, db):
        from routers import besoekers
        import schemas

        campus = models.Kampus(KAM_Naam="Campus Visitor", KAM_Adres="Visitor Street")
        db.add(campus)
        db.flush()

        student = self._make_user(db, name="Host", surname="Student", email="host@school.co.za", role_name="Student")
        db.add(models.Student(Gebruiker_ID=student.Gebruiker_ID, STU_Nommer="STU333", STU_Is_Koshuis=False))
        db.flush()

        payload = schemas.BesoekerUitnodigingCreate(naam="Jane", van="Doe", selfoon="0812345678", rede="Besoek")
        created = besoekers.create_visitor_invite(payload=payload, db=db, current_user=student)
        created_payload = self._response_payload(created)
        invite_id = created_payload["data"]["uitnodiging_id"]
        assert created_payload["sukses"] is True
        assert created_payload["data"]["status"] == "HANGEND"

        mine = besoekers.get_my_visitor_invites(db=db, current_user=student)
        mine_payload = self._response_payload(mine)
        assert mine_payload["sukses"] is True
        assert any(item["uitnodiging_id"] == invite_id for item in mine_payload["data"])

        cancelled = besoekers.cancel_visitor_invite(uitnodiging_id=invite_id, db=db, current_user=student)
        cancelled_payload = self._response_payload(cancelled)
        assert cancelled_payload["sukses"] is True
        assert cancelled_payload["data"]["status"] == "GEKANSELLEER"

        new_payload = schemas.BesoekerUitnodigingCreate(naam="John", van="Smith", selfoon="0823456789", rede="Besoek")
        created2 = besoekers.create_visitor_invite(payload=new_payload, db=db, current_user=student)
        created2_payload = self._response_payload(created2)
        invite2 = created2_payload["data"]["uitnodiging_id"]

        verify = besoekers.verify_visitor_otp(payload=schemas.BesoekerOtpVerifyRequest(otp=created2_payload["data"]["otp"]), db=db, current_user=student, _=True)
        verify_payload = self._response_payload(verify)
        assert verify_payload["sukses"] is True

        allow = besoekers.allow_visitor_entry(uitnodiging_id=invite2, payload=schemas.BesoekerBesluitRequest(kampus_id=campus.Kampus_ID), db=db, current_user=self._make_user(db, name="Guard", surname="User", email="guard@example.com", role_name="Sekuriteit_Wag"), _=True)
        assert self._response_payload(allow)["sukses"] is True

        deny_payload = schemas.BesoekerUitnodigingCreate(naam="Kim", van="Nooit", selfoon="0823456781", rede="Besoek")
        deny_invite = self._response_payload(besoekers.create_visitor_invite(payload=deny_payload, db=db, current_user=student))
        deny_id = deny_invite["data"]["uitnodiging_id"]
        deny = besoekers.deny_visitor_entry(uitnodiging_id=deny_id, payload=schemas.BesoekerBesluitRequest(kampus_id=campus.Kampus_ID), db=db, current_user=self._make_user(db, name="Guard2", surname="User", email="guard2@example.com", role_name="Sekuriteit_Wag"), _=True)
        assert self._response_payload(deny)["sukses"] is True

        helper = besoekers._expire_old_invites(db)
        assert isinstance(helper, int)

    def test_student_and_nfc_route_helpers(self, db):
        from routers import nfc, student
        import schemas

        campus = models.Kampus(KAM_Naam="Camp", KAM_Adres="Addr")
        db.add(campus)
        db.flush()
        lok = models.Lokasie(LOK_Naam="Lab 1", LOK_Tipe="Klaskamer", Kampus_ID=campus.Kampus_ID)
        db.add(lok)
        db.flush()

        role = self._ensure_role(db, "Student")
        user = models.Gebruikers(
            GEB_Naam="Std", GEB_Van="User", GEB_ID_Nommer="900101001000", GEB_Epos="stdnfc@example.com",
            GEB_Wagwoord=auth.get_password_hash("secret123"), Rol_ID=role.Rol_ID, Is_Aktief=True,
        )
        db.add(user)
        db.flush()
        db.add(models.Student(Gebruiker_ID=user.Gebruiker_ID, STU_Nommer="STU777", STU_Is_Koshuis=False))
        db.flush()

        create_tag = nfc.registreer_nfc_tag(
            tag_in=schemas.NFCTagCreate(NFC_UID="UID-123", Gebruiker_ID=user.Gebruiker_ID, Lokasie_ID=lok.Lokasie_ID, NFC_Tipe="Gebruiker", NFC_Is_Aktief=True),
            db=db,
            current_user=self._make_user(db, name="Admin", surname="X", email="adminnfc@example.com", role_name="Administrateur"),
            is_admin=True,
        )
        create_tag_payload = self._response_payload(create_tag)
        assert create_tag_payload["sukses"] is True

        lookup = nfc.kry_lokasie_deur_nfc_uid(uid="UID-123", db=db, current_user=user)
        assert self._response_payload(lookup)["sukses"] is True

        scan = student.student_scan_klas(
            data=schemas.StudentKlasScanRequest(nfc_uid="UID-123", rigting="IN"),
            db=db,
            current_user=user,
        )
        assert self._response_payload(scan)["sukses"] is True

        disabled = nfc.deaktiveer_gebruiker_nfc_tags(user_id=user.Gebruiker_ID, db=db, current_user=user, is_admin=True)
        assert self._response_payload(disabled)["sukses"] is True

        search = student.soek_studente(q="Std", db=db, current_user=user)
        assert isinstance(self._response_payload(search)["data"], list)

    def test_nfc_and_settings_error_branches(self, db):
        from routers import instellings, nfc

        admin = self._make_user(db, name="Admin", surname="NFC", email="nfc-branches@example.com", role_name="Administrateur")
        with pytest.raises(HTTPException, match="nie gevind"):
            nfc.registreer_nfc_tag(
                schemas.NFCTagCreate(NFC_UID="MISSING", Gebruiker_ID=99999, NFC_Tipe="Gebruiker", NFC_Is_Aktief=True),
                db=db, current_user=admin, is_admin=True,
            )

        tag = nfc.registreer_nfc_tag(
            schemas.NFCTagCreate(NFC_UID="BRANCH-TAG", Gebruiker_ID=admin.Gebruiker_ID, NFC_Tipe="Gebruiker", NFC_Is_Aktief=True),
            db=db, current_user=admin, is_admin=True,
        )
        assert tag.sukses is True
        with pytest.raises(HTTPException, match="reeds geregistreer"):
            nfc.registreer_nfc_tag(
                schemas.NFCTagCreate(NFC_UID="BRANCH-TAG", Gebruiker_ID=admin.Gebruiker_ID, NFC_Tipe="Gebruiker", NFC_Is_Aktief=True),
                db=db, current_user=admin, is_admin=True,
            )
        with pytest.raises(HTTPException, match="Geen aktiewe"):
            nfc.deaktiveer_gebruiker_nfc_tags(99999, db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            nfc.kry_lokasie_deur_nfc_uid("MISSING", db=db, current_user=admin)

        assert instellings.kry_instellings(db=db, is_admin=True).sukses is True
        with pytest.raises(HTTPException, match="nie gevind"):
            instellings.kry_instelling("missing", db=db, is_admin=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            instellings.werk_instelling_by("missing", schemas.InstellingUpdate(Waarde="x"), db=db, is_admin=True)

    def test_koshuis_validation_status_and_delete_branches(self, db):
        from routers import koshuis

        admin = self._make_user(db, name="Admin", surname="House", email="house-branches@example.com", role_name="Administrateur")
        campus = models.Kampus(KAM_Naam="House Campus", KAM_Adres="Address")
        db.add(campus)
        db.flush()
        with pytest.raises(HTTPException, match="Koshuisnaam"):
            koshuis.skep_koshuis(schemas.KoshuisCreate(KOS_Naam=" ", KOS_Adres="A", KOS_Kapasiteit=1, Kampus_ID=campus.Kampus_ID), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Kapasiteit"):
            koshuis.skep_koshuis(schemas.KoshuisCreate(KOS_Naam="Bad", KOS_Adres="A", KOS_Kapasiteit=0, Kampus_ID=campus.Kampus_ID), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Kampus_ID"):
            koshuis.skep_koshuis(schemas.KoshuisCreate(KOS_Naam="Bad", KOS_Adres="A", KOS_Kapasiteit=1, Kampus_ID=99999), db=db, current_user=admin, is_admin=True)

        created = koshuis.skep_koshuis(schemas.KoshuisCreate(KOS_Naam="House One", KOS_Adres="A", KOS_Kapasiteit=2, Kampus_ID=campus.Kampus_ID), db=db, current_user=admin, is_admin=True)
        house_id = created.data.Koshuis_ID
        with pytest.raises(HTTPException, match="reeds in gebruik"):
            koshuis.skep_koshuis(schemas.KoshuisCreate(KOS_Naam="house one", KOS_Adres="B", KOS_Kapasiteit=1, Kampus_ID=campus.Kampus_ID), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            koshuis.opdateer_koshuis(99999, schemas.KoshuisUpdate(KOS_Naam="Missing"), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Kapasiteit"):
            koshuis.opdateer_koshuis(house_id, schemas.KoshuisUpdate(KOS_Kapasiteit=0), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            koshuis.kry_koshuis_status_detail(99999, db=db)

        resident = self._make_user(db, name="Resident", surname="House", email="resident-house@example.com", role_name="Student")
        db.add(models.Student(Gebruiker_ID=resident.Gebruiker_ID, STU_Nommer="HOUSE1", Koshuis_ID=house_id))
        db.flush()
        with pytest.raises(HTTPException, match="nog studente"):
            koshuis.verwyder_koshuis(house_id, db=db, current_user=admin, is_admin=True)
        db.query(models.Student).filter(models.Student.Gebruiker_ID == resident.Gebruiker_ID).delete()
        db.commit()
        assert koshuis.verwyder_koshuis(house_id, db=db, current_user=admin, is_admin=True).sukses is True

    def test_kampus_validation_and_delete_protection(self, db):
        from routers import kampus, nfc

        admin = self._make_user(db, name="Admin", surname="Campus", email="campus-branches@example.com", role_name="Administrateur")
        with pytest.raises(HTTPException, match="Kampusnaam"):
            kampus.skep_kampus(schemas.KampusCreate(KAM_Naam=" ", KAM_Adres="A"), db=db, current_user=admin, is_admin=True)
        created = kampus.skep_kampus(schemas.KampusCreate(KAM_Naam="Campus Branch", KAM_Adres="A"), db=db, current_user=admin, is_admin=True)
        campus_id = created.data.Kampus_ID
        with pytest.raises(HTTPException, match="reeds in gebruik"):
            kampus.skep_kampus(schemas.KampusCreate(KAM_Naam="campus branch", KAM_Adres="B"), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            kampus.opdateer_kampus(99999, schemas.KampusUpdate(KAM_Naam="Missing"), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Kampusnaam"):
            kampus.opdateer_kampus(campus_id, schemas.KampusUpdate(KAM_Naam=" "), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="lokale"):
            kampus.verwyder_kampus(campus_id, db=db, current_user=admin, is_admin=True)

        orphan = nfc.registreer_nfc_tag(
            schemas.NFCTagCreate(NFC_UID="ORPHAN-TAG", Gebruiker_ID=admin.Gebruiker_ID, NFC_Tipe="Gebruiker", NFC_Is_Aktief=True),
            db=db, current_user=admin, is_admin=True,
        )
        orphan_tag = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == "ORPHAN-TAG").first()
        orphan_tag.Lokasie_ID = None
        db.commit()
        with pytest.raises(HTTPException, match="klaskamer"):
            nfc.kry_lokasie_deur_nfc_uid("ORPHAN-TAG", db=db, current_user=admin)

    def test_klasse_admin_assignments_and_rosters(self, db):
        from routers import klasse

        admin = self._make_user(db, name="Admin", surname="Roster", email="roster-admin@example.com", role_name="Administrateur")
        student = self._make_user(db, name="Student", surname="Roster", email="roster-student@example.com", role_name="Student")
        personnel = self._make_user(db, name="Staff", surname="Roster", email="roster-staff@example.com", role_name="Personeel")
        db.add_all([
            models.Student(Gebruiker_ID=student.Gebruiker_ID, STU_Nommer="ROSTER-STU"),
            models.Personeel(Gebruiker_ID=personnel.Gebruiker_ID, PER_Nommer="ROSTER-PER"),
        ])
        db.flush()

        module = klasse.skep_module(schemas.ModuleCreate(MOD_Kode="ROSTER101", MOD_Naam="Roster Module"), db=db, _=True)
        module_id = module.data["Module_ID"]
        with pytest.raises(HTTPException, match="bestaan reeds"):
            klasse.skep_module(schemas.ModuleCreate(MOD_Kode="ROSTER101", MOD_Naam="Duplicate"), db=db, _=True)
        group = klasse.skep_groep(schemas.GroepCreate(GRO_Naam="Roster Group"), db=db, _=True)
        group_id = group.data["Groep_ID"]
        with pytest.raises(HTTPException, match="bestaan reeds"):
            klasse.skep_groep(schemas.GroepCreate(GRO_Naam="Roster Group"), db=db, _=True)
        klas = klasse.skep_klas(
            schemas.KlasCreate(Module_ID=module_id, KLA_Lokaal="R1", KLA_Dag="Maandag", KLA_Begin_Tyd="09:00", KLA_Eind_Tyd="10:00"),
            db=db, _=True,
        )
        klas_id = klas.data["Klas_ID"]
        with pytest.raises(HTTPException, match="nie gevind"):
            klasse.skep_klas(schemas.KlasCreate(Module_ID=99999, KLA_Lokaal="R", KLA_Dag="D", KLA_Begin_Tyd="09", KLA_Eind_Tyd="10"), db=db, _=True)

        assert klasse.koppel_groep_aan_klas(klas_id, schemas.KlasGroepAssign(Groep_ID=group_id), db=db, _=True).sukses is True
        klasse.koppel_groep_aan_klas(klas_id, schemas.KlasGroepAssign(Groep_ID=group_id), db=db, _=True)
        klasse.ken_student_groep_toe(student.Gebruiker_ID, schemas.StudentGroepAssign(Groep_ID=group_id), db=db, _=True)
        klasse.ken_student_module_toe(student.Gebruiker_ID, schemas.StudentModuleAssign(Module_ID=module_id), db=db, _=True)
        klasse.ken_student_klas_toe(student.Gebruiker_ID, schemas.StudentKlasAssign(Klas_ID=klas_id), db=db, _=True)
        klasse.ken_personeel_module_toe(personnel.Gebruiker_ID, schemas.PersoneelModuleAssign(Module_ID=module_id), db=db, _=True)
        klasse.ken_personeel_klas_toe(personnel.Gebruiker_ID, schemas.PersoneelKlasAssign(Klas_ID=klas_id), db=db, _=True)
        assert klasse.lys_modules(db=db, _=True).sukses is True
        assert klasse.lys_groepe(db=db, _=True).sukses is True
        assert klasse.lys_klasse(db=db, _=True).sukses is True
        assert klasse.lys_student_toewysings(db=db, _=True).sukses is True
        assert klasse.lys_personeel_modules(db=db, _=True).sukses is True
        assert klasse.resolver_student_rooster(db, student.Gebruiker_ID)
        assert klasse.resolver_personeel_rooster(db, personnel.Gebruiker_ID)
        assert klasse.resolver_klas_studente(db, klas_id)
        assert klasse.verwyder_student_groep(student.Gebruiker_ID, group_id, db=db, _=True).sukses is True
        assert klasse.verwyder_student_module(student.Gebruiker_ID, module_id, db=db, _=True).sukses is True
        assert klasse.verwyder_personeel_module(personnel.Gebruiker_ID, module_id, db=db, _=True).sukses is True

        request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}})
        with pytest.raises(HTTPException, match="net jou eie"):
            klasse.student_rooster(student.Gebruiker_ID, request=request, db=db, current_user=personnel)

    def test_klasse_csv_import_endpoints(self, db):
        from routers import klasse

        user = self._make_user(db, name="Import", surname="Student", email="import-student@example.com", role_name="Student")
        db.add(models.Student(Gebruiker_ID=user.Gebruiker_ID, STU_Nommer="IMP-STU"))
        module = models.Module(MOD_Kode="IMP101", MOD_Naam="Import Module")
        db.add(module)
        db.flush()

        roster_file = UploadFile(
            filename="roster.csv",
            file=io.BytesIO(b"End,Start,Dag,Lokaal,Groep,Module,From,To\n10:00,09:00,Maandag,R1,G1,NEW101,09:00,10:00\n10:00,09:00,Dinsdag,R2,G1,NEW101,09:00,10:00\n"),
        )
        imported = asyncio.run(klasse.importeer_klasse(roster_file, db=db, _=True))
        assert imported.sukses is True
        assert imported.data["modules_geskep"] == 1
        assert imported.data["klasse_geskep"] == 2
        assert imported.data["groepe_geskep"] == 1

        assignments = UploadFile(
            filename="students.csv",
            file=io.BytesIO(b"Studentenommer,Groep,Module\nIMP-STU,G1,IMP101;MISSING\nUNKNOWN,G2,IMP101\n"),
        )
        assigned = asyncio.run(klasse.importeer_student_toewysings(assignments, db=db, _=True))
        assert assigned.sukses is True
        assert assigned.data["studente_verwerk"] == 1
        assert assigned.data["groep_koppelings"] == 1
        assert any("bestaan nie" in error for error in assigned.data["foute"])
        assert any("nie gevind nie" in error for error in assigned.data["foute"])

        empty = UploadFile(filename="empty.csv", file=io.BytesIO(b"Groep,Module\nG1,M1\n"))
        empty_result = asyncio.run(klasse.importeer_student_toewysings(empty, db=db, _=True))
        assert empty_result.data["foute"]

    def test_wagte_routes(self, db):
        from routers import wagte
        import schemas

        admin = self._make_user(db, name="Admin", surname="User", email="guardadmin@example.com", role_name="Administrateur")
        campus = models.Kampus(KAM_Naam="Gate Campus", KAM_Adres="Gate Road")
        db.add(campus)
        db.flush()
        gate = models.Lokasie(LOK_Naam="Main Gate", LOK_Tipe="Kampus", Kampus_ID=campus.Kampus_ID)
        db.add(gate)
        db.flush()

        student_user = self._make_user(db, name="Stud", surname="Gate", email="gateuser@example.com", role_name="Student")
        db.add(models.Student(Gebruiker_ID=student_user.Gebruiker_ID, STU_Nommer="STU912", STU_Is_Koshuis=False))
        db.flush()

        access = wagte.sekuriteit_toegang_toets(current_user=admin, is_authorized=True)
        assert self._response_payload(access)["sukses"] is True

        campus_list = wagte.wagte_kampusse(db=db)
        assert self._response_payload(campus_list)["sukses"] is True

        scan_ok = wagte.wagte_nommer_check(nommer="STU912", db=db)
        scan_ok_payload = self._response_payload(scan_ok)
        assert scan_ok_payload["sukses"] is True
        assert scan_ok_payload["data"]["tipe"] == "STUDENT"

        visitor_list = wagte.opsigter_kampus_besoekers(kampus_id=campus.Kampus_ID, db=db)
        assert self._response_payload(visitor_list)["sukses"] is True

        profile_scan = wagte.wagte_profile_scan(data=schemas.WagteProfileScanRequest(scan_kode="STU912"), db=db)
        assert self._response_payload(profile_scan)["sukses"] is True

        verify = wagte.wagte_profile_verify(data=schemas.WagteProfileVerifyRequest(gebruiker_id=student_user.Gebruiker_ID, kampus_id=campus.Kampus_ID, rigting="IN", metode="QR"), db=db)
        assert self._response_payload(verify)["sukses"] is True

        decline = wagte.decline_profile_access(data=schemas.WagteProfileDeclineRequest(gebruiker_id=student_user.Gebruiker_ID, kampus_id=campus.Kampus_ID, metode="QR"), db=db)
        assert self._response_payload(decline)["sukses"] is True

    def test_saamry_error_branches(self, db):
        from routers import saamry

        user_a = self._make_user(db, name="A", surname="User", email="saamry-errors-a@example.com", role_name="Student")
        user_b = self._make_user(db, name="B", surname="User", email="saamry-errors-b@example.com", role_name="Student")
        user_c = self._make_user(db, name="C", surname="User", email="saamry-errors-c@example.com", role_name="Student")
        db.add_all([
            models.Student(Gebruiker_ID=user_a.Gebruiker_ID, STU_Nommer="ERR-A"),
            models.Student(Gebruiker_ID=user_b.Gebruiker_ID, STU_Nommer="ERR-B"),
            models.Student(Gebruiker_ID=user_c.Gebruiker_ID, STU_Nommer="ERR-C"),
        ])
        db.flush()

        assert saamry.get_saamry_status(db=db, current_user=user_a).sukses is True
        with pytest.raises(HTTPException, match="jouself"):
            saamry.send_friend_request(schemas.SaamryVriendVersoekCreate(ontvanger_id=user_a.Gebruiker_ID), db=db, current_user=user_a)
        with pytest.raises(HTTPException, match="nie gevind"):
            saamry.send_friend_request(schemas.SaamryVriendVersoekCreate(ontvanger_id=99999), db=db, current_user=user_a)

        first = saamry.send_friend_request(schemas.SaamryVriendVersoekCreate(ontvanger_id=user_b.Gebruiker_ID), db=db, current_user=user_a)
        friendship_id = first.data["vriendskap_id"]
        with pytest.raises(HTTPException, match="hangende"):
            saamry.send_friend_request(schemas.SaamryVriendVersoekCreate(ontvanger_id=user_b.Gebruiker_ID), db=db, current_user=user_a)
        with pytest.raises(HTTPException, match="aanvaar"):
            saamry.accept_friend_request(friendship_id, db=db, current_user=user_a)
        assert saamry.accept_friend_request(friendship_id, db=db, current_user=user_b).sukses is True
        with pytest.raises(HTTPException, match="reeds jou vriend"):
            saamry.send_friend_request(schemas.SaamryVriendVersoekCreate(ontvanger_id=user_b.Gebruiker_ID), db=db, current_user=user_a)
        assert saamry.remove_friend(user_b.Gebruiker_ID, db=db, current_user=user_a).sukses is True
        with pytest.raises(HTTPException, match="nie gevind"):
            saamry.remove_friend(user_b.Gebruiker_ID, db=db, current_user=user_a)

        group = saamry.create_group(
            schemas.SaamryGroepCreate(naam="", vertrekpunt="A", bestemming="B", vertrek_tyd=datetime.utcnow(), sitplekke=1),
            db=db, current_user=user_a,
        )
        group_id = group.data["groep_id"]
        with pytest.raises(HTTPException, match="bestuurder"):
            saamry.close_group(group_id, db=db, current_user=user_b)
        with pytest.raises(HTTPException, match="aanvaarde vriend"):
            saamry.invite_friend_to_group(group_id, schemas.SaamryGroepNooiCreate(gebruiker_id=user_c.Gebruiker_ID), db=db, current_user=user_a)
        with pytest.raises(HTTPException, match="bestuurder moet"):
            saamry.leave_group(group_id, db=db, current_user=user_a)
        with pytest.raises(HTTPException, match="nie gevind"):
            saamry.close_group(99999, db=db, current_user=user_a)
        assert saamry.close_group(group_id, db=db, current_user=user_a).sukses is True
        with pytest.raises(HTTPException, match="reeds gesluit"):
            saamry.close_group(group_id, db=db, current_user=user_a)

    def test_saamry_routes_and_helpers(self, db):
        from routers import saamry
        import schemas

        kampus = models.Kampus(KAM_Naam="Saamry Campus", KAM_Adres="Saamry Rd")
        db.add(kampus)
        db.flush()
        db.add(models.Lokasie(LOK_Naam="Main Gate", LOK_Tipe="Kampus", Kampus_ID=kampus.Kampus_ID))
        db.flush()

        user_a = self._make_user(db, name="User", surname="A", email="a@example.com", role_name="Student")
        user_b = self._make_user(db, name="User", surname="B", email="b@example.com", role_name="Student")
        user_c = self._make_user(db, name="User", surname="C", email="c@example.com", role_name="Personeel")
        db.add(models.Student(Gebruiker_ID=user_a.Gebruiker_ID, STU_Nommer="STU100", STU_Is_Koshuis=False))
        db.add(models.Student(Gebruiker_ID=user_b.Gebruiker_ID, STU_Nommer="STU101", STU_Is_Koshuis=False))
        db.add(models.Personeel(Gebruiker_ID=user_c.Gebruiker_ID, PER_Nommer="PER100", PER_Departement="IT"))
        db.flush()

        assert saamry._require_saamry_user(db, user_a) is None
        assert saamry._friendship_status(None, user_a.Gebruiker_ID) == "GEEN"

        request = saamry.send_friend_request(payload=schemas.SaamryVriendVersoekCreate(ontvanger_id=user_b.Gebruiker_ID), db=db, current_user=user_a)
        assert self._response_payload(request)["sukses"] is True

        status = saamry.get_saamry_status(db=db, current_user=user_a)
        assert self._response_payload(status)["sukses"] is True

        search = saamry.search_saamry_users(q="User", db=db, current_user=user_a)
        assert self._response_payload(search)["sukses"] is True

        friendship = db.query(models.SaamryVriendskap).filter(models.SaamryVriendskap.Versoeker_ID == user_a.Gebruiker_ID).first()
        accept = saamry.accept_friend_request(vriendskap_id=friendship.Vriendskap_ID, db=db, current_user=user_b)
        assert self._response_payload(accept)["sukses"] is True

        group = saamry.create_group(payload=schemas.SaamryGroepCreate(naam="Trip", vertrekpunt="Main", bestemming="Campus", vertrek_tyd=datetime.utcnow(), sitplekke=2), db=db, current_user=user_a)
        group_payload = self._response_payload(group)
        assert group_payload["sukses"] is True
        groep_id = group_payload["data"]["groep_id"]

        invite = saamry.invite_friend_to_group(groep_id=groep_id, payload=schemas.SaamryGroepNooiCreate(gebruiker_id=user_b.Gebruiker_ID), db=db, current_user=user_a)
        assert self._response_payload(invite)["sukses"] is True

        accept_invite = saamry.accept_group_invite(groep_id=groep_id, db=db, current_user=user_b)
        assert self._response_payload(accept_invite)["sukses"] is True

        close_group = saamry.close_group(groep_id=groep_id, db=db, current_user=user_a)
        assert self._response_payload(close_group)["sukses"] is True

        preview = saamry.gate_group_preview(payload=schemas.SaamryHekPreviewRequest(bestuurder_id=user_a.Gebruiker_ID, kampus_id=kampus.Kampus_ID, rigting="IN"), db=db, current_user=user_c, _security=None)
        assert self._response_payload(preview)["sukses"] is True

    def test_events_and_public_rsvp_routes(self, db):
        from routers import events, wagte
        import schemas

        admin = self._make_user(db, name="Event", surname="Admin", email="eventadmin@example.com", role_name="Administrateur")
        campus = models.Kampus(KAM_Naam="Event Campus", KAM_Adres="3 Event Rd")
        db.add(campus)
        db.flush()
        lok = models.Lokasie(LOK_Naam="Hall A", LOK_Tipe="Klaskamer", Kampus_ID=campus.Kampus_ID)
        db.add(lok)
        db.flush()

        user = self._make_user(db, name="Student", surname="Event", email="eventstudent@example.com", role_name="Student")
        db.add(models.Student(Gebruiker_ID=user.Gebruiker_ID, STU_Nommer="STU200", STU_Is_Koshuis=False))
        db.flush()

        created = events.create_event(
            payload=schemas.EventCreateRequest(
                naam="Demo Event",
                kampus_id=campus.Kampus_ID,
                lokasie_id=lok.Lokasie_ID,
                begin_tyd=datetime.utcnow() - timedelta(minutes=30),
                eind_tyd=datetime.utcnow() + timedelta(hours=2),
                kapasiteit=2,
                beskrywing="Fun",
            ),
            db=db,
            current_user=admin,
        )
        created_payload = self._response_payload(created)
        assert created_payload["sukses"] is True
        event_id = created_payload["data"]["event_id"]

        listed = events.list_events(view="komende", limit=10, db=db, current_user=admin)
        assert self._response_payload(listed)["sukses"] is True

        updated = events.update_event(
            event_id=event_id,
            payload=schemas.EventUpdateRequest(naam="Updated Event", kapasiteit=3),
            db=db,
            current_user=admin,
        )
        assert self._response_payload(updated)["sukses"] is True

        share = events.share_event(event_id=event_id, db=db, current_user=admin)
        share_payload = self._response_payload(share)
        assert share_payload["sukses"] is True

        rsvp = events.rsvp_event(event_id=event_id, payload=schemas.EventRsvpRequest(status="GAAN"), db=db, current_user=user)
        assert self._response_payload(rsvp)["sukses"] is True

        item = events.event_rsvps(event_id=event_id, db=db, current_user=admin)
        assert self._response_payload(item)["sukses"] is True

        attendance = events.event_attendance(event_id=event_id, db=db, current_user=admin)
        assert self._response_payload(attendance)["sukses"] is True

        cancelled = events.cancel_rsvp(event_id=event_id, db=db, current_user=user)
        assert self._response_payload(cancelled)["sukses"] is True

        public = events.public_event_rsvp(
            share_token=share_payload["data"]["share_token"],
            payload=schemas.PublicEventRsvpRequest(naam="Public", van="Guest", selfoon="+27123456789", epos="guest@example.com"),
            db=db,
        )
        public_payload = self._response_payload(public)
        assert public_payload["sukses"] is True

        event_data = events.public_event_data(share_token=share_payload["data"]["share_token"], db=db)
        assert self._response_payload(event_data)["sukses"] is True

        html = events.public_event_page(share_token=share_payload["data"]["share_token"], db=db)
        assert html.status_code == 200

        restore = events.restore_public_event_rsvp(share_token=share_payload["data"]["share_token"], qr_token=public_payload["data"]["qr_token"], db=db)
        assert self._response_payload(restore)["sukses"] is True

        guest_scan = wagte.wagte_event_guest_scan(
            data=schemas.WagteEventGuestScanRequest(scan_kode=f"MOON-EVENT:{public_payload['data']['qr_token']}", kampus_id=campus.Kampus_ID),
            db=db,
            current_user=admin,
            is_authorized=True,
        )
        assert self._response_payload(guest_scan)["sukses"] is True

        confirm = wagte.wagte_event_guest_confirm(
            data=schemas.WagteEventGuestConfirmRequest(publiek_rsvp_id=public_payload["data"]["publiek_rsvp_id"], kampus_id=campus.Kampus_ID, rigting="IN", metode="QR"),
            db=db,
            current_user=admin,
            is_authorized=True,
        )
        assert self._response_payload(confirm)["sukses"] is True

        cancel_public = events.cancel_public_rsvp_by_opsigter(event_id=event_id, publiek_rsvp_id=public_payload["data"]["publiek_rsvp_id"], db=db, current_user=admin)
        assert self._response_payload(cancel_public)["sukses"] is True

        events.cancel_event(event_id=event_id, db=db, current_user=admin)

    def test_gebruikers_crud_and_status_routes(self, db):
        from routers import gebruikers

        admin = self._make_user(db, name="Admin", surname="User", email="users-admin@example.com", role_name="Administrateur")
        role = self._ensure_role(db, "Student")
        payload = schemas.UserCreate(
            GEB_Naam="New",
            GEB_Van="Student",
            GEB_ID_Nommer="9001010000999",
            GEB_Epos="new-student@example.com",
            GEB_Wagwoord="Secret123!",
            Rol_ID=role.Rol_ID,
            STU_Nommer="STU0099",
        )

        created = gebruikers.skep_gebruiker(payload, db=db, current_user=admin, is_admin=True)
        created_data = self._response_payload(created)["data"]
        user_id = created_data["Gebruiker_ID"]
        assert created_data["GEB_Epos"] == "new-student@example.com"

        listed = gebruikers.lees_gebruikers(db=db, current_user=admin, is_authorized=True)
        assert any(item["Gebruiker_ID"] == user_id for item in self._response_payload(listed)["data"])
        assert self._response_payload(gebruikers.lees_gebruiker(user_id, db=db, current_user=admin, is_authorized=True))["sukses"]

        updated = gebruikers.opdateer_gebruiker(
            user_id,
            schemas.UserUpdate(GEB_Naam="Updated", GEB_Wagwoord="New-secret1"),
            db=db,
            current_user=admin,
            is_admin=True,
        )
        assert self._response_payload(updated)["data"]["GEB_Naam"] == "Updated"

        disabled = gebruikers.opdateer_gebruiker_status(
            user_id=user_id,
            update=schemas.GebruikerStatusUpdate(Is_Aktief=False),
            db=db,
            current_user=admin,
            is_admin=True,
        )
        assert self._response_payload(disabled)["data"]["is_aktief"] is False
        assert db.query(models.Waarskuwings).filter(models.Waarskuwings.Gebruiker_ID == user_id).count() == 1

        reenabled = gebruikers.opdateer_gebruiker_status(
            user_id=user_id,
            is_aktief=True,
            db=db,
            current_user=admin,
            is_admin=True,
        )
        assert self._response_payload(reenabled)["data"]["is_aktief"] is True
        with pytest.raises(HTTPException, match="jou eie rekening"):
            gebruikers.verwyder_gebruiker(admin.Gebruiker_ID, db=db, current_user=admin, is_admin=True)

    def test_gebruikers_security_and_validation_branches(self, db):
        from routers import gebruikers

        admin = self._make_user(db, name="Admin", surname="User", email="users-branches-admin@example.com", role_name="Administrateur")
        student_role = self._ensure_role(db, "Student")

        created = gebruikers.skep_gebruiker(
            schemas.UserCreate(
                GEB_Naam="Generated", GEB_Van="Id", GEB_ID_Nommer="9001010000997",
                GEB_Epos="generated@example.com", GEB_Wagwoord="Secret123!", Rol_ID=student_role.Rol_ID,
                STU_Nommer="STU0097",
            ), db=db, current_user=admin, is_admin=True,
        )
        user_id = created.data["Gebruiker_ID"]
        with pytest.raises(HTTPException, match="nie gevind"):
            gebruikers.lees_gebruiker(99999, db=db, current_user=admin, is_authorized=True)
        with pytest.raises(HTTPException, match="nie gevind"):
            gebruikers.opdateer_gebruiker(99999, schemas.UserUpdate(GEB_Naam="Missing"), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Ten minste een rol"):
            gebruikers.opdateer_gebruiker(user_id, schemas.UserUpdate(Rol_IDs=[]), db=db, current_user=admin, is_admin=True)
        with pytest.raises(HTTPException, match="Geen 'Is_Aktief'"):
            gebruikers.opdateer_gebruiker_status(user_id=user_id, db=db, current_user=admin, is_admin=True)

        guard = self._make_user(db, name="Guard", surname="User", email="users-branches-guard@example.com", role_name="Sekuriteit_Wag")
        security_list = gebruikers.lees_gebruikers(db=db, current_user=guard, is_authorized=True)
        assert "GEB_Epos" not in security_list.data[0]
        security_detail = gebruikers.lees_gebruiker(user_id, db=db, current_user=guard, is_authorized=True)
        assert "GEB_Epos" not in security_detail.data

        campus = models.Kampus(KAM_Naam="Guard Campus", KAM_Adres="Address")
        db.add(campus)
        db.flush()
        opsigter = self._make_user(db, name="Opsigter", surname="User", email="users-branches-ops@example.com", role_name="Kampus_Opsigter")
        db.flush()
        with pytest.raises(HTTPException, match="nie aan 'n kampus"):
            gebruikers.lees_gebruikers(db=db, current_user=opsigter, is_authorized=True)

    def test_lokasie_crud_attendance_and_nfc_routes(self, db):
        from routers import lokasie

        admin = self._make_user(db, name="Admin", surname="User", email="location-admin@example.com", role_name="Administrateur")
        campus = models.Kampus(KAM_Naam="Location Campus", KAM_Adres="1 Test Road")
        db.add(campus)
        db.flush()

        created = lokasie.skep_lokasie(
            schemas.LokasieCreate(LOK_Naam="Room 1", LOK_Tipe="Klaskamer", Kampus_ID=campus.Kampus_ID),
            db=db,
            current_user=admin,
            is_admin=True,
        )
        room_id = self._response_payload(created)["data"].Lokasie_ID
        listed = lokasie.lys_lokasies(db=db, current_user=admin)
        assert any(item["Lokasie_ID"] == room_id and item["NFC_UID"] for item in self._response_payload(listed)["data"])
        assert self._response_payload(lokasie.lys_klasse(db=db, current_user=admin))["data"]

        student_a = self._make_user(db, name="Present", surname="Student", email="present@example.com", role_name="Student")
        student_b = self._make_user(db, name="Absent", surname="Student", email="absent@example.com", role_name="Student")
        db.add_all([
            models.Student(Gebruiker_ID=student_a.Gebruiker_ID, STU_Nommer="STU1001"),
            models.Student(Gebruiker_ID=student_b.Gebruiker_ID, STU_Nommer="STU1002"),
            models.ToegangsLogs(Gebruiker_ID=student_a.Gebruiker_ID, Lokasie_ID=room_id, TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()),
            models.ToegangsLogs(Gebruiker_ID=student_b.Gebruiker_ID, Lokasie_ID=room_id, TOE_Rigting="UIT", TOE_Metode="NFC", TOE_Tydstempel=datetime.utcnow()),
        ])
        db.flush()

        roster = lokasie.kry_klas_roster(room_id, db=db, current_user=admin)
        assert len(self._response_payload(roster)["data"]) == 2
        attendance = lokasie.kry_klas_bywoning(room_id, date=datetime.utcnow().date().isoformat(), db=db, current_user=admin)
        attendance_data = self._response_payload(attendance)["data"]
        assert attendance_data["Present_Count"] == 1
        assert len(attendance_data["Absent"]) == 1

        updated = lokasie.opdateer_lokasie(room_id, schemas.LokasieUpdate(LOK_Naam="Room Updated"), db=db, current_user=admin, is_admin=True)
        assert self._response_payload(updated)["data"].LOK_Naam == "Room Updated"
        linked = lokasie.koppel_nfc_tag_aan_lokasie(
            schemas.NFCTagCreate(NFC_UID="ROOM-TAG", Lokasie_ID=room_id, NFC_Tipe="Lokasie", NFC_Is_Aktief=True),
            db=db,
            current_user=admin,
            is_admin=True,
        )
        assert self._response_payload(linked)["data"].NFC_UID == "ROOM-TAG"
        with pytest.raises(HTTPException, match="Ongeldige datumformaat"):
            lokasie.kry_klas_bywoning(room_id, date="bad-date", db=db, current_user=admin)
        with pytest.raises(HTTPException, match="toegangslogs"):
            lokasie.verwyder_lokasie(room_id, db=db, current_user=admin, is_admin=True)

        new_class = lokasie.skep_klas_met_nfc(
            schemas.KlasSkep(LOK_Naam="Room 2", LOK_Tipe="Klaskamer", Kampus_ID=campus.Kampus_ID, NFC_UID="ignored", NFC_Tipe="Lokasie"),
            db=db,
            current_user=admin,
            is_admin=True,
        )
        assert self._response_payload(new_class)["data"]["lokasie"]["LOK_Naam"] == "Room 2"
