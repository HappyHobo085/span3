// Alle HTTP-roetes na die FastAPI-backend (main.py).
// Stel window.MoonApi vir bladsye soos kampus.js.
// Word gewoonlik deur main.js ingevoeg (insertBefore net na die main.js-tag);
// jy kan dit ook vóór main.js in HTML skakel as jy verkies.
(function () {
  const API_BASE_URL =
    localStorage.getItem('apiBaseUrl') || 'http://127.0.0.1:8000';

  /**
   * Maak 'n fetch na die backend en parse JSON (APIResponse-formaat).
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
    const body = await res.json().catch(function () {
      return {};
    });
    return { ok: res.ok, status: res.status, body: body };
  }

  window.MoonApi = {
    baseUrl: API_BASE_URL,

    /** Kry lys kampusse. */
    fetchKampusse: async function () {
      const r = await apiRequest('/kampusse', { method: 'GET' });
      return r.body;
    },

    /**
     * Skep nuwe klas via POST /klasse.
     * @param {{ naam: string, beskrywing?: string|null, nfc_uid: string, kampus_id?: string|number|null }} payload
     */
    createKlas: async function (payload) {
      const body = {
        naam: payload.naam,
        beskrywing: payload.beskrywing || null,
        nfc_uid: String(payload.nfc_uid).trim(),
        kampus_id:
          payload.kampus_id === '' || payload.kampus_id === undefined
            ? null
            : Number(payload.kampus_id),
      };
      const r = await apiRequest('/klasse', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      return r.body;
    },
  };
})();
