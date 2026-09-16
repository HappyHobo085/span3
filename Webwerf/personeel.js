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
 * NOG DEMO: die bywoning (ingeskandeer / nie ingeskandeer) word steeds
 * deterministies gegenereer (seed = module + datum) oor die REGTE klasregister,
 * omdat skanderings nog nie aan 'n klassessie gekoppel word nie. Dieselfde
 * dag wys dus altyd dieselfde resultaat, sonder enige stoor. Elke weeksdag
 * (Ma–Vr) tel as 'n klasdag, soos in die oorspronklike ontwerp, sodat die
 * linkerpaneel se lyste en grafiek altyd gevul is.
 *
 * Depends on:
 *   - main.js (login gate + Personeel gate; laai website_api_calls.js → MoonApi;
 *     verskaf hasRole())
 *   - styles.css (.kalender* klasse)
 *   - HTML ids: module-select, dag-select, dash-datum, dash-in-count, dash-out-count,
 *     dash-total-count, dash-percent-count,
 *     module-student-list, module-student-titel, module-student-caption,
 *     kal-title, kal-prev, kal-next, kal-grid, roster-search, roster-list,
 *     dash-student-card, student-stats-titel, stat-student-split,
 *     stat-student-caption.
 */

// Al die kode loop binne een omhulsel sodat die veranderlikes hier
// nie met die res van die webwerf deurmekaar raak nie.
(function () {
  // ----- Klasse (regte data van die bediener) -----
  // Elke klas lyk so: { id, klasId, kode, moduleNaam, dag, dagIndeks, begin,
  // eind, lokaal, label }. Die klasregister word apart per klas gelaai en
  // in `studenteKas` gehou sodat ons dit net een keer per klas afhaal.
  var klasse = [];
  var studenteKas = {}; // klasId -> [{ id, naam, van, nommer }]

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
  var rosterSearch = document.getElementById('roster-search');
  var rosterList = document.getElementById('roster-list');
  var statChart = document.getElementById('stat-bywoning-chart');
  var statAvg = document.getElementById('stat-bywoning-avg');
  var studentCard = document.getElementById('dash-student-card');
  var studentTitel = document.getElementById('student-stats-titel');
  var studentSplit = document.getElementById('stat-student-split');
  var studentCaption = document.getElementById('stat-student-caption');
  var moduleList = document.getElementById('module-student-list');
  var moduleTitel = document.getElementById('module-student-titel');
  var moduleCaption = document.getElementById('module-student-caption');

  // ----- Module state -----
  // Onthou watter klas en dag tans gekies is, en watter maand
  // die kalender op die oomblik wys.
  var vandag = new Date();
  vandag.setHours(0, 0, 0, 0);

  var currentKlas = null;      // null totdat die klasse gelaai is
  var selectedStudent = null;  // student wat in die klasregister gekies is
  var selectedDate = new Date(vandag);

  // Oor hoeveel klasdae die gekose student se bywoning bereken word.
  var STUDENT_STAT_DAE = 30;
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
      laasteSkandering: s.Laaste_Skandering || null
    };
  }

  // Hierdie funksie formateer 'n student se laaste inskandering, bv.
  // "Bitterbessie · 09:14" (plaaslike tyd), of 'n verstek-boodskap.
  function formatSkandering(sk) {
    if (!sk || !sk.tyd) return 'Geen skandering vandag';
    var d = new Date(sk.tyd);
    var tyd = '';
    if (!isNaN(d.getTime())) {
      tyd = (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' +
            (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
    }
    return [sk.lokaal, tyd].filter(Boolean).join(' · ') || 'Geen skandering vandag';
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

  // Hierdie funksie laai (en kas) die klasregister van 'n klas.
  function laaiStudente(klas) {
    if (studenteKas[klas.klasId]) return Promise.resolve(studenteKas[klas.klasId]);
    return MoonApi.fetchKlasStudente(klas.klasId).then(function (res) {
      if (!res || !res.sukses) {
        throw new Error(foutVanAntwoord(res, 'Kon nie die klasregister laai nie.'));
      }
      var lys = (res.data || []).map(studentVanApi);
      studenteKas[klas.klasId] = lys;
      return lys;
    });
  }

  // ----- Deterministiese "random" (seed = klas + datum) -----

  // Hierdie funksie verander 'n stuk teks in 'n vaste getal.
  // Dieselfde teks gee altyd dieselfde getal.
  /** djb2-agtige string hash → 32-bit unsigned int. */
  function hashString(str) {
    var h = 5381;
    for (var i = 0; i < str.length; i++) {
      h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  // Hierdie funksie maak 'n "toevalsgetal-maker" wat vir dieselfde
  // begingetal altyd dieselfde reeks getalle gee.
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

  // Hierdie funksie kyk of 'n dag 'n klasdag is: Maandag tot Vrydag,
  // en nie 'n dag in die toekoms nie. (Soos die oorspronklike ontwerp: elke
  // weeksdag wys bywoning, ongeag op watter dag die klas op die rooster staan,
  // sodat die linkerpaneel altyd data het om te wys.)
  /** Klasdae: weeksdae (Ma–Vr) wat nie in die toekoms lê nie. */
  function isKlasdag(d) {
    var dag = d.getDay(); // 0 = Sondag ... 6 = Saterdag
    return dag >= 1 && dag <= 5 && d.getTime() <= vandag.getTime();
  }

  /**
   * Deterministiese bywoning vir 'n klas op 'n datum.
   * Return null as daar geen klasdata is nie (nie 'n klasdag / toekoms),
   * anders { ingeskandeer: [{ student, tyd }], nieIngeskandeer: [student] }.
   */
  // Hierdie funksie werk uit watter studente op 'n dag ingeskandeer het
  // en watter nie (voorbeeld-data oor die regte klasregister; nie regte
  // skanderings nie).
  // Die bywoning per klas+dag word onthou sodat die studentelys (wat elke
  // student oor 30 klasdae nagaan) nie dieselfde dag herhaaldelik bereken nie.
  var bywoningKas = {};

  function kryBywoning(klas, datum) {
    if (!klas || !isKlasdag(datum)) return null;
    var sleutel = klas.kode + '|' + isoDate(datum);
    if (Object.prototype.hasOwnProperty.call(bywoningKas, sleutel)) return bywoningKas[sleutel];
    var resultaat = berekenBywoning(klas, datum);
    bywoningKas[sleutel] = resultaat;
    return resultaat;
  }

  // Die seed is die MODULE-kode + datum: al die klassessies van een module
  // deel dus dieselfde bywoningsrekord, sodat die balk "bywoning per module" is.
  function berekenBywoning(klas, datum) {
    var rand = mulberry32(hashString(klas.kode + '|' + isoDate(datum)));
    var ingeskandeer = [];
    var nieIngeskandeer = [];

    // Die klas se begintyd (bv. "8:00") bepaal die skandeertyd; anders 08:00.
    var beginMinute = tydNaMinute(klas.begin);
    if (beginMinute > 24 * 60) beginMinute = 8 * 60;

    // Vir elke student: omtrent 78% kans dat hy/sy ingeskandeer het,
    // met 'n tyd kort na die klas se begintyd; anders op die afwesig-lys.
    studenteVir(klas).forEach(function (s) {
      if (rand() < 0.78) {
        var totaalMinute = beginMinute + Math.floor(rand() * 25);
        var uur = Math.floor(totaalMinute / 60) % 24;
        var minuut = totaalMinute % 60;
        ingeskandeer.push({
          student: s,
          tyd: (uur < 10 ? '0' : '') + uur + ':' + (minuut < 10 ? '0' : '') + minuut
        });
      } else {
        nieIngeskandeer.push(s);
      }
    });

    return { ingeskandeer: ingeskandeer, nieIngeskandeer: nieIngeskandeer };
  }

  // ----- Kaartjies (selfde markup as kampus.js user cards) -----
  // Hierdie funksie bou 'n klein kaartjie met 'n student se naam en
  // ekstra inligting, wat in die lyste gewys word.
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

  // Hierdie funksie wys 'n boodskap in 'n lys as daar niks is om te wys nie.
  function renderLeegBoodskap(container, boodskap) {
    if (!container) return;
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

  // Hierdie funksie teken die Bywoning-kaartjie as 'n persentasie-sirkel
  // (null = geen klasdata nie, wys strepies).
  function renderPercentCard(persent) {
    if (!dashPercentCount) return;
    if (window.MoonStats && MoonStats.renderPercentRing) {
      MoonStats.renderPercentRing(dashPercentCount, { label: 'Bywoning', percent: persent });
    } else {
      dashPercentCount.textContent = 'Bywoning: ' + (persent === null ? '--' : persent + '%');
    }
  }

  // Hierdie funksie wys strepies op die KPI-teëls (geen klas gekies, geen
  // klasdag, of 'n fout). Die studentelys wys self die rede.
  function renderDashboardLeeg() {
    if (dashInCount) dashInCount.textContent = '--';
    if (dashOutCount) dashOutCount.textContent = '--';
    renderPercentCard(null);
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
      renderModuleStudente();
      return;
    }

    var studente = studenteVir(currentKlas);
    var bywoning = kryBywoning(currentKlas, selectedDate);

    // Die KPI-teëls wys net die syfers — die etikette staan reeds op die teëls.
    if (dashTotalCount) dashTotalCount.textContent = String(studente.length);

    // Die studentelys met vorderingsbalke volg die klas en die gekose dag.
    renderModuleStudente();

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
  }

  // ----- Statistieke: bywoning oor die laaste klasdae -----

  // Hierdie funksie gee die laaste `n` klasdae (Ma–Vr, tot en met vandag),
  // met die oudste dag eerste.
  function kryLaasteKlasdae(n) {
    var dae = [];
    var d = new Date(vandag);
    var guard = 0; // keer dat die lus ooit vashaak
    var maxGuard = n * 2 + 10; // genoeg kalenderdae vir n weeksdae (plus naweke)
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
        renderDashboard();
      }
    });

    // Die gemiddelde staan as gewone teks onder die grafiek.
    if (statAvg) {
      var avg = dae.length ? Math.round(som / dae.length) : 0;
      statAvg.textContent = 'Gemiddelde bywoning oor die laaste ' + dae.length + ' klasdae: ' + avg + '%';
    }
  }

  // ----- Studente per module: lys met vorderingsbalke (linkerpaneel) -----

  // Hierdie funksie maak die klein status-etiket vir die gekose dag:
  // ingeskandeer (met tyd), nie ingeskandeer nie, of geen klasdag nie.
  function maakDagStatus(dagByw, student) {
    var el = document.createElement('span');
    el.className = 'dag-status';
    if (!dagByw) {
      el.classList.add('dag-status--geen');
      el.textContent = 'Geen klasdag';
      return el;
    }
    var rekord = null;
    for (var i = 0; i < dagByw.ingeskandeer.length; i++) {
      if (dagByw.ingeskandeer[i].student.id === student.id) { rekord = dagByw.ingeskandeer[i]; break; }
    }
    if (rekord) {
      el.classList.add('dag-status--in');
      el.textContent = 'In · ' + rekord.tyd;
    } else {
      el.classList.add('dag-status--uit');
      el.textContent = 'Nie in';
    }
    return el;
  }

  /**
   * Hierdie funksie vul die linkerpaneel se studentelys: elke student in die
   * gekose klas se register kry 'n kaartjie met naam, studentenommer, die
   * gekose dag se status, en 'n vorderingsbalk wat wys hoeveel van die laaste
   * klasdae hy/sy vir hierdie module bygewoon het. Klik op 'n kaartjie om die
   * student te kies (dieselfde as in die klasregister regs).
   */
  function renderModuleStudente() {
    if (!moduleList) return;
    moduleList.innerHTML = '';

    if (!currentKlas) {
      if (moduleTitel) moduleTitel.textContent = 'Studente — bywoning per module';
      if (moduleCaption) moduleCaption.textContent = '';
      renderLeegBoodskap(moduleList, 'Geen klas gekies nie.');
      return;
    }

    var studente = studenteVir(currentKlas);
    var dae = kryLaasteKlasdae(STUDENT_STAT_DAE);
    if (moduleTitel) {
      moduleTitel.textContent = 'Studente — ' + currentKlas.kode +
        (currentKlas.moduleNaam ? ' · ' + currentKlas.moduleNaam : '');
    }
    if (moduleCaption) {
      moduleCaption.textContent = studente.length + ' student' + (studente.length === 1 ? '' : 'e') +
        ' · bywoning oor die laaste ' + dae.length + ' klasdae';
    }
    if (studente.length === 0) {
      renderLeegBoodskap(moduleList, 'Geen studente is aan hierdie module gekoppel nie.');
      return;
    }

    var dagByw = kryBywoning(currentKlas, selectedDate);

    studente.forEach(function (s) {
      var stats = kryStudentBywoning(currentKlas, s, STUDENT_STAT_DAE);
      var pct = stats.dae > 0 ? Math.round((stats.bygewoon / stats.dae) * 100) : 0;

      var card = document.createElement('div');
      card.className = 'user-card user-card--bywoning user-card--klikbaar';
      card.dataset.id = String(s.id);
      card.dataset.search = (s.naam + ' ' + s.van + ' ' + s.nommer).toLowerCase();
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label',
        s.naam + ' ' + s.van + ': ' + pct + '% bywoning vir ' + currentKlas.kode);
      if (selectedStudent && selectedStudent.id === s.id) card.classList.add('user-card--gekies');

      // Boonste ry: naam + nommer links, die gekose dag se status regs.
      var ry = document.createElement('div');
      ry.className = 'user-card-ry';
      var info = document.createElement('div');
      info.className = 'admin-user-info';
      var naam = document.createElement('div');
      naam.className = 'admin-user-name';
      naam.textContent = s.naam + ' ' + s.van;
      var sub = document.createElement('div');
      sub.className = 'admin-user-email';
      sub.textContent = s.nommer;
      info.appendChild(naam);
      info.appendChild(sub);
      ry.appendChild(info);
      ry.appendChild(maakDagStatus(dagByw, s));
      card.appendChild(ry);

      // Onderste ry: vorderingsbalk + persentasie + "x van y".
      var balkRy = document.createElement('div');
      balkRy.className = 'bywoning-balk-ry';
      var balk = document.createElement('div');
      balk.className = 'bywoning-balk';
      balk.setAttribute('role', 'progressbar');
      balk.setAttribute('aria-valuemin', '0');
      balk.setAttribute('aria-valuemax', '100');
      balk.setAttribute('aria-valuenow', String(pct));
      var vul = document.createElement('div');
      vul.className = 'bywoning-balk-vul' +
        (pct < 50 ? ' bywoning-balk-vul--laag' : (pct < 75 ? ' bywoning-balk-vul--middel' : ''));
      vul.style.width = pct + '%';
      balk.appendChild(vul);
      var pctEl = document.createElement('span');
      pctEl.className = 'bywoning-pct';
      pctEl.textContent = pct + '%';
      var detail = document.createElement('span');
      detail.className = 'bywoning-detail';
      detail.textContent = stats.bygewoon + ' van ' + stats.dae;
      balkRy.appendChild(balk);
      balkRy.appendChild(pctEl);
      balkRy.appendChild(detail);
      card.appendChild(balkRy);

      card.addEventListener('click', function () { selectStudent(s); });
      card.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          selectStudent(s);
        }
      });
      moduleList.appendChild(card);
    });
  }

  // ----- Studentbywoning: statistieke vir die gekose student -----

  /**
   * Hierdie funksie tel hoeveel keer 'n student oor die laaste `nDae` klasdae
   * die klas bygewoon en gemis het (dieselfde deterministiese data as die
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
   * in die linkerpaneel (onder die statistiek-kaart): 'n verdeling-balk met
   * bygewoon teenoor gemis, plus 'n opsomming. Geen student gekies = weggesteek.
   */
  function renderStudentStats() {
    if (!studentCard) return;

    if (!selectedStudent || !currentKlas) {
      studentCard.hidden = true;
      return;
    }

    var stats = kryStudentBywoning(currentKlas, selectedStudent, STUDENT_STAT_DAE);
    studentCard.hidden = false;

    if (studentTitel) {
      studentTitel.textContent = 'Studentbywoning — ' +
        selectedStudent.naam + ' ' + selectedStudent.van +
        ' (' + currentKlas.kode + ')';
    }

    if (window.MoonStats && studentSplit) {
      MoonStats.renderSplitBar(studentSplit, {
        title: 'Klasse bygewoon / gemis',
        segments: [
          { label: 'Bygewoon', value: stats.bygewoon, color: MoonStats.colors.series1 },
          { label: 'Gemis', value: stats.gemis, color: MoonStats.colors.error }
        ]
      });
    }

    if (studentCaption) {
      var pct = stats.dae > 0 ? Math.round((stats.bygewoon / stats.dae) * 100) : 0;
      studentCaption.textContent = selectedStudent.nommer + ' het ' +
        stats.bygewoon + ' van die laaste ' + stats.dae + ' klasdae bygewoon (' +
        pct + '%) en ' + stats.gemis + ' gemis.';
    }
  }

  // Hierdie funksie kies 'n student (of ontkies met 'n tweede klik) en
  // werk die uitgeligte kaartjie in die klasregister by.
  function selectStudent(student) {
    var selfde = selectedStudent && selectedStudent.id === student.id;
    selectedStudent = selfde ? null : student;

    [rosterList, moduleList].forEach(function (lys) {
      if (!lys) return;
      lys.querySelectorAll('.user-card').forEach(function (row) {
        row.classList.toggle('user-card--gekies',
          !!selectedStudent && row.dataset.id === String(selectedStudent.id));
      });
    });
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
          renderDashboard();
        });

        kalGrid.appendChild(cell);
      })(d);
    }
  }

  // ----- Klasregister (regterpaneel-lys) -----
  // Hierdie funksie wys die volle klasregister van die gekose klas. Elke
  // kaartjie is klikbaar: kies 'n student om sy/haar bywoningstatistieke
  // links te sien.
  function renderRoster() {
    if (!rosterList) return;
    rosterList.innerHTML = '';

    if (!currentKlas) {
      renderLeegBoodskap(rosterList, 'Geen klas gekies nie.');
      return;
    }

    var studente = studenteVir(currentKlas);
    if (studente.length === 0) {
      renderLeegBoodskap(rosterList,
        'Geen studente is aan hierdie klas gekoppel nie. ' +
        'Vra die administrateur om groepe of studente aan die module toe te wys.');
      return;
    }

    studente.forEach(function (s) {
      var card = createStudentCard(s, s.nommer + ' · ' + formatSkandering(s.laasteSkandering));
      card.classList.add('user-card--klikbaar');
      card.dataset.id = String(s.id);
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label',
        'Wys bywoningstatistieke vir ' + s.naam + ' ' + s.van);
      if (selectedStudent && selectedStudent.id === s.id) {
        card.classList.add('user-card--gekies');
      }
      card.addEventListener('click', function () { selectStudent(s); });
      card.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          selectStudent(s);
        }
      });
      rosterList.appendChild(card);
    });
    applyRosterFilter();
  }

  // Hierdie funksie steek studente in die klaslys weg wat nie by die
  // soekwoord pas nie.
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
    bywoningKas = {}; // ander register = ander bywoning
    // 'n Ander klas het 'n ander klasregister: maak die keuse skoon.
    selectedStudent = null;
    renderStudentStats();
    renderDashboard();
    renderLeegBoodskap(rosterList, 'Laai klasregister...');

    return laaiStudente(klas).then(function () {
      if (currentKlas !== klas) return;
      bywoningKas = {}; // die register is nou gelaai: bereken oor
      renderDashboard();
      renderRoster();
    }).catch(function (err) {
      if (currentKlas !== klas) return;
      renderDashboardLeeg();
      renderLeegBoodskap(rosterList, 'Kon nie die klasregister laai nie: ' + err.message);
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

  // Elke keer as die gebruiker in die soekblokkie tik, word die lys gefiltreer.
  if (rosterSearch) {
    rosterSearch.addEventListener('input', applyRosterFilter);
  }

  // As die venster van grootte verander, teken die grafiek oor sodat dit inpas.
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderStats, 150);
  });

  // ----- Bootstrap -----
  // Sodra die bladsy klaar gelaai het, teken ons die leë raamwerk, laai dan
  // die klasse van die bediener en kies die eerste een.
  document.addEventListener('DOMContentLoaded', function () {
    renderKalender();
    renderDashboard();
    populateModuleSelect('Laai klasse...');
    renderLeegBoodskap(rosterList, 'Laai klasse...');

    laaiKlasse().then(function (lys) {
      klasse = lys;
      populateModuleSelect();
      if (klasse.length === 0) {
        renderDashboardLeeg();
        renderLeegBoodskap(rosterList,
          'Geen klasse is aan jou toegewys nie. ' +
          'Vra die administrateur om modules aan jou toe te wys.');
        return;
      }
      return kiesKlas(klasse[0]);
    }).catch(function (err) {
      klasse = [];
      populateModuleSelect('Kon nie klasse laai nie');
      renderDashboardLeeg();
      renderLeegBoodskap(rosterList, 'Kon nie klasse laai nie: ' + err.message);
    });
  });
})();
