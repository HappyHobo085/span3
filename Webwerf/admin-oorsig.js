// =============================================================================
// admin-oorsig.js — Die oorsig-paneelbord bo-aan die Admin-blad.
//
// Wat dit doen, in eenvoudige woorde:
//   - Tel die gebruikers, kampusse en koshuise (GET /gebruikers, /kampusse,
//     /koshuise) en wys dit as KPI-teëls.
//   - Teken 'n sirkeldiagram van aktiewe teenoor onaktiewe gebruikers, en
//     balke vir gebruikers per rol en die besetting van elke koshuis.
//   - Ververs elke 30 sekondes, sodat nuwe gebruikers of koshuise wat op
//     hierdie blad geskep word vanself in die oorsig verskyn.
// Die res van die Admin-blad (die lyste en vorms) sit in admin.js.
// =============================================================================

(function () {
  'use strict';

  var VERFRIS_MS = 30000;
  var ROL_VERTOON = {
    Student: 'Studente',
    Personeel: 'Personeel',
    Kampus_Opsigter: 'Kampus-opsigters',
    Sekuriteit_Wag: 'Sekuriteitswagte',
    Administrateur: 'Administrateurs'
  };

  var laaste = null; // { gebruikers, kampusse, koshuise } vir oorteken

  function stelTeks(id, teks) {
    var el = document.getElementById(id);
    if (el) el.textContent = teks;
  }

  function data(json) {
    return json && json.sukses && Array.isArray(json.data) ? json.data : null;
  }

  async function laai() {
    if (!window.MoonApi) return;
    var res = await Promise.all([
      window.MoonApi.fetchGebruikers().catch(function () { return null; }),
      window.MoonApi.fetchKampusse().catch(function () { return null; }),
      window.MoonApi.fetchKoshuise().catch(function () { return null; })
    ]);
    var gebruikers = data(res[0]);
    if (!gebruikers) return; // hou die vorige syfers as die bediener nie antwoord nie
    laaste = { gebruikers: gebruikers, kampusse: data(res[1]) || [], koshuise: data(res[2]) || [] };
    teken();
  }

  function teken() {
    if (!laaste || !window.MoonStats) return;
    var g = laaste.gebruikers;
    var c = MoonStats.colors;
    var aktief = g.filter(function (u) { return u.Is_Aktief !== false; }).length;

    stelTeks('oorsig-gebruikers', String(g.length));
    stelTeks('oorsig-aktief', String(aktief));
    stelTeks('oorsig-kampusse', String(laaste.kampusse.length));
    stelTeks('oorsig-koshuise', String(laaste.koshuise.length));

    MoonStats.renderDonut(document.getElementById('oorsig-aktief-donut'), {
      title: 'Gebruikers',
      segments: [
        { label: 'Aktief', value: aktief, color: c.series1 },
        { label: 'Onaktief', value: g.length - aktief, color: c.dim }
      ]
    });

    // Gebruikers per (primêre) rol, grootste eerste.
    var perRol = {};
    g.forEach(function (u) {
      var rol = u.Rol_Naam || 'Onbekend';
      perRol[rol] = (perRol[rol] || 0) + 1;
    });
    MoonStats.renderBarsH(document.getElementById('oorsig-rol-balke'), {
      items: Object.keys(perRol)
        .sort(function (a, b) { return perRol[b] - perRol[a]; })
        .map(function (rol) {
          return { label: ROL_VERTOON[rol] || rol.replace(/_/g, ' '), value: perRol[rol] };
        })
    });

    // Besetting per koshuis: inwoners (studente met dié Koshuis_ID) teenoor kapasiteit.
    var inwoners = {};
    g.forEach(function (u) {
      if (u.Koshuis_ID !== undefined && u.Koshuis_ID !== null) {
        inwoners[u.Koshuis_ID] = (inwoners[u.Koshuis_ID] || 0) + 1;
      }
    });
    MoonStats.renderBarsH(document.getElementById('oorsig-koshuis-balke'), {
      items: laaste.koshuise.map(function (k) {
        var n = inwoners[k.Koshuis_ID] || 0;
        var kap = Number(k.KOS_Kapasiteit) || 0;
        return {
          label: k.KOS_Naam,
          value: kap ? Math.round((n / kap) * 100) : 0,
          detail: n + ' van ' + kap + ' plekke'
        };
      }),
      max: 100,
      fmtValue: function (v) { return v + '%'; }
    });
  }

  function begin() {
    if (!window.MoonApi) {
      window.addEventListener('load', begin, { once: true });
      return;
    }
    laai();
    setInterval(function () { if (!document.hidden) laai(); }, VERFRIS_MS);

    var grootteTyd = null;
    window.addEventListener('resize', function () {
      clearTimeout(grootteTyd);
      grootteTyd = setTimeout(teken, 150);
    });
    new MutationObserver(teken).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
  }

  document.addEventListener('DOMContentLoaded', begin);
})();
