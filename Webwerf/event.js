// =============================================================================
// event.js — Die Events-blad se logika.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die events van GET /events?view= (komende of vorige) en wys elkeen
//     as 'n klikbare kaartjie links. Die event wat nou aan die gang is, word
//     outomaties gekies en gemerk.
//   - Vir die gekose event kry dit die gastelys van GET /events/{id}/rsvps:
//     app-gebruikers (studente/personeel wat RSVP het) én eksterne gaste
//     ("plus 1's" wat via die deel-skakel RSVP het).
//   - Wie "hier" is en wie "vertrek" het, kom van die kampus se skandeerstatus
//     (GET /kampusse/{id}/status): 'n gas se laaste skandering by die event
//     se kampus bepaal sy/haar status. Eksterne gaste skandeer nie, so hulle
//     wys as "geen skandering".
//   - Alles word elke paar sekondes vars gehou terwyl 'n event gekies is.
// =============================================================================

(function () {
  'use strict';

  var viewSelect  = document.getElementById('events-view');
  var eventsLys   = document.getElementById('events-lys');
  var eventsTitel = document.getElementById('events-titel');
  var listSearch  = document.getElementById('list-search');

  var gasteTitel   = document.getElementById('gaste-titel');
  var gasteLys     = document.getElementById('gaste-lys');
  var gasteSearch  = document.getElementById('gaste-search');
  var gasteFilter  = document.getElementById('gaste-filter');
  var gasteFilters = document.getElementById('gaste-filters');
  var gasteStats   = document.getElementById('gaste-stats-card');
  var gasteCaption = document.getElementById('gaste-caption');
  var eventKop     = document.getElementById('event-kop');
  var eventNaam    = document.getElementById('event-naam');
  var eventNou     = document.getElementById('event-nou');
  var eventDetail  = document.getElementById('event-detail');
  var eventBeskryf = document.getElementById('event-beskrywing');

  // Hoe gereeld die gastelys en skandeerstatus vars gehou word (ms).
  var VERFRIS_MS = 10000;

  var MAANDE_KORT = ['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'];

  // Die status-etikette en -kleure van 'n gas.
  var STATUS = {
    HIER:     { etiket: 'Hier',              klas: 'status-badge--active' },
    VERTREK:  { etiket: 'Vertrek',           klas: 'status-badge--vertrek' },
    NIE:      { etiket: 'Nog nie aangekom',  klas: 'status-badge--inactive' },
    ONBEKEND: { etiket: 'Geen skandering',   klas: 'status-badge--onbekend' }
  };

  var events = [];          // die events wat tans links gewys word
  var gekoseEvent = null;   // die event waarvan die gaste regs gewys word
  var gaste = [];           // die gekose event se gaste (met status)
  var verfrisTimer = null;
  var laaiTeller = 0;       // keer dat 'n ou antwoord 'n nuwe een oorskryf

  // ----- Hulpfunksies -----

  // Hierdie funksie lees 'n tyd van die bediener. Tye sonder 'n tydsone
  // (bv. die skandeerstatus se Tydstempel) is UTC, so ons sit 'Z' agteraan.
  function leesTyd(iso) {
    if (!iso) return null;
    var s = String(iso);
    if (!/[zZ]|[+-]\d\d:?\d\d$/.test(s)) s += 'Z';
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  // Hierdie funksie skryf 'n tyd as bv. "24 Aug 18:00" (plaaslike tyd).
  function formatTyd(iso) {
    var d = leesTyd(iso);
    if (!d) return '';
    return d.getDate() + ' ' + MAANDE_KORT[d.getMonth()] + ' ' +
      pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  // Hierdie funksie skryf net die uur, bv. "21:30".
  function formatUur(iso) {
    var d = leesTyd(iso);
    return d ? pad(d.getHours()) + ':' + pad(d.getMinutes()) : '';
  }

  // Hierdie funksie skryf die event se tydperk: "24 Aug 18:00 – 21:30"
  // (of met die tweede datum ook, as dit oor middernag strek).
  function formatTydperk(ev) {
    var b = leesTyd(ev.begin_tyd), e = leesTyd(ev.eind_tyd);
    if (!b) return '';
    if (!e) return formatTyd(ev.begin_tyd);
    var selfdeDag = b.toDateString() === e.toDateString();
    return formatTyd(ev.begin_tyd) + ' – ' + (selfdeDag ? formatUur(ev.eind_tyd) : formatTyd(ev.eind_tyd));
  }

  // Hierdie funksie sê of 'n event op hierdie oomblik aan die gang is.
  function isNouAanDieGang(ev) {
    var b = leesTyd(ev.begin_tyd), e = leesTyd(ev.eind_tyd);
    if (!b || !e) return false;
    var nou = Date.now();
    return ev.status !== 'GEKANSELLEER' && b.getTime() <= nou && nou <= e.getTime();
  }

  // Hierdie funksie wys 'n boodskap in 'n lys (bv. "geen events nie").
  function wysBoodskap(houer, boodskap) {
    if (!houer) return;
    houer.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'viz-empty';
    div.textContent = boodskap;
    houer.appendChild(div);
  }

  // Hierdie funksie sit 'n telling langs 'n opskrif, bv. "Gaste 12".
  function stelTitel(el, teks, telling) {
    if (!el) return;
    el.innerHTML = '';
    el.appendChild(document.createTextNode(teks + ' '));
    if (telling !== null && telling !== undefined) {
      var span = document.createElement('span');
      span.className = 'panel-count';
      span.textContent = String(telling);
      el.appendChild(span);
    }
  }

  // ----- Events (linkerpaneel) -----

  // Hierdie funksie laai die events vir die gekose aansig en teken die kaartjies.
  async function laaiEvents() {
    if (!window.MoonApi || !eventsLys) return;

    var view = viewSelect ? viewSelect.value : 'komende';
    var json = await window.MoonApi.fetchEvents(view);

    if (!json || !json.sukses || !Array.isArray(json.data)) {
      wysBoodskap(eventsLys, 'Kon nie die events laai nie.');
      return;
    }

    events = json.data;
    stelTitel(eventsTitel, view === 'vorige' ? 'Vorige Events' : 'Komende Events', events.length);

    if (events.length === 0) {
      wysBoodskap(eventsLys, view === 'vorige' ? 'Geen vorige events nie.' : 'Geen komende events nie.');
      kiesEvent(null);
      return;
    }

    tekenEvents();

    // Kies outomaties: die event wat nou aan die gang is, anders die eerste
    // (of hou die een wat reeds gekies was as dit nog in die lys is).
    var bestaande = gekoseEvent && events.find(function (ev) { return ev.event_id === gekoseEvent.event_id; });
    var nou = events.find(isNouAanDieGang);
    kiesEvent(nou || bestaande || events[0]);
  }

  // Hierdie funksie teken die events se kaartjies links.
  function tekenEvents() {
    eventsLys.innerHTML = '';
    events.forEach(function (ev) {
      var kaart = document.createElement('div');
      kaart.className = 'user-card user-card--klikbaar';
      kaart.dataset.eventId = String(ev.event_id);
      kaart.dataset.search = (
        (ev.naam || '') + ' ' + (ev.kampus_naam || '') + ' ' + (ev.lokasie_naam || '')
      ).toLowerCase();
      kaart.setAttribute('role', 'button');
      kaart.setAttribute('tabindex', '0');
      kaart.setAttribute('aria-label', 'Wys gaste vir ' + ev.naam);

      var info = document.createElement('div');
      info.className = 'admin-user-info';

      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = ev.naam;
      if (isNouAanDieGang(ev)) {
        var nouChip = document.createElement('span');
        nouChip.className = 'status-badge status-badge--active';
        nouChip.innerHTML = '<span class="status-dot"></span>Nou';
        naam.appendChild(nouChip);
      } else if (ev.status === 'GEKANSELLEER') {
        var kanChip = document.createElement('span');
        kanChip.className = 'status-badge status-badge--inactive';
        kanChip.innerHTML = '<span class="status-dot"></span>Gekanselleer';
        naam.appendChild(kanChip);
      }
      info.appendChild(naam);

      var detail = document.createElement('div');
      detail.className = 'admin-user-email';
      var plek = (ev.kampus_naam || '') + (ev.lokasie_naam ? ' · ' + ev.lokasie_naam : '');
      detail.textContent = plek + ' · ' + formatTydperk(ev);
      info.appendChild(detail);
      kaart.appendChild(info);

      var plekke = document.createElement('div');
      plekke.className = 'campus-badge';
      plekke.textContent = (ev.rsvp_aantal || 0) + ' / ' + (ev.kapasiteit || 0) + ' RSVP';
      kaart.appendChild(plekke);

      kaart.addEventListener('click', function () { kiesEvent(ev); });
      kaart.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); kiesEvent(ev); }
      });

      eventsLys.appendChild(kaart);
    });
    pasEventFilterToe();
    merkGekoseEvent();
  }

  // Hierdie funksie merk die gekose event se kaartjie met 'n aksent-rand.
  function merkGekoseEvent() {
    if (!eventsLys) return;
    eventsLys.querySelectorAll('.user-card').forEach(function (kaart) {
      var gekies = !!gekoseEvent && kaart.dataset.eventId === String(gekoseEvent.event_id);
      kaart.classList.toggle('user-card--gekies', gekies);
      kaart.setAttribute('aria-pressed', gekies ? 'true' : 'false');
    });
  }

  // Hierdie funksie steek kaartjies weg wat nie by die soekwoord pas nie.
  function pasEventFilterToe() {
    if (!listSearch || !eventsLys) return;
    var query = listSearch.value.trim().toLowerCase();
    eventsLys.querySelectorAll('.user-card').forEach(function (kaart) {
      var soekbaar = kaart.dataset.search || '';
      kaart.style.display = (query === '' || soekbaar.includes(query)) ? '' : 'none';
    });
  }

  // ----- Gekose event en gaste (regterpaneel) -----

  // Hierdie funksie kies 'n event: wys sy besonderhede en laai sy gaste.
  function kiesEvent(ev) {
    gekoseEvent = ev || null;
    merkGekoseEvent();
    stopVerfris();

    if (!gekoseEvent) {
      stelTitel(gasteTitel, 'Gaste', null);
      if (eventKop) eventKop.hidden = true;
      if (gasteStats) gasteStats.hidden = true;
      if (gasteFilters) gasteFilters.hidden = true;
      wysBoodskap(gasteLys, 'Kies \'n event links om sy gaste te sien.');
      return;
    }

    wysEventKop(gekoseEvent);
    wysBoodskap(gasteLys, 'Laai gaste...');
    laaiGaste();
    verfrisTimer = setInterval(laaiGaste, VERFRIS_MS);
  }

  function stopVerfris() {
    if (verfrisTimer) { clearInterval(verfrisTimer); verfrisTimer = null; }
  }

  // Hierdie funksie wys die gekose event se naam, plek, tyd en beskrywing.
  function wysEventKop(ev) {
    if (!eventKop) return;
    eventKop.hidden = false;
    eventNaam.textContent = ev.naam || '--';
    eventNou.hidden = !isNouAanDieGang(ev);

    var dele = [];
    var plek = (ev.kampus_naam || '') + (ev.lokasie_naam ? ' · ' + ev.lokasie_naam : '');
    if (plek) dele.push(plek);
    dele.push(formatTydperk(ev));
    dele.push((ev.rsvp_aantal || 0) + ' van ' + (ev.kapasiteit || 0) + ' plekke bespreek');
    if (ev.status === 'GEKANSELLEER') dele.push('GEKANSELLEER');
    eventDetail.textContent = dele.join(' · ');

    var beskrywing = (ev.beskrywing || '').trim();
    eventBeskryf.hidden = !beskrywing;
    eventBeskryf.textContent = beskrywing;
  }

  // Hierdie funksie laai die gastelys én die kampus se skandeerstatus vir die
  // gekose event, werk elke gas se status uit en teken alles.
  async function laaiGaste() {
    if (!window.MoonApi || !gekoseEvent || !gasteLys) return;
    var ev = gekoseEvent;
    var teller = ++laaiTeller;

    var resultate = await Promise.all([
      window.MoonApi.fetchEventRsvps(ev.event_id),
      ev.kampus_id ? window.MoonApi.fetchKampusStatus(ev.kampus_id).catch(function () { return null; }) : null
    ]);

    // 'n Ander event is intussen gekies — gooi hierdie antwoord weg
    if (teller !== laaiTeller || !gekoseEvent || gekoseEvent.event_id !== ev.event_id) return;

    var rsvpJson = resultate[0];
    var statusJson = resultate[1];

    if (!rsvpJson || !rsvpJson.sukses || !rsvpJson.data) {
      if (gasteStats) gasteStats.hidden = true;
      if (gasteFilters) gasteFilters.hidden = true;
      stelTitel(gasteTitel, 'Gaste', null);
      if (rsvpJson && rsvpJson.status === 403) {
        wysBoodskap(gasteLys, 'Slegs \'n Administrateur of Kampus-opsigter mag die gastelys sien.');
      } else {
        wysBoodskap(gasteLys, 'Kon nie die gastelys laai nie' +
          (rsvpJson && rsvpJson.fout ? ': ' + rsvpJson.fout : '.'));
      }
      return;
    }

    // Die bediener stuur die event se nuutste syfers saam — hou die kop vars
    if (rsvpJson.data.event) {
      gekoseEvent = Object.assign({}, ev, rsvpJson.data.event);
      wysEventKop(gekoseEvent);
      var i = events.findIndex(function (x) { return x.event_id === ev.event_id; });
      if (i !== -1) events[i] = gekoseEvent;
    }

    var skanderings = bouSkandeerKaart(statusJson);
    gaste = (rsvpJson.data.rsvps || []).map(function (gas) {
      return Object.assign({}, gas, { status: bepaalStatus(gas, skanderings, gekoseEvent) });
    });

    tekenGasteOpsomming();
    tekenGaste();
  }

  // Hierdie funksie maak 'n kaart van gebruiker-ID na sy/haar laaste
  // skandering by die event se kampus (rigting IN/UIT en tyd).
  function bouSkandeerKaart(statusJson) {
    var kaart = {};
    var data = statusJson && statusJson.sukses && statusJson.data ? statusJson.data : null;
    if (!data) return kaart;
    (data.scanned_in || []).concat(data.scanned_out || []).forEach(function (u) {
      if (u && u.Gebruiker_ID !== undefined) {
        kaart[u.Gebruiker_ID] = { rigting: u.Rigting, tyd: leesTyd(u.Tydstempel) };
      }
    });
    return kaart;
  }

  // Hierdie funksie besluit 'n gas se status:
  //   - eksterne gas (plus 1): skandeer nie → ONBEKEND
  //   - laaste skandering is IN → HIER
  //   - laaste skandering is UIT ná die event se begin → VERTREK
  //   - anders (geen skandering, of 'n ou UIT van voor die event) → NIE
  function bepaalStatus(gas, skanderings, ev) {
    if (gas.ekstern || gas.gebruiker_id === null || gas.gebruiker_id === undefined) return 'ONBEKEND';
    var log = skanderings[gas.gebruiker_id];
    if (!log) return 'NIE';
    if (log.rigting === 'IN') return 'HIER';
    var begin = leesTyd(ev.begin_tyd);
    if (log.tyd && begin && log.tyd.getTime() >= begin.getTime()) return 'VERTREK';
    return 'NIE';
  }

  // Hierdie funksie tel die statusse en teken die verdeling-balk bo die lys.
  function tekenGasteOpsomming() {
    var tel = { HIER: 0, VERTREK: 0, NIE: 0, ONBEKEND: 0 };
    gaste.forEach(function (g) { tel[g.status] = (tel[g.status] || 0) + 1; });

    stelTitel(gasteTitel, 'Gaste', gaste.length);
    if (gasteFilters) gasteFilters.hidden = false;
    if (!gasteStats) return;
    gasteStats.hidden = false;

    if (window.MoonStats) {
      var c = MoonStats.colors;
      MoonStats.renderSplitBar(document.getElementById('stat-gaste-split'), {
        title: 'Bywoning',
        total: gaste.length,
        segments: [
          { label: 'Hier',             value: tel.HIER,     color: c.series1 },
          { label: 'Vertrek',          value: tel.VERTREK,  color: c.warning },
          { label: 'Nog nie aangekom', value: tel.NIE,      color: c.dim },
          { label: 'Eksterne gaste',   value: tel.ONBEKEND, color: c.series2 }
        ]
      });
    }
    if (gasteCaption) {
      var appTel = rsvpTelling('app_rsvp_aantal', gaste.length - tel.ONBEKEND);
      var eksTel = rsvpTelling('eksterne_rsvp_aantal', tel.ONBEKEND);
      gasteCaption.textContent =
        tel.HIER + ' van ' + gaste.length + ' gaste is hier · ' +
        appTel + ' app-RSVP\'s · ' + eksTel + ' eksterne gaste (plus 1\'s). ' +
        'Eksterne gaste skandeer nie in nie, so hul status is onbekend.';
    }
  }

  function rsvpTelling(veld, verstek) {
    var ev = gekoseEvent || {};
    return typeof ev[veld] === 'number' ? ev[veld] : verstek;
  }

  // Hierdie funksie teken die gastelys: elke gas met rol, nommer en status.
  function tekenGaste() {
    gasteLys.innerHTML = '';
    if (gaste.length === 0) {
      wysBoodskap(gasteLys, 'Nog niemand het vir hierdie event RSVP nie.');
      return;
    }

    gaste.forEach(function (gas) {
      var kaart = document.createElement('div');
      kaart.className = 'user-card';
      kaart.dataset.status = gas.status;
      kaart.dataset.search = (
        (gas.volle_naam || '') + ' ' + (gas.nommer || '') + ' ' + (gas.epos || '') + ' ' + (gas.rol || '')
      ).toLowerCase();

      var info = document.createElement('div');
      info.className = 'admin-user-info';

      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = gas.volle_naam || '--';
      var st = STATUS[gas.status] || STATUS.NIE;
      var badge = document.createElement('span');
      badge.className = 'status-badge ' + st.klas;
      badge.innerHTML = '<span class="status-dot"></span>';
      badge.appendChild(document.createTextNode(st.etiket));
      naam.appendChild(badge);
      info.appendChild(naam);

      var detail = document.createElement('div');
      detail.className = 'admin-user-email';
      var dele = [];
      if (gas.nommer) dele.push(gas.nommer);
      if (gas.epos) dele.push(gas.epos);
      else if (gas.selfoon && gas.selfoon !== gas.nommer) dele.push(gas.selfoon);
      if (gas.rsvp_tyd) dele.push('RSVP ' + formatTyd(gas.rsvp_tyd));
      detail.textContent = dele.join(' · ');
      info.appendChild(detail);
      kaart.appendChild(info);

      var rol = document.createElement('span');
      var rolNaam = gas.ekstern ? 'Plus 1' : (gas.rol || 'Gebruiker');
      rol.className = 'role-badge role-badge--' + rolNaam.toLowerCase().replace(/[\s_]+/g, '');
      rol.textContent = rolNaam;
      kaart.appendChild(rol);

      gasteLys.appendChild(kaart);
    });

    pasGasteFilterToe();
  }

  // Hierdie funksie steek gaste weg wat nie by die soekwoord of status pas nie.
  function pasGasteFilterToe() {
    if (!gasteLys) return;
    var query = gasteSearch ? gasteSearch.value.trim().toLowerCase() : '';
    var status = gasteFilter ? gasteFilter.value : 'ALMAL';
    var sigbaar = 0;
    gasteLys.querySelectorAll('.user-card').forEach(function (kaart) {
      var pas = (query === '' || (kaart.dataset.search || '').includes(query)) &&
                (status === 'ALMAL' || kaart.dataset.status === status);
      kaart.style.display = pas ? '' : 'none';
      if (pas) sigbaar++;
    });
    var leeg = gasteLys.querySelector('.gaste-leeg');
    if (sigbaar === 0 && gaste.length > 0) {
      if (!leeg) {
        leeg = document.createElement('div');
        leeg.className = 'viz-empty gaste-leeg';
        leeg.textContent = 'Geen gaste pas by die filter nie.';
        gasteLys.appendChild(leeg);
      }
    } else if (leeg) {
      leeg.remove();
    }
  }

  // ----- Gebeurtenisse en begin -----
  if (viewSelect) viewSelect.addEventListener('change', laaiEvents);
  if (listSearch) listSearch.addEventListener('input', pasEventFilterToe);
  if (gasteSearch) gasteSearch.addEventListener('input', pasGasteFilterToe);
  if (gasteFilter) gasteFilter.addEventListener('change', pasGasteFilterToe);

  // Moenie in die agtergrond bly verfris as die blad nie sigbaar is nie
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { stopVerfris(); }
    else if (gekoseEvent && !verfrisTimer) {
      laaiGaste();
      verfrisTimer = setInterval(laaiGaste, VERFRIS_MS);
    }
  });

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
