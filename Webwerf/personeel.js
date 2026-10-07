// personeel.js — Hierdie lêer beheer die "My Klasse" bladsy vir personeel.
// Dit laai die personeellid se regte klasse (rooster) van die bediener,
// wys die module se studente met hul bywoning as vorderingsbalke,
// 'n kalender om die dag te kies, en die volle klasregister met 'n soekblokkie.
/**
 * personeel.js — logic for personeel.html only.
 *
 * REGTE DATA (backend, routers/klasse.py, prefix /rooster):
 *   - Klasse in die "Kies Klas" keuselys kom van
 *       GET /rooster/personeel/{id}/rooster   (eie rooster: module + direk)
 *     of, vir 'n gebruiker met die Administrateur-rol,
 *       GET /rooster/klasse                   (alle klassessies).
 *   - Die klasregister (regterpaneel) kom van
 *       GET /rooster/klasse/{id}/studente     (groep + module + direk, gededupeer).
 *
 * REGTE NFC-BYWONING:
 *   - GET /rooster/klasse/{id}/bywoning?datum=YYYY-MM-DD
 *   - die backend filter op die roosterklas se Lokasie_ID, NFC-metode en
 *     presiese geskeduleerde begin/eindtyd.
 *   - 'n gewone browser refresh laai die nuutste skanderings uit die databasis.
 *
 * Depends on:
 *   - main.js (login gate + Personeel gate; laai website_api_calls.js → MoonApi;
 *     verskaf hasRole())
 *   - styles.css (.kalender* klasse)
 *   - stats.js (MoonStats: renderDonut, renderColumns, createTable)
 *   - HTML ids: module-select, dag-select, dash-datum, dash-in-count, dash-out-count,
 *     dash-total-count, dash-percent-count, stat-dag-donut, stat-dag-caption,
 *     kal-title, kal-prev, kal-next, kal-grid, register-tabel, register-titel,
 *     register-telling, student-stats-titel, stat-student-donut,
 *     stat-student-caption, stat-bywoning-chart, stat-bywoning-avg.
 */

