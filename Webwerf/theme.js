// =============================================================================
// theme.js — Lig/donker modus vir die webwerf.
// Sit <script src="theme.js"></script> in die <head> (na styles.css) sodat die
// regte tema geld voordat die blad teken (geen flits van die verkeerde tema).
//
// Wat dit doen:
//   1. Pas die gestoorde tema toe (localStorage 'theme'), of volg die toestel
//      se voorkeur as die gebruiker nog nie gekies het nie.
//   2. Voeg 'n wisselknoppie by: in die navbar se regterkant as daar een is,
//      anders swewend regs-bo (bv. op die inteken-blad).
// =============================================================================
(function () {
  var theme;

  // Pas die tema toe deur 'n attribuut op <html> te stel — styles.css se
  // html[data-theme="light"] blok doen die res.
  function applyTheme(t) {
    theme = t;
    document.documentElement.setAttribute('data-theme', t);
  }

  // Gestoorde keuse, anders die toestel se voorkeur, anders donker
  var saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  var prefersLight = window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: light)').matches;
  applyTheme(saved === 'light' || saved === 'dark' ? saved : (prefersLight ? 'light' : 'dark'));

  function labelFor(t) { return t === 'light' ? '🌙 Donker' : '☀️ Lig'; }

  // Voeg die wisselknoppie by sodra die blad klaar gelaai het
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-outline btn-sm theme-toggle';
    btn.textContent = labelFor(theme);
    btn.setAttribute('aria-label', 'Wissel tussen lig en donker modus');
    btn.addEventListener('click', function () {
      applyTheme(theme === 'light' ? 'dark' : 'light');
      try { localStorage.setItem('theme', theme); } catch (e) {}
      btn.textContent = labelFor(theme);
    });

    function placeInNavbar() {
      var navRight = document.querySelector('.navbar-right');
      var navbar = document.querySelector('.navbar');
      if (navRight) {
        // Langs die Teken Uit-knoppie
        navRight.insertBefore(btn, navRight.firstChild);
      } else if (navbar) {
        navbar.appendChild(btn);
      }
    }

    if (document.querySelector('.navbar')) {
      placeInNavbar();
    } else if (document.getElementById('site-header')) {
      // Die navbar word async deur main.js se loadSiteHeader() ingelaai —
      // wag vir die sein voordat die knoppie geplaas word
      window.addEventListener('siteHeaderReady', function handle() {
        window.removeEventListener('siteHeaderReady', handle);
        placeInNavbar();
      });
    } else {
      // Geen navbar (bv. login.html): sweef die knoppie regs-bo
      btn.classList.add('theme-toggle--floating');
      document.body.appendChild(btn);
    }
  });
})();
