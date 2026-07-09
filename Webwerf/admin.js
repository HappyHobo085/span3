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

(function () {
  // ===== VENUE DOM NODES =====
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

  // Edit mode tracking: null = create, an ID = editing that record.
  let editingUserId = null;
  let editingKampusId = null;
  let editingLokaalId = null;
  let editingKoshuisId = null;

  // ===== LOOKUP MAPS =====
  let kampusMap = {};
  let rolleMap = {}; // Rol_ID → display name

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

  // =====================================================================
  //  VENUE (LOKALE) SECTION
  // =====================================================================

  function openClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.add('open');
    classModalOverlay.setAttribute('aria-hidden', 'false');
  }

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
  async function submitDeleteLokaal() {
    if (editingLokaalId === null || !window.MoonApi) return;

    const lokasieId = editingLokaalId;
    const naam = (classRoomName ? classRoomName.value.trim() : '') || 'hierdie lokaal';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

    const json = await window.MoonApi.deleteLokasie(lokasieId);

    if (json && json.sukses) {
      alert('Lokaal suksesvol verwyder.');
      closeClassModal();
      const row = venueList
        ? venueList.querySelector('.admin-venue-row[data-lokasie-id="' + lokasieId + '"]')
        : null;
      if (row) row.remove();
      capListHeight(venueList, '.admin-venue-row', 6);
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie lokaal verwyder nie.');
    }
  }

  async function loadKampusDropdown() {
    if (!window.MoonApi) return;

    const json = await window.MoonApi.fetchKampusse();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    if (classKampus) {
      classKampus.innerHTML = '<option value="">Kies kampus...</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        classKampus.appendChild(opt);
      });
    }

    if (venueCampusFilter) {
      venueCampusFilter.innerHTML = '<option value="">Alle Kampusse</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        venueCampusFilter.appendChild(opt);
      });
    }

    if (newKoshuisKampus) {
      newKoshuisKampus.innerHTML = '<option value="">Kies kampus...</option>';
      json.data.forEach(function (k) {
        const opt = document.createElement('option');
        opt.value = String(k.Kampus_ID);
        opt.textContent = k.KAM_Naam;
        newKoshuisKampus.appendChild(opt);
      });
    }

    json.data.forEach(function (k) {
      kampusMap[String(k.Kampus_ID)] = k.KAM_Naam;
    });

    renderKampusList(json.data);
  }

  // =====================================================================
  //  KAMPUS SECTION
  // =====================================================================

  /** Render all kampusse as simple name rows in the Kampusse panel. */
  function renderKampusList(kampusse) {
    if (!kampusList) return;

    kampusList.innerHTML = '';

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

  function openKampusModal() {
    if (!kampusModalOverlay) return;
    kampusModalOverlay.classList.add('open');
    kampusModalOverlay.setAttribute('aria-hidden', 'false');
  }

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
  function openEditKampusModal(kampus) {
    editingKampusId = kampus.Kampus_ID;
    if (newKampusName) newKampusName.value = kampus.KAM_Naam || '';
    if (kampusModalTitle) kampusModalTitle.textContent = 'Wysig Kampus';
    if (createKampusBtn) createKampusBtn.textContent = 'Stoor Veranderinge';
    if (deleteKampusBtn) deleteKampusBtn.style.display = '';
    openKampusModal();
  }

  /** Delete the currently-edited kampus (DELETE /kampusse/{id}). */
  async function submitDeleteKampus() {
    if (editingKampusId === null || !window.MoonApi) return;

    const naam = (newKampusName ? newKampusName.value.trim() : '') || 'hierdie kampus';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

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
  async function submitNewKampus() {
    const naam = newKampusName ? newKampusName.value.trim() : '';

    if (!naam) {
      alert('Voer asseblief die kampusnaam in.');
      return;
    }

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

  async function loadLokale() {
    if (!venueList || !window.MoonApi) return;

    const json = await window.MoonApi.fetchLokasies();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    venueList.innerHTML = '';
    json.data.forEach(function (lok) {
      addVenueRow(lok.Lokasie_ID, lok.LOK_Naam, lok.Kampus_ID);
    });
  }

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

 function applyVenueFilter() {
  console.log('applyVenueFilter running');
  if (!venueList) return;

  const query = venueSearch ? venueSearch.value.trim().toLowerCase() : '';
  const campusFilter = venueCampusFilter ? venueCampusFilter.value : '';

  const rows = venueList.querySelectorAll('.admin-venue-row');

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

  async function submitNewClass() {
    const roomName = classRoomName ? classRoomName.value.trim() : '';
    const kampusId = classKampus ? Number(classKampus.value) : null;

    if (!roomName || !kampusId) {
      alert('Voltooi asseblief die klaskamer naam en kampus.');
      return;
    }

    // ===== EDIT MODE =====
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
  function renderKoshuisList(koshuise) {
    if (!koshuisList) return;

    koshuisList.innerHTML = '';

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

  async function loadKoshuise() {
    if (!koshuisList || !window.MoonApi) return;

    const json = await window.MoonApi.fetchKoshuise();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    renderKoshuisList(json.data);
    populateUserKoshuisDropdown(json.data);
  }

  /** Fill the user modal se koshuis dropdown (student toekenning). */
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

  function openKoshuisModal() {
    if (!koshuisModalOverlay) return;
    koshuisModalOverlay.classList.add('open');
    koshuisModalOverlay.setAttribute('aria-hidden', 'false');
  }

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
  async function submitDeleteKoshuis() {
    if (editingKoshuisId === null || !window.MoonApi) return;

    const naam = (newKoshuisName ? newKoshuisName.value.trim() : '') || 'hierdie koshuis';
    if (!confirm('Is jy seker jy wil "' + naam + '" verwyder?')) return;

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
  async function submitNewKoshuis() {
    const naam = newKoshuisName ? newKoshuisName.value.trim() : '';
    const adres = newKoshuisAddress ? newKoshuisAddress.value.trim() : '';
    const kapasiteit = newKoshuisCapacity ? Number(newKoshuisCapacity.value) : NaN;
    const kampusId = newKoshuisKampus && newKoshuisKampus.value ? Number(newKoshuisKampus.value) : null;

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

  function showUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.add('open');
    userModalOverlay.setAttribute('aria-hidden', 'false');
  }

  /** Open the modal in create mode (from the "Skep Gebruiker" button). */
  function openUserModal() {
    resetUserModalToCreate();
    showUserModal();
  }

  function closeUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.remove('open');
    userModalOverlay.setAttribute('aria-hidden', 'true');
    // Always return the shared modal to create mode after closing.
    resetUserModalToCreate();
  }

  /** Clear the create/edit form and put the modal back into create mode. */
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
  async function openEditUserModal(userId) {
    if (!window.MoonApi) return;

    const json = await window.MoonApi.fetchGebruiker(userId);
    if (!json || !json.sukses || !json.data) {
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
  async function loadRolleDropdown() {
  if (!window.MoonApi) return;

  const json = await window.MoonApi.fetchRolle();
  if (!json || !json.sukses || !Array.isArray(json.data)) return;

  rolleMap = {};

  if (userRoleFilter) {
    userRoleFilter.innerHTML = '<option value="">Alle Rolle</option>';
  }

  if (newUserRole) {
    newUserRole.innerHTML = '<option value="">Kies rol...</option>';
  }

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
  async function loadGebruikers() {
    if (!userList || !window.MoonApi) return;

    const json = await window.MoonApi.fetchGebruikers();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    userList.innerHTML = '';
    json.data.forEach(function (user) {
      // Die Is_Aktief veld uit die databasis bepaal die status in die lys.
      const isAktief = user.Is_Aktief !== false;
      addUserRow(user.Gebruiker_ID, user.GEB_Naam, user.GEB_Van, user.GEB_Epos, user.Rol_ID, isAktief);
    });
  }

  /** Build the Aktief/Nie-Aktief status badge vanaf die Is_Aktief veld. */
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
  function applyUserFilter() {
    console.log('applyUserFilter running');
    if (!userList) return;

  const query = userSearch ? userSearch.value.trim().toLowerCase() : '';
  const roleFilter = userRoleFilter ? userRoleFilter.value : '';

  const rows = userList.querySelectorAll('.admin-user-row');

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
  function toggleKoshuisDropdown() {
    if (!studentKoshuisField) return;

    const wys = !!(newUserIsKoshuis && newUserIsKoshuis.checked &&
                   studentIsKoshuisField && studentIsKoshuisField.style.display !== 'none');
    studentKoshuisField.style.display = wys ? 'block' : 'none';
    if (!wys && newUserKoshuis) newUserKoshuis.value = '';
  }

  /** Submit new user to the backend. */
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
    if (editingUserId !== null) {
      await submitEditUser({ naam, van, epos, wagwoord, rolId, studentNr, rolNaam });
      return;
    }

    // ===== CREATE MODE =====
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
  async function submitEditUser(fields) {
    const { naam, van, epos, wagwoord, rolId, studentNr, rolNaam } = fields;

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
  async function submitDeleteUser() {
    if (!editingUserId || !window.MoonApi) return;

    const naam = ((newUserName ? newUserName.value : '') + ' ' +
                  (newUserSurname ? newUserSurname.value : '')).trim() || 'hierdie gebruiker';
    if (!confirm('Is jy seker jy wil vir ' + naam + ' skrap?')) return;

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

  // --- Venue events ---
  if (openVenueModalBtn) {
    openVenueModalBtn.addEventListener('click', openClassModal);
  }
  if (closeClassModalBtn) {
    closeClassModalBtn.addEventListener('click', closeClassModal);
  }
  if (classModalOverlay) {
    classModalOverlay.addEventListener('click', function (event) {
      if (event.target === classModalOverlay) closeClassModal();
    });
  }
  if (createClassBtn) {
    createClassBtn.addEventListener('click', function () { submitNewClass(); });
  }
  if (deleteLokaalBtn) {
    deleteLokaalBtn.addEventListener('click', function () { submitDeleteLokaal(); });
  }
  if (venueSearch) {
    venueSearch.addEventListener('input', function () {
      console.log('VENUE SEARCH FIRED');
      applyVenueFilter();
    });
}
  if (venueCampusFilter) {
    venueCampusFilter.addEventListener('change', function () {
      console.log('VENUE CAMPUS FILTER FIRED');
      applyVenueFilter();
    });
  }

  // --- Kampus events ---
  if (openKampusModalBtn) {
    openKampusModalBtn.addEventListener('click', openKampusModal);
  }
  if (closeKampusModalBtn) {
    closeKampusModalBtn.addEventListener('click', closeKampusModal);
  }
  if (kampusModalOverlay) {
    kampusModalOverlay.addEventListener('click', function (event) {
      if (event.target === kampusModalOverlay) closeKampusModal();
    });
  }
  if (createKampusBtn) {
    createKampusBtn.addEventListener('click', function () { submitNewKampus(); });
  }
  if (deleteKampusBtn) {
    deleteKampusBtn.addEventListener('click', function () { submitDeleteKampus(); });
  }
  if (kampusSearch) {
    kampusSearch.addEventListener('input', function () { applyKampusFilter(); });
  }

  // --- Koshuis events ---
  if (openKoshuisModalBtn) {
    openKoshuisModalBtn.addEventListener('click', openKoshuisModal);
  }
  if (closeKoshuisModalBtn) {
    closeKoshuisModalBtn.addEventListener('click', closeKoshuisModal);
  }
  if (koshuisModalOverlay) {
    koshuisModalOverlay.addEventListener('click', function (event) {
      if (event.target === koshuisModalOverlay) closeKoshuisModal();
    });
  }
  if (createKoshuisBtn) {
    createKoshuisBtn.addEventListener('click', function () { submitNewKoshuis(); });
  }
  if (deleteKoshuisBtn) {
    deleteKoshuisBtn.addEventListener('click', function () { submitDeleteKoshuis(); });
  }
  if (koshuisSearch) {
    koshuisSearch.addEventListener('input', function () { applyKoshuisFilter(); });
  }

  // --- User events ---
  if (openUserModalBtn) {
    openUserModalBtn.addEventListener('click', openUserModal);
  }
  if (closeUserModalBtn) {
    closeUserModalBtn.addEventListener('click', closeUserModal);
  }
  if (userModalOverlay) {
    userModalOverlay.addEventListener('click', function (event) {
      if (event.target === userModalOverlay) closeUserModal();
    });
  }
  if (createUserBtn) {
    createUserBtn.addEventListener('click', function () { submitNewUser(); });
  }
  if (deleteUserBtn) {
    deleteUserBtn.addEventListener('click', function () { submitDeleteUser(); });
  }
  if (userSearch) {
    userSearch.addEventListener('input', function () {
      console.log('USER SEARCH FIRED');
      applyUserFilter();
    });
  }
  if (userRoleFilter) {
    userRoleFilter.addEventListener('change', function () {
      console.log('ROLE FILTER FIRED');
      applyUserFilter();
    });
  }
  if (newUserRole) {
    newUserRole.addEventListener('change', toggleStudentField);
  }
  if (newUserIsKoshuis) {
    newUserIsKoshuis.addEventListener('change', toggleKoshuisDropdown);
  }


async function refreshDashboard() {
  if (!window.MoonApi || !window.MoonApi.fetchLiveDashboard) return;

  try {
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
    console.error('Dashboard kon nie laai nie:', e);
  }
}

  // =====================================================================
  //  INIT
  // =====================================================================

  document.addEventListener('DOMContentLoaded', async function () {
  await loadKampusDropdown();
  await loadRolleDropdown();

  toggleStudentField();

  await loadLokale();
  applyVenueFilter();

  await loadKoshuise();

  await loadGebruikers();
  applyUserFilter();

  await refreshDashboard();

  setInterval(refreshDashboard, 5000);

  });
})();
