# MOON Backend API & Dienste — Tegniese Verwysing

> **NSWIW370 · Akademia · Span 3 — Finale Inhandiging (DA11)**
> **FastAPI · Python 3.12 · PostgreSQL 15 · Mosquitto MQTT · Scikit-Learn · APScheduler**

Hierdie gids dien as die volledige tegniese verwysing vir die **MOON Backend**. Dit dokumenteer die stelselargitektuur, rol-gebaseerde sekuriteit (RBAC), databasismigrasies, agtergrondskedulering, masjienleer-dienste, en die volledige katalogus van alle REST API-eindpunte.

---

## Inhoudsopgawe
1. [Argitektuur & Oorsig](#argitektuur--oorsig)
2. [Toegangsbeheer, Sekuriteit & RBAC](#toegangsbeheer-sekuriteit--rbac)
3. [Standaard Respons-formaat](#standaard-respons-formaat)
4. [Volledige API-Eindpunte Katalogus](#volledige-api-eindpunte-katalogus)
5. [Agtergronddienste & Skedulering](#agtergronddienste--skedulering)
6. [Masjienleer Sub-stelsels](#masjienleer-sub-stelsels)
7. [Houer-lewensiklus & Opstart](#houer-lewensiklus--opstart)
8. [Databasis & Migrasies](#databasis--migrasies)
9. [Toetsing & Gehaltebeheer](#toetsing--gehaltebeheer)

---

## Argitektuur & Oorsig

Die backend funksioneer as die sentrale kern van die MOON-ekosisteem en hanteer:
- **RESTful API**: Meer as 60 eindpunte georganiseer in 20 modulêre routers onder `Backend/routers/`.
- **Relasionele Datalaag**: PostgreSQL 15 met SQLAlchemy 2.0 ORM, buitesleutel-integriteit en konneksiepoele.
- **Intydse IoT-Boodskappe**: Paho-MQTT koppelvlak gekoppel aan 'n Eclipse Mosquitto broker vir kampuswye noodgevaluitsendings.
- **Masjienleer (ML)**: Twee onafhanklike scikit-learn modelle (Saamry-aankomstyd en Lokaalgebruik-vulgraad).
- **Agtergrondtake**: Outonome APScheduler wat nagtelike kampus-uitcheckprosesse bestuur.

---

## Toegangsbeheer, Sekuriteit & RBAC

### Die 5 Gebruikersrolle
Die backend dwing streng Rol-gebaseerde Toegangsbeheer (RBAC) af via `auth.RoleChecker` en `auth.get_current_user`:

| Rol | Kode / Identifiseerder | Toegangsregte & Omvang |
|---|---|---|
| **Administrateur** | `Administrateur` | Volle globale CRUD-toegang tot alle gebruikers, kampusse, roosters, instellings en logs. |
| **Kampus Opsigter** | `Kampus_Opsigter` | Bestuur slegs hul toegewese kampus se lokale, koshuise, besoekers, geleenthede en ontruimingskontroles. |
| **Sekuriteit Wag** | `Sekuriteit_Wag` | Doen hekverifikasie, QR-kaartjieskandering en besoeker-OTP bekragtiging; sien slegs 'n beperkte profiel (geen e-pos of ID-nommer nie). |
| **Personeel** | `Personeel` | Toegang tot eie klasroosters, klasbywoningregisters, module-inligting, verslae en Saamry. |
| **Student** | `Student` | Toegang tot eie rooster, eie bywoning, koshuisprofiel, noodboodskappe en die Saamry-stelsel. |

### Outentifikasie & Sessies
- **JWT Bearer Tokens**: Verkry via `POST /token` met gebruikersnaam (e-pos of ID-nommer) en wagwoord. Tokens bevat die gebruiker se primêre rol sowel as die volledige lys van toegekende rolle (`roles`).
- **Passlib & BCrypt**: Alle wagwoorde word veilig gehash met sout (salt).
- **Konstante-tyd Verifikasie**: Voorkom newe-kanaal tydsaanvalle tydens aanmelding.
- **Sessies**: Geënkripteerde sessiekoekies met `SessionMiddleware`.

### Sekuriteitsverharding (Hardening)
- **Tempo-beperking (`tempo_beperking.py`)**: In-memory glyvenster-spoedbeperking beskerm sensitiewe roetes:
  - Aanmelding (`/token`): Maksimum 10 versoeke per IP en 5 versoeke per gebruikersnaam per minuut (HTTP 429).
  - Besoeker-OTP validering: Beperk brute-krag raaiing van 6-syfer kodes.
- **HTTP Sekuriteitsopskrifte (`http_sekuriteit.py`)**: Elke respons sluit in:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Strict-Transport-Security` (in produksie)
- **Lêer- en Oplaailimiete**: Beskerming teen diensweiering (DoS) en zip-bomme met 'n 20MB perk op CSV's en 50MB perk op ZIP-argiewe.
- **Formule-inspuiting Beskerming**: Teksvelde wat met `=`, `+`, `-` of `@` begin word in CSV- en Excel-verslae ontsmet om formule-inspuiting in sigblaaie te verhoed.
- **Produksiemodus**: Swagger (`/docs`), ReDoc (`/redoc`) en OpenAPI JSON word outomaties afgeskakel wanneer `ENVIRONMENT=production`.

---

## Standaard Respons-formaat

Alle JSON-antwoorde van die API volg die gestandaardiseerde Pydantic-skema `schemas.APIResponse[T]`:

```json
{
  "sukses": true,
  "data": { ... },
  "fout": null
}
```

By 'n fout (`HTTPException` of bedienerfout):

```json
{
  "sukses": false,
  "data": null,
  "fout": "Beskrywing van die foutboodskap"
}
```

---

## Volledige API-Eindpunte Katalogus

### 1. Outentifikasie (`tags=["Auth"]`)
- **`POST /token`**: Verifieer geloofsbriewe (e-pos of ID-nommer + wagwoord) en reik 'n Bearer JWT-token uit. Onderhewig aan tempo-beperking.
- **`POST /logout`**: Maak die kliënt se sessiekoekie skoon.

### 2. Gebruikerbestuur (`prefix="/gebruikers"`)
- **`GET /gebruikers`**: Lys gebruikers (gefilter volgens versoeker se rol; Admin sien almal, Opsigter sien eie kampus, Wag sien beperkte lys).
- **`GET /gebruikers/{id}`**: Haal spesifieke gebruikerprofiel op (Sekuriteitswagte ontvang slegs `UserSecurityRead`).
- **`POST /gebruikers`**: Skep nuwe gebruiker (Slegs Admin).
- **`PUT /gebruikers/{id}`**: Dateer gebruikerinligting op (Slegs Admin).
- **`DELETE /gebruikers/{id}`**: Sagte verwydering (`Is_Aktief = False`).
- **`PATCH /gebruikers/{id}/status`**: Skakel gebruiker se aktiewe status aan/af en deaktiveer gepaardgaande NFC-tags outomaties.
- **`POST /gebruikers/{id}/foto`**: Laai 'n profielfoto op (valideer MIME-tipe en lêergrootte).
- **`GET /gebruikers/me/profiel`**: Haal die tans aangemelde gebruiker se volledige profiel op.

### 3. Kampusse & Lokasies (`prefix="/kampusse"`, `prefix="/lokasies"`)
- **`GET /kampusse`**: Lys alle geregistreerde kampusse (openbaar vir dropdown-lyste).
- **`POST /kampusse`**: Registreer 'n nuwe kampus (Admin).
- **`GET /lokasies`**: Lys fisiese lokale/klaskamers gefilter volgens kampus.
- **`POST /lokasies`**: Skep 'n nuwe lokaal met sitplekkapasiteit en lokaaltipe.
- **`PUT /lokasies/{id}`**: Dateer lokaalbesonderhede op.

### 4. Koshuisbestuur (`prefix="/koshuise"`)
- **`GET /koshuise`**: Lys alle koshuise met hul adres, kampus en maksimum kapasiteit.
- **`GET /koshuise/{id}/status`**: Gedetailleerde oorsig van huidige inwoners, beskikbare plekke en besettingskoers.
- **`POST /koshuise`**: Skep nuwe koshuis (Admin).
- **`POST /koshuise/{id}/studente`**: Wys 'n student toe aan 'n koshuis.

### 5. NFC-Tags & Hekskanderings (`prefix="/nfc-tags"`)
- **`POST /nfc-tags/registreer`**: Koppel 'n nuwe fisiese NFC UID aan 'n spesifieke student of lokaal.
- **`PATCH /nfc-tags/{user_id}/deaktiveer`**: Deaktiveer alle aktiewe tags vir 'n gegewe gebruiker.
- **`POST /nfc/skandeer`**: Verwerk 'n fisiese NFC-skandering by 'n kampushek of klaskamer (bepaal IN/UIT rigting en skep 'n `ToegangsLogs` rekord).
- **`GET /toegangs-logs`**: Soekbare geskiedenis van hekskanderings met filters vir datum, kampus en metode (`NFC`, `HANDMATIG`, `QR`, `SAAMRY`).

### 6. Sekuriteitswagte (`prefix="/wagte"`)
- **`POST /wagte/skandeer`**: Handmatige of vinnige skandering deur 'n wag by 'n hek. Verifieer studentegeldigheid sonder om sensitiewe PII te ontbloot.
- **`GET /wagte/status`**: Haal die aktiewe wag se huidige hek- en kampusstatus op.

### 7. Studente & Roosters (`prefix="/studente"`, `prefix="/klasse"`)
- **`GET /studente/rooster`**: Persoonlike weekrooster vir die aangemelde student (vakke, tye, klaskamers).
- **`GET /studente/{id}/bywoning`**: Bywoningsrekord per vak gebaseer op klaskamer-NFC skanderings tydens geskeduleerde periodes.
- **`GET /klasse`**: Lys geskeduleerde klasse per kampus en module.
- **`POST /klasse`**: Koppel 'n klasperiode aan 'n fisiese lokaal en NFC-tag.
- **`POST /klasse/invoer-csv`**: Voer semesterroosters in grootmaat in vanaf 'n CSV-lêer (idempotent; vermy duplikate).

### 8. Dashboard & Statistieke (`prefix="/dashboard"`)
- **`GET /dashboard/status`**: Lewendige kampusstatus (totale studente en personeel tans op kampus, besettingskoerse).
- **`GET /dashboard/tendense`**: Uurlikse en daaglikse bewegingstendense vir grafieke.

### 9. Saamry-stelsel (Carpooling) (`prefix="/saamry"`)
- **`GET /saamry/profiel`** & **`PUT /saamry/profiel`**: Bestuur Saamry-rol (`BESTUURDER`, `PASSASIER`, `BEIDE`), voorstad, en maksimum ompad-minute.
- **`POST /saamry/optelplek`**: Stoor presiese GPS-optelkoördinate (breedtegraad, lengtegraad, beskrywing) vanaf die kaart.
- **`GET /saamry/voorstelle`**: Bereken en lys versoenbare pasmaats met behulp van die 4-pilaar algoritme (Tyd, Ligging, Rol, Betroubaarheid).
- **`POST /saamry/groepe`**: Skep 'n permanente Saamrygroep met sitplekkapasiteit en vaste vertrektyd.
- **`POST /saamry/ritte`**: Skep 'n eenmalige rit (`SaamryEvent`) vanuit 'n permanente groep.
- **`POST /saamry/vriende/versoek`** & **`PATCH /saamry/vriende/{id}`**: Stuur, aanvaar of weier Saamry-vriendskappe.
- **`GET /saamry/boodskappe`** & **`POST /saamry/boodskappe`**: Privaat kletse tussen vriende of groepkletse vir ritreëlings.
- **`WebSocket /saamry/ws/chat`**: Intydse tweerigting kletsboodskappe via WebSockets.

### 10. Besoekers & OTP (`prefix="/besoekers"`)
- **`POST /besoekers/uitnodigings`**: Studente of personeel skep 'n tydgebonde uitnodiging vir 'n besoeker; genereer 'n 6-syfer OTP.
- **`POST /besoekers/otp/valideer`**: Wagte valideer die OTP by die hek vir IN- of UIT-deurgang. Onderhewig aan tempo-beperking.
- **`POST /besoekers/onverwag`**: Registreer 'n onverwagte gas by die hek met bestuurslisensie en rede.

### 11. Geleenthede / Funksies (`prefix="/events"`)
- **`GET /funksies`** & **`POST /funksies`**: Lys en skep kampusfunksies met datum, lokaal en maksimum gaste.
- **`POST /funksies/{id}/rsvp`**: Interne studente en personeel RSVP vir die geleentheid.
- **`POST /funksies/publiek/{token}/rsvp`**: Eksterne gaste registreer via 'n unieke publieke skakel en ontvang 'n veilige QR-kode sonder PII.
- **`POST /funksies/skandeer-qr`**: Wagte skandeer die eksterne gas se QR-kode by die hek vir IN/UIT/GEWEIER toelating.

### 12. Noodgevalle & Ontruimingsbestuur (`prefix="/noodgeval"`)
- **`POST /noodgevalle`**: Aktiveer 'n kampuswye noodgeval; publiseer onmiddellik 'n hoë-prioriteit JSON-boodskap na Mosquitto MQTT.
- **`PATCH /noodgevalle/{id}/sluit`**: Sluit 'n aktiewe noodgeval af.
- **`GET /noodgeval-live/{kampus_id}`**: Lewendige ontruimingskontrolepaneel wat alle persone lys wat tans volgens heklogs op kampus is.
- **`POST /noodgeval-kontrole/merk`**: Sekuriteit/opsigters merk individue as `DAAR` of `NIE_DAAR` tydens ontruimingsappèl.
- **`POST /noodgeval/toestel/registreer`**: Registreer mobiele toesteltokens vir langdurige agtergrondwaarskuwings.

### 13. Lokaalgebruik ML (`prefix="/lokaalgebruik"`)
- **`GET /lokaalgebruik/voorspellings`**: Lewer die komende week se voorspelde skanderingskoerse, verwagte studentetalle, vulgrade, 80% onsekerheidsreekse en waarskuwingsvlae (`oor_kapasiteit`, `kan_oorloop`, `konflik`).
- **`GET /lokaalgebruik/ml-status`**: Diagnostiese metrieke van die opgeleide model (metode, keuse-rede, MAE per basislyn, bootstrap-verskil, dekking).

### 14. Verslae (`prefix="/verslae"`)
- **`GET /verslae/bywoning`**: Gee 'n JSON-oorsig van bywoning volgens datum, module en klas.
- **`GET /verslae/uitvoer`**: Laai volledige verslae af in **Excel (`.xlsx`)**, **PDF**, of **CSV** formaat. Beskerm teen formule-inspuiting.

### 15. Stelselinstellings (`prefix="/instellings"`)
- **`GET /instellings`** & **`PUT /instellings/{sleutel}`**: Lees en wysig dinamiese stelselinstellings (bv. `auto_uitcheck_tydstip`).

---

## Agtergronddienste & Skedulering

### Outomatiese Nag-uitcheck (`auto_uitcheck.py`)
- **APScheduler**: Begin tydens FastAPI-opstart in `main.py` se lewensiklus (`lifespan`).
- **Werking**: Kontroleer gereeld of die huidige Suid-Afrikaanse tyd (`Africa/Johannesburg`) die gekonfigureerde afsnytyd (verstek `22:00`) bereik het.
- **Veiligheidsmeganisme (MOON-SEC-007)**: Enige kampus wat 'n **AKTIEWE** noodgeval het, word outomaties oorgeslaan. Niemand word tydens 'n noodtoestand uitgecheck nie, sodat ontruimingslyste ongeskonde bly.
- **Aksie**: Nie-koshuisstudente met 'n oop `IN`-status ontvang 'n outomatiese `UIT`-rekord met `TOE_Auto_Uitgecheck = True` en `TOE_Metode = 'HANDMATIG'`.

### MQTT Uitsaaidiens (`mqtt_service.py`)
- Koppel aan Eclipse Mosquitto oor poort 1883 (of geënkripteerde TLS/WSS).
- Publiseer noodkennisgewings na gekanoniseerde onderwerpe: `moon/noodgeval/kampus/{kampus_id}`.
- Verseker QoS 1 aflewering.

---

## Masjienleer Sub-stelsels

### 1. Saamry-Aankomsmodel
- **Doel**: Voorspel die tyd wat 'n student by die kampus aankom om die Tyd-telling (40% gewig) in die Saamry-algoritme te bereken.
- **Opleiding (`scripts/train_aankoms_model.py`)**: Lei outomaties by opstart op uit die jongste 60 dae se hekskanderings.
- **Koue-begin Terugval**: As 'n nuwe student minder as 3 heklogs het, skat die stelsel dat die student 30 minute voor hul eerste klas aankom, met 'n ingeboude onsekerheid $\sigma = 22.2$ minute (Pythagoras-tydverskil).
- **Dokumentasie**: Sien `docs/Saamry-Algoritme.md`.

### 2. Lokaalgebruik-Voorspelling
- **Doel**: Voorspel skanderingskoerse en vulgrade per lokaal vir die komende week.
- **Argitektuur**: `HistGradientBoostingRegressor` met $L_1$ absolute error verliesfunksie.
- **Statistiese Keuse**: Model word slegs ontplooi as dit die sterkste basislyn met $\ge 1 \text{ SE}$ klop via gepaarde bootstrap ($B = 2,000$).
- **Dokumentasie**: Sien `docs/Lokaalgebruik-Model.md`.

---

## Houer-lewensiklus & Opstart

Wanneer die Docker-houer begin, voer `Backend/entrypoint.sh` die volgende stappe in volgorde uit:
1. **Databasis Inisialisering**: Skep ontbrekende tabelle outomaties met `create_all()`.
2. **Saai-data (Opsioneel)**: Voer `seed.py` uit indien `RUN_SEED=true`.
3. **Saamry ML Opleiding**: Lei die model op uit onlangse heklogs (`train_aankoms_model.py --van-logs`).
4. **Saamry Runtime Kontrole**: Toets dat die Saamry-model korrek laai (`check_ml_runtime.py`).
5. **Lokaalgebruik ML Bootstrap**: Koppel lokale, berei opleidingsdata voor en lei die model op (`bootstrap_lokaalgebruik_ml.py`).
6. **Strengheidskontrole**: As `ML_STRICT_STARTUP=true` en 'n kritieke model faal, stop die houer; andersins val dit soepel terug na basislyne.
7. **Bediener Begin**: Begin Uvicorn produksiebediener op `0.0.0.0:8000`.

---

## Databasis & Migrasies

- **Skema-lêers**: Gestoor onder `Backend/migrations/*.sql` vir amptelike weergawegeskiedenis.
- **Idempotente Python-migrasies**:
  - `migrations.py`: Hernoem nalatige tabelle en voeg kolomme by.
  - `noodgeval_kontrole_migration.py`: Skep en indekseer die ontruimingskontroletabel.
  - `noodgeval_device_migration.py`: Skep die mobiele toestelverifikasietabel.

---

## Toetsing & Gehaltebeheer

Die backend beskik oor 'n uitgebreide outomatiese toetsstel in `Backend/tests/`.

### Uitvoer van Toetse:
```bash
# Aktiveer virtuele omgewing
source .venv/bin/activate  # of .venv\Scripts\activate op Windows

# Voer alle toetse uit
pytest Backend/tests

# Voer spesifieke modules uit
pytest Backend/tests/test_lokaalgebruik.py
pytest Backend/tests/test_router_registrasie.py
pytest Backend/tests/test_skep_gebruiker_rol_ids.py
```