// Al die kode loop binne een omhulsel sodat die veranderlikes hier
// nie met die res van die webwerf deurmekaar raak nie.
(function () {
  // ----- Klasse (regte data van die bediener) -----
  // Elke klas lyk so: { id, klasId, kode, moduleNaam, dag, dagIndeks, begin,
  // eind, lokaal, label }. Die klasregister word apart per klas gelaai en
  // in `studenteKas` gehou sodat ons dit net een keer per klas afhaal.
  var klasse = [];
  var studenteKas = {}; // klasId -> studente vir die tans gekose datum

  // ----- Cached DOM nodes (null-safe checks before use) -----
  // Kry al die dele van die bladsy (keuselys, lyste, knoppies, ens.)
  // een keer, sodat ons hulle later maklik kan gebruik.
  var moduleSelect = document.getElementById('module-select');
  var dagSelect = document.getElementById('dag-select');
  var dashDatum = document.getElementById('dash-datum');
  var dashInCount = document.getElementById('dash-in-count');
  var dashOutCount = document.getElementById('dash-out-count');
  var dashTotalCount = document.getElementById('dash-total-count');
  var dashPercentCount = document.getElementById('dash-percent-count');
  var kalTitle = document.getElementById('kal-title');
  var kalPrev = document.getElementById('kal-prev');
  var kalNext = document.getElementById('kal-next');
  var kalGrid = document.getElementById('kal-grid');
  var statChart = document.getElementById('stat-bywoning-chart');
  var statAvg = document.getElementById('stat-bywoning-avg');
  var dagDonut = document.getElementById('stat-dag-donut');
  var dagCaption = document.getElementById('stat-dag-caption');
  var studentTitel = document.getElementById('student-stats-titel');
  var studentDonut = document.getElementById('stat-student-donut');
  var studentCaption = document.getElementById('stat-student-caption');
  var registerTitel = document.getElementById('register-titel');
  var registerTelling = document.getElementById('register-telling');

  // Die klasregister-tabel (MoonStats.createTable) en sy opsies; die opsies
  // word gehou sodat ons die leë-boodskap kan verander.
  var registerOpts = null;
  var registerTabel = null;

  // ----- Module state -----
  // Onthou watter klas en dag tans gekies is, en watter maand
  // die kalender op die oomblik wys.
  var vandag = new Date();
  vandag.setHours(0, 0, 0, 0);

  var currentKlas = null;      // null totdat die klasse gelaai is
  var selectedStudent = null;  // student wat in die klasregister gekies is
  var selectedDate = new Date(vandag);

  // ----- LIVE klasbywoning -----
  // Wanneer die personeel vandag se klas oop het, haal ons elke 3 sekondes
  // die jongste NFC-bywoning uit die databasis. Historiese datums word nie
  // gepoll nie, sodat ons nie onnodige versoeke na die backend stuur nie.
  var LIVE_REFRESH_MS = 3000;
  var liveRefreshTimer = null;
  var liveRefreshBusy = false;

  // Oor hoeveel klasdae die gekose student se bywoning bereken word.
  var STUDENT_STAT_DAE = 10;
  var displayYear = vandag.getFullYear();
  var displayMonth = vandag.getMonth();

  var MAANDE = ['Januarie', 'Februarie', 'Maart', 'April', 'Mei', 'Junie',
                'Julie', 'Augustus', 'September', 'Oktober', 'November', 'Desember'];
  var DAG_NAME = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Sa', 'So'];

  // Dagname (Afrikaans en Engels, soos in die Lantiv-CSV) → JS weekdag-indeks
  // (0 = Sondag ... 6 = Saterdag).
  var DAG_INDEKS = {
    sondag: 0, maandag: 1, dinsdag: 2, woensdag: 3, donderdag: 4, vrydag: 5, saterdag: 6,
    sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6
  };

  // ----- Omskakeling van bediener-data -----

  // Hierdie funksie skakel 'n dagnaam ("Maandag") om na 'n weekdag-indeks,
  // of null as ons die naam nie ken nie.
  function dagNaIndeks(dag) {
    if (!dag) return null;
    var sleutel = String(dag).trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(DAG_INDEKS, sleutel) ? DAG_INDEKS[sleutel] : null;
  }

  // Hierdie funksie maak 'n klas-objek vir die bladsy uit een ry van die
  // bediener se rooster-antwoord (_klas_na_dict in routers/klasse.py).
  function klasVanApi(k) {
    var kode = k.MOD_Kode || ('Module ' + k.Module_ID);
    var tyd = '';
    if (k.KLA_Begin_Tyd && k.KLA_Eind_Tyd) tyd = k.KLA_Begin_Tyd + '–' + k.KLA_Eind_Tyd;
    else if (k.KLA_Begin_Tyd) tyd = k.KLA_Begin_Tyd;

    // Etiket in die keuselys, bv. "EBREK370 — Maandag 8:00–9:00 · GH117 A (50)"
    var wanneer = [k.KLA_Dag, tyd].filter(Boolean).join(' ');
    var label = kode;
    if (wanneer) label += ' — ' + wanneer;
    if (k.KLA_Lokaal) label += ' · ' + k.KLA_Lokaal;

    // Etiket vir die dag-keuselys, bv. "Maandag 8:00–9:00 · GH117 A (50)"
    var dagLabel = wanneer;
    if (k.KLA_Lokaal) dagLabel = wanneer ? wanneer + ' · ' + k.KLA_Lokaal : k.KLA_Lokaal;
    if (!dagLabel) dagLabel = 'Tyd onbekend';

    return {
      id: String(k.Klas_ID),
      klasId: k.Klas_ID,
      kode: kode,
      moduleNaam: k.MOD_Naam || '',
      dag: k.KLA_Dag || '',
      dagIndeks: dagNaIndeks(k.KLA_Dag),
      begin: k.KLA_Begin_Tyd || '',
      eind: k.KLA_Eind_Tyd || '',
      lokaal: k.KLA_Lokaal || '',
      label: label,
      dagLabel: dagLabel
    };
  }

  // Hierdie funksie maak 'n student-objek uit een ry van die klasregister.
  function studentVanApi(s) {
    return {
      id: s.Gebruiker_ID,
      naam: s.GEB_Naam || '',
      van: s.GEB_Van || '',
      nommer: s.STU_Nommer || ('#' + s.Gebruiker_ID),
      teenwoordig: s.Teenwoordig === true,
      ingescanTyd: s.Ingescan_Tyd || null,
      laasteRigting: s.Laaste_Rigting || null,
      laasteSkandering: s.Laaste_Skandering || null
    };
  }

  // Hierdie funksie formateer 'n student se laaste inskandering, bv.
  // "Bitterbessie · 09:14" (plaaslike tyd), of 'n verstek-boodskap.
  function formatSkandering(sk) {
    if (!sk || !sk.tyd) return 'Geen NFC-skandering vir hierdie klas';
    var d = new Date(sk.tyd);
    var tyd = '';
    if (!isNaN(d.getTime())) {
      tyd = (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' +
            (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
    }
    return [sk.lokaal, tyd, sk.rigting].filter(Boolean).join(' · ') || 'Geen NFC-skandering vir hierdie klas';
  }

  // Sorteer klasse op dag, dan begintyd, dan modulekode sodat die keuselys
  // die week se volgorde volg.
  function vergelykKlasse(a, b) {
    var da = a.dagIndeks === null ? 7 : (a.dagIndeks === 0 ? 7 : a.dagIndeks);
    var db = b.dagIndeks === null ? 7 : (b.dagIndeks === 0 ? 7 : b.dagIndeks);
    if (da !== db) return da - db;
    var ta = tydNaMinute(a.begin);
    var tb = tydNaMinute(b.begin);
    if (ta !== tb) return ta - tb;
    return a.kode.localeCompare(b.kode);
  }

  // "8:00" → 480; onbekend → groot getal sodat dit agter sorteer.
  function tydNaMinute(tyd) {
    var m = /^(\d{1,2}):(\d{2})/.exec(tyd || '');
    if (!m) return 24 * 60 + 1;
    return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
  }

  // Hierdie funksie gee die gelaaide klasregister van 'n klas (leeg as dit
  // nog nie gelaai is nie).
  function studenteVir(klas) {
    return (klas && studenteKas[klas.klasId]) || [];
  }

  // ----- Bediener-oproepe -----

  // Hierdie funksie gee die foutboodskap uit 'n bediener-antwoord, of 'n
  // verstekboodskap.
  function foutVanAntwoord(res, verstek) {
    if (res && typeof res.detail === 'string') return res.detail;
    if (res && typeof res.boodskap === 'string') return res.boodskap;
    return verstek;
  }

  // Hierdie funksie laai die klasse wat in die keuselys moet verskyn:
  // 'n admin sien alle klasse; personeel sien net hul eie rooster.
  function laaiKlasse() {
    if (!window.MoonApi) {
      return Promise.reject(new Error('Die API-kliënt (MoonApi) is nie gelaai nie.'));
    }
    var isAdmin = typeof hasRole === 'function' && hasRole('Administrateur');
    var versoek;
    if (isAdmin) {
      versoek = MoonApi.fetchRoosterKlasse();
    } else {
      var gebruikerId = MoonApi.getCurrentUserId();
      if (!gebruikerId) {
        return Promise.reject(new Error('Kon nie jou gebruiker-ID uit die aanmeldbewys lees nie.'));
      }
      versoek = MoonApi.fetchPersoneelRooster(gebruikerId);
    }
    return versoek.then(function (res) {
      if (!res || !res.sukses) {
        throw new Error(foutVanAntwoord(res, 'Kon nie klasse van die bediener laai nie.'));
      }
      return (res.data || []).map(klasVanApi).sort(vergelykKlasse);
    });
  }

  // Laai die klasregister + regte NFC-status vir die gekose datum.
  // Die /bywoning endpoint gee Present en Absent in een antwoord terug.
  function laaiStudente(klas, datum, force) {
    return laaiBywoning(klas, datum || selectedDate, force === true).then(function () {
      return studenteVir(klas);
    });
  }

  // ----- Regte NFC-bywoning per roosterklas + datum -----

  // Hierdie funksie skryf 'n datum as teks in die vorm JJJJ-MM-DD.
  function isoDate(d) {
    var m = String(d.getMonth() + 1);
    var dd = String(d.getDate());
    if (m.length < 2) m = '0' + m;
    if (dd.length < 2) dd = '0' + dd;
    return d.getFullYear() + '-' + m + '-' + dd;
  }

  // Hierdie funksie skryf 'n datum mooi leesbaar uit, bv. "10 Julie 2026".
  function formatDatum(d) {
    return d.getDate() + ' ' + MAANDE[d.getMonth()] + ' ' + d.getFullYear();
  }

  function isRoosterDag(klas, d) {
    if (!klas) return false;
    if (d.getTime() > vandag.getTime()) return false;
    if (klas.dagIndeks === null || klas.dagIndeks === undefined) {
      var weekdag = d.getDay();
      return weekdag >= 1 && weekdag <= 5;
    }
    return d.getDay() === klas.dagIndeks;
  }

  // Kalender/grafiek gebruik die tans gekose roosterklas se werklike weekdag.
  function isKlasdag(d) {
    if (currentKlas) return isRoosterDag(currentKlas, d);
    var dag = d.getDay();
    return dag >= 1 && dag <= 5 && d.getTime() <= vandag.getTime();
  }

  // Kies vandag as die klas vandag plaasvind; anders die mees onlangse
  // voorkoms van hierdie roosterklas.
  function meesOnlangseKlasDatum(klas) {
    var d = new Date(vandag);
    if (!klas || klas.dagIndeks === null || klas.dagIndeks === undefined) return d;
    var guard = 0;
    while (d.getDay() !== klas.dagIndeks && guard < 7) {
      d.setDate(d.getDate() - 1);
      guard++;
    }
    return d;
  }

  var bywoningKas = {}; // "Klas_ID|YYYY-MM-DD" -> genormaliseerde regte data

  function bywoningSleutel(klas, datum) {
    return String(klas.klasId) + '|' + isoDate(datum);
  }

  function scanTydKort(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' +
           (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
  }

  function normaliseerBywoning(data) {
    data = data || {};
    var present = (data.Present || []).map(studentVanApi);
    var absent = (data.Absent || []).map(studentVanApi);
    var almal = present.concat(absent);

    // Sorteer die register stabiel op van/naam.
    almal.sort(function (a, b) {
      return (a.van + ' ' + a.naam).localeCompare(b.van + ' ' + b.naam);
    });

    var result = {
      ingeskandeer: present.map(function (s) {
        return { student: s, tyd: scanTydKort(s.ingescanTyd) };
      }),
      nieIngeskandeer: absent,
      totaal: Number(data.Total_Students || almal.length || 0),
      lokasieGekoppel: data.Lokasie_Gekoppel === true,
      scanVenster: data.Scan_Venster || null,
      roosterDagMatch: !data.Scan_Venster || data.Scan_Venster.rooster_dag_match !== false
    };

    return { result: result, studente: almal };
  }

  function kryBywoning(klas, datum) {
    if (!klas) return null;
    var item = bywoningKas[bywoningSleutel(klas, datum)];
    if (!item || item.roosterDagMatch === false) return null;
    return item;
  }

  function laaiBywoning(klas, datum, force) {
    if (!klas || !window.MoonApi || typeof MoonApi.fetchKlasBywoning !== 'function') {
      return Promise.reject(new Error('fetchKlasBywoning is nie in website_api_calls.js beskikbaar nie.'));
    }

    var sleutel = bywoningSleutel(klas, datum);
    if (!force && Object.prototype.hasOwnProperty.call(bywoningKas, sleutel)) {
      return Promise.resolve(bywoningKas[sleutel]);
    }

    return MoonApi.fetchKlasBywoning(klas.klasId, isoDate(datum)).then(function (res) {
      if (!res || !res.sukses) {
        throw new Error(foutVanAntwoord(res, 'Kon nie klasbywoning laai nie.'));
      }

      var norm = normaliseerBywoning(res.data || {});
      bywoningKas[sleutel] = norm.result;

      // Slegs die tans gekose datum se register moet die sigbare klaslys vervang.
      if (currentKlas === klas && sameDay(datum, selectedDate)) {
        studenteKas[klas.klasId] = norm.studente;
      }
      return norm.result;
    });
  }

  // Laai die historiese klasdae wat die grafiek/studentstatistiek gebruik.
  function laaiBywoningReeks(klas) {
    var dae = kryLaasteKlasdae(STUDENT_STAT_DAE);
    return Promise.all(dae.map(function (d) {
      return laaiBywoning(klas, d, false).catch(function () { return null; });
    }));
  }

  function isVandag(datum) {
    return sameDay(datum, new Date());
  }

  // Haal stilweg die jongste bywoning vir die oop klas.
  // Geen foutboodskap word oor die UI geskryf as een poll tydelik misluk nie;
  // die volgende poll probeer weer en die gebruiker se huidige lys bly sigbaar.
  function liveRefreshBywoning() {
    if (document.hidden || liveRefreshBusy || !currentKlas || !isVandag(selectedDate)) {
      return;
    }

    liveRefreshBusy = true;
    var klasToeGestuur = currentKlas;
    var datumToeGestuur = new Date(selectedDate);

    laaiBywoning(klasToeGestuur, datumToeGestuur, true).then(function () {
      // Ignoreer 'n laat antwoord as die gebruiker intussen klas/datum verander het.
      if (currentKlas !== klasToeGestuur || !sameDay(selectedDate, datumToeGestuur)) return;
      renderDashboard();
      renderRoster();
      renderStudentStats();
    }).catch(function (err) {
      console.warn('LIVE klasbywoning kon nie herlaai nie:', err);
    }).finally(function () {
      liveRefreshBusy = false;
    });
  }

  function beginLiveRefresh() {
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
    liveRefreshTimer = setInterval(liveRefreshBywoning, LIVE_REFRESH_MS);
  }

  // ----- Klasregister-tabel -----
  // Hierdie funksie bou die soekbare klasregister-tabel een keer. Klik op 'n
  // ry om daardie student se bywoningstatistieke bo te sien.
  function maakRegisterTabel() {
    var houer = document.getElementById('register-tabel');
    if (!houer || !window.MoonStats || !MoonStats.createTable) return;
    registerOpts = {
      columns: [
        { name: 'Student', format: 'teks' },
        { name: 'Studentenommer', format: 'teks' },
        { name: 'Gekose dag', format: 'status' },
        { name: 'Bywoning', format: 'persent' },
        { name: 'Bygewoon', format: 'teks' },
        { name: 'Laaste skandering', format: 'teks' }
      ],
      searchPlaceholder: 'Soek student…',
      emptyText: 'Laai klasse…',
      filters: [
        { label: 'Almal' },
        { label: 'Ingeskandeer', test: function (r) { return r.dagStatus === 'in'; } },
        { label: 'Nie ingeskandeer', test: function (r) { return r.dagStatus === 'uit'; } },
        { label: 'Bywoning onder 75%', test: function (r) { return r.bywoning !== null && r.bywoning < 0.75; } }
      ],
      onRowClick: function (r) { selectStudent(r.student); }
    };
    registerTabel = MoonStats.createTable(houer, registerOpts);
  }

  // Hierdie funksie maak die tabel leeg en wys 'n boodskap (laai, fout,
  // geen studente).
  function renderLeegBoodskap(boodskap) {
    if (registerTelling) registerTelling.textContent = '';
    if (!registerTabel) return;
    registerOpts.emptyText = boodskap;
    registerTabel.setRows([], { note: '' });
  }

  // ----- Dashboard rendering -----

  // Hierdie funksie skryf die Bywoning-teël (null = geen klasdata nie).
  function renderPercentCard(persent) {
    if (!dashPercentCount) return;
    dashPercentCount.textContent = persent === null ? '--' : persent + '%';
  }

  // Hierdie funksie teken die gekose dag se sirkeldiagram (null = geen klasdata).
  function renderDagDonut(bywoning) {
    if (!window.MoonStats || !dagDonut) return;
    var aantalIn = bywoning ? bywoning.ingeskandeer.length : 0;
    var aantalUit = bywoning ? bywoning.nieIngeskandeer.length : 0;
    MoonStats.renderDonut(dagDonut, {
      title: 'Gekose dag',
      segments: [
        { label: 'Ingeskandeer', value: aantalIn, color: MoonStats.colors.series1 },
        { label: 'Nie ingeskandeer', value: aantalUit, color: MoonStats.colors.error }
      ]
    });
    if (dagCaption) {
      if (!currentKlas) dagCaption.textContent = 'Geen klas gekies nie.';
      else if (!bywoning) dagCaption.textContent = 'Geen klasdata vir ' + formatDatum(selectedDate) + ' nie.';
      else {
        dagCaption.textContent = formatDatum(selectedDate) + ' · ' + currentKlas.kode +
          (currentKlas.dagLabel ? ' · ' + currentKlas.dagLabel : '') +
          (bywoning.lokasieGekoppel ? '' : ' · NFC-lokaal NIE gekoppel nie');
      }
    }
  }

  // Hierdie funksie wys strepies op die KPI-teëls (geen klas gekies, geen
  // klasdag, of 'n fout). Die tabel wys self die rede.
  function renderDashboardLeeg() {
    if (dashInCount) dashInCount.textContent = '--';
    if (dashOutCount) dashOutCount.textContent = '--';
    renderPercentCard(null);
    renderDagDonut(null);
  }

  // Hierdie funksie teken die bywoningspaneel: die KPI-teëls bo-aan, die
  // grafiek en die studentelys met vorderingsbalke vir die gekose dag.
  function renderDashboard() {
    // Teken eers die bywoning-grafiek oor (dit volg die gekose klas en dag).
    renderStats();

    if (dashDatum) dashDatum.textContent = formatDatum(selectedDate);

    // Geen klas gekies (nog besig om te laai, of niks toegewys nie).
    if (!currentKlas) {
      if (dashTotalCount) dashTotalCount.textContent = '--';
      renderDashboardLeeg();
      return;
    }

    var studente = studenteVir(currentKlas);
    var bywoning = kryBywoning(currentKlas, selectedDate);

    // Die KPI-teëls wys net die syfers — die etikette staan reeds op die teëls.
    if (dashTotalCount) dashTotalCount.textContent = String(studente.length);

    // Geen klasdata (naweek of toekoms): strepies en boodskap.
    if (!bywoning) {
      renderDashboardLeeg();
      return;
    }

    // Werk uit watter persentasie van die klas ingeskandeer het.
    var totaal = studente.length;
    var persent = totaal > 0 ? Math.round((bywoning.ingeskandeer.length / totaal) * 100) : 0;

    if (dashInCount) dashInCount.textContent = String(bywoning.ingeskandeer.length);
    if (dashOutCount) dashOutCount.textContent = String(bywoning.nieIngeskandeer.length);
    renderPercentCard(persent);
    renderDagDonut(bywoning);
  }

  // ----- Statistieke: bywoning oor die laaste klasdae -----

  // Hierdie funksie gee die laaste `n` werklike roosterdae vir die gekose klas,
  // met die oudste dag eerste.
  function kryLaasteKlasdae(n) {
    var dae = [];
    var d = new Date(vandag);
    var guard = 0; // keer dat die lus ooit vashaak
    var maxGuard = n * 8 + 14; // genoeg dae wanneer 'n klas net een keer per week plaasvind
    while (dae.length < n && guard < maxGuard) {
      if (isKlasdag(d)) dae.unshift(new Date(d));
      d.setDate(d.getDate() - 1);
      guard++;
    }
    return dae;
  }

  /**
   * Hierdie funksie teken die bywoning-grafiek: 'n kolom vir elk van die laaste
   * 10 klasdae se bywoningspersentasie. Die gekose dag word uitgelig, en as jy
   * op 'n kolom klik, word daardie dag gekies (nes op die kalender).
   */
  function renderStats() {
    if (!window.MoonStats || !statChart) return;

    if (!currentKlas) {
      MoonStats.renderColumns(statChart, { items: [], selectedIndex: -1 });
      if (statAvg) statAvg.textContent = '';
      return;
    }

    var dae = kryLaasteKlasdae(10);
    var totaal = studenteVir(currentKlas).length;
    var som = 0;

    var items = dae.map(function (d) {
      var byw = kryBywoning(currentKlas, d);
      var aantalIn = byw ? byw.ingeskandeer.length : 0;
      var pct = totaal > 0 ? Math.round((aantalIn / totaal) * 100) : 0;
      som += pct;
      return {
        label: d.getDate() + ' ' + MAANDE[d.getMonth()],
        tick: d.getDate() + '/' + (d.getMonth() + 1),
        value: pct,
        detail: aantalIn + ' van ' + totaal + ' studente'
      };
    });

    // Kyk of die gekose dag in die venster val sodat sy kolom uitgelig kan word.
    var selectedIndex = -1;
    dae.forEach(function (d, i) {
      if (sameDay(d, selectedDate)) selectedIndex = i;
    });

    MoonStats.renderColumns(statChart, {
      items: items,
      selectedIndex: selectedIndex,
      onSelect: function (i) {
        selectedDate = new Date(dae[i]);
        displayYear = selectedDate.getFullYear();
        displayMonth = selectedDate.getMonth();
        renderKalender();
        laaiBywoning(currentKlas, selectedDate, true).then(function () {
          renderDashboard();
          renderRoster();
          renderStudentStats();
        }).catch(function () {
          renderDashboardLeeg();
        });
      }
    });

    // Die gemiddelde staan as gewone teks onder die grafiek.
    if (statAvg) {
      var avg = dae.length ? Math.round(som / dae.length) : 0;
      statAvg.textContent = 'Gemiddelde bywoning oor die laaste ' + dae.length + ' klasdae: ' + avg + '%';
    }
  }

  // ----- Status vir die gekose dag -----

  // Hierdie funksie gee 'n student se status op die gekose dag:
  // { sleutel: 'in' | 'uit' | 'geen', label, tone } vir die status-kolom.
  function dagStatus(dagByw, student) {
    if (!dagByw) return { sleutel: 'geen', label: 'Geen klasdag', tone: 'neutraal' };
    for (var i = 0; i < dagByw.ingeskandeer.length; i++) {
      var rekord = dagByw.ingeskandeer[i];
      if (rekord.student.id === student.id) {
        return { sleutel: 'in', label: rekord.tyd ? 'In · ' + rekord.tyd : 'In', tone: 'goed' };
      }
    }
    return { sleutel: 'uit', label: 'Nie in', tone: 'sleg' };
  }

  // ----- Studentbywoning: statistieke vir die gekose student -----

  /**
   * Hierdie funksie tel hoeveel keer 'n student oor die laaste `nDae` klasdae
   * die klas bygewoon en gemis het (dieselfde regte NFC-data as die
   * dashboard, so die syfers stem ooreen met die dag-vir-dag lyste).
   */
  function kryStudentBywoning(klas, student, nDae) {
    var dae = kryLaasteKlasdae(nDae);
    var bygewoon = 0;
    var gemis = 0;

    dae.forEach(function (d) {
      var byw = kryBywoning(klas, d);
      if (!byw) return;
      var was_in = byw.ingeskandeer.some(function (b) {
        return b.student.id === student.id;
      });
      if (was_in) bygewoon++; else gemis++;
    });

    return { bygewoon: bygewoon, gemis: gemis, dae: dae.length };
  }

  /**
   * Hierdie funksie wys die gekose student se bywoning vir die huidige module
   * as 'n sirkeldiagram (bygewoon teenoor gemis) met 'n opsomming. Geen
   * student gekies = 'n leë sirkel met 'n wenk.
   */
  function renderStudentStats() {
    if (!window.MoonStats || !studentDonut) return;

    if (!selectedStudent || !currentKlas) {
      if (studentTitel) studentTitel.textContent = 'Studentbywoning';
      MoonStats.renderDonut(studentDonut, {
        title: 'Studentbywoning',
        segments: [
          { label: 'Bygewoon', value: 0, color: MoonStats.colors.series1 },
          { label: 'Gemis', value: 0, color: MoonStats.colors.error }
        ]
      });
      if (studentCaption) studentCaption.textContent = 'Kies \'n student in die klasregister hieronder.';
      return;
    }

    var stats = kryStudentBywoning(currentKlas, selectedStudent, STUDENT_STAT_DAE);
    var gemeet = stats.bygewoon + stats.gemis;

    if (studentTitel) {
      studentTitel.textContent = selectedStudent.naam + ' ' + selectedStudent.van +
        ' · ' + currentKlas.kode;
    }

    MoonStats.renderDonut(studentDonut, {
      title: 'Klasse bygewoon / gemis',
      segments: [
        { label: 'Bygewoon', value: stats.bygewoon, color: MoonStats.colors.series1 },
        { label: 'Gemis', value: stats.gemis, color: MoonStats.colors.error }
      ]
    });

    if (studentCaption) {
      var pct = gemeet > 0 ? Math.round((stats.bygewoon / gemeet) * 100) : 0;
      studentCaption.textContent = selectedStudent.nommer + ' het ' +
        stats.bygewoon + ' van die laaste ' + gemeet + ' klasdae bygewoon (' +
        pct + '%) en ' + stats.gemis + ' gemis.';
    }
  }

  // Hierdie funksie kies 'n student (of ontkies met 'n tweede klik) en
  // lig sy/haar ry in die klasregister uit.
  function selectStudent(student) {
    var selfde = selectedStudent && selectedStudent.id === student.id;
    selectedStudent = selfde ? null : student;
    if (registerTabel) registerTabel.setSelected(selectedStudent ? String(selectedStudent.id) : null);
    renderStudentStats();
  }

  // ----- Kalender rendering -----
  // Hierdie funksie kyk of twee datums op dieselfde dag val.
  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth() === b.getMonth() &&
           a.getDate() === b.getDate();
  }

  // Hierdie funksie teken die kalender vir die maand wat tans gewys word.
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

    // Werk uit op watter weeksdag die maand begin en hoeveel dae dit het.
    var eerste = new Date(displayYear, displayMonth, 1);
    var offset = (eerste.getDay() + 6) % 7; // Maandag in die eerste kolom
    var daeInMaand = new Date(displayYear, displayMonth + 1, 0).getDate();

    // Sit leë blokkies in totdat ons by die eerste dag van die maand kom.
    for (var i = 0; i < offset; i++) {
      var leeg = document.createElement('div');
      leeg.className = 'kalender-dag kalender-dag--leeg';
      kalGrid.appendChild(leeg);
    }

    // Maak 'n knoppie vir elke dag van die maand en merk vandag,
    // die gekose dag en klasdae met hul eie kleure.
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

        // As jy op 'n dag klik, word daardie dag gekies en die bladsy
        // word oorgeteken met daardie dag se bywoning.
        cell.addEventListener('click', function () {
          selectedDate = datum;
          renderKalender();
          if (!currentKlas) {
            renderDashboard();
            return;
          }
          renderLeegBoodskap('Laai klasbywoning...');
          laaiBywoning(currentKlas, selectedDate, true).then(function () {
            renderDashboard();
            renderRoster();
          }).catch(function (err) {
            renderDashboardLeeg();
            renderLeegBoodskap('Kon nie klasbywoning laai nie: ' + err.message);
          });
        });

        kalGrid.appendChild(cell);
      })(d);
    }
  }

  // ----- Klasregister (tabel) -----
  // Hierdie funksie vul die klasregister-tabel: elke student in die gekose
  // klas met die gekose dag se status, bywoning oor die laaste klasdae vir
  // hierdie module en die laaste NFC-skandering. Die tabel hou self die
  // soekteks, filter en gekose ry oor die regstreekse herlaai.
  function renderRoster() {
    if (!registerTabel) return;

    if (!currentKlas) {
      if (registerTitel && registerTitel.firstChild) registerTitel.firstChild.nodeValue = 'Klasregister ';
      renderLeegBoodskap('Geen klas gekies nie.');
      return;
    }

    if (registerTitel && registerTitel.firstChild) {
      registerTitel.firstChild.nodeValue = 'Klasregister — ' + currentKlas.kode +
        (currentKlas.moduleNaam ? ' · ' + currentKlas.moduleNaam : '') + ' ';
    }

    var studente = studenteVir(currentKlas);
    if (studente.length === 0) {
      renderLeegBoodskap('Geen studente is aan hierdie klas gekoppel nie. ' +
        'Vra die administrateur om groepe of studente aan die module toe te wys.');
      return;
    }

    var dae = kryLaasteKlasdae(STUDENT_STAT_DAE);
    var dagByw = kryBywoning(currentKlas, selectedDate);
    var rye = studente.map(function (s) {
      var stats = kryStudentBywoning(currentKlas, s, STUDENT_STAT_DAE);
      var gemeet = stats.bygewoon + stats.gemis;
      var status = dagStatus(dagByw, s);
      return {
        key: String(s.id),
        student: s,
        dagStatus: status.sleutel,
        bywoning: gemeet > 0 ? stats.bygewoon / gemeet : null,
        cells: [
          s.naam + ' ' + s.van,
          s.nommer,
          { label: status.label, tone: status.tone },
          gemeet > 0 ? stats.bygewoon / gemeet : null,
          stats.bygewoon + ' van ' + gemeet,
          formatSkandering(s.laasteSkandering)
        ]
      };
    });

    if (registerTelling) registerTelling.textContent = String(studente.length);
    registerTabel.setRows(rye, {
      note: 'Bywoning oor die laaste ' + dae.length + ' roosterdae · klik op \'n student vir sy/haar statistiek'
    });
    registerTabel.setSelected(selectedStudent ? String(selectedStudent.id) : null);
  }

  // ----- Module- en dag-dropdowns -----
  // Unieke modulekodes uit die gelaaide klasse, in rooster-volgorde.
  function moduleKodes() {
    var kodes = [];
    klasse.forEach(function (k) {
      if (kodes.indexOf(k.kode) === -1) kodes.push(k.kode);
    });
    return kodes;
  }

  // Al die klas-sessies van een module, in dag/tyd-volgorde (klasse is
  // reeds so gesorteer).
  function sessiesVirModule(kode) {
    return klasse.filter(function (k) { return k.kode === kode; });
  }

  // Hierdie funksie vul die "Kies Module"-keuselys (of wys 'n enkele
  // gedeaktiveerde boodskap as daar niks is nie) en vul dan die dag-lys.
  function populateModuleSelect(boodskap) {
    if (!moduleSelect) return;
    moduleSelect.innerHTML = '';

    var kodes = moduleKodes();
    if (kodes.length === 0) {
      var leeg = document.createElement('option');
      leeg.value = '';
      leeg.textContent = boodskap || 'Geen klasse toegewys nie';
      leeg.disabled = true;
      leeg.selected = true;
      moduleSelect.appendChild(leeg);
      moduleSelect.disabled = true;
      populateDagSelect(null, boodskap || 'Geen klasse toegewys nie');
      return;
    }

    moduleSelect.disabled = false;
    kodes.forEach(function (kode) {
      var opt = document.createElement('option');
      opt.value = kode;
      var naam = sessiesVirModule(kode)[0].moduleNaam;
      opt.textContent = naam ? kode + ' — ' + naam : kode;
      moduleSelect.appendChild(opt);
    });
    if (currentKlas) moduleSelect.value = currentKlas.kode;
    populateDagSelect(moduleSelect.value);
  }

  // Hierdie funksie vul die "Kies Dag"-keuselys met die gekose module se
  // sessies.
  function populateDagSelect(kode, boodskap) {
    if (!dagSelect) return;
    dagSelect.innerHTML = '';

    var sessies = kode ? sessiesVirModule(kode) : [];
    if (sessies.length === 0) {
      var leeg = document.createElement('option');
      leeg.value = '';
      leeg.textContent = boodskap || 'Geen dae nie';
      leeg.disabled = true;
      leeg.selected = true;
      dagSelect.appendChild(leeg);
      dagSelect.disabled = true;
      return;
    }

    dagSelect.disabled = false;
    sessies.forEach(function (k) {
      var opt = document.createElement('option');
      opt.value = k.id;
      opt.textContent = k.dagLabel;
      dagSelect.appendChild(opt);
    });
    if (currentKlas && currentKlas.kode === kode) dagSelect.value = currentKlas.id;
  }

  // Hierdie funksie maak 'n klas die huidige een, laai sy klasregister van
  // die bediener en teken dan alles oor. As die gebruiker intussen 'n ander
  // klas kies, word die ou antwoord geïgnoreer.
  function kiesKlas(klas) {
    currentKlas = klas;
    studenteKas[klas.klasId] = [];
    selectedStudent = null;

    // Begin op vandag indien hierdie klas vandag plaasvind, anders op sy
    // mees onlangse roosterdatum.
    selectedDate = meesOnlangseKlasDatum(klas);
    displayYear = selectedDate.getFullYear();
    displayMonth = selectedDate.getMonth();

    renderKalender();
    renderStudentStats();
    renderDashboardLeeg();
    renderLeegBoodskap('Laai regte NFC-klasbywoning...');

    // Force=true is belangrik: 'n gewone page refresh / klas-herkeuse moet
    // die jongste databasis-skanderings kry.
    return laaiStudente(klas, selectedDate, true).then(function () {
      if (currentKlas !== klas) return;
      renderDashboard();
      renderRoster();

      // Laai die laaste roosterdae vir die grafiek en studentstatistiek.
      return laaiBywoningReeks(klas).then(function () {
        if (currentKlas !== klas) return;
        renderDashboard();
        renderRoster();
        renderStudentStats();
      });
    }).catch(function (err) {
      if (currentKlas !== klas) return;
      renderDashboardLeeg();
      renderLeegBoodskap('Kon nie die klasbywoning laai nie: ' + err.message);
    });
  }

  // ----- Event wiring -----
  // As die gebruiker 'n ander module kies, wys sy eerste sessie se data.
  if (moduleSelect) {
    moduleSelect.addEventListener('change', function () {
      populateDagSelect(moduleSelect.value);
      var eerste = sessiesVirModule(moduleSelect.value)[0];
      if (eerste) kiesKlas(eerste);
    });
  }

  // As die gebruiker 'n ander dag/sessie kies, wys daardie sessie se data.
  if (dagSelect) {
    dagSelect.addEventListener('change', function () {
      var gekies = klasse.filter(function (k) {
        return k.id === dagSelect.value;
      })[0];
      if (gekies) kiesKlas(gekies);
    });
  }

  // Die pyltjie-knoppie wat die kalender een maand terug vat.
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

  // Die pyltjie-knoppie wat die kalender een maand vorentoe vat.
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

  // As die venster van grootte verander of die tema wissel, teken die
  // grafieke oor sodat hulle inpas en die regte kleure het.
  function herteken() {
    renderDashboard();
    renderStudentStats();
  }
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(herteken, 150);
  });
  if (window.MutationObserver) {
    new MutationObserver(herteken).observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
  }

  // ----- Bootstrap -----
  // Sodra die bladsy klaar gelaai het, teken ons die leë raamwerk, laai dan
  // die klasse van die bediener en kies die eerste een.
  window.addEventListener('beforeunload', function () {
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
  });

  document.addEventListener('DOMContentLoaded', function () {
    maakRegisterTabel();
    renderKalender();
    renderStudentStats();
    renderDashboard();
    populateModuleSelect('Laai klasse...');
    renderLeegBoodskap('Laai klasse...');

    beginLiveRefresh();

    laaiKlasse().then(function (lys) {
      klasse = lys;
      populateModuleSelect();
      if (klasse.length === 0) {
        renderDashboardLeeg();
        renderLeegBoodskap(
          'Geen klasse is aan jou toegewys nie. ' +
          'Vra die administrateur om modules aan jou toe te wys.');
        return;
      }
      return kiesKlas(klasse[0]);
    }).catch(function (err) {
      klasse = [];
      populateModuleSelect('Kon nie klasse laai nie');
      renderDashboardLeeg();
      renderLeegBoodskap('Kon nie klasse laai nie: ' + err.message);
    });
  });
})();
