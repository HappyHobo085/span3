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

  // After full DOM (and MoonApi script) are ready, refresh campus dropdown
  document.addEventListener('DOMContentLoaded', function () {
    loadKampusDropdown();
  });
})();
