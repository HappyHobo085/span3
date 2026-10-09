// =============================================================================
// home.js — Die Oorsig-blad se logika: laai al die syfers van die bediener af.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die regstreekse tellings (wie is nou op kampus, toegange vandag)
//     van GET /dashboard/live en hou dit elke 10 sekondes vars.
//   - Bou uit daardie peiling 'n geskiedenis en teken die held-grafiek.
//   - Tel die kampusse en koshuise (GET /kampusse/status en GET /koshuise).
//   - Wys per kampus hoeveel mense tans ingeskandeer is (balk-grafiek).
//   - Wys die komende events (GET /events?view=komende) in 'n soekbare tabel.
//   - Wys my eie status (GET /dashboard), 'n sirkeldiagram van wie op kampus
//     is, en die nuutste skanderings (GET /toegangslogs) in 'n soekbare tabel.
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
  var myStatus = document.getElementById('my-status');
  var samestellingDonut = document.getElementById('stat-samestelling-donut');
  var eventsTabel = null;
  var aktiwiteitTabel = null;
  var laasteLive = null;   // jongste {stu, per} vir die sirkeldiagram

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

  // Tye van die bediener sonder 'n tydsone is UTC; maak 'n plaaslike Date.
  function leesTyd(iso) {
    if (!iso) return null;
    var s = String(iso);
    if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += 'Z';
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
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

  // Sirkeldiagram: studente teenoor personeel wat nou op kampus is.
  function tekenSamestelling() {
    if (!window.MoonStats || !samestellingDonut || !laasteLive) return;
    MoonStats.renderDonut(samestellingDonut, {
      title: 'Op kampus nou',
      segments: [
        { label: 'Studente', value: laasteLive.stu, color: MoonStats.colors.series1 },
        { label: 'Personeel', value: laasteLive.per, color: MoonStats.colors.series2 }
      ]
    });
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

    laasteLive = { stu: stu, per: per };
    tekenSamestelling();

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
  // Hierdie funksie wys die nuutste in- en uitskanderings oor die stelsel
  // in 'n soekbare tabel (die soekwoord bly staan as dit verfris).
  async function laaiAktiwiteit() {
    if (!window.MoonApi || !aktiwiteitTabel) return;

    var json = await window.MoonApi.fetchToegangsLogs();
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      aktiwiteitTabel.setNote('Kon nie die aktiwiteit laai nie.');
      return;
    }

    aktiwiteitTabel.setNote('');
    aktiwiteitTabel.setRows(json.data.map(function (log) {
      var inn = log.Rigting === 'IN';
      return {
        key: log.Log_ID,
        cells: [
          leesTyd(log.Tyd),
          log.Naam || ('Gebruiker #' + log.Gebruiker_ID),
          log.Lokasie || ('Lokasie #' + log.Lokasie_ID),
          { label: inn ? 'IN' : 'UIT', tone: inn ? 'goed' : 'waarsku' }
        ]
      };
    }));
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
  // Hierdie funksie wys die events wat voorlê in 'n soekbare tabel:
  // naam, plek, tyd en hoeveel plekke oor is.
  async function laaiEvents() {
    if (!window.MoonApi || !eventsTabel) return;

    var json = await window.MoonApi.fetchEvents('komende');
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      eventsTabel.setNote('Kon nie die geleenthede laai nie.');
      return;
    }

    var telling = document.getElementById('events-telling');
    if (telling) telling.textContent = String(json.data.length);
    eventsTabel.setRows(json.data.map(function (ev) {
      return {
        key: ev.event_id,
        cells: [
          ev.naam,
          ev.kampus_naam + (ev.lokasie_naam ? ' · ' + ev.lokasie_naam : ''),
          leesTyd(ev.begin_tyd),
          ev.vol ? { label: 'Vol', tone: 'sleg' } : { label: ev.plekke_oor + ' plekke oor', tone: 'goed' }
        ]
      };
    }));
  }

  // Bou die twee tabelle een keer; die data word daarna ingelaai en ververs.
  function maakTabelle() {
    if (!window.MoonStats) return;
    eventsTabel = MoonStats.createTable(document.getElementById('events-tabel'), {
      columns: [
        { name: 'Geleentheid', format: 'teks' },
        { name: 'Plek', format: 'teks' },
        { name: 'Begin', format: 'datumtyd' },
        { name: 'Plekke', format: 'status' }
      ],
      searchPlaceholder: 'Soek geleentheid…',
      emptyText: 'Geen komende geleenthede nie.',
      pageSize: 10
    });
    aktiwiteitTabel = MoonStats.createTable(document.getElementById('aktiwiteit-tabel'), {
      columns: [
        { name: 'Tyd', format: 'datumtyd' },
        { name: 'Naam', format: 'teks' },
        { name: 'Lokasie', format: 'teks' },
        { name: 'Rigting', format: 'status' }
      ],
      searchPlaceholder: 'Soek persoon of plek…',
      emptyText: 'Nog geen skanderings nie.',
      pageSize: 10,
      filters: [
        { label: 'Almal' },
        { label: 'Net IN', test: function (r) { return r.cells[3].label === 'IN'; } },
        { label: 'Net UIT', test: function (r) { return r.cells[3].label === 'UIT'; } }
      ]
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

    maakTabelle();
    laaiLiveTellings();
    laaiMyStatus();
    laaiKampusse();
    laaiKoshuise();
    laaiEvents();
    laaiAktiwiteit();

    // Teken die grafieke oor wanneer die tema wissel.
    new MutationObserver(function () {
      tekenHeroGrafiek();
      tekenKampusBalke();
      tekenSamestelling();
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

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
      tekenSamestelling();
    }, 150);
  });

  document.addEventListener('DOMContentLoaded', begin);
})();
