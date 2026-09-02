/**
 * koshuis.js — Hierdie lêer beheer die Koshuis-bladsy (koshuis.html).
 *
 * Wat dit doen, in eenvoudige woorde:
 *   - Laai die lys van koshuise in die keuselys bo-aan die bladsy.
 *   - Wys op die paneelbord hoeveel studente in- en uitgeteken is,
 *     en hoeveel inwoners die koshuis het teenoor sy kapasiteit.
 *   - Wys aan die regterkant 'n soekbare lys van die gekose koshuis se studente.
 *   - Gaan haal vanself elke paar sekondes vars inligting by die bediener.
 *
 * Dit het main.js nodig (wat eerste moet laai) om met die bediener te praat.
 */

// Alles word in een blok toegedraai sodat die veranderlikes nie met ander lêers bots nie.
(function () {
  // ----- Kry die belangrike dele van die bladsy en hou hulle byderhand -----
  const listSearch = document.getElementById('list-search');
  const dataList = document.getElementById('data-list');
  const dataSelect = document.getElementById('data-select');

  // ----- Waardes wat die bladsy onthou terwyl dit oop is -----
  var currentKoshuisId = null;  // Watter koshuis is nou gekies
  var pollingInterval = null;   // Die "horlosie" wat die paneelbord gereeld opdateer
  var alleStudente = null;      // Al die studente word een keer gelaai en hier gebêre
  var trendHistory = {};        // Per koshuis: monsters van {t, v} vir die tendens-grafiek

  /**
   * Hierdie funksie bou 'n klein kaartjie vir een persoon.
   * Die kaartjie wys die naam, 'n reël daaronder (bv. studentenommer of e-pos)
   * en 'n klein kenteken met die persoon se rol.
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
   * As die lys leeg is, wys dit die gegewe "leeg" boodskap.
   */
  function renderUserList(container, users, emptyMessage) {
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
      msg.textContent = emptyMessage || 'Geen gebruikers nie';
      info.appendChild(msg);
      empty.appendChild(info);
      container.appendChild(empty);
      return;
    }
    // Maak vir elke persoon 'n kaartjie en sit dit in die houer
    users.forEach(function (u) {
      var subtitle = u.STU_Nommer || u.GEB_Epos || u.Rol_Naam || '';
      container.appendChild(createUserCard(u, subtitle, u.Rol_Naam || 'Student'));
    });
  }

  /**
   * Hierdie funksie laai al die gebruikers vanaf die bediener (net een keer)
   * en bêre net die studente. Die lys aan die regterkant word later hieruit gebou.
   */
  async function loadStudenteCache() {
    if (!window.MoonApi) return;

    // Vra die bediener vir al die gebruikers
    var json = await window.MoonApi.fetchGebruikers();

    // As iets verkeerd gegaan het, wys 'n foutboodskap in die lys
    if (!json || !json.sukses || !Array.isArray(json.data)) {
      if (dataList) {
        dataList.innerHTML = '<div class="user-card"><div class="admin-user-info"><div class="admin-user-email">Kon nie gebruikers laai nie.</div></div></div>';
      }
      return;
    }

    // Hou net die studente en bêre hulle vir later gebruik
    alleStudente = json.data.filter(function (g) {
      return g.Rol_Naam === 'Student';
    });

    renderKoshuisStudente();
  }

  /**
   * Hierdie funksie wys aan die regterkant net die studente
   * wat aan die gekose koshuis behoort. Dit wag totdat die studente
   * gelaai is én 'n koshuis gekies is.
   */
  function renderKoshuisStudente() {
    if (!dataList || alleStudente === null || currentKoshuisId === null) return;

    // Hou net die studente wie se koshuis dieselfde is as die gekose koshuis
    var studente = alleStudente.filter(function (g) {
      return Number(g.Koshuis_ID) === Number(currentKoshuisId);
    });

    renderUserList(dataList, studente, 'Geen studente in hierdie koshuis nie');
    applyListFilter();
  }

  /**
   * Hierdie funksie vra die bediener wie tans in- en uitgeteken is by 'n koshuis,
   * en werk dan die tellings, inwoner-kaart en lyste op die paneelbord by.
   */
  async function refreshDashboard(koshuisId) {
    if (!koshuisId || !window.MoonApi) return;

    // Vra die bediener vir die nuutste in/uit-inligting van hierdie koshuis
    var json = await window.MoonApi.fetchKoshuisStatus(koshuisId);

    var inCount = document.getElementById('dash-student-in-count');
    var outCount = document.getElementById('dash-student-out-count');
    var kapasiteitCard = document.getElementById('dash-kapasiteit-card');

    // As die bediener nie geantwoord het nie, wys strepies in plaas van getalle
    if (!json || !json.sukses || !json.data) {
      if (inCount) inCount.textContent = '--';
      if (outCount) outCount.textContent = '--';
      if (kapasiteitCard) kapasiteitCard.textContent = '--';
      return;
    }

    var data = json.data;

    // Die KPI-teëls wys net die syfers — die etikette staan reeds op die teëls.
    if (inCount) inCount.textContent = data.scanned_in_count;
    if (outCount) outCount.textContent = data.scanned_out_count;
    if (kapasiteitCard) {
      kapasiteitCard.textContent = data.inwoner_count + ' / ' + data.KOS_Kapasiteit;
    }

    // Werk die twee naamlyste (ingeteken en uitgeteken) op die paneelbord by
    renderUserList(document.getElementById('dash-student-in-list'), data.scanned_in || [], 'Geen studente nie');
    renderUserList(document.getElementById('dash-student-out-list'), data.scanned_out || [], 'Geen studente nie');

    // Werk die statistieke by: die meter, die verdeling-balk en die tendens-grafiek
    recordTrendSample(koshuisId, data.scanned_in_count);
    renderStats(koshuisId, data);
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
   * Hierdie funksie teken die statistieke-paneel met stats.js:
   * die kapasiteit-meter, die in/uit-verdeling en die tendens-grafiek.
   */
  function renderStats(koshuisId, data) {
    if (!window.MoonStats) return;

    // Meter: hoeveel inwoners teenoor die koshuis se kapasiteit
    MoonStats.renderMeter(document.getElementById('stat-kapasiteit-meter'), {
      label: 'Kapasiteit',
      value: Number(data.inwoner_count) || 0,
      max: Number(data.KOS_Kapasiteit) || 0
    });

    // Verdeling-balk: ingeteken (blou) teenoor uitgeteken (dowwe grys)
    MoonStats.renderSplitBar(document.getElementById('stat-inuit-split'), {
      title: 'Studente in / uit',
      segments: [
        { label: 'Ingeteken', value: Number(data.scanned_in_count) || 0, color: MoonStats.colors.series1 },
        { label: 'Uitgeteken', value: Number(data.scanned_out_count) || 0, color: MoonStats.colors.dim }
      ]
    });

    // Tendens-grafiek: hoeveel studente was oor die afgelope tyd ingeteken
    var hist = trendHistory[String(koshuisId)] || [];
    MoonStats.renderTrend(document.getElementById('stat-trend'), {
      times: hist.map(function (p) { return p.t; }),
      series: [
        {
          label: 'Ingeteken',
          color: MoonStats.colors.series1,
          values: hist.map(function (p) { return p.v; })
        }
      ]
    });
  }

  /**
   * Hierdie funksie laai al die koshuise vanaf die bediener in die keuselys bo-aan die bladsy.
   * Dit kies dan vanself die eerste koshuis en laai daardie koshuis se paneelbord en studente.
   */
  async function loadKoshuisDropdown() {
    if (!dataSelect || !window.MoonApi) return;

    // Vra die bediener vir die lys van koshuise
    var json = await window.MoonApi.fetchKoshuise();

    if (!json || !json.sukses || !Array.isArray(json.data)) return;

    // Sit elke koshuis as 'n keuse in die keuselys
    dataSelect.innerHTML = '';
    json.data.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = String(k.Koshuis_ID);
      opt.textContent = k.KOS_Naam;
      dataSelect.appendChild(opt);
    });

    // Kies vanself die eerste koshuis en begin die paneelbord opdateer
    if (json.data.length > 0) {
      currentKoshuisId = json.data[0].Koshuis_ID;
      refreshDashboard(currentKoshuisId);
      renderKoshuisStudente();
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
      refreshDashboard(currentKoshuisId);
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

  // ----- Koppel die soekblokkie aan sy funksie -----
  // As die gebruiker in die soekblokkie tik, filtreer die studente-lys.
  if (listSearch) {
    listSearch.addEventListener('input', applyListFilter);
  }

  // ----- Koppel die koshuis-keuselys -----
  // As die gebruiker 'n ander koshuis kies, laai daardie koshuis se paneelbord en studente.
  if (dataSelect) {
    dataSelect.addEventListener('change', function () {
      currentKoshuisId = Number(dataSelect.value);
      refreshDashboard(currentKoshuisId);
      renderKoshuisStudente();
      startPolling();
    });
  }

  // Wanneer die bladsy klaar gelaai het, begin alles: laai die keuselys en die studente.
  document.addEventListener('DOMContentLoaded', function () {
    loadKoshuisDropdown();   // vul die keuselys bo-aan die bladsy en laai die paneelbord
    loadStudenteCache();     // laai en bêre die studente vir die lys aan die regterkant
  });
})();
