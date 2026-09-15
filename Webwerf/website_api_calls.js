// website_api_calls.js — Hierdie lêer praat met die bediener (backend).
// Al die funksies hier stuur versoeke oor die netwerk om data te kry,
// by te voeg, te verander of uit te vee. Die res van die webwerf gebruik
// hierdie funksies deur "window.MoonApi".
/**
 * website_api_calls.js — thin HTTP client for the FastAPI backend (main.py).
 *
 * Exposes window.MoonApi with:
 *   - baseUrl
 *   - fetchKampusse()
 *   - createKlas()
 *   - rooster-helpers: getCurrentUserId(), fetchModules(), fetchGroepe(),
 *     fetchRoosterKlasse(), fetchPersoneelRooster(), fetchStudentRooster(),
 *     fetchKlasStudente(), create-/assign-toewysings, importKlasseCsv()
 */

(function () {

  // Hierdie funksie werk uit wat die bediener se adres is.
  // As daar 'n gestoorde adres is, gebruik dit; anders gebruik dit dieselfde
  // rekenaar as die webwerf, op poort 8000.
  function getApiBaseUrl() {
    const stored = localStorage.getItem('apiBaseUrl');
    if (stored) {
      return stored;
    }

    // Plaaslike ontwikkeling praat met die backend op poort 8000; enige ander
    // gasheer (bv. die Railway-webwerf) gebruik die Railway-backend.
    // Dieselfde logika as login.js — die twee MOET ooreenstem.
    const host = window.location.hostname || 'localhost';
    if (host === 'localhost' || host === '127.0.0.1') {
      const protocol = window.location.protocol || 'http:';
      return `${protocol}//${host}:8000`;
    }
    return 'https://humorous-endurance-production-ee64.up.railway.app';
  }

  // Backend URL
  // Die bediener se adres word een keer hier uitgewerk en gestoor.
  const API_BASE_URL = getApiBaseUrl();

  // Hierdie funksie kyk of die bediener die aanmeldbewys verwerp het (401).
  // As dit so is, word die sessie skoongemaak en die gebruiker na die
  // inteken-blad gestuur met 'n boodskap — in plaas daarvan dat elke bladsy
  // 'n verwarrende "Kon nie geloofsbriewe verifieer nie" wys.
  function hanteerOngemagtig(response, pathname) {
    if (!response || response.status !== 401) return false;
    if (pathname === '/token') return false; // verkeerde wagwoord, nie 'n vervalle sessie nie
    const bladsy = window.location.pathname.split('/').pop();
    if (bladsy === 'login.html') return false;
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_roles');
    window.location.href = 'login.html?rede=verval';
    return true;
  }

  /**
   * Generic API request helper
   */
  // Hierdie funksie stuur enige versoek na die bediener en gee die antwoord
  // terug. Al die ander funksies hieronder gebruik hierdie een.
  async function apiRequest(path, options = {}) {

    const token = localStorage.getItem('access_token');
    const isFormData = options.body instanceof FormData;

    // Maak die opskrifte reg: ons stuur en ontvang JSON-teks.
    const headers = Object.assign({}, options.headers || {});

    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    // Only attach token if one exists
    // Sit die aanmeld-bewys by (net as daar een is) sodat die bediener
    // weet wie die versoek stuur.
    if (token) {
      headers.Authorization = 'Bearer ' + token;
    }

    // Stuur die versoek na die bediener en wag vir die antwoord.
    const response = await fetch(
      API_BASE_URL + path,
      Object.assign({}, options, { headers })
    );

    hanteerOngemagtig(response, path);

    // Probeer die antwoord se inhoud lees; as dit nie kan nie, bly dit leeg.
    let body = {};

    try {
      body = await response.json();
    } catch (e) {
      body = {};
    }

    return {
      ok: response.ok,
      status: response.status,
      body: body,
      raw: response,
    };
  }

  /**
   * Public API
   */
  // Hier word al die funksies beskikbaar gemaak vir die res van die webwerf.
  window.MoonApi = {

    // Die bediener se adres, sodat ander lêers dit ook kan sien.
    baseUrl: API_BASE_URL,

    // Hierdie funksie roep GET /dashboard/live — dit kry die nuutste
    // syfers vir die regstreekse paneelbord (wie is nou in en uit).
    fetchLiveDashboard: async function () {
      const r = await apiRequest('/dashboard/live', {
        method: 'GET',
      });

      return r.body;
    },

    // Hierdie funksie roep GET /dashboard — dit kry die ingetekende
    // gebruiker se eie status (op kampus of nie, laaste skanderings).
    fetchMyDashboard: async function () {
      const r = await apiRequest('/dashboard', {
        method: 'GET',
      });

      return r.body;
    },

    // Hierdie funksie roep GET /toegangslogs — dit kry die nuutste
    // in- en uitskanderings (vir die Tuisblad se aktiwiteitslys).
    fetchToegangsLogs: async function () {
      const r = await apiRequest('/toegangslogs', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /kampusse
     */
    // Hierdie funksie roep GET /kampusse — dit kry die lys van al die kampusse.
    fetchKampusse: async function () {

      const r = await apiRequest('/kampusse', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /kampusse  (slegs Admin)
     */
    // Hierdie funksie roep POST /kampusse — dit stuur 'n nuwe kampus se
    // inligting sodat dit bygevoeg word (net vir Admin).
    createKampus: async function (data) {

      const r = await apiRequest('/kampusse', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * POST /klasse
     */
    // Hierdie funksie roep POST /klasse — dit stuur 'n nuwe klas se
    // inligting sodat dit bygevoeg word.
    createKlas: async function (data) {

      const r = await apiRequest('/klasse', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * PUT /kampusse/{kampusId}  (slegs Admin)
     */
    // Hierdie funksie roep PUT /kampusse/{id} — dit stuur nuwe inligting
    // om 'n bestaande kampus te verander (net vir Admin).
    updateKampus: async function (kampusId, data) {

      const r = await apiRequest('/kampusse/' + kampusId, {
        method: 'PUT',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * PUT /lokasies/{lokasieId}  (slegs Admin)
     */
    // Hierdie funksie roep PUT /lokasies/{id} — dit stuur nuwe inligting
    // om 'n bestaande plek/lokaal te verander (net vir Admin).
    updateLokasie: async function (lokasieId, data) {

      const r = await apiRequest('/lokasies/' + lokasieId, {
        method: 'PUT',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * PUT /koshuise/{koshuisId}  (slegs Admin)
     */
    // Hierdie funksie roep PUT /koshuise/{id} — dit stuur nuwe inligting
    // om 'n bestaande koshuis te verander (net vir Admin).
    updateKoshuis: async function (koshuisId, data) {

      const r = await apiRequest('/koshuise/' + koshuisId, {
        method: 'PUT',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * DELETE /kampusse/{kampusId}  (slegs Admin)
     */
    // Hierdie funksie roep DELETE /kampusse/{id} — dit vra die bediener
    // om 'n kampus uit te vee (net vir Admin).
    deleteKampus: async function (kampusId) {

      const r = await apiRequest('/kampusse/' + kampusId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * DELETE /lokasies/{lokasieId}  (slegs Admin)
     */
    // Hierdie funksie roep DELETE /lokasies/{id} — dit vra die bediener
    // om 'n plek/lokaal uit te vee (net vir Admin).
    deleteLokasie: async function (lokasieId) {

      const r = await apiRequest('/lokasies/' + lokasieId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * DELETE /koshuise/{koshuisId}  (slegs Admin)
     */
    // Hierdie funksie roep DELETE /koshuise/{id} — dit vra die bediener
    // om 'n koshuis uit te vee (net vir Admin).
    deleteKoshuis: async function (koshuisId) {

      const r = await apiRequest('/koshuise/' + koshuisId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * GET /koshuise
     */
    // Hierdie funksie roep GET /koshuise — dit kry die lys van al die koshuise.
    fetchKoshuise: async function () {

      const r = await apiRequest('/koshuise', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /koshuise  (slegs Admin)
     */
    // Hierdie funksie roep POST /koshuise — dit stuur 'n nuwe koshuis se
    // inligting sodat dit bygevoeg word (net vir Admin).
    createKoshuis: async function (data) {

      const r = await apiRequest('/koshuise', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * GET /lokasies
     */
    // Hierdie funksie roep GET /lokasies — dit kry die lys van al die
    // plekke/lokale op die kampusse.
    fetchLokasies: async function () {

      const r = await apiRequest('/lokasies', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /rolle
     */
    // Hierdie funksie roep GET /rolle — dit kry die lys van gebruikersrolle
    // (bv. Admin, Personeel, Student).
    fetchRolle: async function () {

      const r = await apiRequest('/rolle', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /gebruikers
     */
    // Hierdie funksie roep GET /gebruikers — dit kry die lys van al die gebruikers.
    fetchGebruikers: async function () {

      const r = await apiRequest('/gebruikers', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /gebruikers/{userId}
     */
    // Hierdie funksie roep GET /gebruikers/{id} — dit kry een spesifieke
    // gebruiker se inligting.
    fetchGebruiker: async function (userId) {

      const r = await apiRequest('/gebruikers/' + userId, {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /gebruikers
     */
    // Hierdie funksie roep POST /gebruikers — dit stuur 'n nuwe gebruiker
    // se inligting sodat hy/sy bygevoeg word.
    createGebruiker: async function (data) {

      const r = await apiRequest('/gebruikers', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * PUT /gebruikers/{userId}
     */
    // Hierdie funksie roep PUT /gebruikers/{id} — dit stuur nuwe inligting
    // om 'n bestaande gebruiker te verander.
    updateGebruiker: async function (userId, data) {

      const r = await apiRequest('/gebruikers/' + userId, {
        method: 'PUT',
        body: JSON.stringify(data),
      });

      return r.body;
    },

    /**
     * DELETE /gebruikers/{userId}  (slegs Admin — sagte verwydering)
     */
    // Hierdie funksie roep DELETE /gebruikers/{id} — dit vra die bediener
    // om 'n gebruiker af te skakel (net vir Admin; data word nie regtig
    // uitgevee nie, net gemerk as onaktief).
    deleteGebruiker: async function (userId) {

      const r = await apiRequest('/gebruikers/' + userId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * GET /events?view=
     * view: 'komende' (verstek), 'my' of 'vorige'.
     */
    // Hierdie funksie roep GET /events — dit kry die lys van gebeure
    // (events), verstek net dié wat nog voorlê.
    fetchEvents: async function (view) {
      const params = new URLSearchParams({ view: view || 'komende' });
      const r = await apiRequest('/events?' + params.toString(), {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * GET /events/{eventId}/rsvps
     * Gee die event se besonderhede saam met almal wat RSVP het: app-gebruikers
     * (studente/personeel) én eksterne gaste ("plus 1's" via die deel-skakel).
    * Slegs Administrateurs en Kampus_Opsigters mag dit sien (anders 403).
     */
    // Hierdie funksie roep GET /events/{id}/rsvps — dit kry die gastelys
    // van een event: wie genooi is (RSVP) en die eksterne gaste.
    fetchEventRsvps: async function (eventId) {
      const r = await apiRequest('/events/' + eventId + '/rsvps', {
        method: 'GET',
      });
      const body = r.body || {};
      if (!r.ok && body.sukses === undefined) {
        return { sukses: false, data: null, fout: body.detail || ('Fout ' + r.status), status: r.status };
      }
      if (body.status === undefined) body.status = r.status;
      return body;
    },

    /**
     * GET /kampusse/status
     * Returns summary scan counts for all campuses. No auth required.
     * Used by the Tuis dashboard (home.js) for the per-campus overview.
     */
    // Hierdie funksie roep GET /kampusse/status — dit kry 'n opsomming van
    // die skandeer-tellings vir al die kampusse.
    fetchKampusseStatus: async function () {
      const r = await apiRequest('/kampusse/status', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * GET /admin/csv/tables
     */
    fetchCsvTables: async function () {
      const r = await apiRequest('/admin/csv/tables', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * POST /admin/csv/import
     */
    importCsvTable: async function (table, file, text, mode) {
      const formData = new FormData();
      formData.append('table', table);
      formData.append('mode', mode || 'merge');

      if (file) {
        formData.append('file', file);
      }
      if (text && !file) {
        formData.append('text', text);
      }

      const token = localStorage.getItem('access_token');
      const headers = {};
      if (token) {
        headers.Authorization = 'Bearer ' + token;
      }

      const response = await fetch(API_BASE_URL + '/admin/csv/import', {
        method: 'POST',
        headers,
        body: formData,
      });
      hanteerOngemagtig(response, '/admin/csv/import');

      let body = {};
      try {
        body = await response.json();
      } catch (e) {
        body = {};
      }

      return {
        ok: response.ok,
        status: response.status,
        body,
      };
    },

    /**
     * GET /admin/csv/export?table=
     */
    exportCsvTable: async function (table) {
      const url = new URL(API_BASE_URL + '/admin/csv/export');
      url.searchParams.set('table', table);

      const token = localStorage.getItem('access_token');
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: token ? { Authorization: 'Bearer ' + token } : {},
      });
      hanteerOngemagtig(response, '/admin/csv/export');

      const text = await response.text();
      return {
        ok: response.ok,
        status: response.status,
        text,
      };
    },

    /**
     * GET /admin/csv/export-all
     * Returns a ZIP file with all tables as CSVs
     */
    exportAllCsvTables: async function () {
      const token = localStorage.getItem('access_token');
      const response = await fetch(API_BASE_URL + '/admin/csv/export-all', {
        method: 'GET',
        headers: token ? { Authorization: 'Bearer ' + token } : {},
      });
      hanteerOngemagtig(response, '/admin/csv/export-all');

      const blob = await response.blob();
      return {
        ok: response.ok,
        status: response.status,
        blob,
      };
    },

    /**
     * POST /admin/csv/import-all
     * Accepts a ZIP file with multiple CSVs
     */
    importAllCsvTables: async function (zipFile, mode) {
      const formData = new FormData();
      formData.append('file', zipFile);
      formData.append('mode', mode || 'merge');

      const token = localStorage.getItem('access_token');
      const headers = {};
      if (token) {
        headers.Authorization = 'Bearer ' + token;
      }

      const response = await fetch(API_BASE_URL + '/admin/csv/import-all', {
        method: 'POST',
        headers,
        body: formData,
      });
      hanteerOngemagtig(response, '/admin/csv/import-all');

      let body = {};
      try {
        body = await response.json();
      } catch (e) {
        body = {};
      }

      return {
        ok: response.ok,
        status: response.status,
        body,
      };
    },

    /**
     * GET /kampusse/{kampusId}/status
     * Returns detailed scanned-in/out lists for a specific campus. No auth required.
     */
    // Hierdie funksie roep GET /kampusse/{id}/status — dit kry die lyste van
    // wie by 'n spesifieke kampus in- en uitgeskandeer is.
    fetchKampusStatus: async function (kampusId) {
      const r = await apiRequest('/kampusse/' + kampusId + '/status', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * GET /koshuise/{koshuisId}/status
     * Returns detailed scanned-in/out lists for a specific koshuis. No auth required.
     */
    // Hierdie funksie roep GET /koshuise/{id}/status — dit kry die lyste van
    // wie by 'n spesifieke koshuis in- en uitgeskandeer is.
    fetchKoshuisStatus: async function (koshuisId) {
      const r = await apiRequest('/koshuise/' + koshuisId + '/status', {
        method: 'GET',
      });
      return r.body;
    },

    // =====================================================================
    //  INSTELLINGS (settings)
    // =====================================================================

    /**
     * GET /instellings
     * Returns all settings.
     */
    fetchInstellings: async function () {
      const r = await apiRequest('/instellings', { method: 'GET' });
      return r.body;
    },

    /**
     * GET /instellings/{sleutel}
     * Returns a single setting by key.
     */
    fetchInstelling: async function (sleutel) {
      const r = await apiRequest('/instellings/' + encodeURIComponent(sleutel), { method: 'GET' });
      return r.body;
    },

    /**
     * PUT /instellings/{sleutel}
     * Updates a setting value.
     */
    updateInstelling: async function (sleutel, data) {
      const r = await apiRequest('/instellings/' + encodeURIComponent(sleutel), {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      return r.body;
    },

    // =====================================================================
    //  ROOSTER (klasse / modules / groepe) — routers/klasse.py, prefix /rooster
    // =====================================================================

    /**
     * Lees die aangemelde gebruiker se Gebruiker_ID uit die JWT ("sub").
     * Gee null terug as daar geen (geldige) token is nie.
     */
    // Hierdie funksie lees die gebruiker se ID uit die gestoorde aanmeldbewys,
    // sodat bladsye soos My Klasse weet wie se rooster om te vra.
    getCurrentUserId: function () {
      const token = localStorage.getItem('access_token');
      if (!token) return null;
      try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
        const payload = JSON.parse(atob(padded));
        const id = parseInt(payload.sub, 10);
        return Number.isFinite(id) ? id : null;
      } catch (e) {
        return null;
      }
    },

    /**
     * GET /rooster/modules  (slegs Admin)
     * Alle modules: [{ Module_ID, MOD_Kode, MOD_Naam }]
     */
    fetchModules: async function () {
      const r = await apiRequest('/rooster/modules', { method: 'GET' });
      return r.body;
    },

    /**
     * GET /rooster/groepe  (slegs Admin)
     * Alle groepe: [{ Groep_ID, GRO_Naam }]
     */
    fetchGroepe: async function () {
      const r = await apiRequest('/rooster/groepe', { method: 'GET' });
      return r.body;
    },

    /**
     * GET /rooster/klasse  (slegs Admin)
     * Alle klassessies: [{ Klas_ID, Module_ID, MOD_Kode, MOD_Naam,
     *                      KLA_Lokaal, KLA_Dag, KLA_Begin_Tyd, KLA_Eind_Tyd }]
     * (Nie te verwar met fetch van /klasse in lokasie.py, wat lokale lys.)
     */
    fetchRoosterKlasse: async function () {
      const r = await apiRequest('/rooster/klasse', { method: 'GET' });
      return r.body;
    },

    /**
     * POST /rooster/modules  (slegs Admin)
     * data: { MOD_Kode, MOD_Naam? }
     */
    createModule: async function (data) {
      const r = await apiRequest('/rooster/modules', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return r.body;
    },

    /**
     * POST /rooster/groepe  (slegs Admin)
     * data: { GRO_Naam }
     */
    createGroep: async function (data) {
      const r = await apiRequest('/rooster/groepe', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return r.body;
    },

    /**
     * POST /rooster/klasse  (slegs Admin)
     * data: { Module_ID, KLA_Lokaal?, KLA_Dag?, KLA_Begin_Tyd?, KLA_Eind_Tyd? }
     */
    createRoosterKlas: async function (data) {
      const r = await apiRequest('/rooster/klasse', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return r.body;
    },

    /**
     * POST /rooster/klasse/{klasId}/groepe  (slegs Admin)
     * Koppel 'n groep aan 'n klassessie.
     */
    assignGroepToKlas: async function (klasId, groepId) {
      const r = await apiRequest('/rooster/klasse/' + encodeURIComponent(klasId) + '/groepe', {
        method: 'POST',
        body: JSON.stringify({ Groep_ID: groepId }),
      });
      return r.body;
    },

    /**
     * POST /rooster/studente/{userId}/groepe  (slegs Admin)
     */
    assignStudentGroep: async function (userId, groepId) {
      const r = await apiRequest('/rooster/studente/' + encodeURIComponent(userId) + '/groepe', {
        method: 'POST',
        body: JSON.stringify({ Groep_ID: groepId }),
      });
      return r.body;
    },

    /**
     * POST /rooster/studente/{userId}/modules  (slegs Admin)
     */
    assignStudentModule: async function (userId, moduleId) {
      const r = await apiRequest('/rooster/studente/' + encodeURIComponent(userId) + '/modules', {
        method: 'POST',
        body: JSON.stringify({ Module_ID: moduleId }),
      });
      return r.body;
    },

    /**
     * POST /rooster/studente/{userId}/klasse  (slegs Admin)
     */
    assignStudentKlas: async function (userId, klasId) {
      const r = await apiRequest('/rooster/studente/' + encodeURIComponent(userId) + '/klasse', {
        method: 'POST',
        body: JSON.stringify({ Klas_ID: klasId }),
      });
      return r.body;
    },

    /**
     * POST /rooster/personeel/{userId}/modules  (slegs Admin)
     */
    assignPersoneelModule: async function (userId, moduleId) {
      const r = await apiRequest('/rooster/personeel/' + encodeURIComponent(userId) + '/modules', {
        method: 'POST',
        body: JSON.stringify({ Module_ID: moduleId }),
      });
      return r.body;
    },

    /**
     * POST /rooster/personeel/{userId}/klasse  (slegs Admin)
     */
    assignPersoneelKlas: async function (userId, klasId) {
      const r = await apiRequest('/rooster/personeel/' + encodeURIComponent(userId) + '/klasse', {
        method: 'POST',
        body: JSON.stringify({ Klas_ID: klasId }),
      });
      return r.body;
    },

    /**
     * GET /rooster/personeel-modules  (slegs Admin)
     * Alle dosent-module-toewysings: [{ Gebruiker_ID, Module_ID, MOD_Kode, MOD_Naam }]
     */
    fetchPersoneelModuleToewysings: async function () {
      const r = await apiRequest('/rooster/personeel-modules', { method: 'GET' });
      return r.body;
    },

    /**
     * DELETE /rooster/personeel/{userId}/modules/{moduleId}  (slegs Admin)
     * Haal 'n module van 'n personeellid af.
     */
    unassignPersoneelModule: async function (userId, moduleId) {
      const r = await apiRequest(
        '/rooster/personeel/' + encodeURIComponent(userId) + '/modules/' + encodeURIComponent(moduleId),
        { method: 'DELETE' }
      );
      return r.body;
    },

    /**
     * GET /gebruikers?limit=10000
     * Alle gebruikers (die verstek-limiet van /gebruikers is 100).
     */
    fetchGebruikersAlle: async function () {
      const r = await apiRequest('/gebruikers?limit=10000', { method: 'GET' });
      return r.body;
    },

    /**
     * GET /rooster/studente-toewysings  (slegs Admin)
     * { groepe: [{ Gebruiker_ID, Groep_ID, GRO_Naam }],
     *   modules: [{ Gebruiker_ID, Module_ID, MOD_Kode, MOD_Naam }] }
     */
    fetchStudentToewysings: async function () {
      const r = await apiRequest('/rooster/studente-toewysings', { method: 'GET' });
      return r.body;
    },

    /**
     * DELETE /rooster/studente/{userId}/groepe/{groepId}  (slegs Admin)
     */
    unassignStudentGroep: async function (userId, groepId) {
      const r = await apiRequest(
        '/rooster/studente/' + encodeURIComponent(userId) + '/groepe/' + encodeURIComponent(groepId),
        { method: 'DELETE' }
      );
      return r.body;
    },

    /**
     * DELETE /rooster/studente/{userId}/modules/{moduleId}  (slegs Admin)
     */
    unassignStudentModule: async function (userId, moduleId) {
      const r = await apiRequest(
        '/rooster/studente/' + encodeURIComponent(userId) + '/modules/' + encodeURIComponent(moduleId),
        { method: 'DELETE' }
      );
      return r.body;
    },

    /**
     * POST /rooster/studente/import  (slegs Admin)
     * CSV met kop-ry: studentenommer (of epos), groep, module.
     * Meer as een groep/module per ry word met ';' geskei.
     */
    importStudentToewysingsCsv: async function (file) {
      const formData = new FormData();
      formData.append('l\u00eaer', file);
      const r = await apiRequest('/rooster/studente/import', {
        method: 'POST',
        body: formData,
      });
      return r.body;
    },

    /**
     * GET /rooster/studente/{userId}/rooster
     * Student se eie rooster (of Admin vir enige student).
     */
    fetchStudentRooster: async function (userId) {
      const r = await apiRequest('/rooster/studente/' + encodeURIComponent(userId) + '/rooster', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * GET /rooster/personeel/{userId}/rooster
     * Personeellid se eie rooster (of Admin vir enige personeellid):
     * alle klassessies (module-toewysing + direkte toewysing, gededupeer).
     */
    fetchPersoneelRooster: async function (userId) {
      const r = await apiRequest('/rooster/personeel/' + encodeURIComponent(userId) + '/rooster', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * GET /rooster/klasse/{klasId}/studente
     * Klasregister: [{ Gebruiker_ID, GEB_Naam, GEB_Van, STU_Nommer }].
     * Personeel net vir klasse op hul eie rooster; Admin vir enige klas.
     */
    fetchKlasStudente: async function (klasId) {
      const r = await apiRequest('/rooster/klasse/' + encodeURIComponent(klasId) + '/studente', {
        method: 'GET',
      });
      return r.body;
    },

    /**
     * POST /rooster/klasse/import  (slegs Admin)
     * Laai 'n Lantiv-uitvoer-CSV op; skep modules, groepe en klasse.
     */
    importKlasseCsv: async function (file) {
      const formData = new FormData();
      formData.append('l\u00eaer', file);
      const r = await apiRequest('/rooster/klasse/import', {
        method: 'POST',
        body: formData,
      });
      return r.body;
    },

  };

})();


