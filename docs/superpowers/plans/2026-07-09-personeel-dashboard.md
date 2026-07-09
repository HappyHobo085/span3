# Personeel Dashboard + Admin Outo-Uitskandering Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Personeel-only class-attendance dashboard page (mock data) with calendar + panels styled like the Kampus page, and a display-only "Outo-Uitskandering" demo panel on the Admin page.

**Architecture:** Pure frontend additions to `Webwerf/` (vanilla HTML/JS/CSS, no build step). A new `personeel.html`/`personeel.js` pair renders deterministic mock attendance (seeded PRNG keyed on class+date, so no storage needed). Access control extends the existing gate in `main.js` (mirrors the admin.html gate). The admin demo panel is static markup plus a click handler with zero persistence. **`Backend/` is never touched.**

**Tech Stack:** Vanilla HTML/CSS/JS, existing `styles.css` glassmorphism classes. No test framework exists in `Webwerf/` — every task ends with explicit manual browser verification steps instead of automated tests (approved in the spec).

**Spec:** `docs/superpowers/specs/2026-07-09-personeel-dashboard-design.md`

---

## How to run the site for verification

The pages are static; the FastAPI backend is NOT needed for these features (all new data is mock). Serve `Webwerf/` locally:

```powershell
cd C:\Users\Connor\Documents\Capstone\span3\Webwerf
py -m http.server 8080
```

(Use `python -m http.server 8080` if `py` is unavailable.)

To simulate a logged-in user without the backend, open http://localhost:8080/home.html, open DevTools console, and run:

```js
localStorage.setItem('isLoggedIn', 'true');
localStorage.setItem('user_role', 'Personeel');   // or 'Administrateur', 'Sekuriteit_Wag', 'Kampus_Opsigter'
```

Then navigate to the page under test. (The real login flow also works if the backend is running, but is not required.)

---

## File map

| File | Change | Responsibility |
|---|---|---|
| `Webwerf/personeel.html` | Create | Page skeleton: navbar, klas dropdown, dashboard panel, kalender+register panel |
| `Webwerf/personeel.js` | Create | Mock classes/rosters, seeded attendance generator, dashboard/calendar/roster rendering |
| `Webwerf/main.js` | Modify | Personeel gate for `personeel.html`; dynamic "My Klasse" nav link |
| `Webwerf/styles.css` | Modify (append) | `.kalender*` classes only |
| `Webwerf/admin.html` | Modify | "Outo-Uitskandering" panel markup in `.panels` grid |
| `Webwerf/admin.js` | Modify | Demo save handler (no persistence) |

---

### Task 1: `personeel.html` page skeleton

**Files:**
- Create: `Webwerf/personeel.html`

- [ ] **Step 1: Create the page**

