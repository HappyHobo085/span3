// Sentrale plek vir API-roetes na die FastAPI-backend (main.py).
// Die token vir beskermde roetes word verwag in localStorage onder sleutel "access_token"
// (bv. ná werklike OAuth login met POST /token).

(function () {
  const isLoggedIn = localStorage.getItem('isLoggedIn');
  const currentPage = window.location.pathname.split('/').pop();

  if (!isLoggedIn && currentPage !== 'login.html') {
    window.location.href = 'login.html';
  }
})();

(function () {
  const API_BASE_URL =
    localStorage.getItem('apiBaseUrl') || 'http://127.0.0.1:8000';

  /**
   * Maak 'n fetch na die backend en parse JSON (APIResponse-formaat).
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

    const res = await fetch(API_BASE_URL + path, Object.assign({}, options, { headers }));
    const body = await res.json().catch(function () {
      return {};
    });
    return { ok: res.ok, status: res.status, body: body };
  }

  /**
   * Globale API vir ander bladsye (bv. kampus.js).
   */
  window.MoonApi = {
    baseUrl: API_BASE_URL,

    /** Kry lys kampusse (openbare roete op backend). */
    fetchKampusse: async function () {
      const r = await apiRequest('/kampusse', { method: 'GET' });
      return r.body;
    },

    /**
     * Skep nuwe klas: stoor naam, beskrywing, NFC vir saal in databasis via POST /klasse.
     * Vereis admin-token (dieselfde as /lokasies).
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
