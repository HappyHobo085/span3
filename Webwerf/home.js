// =============================================================================
// home.js — Die Tuisblad se logika: laai al die syfers van die bediener af.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die regstreekse tellings (wie is nou op kampus, toegange vandag)
//     van GET /dashboard/live en hou dit elke 10 sekondes vars.
//   - Tel die kampusse en koshuise (GET /kampusse/status en GET /koshuise).
//   - Wys per kampus hoeveel mense tans ingeskandeer is.
//   - Wys die komende events (GET /events?view=komende).
//   - Wys my eie status (GET /dashboard) en die nuutste skanderings
//     (GET /toegangslogs), en wanneer alles laas opgedateer is.
// Alle data kom van die bediener — niks op hierdie blad is mock data nie.
// =============================================================================

(function () {
  'use strict';

  // ----- DOM verwysings -----
  var statStudente = document.getElementById('stat-studente');
  var statPersoneel = document.getElementById('stat-personeel');
  var statToegange = document.getElementById('stat-toegange');
  var statKampusse = document.getElementById('stat-kampusse');
  var statKoshuise = document.getElementById('stat-koshuise');
  var foutKaart = document.getElementById('home-fout');
  var kampusLys = document.getElementById('kampus-lys');
  var eventsLys = document.getElementById('events-lys');
  var eventsTitel = document.getElementById('events-titel');
  var myStatus = document.getElementById('my-status');
  var aktiwiteitLys = document.getElementById('aktiwiteit-lys');
  var laasOpgedateer = document.getElementById('laas-opgedateer');

  // Hoeveel skanderings die aktiwiteitslys hoogstens wys.
  var AKTIWITEIT_MAKS = 15;

  // Oor hoeveel sekondes die regstreekse syfers weer gaan haal word.
  var VERFRIS_SEKONDES = 10;
  var pollTimer = null;

  var MAANDE_KORT = ['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'];

  // Hierdie funksie skryf 'n ISO-tyd as bv. "24 Aug 18:00" (plaaslike tyd).
  function formatTyd(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    return d.getDate() + ' ' + MAANDE_KORT[d.getMonth()] + ' ' +
      pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  // Hierdie funksie skryf net die tyd (bv. "07:42"), met die datum by as
  // dit nie vandag was nie (bv. "17 Aug 07:42").
  function formatTydKort(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    var tyd = pad(d.getHours()) + ':' + pad(d.getMinutes());
    var nou = new Date();
    if (d.getFullYear() === nou.getFullYear() &&
        d.getMonth() === nou.getMonth() &&
        d.getDate() === nou.getDate()) {
      return tyd;
    }
    return d.getDate() + ' ' + MAANDE_KORT[d.getMonth()] + ' ' + tyd;
  }

  // Hierdie funksie wys of versteek die "kan nie bediener bereik nie" kaart.
  function wysFout(wys) {
    if (foutKaart) foutKaart.hidden = !wys;
  }

  // Hierdie funksie wys wanneer die syfers laas suksesvol gelaai is.
  function stempelOpdatering() {
    if (!laasOpgedateer) return;
    var nou = new Date();
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    laasOpgedateer.textContent = 'Laas opgedateer ' +
      pad(nou.getHours()) + ':' + pad(nou.getMinutes()) + ':' + pad(nou.getSeconds());
    laasOpgedateer.hidden = false;
  }

  // Hierdie funksie wys 'n boodskap in 'n lys-houer (bv. "geen data nie").
  function wysBoodskap(houer, boodskap) {
    houer.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'viz-empty';
    div.textContent = boodskap;
    houer.appendChild(div);
  }

  // ----- Regstreekse tellings (GET /dashboard/live) -----
  // Hierdie funksie kry wie nou op kampus is en hoeveel toegange daar
  // vandag was, en sit die syfers in die boonste kaartjies.
  async function laaiLiveTellings() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchLiveDashboard();
    if (!json || !json.sukses || !json.data) {
      wysFout(true);
      return;
    }
    wysFout(false);

    if (statStudente) statStudente.textContent = json.data.studente_op_kampus;
    if (statPersoneel) statPersoneel.textContent = json.data.personeel_op_kampus;
    if (statToegange) statToegange.textContent = json.data.toegange_vandag;
    stempelOpdatering();
  }

  // ----- My status (GET /dashboard) -----
  // Hierdie funksie wys die ingetekende gebruiker se eie status: op kampus
  // of nie, en sy/haar laaste kampus- en klas-skanderings.
  async function laaiMyStatus() {
    if (!window.MoonApi || !myStatus) return;

    var json = await window.MoonApi.fetchMyDashboard();
    if (!json || !json.sukses || !json.data) {
      if (!myStatus.hasChildNodes()) {
        wysBoodskap(myStatus, 'Kon nie jou status laai nie.');
      }
      return;
    }
    var data = json.data;

    myStatus.innerHTML = '';

    // Kop: naam en rol links, die status-plakkertjie regs.
    var kop = document.createElement('div');
    kop.style.display = 'flex';
    kop.style.alignItems = 'center';
    kop.style.justifyContent = 'space-between';
    kop.style.gap = '10px';

    var info = document.createElement('div');
    info.className = 'admin-user-info';
    var naam = document.createElement('div');
    naam.className = 'admin-user-name';
    naam.textContent = (data.naam + ' ' + (data.van || '')).trim();
    info.appendChild(naam);
    var rol = document.createElement('div');
    rol.className = 'admin-user-email';
    rol.textContent = data.rol || '';
    info.appendChild(rol);
    kop.appendChild(info);

    var badge = document.createElement('span');
    badge.className = 'status-badge ' +
      (data.kampus_status === 'OP_KAMPUS' ? 'status-badge--active' : 'status-badge--inactive');
    var dot = document.createElement('span');
    dot.className = 'status-dot';
    badge.appendChild(dot);
    badge.appendChild(document.createTextNode(
      data.kampus_status === 'OP_KAMPUS' ? 'Op kampus' :
      data.kampus_status === 'NIE_OP_KAMPUS' ? 'Nie op kampus' : 'Onbekend'));
    kop.appendChild(badge);
    myStatus.appendChild(kop);

    // Twee reëls: die laaste kampus- en klas-skandering.
    var lys = document.createElement('ul');
    lys.className = 'updates-list';
    lys.style.marginTop = '10px';

    function skanderingReël(etiket, log) {
      var li = document.createElement('li');
      var kol = document.createElement('span');
      kol.className = 'updates-dot';
      if (log && log.rigting === 'UIT') kol.style.background = 'var(--warning)';
      if (!log) kol.style.background = 'var(--text-muted)';
      li.appendChild(kol);
      var teks = document.createElement('span');
      teks.textContent = log
        ? etiket + ': ' + log.rigting + ' by ' + log.lokasie
        : etiket + ': nog geen skandering nie';
      li.appendChild(teks);
      if (log && log.tyd) {
        var tyd = document.createElement('span');
        tyd.className = 'viz-caption';
        tyd.style.marginLeft = 'auto';
        tyd.textContent = formatTydKort(log.tyd);
        li.appendChild(tyd);
      }
      return li;
    }

    lys.appendChild(skanderingReël('Laaste kampus-skandering', data.laaste_kampus));
    lys.appendChild(skanderingReël('Laaste klas-skandering', data.laaste_klas));
    myStatus.appendChild(lys);
  }

  // ----- Onlangse aktiwiteit (GET /toegangslogs) -----
  // Hierdie funksie wys die nuutste in- en uitskanderings oor die stelsel.
  // Ouer bedieners stuur nie name nie — dan wys ons die ID's.
  async function laaiAktiwiteit() {
    if (!window.MoonApi || !aktiwiteitLys) return;

    var json = await window.MoonApi.fetchToegangsLogs();
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (!aktiwiteitLys.hasChildNodes()) {
        wysBoodskap(aktiwiteitLys, 'Kon nie die aktiwiteit laai nie.');
      }
      return;
    }

    aktiwiteitLys.innerHTML = '';
    if (json.data.length === 0) {
      wysBoodskap(aktiwiteitLys, 'Nog geen skanderings nie.');
      return;
    }

    var lys = document.createElement('ul');
    lys.className = 'updates-list';

    json.data.slice(0, AKTIWITEIT_MAKS).forEach(function (log) {
      var li = document.createElement('li');

      var kol = document.createElement('span');
      kol.className = 'updates-dot';
      kol.style.background = log.Rigting === 'IN' ? 'var(--success)' : 'var(--warning)';
      li.appendChild(kol);

      var wie = log.Naam || ('Gebruiker #' + log.Gebruiker_ID);
      var waar = log.Lokasie || ('Lokasie #' + log.Lokasie_ID);
      var teks = document.createElement('span');
      teks.textContent = wie + ' · ' + log.Rigting + ' by ' + waar;
      li.appendChild(teks);

      var tyd = document.createElement('span');
      tyd.className = 'viz-caption';
      tyd.style.marginLeft = 'auto';
      tyd.style.whiteSpace = 'nowrap';
      tyd.textContent = formatTydKort(log.Tyd);
      li.appendChild(tyd);

      lys.appendChild(li);
    });

    aktiwiteitLys.appendChild(lys);
  }

  // ----- Kampusse (GET /kampusse/status) -----
  // Hierdie funksie tel die kampusse en teken die "Nou op kampus" lys:
  // een kaartjie per kampus met hoeveel mense tans ingeskandeer is.
  async function laaiKampusse() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchKampusseStatus();
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (kampusLys && !kampusLys.hasChildNodes()) {
        wysBoodskap(kampusLys, 'Kon nie die kampusse laai nie.');
      }
      return;
    }

    if (statKampusse) statKampusse.textContent = json.data.length;
    if (!kampusLys) return;

    kampusLys.innerHTML = '';
    if (json.data.length === 0) {
      wysBoodskap(kampusLys, 'Geen kampusse geregistreer nie.');
      return;
    }

    json.data.forEach(function (k) {
      var kaart = document.createElement('div');
      kaart.className = 'user-card';

      var info = document.createElement('div');
      info.className = 'admin-user-info';
      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = k.KAM_Naam;
      info.appendChild(naam);
      if (k.KAM_Adres) {
        var adres = document.createElement('div');
        adres.className = 'admin-user-email';
        adres.textContent = k.KAM_Adres;
        info.appendChild(adres);
      }
      kaart.appendChild(info);

      var telling = document.createElement('div');
      telling.className = 'admin-user-name';
      telling.style.whiteSpace = 'nowrap';
      telling.textContent = k.scanned_in_count + ' op kampus';
      kaart.appendChild(telling);

      kampusLys.appendChild(kaart);
    });
  }

  // ----- Koshuise (GET /koshuise) -----
  // Hierdie funksie tel hoeveel koshuise geregistreer is.
  async function laaiKoshuise() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchKoshuise();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    if (statKoshuise) statKoshuise.textContent = json.data.length;
  }

  // ----- Komende events (GET /events?view=komende) -----
  // Hierdie funksie wys die events wat voorlê: naam, plek, tyd en
  // hoeveel plekke oor is.
  async function laaiEvents() {
    if (!window.MoonApi || !eventsLys) return;

    var json = await window.MoonApi.fetchEvents('komende');
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      wysBoodskap(eventsLys, 'Kon nie die events laai nie.');
      return;
    }

    if (eventsTitel) {
      eventsTitel.textContent = 'Komende Events (' + json.data.length + ')';
    }

    eventsLys.innerHTML = '';
    if (json.data.length === 0) {
      wysBoodskap(eventsLys, 'Geen komende events nie.');
      return;
    }

    json.data.forEach(function (ev) {
      var kaart = document.createElement('div');
      kaart.className = 'user-card';

      var info = document.createElement('div');
      info.className = 'admin-user-info';
      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = ev.naam;
      info.appendChild(naam);

      var detail = document.createElement('div');
      detail.className = 'admin-user-email';
      var plek = ev.kampus_naam + (ev.lokasie_naam ? ' · ' + ev.lokasie_naam : '');
      detail.textContent = plek + ' · ' + formatTyd(ev.begin_tyd);
      info.appendChild(detail);
      kaart.appendChild(info);

      var plekke = document.createElement('div');
      plekke.className = 'admin-user-email';
      plekke.style.whiteSpace = 'nowrap';
      plekke.textContent = ev.vol ? 'Vol' : ev.plekke_oor + ' plekke oor';
      kaart.appendChild(plekke);

      eventsLys.appendChild(kaart);
    });
  }

  // ----- Begin -----
  // Hierdie funksie laai alles een keer en hou dan die regstreekse
  // syfers en kampus-tellings elke paar sekondes vars.
  function begin() {
    // As die API-lêer nog nie klaar gelaai het nie, probeer weer sodra
    // die blad klaar is (main.js laai website_api_calls.js dinamies).
    if (!window.MoonApi) {
      window.addEventListener('load', begin, { once: true });
      return;
    }

    laaiLiveTellings();
    laaiMyStatus();
    laaiKampusse();
    laaiKoshuise();
    laaiEvents();
    laaiAktiwiteit();

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(function () {
      laaiLiveTellings();
      laaiMyStatus();
      laaiKampusse();
      laaiAktiwiteit();
    }, VERFRIS_SEKONDES * 1000);
  }

  document.addEventListener('DOMContentLoaded', begin);
})();
