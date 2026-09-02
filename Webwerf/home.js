// =============================================================================
// home.js — Die Oorsig-blad se logika: laai al die syfers van die bediener af.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die regstreekse tellings (wie is nou op kampus, toegange vandag)
//     van GET /dashboard/live en hou dit elke 10 sekondes vars.
//   - Bou uit daardie peiling 'n geskiedenis en teken die held-grafiek.
//   - Tel die kampusse en koshuise (GET /kampusse/status en GET /koshuise).
//   - Wys per kampus hoeveel mense tans ingeskandeer is (balk-grafiek).
//   - Wys die komende events (GET /events?view=komende).
//   - Wys my eie status (GET /dashboard) en die nuutste skanderings
//     (GET /toegangslogs), en wanneer alles laas opgedateer is.
// Alle data kom van die bediener — niks op hierdie blad is mock data nie.
// =============================================================================

(function () {
  'use strict';

  // ----- DOM verwysings -----
  var heroValue = document.getElementById('hero-value');
  var heroStu = document.getElementById('hero-stu');
  var heroPer = document.getElementById('hero-per');
  var heroChart = document.getElementById('hero-chart');
  var heroKeyStu = document.getElementById('hero-key-stu');
  var heroKeyPer = document.getElementById('hero-key-per');
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

  // Hoeveel skanderings die aktiwiteitslys hoogstens wys.
  var AKTIWITEIT_MAKS = 15;

  // Oor hoeveel sekondes die regstreekse syfers weer gaan haal word.
  var VERFRIS_SEKONDES = 10;
  var pollTimer = null;

  // Geskiedenis van die peiling vir die held-grafiek: {t, stu, per}.
  // 90 monsters teen 10 sekondes elk is sowat 15 minute.
  var heroHistory = [];
  var HERO_MAKS_MONSTERS = 90;

  // Die jongste kampus-tellings, sodat die balke oorgeteken kan word
  // as die venster van grootte verander of die tema wissel.
  var laasteKampusData = null;

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

  // Hierdie funksie wys in die boonste balk wanneer die syfers laas
  // suksesvol gelaai is.
  function stempelOpdatering() {
    var el = document.getElementById('topbar-updated');
    if (!el) return;
    var nou = new Date();
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    el.textContent = 'Opgedateer ' +
      pad(nou.getHours()) + ':' + pad(nou.getMinutes()) + ':' + pad(nou.getSeconds());
    el.hidden = false;
  }

  // Hierdie funksie wys 'n boodskap in 'n lys-houer (bv. "geen data nie").
  function wysBoodskap(houer, boodskap) {
    houer.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'viz-empty';
    div.textContent = boodskap;
    houer.appendChild(div);
  }

  // ----- Held-grafiek -----
  // Hierdie funksie kleur die legende-sleutels en teken die area-grafiek
  // uit die geskiedenis van die peiling.
  function tekenHeroGrafiek() {
    if (!window.MoonStats || !heroChart) return;

    if (heroKeyStu) heroKeyStu.style.background = MoonStats.colors.series1;
    if (heroKeyPer) heroKeyPer.style.background = MoonStats.colors.series2;

    MoonStats.renderTrend(heroChart, {
      times: heroHistory.map(function (p) { return p.t; }),
      series: [
        {
          label: 'Studente',
          color: MoonStats.colors.series1,
          values: heroHistory.map(function (p) { return p.stu; })
        },
        {
          label: 'Personeel',
          color: MoonStats.colors.series2,
          values: heroHistory.map(function (p) { return p.per; })
        }
      ],
      height: 130,
      fill: true
    });

    // Die held het reeds sy eie legende in die kop — haal die outomatiese een uit.
    var outoLegende = heroChart.querySelector('.viz-legend');
    if (outoLegende) outoLegende.remove();
  }

  // ----- Regstreekse tellings (GET /dashboard/live) -----
  // Hierdie funksie kry wie nou op kampus is en hoeveel toegange daar
  // vandag was, en werk die held-strook en die KPI-teëls by.
  async function laaiLiveTellings() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchLiveDashboard();
    if (!json || !json.sukses || !json.data) {
      wysFout(true);
      return;
    }
    wysFout(false);

    var stu = Number(json.data.studente_op_kampus) || 0;
    var per = Number(json.data.personeel_op_kampus) || 0;

    if (heroValue) heroValue.textContent = stu + per;
    if (heroStu) heroStu.textContent = stu;
    if (heroPer) heroPer.textContent = per;
    if (statStudente) statStudente.textContent = stu;
    if (statPersoneel) statPersoneel.textContent = per;
    if (statToegange) statToegange.textContent = json.data.toegange_vandag;

    // Bêre 'n monster vir die held-grafiek en teken dit oor.
    heroHistory.push({ t: new Date(), stu: stu, per: per });
    if (heroHistory.length > HERO_MAKS_MONSTERS) heroHistory.shift();
    tekenHeroGrafiek();

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
  // Hierdie funksie wys die nuutste in- en uitskanderings oor die stelsel,
  // elkeen met 'n IN- of UIT-plakkertjie.
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

      var chip = document.createElement('span');
      chip.className = 'feed-chip ' + (log.Rigting === 'IN' ? 'feed-chip--in' : 'feed-chip--uit');
      chip.textContent = log.Rigting === 'IN' ? 'IN' : 'UIT';
      li.appendChild(chip);

      var wie = log.Naam || ('Gebruiker #' + log.Gebruiker_ID);
      var waar = log.Lokasie || ('Lokasie #' + log.Lokasie_ID);
      var teks = document.createElement('span');
      teks.textContent = wie + ' · ' + waar;
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
  // Hierdie funksie tel die kampusse en teken die "Nou per kampus" balke:
  // een balk per kampus met hoeveel mense tans ingeskandeer is.
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
    laasteKampusData = json.data;
    tekenKampusBalke();
  }

  // Hierdie funksie teken die per-kampus balke uit die jongste data.
  function tekenKampusBalke() {
    if (!kampusLys || !laasteKampusData) return;

    if (laasteKampusData.length === 0) {
      wysBoodskap(kampusLys, 'Geen kampusse geregistreer nie.');
      return;
    }

    if (!window.MoonStats) return;
    MoonStats.renderBarsH(kampusLys, {
      color: MoonStats.colors.series1,
      items: laasteKampusData.map(function (k) {
        return {
          label: k.KAM_Naam,
          value: k.scanned_in_count,
          detail: (k.KAM_Adres ? k.KAM_Adres + ' · ' : '') + 'tans ingeskandeer'
        };
      })
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
      eventsTitel.innerHTML = '';
      eventsTitel.appendChild(document.createTextNode('Komende Events '));
      var telling = document.createElement('span');
      telling.className = 'panel-count';
      telling.textContent = String(json.data.length);
      eventsTitel.appendChild(telling);
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

  // As die venster van grootte verander, teken die grafieke oor sodat hulle pas.
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      tekenHeroGrafiek();
      tekenKampusBalke();
    }, 150);
  });

  document.addEventListener('DOMContentLoaded', begin);
})();
