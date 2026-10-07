/**
 * kampus.js — Hierdie lêer beheer die Kampus-bladsy (kampus.html).
 *
 * Wat dit doen, in eenvoudige woorde:
 *   - Laai die lys van kampusse in die keuselys bo-aan die bladsy.
 *   - Wys op die paneelbord hoeveel studente en personeel in- en uitgeteken is.
 *   - Wys lyste van studente en personeel wat mens kan deursoek.
 *   - Laat die gebruiker 'n nuwe klaskamer skep deur 'n klein venster (modal).
 *
 * Dit het main.js nodig (wat eerste moet laai) om met die bediener te praat.
 */

// Alles word in een blok toegedraai sodat die veranderlikes nie met ander lêers bots nie.
(function () {
  // ----- Kry die belangrike dele van die bladsy en hou hulle byderhand -----
  const listSearch = document.getElementById('list-search');
  const dataList = document.getElementById('data-list');
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

  /**
   * Hierdie funksie bou 'n klein kaartjie vir een persoon.
   * Die kaartjie wys die naam, 'n reël daaronder (bv. studentenommer of e-pos)
   * en 'n klein kenteken met die persoon se rol (Student of Personeel).
   */
  function createUserCard(user, subtitle, rolNaam) {
    var card = document.createElement('div');
    card.className = 'user-card';
    // Stoor die naam en van as soekwoorde sodat die soekblokkie die kaartjie kan vind
    card.dataset.search = ((user.GEB_Naam || '') + ' ' + (user.GEB_Van || '') + ' ' + (subtitle || '')).toLowerCase();

    var infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    // Sit die persoon se naam en van op die kaartjie
    var nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    nameDiv.textContent = (user.GEB_Naam || '') + ' ' + (user.GEB_Van || '');
    infoDiv.appendChild(nameDiv);

    // Sit die tweede reël (bv. nommer of e-pos) onder die naam
    var subDiv = document.createElement('div');
    subDiv.className = 'admin-user-email';
    subDiv.textContent = subtitle || '';
    infoDiv.appendChild(subDiv);

    card.appendChild(infoDiv);

    // As die persoon 'n rol het, wys dit as 'n klein kenteken
    if (rolNaam) {
      var rolesDiv = document.createElement('div');
      rolesDiv.className = 'admin-user-roles';
      var badge = document.createElement('span');
      badge.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/[\s_]+/g, '');
      badge.textContent = rolNaam;
      rolesDiv.appendChild(badge);
      card.appendChild(rolesDiv);
    }

    return card;
  }

  /**
   * Hierdie funksie neem 'n lys van mense en sit vir elkeen 'n kaartjie in 'n houer op die bladsy.
   * As die lys leeg is, wys dit 'n boodskap dat daar geen gebruikers is nie.
   */
  function renderUserList(container, users) {
    if (!container) return;
    container.innerHTML = '';
    // As daar niemand in die lys is nie, wys 'n "leeg" boodskap
    if (!users || users.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'user-card';
      var info = document.createElement('div');
      info.className = 'admin-user-info';
      var msg = document.createElement('div');
      msg.className = 'admin-user-email';
      msg.textContent = 'Geen gebruikers nie';
      info.appendChild(msg);
      empty.appendChild(info);
      container.appendChild(empty);
      return;
    }
    // Maak vir elke persoon 'n kaartjie en sit dit in die houer
    users.forEach(function (u) {
      var rolNaam = u.Rol_Naam || '';
      container.appendChild(createUserCard(u, u.GEB_Epos || rolNaam, rolNaam));
    });
  }

  /**
   * Hierdie funksie laai al die gebruikers vanaf die bediener (net een keer).
   * Studente gaan na die studente-lys en personeel na die personeel-lys aan die regterkant.
   */
  async function loadGebruikersLys() {
    if (!window.MoonApi) return;

    // Vra die bediener vir al die gebruikers
    var json = await window.MoonApi.fetchGebruikers();

    // As iets verkeerd gegaan het, wys 'n foutboodskap in albei lyste
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (dataList) {
        dataList.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Kon nie gebruikers laai nie.</div></div></div>';
      }
      var personeelListErr = document.getElementById('personeel-list');
      if (personeelListErr) {
        personeelListErr.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Kon nie personeel laai nie.</div></div></div>';
      }
      return;
    }

    // Skei die studente uit die volle lys uit
    var students = json.data.filter(function (g) {
      return g.Rol_Naam === 'Student';
    });

    // Skei die personeel uit die volle lys uit
    var personeel = json.data.filter(function (g) {
      return g.Rol_Naam === 'Personeel';
    });

    // Sit die studente se kaartjies in die studente-lys
    if (dataList) {
      dataList.innerHTML = '';
      if (students.length === 0) {
        dataList.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Geen studente nie</div></div></div>';
      } else {
        students.forEach(function (g) {
          var subtitle = g.STU_Nommer || g.GEB_Epos || '';
          dataList.appendChild(createUserCard(g, subtitle, 'Student'));
        });
      }
    }

    // Sit die personeel se kaartjies in die personeel-lys
    var personeelList = document.getElementById('personeel-list');
    if (personeelList) {
      personeelList.innerHTML = '';
      if (personeel.length === 0) {
        personeelList.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Geen personeel nie</div></div></div>';
      } else {
        personeel.forEach(function (g) {
          var subtitle = g.PER_Nommer || g.GEB_Epos || '';
          personeelList.appendChild(createUserCard(g, subtitle, 'Personeel'));
        });
      }
    }
  }

  /**
   * Hierdie funksie vra die bediener wie tans in- en uitgeteken is by 'n kampus,
   * en werk dan die tellings en lyste op die paneelbord by.
   */
  async function refreshDashboard(kampusId) {
    if (!kampusId || !window.MoonApi) return;

    // Vra die bediener vir die nuutste in/uit-inligting van hierdie kampus
    var json = await window.MoonApi.fetchKampusStatus(kampusId);

    // Klein hulpfunksie: as iets fout gaan, wys strepies in plaas van getalle
    function resetCounts() {
      ['dash-student-in-count', 'dash-student-out-count',
       'dash-personeel-in-count', 'dash-personeel-out-count'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.textContent = '--';
      });
    }

    // As die bediener nie geantwoord het nie, wys strepies en stop hier
    if (!json || !json.sukses || !json.data) {
      resetCounts();
      return;
    }

    var data = json.data;

    // Verdeel die mense wat in en uit is tussen studente en personeel
    var studentIn = (data.scanned_in || []).filter(function (u) {
      return u.Rol_Naam === 'Student';
    });
    var studentOut = (data.scanned_out || []).filter(function (u) {
      return u.Rol_Naam === 'Student';
    });
    var personeelIn = (data.scanned_in || []).filter(function (u) {
      return u.Rol_Naam === 'Personeel';
    });
    var personeelOut = (data.scanned_out || []).filter(function (u) {
      return u.Rol_Naam === 'Personeel';
    });

    // Werk die vier telling-blokkies op die paneelbord by
    var stuInCount = document.getElementById('dash-student-in-count');
    var stuOutCount = document.getElementById('dash-student-out-count');
    var perInCount = document.getElementById('dash-personeel-in-count');
    var perOutCount = document.getElementById('dash-personeel-out-count');

    // Die KPI-teëls wys net die syfer — die etiket staan reeds op die teël.
    if (stuInCount) stuInCount.textContent = studentIn.length;
    if (stuOutCount) stuOutCount.textContent = studentOut.length;
    if (perInCount) perInCount.textContent = personeelIn.length;
    if (perOutCount) perOutCount.textContent = personeelOut.length;

    // Werk die vier naamlyste op die paneelbord by
    renderUserList(document.getElementById('dash-student-in-list'), studentIn);
    renderUserList(document.getElementById('dash-student-out-list'), studentOut);
    renderUserList(document.getElementById('dash-personeel-in-list'), personeelIn);
    renderUserList(document.getElementById('dash-personeel-out-list'), personeelOut);

    // Werk die statistieke by: die twee verdeling-balke en die tendens-grafiek
    recordTrendSample(kampusId, studentIn.length, personeelIn.length);
    renderStats(kampusId, studentIn.length, studentOut.length, personeelIn.length, personeelOut.length);
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

  /**
   * Hierdie funksie teken die statistieke-paneel met stats.js:
   * verdeling-balke vir studente en personeel, en die tendens-grafiek.
   */
  function renderStats(kampusId, stuIn, stuOut, perIn, perOut) {
    if (!window.MoonStats) return;

    // Verdeling-balk: studente in (blou) teenoor uit (dowwe grys)
    MoonStats.renderSplitBar(document.getElementById('stat-studente-split'), {
      title: 'Studente in / uit',
      segments: [
        { label: 'Ingeteken', value: stuIn, color: MoonStats.colors.series1 },
        { label: 'Uitgeteken', value: stuOut, color: MoonStats.colors.dim }
      ]
    });

    // Verdeling-balk: personeel in (pers) teenoor uit (dowwe grys)
    MoonStats.renderSplitBar(document.getElementById('stat-personeel-split'), {
      title: 'Personeel in / uit',
      segments: [
        { label: 'Ingeteken', value: perIn, color: MoonStats.colors.series2 },
        { label: 'Uitgeteken', value: perOut, color: MoonStats.colors.dim }
      ]
    });

    // Tendens-grafiek: studente en personeel op kampus oor die afgelope tyd
    var hist = trendHistory[String(kampusId)] || [];
    MoonStats.renderTrend(document.getElementById('stat-trend'), {
      times: hist.map(function (p) { return p.t; }),
      series: [
        {
          label: 'Studente',
          color: MoonStats.colors.series1,
          values: hist.map(function (p) { return p.stu; })
        },
        {
          label: 'Personeel',
          color: MoonStats.colors.series2,
          values: hist.map(function (p) { return p.per; })
        }
      ]
    });
  }

  /**
   * Hierdie funksie laai al die kampusse vanaf die bediener in die keuselys bo-aan die bladsy.
   * Dit kies dan vanself die eerste kampus en laai daardie kampus se paneelbord.
   */
  async function loadPageKampusDropdown() {
    if (!dataSelect || !window.MoonApi) return;

    // Vra die bediener vir die lys van kampusse
    var json = await window.MoonApi.fetchKampusse();

    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    // Sit elke kampus as 'n keuse in die keuselys
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

  // Hierdie funksie steek studente-kaartjies weg wat nie by die soekwoord pas nie.
  function applyListFilter() {
    if (!listSearch || !dataList) return;
    var query = listSearch.value.trim().toLowerCase();
    var rows = dataList.querySelectorAll('.user-card');

    // Gaan deur elke kaartjie: wys dit net as die soekwoord daarin voorkom
    rows.forEach(function (row) {
      var searchable = row.dataset.search || (row.textContent || '').toLowerCase();
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
  }

  // Hierdie funksie steek personeel-kaartjies weg wat nie by die soekwoord pas nie.
  function applyPersoneelFilter() {
    var bottomSearch = document.getElementById('bottom-search');
    var personeelList = document.getElementById('personeel-list');
    if (!bottomSearch || !personeelList) return;
    var query = bottomSearch.value.trim().toLowerCase();
    var rows = personeelList.querySelectorAll('.user-card');

    // Gaan deur elke kaartjie: wys dit net as die soekwoord daarin voorkom
    rows.forEach(function (row) {
      var searchable = row.dataset.search || (row.textContent || '').toLowerCase();
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
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

  // ----- Koppel die soekblokkies aan hulle funksies -----
  // As die gebruiker in die studente-soekblokkie tik, filtreer die studente-lys.
  if (listSearch) {
    listSearch.addEventListener('input', applyListFilter);
  }

  // As die gebruiker in die onderste soekblokkie tik, filtreer die personeel-lys.
  var bottomSearch = document.getElementById('bottom-search');
  if (bottomSearch) {
    bottomSearch.addEventListener('input', applyPersoneelFilter);
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
    loadKampusDropdown();       // vul die kampus-keuselys in die "nuwe klas" venster
    loadPageKampusDropdown();   // vul die keuselys bo-aan die bladsy en laai die paneelbord
    loadGebruikersLys();        // vul die studente- en personeel-lyste aan die regterkant
    
    // Initialiseer lokaalgebruik vir die eerste kampus as daar een is
    setTimeout(() => {
      if (dataSelect && dataSelect.value) {
        loadLokaalGebruik(dataSelect.value);
      }
    }, 1000);
  });
})();
