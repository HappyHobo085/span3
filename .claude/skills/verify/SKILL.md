---
name: verify
description: How to build, run, and manually verify changes in the MOON stack (FastAPI backend + static Webwerf frontend + Postgres, all via docker compose)
---

# Verifying changes in this repo

## Stack

`docker compose up -d` at the repo root runs three containers:

- `moon_backend` — FastAPI on http://localhost:8000. Code is **baked into the
  image**: after backend changes run `docker compose up -d --build backend`.
  Startup applies idempotent migrations (see top of `Backend/main.py`) and
  seeds via `seed.py`.
- `webwerf_frontend` — nginx on http://localhost:80 serving `./Webwerf` as a
  **live read-only mount**: frontend changes need no rebuild, just reload.
- `moon_db` — Postgres 15. Inspect with:
  `docker exec moon_db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d student"'`
  (column names are case-sensitive/quoted — SQLAlchemy created them).

## API access

Login: `POST /token` form-encoded `username`/`password`. Seeded admin:
`admin@moon.com` / `admin123` (see `Backend/seed.py` for more users).
Token is at `.data.access_token`. Pass as `Authorization: Bearer <token>`.
All responses are `{sukses, data, fout}`.

## Driving the website headlessly

No Playwright installed; use headless Edge. The site gates every page on
localStorage (`isLoggedIn`, `user_role`, `access_token`) — headless sessions
get a fresh profile, so inject state via a temp bootstrap page in `Webwerf/`
(it is served by nginx; **delete it afterwards**):

```html
<!-- Webwerf/__verify_settoken.html -->
<script>
localStorage.setItem('access_token', '<token>');
localStorage.setItem('isLoggedIn', 'true');
localStorage.setItem('user_role', 'Administrateur');
location.replace('koshuis.html'); // target page
</script>
```

```bash
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --headless=new --disable-gpu --window-size=1500,1400 \
  --virtual-time-budget=15000 \
  --screenshot=<scratchpad>/page.png \
  http://localhost/__verify_settoken.html
# or --dump-dom > page.html to assert on rendered DOM
```

Note `user_role === 'Student'` is rejected by main.js; use Administrateur.

## Gotchas

- `python` is not on PATH; use `py -3`.
- Windows PowerShell 5.1: no `&&` — the Bash tool works fine for chains.
- IDs from seeded/recreated data are not stable (sequences advance); query
  the DB or list endpoints instead of assuming ID 1.
