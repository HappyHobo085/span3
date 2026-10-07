/**
 * kampus.js — Hierdie lêer beheer die Kampus-bladsy (kampus.html).
 *
 * Wat dit doen, in eenvoudige woorde:
 *   - Laai die lys van kampusse in die keuselys bo-aan die bladsy.
 *   - Wys op die paneelbord hoeveel studente en personeel in- en uitgeteken is,
 *     met sirkeldiagramme en 'n regstreekse tendens-grafiek.
 *   - Wys soekbare tabelle: wie is nou op die kampus, en almal op die stelsel.
 *   - Laat die gebruiker 'n nuwe klaskamer skep deur 'n klein venster (modal).
 *
 * Dit het main.js nodig (wat eerste moet laai) om met die bediener te praat.
 */

// Alles word in een blok toegedraai sodat die veranderlikes nie met ander lêers bots nie.
(function () {
  // ----- Kry die belangrike dele van die bladsy en hou hulle byderhand -----
  const openClassModalButton = document.getElementById('open-class-modal');
  const closeClassModalButton = document.getElementById('close-class-modal');
  const createClassButton = document.getElementById('create-class-button');
  const classModalOverlay = document.getElementById('class-modal-overlay');
  const classRoomName = document.getElementById('class-room-name');
  const classKampus = document.getElementById('class-kampus');
  const classNfcTag = document.getElementById('class-nfc-tag');
  const dataSelect = document.getElementById('data-select');

  // ----- Waardes wat die bladsy onthou terwyl dit oop is -----
  var currentKampusId = null;   // Watter kampus is nou gekies
  var pollingInterval = null;   // Die "horlosie" wat die paneelbord gereeld opdateer
  var trendHistory = {};        // Per kampus: monsters van {t, stu, per} vir die tendens-grafiek

  // ----- Gedeelde hulpfunksies -----

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

  // Vriendelike rolname vir die tabelle (bv. "Kampus_Opsigter" -> "Kampus Opsigter").
  function rolTeks(rol) {
    return String(rol || '').replace(/_/g, ' ');
  }

  // ----- Tabelle (stats.js se gedeelde tabel) -----
  var nouTabel = null;     // wie is nou in en uit by die gekose kampus
  var almalTabel = null;   // al die gebruikers op die stelsel

  function maakTabelle() {
    if (!window.MoonStats) return;
    nouTabel = MoonStats.createTable(document.getElementById('nou-tabel'), {
      columns: [
        { name: 'Naam', format: 'teks' },
        { name: 'E-pos', format: 'teks' },
        { name: 'Rol', format: 'teks' },
        { name: 'Status', format: 'status' },
        { name: 'Laaste skandering', format: 'datumtyd' },
        { name: 'Metode', format: 'teks' }
      ],
      searchPlaceholder: 'Soek persoon…',
      emptyText: 'Nog niemand het by hierdie kampus gescan nie.',
      filters: [
        { label: 'Almal' },
        { label: 'Op kampus', test: function (r) { return r.inn; } },
        { label: 'Van kampus af', test: function (r) { return !r.inn; } },
        { label: 'Studente', test: function (r) { return r.rol === 'Student'; } },
        { label: 'Personeel', test: function (r) { return r.rol === 'Personeel'; } }
      ]
    });
    almalTabel = MoonStats.createTable(document.getElementById('almal-tabel'), {
      columns: [
        { name: 'Naam', format: 'teks' },
        { name: 'Nommer', format: 'teks' },
        { name: 'E-pos', format: 'teks' },
        { name: 'Rol', format: 'teks' },
        { name: 'Status', format: 'status' }
      ],
      searchPlaceholder: 'Soek gebruiker…',
      emptyText: 'Laai gebruikers…',
      filters: [
        { label: 'Almal' },
        { label: 'Studente', test: function (r) { return r.rol === 'Student'; } },
        { label: 'Personeel', test: function (r) { return r.rol === 'Personeel'; } },
        { label: 'Ander rolle', test: function (r) { return r.rol !== 'Student' && r.rol !== 'Personeel'; } }
      ]
    });
  }

  function stelTelling(id, n) {
    var el = document.getElementById(id);
    if (el) el.textContent = n === null ? '' : String(n);
  }

  /**
   * Hierdie funksie laai al die gebruikers vanaf die bediener (net een keer)
   * en wys hulle in die "Almal op die stelsel" tabel.
   */
  async function loadGebruikersLys() {
    if (!window.MoonApi || !almalTabel) return;

    var json = await window.MoonApi.fetchGebruikers();
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      almalTabel.setRows([]);
      almalTabel.setNote('Kon nie gebruikers laai nie.');
      return;
    }

    stelTelling('almal-telling', json.data.length);
    almalTabel.setRows(json.data.map(function (g) {
      var rol = g.Rol_Naam || '';
      return {
        key: g.Gebruiker_ID,
        rol: rol,
        cells: [
          volleNaam(g),
          g.STU_Nommer || g.PER_Nommer || g.KAMO_Nommer || g.SEK_Nommer || null,
          g.GEB_Epos || null,
          rolTeks(rol),
          g.Is_Aktief === false
            ? { label: 'Onaktief', tone: 'sleg' }
            : { label: 'Aktief', tone: 'goed' }
        ]
      };
    }));
  }

  /**
   * Hierdie funksie vra die bediener wie tans in- en uitgeteken is by 'n kampus,
   * en werk dan die tellings, grafieke en die "nou" tabel by.
   */
  async function refreshDashboard(kampusId) {
    if (!kampusId || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKampusStatus(kampusId);

    // As die bediener nie geantwoord het nie, wys strepies en stop hier
    if (!json || !json.sukses || !json.data) {
      ['dash-student-in-count', 'dash-student-out-count',
       'dash-personeel-in-count', 'dash-personeel-out-count'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.textContent = '--';
      });
      return;
    }

    var data = json.data;
    var inn = data.scanned_in || [];
    var uit = data.scanned_out || [];
    function tel(lys, rol) { return lys.filter(function (u) { return u.Rol_Naam === rol; }).length; }
    var stuIn = tel(inn, 'Student'), stuUit = tel(uit, 'Student');
    var perIn = tel(inn, 'Personeel'), perUit = tel(uit, 'Personeel');

    // Die KPI-teëls wys net die syfer — die etiket staan reeds op die teël.
    document.getElementById('dash-student-in-count').textContent = stuIn;
    document.getElementById('dash-student-out-count').textContent = stuUit;
    document.getElementById('dash-personeel-in-count').textContent = perIn;
    document.getElementById('dash-personeel-out-count').textContent = perUit;

    // Een tabel vir almal: die statusfilter vervang die vier aparte lyste.
    if (nouTabel) {
      var rye = inn.map(function (u) { return [u, true]; }).concat(uit.map(function (u) { return [u, false]; }));
      rye.sort(function (a, b) { return (b[1] - a[1]) || volleNaam(a[0]).localeCompare(volleNaam(b[0])); });
      stelTelling('nou-telling', inn.length + ' in · ' + uit.length + ' uit');
      nouTabel.setRows(rye.map(function (p) {
        var u = p[0];
        return {
          key: u.Gebruiker_ID,
          inn: p[1],
          rol: u.Rol_Naam,
          cells: [
            volleNaam(u), u.GEB_Epos || null, rolTeks(u.Rol_Naam),
            p[1] ? { label: 'Op kampus', tone: 'goed' } : { label: 'Van kampus af', tone: 'neutraal' },
            leesTyd(u.Tydstempel), u.Metode || null
          ]
        };
      }));
    }

    recordTrendSample(kampusId, stuIn, perIn);
    renderStats(kampusId, stuIn, stuUit, perIn, perUit);
  }

  /**
   * Hierdie funksie bêre elke keer 'n "monster" van hoeveel studente en personeel
   * op die kampus is, sodat die tendens-grafiek kan wys hoe dit oor tyd verander.
   */
  function recordTrendSample(kampusId, studente, personeel) {
    var key = String(kampusId);
    if (!trendHistory[key]) trendHistory[key] = [];
    var arr = trendHistory[key];
    arr.push({ t: new Date(), stu: studente, per: personeel });
    // Hou net die laaste 60 monsters (teen 5 sekondes elk is dit sowat 5 minute)
    if (arr.length > 60) arr.shift();
  }

  // Die jongste syfers, sodat die grafieke oorgeteken kan word (venstergrootte/tema).
  var laasteStats = null;

  /**
   * Hierdie funksie teken die grafieke met stats.js: 'n sirkeldiagram vir
   * studente en vir personeel (in teenoor uit), en die tendens-grafiek.
   */
  function renderStats(kampusId, stuIn, stuOut, perIn, perOut) {
    if (!window.MoonStats) return;
    laasteStats = [kampusId, stuIn, stuOut, perIn, perOut];
    var c = MoonStats.colors;

    MoonStats.renderDonut(document.getElementById('stat-studente-donut'), {
      title: 'Studente in / uit',
      segments: [
        { label: 'Ingeteken', value: stuIn, color: c.series1 },
        { label: 'Uitgeteken', value: stuOut, color: c.dim }
      ]
    });
    MoonStats.renderDonut(document.getElementById('stat-personeel-donut'), {
      title: 'Personeel in / uit',
      segments: [
        { label: 'Ingeteken', value: perIn, color: c.series2 },
        { label: 'Uitgeteken', value: perOut, color: c.dim }
      ]
    });

    var hist = trendHistory[String(kampusId)] || [];
    MoonStats.renderTrend(document.getElementById('stat-trend'), {
      times: hist.map(function (p) { return p.t; }),
      height: 180,
      series: [
        { label: 'Studente', color: c.series1, values: hist.map(function (p) { return p.stu; }) },
        { label: 'Personeel', color: c.series2, values: hist.map(function (p) { return p.per; }) }
      ]
    });
  }

  function herteken() {
    if (laasteStats) renderStats.apply(null, laasteStats);
  }

  /**
   * Hierdie funksie laai al die kampusse vanaf die bediener in die keuselys bo-aan die bladsy.
   * Dit kies dan vanself die eerste kampus en laai daardie kampus se paneelbord.
   */
  async function loadPageKampusDropdown() {
    if (!dataSelect || !window.MoonApi) return;

    var json = await window.MoonApi.fetchKampusse();
    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    dataSelect.innerHTML = '';
    json.data.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = String(k.Kampus_ID);
      opt.textContent = k.KAM_Naam;
      dataSelect.appendChild(opt);
    });

    // Kies vanself die eerste kampus en begin die paneelbord opdateer
    if (json.data.length > 0) {
      currentKampusId = json.data[0].Kampus_ID;
      refreshDashboard(currentKampusId);
      startPolling();
    }
  }

  /**
   * Hierdie funksie laat die paneelbord vanself elke 5 sekondes vars inligting gaan haal.
   * Dit stop eers enige ou "horlosie" sodat daar net een op 'n slag loop.
   */
  function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(function () {
      refreshDashboard(currentKampusId);
    }, 5000);
  }

  // Hierdie funksie maak die "nuwe klas" venster oop op die skerm.
  function openClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.add('open');
    classModalOverlay.setAttribute('aria-hidden', 'false');
  }

  // Hierdie funksie maak die "nuwe klas" venster weer toe.
  function closeClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.remove('open');
    classModalOverlay.setAttribute('aria-hidden', 'true');
  }

  /**
   * Hierdie funksie laai die kampusse vanaf die bediener
   * en sit hulle in die kampus-keuselys binne die "nuwe klas" venster.
   */
  async function loadKampusDropdown() {
  if (!classKampus || !window.MoonApi) return;

  // Vra die bediener vir die lys van kampusse
  const json = await window.MoonApi.fetchKampusse();

  if (json && json.sukses && Array.isArray(json.data)) {
    classKampus.innerHTML = '<option value="">Kies kampus...</option>';

    // Sit elke kampus as 'n keuse in die keuselys
    json.data.forEach(function (k) {
      const opt = document.createElement('option');
      opt.value = String(k.Kampus_ID);
      opt.textContent = k.KAM_Naam;
      classKampus.appendChild(opt);
    });
  }
}

  /**
   * Hierdie funksie lees die vorm in die venster, maak seker alles is ingevul,
   * en stuur dan die nuwe klaskamer na die bediener om gestoor te word.
   */
  async function submitNewClass() {
  const roomName = classRoomName ? classRoomName.value.trim() : '';
  const kampusId = classKampus ? Number(classKampus.value) : null;

  // Maak seker die gebruiker het 'n naam en 'n kampus gekies
  if (!roomName || !kampusId) {
    alert('Voltooi asseblief die klaskamer naam en kampus.');
    return;
  }

  // Stuur die nuwe klas se inligting na die bediener
  const json = await window.MoonApi.createKlas({
    LOK_Naam: roomName,
    LOK_Tipe: "Klaskamer",
    Kampus_ID: kampusId,
    NFC_UID: "TEMP",
    NFC_Tipe: "Lokasie"
  });

  // Wys of dit gewerk het, en maak die venster skoon en toe as dit reg is
  if (json && json.sukses) {
    alert('Klas suksesvol gestoor. UID: ' + json.data.nfc_tag.NFC_UID);
    closeClassModal();
    classRoomName.value = '';
    classKampus.value = '';
  } else {
    alert((json && json.fout) || 'Kon nie klas skep nie.');
  }
}

  // ----- Koppel die kampus-keuselys -----
  // As die gebruiker 'n ander kampus kies, laai daardie kampus se paneelbord.
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      currentKampusId = Number(dataSelect.value);
      refreshDashboard(currentKampusId);
      startPolling();
    });
  }

  // ----- Knoppies wat die venster oopmaak en toemaak -----
  // As die gebruiker die "maak oop" knoppie druk, wys die venster.
  if (openClassModalButton) {
    openClassModalButton.addEventListener('click', openClassModal);
  }

  // As die gebruiker die "maak toe" knoppie druk, steek die venster weg.
  if (closeClassModalButton) {
    closeClassModalButton.addEventListener('click', closeClassModal);
  }

  // As die gebruiker buite die wit venster op die donker agtergrond klik, maak die venster toe.
  if (classModalOverlay) {
    classModalOverlay.addEventListener('click', function (event) {
      if (event.target === classModalOverlay) {
        closeClassModal();
      }
    });
  }

  // ----- Stuur die nuwe klas wanneer die knoppie gedruk word -----
  // As die gebruiker die "skep klas" knoppie druk, stoor die nuwe klas.
  if (createClassButton) {
    createClassButton.addEventListener('click', function () {
      submitNewClass();
    });
  }

  // ----- Lokaalgebruik Voorspelling / Hittekaart -----
  let huidigeLokaalGebruik = [];
  
  async function loadLokaalGebruik(kampusId) {
    if (!kampusId) return;
    try {
      const response = await window.app.api.get(`/kampusse/${kampusId}/lokaalgebruik`);
      if (response.sukses) {
        huidigeLokaalGebruik = response.data;
        renderLokaalGebruik();
      }
    } catch (error) {
      console.error('Fout met die laai van lokaalgebruik:', error);
    }
  }

  function getStatusKleur(vulgraad) {
    if (vulgraad === null) return 'var(--border-dim)';
    if (vulgraad <= 0.5) return 'var(--success-color, #4CAF50)';
    if (vulgraad <= 0.8) return 'var(--warning-color, #FFEB3B)';
    if (vulgraad <= 1.0) return 'var(--primary-color, #FF9800)';
    return 'var(--danger-color, #F44336)';
  }

  function renderLokaalGebruik() {
    const container = document.getElementById('lokaalgebruik-container');
    const dagSelect = document.getElementById('lokaalgebruik-dag-select');
    if (!container || !dagSelect) return;

    const gekoseDag = dagSelect.value;
    const gleuwe = huidigeLokaalGebruik.filter(g => g.Dag === gekoseDag);

    if (gleuwe.length === 0) {
      container.innerHTML = `<p style="padding: 20px; text-align: center; color: var(--text-muted)">Geen voorspellings data vir ${gekoseDag} nie.</p>`;
      return;
    }

    // Unieke lokale en unieke ure om die matriks te bou
    const lokale = [...new Set(gleuwe.map(g => g.Lokaal))].sort();
    const ure = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]; // Standaard akademiese ure (08:00 tot 17:00)

    let html = `<table class="admin-table" style="width: 100%; text-align: center; border-collapse: collapse; margin-top: 15px;">`;
    
    // Opskrifte
    html += `<thead><tr><th style="text-align:left; border-bottom: 2px solid var(--border-dim);">Lokaal</th>`;
    ure.forEach(u => {
      html += `<th style="border-bottom: 2px solid var(--border-dim); width: 8%;">${u.toString().padStart(2, '0')}:00</th>`;
    });
    html += `</tr></thead><tbody>`;

    // Rye vir elke lokaal
    lokale.forEach(lokaal => {
      html += `<tr><td style="text-align:left; font-weight: bold; border-bottom: 1px solid var(--border-dim); padding: 8px;">${lokaal}</td>`;
      ure.forEach(uur => {
        // Soek 'n gleuf wat oorvleuel met hierdie uur
        const match = gleuwe.find(g => {
          if (g.Lokaal !== lokaal) return false;
          const beginUur = parseInt(g.Begin.split(':')[0], 10);
          const eindeUur = parseInt(g.Einde.split(':')[0], 10);
          return uur >= beginUur && uur < eindeUur;
        });

        if (match) {
          const vulTeks = match.Vulgraad !== null ? Math.round(match.Vulgraad * 100) + '%' : 'Onbekend';
          const agtergrond = getStatusKleur(match.Vulgraad);
          const grens = match.Konflik ? '2px solid red' : '1px solid var(--border-dim)';
          const flits = match.Konflik || (match.Vulgraad > 1.0) ? 'animation: pulse 2s infinite;' : '';
          
          html += `
            <td style="border: ${grens}; background: ${agtergrond}; color: #000; padding: 4px; position: relative; ${flits}" title="Vak: ${match.Vak}&#10;Tyd: ${match.Begin} - ${match.Einde}&#10;Inskrywing: ${match.Inskrywing}&#10;Voorspel: ${match.Verwagte_Skanderings}&#10;Kapasiteit: ${match.Kapasiteit}&#10;Bron: ${match.Bron}">
              <div style="font-size: 0.75em; font-weight:bold;">${match.Vak}</div>
              <div style="font-size: 0.85em;">${vulTeks}</div>
              ${match.Konflik ? '<span style="color:red;font-weight:900;" title="Bespreekings konflik!">&#9888;</span>' : ''}
            </td>
          `;
        } else {
          html += `<td style="border-bottom: 1px solid var(--border-dim); border-right: 1px solid var(--border-dim);">&nbsp;</td>`;
        }
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    
    // Voeg effense pulse animasie by CSS as dit nie daar is nie
    html += `
      <style>
        @keyframes pulse {
          0% { box-shadow: inset 0 0 0 0 rgba(255, 0, 0, 0.7); }
          50% { box-shadow: inset 0 0 5px 2px rgba(255, 0, 0, 0.7); }
          100% { box-shadow: inset 0 0 0 0 rgba(255, 0, 0, 0.7); }
        }
      </style>
    `;

    container.innerHTML = html;
  }

  // Voeg 'n event listener by die dag seleksie sodat dit onmiddellik herteken as mens verander
  const lokaalDagSelect = document.getElementById('lokaalgebruik-dag-select');
  if (lokaalDagSelect) {
    lokaalDagSelect.addEventListener('change', renderLokaalGebruik);
  }

  // Koppel loadLokaalGebruik in die dataSelect ('Kies Kampus' dropdown) veranderingslus
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      const geselekteerdeKampus = this.value;
      if (geselekteerdeKampus) {
        loadLokaalGebruik(geselekteerdeKampus);
      }
    });
  }

  // Wanneer die bladsy klaar gelaai het, begin alles: laai die keuselyste en die naamlyste.
  document.addEventListener('DOMContentLoaded', function () {
    maakTabelle();              // bou die twee soekbare tabelle
    loadKampusDropdown();       // vul die kampus-keuselys in die "nuwe klas" venster
    loadPageKampusDropdown();   // vul die keuselys bo-aan die bladsy en laai die paneelbord
    loadGebruikersLys();        // vul die "Almal op die stelsel" tabel

    // Teken die grafieke oor as die venster verander of die tema wissel.
    var grootteTyd = null;
    window.addEventListener('resize', function () {
      clearTimeout(grootteTyd);
      grootteTyd = setTimeout(herteken, 150);
    });
    new MutationObserver(herteken).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
    
    // Initialiseer lokaalgebruik vir die eerste kampus as daar een is
    setTimeout(() => {
      if (dataSelect && dataSelect.value) {
        loadLokaalGebruik(dataSelect.value);
      }
    }, 1000);
  });
})();
