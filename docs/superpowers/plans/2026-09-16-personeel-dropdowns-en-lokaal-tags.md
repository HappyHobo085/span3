# Personeel-dropdowns & lokaal-tag-koppeling — Implementeringsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Splits die personeel-bladsy se klas-keuse in module- en dag-dropdowns, laat admins 'n NFC-tag-UID aan 'n lokaal koppel, en wys elke student se laaste werklike inskandering in die klasregister.

**Architecture:** Drie onafhanklike dele. (1) Suiwer frontend-herstrukturering van `personeel.js` se keuselys. (2) Nuwe `PUT /lokasies/{id}/nfc-tag`-endpoint plus 'n UID-veld in die admin-lokaal-venster; `POST /lokasies/klasse` aanvaar voortaan 'n verskafte UID. (3) `resolver_klas_studente` kry 'n groepsquery oor `toegangs_logs` en gee `Laaste_Skandering` per student terug; `personeel.js` wys dit.

**Tech Stack:** FastAPI + SQLAlchemy (Backend), vanilla JS (Webwerf), pytest (file-based sqlite via bestaande fixtures).

**Spec:** `docs/superpowers/specs/2026-09-16-personeel-dropdowns-en-lokaal-tags-design.md`

**Belangrike omgewing-nota vir toetse:** die wortel-`.env` stel `DISABLE_AUTH=1`; loop toetse ALTYD met die omgewingsveranderlike `DISABLE_AUTH=0`, vanuit die `Backend/`-gids. Daar is 9 bekende, vooraf-bestaande falings in `tests/test_backend_helpers.py` (ongepinde nuutste FastAPI/Starlette op Python 3.14) — dié tel nie as regressies nie.

---

### Task 1: Backend — `Laaste_Skandering` in die klasregister

