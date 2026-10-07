// =============================================================================
// main.js — Hierdie lêer word op al die blaaie van die webwerf gebruik.
// Dit maak seker die gebruiker is ingeteken, laai die API-lêer,
// bou die sybalk-navigasie en wys ekstra skakels net vir die regte rolle.
// =============================================================================

/**
 * main.js — shared bootstrap for every page that includes it (except login-only flows).
 *
 * Part 1 — API script loader:
 *   Ensures website_api_calls.js runs after this tag so `window.MoonApi` exists.
 * Part 2 — Shared shell loader:
 *   Injects header.html (sidebar + topbar) into #site-header and wires the
 *   mobile menu button, the active nav link and the topbar title.
 * Part 3 — Login gate:
 *   If the user is not marked logged in, force redirect to login.html.
 * Part 4 — Role gates + role-based nav:
 *   admin.html only for Administrateur; personeel.html only for Personeel;
 *   Personeel see only Tuis + My Klasse; Students are blocked entirely.
 */

// -----------------------------------------------------------------------------
// Laai die API-laag (website_api_calls.js) as dit nog nie gelaai is nie.
// -----------------------------------------------------------------------------
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
  s.async = false; // Run API file before any following scripts
  var parent = cur.parentNode;
  if (!parent) return;
  parent.insertBefore(s, cur.nextSibling);
})();

// -----------------------------------------------------------------------------
// Gedeelde raamwerk (sybalk + boonste balk)
// -----------------------------------------------------------------------------
var PAGE_TITLES = {
  'home.html': 'Oorsig',
  'kampus.html': 'Kampus',
  'koshuis.html': 'Koshuis',
  'events.html': 'Events',
  'admin.html': 'Admin',
  'personeel.html': 'My Klasse',
  'verslag.html': 'Verslag'
};

// Vriendelike name vir die rol-plakkertjie in die sybalk.
var ROL_VERTOON = {
  'Administrateur': 'Administrateur',
  'Personeel': 'Personeel',
  'Kampus_Opsigter': 'Kampus Opsigter',
  'Sekuriteit_Wag': 'Sekuriteitswag'
};

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
      setTopbarTitle();
      setSidebarRole();
      wireMobileMenu();
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

function currentPageName() {
  return window.location.pathname.split('/').pop() || 'home.html';
}

function setActiveNavLink() {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;

  var page = currentPageName();
  navbar.querySelectorAll('a').forEach(function (link) {
    link.classList.toggle('active', link.getAttribute('href') === page);
  });
}

function setTopbarTitle() {
  var titleEl = document.getElementById('topbar-title');
  if (!titleEl) return;
  titleEl.textContent = PAGE_TITLES[currentPageName()] || 'MOON';
}

function setSidebarRole() {
  var roleEl = document.getElementById('sidebar-role');
  if (!roleEl) return;
  var rol = localStorage.getItem('user_role') || '';
  roleEl.textContent = ROL_VERTOON[rol] || rol || 'Aangemeld';
}

function wireMobileMenu() {
  var btn = document.getElementById('menu-btn');
  var sidebar = document.getElementById('app-sidebar');
  var scrim = document.getElementById('sidebar-scrim');
  if (!btn || !sidebar) return;

  function setOpen(open) {
    sidebar.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  btn.addEventListener('click', function () {
    setOpen(!sidebar.classList.contains('open'));
  });
  if (scrim) scrim.addEventListener('click', function () { setOpen(false); });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') setOpen(false);
  });
}

// Ikone vir skakels wat per rol bygevoeg word.
var NAV_ICONS = {
  'admin.html': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M8 1.5 13.5 4v4c0 3.2-2.3 5.6-5.5 6.5C4.8 13.6 2.5 11.2 2.5 8V4L8 1.5Z"/><path d="M5.8 8l1.5 1.5L10.4 6.4"/></svg>',
  'personeel.html': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2.5 3.5h4.2c.7 0 1.3.6 1.3 1.3V14c0-.7-.6-1.3-1.3-1.3H2.5V3.5ZM13.5 3.5H9.3c-.7 0-1.3.6-1.3 1.3V14c0-.7.6-1.3 1.3-1.3h4.2V3.5Z"/></svg>'
};

