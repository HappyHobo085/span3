// =====================================================================
// admin.js — Hierdie lêer beheer die Admin-bladsy van die webwerf.
// Dit laai die lyste van gebruikers, kampusse, lokale en koshuise
// vanaf die bediener, en laat die admin toe om nuwes te skep,
// bestaandes te wysig, en oues te verwyder.
// =====================================================================

/**
 * admin.js — logic for admin.html.
 *
 * Depends on:
 *   - main.js (loads website_api_calls.js → window.MoonApi)
 *
 * Features:
 *   - Load lokale from API into the venue list.
 *   - Filter venue list by search and campus dropdown.
 *   - Open/close "Skep Lokaal" modal + POST new class.
 *   - Load gebruikers from API into the user list.
 *   - Filter user list by search and role dropdown.
 *   - Open/close "Skep Gebruiker" modal + POST new user.
 */

// Alles hieronder is in een groot funksie toegedraai sodat die name
// hier binne nie met ander lêers se name bots nie.
(function () {
  // ===== VENUE DOM NODES =====
  // Hier kry ons al die knoppies en velde op die bladsy wat met lokale werk.
  const venueList = document.getElementById('venue-list');
  const venueSearch = document.getElementById('venue-search');
  const venueCampusFilter = document.getElementById('venue-campus-filter');
  const gateList = document.getElementById('gate-list');
  const gateSearch = document.getElementById('gate-search');
  const gateCampusFilter = document.getElementById('gate-campus-filter');
  const openVenueModalBtn = document.getElementById('open-create-venue-modal');
  const classModalOverlay = document.getElementById('class-modal-overlay');
  const closeClassModalBtn = document.getElementById('close-class-modal');
  const createClassBtn = document.getElementById('create-class-button');
  const classRoomName = document.getElementById('class-room-name');
  const classKampus = document.getElementById('class-kampus');
  const classTagUid = document.getElementById('class-tag-uid');
  const classModalTitle = document.getElementById('class-modal-title');
  const deleteLokaalBtn = document.getElementById('delete-lokaal-btn');

  // ===== KAMPUS DOM NODES =====
  // Die knoppies en velde wat met kampusse werk.
  const kampusList = document.getElementById('kampus-list');
  const kampusSearch = document.getElementById('kampus-search');
  const openKampusModalBtn = document.getElementById('open-create-kampus-modal');
  const kampusModalOverlay = document.getElementById('createKampusModal');
  const closeKampusModalBtn = document.getElementById('close-create-kampus-modal');
  const createKampusBtn = document.getElementById('create-kampus-btn');
  const newKampusName = document.getElementById('new-kampus-name');
  const kampusModalTitle = document.getElementById('create-kampus-title');
  const deleteKampusBtn = document.getElementById('delete-kampus-btn');

  // ===== KOSHUIS DOM NODES =====
  // Die knoppies en velde wat met koshuise werk.
  const koshuisList = document.getElementById('koshuis-list');
  const koshuisSearch = document.getElementById('koshuis-search');
  const openKoshuisModalBtn = document.getElementById('open-create-koshuis-modal');
  const koshuisModalOverlay = document.getElementById('createKoshuisModal');
  const closeKoshuisModalBtn = document.getElementById('close-create-koshuis-modal');
  const createKoshuisBtn = document.getElementById('create-koshuis-btn');
  const newKoshuisName = document.getElementById('new-koshuis-name');
  const newKoshuisAddress = document.getElementById('new-koshuis-address');
  const newKoshuisCapacity = document.getElementById('new-koshuis-capacity');
  const newKoshuisKampus = document.getElementById('new-koshuis-kampus');
  const koshuisModalTitle = document.getElementById('create-koshuis-title');
  const deleteKoshuisBtn = document.getElementById('delete-koshuis-btn');

  // ===== USER DOM NODES =====
  // Die knoppies en velde wat met gebruikers werk.
  const userList = document.getElementById('user-list');
  const userSearch = document.getElementById('user-search');
  const userRoleFilter = document.getElementById('user-role-filter');
  const openUserModalBtn = document.getElementById('open-create-user-modal');
  const userModalOverlay = document.getElementById('createUserModal');
  const closeUserModalBtn = document.getElementById('close-create-user-modal');
  const createUserBtn = document.getElementById('create-user-btn');
  const deleteUserBtn = document.getElementById('delete-user-btn');
  const newUserName = document.getElementById('new-user-name');
  const newUserSurname = document.getElementById('new-user-surname');
  const newUserEmail = document.getElementById('new-user-email');

  const uploadCsvBtn = document.getElementById('upload-csv-btn');
  const csvFileInput = document.getElementById('csv-file-input');
  const csvModal = document.getElementById('csvModal');
  const csvModeSelect = document.getElementById('csv-mode-select');
  const csvTableSelect = document.getElementById('csv-table-select');
  const csvActionSelect = document.getElementById('csv-action-select');
  const csvSourceSelect = document.getElementById('csv-source-select');
  const csvSourceGroup = document.getElementById('csv-source-group');
  const csvFilePicker = document.getElementById('csv-file-picker');
  const csvTextArea = document.getElementById('csv-text-area');
  const csvFileGroup = document.getElementById('csv-file-group');
  const csvTextGroup = document.getElementById('csv-text-group');
  const closeCsvModalBtn = document.getElementById('close-csv-modal');
  const confirmCsvActionBtn = document.getElementById('confirm-csv-action');
  const newUserStudentNr = document.getElementById('new-user-student-nr');
  const studentNumberField = document.getElementById('student-number-field');
  const newUserIsKoshuis = document.getElementById('new-user-is-koshuis');
  const studentIsKoshuisField = document.getElementById('student-is-koshuis-field');
  const newUserKoshuis = document.getElementById('new-user-koshuis');
  const studentKoshuisField = document.getElementById('student-koshuis-field');
  const newUserKampus = document.getElementById('new-user-kampus');
  const opsigterKampusField = document.getElementById('opsigter-kampus-field');
  const newUserPassword = document.getElementById('new-user-password');
  const newUserRoles = document.getElementById('new-user-roles');
  const userModalTitle = document.getElementById('create-user-title');
  const newUserActive = document.getElementById('newUserActive');
  const userActiveRow = document.getElementById('user-active-row');

  // Hierdie veranderlikes onthou of ons besig is om iets te wysig:
  // null beteken "skep nuut", 'n nommer beteken "wysig daardie een".
  // Edit mode tracking: null = create, an ID = editing that record.
  let editingUserId = null;
  let editingKampusId = null;
  let editingLokaalId = null;
  let editingLokaalOldUid = '';
  let editingKoshuisId = null;

  // ===== LOOKUP MAPS =====
  // Hier onthou ons die name van kampusse en rolle sodat ons hulle
  // vinnig kan opsoek sonder om weer die bediener te vra.
  let kampusMap = {};
  let rolleMap = {}; // Rol_ID → display name

  // Mooi, kort name vir die rolle soos ons dit op die skerm wys.
  // Friendly display names for backend role names
  const rolDisplayNames = {
    'Administrateur': 'Admin',
    'Student': 'Student',
    'Personeel': 'Personeel',
    'Kampus_Opsigter': 'Opsigter',
    'Sekuriteit_Wag': 'Sekuriteits Wag'
  };

  // =====================================================================
  //  SHARED HELPERS
  // =====================================================================

  /** Read the logged-in user's ID from the JWT payload (null if unknown). */
  // Hierdie funksie lees die ingetekende gebruiker se ID uit die
  // gestoorde aanteken-bewys. Gee niks (null) terug as dit nie kan nie.
  function getLoggedInUserId() {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub ? Number(payload.sub) : null;
    } catch (decodeErr) {
      return null;
    }
  }

  /** Cap a panel list at maxRows visible rows (default 5); more than that scrolls inside the list. */
  // Hierdie funksie keer dat 'n lys te lank word: na 'n paar rye
  // moet die res van die lys binne die blokkie rol (scroll).
  function capListHeight(list, rowSelector, maxRows) {
    if (!list) return;

    maxRows = maxRows || 5;

    const visible = Array.prototype.filter.call(
      list.querySelectorAll(rowSelector),
      function (row) { return row.style.display !== 'none'; }
    );

    if (visible.length > maxRows) {
      const first = visible[0].getBoundingClientRect();
      const last = visible[maxRows - 1].getBoundingClientRect();
      list.style.maxHeight = (last.bottom - first.top) + 'px';
    } else {
      list.style.maxHeight = '';
    }
  }

  async function loadCsvTableOptions() {
    if (!csvTableSelect || !window.MoonApi) return;

    const json = await window.MoonApi.fetchCsvTables();
    const tables = json && json.data && Array.isArray(json.data.tables) ? json.data.tables : [];

    if (!tables.length) {
      csvTableSelect.innerHTML = '<option value="">Geen tabelle beskikbaar</option>';
      return;
    }

    csvTableSelect.innerHTML = '<option value="">Kies tabel...</option>';
    tables.forEach(function (tableName) {
      const option = document.createElement('option');
      option.value = tableName;
      option.textContent = tableName;
      csvTableSelect.appendChild(option);
    });
  }

  function showCsvStatus(message, type) {
    const statusEl = document.getElementById('csv-status-message');
    if (!statusEl) {
      alert(message);
      return;
    }

    statusEl.textContent = message;
    statusEl.classList.remove('success', 'error');
    statusEl.classList.add(type === 'error' ? 'error' : 'success');
    statusEl.hidden = false;
  }

  function clearCsvStatus() {
    const statusEl = document.getElementById('csv-status-message');
    if (!statusEl) return;
    statusEl.textContent = '';
    statusEl.classList.remove('success', 'error');
    statusEl.hidden = true;
  }

  async function reloadAdminPageDataAfterImport(tableName) {
    const table = (tableName || '').toLowerCase();

    const refreshTasks = [
      loadKampusDropdown(),
      loadLokale(),
      loadKoshuise(),
      loadRolleDropdown(),
      loadGebruikers()
    ];

    try {
      await Promise.all(refreshTasks);

      if (table.includes('kampus')) {
        await loadKampusDropdown();
      }
      if (table.includes('loka') || table.includes('klas')) {
        await loadLokale();
      }
      if (table.includes('kosh')) {
        await loadKoshuise();
      }
      if (table.includes('gebruiker') || table.includes('role') || table.includes('rol')) {
        await loadGebruikers();
        await loadRolleDropdown();
      }
    } catch (error) {
      console.warn('CSV import refresh failed:', error);
    }
  }

  function openCsvModal() {
    if (!csvModal) return;
    csvModal.classList.add('open');
    csvModal.setAttribute('aria-hidden', 'false');
    if (csvTableSelect && !csvTableSelect.value) {
      csvTableSelect.value = '';
    }
    if (csvActionSelect) {
      csvActionSelect.value = 'import';
    }
    if (csvModeSelect) {
      csvModeSelect.value = 'merge';
    }
    if (csvSourceSelect) {
      csvSourceSelect.value = 'file';
    }
    if (csvTextArea) csvTextArea.value = '';
    if (csvFilePicker) csvFilePicker.value = '';
    clearCsvStatus();
    updateCsvPanelVisibility();
  }

  function closeCsvModal() {
    if (!csvModal) return;
    csvModal.classList.remove('open');
    csvModal.setAttribute('aria-hidden', 'true');
    if (csvTextArea) csvTextArea.value = '';
    if (csvFilePicker) csvFilePicker.value = '';
    if (csvTableSelect) csvTableSelect.value = '';
    if (csvSourceSelect) csvSourceSelect.value = 'file';
    if (csvModeSelect) csvModeSelect.value = 'merge';
    clearCsvStatus();
    updateCsvPanelVisibility();
  }

  function updateCsvPanelVisibility() {
    if (!csvActionSelect || !csvSourceSelect) return;
    const action = csvActionSelect.value;
    const isImport = action === 'import';
    const isImportAll = action === 'import-all';
    const isExportAll = action === 'export-all';
    const isAllAction = isImportAll || isExportAll;

    // Hide/show CSV Bron (source) group - only for regular import
    if (csvSourceGroup) {
      csvSourceGroup.style.display = isImport ? '' : 'none';
    }

    // Hide/show Import Modus (merge/replace) - for regular import and import-all
    if (csvModeSelect) {
      const modeGroup = csvModeSelect.closest('.field');
      if (modeGroup) {
        modeGroup.style.display = (isImport || isImportAll) ? '' : 'none';
      }
    }

    // Hide/show Tabel selection - only for regular import/export
    if (csvTableSelect) {
      const tableGroup = csvTableSelect.closest('.field');
      if (tableGroup) {
        tableGroup.style.display = isImport ? '' : 'none';
      }
    }

    // For non-import actions, hide file/text groups
    if (!isImport && !isImportAll) {
      if (csvFileGroup) csvFileGroup.style.display = 'none';
      if (csvTextGroup) csvTextGroup.style.display = 'none';
      return;
    }

    // For import-all: lock to file upload only, hide text area
    if (isImportAll) {
      if (csvFileGroup) csvFileGroup.style.display = '';
      if (csvTextGroup) csvTextGroup.style.display = 'none';
      // Force source to file
      if (csvSourceSelect) csvSourceSelect.value = 'file';
    } else if (isImport) {
      // Regular import: show file/text based on source selection
      const source = csvSourceSelect.value;
      if (csvFileGroup) csvFileGroup.style.display = source === 'file' ? '' : 'none';
      if (csvTextGroup) csvTextGroup.style.display = source === 'text' ? '' : 'none';
    }

    // Update file picker accept attribute and label
    if (csvFilePicker) {
      if (isImportAll) {
        csvFilePicker.accept = '.zip';
        if (csvFileGroup) {
          const label = csvFileGroup.querySelector('label');
          if (label) label.textContent = 'ZIP-lêer';
        }
      } else {
        csvFilePicker.accept = '.csv,text/csv';
        if (csvFileGroup) {
          const label = csvFileGroup.querySelector('label');
          if (label) label.textContent = 'CSV-lêer';
        }
      }
    }
  }

  async function handleCsvAction() {
    if (!window.MoonApi) return;

    const table = csvTableSelect ? csvTableSelect.value : '';
    const action = csvActionSelect ? csvActionSelect.value : 'import';
    const source = csvSourceSelect ? csvSourceSelect.value : 'file';
    const mode = csvModeSelect ? csvModeSelect.value : 'merge';

    // Handle export-all
    if (action === 'export-all') {
      const result = await window.MoonApi.exportAllCsvTables();
      if (!result || !result.ok) {
        showCsvStatus('Kon nie alle tabelle uitstuur nie.', 'error');
        return;
      }

      const link = document.createElement('a');
      const url = URL.createObjectURL(result.blob);
      link.href = url;
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      link.download = 'moon_export_' + timestamp + '.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showCsvStatus('Alle tabelle is suksesvol as ZIP afgelaai.', 'success');
      return;
    }

    // Handle import-all
    if (action === 'import-all') {
      const file = csvFilePicker && csvFilePicker.files && csvFilePicker.files[0] ? csvFilePicker.files[0] : null;

      if (!file) {
        showCsvStatus('Kies asseblief ' + 'n ZIP-lêer om op te laai.', 'error');
        return;
      }

      if (!file.name.endsWith('.zip')) {
        showCsvStatus('Die lêer moet ' + 'n ZIP-lêer wees.', 'error');
        return;
      }

      showCsvStatus('Besig om alle tabelle in te voer...', 'success');

      const result = await window.MoonApi.importAllCsvTables(file, mode);
      if (!result || !result.ok) {
        const errMsg = (result && result.body && (result.body.fout || result.body.detail)) || 'CSV-oplaai het misluk.';
        showCsvStatus('Invoer misluk: ' + errMsg, 'error');
        return;
      }

      if (csvFilePicker) csvFilePicker.value = '';

      const data = result.body && result.body.data ? result.body.data : {};
      const imported = data.imported || {};
      const errors = data.errors || {};
      const skipped = data.skipped || [];
      const details = data.details || {};

      showCsvStatus(bouInvoerOpsomming(imported, errors, skipped, details), Object.keys(errors).length > 0 ? 'error' : 'success');

      // Refresh all admin page data
      await Promise.all([
        loadKampusDropdown(),
        loadLokale(),
        loadKoshuise(),
        loadRolleDropdown(),
        loadGebruikers()
      ]);
      return;
    }

    // Original single-table logic
    if (!table) {
      showCsvStatus('Kies asseblief die tabel wat jy wil gebruik.', 'error');
      return;
    }

    if (action === 'export') {
      const result = await window.MoonApi.exportCsvTable(table);
      if (!result || !result.ok) {
        showCsvStatus('Kon CSV nie uitstuur nie.', 'error');
        return;
      }

      const blob = new Blob([result.text], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = table + '.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showCsvStatus('CSV-uitsending is suksesvol afgelaai.', 'success');
      return;
    }

    const file = csvFilePicker && csvFilePicker.files && csvFilePicker.files[0] ? csvFilePicker.files[0] : null;
    const text = csvTextArea ? csvTextArea.value.trim() : '';

    if (source === 'file' && !file) {
      showCsvStatus('Kies asseblief ' + 'n CSV-lêer om op te laai.', 'error');
      return;
    }

    if (source === 'text' && !text) {
      showCsvStatus('Plak asseblief CSV-teks in die teksveld.', 'error');
      return;
    }

    const result = await window.MoonApi.importCsvTable(
      table,
      source === 'file' ? file : null,
      source === 'text' ? text : null,
      mode
    );
    if (!result || !result.ok) {
      showCsvStatus((result && result.body && (result.body.fout || result.body.detail)) || 'CSV-oplaai het misluk.', 'error');
      return;
    }

    if (csvFilePicker) csvFilePicker.value = '';
    if (csvTextArea) csvTextArea.value = '';

    const enkel = result.body && result.body.data ? result.body.data : {};
    const enkelDetails = {};
    if (enkel.details) enkelDetails[table] = enkel.details;
    showCsvStatus(
      'CSV opgelaai na ' + table + ' in ' + mode + '-modus. ' +
      bouInvoerOpsomming({ [table]: enkel.imported_rows || 0 }, {}, [], enkelDetails),
      'success'
    );
    await reloadAdminPageDataAfterImport(table);
  }

  // Hierdie funksie bou die opsomming van 'n CSV/ZIP-invoer: per tabel hoeveel
  // rye nuut is, reeds bestaan het of misluk het, plus die eerste ry-foute,
  // sodat 'n invoer wat "0" wys verduidelik word.
  function bouInvoerOpsomming(imported, errors, skipped, details) {
    let totNuut = 0, totBestaan = 0, totMisluk = 0;
    const dele = [];
    const ryFoute = [];

    Object.keys(imported).forEach(function (t) {
      const d = details[t] || {};
      const nuut = d.nuut !== undefined ? d.nuut : (imported[t] || 0);
      const bestaan = d.bestaan_reeds || 0;
      const misluk = (d.misluk || 0) + (d.ontbrekende_velde || 0);
      totNuut += nuut; totBestaan += bestaan; totMisluk += misluk;
      let deel = t + ': ' + nuut + ' nuut';
      if (bestaan) deel += ', ' + bestaan + ' bestaan reeds';
      if (misluk) deel += ', ' + misluk + ' misluk';
      dele.push(deel);
      (d.foute || []).slice(0, 2).forEach(function (f) { ryFoute.push(t + ' — ' + f); });
    });

    let msg = 'Invoer voltooi: ' + totNuut + ' nuwe rye';
    if (totBestaan) msg += ', ' + totBestaan + ' het reeds bestaan';
    if (totMisluk) msg += ', ' + totMisluk + ' misluk';
    msg += '. ';
    if (dele.length) msg += dele.join('; ') + '. ';
    if (Object.keys(errors).length > 0) {
      msg += 'Tabelfoute: ' + Object.entries(errors).map(function (e) { return e[0] + ': ' + e[1]; }).join('; ') + '. ';
    }
    if (ryFoute.length) msg += 'Ry-foute: ' + ryFoute.slice(0, 4).join(' | ') + '. ';
    if (skipped.length > 0) msg += 'Oorgeslaan: ' + skipped.join(', ') + '. ';
    return msg;
  }

  // =====================================================================
  //  VENUE (LOKALE) SECTION
  // =====================================================================

  // Hierdie funksie maak die venster oop waar 'n lokaal geskep of gewysig word.
  function openClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.add('open');
    classModalOverlay.setAttribute('aria-hidden', 'false');
  }

  // Hierdie funksie maak die lokaal-venster toe en maak die velde weer skoon.
  function closeClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.remove('open');
    classModalOverlay.setAttribute('aria-hidden', 'true');
    if (classRoomName) classRoomName.value = '';
    if (classKampus) classKampus.value = '';
    if (classTagUid) classTagUid.value = '';
    editingLokaalOldUid = '';
    // Return the shared modal to create mode after closing.
    editingLokaalId = null;
    if (classModalTitle) classModalTitle.textContent = 'Skep nuwe klas';
    if (createClassBtn) createClassBtn.textContent = 'Skep';
    if (deleteLokaalBtn) deleteLokaalBtn.style.display = 'none';
  }

  /** Open the class modal in edit mode, pre-filled from the clicked venue row. */
  // Hierdie funksie maak die lokaal-venster oop om 'n bestaande lokaal
  // te wysig, met die ry se inligting reeds ingevul.
  function openEditLokaalModal(row) {
    editingLokaalId = Number(row.dataset.lokasieId);
    const nameSpan = row.querySelector('.admin-venue-name');
    if (classRoomName) classRoomName.value = nameSpan ? nameSpan.textContent : '';
    if (classKampus) classKampus.value = row.dataset.kampusId || '';
    if (classTagUid) classTagUid.value = row.dataset.nfcUid || '';
    editingLokaalOldUid = row.dataset.nfcUid || '';
    if (classModalTitle) classModalTitle.textContent = 'Wysig Lokaal';
    if (createClassBtn) createClassBtn.textContent = 'Stoor Veranderinge';
    if (deleteLokaalBtn) deleteLokaalBtn.style.display = '';
    openClassModal();
  }

  /** Delete the currently-edited lokaal (DELETE /lokasies/{id}). */
  // Hierdie funksie verwyder die lokaal wat tans gewysig word,
  // nadat die admin eers "ja" gesê het.
  async function submitDeleteLokaal() {
    if (editingLokaalId === null || !window.MoonApi) return;

    const lokasieId = editingLokaalId;
    const naam = (classRoomName ? classRoomName.value.trim() : '') || 'hierdie lokaal';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

    // Vra die bediener om die lokaal uit te vee.
    const json = await window.MoonApi.deleteLokasie(lokasieId);

    if (json && json.sukses) {
      // Dit het gewerk: wys 'n boodskap en haal die ry uit die lys.
      alert('Lokaal suksesvol verwyder.');
      closeClassModal();
      const row = venueList
        ? venueList.querySelector('.admin-venue-row[data-lokasie-id="' + lokasieId + '"]')
        : null;
      if (row) row.remove();
      capListHeight(venueList, '.admin-venue-row', 6);
    } else {
      // Iets het skeefgeloop: wys die foutboodskap.
      alert((json && json.fout) || (json && json.detail) || 'Kon nie lokaal verwyder nie.');
    }
  }

  // Hierdie funksie laai die lys van kampusse vanaf die bediener
  // en vul al die kampus-keuselyste op die bladsy in.
  async function loadKampusDropdown() {
    if (!window.MoonApi) return;

    // Vra die bediener vir al die kampusse.
    const json = await window.MoonApi.fetchKampusse();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    // Vul die kampus-keuselys in die lokaal-venster.
    if (classKampus) {
      classKampus.innerHTML = '<option value="">Kies kampus...</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        classKampus.appendChild(opt);
      });
    }

    // Vul die kampus-filter bo die lys van lokale.
    if (venueCampusFilter) {
      venueCampusFilter.innerHTML = '<option value="">Alle Kampusse</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        venueCampusFilter.appendChild(opt);
      });
    }
    if (gateCampusFilter) {
      gateCampusFilter.innerHTML = '<option value="">Alle Kampusse</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        gateCampusFilter.appendChild(opt);
      });
    }

    // Vul die kampus-keuselys in die koshuis-venster.
    if (newKoshuisKampus) {
      newKoshuisKampus.innerHTML = '<option value="">Kies kampus...</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        newKoshuisKampus.appendChild(opt);
      });
    }

    // Vul die kampus-keuselys in die gebruiker-venster (slegs vir Opsigters).
    if (newUserKampus) {
      const huidige = newUserKampus.value;
      newUserKampus.innerHTML = '<option value="">Kies kampus...</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        newUserKampus.appendChild(opt);
      });
      newUserKampus.value = huidige;
    }

    // Onthou elke kampus se naam sodat ander lyste dit kan wys.
    json.data.forEach(function (k) {
      kampusMap[String(k.Kampus_ID)] = k.KAM_Naam;
    });

    renderKampusList(json.data);
  }

  // =====================================================================
  //  KAMPUS SECTION
  // =====================================================================

  /** Render all kampusse as simple name rows in the Kampusse panel. */
  // Hierdie funksie bou die lys van kampusse op die bladsy, een ry per kampus.
  function renderKampusList(kampusse) {
    if (!kampusList) return;

    kampusList.innerHTML = '';

    // As daar geen kampusse is nie, wys 'n boodskap in die lys.
    if (!kampusse || kampusse.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'admin-venue-row';
      const msg = document.createElement('span');
      msg.className = 'admin-user-email';
      msg.textContent = 'Geen kampusse nie';
      empty.appendChild(msg);
      kampusList.appendChild(empty);
      return;
    }

    // Maak vir elke kampus 'n ry met 'n naam en 'n "Wysig"-knoppie.
    kampusse.forEach(function (k) {
      const row = document.createElement('div');
      row.className = 'admin-venue-row';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'admin-venue-name';
      nameSpan.textContent = k.KAM_Naam;

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'btn-outline btn-sm';
      editBtn.textContent = 'Wysig';
      editBtn.addEventListener('click', function () { openEditKampusModal(k); });

      row.dataset.search = k.KAM_Naam.toLowerCase();
      row.appendChild(nameSpan);
      row.appendChild(editBtn);
      kampusList.appendChild(row);
    });

    applyKampusFilter();
  }

  /** Filter kampus list by search text. */
  // Hierdie funksie wys net die kampusse wat by die soekwoord pas
  // en steek die res weg.
  function applyKampusFilter() {
    if (!kampusList) return;

    const query = kampusSearch ? kampusSearch.value.trim().toLowerCase() : '';

    const rows = kampusList.querySelectorAll('.admin-venue-row');
    rows.forEach(function (row) {
      // Rye sonder soekdata (bv. die "Geen kampusse nie" boodskap) bly altyd sigbaar.
      if (row.dataset.search === undefined) return;
      row.style.display = (query === '' || row.dataset.search.includes(query)) ? '' : 'none';
    });

    capListHeight(kampusList, '.admin-venue-row');
  }

  // Hierdie funksie maak die venster oop waar 'n kampus geskep of gewysig word.
  function openKampusModal() {
    if (!kampusModalOverlay) return;
    kampusModalOverlay.classList.add('open');
    kampusModalOverlay.setAttribute('aria-hidden', 'false');
  }

  // Hierdie funksie maak die kampus-venster toe en maak die veld weer skoon.
  function closeKampusModal() {
    if (!kampusModalOverlay) return;
    kampusModalOverlay.classList.remove('open');
    kampusModalOverlay.setAttribute('aria-hidden', 'true');
    if (newKampusName) newKampusName.value = '';
    // Return the shared modal to create mode after closing.
    editingKampusId = null;
    if (kampusModalTitle) kampusModalTitle.textContent = 'Skep Kampus';
    if (createKampusBtn) createKampusBtn.textContent = 'Skep';
    if (deleteKampusBtn) deleteKampusBtn.style.display = 'none';
  }

  /** Open the kampus modal in edit mode, pre-filled with the kampus data. */
  // Hierdie funksie maak die kampus-venster oop om 'n bestaande kampus
  // te wysig, met die naam reeds ingevul.
  function openEditKampusModal(kampus) {
    editingKampusId = kampus.Kampus_ID;
    if (newKampusName) newKampusName.value = kampus.KAM_Naam || '';
    if (kampusModalTitle) kampusModalTitle.textContent = 'Wysig Kampus';
    if (createKampusBtn) createKampusBtn.textContent = 'Stoor Veranderinge';
    if (deleteKampusBtn) deleteKampusBtn.style.display = '';
    openKampusModal();
  }

  /** Delete the currently-edited kampus (DELETE /kampusse/{id}). */
  // Hierdie funksie verwyder die kampus wat tans gewysig word,
  // nadat die admin eers "ja" gesê het.
  async function submitDeleteKampus() {
    if (editingKampusId === null || !window.MoonApi) return;

    const naam = (newKampusName ? newKampusName.value.trim() : '') || 'hierdie kampus';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

    // Vra die bediener om die kampus uit te vee.
    const json = await window.MoonApi.deleteKampus(editingKampusId);

    if (json && json.sukses) {
      alert('Kampus suksesvol verwyder.');
      closeKampusModal();
      // Herlaai sodat die lys én die kampus-dropdowns opdateer.
      await loadKampusDropdown();
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie kampus verwyder nie.');
    }
  }

  /** Submit the kampus modal: POST /kampusse or PUT /kampusse/{id} in edit mode. */
  // Hierdie funksie stoor die kampus-venster se inligting:
  // dit skep 'n nuwe kampus, of werk 'n bestaande een by.
  async function submitNewKampus() {
    const naam = newKampusName ? newKampusName.value.trim() : '';

    // Maak seker daar is 'n naam ingevul.
    if (!naam) {
      alert('Voer asseblief die kampusnaam in.');
      return;
    }

    // Stuur die naam na die bediener: werk by as ons wysig, skep anders 'n nuwe een.
    const json = editingKampusId !== null
      ? await window.MoonApi.updateKampus(editingKampusId, { KAM_Naam: naam })
      : await window.MoonApi.createKampus({ KAM_Naam: naam });

    if (json && json.sukses) {
      alert(editingKampusId !== null ? 'Kampus suksesvol opgedateer.' : 'Kampus suksesvol geskep.');
      closeKampusModal();
      // Herlaai sodat die lys én die kampus-dropdowns die nuwe kampus wys.
      await loadKampusDropdown();
      // Kampusnaam-wysigings moet ook in die lokaal- en koshuis-lyste se badges wys.
      await loadLokale();
      applyVenueFilter();
      await loadKoshuise();
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie kampus stoor nie.');
    }
  }

  // Hierdie funksie laai die lys van lokale vanaf die bediener
  // en sit elkeen as 'n ry in die Lokale-paneel.
  async function loadLokale() {
    if (!venueList || !window.MoonApi) return;

    // Vra die bediener vir al die lokale.
    const json = await window.MoonApi.fetchLokasies();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    // Maak die lys leeg en bou dit dan ry vir ry op.
    venueList.innerHTML = '';
    if (gateList) gateList.innerHTML = '';
    json.data.forEach(function (lok) {
      addVenueRow(lok.Lokasie_ID, lok.LOK_Naam, lok.Kampus_ID, lok.LOK_Tipe, lok.NFC_UID);
    });
  }

  // Hierdie funksie voeg een lokaal-ry by die lys: naam,
  // kampus-etiket en 'n "Wysig"-knoppie.
  function addVenueRow(lokasieId, name, kampusId, lokasieType, nfcUid) {
    const targetList = lokasieType === 'Kampus' ? gateList : venueList;
    if (!targetList) return;

    const row = document.createElement('div');
    row.className = 'admin-venue-row';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-venue-name';
    nameSpan.textContent = name;

    const badge = document.createElement('span');
    badge.className = 'campus-badge';
    badge.textContent = kampusMap[String(kampusId)] || 'Onbekend';

    const tagBadge = document.createElement('span');
    tagBadge.className = 'campus-badge tag-badge';
    tagBadge.textContent = 'Tag: ' + (nfcUid || '—');

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn-outline btn-sm';
    editBtn.textContent = 'Wysig';
    editBtn.addEventListener('click', function () { openEditLokaalModal(row); });

    row.dataset.lokasieId = String(lokasieId);
    row.dataset.kampusId = String(kampusId);
    row.dataset.nfcUid = nfcUid || '';
    row.dataset.name = name.toLowerCase();
    row.appendChild(nameSpan);
    row.appendChild(badge);
    row.appendChild(tagBadge);
    row.appendChild(editBtn);
    targetList.appendChild(row);
  }

  /** Update an existing venue row in place with fresh data. */
  // Hierdie funksie werk 'n bestaande lokaal-ry se naam en kampus by
  // sonder om die hele lys oor te bou.
  function updateVenueRow(lokasieId, name, kampusId, nfcUid) {
    if (!venueList) return;

    const row = document.querySelector('.admin-venue-row[data-lokasie-id="' + lokasieId + '"]');
    if (!row) return;

    const nameSpan = row.querySelector('.admin-venue-name');
    const badge = row.querySelector('.campus-badge');

    if (nameSpan) nameSpan.textContent = name;
    if (badge) badge.textContent = kampusMap[String(kampusId)] || 'Onbekend';

    row.dataset.kampusId = String(kampusId);
    row.dataset.name = name.toLowerCase();
    const tagBadge = row.querySelector('.tag-badge');
    if (tagBadge) tagBadge.textContent = 'Tag: ' + (nfcUid || '—');
    row.dataset.nfcUid = nfcUid || '';
  }

 // Hierdie funksie wys net die lokale wat by die soekwoord en die
 // gekose kampus pas, en steek die res weg.
 function applyVenueFilter() {
  console.log('applyVenueFilter running');
  function filterList(list, search, campusFilter) {
    if (!list) return;
    const query = search ? search.value.trim().toLowerCase() : '';
    const campus = campusFilter ? campusFilter.value : '';
    list.querySelectorAll('.admin-venue-row').forEach(function (row) {
      const matchesSearch = query === '' || (row.dataset.name || '').includes(query);
      const matchesCampus = campus === '' || (row.dataset.kampusId || '') === campus;
      row.style.display = (matchesSearch && matchesCampus) ? '' : 'none';
    });
    capListHeight(list, '.admin-venue-row', 6);
  }

  filterList(venueList, venueSearch, venueCampusFilter);
  filterList(gateList, gateSearch, gateCampusFilter);
}

  // Hierdie funksie stoor die lokaal-venster se inligting:
  // dit skep 'n nuwe lokaal, of werk 'n bestaande een by.
  async function submitNewClass() {
    const roomName = classRoomName ? classRoomName.value.trim() : '';
    const kampusId = classKampus ? Number(classKampus.value) : null;

    // Maak seker albei velde is ingevul.
    if (!roomName || !kampusId) {
      alert('Voltooi asseblief die klaskamer naam en kampus.');
      return;
    }

    // ===== EDIT MODE =====
    // Ons wysig 'n bestaande lokaal: stuur die nuwe waardes na die bediener.
    if (editingLokaalId !== null) {
      const lokasieId = editingLokaalId;
      const json = await window.MoonApi.updateLokasie(lokasieId, {
        LOK_Naam: roomName,
        Kampus_ID: kampusId
      });

      if (!json || !json.sukses) {
        alert((json && json.fout) || (json && json.detail) || 'Kon nie lokaal opdateer nie.');
        return;
      }

      // Koppel/hernoem die NFC-tag as die UID verander het. Die venster bly
      // oop by 'n fout (bv. UID reeds in gebruik) sodat die admin kan regmaak.
      const nuweUid = classTagUid ? classTagUid.value.trim() : '';
      let finaleUid = editingLokaalOldUid;
      if (nuweUid && nuweUid !== editingLokaalOldUid) {
        const tagJson = await window.MoonApi.updateLokasieTag(lokasieId, nuweUid);
        if (!tagJson || !tagJson.sukses) {
          alert(foutBoodskap(tagJson, 'Kon nie die NFC-tag opdateer nie.'));
          return;
        }
        finaleUid = nuweUid;
      }

      alert('Lokaal suksesvol opgedateer.');
      closeClassModal();
      updateVenueRow(lokasieId, roomName, kampusId, finaleUid);
      applyVenueFilter();
      return;
    }

    // ===== CREATE MODE =====
    // Ons skep 'n splinternuwe lokaal op die bediener.
    const json = await window.MoonApi.createKlas({
      LOK_Naam: roomName,
      LOK_Tipe: 'Klaskamer',
      Kampus_ID: kampusId,
      NFC_UID: (classTagUid && classTagUid.value.trim()) || 'TEMP',
      NFC_Tipe: 'Lokasie'
    });

    if (json && json.sukses) {
      alert('Lokaal suksesvol geskep.');
      closeClassModal();
      const nuweId = json.data && json.data.lokasie ? json.data.lokasie.Lokasie_ID : '';
      const nuweUid = json.data && json.data.nfc_tag ? json.data.nfc_tag.NFC_UID : '';
      addVenueRow(nuweId, roomName, kampusId, 'Klaskamer', nuweUid);
      capListHeight(venueList, '.admin-venue-row', 6);
    } else {
      alert(foutBoodskap(json, 'Kon nie lokaal skep nie.'));
    }
  }

  // =====================================================================
  //  KOSHUIS SECTION
  // =====================================================================

  /** Render all koshuise as rows (naam + kapasiteit) in the Koshuise panel. */
  // Hierdie funksie bou die lys van koshuise op die bladsy,
  // een ry per koshuis met naam, kampus en kapasiteit.
  function renderKoshuisList(koshuise) {
    if (!koshuisList) return;

    koshuisList.innerHTML = '';

    // As daar geen koshuise is nie, wys 'n boodskap in die lys.
    if (!koshuise || koshuise.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'admin-venue-row';
      const msg = document.createElement('span');
      msg.className = 'admin-user-email';
      msg.textContent = 'Geen koshuise nie';
      empty.appendChild(msg);
      koshuisList.appendChild(empty);
      return;
    }

    // Maak vir elke koshuis 'n ry met etikette en 'n "Wysig"-knoppie.
    koshuise.forEach(function (kos) {
      const row = document.createElement('div');
      row.className = 'admin-venue-row';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'admin-venue-name';
      nameSpan.textContent = kos.KOS_Naam;

      const kampusBadge = document.createElement('span');
      kampusBadge.className = 'campus-badge';
      kampusBadge.textContent = kampusMap[String(kos.Kampus_ID)] || 'Geen kampus';

      const badge = document.createElement('span');
      badge.className = 'campus-badge';
      badge.textContent = 'Kapasiteit: ' + kos.KOS_Kapasiteit;

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'btn-outline btn-sm';
      editBtn.textContent = 'Wysig';
      editBtn.addEventListener('click', function () { openEditKoshuisModal(kos); });

      row.dataset.search = (
        kos.KOS_Naam + ' ' +
        (kos.KOS_Adres || '') + ' ' +
        (kampusMap[String(kos.Kampus_ID)] || '')
      ).toLowerCase();
      row.appendChild(nameSpan);
      row.appendChild(kampusBadge);
      row.appendChild(badge);
      row.appendChild(editBtn);
      koshuisList.appendChild(row);
    });

    applyKoshuisFilter();
  }

  /** Filter koshuis list by search text (naam, adres of kampus). */
  // Hierdie funksie wys net die koshuise wat by die soekwoord pas
  // (naam, adres of kampus) en steek die res weg.
  function applyKoshuisFilter() {
    if (!koshuisList) return;

    const query = koshuisSearch ? koshuisSearch.value.trim().toLowerCase() : '';

    const rows = koshuisList.querySelectorAll('.admin-venue-row');
    rows.forEach(function (row) {
      // Rye sonder soekdata (bv. die "Geen koshuise nie" boodskap) bly altyd sigbaar.
      if (row.dataset.search === undefined) return;
      row.style.display = (query === '' || row.dataset.search.includes(query)) ? '' : 'none';
    });

    capListHeight(koshuisList, '.admin-venue-row');
  }

  // Hierdie funksie laai die lys van koshuise vanaf die bediener
  // en wys hulle in die Koshuise-paneel.
  async function loadKoshuise() {
    if (!koshuisList || !window.MoonApi) return;

    // Vra die bediener vir al die koshuise.
    const json = await window.MoonApi.fetchKoshuise();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    renderKoshuisList(json.data);
    populateUserKoshuisDropdown(json.data);
  }

  /** Fill the user modal se koshuis dropdown (student toekenning). */
  // Hierdie funksie vul die koshuis-keuselys in die gebruiker-venster
  // (waar 'n student aan 'n koshuis gekoppel word).
  function populateUserKoshuisDropdown(koshuise) {
    if (!newUserKoshuis) return;

    const huidigeWaarde = newUserKoshuis.value;
    newUserKoshuis.innerHTML = '<option value="">Kies koshuis...</option>';

    koshuise.forEach(function (kos) {
      const opt = document.createElement('option');
      opt.value = String(kos.Koshuis_ID);
      opt.textContent = kos.KOS_Naam;
      newUserKoshuis.appendChild(opt);
    });

    newUserKoshuis.value = huidigeWaarde;
  }

  // Hierdie funksie maak die venster oop waar 'n koshuis geskep of gewysig word.
  function openKoshuisModal() {
    if (!koshuisModalOverlay) return;
    koshuisModalOverlay.classList.add('open');
    koshuisModalOverlay.setAttribute('aria-hidden', 'false');
  }

  // Hierdie funksie maak die koshuis-venster toe en maak al die velde weer skoon.
  function closeKoshuisModal() {
    if (!koshuisModalOverlay) return;
    koshuisModalOverlay.classList.remove('open');
    koshuisModalOverlay.setAttribute('aria-hidden', 'true');
    if (newKoshuisName) newKoshuisName.value = '';
    if (newKoshuisAddress) newKoshuisAddress.value = '';
    if (newKoshuisCapacity) newKoshuisCapacity.value = '';
    if (newKoshuisKampus) newKoshuisKampus.value = '';
    // Return the shared modal to create mode after closing.
    editingKoshuisId = null;
    if (koshuisModalTitle) koshuisModalTitle.textContent = 'Skep Koshuis';
    if (createKoshuisBtn) createKoshuisBtn.textContent = 'Skep';
    if (deleteKoshuisBtn) deleteKoshuisBtn.style.display = 'none';
  }

  /** Open the koshuis modal in edit mode, pre-filled with the koshuis data. */
  // Hierdie funksie maak die koshuis-venster oop om 'n bestaande koshuis
  // te wysig, met al die inligting reeds ingevul.
  function openEditKoshuisModal(koshuis) {
    editingKoshuisId = koshuis.Koshuis_ID;
    if (newKoshuisName) newKoshuisName.value = koshuis.KOS_Naam || '';
    if (newKoshuisAddress) newKoshuisAddress.value = koshuis.KOS_Adres || '';
    if (newKoshuisCapacity) newKoshuisCapacity.value = koshuis.KOS_Kapasiteit != null ? String(koshuis.KOS_Kapasiteit) : '';
    if (newKoshuisKampus) newKoshuisKampus.value = koshuis.Kampus_ID != null ? String(koshuis.Kampus_ID) : '';
    if (koshuisModalTitle) koshuisModalTitle.textContent = 'Wysig Koshuis';
    if (createKoshuisBtn) createKoshuisBtn.textContent = 'Stoor Veranderinge';
    if (deleteKoshuisBtn) deleteKoshuisBtn.style.display = '';
    openKoshuisModal();
  }

  /** Delete the currently-edited koshuis (DELETE /koshuise/{id}). */
  // Hierdie funksie verwyder die koshuis wat tans gewysig word,
  // nadat die admin eers "ja" gesê het.
  async function submitDeleteKoshuis() {
    if (editingKoshuisId === null || !window.MoonApi) return;

    const naam = (newKoshuisName ? newKoshuisName.value.trim() : '') || 'hierdie koshuis';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

    // Vra die bediener om die koshuis uit te vee.
    const json = await window.MoonApi.deleteKoshuis(editingKoshuisId);

    if (json && json.sukses) {
      alert('Koshuis suksesvol verwyder.');
      closeKoshuisModal();
      await loadKoshuise();
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie koshuis verwyder nie.');
    }
  }

  /** Submit the koshuis modal: POST /koshuise or PUT /koshuise/{id} in edit mode. */
  // Hierdie funksie stoor die koshuis-venster se inligting:
  // dit skep 'n nuwe koshuis, of werk 'n bestaande een by.
  async function submitNewKoshuis() {
    const naam = newKoshuisName ? newKoshuisName.value.trim() : '';
    const adres = newKoshuisAddress ? newKoshuisAddress.value.trim() : '';
    const kapasiteit = newKoshuisCapacity ? Number(newKoshuisCapacity.value) : NaN;
    const kampusId = newKoshuisKampus && newKoshuisKampus.value ? Number(newKoshuisKampus.value) : null;

    // Kyk dat al die verpligte velde reg ingevul is.
    if (!naam) {
      alert('Voer asseblief die koshuisnaam in.');
      return;
    }
    if (!Number.isInteger(kapasiteit) || kapasiteit <= 0) {
      alert("Voer asseblief 'n geldige kapasiteit in.");
      return;
    }
    if (!kampusId) {
      alert('Kies asseblief die kampus.');
      return;
    }

    const payload = {
      KOS_Naam: naam,
      KOS_Adres: adres || null,
      KOS_Kapasiteit: kapasiteit,
      Kampus_ID: kampusId
    };

    // Stuur die inligting na die bediener: werk by as ons wysig, skep anders 'n nuwe een.
    const json = editingKoshuisId !== null
      ? await window.MoonApi.updateKoshuis(editingKoshuisId, payload)
      : await window.MoonApi.createKoshuis(payload);

    if (json && json.sukses) {
      alert(editingKoshuisId !== null ? 'Koshuis suksesvol opgedateer.' : 'Koshuis suksesvol geskep.');
      closeKoshuisModal();
      await loadKoshuise();
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie koshuis stoor nie.');
    }
  }

  // =====================================================================
  //  USER (GEBRUIKERS) SECTION
  // =====================================================================

  // Hierdie funksie wys die gebruiker-venster op die skerm.
  function showUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.add('open');
    userModalOverlay.setAttribute('aria-hidden', 'false');
  }

  /** Open the modal in create mode (from the "Skep Gebruiker" button). */
  // Hierdie funksie maak die gebruiker-venster oop om 'n nuwe gebruiker te skep.
  function openUserModal() {
    resetUserModalToCreate();
    showUserModal();
  }

  // Hierdie funksie maak die gebruiker-venster toe en stel dit terug
  // sodat dit weer gereed is om 'n nuwe gebruiker te skep.
  function closeUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.remove('open');
    userModalOverlay.setAttribute('aria-hidden', 'true');
    // Always return the shared modal to create mode after closing.
    resetUserModalToCreate();
  }

  /** Clear the create/edit form and put the modal back into create mode. */
  // Hierdie funksie maak al die velde in die gebruiker-venster skoon
  // en sit die venster terug in "skep"-modus.
  function resetUserModalToCreate() {
    editingUserId = null;

    if (newUserName) newUserName.value = '';
    if (newUserSurname) newUserSurname.value = '';
    if (newUserEmail) newUserEmail.value = '';
    if (newUserStudentNr) newUserStudentNr.value = '';
    if (newUserPassword) {
      newUserPassword.value = '';
      newUserPassword.placeholder = 'Voer wagwoord in';
    }
    if (newUserRoles) {
    newUserRoles.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = false; });
  }
    if (newUserIsKoshuis) newUserIsKoshuis.checked = false;
    if (newUserKoshuis) newUserKoshuis.value = '';
    if (studentNumberField) studentNumberField.style.display = 'none';
    if (studentIsKoshuisField) studentIsKoshuisField.style.display = 'none';
    if (studentKoshuisField) studentKoshuisField.style.display = 'none';
    if (newUserKampus) newUserKampus.value = '';
    if (opsigterKampusField) opsigterKampusField.style.display = 'none';
    if (userActiveRow) userActiveRow.style.display = 'none';
    if (newUserActive) newUserActive.checked = true;

    if (userModalTitle) userModalTitle.textContent = 'Skep Gebruiker';
    if (createUserBtn) createUserBtn.textContent = 'Skep';
    if (deleteUserBtn) deleteUserBtn.style.display = 'none';
  }

  /**
   * Open the shared modal in edit mode for a given user.
   * Fetches fresh data via GET /gebruikers/{userId} and pre-fills the form.
   */
  // Hierdie funksie maak die gebruiker-venster oop om 'n bestaande gebruiker
  // te wysig. Dit haal eers die nuutste inligting vanaf die bediener.
  async function openEditUserModal(userId) {
    if (!window.MoonApi) return;

    // Vra die bediener vir hierdie gebruiker se inligting.
    const json = await window.MoonApi.fetchGebruiker(userId);
    if (!json || !json.sukses || !json.data) {
      // Kon nie die inligting kry nie: wys die foutboodskap.
      alert((json && (json.fout || json.detail)) || 'Kon nie gebruiker se data laai nie.');
      return;
    }

    const user = json.data;
    editingUserId = userId;

    if (newUserName) newUserName.value = user.GEB_Naam || '';
    if (newUserSurname) newUserSurname.value = user.GEB_Van || '';
    if (newUserEmail) newUserEmail.value = user.GEB_Epos || '';
    if (newUserRoles) {
      newUserRoles.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
        cb.checked = (user.Rol_IDs || []).indexOf(Number(cb.value)) !== -1;
      });
    }

    // Password stays blank + optional while editing.
    if (newUserPassword) {
      newUserPassword.value = '';
      newUserPassword.placeholder = 'Los leeg om wagwoord te behou';
    }

    // Show/hide + pre-fill the student-number field based on the role.
    if (newUserIsKoshuis) {
      newUserIsKoshuis.checked = !!(user.STU_Is_Koshuis || user.Koshuis_ID != null);
    }
    toggleStudentField();
    if (newUserStudentNr) newUserStudentNr.value = user.STU_Nommer || '';
    if (newUserKoshuis) newUserKoshuis.value = user.Koshuis_ID != null ? String(user.Koshuis_ID) : '';

    // Opsigters: wys en vul die kampus-keuselys in.
    toggleOpsigterField();
    if (newUserKampus) newUserKampus.value = user.Kampus_ID != null ? String(user.Kampus_ID) : '';

    if (userModalTitle) userModalTitle.textContent = 'Wysig Gebruiker';
    if (createUserBtn) createUserBtn.textContent = 'Stoor Veranderinge';

    // Admins mag nie hul eie rekening skrap nie — kry ook 'n 400 van die backend.
    if (deleteUserBtn) {
      deleteUserBtn.style.display = Number(userId) === getLoggedInUserId() ? 'none' : '';
    }

    if (userActiveRow) userActiveRow.style.display = 'block';
    if (newUserActive) newUserActive.checked = user.Is_Aktief !== false;

    showUserModal();
  }

  /** Load roles from API into the filter dropdown and build rolleMap. */
  // Hierdie funksie laai die lys van rolle (bv. Student, Admin) vanaf
  // die bediener en vul die rol-keuselyste in.
  async function loadRolleDropdown() {
  if (!window.MoonApi) return;

  // Vra die bediener vir al die rolle.
  const json = await window.MoonApi.fetchRolle();
  if (!json || !json.sukses || !Array.isArray(json.data)) return;

  rolleMap = {};

  if (userRoleFilter) {
    userRoleFilter.innerHTML = '<option value="">Alle Rolle</option>';
  }

  // Sit elke rol in die filter-lys en in die skep-gebruiker-lys.
  json.data.forEach(function (r) {
    const displayName = rolDisplayNames[r.ROL_Naam] || r.ROL_Naam;
    rolleMap[String(r.Rol_ID)] = displayName;

    if (userRoleFilter) {
      const opt = document.createElement('option');
      opt.value = String(r.Rol_ID);
      opt.textContent = displayName;
      userRoleFilter.appendChild(opt);
    }

    if (newUserRoles) {
      const label = document.createElement('label');
      label.className = 'role-checkbox';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.name = 'new-user-roles';
      cb.value = String(r.Rol_ID);
      cb.dataset.rolNaam = r.ROL_Naam;
      label.appendChild(cb);
      label.appendChild(document.createTextNode(' ' + displayName));
      newUserRoles.appendChild(label);
    }
  });
}

  /** Load all gebruikers from the API into the user list. */
  // Hierdie funksie laai die lys van gebruikers vanaf die bediener
  // en sit elkeen as 'n ry in die Gebruikers-paneel.
  async function loadGebruikers() {
    if (!userList || !window.MoonApi) return;

    // Vra die bediener vir al die gebruikers.
    const json = await window.MoonApi.fetchGebruikers();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    // Maak die lys leeg en bou dit dan ry vir ry op.
    userList.innerHTML = '';
    json.data.forEach(function (user) {
      // Die Is_Aktief veld uit die databasis bepaal die status in die lys.
      const isAktief = user.Is_Aktief !== false;
      // 'n Leë Rol_IDs-lys is "truthy" — val net terug na die legacy Rol_ID
      // as daar werklik geen rolle in die nuwe stelsel nie.
      const gebruikerRolIds = Array.isArray(user.Rol_IDs) && user.Rol_IDs.length ? user.Rol_IDs : [user.Rol_ID];
      addUserRow(user.Gebruiker_ID, user.GEB_Naam, user.GEB_Van, user.GEB_Epos, gebruikerRolIds, isAktief, user.Kampus_ID);
    });
  }

  /** Build the Aktief/Nie-Aktief status badge vanaf die Is_Aktief veld. */
  // Hierdie funksie maak die klein "Aktief" of "Nie-Aktief" etiket
  // wat langs 'n gebruiker se naam wys.
  function buildStatusBadge(isAktief) {
    const badge = document.createElement('span');
    badge.className = 'status-badge ' + (isAktief ? 'status-badge--active' : 'status-badge--inactive');

    const dot = document.createElement('span');
    dot.className = 'status-dot';
    badge.appendChild(dot);
    badge.appendChild(document.createTextNode(isAktief ? 'Aktief' : 'Nie-Aktief'));

    return badge;
  }

  /** Create a user row in the list. */
  // Hierdie funksie voeg een gebruiker-ry by die lys: naam, e-pos,
  // status, rol-etiket en 'n "Wysig"-knoppie.
  /** Show (or remove) the "Kampus: X" line under an opsigter's roles. */
  // Hierdie funksie wys onder 'n Opsigter se rolle aan watter kampus
  // hy/sy gekoppel is, of haal die reël weg as daar geen kampus is nie.
  function setUserRowKampus(row, kampusId) {
    const rolesDiv = row.querySelector('.admin-user-roles');
    if (!rolesDiv) return;
    let kampusDiv = rolesDiv.querySelector('.admin-user-kampus');
    if (kampusId == null || kampusId === '') {
      if (kampusDiv) kampusDiv.remove();
      return;
    }
    if (!kampusDiv) {
      kampusDiv = document.createElement('div');
      kampusDiv.className = 'admin-user-email admin-user-kampus';
      rolesDiv.appendChild(kampusDiv);
    }
    kampusDiv.textContent = 'Kampus: ' + (kampusMap[String(kampusId)] || ('#' + kampusId));
  }

  function addUserRow(userId, naam, van, epos, rolIds, isAktief, kampusId) {
    if (!userList) return;

    var roleIdsArr = Array.isArray(rolIds) ? rolIds : (rolIds ? [rolIds] : []);
    const row = document.createElement('div');
    row.className = 'admin-user-row';

    const infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-user-name-text';
    nameSpan.textContent = naam + ' ' + van;

    nameDiv.appendChild(nameSpan);
    nameDiv.appendChild(buildStatusBadge(isAktief));

    const emailDiv = document.createElement('div');
    emailDiv.className = 'admin-user-email';
    emailDiv.textContent = epos;

    infoDiv.appendChild(nameDiv);
    infoDiv.appendChild(emailDiv);

    const rolesDiv = document.createElement('div');
    rolesDiv.className = 'admin-user-roles';

    roleIdsArr.forEach(function(rolId) {
      const rolNaam = rolleMap[String(rolId)] || 'Onbekend';
      const badge = document.createElement('span');
      // Strip spasies EN onderstrepe sodat rou DB-rolname (bv. Kampus_Opsigter)
      // na dieselfde CSS-klasse as vertoonname (bv. "Kampus Opsigter") map.
      badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/[\s_]+/g, '');
      badge.textContent = rolNaam;
      rolesDiv.appendChild(badge);
    });

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'admin-user-actions';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn-outline btn-sm';
    editBtn.textContent = 'Wysig';
    editBtn.addEventListener('click', function () { openEditUserModal(userId); });
    actionsDiv.appendChild(editBtn);

    // Store IDs for filtering + editing
    row.dataset.userId = String(userId);
    row.dataset.rolIds = JSON.stringify(roleIdsArr);
    row.dataset.search = `${naam} ${van} ${epos}`.toLowerCase();

    row.appendChild(infoDiv);
    row.appendChild(rolesDiv);
    row.appendChild(actionsDiv);
    setUserRowKampus(row, kampusId);
    userList.appendChild(row);
  }

  /** Filter user list by search text and role dropdown. */
  // Hierdie funksie wys net die gebruikers wat by die soekwoord en die
  // gekose rol pas, en steek die res weg.
  function applyUserFilter() {
    console.log('applyUserFilter running');
    if (!userList) return;

  const query = userSearch ? userSearch.value.trim().toLowerCase() : '';
  const roleFilter = userRoleFilter ? userRoleFilter.value : '';

  const rows = userList.querySelectorAll('.admin-user-row');

  // Kyk vir elke ry of dit by die soekwoord én die rol-filter pas.
  rows.forEach(function (row) {
    const searchable = row.dataset.search || '';
    let userRoleIds = [];
    try { userRoleIds = JSON.parse(row.dataset.rolIds || '[]'); } catch(e) {}

    const matchesSearch =
      query === '' || searchable.includes(query);

    const matchesRole =
      roleFilter === '' || userRoleIds.indexOf(Number(roleFilter)) !== -1;

    row.style.display = (matchesSearch && matchesRole) ? '' : 'none';
  });

  capListHeight(userList, '.admin-user-row');
}

  /** Show/hide the studentenommer + koshuis fields based on selected role. */
  // Hierdie funksie wys of versteek die studentenommer- en koshuis-velde,
  // afhangend of die gekose rol "Student" is.
  function toggleStudentField() {
  if (!newUserRoles || !studentNumberField) return;
  var isStudent = newUserRoles.querySelector('input[data-rol-naam="Student"]:checked') !== null;

  studentNumberField.style.display = isStudent ? 'block' : 'none';
  // Die koshuis-merkblokkie wys slegs vir studente; die dropdown volg die merkblokkie.
  if (studentIsKoshuisField) studentIsKoshuisField.style.display = isStudent ? 'block' : 'none';
  if (!isStudent && newUserIsKoshuis) newUserIsKoshuis.checked = false;
  toggleKoshuisDropdown();
}

  /** Show the koshuis dropdown only while the "bly in 'n koshuis" checkbox is ticked. */
  // Hierdie funksie wys die koshuis-keuselys net terwyl die
  // "bly in 'n koshuis" blokkie gemerk is.
  function toggleKoshuisDropdown() {
    if (!studentKoshuisField) return;

    const wys = !!(newUserIsKoshuis && newUserIsKoshuis.checked &&
                   studentIsKoshuisField && studentIsKoshuisField.style.display !== 'none');
    studentKoshuisField.style.display = wys ? 'block' : 'none';
    if (!wys && newUserKoshuis) newUserKoshuis.value = '';
  }

  /** Is the Opsigter role ticked in the create/edit user modal? */
  // Hierdie funksie kyk of die "Opsigter"-rol in die venster gemerk is.
  function isOpsigterGekies() {
    return !!(newUserRoles && newUserRoles.querySelector('input[data-rol-naam="Kampus_Opsigter"]:checked'));
  }

  /** Show the kampus dropdown only while the Opsigter role is ticked. */
  // Hierdie funksie wys die kampus-keuselys net vir Opsigters, want
  // 'n Opsigter moet aan 'n kampus gekoppel wees om dit te kan bestuur.
  function toggleOpsigterField() {
    if (!opsigterKampusField) return;
    const wys = isOpsigterGekies();
    opsigterKampusField.style.display = wys ? 'block' : 'none';
    if (!wys && newUserKampus) newUserKampus.value = '';
  }

  /** Submit new user to the backend. */
  // Hierdie funksie stoor die gebruiker-venster se inligting:
  // dit skep 'n nuwe gebruiker, of stuur wysigings aan na submitEditUser.
  async function submitNewUser() {
    const naam = newUserName ? newUserName.value.trim() : '';
    const van = newUserSurname ? newUserSurname.value.trim() : '';
    const epos = newUserEmail ? newUserEmail.value.trim() : '';
    const wagwoord = newUserPassword ? newUserPassword.value.trim() : '';
    const rolIds = newUserRoles ? [...newUserRoles.querySelectorAll('input:checked')].map(function(cb) { return Number(cb.value); }) : [];
    const studentNr = newUserStudentNr ? newUserStudentNr.value.trim() : '';

    // Use studentenommer as ID_Nommer if student, otherwise use email as fallback
    const isStudent = newUserRoles ? newUserRoles.querySelector('input[data-rol-naam="Student"]:checked') !== null : false;
    const isOpsigter = isOpsigterGekies();
    const kampusId = newUserKampus && newUserKampus.value ? Number(newUserKampus.value) : null;

    // ===== EDIT MODE =====
    // As ons besig is om 'n bestaande gebruiker te wysig, gaan na submitEditUser.
    if (editingUserId !== null) {
      await submitEditUser({ naam, van, epos, wagwoord, rolIds, studentNr, isStudent, isOpsigter, kampusId });
      return;
    }

    // ===== CREATE MODE =====
    // Kyk dat al die verpligte velde ingevul is.
    if (!naam || !van || !epos || !wagwoord || rolIds.length === 0) {
      alert('Voltooi asseblief alle verpligte velde.');
      return;
    }

const payload = {
  GEB_Naam: naam,
  GEB_Van: van,
  GEB_Epos: epos,
  GEB_Wagwoord: wagwoord,
  Rol_IDs: rolIds,
  Is_Aktief: true,
};

// Studente het ekstra inligting nodig: 'n studentenommer en dalk 'n koshuis.
if (isStudent) {
  if (!studentNr) {
    alert('Voer asseblief die studentenommer in.');
    return;
  }

  const isKoshuis = !!(newUserIsKoshuis && newUserIsKoshuis.checked);
  if (isKoshuis && (!newUserKoshuis || !newUserKoshuis.value)) {
    alert('Kies asseblief die koshuis waarin die student bly.');
    return;
  }

  payload.GEB_ID_Nommer = studentNr;
  payload.STU_Nommer = studentNr;
  payload.STU_Is_Koshuis = isKoshuis;
  payload.Koshuis_ID = isKoshuis ? Number(newUserKoshuis.value) : null;
}

else if (
    rolIds.some(function(rid) {
      var n = rolleMap[String(rid)] || '';
      return n === 'Personeel' || n === 'Sekuriteits Wag' || n === 'Opsigter' || n === 'Admin';
    })
) {
    // Werknemers login met e-pos.
    // PER_Nommer word outomaties deur die backend geskep.
    payload.GEB_ID_Nommer = Date.now().toString().slice(-13);
}

else {
  payload.GEB_ID_Nommer = Date.now().toString().slice(-13);
}

// 'n Opsigter MOET aan 'n kampus gekoppel wees, anders kan hy/sy geen
// kampus-bladsye gebruik nie.
if (isOpsigter) {
  if (!kampusId) {
    alert('Kies asseblief die kampus waarvoor die Opsigter verantwoordelik is.');
    return;
  }
  payload.Kampus_ID = kampusId;
}

// Stuur die nuwe gebruiker se inligting na die bediener.
const json = await window.MoonApi.createGebruiker(payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol geskep.');
      const nuweId = json.data ? json.data.Gebruiker_ID : null;
      closeUserModal(); // also resets the form back to create mode

      // Add new user to the list immediately (nog geen NFC-tag → Nie-Aktief)
      addUserRow(nuweId, naam, van, epos, rolIds, payload.Is_Aktief, payload.Kampus_ID);
      capListHeight(userList, '.admin-user-row');
    } else {
      alert(foutBoodskap(json, 'Kon nie gebruiker skep nie.'));
    }
  }

  /** Submit edits for the currently-edited user (PUT /gebruikers/{id}). */
  // Hierdie funksie stuur die wysigings van 'n bestaande gebruiker
  // na die bediener en werk dan die ry in die lys by.
  async function submitEditUser(fields) {
    const { naam, van, epos, wagwoord, rolIds, studentNr, isStudent, isOpsigter, kampusId } = fields;

    // Kyk dat al die verpligte velde ingevul is.
    if (!naam || !van || !epos || rolIds.length === 0) {
      alert('Voltooi asseblief alle verpligte velde.');
      return;
    }

    const payload = {
      GEB_Naam: naam,
      GEB_Van: van,
      GEB_Epos: epos,
      Rol_IDs: rolIds,
      Is_Aktief: newUserActive ? newUserActive.checked : true,
    };

    // Password is optional in edit mode — only send it when a new one is typed.
    if (wagwoord) {
      payload.GEB_Wagwoord = wagwoord;
    }

    if (isStudent) {
      if (!studentNr) {
        alert('Voer asseblief die studentenommer in.');
        return;
      }

      const isKoshuis = !!(newUserIsKoshuis && newUserIsKoshuis.checked);
      if (isKoshuis && (!newUserKoshuis || !newUserKoshuis.value)) {
        alert('Kies asseblief die koshuis waarin die student bly.');
        return;
      }

      payload.STU_Nommer = studentNr;
      payload.STU_Is_Koshuis = isKoshuis;
      payload.Koshuis_ID = isKoshuis ? Number(newUserKoshuis.value) : null;
    }

    // Opsigter: kampus is verpligtend. As die Opsigter-rol verwyder is,
    // stuur null sodat die ou kampus-koppeling ook verwyder word.
    if (isOpsigter) {
      if (!kampusId) {
        alert('Kies asseblief die kampus waarvoor die Opsigter verantwoordelik is.');
        return;
      }
      payload.Kampus_ID = kampusId;
    } else {
      payload.Kampus_ID = null;
    }

    // Stuur die wysigings na die bediener.
    const json = await window.MoonApi.updateGebruiker(editingUserId, payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol opgedateer.');
      const data = json.data || {};
      updateUserRow(editingUserId,{
        naam: data.GEB_Naam || naam,
        van: data.GEB_Van || van,
        epos: data.GEB_Epos || epos,
        rolIds: data.Rol_IDs || rolIds,
        isAktief: data.Is_Aktief ?? payload.Is_Aktief,
        kampusId: isOpsigter ? (data.Kampus_ID ?? payload.Kampus_ID) : null,
    });
      closeUserModal(); // resets the form back to create mode
    } else {
      alert(foutBoodskap(json, 'Kon nie gebruiker opdateer nie.'));
    }
  }

  /** Update an existing user row in place with fresh data. */
  // Hierdie funksie werk 'n bestaande gebruiker-ry se naam, e-pos,
  // rol en status by sonder om die hele lys oor te bou.
  function updateUserRow(userId, info) {
    if (!userList) return;

    const row = userList.querySelector('.admin-user-row[data-user-id="' + userId + '"]');
    if (!row) return;

    const nameSpan = row.querySelector('.admin-user-name-text');
    const emailDiv = row.querySelector('.admin-user-email');
    const rolesDiv = row.querySelector('.admin-user-roles');

    if (nameSpan) nameSpan.textContent = info.naam + ' ' + info.van;
    if (emailDiv) emailDiv.textContent = info.epos;

    if (rolesDiv) {
      rolesDiv.innerHTML = '';
      var roleIdsArr = Array.isArray(info.rolIds) ? info.rolIds : (info.rolIds ? [info.rolIds] : []);
      roleIdsArr.forEach(function(rolId) {
        const rolNaam = rolleMap[String(rolId)] || 'Onbekend';
        const badge = document.createElement('span');
        // Strip spasies EN onderstrepe sodat rou DB-rolname (bv. Kampus_Opsigter)
      // na dieselfde CSS-klasse as vertoonname (bv. "Kampus Opsigter") map.
      badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/[\s_]+/g, '');
        badge.textContent = rolNaam;
        rolesDiv.appendChild(badge);
      });
    }

    const oldBadge = row.querySelector('.status-badge');
    if (oldBadge) {
        oldBadge.replaceWith(buildStatusBadge(info.isAktief !== false));
    }

    setUserRowKampus(row, info.kampusId);

    row.dataset.rolIds = JSON.stringify(info.rolIds || []);
    row.dataset.search = `${info.naam} ${info.van} ${info.epos}`.toLowerCase();
  }

  /** Soft-delete the currently-edited user (DELETE /gebruikers/{id}). */
  // Hierdie funksie skrap die gebruiker wat tans gewysig word, nadat die
  // admin eers "ja" gesê het. Die gebruiker word net onaktief gemaak.
  async function submitDeleteUser() {
    if (!editingUserId || !window.MoonApi) return;

    const naam = ((newUserName ? newUserName.value : '') + ' ' +
                  (newUserSurname ? newUserSurname.value : '')).trim() || 'hierdie gebruiker';
    if (!confirm('Is jy seker jy wil vir ' + naam + ' skrap?')) return;

    // Vra die bediener om die gebruiker te skrap.
    const userId = editingUserId;
    const json = await window.MoonApi.deleteGebruiker(userId);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol geskrap.');
      // Geskrapte gebruikers bly in die lys, maar hul badge wys nou Nie-Aktief.
      const row = userList
        ? userList.querySelector('.admin-user-row[data-user-id="' + userId + '"]')
        : null;
      if (row) {
        const oldBadge = row.querySelector('.status-badge');
        if (oldBadge) oldBadge.replaceWith(buildStatusBadge(false));
      }
      closeUserModal(); // resets the form back to create mode
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie gebruiker skrap nie.');
    }
  }

  // =====================================================================
  //  WIRE EVENTS
  // =====================================================================
  // Hieronder koppel ons al die knoppies en velde aan die regte funksies,
  // sodat iets gebeur wanneer die admin klik of tik.

  // --- Venue events ---
  // Die "+ Skep Lokaal" knoppie maak die lokaal-venster oop.
  if (openVenueModalBtn) {
    openVenueModalBtn.addEventListener('click', openClassModal);
  }
  // Die "Kanselleer" knoppie maak die lokaal-venster toe.
  if (closeClassModalBtn) {
    closeClassModalBtn.addEventListener('click', closeClassModal);
  }
  // As jy buite die lokaal-venster klik, maak dit ook toe.
  if (classModalOverlay) {
    classModalOverlay.addEventListener('click', function (event) {
      if (event.target === classModalOverlay) closeClassModal();
    });
  }
  // Die "Skep" knoppie stoor die lokaal.
  if (createClassBtn) {
    createClassBtn.addEventListener('click', function () { submitNewClass(); });
  }
  // Die "Verwyder" knoppie skrap die lokaal.
  if (deleteLokaalBtn) {
    deleteLokaalBtn.addEventListener('click', function () { submitDeleteLokaal(); });
  }
  // As jy in die soekveld tik, word die lokale-lys dadelik gefiltreer.
  if (venueSearch) {
    venueSearch.addEventListener('input', function () {
      console.log('VENUE SEARCH FIRED');
      applyVenueFilter();
    });
}
  // As jy 'n ander kampus in die filter kies, word die lys ook gefiltreer.
  if (venueCampusFilter) {
    venueCampusFilter.addEventListener('change', function () {
      console.log('VENUE CAMPUS FILTER FIRED');
      applyVenueFilter();
    });
  }
  if (gateSearch) {
    gateSearch.addEventListener('input', applyVenueFilter);
  }
  if (gateCampusFilter) {
    gateCampusFilter.addEventListener('change', applyVenueFilter);
  }

  // --- Kampus events ---
  // Die "+ Skep Kampus" knoppie maak die kampus-venster oop.
  if (openKampusModalBtn) {
    openKampusModalBtn.addEventListener('click', openKampusModal);
  }
  // Die "Kanselleer" knoppie maak die kampus-venster toe.
  if (closeKampusModalBtn) {
    closeKampusModalBtn.addEventListener('click', closeKampusModal);
  }
  // As jy buite die kampus-venster klik, maak dit ook toe.
  if (kampusModalOverlay) {
    kampusModalOverlay.addEventListener('click', function (event) {
      if (event.target === kampusModalOverlay) closeKampusModal();
    });
  }
  // Die "Skep" knoppie stoor die kampus.
  if (createKampusBtn) {
    createKampusBtn.addEventListener('click', function () { submitNewKampus(); });
  }
  // Die "Verwyder" knoppie skrap die kampus.
  if (deleteKampusBtn) {
    deleteKampusBtn.addEventListener('click', function () { submitDeleteKampus(); });
  }
  // As jy in die soekveld tik, word die kampus-lys dadelik gefiltreer.
  if (kampusSearch) {
    kampusSearch.addEventListener('input', function () { applyKampusFilter(); });
  }

  // --- Koshuis events ---
  // Die "+ Skep Koshuis" knoppie maak die koshuis-venster oop.
  if (openKoshuisModalBtn) {
    openKoshuisModalBtn.addEventListener('click', openKoshuisModal);
  }
  // Die "Kanselleer" knoppie maak die koshuis-venster toe.
  if (closeKoshuisModalBtn) {
    closeKoshuisModalBtn.addEventListener('click', closeKoshuisModal);
  }
  // As jy buite die koshuis-venster klik, maak dit ook toe.
  if (koshuisModalOverlay) {
    koshuisModalOverlay.addEventListener('click', function (event) {
      if (event.target === koshuisModalOverlay) closeKoshuisModal();
    });
  }
  // Die "Skep" knoppie stoor die koshuis.
  if (createKoshuisBtn) {
    createKoshuisBtn.addEventListener('click', function () { submitNewKoshuis(); });
  }
  // Die "Verwyder" knoppie skrap die koshuis.
  if (deleteKoshuisBtn) {
    deleteKoshuisBtn.addEventListener('click', function () { submitDeleteKoshuis(); });
  }
  // As jy in die soekveld tik, word die koshuis-lys dadelik gefiltreer.
  if (koshuisSearch) {
    koshuisSearch.addEventListener('input', function () { applyKoshuisFilter(); });
  }

  // --- User events ---
  // Die "+ Skep Gebruiker" knoppie maak die gebruiker-venster oop.
  if (openUserModalBtn) {
    openUserModalBtn.addEventListener('click', openUserModal);
  }
  // Die "Kanselleer" knoppie maak die gebruiker-venster toe.
  if (closeUserModalBtn) {
    closeUserModalBtn.addEventListener('click', closeUserModal);
  }
  // As jy buite die gebruiker-venster klik, maak dit ook toe.
  if (userModalOverlay) {
    userModalOverlay.addEventListener('click', function (event) {
      if (event.target === userModalOverlay) closeUserModal();
    });
  }
  // Die "Skep" knoppie stoor die gebruiker.
  if (createUserBtn) {
    createUserBtn.addEventListener('click', function () { submitNewUser(); });
  }
  // Die "Verwyder" knoppie skrap die gebruiker.
  if (deleteUserBtn) {
    deleteUserBtn.addEventListener('click', function () { submitDeleteUser(); });
  }
  // As jy in die soekveld tik, word die gebruiker-lys dadelik gefiltreer.
  if (userSearch) {
    userSearch.addEventListener('input', function () {
      console.log('USER SEARCH FIRED');
      applyUserFilter();
    });
  }
  // As jy 'n ander rol in die filter kies, word die lys ook gefiltreer.
  if (userRoleFilter) {
    userRoleFilter.addEventListener('change', function () {
      console.log('ROLE FILTER FIRED');
      applyUserFilter();
    });
  }
  // As die rol verander, wys of versteek die student-velde.
  if (newUserRoles) {
    newUserRoles.addEventListener('change', toggleStudentField);
    newUserRoles.addEventListener('change', toggleOpsigterField);
  }
  // As die koshuis-blokkie gemerk word, wys of versteek die koshuis-keuselys.
  if (newUserIsKoshuis) {
    newUserIsKoshuis.addEventListener('change', toggleKoshuisDropdown);
  }


