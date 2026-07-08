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

  // ===== KAMPUS DOM NODES =====
  const kampusList = document.getElementById('kampus-list');
  const openKampusModalBtn = document.getElementById('open-create-kampus-modal');
  const kampusModalOverlay = document.getElementById('createKampusModal');
  const closeKampusModalBtn = document.getElementById('close-create-kampus-modal');
  const createKampusBtn = document.getElementById('create-kampus-btn');
  const newKampusName = document.getElementById('new-kampus-name');

  // ===== USER DOM NODES =====
  const userList = document.getElementById('user-list');
  const userSearch = document.getElementById('user-search');
  const userRoleFilter = document.getElementById('user-role-filter');
  const openUserModalBtn = document.getElementById('open-create-user-modal');
  const userModalOverlay = document.getElementById('createUserModal');
  const closeUserModalBtn = document.getElementById('close-create-user-modal');
  const createUserBtn = document.getElementById('create-user-btn');
  const newUserName = document.getElementById('new-user-name');
  const newUserSurname = document.getElementById('new-user-surname');
  const newUserEmail = document.getElementById('new-user-email');
  const newUserStudentNr = document.getElementById('new-user-student-nr');
  const studentNumberField = document.getElementById('student-number-field');
  const newUserPassword = document.getElementById('new-user-password');
  const newUserRole = document.getElementById('new-user-role');
  const userModalTitle = document.getElementById('create-user-title');

  // Edit mode tracking: null = create, a user ID = editing that user.
  let editingUserId = null;

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

      row.appendChild(nameSpan);
      kampusList.appendChild(row);
    });
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
  }

  /** Submit new kampus to the backend (POST /kampusse). */
  async function submitNewKampus() {
    const naam = newKampusName ? newKampusName.value.trim() : '';

    if (!naam) {
      alert('Voer asseblief die kampusnaam in.');
      return;
    }

    const json = await window.MoonApi.createKampus({ KAM_Naam: naam });

    if (json && json.sukses) {
      alert('Kampus suksesvol geskep.');
      closeKampusModal();
      // Herlaai sodat die lys én die kampus-dropdowns die nuwe kampus wys.
      await loadKampusDropdown();
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie kampus skep nie.');
    }
  }

  async function loadLokale() {
    if (!venueList || !window.MoonApi) return;

    const json = await window.MoonApi.fetchLokasies();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    venueList.innerHTML = '';
    json.data.forEach(function (lok) {
      addVenueRow(lok.LOK_Naam, lok.Kampus_ID);
    });
  }

  function addVenueRow(name, kampusId) {
    if (!venueList) return;

    const row = document.createElement('div');
    row.className = 'admin-venue-row';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'admin-venue-name';
    nameSpan.textContent = name;

    const badge = document.createElement('span');
    badge.className = 'campus-badge';
    badge.textContent = kampusMap[String(kampusId)] || 'Onbekend';

    row.dataset.kampusId = String(kampusId);
    row.dataset.name = name.toLowerCase();
    row.appendChild(nameSpan);
    row.appendChild(badge);
    venueList.appendChild(row);
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
}

  async function submitNewClass() {
    const roomName = classRoomName ? classRoomName.value.trim() : '';
    const kampusId = classKampus ? Number(classKampus.value) : null;

    if (!roomName || !kampusId) {
      alert('Voltooi asseblief die klaskamer naam en kampus.');
      return;
    }

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
      classRoomName.value = '';
      classKampus.value = '';
      addVenueRow(roomName, kampusId);
    } else {
      alert((json && json.fout) || 'Kon nie lokaal skep nie.');
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
    if (studentNumberField) studentNumberField.style.display = 'none';

    if (userModalTitle) userModalTitle.textContent = 'Skep Gebruiker';
    if (createUserBtn) createUserBtn.textContent = 'Skep';
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
    toggleStudentField();
    if (newUserStudentNr) newUserStudentNr.value = user.STU_Nommer || '';

    if (userModalTitle) userModalTitle.textContent = 'Wysig Gebruiker';
    if (createUserBtn) createUserBtn.textContent = 'Stoor Veranderinge';

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
      // 'n Gebruiker is "Aktief" sodra daar 'n NFC-tag aan sy profiel gekoppel is.
      const hetNfc = Boolean(user.NFC_UID);
      addUserRow(user.Gebruiker_ID, user.GEB_Naam, user.GEB_Van, user.GEB_Epos, user.Rol_ID, hetNfc);
    });
  }

  /** Build the Aktief/Nie-Aktief status badge (aktief = NFC-tag gekoppel). */
  function buildStatusBadge(hetNfc) {
    const badge = document.createElement('span');
    badge.className = 'status-badge ' + (hetNfc ? 'status-badge--active' : 'status-badge--inactive');

    const dot = document.createElement('span');
    dot.className = 'status-dot';
    badge.appendChild(dot);
    badge.appendChild(document.createTextNode(hetNfc ? 'Aktief' : 'Nie-Aktief'));

    return badge;
  }

  /** Create a user row in the list. */
  function addUserRow(userId, naam, van, epos, rolId, hetNfc) {
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
    nameDiv.appendChild(buildStatusBadge(hetNfc));

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

  capUserListHeight();
}

  /** Cap the user list at 5 visible rows; more than that scrolls inside the list. */
  function capUserListHeight() {
    if (!userList) return;

    const visible = Array.prototype.filter.call(
      userList.querySelectorAll('.admin-user-row'),
      function (row) { return row.style.display !== 'none'; }
    );

    if (visible.length > 5) {
      const first = visible[0].getBoundingClientRect();
      const fifth = visible[4].getBoundingClientRect();
      userList.style.maxHeight = (fifth.bottom - first.top) + 'px';
    } else {
      userList.style.maxHeight = '';
    }
  }

  /** Show/hide the studentenommer field based on selected role. */
  function toggleStudentField() {
  if (!newUserRole || !studentNumberField) return;

  const selected = newUserRole.options[newUserRole.selectedIndex];
  const rolNaam = selected ? selected.dataset.rolNaam : '';

  studentNumberField.style.display =
  rolNaam === 'Student'
    ? 'block'
    : 'none';
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

  payload.GEB_ID_Nommer = studentNr;
  payload.STU_Nommer = studentNr;
}

