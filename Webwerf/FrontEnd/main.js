// Sessie-roete en laai van die API-laag (website_api_calls.js).
// MoonApi word gestel in website_api_calls.js — hierdie lêer skakel dit in
// (reg na hierdie script-tag, met async=false) indien dit nog nie gelaai is.

(function loadWebsiteApiCalls() {
  if (typeof window.MoonApi !== 'undefined') return;
  var cur = document.currentScript;
  if (!cur || !cur.src) {
    console.error(
      '[main.js] Kan nie website_api_calls.js outomaties laai nie (geen currentScript.src). Skakel dit handmatig in HTML.'
    );
    return;
  }
  var apiSrc = cur.src.replace(/main\.js(\?[^#]*)?$/i, 'website_api_calls.js$1');
  var s = document.createElement('script');
  s.src = apiSrc;
  s.async = false;
  var parent = cur.parentNode;
  if (!parent) return;
  parent.insertBefore(s, cur.nextSibling);
})();

(function () {
  // --- SPAN-TOETSING: webwerf-sessie / redirect na login AF (aktiveer weer vir produksie) ---
  localStorage.setItem('isLoggedIn', 'true');
  // const isLoggedIn = localStorage.getItem('isLoggedIn');
  // const currentPage = window.location.pathname.split('/').pop();
  // if (!isLoggedIn && currentPage !== 'login.html') {
  //   window.location.href = 'login.html';
  // }
})();
