# Kampus Dashboard Live Scan Status — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `kampus.html` to `GET /kampusse/status` and `GET /kampusse/{kampus_id}/status` so the dashboard shows live scanned-in/out counts and user lists per campus, while the right panel shows a constant full roster of all students and personeel.

**Architecture:** Three files are touched in order — API client first, then HTML structure, then JS logic. No new files are created. The right-panel lists are loaded once on page load and never re-rendered on campus change; only the dashboard cards refresh.

**Tech Stack:** Vanilla JS (ES5-compatible IIFE pattern matching existing codebase), FastAPI backend, HTML/CSS already in place.

---

## File Map

| File | Change |
|------|--------|
| `Webwerf/website_api_calls.js` | Add `fetchKampusseStatus()` and `fetchKampusStatus(kampusId)` to `window.MoonApi` |
| `Webwerf/kampus.html` | Replace 5 mock `.dashboard-grid` cards with 8 real data cards; add `<ul id="personeel-list">` inside `.bottom-inner-panel` |
| `Webwerf/kampus.js` | Add module state vars, `renderUserList()`, `loadGebruikersLys()`, `loadPageKampusDropdown()`, `refreshDashboard()`, `startPolling()`, personeel search filter; wire everything in `DOMContentLoaded` |

---

## Task 1: Add API methods to `website_api_calls.js`

**Files:**
- Modify: `Webwerf/website_api_calls.js`

- [ ] **Step 1: Open the file and locate the closing brace of `window.MoonApi`**

  In `website_api_calls.js`, find the line that reads:
  ```js
    createGebruiker: async function (data) {
  ```
  The block ends a few lines later with `},` then the closing `};` of `window.MoonApi`. Insert the two new methods **before** the `};`.

- [ ] **Step 2: Add the two new methods**

  Insert the following two methods as the last entries in the `window.MoonApi = { ... }` block (after `createGebruiker`, before the closing `};`):

  ```js
      /**
       * GET /kampusse/status
       * Returns summary scan counts for all campuses. No auth required.
       */
      fetchKampusseStatus: async function () {
        const r = await apiRequest('/kampusse/status', {
          method: 'GET',
        });
        return r.body;
      },

      /**
       * GET /kampusse/{kampusId}/status
       * Returns detailed scanned-in/out lists for a specific campus. No auth required.
       */
      fetchKampusStatus: async function (kampusId) {
        const r = await apiRequest('/kampusse/' + kampusId + '/status', {
          method: 'GET',
        });
        return r.body;
      },
  ```

- [ ] **Step 3: Verify the file is valid JS**

  Open `Webwerf/website_api_calls.js` in the browser (or paste into browser console). There should be no syntax errors. You can confirm by opening DevTools → Console and typing:
  ```
  typeof window.MoonApi.fetchKampusseStatus
  ```
  Expected: `"function"`

- [ ] **Step 4: Commit**

  ```bash
  git add Webwerf/website_api_calls.js
  git commit -m "feat: add fetchKampusseStatus and fetchKampusStatus to MoonApi"
  ```

---

## Task 2: Replace mock dashboard cards in `kampus.html`

**Files:**
- Modify: `Webwerf/kampus.html`

- [ ] **Step 1: Locate the dashboard grid**

  In `kampus.html`, find:
  ```html
        <div class="dashboard-grid">
          <div class="card">Totale gebruikers</div>
          <div class="card">Aktiewe sessies</div>
          <div class="card mock-circle-card">
            <div class="mock-circle" aria-label="Mock circle diagram"></div>
          </div>
          <div class="card mock-graph-card" aria-label="Mock graph">
            <div class="mock-graph">
              <span class="bar bar-1"></span>
              <span class="bar bar-2"></span>
              <span class="bar bar-3"></span>
              <span class="bar bar-4"></span>
              <span class="bar bar-5"></span>
            </div>
          </div>
          <div class="card wide">Toegang oorsig</div>
        </div>
  ```