function insertNavLink(href, text) {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;
  if (navbar.querySelector('a[href="' + href + '"]')) return;

  var link = document.createElement('a');
  link.href = href;
  if (NAV_ICONS[href]) link.innerHTML = NAV_ICONS[href];
  link.appendChild(document.createTextNode(text));
  navbar.appendChild(link);

  setActiveNavLink();
}

// Hierdie funksie haal 'n skakel uit die sybalk (bv. blaaie wat 'n
// sekere rol nie mag sien nie).
function removeNavLink(href) {
  var navbar = document.querySelector('.navbar');
  if (!navbar) return;
  var link = navbar.querySelector('a[href="' + href + '"]');
  if (link) link.remove();
}

loadSiteHeader();

// Multi-role helper: check if the current user has a specific role.
// Faal toe (fail-closed): as user_roles korrup of ongeldig is, behandel ons
// die gebruiker as rolloos sodat die hekke TOE bly in plaas van oop te breek.
function hasRole(roleName) {
  try {
    var roles = JSON.parse(localStorage.getItem('user_roles') || '[]');
    return Array.isArray(roles) && roles.indexOf(roleName) !== -1;
  } catch (err) {
    return false;
  }
}

// -----------------------------------------------------------------------------
// Login gate + rol-hekke + rol-gebaseerde navigasie
// -----------------------------------------------------------------------------
(function () {
  var isLoggedIn = localStorage.getItem('isLoggedIn');
  var currentPage = currentPageName();

  // As die gebruiker nie ingeteken is nie, stuur hom/haar na die inteken-blad
  if (!isLoggedIn && currentPage !== 'login.html') {
    window.location.href = 'login.html';
    return;
  }

  // 'n Vervalle (of ontbrekende) aanmeldbewys: gaan terug na die inteken-blad
  // met 'n boodskap, eerder as dat elke bediener-oproep met 401 misluk.
  if (currentPage !== 'login.html' && tokenHetVerval()) {
    logOut('verval');
    return;
  }

  // Rolle word via hasRole() hieronder getoets (sien user_roles array in localStorage)

  // Studente mag nie die website gebruik nie.
// Hulle gebruik slegs die Flutter app.
// LET WEL: 'n gebruiker met 'n Student-rol SAAM met 'n personeelrol
// (Administrateur, Personeel, Kampus_Opsigter of Sekuriteit_Wag) is wel Welkom
// op die website — slegs suiwer studente word hier uitgekeer.
var isSuwerStudent = hasRole('Student')
  && !hasRole('Administrateur')
  && !hasRole('Personeel')
  && !hasRole('Kampus_Opsigter')
  && !hasRole('Sekuriteit_Wag');
if (isSuwerStudent && currentPage !== 'login.html') {
  alert('Studente gebruik asseblief die Moon Flutter app.');
  logOut();
  return;
}

  // As iemand wat nie 'n admin is nie die admin-blad probeer oopmaak,
  // stuur ons hom/haar stilweg terug na die tuisblad
  // Silently redirect non-admins away from admin.html
  if (currentPage === 'admin.html' && !hasRole('Administrateur')) {
    window.location.href = 'home.html';
    return;
  }

  // Silently redirect non-personeel away from personeel.html.
  // Slegs die Personeel-rol (nie Admin, Sekuriteit_Wag of Kampus_Opsigter nie)
  // mag die klas-bywoning blad sien.
  if (currentPage === 'personeel.html' && !hasRole('Personeel')) {
    window.location.href = 'home.html';
    return;
  }

  // Die Verslag-blad is net vir Administrateur, Personeel en Kampus_Opsigter.
  if (currentPage === 'verslag.html' && !magVerslagUitvoer()) {
    window.location.href = 'home.html';
    return;
  }

  // Wys die "Admin" skakel in die balk bo, maar net vir admin-gebruikers
  // Show the Admin nav link only for admin users
  if (hasRole('Administrateur') && currentPage !== 'login.html') {
    onSiteHeaderReady(function () {
      insertNavLink('admin.html', 'Admin');
    });
  }

  // Wys die "My Klasse" skakel in die balk bo, maar net vir personeel.
  // As die gebruiker slegs Personeel-rol het (nie Admin, Kampus_Opsigter
  // of Sekuriteit_Wag nie), verwyder die Kampus-, Koshuis- en Events-skakels.
  // Show the "My Klasse" nav link for Personeel users
  if (hasRole('Personeel') && currentPage !== 'login.html') {
    onSiteHeaderReady(function () {
      // Only strip nav links if user is ONLY Personeel — not if they also
      // have Admin, Kampus_Opsigter, or Sekuriteit_Wag
      var onlyPersoneel = !hasRole('Administrateur') && !hasRole('Kampus_Opsigter') && !hasRole('Sekuriteit_Wag');
      if (onlyPersoneel) {
        removeNavLink('kampus.html');
        removeNavLink('koshuis.html');
        removeNavLink('events.html');
      }
      insertNavLink('personeel.html', 'My Klasse');
    });
  }
})();

