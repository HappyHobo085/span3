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

    const protocol = window.location.protocol || 'http:';
    const host = window.location.hostname || 'localhost';
    return `${protocol}//${host}:8000`;
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

    // Maak die opskrifte reg: ons stuur en ontvang JSON-teks.
    const headers = Object.assign(
      {
        'Content-Type': 'application/json',
      },
      options.headers || {}
    );

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
     * GET /kampusse/status
     * Returns summary scan counts for all campuses. No auth required.
     * Reserved for future use (e.g. a multi-campus overview dashboard).
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