- [ ] **Step 2: Replace the entire dashboard-grid block**

  Replace everything from `<div class="dashboard-grid">` to its closing `</div>` with:

  ```html
        <div class="dashboard-grid">
          <div class="card" id="dash-student-in-count">Studente ingeklokt: --</div>
          <div class="card" id="dash-personeel-in-count">Personeel ingeklokt: --</div>
          <div class="card" id="dash-student-out-count">Studente uitgeklokt: --</div>
          <div class="card" id="dash-personeel-out-count">Personeel uitgeklokt: --</div>
          <div class="card wide" id="dash-student-in-card">
            <strong>Studente tans op kampus</strong>
            <ul id="dash-student-in-list" style="margin:6px 0 0;padding-left:16px;font-weight:normal"></ul>
          </div>
          <div class="card wide" id="dash-student-out-card">
            <strong>Studente nie op kampus</strong>
            <ul id="dash-student-out-list" style="margin:6px 0 0;padding-left:16px;font-weight:normal"></ul>
          </div>
          <div class="card wide" id="dash-personeel-in-card">
            <strong>Personeel tans op kampus</strong>
            <ul id="dash-personeel-in-list" style="margin:6px 0 0;padding-left:16px;font-weight:normal"></ul>
          </div>
          <div class="card wide" id="dash-personeel-out-card">
            <strong>Personeel nie op kampus</strong>
            <ul id="dash-personeel-out-list" style="margin:6px 0 0;padding-left:16px;font-weight:normal"></ul>
          </div>
        </div>
  ```

- [ ] **Step 3: Verify in browser**

  Open `kampus.html` in a browser. The left panel should show 8 cards:
  - Two rows of two count cards each showing `--`
  - Four wide cards with headings and empty lists

- [ ] **Step 4: Commit**

  ```bash
  git add Webwerf/kampus.html
  git commit -m "feat: replace mock dashboard cards with real data card structure"
  ```

---

## Task 3: Add personeel list to right panel in `kampus.html`

**Files:**
- Modify: `Webwerf/kampus.html`

- [ ] **Step 1: Locate the bottom inner panel**

  In `kampus.html`, find:
  ```html
        <div class="bottom-inner-panel" aria-label="Verdere inligting"></div>
  ```

- [ ] **Step 2: Add the personeel `<ul>` inside it**

  Replace that single line with:
  ```html
        <div class="bottom-inner-panel" aria-label="Personeel lys">
          <ul id="personeel-list" class="empty-list" aria-label="Personeel lys"></ul>
        </div>
  ```

- [ ] **Step 3: Verify in browser**

  Inspect the right panel bottom section — `#personeel-list` should now exist in the DOM (empty for now).

- [ ] **Step 4: Commit**

  ```bash
  git add Webwerf/kampus.html
  git commit -m "feat: add personeel-list ul to kampus right panel"
  ```

---

## Task 4: Add module state and `renderUserList()` helper to `kampus.js`

**Files:**
- Modify: `Webwerf/kampus.js`

- [ ] **Step 1: Locate the top of the IIFE in `kampus.js`**

  The file starts with:
  ```js
  (function () {
    // ----- Cached DOM nodes (null-safe checks before use) -----
    const listSearch = document.getElementById('list-search');
  ```

- [ ] **Step 2: Add module-level state variables and `renderUserList()` after the cached DOM nodes block**

  Find the end of the DOM node declarations (the line `const dataSelect = document.getElementById('data-select');`) and insert the following immediately after it:

  ```js
    // ----- Module state -----
    var currentKampusId = null;
    var pollingInterval = null;

    /**
     * Renders an array of user objects into a <ul> element.
     * Each item shows "Naam Van" text.
     * Shows a placeholder if the array is empty.
     */
    function renderUserList(ulElement, users) {
      if (!ulElement) return;
      ulElement.innerHTML = '';
      if (!users || users.length === 0) {
        var empty = document.createElement('li');
        empty.textContent = 'Geen gebruikers nie';
        empty.style.color = 'var(--text-2)';
        ulElement.appendChild(empty);
        return;
      }
      users.forEach(function (u) {
        var li = document.createElement('li');
        li.textContent = (u.GEB_Naam || '') + ' ' + (u.GEB_Van || '');
        ulElement.appendChild(li);
      });
    }
  ```

- [ ] **Step 3: Verify no syntax errors**

  Reload `kampus.html` in the browser. DevTools Console should show no errors.

- [ ] **Step 4: Commit**

  ```bash
  git add Webwerf/kampus.js
  git commit -m "feat: add module state and renderUserList helper to kampus.js"
  ```

