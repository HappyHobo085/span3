/**
 * kampus.js — logic for kampus.html only.
 *
 * Depends on:
 *   - main.js (must run first: loads website_api_calls.js → window.MoonApi)
 *   - HTML ids: list-search, data-list, modal fields, overlay, buttons.
 *
 * Features:
 *   - Filter student list as you type.
 *   - Open/close “new class” modal (including click on backdrop).
 *   - Load campuses into dropdown from GET /kampusse.
 *   - POST new class via MoonApi.createKlas.
 */

(function () {
  // ----- Cached DOM nodes (null-safe checks before use) -----
  const listSearch = document.getElementById('list-search');
  const dataList = document.getElementById('data-list');
  const openClassModalButton = document.getElementById('open-class-modal');
  const closeClassModalButton = document.getElementById('close-class-modal');
  const createClassButton = document.getElementById('create-class-button');
  const classModalOverlay = document.getElementById('class-modal-overlay');
  const classRoomName = document.getElementById('class-room-name');
  const classKampus = document.getElementById('class-kampus');
  const classNfcTag = document.getElementById('class-nfc-tag');
  const dataSelect = document.getElementById('data-select');

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

  /** Hide list rows that do not contain the search text. */
  function applyListFilter() {
    if (!listSearch || !dataList) return;
    const query = listSearch.value.trim().toLowerCase();
    const items = dataList.querySelectorAll('li');

    items.forEach(function (li) {
      const text = (li.textContent || '').trim().toLowerCase();
      const matches = query === '' || text.includes(query);
      li.hidden = !matches;
    });
  }

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

  /** Show modal: CSS class .open + accessibility flag. */
  function openClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.add('open');
    classModalOverlay.setAttribute('aria-hidden', 'false');
  }

  /** Hide modal and mark hidden for screen readers. */
  function closeClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.remove('open');
    classModalOverlay.setAttribute('aria-hidden', 'true');
  }

  /**
   * Laai kampusse vanaf API en vul die dropdown (IDs uit databasis).
   * Fetches campuses from the API and fills the dropdown (database IDs).
   */
  async function loadKampusDropdown() {
  if (!classKampus || !window.MoonApi) return;

  const json = await window.MoonApi.fetchKampusse();

  if (json && json.sukses && Array.isArray(json.data)) {
    classKampus.innerHTML = '<option value="">Kies kampus...</option>';

    json.data.forEach(function (k) {
      const opt = document.createElement('option');
      opt.value = String(k.Kampus_ID);
      opt.textContent = k.KAM_Naam;
      classKampus.appendChild(opt);
    });
  }
}

  /**
   * Neem vormdata en roep MoonApi.createKlas aan (POST /klasse via website_api_calls.js).
   * Reads modal fields, validates, POSTs new class, shows alerts for success/errors.
   */
  async function submitNewClass() {
  const roomName = classRoomName ? classRoomName.value.trim() : '';
  const kampusId = classKampus ? Number(classKampus.value) : null;

  if (!roomName || !kampusId) {
    alert('Voltooi asseblief die klaskamer naam en kampus.');
    return;
  }

  const json = await window.MoonApi.createKlas({
    LOK_Naam: roomName,
    LOK_Tipe: "Klaskamer",
    Kampus_ID: kampusId,
    NFC_UID: "TEMP",
    NFC_Tipe: "Lokasie"
  });

  if (json && json.sukses) {
    alert('Klas suksesvol gestoor. UID: ' + json.data.nfc_tag.NFC_UID);
    closeClassModal();
    classRoomName.value = '';
    classKampus.value = '';
  } else {
    alert((json && json.fout) || 'Kon nie klas skep nie.');
  }
}

  // ----- Wire list filter -----
  if (listSearch) {
    listSearch.addEventListener('input', applyListFilter);
  }

  var bottomSearch = document.getElementById('bottom-search');
  if (bottomSearch) {
    bottomSearch.addEventListener('input', applyPersoneelFilter);
  }

  // ----- Wire campus dropdown -----
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      currentKampusId = Number(dataSelect.value);
      refreshDashboard(currentKampusId);
      startPolling(currentKampusId);
    });
  }

  // ----- Modal open / close -----
  if (openClassModalButton) {
    openClassModalButton.addEventListener('click', openClassModal);
  }

  if (closeClassModalButton) {
    closeClassModalButton.addEventListener('click', closeClassModal);
  }

  // Click dark area outside the white dialog → close
  if (classModalOverlay) {
    classModalOverlay.addEventListener('click', function (event) {
      if (event.target === classModalOverlay) {
        closeClassModal();
      }
    });
  }

  // ----- Submit new class from modal -----
  if (createClassButton) {
    createClassButton.addEventListener('click', function () {
      submitNewClass();
    });
  }

  // After full DOM (and MoonApi script) are ready, bootstrap the page
  document.addEventListener('DOMContentLoaded', function () {
    loadKampusDropdown();       // populate modal class-kampus dropdown (existing)
    loadPageKampusDropdown();   // populate #data-select + trigger first dashboard refresh
    loadGebruikersLys();        // populate constant student + personeel right-panel lists
  });
})();
