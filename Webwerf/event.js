// =============================================================================
// event.js — Die Events-blad se logika.
//
// Wat dit doen, in eenvoudige woorde:
//   - Kry die events van GET /events?view= (komende of vorige) en wys hulle
//     as KPI-teëls, grafieke en 'n klikbare tabel. Die event wat nou aan die
//     gang is, word outomaties gekies.
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

  var viewSelect   = document.getElementById('events-view');
  var gasteTitel   = document.getElementById('gaste-titel');
  var eventKaart   = document.getElementById('event-kaart');
  var eventLeeg    = document.getElementById('event-leeg');
  var eventKop     = document.getElementById('event-kop');
  var eventNaam    = document.getElementById('event-naam');
  var eventNou     = document.getElementById('event-nou');
  var eventDetail  = document.getElementById('event-detail');
  var eventBeskryf = document.getElementById('event-beskrywing');
  var gasteCaption = document.getElementById('gaste-caption');

  // Hoe gereeld die gastelys en skandeerstatus vars gehou word (ms).
  var VERFRIS_MS = 10000;

  var MAANDE_KORT = ['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'];

  // Die status-etikette en -toon van 'n gas (toon = kleur van die status-kenteken).
  var STATUS = {
    HIER:     { etiket: 'Hier',             toon: 'goed' },
    VERTREK:  { etiket: 'Vertrek',          toon: 'waarsku' },
    NIE:      { etiket: 'Nog nie aangekom', toon: 'sleg' },
    ONBEKEND: { etiket: 'Geen skandering',  toon: 'neutraal' }
  };

  var events = [];          // die events wat tans gewys word
  var gekoseEvent = null;   // die event waarvan die gaste gewys word
  var gaste = [];           // die gekose event se gaste (met status)
  var verfrisTimer = null;
  var laaiTeller = 0;       // keer dat 'n ou antwoord 'n nuwe een oorskryf
  var eventTabel = null;
  var gasteTabel = null;

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

  // Hierdie funksie skryf die event se tydperk: "24 Aug 18:00 – 21:30"
  // (of met die tweede datum ook, as dit oor middernag strek).
  function formatTydperk(ev) {
    var b = leesTyd(ev.begin_tyd), e = leesTyd(ev.eind_tyd);
    if (!b) return '';
    if (!e) return formatTyd(ev.begin_tyd);
    var selfdeDag = b.toDateString() === e.toDateString();
    return formatTyd(ev.begin_tyd) + ' – ' +
      (selfdeDag ? pad(e.getHours()) + ':' + pad(e.getMinutes()) : formatTyd(ev.eind_tyd));
  }

  // Hierdie funksie sê of 'n event op hierdie oomblik aan die gang is.
  function isNouAanDieGang(ev) {
    var b = leesTyd(ev.begin_tyd), e = leesTyd(ev.eind_tyd);
    if (!b || !e) return false;
    var nou = Date.now();
    return ev.status !== 'GEKANSELLEER' && b.getTime() <= nou && nou <= e.getTime();
  }

  function eventStatus(ev) {
    if (ev.status === 'GEKANSELLEER') return { label: 'Gekanselleer', tone: 'sleg' };
    if (isNouAanDieGang(ev)) return { label: 'Nou', tone: 'goed' };
    var e = leesTyd(ev.eind_tyd);
    if (e && e.getTime() < Date.now()) return { label: 'Afgehandel', tone: 'neutraal' };
    return { label: 'Komende', tone: 'waarsku' };
  }

  // "STUDENT" -> "Student" (die bediener stuur rolle in hoofletters).
  function rolTeks(rol) {
    var s = String(rol || 'Gebruiker').replace(/_/g, ' ').toLowerCase();
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function stelTeks(id, teks) {
    var el = document.getElementById(id);
    if (el) el.textContent = teks;
  }

  // ----- Tabelle -----
  function maakTabelle() {
    if (!window.MoonStats) return;
    eventTabel = MoonStats.createTable(document.getElementById('events-tabel'), {
      columns: [
        { name: 'Geleentheid', format: 'teks' },
        { name: 'Kampus', format: 'teks' },
        { name: 'Lokaal', format: 'teks' },
        { name: 'Begin', format: 'datumtyd' },
        { name: "RSVP's", format: 'getal' },
        { name: 'Kapasiteit', format: 'getal' },
        { name: 'Status', format: 'status' }
      ],
      searchPlaceholder: 'Soek geleentheid of plek…',
      emptyText: 'Laai geleenthede…',
      pageSize: 25,
      onRowClick: function (r) { kiesEvent(r.ev); }
    });
    gasteTabel = MoonStats.createTable(document.getElementById('gaste-tabel'), {
      columns: [
        { name: 'Naam', format: 'teks' },
        { name: 'Rol', format: 'teks' },
        { name: 'Nommer', format: 'teks' },
        { name: 'Kontak', format: 'teks' },
        { name: 'RSVP-tyd', format: 'datumtyd' },
        { name: 'Status', format: 'status' }
      ],
      searchPlaceholder: 'Soek gas…',
      emptyText: 'Kies \'n geleentheid om die gaste te sien.',
      filters: [
        { label: 'Almal' },
        { label: 'Hier', test: function (r) { return r.status === 'HIER'; } },
        { label: 'Vertrek', test: function (r) { return r.status === 'VERTREK'; } },
        { label: 'Nog nie aangekom', test: function (r) { return r.status === 'NIE'; } },
        { label: 'Eksterne gaste', test: function (r) { return r.status === 'ONBEKEND'; } }
      ]
    });
  }

  // ----- Events -----

  // Hierdie funksie laai die events vir die gekose aansig.
  async function laaiEvents() {
    if (!window.MoonApi || !eventTabel) return;

    var view = viewSelect ? viewSelect.value : 'komende';
    var json = await window.MoonApi.fetchEvents(view);

    if (!json || !json.sukses || !Array.isArray(json.data)) {
      eventTabel.setRows([]);
      eventTabel.setNote('Kon nie die geleenthede laai nie.');
      return;
    }

    events = json.data;
    stelTeks('events-titel-teks', view === 'vorige' ? 'Vorige geleenthede' : 'Komende geleenthede');
    stelTeks('events-telling', String(events.length));
    eventTabel.setNote('');
    tekenEvents();

    if (events.length === 0) {
      kiesEvent(null);
      return;
    }

    // Kies outomaties: die event wat nou aan die gang is, anders die eerste
    // (of hou die een wat reeds gekies was as dit nog in die lys is).
    var bestaande = gekoseEvent && events.find(function (ev) { return ev.event_id === gekoseEvent.event_id; });
    var nou = events.find(isNouAanDieGang);
    kiesEvent(nou || bestaande || events[0]);
  }

  // Hierdie funksie teken die KPI-teëls, die oorsiggrafieke en die events-tabel.
  function tekenEvents() {
    var aktief = events.filter(function (ev) { return ev.status !== 'GEKANSELLEER'; });
    var bespreek = 0, kapasiteit = 0;
    aktief.forEach(function (ev) {
      bespreek += Number(ev.rsvp_aantal) || 0;
      kapasiteit += Number(ev.kapasiteit) || 0;
    });
    stelTeks('kpi-events', String(events.length));
    stelTeks('kpi-nou', String(events.filter(isNouAanDieGang).length));
    stelTeks('kpi-rsvp', String(bespreek));
    stelTeks('kpi-plekke', String(Math.max(kapasiteit - bespreek, 0)));

    tekenOorsigGrafieke();

    eventTabel.setRows(events.map(function (ev) {
      return {
        key: ev.event_id,
        ev: ev,
        cells: [
          ev.naam, ev.kampus_naam || null, ev.lokasie_naam || null, leesTyd(ev.begin_tyd),
          Number(ev.rsvp_aantal) || 0, Number(ev.kapasiteit) || 0, eventStatus(ev)
        ]
      };
    }));
    eventTabel.setSelected(gekoseEvent ? gekoseEvent.event_id : null);
  }

  function tekenOorsigGrafieke() {
    if (!window.MoonStats) return;
    var c = MoonStats.colors;
    var aktief = events.filter(function (ev) { return ev.status !== 'GEKANSELLEER'; });
    var bespreek = 0, kapasiteit = 0;
    aktief.forEach(function (ev) {
      bespreek += Number(ev.rsvp_aantal) || 0;
      kapasiteit += Number(ev.kapasiteit) || 0;
    });

    MoonStats.renderDonut(document.getElementById('stat-plekke-donut'), {
      title: 'Plekke',
      segments: [
        { label: 'Bespreek', value: bespreek, color: c.series1 },
        { label: 'Oop', value: Math.max(kapasiteit - bespreek, 0), color: c.dim }
      ]
    });

    MoonStats.renderBarsH(document.getElementById('stat-bespreking-balke'), {
      items: aktief.slice(0, 8).map(function (ev) {
        var kap = Number(ev.kapasiteit) || 0;
        var naam = ev.naam || '';
        return {
          label: naam.length > 22 ? naam.slice(0, 21) + '…' : naam,
          value: kap ?Math.round(((Number(ev.rsvp_aantal) || 0) / kap) * 100) : 0,
          detail: (ev.rsvp_aantal || 0) + ' van ' + kap + ' plekke'
        };
      }),
      max: 100,
      fmtValue: function (v) { return v + '%'; }
    });
  }

  // ----- Gekose event en gaste -----

  // Hierdie funksie kies 'n event: wys sy besonderhede en laai sy gaste.
  function kiesEvent(ev) {
    gekoseEvent = ev || null;
    if (eventTabel) eventTabel.setSelected(gekoseEvent ? gekoseEvent.event_id : null);
    stopVerfris();

    if (!gekoseEvent) {
      if (eventKaart) eventKaart.hidden = true;
      if (eventLeeg) eventLeeg.hidden = false;
      gaste = [];
      stelTeks('gaste-telling', '');
      if (gasteTabel) gasteTabel.setRows([]);
      return;
    }

    if (eventKaart) eventKaart.hidden = false;
    if (eventLeeg) eventLeeg.hidden = true;
    wysEventKop(gekoseEvent);
    if (gasteTabel) gasteTabel.setNote('Laai gaste…');
    laaiGaste();
    verfrisTimer = setInterval(laaiGaste, VERFRIS_MS);
  }

  function stopVerfris() {
    if (verfrisTimer) { clearInterval(verfrisTimer); verfrisTimer = null; }
  }

  // Hierdie funksie wys die gekose event se naam, plek, tyd en beskrywing.
  function wysEventKop(ev) {
    if (!eventKop) return;
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
    if (gasteTitel) gasteTitel.firstChild.textContent = 'Gaste — ' + (ev.naam || '') + ' ';
  }

  // Hierdie funksie laai die gastelys én die kampus se skandeerstatus vir die
  // gekose event, werk elke gas se status uit en teken alles.
  async function laaiGaste() {
    if (!window.MoonApi || !gekoseEvent || !gasteTabel) return;
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
      gaste = [];
      gasteTabel.setRows([]);
      tekenGasteOpsomming();
      gasteTabel.setNote(rsvpJson && rsvpJson.status === 403
        ? 'Net \'n Administrateur, of die opsigter van hierdie geleentheid se kampus, mag die gastelys sien.'
        : 'Kon nie die gastelys laai nie' + (rsvpJson && rsvpJson.fout ? ': ' + rsvpJson.fout : '.'));
      return;
    }

    // Die bediener stuur die event se nuutste syfers saam — hou die kop vars
    if (rsvpJson.data.event) {
      gekoseEvent = Object.assign({}, ev, rsvpJson.data.event);
      wysEventKop(gekoseEvent);
      var i = events.findIndex(function (x) { return x.event_id === ev.event_id; });
      if (i !== -1) {
        events[i] = gekoseEvent;
        tekenEvents();
      }
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

  // Hierdie funksie tel die statusse en teken die bywoning-sirkeldiagram.
  function tekenGasteOpsomming() {
    var tel = { HIER: 0, VERTREK: 0, NIE: 0, ONBEKEND: 0 };
    gaste.forEach(function (g) { tel[g.status] = (tel[g.status] || 0) + 1; });
    stelTeks('gaste-telling', String(gaste.length));

    if (window.MoonStats) {
      var c = MoonStats.colors;
      MoonStats.renderDonut(document.getElementById('stat-gaste-donut'), {
        title: 'Bywoning',
        segments: [
          { label: 'Hier',             value: tel.HIER,     color: c.series1 },
          { label: 'Vertrek',          value: tel.VERTREK,  color: c.warning },
          { label: 'Nog nie aangekom', value: tel.NIE,      color: c.dim },
          { label: 'Eksterne gaste',   value: tel.ONBEKEND, color: c.series2 }
        ]
      });
    }
    if (gasteCaption) {
      var ev = gekoseEvent || {};
      var appTel = typeof ev.app_rsvp_aantal === 'number' ? ev.app_rsvp_aantal : gaste.length - tel.ONBEKEND;
      var eksTel = typeof ev.eksterne_rsvp_aantal === 'number' ? ev.eksterne_rsvp_aantal : tel.ONBEKEND;
      gasteCaption.textContent =
        tel.HIER + ' van ' + gaste.length + ' gaste is hier · ' +
        appTel + ' app-RSVP\'s · ' + eksTel + ' eksterne gaste (plus 1\'s). ' +
        'Eksterne gaste skandeer nie in nie, so hul status is onbekend.';
    }
  }

  // Hierdie funksie vul die gastetabel: elke gas met rol, nommer en status.
  function tekenGaste() {
    gasteTabel.setNote('');
    gasteTabel.setRows(gaste.map(function (gas, i) {
      var st = STATUS[gas.status] || STATUS.NIE;
      var kontak = gas.epos || (gas.selfoon && gas.selfoon !== gas.nommer ? gas.selfoon : null);
      return {
        key: gas.gebruiker_id !== null && gas.gebruiker_id !== undefined ? 'g' + gas.gebruiker_id : 'e' + i,
        status: gas.status,
        cells: [
          gas.volle_naam || '--',
          gas.ekstern ? 'Plus 1' : rolTeks(gas.rol),
          gas.nommer || null,
          kontak,
          leesTyd(gas.rsvp_tyd),
          { label: st.etiket, tone: st.toon }
        ]
      };
    }));
    if (!gaste.length) gasteTabel.setNote('Nog niemand het vir hierdie geleentheid RSVP nie.');
  }

  // Teken die grafieke oor as die venster verander of die tema wissel.
  function herteken() {
    tekenOorsigGrafieke();
    if (gekoseEvent) tekenGasteOpsomming();
  }

  // ----- Gebeurtenisse en begin -----
  if (viewSelect) viewSelect.addEventListener('change', laaiEvents);

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
    maakTabelle();
    laaiEvents();

    var grootteTyd = null;
    window.addEventListener('resize', function () {
      clearTimeout(grootteTyd);
      grootteTyd = setTimeout(herteken, 150);
    });
    new MutationObserver(herteken).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
  }

  document.addEventListener('DOMContentLoaded', begin);
})();
