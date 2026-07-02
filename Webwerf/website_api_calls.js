/**
 * website_api_calls.js — thin HTTP client for the FastAPI backend (main.py).
 *
 * Exposes window.MoonApi with:
 *   - baseUrl
 *   - fetchKampusse()
 *   - createKlas()
 */

(function () {

  // Backend URL
const API_BASE_URL =
  localStorage.getItem('apiBaseUrl') || 'http://happyhobo-pc.tail251156.ts.net:8000';

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

  };

})();


