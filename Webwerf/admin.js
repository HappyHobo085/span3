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
    row.appendChild(nameSpan);
    row.appendChild(badge);
    venueList.appendChild(row);
  }

  function applyVenueFilter() {
    if (!venueList) return;

    const query = venueSearch ? venueSearch.value.trim().toLowerCase() : '';
    const campusFilter = venueCampusFilter ? venueCampusFilter.value : '';
    const rows = venueList.querySelectorAll('.admin-venue-row');

    rows.forEach(function (row) {
      const name = (row.querySelector('.admin-venue-name') || {}).textContent || '';
      const matchesSearch = query === '' || name.toLowerCase().includes(query);
      const matchesCampus = campusFilter === '' || row.dataset.kampusId === campusFilter;
      row.hidden = !(matchesSearch && matchesCampus);
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

  function openUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.add('open');
    userModalOverlay.setAttribute('aria-hidden', 'false');
  }

  function closeUserModal() {
    if (!userModalOverlay) return;
    userModalOverlay.classList.remove('open');
    userModalOverlay.setAttribute('aria-hidden', 'true');
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
      addUserRow(user.GEB_Naam, user.GEB_Van, user.GEB_Epos, user.Rol_ID);
    });
  }

  /** Create a user row in the list. */
  function addUserRow(naam, van, epos, rolId) {
    if (!userList) return;

    const row = document.createElement('div');
    row.className = 'admin-user-row';

    const infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    nameDiv.textContent = naam + ' ' + van;

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

    // Store rol ID for filtering
    row.dataset.rolId = String(rolId);

    row.appendChild(infoDiv);
    row.appendChild(rolesDiv);
    userList.appendChild(row);
  }

  /** Filter user list by search text and role dropdown. */
  function applyUserFilter() {
    if (!userList) return;

    const query = userSearch ? userSearch.value.trim().toLowerCase() : '';
    const roleFilter = userRoleFilter ? userRoleFilter.value : '';
    const rows = userList.querySelectorAll('.admin-user-row');

    rows.forEach(function (row) {
      const name = (row.querySelector('.admin-user-name') || {}).textContent || '';
      const email = (row.querySelector('.admin-user-email') || {}).textContent || '';
      const text = (name + ' ' + email).toLowerCase();
      const matchesSearch = query === '' || text.includes(query);
      const matchesRole = roleFilter === '' || row.dataset.rolId === roleFilter;
      row.hidden = !(matchesSearch && matchesRole);
    });
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

    if (!naam || !van || !epos || !wagwoord || !rolId) {
      alert('Voltooi asseblief alle verpligte velde.');
      return;
    }

    // Use studentenommer as ID_Nommer if student, otherwise use email as fallback
    const selected = newUserRole.options[newUserRole.selectedIndex];
const rolNaam = selected ? selected.dataset.rolNaam : '';

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
      closeUserModal();
      // Clear form
      if (newUserName) newUserName.value = '';
      if (newUserSurname) newUserSurname.value = '';
      if (newUserEmail) newUserEmail.value = '';
      if (newUserStudentNr) newUserStudentNr.value = '';
      if (newUserPassword) newUserPassword.value = '';
      if (newUserRole) newUserRole.value = '';
      if (studentNumberField) studentNumberField.style.display = 'none';

      // Add new user to the list immediately
      addUserRow(naam, van, epos, rolId);
    } else {
      alert((json && json.fout) || (json && json.detail) || 'Kon nie gebruiker skep nie.');
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
  if (venueSearch) {
    venueSearch.addEventListener('input', applyVenueFilter);
  }
  if (venueCampusFilter) {
    venueCampusFilter.addEventListener('change', applyVenueFilter);
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
    userSearch.addEventListener('input', applyUserFilter);
  }
  if (userRoleFilter) {
    userRoleFilter.addEventListener('change', applyUserFilter);
  }
  if (newUserRole) {
    newUserRole.addEventListener('change', toggleStudentField);
  }

  // =====================================================================
  //  INIT
  // =====================================================================

  document.addEventListener('DOMContentLoaded', async function () {
  await loadKampusDropdown();

  // BELANGRIK
  await loadRolleDropdown();

  toggleStudentField();

  await loadLokale();
  await loadGebruikers();
  });
})();