// -----------------------------------------------------------------------------
// Bywoningsverslag — knoppie in die sybalk se profielblok vir Administrateur,
// Personeel en Kampus_Opsigter. Dit maak die Verslag-blad (verslag.html) oop,
// waar die gebruiker die data sien en dit as Excel, PDF, Word of teks aflaai.
// Die bediener bepaal die omvang volgens die rol (alles / eie kampus / eie klasse).
// -----------------------------------------------------------------------------
function magVerslagUitvoer() {
  return hasRole('Administrateur') || hasRole('Personeel') || hasRole('Kampus_Opsigter');
}

function voegVerslagKnoppieBy() {
  var voet = document.querySelector('.sidebar-foot');
  if (!voet || document.getElementById('verslag-knoppie')) return;
  var skakel = document.createElement('a');
  skakel.id = 'verslag-knoppie';
  skakel.href = 'verslag.html';
  skakel.className = 'btn-outline';
  if (currentPageName() === 'verslag.html') {
    skakel.classList.add('active');
    skakel.setAttribute('aria-current', 'page');
  }
  skakel.innerHTML =
    '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">' +
    '<path d="M9 1.5H4a1.5 1.5 0 0 0-1.5 1.5v10A1.5 1.5 0 0 0 4 14.5h8a1.5 1.5 0 0 0 1.5-1.5V6L9 1.5Z"/>' +
    '<path d="M9 1.5V6h4.5M8 8v4.5M6 10.5l2 2 2-2"/></svg>' +
    '<span>Eksporteer Verslag</span>';
  var uitteken = voet.querySelector('button[onclick="logOut()"]');
  voet.insertBefore(skakel, uitteken || null);
}

if (magVerslagUitvoer() && currentPageName() !== 'login.html') {
  onSiteHeaderReady(voegVerslagKnoppieBy);
}

// Hierdie funksie teken die gebruiker uit en stuur hom/haar terug
// na die inteken-blad.
function logOut(rede) {
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_roles');
  // Stuur die gebruiker na die inteken-blad (met 'n rede as daar een is)
  window.location.href = rede ? 'login.html?rede=' + encodeURIComponent(rede) : 'login.html';
}

// Hierdie funksie kyk of die gestoorde aanmeldbewys (JWT) ontbreek of verval
// het, deur die "exp"-tyd in die token te lees. Geen token = verval.
function tokenHetVerval() {
  var token = localStorage.getItem('access_token');
  if (!token) return true;
  try {
    var base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    var padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
    var payload = JSON.parse(atob(padded));
    if (!payload.exp) return false;
    return payload.exp * 1000 <= Date.now();
  } catch (err) {
    return true;
  }
}