// Hierdie funksie haal die nuutste syfers vir die kontroleskerm
// (hoeveel studente, personeel en besoekers op kampus is) en wys dit.
async function refreshDashboard() {
  if (!window.MoonApi || !window.MoonApi.fetchLiveDashboard) return;

  try {
    // Vra die bediener vir die jongste syfers.
    const json = await window.MoonApi.fetchLiveDashboard();

    if (!json || !json.sukses || !json.data) return;

    const d = json.data;

    const studenteEl = document.getElementById('dashboard-studente');
    const personeelEl = document.getElementById('dashboard-personeel');
    const besoekersEl = document.getElementById('dashboard-besoekers');
    const toegangeEl = document.getElementById('dashboard-toegange');

    if (studenteEl) studenteEl.textContent = d.studente_op_kampus ?? 0;
    if (personeelEl) personeelEl.textContent = d.personeel_op_kampus ?? 0;
    if (besoekersEl) besoekersEl.textContent = d.besoekers_vandag ?? 0;
    if (toegangeEl) toegangeEl.textContent = d.toegange_vandag ?? 0;

  } catch (e) {
    // As iets skeefloop, skryf die fout net in die konsole neer.
    console.error('Dashboard kon nie laai nie:', e);
  }
}

  // =====================================================================
  //  OUTO-UITSKANDERING (gekoppel aan instellings-API)
  // =====================================================================

  // Die velde en knoppie vir die outo-uitskandering paneel.
  var autoScanoutTime = document.getElementById('auto-scanout-time');
  var saveAutoScanoutBtn = document.getElementById('save-auto-scanout');
  var autoScanoutMsg = document.getElementById('auto-scanout-msg');

  // Laai die gestelde tyd van die bediener af by bladsylaaityd.
  async function loadAutoUitcheckTydstip() {
    if (!window.MoonApi || !autoScanoutTime) return;
    try {
      var json = await window.MoonApi.fetchInstelling('auto_uitcheck_tydstip');
      if (json.sukses && json.data && json.data.Waarde) {
        autoScanoutTime.value = json.data.Waarde;
      }
    } catch (e) {
      console.error('Kon nie auto-uitcheck tyd laai nie:', e);
    }
  }

  // Stoor die tyd via die instellings-API.
  if (saveAutoScanoutBtn) {
    saveAutoScanoutBtn.addEventListener('click', async function () {
      var tyd = autoScanoutTime ? autoScanoutTime.value : '';

      if (!tyd) {
        alert('Kies asseblief \'n tyd.');
        return;
      }

      if (!window.MoonApi) return;

      try {
        saveAutoScanoutBtn.disabled = true;
        var json = await window.MoonApi.updateInstelling('auto_uitcheck_tydstip', { Waarde: tyd });

        if (autoScanoutMsg) {
          if (json.sukses) {
            autoScanoutMsg.textContent = 'Outo-uitcheck tyd gestel vir ' + tyd + '.';
          } else {
            autoScanoutMsg.textContent = json.fout || 'Stoor het misluk.';
          }
          autoScanoutMsg.style.display = 'block';
          setTimeout(function () { autoScanoutMsg.style.display = 'none'; }, 3000);
        }
      } catch (e) {
        console.error('Kon nie auto-uitcheck tyd stoor nie:', e);
        if (autoScanoutMsg) {
          autoScanoutMsg.textContent = 'Fout tydens stoor.';
          autoScanoutMsg.style.display = 'block';
        }
      } finally {
        saveAutoScanoutBtn.disabled = false;
      }
    });
  }

  // =====================================================================
  //  DOSENTE & MODULES (rooster-toewysing)
  // =====================================================================
  // Hierdie paneel wys elke gebruiker met die Personeel-rol saam met die
  // modules wat aan hom/haar toegewys is, en laat die admin modules byvoeg
  // of verwyder. Dit is wat "My Klasse" (personeel.html) vir 'n dosent vul:
  // GET /rooster/personeel/{id}/rooster gee net klasse van toegewysde modules.
  // Die Lantiv-rooster-oplaai (POST /rooster/klasse/import) skep die modules,
  // groepe en klasse waaruit hier gekies word.

  const dosentList = document.getElementById('dosent-list');
  const dosentSearch = document.getElementById('dosent-search');
  const uploadRoosterBtn = document.getElementById('upload-rooster-btn');
  const roosterFileInput = document.getElementById('rooster-file-input');
  const roosterStatus = document.getElementById('rooster-status');
  const roosterOpsomming = document.getElementById('rooster-opsomming');
  const moduleModal = document.getElementById('moduleModal');
  const moduleModalUserName = document.getElementById('module-modal-user-name');
  const currentModules = document.getElementById('current-modules');
  const addModuleSelect = document.getElementById('add-module-select');
  const addModuleBtn = document.getElementById('add-module-btn');
  const moduleModalStatus = document.getElementById('module-modal-status');
  const closeModuleModalBtn = document.getElementById('close-module-modal');

  let alleModules = [];      // [{ Module_ID, MOD_Kode, MOD_Naam }]
  let aantalKlasse = null;   // hoeveel klassessies die rooster het (null = onbekend)
  let dosente = [];          // [{ id, naam, van, epos }]
  let dosentModules = {};    // Gebruiker_ID -> [{ Module_ID, MOD_Kode, MOD_Naam }]
  let moduleModalDosent = null; // dosent wie se modules tans in die modal wys

  // Hierdie funksie wys 'n groen (success) of rooi (error) boodskap in 'n
  // .modal-status-blokkie; 'n leë boodskap steek dit weg.
  function setStatusBox(el, message, type) {
    if (!el) return;
    el.textContent = message || '';
    el.className = 'modal-status' + (message ? ' ' + (type || 'success') : '');
  }

  // Hierdie funksie kyk of 'n bediener-antwoord suksesvol was.
  function isOk(json) {
    return !!(json && json.sukses);
  }

  // Hierdie funksie gee die foutboodskap uit 'n bediener-antwoord.
  // FastAPI se validasiefoute (422) kom as 'n lys objekte in `detail` —
  // anders wys die alert net "[object Object]".
  function foutBoodskap(json, verstek) {
    if (json && typeof json.fout === 'string') return json.fout;
    if (json && typeof json.detail === 'string') return json.detail;
    if (json && Array.isArray(json.detail)) {
      const boodskappe = json.detail
        .map(function (d) {
          if (!d || !d.msg) return '';
          const veld = Array.isArray(d.loc) && d.loc.length > 1 ? d.loc[d.loc.length - 1] + ': ' : '';
          return veld + d.msg.replace(/^Value error, /, '');
        })
        .filter(Boolean);
      if (boodskappe.length) return boodskappe.join('\n');
    }
    if (json && typeof json.boodskap === 'string') return json.boodskap;
    return verstek;
  }

  // Hierdie funksie skryf 'n module leesbaar uit, bv. "EBREK370 — Rekeningkunde".
  function moduleLabel(m) {
    return m.MOD_Naam ? m.MOD_Kode + ' — ' + m.MOD_Naam : m.MOD_Kode;
  }

  // Hierdie funksie kyk of 'n gebruiker se rolle die Personeel-rol insluit
  // (via rolleMap se vertoonname, dus "Personeel" of "Dosente").
  function hetPersoneelRol(rolIds) {
    return rolIds.some(function (rolId) {
      const naam = (rolleMap[String(rolId)] || '').toLowerCase().replace(/[\s_]+/g, '');
      return naam === 'personeel' || naam === 'dosente' || naam === 'dosent';
    });
  }

  // Hierdie funksie gee 'n gebruiker se rol-ID's (nuwe multi-rol lys, of die
  // ou enkel Rol_ID as terugval) — dieselfde reël as loadGebruikers().
  function gebruikerRolIds(user) {
    return Array.isArray(user.Rol_IDs) && user.Rol_IDs.length ? user.Rol_IDs : [user.Rol_ID];
  }

  /** Laai modules, klasse, dosente en toewysings en teken die paneel. */
  async function loadRoosterPaneel() {
    if (!dosentList || !window.MoonApi) return;
    setStatusBox(roosterStatus, '');

    try {
      const resultate = await Promise.all([
        window.MoonApi.fetchModules(),
        window.MoonApi.fetchRoosterKlasse(),
        window.MoonApi.fetchGebruikersAlle(),
        window.MoonApi.fetchPersoneelModuleToewysings()
      ]);
      const modJson = resultate[0];
      const klasJson = resultate[1];
      const gebJson = resultate[2];
      const toewJson = resultate[3];

      if (!isOk(modJson)) throw new Error(foutBoodskap(modJson, 'Kon nie modules laai nie.'));
      if (!isOk(gebJson)) throw new Error(foutBoodskap(gebJson, 'Kon nie gebruikers laai nie.'));
      if (!isOk(toewJson)) throw new Error(foutBoodskap(toewJson, 'Kon nie toewysings laai nie.'));

      alleModules = (modJson.data || []).slice().sort(function (a, b) {
        return String(a.MOD_Kode).localeCompare(String(b.MOD_Kode));
      });
      aantalKlasse = isOk(klasJson) && Array.isArray(klasJson.data) ? klasJson.data.length : null;

      dosentModules = {};
      (toewJson.data || []).forEach(function (t) {
        if (!dosentModules[t.Gebruiker_ID]) dosentModules[t.Gebruiker_ID] = [];
        dosentModules[t.Gebruiker_ID].push({
          Module_ID: t.Module_ID, MOD_Kode: t.MOD_Kode, MOD_Naam: t.MOD_Naam
        });
      });

      dosente = (gebJson.data || [])
        .filter(function (u) { return hetPersoneelRol(gebruikerRolIds(u)); })
        .map(function (u) {
          return { id: u.Gebruiker_ID, naam: u.GEB_Naam, van: u.GEB_Van, epos: u.GEB_Epos, isAktief: u.Is_Aktief !== false };
        })
        .sort(function (a, b) { return (a.van + a.naam).localeCompare(b.van + b.naam); });

      renderDosente();
      renderRoosterOpsomming();
    } catch (err) {
      setStatusBox(roosterStatus, 'Kon nie die dosente-paneel laai nie: ' + err.message, 'error');
    }
  }

  // Hierdie funksie wys onderaan die paneel hoeveel modules en klasse daar is.
  function renderRoosterOpsomming() {
    if (!roosterOpsomming) return;
    let teks = alleModules.length + ' module' + (alleModules.length === 1 ? '' : 's');
    if (aantalKlasse !== null) teks += ' · ' + aantalKlasse + ' klas' + (aantalKlasse === 1 ? '' : 'se') + ' in die rooster';
    if (alleModules.length === 0) teks += '. Laai die Lantiv-rooster op om modules te skep.';
    roosterOpsomming.textContent = teks;
  }

  // Hierdie funksie bou een dosent-ry: naam, e-pos, module-etikette en 'n
  // "Modules"-knoppie wat die toewysings-modal oopmaak.
  function addDosentRow(dosent) {
    const row = document.createElement('div');
    row.className = 'admin-user-row';
    row.dataset.userId = String(dosent.id);
    row.dataset.search = (dosent.naam + ' ' + dosent.van + ' ' + dosent.epos).toLowerCase();

    const infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';
    const nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-user-name-text';
    nameSpan.textContent = dosent.naam + ' ' + dosent.van;
    nameDiv.appendChild(nameSpan);
    nameDiv.appendChild(buildStatusBadge(dosent.isAktief));
    const emailDiv = document.createElement('div');
    emailDiv.className = 'admin-user-email';
    emailDiv.textContent = dosent.epos;
    infoDiv.appendChild(nameDiv);
    infoDiv.appendChild(emailDiv);

    const modulesDiv = document.createElement('div');
    modulesDiv.className = 'admin-user-roles';
    const modules = dosentModules[dosent.id] || [];
    if (modules.length === 0) {
      const geen = document.createElement('span');
      geen.className = 'admin-user-email';
      geen.textContent = 'Geen modules';
      modulesDiv.appendChild(geen);
    } else {
      modules.forEach(function (m) {
        const badge = document.createElement('span');
        badge.className = 'role-badge module-badge';
        badge.textContent = m.MOD_Kode;
        if (m.MOD_Naam) badge.title = m.MOD_Naam;
        modulesDiv.appendChild(badge);
      });
    }

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'admin-user-actions';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-outline btn-sm';
    btn.textContent = 'Modules';
    btn.addEventListener('click', function () { openModuleModal(dosent); });
    actionsDiv.appendChild(btn);

    row.appendChild(infoDiv);
    row.appendChild(modulesDiv);
    row.appendChild(actionsDiv);
    dosentList.appendChild(row);
  }

  /** Teken die dosente-lys oor (en pas die soekfilter toe). */
  function renderDosente() {
    if (!dosentList) return;
    dosentList.innerHTML = '';
    if (dosente.length === 0) {
      const leeg = document.createElement('div');
      leeg.className = 'admin-user-row';
      const info = document.createElement('div');
      info.className = 'admin-user-info';
      const msg = document.createElement('div');
      msg.className = 'admin-user-email';
      msg.textContent = 'Geen gebruikers met die Personeel-rol nie. Gee \'n gebruiker die Personeel-rol onder "Gebruikers".';
      info.appendChild(msg);
      leeg.appendChild(info);
      dosentList.appendChild(leeg);
      return;
    }
    dosente.forEach(addDosentRow);
    applyDosentFilter();
  }

  /** Steek dosente weg wat nie by die soekwoord pas nie. */
  function applyDosentFilter() {
    if (!dosentList) return;
    const query = dosentSearch ? dosentSearch.value.trim().toLowerCase() : '';
    dosentList.querySelectorAll('.admin-user-row').forEach(function (row) {
      const searchable = row.dataset.search || '';
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
    capListHeight(dosentList, '.admin-user-row');
  }

  // ----- Module-modal -----

  /** Maak die modal oop vir 'n dosent. */
  function openModuleModal(dosent) {
    if (!moduleModal) return;
    moduleModalDosent = dosent;
    if (moduleModalUserName) moduleModalUserName.textContent = dosent.naam + ' ' + dosent.van;
    setStatusBox(moduleModalStatus, '');
    renderModuleModal();
    moduleModal.classList.add('open');
    moduleModal.setAttribute('aria-hidden', 'false');
  }

  /** Maak die modal toe. */
  function closeModuleModal() {
    if (!moduleModal) return;
    moduleModal.classList.remove('open');
    moduleModal.setAttribute('aria-hidden', 'true');
    moduleModalDosent = null;
  }

  /** Teken die toegewysde modules (met ×) en die keuselys van oorblywende modules. */
  function renderModuleModal() {
    if (!moduleModalDosent) return;
    const toegewys = dosentModules[moduleModalDosent.id] || [];
    const toegewysIds = toegewys.map(function (m) { return m.Module_ID; });

    if (currentModules) {
      currentModules.innerHTML = '';
      if (toegewys.length === 0) {
        const geen = document.createElement('span');
        geen.className = 'admin-user-email';
        geen.textContent = 'Nog geen modules toegewys nie.';
        currentModules.appendChild(geen);
      }
      toegewys.forEach(function (m) {
        const badge = document.createElement('span');
        badge.className = 'role-badge-removable module-badge';
        badge.title = moduleLabel(m);
        badge.appendChild(document.createTextNode(m.MOD_Kode + ' '));
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'role-badge-remove';
        x.innerHTML = '&times;';
        x.setAttribute('aria-label', 'Verwyder ' + m.MOD_Kode);
        x.addEventListener('click', function () { verwyderModuleVanDosent(m); });
        badge.appendChild(x);
        currentModules.appendChild(badge);
      });
    }

    if (addModuleSelect) {
      addModuleSelect.innerHTML = '';
      const eerste = document.createElement('option');
      eerste.value = '';
      const oorblywend = alleModules.filter(function (m) { return toegewysIds.indexOf(m.Module_ID) === -1; });
      eerste.textContent = alleModules.length === 0
        ? 'Geen modules — laai eers die rooster op'
        : (oorblywend.length === 0 ? 'Alle modules is reeds toegewys' : 'Kies module...');
      addModuleSelect.appendChild(eerste);
      oorblywend.forEach(function (m) {
        const opt = document.createElement('option');
        opt.value = String(m.Module_ID);
        opt.textContent = moduleLabel(m);
        addModuleSelect.appendChild(opt);
      });
      addModuleSelect.disabled = oorblywend.length === 0;
      if (addModuleBtn) addModuleBtn.disabled = oorblywend.length === 0;
    }
  }

  /** Wys die gekose module in die keuselys aan die dosent toe. */
  async function voegModuleByDosent() {
    if (!moduleModalDosent || !addModuleSelect || !window.MoonApi) return;
    const moduleId = parseInt(addModuleSelect.value, 10);
    if (!moduleId) {
      setStatusBox(moduleModalStatus, 'Kies eers \'n module.', 'error');
      return;
    }
    const module = alleModules.filter(function (m) { return m.Module_ID === moduleId; })[0];
    const dosent = moduleModalDosent;
    if (addModuleBtn) addModuleBtn.disabled = true;
    try {
      const json = await window.MoonApi.assignPersoneelModule(dosent.id, moduleId);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie module toewys nie.'));
      if (!dosentModules[dosent.id]) dosentModules[dosent.id] = [];
      dosentModules[dosent.id].push(module);
      dosentModules[dosent.id].sort(function (a, b) { return String(a.MOD_Kode).localeCompare(String(b.MOD_Kode)); });
      setStatusBox(moduleModalStatus, module.MOD_Kode + ' toegewys aan ' + dosent.naam + ' ' + dosent.van + '.', 'success');
      if (moduleModalDosent === dosent) renderModuleModal();
      renderDosente();
    } catch (err) {
      setStatusBox(moduleModalStatus, err.message, 'error');
      if (addModuleBtn) addModuleBtn.disabled = false;
    }
  }

  /** Haal 'n module van die dosent in die modal af. */
  async function verwyderModuleVanDosent(module) {
    if (!moduleModalDosent || !window.MoonApi) return;
    const dosent = moduleModalDosent;
    try {
      const json = await window.MoonApi.unassignPersoneelModule(dosent.id, module.Module_ID);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie module verwyder nie.'));
      dosentModules[dosent.id] = (dosentModules[dosent.id] || []).filter(function (m) {
        return m.Module_ID !== module.Module_ID;
      });
      setStatusBox(moduleModalStatus, module.MOD_Kode + ' verwyder van ' + dosent.naam + ' ' + dosent.van + '.', 'success');
      if (moduleModalDosent === dosent) renderModuleModal();
      renderDosente();
    } catch (err) {
      setStatusBox(moduleModalStatus, err.message, 'error');
    }
  }

  // ----- Lantiv-rooster oplaai -----

  /** Stuur die gekose CSV na POST /rooster/klasse/import en herlaai die paneel. */
  async function handleRoosterUpload() {
    if (!roosterFileInput || !roosterFileInput.files || !roosterFileInput.files.length) return;
    const file = roosterFileInput.files[0];
    roosterFileInput.value = '';
    if (!window.MoonApi) return;

    setStatusBox(roosterStatus, 'Laai "' + file.name + '" op...', 'success');
    if (uploadRoosterBtn) uploadRoosterBtn.disabled = true;
    try {
      const json = await window.MoonApi.importKlasseCsv(file);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Oplaai het misluk.'));
      const d = json.data || {};
      const foute = Array.isArray(d.foute) ? d.foute : [];
      let boodskap = 'Rooster ingevoer: ' + (d.modules_geskep || 0) + ' nuwe modules, ' +
        (d.groepe_geskep || 0) + ' nuwe groepe, ' + (d.klasse_geskep || 0) + ' klasse.';
      if (foute.length) boodskap += ' ' + foute.length + ' ry(e) oorgeslaan: ' + foute.slice(0, 3).join('; ') + (foute.length > 3 ? ' …' : '');
      await loadRoosterPaneel();
      await loadStudentPaneel();
      setStatusBox(roosterStatus, boodskap, foute.length && !d.klasse_geskep ? 'error' : 'success');
    } catch (err) {
      setStatusBox(roosterStatus, 'Kon nie die rooster oplaai nie: ' + err.message, 'error');
    } finally {
      if (uploadRoosterBtn) uploadRoosterBtn.disabled = false;
    }
  }

  // ----- Gebeurtenisse vir hierdie paneel -----
  if (dosentSearch) dosentSearch.addEventListener('input', applyDosentFilter);
  if (uploadRoosterBtn && roosterFileInput) {
    uploadRoosterBtn.addEventListener('click', function () { roosterFileInput.click(); });
    roosterFileInput.addEventListener('change', handleRoosterUpload);
  }
  if (addModuleBtn) addModuleBtn.addEventListener('click', voegModuleByDosent);
  if (closeModuleModalBtn) closeModuleModalBtn.addEventListener('click', closeModuleModal);
  if (moduleModal) {
    // Klik buite die venster maak dit toe (soos die ander modals).
    moduleModal.addEventListener('click', function (ev) {
      if (ev.target === moduleModal) closeModuleModal();
    });
  }

  // =====================================================================
  //  STUDENTE & GROEPE (wie op 'n klas se register verskyn)
  // =====================================================================
  // 'n Student kom op 'n klas se register (personeel.html) via sy/haar groep
  // (Student_Groep -> Klas_Groep), via 'n module (Student_Module -> Klas) of
  // via 'n direkte klas-toewysing. Hierdie paneel bestuur die eerste twee,
  // een-vir-een in 'n modal of in grootmaat met 'n CSV
  // (POST /rooster/studente/import).

  const studentList = document.getElementById('student-list');
  const studentSearch = document.getElementById('student-search');
  const uploadStudenteBtn = document.getElementById('upload-studente-btn');
  const studenteFileInput = document.getElementById('studente-file-input');
  const studenteStatus = document.getElementById('studente-status');
  const studenteOpsomming = document.getElementById('studente-opsomming');
  const studentModal = document.getElementById('studentModal');
  const studentModalUserName = document.getElementById('student-modal-user-name');
  const currentStudentGroepe = document.getElementById('current-student-groepe');
  const addStudentGroepSelect = document.getElementById('add-student-groep-select');
  const addStudentGroepBtn = document.getElementById('add-student-groep-btn');
  const currentStudentModules = document.getElementById('current-student-modules');
  const addStudentModuleSelect = document.getElementById('add-student-module-select');
  const addStudentModuleBtn = document.getElementById('add-student-module-btn');
  const studentModalStatus = document.getElementById('student-modal-status');
  const closeStudentModalBtn = document.getElementById('close-student-modal');

  let alleGroepe = [];          // [{ Groep_ID, GRO_Naam }]
  let studente = [];            // [{ id, naam, van, epos, nommer, isAktief }]
  let studentGroepe = {};       // Gebruiker_ID -> [{ Groep_ID, GRO_Naam }]
  let studentModules = {};      // Gebruiker_ID -> [{ Module_ID, MOD_Kode, MOD_Naam }]
  let studentModalStudent = null;

  // Hierdie funksie kyk of 'n gebruiker die Student-rol het (Rol_Namen van
  // die bediener, of rolleMap as terugval).
  function hetStudentRol(user) {
    if (Array.isArray(user.Rol_Namen) && user.Rol_Namen.length) {
      return user.Rol_Namen.indexOf('Student') !== -1;
    }
    return gebruikerRolIds(user).some(function (rolId) {
      return (rolleMap[String(rolId)] || '').toLowerCase() === 'student';
    });
  }

  /** Laai groepe, modules, studente en toewysings en teken die paneel. */
  async function loadStudentPaneel() {
    if (!studentList || !window.MoonApi) return;
    setStatusBox(studenteStatus, '');

    try {
      const resultate = await Promise.all([
        window.MoonApi.fetchGroepe(),
        alleModules.length ? Promise.resolve({ sukses: true, data: alleModules }) : window.MoonApi.fetchModules(),
        window.MoonApi.fetchGebruikersAlle(),
        window.MoonApi.fetchStudentToewysings()
      ]);
      const groepJson = resultate[0];
      const modJson = resultate[1];
      const gebJson = resultate[2];
      const toewJson = resultate[3];

      if (!isOk(groepJson)) throw new Error(foutBoodskap(groepJson, 'Kon nie groepe laai nie.'));
      if (!isOk(modJson)) throw new Error(foutBoodskap(modJson, 'Kon nie modules laai nie.'));
      if (!isOk(gebJson)) throw new Error(foutBoodskap(gebJson, 'Kon nie gebruikers laai nie.'));
      if (!isOk(toewJson)) throw new Error(foutBoodskap(toewJson, 'Kon nie toewysings laai nie.'));

      alleGroepe = (groepJson.data || []).slice().sort(function (a, b) {
        return String(a.GRO_Naam).localeCompare(String(b.GRO_Naam));
      });
      if (!alleModules.length) {
        alleModules = (modJson.data || []).slice().sort(function (a, b) {
          return String(a.MOD_Kode).localeCompare(String(b.MOD_Kode));
        });
      }

      studentGroepe = {};
      studentModules = {};
      const toew = toewJson.data || {};
      (toew.groepe || []).forEach(function (t) {
        if (!studentGroepe[t.Gebruiker_ID]) studentGroepe[t.Gebruiker_ID] = [];
        studentGroepe[t.Gebruiker_ID].push({ Groep_ID: t.Groep_ID, GRO_Naam: t.GRO_Naam });
      });
      (toew.modules || []).forEach(function (t) {
        if (!studentModules[t.Gebruiker_ID]) studentModules[t.Gebruiker_ID] = [];
        studentModules[t.Gebruiker_ID].push({ Module_ID: t.Module_ID, MOD_Kode: t.MOD_Kode, MOD_Naam: t.MOD_Naam });
      });

      studente = (gebJson.data || [])
        .filter(hetStudentRol)
        .map(function (u) {
          return {
            id: u.Gebruiker_ID, naam: u.GEB_Naam, van: u.GEB_Van, epos: u.GEB_Epos,
            nommer: u.STU_Nommer || '', isAktief: u.Is_Aktief !== false
          };
        })
        .sort(function (a, b) { return (a.van + a.naam).localeCompare(b.van + b.naam); });

      renderStudente();
      renderStudenteOpsomming();
    } catch (err) {
      setStatusBox(studenteStatus, 'Kon nie die studente-paneel laai nie: ' + err.message, 'error');
    }
  }

  // Hierdie funksie wys onderaan hoeveel studente gekoppel is.
  function renderStudenteOpsomming() {
    if (!studenteOpsomming) return;
    const gekoppel = studente.filter(function (s) {
      return (studentGroepe[s.id] || []).length || (studentModules[s.id] || []).length;
    }).length;
    let teks = studente.length + ' student' + (studente.length === 1 ? '' : 'e') + ', ' +
      gekoppel + ' gekoppel aan \'n groep of module · ' + alleGroepe.length + ' groep' + (alleGroepe.length === 1 ? '' : 'e');
    if (alleGroepe.length === 0) teks += '. Laai die Lantiv-rooster op om groepe te skep.';
    studenteOpsomming.textContent = teks;
  }

  // Hierdie funksie bou een student-ry: naam, nommer/e-pos, groep- en
  // module-etikette en 'n "Toewysings"-knoppie.
  function addStudentRow(student) {
    const row = document.createElement('div');
    row.className = 'admin-user-row';
    row.dataset.userId = String(student.id);
    const groepe = studentGroepe[student.id] || [];
    const modules = studentModules[student.id] || [];
    row.dataset.search = (
      student.naam + ' ' + student.van + ' ' + student.epos + ' ' + student.nommer + ' ' +
      groepe.map(function (g) { return g.GRO_Naam; }).join(' ') + ' ' +
      modules.map(function (m) { return m.MOD_Kode; }).join(' ')
    ).toLowerCase();

    const infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';
    const nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-user-name-text';
    nameSpan.textContent = student.naam + ' ' + student.van;
    nameDiv.appendChild(nameSpan);
    nameDiv.appendChild(buildStatusBadge(student.isAktief));
    const subDiv = document.createElement('div');
    subDiv.className = 'admin-user-email';
    subDiv.textContent = student.nommer ? student.nommer + ' · ' + student.epos : student.epos;
    infoDiv.appendChild(nameDiv);
    infoDiv.appendChild(subDiv);

    const badgesDiv = document.createElement('div');
    badgesDiv.className = 'admin-user-roles';
    if (groepe.length === 0 && modules.length === 0) {
      const geen = document.createElement('span');
      geen.className = 'admin-user-email';
      geen.textContent = 'Geen groep of module';
      badgesDiv.appendChild(geen);
    }
    groepe.forEach(function (g) {
      const badge = document.createElement('span');
      badge.className = 'role-badge groep-badge';
      badge.textContent = g.GRO_Naam;
      badge.title = 'Groep';
      badgesDiv.appendChild(badge);
    });
    modules.forEach(function (m) {
      const badge = document.createElement('span');
      badge.className = 'role-badge module-badge';
      badge.textContent = m.MOD_Kode;
      badge.title = 'Module' + (m.MOD_Naam ? ': ' + m.MOD_Naam : '');
      badgesDiv.appendChild(badge);
    });

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'admin-user-actions';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-outline btn-sm';
    btn.textContent = 'Toewysings';
    btn.addEventListener('click', function () { openStudentModal(student); });
    actionsDiv.appendChild(btn);

    row.appendChild(infoDiv);
    row.appendChild(badgesDiv);
    row.appendChild(actionsDiv);
    studentList.appendChild(row);
  }

  /** Teken die studente-lys oor (en pas die soekfilter toe). */
  function renderStudente() {
    if (!studentList) return;
    studentList.innerHTML = '';
    if (studente.length === 0) {
      const leeg = document.createElement('div');
      leeg.className = 'admin-user-row';
      const info = document.createElement('div');
      info.className = 'admin-user-info';
      const msg = document.createElement('div');
      msg.className = 'admin-user-email';
      msg.textContent = 'Geen gebruikers met die Student-rol nie.';
      info.appendChild(msg);
      leeg.appendChild(info);
      studentList.appendChild(leeg);
      return;
    }
    studente.forEach(addStudentRow);
    applyStudentFilter();
  }

  /** Steek studente weg wat nie by die soekwoord pas nie (naam, nommer, groep, module). */
  function applyStudentFilter() {
    if (!studentList) return;
    const query = studentSearch ? studentSearch.value.trim().toLowerCase() : '';
    studentList.querySelectorAll('.admin-user-row').forEach(function (row) {
      const searchable = row.dataset.search || '';
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
    capListHeight(studentList, '.admin-user-row');
  }

  // ----- Student-modal -----

  function openStudentModal(student) {
    if (!studentModal) return;
    studentModalStudent = student;
    if (studentModalUserName) {
      studentModalUserName.textContent = student.naam + ' ' + student.van + (student.nommer ? ' (' + student.nommer + ')' : '');
    }
    setStatusBox(studentModalStatus, '');
    renderStudentModal();
    studentModal.classList.add('open');
    studentModal.setAttribute('aria-hidden', 'false');
  }

  function closeStudentModal() {
    if (!studentModal) return;
    studentModal.classList.remove('open');
    studentModal.setAttribute('aria-hidden', 'true');
    studentModalStudent = null;
  }

  // Hierdie funksie vul een etiket-houer + keuselys (vir groepe óf modules).
  function renderToewysingBlok(houer, select, knoppie, toegewys, alles, idVeld, naamFn, leegTeks, verwyderFn) {
    const toegewysIds = toegewys.map(function (t) { return t[idVeld]; });
    if (houer) {
      houer.innerHTML = '';
      if (toegewys.length === 0) {
        const geen = document.createElement('span');
        geen.className = 'admin-user-email';
        geen.textContent = leegTeks;
        houer.appendChild(geen);
      }
      toegewys.forEach(function (t) {
        const badge = document.createElement('span');
        badge.className = 'role-badge-removable ' + (idVeld === 'Groep_ID' ? 'groep-badge' : 'module-badge');
        badge.title = naamFn(t);
        badge.appendChild(document.createTextNode((idVeld === 'Groep_ID' ? t.GRO_Naam : t.MOD_Kode) + ' '));
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'role-badge-remove';
        x.innerHTML = '&times;';
        x.setAttribute('aria-label', 'Verwyder ' + naamFn(t));
        x.addEventListener('click', function () { verwyderFn(t); });
        badge.appendChild(x);
        houer.appendChild(badge);
      });
    }
    if (select) {
      select.innerHTML = '';
      const oorblywend = alles.filter(function (a) { return toegewysIds.indexOf(a[idVeld]) === -1; });
      const eerste = document.createElement('option');
      eerste.value = '';
      eerste.textContent = alles.length === 0
        ? 'Geen beskikbaar — laai eers die rooster op'
        : (oorblywend.length === 0 ? 'Alles is reeds toegewys' : 'Kies...');
      select.appendChild(eerste);
      oorblywend.forEach(function (a) {
        const opt = document.createElement('option');
        opt.value = String(a[idVeld]);
        opt.textContent = naamFn(a);
        select.appendChild(opt);
      });
      select.disabled = oorblywend.length === 0;
      if (knoppie) knoppie.disabled = oorblywend.length === 0;
    }
  }

  /** Teken albei blokke (groepe en modules) vir die student in die modal. */
  function renderStudentModal() {
    if (!studentModalStudent) return;
    const id = studentModalStudent.id;
    renderToewysingBlok(
      currentStudentGroepe, addStudentGroepSelect, addStudentGroepBtn,
      studentGroepe[id] || [], alleGroepe, 'Groep_ID',
      function (g) { return g.GRO_Naam; },
      'Nog geen groep nie.', verwyderGroepVanStudent
    );
    renderToewysingBlok(
      currentStudentModules, addStudentModuleSelect, addStudentModuleBtn,
      studentModules[id] || [], alleModules, 'Module_ID',
      moduleLabel,
      'Geen direkte module nie (groep dek gewoonlik die klasse).', verwyderModuleVanStudent
    );
  }

  async function voegGroepByStudent() {
    if (!studentModalStudent || !addStudentGroepSelect || !window.MoonApi) return;
    const groepId = parseInt(addStudentGroepSelect.value, 10);
    if (!groepId) { setStatusBox(studentModalStatus, 'Kies eers \'n groep.', 'error'); return; }
    const groep = alleGroepe.filter(function (g) { return g.Groep_ID === groepId; })[0];
    const student = studentModalStudent;
    if (addStudentGroepBtn) addStudentGroepBtn.disabled = true;
    try {
      const json = await window.MoonApi.assignStudentGroep(student.id, groepId);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie groep toewys nie.'));
      if (!studentGroepe[student.id]) studentGroepe[student.id] = [];
      studentGroepe[student.id].push(groep);
      studentGroepe[student.id].sort(function (a, b) { return String(a.GRO_Naam).localeCompare(String(b.GRO_Naam)); });
      setStatusBox(studentModalStatus, student.naam + ' ' + student.van + ' is by groep ' + groep.GRO_Naam + ' gevoeg.', 'success');
      if (studentModalStudent === student) renderStudentModal();
      renderStudente();
      renderStudenteOpsomming();
    } catch (err) {
      setStatusBox(studentModalStatus, err.message, 'error');
      if (addStudentGroepBtn) addStudentGroepBtn.disabled = false;
    }
  }

  async function verwyderGroepVanStudent(groep) {
    if (!studentModalStudent || !window.MoonApi) return;
    const student = studentModalStudent;
    try {
      const json = await window.MoonApi.unassignStudentGroep(student.id, groep.Groep_ID);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie groep verwyder nie.'));
      studentGroepe[student.id] = (studentGroepe[student.id] || []).filter(function (g) { return g.Groep_ID !== groep.Groep_ID; });
      setStatusBox(studentModalStatus, 'Groep ' + groep.GRO_Naam + ' verwyder.', 'success');
      if (studentModalStudent === student) renderStudentModal();
      renderStudente();
      renderStudenteOpsomming();
    } catch (err) {
      setStatusBox(studentModalStatus, err.message, 'error');
    }
  }

  async function voegModuleByStudent() {
    if (!studentModalStudent || !addStudentModuleSelect || !window.MoonApi) return;
    const moduleId = parseInt(addStudentModuleSelect.value, 10);
    if (!moduleId) { setStatusBox(studentModalStatus, 'Kies eers \'n module.', 'error'); return; }
    const module = alleModules.filter(function (m) { return m.Module_ID === moduleId; })[0];
    const student = studentModalStudent;
    if (addStudentModuleBtn) addStudentModuleBtn.disabled = true;
    try {
      const json = await window.MoonApi.assignStudentModule(student.id, moduleId);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie module toewys nie.'));
      if (!studentModules[student.id]) studentModules[student.id] = [];
      studentModules[student.id].push(module);
      studentModules[student.id].sort(function (a, b) { return String(a.MOD_Kode).localeCompare(String(b.MOD_Kode)); });
      setStatusBox(studentModalStatus, module.MOD_Kode + ' toegewys aan ' + student.naam + ' ' + student.van + '.', 'success');
      if (studentModalStudent === student) renderStudentModal();
      renderStudente();
      renderStudenteOpsomming();
    } catch (err) {
      setStatusBox(studentModalStatus, err.message, 'error');
      if (addStudentModuleBtn) addStudentModuleBtn.disabled = false;
    }
  }

  async function verwyderModuleVanStudent(module) {
    if (!studentModalStudent || !window.MoonApi) return;
    const student = studentModalStudent;
    try {
      const json = await window.MoonApi.unassignStudentModule(student.id, module.Module_ID);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Kon nie module verwyder nie.'));
      studentModules[student.id] = (studentModules[student.id] || []).filter(function (m) { return m.Module_ID !== module.Module_ID; });
      setStatusBox(studentModalStatus, module.MOD_Kode + ' verwyder.', 'success');
      if (studentModalStudent === student) renderStudentModal();
      renderStudente();
      renderStudenteOpsomming();
    } catch (err) {
      setStatusBox(studentModalStatus, err.message, 'error');
    }
  }

  // ----- Grootmaat CSV-oplaai -----

  /** Stuur die CSV na POST /rooster/studente/import en herlaai die paneel. */
  async function handleStudenteUpload() {
    if (!studenteFileInput || !studenteFileInput.files || !studenteFileInput.files.length) return;
    const file = studenteFileInput.files[0];
    studenteFileInput.value = '';
    if (!window.MoonApi) return;

    setStatusBox(studenteStatus, 'Laai "' + file.name + '" op...', 'success');
    if (uploadStudenteBtn) uploadStudenteBtn.disabled = true;
    try {
      const json = await window.MoonApi.importStudentToewysingsCsv(file);
      if (!isOk(json)) throw new Error(foutBoodskap(json, 'Oplaai het misluk.'));
      const d = json.data || {};
      const foute = Array.isArray(d.foute) ? d.foute : [];
      let boodskap = 'Toewysings ingevoer: ' + (d.studente_verwerk || 0) + ' studente verwerk, ' +
        (d.groep_koppelings || 0) + ' groep-koppelings, ' + (d.module_koppelings || 0) + ' module-koppelings' +
        ((d.groepe_geskep || 0) ? ', ' + d.groepe_geskep + ' nuwe groepe' : '') + '.';
      if (foute.length) boodskap += ' ' + foute.length + ' fout(e): ' + foute.slice(0, 3).join('; ') + (foute.length > 3 ? ' …' : '');
      await loadStudentPaneel();
      setStatusBox(studenteStatus, boodskap, foute.length && !d.studente_verwerk ? 'error' : 'success');
    } catch (err) {
      setStatusBox(studenteStatus, 'Kon nie die toewysings oplaai nie: ' + err.message, 'error');
    } finally {
      if (uploadStudenteBtn) uploadStudenteBtn.disabled = false;
    }
  }

  // ----- Gebeurtenisse vir hierdie paneel -----
  if (studentSearch) studentSearch.addEventListener('input', applyStudentFilter);
  if (uploadStudenteBtn && studenteFileInput) {
    uploadStudenteBtn.addEventListener('click', function () { studenteFileInput.click(); });
    studenteFileInput.addEventListener('change', handleStudenteUpload);
  }
  if (addStudentGroepBtn) addStudentGroepBtn.addEventListener('click', voegGroepByStudent);
  if (addStudentModuleBtn) addStudentModuleBtn.addEventListener('click', voegModuleByStudent);
  if (closeStudentModalBtn) closeStudentModalBtn.addEventListener('click', closeStudentModal);
  if (studentModal) {
    studentModal.addEventListener('click', function (ev) {
      if (ev.target === studentModal) closeStudentModal();
    });
  }

  // =====================================================================
  //  INIT
  // =====================================================================

  // Wanneer die bladsy klaar gelaai het, laai ons al die lyste
  // vanaf die bediener en begin die kontroleskerm elke 5 sekondes verfris.
  document.addEventListener('DOMContentLoaded', async function () {
  await loadKampusDropdown();
  await loadRolleDropdown();
  await loadCsvTableOptions();

  toggleStudentField();
  toggleOpsigterField();

  await loadLokale();
  applyVenueFilter();

  await loadKoshuise();

  await loadGebruikers();
  applyUserFilter();

  await loadRoosterPaneel();
  await loadStudentPaneel();

  await loadAutoUitcheckTydstip();

  await refreshDashboard();

  if (uploadCsvBtn) {
    uploadCsvBtn.addEventListener('click', openCsvModal);
  }

  if (closeCsvModalBtn) {
    closeCsvModalBtn.addEventListener('click', closeCsvModal);
  }

  if (csvActionSelect) {
    csvActionSelect.addEventListener('change', updateCsvPanelVisibility);
  }

  if (csvSourceSelect) {
    csvSourceSelect.addEventListener('change', updateCsvPanelVisibility);
  }

  if (confirmCsvActionBtn) {
    confirmCsvActionBtn.addEventListener('click', handleCsvAction);
  }

  if (csvFileInput) {
    csvFileInput.addEventListener('change', function () {
      if (!csvFileInput.files || !csvFileInput.files.length) return;
      openCsvModal();
    });
  }

  setInterval(refreshDashboard, 5000);

  });
})();
