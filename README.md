# MOON — Kampus Toegangsbeheer Stelsel

> **NSWIW370 · 2026 · Span 3**

MOON is 'n kampus toegangsbeheer stelsel wat NFC-tegnologie gebruik om studentebywoning, kampustoegang, en sekuriteitsbestuur te stroomlyn. Die stelsel bestaan uit 'n mobiele Flutter-app, 'n webkoppelvlak vir administrateurs, 'n MQTT-boodskapdiens vir noodgevalle, en 'n FastAPI-backend gekoppel aan 'n PostgreSQL-databasis.

---

## Spansamestelling

| Lid | Rol |
|---|---|
| **Jaco** | Databasis & Projekleier |
| **Louis** | Backend Ontwikkelaar |
| **Steven** | Backend Ontwikkelaar |
| **Connor** | Frontend Ontwikkelaar |

---

## Tegniese Stapel

| Laag | Tegnologie |
|---|---|
| Mobiele App | Flutter (Dart) |
| Webkoppelvlak | HTML / CSS / JS (Nginx bediener) |
| Backend API | FastAPI (Python) |
| Databasis | PostgreSQL 15 |
| IoT Boodskappe | Mosquitto (MQTT) |
| Houerbestuur | Docker & Docker Compose |
| Weergawebeheer | GitLab |

---

## Repo Struktuur

```text
span3/
├── Backend/                  # FastAPI Python backend
│   ├── routers/              # API eindpunte per module
│   ├── services/             # Besigheidslogika
│   ├── auth.py               # Outentifikasie en sekuriteit
│   ├── models.py             # Databasis modelle
│   ├── schemas.py            # Pydantic schemas
│   ├── main.py               # FastAPI app ingangspunt
│   ├── Dockerfile            # Docker bou-instruksies
│   └── requirements.txt      # Python afhanklikhede
├── Webwerf/                  # Admin webkoppelvlak
│   ├── assets/               # Prente en bates
│   ├── nginx.docker.conf     # Nginx konfigurasie
│   └── *.html, *.js, *.css   # Voorpunt blaaie en skripte
├── studente_mobile_flutter_app/   # Flutter mobiele app
│   ├── lib/                  # Dart bronkode
│   ├── android/, ios/, web/  # Platform-spesifieke kode
│   └── pubspec.yaml          # Flutter afhanklikhede
├── Mosquitto/                # MQTT konfigurasie
│   └── mosquitto.conf
├── docs/                     # Projekdokumentasie
├── docker-compose.yml        # Docker dienste definisie
├── .env.example              # Omgewings-template (kopieer na .env)
├── reset_server.sh           # Hulpskrip om bediener te herbou
└── db_check.sh               # Hulpskrip om databasis te toets
```

---

## Opstelling

### Vereistes

- Docker en Docker Compose
- Flutter SDK 3.x (vir die mobiele app)

### Bediener / Backend / Databasis (Docker)

Ons gebruik Docker Compose om die hele stelsel (Databasis, MQTT, Backend, en Frontend webbediener) te integreer.

```bash
# 1. Kloon die repo
git clone <repo-url>
cd span3

# 2. Stel omgewingsveranderlikes op
cp .env.example .env
# Maak seker jy verander die SECRET_KEY in .env

# 3. Begin die dienste met Docker Compose
docker-compose up -d --build

# Alternatiewelik, gebruik die herbou-skrip (stop containers, pull nuutste, herbou, run)
./reset_server.sh
```

Na opstelling:
- Die **API** is beskikbaar by `http://localhost:8000`
- Interaktiewe **API dokumentasie** (Swagger): `http://localhost:8000/docs`
- Die **Webkoppelvlak** is beskikbaar by `http://localhost`
- **MQTT bediener** luister op poort `1883`

### Flutter App

```bash
cd span3/studente_mobile_flutter_app

# Installeer afhanklikhede
flutter pub get

# Begin op 'n gekoppelde toestel, blaaier, of emulator
flutter run
```

---

## Omgewingsveranderlikes

Kopieer `.env.example` na `.env` in die hoofgids en vul die nodige waardes in (soos wagwoorde en geheime sleutels). Die `docker-compose.yml` gebruik hierdie `.env` lêer om die omgewing vir al die houers in te stel.

> **Moenie** die `.env` lêer na die repo commit nie — dit is reeds in `.gitignore`.

---

## Hulpskripte

- **`reset_server.sh`**: Trek die nuutste kode via git, stop bestaande Docker-houers, herbou die beelde en begin die stelsel.
- **`db_check.sh`**: Maak seker die databasis houer loop, lys databasisse en toets as `toegangs_logs` bestaan. Handig om vinnig na log-data te kyk.

---

## Projekmylpale

| Mylpaal | Datum | Status |
|---|---|---|
| DA6 — Pre-Alpha | 15 Mei 2026 | ✅ Voltooi |
| DA7 — Alfa / MVP | 10 Julie 2026 | ✅ Voltooi |
| DA9 — Beta | 18 September 2026 | 🔄 In Vordering |
| DA11 — Finale Inhandiging | 14 Oktober 2026 | ⏳ Gepland |

---

## Bydraersriglyne

1. Werk op jou eie tak: `git checkout -b feature/jou-taak` of `bugfix/jou-taak`
2. Commit gereeld met duidelike boodskappe
3. Maak 'n merge request na `main` — moenie direk na `main` stoot nie
4. Laat 'n spanlid jou MR hersien voor dit saamgesmelt word

---

## Lisensie

Hierdie projek is deel van die NSWIW370-module by die Akademie vir Inligtingstegnologie (AIT). Alle regte voorbehou.