---

## Task 5: Add `loadGebruikersLys()` to `kampus.js`

**Files:**
- Modify: `Webwerf/kampus.js`

This function fetches all users once on page load, splits by role, and populates the two constant right-panel lists.

- [ ] **Step 1: Add the function after `renderUserList()`**

  Insert immediately after the `renderUserList` function:

  ```js
    /**
     * Fetch all gebruikers once and populate the constant right-panel lists.
     * Students → #data-list. Personeel → #personeel-list.
     * Never called again after initial page load.
     */
    async function loadGebruikersLys() {
      if (!window.MoonApi) return;

      var json = await window.MoonApi.fetchGebruikers();

      if (!json || !json.sukses || !Array.isArray(json.data)) {
        if (dataList) {
          dataList.innerHTML = '<li>Kon nie gebruikers laai nie.</li>';
        }
        return;
      }

      var students = json.data.filter(function (g) {
        return g.Rol_Naam === 'Student';
      });

      var personeel = json.data.filter(function (g) {
        return g.Rol_Naam === 'Personeel';
      });

      // Render student list
      if (dataList) {
        dataList.innerHTML = '';
        dataList.classList.remove('empty-list');
        if (students.length === 0) {
          dataList.innerHTML = '<li>Geen studente nie</li>';
        } else {
          students.forEach(function (g) {
            var li = document.createElement('li');
            var label = (g.GEB_Naam || '') + ' ' + (g.GEB_Van || '');
            if (g.STU_Nommer) label += ' (' + g.STU_Nommer + ')';
            li.textContent = label;
            dataList.appendChild(li);
          });
        }
      }

      // Render personeel list
      var personeelList = document.getElementById('personeel-list');
      if (personeelList) {
        personeelList.innerHTML = '';
        personeelList.classList.remove('empty-list');
        if (personeel.length === 0) {
          personeelList.innerHTML = '<li>Geen personeel nie</li>';
        } else {
          personeel.forEach(function (g) {
            var li = document.createElement('li');
            var label = (g.GEB_Naam || '') + ' ' + (g.GEB_Van || '');
            if (g.PER_Nommer) label += ' (' + g.PER_Nommer + ')';
            li.textContent = label;
            personeelList.appendChild(li);
          });
        }
      }
    }
  ```

- [ ] **Step 2: Verify in browser**

  Call `loadGebruikersLys()` manually from the DevTools console after the page loads. Both `#data-list` and `#personeel-list` should populate with names (or show "Geen ... nie" if empty).

- [ ] **Step 3: Commit**

  ```bash
  git add Webwerf/kampus.js
  git commit -m "feat: add loadGebruikersLys to populate constant right-panel lists"
  ```

---

## Task 6: Add `refreshDashboard()` to `kampus.js`

**Files:**
- Modify: `Webwerf/kampus.js`

- [ ] **Step 1: Add the function after `loadGebruikersLys()`**

  Insert:

  ```js
    /**
     * Fetch live scan status for a specific campus and update dashboard cards.
     * Does NOT touch the right-panel lists.
     * Splits scanned_in / scanned_out by Rol_Naam to separate students from personeel.
     */
    async function refreshDashboard(kampusId) {
      if (!kampusId || !window.MoonApi) return;

      var json = await window.MoonApi.fetchKampusStatus(kampusId);

      // Helper to reset counts to '--' on error
      function resetCounts() {
        ['dash-student-in-count', 'dash-student-out-count',
         'dash-personeel-in-count', 'dash-personeel-out-count'].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.textContent = el.textContent.replace(/: .*$/, ': --');
        });
      }

      if (!json || !json.sukses || !json.data) {
        resetCounts();
        return;
      }

      var data = json.data;

      var studentIn = (data.scanned_in || []).filter(function (u) {
        return u.Rol_Naam === 'Student';
      });
      var studentOut = (data.scanned_out || []).filter(function (u) {
        return u.Rol_Naam === 'Student';
      });
      var personeelIn = (data.scanned_in || []).filter(function (u) {
        return u.Rol_Naam === 'Personeel';
      });
      var personeelOut = (data.scanned_out || []).filter(function (u) {
        return u.Rol_Naam === 'Personeel';
      });

      // Update count cards
      var stuInCount = document.getElementById('dash-student-in-count');
      var stuOutCount = document.getElementById('dash-student-out-count');
      var perInCount = document.getElementById('dash-personeel-in-count');
      var perOutCount = document.getElementById('dash-personeel-out-count');

      if (stuInCount) stuInCount.textContent = 'Studente ingeklokt: ' + studentIn.length;
      if (stuOutCount) stuOutCount.textContent = 'Studente uitgeklokt: ' + studentOut.length;
      if (perInCount) perInCount.textContent = 'Personeel ingeklokt: ' + personeelIn.length;
      if (perOutCount) perOutCount.textContent = 'Personeel uitgeklokt: ' + personeelOut.length;

      // Update lists
      renderUserList(document.getElementById('dash-student-in-list'), studentIn);
      renderUserList(document.getElementById('dash-student-out-list'), studentOut);
      renderUserList(document.getElementById('dash-personeel-in-list'), personeelIn);
      renderUserList(document.getElementById('dash-personeel-out-list'), personeelOut);
    }
  ```

