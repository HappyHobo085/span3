/**
 * main.js — shared bootstrap for every page that includes it (except login-only flows).
 *
 * Part 1 — API script loader (Afrikaans comments preserved below):
 *   Ensures website_api_calls.js runs after this tag so `window.MoonApi` exists for kampus.js.
 * Part 2 — Simple “gate”:
 *   If the user is not marked logged in, force redirect to login.html (except when already there).
 */

// -----------------------------------------------------------------------------
// Sessie-roete en laai van die API-laag (website_api_calls.js).
// MoonApi word gestel in website_api_calls.js — hierdie lêer skakel dit in
// (reg na hierdie script-tag, met async=false) indien dit nog nie gelaai is.
// -----------------------------------------------------------------------------
(function loadWebsiteApiCalls() {
  // Already loaded (e.g. manual script tag in HTML) — nothing to do
  if (typeof window.MoonApi !== 'undefined') return;

  var cur = document.currentScript;
  if (!cur || !cur.src) {
    console.error(
      '[main.js] Kan nie website_api_calls.js outomaties laai nie (geen currentScript.src). Skakel dit handmatig in HTML.'
    );
    return;
  }

  // Same folder as main.js, swap filename to website_api_calls.js (keep query string if any)
  var apiSrc = cur.src.replace(/main\.js(\?[^#]*)?$/i, 'website_api_calls.js$1');
  var s = document.createElement('script');
  s.src = apiSrc;
  s.async = false; // Run API file before any following scripts (e.g. kampus.js)
  var parent = cur.parentNode;
  if (!parent) return;
  parent.insertBefore(s, cur.nextSibling);
})();

// -----------------------------------------------------------------------------
// Login gate: reads flag set by login.js on successful demo login
// -----------------------------------------------------------------------------
(function () {
  // --- SPAN-TOETSING: webwerf-sessie / redirect na login AF (aktiveer weer vir produksie) ---
  localStorage.setItem('isLoggedIn', 'true');
  // const isLoggedIn = localStorage.getItem('isLoggedIn');
  // const currentPage = window.location.pathname.split('/').pop();
  // if (!isLoggedIn && currentPage !== 'login.html') {
  //   window.location.href = 'login.html';
  // }
})();
