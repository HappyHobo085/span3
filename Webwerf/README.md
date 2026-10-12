# MOON Administrasie Webwerf — Tegniese Verwysing & Gids

> **NSWIW370 · Akademia · Span 3 — Finale Inhandiging (DA11)**
> **HTML5 · CSS3 · Vanilla JavaScript · Nginx Alpine · REST API Integrasie**

Hierdie gids dien as die amptelike tegniese verwysing vir die **MOON Administrasie Webwerf** (`Webwerf/`). Dit dokumenteer die webwerf se argitektuur, Nginx-omgewing, sekuriteitskoppe, bladsy- en funksiekatalogus, API-integrasie, temastelsel, en instruksies vir plaaslike toetsing en ontplooiing.

---

## Inhoudsopgawe
1. [Oorsig & Doel](#oorsig--doel)
2. [Nginx-argitektuur & Sekuriteitskonfigurasie](#nginx-argitektuur--sekuriteitskonfigurasie)
3. [Bladsy- en Funksie-katalogus](#bladsy--en-funksie-katalogus)
4. [API-Integrasie & Outentifikasie](#api-integrasie--outentifikasie)
5. [UI-Stelsel, Grafieke & Temas](#ui-stelsel-grafieke--temas)
6. [Gidsstruktuur](#gidsstruktuur)
7. [Opstelling & Plaaslike Toetsing](#opstelling--plaaslike-toetsing)

---

## Oorsig & Doel

Die MOON-webwerf is die primêre beheersentrum vir Akademia se kampusbestuurders, sisteemadministrateurs en personeel. Dit bied 'n vinnige, responsiewe en intuïtiewe webkoppelvlak sonder die oorhoofse las van swaar kliënt-raamwerke, wat hoë werkverrigting en kitslaaitye verseker.

### Sleutelkenmerke:
- **Intydse Kampusmonitering**: Lewendige oorsig van alle studente en personeel wat tans op kampus teenwoordig is.
- **Gebruiker- & Toegangsbeheer**: Bestuur rekeninge, roltoewysings en NFC-tags.
- **Masjienleer Lokaalvoorspelling**: 'n Interaktiewe weekrooster wat die ML-model se voorspelde skanderingskoerse, studentetalle en vulgrade vertoon.
- **Koshuis- & Lokaaladministrasie**: Moniteer kapasiteite, besetting en lokaalbotsings.
- **Geleenthede & QR-Toegang**: Skep kampusfunksies en genereer publieke RSVP-skakels met veilige QR-toegangskaartjies vir eksterne besoekers.
- **Dinamiese Verslae**: Genereer en laai pasgemaakte verslae af in Excel (`.xlsx`), PDF en CSV formaat.

---

## Nginx-argitektuur & Sekuriteitskonfigurasie

Die webwerf word in produksie bedien deur 'n hoogs geoptimaliseerde **Nginx Alpine** Docker-houer op poort 80 (`webwerf_frontend`).

### Nginx Konfigurasie (`nginx.docker.conf`)
- **Roetering**:
  - `/` herlei outomaties na `/login.html` (HTTP 302).
  - `/assets/` word gekarteer na `/usr/share/nginx/assets/`.
  - Alle HTML/JS/CSS-lêers word staties bedien met `no-cache` opskrifte om onmiddellike kliënt-opdaterings te waarborg.
- **Sekuriteitsopskrifte**:
  ```nginx
  add_header X-Frame-Options "DENY" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http://localhost:8000 https://humorous-endurance-production-ee64.up.railway.app" always;
  ```

---

## Bladsy- en Funksie-katalogus

| Bladsy | Skrip | Doel & Funksionaliteit |
|---|---|---|
| **`login.html`** | `login.js` | Veilige aanmeldskerm. Valideer geloofsbriewe teen `POST /token`, stoor die JWT Bearer token in plaaslike berging (`localStorage`), en stuur die gebruiker outomaties na die dashboard. |
| **`home.html`** | `home.js` | Hoofpaneelbord. Vertoon lewendige kampustellers (persone tans op kampus), sirkeldiagramme vir rolverspreiding, en 'n uurlikse bewegingstendens-grafiek. |
| **`admin.html`** | `admin.js`, `admin-oorsig.js` | Gebruikeradministrasie. Soekbare tabel van alle gebruikers met rolfilters, modal venster vir die skep van nuwe rekeninge, sagte verwydering (`deaktiveer`), en statuswisseling. |
| **`kampus.html`** | `kampus.js` | Lokale en ML-voorspellings. Lys alle sale en klaskamers, skep nuwe lokale met kapasiteite, en vertoon die **interaktiewe ML Lokaalgebruik-rooster**. |
| **`koshuis.html`** | `koshuis.js` | Koshuisbestuur. Vertoon kapasiteite, huidige inwoners, leë kamers, en fasiliteer studentetoewysings per koshuis. |
| **`personeel.html`** | `personeel.js` | Personeeltoesig. Oorsig van dosente, hul doseerroosters, en elektroniese klasregisters met bywoningstellers. |
| **`event.html` / `events.html`** | `event.js` | Kampusfunksies & Geleenthede. Skep nuwe geleenthede, genereer unieke publieke registrasieskakels vir gaste, en monitor RSVP-statusse. |
| **`verslag.html`** | `verslag.js` | Verslagdoeningsentrum. Filter bywoning en toegangslogs volgens datumperiode, kampus en module; voorskou data in tabelle en laai af as Excel, PDF of CSV. |

---

## API-Integrasie & Outentifikasie

Die frontend kommunikeer direk met die FastAPI-backend via `website_api_calls.js`:

### 1. Token- en Sessiebestuur
- By suksesvolle aanmelding word die JWT-token gestoor in `localStorage.getItem('token')`.
- Elke versoek na beskermde roetes stuur outomaties die Bearer-opskrif mee:
  ```javascript
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  }
  ```
- Indien die bediener 'n `401 Unauthorized` teruggee, word die token skoongemaak en die gebruiker outomaties teruggestuur na `login.html`.

### 2. Gekoppelde API-Eindpunte
- Kampus- en gebruikersdata: `GET /kampusse`, `GET /gebruikers`, `POST /gebruikers`
- Lewendige tellers: `GET /dashboard/status`, `GET /toegangs-logs`
- Lokaalgebruik ML: `GET /lokaalgebruik/voorspellings?kampus_id={id}&dag={dag}`
- Verslae: `GET /verslae/bywoning`, `GET /verslae/uitvoer?formaat=xlsx`

---

## UI-Stelsel, Grafieke & Temas

### 1. Donker- en Lig-tema (`theme.js`, `styles.css`)
- Ondersteun kitswisseling tussen Donker- en Lig-modus met behulp van CSS-veranderlikes (`--bg-primary`, `--card-bg`, `--text-primary`, ens.).
- Onthou die gebruiker se voorkeur in `localStorage` en pas dit toe voor die DOM klaar gerender is om flikkering te voorkom.

### 2. Statistieke & Tabelle (`stats.js`)
- `MoonStats.createTable`: Herbruikbare, soekbare en filtreerbare datatabel met pagination.
- `MoonStats.createDoughnutChart`: Pasgemaakte SVG- en Canvas-sirkeldiagramme vir rolverspreiding.
- `MoonStats.createTrendChart`: Lewendige lyn- en staafgrafieke vir kampusbewegings oor tyd.

### 3. ML Lokaalgebruik-Kleurkodering (`kampus.js`)
Die interaktiewe klaskamerrooster gebruik dinamiese kleure gebaseer op die voorspelde vulgraad:
- **Groen** ($\le 50\%$): Baie beskikbare sitplekke.
- **Geel** ($51\% - 80\%$): Normale, gesonde lokaalbesetting.
- **Pers / Aksent** ($81\% - 100\%$): Optimale lokaalbenutting.
- **Rooi** ($> 100\%$): Waarskuwing — verwagte bywoning oorskry lokaalkapasiteit.
- **⚠ / ! Merktekens**: Dui op klaskamerbotsings of risiko dat die 90%-onsekerheidsreeks bo kapasiteit gaan.

---

## Gidsstruktuur

```text
Webwerf/
├── assets/                     # Prente, logo's en ikone (MOON-logo.png, ens.)
├── nginx.docker.conf           # Nginx produksiebediener-konfigurasie
├── styles.css                  # Globale temas, CSS-veranderlikes en uitleg
├── theme.js                    # Donker/Lig-tema wisseling en voorkeur-berging
├── stats.js                    # Herbruikbare tabelle, filters en grafieke
├── website_api_calls.js        # API-kliëntfunksies en JWT Bearer token-bestuur
├── index.html                  # Ingangspunt (herlei na login.html)
├── login.html / login.js       # Aanmeldingskoppelvlak en sessie-inisialisering
├── home.html / home.js         # Hoofpaneelbord met lewendige kampusstatistieke
├── admin.html / admin.js       # Gebruikersadministrasie en sagte verwydering
├── admin-oorsig.js             # Globale admin-tellings en stelseloorsig
├── kampus.html / kampus.js     # Lokale, NFC-tags en ML-lokaalvoorspellingsrooster
├── koshuis.html / koshuis.js   # Koshuisbesetting en studentetoewysings
├── personeel.html / personeel.js# Personeelroosters en elektroniese klasregisters
├── event.html / event.js       # Funksies, publieke RSVP's en gaste-oorsig
├── events.html                 # Lys van alle aktiewe en historiese funksies
└── verslag.html / verslag.js   # Verslagdoening en aflaai van Excel/PDF/CSV
```

---

## Opstelling & Plaaslike Toetsing

### 1. Uitvoering met Docker Compose (Aanbeveel)
Die webwerf word outomaties saam met die res van die stelsel ontplooi:

```bash
docker compose up -d webwerf-frontend
```
Sodra die houer loop, is die webkoppelvlak beskikbaar by:
👉 **`http://localhost`** (poort 80)

### 2. Plaaslike Toetsing sonder Docker
Aangesien die webwerf uit suiwer statiese HTML, CSS en JavaScript bestaan, kan dit met enige statiese webbediener getoets word:

```bash
cd Webwerf

# Met Python:
python -m http.server 8080

# Of met VS Code Live Server / Node http-server
```
Maak dan `http://localhost:8080/login.html` oop in jou blaaier.
> **Wenk:** Maak seker die FastAPI-backend loop op `http://localhost:8000` sodat die API-versoeke slaag.