Create `Webwerf/personeel.html` with exactly this content. It mirrors `kampus.html`'s structure (navbar, `.top-controls`, `.panels`, `.glass-card` panels, `.admin-list` containers). All element IDs referenced later by `personeel.js` are defined here.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MOON — My Klasse</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <!-- Personeel toegang: slegs Personeel-rol (gate in main.js) -->
  <nav class="navbar">
    <a href="home.html" class="navbar-logo" aria-label="MOON">MOON</a>
    <a href="home.html">Tuis</a>
    <a href="kampus.html">Kampus</a>
    <a href="koshuis.html">Koshuis</a>
    <a href="events.html">Events</a>
    <a href="personeel.html" class="active">My Klasse</a>
    <div class="navbar-right">
      <button class="btn-outline" type="button" onclick="logOut()">Teken Uit</button>
    </div>
  </nav>

  <main class="page" id="personeel-page">
    <!-- Top controls: klas select links, gekose datum regs -->
    <section class="top-controls space-between" aria-label="Opsies">
      <div class="control-group">
        <label class="field-label" for="klas-select">Kies Klas</label>
        <select class="glass-select" id="klas-select" name="klas-select" style="width:260px"></select>
      </div>
      <div class="control-group">
        <span class="field-label">Gekose Datum</span>
        <span id="dash-datum" style="font-size:14px;font-weight:600">--</span>
      </div>
    </section>

    <!-- Two-panel layout soos kampus.html -->
    <section class="panels">
      <!-- Links: bywoning dashboard -->
      <article class="glass-card panel" aria-label="Bywoning Dashboard">
        <h2>Klas Bywoning</h2>
        <div class="dashboard-grid">
          <div class="card" id="dash-in-count">Ingeskandeer: --</div>
          <div class="card" id="dash-out-count">Nie ingeskandeer: --</div>
          <div class="card" id="dash-total-count">Totaal studente: --</div>
          <div class="card" id="dash-percent-count">Bywoning: --</div>
          <div class="card wide" id="dash-in-card" style="flex-direction:column;align-items:stretch">
            <strong>Studente ingeskandeer</strong>
            <div id="dash-in-list" class="admin-list" style="margin-top:8px"></div>
          </div>
          <div class="card wide" id="dash-out-card" style="flex-direction:column;align-items:stretch">
            <strong>Studente nie ingeskandeer</strong>
            <div id="dash-out-list" class="admin-list" style="margin-top:8px"></div>
          </div>
        </div>
      </article>

      <!-- Regs: kalender + klasregister -->
      <article class="glass-card panel" aria-label="Kalender en Klasregister">
        <h2>Kalender</h2>
        <div class="kalender">
          <div class="kalender-header">
            <button class="btn-outline btn-sm" id="kal-prev" type="button" aria-label="Vorige maand">&larr;</button>
            <div class="kalender-title" id="kal-title">--</div>
            <button class="btn-outline btn-sm" id="kal-next" type="button" aria-label="Volgende maand">&rarr;</button>
          </div>
          <div class="kalender-grid" id="kal-grid"></div>
        </div>

        <h2 style="margin-top:14px">Klasregister</h2>
        <div class="list-search">
          <input class="glass-input" type="search" id="roster-search"
                 aria-label="Soek student" placeholder="Soek student...">
        </div>
        <div id="roster-list" class="admin-list" aria-label="Klasregister lys"></div>
      </article>
    </section>
  </main>

  <div class="action-bar">
    <button class="btn-outline" type="button"
            onclick="window.location.href='home.html'">← Terug</button>
  </div>

  <script src="main.js"></script>
  <script src="personeel.js"></script>
</body>
</html>
```

Note: `personeel.js` does not exist yet — the browser logs a 404 for it until Task 4. That is expected and harmless.

- [ ] **Step 2: Verify in browser**

Serve the site (see "How to run" above), set `localStorage` role to `Personeel`, open http://localhost:8080/personeel.html.

Expected: page renders with navbar ("My Klasse" highlighted), "Kies Klas" dropdown (empty), left "Klas Bywoning" panel with four `--` cards and two empty wide cards, right panel with empty Kalender header/grid and Klasregister search box. The calendar has no styling yet (Task 3).

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git add Webwerf/personeel.html
git commit -m "Add personeel.html skeleton for class attendance dashboard"
```

---

### Task 2: Access gate + "My Klasse" nav link in `main.js`

**Files:**
- Modify: `Webwerf/main.js` (the IIFE at lines 44–92: gate block and nav-link block)

- [ ] **Step 1: Add the Personeel gate**

In `Webwerf/main.js`, find this existing block:

```js
  // Silently redirect non-admins away from admin.html
  if (currentPage === 'admin.html' && userRole !== 'Administrateur') {
    window.location.href = 'home.html';
    return;
  }
```

Insert directly **after** it:

```js
  // Silently redirect non-personeel away from personeel.html.
  // Slegs die Personeel-rol (nie Admin, Sekuriteit_Wag of Kampus_Opsigter nie)
  // mag die klas-bywoning blad sien.
  if (currentPage === 'personeel.html' && userRole !== 'Personeel') {
    window.location.href = 'home.html';
    return;
  }
```

- [ ] **Step 2: Add the dynamic "My Klasse" nav link**

In the same IIFE, find the closing of the admin nav-link block (ends with the `});` that closes `document.addEventListener('DOMContentLoaded', ...)` followed by `}` closing the `if (userRole === 'Administrateur' ...)` statement). Insert directly **after** that closing `}` and before the IIFE's final `})();`:

