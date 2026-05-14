/**
 * website_api_calls.js — thin HTTP client for the FastAPI backend (main.py).
 *
 * Exposes window.MoonApi with:
 *   - baseUrl (from localStorage 'apiBaseUrl' or default localhost:8000)
 *   - fetchKampusse()  → GET /kampusse
 *   - createKlas(...) → POST /klasse
 *
 * Usually injected automatically by main.js right after the main.js script tag.
 * You may also include this file explicitly in HTML before main.js if you prefer.
 */
(function () {
  // Backend root; change in DevTools: localStorage.setItem('apiBaseUrl', 'http://...')
  const API_BASE_URL =
    localStorage.getItem('apiBaseUrl') || 'http://127.0.0.1:8000';

  /**
   * Maak 'n fetch na die backend en parse JSON (APIResponse-formaat).
   * Performs one HTTP request, attaches JSON + Bearer token when present, returns parsed body.
   * @param {string} path bv. '/kampusse'
   * @param {RequestInit} options fetch-opsies (method, body, ens.)
   * @returns {Promise<{ ok: boolean, status: number, body: object }>}
   */
  async function apiRequest(path, options) {
    const token = localStorage.getItem('access_token');
    const headers = Object.assign(
      { 'Content-Type': 'application/json' },
      (options && options.headers) || {}
    );
    if (token) {
      headers.Authorization = 'Bearer ' + token;
    }

    const res = await fetch(
      API_BASE_URL + path,
      Object.assign({}, options, { headers })
    );
    // Non-JSON responses become {} so callers can still read .fout etc.
    const body = await res.json().catch(function () {
      return {};
    });
    return { ok: res.ok, status: res.status, body: body };
  }

  /** Public API attached to window for other scripts */
  window.MoonApi = {
    baseUrl: API_BASE_URL,

    /** Kry lys kampusse. — GET /kampusse, returns API JSON body */
    fetchKampusse: async function () {
      const r = await apiRequest('/kampusse', { method: 'GET' });
      return r.body;
    },

    /**
     * Skep nuwe klas via POST /klasse.
     * @param {{ kampus_naam: string, klas_naam: string, beskrywing?: string|null}} payload
     */
    createKlas: async function (payload) {
      const body = {
        kampus_naam: payload.kampus_naam,
        klas_naam: payload.klas_naam,
        beskrywing: payload.beskrywing || null,
      };
      const r = await apiRequest('/klasse', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      return r.body;
    },
  };
})();
