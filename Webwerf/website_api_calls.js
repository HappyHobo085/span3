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

    // Plaaslike ontwikkeling gebruik poort 8000; andersins die Railway-bediener
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

  };

})();


