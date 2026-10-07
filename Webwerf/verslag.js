// =============================================================================
// verslag.js — Die Verslag-bladsy (verslag.html).
//
// Wat dit doen, in eenvoudige woorde:
//   1. Laai die verslag se data vir die gekose tydperk (GET /verslae/bywoning/oorsig).
//   2. Wys elke afdeling (Kampus, Koshuis, Events — of Klas vir personeel) as
//      'n oortjie met KPI-teëls, sirkeldiagramme, grafieke en soekbare lyste.
//      Die oortjies is dieselfde as die tabs in die Excel-lêer.
//   3. Die "Laai verslag af"-knoppie regs-bo laai dieselfde data af as
//      Excel, PDF, Word of teks (GET /verslae/bywoning/export?formaat=...).
// =============================================================================

(function () {
  var MAAND = ['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'];
  var BLADSY_RYE = 50; // soveel rye wys 'n lys op 'n slag

  var vanEl, totEl, kampusEl, statusEl, omvangEl, tabsEl, inhoudEl;
  var aflaaiKnoppie, aflaaiMenu;

  var oorsig = null;   // die laaste antwoord van die bediener
  var aktief = 0;      // indeks van die oortjie wat gewys word
  var laaiNommer = 0;  // ignoreer ou antwoorde as die gebruiker vinnig verander

  // ---------------------------------------------------------------------------
  // Formatering
  // ---------------------------------------------------------------------------
  function isoDatum(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') +
      '-' + String(d.getDate()).padStart(2, '0');
  }

  // '2026-10-05' -> '5 Okt 2026'. Die bediener stuur reeds SA-tyd, so ons
  // lees die teks direk en laat die blaaier se tydsone uit.
  function datumTeks(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    if (!m) return iso || '';
    return parseInt(m[3], 10) + ' ' + MAAND[parseInt(m[2], 10) - 1] + ' ' + m[1];
  }

  function datumTydTeks(iso) {
    var m = /T(\d{2}):(\d{2})/.exec(iso || '');
    return datumTeks(iso) + (m ? ' ' + m[1] + ':' + m[2] : '');
  }

  function persent(v) {
    return Math.round(Number(v) * 100) + '%';
  }

  function formateer(waarde, formaat, leeg) {
    if (waarde === null || waarde === undefined || waarde === '') return leeg === undefined ? '–' : leeg;
    if (formaat === 'persent') return persent(waarde);
    if (formaat === 'datum') return datumTeks(waarde);
    if (formaat === 'datumtyd') return datumTydTeks(waarde);
    return String(waarde);
  }

  // 'n Datum-sleutel as 'n plaaslike Date (vir die tendens-grafiek se x-as).
  function naDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    return new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
  }

  function foutTeks(body, status) {
    var d = body && (body.fout || body.detail);
    if (Array.isArray(d)) d = d.map(function (x) { return x.msg || ''; }).join('; ');
    return d || ('Kon nie die verslag laai nie (fout ' + status + ').');
  }

  function wysStatus(teks, tipe) {
    statusEl.textContent = teks || '';
    statusEl.className = 'modal-status' + (tipe ? ' ' + tipe : '');
  }

  function el(tag, klas, teks) {
    var e = document.createElement(tag);
    if (klas) e.className = klas;
    if (teks !== undefined && teks !== null) e.textContent = teks;
    return e;
  }

  // ---------------------------------------------------------------------------
  // Tydperk
  // ---------------------------------------------------------------------------
  function stelTydperk(keuse) {
    var tot = new Date();
    var van = new Date(tot);
    if (keuse === 'maand') {
      van.setDate(1);
    } else {
      var dae = parseInt(keuse, 10) || 0;
      van.setDate(van.getDate() - Math.max(dae - 1, 0));
    }
    vanEl.value = isoDatum(van);
    totEl.value = isoDatum(tot);
    merkVoorafstelling(keuse);
  }

  function merkVoorafstelling(keuse) {
    document.querySelectorAll('.verslag-voorafstellings [data-dae]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-dae') === keuse ? 'true' : 'false');
    });
  }

  function tydperkGeldig() {
    if (!vanEl.value || !totEl.value) {
      wysStatus('Kies asseblief beide datums.', 'error');
      return false;
    }
    if (vanEl.value > totEl.value) {
      wysStatus("Die 'Van'-datum moet voor die 'Tot'-datum wees.", 'error');
      return false;
    }
    return true;
  }

  // ---------------------------------------------------------------------------
  // Data laai
  // ---------------------------------------------------------------------------
  async function laaiOorsig() {
    if (!tydperkGeldig()) return;
    var nommer = ++laaiNommer;
    wysStatus('', '');
    inhoudEl.setAttribute('aria-busy', 'true');
    inhoudEl.classList.add('is-besig');
    try {
      var r = await window.MoonApi.fetchVerslagOorsig(vanEl.value, totEl.value, kampusEl.value);
      if (nommer !== laaiNommer) return;
      if (!r.ok || !r.body || !r.body.data) {
        wysStatus(foutTeks(r.body, r.status), 'error');
        return;
      }
      oorsig = r.body.data;
      if (aktief >= oorsig.afdelings.length) aktief = 0;
      teken();
    } catch (err) {
      if (nommer !== laaiNommer) return;
      console.error('[verslag.js] oorsig', err);
      wysStatus('Kon nie die bediener bereik nie.', 'error');
    } finally {
      if (nommer === laaiNommer) {
        inhoudEl.removeAttribute('aria-busy');
        inhoudEl.classList.remove('is-besig');
      }
    }
  }

  var laaiTydhouer = null;
  function laaiBietjieLater() {
    clearTimeout(laaiTydhouer);
    laaiTydhouer = setTimeout(laaiOorsig, 250);
  }

  // ---------------------------------------------------------------------------
  // Teken die blad
  // ---------------------------------------------------------------------------
  function teken() {
    var m = oorsig.meta;
    omvangEl.textContent = m.omvang + ' · ' + datumTeks(m.van) + ' tot ' + datumTeks(m.tot) +
      ' · ' + m.werksdae + ' werksdae · Opgestel ' + datumTydTeks(m.gegenereer_op);

    var titels = oorsig.afdelings.map(function (a) { return a.titel; });
    document.getElementById('aflaai-excel-detail').textContent =
      (titels.length === 1 ? 'Tab: ' : 'Tabs: ') + titels.join(', ');

    tekenOortjies();
    tekenAfdeling();
  }

  function tekenOortjies() {
    tabsEl.innerHTML = '';
    tabsEl.hidden = oorsig.afdelings.length < 2;
    oorsig.afdelings.forEach(function (afd, i) {
      var b = el('button', 'verslag-tab', afd.titel);
      b.type = 'button';
      b.id = 'verslag-tab-' + afd.sleutel;
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', i === aktief ? 'true' : 'false');
      b.setAttribute('aria-controls', 'verslag-inhoud');
      b.tabIndex = i === aktief ? 0 : -1;
      b.addEventListener('click', function () { kiesOortjie(i); });
      b.addEventListener('keydown', function (ev) {
        var nuut = null;
        if (ev.key === 'ArrowRight') nuut = (i + 1) % oorsig.afdelings.length;
        if (ev.key === 'ArrowLeft') nuut = (i - 1 + oorsig.afdelings.length) % oorsig.afdelings.length;
        if (nuut !== null) {
          ev.preventDefault();
          kiesOortjie(nuut);
          tabsEl.children[nuut].focus();
        }
      });
      tabsEl.appendChild(b);
    });
  }

  function kiesOortjie(i) {
    if (i === aktief) return;
    aktief = i;
    tekenOortjies();
    tekenAfdeling();
  }

  function tekenAfdeling() {
    var afd = oorsig.afdelings[aktief];
    inhoudEl.innerHTML = '';
    inhoudEl.setAttribute('role', 'tabpanel');
    inhoudEl.setAttribute('aria-labelledby', 'verslag-tab-' + afd.sleutel);

    inhoudEl.appendChild(el('p', 'verslag-beskrywing', afd.beskrywing));

    // --- KPI-teëls ---
    var rooster = el('div', 'stat-grid');
    rooster.setAttribute('aria-label', afd.titel + ' kernsyfers');
    afd.kernsyfers.forEach(function (s) {
      var kaart = el('div', 'glass-card stat-card');
      var streep = el('span', 'stat-accent');
      streep.setAttribute('aria-hidden', 'true');
      kaart.appendChild(streep);
      kaart.appendChild(el('div', 'stat-label', s.etiket));
      kaart.appendChild(el('div', 'stat-value', formateer(s.waarde, s.formaat, 'n.v.t.')));
      rooster.appendChild(kaart);
    });
    inhoudEl.appendChild(rooster);

    // --- Grafieke ---
    var grafiekRooster = el('div', 'verslag-grafieke');
    var houers = [];
    // Sirkels en balke deel 'n ry; tendenslyne kry die volle breedte onderaan.
    var grafieke = afd.grafieke.filter(function (g) { return g.tipe !== 'lyn'; })
      .concat(afd.grafieke.filter(function (g) { return g.tipe === 'lyn'; }));
    grafieke.forEach(function (g) {
      var kaart = el('article', 'glass-card panel verslag-grafiek verslag-grafiek--' + g.tipe);
      kaart.appendChild(el('h2', null, g.titel));
      var houer = el('div', 'viz-chart');
      kaart.appendChild(houer);
      grafiekRooster.appendChild(kaart);
      houers.push({ houer: houer, grafiek: g });
    });
    inhoudEl.appendChild(grafiekRooster);

    // --- Wat die data wys ---
    if (afd.insigte.length) {
      var insigKaart = el('article', 'glass-card panel');
      insigKaart.appendChild(el('h2', null, 'Wat die data wys'));
      var lys = el('ul', 'verslag-insigte');
      afd.insigte.forEach(function (t) { lys.appendChild(el('li', null, t)); });
      insigKaart.appendChild(lys);
      inhoudEl.appendChild(insigKaart);
    }

    // --- Lyste ---
    afd.tabelle.forEach(function (t) { inhoudEl.appendChild(bouTabel(t)); });

    // Grafieke word geteken nadat hulle in die blad is (hulle meet hul breedte).
    tekenGrafieke(houers);
    inhoudEl._grafieke = houers;
  }

  function kleure() {
    var c = window.MoonStats.colors;
    return [c.series1, c.series2, c.dim];
  }

  function tekenGrafieke(houers) {
    if (!window.MoonStats) return;
    var k = kleure();
    houers.forEach(function (h) {
      var g = h.grafiek;
      var isPers = g.formaat === 'persent';
      if (g.tipe === 'sirkel') {
        MoonStats.renderDonut(h.houer, {
          title: g.titel,
          segments: g.segmente.map(function (s, i) {
            return { label: s.etiket, value: s.waarde, color: k[Math.min(i, k.length - 1)] };
          })
        });
      } else if (g.tipe === 'balk') {
        MoonStats.renderBarsH(h.houer, {
          items: g.items.map(function (it) {
            return { label: it.etiket, value: isPers ? Math.round(it.waarde * 100) : it.waarde };
          }),
          max: isPers ? 100 : undefined,
          fmtValue: isPers ? function (v) { return v + '%'; } : undefined
        });
      } else {
        MoonStats.renderTrend(h.houer, {
          times: g.etikette.map(naDate),
          series: g.reekse.map(function (r, i) {
            return {
              label: r.etiket,
              color: k[Math.min(i, 1)],
              values: r.waardes.map(function (v) { return isPers ? Math.round(v * 100) : v; })
            };
          }),
          height: 180,
          yMax: isPers ? 100 : undefined,
          fmtTime: function (d) { return d.getDate() + ' ' + MAAND[d.getMonth()]; },
          fmtValue: isPers ? function (v) { return v + '%'; } : undefined,
          emptyText: 'Te min dae in die tydperk vir ’n tendens.'
        });
      }
    });
  }

  function herteken() {
    if (inhoudEl && inhoudEl._grafieke) tekenGrafieke(inhoudEl._grafieke);
  }

  // ---------------------------------------------------------------------------
  // Soekbare lys (tabel)
  // ---------------------------------------------------------------------------
  function bouTabel(t) {
    var kaart = el('article', 'glass-card panel verslag-lys');
    var kop = el('h2', null, t.titel);
    var tel = el('span', 'panel-count', String(t.totaal));
    kop.appendChild(tel);
    kaart.appendChild(kop);

    if (!t.rye.length) {
      kaart.appendChild(el('div', 'viz-empty', 'Geen data in hierdie tydperk nie.'));
      return kaart;
    }

    var soek = el('input', 'glass-input verslag-soek');
    soek.type = 'search';
    soek.placeholder = 'Soek in ' + t.titel.toLowerCase() + '…';
    soek.setAttribute('aria-label', 'Soek in ' + t.titel);
    kaart.appendChild(soek);

    var houer = el('div', 'verslag-tabel-houer');
    var tabel = el('table', 'verslag-tabel');
    var thead = el('thead');
    var kopRy = el('tr');
    t.kolomme.forEach(function (k) {
      var th = el('th', k.formaat === 'getal' || k.formaat === 'persent' ? 'is-getal' : null, k.naam);
      th.scope = 'col';
      kopRy.appendChild(th);
    });
    thead.appendChild(kopRy);
    tabel.appendChild(thead);
    var tbody = el('tbody');
    tabel.appendChild(tbody);
    houer.appendChild(tabel);
    kaart.appendChild(houer);

    var voet = el('div', 'verslag-lys-voet');
    var inligting = el('span', 'viz-caption');
    var meer = el('button', 'btn-outline btn-sm', 'Wys meer');
    meer.type = 'button';
    voet.appendChild(inligting);
    voet.appendChild(meer);
    kaart.appendChild(voet);

    // Elke ry se teks word een keer opgestel sodat soek vinnig bly.
    var rye = t.rye.map(function (ry) {
      var selle = ry.map(function (v, i) { return formateer(v, t.kolomme[i].formaat); });
      return { ry: ry, selle: selle, soek: selle.join(' ').toLowerCase() };
    });
    var gefiltreer = rye;
    var gewys = BLADSY_RYE;

    function vul() {
      tbody.innerHTML = '';
      var frag = document.createDocumentFragment();
      gefiltreer.slice(0, gewys).forEach(function (r) {
        var tr = el('tr');
        r.selle.forEach(function (teks, i) {
          var k = t.kolomme[i];
          var klas = k.formaat === 'getal' || k.formaat === 'persent' ? 'is-getal' : null;
          var td = el('td', klas, teks);
          if (k.formaat === 'persent' && r.ry[i] !== null && r.ry[i] < 0.75) td.classList.add('is-laag');
          tr.appendChild(td);
        });
        frag.appendChild(tr);
      });
      tbody.appendChild(frag);

      var getoon = Math.min(gewys, gefiltreer.length);
      var teks = 'Wys ' + getoon + ' van ' + gefiltreer.length;
      if (gefiltreer.length !== rye.length) teks += ' (gefiltreer uit ' + rye.length + ')';
      if (t.totaal > t.rye.length) {
        teks += ' · die voorskou bevat die eerste ' + t.rye.length + ' van ' + t.totaal +
          ' rye; die aflaai bevat alles';
      }
      inligting.textContent = teks;
      meer.hidden = gewys >= gefiltreer.length;
      if (!gefiltreer.length) {
        var leeg = el('tr');
        var td = el('td', 'verslag-geen', 'Niks pas by jou soektog nie.');
        td.colSpan = t.kolomme.length;
        leeg.appendChild(td);
        tbody.appendChild(leeg);
      }
    }

    soek.addEventListener('input', function () {
      var q = soek.value.trim().toLowerCase();
      gefiltreer = q ? rye.filter(function (r) { return r.soek.indexOf(q) !== -1; }) : rye;
      gewys = BLADSY_RYE;
      vul();
    });
    meer.addEventListener('click', function () {
      gewys += BLADSY_RYE * 2;
      vul();
    });
    vul();
    return kaart;
  }

  // ---------------------------------------------------------------------------
  // Aflaai
  // ---------------------------------------------------------------------------
  function menuOop(oop) {
    aflaaiMenu.hidden = !oop;
    aflaaiKnoppie.setAttribute('aria-expanded', oop ? 'true' : 'false');
    if (oop) aflaaiMenu.querySelector('[role="menuitem"]').focus();
  }

  var FORMAAT_NAAM = { xlsx: 'Excel', pdf: 'PDF', docx: 'Word', txt: 'teks' };

  async function laaiAf(formaat) {
    menuOop(false);
    if (!tydperkGeldig()) return;
    aflaaiKnoppie.disabled = true;
    wysStatus(FORMAAT_NAAM[formaat] + '-verslag word opgestel…', '');
    try {
      var r = await window.MoonApi.exportBywoningVerslag(vanEl.value, totEl.value, kampusEl.value, formaat);
      if (!r.ok) {
        wysStatus(r.fout || 'Kon nie die verslag genereer nie.', 'error');
        return;
      }
      var url = URL.createObjectURL(r.blob);
      var link = document.createElement('a');
      link.href = url;
      link.download = r.leernaam;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      wysStatus('Verslag afgelaai: ' + r.leernaam, 'success');
    } catch (err) {
      console.error('[verslag.js] aflaai', err);
      wysStatus('Kon nie die bediener bereik nie.', 'error');
    } finally {
      aflaaiKnoppie.disabled = false;
      aflaaiKnoppie.focus();
    }
  }

  function koppelAflaai() {
    aflaaiKnoppie.addEventListener('click', function () { menuOop(aflaaiMenu.hidden); });
    var items = Array.prototype.slice.call(aflaaiMenu.querySelectorAll('[role="menuitem"]'));
    items.forEach(function (item, i) {
      item.addEventListener('click', function () { laaiAf(item.getAttribute('data-formaat')); });
      item.addEventListener('keydown', function (ev) {
        if (ev.key === 'ArrowDown') { ev.preventDefault(); items[(i + 1) % items.length].focus(); }
        if (ev.key === 'ArrowUp') { ev.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
        if (ev.key === 'Tab') menuOop(false);
      });
    });
    document.addEventListener('click', function (ev) {
      if (!aflaaiMenu.hidden && !document.getElementById('aflaai-kieser').contains(ev.target)) menuOop(false);
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && !aflaaiMenu.hidden) {
        menuOop(false);
        aflaaiKnoppie.focus();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Begin
  // ---------------------------------------------------------------------------
  function begin() {
    vanEl = document.getElementById('verslag-van');
    totEl = document.getElementById('verslag-tot');
    kampusEl = document.getElementById('verslag-kampus');
    statusEl = document.getElementById('verslag-status');
    omvangEl = document.getElementById('verslag-omvang');
    tabsEl = document.getElementById('verslag-tabs');
    inhoudEl = document.getElementById('verslag-inhoud');
    aflaaiKnoppie = document.getElementById('aflaai-knoppie');
    aflaaiMenu = document.getElementById('aflaai-menu');

    document.querySelectorAll('.verslag-voorafstellings [data-dae]').forEach(function (b) {
      b.addEventListener('click', function () {
        stelTydperk(b.getAttribute('data-dae'));
        laaiBietjieLater();
      });
    });
    [vanEl, totEl].forEach(function (inp) {
      inp.addEventListener('change', function () {
        merkVoorafstelling(null);
        laaiBietjieLater();
      });
    });
    kampusEl.addEventListener('change', laaiBietjieLater);
    koppelAflaai();

    // Slegs admins kan 'n spesifieke kampus kies; opsigters en personeel is reeds beperk.
    if (hasRole('Administrateur') && window.MoonApi.fetchKampusse) {
      window.MoonApi.fetchKampusse().then(function (body) {
        var kampusse = (body && body.data) || [];
        kampusse.forEach(function (k) {
          var opt = document.createElement('option');
          opt.value = k.Kampus_ID;
          opt.textContent = k.KAM_Naam;
          kampusEl.appendChild(opt);
        });
        if (kampusse.length) document.getElementById('verslag-kampus-veld').hidden = false;
      }).catch(function () { /* kampuskeuse bly versteek */ });
    }

    // Teken die grafieke oor as die venster verander of die tema wissel.
    var grootteTyd = null;
    window.addEventListener('resize', function () {
      clearTimeout(grootteTyd);
      grootteTyd = setTimeout(herteken, 150);
    });
    new MutationObserver(herteken).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });

    stelTydperk('30');
    laaiOorsig();
  }

  document.addEventListener('DOMContentLoaded', begin);
})();
