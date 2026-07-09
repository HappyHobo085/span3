/**
 * main.js — shared bootstrap for every page that includes it (except login-only flows).
 *
 * Part 1 — API script loader (Afrikaans comments preserved below):
 *   Ensures website_api_calls.js runs after this tag so `window.MoonApi` exists for kampus.js.
 * Part 2 — Simple "gate":
 *   If the user is not marked logged in, force redirect to login.html (except when already there).
 * Part 3 — Admin gate:
 *   If the current page is admin.html and the user is not an Administrateur, block access.
 * Part 4 — Admin nav link:
 *   Dynamically adds an "Admin" link in the navbar for admin users only.
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
// Login gate + Admin gate + Admin nav link
// -----------------------------------------------------------------------------
(function () {
  var isLoggedIn = localStorage.getItem('isLoggedIn');
  var currentPage = window.location.pathname.split('/').pop();

  // If not logged in, redirect to login
  if (!isLoggedIn && currentPage !== 'login.html') {
    window.location.href = 'login.html';
    return;
  }

  var userRole = localStorage.getItem('user_role') || '';

  // Studente mag nie die website gebruik nie.
// Hulle gebruik slegs die Flutter app.
if (userRole === 'Student' && currentPage !== 'login.html') {
  alert('Studente gebruik asseblief die Moon Flutter app.');
  logOut();
  return;
}

  // Silently redirect non-admins away from admin.html
  if (currentPage === 'admin.html' && userRole !== 'Administrateur') {
    window.location.href = 'home.html';
    return;
  }

  // Silently redirect non-personeel away from personeel.html.
  // Slegs die Personeel-rol (nie Admin, Sekuriteit_Wag of Kampus_Opsigter nie)
  // mag die klas-bywoning blad sien.
  if (currentPage === 'personeel.html' && userRole !== 'Personeel') {
    window.location.href = 'home.html';
    return;
  }

  // Show the Admin nav link only for admin users
  if (userRole === 'Administrateur' && currentPage !== 'login.html') {
    document.addEventListener('DOMContentLoaded', function () {
      var navbar = document.querySelector('.navbar');
      if (!navbar) return;

      // Don't add if already present (e.g. on admin.html itself)
      if (navbar.querySelector('a[href="admin.html"]')) return;

      var adminLink = document.createElement('a');
      adminLink.href = 'admin.html';
      adminLink.textContent = 'Admin';

      // Insert before navbar-right if it exists, otherwise append to end of navbar
      var navRight = navbar.querySelector('.navbar-right');
      if (navRight) {
        navbar.insertBefore(adminLink, navRight);
      } else {
        navbar.appendChild(adminLink);
      }
    });
  }

  // Show the "My Klasse" nav link only for Personeel users
  if (userRole === 'Personeel' && currentPage !== 'login.html') {
    document.addEventListener('DOMContentLoaded', function () {
      var navbar = document.querySelector('.navbar');
      if (!navbar) return;

      // Don't add if already present (e.g. on personeel.html itself)
      if (navbar.querySelector('a[href="personeel.html"]')) return;

      var personeelLink = document.createElement('a');
      personeelLink.href = 'personeel.html';
      personeelLink.textContent = 'My Klasse';

      var navRight = navbar.querySelector('.navbar-right');
      if (navRight) {
        navbar.insertBefore(personeelLink, navRight);
      } else {
        navbar.appendChild(personeelLink);
      }
    });
  }
})();

function logOut() {
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  window.location.href = 'login.html';
}
