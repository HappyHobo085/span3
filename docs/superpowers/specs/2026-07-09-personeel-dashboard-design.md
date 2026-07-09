# Design: Personeel klas-bywoning dashboard + Admin outo-uitskandering demo

**Date:** 2026-07-09
**Status:** Approved by user

## Goal

Two frontend-only additions to the MOON website (`Webwerf/`):

1. A **Personeel page** where a staff member sees which students scanned into
   their class and which did not, with a calendar and dashboard panels styled
   like the existing Kampus page.
2. A **demo panel on the Admin page** where an admin sets the time at which
   users are automatically scanned out of campus grounds — display only, to
   demonstrate the idea before backend work starts.

**Hard constraint: no backend files (`Backend/`) are touched.** All data on the
new Personeel page is mock/demo data; the admin panel persists nothing.

## Background / context

- The site is vanilla HTML/JS. Auth state lives in `localStorage`
  (`isLoggedIn`, `access_token`, `user_role`); `main.js` is the shared gate.
- Roles: `Student`, `Personeel`, `Administrateur`, `Sekuriteit_Wag`,
  `Kampus_Opsigter`. Students are already blocked from the website;
  `admin.html` is already admin-only via `main.js`.
- The backend has no personeel↔class link and no class roster, which is why
  the dashboard uses mock data (decided with the user).

## 1. Personeel page — `personeel.html` + `personeel.js`

Layout modeled on `kampus.html` (same navbar, `.top-controls`, `.panels`,
`.glass-card` panel pair, `.admin-list` user cards).

### Top controls
- "Kies Klas" dropdown (`glass-select`) listing mock classes for the logged-in
  personeel, e.g. *WIS114 — Klaskamer A*, *FIS121 — Klaskamer B*,
  *RKN214 — Lokaal C*.

### Left panel — Dashboard
Count cards (like Kampus dashboard cards):
- Studente ingeskandeer
- Studente nie ingeskandeer
- Totaal studente
- Bywoning % (scanned-in / total)

Wide list cards:
- **Studente ingeskandeer** — student cards with name, student number, and a
  mock scan time (e.g. "08:07").
- **Studente nie ingeskandeer** — student cards with name and student number.

### Right panel — Kalender + Lys
- Month-view calendar: Afrikaans month/day labels, vorige/volgende month
  buttons, today outlined, selected day highlighted, small dot on weekdays
  (class days) in the past/today.
- Clicking a day re-renders all dashboard panels for that day.
- Below the calendar: full searchable student list for the selected class
  (search input filters like the Kampus page lists).

### Mock data
- Fixed mock class list, each with a fixed roster of ~10–14 students
  (Afrikaans names + STU-style student numbers), defined in `personeel.js`.
- Attendance per (class, date) is generated with a small deterministic
  seeded PRNG (seed = hash of class id + ISO date), so the same day always
  shows the same result across reloads without any storage.
- Weekends and future dates show "Geen klasdata vir hierdie dag nie" and
  `--` placeholder counts (Totaal studente keeps its real value).

## 2. Access control — `main.js`

Mirrors the existing admin gate:
- If current page is `personeel.html` and `user_role !== 'Personeel'`,
  silently redirect to `home.html`. Admin, Sekuriteit_Wag and Kampus_Opsigter
  are therefore blocked.
- Add a "My Klasse" navbar link dynamically for `Personeel` users only
  (same pattern as the dynamic Admin link; skip if already present).
- Existing student site-wide block stays unchanged.

## 3. Admin demo panel — `admin.html` + `admin.js`

- New `glass-card` panel "Outo-Uitskandering" appended to the existing
  `.panels` grid on `admin.html`.
- Contents: short explanation line, `<input type="time">` defaulting to
  18:00, "Stoor Tyd" button, inline confirmation area.
- On save: show inline message *"Outo-uitskandering gestel vir HH:MM"*.
- Visible note in the panel: *"Demo — backend word later gekoppel."*
- **No persistence**: nothing written to localStorage or the API; resets to
  18:00 on reload.

## Files changed

| File | Change |
|---|---|
| `Webwerf/personeel.html` | New page |
| `Webwerf/personeel.js` | New: mock data, calendar, dashboard rendering |
| `Webwerf/main.js` | Personeel gate + "My Klasse" nav link |
| `Webwerf/admin.html` | Outo-Uitskandering panel markup |
| `Webwerf/admin.js` | Demo save handler |
| `Webwerf/styles.css` | Calendar styles (and small panel tweaks only) |

## Error handling

- No network calls on the personeel page, so no API error paths; empty/no-data
  days render the "Geen klasdata" placeholder.
- Admin panel validates that a time is chosen before showing the confirmation.

## Testing

No test framework exists in `Webwerf/`; verification is manual:
1. Log in as Personeel → "My Klasse" link visible, page loads, class switch
   and calendar day clicks update the panels, search filters the roster.
2. Log in as Administrateur / Sekuriteit_Wag / Kampus_Opsigter → no
   "My Klasse" link; opening `personeel.html` directly redirects to
   `home.html`.
3. Admin page shows the Outo-Uitskandering panel; saving a time shows the
   confirmation; reload resets it; `git status` confirms `Backend/` untouched.
