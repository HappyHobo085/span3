// =============================================================================
// event.js — Die Events-blad se logika: laai die gebeure van die bediener af.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die events van GET /events?view= (komende of vorige).
//   - Wys elkeen as 'n kaartjie met naam, plek, tyd en plekke oor.
//   - Die soekveld filtreer die lys terwyl jy tik.
// =============================================================================

(function () {
  'use strict';

  var viewSelect = document.getElementById('events-view');
  var eventsLys = document.getElementById('events-lys');
  var eventsTitel = document.getElementById('events-titel');
  var listSearch = document.getElementById('list-search');

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

  // Hierdie funksie wys 'n boodskap in die lys (bv. "geen events nie").
  function wysBoodskap(boodskap) {
    if (!eventsLys) return;
    eventsLys.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'viz-empty';
    div.textContent = boodskap;
    eventsLys.appendChild(div);
  }

  // Hierdie funksie laai die events vir die gekose aansig en teken die kaartjies.
  async function laaiEvents() {
    if (!window.MoonApi || !eventsLys) return;

    var view = viewSelect ? viewSelect.value : 'komende';
    var json = await window.MoonApi.fetchEvents(view);

    if (!json || !json.sukses || !Array.isArray(json.data)) {
      wysBoodskap('Kon nie die events laai nie.');
      return;
    }

    if (eventsTitel) {
      eventsTitel.innerHTML = '';
      eventsTitel.appendChild(document.createTextNode(
        (view === 'vorige' ? 'Vorige Events ' : 'Komende Events ')));
      var telling = document.createElement('span');
      telling.className = 'panel-count';
      telling.textContent = String(json.data.length);
      eventsTitel.appendChild(telling);
    }

    eventsLys.innerHTML = '';
    if (json.data.length === 0) {
      wysBoodskap(view === 'vorige' ? 'Geen vorige events nie.' : 'Geen komende events nie.');
      return;
    }

    json.data.forEach(function (ev) {
      var kaart = document.createElement('div');
      kaart.className = 'user-card';
      kaart.dataset.search = (
        (ev.naam || '') + ' ' + (ev.kampus_naam || '') + ' ' + (ev.lokasie_naam || '')
      ).toLowerCase();

      var info = document.createElement('div');
      info.className = 'admin-user-info';

      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = ev.naam;
      info.appendChild(naam);

      var detail = document.createElement('div');
      detail.className = 'admin-user-email';
      var plek = (ev.kampus_naam || '') + (ev.lokasie_naam ? ' · ' + ev.lokasie_naam : '');
      detail.textContent = plek + ' · ' + formatTyd(ev.begin_tyd);
      info.appendChild(detail);
      kaart.appendChild(info);

      var plekke = document.createElement('div');
      plekke.className = 'campus-badge';
      plekke.textContent = ev.vol ? 'Vol' : (ev.plekke_oor + ' plekke oor');
      kaart.appendChild(plekke);

      eventsLys.appendChild(kaart);
    });

    pasFilterToe();
  }

  // Hierdie funksie steek kaartjies weg wat nie by die soekwoord pas nie.
  function pasFilterToe() {
    if (!listSearch || !eventsLys) return;
    var query = listSearch.value.trim().toLowerCase();
    eventsLys.querySelectorAll('.user-card').forEach(function (kaart) {
      var soekbaar = kaart.dataset.search || '';
      kaart.style.display = (query === '' || soekbaar.includes(query)) ? '' : 'none';
    });
  }

  if (viewSelect) viewSelect.addEventListener('change', laaiEvents);
  if (listSearch) listSearch.addEventListener('input', pasFilterToe);

  // Wag totdat die API-lêer gelaai is (main.js laai dit dinamies).
  function begin() {
    if (!window.MoonApi) {
      window.addEventListener('load', begin, { once: true });
      return;
    }
    laaiEvents();
  }

  document.addEventListener('DOMContentLoaded', begin);
})();
