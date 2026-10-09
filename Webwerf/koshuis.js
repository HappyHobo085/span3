/**
 * koshuis.js — Hierdie lêer beheer die Koshuis-bladsy (koshuis.html).
 *
 * Wat dit doen, in eenvoudige woorde:
 *   - Laai die lys van koshuise in die keuselys bo-aan die bladsy.
 *   - Wys KPI-teëls en sirkeldiagramme: hoeveel inwoners in- en uitgeteken is,
 *     en hoe vol die koshuis is teenoor sy kapasiteit.
 *   - Teken 'n regstreekse tendens-grafiek van wie ingeteken is.
 *   - Wys 'n soekbare tabel van die koshuis se inwoners met elkeen se status.
 *   - Gaan haal vanself elke paar sekondes vars inligting by die bediener.
 *
 * Dit het main.js en stats.js nodig (wat eerste moet laai).
 */

// Alles word in een blok toegedraai sodat die veranderlikes nie met ander lêers bots nie.
(function () {
  const dataSelect = document.getElementById('data-select');

  // ----- Waardes wat die bladsy onthou terwyl dit oop is -----
  var currentKoshuisId = null;  // Watter koshuis is nou gekies
  var pollingInterval = null;   // Die "horlosie" wat die paneelbord gereeld opdateer
  var alleStudente = null;      // Al die studente word een keer gelaai en hier gebêre
  var laasteStatus = null;      // Die jongste in/uit-data van die gekose koshuis
  var trendHistory = {};        // Per koshuis: monsters van {t, v} vir die tendens-grafiek
  var inwonerTabel = null;

  // Tye van die bediener sonder 'n tydsone is UTC; maak 'n plaaslike Date.
  function leesTyd(iso) {
    if (!iso) return null;
    var s = String(iso);
    if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += 'Z';
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function volleNaam(u) {
    return ((u.GEB_Naam || '') + ' ' + (u.GEB_Van || '')).trim();
  }

  function stelTeks(id, teks) {
    var el = document.getElementById(id);
    if (el) el.textContent = teks;
  }

  // ----- Inwoners-tabel -----
  function maakTabel() {
    if (!window.MoonStats) return;
    inwonerTabel = MoonStats.createTable(document.getElementById('inwoner-tabel'), {
      columns: [
        { name: 'Naam', format: 'teks' },
        { name: 'Studentenommer', format: 'teks' },
        { name: 'E-pos', format: 'teks' },
        { name: 'Status', format: 'status' },
        { name: 'Laaste skandering', format: 'datumtyd' },
        { name: 'Metode', format: 'teks' }
      ],
      searchPlaceholder: 'Soek inwoner…',
      emptyText: 'Laai inwoners…',
      filters: [
        { label: 'Almal' },
        { label: 'Ingeteken', test: function (r) { return r.status === 'IN'; } },
        { label: 'Uitgeteken', test: function (r) { return r.status === 'UIT'; } },
        { label: 'Nog nooit geskandeer', test: function (r) { return r.status === null; } }
      ]
    });
  }

  /**
   * Hierdie funksie bou die inwoners-tabel: elke student van die gekose
   * koshuis, met sy/haar jongste skandering (as daar een is).
   */
  function tekenInwoners() {
    if (!inwonerTabel || alleStudente === null || currentKoshuisId === null) return;

    var skandering = {};
    if (laasteStatus) {
      (laasteStatus.scanned_in || []).concat(laasteStatus.scanned_out || []).forEach(function (u) {
        skandering[u.Gebruiker_ID] = u;
      });
    }

    var inwoners = alleStudente.filter(function (g) {
      return Number(g.Koshuis_ID) === Number(currentKoshuisId);
    });
    // Ingeteken eerste, dan uitgeteken, dan nog nooit gescan; binne elk alfabeties.
    var orde = { IN: 0, UIT: 1 };
    inwoners.sort(function (a, b) {
      var sa = skandering[a.Gebruiker_ID], sb = skandering[b.Gebruiker_ID];
      var oa = sa ? orde[sa.Rigting] : 2, ob = sb ? orde[sb.Rigting] : 2;
      return (oa - ob) || volleNaam(a).localeCompare(volleNaam(b));
    });

    inwonerTabel.setRows(inwoners.map(function (g) {
      var sk = skandering[g.Gebruiker_ID] || null;
      var status = sk ? sk.Rigting : null;
      return {
        key: g.Gebruiker_ID,
        status: status,
        cells: [
          volleNaam(g), g.STU_Nommer || null, g.GEB_Epos || null,
          status === 'IN' ? { label: 'Ingeteken', tone: 'goed' }
            : status === 'UIT' ? { label: 'Uitgeteken', tone: 'neutraal' }
            : { label: 'Nog nooit geskandeer', tone: 'sleg' },
          sk ? leesTyd(sk.Tydstempel) : null,
          sk ? sk.Metode : null
        ]
      };
    }));
    stelTeks('inwoner-telling', String(inwoners.length));
  }

  /**
   * Hierdie funksie laai al die gebruikers vanaf die bediener (net een keer)
   * en bêre net die studente; die inwoners-tabel word hieruit gebou.
   */
  async function loadStudenteCache() {
    if (!window.MoonApi) return;

    var json = await window.MoonApi.fetchGebruikers();
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (inwonerTabel) inwonerTabel.setNote('Kon nie gebruikers laai nie.');
      return;
    }

    alleStudente = json.data.filter(function (g) {
      return g.Rol_Naam === 'Student';
    });
    tekenInwoners();
  }

  /**
   * Hierdie funksie vra die bediener wie tans in- en uitgeteken is by 'n koshuis,
   * en werk dan die tellings, grafieke en tabel by.
   */
  async function refreshDashboard(koshuisId) {
    if (!koshuisId || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKoshuisStatus(koshuisId);

    if (!json || !json.sukses || !json.data) {
      ['dash-student-in-count', 'dash-student-out-count', 'dash-nooit-count', 'dash-kapasiteit-card']
        .forEach(function (id) { stelTeks(id, '--'); });
      return;
    }
    // 'n Ander koshuis is intussen gekies — gooi hierdie antwoord weg
    if (Number(koshuisId) !== Number(currentKoshuisId)) return;

    var data = json.data;
    laasteStatus = data;
    var nooit = Math.max((Number(data.inwoner_count) || 0) -
      (Number(data.scanned_in_count) || 0) - (Number(data.scanned_out_count) || 0), 0);

    // Die KPI-teëls wys net die syfers — die etikette staan reeds op die teëls.
    stelTeks('dash-student-in-count', data.scanned_in_count);
    stelTeks('dash-student-out-count', data.scanned_out_count);
    stelTeks('dash-nooit-count', nooit);
    stelTeks('dash-kapasiteit-card', data.inwoner_count + ' / ' + data.KOS_Kapasiteit);

    recordTrendSample(koshuisId, data.scanned_in_count);
    renderStats();
    tekenInwoners();
  }

  /**
   * Hierdie funksie bêre elke keer 'n "monster" van hoeveel studente ingeteken is,
   * sodat die tendens-grafiek kan wys hoe dit oor tyd verander.
   */
  function recordTrendSample(koshuisId, value) {
    var key = String(koshuisId);
    if (!trendHistory[key]) trendHistory[key] = [];
    var arr = trendHistory[key];
    arr.push({ t: new Date(), v: Number(value) || 0 });
    // Hou net die laaste 60 monsters (teen 5 sekondes elk is dit sowat 5 minute)
    if (arr.length > 60) arr.shift();
  }

  /**
   * Hierdie funksie teken die grafieke met stats.js: die inwoners se status
   * en die besetting as sirkeldiagramme, en die tendens-grafiek.
   */
  function renderStats() {
    if (!window.MoonStats || !laasteStatus) return;
    var data = laasteStatus;
    var c = MoonStats.colors;
    var inwoners = Number(data.inwoner_count) || 0;
    var kapasiteit = Number(data.KOS_Kapasiteit) || 0;
    var ingeteken = Number(data.scanned_in_count) || 0;
    var uitgeteken = Number(data.scanned_out_count) || 0;

    MoonStats.renderDonut(document.getElementById('stat-inuit-donut'), {
      title: 'Inwoners in / uit',
      segments: [
        { label: 'Ingeteken', value: ingeteken, color: c.series1 },
        { label: 'Uitgeteken', value: uitgeteken, color: c.series2 },
        { label: 'Nog nooit geskandeer', value: Math.max(inwoners - ingeteken - uitgeteken, 0), color: c.dim }
      ]
    });

    MoonStats.renderDonut(document.getElementById('stat-besetting-donut'), {
      title: 'Besetting',
      segments: [
        { label: 'Inwoners', value: inwoners, color: c.series1 },
        { label: 'Oop plekke', value: Math.max(kapasiteit - inwoners, 0), color: c.dim }
      ]
    });
    var nota = document.getElementById('besetting-nota');
    if (nota) {
      nota.textContent = kapasiteit
        ? Math.round((inwoners / kapasiteit) * 100) + '% vol · kapasiteit ' + kapasiteit +
          (inwoners > kapasiteit ? ' · ' + (inwoners - kapasiteit) + ' oor kapasiteit' : '')
        : 'Geen kapasiteit opgestel nie.';
    }

    var hist = trendHistory[String(currentKoshuisId)] || [];
    MoonStats.renderTrend(document.getElementById('stat-trend'), {
      times: hist.map(function (p) { return p.t; }),
      height: 180,
      series: [
        { label: 'Ingeteken', color: c.series1, values: hist.map(function (p) { return p.v; }) }
      ]
    });
  }

  /**
   * Hierdie funksie laai al die koshuise vanaf die bediener in die keuselys bo-aan die bladsy.
   * Dit kies dan vanself die eerste koshuis en laai daardie koshuis se paneelbord.
   */
  async function loadKoshuisDropdown() {
    if (!dataSelect || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKoshuise();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    dataSelect.innerHTML = '';
    json.data.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = String(k.Koshuis_ID);
      opt.textContent = k.KOS_Naam;
      dataSelect.appendChild(opt);
    });

    if (json.data.length > 0) {
      kiesKoshuis(json.data[0].Koshuis_ID);
    } else if (inwonerTabel) {
      inwonerTabel.setNote('Geen koshuise is nog geregistreer nie.');
    }
  }

  function kiesKoshuis(id) {
    currentKoshuisId = Number(id);
    laasteStatus = null;
    tekenInwoners();
    refreshDashboard(currentKoshuisId);
    startPolling();
  }

  /**
   * Hierdie funksie laat die paneelbord vanself elke 5 sekondes vars inligting gaan haal.
   * Dit stop eers enige ou "horlosie" sodat daar net een op 'n slag loop.
   */
  function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(function () {
      refreshDashboard(currentKoshuisId);
    }, 5000);
  }

  // As die gebruiker 'n ander koshuis kies, laai daardie koshuis se paneelbord en inwoners.
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      kiesKoshuis(dataSelect.value);
    });
  }

  // Wanneer die bladsy klaar gelaai het, begin alles.
  document.addEventListener('DOMContentLoaded', function () {
    maakTabel();
    loadKoshuisDropdown();   // vul die keuselys en laai die paneelbord
    loadStudenteCache();     // laai die studente vir die inwoners-tabel

    // Teken die grafieke oor as die venster verander of die tema wissel.
    var grootteTyd = null;
    window.addEventListener('resize', function () {
      clearTimeout(grootteTyd);
      grootteTyd = setTimeout(renderStats, 150);
    });
    new MutationObserver(renderStats).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
  });
})();
