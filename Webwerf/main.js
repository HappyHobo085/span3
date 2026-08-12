// =============================================================================
// main.js — Hierdie lêer word op al die blaaie van die webwerf gebruik.
// Dit maak seker die gebruiker is ingeteken, laai die API-lêer,
// en wys ekstra skakels in die balk bo net vir admin- en personeel-gebruikers.
// =============================================================================

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
 * Part 5 — Personeel gate + nav link:
 *   personeel.html is only for the Personeel role; a "My Klasse" navbar link
 *   is added dynamically for Personeel users only.
 */

// -----------------------------------------------------------------------------
// Sessie-roete en laai van die API-laag (website_api_calls.js).
// MoonApi word gestel in website_api_calls.js — hierdie lêer skakel dit in
// (reg na hierdie script-tag, met async=false) indien dit nog nie gelaai is.
// -----------------------------------------------------------------------------
// Hierdie funksie begin dadelik en laai die API-lêer (website_api_calls.js)
// as dit nog nie gelaai is nie, sodat die blad met die bediener kan praat.
(function loadWebsiteApiCalls() {
  // As die API-lêer reeds gelaai is, hoef ons niks te doen nie
  // Already loaded (e.g. manual script tag in HTML) — nothing to do
  if (typeof window.MoonApi !== 'undefined') return;

  // Kry die huidige script-element sodat ons weet waar main.js vandaan kom
  var cur = document.currentScript;
  if (!cur || !cur.src) {
    // Foutboodskap: ons kan nie uitwerk waar die API-lêer is nie
    console.error(
      '[main.js] Kan nie website_api_calls.js outomaties laai nie (geen currentScript.src). Skakel dit handmatig in HTML.'
    );
    return;
  }

  // Bou die adres van die API-lêer: dieselfde plek as main.js, net 'n ander naam
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
// Shared site header loader
// -----------------------------------------------------------------------------
function loadSiteHeader() {
  var placeholder = document.getElementById('site-header');
  if (!placeholder) return Promise.resolve();

  return fetch('header.html', { cache: 'no-cache' })
    .then(function (response) {
      if (!response.ok) throw new Error('Header fetch failed: ' + response.status);
      return response.text();
    })
    .then(function (html) {
      placeholder.innerHTML = html;
      setActiveNavLink();
      window.dispatchEvent(new Event('siteHeaderReady'));
    })
    .catch(function (error) {
      console.error('[main.js] header load error', error);
    });
}

function onSiteHeaderReady(callback) {
  if (document.querySelector('.navbar')) {
    callback();
    return;
  }

  window.addEventListener('siteHeaderReady', function handle() {
    window.removeEventListener('siteHeaderReady', handle);
    callback();
  });
}

function setActiveNavLink() {
  var currentPage = window.location.pathname.split('/').pop();
  var activeMap = {
    'home.html': 'Tuis',
    'kampus.html': 'Kampus',
    'koshuis.html': 'Koshuis',
    'events.html': 'Events',
    'admin.html': 'Admin',
    'personeel.html': 'My Klasse'
  };
  var activeText = activeMap[currentPage];
  if (!activeText) return;

  var navbar = document.querySelector('.navbar');
  if (!navbar) return;

  navbar.querySelectorAll('a').forEach(function (link) {
    link.classList.remove('active');
  });

  var link = Array.from(navbar.querySelectorAll('a')).find(function (a) {
    return a.textContent.trim() === activeText;
  });
  if (link) link.classList.add('active');
}

function insertNavLink(href, text) {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;
  if (navbar.querySelector('a[href="' + href + '"]')) return;

  var link = document.createElement('a');
  link.href = href;
  link.textContent = text;

  var navRight = navbar.querySelector('.navbar-right');
  if (navRight) {
    navbar.insertBefore(link, navRight);
  } else {
    navbar.appendChild(link);
  }

  setActiveNavLink();
}

loadSiteHeader();

// -----------------------------------------------------------------------------
// Login gate + Admin gate + Admin nav link
// -----------------------------------------------------------------------------
// Hierdie funksie begin dadelik en werk soos 'n hek: dit kyk of die gebruiker
// ingeteken is en of hy/sy die regte rol het om die huidige blad te sien.
(function () {
  // Kyk in die blaaier se stoorplek of die gebruiker ingeteken is
  var isLoggedIn = localStorage.getItem('isLoggedIn');
  var currentPage = window.location.pathname.split('/').pop();

  // As die gebruiker nie ingeteken is nie, stuur hom/haar na die inteken-blad
  // If not logged in, redirect to login
  if (!isLoggedIn && currentPage !== 'login.html') {
    window.location.href = 'login.html';
    return;
  }

  // Kry die gebruiker se rol (bv. Administrateur, Personeel of Student)
  var userRole = localStorage.getItem('user_role') || '';

  // Studente mag nie die website gebruik nie.
// Hulle gebruik slegs die Flutter app.
if (userRole === 'Student' && currentPage !== 'login.html') {
  alert('Studente gebruik asseblief die Moon Flutter app.');
  logOut();
  return;
}

  // As iemand wat nie 'n admin is nie die admin-blad probeer oopmaak,
  // stuur ons hom/haar stilweg terug na die tuisblad
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

  // Wys die "Admin" skakel in die balk bo, maar net vir admin-gebruikers
  // Show the Admin nav link only for admin users
  if (userRole === 'Administrateur' && currentPage !== 'login.html') {
    onSiteHeaderReady(function () {
      insertNavLink('admin.html', 'Admin');
    });
  }

  // Wys die "My Klasse" skakel in die balk bo, maar net vir personeel
  // Show the "My Klasse" nav link only for Personeel users
  if (userRole === 'Personeel' && currentPage !== 'login.html') {
    onSiteHeaderReady(function () {
      insertNavLink('personeel.html', 'My Klasse');
    });
  }
})();

// Hierdie funksie teken die gebruiker uit: dit vee die gestoorde inteken-inligting
// uit en stuur die gebruiker terug na die inteken-blad.
function logOut() {
  // Vee al die gestoorde inteken-inligting uit die blaaier se stoorplek
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  // Stuur die gebruiker na die inteken-blad
  window.location.href = 'login.html';
}
