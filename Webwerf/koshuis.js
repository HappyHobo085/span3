/**
 * koshuis.js — logic for koshuis.html only.
 *
 * Depends on:
 *   - main.js (must run first: loads website_api_calls.js → window.MoonApi)
 *   - HTML ids: data-select, list-search, data-list, dash-* dashboard cards.
 *
 * Features:
 *   - Load koshuise into the page dropdown from GET /koshuise.
 *   - Live dashboard via GET /koshuise/{id}/status (30s polling):
 *     scanned-in/out counts + lists and inwoners/kapasiteit card.
 *   - Right panel: searchable list of studente gekoppel aan die gekose koshuis.
 */

(function () {
  // ----- Cached DOM nodes (null-safe checks before use) -----
  const listSearch = document.getElementById('list-search');
  const dataList = document.getElementById('data-list');
  const dataSelect = document.getElementById('data-select');

  // ----- Module state -----
  var currentKoshuisId = null;
  var pollingInterval = null;
  var alleStudente = null; // cache of GET /gebruikers students so dropdown changes re-render locally

  /**
   * Creates an individual glass-card for a user.
   * subtitle is shown under the name (e.g. student number or email).
   * rolNaam is displayed as a role-badge.
   */
  function createUserCard(user, subtitle, rolNaam) {
    var card = document.createElement('div');
    card.className = 'user-card';
    card.dataset.search = ((user.GEB_Naam || '') + ' ' + (user.GEB_Van || '') + ' ' + (subtitle || '')).toLowerCase();

    var infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    var nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    nameDiv.textContent = (user.GEB_Naam || '') + ' ' + (user.GEB_Van || '');
    infoDiv.appendChild(nameDiv);

    var subDiv = document.createElement('div');
    subDiv.className = 'admin-user-email';
    subDiv.textContent = subtitle || '';
    infoDiv.appendChild(subDiv);

    card.appendChild(infoDiv);

    if (rolNaam) {
      var rolesDiv = document.createElement('div');
      rolesDiv.className = 'admin-user-roles';
      var badge = document.createElement('span');
      badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/[\s_]+/g, '');
      badge.textContent = rolNaam;
      rolesDiv.appendChild(badge);
      card.appendChild(rolesDiv);
    }

    return card;
  }

  /**
   * Renders an array of user objects into a container div as individual cards.
   * Shows a placeholder card if the array is empty.
   */
  function renderUserList(container, users, emptyMessage) {
    if (!container) return;
    container.innerHTML = '';
    if (!users || users.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'user-card';
      var info = document.createElement('div');
      info.className = 'admin-user-info';
      var msg = document.createElement('div');
      msg.className = 'admin-user-email';
      msg.textContent = emptyMessage || 'Geen gebruikers nie';
      info.appendChild(msg);
      empty.appendChild(info);
      container.appendChild(empty);
      return;
    }
    users.forEach(function (u) {
      var subtitle = u.STU_Nommer || u.GEB_Epos || u.Rol_Naam || '';
      container.appendChild(createUserCard(u, subtitle, u.Rol_Naam || 'Student'));
    });
  }

  /**
   * Fetch all gebruikers once and cache the studente.
   * The right-panel list is re-rendered from this cache per gekose koshuis.
   */
  async function loadStudenteCache() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchGebruikers();

    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (dataList) {
        dataList.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Kon nie gebruikers laai nie.</div></div></div>';
      }
      return;
    }

    alleStudente = json.data.filter(function (g) {
      return g.Rol_Naam === 'Student';
    });

    renderKoshuisStudente();
  }

  /**
   * Render the right-panel list: studente whose Koshuis_ID matches the
   * currently selected koshuis. Waits until both the cache and the
   * dropdown selection are available.
   */
  function renderKoshuisStudente() {
    if (!dataList || alleStudente === null || currentKoshuisId === null) return;

    var studente = alleStudente.filter(function (g) {
      return Number(g.Koshuis_ID) === Number(currentKoshuisId);
    });

    renderUserList(dataList, studente, 'Geen studente in hierdie koshuis nie');
    applyListFilter();
  }

  /**
   * Fetch live scan status for a specific koshuis and update dashboard cards.
   * Does NOT touch the right-panel list.
   */
  async function refreshDashboard(koshuisId) {
    if (!koshuisId || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKoshuisStatus(koshuisId);

    var inCount = document.getElementById('dash-student-in-count');
    var outCount = document.getElementById('dash-student-out-count');
    var kapasiteitCard = document.getElementById('dash-kapasiteit-card');

    if (!json || !json.sukses || !json.data) {
      if (inCount) inCount.textContent = 'Studente ingeteken: --';
      if (outCount) outCount.textContent = 'Studente uitgeteken: --';
      if (kapasiteitCard) kapasiteitCard.textContent = 'Inwoners: -- / --';
      return;
    }

    var data = json.data;

    if (inCount) inCount.textContent = 'Studente ingeteken: ' + data.scanned_in_count;
    if (outCount) outCount.textContent = 'Studente uitgeteken: ' + data.scanned_out_count;
    if (kapasiteitCard) {
      kapasiteitCard.textContent = 'Inwoners: ' + data.inwoner_count + ' / ' + data.KOS_Kapasiteit;
    }

    renderUserList(document.getElementById('dash-student-in-list'), data.scanned_in || [], 'Geen studente nie');
    renderUserList(document.getElementById('dash-student-out-list'), data.scanned_out || [], 'Geen studente nie');
  }

  /**
   * Load koshuise from GET /koshuise into the page-level #data-select dropdown.
   * After loading, auto-selects the first koshuis and triggers the first dashboard refresh.
   */
  async function loadKoshuisDropdown() {
    if (!dataSelect || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKoshuise();

    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    dataSelect.innerHTML = '';
    json.data.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = String(k.Koshuis_ID);
      opt.textContent = k.KOS_Naam;
      dataSelect.appendChild(opt);
    });

    if (json.data.length > 0) {
      currentKoshuisId = json.data[0].Koshuis_ID;
      refreshDashboard(currentKoshuisId);
      renderKoshuisStudente();
      startPolling();
    }
  }

  /**
   * Start a 30-second polling interval for the given koshuis ID.
   * Clears any existing interval first so only one is active at a time.
   */
  function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(function () {
      refreshDashboard(currentKoshuisId);
    }, 5000);
  }

  /** Hide list rows that do not contain the search text. */
  function applyListFilter() {
    if (!listSearch || !dataList) return;
    var query = listSearch.value.trim().toLowerCase();
    var rows = dataList.querySelectorAll('.user-card');

    rows.forEach(function (row) {
      var searchable = row.dataset.search || (row.textContent || '').toLowerCase();
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
  }

  // ----- Wire list filter -----
  if (listSearch) {
    listSearch.addEventListener('input', applyListFilter);
  }

  // ----- Wire koshuis dropdown -----
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      currentKoshuisId = Number(dataSelect.value);
      refreshDashboard(currentKoshuisId);
      renderKoshuisStudente();
      startPolling();
    });
  }

  // After full DOM (and MoonApi script) are ready, bootstrap the page
  document.addEventListener('DOMContentLoaded', function () {
    loadKoshuisDropdown();   // populate #data-select + trigger first dashboard refresh
    loadStudenteCache();     // cache studente for the right-panel list
  });
})();
