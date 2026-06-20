# MOON — Kampus Toegangsbeheer Stelsel

> **NSWIW370 · 2026 · Span 3**

MOON is 'n kampus toegangsbeheer stelsel wat NFC-tegnologie gebruik om studentebywoning, kampustoegang, en sekuriteitsbestuur te stroomlyn. Die stelsel bestaan uit 'n mobiele Flutter-app, 'n webkoppelvlak vir administrateurs, en 'n FastAPI-backend gekoppel aan 'n PostgreSQL-databasis.

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
| Webkoppelvlak | HTML / CSS / JS |
| Backend API | FastAPI (Python) |
| Databasis | PostgreSQL 18 |
| DB Hosting | Railway |
| Weergawebeheer | GitLab |

---

## Repo Struktuur

```
span3/
├── Backend/                  # FastAPI Python backend
│   ├── config.py             # Omgewingsveranderlikes
│   ├── database.py           # SQLAlchemy verbinding (Railway)
│   ├── models.py             # Alle databasis tabelle
│   ├── main.py               # FastAPI app ingangspunt
│   ├── .env.example          # Omgewings-template (kopieer na .env)
│   └── venv/                 # Lokaal — nie in repo nie
├── Webwerf/                  # Admin webkoppelvlak
│   └── FrontEnd/
├── studente_mobile_flutter_app/   # Flutter mobiele app
│   ├── lib/
│   ├── android/
│   ├── ios/
│   └── pubspec.yaml
├── docs/                     # Projekdokumentasie
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Opstelling

### Vereistes

- Python 3.11+
- Flutter SDK 3.x
- PostgreSQL 18 (of Railway-verbinding)
- Node.js (vir webbou, indien van toepassing)

### Backend

```bash
# 1. Kloon die repo
git clone <repo-url>
cd span3/Backend

# 2. Skep virtuele omgewing
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Installeer afhanklikhede
pip install -r requirements.txt

# 4. Stel omgewingsveranderlikes op
cp .env.example .env
# Wysig .env met jou Railway / plaaslike databasis-verbindingstring

# 5. Begin die API
uvicorn main:app --reload
```

Die API is nou beskikbaar by `http://127.0.0.1:8000`  
Interaktiewe dokumentasie: `http://127.0.0.1:8000/docs`

### Flutter App

```bash
cd span3/studente_mobile_flutter_app

# Installeer afhanklikhede
flutter pub get

# Begin op 'n gekoppelde toestel of emulator
flutter run
```

### Webkoppelvlak

```bash
cd span3/Webwerf/FrontEnd
# Open index.html in 'n blaaier, of gebruik 'n plaaslike bediener
```

---

## Omgewingsveranderlikes

Kopieer `.env.example` na `.env` in die `Backend/` vouer en vul die volgende in:

```env
DATABASE_URL=postgresql://gebruiker:wagwoord@host:poort/databasisnaam
SECRET_KEY=jou_jwt_geheim_sleutel
```

> **Moenie** die `.env` lêer na die repo commit nie — dit is reeds in `.gitignore`.

---

## API Eindpunte (Pre-Alpha)

| Metode | URL | Beskrywing |
|---|---|---|
| `POST` | `/lokasies` | Skep 'n nuwe klaskamer / lokasie |
| `GET` | `/lokasies` | Lys alle lokasies |
| `POST` | `/nfc-tags` | Koppel 'n NFC-tag aan 'n lokasie |
| `GET` | `/nfc-tags/{uid}` | Soek 'n lokasie via NFC-tag UID |

Volledige API-dokumentasie beskikbaar by `/docs` wanneer die backend loop.

---

## Projekmylpale

| Mylpaal | Datum | Status |
|---|---|---|
| DA6 — Pre-Alpha | 15 Mei 2026 | ✅ Voltooi |
| DA7 — Alfa / MVP | 10 Julie 2026 | 🔄 In Vordering |
| DA9 — Beta | 18 September 2026 | ⏳ Gepland |
| DA11 — Finale Inhandiging | 14 Oktober 2026 | ⏳ Gepland |

---

## Bydraersriglyne

1. Werk op jou eie tak: `git checkout -b feature/jou-taak`
2. Commit gereeld met duidelike boodskappe
3. Maak 'n merge request na `main` — moenie direk na `main` druk nie
4. Laat 'n spanlid jou MR hersien voor samesmelting

---

## Lisensie

Hierdie projek is deel van die NSWIW370-module by die Akademie vir Inligtingstegnologie (AIT). Alle regte voorbehou.