```js

  // Show the "My Klasse" nav link only for Personeel users
  if (userRole === 'Personeel' && currentPage !== 'login.html') {
    document.addEventListener('DOMContentLoaded', function () {
      var navbar = document.querySelector('.navbar');
      if (!navbar) return;

      // Don't add if already present (e.g. on personeel.html itself)
      if (navbar.querySelector('a[href="personeel.html"]')) return;

      var personeelLink = document.createElement('a');
      personeelLink.href = 'personeel.html';
      personeelLink.textContent = 'My Klasse';

      var navRight = navbar.querySelector('.navbar-right');
      if (navRight) {
        navbar.insertBefore(personeelLink, navRight);
      } else {
        navbar.appendChild(personeelLink);
      }
    });
  }
```

- [ ] **Step 3: Verify in browser**

With the site served:
1. Set `localStorage.setItem('user_role','Personeel')` → open `home.html`. Expected: "My Klasse" link appears in navbar; clicking it opens `personeel.html` and you stay there.
2. Set `localStorage.setItem('user_role','Administrateur')` → open `personeel.html` directly. Expected: silent redirect to `home.html`; navbar shows "Admin" but NOT "My Klasse".
3. Repeat with `'Sekuriteit_Wag'` and `'Kampus_Opsigter'`. Expected: same redirect, no "My Klasse" link.
4. On `personeel.html` as Personeel: only ONE "My Klasse" link (the static one; the dynamic insert is skipped).

- [ ] **Step 4: Commit**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git add Webwerf/main.js
git commit -m "Gate personeel.html to Personeel role and add My Klasse nav link"
```

---

### Task 3: Calendar styles in `styles.css`

**Files:**
- Modify: `Webwerf/styles.css` (append at end of file)

- [ ] **Step 1: Append calendar styles**

Append this block to the end of `Webwerf/styles.css`. It only uses existing `:root` tokens; no existing rules are edited.

```css

