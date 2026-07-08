# Koshuis Dashboard — Design

**Date:** 2026-07-08
**Status:** Approved

## Goal

Give the Koshuis page (`Webwerf/koshuis.html`) a live dashboard equivalent to the
Kampus page's: per-koshuis scanned-in/out counts and student lists, plus a
searchable list of all students connected to the selected koshuis.

## Problem

The Kampus dashboard is driven by `GET /kampusse/{id}/status`, which derives
each user's in/out state from their latest `ToegangsLogs` entry at that kampus.
There is no koshuis equivalent because the database has no link between a
student and a specific koshuis — only the boolean `Student.STU_Is_Koshuis`.

## Decision

Add a real student→koshuis link (approved over the alternatives of reusing the
boolean flag or a frontend-only mock).

## 1. Database — migration `007_student_koshuis.sql`

- `ALTER TABLE student ADD COLUMN IF NOT EXISTS "Koshuis_ID" INT NULL` with FK
  to `koshuis("Koshuis_ID")`, guarded the same way as migration 005's FK.
- `models.py`: add `Koshuis_ID` column (nullable FK) and `koshuis` relationship
  to `Student`; back-reference `studente` on `Koshuis`.

## 2. Backend (`main.py`, `schemas.py`)

### New endpoint `GET /koshuise/{koshuis_id}/status`

Same shape as the kampus detail status endpoint. 404 if koshuis not found.
Response data (`KoshuisDetailStatus`):

- `Koshuis_ID`, `KOS_Naam`, `KOS_Kapasiteit`
- `inwoner_count` — number of students with `Koshuis_ID == id`
- `scanned_in_count`, `scanned_out_count`
- `scanned_in`, `scanned_out` — lists of `KampusGebruikerStatus` (reused schema)

Logic: fetch the koshuis's students, take each student's **latest ToegangsLog
at any location** (max `Log_ID` per gebruiker), split by `TOE_Rigting`.
Students with no logs appear in neither list (matches kampus behaviour).
No auth, same as the kampus status endpoint.

### Student koshuis assignment

- `schemas.py`: `Koshuis_ID: Optional[int]` accepted on user create/update
  student paths; add `KoshuisDetailStatus`.
- `main.py` user create/update: persist `Koshuis_ID` on the `Student` row
  (validate the koshuis exists when non-null).
- `GET /gebruikers`: return `Koshuis_ID` next to `STU_Is_Koshuis`.

## 3. Frontend

### `website_api_calls.js`

- `fetchKoshuisStatus(koshuisId)` → `GET /koshuise/{id}/status`.

### `koshuis.html`

Mirrors `kampus.html`:

- `#data-select` dropdown populated from `GET /koshuise` (hardcoded options removed).
- Dashboard cards: *Studente ingeteken: N*, *Studente uitgeteken: N*,
  *Inwoners: N / Kapasiteit* and two wide list cards (*Studente tans
  ingeteken* / *Studente uitgeteken*) using the same `admin-list` /
  `user-card` rendering.
- Right panel: searchable list of the selected koshuis's students, re-rendered
  on dropdown change (unlike Kampus where the list is global). No personeel
  section — personeel aren't koshuis residents.
- Inline filter script replaced by `koshuis.js`.

### `koshuis.js` (currently empty)

Adapted from `kampus.js`: load koshuise into the dropdown, first refresh +
30-second polling of `fetchKoshuisStatus`, card rendering helpers, search
filter over `.user-card` rows. Right-panel list built from `fetchGebruikers`
filtered by `Koshuis_ID === selected`.

### Admin (`admin.html`, `admin.js`)

"Koshuis" dropdown in the user create/edit modal, shown for role Student
(next to the student number field), populated from `GET /koshuise`, sent as
`Koshuis_ID` on create/update.

## Error handling

Same conventions as kampus.js: counts fall back to `--`, lists show
"Geen studente nie" / "Kon nie … laai nie" cards on API failure.

## Testing

Repo has no automated test suite; verify manually by running the FastAPI
backend + static frontend, assigning a student to a koshuis via the admin
panel, posting a scan, and confirming the dashboard updates.