- [ ] **Step 2: Verify in browser**

  With a valid campus ID (e.g., `1`), call from console:
  ```js
  window.MoonApi.fetchKampusStatus(1).then(console.log)
  ```
  Confirm the response has `scanned_in` and `scanned_out` arrays. Then verify the dashboard cards update with real values.

- [ ] **Step 3: Commit**

  ```bash
  git add Webwerf/kampus.js
  git commit -m "feat: add refreshDashboard to update dashboard cards from campus scan status"
  ```

---

## Task 7: Add `loadPageKampusDropdown()` and `startPolling()` to `kampus.js`

**Files:**
- Modify: `Webwerf/kampus.js`

- [ ] **Step 1: Add both functions after `refreshDashboard()`**

  Insert:

  ```js
    /**
     * Load campuses from GET /kampusse into the page-level #data-select dropdown.
     * After loading, auto-selects the first campus and triggers the first dashboard refresh.
     */
    async function loadPageKampusDropdown() {
      if (!dataSelect || !window.MoonApi) return;

      var json = await window.MoonApi.fetchKampusse();

      if (!json || !json.sukses || !Array.isArray(json.data)) return;

      dataSelect.innerHTML = '';
      json.data.forEach(function (k) {
        var opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        dataSelect.appendChild(opt);
      });

      if (json.data.length > 0) {
        currentKampusId = json.data[0].Kampus_ID;
        refreshDashboard(currentKampusId);
        startPolling(currentKampusId);
      }
    }

    /**
     * Start a 30-second polling interval for the given campus ID.
     * Clears any existing interval first so only one is active at a time.
     */
    function startPolling(kampusId) {
      if (pollingInterval) clearInterval(pollingInterval);
      pollingInterval = setInterval(function () {
        refreshDashboard(currentKampusId);
      }, 30000);
    }
  ```

- [ ] **Step 2: Wire the dropdown `change` event**

  Find the section in `kampus.js` that reads:
  ```js
    // ----- Wire list filter -----
    if (listSearch) {
      listSearch.addEventListener('input', applyListFilter);
    }
  ```

  Add the following block immediately after it:

  ```js
    // ----- Wire campus dropdown -----
    if (dataSelect) {
      dataSelect.addEventListener('change', function () {
        currentKampusId = Number(dataSelect.value);
        refreshDashboard(currentKampusId);
        startPolling(currentKampusId);
      });
    }
  ```

- [ ] **Step 3: Verify in browser**

  Change the campus dropdown. The four count cards and four list cards should update without the right-panel student/personeel lists changing.

- [ ] **Step 4: Commit**

  ```bash
  git add Webwerf/kampus.js
  git commit -m "feat: add loadPageKampusDropdown, startPolling, wire dropdown change"
  ```

---

## Task 8: Add personeel search filter and update `DOMContentLoaded` to `kampus.js`

**Files:**
- Modify: `Webwerf/kampus.js`

