/**
 * stats.js — Klein grafiek-biblioteek vir die MOON statistiek-panele.
 *
 * Wat dit doen, in eenvoudige woorde:
 *   - Teken 'n meter (bv. koshuis-kapasiteit) met 'n kleur wat waarsku as dit vol raak.
 *   - Teken 'n verdeling-balk wat wys hoeveel mense in en uit is.
 *   - Teken 'n lyngrafiek wat oor tyd wys hoeveel mense in is (regstreeks).
 *   - Teken 'n kolomgrafiek vir klasbywoning oor die laaste klasdae.
 *
 * Die bladsye (koshuis.js, kampus.js, personeel.js) roep hierdie funksies
 * deur "window.MoonStats". Alles is gewone SVG/HTML — geen biblioteke nie.
 *
 * Kleure: die twee reekskleure (#009fd4 studente, #7b61ff personeel) is met
 * die dataviz-validator teen die donker agtergrond (#0A1423) getoets:
 * kleurblind-skeiding ΔE 11.9 (>= 8 teiken) en kontras >= 3:1 — albei slaag.
 */

(function () {
  // Lees 'n kleur uit die CSS-veranderlikes in styles.css sodat die grafieke
  // saam met die tema (lig/donker) verander wanneer hulle weer geteken word.
  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  // ----- Kleure wat al die grafieke deel -----
  // Die tema-afhanklike kleure is "getters": elke keer as 'n grafiek geteken
  // word, word die huidige tema se waarde gelees.
  var COLORS = {
    series1: '#009fd4',              // Studente — donkerder stap van --accent-2
    series2: '#7b61ff',              // Personeel — die --accent kleur
    get dim() { return cssVar('--viz-dim', 'rgba(255,255,255,0.20)'); },   // de-emfase
    get grid() { return cssVar('--viz-grid', 'rgba(255,255,255,0.07)'); }, // rooster-lyne
    get axis() { return cssVar('--viz-axis', 'rgba(255,255,255,0.35)'); }, // as-etikette
    get ink() { return cssVar('--viz-ink', 'rgba(255,255,255,0.85)'); },   // waarde-etikette
    get surface() { return cssVar('--bg', '#0A1423'); },                   // blad-agtergrond
    accent: '#7b61ff',
    warning: '#f59e0b',
    error: '#ef4444'
  };

  var SVG_NS = 'http://www.w3.org/2000/svg';

  // Hierdie funksie maak 'n SVG-element met die gegewe eienskappe.
  function svgEl(name, attrs) {
    var el = document.createElementNS(SVG_NS, name);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        el.setAttribute(k, attrs[k]);
      });
    }
    return el;
  }

  // Hierdie funksie skryf 'n tyd as HH:MM:SS.
  function fmtTime(d) {
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }

  // ----- Tooltip: een gedeelde blokkie wat by die muis verskyn -----
  var tipEl = null;

  function ensureTip() {
    if (tipEl) return tipEl;
    tipEl = document.createElement('div');
    tipEl.className = 'viz-tooltip';
    document.body.appendChild(tipEl);
    return tipEl;
  }

  /**
   * Wys die tooltip by (x, y). content = { title, rows: [{ color, value, label }] }.
   * Alle teks word met textContent gesit (nooit innerHTML nie) — name kom van die bediener.
   */
  function showTip(content, x, y) {
    var tip = ensureTip();
    tip.innerHTML = '';

    if (content.title) {
      var t = document.createElement('div');
      t.className = 'viz-tooltip-title';
      t.textContent = content.title;
      tip.appendChild(t);
    }

    (content.rows || []).forEach(function (r) {
      var row = document.createElement('div');
      row.className = 'viz-tooltip-row';
      if (r.color) {
        var key = document.createElement('span');
        key.className = 'viz-tooltip-key';
        key.style.background = r.color;
        row.appendChild(key);
      }
      var val = document.createElement('b');
      val.textContent = r.value;
      row.appendChild(val);
      if (r.label) {
        var lab = document.createElement('span');
        lab.textContent = r.label;
        row.appendChild(lab);
      }
      tip.appendChild(row);
    });

    tip.style.display = 'block';
    var rect = tip.getBoundingClientRect();
    var left = x + 12;
    var top = y + 12;
    if (left + rect.width > window.innerWidth - 8) left = x - rect.width - 12;
    if (top + rect.height > window.innerHeight - 8) top = y - rect.height - 12;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function hideTip() {
    if (tipEl) tipEl.style.display = 'none';
  }

  // Hierdie funksie wys 'n "geen data" boodskap in 'n grafiek-houer.
  function renderEmpty(container, boodskap) {
    container.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'viz-empty';
    div.textContent = boodskap;
    container.appendChild(div);
  }

  // Hierdie funksie kies 'n mooi ronde boonste waarde vir die y-as.
  function niceMax(m) {
    var steps = [4, 6, 8, 10, 20, 40, 60, 80, 100, 200, 400, 600, 800, 1000];
    for (var i = 0; i < steps.length; i++) {
      if (steps[i] >= m) return steps[i];
    }
    var v = 1000;
    while (v < m) v *= 2;
    return v;
  }

  /**
   * Meter — vir 'n enkele verhouding teen 'n limiet (bv. inwoners / kapasiteit).
   * opts = { label, value, max }
   * Die vul-kleur dra die erns: gewoon → waarskuwing (>= 80%) → vol (>= 95%),
   * altyd saam met 'n ikoon + woord sodat kleur nooit alleen die boodskap dra nie.
   */
  function renderMeter(container, opts) {
    if (!container) return;

    var value = Number(opts.value) || 0;
    var max = Number(opts.max) || 0;
    var pct = max > 0 ? Math.min(1, value / max) : 0;

    // Kies die kleur en status-woord volgens hoe vol dit is.
    var fill = COLORS.accent;
    var track = 'rgba(123,97,255,0.15)';
    var status = '';
    var statusColor = '';
    if (max > 0 && pct >= 0.95) {
      fill = COLORS.error; track = 'rgba(239,68,68,0.15)';
      status = '⛔ Vol'; statusColor = COLORS.error;
    } else if (max > 0 && pct >= 0.8) {
      fill = COLORS.warning; track = 'rgba(245,158,11,0.15)';
      status = '⚠ Byna vol'; statusColor = COLORS.warning;
    }

    container.innerHTML = '';

    var head = document.createElement('div');
    head.className = 'viz-meter-head';
    var lab = document.createElement('span');
    lab.className = 'viz-meter-label';
    lab.textContent = opts.label || '';
    var val = document.createElement('span');
    val.className = 'viz-meter-value';
    val.textContent = value + ' / ' + (max > 0 ? max : '--');
    head.appendChild(lab);
    head.appendChild(val);
    container.appendChild(head);

    var trackEl = document.createElement('div');
    trackEl.className = 'viz-meter-track';
    trackEl.style.background = track;
    var fillEl = document.createElement('div');
    fillEl.className = 'viz-meter-fill';
    fillEl.style.background = fill;
    fillEl.style.width = (pct * 100) + '%';
    trackEl.appendChild(fillEl);
    container.appendChild(trackEl);

    var sub = document.createElement('div');
    sub.className = 'viz-meter-sub';
    var pctSpan = document.createElement('span');
    pctSpan.textContent = max > 0 ? Math.round(pct * 100) + '% beset' : 'Kapasiteit onbekend';
    sub.appendChild(pctSpan);
    if (status) {
      var st = document.createElement('span');
      st.className = 'viz-meter-status';
      st.style.color = statusColor;
      st.textContent = status;
      sub.appendChild(st);
    }
    container.appendChild(sub);
  }

  /**
   * Verdeling-balk — een gestapelde horisontale balk met 2 segmente (bv. in vs uit),
   * geskei deur 'n 2px gaping. Die tellings staan altyd ook as teks in die legende,
   * sodat die tooltip nooit die enigste plek is waar die waarde leef nie.
   * opts = { title, segments: [{ label, value, color }] }
   */
  function renderSplitBar(container, opts) {
    if (!container) return;

    var segs = opts.segments || [];
    var total = segs.reduce(function (s, x) { return s + (Number(x.value) || 0); }, 0);

    container.innerHTML = '';

    if (opts.title) {
      var head = document.createElement('div');
      head.className = 'viz-split-head';
      var title = document.createElement('span');
      title.className = 'viz-split-title';
      title.textContent = opts.title;
      var tot = document.createElement('span');
      tot.className = 'viz-split-total';
      tot.textContent = total + ' totaal';
      head.appendChild(title);
      head.appendChild(tot);
      container.appendChild(head);
    }

    var track = document.createElement('div');
    track.className = 'viz-split-track';

    if (total === 0) {
      // Niks om te verdeel nie: wys 'n dowwe leë balk.
      var leeg = document.createElement('div');
      leeg.className = 'viz-split-empty';
      leeg.textContent = 'Geen data';
      track.appendChild(leeg);
    } else {
      segs.forEach(function (seg) {
        var v = Number(seg.value) || 0;
        if (v <= 0) return; // 'n leë segment word nie geteken nie
        var pct = Math.round((v / total) * 100);

        var el = document.createElement('div');
        el.className = 'viz-split-seg';
        el.style.flexGrow = String(v);
        el.style.background = seg.color;
        el.setAttribute('tabindex', '0');
        el.setAttribute('aria-label', seg.label + ': ' + v + ' (' + pct + '%)');
        // Wys die persentasie net as die segment breed genoeg is dat dit pas.
        if (pct >= 18) el.textContent = pct + '%';

        function segTip(x, y) {
          showTip({
            title: opts.title || '',
            rows: [{ color: seg.color, value: String(v), label: seg.label + ' (' + pct + '%)' }]
          }, x, y);
        }
        el.addEventListener('pointermove', function (ev) { segTip(ev.clientX, ev.clientY); });
        el.addEventListener('pointerleave', hideTip);
        el.addEventListener('focus', function () {
          var r = el.getBoundingClientRect();
          segTip(r.left + r.width / 2, r.top);
        });
        el.addEventListener('blur', hideTip);

        track.appendChild(el);
      });
    }
    container.appendChild(track);

    // Legende met die werklike tellings — die "tabel-weergawe" van hierdie balk.
    var legend = document.createElement('div');
    legend.className = 'viz-legend';
    segs.forEach(function (seg) {
      var key = document.createElement('span');
      key.className = 'viz-key';
      var swatch = document.createElement('i');
      swatch.style.background = seg.color;
      key.appendChild(swatch);
      var txt = document.createElement('span');
      txt.textContent = seg.label + ' ';
      key.appendChild(txt);
      var b = document.createElement('b');
      b.textContent = String(Number(seg.value) || 0);
      key.appendChild(b);
      legend.appendChild(key);
    });
    container.appendChild(legend);
  }

  /**
   * Tendens-lyngrafiek — wys hoe 'n telling oor tyd verander (regstreeks).
   * opts = { times: [Date], series: [{ label, color, values: [getal] }], height }
   * Die lyn is 2px, die endpunt kry 'n kol met 'n ring in die agtergrond-kleur,
   * en die jongste waarde staan direk langs die lyn se ent.
   */
  function renderTrend(container, opts) {
    if (!container) return;

    var times = opts.times || [];
    var series = opts.series || [];
    container.innerHTML = '';

    if (times.length < 2) {
      renderEmpty(container, 'Versamel data — wag ’n paar sekondes…');
      return;
    }

    var w = container.clientWidth || 320;
    var h = opts.height || 150;
    var padL = 34, padR = 48, padT = 12, padB = 20;
    var n = times.length;

    var maxV = 1;
    series.forEach(function (s) {
      s.values.forEach(function (v) { if (v > maxV) maxV = v; });
    });
    var yMax = niceMax(maxV);

    function X(i) { return padL + i * (w - padL - padR) / (n - 1); }
    function Y(v) { return padT + (1 - v / yMax) * (h - padT - padB); }

    var svg = svgEl('svg', {
      width: w, height: h, viewBox: '0 0 ' + w + ' ' + h,
      'class': 'viz-svg', role: 'img',
      'aria-label': 'Tendens-grafiek: ' + series.map(function (s) {
        return s.label + ' tans ' + s.values[n - 1];
      }).join(', ')
    });

    // Rooster: dun soliede lyne by 0, die middel en die maksimum.
    [0, yMax / 2, yMax].forEach(function (tv) {
      var gy = Y(tv);
      svg.appendChild(svgEl('line', {
        x1: padL, x2: w - padR, y1: gy, y2: gy,
        stroke: COLORS.grid, 'stroke-width': 1
      }));
      var tick = svgEl('text', {
        x: padL - 6, y: gy + 3, 'text-anchor': 'end',
        'font-size': 9, fill: COLORS.axis,
        style: 'font-variant-numeric:tabular-nums'
      });
      tick.textContent = String(tv);
      svg.appendChild(tick);
    });

    // Tye onderaan: net die eerste en die laaste monster.
    var t0 = svgEl('text', {
      x: padL, y: h - 5, 'text-anchor': 'start',
      'font-size': 9, fill: COLORS.axis
    });
    t0.textContent = fmtTime(times[0]);
    svg.appendChild(t0);
    var t1 = svgEl('text', {
      x: w - padR, y: h - 5, 'text-anchor': 'end',
      'font-size': 9, fill: COLORS.axis
    });
    t1.textContent = fmtTime(times[n - 1]);
    svg.appendChild(t1);

    // Die lyne self, met 'n kol en 'n waarde-etiket by elke lyn se ent.
    var endLabels = [];
    series.forEach(function (s) {
      var pts = s.values.map(function (v, i) { return X(i) + ',' + Y(v); }).join(' ');
      svg.appendChild(svgEl('polyline', {
        points: pts, fill: 'none', stroke: s.color,
        'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'
      }));
      var lx = X(n - 1);
      var ly = Y(s.values[n - 1]);
      svg.appendChild(svgEl('circle', {
        cx: lx, cy: ly, r: 4.5, fill: s.color,
        stroke: COLORS.surface, 'stroke-width': 2
      }));
      endLabels.push({ x: lx, y: ly, v: s.values[n - 1] });
    });

    // As twee ent-etikette bo-op mekaar sit, skuif hulle effens uitmekaar.
    endLabels.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < endLabels.length; i++) {
      if (endLabels[i].y - endLabels[i - 1].y < 12) {
        endLabels[i].y = endLabels[i - 1].y + 12;
      }
    }
    endLabels.forEach(function (l) {
      var txt = svgEl('text', {
        x: l.x + 9, y: l.y + 4, 'font-size': 10,
        'font-weight': 600, fill: COLORS.ink
      });
      txt.textContent = String(l.v);
      svg.appendChild(txt);
    });

    // Kruishaar + tooltip: beweeg oor die grafiek en sien elke reeks se waarde.
    var cross = svgEl('line', {
      y1: padT, y2: h - padB, x1: padL, x2: padL,
      stroke: COLORS.axis, 'stroke-width': 1, visibility: 'hidden'
    });
    svg.appendChild(cross);

    var overlay = svgEl('rect', {
      x: padL, y: 0, width: Math.max(0, w - padL - padR), height: h, fill: 'transparent'
    });
    overlay.addEventListener('pointermove', function (ev) {
      var box = svg.getBoundingClientRect();
      var px = ev.clientX - box.left;
      var idx = Math.round((px - padL) / ((w - padL - padR) / (n - 1)));
      idx = Math.max(0, Math.min(n - 1, idx));
      cross.setAttribute('x1', X(idx));
      cross.setAttribute('x2', X(idx));
      cross.setAttribute('visibility', 'visible');
      showTip({
        title: fmtTime(times[idx]),
        rows: series.map(function (s) {
          return { color: s.color, value: String(s.values[idx]), label: s.label };
        })
      }, ev.clientX, ev.clientY);
    });
    overlay.addEventListener('pointerleave', function () {
      cross.setAttribute('visibility', 'hidden');
      hideTip();
    });
    svg.appendChild(overlay);

    container.appendChild(svg);

    // Legende (net wanneer daar meer as een reeks is — een reeks se titel sê klaar wat dit is).
    if (series.length > 1) {
      var legend = document.createElement('div');
      legend.className = 'viz-legend';
      series.forEach(function (s) {
        var key = document.createElement('span');
        key.className = 'viz-key viz-key--line';
        var swatch = document.createElement('i');
        swatch.style.background = s.color;
        key.appendChild(swatch);
        var txt = document.createElement('span');
        txt.textContent = s.label;
        key.appendChild(txt);
        legend.appendChild(key);
      });
      container.appendChild(legend);
    }
  }

  // Hierdie funksie bou die pad vir een kolom: plat onderkant, ronde boonste hoeke.
  function barPath(x, baseY, wBar, topY, r) {
    if (baseY - topY < r) r = Math.max(0, baseY - topY);
    return 'M' + x + ' ' + baseY +
           ' L' + x + ' ' + (topY + r) +
           ' Q' + x + ' ' + topY + ' ' + (x + r) + ' ' + topY +
           ' L' + (x + wBar - r) + ' ' + topY +
           ' Q' + (x + wBar) + ' ' + topY + ' ' + (x + wBar) + ' ' + (topY + r) +
           ' L' + (x + wBar) + ' ' + baseY + ' Z';
  }

  /**
   * Kolomgrafiek vir persentasies (0–100) — bv. bywoning oor die laaste klasdae.
   * Die gekose kolom kry die aksent-kleur (klem), die res is dowwe grys.
   * Elke kolom is klikbaar en met die sleutelbord bereikbaar.
   * opts = { items: [{ label, tick, value, detail }], selectedIndex, onSelect, height }
   */
  function renderColumns(container, opts) {
    if (!container) return;

    var items = opts.items || [];
    container.innerHTML = '';
    if (items.length === 0) {
      renderEmpty(container, 'Geen data nie.');
      return;
    }

    var w = container.clientWidth || 320;
    var h = opts.height || 160;
    var padL = 34, padR = 6, padT = 14, padB = 18;
    var plotH = h - padT - padB;
    var baseY = h - padB;
    var band = (w - padL - padR) / items.length;
    var barW = Math.max(6, Math.min(24, band - 4));

    var svg = svgEl('svg', {
      width: w, height: h, viewBox: '0 0 ' + w + ' ' + h,
      'class': 'viz-svg', role: 'group', 'aria-label': 'Bywoning per klasdag'
    });

    // Rooster by 0%, 50% en 100%.
    [0, 50, 100].forEach(function (tv) {
      var gy = baseY - plotH * tv / 100;
      svg.appendChild(svgEl('line', {
        x1: padL, x2: w - padR, y1: gy, y2: gy,
        stroke: COLORS.grid, 'stroke-width': 1
      }));
      var tick = svgEl('text', {
        x: padL - 6, y: gy + 3, 'text-anchor': 'end',
        'font-size': 9, fill: COLORS.axis,
        style: 'font-variant-numeric:tabular-nums'
      });
      tick.textContent = tv + '%';
      svg.appendChild(tick);
    });

    items.forEach(function (it, i) {
      var v = Math.max(0, Math.min(100, Number(it.value) || 0));
      var x = padL + i * band + (band - barW) / 2;
      var topY = baseY - plotH * v / 100;
      var selected = i === opts.selectedIndex;
      var fill = selected ? COLORS.accent : COLORS.dim;

      var g = svgEl('g', { 'class': 'viz-col' });

      if (v > 0) {
        g.appendChild(svgEl('path', {
          d: barPath(x, baseY, barW, topY, 4),
          fill: fill, 'class': 'viz-col-bar'
        }));
      }

      // Die waarde staan net op die gekose kolom — die res leef in die tooltip.
      if (selected && v > 0) {
        var valTxt = svgEl('text', {
          x: x + barW / 2, y: topY - 5, 'text-anchor': 'middle',
          'font-size': 10, 'font-weight': 700, fill: COLORS.ink
        });
        valTxt.textContent = v + '%';
        svg.appendChild(valTxt);
      }

      // Dag-etiket onder die kolom (elke tweede een as dit te nou raak).
      if (band >= 22 || i % 2 === 0) {
        var tickTxt = svgEl('text', {
          x: padL + i * band + band / 2, y: h - 5, 'text-anchor': 'middle',
          'font-size': 8.5, fill: COLORS.axis
        });
        tickTxt.textContent = it.tick || it.label;
        svg.appendChild(tickTxt);
      }

      // Die trefteiken is die hele band — groter as die kolom self —
      // en werk ook met die sleutelbord (Enter of Spasie kies die dag).
      var hit = svgEl('rect', {
        x: padL + i * band, y: padT, width: band, height: plotH,
        fill: 'transparent', tabindex: 0, role: 'button',
        'aria-label': it.label + ': ' + v + '%' + (it.detail ? ' — ' + it.detail : '')
      });

      function colTip(cx, cy) {
        showTip({
          title: it.label,
          rows: [{ color: fill, value: v + '%', label: it.detail || '' }]
        }, cx, cy);
      }
      hit.addEventListener('pointermove', function (ev) { colTip(ev.clientX, ev.clientY); });
      hit.addEventListener('pointerleave', hideTip);
      hit.addEventListener('focus', function () {
        var r = hit.getBoundingClientRect();
        colTip(r.left + r.width / 2, r.top);
      });
      hit.addEventListener('blur', hideTip);
      hit.addEventListener('click', function () {
        if (opts.onSelect) opts.onSelect(i);
      });
      hit.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          if (opts.onSelect) opts.onSelect(i);
        }
      });

      g.appendChild(hit);
      svg.appendChild(g);
    });

    container.appendChild(svg);
  }

  /**
   * Persentasie-sirkel — 'n ring wat een persentasie (0–100) wys, met die
   * syfer in die middel en die etiket daaronder (bv. die dag se klasbywoning).
   * Die waarde staan altyd as teks in die middel, so kleur dra nooit alleen
   * die boodskap nie. percent = null wys strepies (geen klasdata nie).
   * opts = { label, percent }
   */
  function renderPercentRing(container, opts) {
    if (!container) return;

    var pct = (opts.percent === null || opts.percent === undefined || isNaN(Number(opts.percent)))
      ? null
      : Math.max(0, Math.min(100, Number(opts.percent)));

    container.innerHTML = '';

    var size = 68, stroke = 7;
    var c = size / 2;
    var r = (size - stroke) / 2;
    var omtrek = 2 * Math.PI * r;

    var svg = svgEl('svg', {
      width: size, height: size, viewBox: '0 0 ' + size + ' ' + size,
      'class': 'viz-ring-svg', role: 'img',
      'aria-label': (opts.label || '') + ': ' + (pct === null ? '--' : pct + '%')
    });

    // Die dowwe agtergrond-ring (die "baan").
    svg.appendChild(svgEl('circle', {
      cx: c, cy: c, r: r, fill: 'none',
      stroke: pct === null ? COLORS.grid : 'rgba(123,97,255,0.15)',
      'stroke-width': stroke
    }));

    // Die gevulde boog — begin bo (12-uur) en groei kloksgewys.
    if (pct !== null && pct > 0) {
      svg.appendChild(svgEl('circle', {
        cx: c, cy: c, r: r, fill: 'none',
        stroke: COLORS.accent, 'stroke-width': stroke,
        'stroke-linecap': pct < 100 ? 'round' : 'butt',
        'stroke-dasharray': (omtrek * pct / 100) + ' ' + omtrek,
        transform: 'rotate(-90 ' + c + ' ' + c + ')'
      }));
    }

    var txt = svgEl('text', {
      x: c, y: c + 4.5, 'text-anchor': 'middle',
      'font-size': 14, 'font-weight': 700, fill: COLORS.ink,
      style: 'font-variant-numeric:tabular-nums'
    });
    txt.textContent = pct === null ? '--' : pct + '%';
    svg.appendChild(txt);
    container.appendChild(svg);

    if (opts.label) {
      var lab = document.createElement('div');
      lab.className = 'viz-ring-label';
      lab.textContent = opts.label;
      container.appendChild(lab);
    }
  }

  // Maak alles beskikbaar vir die res van die webwerf.
  window.MoonStats = {
    colors: COLORS,
    renderMeter: renderMeter,
    renderSplitBar: renderSplitBar,
    renderTrend: renderTrend,
    renderColumns: renderColumns,
    renderPercentRing: renderPercentRing
  };
})();