/* ─── Kalender (personeel.html) ─────────────────────────────────────────── */
.kalender{margin-bottom:4px}
.kalender-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.kalender-title{font-size:13px;font-weight:700;color:var(--text-1)}
.kalender-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
.kalender-dagnaam{
  font-size:10px;font-weight:600;color:var(--text-muted);
  text-align:center;padding:4px 0;text-transform:uppercase;
}
.kalender-dag{
  position:relative;
  aspect-ratio:1/1;
  display:flex;align-items:center;justify-content:center;
  font-family:'Inter',sans-serif;font-size:12px;color:var(--text-2);
  background:var(--surface-1);
  border:1px solid transparent;border-radius:var(--r-sm);
  cursor:pointer;
}
.kalender-dag:hover{background:var(--surface-2);color:var(--text-1)}
.kalender-dag--leeg{background:transparent;cursor:default;pointer-events:none}
.kalender-dag--vandag{border-color:var(--border-em)}
.kalender-dag--gekies{background:var(--accent);color:#fff;font-weight:700}
.kalender-dag--gekies:hover{background:var(--accent)}
.kalender-dag--klasdag::after{
  content:'';position:absolute;bottom:4px;left:50%;transform:translateX(-50%);
  width:4px;height:4px;border-radius:50%;background:var(--accent-2);
}
.kalender-dag--gekies.kalender-dag--klasdag::after{background:#fff}
```

- [ ] **Step 2: Verify no regressions**

Reload `personeel.html`, `kampus.html`, and `admin.html` in the browser. Expected: existing pages look unchanged (styles were only appended); `personeel.html`'s calendar area is still empty (grid renders in Task 4).

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git add Webwerf/styles.css
git commit -m "Add kalender styles for personeel dashboard"
```

---

### Task 4: `personeel.js` — mock data, attendance generator, rendering

**Files:**
- Create: `Webwerf/personeel.js`

- [ ] **Step 1: Create the module**

Create `Webwerf/personeel.js` with exactly this content:

```js
/**
 * personeel.js — logic for personeel.html only.
 *
 * DEMO: alle klas- en bywoningsdata op hierdie blad is mock data.
 * Die backend het nog geen personeel↔klas koppeling of klasregister nie.
 * Bywoning word deterministies gegenereer (seed = klas + datum) sodat
 * dieselfde dag altyd dieselfde resultaat wys, sonder enige stoor.
 *
 * Depends on:
 *   - main.js (login gate + Personeel gate)
 *   - styles.css (.kalender* klasse)
 *   - HTML ids: klas-select, dash-datum, dash-in-count, dash-out-count,
 *     dash-total-count, dash-percent-count, dash-in-list, dash-out-list,
 *     kal-title, kal-prev, kal-next, kal-grid, roster-search, roster-list.
 */

(function () {
  // ----- Mock klasse met klasregisters (demo data) -----
  var MOCK_KLASSE = [
    {
      id: 'WIS114',
      naam: 'WIS114 — Klaskamer A',
      studente: [
        { naam: 'Anika',   van: 'Botha',           nommer: 'STU2024001' },
        { naam: 'Dewald',  van: 'Pretorius',       nommer: 'STU2024002' },
        { naam: 'Elmarie', van: 'van der Merwe',   nommer: 'STU2024003' },
        { naam: 'Francois', van: 'Joubert',        nommer: 'STU2024004' },
        { naam: 'Hannelie', van: 'Coetzee',        nommer: 'STU2024005' },
        { naam: 'Jaco',    van: 'Steyn',           nommer: 'STU2024006' },
        { naam: 'Karla',   van: 'du Plessis',      nommer: 'STU2024007' },
        { naam: 'Lourens', van: 'Venter',          nommer: 'STU2024008' },
        { naam: 'Mariska', van: 'Nel',             nommer: 'STU2024009' },
        { naam: 'Pieter',  van: 'Fourie',          nommer: 'STU2024010' },
        { naam: 'Rentia',  van: 'Swanepoel',       nommer: 'STU2024011' },
        { naam: 'Tiaan',   van: 'Kruger',          nommer: 'STU2024012' }
      ]
    },
    {
      id: 'FIS121',
      naam: 'FIS121 — Klaskamer B',
      studente: [
        { naam: 'Bernadette', van: 'Olivier',      nommer: 'STU2024013' },
        { naam: 'Christiaan', van: 'Bezuidenhout', nommer: 'STU2024014' },
        { naam: 'Elsabe',  van: 'Meyer',           nommer: 'STU2024015' },
        { naam: 'Gideon',  van: 'Erasmus',         nommer: 'STU2024016' },
        { naam: 'Ilse',    van: 'van Rensburg',    nommer: 'STU2024017' },
        { naam: 'Kobus',   van: 'Scholtz',         nommer: 'STU2024018' },
        { naam: 'Lizelle', van: 'Barnard',         nommer: 'STU2024019' },
        { naam: 'Neels',   van: 'Terblanche',      nommer: 'STU2024020' },
        { naam: 'Ronel',   van: 'Grobler',         nommer: 'STU2024021' },
        { naam: 'Wian',    van: 'de Klerk',        nommer: 'STU2024022' }
      ]
    },
    {
      id: 'RKN214',
      naam: 'RKN214 — Lokaal C',
      studente: [
        { naam: 'Adele',   van: 'Ferreira',        nommer: 'STU2024023' },
        { naam: 'Braam',   van: 'Viljoen',         nommer: 'STU2024024' },
        { naam: 'Chanel',  van: 'Roux',            nommer: 'STU2024025' },
        { naam: 'Divan',   van: 'Lombard',         nommer: 'STU2024026' },
        { naam: 'Este',    van: 'Marais',          nommer: 'STU2024027' },
        { naam: 'Gerhard', van: 'Odendaal',        nommer: 'STU2024028' },
        { naam: 'Janke',   van: 'Visagie',         nommer: 'STU2024029' },
        { naam: 'Marnus',  van: 'Bester',          nommer: 'STU2024030' },
        { naam: 'Nadia',   van: 'Strydom',         nommer: 'STU2024031' },
        { naam: 'Ruan',    van: 'le Roux',         nommer: 'STU2024032' },
        { naam: 'Zander',  van: 'Human',           nommer: 'STU2024033' }
      ]
    }
  ];

  // ----- Cached DOM nodes (null-safe checks before use) -----
  var klasSelect = document.getElementById('klas-select');
  var dashDatum = document.getElementById('dash-datum');
  var dashInCount = document.getElementById('dash-in-count');
  var dashOutCount = document.getElementById('dash-out-count');
  var dashTotalCount = document.getElementById('dash-total-count');
  var dashPercentCount = document.getElementById('dash-percent-count');
  var dashInList = document.getElementById('dash-in-list');
  var dashOutList = document.getElementById('dash-out-list');
  var kalTitle = document.getElementById('kal-title');
  var kalPrev = document.getElementById('kal-prev');
  var kalNext = document.getElementById('kal-next');
  var kalGrid = document.getElementById('kal-grid');
  var rosterSearch = document.getElementById('roster-search');
  var rosterList = document.getElementById('roster-list');

  // ----- Module state -----
  var vandag = new Date();
  vandag.setHours(0, 0, 0, 0);

  var currentKlas = MOCK_KLASSE[0];
  var selectedDate = new Date(vandag);
  var displayYear = vandag.getFullYear();
  var displayMonth = vandag.getMonth();

  var MAANDE = ['Januarie', 'Februarie', 'Maart', 'April', 'Mei', 'Junie',
                'Julie', 'Augustus', 'September', 'Oktober', 'November', 'Desember'];
  var DAG_NAME = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Sa', 'So'];

  // ----- Deterministiese "random" (seed = klas + datum) -----

  /** djb2-agtige string hash → 32-bit unsigned int. */
  function hashString(str) {
    var h = 5381;
    for (var i = 0; i < str.length; i++) {
      h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  /** mulberry32 PRNG — klein, vinnig, deterministies vir 'n gegewe seed. */
  function mulberry32(seed) {
    return function () {
      seed |= 0;
      seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function isoDate(d) {
    var m = String(d.getMonth() + 1);
    var dd = String(d.getDate());
    if (m.length < 2) m = '0' + m;
    if (dd.length < 2) dd = '0' + dd;
    return d.getFullYear() + '-' + m + '-' + dd;
  }

  function formatDatum(d) {
    return d.getDate() + ' ' + MAANDE[d.getMonth()] + ' ' + d.getFullYear();
  }

  /** Klasdae: weeksdae (Ma–Vr) wat nie in die toekoms lê nie. */
  function isKlasdag(d) {
    var dag = d.getDay(); // 0 = Sondag ... 6 = Saterdag
    return dag >= 1 && dag <= 5 && d.getTime() <= vandag.getTime();
  }

  /**
   * Deterministiese bywoning vir 'n klas op 'n datum.
   * Return null as daar geen klasdata is nie (naweek / toekoms), anders
   * { ingeskandeer: [{ student, tyd }], nieIngeskandeer: [student] }.
   */
  function kryBywoning(klas, datum) {
    if (!isKlasdag(datum)) return null;

    var rand = mulberry32(hashString(klas.id + '|' + isoDate(datum)));
    var ingeskandeer = [];
    var nieIngeskandeer = [];

    klas.studente.forEach(function (s) {
      if (rand() < 0.78) {
        var minuut = Math.floor(rand() * 25);
        ingeskandeer.push({
          student: s,
          tyd: '08:' + (minuut < 10 ? '0' : '') + minuut
        });
      } else {
        nieIngeskandeer.push(s);
      }
    });

    return { ingeskandeer: ingeskandeer, nieIngeskandeer: nieIngeskandeer };
  }

  // ----- Kaartjies (selfde markup as kampus.js user cards) -----
  function createStudentCard(student, subtitle) {
    var card = document.createElement('div');
    card.className = 'user-card';
    card.dataset.search = (student.naam + ' ' + student.van + ' ' + student.nommer).toLowerCase();

    var infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    var nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    nameDiv.textContent = student.naam + ' ' + student.van;
    infoDiv.appendChild(nameDiv);

    var subDiv = document.createElement('div');
    subDiv.className = 'admin-user-email';
    subDiv.textContent = subtitle || '';
    infoDiv.appendChild(subDiv);

    card.appendChild(infoDiv);
    return card;
  }

  function renderLeegBoodskap(container, boodskap) {
    container.innerHTML = '';
    var empty = document.createElement('div');
    empty.className = 'user-card';
    var info = document.createElement('div');
    info.className = 'admin-user-info';
    var msg = document.createElement('div');
    msg.className = 'admin-user-email';
    msg.textContent = boodskap;
    info.appendChild(msg);
    empty.appendChild(info);
    container.appendChild(empty);
  }

  // ----- Dashboard rendering -----
  function renderDashboard() {
    var bywoning = kryBywoning(currentKlas, selectedDate);

    if (dashDatum) dashDatum.textContent = formatDatum(selectedDate);
    if (dashTotalCount) dashTotalCount.textContent = 'Totaal studente: ' + currentKlas.studente.length;

    if (!bywoning) {
      if (dashInCount) dashInCount.textContent = 'Ingeskandeer: --';
      if (dashOutCount) dashOutCount.textContent = 'Nie ingeskandeer: --';
      if (dashPercentCount) dashPercentCount.textContent = 'Bywoning: --';
      if (dashInList) renderLeegBoodskap(dashInList, 'Geen klasdata vir hierdie dag nie.');
      if (dashOutList) renderLeegBoodskap(dashOutList, 'Geen klasdata vir hierdie dag nie.');
      return;
    }

    var totaal = currentKlas.studente.length;
    var persent = totaal > 0 ? Math.round((bywoning.ingeskandeer.length / totaal) * 100) : 0;

    if (dashInCount) dashInCount.textContent = 'Ingeskandeer: ' + bywoning.ingeskandeer.length;
    if (dashOutCount) dashOutCount.textContent = 'Nie ingeskandeer: ' + bywoning.nieIngeskandeer.length;
    if (dashPercentCount) dashPercentCount.textContent = 'Bywoning: ' + persent + '%';

    if (dashInList) {
      dashInList.innerHTML = '';
      if (bywoning.ingeskandeer.length === 0) {
        renderLeegBoodskap(dashInList, 'Geen studente ingeskandeer nie.');
      } else {
        bywoning.ingeskandeer.forEach(function (b) {
          dashInList.appendChild(
            createStudentCard(b.student, b.student.nommer + ' · ingeskandeer ' + b.tyd)
          );
        });
      }
    }

    if (dashOutList) {
      dashOutList.innerHTML = '';
      if (bywoning.nieIngeskandeer.length === 0) {
        renderLeegBoodskap(dashOutList, 'Alle studente is ingeskandeer.');
      } else {
        bywoning.nieIngeskandeer.forEach(function (s) {
          dashOutList.appendChild(createStudentCard(s, s.nommer));
        });
      }
    }
  }

  // ----- Kalender rendering -----
  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth() === b.getMonth() &&
           a.getDate() === b.getDate();
  }

  function renderKalender() {
    if (!kalGrid || !kalTitle) return;

    kalTitle.textContent = MAANDE[displayMonth] + ' ' + displayYear;
    kalGrid.innerHTML = '';

    // Dagname-ry (Ma ... So)
    DAG_NAME.forEach(function (naam) {
      var cell = document.createElement('div');
      cell.className = 'kalender-dagnaam';
      cell.textContent = naam;
      kalGrid.appendChild(cell);
    });

    var eerste = new Date(displayYear, displayMonth, 1);
    var offset = (eerste.getDay() + 6) % 7; // Maandag in die eerste kolom
    var daeInMaand = new Date(displayYear, displayMonth + 1, 0).getDate();

    for (var i = 0; i < offset; i++) {
      var leeg = document.createElement('div');
      leeg.className = 'kalender-dag kalender-dag--leeg';
      kalGrid.appendChild(leeg);
    }

    for (var d = 1; d <= daeInMaand; d++) {
      (function (dagNommer) {
        var datum = new Date(displayYear, displayMonth, dagNommer);

        var cell = document.createElement('button');
        cell.type = 'button';
        cell.className = 'kalender-dag';
        cell.textContent = String(dagNommer);

        if (sameDay(datum, vandag)) cell.classList.add('kalender-dag--vandag');
        if (sameDay(datum, selectedDate)) cell.classList.add('kalender-dag--gekies');
        if (isKlasdag(datum)) cell.classList.add('kalender-dag--klasdag');

        cell.addEventListener('click', function () {
          selectedDate = datum;
          renderKalender();
          renderDashboard();
        });

        kalGrid.appendChild(cell);
      })(d);
    }
  }

  // ----- Klasregister (regterpaneel-lys) -----
  function renderRoster() {
    if (!rosterList) return;
    rosterList.innerHTML = '';
    currentKlas.studente.forEach(function (s) {
      rosterList.appendChild(createStudentCard(s, s.nommer));
    });
    applyRosterFilter();
  }

  /** Hide roster rows that do not contain the search text. */
  function applyRosterFilter() {
    if (!rosterSearch || !rosterList) return;
    var query = rosterSearch.value.trim().toLowerCase();
    var rows = rosterList.querySelectorAll('.user-card');

    rows.forEach(function (row) {
      var searchable = row.dataset.search || (row.textContent || '').toLowerCase();
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
  }

  // ----- Klas dropdown -----
  function populateKlasSelect() {
    if (!klasSelect) return;
    klasSelect.innerHTML = '';
    MOCK_KLASSE.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = k.id;
      opt.textContent = k.naam;
      klasSelect.appendChild(opt);
    });
  }

  // ----- Event wiring -----
  if (klasSelect) {
    klasSelect.addEventListener('change', function () {
      var gekies = MOCK_KLASSE.filter(function (k) {
        return k.id === klasSelect.value;
      })[0];
      if (gekies) currentKlas = gekies;
      renderDashboard();
      renderRoster();
    });
  }

  if (kalPrev) {
    kalPrev.addEventListener('click', function () {
      displayMonth--;
      if (displayMonth < 0) {
        displayMonth = 11;
        displayYear--;
      }
      renderKalender();
    });
  }

  if (kalNext) {
    kalNext.addEventListener('click', function () {
      displayMonth++;
      if (displayMonth > 11) {
        displayMonth = 0;
        displayYear++;
      }
      renderKalender();
    });
  }

  if (rosterSearch) {
    rosterSearch.addEventListener('input', applyRosterFilter);
  }

  // ----- Bootstrap -----
  document.addEventListener('DOMContentLoaded', function () {
    populateKlasSelect();
    renderKalender();
    renderDashboard();
    renderRoster();
  });
})();
```

- [ ] **Step 2: Verify in browser**

As role `Personeel`, open http://localhost:8080/personeel.html and check:

1. Dropdown lists the three mock classes; "Gekose Datum" shows today (e.g. "9 Julie 2026").
2. Count cards show real numbers; *Bywoning* % matches ingeskandeer/totaal; the two wide lists show students, scanned-in entries include "· ingeskandeer 08:MM".
3. Calendar shows the current month in Afrikaans, Monday first; today is outlined AND filled (selected); past weekdays have a small cyan dot; weekends/future days have none.
4. Click a past weekday → panels update; click the same day again → identical data (deterministic). Reload page, click the same day → still identical.
5. Click a weekend or future day → cards show `--` and lists show "Geen klasdata vir hierdie dag nie."
6. Switch class in the dropdown → different roster and attendance; Klasregister list updates.
7. Type in "Soek student..." → roster filters by name/number.
8. Prev/next month arrows navigate; December→January crosses the year correctly.
9. Console shows no JS errors.

- [ ] **Step 3: Commit**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git add Webwerf/personeel.js
git commit -m "Add personeel.js with mock class attendance, calendar and roster"
```

---

### Task 5: Admin "Outo-Uitskandering" demo panel

**Files:**
- Modify: `Webwerf/admin.html` (add panel inside `<section class="panels">`)
- Modify: `Webwerf/admin.js` (add handler before the INIT section)

- [ ] **Step 1: Add the panel markup**

In `Webwerf/admin.html`, find the closing of the Koshuise panel:

```html
      <article class="glass-card panel" aria-label="Koshuise">
        <h2>Koshuise</h2>
        <div class="list-search">
          <input class="glass-input" type="search" id="koshuis-search"
                 aria-label="Soek koshuis" placeholder="Soek koshuis...">
        </div>
        <div class="admin-list" id="koshuis-list">
          <!-- Loaded from API by admin.js -->
        </div>
      </article>
    </section>
```

Replace with:

```html
      <article class="glass-card panel" aria-label="Koshuise">
        <h2>Koshuise</h2>
        <div class="list-search">
          <input class="glass-input" type="search" id="koshuis-search"
                 aria-label="Soek koshuis" placeholder="Soek koshuis...">
        </div>
        <div class="admin-list" id="koshuis-list">
          <!-- Loaded from API by admin.js -->
        </div>
      </article>
      <article class="glass-card panel" aria-label="Outo-Uitskandering">
        <h2>Outo-Uitskandering</h2>
        <p style="font-size:12px;color:var(--text-2);margin-bottom:14px">
          Stel die tyd waarop alle gebruikers outomaties van kampusgronde
          uitgeskandeer word.
        </p>
        <div class="field">
          <label class="field-label" for="auto-scanout-time">Uitskandering Tyd</label>
          <input class="glass-input" type="time" id="auto-scanout-time"
                 value="18:00" style="width:160px;display:block;margin-top:6px">
        </div>
        <button class="btn-primary" id="save-auto-scanout" type="button">Stoor Tyd</button>
        <div id="auto-scanout-msg"
             style="margin-top:10px;font-size:12px;color:var(--success);display:none"></div>
        <p style="margin-top:12px;font-size:11px;color:var(--warning)">
          Demo — backend word later gekoppel.
        </p>
      </article>
    </section>
```

- [ ] **Step 2: Add the demo save handler**

In `Webwerf/admin.js`, find the INIT banner:

```js
  // =====================================================================
  //  INIT
  // =====================================================================
```

Insert directly **before** it:

```js
  // =====================================================================
  //  OUTO-UITSKANDERING (demo — geen backend, geen stoor nie)
  // =====================================================================

  var autoScanoutTime = document.getElementById('auto-scanout-time');
  var saveAutoScanoutBtn = document.getElementById('save-auto-scanout');
  var autoScanoutMsg = document.getElementById('auto-scanout-msg');

  if (saveAutoScanoutBtn) {
    saveAutoScanoutBtn.addEventListener('click', function () {
      var tyd = autoScanoutTime ? autoScanoutTime.value : '';

      if (!tyd) {
        alert('Kies asseblief \'n tyd.');
        return;
      }

      if (autoScanoutMsg) {
        autoScanoutMsg.textContent = 'Outo-uitskandering gestel vir ' + tyd + '.';
        autoScanoutMsg.style.display = 'block';
      }
    });
  }

```

- [ ] **Step 3: Verify in browser**

As role `Administrateur`, open http://localhost:8080/admin.html:
1. "Outo-Uitskandering" panel appears in the panels grid with time input showing 18:00, the "Stoor Tyd" button and the amber "Demo — backend word later gekoppel." note. (The API-backed lists may show load errors without the backend running — that's pre-existing and unrelated.)
2. Change the time to 21:30 → click "Stoor Tyd" → green message "Outo-uitskandering gestel vir 21:30." appears.
3. Clear the time field → click "Stoor Tyd" → alert "Kies asseblief 'n tyd."
4. Reload the page → input is back to 18:00 and no message (nothing persisted).
5. DevTools → Network tab while clicking "Stoor Tyd": no request is made.

- [ ] **Step 4: Commit**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git add Webwerf/admin.html Webwerf/admin.js
git commit -m "Add display-only auto scan-out time demo panel to admin page"
```

---

### Task 6: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Confirm Backend/ untouched**

```powershell
cd C:\Users\Connor\Documents\Capstone\span3
git log --oneline -8
git diff HEAD~5 --stat -- Backend/
```

Expected: the diff against the pre-work commit shows NO files under `Backend/` (empty output for the second command; adjust `HEAD~5` to the number of commits made in Tasks 1–5).

- [ ] **Step 2: Full role sweep in browser**

With the site served, walk each role via `localStorage.setItem('user_role', ...)` + `localStorage.setItem('isLoggedIn','true')`:

| Role | personeel.html | "My Klasse" link | admin.html |
|---|---|---|---|
| `Personeel` | loads, dashboard works | visible | redirects to home.html |
| `Administrateur` | redirects to home.html | hidden | loads, Outo-Uitskandering panel works |
| `Sekuriteit_Wag` | redirects to home.html | hidden | redirects to home.html |
| `Kampus_Opsigter` | redirects to home.html | hidden | redirects to home.html |
| `Student` | blocked site-wide (existing alert + logout) | n/a | n/a |

- [ ] **Step 3: Report results**

Report any deviation from the table to the user before claiming the work complete (per superpowers:verification-before-completion).
