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
      emptyText: 'Nog niemand het by hierdie kampus geskandeer nie.',
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
      loadLokaalGebruik(currentKampusId);
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
    alert('Voltooi asseblief die klaskamernaam en kampus.');
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
  // Die bediener voorspel vir elke sessie van volgende week watter breuk van die
  // ingeskrewe studente sal skandeer (koers), en reken dit om na 'n vulgraad.
  var lokaalGebruik = null;      // die laaste antwoord van die bediener
  var lokaalGebruikKampus = null;

  function esc(teks) {
    return String(teks == null ? '' : teks).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function pct(waarde) {
    return waarde == null ? '?' : Math.round(waarde * 100) + '%';
  }

  function minute(tyd) {
    var m = /^(\d{1,2}):(\d{2})/.exec(String(tyd || ''));
    return m ? Number(m[1]) * 60 + Number(m[2]) : null;
  }

  async function loadLokaalGebruik(kampusId) {
    if (!kampusId || !window.MoonApi) return;
    lokaalGebruikKampus = String(kampusId);
    var container = document.getElementById('lokaalgebruik-container');
    if (container) container.innerHTML = '<p class="lg-leeg">Laai voorspelling…</p>';
    try {
      var json = await window.MoonApi.fetchLokaalGebruik(kampusId);
      if (String(kampusId) !== lokaalGebruikKampus) return;  // ou antwoord vir 'n vorige kampus
      if (!json || !json.sukses) throw new Error((json && (json.fout || json.detail)) || 'Onbekende fout');
      lokaalGebruik = json.data;
    } catch (error) {
      console.error('Fout met die laai van lokaalgebruik:', error);
      lokaalGebruik = null;
      if (container) container.innerHTML = '<p class="lg-leeg">Kon nie die voorspelling laai nie.</p>';
      return;
    }
    renderLokaalGebruik();
  }

  // Kleur volgens voorspelde vulgraad: groen tot 50%, geel tot 80%, pers tot 100%, rooi daarbo.
  function vulKleur(vulgraad) {
    if (vulgraad == null) return 'transparent';
    var kleur = vulgraad <= 0.5 ? 'var(--success)'
      : vulgraad <= 0.8 ? 'var(--warning)'
      : vulgraad <= 1.0 ? 'var(--accent)'
      : 'var(--error)';
    return 'color-mix(in srgb, ' + kleur + ' 30%, transparent)';
  }

  function renderInfo() {
    var info = document.getElementById('lokaalgebruik-info');
    if (!info) return;
    var d = lokaalGebruik;
    if (!d) { info.textContent = ''; return; }
    var dele = [];
    if (d.voorspel_week) {
      dele.push('<strong>Week ' + esc(d.voorspel_week) + '</strong> (data tot week ' + esc(d.laaste_data_week) + ')');
    }
    dele.push('Metode: <span title="' + esc(d.keuse_rede) + '">' + esc(d.metode_etiket) + '</span>');
    if (d.metrics && d.metrics.mae && d.metrics.mae[d.metode] != null) {
      dele.push('MAE koers: ' + esc(d.metrics.mae[d.metode]));
    }
    if (d.interval && d.interval.dekking != null) {
      dele.push('Reeks-dekking: ' + pct(d.interval.dekking) + (d.interval.wys ? '' : ' (te laag, reeks versteek)'));
    }
    if (d.databron === 'SINTETIES') {
      dele.push('<em>Sintetiese data: wys net dat die pyplyn werk</em>');
    }
    info.innerHTML = dele.join(' · ');
  }

  function selTitel(g) {
    var reels = [
      g.vak + ' — ' + g.begin + '–' + g.einde,
      'Ingeskryf: ' + g.inskrywing + ' · Kapasiteit: ' + (g.kapasiteit || 'onbekend'),
      'Rooster-vulgraad: ' + pct(g.geskeduleerde_vulgraad),
      'Voorspelde koers: ' + g.koers.toFixed(2) + ' → ' + g.verwagte_getal + ' studente',
      'Voorspelde vulgraad: ' + pct(g.vulgraad),
    ];
    if (g.reeks) {
      reels.push('Reeks: ' + g.reeks.getal_laag + '–' + g.reeks.getal_hoog + ' studente (' +
        pct(g.reeks.vulgraad_laag) + ' tot ' + pct(g.reeks.vulgraad_hoog) + ')');
    }
    if (g.oor_kapasiteit) reels.push('⚠ Voorspelling bo kapasiteit');
    else if (g.kan_oorloop) reels.push('! Kan bo kapasiteit gaan');
    if (g.konflik) reels.push('⚠ Besprekingskonflik in hierdie lokaal');
    return reels.join('\n');
  }

  function renderLokaalGebruik() {
    var container = document.getElementById('lokaalgebruik-container');
    var dagSelect = document.getElementById('lokaalgebruik-dag-select');
    if (!container || !dagSelect) return;
    renderInfo();
    if (!lokaalGebruik) return;

    var gekoseDag = dagSelect.value;
    var gleuwe = (lokaalGebruik.gleuwe || []).filter(function (g) { return g.dag === gekoseDag; });

    if (gleuwe.length === 0) {
      container.innerHTML = '<p class="lg-leeg">Geen klasse met \'n lokaal en inskrywings op ' + esc(gekoseDag) + ' nie.</p>';
      return;
    }

    // Uurgleuwe van die vroegste begin tot die laaste einde (minstens 08:00–17:00).
    var eersteUur = 8, laasteUur = 17;
    gleuwe.forEach(function (g) {
      var b = minute(g.begin), e = minute(g.einde);
      if (b != null) eersteUur = Math.min(eersteUur, Math.floor(b / 60));
      if (e != null) laasteUur = Math.max(laasteUur, Math.ceil(e / 60));
    });
    var ure = [];
    for (var u = eersteUur; u < laasteUur; u++) ure.push(u);

    var lokale = Array.from(new Set(gleuwe.map(function (g) { return g.lokaal; }))).sort();

    var html = '<table class="lg-tabel"><thead><tr><th class="lg-lokaal">Lokaal</th>';
    ure.forEach(function (uur) {
      html += '<th>' + String(uur).padStart(2, '0') + ':00</th>';
    });
    html += '</tr></thead><tbody>';

    lokale.forEach(function (lokaal) {
      var kap = (gleuwe.find(function (g) { return g.lokaal === lokaal; }) || {}).kapasiteit;
      html += '<tr><td class="lg-lokaal">' + esc(lokaal) +
        '<div class="lg-sub">' + (kap ? kap + ' plekke' : 'kapasiteit onbekend') + '</div></td>';

      ure.forEach(function (uur) {
        // 'n Sessie hoort in elke uurgleuf waarmee dit oorvleuel (bv. 08:30–09:20 → 08:00 en 09:00).
        var van = uur * 60, tot = van + 60;
        var hier = gleuwe.filter(function (g) {
          var b = minute(g.begin), e = minute(g.einde);
          return g.lokaal === lokaal && b != null && e != null && b < tot && e > van;
        });
        if (hier.length === 0) {
          html += '<td></td>';
          return;
        }
        var ergste = hier.reduce(function (a, g) {
          return (g.vulgraad || 0) > (a.vulgraad || 0) ? g : a;
        });
        var vlag = hier.some(function (g) { return g.konflik || g.oor_kapasiteit || g.kan_oorloop; });
        html += '<td class="lg-sel' + (vlag ? ' lg-vlag' : '') + '" style="background:' + vulKleur(ergste.vulgraad) + '">';
        hier.forEach(function (g) {
          var merk = g.konflik ? ' <span class="lg-merk">⚠ konflik</span>'
            : g.oor_kapasiteit ? ' <span class="lg-merk">⚠</span>'
            : g.kan_oorloop ? ' <span class="lg-merk">!</span>' : '';
          html += '<div class="lg-sessie" title="' + esc(selTitel(g)) + '">' +
            '<div class="lg-vak">' + esc(g.vak) + merk + '</div>' +
            '<div class="lg-vul">' + pct(g.vulgraad) + '</div>' +
            (g.reeks ? '<div class="lg-sub">' + pct(g.reeks.vulgraad_laag) + '–' + pct(g.reeks.vulgraad_hoog) + '</div>' : '') +
            '<div class="lg-sub">rooster ' + pct(g.geskeduleerde_vulgraad) + '</div>' +
            '</div>';
        });
        html += '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<div class="lg-sleutel">' +
      '<span><i style="background:' + vulKleur(0.4) + '"></i>tot 50%</span>' +
      '<span><i style="background:' + vulKleur(0.7) + '"></i>tot 80%</span>' +
      '<span><i style="background:' + vulKleur(0.95) + '"></i>tot 100%</span>' +
      '<span><i style="background:' + vulKleur(1.2) + '"></i>bo kapasiteit</span>' +
      '<span>⚠ bo kapasiteit of konflik · ! reeks kom bo 100%</span>' +
      '</div>';

    container.innerHTML = html;
  }

  // Kies vandag se dag by verstek en herteken onmiddellik as die gebruiker 'n ander dag kies.
  var lokaalDagSelect = document.getElementById('lokaalgebruik-dag-select');
  if (lokaalDagSelect) {
    var vandag = ['Sondag', 'Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrydag', 'Saterdag'][new Date().getDay()];
    if (Array.from(lokaalDagSelect.options).some(function (o) { return o.value === vandag; })) {
      lokaalDagSelect.value = vandag;
    }
    lokaalDagSelect.addEventListener('change', renderLokaalGebruik);
  }

  // Laai die voorspelling vir die nuwe kampus as die 'Kies Kampus' keuselys verander.
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      if (this.value) loadLokaalGebruik(this.value);
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
  });
})();