**Files:**
- Modify: `Backend/routers/klasse.py` (imports bo; `resolver_klas_studente` ± reël 248–310)
- Test: `Backend/tests/test_klasse.py` (voeg 'n klas by onderaan)

- [ ] **Step 1: Skryf die falende toetse**

Voeg onderaan `Backend/tests/test_klasse.py` by:

```python
class TestLaasteSkandering:
    """resolver_klas_studente se Laaste_Skandering-veld (jongste IN-log vandag)."""

    def _maak_student(self, db, n):
        rol = db.query(models.Rolle).filter(models.Rolle.ROL_Naam == "Student").first()
        if not rol:
            rol = models.Rolle(ROL_Naam="Student")
            db.add(rol)
            db.flush()
        gebruiker = models.Gebruikers(
            GEB_Naam="Toets",
            GEB_Van=f"Student{n}",
            GEB_ID_Nommer=f"900101000010{n}",
            GEB_Epos=f"skandering{n}@voorbeeld.co.za",
            GEB_Wagwoord="hashed",
            Rol_ID=rol.Rol_ID,
        )
        db.add(gebruiker)
        db.flush()
        return gebruiker

    def _maak_lokaal(self, db, naam):
        kampus = db.query(models.Kampus).first()
        if not kampus:
            kampus = models.Kampus(KAM_Naam="Hoofkampus")
            db.add(kampus)
            db.flush()
        lokaal = models.Lokasie(LOK_Naam=naam, LOK_Tipe="Klaskamer", Kampus_ID=kampus.Kampus_ID)
        db.add(lokaal)
        db.flush()
        return lokaal

    def _log(self, db, gebruiker, lokaal, rigting, tydstempel):
        db.add(models.ToegangsLogs(
            Gebruiker_ID=gebruiker.Gebruiker_ID,
            Lokasie_ID=lokaal.Lokasie_ID,
            TOE_Rigting=rigting,
            TOE_Metode="NFC",
            TOE_Tydstempel=tydstempel,
        ))
        db.flush()

    def _register(self, db, klas):
        return {s["Gebruiker_ID"]: s for s in resolver_klas_studente(db, klas.Klas_ID)}

    def test_jongste_in_log_vandag_word_teruggegee(self, db):
        from datetime import datetime, timedelta
        module = skep_module(db, "SKND100")
        klas = skep_klas(db, module)
        student = self._maak_student(db, 1)
        db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        vroeg = self._maak_lokaal(db, "Ou Lokaal")
        laat = self._maak_lokaal(db, "Bitterbessie")
        nou = datetime.utcnow()
        self._log(db, student, vroeg, "IN", nou - timedelta(minutes=90))
        self._log(db, student, laat, "IN", nou - timedelta(minutes=5))

        info = self._register(db, klas)[student.Gebruiker_ID]["Laaste_Skandering"]
        assert info is not None
        assert info["lokaal"] == "Bitterbessie"
        assert info["tyd"].endswith("Z")

    def test_geen_logs_gee_none(self, db):
        module = skep_module(db, "SKND200")
        klas = skep_klas(db, module)
        student = self._maak_student(db, 2)
        db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))

        assert self._register(db, klas)[student.Gebruiker_ID]["Laaste_Skandering"] is None

    def test_gister_en_uit_logs_tel_nie(self, db):
        from datetime import datetime, timedelta
        module = skep_module(db, "SKND300")
        klas = skep_klas(db, module)
        student = self._maak_student(db, 3)
        db.add(models.Student_Klas(Gebruiker_ID=student.Gebruiker_ID, Klas_ID=klas.Klas_ID))
        lokaal = self._maak_lokaal(db, "Gister Lokaal")
        nou = datetime.utcnow()
        self._log(db, student, lokaal, "IN", nou - timedelta(days=1, hours=1))
        self._log(db, student, lokaal, "UIT", nou - timedelta(minutes=10))

        assert self._register(db, klas)[student.Gebruiker_ID]["Laaste_Skandering"] is None
```

- [ ] **Step 2: Loop die toetse — hulle moet faal**

Run (vanuit `Backend/`): `DISABLE_AUTH=0 python -m pytest tests/test_klasse.py::TestLaasteSkandering -q`
Expected: 3 FAILED met `KeyError: 'Laaste_Skandering'`

- [ ] **Step 3: Implementeer**

In `Backend/routers/klasse.py`, voeg by die imports bo (na `import csv` / `import io`):

```python
from datetime import datetime
```

Voeg net bo `resolver_klas_studente` hierdie helper by:

```python
def _laaste_skanderings_vandag(db: Session, gebruiker_ids: set[int]) -> dict[int, dict]:
    """Jongste 'IN'-skandering van vandag (UTC-dag) per gebruiker.

    Een groepsquery; die frontend formateer die ISO-UTC-tydstempel na
    plaaslike tyd sodat personeel nie UTC sien nie.
    """
    if not gebruiker_ids:
        return {}
    vandag_begin = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rye = (
        db.query(models.ToegangsLogs, models.Lokasie.LOK_Naam)
        .outerjoin(models.Lokasie, models.Lokasie.Lokasie_ID == models.ToegangsLogs.Lokasie_ID)
        .filter(
            models.ToegangsLogs.Gebruiker_ID.in_(gebruiker_ids),
            models.ToegangsLogs.TOE_Rigting == "IN",
            models.ToegangsLogs.TOE_Tydstempel >= vandag_begin,
        )
        .order_by(models.ToegangsLogs.TOE_Tydstempel.desc())
        .all()
    )
    resultaat: dict[int, dict] = {}
    for log, lok_naam in rye:
        if log.Gebruiker_ID not in resultaat:
            resultaat[log.Gebruiker_ID] = {
                "lokaal": lok_naam,
                "tyd": log.TOE_Tydstempel.isoformat() + "Z",
            }
    return resultaat
```

Verander die einde van `resolver_klas_studente` (die return-blok wat tans die lys dicts bou) na:

```python
    skanderings = _laaste_skanderings_vandag(db, gebruiker_ids)
    return [
        {
            "Gebruiker_ID": gebruiker.Gebruiker_ID,
            "GEB_Naam": gebruiker.GEB_Naam,
            "GEB_Van": gebruiker.GEB_Van,
            "STU_Nommer": student.STU_Nommer if student else None,
            "Laaste_Skandering": skanderings.get(gebruiker.Gebruiker_ID),
        }
        for gebruiker, student in rye
    ]
```

- [ ] **Step 4: Loop die toetse — alles moet slaag**

Run: `DISABLE_AUTH=0 python -m pytest tests/test_klasse.py -q`
Expected: alles PASS (geen regressies in die bestaande klasse-toetse nie)

- [ ] **Step 5: Commit**

```bash
git add Backend/routers/klasse.py Backend/tests/test_klasse.py
git commit -m "feat(klasregister): wys elke student se laaste IN-skandering van vandag"
```

---

### Task 2: Backend — `PUT /lokasies/{id}/nfc-tag`

**Files:**
- Modify: `Backend/schemas.py` (naby die Lokasie-schemas, ± reël 272)
- Modify: `Backend/routers/lokasie.py` (nuwe endpoint onderaan, naby `POST /nfc-tags`)
- Test: Create `Backend/tests/test_lokasie_nfc_tag.py`

- [ ] **Step 1: Skryf die falende toetse**

Skep `Backend/tests/test_lokasie_nfc_tag.py`:

```python
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
```

- [ ] **Step 2: Loop die toetse — hulle moet faal**

Run: `DISABLE_AUTH=0 python -m pytest tests/test_lokasie_nfc_tag.py -q`
Expected: FAIL — die PUT-roete bestaan nie (405/404-antwoorde)

- [ ] **Step 3: Implementeer**

In `Backend/schemas.py`, direk ná die `Lokasie`-klas (± reël 276), voeg by:

```python
class LokasieNFCTagUpdate(BaseModel):
    """Body vir PUT /lokasies/{id}/nfc-tag: die nuwe fisiese tag-UID."""
    NFC_UID: str
```

In `Backend/routers/lokasie.py`, onderaan (ná `koppel_nfc_tag_aan_lokasie`), voeg by:

```python
@router.put("/lokasies/{lokasie_id}/nfc-tag", response_model=schemas.APIResponse[schemas.NFCTag])
def stel_lokasie_nfc_tag(
    lokasie_id: int,
    tag_in: schemas.LokasieNFCTagUpdate,
    db: Session = Depends(get_db),
    current_user: models.Gebruikers = Depends(auth.get_current_user),
    is_admin: bool = Depends(auth.check_admin),
):
    """Hernoem die lokaal se aktiewe Lokasie-tag na 'n fisiese UID (bv. "L4").

    Doelbewus nie die generiese POST /nfc-tags-upsert nie: dié sou stilweg
    'n ander lokaal se tag kon skuif. Hier valideer ons eers uniekheid.
    """
    nuwe_uid = (tag_in.NFC_UID or "").strip()
    if not nuwe_uid:
        raise HTTPException(status_code=400, detail="NFC_UID mag nie leeg wees nie")

    lokasie = db.query(models.Lokasie).filter(models.Lokasie.Lokasie_ID == lokasie_id).first()
    if not lokasie:
        raise HTTPException(status_code=404, detail="Lokasie nie gevind nie")

    aktiewe = [t for t in (lokasie.nfc_tags or []) if t.NFC_Is_Aktief]
    tag = aktiewe[0] if aktiewe else None

    bestaande = db.query(models.NFC_Tags).filter(models.NFC_Tags.NFC_UID == nuwe_uid).first()
    if bestaande and (tag is None or bestaande.NFC_Tags_ID != tag.NFC_Tags_ID):
        raise HTTPException(
            status_code=409,
            detail=f"NFC-UID '{nuwe_uid}' is reeds aan 'n ander tag gekoppel",
        )

    if tag is None:
        tag = models.NFC_Tags(
            NFC_UID=nuwe_uid,
            Lokasie_ID=lokasie_id,
            NFC_Tipe="Lokasie",
            NFC_Is_Aktief=True,
        )
        db.add(tag)
    else:
        tag.NFC_UID = nuwe_uid
    db.commit()
    db.refresh(tag)
    return schemas.APIResponse(sukses=True, data=tag)
```

- [ ] **Step 4: Loop die toetse — alles moet slaag**

Run: `DISABLE_AUTH=0 python -m pytest tests/test_lokasie_nfc_tag.py -q`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add Backend/schemas.py Backend/routers/lokasie.py Backend/tests/test_lokasie_nfc_tag.py
git commit -m "feat(lokasie): PUT /lokasies/{id}/nfc-tag om 'n fisiese tag-UID te koppel"
```

---

### Task 3: Backend — `POST /klasse` aanvaar 'n verskafte UID

**Files:**
- Modify: `Backend/routers/lokasie.py` (`skep_klas_met_nfc`, ± reël 335)
- Test: `Backend/tests/test_lokasie_nfc_tag.py` (voeg klas by)

- [ ] **Step 1: Skryf die falende toetse**

Voeg onderaan `Backend/tests/test_lokasie_nfc_tag.py` by (selfde lêer; hergebruik die klas hierbo se patrone deur oorerwing):

```python
def _skep_payload(kampus_id, uid):
    return {
        "LOK_Naam": "Bitterbessie",
        "LOK_Tipe": "Klaskamer",
        "Kampus_ID": kampus_id,
        "NFC_UID": uid,
        "NFC_Tipe": "Lokasie",
    }


class TestSkepKlasMetUid:
    """POST /klasse: gebruik die verskafte UID; genereer as dit leeg/TEMP is."""

    def test_verskafte_uid_word_gebruik(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 7)
        kampus = maak_kampus(http_db)
        client = bou_client(http_db)

        resp = client.post(
            "/klasse",
            json=_skep_payload(kampus.Kampus_ID, "L4"),
            headers=headers_vir(admin),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["nfc_tag"]["NFC_UID"] == "L4"

    def test_temp_uid_word_gegenereer(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 8)
        kampus = maak_kampus(http_db)
        client = bou_client(http_db)

        resp = client.post(
            "/klasse",
            json=_skep_payload(kampus.Kampus_ID, "TEMP"),
            headers=headers_vir(admin),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["nfc_tag"]["NFC_UID"] != "TEMP"

    def test_gebruikte_uid_gee_409(self, http_db):
        admin = maak_gebruiker(http_db, "Administrateur", 9)
        kampus = maak_kampus(http_db)
        maak_lokaal(http_db, "Ander Lokaal", "L4")
        client = bou_client(http_db)

        resp = client.post(
            "/klasse",
            json=_skep_payload(kampus.Kampus_ID, "L4"),
            headers=headers_vir(admin),
        )
        assert resp.status_code == 409
```

- [ ] **Step 2: Loop die toetse — die eerste en derde moet faal**

Run: `DISABLE_AUTH=0 python -m pytest tests/test_lokasie_nfc_tag.py::TestSkepKlasMetUid -q`
Expected: `test_verskafte_uid_word_gebruik` en `test_gebruikte_uid_gee_409` FAIL (UID word tans altyd gegenereer); `test_temp_uid_word_gegenereer` PASS

- [ ] **Step 3: Implementeer**

In `skep_klas_met_nfc` (`Backend/routers/lokasie.py`), vervang die reël
`generated_uid = genereer_unieke_nfc_uid(db)` met:

```python
        gevraagde_uid = (klas_in.NFC_UID or "").strip()
        if gevraagde_uid and gevraagde_uid.upper() != "TEMP":
            bestaande = db.query(models.NFC_Tags).filter(
                models.NFC_Tags.NFC_UID == gevraagde_uid
            ).first()
            if bestaande:
                raise HTTPException(
                    status_code=409,
                    detail=f"NFC-UID '{gevraagde_uid}' is reeds aan 'n ander tag gekoppel",
                )
            generated_uid = gevraagde_uid
        else:
            generated_uid = genereer_unieke_nfc_uid(db)
```

Let op: die `except`-blok onder in dieselfde funksie laat `HTTPException` reeds deur (`except HTTPException: raise`), so die 409 oorleef die try/except.

- [ ] **Step 4: Loop die toetse — alles moet slaag**

Run: `DISABLE_AUTH=0 python -m pytest tests/test_lokasie_nfc_tag.py -q`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add Backend/routers/lokasie.py Backend/tests/test_lokasie_nfc_tag.py
git commit -m "feat(lokasie): POST /klasse gebruik die verskafte NFC-UID indien gegee"
```

---

### Task 4: Frontend — NFC-tag-veld in die admin-lokaal-venster

**Files:**
- Modify: `Webwerf/admin.html` (lokaal-venster ± reël 445–460; script-weergawes ± reël 469–471)
- Modify: `Webwerf/admin.js` (konstantes ± reël 35–40; `closeClassModal` ± reël 535; `openEditLokaalModal` ± reël 550; `addVenueRow`/`updateVenueRow` ± reël 830–880; `submitNewClass` ± reël 900–950; `loadVenues` ± reël 817)
- Modify: `Webwerf/website_api_calls.js` (na `updateLokasie`, ± reël 219)

Geen JS-toetsraamwerk bestaan in hierdie repo nie — verifikasie is 'n sintaks-kontrole plus handmatige toets (stap 7).

- [ ] **Step 1: Voeg die veld in `admin.html` by**

Vind die lokaal-venster se kampus-kiesveld (± reël 453):

```html
        <label for="class-kampus">Kies kampus</label>
        <select id="class-kampus">
```

en voeg ná daardie form-group se sluit-`</div>` 'n nuwe form-group by (selfde struktuur as die bestaandes):

```html
      <div class="form-group">
        <label for="class-tag-uid">NFC-tag UID (bv. L4)</label>
        <input id="class-tag-uid" type="text" placeholder="Los leeg om outomaties te genereer">
      </div>
```

- [ ] **Step 2: Voeg `updateLokasieTag` by `website_api_calls.js`**

Direk ná die `updateLokasie`-funksie (± reël 219):

```javascript
    /**
     * PUT /lokasies/{lokasieId}/nfc-tag  (slegs Admin)
     * Koppel/hernoem die lokaal se fisiese NFC-tag-UID.
     */
    updateLokasieTag: async function (lokasieId, nfcUid) {
      const r = await apiRequest('/lokasies/' + lokasieId + '/nfc-tag', {
        method: 'PUT',
        body: JSON.stringify({ NFC_UID: nfcUid }),
      });
      return r.body;
    },
```

- [ ] **Step 3: Werk `admin.js` by**

3a. By die konstantes (na `const classKampus = ...`, ± reël 39):

```javascript
  const classTagUid = document.getElementById('class-tag-uid');
```

3b. Vind die deklarasie `let editingLokaalId = null;` (soek daarna) en voeg langsaan by:

```javascript
  let editingLokaalOldUid = '';
```

3c. In `closeClassModal` (± reël 535), saam met die ander veld-skoonmaak:

```javascript
    if (classTagUid) classTagUid.value = '';
    editingLokaalOldUid = '';
```

3d. In `openEditLokaalModal` (± reël 550), saam met die ander veld-invul:

```javascript
    if (classTagUid) classTagUid.value = row.dataset.nfcUid || '';
    editingLokaalOldUid = row.dataset.nfcUid || '';
```

3e. `addVenueRow`: verander die funksie-handtekening na
`function addVenueRow(lokasieId, name, kampusId, lokasieType, nfcUid)` en voeg ná die kampus-`badge` by:

```javascript
    const tagBadge = document.createElement('span');
    tagBadge.className = 'campus-badge tag-badge';
    tagBadge.textContent = 'Tag: ' + (nfcUid || '—');
```

Voeg `row.dataset.nfcUid = nfcUid || '';` by die ander `row.dataset.*`-reëls, en
`row.appendChild(tagBadge);` direk ná `row.appendChild(badge);`.

3f. In `loadVenues` (± reël 823), gee die UID deur:

```javascript
      addVenueRow(lok.Lokasie_ID, lok.LOK_Naam, lok.Kampus_ID, lok.LOK_Tipe, lok.NFC_UID);
```

3g. `updateVenueRow`: verander die handtekening na
`function updateVenueRow(lokasieId, name, kampusId, nfcUid)` en voeg onderaan by:

```javascript
    const tagBadge = row.querySelector('.tag-badge');
    if (tagBadge) tagBadge.textContent = 'Tag: ' + (nfcUid || '—');
    row.dataset.nfcUid = nfcUid || '';
```

3h. Vervang die HELE edit-modus-blok in `submitNewClass` (die `if (editingLokaalId !== null) { ... return; }`-blok) met:

```javascript
    // ===== EDIT MODE =====
    // Ons wysig 'n bestaande lokaal: stuur die nuwe waardes na die bediener.
    if (editingLokaalId !== null) {
      const lokasieId = editingLokaalId;
      const json = await window.MoonApi.updateLokasie(lokasieId, {
        LOK_Naam: roomName,
        Kampus_ID: kampusId
      });

      if (!json || !json.sukses) {
        alert((json && json.fout) || (json && json.detail) || 'Kon nie lokaal opdateer nie.');
        return;
      }

      // Koppel/hernoem die NFC-tag as die UID verander het. Die venster bly
      // oop by 'n fout (bv. UID reeds in gebruik) sodat die admin kan regmaak.
      const nuweUid = classTagUid ? classTagUid.value.trim() : '';
      let finaleUid = editingLokaalOldUid;
      if (nuweUid && nuweUid !== editingLokaalOldUid) {
        const tagJson = await window.MoonApi.updateLokasieTag(lokasieId, nuweUid);
        if (!tagJson || !tagJson.sukses) {
          alert(foutBoodskap(tagJson, 'Kon nie die NFC-tag opdateer nie.'));
          return;
        }
        finaleUid = nuweUid;
      }

      alert('Lokaal suksesvol opgedateer.');
      closeClassModal();
      updateVenueRow(lokasieId, roomName, kampusId, finaleUid);
      applyVenueFilter();
      return;
    }
```

3i. In die create-modus van `submitNewClass`, verander die `createKlas`-payload se
`NFC_UID: 'TEMP',` na:

```javascript
      NFC_UID: (classTagUid && classTagUid.value.trim()) || 'TEMP',
```

en vervang die sukses-hantering se `addVenueRow`-oproep met:

```javascript
      const nuweId = json.data && json.data.lokasie ? json.data.lokasie.Lokasie_ID : '';
      const nuweUid = json.data && json.data.nfc_tag ? json.data.nfc_tag.NFC_UID : '';
      addVenueRow(nuweId, roomName, kampusId, 'Klaskamer', nuweUid);
```

en verander die create-modus se fout-alert na:

```javascript
      alert(foutBoodskap(json, 'Kon nie lokaal skep nie.'));
```

- [ ] **Step 4: Bump die script-weergawes in `admin.html`**

```html
  <script src="website_api_calls.js?v=20260916"></script>
  <script src="main.js?v=20260915"></script>
  <script src="admin.js?v=20260916"></script>
```

- [ ] **Step 5: Sintaks-kontrole**

Run (vanuit die repo-wortel): `node --check Webwerf/admin.js && node --check Webwerf/website_api_calls.js`
Expected: geen uitset (sukses). As `node` nie beskikbaar is nie, laai die bladsy in 'n blaaier en kyk vir konsole-foute (stap 7 hieronder dek dit).

- [ ] **Step 6: Commit**

```bash
git add Webwerf/admin.html Webwerf/admin.js Webwerf/website_api_calls.js
git commit -m "feat(admin): koppel 'n fisiese NFC-tag-UID aan 'n lokaal in die lokaal-venster"
```

- [ ] **Step 7: Handmatige verifikasie (na deploy of teen 'n plaaslike backend)**

1. Meld as admin aan, maak die lokale-paneel oop — elke ry wys "Tag: <uid>".
2. Wysig 'n lokaal, tik "L4", stoor — ry wys "Tag: L4".
3. Wysig 'n ander lokaal, tik weer "L4" — verwag 'n duidelike foutboodskap (409).
4. Skep 'n nuwe lokaal met 'n leë UID-veld — kry 'n outomaties gegenereerde tag.

---

### Task 5: Frontend — module- en dag-dropdowns op die personeel-bladsy

**Files:**
- Modify: `Webwerf/personeel.html` (± reël 24–28; script-weergawes ± reël 119–122)
- Modify: `Webwerf/personeel.js` (konstante ± reël 48; `klasVanApi` ± reël 108–132; `populateKlasSelect` ± reël 824–848; event wiring ± reël 877–884; bootstrap ± reël 925–948)

- [ ] **Step 1: Vervang die markup in `personeel.html`**

Vervang:

```html
      <div class="control-group">
        <label class="field-label" for="klas-select">Kies Klas</label>
        <select class="glass-select" id="klas-select" name="klas-select" style="width:260px"></select>
      </div>
```

met:

```html
      <div class="control-group">
        <label class="field-label" for="module-select">Kies Module</label>
        <select class="glass-select" id="module-select" name="module-select" style="width:260px"></select>
      </div>
      <div class="control-group">
        <label class="field-label" for="dag-select">Kies Dag</label>
        <select class="glass-select" id="dag-select" name="dag-select" style="width:260px"></select>
      </div>
```

- [ ] **Step 2: Werk `personeel.js` by — konstantes en `klasVanApi`**

2a. Vervang `var klasSelect = document.getElementById('klas-select');` (± reël 48) met:

```javascript
  var moduleSelect = document.getElementById('module-select');
  var dagSelect = document.getElementById('dag-select');
```

2b. In `klasVanApi`, voeg 'n dag-etiket by. Ná die bestaande `label`-bou:

```javascript
    // Etiket vir die dag-keuselys, bv. "Maandag 8:00–9:00 · GH117 A (50)"
    var dagLabel = wanneer;
    if (k.KLA_Lokaal) dagLabel = wanneer ? wanneer + ' · ' + k.KLA_Lokaal : k.KLA_Lokaal;
    if (!dagLabel) dagLabel = 'Tyd onbekend';
```

en voeg `dagLabel: dagLabel,` by die teruggegee objek (langs `label: label`).

- [ ] **Step 3: Vervang `populateKlasSelect` met module-/dag-funksies**

Vervang die hele `populateKlasSelect`-funksie (± reël 824–848) met:

```javascript
  // ----- Module- en dag-dropdowns -----
  // Unieke modulekodes uit die gelaaide klasse, in rooster-volgorde.
  function moduleKodes() {
    var kodes = [];
    klasse.forEach(function (k) {
      if (kodes.indexOf(k.kode) === -1) kodes.push(k.kode);
    });
    return kodes;
  }

  // Al die klas-sessies van een module, in dag/tyd-volgorde (klasse is
  // reeds so gesorteer).
  function sessiesVirModule(kode) {
    return klasse.filter(function (k) { return k.kode === kode; });
  }

  // Hierdie funksie vul die "Kies Module"-keuselys (of wys 'n enkele
  // gedeaktiveerde boodskap as daar niks is nie) en vul dan die dag-lys.
  function populateModuleSelect(boodskap) {
    if (!moduleSelect) return;
    moduleSelect.innerHTML = '';

    var kodes = moduleKodes();
    if (kodes.length === 0) {
      var leeg = document.createElement('option');
      leeg.value = '';
      leeg.textContent = boodskap || 'Geen klasse toegewys nie';
      leeg.disabled = true;
      leeg.selected = true;
      moduleSelect.appendChild(leeg);
      moduleSelect.disabled = true;
      populateDagSelect(null, boodskap || 'Geen klasse toegewys nie');
      return;
    }

    moduleSelect.disabled = false;
    kodes.forEach(function (kode) {
      var opt = document.createElement('option');
      opt.value = kode;
      var naam = sessiesVirModule(kode)[0].moduleNaam;
      opt.textContent = naam ? kode + ' — ' + naam : kode;
      moduleSelect.appendChild(opt);
    });
    if (currentKlas) moduleSelect.value = currentKlas.kode;
    populateDagSelect(moduleSelect.value);
  }

  // Hierdie funksie vul die "Kies Dag"-keuselys met die gekose module se
  // sessies.
  function populateDagSelect(kode, boodskap) {
    if (!dagSelect) return;
    dagSelect.innerHTML = '';

    var sessies = kode ? sessiesVirModule(kode) : [];
    if (sessies.length === 0) {
      var leeg = document.createElement('option');
      leeg.value = '';
      leeg.textContent = boodskap || 'Geen dae nie';
      leeg.disabled = true;
      leeg.selected = true;
      dagSelect.appendChild(leeg);
      dagSelect.disabled = true;
      return;
    }

    dagSelect.disabled = false;
    sessies.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = k.id;
      opt.textContent = k.dagLabel;
      dagSelect.appendChild(opt);
    });
    if (currentKlas && currentKlas.kode === kode) dagSelect.value = currentKlas.id;
  }
```

- [ ] **Step 4: Vervang die event wiring**

Vervang die `if (klasSelect) { ... }`-blok (± reël 877–884) met:

```javascript
  // As die gebruiker 'n ander module kies, wys sy eerste sessie se data.
  if (moduleSelect) {
    moduleSelect.addEventListener('change', function () {
      populateDagSelect(moduleSelect.value);
      var eerste = sessiesVirModule(moduleSelect.value)[0];
      if (eerste) kiesKlas(eerste);
    });
  }

  // As die gebruiker 'n ander dag/sessie kies, wys daardie sessie se data.
  if (dagSelect) {
    dagSelect.addEventListener('change', function () {
      var gekies = klasse.filter(function (k) {
        return k.id === dagSelect.value;
      })[0];
      if (gekies) kiesKlas(gekies);
    });
  }
```

- [ ] **Step 5: Werk die bootstrap by**

In die `DOMContentLoaded`-hanteerder: vervang `populateKlasSelect('Laai klasse...');` met `populateModuleSelect('Laai klasse...');`, vervang die `populateKlasSelect();` ná `klasse = lys;` met `populateModuleSelect();`, en vervang `populateKlasSelect('Kon nie klasse laai nie');` in die catch met `populateModuleSelect('Kon nie klasse laai nie');`.

- [ ] **Step 6: Kontroleer dat geen `klasSelect`-verwysings oorbly nie**

Run: `grep -n "klasSelect" Webwerf/personeel.js`
Expected: geen uitset

Run: `node --check Webwerf/personeel.js`
Expected: geen uitset (sukses)

- [ ] **Step 7: Bump die script-weergawe in `personeel.html`**

```html
  <script src="personeel.js?v=20260916"></script>
```

- [ ] **Step 8: Commit**

```bash
git add Webwerf/personeel.html Webwerf/personeel.js
git commit -m "feat(personeel): splits klas-keuse in module- en dag-dropdowns"
```

---

### Task 6: Frontend — laaste skandering in die klasregister

**Files:**
- Modify: `Webwerf/personeel.js` (`studentVanApi` ± reël 135–142; `renderRoster` ± reël 768; nuwe helper)
- Modify: `Webwerf/personeel.html` (script-weergawe reeds gebump in Task 5 — geen verdere verandering nie)

- [ ] **Step 1: Neem die veld in `studentVanApi` op**

Voeg `laasteSkandering: s.Laaste_Skandering || null` by die teruggegee objek:

```javascript
  function studentVanApi(s) {
    return {
      id: s.Gebruiker_ID,
      naam: s.GEB_Naam || '',
      van: s.GEB_Van || '',
      nommer: s.STU_Nommer || ('#' + s.Gebruiker_ID),
      laasteSkandering: s.Laaste_Skandering || null
    };
  }
```

- [ ] **Step 2: Voeg 'n formatteringshelper by**

Direk ná `studentVanApi`:

```javascript
  // Hierdie funksie formateer 'n student se laaste inskandering, bv.
  // "Bitterbessie · 09:14" (plaaslike tyd), of 'n verstek-boodskap.
  function formatSkandering(sk) {
    if (!sk || !sk.tyd) return 'Geen skandering vandag';
    var d = new Date(sk.tyd);
    var tyd = '';
    if (!isNaN(d.getTime())) {
      tyd = (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' +
            (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
    }
    return [sk.lokaal, tyd].filter(Boolean).join(' · ') || 'Geen skandering vandag';
  }
```

- [ ] **Step 3: Wys dit in `renderRoster`**

In `renderRoster`, vervang `var card = createStudentCard(s, s.nommer);` met:

```javascript
      var card = createStudentCard(s, s.nommer + ' · ' + formatSkandering(s.laasteSkandering));
```

- [ ] **Step 4: Sintaks-kontrole**

Run: `node --check Webwerf/personeel.js`
Expected: geen uitset (sukses)

- [ ] **Step 5: Commit**

```bash
git add Webwerf/personeel.js
git commit -m "feat(personeel): wys elke student se laaste inskandering in die klasregister"
```

---

### Task 7: Finale verifikasie en push

- [ ] **Step 1: Loop die volle backend-toetssuite**

Run (vanuit `Backend/`): `DISABLE_AUTH=0 python -m pytest tests/ -q`
Expected: al die klasse-/lokasie-toetse slaag; slegs die 9 bekende vooraf-bestaande falings in `tests/test_backend_helpers.py` mag oorbly.

- [ ] **Step 2: Kontroleer die diff teen die spec**

Run: `git log --oneline -8` en `git diff origin/main --stat`
Expected: 5 commits (Task 1, 2, 3, 4, 5+6), net die lêers in hierdie plan geraak.

- [ ] **Step 3: Push na albei remotes (Railway deploy vanaf GitHub)**

```bash
git push origin main && git push github main
```

- [ ] **Step 4: Verifieer die deploy**

Run: `curl -s -o /dev/null -w '%{http_code}' https://humorous-endurance-production-ee64.up.railway.app/rooster/modules`
Expected: `401` (backend aanlyn met die roetes). Doen daarna die handmatige verifikasie in Task 4 Step 7 en kyk dat die personeel-bladsy se twee dropdowns werk.
