/* Small chart kit: SVG and HTML, no libraries, no internet. Every chart has a hover tooltip.
 * Text coming from data is always escaped. */
(function (root) {
  'use strict';
  var C = {};
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* ------------------------------------------------------------ formatting */
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var F = {
    esc: esc,
    num: function (x, dp) { if (x == null || isNaN(x)) return '-'; return (x < 0 ? '−' : '') + Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 }); },
    inr: function (x) { return x == null ? '-' : '₹ ' + F.num(x, 0); },
    cur: function (x, ccy) { return ccy === 'USD' ? 'USD ' + F.num(x, 2) : F.inr(x); },
    cr: function (x) {
      var a = Math.abs(x), s = x < 0 ? '−' : '';
      if (a >= 1e7) return s + (a / 1e7).toFixed(2) + ' Cr';
      if (a >= 1e5) return s + (a / 1e5).toFixed(2) + ' L';
      return s + Math.round(a).toLocaleString('en-IN');
    },
    pct: function (x, dp) { if (x == null) return '-'; return (x < 0 ? '−' : '+') + Math.abs(x * 100).toFixed(dp == null ? 1 : dp) + '%'; },
    dmy: function (iso) { return iso ? (+iso.slice(8, 10)) + ' ' + MON[+iso.slice(5, 7) - 1] + ' ' + iso.slice(0, 4) : '-'; },
    mon: function (iso) { return MON[+iso.slice(5, 7) - 1] + ' ' + iso.slice(2, 4); },
    gainHtml: function (g, p) {
      var cls = g > 0.5 ? 'up' : (g < -0.5 ? 'down' : 'flat'), arrow = g > 0.5 ? '▲ ' : (g < -0.5 ? '▼ ' : '');
      return '<span class="' + cls + '">' + arrow + F.num(g, 0) + (p == null ? '' : ' (' + F.pct(p) + ')') + '</span>';
    }
  };
  C.F = F;

  /* ------------------------------------------------------------ tooltip */
  var tipEl = null;
  function tip() { return tipEl || (tipEl = document.getElementById('tip')); }
  C.showTip = function (html, e) {
    var t = tip(); t.innerHTML = html; t.style.display = 'block';
    var w = t.offsetWidth, h = t.offsetHeight, x = e.clientX + 14, y = e.clientY + 14;
    if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
    if (y + h > window.innerHeight - 8) y = e.clientY - h - 14;
    t.style.left = Math.max(4, x) + 'px'; t.style.top = Math.max(4, y) + 'px';
  };
  C.hideTip = function () { var t = tip(); if (t) t.style.display = 'none'; };
  function row(color, name, value, dash) {
    return '<div class="tr"><span class="key" style="border-top:3px ' + (dash ? 'dashed ' : 'solid ') + color + '"></span><span class="tv">' + value + '</span><span class="tn">' + esc(name) + '</span></div>';
  }
  C.tipRow = row;

  function niceMax(v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }
  function niceRange(lo, hi, n) {
    var span = hi - lo || Math.abs(hi) || 1, raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
    var step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
    var a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, t = [];
    for (var v = a; v <= b + step / 2; v += step) t.push(v);
    return { min: a, max: b, ticks: t };
  }

  /* ------------------------------------------------------------ line chart */
  /* o: {labels:[...], series:[{name,color,dash,values:[...]}], height, fmt, tipTitle:[...]} */
  C.line = function (el, o) {
    var W = el.clientWidth || 600, H = o.height || 230, m = { l: 62, r: 14, t: 10, b: 26 }, n = o.labels.length;
    var all = [].concat.apply([], o.series.map(function (s) { return s.values; }));
    var rg = niceRange(Math.min.apply(null, all), Math.max.apply(null, all), 4), pw = W - m.l - m.r, ph = H - m.t - m.b;
    function X(i) { return m.l + (n === 1 ? pw / 2 : pw * i / (n - 1)); }
    function Y(v) { return m.t + ph * (1 - (v - rg.min) / (rg.max - rg.min)); }
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria || 'Line chart') + '">';
    rg.ticks.forEach(function (t) {
      s += '<line class="grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text class="ax" x="' + (m.l - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + esc(o.fmt ? o.fmt(t) : t) + '</text>';
    });
    var every = Math.ceil(n / Math.max(2, Math.floor(pw / 70)));
    o.labels.forEach(function (l, i) { if ((i % every === 0 && n - 1 - i >= Math.ceil(every * 0.75)) || i === n - 1) s += '<text class="ax" x="' + X(i) + '" y="' + (H - 7) + '" text-anchor="' + (i === n - 1 && n > 2 ? 'end' : 'middle') + '">' + esc(l) + '</text>'; });
    o.series.forEach(function (se) {
      s += '<polyline class="' + (se.dash ? 'ln2' : 'ln') + '"' + (se.dash ? '' : ' pathLength="1"') + ' fill="none" stroke="' + se.color + '" stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"' + (se.dash ? ' stroke-dasharray="6 4"' : '') + ' points="' + se.values.map(function (v, i) { return X(i).toFixed(1) + ',' + Y(v).toFixed(1); }).join(' ') + '"/>';
      var last = se.values.length - 1;
      s += '<circle class="end" cx="' + X(last) + '" cy="' + Y(se.values[last]) + '" r="4" fill="' + se.color + '" style="stroke:var(--dot)" stroke-width="2"/>';
    });
    s += '<line id="xh" class="xh" x1="0" x2="0" y1="' + m.t + '" y2="' + (m.t + ph) + '" style="display:none"/><g id="dots"></g></svg>';
    el.innerHTML = s;
    var svg = el.firstChild, xh = svg.querySelector('#xh'), dots = svg.querySelector('#dots');
    el.onpointermove = function (e) {
      var r = svg.getBoundingClientRect(), x = (e.clientX - r.left) * W / r.width, i = Math.round((x - m.l) / (pw / Math.max(1, n - 1)));
      i = Math.max(0, Math.min(n - 1, i));
      xh.setAttribute('x1', X(i)); xh.setAttribute('x2', X(i)); xh.style.display = '';
      dots.innerHTML = o.series.map(function (se) { return '<circle cx="' + X(i) + '" cy="' + Y(se.values[i]) + '" r="4.5" fill="' + se.color + '" style="stroke:var(--dot)" stroke-width="2"/>'; }).join('');
      C.showTip('<div class="th">' + esc(o.tipTitle ? o.tipTitle[i] : o.labels[i]) + '</div>' + o.series.map(function (se) { return row(se.color, se.name, o.fmtFull ? o.fmtFull(se.values[i]) : esc(se.values[i]), se.dash); }).join(''), e);
    };
    el.onpointerleave = function () { xh.style.display = 'none'; dots.innerHTML = ''; C.hideTip(); };
  };

  /* ------------------------------------------------------------ donut */
  /* items: [{key,label,value,color,sub}]; o: {center:[top,bottom], active, onClick, fmt} */
  C.donut = function (el, items, o) {
    o = o || {};
    var tot = items.reduce(function (s, i) { return s + Math.max(i.value, 0); }, 0), S = 150, R = 58, T = 24, cx = S / 2, cy = S / 2, a0 = -Math.PI / 2;
    var gap = items.filter(function (i) { return i.value > 0; }).length > 1 ? 0.035 : 0, svg = '<svg viewBox="0 0 ' + S + ' ' + S + '" width="' + S + '" height="' + S + '" role="img" aria-label="' + esc(o.aria || 'Donut chart') + '">';
    if (!tot) svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="none" stroke="#E2E8F0" stroke-width="' + T + '"/>';
    items.forEach(function (it, i) {
      if (it.value <= 0 || !tot) return;
      var a1 = a0 + 2 * Math.PI * it.value / tot, s0 = a0 + gap / 2, s1 = a1 - gap / 2, big = (s1 - s0) > Math.PI ? 1 : 0;
      var p = (items.filter(function (x) { return x.value > 0; }).length === 1)
        ? '<circle data-i="' + i + '" pathLength="1" style="--i:' + i + '" class="seg" cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="none" stroke="' + it.color + '" stroke-width="' + T + '"/>'
        : '<path data-i="' + i + '" pathLength="1" style="--i:' + i + '" class="seg' + (o.active && o.active === it.key ? ' on' : '') + '" fill="none" stroke="' + it.color + '" stroke-width="' + T + '" d="M' + (cx + R * Math.cos(s0)).toFixed(2) + ' ' + (cy + R * Math.sin(s0)).toFixed(2) + ' A' + R + ' ' + R + ' 0 ' + big + ' 1 ' + (cx + R * Math.cos(s1)).toFixed(2) + ' ' + (cy + R * Math.sin(s1)).toFixed(2) + '"/>';
      svg += p; a0 = a1;
    });
    if (o.center) svg += '<text class="dc1" x="' + cx + '" y="' + (cy - 1) + '" text-anchor="middle">' + esc(o.center[0]) + '</text><text class="dc2" x="' + cx + '" y="' + (cy + 14) + '" text-anchor="middle">' + esc(o.center[1]) + '</text>';
    svg += '</svg>';
    var leg = '<ul class="legend">' + items.map(function (it, i) {
      return '<li data-i="' + i + '" class="' + (o.active && o.active === it.key ? 'on' : '') + '"><span class="sw" style="background:' + it.color + '"></span><span class="ln">' + esc(it.label) + '</span><span class="lv">' + (tot ? (100 * Math.max(it.value, 0) / tot).toFixed(1) + '%' : '-') + '</span></li>';
    }).join('') + '</ul>';
    el.innerHTML = '<div class="donut">' + svg + leg + '</div>';
    function over(e) {
      var t = e.target.closest('[data-i]'); if (!t) { C.hideTip(); return; }
      var it = items[+t.getAttribute('data-i')];
      C.showTip('<div class="th">' + esc(it.label) + '</div>' + row(it.color, 'Value', (o.fmt || F.inr)(it.value)) + row(it.color, 'Share', (tot ? (100 * it.value / tot).toFixed(1) : '0') + '%') + (it.sub ? '<div class="ts">' + esc(it.sub) + '</div>' : ''), e);
    }
    el.onpointermove = over; el.onpointerleave = C.hideTip;
    el.onclick = function (e) { var t = e.target.closest('[data-i]'); if (t && o.onClick) o.onClick(items[+t.getAttribute('data-i')]); };
  };

  /* ------------------------------------------------------------ horizontal bars (HTML) */
  /* items: [{key,label,value,color,text,sub,tip}]; o: {active,onClick,diverging,max} */
  C.hbars = function (el, items, o) {
    o = o || {};
    var mx = o.max || Math.max.apply(null, items.map(function (i) { return Math.abs(i.value); }).concat([1e-9]));
    var h = items.map(function (it, i) {
      var w = Math.min(100, 100 * Math.abs(it.value) / mx), on = o.active && o.active === it.key;
      var bar;
      if (o.diverging) {
        var neg = it.value < 0;
        bar = '<div class="trk dv"><div class="half l">' + (neg ? '<div class="bar" style="width:' + w + '%;background:' + it.color + '"></div>' : '') + '</div><div class="half r">' + (!neg ? '<div class="bar" style="width:' + w + '%;background:' + it.color + '"></div>' : '') + '</div></div>';
      } else {
        bar = '<div class="trk"><div class="bar" style="width:' + w + '%;background:' + it.color + '"></div></div>';
      }
      return '<div class="hb' + (on ? ' on' : '') + '" style="--i:' + i + '" data-i="' + i + '" tabindex="0"><span class="hl" title="' + esc(it.label) + '">' + esc(it.label) + '</span>' + bar + '<span class="hv">' + esc(it.text) + '</span></div>';
    }).join('');
    el.innerHTML = '<div class="hbars">' + (h || '<div class="empty">Nothing matches the slicers.</div>') + '</div>';
    el.onpointermove = function (e) {
      var t = e.target.closest('[data-i]'); if (!t) { C.hideTip(); return; }
      var it = items[+t.getAttribute('data-i')]; C.showTip(it.tip || '<div class="th">' + esc(it.label) + '</div><div class="tv">' + esc(it.text) + '</div>', e);
    };
    el.onpointerleave = C.hideTip;
    el.onclick = function (e) { var t = e.target.closest('[data-i]'); if (t && o.onClick) o.onClick(items[+t.getAttribute('data-i')]); };
    el.onkeydown = function (e) { if (e.key === 'Enter') { var t = e.target.closest('[data-i]'); if (t && o.onClick) o.onClick(items[+t.getAttribute('data-i')]); } };
  };

  /* ------------------------------------------------------------ vertical bars */
  /* items: [{label,value,color,tip}] */
  C.vbars = function (el, items, o) {
    o = o || {};
    var W = el.clientWidth || 400, H = o.height || 200, m = { l: 56, r: 8, t: 10, b: 26 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
    var mx = niceMax(Math.max.apply(null, items.map(function (i) { return i.value; }).concat([0])));
    function Y(v) { return m.t + ph * (1 - v / mx); }
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria || 'Bar chart') + '">';
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) { var v = mx * f; s += '<line class="grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/><text class="ax" x="' + (m.l - 8) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + esc(o.fmt ? o.fmt(v) : v) + '</text>'; });
    var bw = items.length ? pw / items.length : pw, every = Math.ceil(items.length / Math.max(2, Math.floor(pw / 44)));
    items.forEach(function (it, i) {
      var x = m.l + i * bw + Math.min(6, bw * 0.18), w = Math.max(2, bw - 2 * Math.min(6, bw * 0.18)), y = Y(it.value), h = Math.max(0, m.t + ph - y);
      var r = Math.min(4, w / 2, h);
      s += '<path data-i="' + i + '" class="bar" fill="' + it.color + '" d="M' + x + ' ' + (m.t + ph) + ' V' + (y + r) + ' Q' + x + ' ' + y + ' ' + (x + r) + ' ' + y + ' H' + (x + w - r) + ' Q' + (x + w) + ' ' + y + ' ' + (x + w) + ' ' + (y + r) + ' V' + (m.t + ph) + ' Z"/>';
      s += '<rect data-i="' + i + '" x="' + (m.l + i * bw) + '" y="' + m.t + '" width="' + bw + '" height="' + ph + '" fill="transparent"/>';
      if (i % every === 0) s += '<text class="ax" x="' + (x + w / 2) + '" y="' + (H - 7) + '" text-anchor="middle">' + esc(it.label) + '</text>';
    });
    s += '<line class="base" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (m.t + ph) + '" y2="' + (m.t + ph) + '"/></svg>';
    el.innerHTML = items.length ? s : '<div class="empty">Nothing matches the slicers.</div>';
    el.onpointermove = function (e) { var t = e.target.closest('[data-i]'); if (!t) { C.hideTip(); return; } var it = items[+t.getAttribute('data-i')]; C.showTip(it.tip, e); };
    el.onpointerleave = C.hideTip;
  };

  /* ------------------------------------------------------------ motion helpers */
  C.motionOK = function () { return !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); };
  /* Counts a number up from 0. The final text is always exactly fmt(value). */
  C.countUp = function (el, value, fmt, ms) {
    if (!C.motionOK()) { el.textContent = fmt(value); return; }
    var t0 = null, d = ms || 1000;
    function step(t) {
      if (t0 == null) t0 = t;
      var k = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(k >= 1 ? value : value * e);
      if (k < 1) requestAnimationFrame(step);
    }
    el.textContent = fmt(0); requestAnimationFrame(step);
  };

  /* ------------------------------------------------------------ sparkline */
  /* values: [numbers]; labels: [text]; o: {color, fmt} */
  C.spark = function (el, values, labels, o) {
    o = o || {};
    var W = el.clientWidth || 150, H = o.height || 38, n = values.length, p = o.pad || 3;
    if (n < 2) { el.innerHTML = ''; return; }
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values), sp = hi - lo || Math.abs(hi) || 1;
    function X(i) { return p + (W - 2 * p) * i / (n - 1); }
    function Y(v) { return p + (H - 2 * p - 2) * (1 - (v - lo) / sp); }
    var pts = values.map(function (v, i) { return X(i).toFixed(1) + ',' + Y(v).toFixed(1); }).join(' ');
    var gid = 'sg' + Math.random().toString(36).slice(2, 8);
    el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria || 'Trend') + '">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + o.color + '" stop-opacity="' + (o.fillop || .22) + '"/><stop offset="1" stop-color="' + o.color + '" stop-opacity="0"/></linearGradient></defs>' +
      '<polygon class="sa" fill="url(#' + gid + ')" points="' + X(0).toFixed(1) + ',' + H + ' ' + pts + ' ' + X(n - 1).toFixed(1) + ',' + H + '"/>' +
      '<polyline class="ln" pathLength="1" fill="none" stroke="' + o.color + '" stroke-width="' + (o.sw || 1.8) + '" stroke-linejoin="round" stroke-linecap="round" points="' + pts + '"/>' +
      (o.pulse ? '<circle class="pulse" cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(values[n - 1]).toFixed(1) + '" r="6" fill="' + o.color + '"/>' : '') + '<circle class="end" cx="' + X(n - 1).toFixed(1) + '" cy="' + Y(values[n - 1]).toFixed(1) + '" r="' + (o.pulse ? 4.5 : 3) + '" fill="' + o.color + '"/><circle id="sd" r="3.6" fill="' + o.color + '" stroke-width="1.5" style="display:none;stroke:var(--dot)"/></svg>';
    var svg = el.firstChild, dot = svg.querySelector('#sd');
    function idx(e) { var r = svg.getBoundingClientRect(), i = Math.round(((e.clientX - r.left) * W / r.width - p) / ((W - 2 * p) / (n - 1))); return Math.max(0, Math.min(n - 1, i)); }
    el.onclick = o.onClick ? function (e) { o.onClick(idx(e)); } : null; el.style.cursor = o.onClick ? 'pointer' : '';
    el.onpointermove = function (e) {
      var i = idx(e); dot.setAttribute('cx', X(i)); dot.setAttribute('cy', Y(values[i])); dot.style.display = '';
      C.showTip('<div class="th">' + esc(labels[i]) + '</div><div class="tv" style="margin:0">' + esc((o.fmt || F.inr)(values[i])) + '</div>', e);
    };
    el.onpointerleave = function () { dot.style.display = 'none'; C.hideTip(); };
    return { at: function (i) { return [X(i), Y(values[i])]; } };
  };

  /* ------------------------------------------------------------ waterfall */
  /* steps: [{key,label,value,total,tip}] ; a step with total:true is drawn from zero to its value; others float on the running total. */
  C.waterfall = function (el, steps, o) {
    o = o || {};
    if (!steps.some(function (x) { return Math.abs(x.value) > 0.5; })) { el.innerHTML = '<div class="empty">No gain or loss to show for this view.</div>'; el.onpointermove = el.onpointerleave = el.onclick = null; return; }
    var W = el.clientWidth || 560, H = o.height || 250, m = { l: 62, r: 10, t: 24, b: 40 }, pw = W - m.l - m.r, ph = H - m.t - m.b, run = 0, bars = [];
    steps.forEach(function (st) {
      var a, b;
      if (st.total) { a = 0; b = st.value; run = st.value; } else { a = run; b = run + st.value; run = b; }
      bars.push({ st: st, lo: Math.min(a, b), hi: Math.max(a, b), a: a, b: b });
    });
    var lo = Math.min.apply(null, bars.map(function (x) { return x.lo; }).concat([0])), hi = Math.max.apply(null, bars.map(function (x) { return x.hi; }).concat([0]));
    var rg = niceRange(lo, hi, 4);
    function Y(v) { return m.t + ph * (1 - (v - rg.min) / (rg.max - rg.min)); }
    var bw = pw / bars.length, w = Math.min(64, bw * 0.56);
    var s = '<svg class="wf" viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria || 'Waterfall chart') + '">';
    rg.ticks.forEach(function (t) { s += '<line class="grid" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text class="ax" x="' + (m.l - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + esc(o.fmt ? o.fmt(t) : t) + '</text>'; });
    s += '<line class="base" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
    bars.forEach(function (x, i) {
      var cx = m.l + bw * i + bw / 2, y = Y(x.hi), h = Math.max(2, Y(x.lo) - Y(x.hi)), neg = !x.st.total && x.st.value < 0;
      var col = x.st.total ? (o.totalColor || (document.documentElement.getAttribute('data-theme') === 'dark' ? '#6F95E8' : '#122750')) : (neg ? '#BA2936' : '#008B59');
      if (i > 0) s += '<line class="conn" x1="' + (m.l + bw * (i - 1) + bw / 2 + w / 2) + '" x2="' + (cx - w / 2) + '" y1="' + Y(bars[i - 1].b) + '" y2="' + Y(bars[i - 1].b) + '"/>';
      s += '<rect data-i="' + i + '" class="wb' + (o.active && o.active === x.st.key ? ' on' : '') + '" style="--i:' + i + '" x="' + (cx - w / 2) + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="3" fill="' + col + '"/>';
      s += '<text class="wv" x="' + cx + '" y="' + (y - 6) + '" text-anchor="middle" fill="' + col + '">' + esc((x.st.value < 0 ? '−' : (x.st.total ? '' : '+')) + F.cr(Math.abs(x.st.value))) + '</text>';
      s += '<text class="ax" x="' + cx + '" y="' + (H - 16) + '" text-anchor="middle">' + esc(x.st.label) + '</text>';
    });
    s += '</svg>';
    el.innerHTML = s;
    el.onpointermove = function (e) { var t = e.target.closest('[data-i]'); if (!t) { C.hideTip(); return; } C.showTip(steps[+t.getAttribute('data-i')].tip || '', e); };
    el.onpointerleave = C.hideTip;
    el.onclick = function (e) { var t = e.target.closest('[data-i]'); if (t && o.onClick) o.onClick(steps[+t.getAttribute('data-i')]); };
  };

  /* ------------------------------------------------------------ treemap */
  function worst(row, side) {
    var s = row.reduce(function (a, n) { return a + n.a; }, 0), mx = Math.max.apply(null, row.map(function (n) { return n.a; })), mn = Math.min.apply(null, row.map(function (n) { return n.a; }));
    return Math.max(side * side * mx / (s * s), s * s / (side * side * mn));
  }
  function squarify(items, x, y, w, h) {
    var total = items.reduce(function (s, i) { return s + i.v; }, 0), res = [];
    if (total <= 0 || w <= 0 || h <= 0) return res;
    var k = w * h / total, nodes = items.map(function (i) { return { it: i, a: i.v * k }; }), row = [], rx = x, ry = y, rw = w, rh = h;
    function flush() {
      var s = row.reduce(function (a, n) { return a + n.a; }, 0);
      if (rw >= rh) { var cw = s / rh, cy = ry; row.forEach(function (n) { var ch = n.a / cw; res.push({ it: n.it, x: rx, y: cy, w: cw, h: ch }); cy += ch; }); rx += cw; rw -= cw; }
      else { var rhh = s / rw, cx = rx; row.forEach(function (n) { var c2 = n.a / rhh; res.push({ it: n.it, x: cx, y: ry, w: c2, h: rhh }); cx += c2; }); ry += rhh; rh -= rhh; }
      row = [];
    }
    nodes.forEach(function (n) { var side = Math.min(rw, rh); if (!row.length || worst(row.concat([n]), side) <= worst(row, side)) row.push(n); else { flush(); row.push(n); } });
    if (row.length) flush();
    return res;
  }
  function mix(a, b, t) { return a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); }); }
  var NEU = [232, 237, 243], GRN = [120, 205, 160], RED = [240, 150, 150];
  /* ------------------------------------------------------------ heatmap */
  /* rows: [{key,label,cells:[{v (fraction or null), tip}]}]; cols: [label]; o: {onRow, active, scale} */
  C.heat = function (el, cols, rows, o) {
    o = o || {}; var sc = o.scale || 0.08;
    function bg(v) { if (v == null) return 'transparent'; var t = Math.min(1, Math.abs(v) / sc); return 'rgb(' + mix(NEU, v >= 0 ? GRN : RED, t).join(',') + ')'; }
    var h = '<div class="heatwrap"><table class="heat"><thead><tr><th></th>' + cols.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      rows.map(function (r, ri) {
        return '<tr' + (o.active && o.active === r.key ? ' class="on"' : '') + '><th class="rl" data-r="' + ri + '" tabindex="0" title="' + esc(r.label) + '">' + esc(r.label) + '</th>' +
          r.cells.map(function (c, ci) {
            var strong = c.v != null && Math.abs(c.v) / sc > 0.62;
            return '<td data-r="' + ri + '" data-c="' + ci + '" style="background:' + bg(c.v) + (strong ? ';color:#fff' : '') + ';--i:' + (ri + ci) + '">' + (c.v == null ? '' : (c.v >= 0 ? '+' : '') + (c.v * 100).toFixed(1)) + '</td>';
          }).join('') + '</tr>';
      }).join('') + '</tbody></table></div>';
    el.innerHTML = rows.length ? h : '<div class="empty">Nothing matches the slicers.</div>';
    el.onpointermove = function (e) { var t = e.target.closest('td[data-c]'); if (!t) { C.hideTip(); return; } C.showTip(rows[+t.getAttribute('data-r')].cells[+t.getAttribute('data-c')].tip, e); };
    el.onpointerleave = C.hideTip;
    el.onclick = function (e) { var t = e.target.closest('[data-r]'); if (t && o.onRow) o.onRow(rows[+t.getAttribute('data-r')]); };
    el.onkeydown = function (e) { if (e.key === 'Enter') { var t = e.target.closest('th[data-r]'); if (t && o.onRow) o.onRow(rows[+t.getAttribute('data-r')]); } };
  };

  C.gainColor = function (p) {
    if (p == null) return 'rgb(' + NEU.join(',') + ')';
    var t = Math.min(1, Math.abs(p) / 0.30);
    return 'rgb(' + mix(NEU, p >= 0 ? GRN : RED, t).join(',') + ')';
  };
  /* groups: [{name, key, children:[{key,name,value,cost,pct}]}]; o: {height,onTile,onGroup,activeKey} */
  C.treemap = function (el, groups, o) {
    o = o || {};
    var W = el.clientWidth || 600, H = o.height || 300, FS = 11;
    var top = groups.map(function (g) { return { g: g, v: g.children.reduce(function (s, c) { return s + Math.max(c.value, 0); }, 0) }; }).filter(function (x) { return x.v > 0; }).sort(function (a, b) { return b.v - a.v; });
    var tiles = [], s = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria || 'Treemap of holdings') + '">';
    squarify(top, 0, 0, W, H).forEach(function (gr, gi) {
      var g = gr.it.g, hdr = gr.h > 34 && gr.w > 56 ? 16 : 0;
      s += '<rect class="grp" data-g="' + gi + '" x="' + gr.x + '" y="' + gr.y + '" width="' + gr.w + '" height="' + gr.h + '" rx="6"/>';
      if (hdr) s += '<text class="gt" x="' + (gr.x + 7) + '" y="' + (gr.y + 12) + '" data-g="' + gi + '">' + esc(trunc(g.name, gr.w - 14, FS)) + '</text>';
      var kids = g.children.filter(function (c) { return c.value > 0; }).map(function (c) { return { c: c, v: c.value }; }).sort(function (a, b) { return b.v - a.v; });
      squarify(kids, gr.x + 3, gr.y + hdr + 2, gr.w - 6, gr.h - hdr - 5).forEach(function (t) {
        var c = t.it.c, i = tiles.length; tiles.push({ c: c, g: g });
        s += '<rect class="tile' + (o.activeKey && o.activeKey === c.key ? ' on' : '') + '" data-i="' + i + '" x="' + (t.x + 1) + '" y="' + (t.y + 1) + '" width="' + Math.max(0, t.w - 2) + '" height="' + Math.max(0, t.h - 2) + '" rx="4" fill="' + C.gainColor(c.pct) + '"/>';
        if (t.w > 54 && t.h > 30) {
          s += '<text class="tn1" x="' + (t.x + 7) + '" y="' + (t.y + 16) + '">' + esc(trunc(c.name, t.w - 12, FS)) + '</text>';
          if (t.h > 44) s += '<text class="tn2" x="' + (t.x + 7) + '" y="' + (t.y + 30) + '">' + esc(F.cr(c.value)) + (c.pct == null ? '' : ' ' + F.pct(c.pct, 1)) + '</text>';
        }
      });
    });
    s += '</svg>';
    el.innerHTML = top.length ? s + '<div class="tmleg"><span>Loss on cost</span><i></i><span>Gain on cost</span><span class="mut">Size = value on the date. Colour = gain or loss, full colour at 30%.</span></div>' : '<div class="empty">Nothing matches the slicers.</div>';
    el.onpointermove = function (e) {
      var t = e.target.closest('[data-i]'); if (!t) { C.hideTip(); return; }
      var d = tiles[+t.getAttribute('data-i')], c = d.c;
      C.showTip('<div class="th">' + esc(c.name) + '</div><div class="ts">' + esc(d.g.name) + '</div>' + row('#2C52AE', 'Value', F.inr(c.value)) + row('#64748B', 'Cost', F.inr(c.cost)) + row(c.value >= c.cost ? '#047857' : '#B91C1C', 'Gain or loss', F.num(c.value - c.cost, 0) + (c.pct == null ? '' : ' (' + F.pct(c.pct) + ')')), e);
    };
    el.onpointerleave = C.hideTip;
    el.onclick = function (e) {
      var t = e.target.closest('[data-i]'); if (t && o.onTile) { o.onTile(tiles[+t.getAttribute('data-i')].c, tiles[+t.getAttribute('data-i')].g); return; }
      var g = e.target.closest('[data-g]'); if (g && o.onGroup) { var gg = top.length ? squarify(top, 0, 0, W, H)[+g.getAttribute('data-g')].it.g : null; if (gg) o.onGroup(gg); }
    };
  };
  function trunc(s, w, fs) { var n = Math.max(0, Math.floor(w / (fs * 0.56))); return s.length <= n ? s : (n <= 1 ? '' : s.slice(0, n - 1) + '…'); }

  /* ------------------------------------------------------------ sortable table */
  /* cols: [{k,label,align,fmt(row)->html,sort(row)->value}]; o:{sort:{k,dir},onSort,onRow,activeKey(row)->bool,foot:row} */
  C.table = function (el, cols, rows, o) {
    o = o || {};
    var st = o.sort || {}, col = cols.filter(function (c) { return c.k === st.k; })[0];
    var data = rows.slice();
    if (col) data.sort(function (a, b) { var x = col.sort ? col.sort(a) : a[col.k], y = col.sort ? col.sort(b) : b[col.k]; if (x == null) return 1; if (y == null) return -1; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * (st.dir === 'desc' ? -1 : 1); });
    var h = '<div class="tw' + (o.flat ? ' flat' : '') + '"><table><thead><tr>' + cols.map(function (c) {
      return '<th class="' + (c.align || '') + (c.k === st.k ? ' sorted' : '') + '" data-k="' + esc(c.k) + '" tabindex="0">' + esc(c.label) + (c.k === st.k ? (st.dir === 'desc' ? ' ▾' : ' ▴') : '') + '</th>';
    }).join('') + '</tr></thead><tbody>' + data.map(function (r, i) {
      return '<tr data-i="' + i + '" class="' + (o.activeKey && o.activeKey(r) ? 'on' : '') + (o.onRow ? ' click' : '') + '">' + cols.map(function (c) { return '<td class="' + (c.align || '') + '">' + (c.fmt ? c.fmt(r) : esc(r[c.k])) + '</td>'; }).join('') + '</tr>';
    }).join('') + (o.foot ? '<tr class="foot">' + cols.map(function (c) { return '<td class="' + (c.align || '') + '">' + (o.foot[c.k] == null ? '' : o.foot[c.k]) + '</td>'; }).join('') + '</tr>' : '') + '</tbody></table>' + (data.length ? '' : '<div class="empty">Nothing matches the slicers.</div>') + '</div>';
    el.innerHTML = h;
    el.onclick = function (e) {
      var th = e.target.closest('th[data-k]');
      if (th && o.onSort) { var k = th.getAttribute('data-k'); o.onSort(k, st.k === k && st.dir !== 'desc' ? 'desc' : (st.k === k ? 'asc' : 'desc')); return; }
      var tr = e.target.closest('tbody tr[data-i]'); if (tr && o.onRow) o.onRow(data[+tr.getAttribute('data-i')]);
    };
    el.onkeydown = function (e) { if (e.key === 'Enter') { var th = e.target.closest('th[data-k]'); if (th) th.click(); } };
  };

  root.Charts = C;
})(typeof window !== 'undefined' ? window : this);
