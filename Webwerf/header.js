// =============================================================================
// header.js — Die gedeelde navigasie-balk (header) vir al die bladsye.
// Sit <script src="header.js"></script> bo-aan die <body> waar die balk
// moet verskyn — die balk word dadelik op daardie plek ingevoeg.
//
// Die lêer doen drie dinge:
//   1. Bou die navigasie-balk met al die skakels en die "Teken Uit" knoppie.
//   2. Merk die skakel van die huidige blad as "active".
//   3. Voeg die rol-gebaseerde skakels by: "Admin" net vir Administrateurs
//      en "My Klasse" net vir Personeel (rol kom uit localStorage).
// =============================================================================
(function () {
  // Watter blad is tans oop? (bv. "kampus.html")
  var page = window.location.pathname.split('/').pop() || 'index.html';

  // Kry die gebruiker se rol uit die blaaier se stoorplek
  var role = localStorage.getItem('user_role') || '';

  // Die skakels wat op elke blad gewys word
  var links = [
    { href: 'home.html',    teks: 'Tuis' },
    { href: 'kampus.html',  teks: 'Kampus' },
    { href: 'koshuis.html', teks: 'Koshuis' },
    { href: 'events.html',  teks: 'Events' }
  ];

  // Rol-gebaseerde skakels: net vir die regte rolle
  if (role === 'Administrateur') links.push({ href: 'admin.html', teks: 'Admin' });
  if (role === 'Personeel') links.push({ href: 'personeel.html', teks: 'My Klasse' });

  // Bou die HTML van die balk
  var html = '<nav class="navbar">' +
    '<a href="home.html" class="navbar-logo" aria-label="MOON">MOON</a>';
  links.forEach(function (l) {
    html += '<a href="' + l.href + '"' +
      (page === l.href ? ' class="active"' : '') + '>' + l.teks + '</a>';
  });
  html += '<div class="navbar-right">' +
    '<button class="btn-outline" type="button" onclick="logOut()">Teken Uit</button>' +
    '</div></nav>';

  // Voeg die balk in presies waar hierdie script-tag in die HTML sit
  var cur = document.currentScript;
  if (cur) cur.insertAdjacentHTML('beforebegin', html);
})();