else if (rolNaam === 'Personeel') {
  const perNr = prompt('Voer personeelnommer in');

  if (!perNr) {
    alert('Personeelnommer is verpligtend');
    return;
  }

  payload.GEB_ID_Nommer = perNr;
  payload.PER_Nommer = perNr;
}

else if (rolNaam === 'Sekuriteit_Wag') {
  const sekNr = prompt('Voer wagnommer in');

  if (!sekNr) {
    alert('Wagnommer is verpligtend');
    return;
  }

  payload.GEB_ID_Nommer = sekNr;
  payload.SEK_Nommer = sekNr;
}

else if (rolNaam === 'Kampus_Opsigter') {
  const kamoNr = prompt('Voer opsigternommer in');

  if (!kamoNr) {
    alert('Opsigternommer is verpligtend');
    return;
  }

  payload.GEB_ID_Nommer = kamoNr;
  payload.KAMO_Nommer = kamoNr;
}

else {
  payload.GEB_ID_Nommer = epos;
}

const json = await window.MoonApi.createGebruiker(payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol geskep.');
      const nuweId = json.data ? json.data.Gebruiker_ID : null;
      closeUserModal(); // also resets the form back to create mode

      // Add new user to the list immediately (nog geen NFC-tag → Nie-Aktief)
      addUserRow(nuweId, naam, van, epos, rolId, false);
      capUserListHeight();
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
      payload.STU_Nommer = studentNr;
    }

    const json = await window.MoonApi.updateGebruiker(editingUserId, payload);

    if (json && json.sukses) {
      alert('Gebruiker suksesvol opgedateer.');
      const data = json.data || {};
      updateUserRow(editingUserId, {
        naam: data.GEB_Naam || naam,
        van: data.GEB_Van || van,
        epos: data.GEB_Epos || epos,
        rolId: data.Rol_ID || rolId,
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

    row.dataset.rolId = String(info.rolId);
    row.dataset.search = `${info.naam} ${info.van} ${info.epos}`.toLowerCase();
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

  // =====================================================================
  //  INIT
  // =====================================================================

  document.addEventListener('DOMContentLoaded', async function () {
  await loadKampusDropdown();
  await loadRolleDropdown();

  toggleStudentField();

  await loadLokale();
  applyVenueFilter();

  await loadGebruikers();
  applyUserFilter();
  });
})();
