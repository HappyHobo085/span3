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
  const openVenueModalBtn = document.getElementById('open-create-venue-modal');
  const classModalOverlay = document.getElementById('class-modal-overlay');
  const closeClassModalBtn = document.getElementById('close-class-modal');
  const createClassBtn = document.getElementById('create-class-button');
  const classRoomName = document.getElementById('class-room-name');
  const classKampus = document.getElementById('class-kampus');
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
  const newUserPassword = document.getElementById('new-user-password');
  const newUserRole = document.getElementById('new-user-role');
  const userModalTitle = document.getElementById('create-user-title');
  const newUserActive = document.getElementById('newUserActive');
  const userActiveRow = document.getElementById('user-active-row');

  // Hierdie veranderlikes onthou of ons besig is om iets te wysig:
  // null beteken "skep nuut", 'n nommer beteken "wysig daardie een".
  // Edit mode tracking: null = create, an ID = editing that record.
  let editingUserId = null;
  let editingKampusId = null;
  let editingLokaalId = null;
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

    if (csvSourceGroup) {
      csvSourceGroup.style.display = isImport ? '' : 'none';
    }

    if (!isImport) {
      if (csvFileGroup) csvFileGroup.style.display = 'none';
      if (csvTextGroup) csvTextGroup.style.display = 'none';
      return;
    }

    const source = csvSourceSelect.value;
    if (csvFileGroup) {
      csvFileGroup.style.display = source === 'file' ? '' : 'none';
    }
    if (csvTextGroup) {
      csvTextGroup.style.display = source === 'text' ? '' : 'none';
    }
  }

  async function handleCsvAction() {
    if (!window.MoonApi) return;

    const table = csvTableSelect ? csvTableSelect.value : '';
    const action = csvActionSelect ? csvActionSelect.value : 'import';
    const source = csvSourceSelect ? csvSourceSelect.value : 'file';
    const mode = csvModeSelect ? csvModeSelect.value : 'merge';

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

    showCsvStatus('CSV is suksesvol opgelaai na ' + table + ' in ' + mode + '-modus.', 'success');
    await reloadAdminPageDataAfterImport(table);
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
    json.data.forEach(function (lok) {
      addVenueRow(lok.Lokasie_ID, lok.LOK_Naam, lok.Kampus_ID);
    });
  }

  // Hierdie funksie voeg een lokaal-ry by die lys: naam,
  // kampus-etiket en 'n "Wysig"-knoppie.
  function addVenueRow(lokasieId, name, kampusId) {
    if (!venueList) return;

    const row = document.createElement('div');
    row.className = 'admin-venue-row';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-venue-name';
    nameSpan.textContent = name;

    const badge = document.createElement('span');
    badge.className = 'campus-badge';
    badge.textContent = kampusMap[String(kampusId)] || 'Onbekend';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn-outline btn-sm';
    editBtn.textContent = 'Wysig';
    editBtn.addEventListener('click', function () { openEditLokaalModal(row); });

    row.dataset.lokasieId = String(lokasieId);
    row.dataset.kampusId = String(kampusId);
    row.dataset.name = name.toLowerCase();
    row.appendChild(nameSpan);
    row.appendChild(badge);
    row.appendChild(editBtn);
    venueList.appendChild(row);
  }

  /** Update an existing venue row in place with fresh data. */
  // Hierdie funksie werk 'n bestaande lokaal-ry se naam en kampus by
  // sonder om die hele lys oor te bou.
  function updateVenueRow(lokasieId, name, kampusId) {
    if (!venueList) return;

    const row = venueList.querySelector('.admin-venue-row[data-lokasie-id="' + lokasieId + '"]');
    if (!row) return;

    const nameSpan = row.querySelector('.admin-venue-name');
    const badge = row.querySelector('.campus-badge');

    if (nameSpan) nameSpan.textContent = name;
    if (badge) badge.textContent = kampusMap[String(kampusId)] || 'Onbekend';

    row.dataset.kampusId = String(kampusId);
    row.dataset.name = name.toLowerCase();
  }

 // Hierdie funksie wys net die lokale wat by die soekwoord en die
 // gekose kampus pas, en steek die res weg.
 function applyVenueFilter() {
  console.log('applyVenueFilter running');
  if (!venueList) return;

  const query = venueSearch ? venueSearch.value.trim().toLowerCase() : '';
  const campusFilter = venueCampusFilter ? venueCampusFilter.value : '';

  const rows = venueList.querySelectorAll('.admin-venue-row');

  // Kyk vir elke ry of dit by die soekwoord én die kampus-filter pas.
  rows.forEach(function (row) {
    const name = row.dataset.name || '';
    const kampusId = row.dataset.kampusId || '';

    const matchesSearch =
      query === '' || name.includes(query);

    const matchesCampus =
      campusFilter === '' || kampusId === campusFilter;

    row.style.display = (matchesSearch && matchesCampus) ? '' : 'none';
  });

  capListHeight(venueList, '.admin-venue-row', 6);
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

      if (json && json.sukses) {
        alert('Lokaal suksesvol opgedateer.');
        closeClassModal();
        updateVenueRow(lokasieId, roomName, kampusId);
        applyVenueFilter();
      } else {
        alert((json && json.fout) || (json && json.detail) || 'Kon nie lokaal opdateer nie.');
      }
      return;
    }

    // ===== CREATE MODE =====
    // Ons skep 'n splinternuwe lokaal op die bediener.
    const json = await window.MoonApi.createKlas({
      LOK_Naam: roomName,
      LOK_Tipe: 'Klaskamer',
      Kampus_ID: kampusId,
      NFC_UID: 'TEMP',
      NFC_Tipe: 'Lokasie'
    });

    if (json && json.sukses) {
      alert('Lokaal suksesvol geskep.');
      closeClassModal();
      const nuweId = json.data && json.data.lokasie ? json.data.lokasie.Lokasie_ID : '';
      addVenueRow(nuweId, roomName, kampusId);
      capListHeight(venueList, '.admin-venue-row', 6);
    } else {
      alert((json && json.fout) || 'Kon nie lokaal skep nie.');
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
    if (newUserRole) newUserRole.value = '';
    if (newUserIsKoshuis) newUserIsKoshuis.checked = false;
    if (newUserKoshuis) newUserKoshuis.value = '';
    if (studentNumberField) studentNumberField.style.display = 'none';
    if (studentIsKoshuisField) studentIsKoshuisField.style.display = 'none';
    if (studentKoshuisField) studentKoshuisField.style.display = 'none';
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
    if (newUserRole) newUserRole.value = String(user.Rol_ID);

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

  if (newUserRole) {
    newUserRole.innerHTML = '<option value="">Kies rol...</option>';
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

    if (newUserRole) {
      const opt = document.createElement('option');
      opt.value = String(r.Rol_ID);
      opt.textContent = displayName;
      opt.dataset.rolNaam = r.ROL_Naam;
      newUserRole.appendChild(opt);
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
      addUserRow(user.Gebruiker_ID, user.GEB_Naam, user.GEB_Van, user.GEB_Epos, user.Rol_ID, isAktief);
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
  function addUserRow(userId, naam, van, epos, rolId, isAktief) {
    if (!userList) return;

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

    const rolNaam = rolleMap[String(rolId)] || 'Onbekend';
    const badge = document.createElement('span');
    badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/\s+/g, '');
    badge.textContent = rolNaam;
    rolesDiv.appendChild(badge);

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
    row.dataset.rolId = String(rolId);
    row.dataset.search = `${naam} ${van} ${epos}`.toLowerCase();

    row.appendChild(infoDiv);
    row.appendChild(rolesDiv);
    row.appendChild(actionsDiv);
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
    const rolId = row.dataset.rolId || '';

    const matchesSearch =
      query === '' || searchable.includes(query);

    const matchesRole =
      roleFilter === '' || rolId === roleFilter;

    row.style.display = (matchesSearch && matchesRole) ? '' : 'none';
  });

  capListHeight(userList, '.admin-user-row');
}

  /** Show/hide the studentenommer + koshuis fields based on selected role. */
  // Hierdie funksie wys of versteek die studentenommer- en koshuis-velde,
  // afhangend of die gekose rol "Student" is.
  function toggleStudentField() {
  if (!newUserRole || !studentNumberField) return;

  const selected = newUserRole.options[newUserRole.selectedIndex];
  const rolNaam = selected ? selected.dataset.rolNaam : '';
  const isStudent = rolNaam === 'Student';

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

  /** Submit new user to the backend. */
  // Hierdie funksie stoor die gebruiker-venster se inligting:
  // dit skep 'n nuwe gebruiker, of stuur wysigings aan na submitEditUser.
  async function submitNewUser() {
    const naam = newUserName ? newUserName.value.trim() : '';
    const van = newUserSurname ? newUserSurname.value.trim() : '';
    const epos = newUserEmail ? newUserEmail.value.trim() : '';
    const wagwoord = newUserPassword ? newUserPassword.value.trim() : '';
    const rolId = newUserRole ? Number(newUserRole.value) : null;
    const studentNr = newUserStudentNr ? newUserStudentNr.value.trim() : '';

    // Use studentenommer as ID_Nommer if student, otherwise use email as fallback
    const selected = newUserRole ? newUserRole.options[newUserRole.selectedIndex] : null;
    const rolNaam = selected ? selected.dataset.rolNaam : '';

    // ===== EDIT MODE =====
    // As ons besig is om 'n bestaande gebruiker te wysig, gaan na submitEditUser.
    if (editingUserId !== null) {
      await submitEditUser({ naam, van, epos, wagwoord, rolId, studentNr, rolNaam });
      return;
    }

    // ===== CREATE MODE =====
    // Kyk dat al die verpligte velde ingevul is.
    if (!naam || !van || !epos || !wagwoord || !rolId) {
      alert('Voltooi asseblief alle verpligte velde.');
      return;
    }

const payload = {
  GEB_Naam: naam,
  GEB_Van: van,
  GEB_Epos: epos,
  GEB_Wagwoord: wagwoord,
  Rol_ID: rolId,
  Is_Aktief: true,
};

// Studente het ekstra inligting nodig: 'n studentenommer en dalk 'n koshuis.
if (rolNaam === 'Student') {
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
    rolNaam === 'Personeel' ||
    rolNaam === 'Sekuriteit_Wag' ||
    rolNaam === 'Kampus_Opsigter' ||
    rolNaam === 'Administrateur'
) {
    // Werknemers login met e-pos.
    // PER_Nommer word outomaties deur die backend geskep.
    payload.GEB_ID_Nommer = Date.now().toString().slice(-13);
}

else {
  payload.GEB_ID_Nommer = Date.now().toString().slice(-13);
}

// Stuur die nuwe gebruiker se inligting na die bediener.
const json = await window.MoonApi.createGebruiker(payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol geskep.');
      const nuweId = json.data ? json.data.Gebruiker_ID : null;
      closeUserModal(); // also resets the form back to create mode

      // Add new user to the list immediately (nog geen NFC-tag → Nie-Aktief)
      addUserRow(nuweId, naam, van, epos, rolId, payload.Is_Aktief);
      capListHeight(userList, '.admin-user-row');
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie gebruiker skep nie.');
    }
  }

  /** Submit edits for the currently-edited user (PUT /gebruikers/{id}). */
  // Hierdie funksie stuur die wysigings van 'n bestaande gebruiker
  // na die bediener en werk dan die ry in die lys by.
  async function submitEditUser(fields) {
    const { naam, van, epos, wagwoord, rolId, studentNr, rolNaam } = fields;

    // Kyk dat al die verpligte velde ingevul is.
    if (!naam || !van || !epos || !rolId) {
      alert('Voltooi asseblief alle verpligte velde.');
      return;
    }

    const payload = {
      GEB_Naam: naam,
      GEB_Van: van,
      GEB_Epos: epos,
      Rol_ID: rolId,
      Is_Aktief: newUserActive ? newUserActive.checked : true,
    };

    // Password is optional in edit mode — only send it when a new one is typed.
    if (wagwoord) {
      payload.GEB_Wagwoord = wagwoord;
    }

    if (rolNaam === 'Student') {
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

    // Stuur die wysigings na die bediener.
    const json = await window.MoonApi.updateGebruiker(editingUserId, payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol opgedateer.');
      const data = json.data || {};
      updateUserRow(editingUserId,{
        naam: data.GEB_Naam || naam,
        van: data.GEB_Van || van,
        epos: data.GEB_Epos || epos,
        rolId: data.Rol_ID || rolId,
        isAktief: data.Is_Aktief ?? payload.Is_Aktief,
    });
      closeUserModal(); // resets the form back to create mode
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie gebruiker opdateer nie.');
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
    const badge = row.querySelector('.role-badge');

    if (nameSpan) nameSpan.textContent = info.naam + ' ' + info.van;
    if (emailDiv) emailDiv.textContent = info.epos;

    const rolNaam = rolleMap[String(info.rolId)] || 'Onbekend';
    if (badge) {
      badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/\s+/g, '');
      badge.textContent = rolNaam;
    }

    const oldBadge = row.querySelector('.status-badge');
    if (oldBadge) {
        oldBadge.replaceWith(buildStatusBadge(info.isAktief !== false));
    }

    row.dataset.rolId = String(info.rolId);
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
  if (newUserRole) {
    newUserRole.addEventListener('change', toggleStudentField);
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
  //  OUTO-UITSKANDERING (demo — geen backend, geen stoor nie)
  // =====================================================================

  // Die velde en knoppie vir die outo-uitskandering paneel.
  var autoScanoutTime = document.getElementById('auto-scanout-time');
  var saveAutoScanoutBtn = document.getElementById('save-auto-scanout');
  var autoScanoutMsg = document.getElementById('auto-scanout-msg');

  // Die "Stoor Tyd" knoppie: wys net 'n boodskap met die gekose tyd.
  // (Dit is nog 'n demonstrasie — niks word regtig gestoor nie.)
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

  await loadLokale();
  applyVenueFilter();

  await loadKoshuise();

  await loadGebruikers();
  applyUserFilter();

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
