/**
 * personeel.js — logic for personeel.html only.
 *
 * DEMO: alle klas- en bywoningsdata op hierdie blad is mock data.
 * Die backend het nog geen personeel↔klas koppeling of klasregister nie.
 * Bywoning word deterministies gegenereer (seed = klas + datum) sodat
 * dieselfde dag altyd dieselfde resultaat wys, sonder enige stoor.
 *
 * Depends on:
 *   - main.js (login gate + Personeel gate)
 *   - styles.css (.kalender* klasse)
 *   - HTML ids: klas-select, dash-datum, dash-in-count, dash-out-count,
 *     dash-total-count, dash-percent-count, dash-in-list, dash-out-list,
 *     kal-title, kal-prev, kal-next, kal-grid, roster-search, roster-list.
 */

(function () {
  // ----- Mock klasse met klasregisters (demo data) -----
  var MOCK_KLASSE = [
    {
      id: 'WIS114',
      naam: 'WIS114 — Klaskamer A',
      studente: [
        { naam: 'Anika',   van: 'Botha',           nommer: 'STU2024001' },
        { naam: 'Dewald',  van: 'Pretorius',       nommer: 'STU2024002' },
        { naam: 'Elmarie', van: 'van der Merwe',   nommer: 'STU2024003' },
        { naam: 'Francois', van: 'Joubert',        nommer: 'STU2024004' },
        { naam: 'Hannelie', van: 'Coetzee',        nommer: 'STU2024005' },
        { naam: 'Jaco',    van: 'Steyn',           nommer: 'STU2024006' },
        { naam: 'Karla',   van: 'du Plessis',      nommer: 'STU2024007' },
        { naam: 'Lourens', van: 'Venter',          nommer: 'STU2024008' },
        { naam: 'Mariska', van: 'Nel',             nommer: 'STU2024009' },
        { naam: 'Pieter',  van: 'Fourie',          nommer: 'STU2024010' },
        { naam: 'Rentia',  van: 'Swanepoel',       nommer: 'STU2024011' },
        { naam: 'Tiaan',   van: 'Kruger',          nommer: 'STU2024012' }
      ]
    },
    {
      id: 'FIS121',
      naam: 'FIS121 — Klaskamer B',
      studente: [
        { naam: 'Bernadette', van: 'Olivier',      nommer: 'STU2024013' },
        { naam: 'Christiaan', van: 'Bezuidenhout', nommer: 'STU2024014' },
        { naam: 'Elsabe',  van: 'Meyer',           nommer: 'STU2024015' },
        { naam: 'Gideon',  van: 'Erasmus',         nommer: 'STU2024016' },
        { naam: 'Ilse',    van: 'van Rensburg',    nommer: 'STU2024017' },
        { naam: 'Kobus',   van: 'Scholtz',         nommer: 'STU2024018' },
        { naam: 'Lizelle', van: 'Barnard',         nommer: 'STU2024019' },
        { naam: 'Neels',   van: 'Terblanche',      nommer: 'STU2024020' },
        { naam: 'Ronel',   van: 'Grobler',         nommer: 'STU2024021' },
        { naam: 'Wian',    van: 'de Klerk',        nommer: 'STU2024022' }
      ]
    },
    {
      id: 'RKN214',
      naam: 'RKN214 — Lokaal C',
      studente: [
        { naam: 'Adele',   van: 'Ferreira',        nommer: 'STU2024023' },
        { naam: 'Braam',   van: 'Viljoen',         nommer: 'STU2024024' },
        { naam: 'Chanel',  van: 'Roux',            nommer: 'STU2024025' },
        { naam: 'Divan',   van: 'Lombard',         nommer: 'STU2024026' },
        { naam: 'Este',    van: 'Marais',          nommer: 'STU2024027' },
        { naam: 'Gerhard', van: 'Odendaal',        nommer: 'STU2024028' },
        { naam: 'Janke',   van: 'Visagie',         nommer: 'STU2024029' },
        { naam: 'Marnus',  van: 'Bester',          nommer: 'STU2024030' },
        { naam: 'Nadia',   van: 'Strydom',         nommer: 'STU2024031' },
        { naam: 'Ruan',    van: 'le Roux',         nommer: 'STU2024032' },
        { naam: 'Zander',  van: 'Human',           nommer: 'STU2024033' }
      ]
    }
  ];

  // ----- Cached DOM nodes (null-safe checks before use) -----
  var klasSelect = document.getElementById('klas-select');
  var dashDatum = document.getElementById('dash-datum');
  var dashInCount = document.getElementById('dash-in-count');
  var dashOutCount = document.getElementById('dash-out-count');
  var dashTotalCount = document.getElementById('dash-total-count');
  var dashPercentCount = document.getElementById('dash-percent-count');
  var dashInList = document.getElementById('dash-in-list');
  var dashOutList = document.getElementById('dash-out-list');
  var kalTitle = document.getElementById('kal-title');
  var kalPrev = document.getElementById('kal-prev');
  var kalNext = document.getElementById('kal-next');
  var kalGrid = document.getElementById('kal-grid');
  var rosterSearch = document.getElementById('roster-search');
  var rosterList = document.getElementById('roster-list');

  // ----- Module state -----
  var vandag = new Date();
  vandag.setHours(0, 0, 0, 0);

  var currentKlas = MOCK_KLASSE[0];
  var selectedDate = new Date(vandag);
  var displayYear = vandag.getFullYear();
  var displayMonth = vandag.getMonth();

  var MAANDE = ['Januarie', 'Februarie', 'Maart', 'April', 'Mei', 'Junie',
                'Julie', 'Augustus', 'September', 'Oktober', 'November', 'Desember'];
  var DAG_NAME = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Sa', 'So'];

  // ----- Deterministiese "random" (seed = klas + datum) -----

  /** djb2-agtige string hash → 32-bit unsigned int. */
  function hashString(str) {
    var h = 5381;
    for (var i = 0; i < str.length; i++) {
      h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  /** mulberry32 PRNG — klein, vinnig, deterministies vir 'n gegewe seed. */
  function mulberry32(seed) {
    return function () {
      seed |= 0;
      seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function isoDate(d) {
    var m = String(d.getMonth() + 1);
    var dd = String(d.getDate());
    if (m.length < 2) m = '0' + m;
    if (dd.length < 2) dd = '0' + dd;
    return d.getFullYear() + '-' + m + '-' + dd;
  }

  function formatDatum(d) {
    return d.getDate() + ' ' + MAANDE[d.getMonth()] + ' ' + d.getFullYear();
  }

  /** Klasdae: weeksdae (Ma–Vr) wat nie in die toekoms lê nie. */
  function isKlasdag(d) {
    var dag = d.getDay(); // 0 = Sondag ... 6 = Saterdag
    return dag >= 1 && dag <= 5 && d.getTime() <= vandag.getTime();
  }

  /**
   * Deterministiese bywoning vir 'n klas op 'n datum.
   * Return null as daar geen klasdata is nie (naweek / toekoms), anders
   * { ingeskandeer: [{ student, tyd }], nieIngeskandeer: [student] }.
   */
  function kryBywoning(klas, datum) {
    if (!isKlasdag(datum)) return null;

    var rand = mulberry32(hashString(klas.id + '|' + isoDate(datum)));
    var ingeskandeer = [];
    var nieIngeskandeer = [];

    klas.studente.forEach(function (s) {
      if (rand() < 0.78) {
        var minuut = Math.floor(rand() * 25);
        ingeskandeer.push({
          student: s,
          tyd: '08:' + (minuut < 10 ? '0' : '') + minuut
        });
      } else {
        nieIngeskandeer.push(s);
      }
    });

    return { ingeskandeer: ingeskandeer, nieIngeskandeer: nieIngeskandeer };
  }

  // ----- Kaartjies (selfde markup as kampus.js user cards) -----
  function createStudentCard(student, subtitle) {
    var card = document.createElement('div');
    card.className = 'user-card';
    card.dataset.search = (student.naam + ' ' + student.van + ' ' + student.nommer).toLowerCase();

    var infoDiv = document.createElement('div');
    infoDiv.className = 'admin-user-info';

    var nameDiv = document.createElement('div');
    nameDiv.className = 'admin-user-name';
    nameDiv.textContent = student.naam + ' ' + student.van;
    infoDiv.appendChild(nameDiv);

    var subDiv = document.createElement('div');
    subDiv.className = 'admin-user-email';
    subDiv.textContent = subtitle || '';
    infoDiv.appendChild(subDiv);

    card.appendChild(infoDiv);
    return card;
  }

  function renderLeegBoodskap(container, boodskap) {
    container.innerHTML = '';
    var empty = document.createElement('div');
    empty.className = 'user-card';
    var info = document.createElement('div');
    info.className = 'admin-user-info';
    var msg = document.createElement('div');
    msg.className = 'admin-user-email';
    msg.textContent = boodskap;
    info.appendChild(msg);
    empty.appendChild(info);
    container.appendChild(empty);
  }

  // ----- Dashboard rendering -----
  function renderDashboard() {
    var bywoning = kryBywoning(currentKlas, selectedDate);

    if (dashDatum) dashDatum.textContent = formatDatum(selectedDate);
    if (dashTotalCount) dashTotalCount.textContent = 'Totaal studente: ' + currentKlas.studente.length;

    if (!bywoning) {
      if (dashInCount) dashInCount.textContent = 'Ingeskandeer: --';
      if (dashOutCount) dashOutCount.textContent = 'Nie ingeskandeer: --';
      if (dashPercentCount) dashPercentCount.textContent = 'Bywoning: --';
      if (dashInList) renderLeegBoodskap(dashInList, 'Geen klasdata vir hierdie dag nie.');
      if (dashOutList) renderLeegBoodskap(dashOutList, 'Geen klasdata vir hierdie dag nie.');
      return;
    }

    var totaal = currentKlas.studente.length;
    var persent = totaal > 0 ? Math.round((bywoning.ingeskandeer.length / totaal) * 100) : 0;

    if (dashInCount) dashInCount.textContent = 'Ingeskandeer: ' + bywoning.ingeskandeer.length;
    if (dashOutCount) dashOutCount.textContent = 'Nie ingeskandeer: ' + bywoning.nieIngeskandeer.length;
    if (dashPercentCount) dashPercentCount.textContent = 'Bywoning: ' + persent + '%';

    if (dashInList) {
      dashInList.innerHTML = '';
      if (bywoning.ingeskandeer.length === 0) {
        renderLeegBoodskap(dashInList, 'Geen studente ingeskandeer nie.');
      } else {
        bywoning.ingeskandeer.forEach(function (b) {
          dashInList.appendChild(
            createStudentCard(b.student, b.student.nommer + ' · ingeskandeer ' + b.tyd)
          );
        });
      }
    }

    if (dashOutList) {
      dashOutList.innerHTML = '';
      if (bywoning.nieIngeskandeer.length === 0) {
        renderLeegBoodskap(dashOutList, 'Alle studente is ingeskandeer.');
      } else {
        bywoning.nieIngeskandeer.forEach(function (s) {
          dashOutList.appendChild(createStudentCard(s, s.nommer));
        });
      }
    }
  }

  // ----- Kalender rendering -----
  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth() === b.getMonth() &&
           a.getDate() === b.getDate();
  }

  function renderKalender() {
    if (!kalGrid || !kalTitle) return;

    kalTitle.textContent = MAANDE[displayMonth] + ' ' + displayYear;
    kalGrid.innerHTML = '';

    // Dagname-ry (Ma ... So)
    DAG_NAME.forEach(function (naam) {
      var cell = document.createElement('div');
      cell.className = 'kalender-dagnaam';
      cell.textContent = naam;
      kalGrid.appendChild(cell);
    });

    var eerste = new Date(displayYear, displayMonth, 1);
    var offset = (eerste.getDay() + 6) % 7; // Maandag in die eerste kolom
    var daeInMaand = new Date(displayYear, displayMonth + 1, 0).getDate();

    for (var i = 0; i < offset; i++) {
      var leeg = document.createElement('div');
      leeg.className = 'kalender-dag kalender-dag--leeg';
      kalGrid.appendChild(leeg);
    }

    for (var d = 1; d <= daeInMaand; d++) {
      (function (dagNommer) {
        var datum = new Date(displayYear, displayMonth, dagNommer);

        var cell = document.createElement('button');
        cell.type = 'button';
        cell.className = 'kalender-dag';
        cell.textContent = String(dagNommer);

        if (sameDay(datum, vandag)) cell.classList.add('kalender-dag--vandag');
        if (sameDay(datum, selectedDate)) cell.classList.add('kalender-dag--gekies');
        if (isKlasdag(datum)) cell.classList.add('kalender-dag--klasdag');

        cell.addEventListener('click', function () {
          selectedDate = datum;
          renderKalender();
          renderDashboard();
        });

        kalGrid.appendChild(cell);
      })(d);
    }
  }

  // ----- Klasregister (regterpaneel-lys) -----
  function renderRoster() {
    if (!rosterList) return;
    rosterList.innerHTML = '';
    currentKlas.studente.forEach(function (s) {
      rosterList.appendChild(createStudentCard(s, s.nommer));
    });
    applyRosterFilter();
  }

  /** Hide roster rows that do not contain the search text. */
  function applyRosterFilter() {
    if (!rosterSearch || !rosterList) return;
    var query = rosterSearch.value.trim().toLowerCase();
    var rows = rosterList.querySelectorAll('.user-card');

    rows.forEach(function (row) {
      var searchable = row.dataset.search || (row.textContent || '').toLowerCase();
      row.style.display = (query === '' || searchable.includes(query)) ? '' : 'none';
    });
  }

  // ----- Klas dropdown -----
  function populateKlasSelect() {
    if (!klasSelect) return;
    klasSelect.innerHTML = '';
    MOCK_KLASSE.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = k.id;
      opt.textContent = k.naam;
      klasSelect.appendChild(opt);
    });
  }

  // ----- Event wiring -----
  if (klasSelect) {
    klasSelect.addEventListener('change', function () {
      var gekies = MOCK_KLASSE.filter(function (k) {
        return k.id === klasSelect.value;
      })[0];
      if (gekies) currentKlas = gekies;
      renderDashboard();
      renderRoster();
    });
  }

  if (kalPrev) {
    kalPrev.addEventListener('click', function () {
      displayMonth--;
      if (displayMonth < 0) {
        displayMonth = 11;
        displayYear--;
      }
      renderKalender();
    });
  }

  if (kalNext) {
    kalNext.addEventListener('click', function () {
      displayMonth++;
      if (displayMonth > 11) {
        displayMonth = 0;
        displayYear++;
      }
      renderKalender();
    });
  }

  if (rosterSearch) {
    rosterSearch.addEventListener('input', applyRosterFilter);
  }

  // ----- Bootstrap -----
  document.addEventListener('DOMContentLoaded', function () {
    populateKlasSelect();
    renderKalender();
    renderDashboard();
    renderRoster();
  });
})();
