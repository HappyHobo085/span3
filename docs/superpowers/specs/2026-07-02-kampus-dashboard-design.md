# Kampus Dashboard — Live Scan Status Design

**Date:** 2026-07-02
**Status:** Approved

---

## Goal

Wire `kampus.html` to two new FastAPI endpoints so the dashboard shows real-time campus scan data (students and personeel scanned in/out), while the right-panel student and personeel lists remain a constant full roster loaded once on page load.

---

## API Endpoints Used

### `GET /kampusse/status`
Returns summary scan counts for all campuses. No auth required.

```json
{
  "sukses": true,
  "data": [
    {
      "Kampus_ID": 1,
      "KAM_Naam": "Leriba",
      "KAM_Adres": "...",
      "scanned_in_count": 5,
      "scanned_out_count": 3
    }
  ]
}
```

### `GET /kampusse/{kampus_id}/status`
Returns detailed scanned-in and scanned-out user lists for a specific campus. No auth required.

```json
{
  "sukses": true,
  "data": {
    "Kampus_ID": 1,
    "KAM_Naam": "Leriba",
    "scanned_in_count": 5,
    "scanned_out_count": 3,
    "scanned_in": [
      {
        "Gebruiker_ID": 1,
        "GEB_Naam": "John",
        "GEB_Van": "Doe",
        "GEB_Epos": "john@example.com",
        "Rol_Naam": "Student",
        "Tydstempel": "2026-07-02T10:00:00",
        "Rigting": "IN",
        "Metode": "NFC"
      }
    ],
    "scanned_out": [ ... ]
  }
}
```

---

## Files Changed

| File | Change |
|------|--------|
| `Webwerf/website_api_calls.js` | Add `fetchKampusseStatus()` and `fetchKampusStatus(kampusId)` to `window.MoonApi` |
| `Webwerf/kampus.html` | Replace 5 mock dashboard cards with 6 real data cards with IDs; add `<ul id="personeel-list">` inside `.bottom-inner-panel` |
| `Webwerf/kampus.js` | Add `loadGebruikersLys()`, `refreshDashboard()`, `startPolling()`; wire dropdown `change` event; load campuses from API |

---

## Component Design

### `website_api_calls.js`

Two new methods on `window.MoonApi`:

- **`fetchKampusseStatus()`** — `GET /kampusse/status`, no auth header needed
- **`fetchKampusStatus(kampusId)`** — `GET /kampusse/{kampusId}/status`, no auth header needed

Both follow the existing `apiRequest()` pattern and return the parsed response body.

---

### `kampus.html` — Dashboard Panel (left)

Replace the existing `.dashboard-grid` contents with 6 cards:

```
┌────────────────────────────┬────────────────────────────┐
│  Studente ingeklokt: --    │  Personeel ingeklokt: --   │
│  #dash-student-in-count    │  #dash-personeel-in-count  │
├────────────────────────────┼────────────────────────────┤
│  Studente uitgeklokt: --   │  Personeel uitgeklokt: --  │
│  #dash-student-out-count   │  #dash-personeel-out-count │
├────────────────────────────┴────────────────────────────┤
│  Studente tans op kampus (ingeklokt)                    │
│  <ul id="dash-student-in-list">  [.card.wide]           │
├─────────────────────────────────────────────────────────┤
│  Studente nie op kampus (uitgeklokt)                    │
│  <ul id="dash-student-out-list">  [.card.wide]          │
├─────────────────────────────────────────────────────────┤
│  Personeel tans op kampus (ingeklokt)                   │
│  <ul id="dash-personeel-in-list">  [.card.wide]         │
├─────────────────────────────────────────────────────────┤
│  Personeel nie op kampus (uitgeklokt)                   │
│  <ul id="dash-personeel-out-list">  [.card.wide]        │
└─────────────────────────────────────────────────────────┘
```

### `kampus.html` — Right Panel (Lys)

- Top section unchanged: `#list-search` + `#data-list` (student list)
- Bottom section: `#bottom-search` (personeel search) + add `<ul id="personeel-list">` inside `.bottom-inner-panel`

---

### `kampus.js` — Function Map

| Function | Trigger | Source | Target |
|----------|---------|--------|--------|
| `loadKampusDropdown()` | Page load (once) | `GET /kampusse` | `#data-select` |
| `loadGebruikersLys()` | Page load (once) | `GET /gebruikers` | `#data-list` (students), `#personeel-list` (personeel) |
| `refreshDashboard(kampusId)` | Dropdown `change` + `setInterval` | `GET /kampusse/{id}/status` | Dashboard cards only |
| `startPolling(kampusId)` | After first dropdown selection | — | calls `refreshDashboard()` every 30s |

#### `loadGebruikersLys()`
- Fetches all gebruikers from `GET /gebruikers`
- Filters by `Rol_Naam === "Student"` → renders `<li>` items into `#data-list` (naam + van + studentnommer if present)
- Filters by `Rol_Naam === "Personeel"` → renders `<li>` items into `#personeel-list`
- Called once on page load; never called again

#### `refreshDashboard(kampusId)`
- Calls `MoonApi.fetchKampusStatus(kampusId)`
- Splits `data.scanned_in` and `data.scanned_out` by `Rol_Naam`
- Updates `#dash-student-in-count`, `#dash-student-out-count`, `#dash-personeel-in-count`, `#dash-personeel-out-count` text
- Renders lists into `#dash-student-in-list`, `#dash-student-out-list`, `#dash-personeel-in-list`, and `#dash-personeel-out-list`
- Dashboard only — right panel is not touched

#### `startPolling(kampusId)`
- Clears any existing interval
- Sets a new `setInterval` every 30 000ms calling `refreshDashboard(currentKampusId)`
- `currentKampusId` is a module-level variable updated whenever the dropdown changes

#### Dropdown wiring
- On `change` of `#data-select`: read selected value, call `refreshDashboard(id)`, restart polling
- On page load: after `loadKampusDropdown()` resolves, auto-select first campus and call `refreshDashboard()`

---

## Data Flow

```
Page Load
  ├── loadKampusDropdown()  → GET /kampusse       → #data-select options
  ├── loadGebruikersLys()   → GET /gebruikers     → #data-list + #personeel-list (constant)
  └── refreshDashboard(firstKampusId)             → #dash-* cards
        └── startPolling(firstKampusId)

Dropdown Change
  ├── refreshDashboard(newKampusId)               → #dash-* cards only
  └── startPolling(newKampusId)                   → replaces old interval
```

---

## Error Handling

- If `GET /gebruikers` fails (no token / network): `#data-list` and `#personeel-list` show a single `<li>` with an error message; no crash
- If `GET /kampusse/{id}/status` fails: dashboard cards show `--` and existing list items are cleared; polling continues
- If no campus is selected (dropdown empty): `refreshDashboard()` is a no-op

---

## Out of Scope

- WebSocket / SSE live push (polling at 30s is sufficient)
- Pagination of the gebruikers list