- [ ] **Step 1: Add `applyPersoneelFilter()` after the existing `applyListFilter()` function**

  Find the existing function:
  ```js
    /** Hide list rows that do not contain the search text. */
    function applyListFilter() {
  ```

  After the closing `}` of `applyListFilter`, insert:

  ```js
    /** Hide personeel rows that do not contain the search text. */
    function applyPersoneelFilter() {
      var bottomSearch = document.getElementById('bottom-search');
      var personeelList = document.getElementById('personeel-list');
      if (!bottomSearch || !personeelList) return;
      var query = bottomSearch.value.trim().toLowerCase();
      var items = personeelList.querySelectorAll('li');
      items.forEach(function (li) {
        var text = (li.textContent || '').trim().toLowerCase();
        li.hidden = query !== '' && !text.includes(query);
      });
    }
  ```

- [ ] **Step 2: Wire the personeel search input**

  In the event-wiring section, after the line that wires `listSearch`:
  ```js
    if (listSearch) {
      listSearch.addEventListener('input', applyListFilter);
    }
  ```

  Add:

  ```js
    var bottomSearch = document.getElementById('bottom-search');
    if (bottomSearch) {
      bottomSearch.addEventListener('input', applyPersoneelFilter);
    }
  ```

- [ ] **Step 3: Update the `DOMContentLoaded` handler**

  Find the existing handler at the bottom of the IIFE:
  ```js
    // After full DOM (and MoonApi script) are ready, refresh campus dropdown
    document.addEventListener('DOMContentLoaded', function () {
      loadKampusDropdown();
    });
  ```

  Replace it with:

  ```js
    // After full DOM (and MoonApi script) are ready, bootstrap the page
    document.addEventListener('DOMContentLoaded', function () {
      loadKampusDropdown();       // populate modal class-kampus dropdown (existing)
      loadPageKampusDropdown();   // populate #data-select + trigger first dashboard refresh
      loadGebruikersLys();        // populate constant student + personeel right-panel lists
    });
  ```

- [ ] **Step 4: Full browser verification**

  Open `kampus.html`. Confirm:
  1. `#data-select` is populated from the API (not hardcoded Leriba/Peerl/Gerhard strings — actual DB names)
  2. Dashboard cards show real counts on load
  3. Dashboard lists show scanned users (or "Geen gebruikers nie" if none)
  4. Right panel `#data-list` shows all students
  5. Right panel `#personeel-list` shows all personeel
  6. Changing the dropdown updates dashboard cards but NOT the right-panel lists
  7. Typing in `#list-search` filters `#data-list`
  8. Typing in `#bottom-search` filters `#personeel-list`
  9. Wait 30 seconds — dashboard refreshes automatically (check Network tab in DevTools)

- [ ] **Step 5: Commit**

  ```bash
  git add Webwerf/kampus.js
  git commit -m "feat: add personeel search filter and wire DOMContentLoaded bootstrap"
  ```

---

## Self-Review Checklist

- [x] `GET /kampusse/status` — covered by Task 1 (`fetchKampusseStatus`) and used by `loadPageKampusDropdown` via `fetchKampusse` for names; note `fetchKampusseStatus` is added to MoonApi for potential future use but the dropdown itself uses `fetchKampusse` (which already existed) for names + `fetchKampusStatus` for detail
- [x] `GET /kampusse/{id}/status` — covered by Task 1 (`fetchKampusStatus`) and Task 6 (`refreshDashboard`)
- [x] Student list (constant right panel) — Task 5 (`loadGebruikersLys`)
- [x] Personeel list (constant right panel) — Task 5 (`loadGebruikersLys`)
- [x] Dashboard: students scanned in — Task 6 + Task 2 (`#dash-student-in-count`, `#dash-student-in-list`)
- [x] Dashboard: students not scanned in (scanned out) — Task 6 + Task 2 (`#dash-student-out-count`, `#dash-student-out-list`)
- [x] Dashboard: personeel scanned in — Task 6 + Task 2 (`#dash-personeel-in-count`, `#dash-personeel-in-list`)
- [x] Dashboard: personeel not scanned in — Task 6 + Task 2 (`#dash-personeel-out-count`, `#dash-personeel-out-list`)
- [x] Dropdown refreshes dashboard, not right panel — Task 7
- [x] Live polling 30s — Task 7 (`startPolling`)
- [x] Personeel search filter — Task 8 (`applyPersoneelFilter`)
- [x] Student search filter — already existed, preserved in Task 8
- [x] `renderUserList` used consistently by same name across Tasks 4 and 6 — confirmed
- [x] No TBDs or placeholders
