/**
 * website_api_calls.js — thin HTTP client for the FastAPI backend (main.py).
 *
 * Exposes window.MoonApi with:
 *   - baseUrl
 *   - fetchKampusse()
 *   - createKlas()
 */

(function () {

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
  const API_BASE_URL = getApiBaseUrl();

  /**
   * Generic API request helper
   */
  async function apiRequest(path, options = {}) {

    const token = localStorage.getItem('access_token');

    const headers = Object.assign(
      {
        'Content-Type': 'application/json',
      },
      options.headers || {}
    );

    // Only attach token if one exists
    if (token) {
      headers.Authorization = 'Bearer ' + token;
    }

    const response = await fetch(
      API_BASE_URL + path,
      Object.assign({}, options, { headers })
    );

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
  window.MoonApi = {

    baseUrl: API_BASE_URL,

    /**
     * GET /kampusse
     */
    fetchKampusse: async function () {

      const r = await apiRequest('/kampusse', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /kampusse  (slegs Admin)
     */
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
    deleteKampus: async function (kampusId) {

      const r = await apiRequest('/kampusse/' + kampusId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * DELETE /lokasies/{lokasieId}  (slegs Admin)
     */
    deleteLokasie: async function (lokasieId) {

      const r = await apiRequest('/lokasies/' + lokasieId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * DELETE /koshuise/{koshuisId}  (slegs Admin)
     */
    deleteKoshuis: async function (koshuisId) {

      const r = await apiRequest('/koshuise/' + koshuisId, {
        method: 'DELETE',
      });

      return r.body;
    },

    /**
     * GET /koshuise
     */
    fetchKoshuise: async function () {

      const r = await apiRequest('/koshuise', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /koshuise  (slegs Admin)
     */
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
    fetchLokasies: async function () {

      const r = await apiRequest('/lokasies', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /rolle
     */
    fetchRolle: async function () {

      const r = await apiRequest('/rolle', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /gebruikers
     */
    fetchGebruikers: async function () {

      const r = await apiRequest('/gebruikers', {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * GET /gebruikers/{userId}
     */
    fetchGebruiker: async function (userId) {

      const r = await apiRequest('/gebruikers/' + userId, {
        method: 'GET',
      });

      return r.body;
    },

    /**
     * POST /gebruikers
     */
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
    fetchKoshuisStatus: async function (koshuisId) {
      const r = await apiRequest('/koshuise/' + koshuisId + '/status', {
        method: 'GET',
      });
      return r.body;
    },

  };

})();


