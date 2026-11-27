/* Dashboard screens. All numbers come from Engine (engine.js). Charts come from Charts (charts.js). */
(function () {
  'use strict';
  var data = JSON.parse(document.getElementById('data').textContent);
  var E = new Engine(data), L = new Life(data), C = Charts, F = C.F, esc = F.esc;
  var COL = { 'Mutual funds': '#2C52AE', 'Equity shares': '#0E9F6E', 'Bank balances': '#8A6FB3', 'Term deposits': '#D69E1E' };
  var MARK = { 'Mutual funds': 'MF', 'Equity shares': 'EQ', 'Bank balances': 'BK', 'Term deposits': 'FD' };
  var TABS = ['Overview', 'Mutual Funds', 'Equity shares', 'Bank and Deposits', 'Property and Rent', 'Insurance', 'Cash Calendar', 'Data checks', 'NRI DTAA'];
  var NOSLICE = { 4: 1, 5: 1, 6: 1, 8: 1 }, TAB_CHECKS = 7, TAB_DTAA = 8;
  var TITLES = ['Portfolio overview', 'Mutual funds', 'Equity shares', 'Bank balances and deposits', 'House property and rent', 'Insurance policies', 'Cash commitments calendar', 'Data checks', 'DTAA claim on mutual fund redemption'];
  var SUBS = ['A consolidated view of funds, shares, bank balances and deposits.', 'Units, average cost and value of every fund.', 'Every share with its cost, price and sector.', 'Savings, foreign currency, broker cash and term deposits.', 'The house, its rent, the lease and the yearly house tax and maintenance.', 'Cover, premiums and retirement income. Insurance cover is not an asset.', 'SIPs, premiums, house tax and maintenance due in the next 12 months.', 'How the numbers are worked out, and the checks that ran.', 'How a non-resident Indian registers a treaty claim with a fund house before redeeming.'];
  var ICONS = [
    '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    '<path d="M3 10l9-6 9 6"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8"/><path d="M3 21h18"/>',
    '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    '<path d="M3 12a9 9 0 0 1 18 0z"/><path d="M12 12v6.5a2 2 0 0 1-4 0"/>',
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>'];
  var S = { fh: false, tab: 0, on: data.meta.latest, F: {}, sort: {}, range: 'ALL', q: '', anim: true, replay: null };
  var replayTimer = null;
  var $ = function (id) { return document.getElementById(id); };
  var GREEN = '#008B59', RED = '#BA2936';

  /* ---------------------------------------------------------- helpers */
  function without(f) { var o = Object.assign({}, S.F); delete o[f]; return o; }
  function toggle(field, value) { stopReplay(); if (field === 'account') delete S.F.bank; if (field === 'bank') delete S.F.account; if (S.F[field] === value) delete S.F[field]; else S.F[field] = value; render(); }
  function pct(l) { return l.cost > 0 ? (l.value - l.cost) / l.cost : null; }
  function group(ls, keyFn) {                                  // merge lines of the same holding held in several accounts
    var m = {}, order = [];
    ls.forEach(function (l) {
      var k = keyFn(l);
      if (!m[k]) { m[k] = { key: l.key, name: short(l.name), cls: l.cls, sector: l.sector, category: l.category, fh: l.fh, value: 0, cost: 0, qty: 0 }; order.push(k); }
      m[k].value += l.value; m[k].cost += l.cost; m[k].qty += l.qty || 0;
    });
    return order.map(function (k) { var o = m[k]; o.pct = o.cost > 0 ? (o.value - o.cost) / o.cost : null; return o; });
  }
  function kpi(label, value, sub, hero) { return '<div class="card kpi' + (hero ? ' hero' : '') + '"><div class="l">' + esc(label) + '</div><div class="n">' + value + '</div><div class="d">' + (sub || '') + '</div></div>'; }
  function card(title, id, note, cls) { return '<div class="card ' + (cls || '') + '"><h3>' + esc(title) + '</h3><div id="' + id + '"></div>' + (note ? '<div class="note">' + note + '</div>' : '') + '</div>'; }
  function gainKpi(s) { var c = s.gain > 0.5 ? 'up' : (s.gain < -0.5 ? 'down' : 'flat'); return '<span class="' + c + '">' + (s.gain > 0.5 ? '\u25B2 ' : (s.gain < -0.5 ? '\u25BC ' : '')) + F.num(s.gain, 0) + '</span>'; }
  function gainSub(s) { return s.pct == null ? '' : '<span class="' + (s.gain >= 0 ? 'up' : 'down') + '">' + F.pct(s.pct) + '</span> on cost'; }
  function short(n) { return n.replace(' - Direct Growth', ''); }
  function sortOpt(id, def) { return { sort: S.sort[id] || def, onSort: function (k, d) { S.sort[id] = { k: k, dir: d }; render(); } }; }

  /* ---------------------------------------------------------- slicers */
  var latestLines = E.lines(data.meta.latest);
  var ACCOUNTS = (function () {
    var s = {}; Object.keys(E.series).forEach(function (id) { s[E.series[id].account] = 1; }); latestLines.forEach(function (l) { s[l.account] = 1; });
    var a = Object.keys(s).sort();
    return { demat: a.filter(function (x) { return x.indexOf('Demat') === 0; }), folio: a.filter(function (x) { return x.indexOf('Folio') === 0; }),
      bank: a.filter(function (x) { return x.indexOf('Demat') !== 0 && x.indexOf('Folio') !== 0; }) };
  })();
  var BANKS = (function () {
    var m = {}; latestLines.forEach(function (l) { if (l.bank) { (m[l.bank] = m[l.bank] || {})[l.account] = 1; } });
    return Object.keys(m).sort().map(function (b) { return { name: b, accounts: Object.keys(m[b]).sort() }; });
  })();
  var HOUSES = uniq(data.instruments.filter(function (i) { return i.kind === 'MF'; }).map(function (i) { return i.house; }));
  var SECTORS = uniq(data.instruments.filter(function (i) { return i.kind === 'SHARE'; }).map(function (i) { return i.group; }));
  var CATS = uniq(data.instruments.filter(function (i) { return i.kind === 'MF'; }).map(function (i) { return i.group; }));
  var CCYS = uniq(latestLines.map(function (l) { return l.ccy; }));
  var DATES = uniq(data.prices.map(function (r) { return r.date; })).sort().reverse();
  function uniq(a) { var s = {}; a.forEach(function (x) { if (x) s[x] = 1; }); return Object.keys(s).sort(); }
  var MONTH_ENDS = (function () { var by = {}; DATES.slice().reverse().forEach(function (d) { by[d.slice(0, 7)] = d; }); return Object.keys(by).sort().reverse().map(function (m) { return by[m]; }); })();

  function opts(list, cur, allLabel) { return '<option value="">' + esc(allLabel) + '</option>' + list.map(function (x) { return '<option' + (x === cur ? ' selected' : '') + ' value="' + esc(x) + '">' + esc(x) + '</option>'; }).join(''); }
  function select(id, label, inner, cls) { return '<div class="sl ' + (cls || '') + '"><label for="' + id + '">' + esc(label) + '</label><select id="' + id + '">' + inner + '</select></div>'; }
  function buildSlicers() {
    var on = '', seen = {};
    MONTH_ENDS.forEach(function (d) { seen[d] = 1; });
    var dl = [data.meta.latest].concat(MONTH_ENDS.filter(function (d) { return d !== data.meta.latest; }));
    dl.forEach(function (d, i) { on += '<option value="' + d + '">' + (i === 0 ? 'Latest, ' : '') + F.dmy(d) + '</option>'; });
    var acc = '<option value="">All accounts</option>';
    BANKS.forEach(function (b) {
      acc += '<optgroup label="' + esc(b.name) + '"><option value="bank:' + esc(b.name) + '">All ' + esc(b.name) + ' accounts</option>' + b.accounts.map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join('') + '</optgroup>';
    });
    [['Demat accounts', ACCOUNTS.demat], ['Fund folios', ACCOUNTS.folio]].forEach(function (g) {
      acc += '<optgroup label="' + g[0] + '">' + g[1].map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join('') + '</optgroup>';
    });
    var h = select('sl-on', 'As on', on, 'asof') + select('sl-account', 'Account', acc) + select('sl-fh', 'Fund house', opts(HOUSES, '', 'All fund houses')) +
      select('sl-sector', 'Sector', opts(SECTORS, '', 'All sectors'));
    if (S.tab === 1) h += select('sl-category', 'Fund category', opts(CATS, '', 'All categories'));
    if (S.tab === 3) h += select('sl-ccy', 'Currency', opts(CCYS, '', 'All currencies'));
    h += '<div class="hint" style="margin-left:auto;align-self:center">Click any bar, slice, tile or row to filter every page. Click again to clear.</div>';
    $('slicers').innerHTML = h;
    var map = { 'sl-on': 'on', 'sl-account': 'account', 'sl-fh': 'fh', 'sl-sector': 'sector', 'sl-category': 'category', 'sl-ccy': 'ccy' };
    Object.keys(map).forEach(function (id) {
      var el = $(id); if (!el) return;
      el.onchange = function () {
        stopReplay(id === 'sl-on');
        if (id === 'sl-on') S.on = el.value;
        else if (id === 'sl-account') { delete S.F.account; delete S.F.bank; if (el.value.indexOf('bank:') === 0) S.F.bank = el.value.slice(5); else if (el.value) S.F.account = el.value; }
        else if (el.value) S.F[map[id]] = el.value; else delete S.F[map[id]];
        render();
      };
    });
  }
  function syncSlicers() {
    var m = { 'sl-fh': 'fh', 'sl-sector': 'sector', 'sl-category': 'category', 'sl-ccy': 'ccy' };
    $('sl-on').value = S.on;
    $('sl-account').value = S.F.bank ? 'bank:' + S.F.bank : (S.F.account || '');
    Object.keys(m).forEach(function (id) { var el = $(id); if (el) el.value = S.F[m[id]] || ''; });
  }
  var LABELS = { account: 'Account', bank: 'Bank', fh: 'Fund house', sector: 'Sector', category: 'Category', ccy: 'Currency', cls: 'Asset class', key: 'Holding', atype: 'Account type' };
  function chips() {
    var h = Object.keys(S.F).map(function (f) {
      var v = S.F[f]; if (f === 'key') { var l = E.ins[v] ? E.ins[v].name : (E.lines(S.on).filter(function (x) { return x.key === v; })[0] || { name: v }).name; v = l; }
      return '<button class="chip" data-f="' + f + '" title="Remove this filter">' + esc(LABELS[f] + ': ' + v) + ' <b>×</b></button>';
    }).join('');
    $('chips').innerHTML = h ? h + '<button class="clear" id="clear">Clear all</button>' : '';
    $('chips').onclick = function (e) {
      var c = e.target.closest('.chip'); if (c) { delete S.F[c.getAttribute('data-f')]; render(); return; }
      if (e.target.id === 'clear') { S.F = {}; render(); }
    };
  }

  /* ---------------------------------------------------------- Overview */
  function attentionHtml(ls) {
    var items = E.attention(S.on, S.F), bad = data.checks.filter(function (c) { return !c.ok; });
    bad.forEach(function (c) { items.push({ kind: 'bad', text: 'Data check failed: ' + c.name }); });
    if (!items.length) return '<ul class="att"><li class="good"><span class="ic">✓</span><span>Nothing needs attention for this view.</span></li></ul>';
    var more = items.length > 9 ? items.length - 9 : 0;
    return '<ul class="att">' + items.slice(0, 9).map(function (x, i) { return '<li class="' + x.kind + '" data-k="' + esc(x.key || '') + '"><span class="ic">' + (x.kind === 'warn' ? '!' : '×') + '</span><span>' + esc(x.text) + '</span></li>'; }).join('') + '</ul>' + (more ? '<div class="note">and ' + more + ' more</div>' : '');
  }
  function assetCard(label, c, color, tv, sub) {
    return '<div class="card kpi pick' + (S.F.cls === label ? ' on' : '') + '" role="button" tabindex="0" aria-pressed="' + (S.F.cls === label) + '" data-cls="' + esc(label) + '" title="Click to filter the page to this asset class" style="--accent:' + color + '"><div class="l">' + esc(label) + '</div><div class="n" data-v="' + c.value + '">' + F.inr(c.value) + '</div><div class="d">' + sub + '</div><div class="spark" data-c="' + esc(label) + '"></div>' +
      '<div class="share"><span>' + F.cr(c.value) + '</span><span>' + (tv ? (100 * c.value / tv).toFixed(1) : '0.0') + '% of portfolio</span></div></div>';
  }
  var RANGES = [['3M', 4], ['6M', 7], ['1Y', 13], ['ALL', 0]];
  var CLASS_BTN = [['', 'All assets'], ['Mutual funds', 'Mutual funds'], ['Equity shares', 'Equity shares'], ['Bank balances', 'Bank'], ['Term deposits', 'Fixed deposits']];
  function outside() {
    var pv = L.props.reduce(function (s, p) { return s + (p.value || 0); }, 0), bits = [];
    if (pv) bits.push('house property ' + F.inr(pv)); if (L.hasIns) bits.push('insurance cover');
    return bits.length ? '<div class="outside">Not in this total: ' + bits.join(' and ') + '. Each has its own page.</div>' : '';
  }
  /* ---------------------------------------------------------- replay: plays the portfolio month by month */
  function stopReplay(keepDate) {
    if (replayTimer) { clearTimeout(replayTimer); replayTimer = null; }
    if (S.replay) { var o = S.replay.orig; S.replay = null; if (!keepDate) S.on = o; }
  }
  function startReplay() {
    stopReplay();
    var seq = E.timeline(S.on); if (seq.length < 2) return;
    var orig = S.on, i = 0;
    (function step() {
      S.on = seq[i]; S.replay = { i: i, n: seq.length, orig: orig };
      if (i === seq.length - 1) { S.replay = null; replayTimer = null; render(); return; }
      render(); i++; replayTimer = setTimeout(step, 800);
    })();
  }
  var WFL = { 'Mutual funds': 'Funds', 'Equity shares': 'Equity shares', 'Bank balances': 'Bank balances', 'Term deposits': 'Interest' };
  function glanceHtml(ls, t, bc) {
    var rows = [], best = null;
    ['Mutual funds', 'Equity shares', 'Term deposits'].forEach(function (c) { if (bc[c].cost > 0) { var p = (bc[c].value - bc[c].cost) / bc[c].cost; if (!best || p > best.p) best = { c: c, p: p }; } });
    if (best) rows.push(['Best return on cost', '<b>' + esc(best.c) + ' <span class="' + (best.p >= 0 ? 'up' : 'down') + '">' + F.pct(best.p) + '</span></b>']);
    var gs = group(ls, function (l) { return l.key; }).sort(function (a, b) { return b.value - a.value; });
    if (gs.length && t.value > 0) rows.push(['Largest holding', '<b>' + esc(gs[0].name) + '<br><small>' + (100 * gs[0].value / t.value).toFixed(1) + '% of the total</small></b>']);
    var fs = gs.filter(function (x) { return (x.cls === 'Mutual funds' || x.cls === 'Equity shares') && x.cost > 0; }).sort(function (a, b) { return a.pct - b.pct; });
    if (fs.length) rows.push(['Lowest return on cost', fs[0].pct < 0 ? '<b>' + esc(fs[0].name) + '<br><small class="down">' + F.pct(fs[0].pct) + '</small></b>' : '<b>No fund or share is below cost</b>']);
    var dep = ls.filter(function (l) { return l.cls === 'Term deposits' && !l.matured; }).sort(function (a, b) { return a.daysLeft - b.daysLeft; });
    if (dep.length) rows.push(['Next deposit maturity', '<b>' + esc(dep[0].name) + '<br><small>' + F.dmy(dep[0].maturity) + ', in ' + dep[0].daysLeft + ' days</small></b>']);
    return rows.length ? rows.map(function (r) { return '<div class="fact"><span>' + r[0] + '</span>' + r[1] + '</div>'; }).join('') : '<div class="empty">Nothing matches the slicers.</div>';
  }
  function heroLeft(d) {
    var ls = E.filtered(d, S.F), t = E.sum(ls), x = E.xirrFor(d, S.F), up = t.gain >= 0;
    return '<div class="card kpi nw"><div class="l">Total value</div><div class="n" data-v="' + t.value + '">' + F.inr(t.value) + '</div><div class="d"><span class="gain-badge' + (up ? '' : ' loss') + '">' + (up ? '\u25B2 ' : '\u25BC ') + F.num(Math.abs(t.gain), 0) + (t.pct == null ? '' : ' (' + F.pct(t.pct) + ')') + '</span> <span class="mut">on cost, as on ' + F.dmy(d) + '</span></div>' + outside() + '</div>' +
      '<div class="bandstats">' + kpi('Total cost', F.inr(t.cost), 'Equity shares with brokerage') + kpi('Gain or loss', gainKpi(t), gainSub(t)) +
      kpi('Fund return per year (XIRR)', x == null ? '<span class="mut">Not yet</span>' : F.pct(x), x == null ? 'Needs 6 months from ' + F.dmy(E.openDate()) : 'Mutual funds, since ' + F.dmy(E.openDate())) + '</div>';
  }
  function pOverview(ls) {
    var t = E.sum(ls), bc = E.byClass(ls), ba = E.byClass(E.filtered(S.on, without('cls'))), up = t.gain >= 0;
    function gs(c) { return F.gainHtml(c.value - c.cost, c.cost ? (c.value - c.cost) / c.cost : null); }
    var htl = E.timeline(data.meta.latest), hcur = Math.max(0, htl.indexOf(S.on));
    var h = '<div class="hero2"><div class="hl" id="hero-l">' + heroLeft(S.on) + '</div>' +
      '<div class="hr"><div class="hrh"><span>Total value at each month end</span><b id="hero-last"></b></div><div id="c-hero" class="spark" style="margin-top:6px"></div>' +
      '<div class="hscrub"><label for="hero-sl">Drag to travel in time</label><input type="range" id="hero-sl" min="0" max="' + (htl.length - 1) + '" step="1" value="' + hcur + '"><div class="hax"><span id="hero-a"></span><span id="hero-d"></span><span id="hero-z"></span></div></div></div></div>' +
      '<div class="grid g4 assets">' +
        assetCard('Mutual funds', ba['Mutual funds'], COL['Mutual funds'], t.value, gs(ba['Mutual funds'])) +
        assetCard('Equity shares', ba['Equity shares'], COL['Equity shares'], t.value, gs(ba['Equity shares'])) +
        assetCard('Bank balances', ba['Bank balances'], COL['Bank balances'], t.value, 'Savings, foreign currency, broker cash') +
        assetCard('Term deposits', ba['Term deposits'], COL['Term deposits'], t.value, 'Principal plus interest to the date') + '</div>' +
      '<div class="grid gchart"><div class="card"><div class="panelhead"><div><h3>Value and cost, month by month</h3><div class="note" style="margin:2px 0 0">' + (S.replay ? '<span class="rp">Replaying month by month: ' + F.dmy(S.on) + '</span>' : 'Month ends and the chosen date. Hover for values.') + '</div></div>' +
        '<div class="panelctl"><button type="button" id="replay" class="replay' + (S.replay ? ' on' : '') + '">' + (S.replay ? '\u25A0 Stop' : '\u25B6 Replay') + '</button><div class="range" role="group" aria-label="Period">' + RANGES.map(function (r) { return '<button type="button" data-r="' + r[0] + '" aria-pressed="' + (S.range === r[0]) + '">' + (r[0] === 'ALL' ? 'All' : r[0]) + '</button>'; }).join('') + '</div></div></div><div id="c-line"></div></div>' +
        card('Where it sits', 'c-donut', 'Click a slice to filter.') + '</div>' +
      '<div class="grid gchart">' + card('Where the gain came from', 'c-wf', 'Total gain = value minus cost = ' + F.inr(t.gain) + '. Click a bar to filter.') + card('At a glance', 'c-glance') + '</div>' +
      '<div class="grid gchart">' + card('Where the money is held', 'c-atype', 'By account type. Click a bar to filter.') + card('Currency', 'c-ccy', 'Foreign currency is shown in rupees at the rate of the date. Click a slice to filter.') + '</div>' +
      '<div class="grid gchart">' + card('Month by month: price change', 'c-heat', 'Largest ten funds and shares. Change in price from one month end to the next. Click a name to filter.') + card('Biggest gainers and losers', 'c-mov', 'Return on cost, five best and five worst. Click a bar to filter.') + '</div>' +
      '<div class="grid gins">' + card('Top 10 funds and shares', 'c-top', 'Click a bar to filter.') + card('All holdings as tiles', 'c-tree') + card('Needs attention', 'c-att', 'Click an item to filter to it.') + '</div>' +
      '<div class="sectionhead"><div><h2 style="display:inline">Your holdings</h2><span class="cnt" id="hold-cnt"></span></div><button class="btn-out" id="hold-dl" type="button">Download holdings (CSV)</button></div>' +
      '<div class="toolbar"><div class="filters" id="hold-f" role="group" aria-label="Asset class filter"></div>' +
      '<label class="search"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="q" type="search" placeholder="Search holdings" aria-label="Search holdings" autocomplete="off"></label></div>' +
      '<div class="holdwrap"><div id="c-hold"></div></div>' +
      '<div class="sectionhead"><h2>On the horizon</h2><span class="mut" style="font-size:12.5px">Term deposits not yet matured, by maturity date</span></div><div id="c-hz"></div>';
    $('page').innerHTML = h;
    var hts = E.timeSeries(data.meta.latest, S.F), hsl = $('hero-sl');
    function heroMark(i) {
      var svg = $('c-hero').firstChild, pt = hh.at(i), mk = svg.querySelector('#hmk'), md = svg.querySelector('#hmd');
      mk.setAttribute('x1', pt[0]); mk.setAttribute('x2', pt[0]); md.setAttribute('cx', pt[0]); md.setAttribute('cy', pt[1]);
      $('hero-last').textContent = F.cr(hts[i].value); $('hero-d').textContent = (i === htl.length - 1 ? 'Latest, ' : '') + F.dmy(htl[i]);
    }
    function heroCommit(i) { stopReplay(true); S.on = htl[i]; S.fh = document.activeElement === hsl; render(); }
    var hh = C.spark($('c-hero'), hts.map(function (p) { return p.value; }), hts.map(function (p) { return F.dmy(p.date); }), { color: '#8DE3BC', height: 170, pad: 6, sw: 2.6, fillop: .38, pulse: true, dotStroke: '#0B1B3D', fmt: F.inr, aria: 'Total value at each month end. Click a point to travel to that date.', onClick: function (i) { heroCommit(i); } });
    if (hh) {
      $('c-hero').firstChild.insertAdjacentHTML('beforeend', '<line id="hmk" x1="0" x2="0" y1="0" y2="170" stroke="rgba(255,255,255,.4)" stroke-width="1" stroke-dasharray="3 3"/><circle id="hmd" r="5.5" fill="#fff" stroke="#8DE3BC" stroke-width="2.5"/>');
      $('hero-a').textContent = F.mon(htl[0]); $('hero-z').textContent = 'Latest';
      heroMark(hcur);
      hsl.oninput = function () { var i = +hsl.value; stopReplay(true); heroMark(i); $('hero-l').innerHTML = heroLeft(htl[i]); };
      hsl.onchange = function () { heroCommit(+hsl.value); };
      if (S.fh) { hsl.focus(); S.fh = false; }
    }
    var ts = E.timeSeries(S.on, S.F), nr = RANGES.filter(function (r) { return r[0] === S.range; })[0][1];
    if (nr && ts.length > nr) ts = ts.slice(ts.length - nr);
    C.line($('c-line'), { labels: ts.map(function (p) { return p.date === data.meta.latest ? 'Latest' : F.mon(p.date); }), tipTitle: ts.map(function (p) { return F.dmy(p.date); }),
      series: [{ name: 'Value', color: '#2C52AE', values: ts.map(function (p) { return p.value; }) }, { name: 'Cost', color: '#64748B', dash: true, values: ts.map(function (p) { return p.cost; }) }],
      fmt: F.cr, fmtFull: F.inr, aria: 'Value and cost by month end' });
    document.querySelectorAll('.range button').forEach(function (b) { b.onclick = function () { stopReplay(); S.range = b.getAttribute('data-r'); render(); }; });
    $('replay').onclick = function () { if (S.replay) { stopReplay(); render(); } else startReplay(); };
    var cser = E.timeline(S.on).map(function (d) { return { d: d, bc: E.byClass(E.filtered(d, without('cls'))) }; }).slice(-13);
    document.querySelectorAll('.assets .kpi[data-cls]').forEach(function (el) { var go = function () { toggle('cls', el.getAttribute('data-cls')); }; el.onclick = go; el.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } }; });
    document.querySelectorAll('.assets .spark').forEach(function (el) {
      var c = el.getAttribute('data-c');
      C.spark(el, cser.map(function (x) { return x.bc[c].value; }), cser.map(function (x) { return F.dmy(x.d); }), { color: COL[c], fmt: F.inr, aria: c + ', value at each month end' });
    });
    var wfs = [];
    E.CLASSES.forEach(function (c) {
      var d = bc[c].value - bc[c].cost;
      if (Math.abs(d) > 0.5) wfs.push({ key: c, label: WFL[c], value: d, tip: '<div class="th">' + esc(WFL[c]) + '</div>' + C.tipRow(d >= 0 ? GREEN : RED, 'Gain or loss', F.inr(d)) + C.tipRow('#64748B', 'Cost', F.inr(bc[c].cost)) + C.tipRow(COL[c], 'Value', F.inr(bc[c].value)) + (t.gain > 0 && d > 0 ? C.tipRow('#64748B', 'Share of total gain', (100 * d / t.gain).toFixed(1) + '%') : '') });
    });
    wfs.push({ key: 'total', label: 'Total gain', value: t.gain, total: true, tip: '<div class="th">Total gain</div>' + C.tipRow(t.gain >= 0 ? GREEN : RED, 'Value minus cost', F.inr(t.gain)) + C.tipRow('#64748B', 'Cost', F.inr(t.cost)) + C.tipRow(COL['Mutual funds'], 'Value', F.inr(t.value)) });
    C.waterfall($('c-wf'), wfs, { fmt: F.cr, height: 250, active: S.F.cls, aria: 'Gain or loss by source, adding up to the total gain', onClick: function (st) { if (st.key !== 'total') toggle('cls', st.key); } });
    $('c-glance').innerHTML = glanceHtml(ls, t, bc);
    var la = E.filtered(S.on, without('atype')), at = {}, atot = 0;
    la.forEach(function (l) { at[l.atype] = (at[l.atype] || 0) + l.value; atot += l.value; });
    C.hbars($('c-atype'), Object.keys(at).sort(function (a, b) { return at[b] - at[a]; }).map(function (k) {
      return { key: k, label: k, value: at[k], color: '#3E5C9A', text: F.cr(at[k]), tip: '<div class="th">' + esc(k) + '</div>' + C.tipRow('#3E5C9A', 'Value', F.inr(at[k])) + C.tipRow('#64748B', 'Share', (atot ? (100 * at[k] / atot).toFixed(1) : '0') + '%') };
    }), { active: S.F.atype, onClick: function (it) { toggle('atype', it.key); } });
    var lc2 = E.filtered(S.on, without('ccy')), cv = {}, cl = {};
    lc2.forEach(function (l) { cv[l.ccy] = (cv[l.ccy] || 0) + l.value; cl[l.ccy] = (cl[l.ccy] || 0) + (l.local != null ? l.local : l.value); });
    var CCOL = { INR: document.documentElement.getAttribute('data-theme') === 'dark' ? '#6F95E8' : '#122750', USD: '#D1603D' };
    C.donut($('c-ccy'), Object.keys(cv).sort(function (a, b) { return cv[b] - cv[a]; }).map(function (k) {
      return { key: k, label: k === 'INR' ? 'Indian rupee' : k, value: cv[k], color: CCOL[k] || '#64748B', sub: k === 'INR' ? '' : k + ' ' + F.num(cl[k], 2) + ' held' };
    }), { center: [Object.keys(cv).length + (Object.keys(cv).length === 1 ? ' currency' : ' currencies'), 'held'], active: S.F.ccy, onClick: function (it) { toggle('ccy', it.key === 'Indian rupee' ? 'INR' : it.key); }, fmt: F.inr, aria: 'Value by currency' });
    if (S.anim && C.motionOK()) document.querySelectorAll('#page [data-v]').forEach(function (el) { C.countUp(el, +el.getAttribute('data-v'), F.inr, 1100); });
    var lc = E.byClass(E.filtered(S.on, without('cls')));
    C.donut($('c-donut'), E.CLASSES.map(function (c) { return { key: c, label: c, value: lc[c].value, color: COL[c], sub: 'Cost ' + F.inr(lc[c].cost) }; }),
      { center: [F.cr(E.sum(E.filtered(S.on, without('cls'))).value), 'Total'], active: S.F.cls, onClick: function (it) { toggle('cls', it.key); }, fmt: F.inr, aria: 'Value by asset class' });
    var lk = group(E.filtered(S.on, without('key')).filter(function (l) { return l.cls === 'Mutual funds' || l.cls === 'Equity shares'; }), function (l) { return l.key; }).sort(function (a, b) { return b.value - a.value; }).slice(0, 10);
    C.hbars($('c-top'), lk.map(function (x) { return { key: x.key, label: x.name, value: x.value, color: COL[x.cls], text: F.cr(x.value), tip: '<div class="th">' + esc(x.name) + '</div>' + C.tipRow(COL[x.cls], 'Value', F.inr(x.value)) + C.tipRow('#64748B', 'Cost', F.inr(x.cost)) + (x.cost > 0 ? C.tipRow(x.value >= x.cost ? GREEN : RED, 'Gain or loss', F.pct(x.pct)) : '') }; }),
      { active: S.F.key, onClick: function (it) { toggle('key', it.key); } });
    var gs2 = E.CLASSES.map(function (c) { return { name: c, key: c, children: group(E.filtered(S.on, without('key')).filter(function (l) { return l.cls === c; }), function (l) { return l.key; }) }; });
    C.treemap($('c-tree'), gs2, { height: 310, activeKey: S.F.key, onTile: function (c) { toggle('key', c.key); }, onGroup: function (g) { toggle('cls', g.key); } });
    var hl = group(E.filtered(S.on, without('key')).filter(function (l) { return l.cls === 'Mutual funds' || l.cls === 'Equity shares'; }), function (l) { return l.key; }), hm = hl.filter(function (x) { return x.cost > 0; }).sort(function (a, b) { return b.pct - a.pct; });
    var mv = hm.length > 10 ? hm.slice(0, 5).concat(hm.slice(-5)) : hm;
    C.hbars($('c-mov'), mv.map(function (x) { return { key: x.key, label: x.name, value: x.pct, color: x.pct >= 0 ? '#2FA97C' : '#E0605F', text: F.pct(x.pct), tip: '<div class="th">' + esc(x.name) + '</div>' + C.tipRow('#2C52AE', 'Value', F.inr(x.value)) + C.tipRow('#64748B', 'Cost', F.inr(x.cost)) + C.tipRow(x.pct >= 0 ? GREEN : RED, 'Gain or loss', F.num(x.value - x.cost, 0) + ' (' + F.pct(x.pct) + ')') }; }),
      { diverging: true, active: S.F.key, onClick: function (it) { toggle('key', it.key); }, aria: 'Return on cost, best and worst holdings' });
    var hmd = E.timeline(S.on).slice(-13), hrows = hl.slice().sort(function (a, b) { return b.value - a.value; }).slice(0, 10).map(function (x) {
      var cells = [];
      for (var i = 1; i < hmd.length; i++) {
        var p0 = E.priceOn(x.key, hmd[i - 1]), p1 = E.priceOn(x.key, hmd[i]), v = p0 && p1 && p0.p ? p1.p / p0.p - 1 : null;
        cells.push({ v: v, tip: '<div class="th">' + esc(x.name) + '</div><div class="ts">' + F.mon(hmd[i - 1]) + ' to ' + (hmd[i] === data.meta.latest ? 'latest' : F.mon(hmd[i])) + '</div>' + (v == null ? '<div class="tv">No price</div>' : C.tipRow(v >= 0 ? GREEN : RED, 'Price change', F.pct(v)) + C.tipRow('#64748B', 'Price', F.num(p1.p, 2))) });
      }
      return { key: x.key, label: x.name, cells: cells };
    });
    C.heat($('c-heat'), hmd.slice(1).map(function (d) { return d === data.meta.latest ? 'Latest' : F.mon(d).split(' ')[0]; }), hrows, { active: S.F.key, onRow: function (r) { toggle('key', r.key); } });
    $('c-att').innerHTML = attentionHtml(ls);
    $('c-att').onclick = function (e) { var li = e.target.closest('li[data-k]'); if (li && li.getAttribute('data-k')) toggle('key', li.getAttribute('data-k')); };
    drawHoldings(ls);
    $('hold-f').innerHTML = CLASS_BTN.map(function (b) { return '<button type="button" data-c="' + esc(b[0]) + '" aria-pressed="' + ((S.F.cls || '') === b[0]) + '">' + esc(b[1]) + '</button>'; }).join('');
    $('hold-f').onclick = function (e) { var b = e.target.closest('button[data-c]'); if (!b) return; var v = b.getAttribute('data-c'); if (v) S.F.cls = v; else delete S.F.cls; render(); };
    var q = $('q'); q.value = S.q; q.oninput = function () { S.q = q.value; drawHoldings(ls); };
    $('hold-dl').onclick = exportCsv;
    // deposits still running, soonest first
    var dep = ls.filter(function (l) { return l.cls === 'Term deposits' && !l.matured; }).sort(function (a, b) { return a.daysLeft - b.daysLeft; });
    $('c-hz').innerHTML = dep.length ? '<div class="horizon">' + dep.map(function (l, i) {
      return '<div class="hz"><div class="dt"><span class="m">' + F.mon(l.maturity) + '</span><span class="dd">' + l.maturity.slice(8, 10) + '</span></div><div><div class="nm2">' + esc(l.name) + '</div><div class="vv">' + F.inr(l.value) + ' · ' + F.num(l.rate, 2) + '% a year</div>' + (i === 0 ? '<div class="next">NEXT MATURITY, IN ' + l.daysLeft + ' DAYS</div>' : '') + '</div></div>';
    }).join('') + '</div>' : '<div class="empty">No running deposit in this view.</div>';
  }
  function drawHoldings(ls) {
    var q = S.q.trim().toLowerCase(), all = group(ls, function (l) { return l.key; });
    var rows = all.filter(function (r) { return !q || r.name.toLowerCase().indexOf(q) >= 0 || r.cls.toLowerCase().indexOf(q) >= 0; });
    var t = rows.reduce(function (s, r) { s.value += r.value; s.cost += r.cost; return s; }, { value: 0, cost: 0 }), tot = E.sum(ls).value;
    $('hold-cnt').textContent = rows.length + ' of ' + all.length + ' holdings';
    C.table($('c-hold'), [
      { k: 'name', label: 'Holding', sort: function (r) { return r.name; }, fmt: function (r) { return '<span class="mark" style="--c:' + COL[r.cls] + '">' + MARK[r.cls] + '</span><span class="nm">' + esc(r.name) + '</span>'; } },
      { k: 'cls', label: 'Class', sort: function (r) { return r.cls; }, fmt: function (r) { return '<span class="cls">' + esc(r.cls) + '</span>'; } },
      { k: 'cost', label: 'Cost', align: 'r', sort: function (r) { return r.cost; }, fmt: function (r) { return F.num(r.cost, 0); } },
      { k: 'value', label: 'Value', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return F.num(r.value, 0); } },
      { k: 'gain', label: 'Gain or loss', align: 'r', sort: function (r) { return r.value - r.cost; }, fmt: function (r) { return r.cls === 'Bank balances' ? '<span class="mut">-</span>' : F.gainHtml(r.value - r.cost, r.cost > 0 ? (r.value - r.cost) / r.cost : null); } },
      { k: 'w', label: 'Share of total', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return tot ? (100 * r.value / tot).toFixed(1) + '%' : '-'; } }
    ], rows, Object.assign({ foot: { name: 'Total (' + rows.length + ' holdings)', cost: F.num(t.cost, 0), value: F.num(t.value, 0), w: tot ? (100 * t.value / tot).toFixed(1) + '%' : '-' },
      onRow: function (r) { toggle('key', r.key); }, activeKey: function (r) { return S.F.key === r.key; } }, sortOpt('hold', { k: 'value', dir: 'desc' })));
  }
  function csvCell(v) { v = v == null ? '' : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function exportCsv() {
    var ls = E.filtered(S.on, S.F), head = ['Asset class', 'Name', 'Account', 'Quantity', 'Cost INR', 'Value INR', 'Gain or loss INR', 'Price date'];
    var out = [head.join(',')].concat(ls.map(function (l) {
      return [l.cls, l.name, l.account, l.qty == null ? '' : l.qty, Math.round(l.cost), Math.round(l.value), Math.round(l.value - l.cost), l.pdate || ''].map(csvCell).join(',');
    }));
    var url = URL.createObjectURL(new Blob([out.join('\r\n') + '\r\n'], { type: 'text/csv;charset=utf-8;' })), a = document.createElement('a');
    a.href = url; a.download = 'holdings_' + S.on + '.csv'; document.body.appendChild(a); a.click(); document.body.removeChild(a); setTimeout(function () { URL.revokeObjectURL(url); }, 500);
  }

  /* ---------------------------------------------------------- Mutual funds */
  function lastSip(account, key) {
    var ev = (E.series[account + '|' + key] || { ev: [] }).ev.filter(function (e) { return e.action === 'SIP' && e.date <= S.on; });
    return ev.length ? ev[ev.length - 1].qty * ev[ev.length - 1].price : null;
  }
  function pFunds(ls0) {
    var ls = ls0.filter(function (l) { return l.cls === 'Mutual funds'; }), t = E.sum(ls), x = E.xirrFor(S.on, S.F), sip = E.sipMonth(S.on, S.F);
    var open = E.openDate();
    var h = '<div class="grid g5">' + kpi('Value', F.inr(t.value), 'As on ' + F.dmy(S.on), true) + kpi('Cost', F.inr(t.cost)) + kpi('Gain or loss', gainKpi(t), gainSub(t)) +
      kpi('Return per year (XIRR)', x == null ? '<span class="mut">Not yet</span>' : F.pct(x), x == null ? 'Needs 6 months from ' + F.dmy(open) : 'Since ' + F.dmy(open) + ', opening value as invested') +
      kpi('SIP in ' + F.mon(S.on).split(' ')[0] + ' ' + S.on.slice(0, 4), F.inr(sip), 'Money added by SIP this month') + '</div>' +
      sipPlanHtml() +
      '<div class="grid g3b">' + card('Value by fund house', 'c-house', 'Click a bar to filter.') + card('Value by category', 'c-cat', 'Click a slice to filter.') +
      '<div class="card"><h3>Units and average cost after each purchase or SIP</h3><div class="cap" id="d-name"></div><div class="duo"><div><div class="cap">Units held</div><div id="d-units"></div></div><div><div class="cap">Average cost per unit</div><div id="d-avg"></div></div></div></div></div>' +
      '<div class="grid g1" style="grid-template-columns:1fr">' + card('Funds', 'c-ftab', 'Click a column heading to sort. Click a row to filter and to see its ledger below.') + '</div>' +
      '<div class="grid" style="grid-template-columns:1fr">' + card('Ledger of the fund shown above', 'c-ledger', 'Each purchase or SIP adds units and cost. Average cost = cost / units. A redemption removes units at the average cost.') + '</div>';
    $('page').innerHTML = h;
    drawSipPlan();
    var hmap = {}; E.filtered(S.on, without('fh')).filter(function (l) { return l.cls === 'Mutual funds'; }).forEach(function (l) { hmap[l.fh] = hmap[l.fh] || { v: 0, c: 0 }; hmap[l.fh].v += l.value; hmap[l.fh].c += l.cost; });
    var hs = Object.keys(hmap).map(function (k) { return { key: k, label: k.replace(' Mutual Fund', ''), value: hmap[k].v, cost: hmap[k].c }; }).sort(function (a, b) { return b.value - a.value; });
    C.hbars($('c-house'), hs.map(function (x) { return { key: x.key, label: x.label, value: x.value, color: COL['Mutual funds'], text: F.cr(x.value), tip: '<div class="th">' + esc(x.key) + '</div>' + C.tipRow('#2C52AE', 'Value', F.inr(x.value)) + C.tipRow('#64748B', 'Cost', F.inr(x.cost)) + C.tipRow(x.value >= x.cost ? GREEN : RED, 'Gain or loss', F.pct((x.value - x.cost) / x.cost)) }; }),
      { active: S.F.fh, onClick: function (it) { toggle('fh', it.key); } });
    var cm = {}; E.filtered(S.on, without('category')).filter(function (l) { return l.cls === 'Mutual funds'; }).forEach(function (l) { cm[l.category] = (cm[l.category] || 0) + l.value; });
    var PAL = ['#2C52AE', '#0E9F6E', '#8A6FB3', '#D69E1E', '#D2557A', '#2A9DB8'];
    var cats = Object.keys(cm).sort(function (a, b) { return cm[b] - cm[a]; }), ci = [];
    cats.slice(0, 6).forEach(function (k, i) { ci.push({ key: k, label: k, value: cm[k], color: PAL[i] }); });
    if (cats.length > 6) ci.push({ key: '', label: 'Other (' + (cats.length - 6) + ')', value: cats.slice(6).reduce(function (s, k) { return s + cm[k]; }, 0), color: '#94A3B8' });
    C.donut($('c-cat'), ci, { center: [F.cr(E.sum(E.filtered(S.on, without('category')).filter(function (l) { return l.cls === 'Mutual funds'; })).value), 'Funds'], active: S.F.category, onClick: function (it) { if (it.key) toggle('category', it.key); }, fmt: F.inr });
    // fund shown in the detail panel
    var pick = ls.slice().sort(function (a, b) { return b.value - a.value; })[0];
    if (S.F.key) pick = ls.filter(function (l) { return l.key === S.F.key; })[0] || pick;
    if (pick) {
      var led = E.ledger(pick.account, pick.key, S.on), lab = led.map(function (e) { return F.dmy(e.date).slice(0, -5); });
      $('d-name').textContent = pick.name + (S.F.key ? '' : '. Largest fund in view. Click a fund below to choose.');
      var tt = led.map(function (e) { return F.dmy(e.date) + ', ' + (e.action === 'OPENING' ? 'opening balance' : e.action === 'SIP' ? 'SIP' : e.action === 'SELL' ? 'redemption' : 'purchase'); });
      C.line($('d-units'), { labels: lab, tipTitle: tt, height: 250, series: [{ name: 'Units', color: '#2C52AE', values: led.map(function (e) { return e.units; }) }], fmt: function (v) { return F.num(v, 0); }, fmtFull: function (v) { return F.num(v, 3); } });
      C.line($('d-avg'), { labels: lab, tipTitle: tt, height: 250, series: [{ name: 'Average cost per unit', color: '#64748B', dash: true, values: led.map(function (e) { return e.avg; }) }], fmt: function (v) { return F.num(v, 1); }, fmtFull: function (v) { return F.num(v, 4); } });
      C.table($('c-ledger'), [
        { k: 'date', label: 'Date', fmt: function (r) { return F.dmy(r.date); } },
        { k: 'action', label: 'Event', fmt: function (r) { return r.action === 'OPENING' ? 'Opening balance' : r.action === 'SIP' ? 'SIP' : r.action === 'SELL' ? 'Redemption' : 'Purchase'; } },
        { k: 'qty', label: 'Units', align: 'r', fmt: function (r) { return (r.action === 'SELL' ? '−' : '') + F.num(r.qty, 3); } },
        { k: 'price', label: 'NAV or cost', align: 'r', fmt: function (r) { return F.num(r.price, 4); } },
        { k: 'amt', label: 'Amount', align: 'r', fmt: function (r) { return F.num(r.qty * r.price, 0); } },
        { k: 'units', label: 'Units after', align: 'r', fmt: function (r) { return F.num(r.units, 3); } },
        { k: 'cost', label: 'Cost after', align: 'r', fmt: function (r) { return F.num(r.cost, 0); } },
        { k: 'avg', label: 'Average cost after', align: 'r', fmt: function (r) { return F.num(r.avg, 4); } }
      ], led, {});
    } else { $('d-name').textContent = 'No fund matches the slicers.'; $('c-ledger').innerHTML = '<div class="empty">No fund matches the slicers.</div>'; }
    C.table($('c-ftab'), [
      { k: 'name', label: 'Fund', sort: function (r) { return r.name; }, fmt: function (r) { return esc(r.name); } },
      { k: 'fh', label: 'Fund house', sort: function (r) { return r.fh; }, fmt: function (r) { return esc(r.fh.replace(' Mutual Fund', '')); } },
      { k: 'account', label: 'Folio', sort: function (r) { return r.account; }, fmt: function (r) { return esc(r.account.replace('Folio ', '')); } },
      { k: 'qty', label: 'Units', align: 'r', sort: function (r) { return r.qty; }, fmt: function (r) { return F.num(r.qty, 3); } },
      { k: 'avg', label: 'Average cost', align: 'r', sort: function (r) { return r.avg; }, fmt: function (r) { return F.num(r.avg, 4); } },
      { k: 'cost', label: 'Cost', align: 'r', sort: function (r) { return r.cost; }, fmt: function (r) { return F.num(r.cost, 0); } },
      { k: 'price', label: 'NAV on date', align: 'r', sort: function (r) { return r.price; }, fmt: function (r) { return F.num(r.price, 4); } },
      { k: 'value', label: 'Value', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return F.num(r.value, 0); } },
      { k: 'gain', label: 'Gain or loss', align: 'r', sort: function (r) { return r.value - r.cost; }, fmt: function (r) { return F.gainHtml(r.value - r.cost, pct(r)); } },
      { k: 'sip', label: 'Last SIP', align: 'r', sort: function (r) { return lastSip(r.account, r.key); }, fmt: function (r) { var s = lastSip(r.account, r.key); return s == null ? '<span class="mut">-</span>' : F.num(s, 0); } }
    ], ls, Object.assign({ foot: { name: 'Total (' + ls.length + ' funds)', cost: F.num(t.cost, 0), value: F.num(t.value, 0), gain: F.gainHtml(t.gain, t.pct) }, onRow: function (r) { toggle('key', r.key); }, activeKey: function (r) { return S.F.key === r.key; } }, sortOpt('funds', { k: 'value', dir: 'desc' })));
  }

  /* ---------------------------------------------------------- Equity shares */
  function pShares(ls0) {
    var ls = ls0.filter(function (l) { return l.cls === 'Equity shares'; }), t = E.sum(ls), g = group(ls, function (l) { return l.key; }).filter(function (x) { return x.pct != null; });
    var best = g.slice().sort(function (a, b) { return b.pct - a.pct; })[0], worst = g.slice().sort(function (a, b) { return a.pct - b.pct; })[0];
    var h = '<div class="grid g5">' + kpi('Value', F.inr(t.value), 'As on ' + F.dmy(S.on), true) + kpi('Cost with brokerage', F.inr(t.cost)) + kpi('Gain or loss', gainKpi(t), gainSub(t)) +
      kpi('Best share', best ? esc(best.name) : '-', best ? F.gainHtml(best.value - best.cost, best.pct) : '') + kpi('Weakest share', worst ? esc(worst.name) : '-', worst ? F.gainHtml(worst.value - worst.cost, worst.pct) : '') + '</div>' +
      '<div class="grid g3c">' + card('Sector, then company', 'c-stree', 'Click a company to filter. Click a sector name to filter by sector.') + card('Gain or loss by share', 'c-gl', 'Percent on cost, best first.') + card('Buys over time', 'c-buys', 'Shares bought each month. Opening holdings are not buys.') + '</div>' +
      '<div class="grid" style="grid-template-columns:1fr">' + card('Equity shares', 'c-shtab', 'Cost per share includes brokerage. Price comes from the prices file for the chosen date.') + '</div>';
    $('page').innerHTML = h;
    var base = E.filtered(S.on, without('key')).filter(function (l) { return l.cls === 'Equity shares'; }), secs = {};
    base.forEach(function (l) { (secs[l.sector] = secs[l.sector] || []).push(l); });
    C.treemap($('c-stree'), Object.keys(secs).map(function (s) { return { name: s, key: s, children: group(secs[s], function (l) { return l.key; }) }; }),
      { height: 330, activeKey: S.F.key, onTile: function (c) { toggle('key', c.key); }, onGroup: function (gp) { toggle('sector', gp.key); } });
    var gl = group(base, function (l) { return l.key; }).filter(function (x) { return x.pct != null; }).sort(function (a, b) { return b.pct - a.pct; });
    var mx = Math.max.apply(null, gl.map(function (x) { return Math.abs(x.pct); }).concat([0.01]));
    $('c-gl').innerHTML = '<div class="scroll" id="c-gl2"></div>';
    C.hbars($('c-gl2'), gl.map(function (x) { return { key: x.key, label: x.name, value: x.pct, color: x.pct >= 0 ? '#2FA97C' : '#E0605F', text: F.pct(x.pct), tip: '<div class="th">' + esc(x.name) + '</div>' + C.tipRow('#2C52AE', 'Value', F.inr(x.value)) + C.tipRow('#64748B', 'Cost', F.inr(x.cost)) + C.tipRow(x.pct >= 0 ? GREEN : RED, 'Gain or loss', F.num(x.value - x.cost, 0) + ' (' + F.pct(x.pct) + ')') }; }),
      { diverging: true, max: mx, active: S.F.key, onClick: function (it) { toggle('key', it.key); } });
    var by = E.buysByMonth(S.on, S.F, 'SHARE'), months = uniq(E.timeline(S.on).map(function (d) { return d.slice(0, 7); }));
    C.vbars($('c-buys'), months.map(function (m) { return { label: F.mon(m + '-01'), value: by[m] || 0, color: COL['Equity shares'], tip: '<div class="th">' + F.mon(m + '-01') + '</div>' + C.tipRow(COL['Equity shares'], 'Bought', F.inr(by[m] || 0)) }; }), { fmt: F.cr, height: 250 });
    C.table($('c-shtab'), [
      { k: 'name', label: 'Company', sort: function (r) { return r.name; }, fmt: function (r) { return esc(r.name); } },
      { k: 'sector', label: 'Sector', sort: function (r) { return r.sector; }, fmt: function (r) { return esc(r.sector); } },
      { k: 'account', label: 'Account', sort: function (r) { return r.account; }, fmt: function (r) { return esc(r.account); } },
      { k: 'qty', label: 'Quantity', align: 'r', sort: function (r) { return r.qty; }, fmt: function (r) { return F.num(r.qty, 0); } },
      { k: 'avg', label: 'Average cost', align: 'r', sort: function (r) { return r.avg; }, fmt: function (r) { return F.num(r.avg, 2); } },
      { k: 'price', label: 'Price on date', align: 'r', sort: function (r) { return r.price; }, fmt: function (r) { return F.num(r.price, 2); } },
      { k: 'cost', label: 'Cost', align: 'r', sort: function (r) { return r.cost; }, fmt: function (r) { return F.num(r.cost, 0); } },
      { k: 'value', label: 'Value', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return F.num(r.value, 0); } },
      { k: 'gain', label: 'Gain or loss', align: 'r', sort: function (r) { return r.value - r.cost; }, fmt: function (r) { return F.gainHtml(r.value - r.cost, pct(r)); } }
    ], ls, Object.assign({ foot: { name: 'Total (' + ls.length + ' lines)', cost: F.num(t.cost, 0), value: F.num(t.value, 0), gain: F.gainHtml(t.gain, t.pct) }, onRow: function (r) { toggle('key', r.key); }, activeKey: function (r) { return S.F.key === r.key; } }, sortOpt('shares', { k: 'value', dir: 'desc' })));
  }

  /* ---------------------------------------------------------- Bank and deposits */
  function pBank(ls) {
    var bk = ls.filter(function (l) { return l.cls === 'Bank balances'; }), td = ls.filter(function (l) { return l.cls === 'Term deposits'; });
    var fcAll = bk.concat(td).filter(function (l) { return l.ccy !== 'INR'; }), fcInr = fcAll.reduce(function (s, l) { return s + l.value; }, 0);
    var usd = fcAll.reduce(function (s, l) { return s + l.local; }, 0), fx = E.priceOn('USDINR', S.on);
    var nxt = td.filter(function (l) { return !l.matured; }).sort(function (a, b) { return a.daysLeft - b.daysLeft; })[0];
    var h = '<div class="grid g4">' + kpi('Bank balances', F.inr(E.sum(bk).value), 'Savings, foreign currency and broker cash', true) + kpi('Term deposits', F.inr(E.sum(td).value), 'Principal plus interest to the date') +
      kpi('Foreign currency, in INR', F.inr(fcInr), fcAll.length ? 'USD ' + F.num(usd, 2) + ' at ' + F.num(fx ? fx.p : 0, 4) : 'None in view') +
      kpi('Next maturity', nxt ? F.dmy(nxt.maturity) : '-', nxt ? F.cr(nxt.value) + ', in ' + nxt.daysLeft + ' days' : 'No deposit maturing') + '</div>' +
      '<div class="grid g3a">' + card('Balance by account', 'c-bal', 'Click a bar to filter. Foreign currency shown in INR.') + card('Deposits by maturity month', 'c-mat', 'Value on the chosen date, by month of maturity.') + card('Currency split', 'c-ccy', 'Click a slice to filter.') + '</div>' +
      '<div class="grid" style="grid-template-columns:1fr"><div class="card"><h3>Accounts</h3><div id="c-acc"></div></div></div><div class="grid" style="grid-template-columns:1fr"><div class="card"><h3>Term deposits</h3><div id="c-fd"></div><p class="hint" style="margin:10px 0 0;font-size:13px;color:var(--muted)">US dollar deposits are held in USD and shown in INR at the last USD/INR rate on or before the chosen date. Their cost is converted at the same rate, so gain or loss here excludes currency movement since the deposit date.</p></div></div>';
    $('page').innerHTML = h;
    var all = E.filtered(S.on, without('account'));
    C.hbars($('c-bal'), all.filter(function (l) { return l.cls === 'Bank balances'; }).sort(function (a, b) { return b.value - a.value; }).map(function (l) { return { key: l.account, label: l.name.replace('Foreign currency account', 'Foreign ccy').replace(' savings', '').replace(' cash', ' cash'), value: l.value, color: COL['Bank balances'], text: F.cr(l.value), tip: '<div class="th">' + esc(l.name) + '</div>' + C.tipRow(COL['Bank balances'], 'Balance', F.cur(l.local, l.ccy)) + (l.ccy !== 'INR' ? C.tipRow('#64748B', 'In INR', F.inr(l.value)) : '') + '<div class="ts">Balance as of ' + F.dmy(l.pdate) + '</div>' }; }),
      { active: S.F.account, onClick: function (it) { toggle('account', it.key); } });
    var mm = {}; td.filter(function (l) { return !l.matured; }).forEach(function (l) { var m = l.maturity.slice(0, 7); mm[m] = (mm[m] || 0) + l.value; });
    var ms = Object.keys(mm).sort();
    C.vbars($('c-mat'), ms.map(function (m) { return { label: F.mon(m + '-01'), value: mm[m], color: COL['Term deposits'], tip: '<div class="th">Maturing ' + F.mon(m + '-01') + '</div>' + C.tipRow(COL['Term deposits'], 'Value', F.inr(mm[m])) }; }), { fmt: F.cr, height: 230 });
    var cc = {}; E.filtered(S.on, without('ccy')).filter(function (l) { return l.cls === 'Bank balances' || l.cls === 'Term deposits'; }).forEach(function (l) { cc[l.ccy] = (cc[l.ccy] || 0) + l.value; });
    C.donut($('c-ccy'), Object.keys(cc).map(function (k, i) { return { key: k, label: k, value: cc[k], color: ['#8A6FB3', '#D69E1E', '#2C52AE'][i % 3] }; }), { center: [F.cr(Object.keys(cc).reduce(function (s, k) { return s + cc[k]; }, 0)), 'In INR'], active: S.F.ccy, onClick: function (it) { toggle('ccy', it.key); }, fmt: F.inr });
    C.table($('c-acc'), [
      { k: 'bank', label: 'Bank', sort: function (r) { return r.bank; }, fmt: function (r) { return esc(r.bank); } },
      { k: 'name', label: 'Account', sort: function (r) { return r.name; }, fmt: function (r) { return esc(r.kind + ' ' + r.name.split(' ').pop()); } },
      { k: 'ccy', label: 'Currency', sort: function (r) { return r.ccy; }, fmt: function (r) { return esc(r.ccy); } },
      { k: 'local', label: 'Balance', align: 'r', sort: function (r) { return r.local; }, fmt: function (r) { return F.num(r.local, r.ccy === 'INR' ? 0 : 2); } },
      { k: 'value', label: 'In INR', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return F.num(r.value, 0); } }
    ], bk, Object.assign({ foot: { bank: 'Total', value: F.num(E.sum(bk).value, 0) }, onRow: function (r) { toggle('account', r.account); }, activeKey: function (r) { return S.F.account === r.account; } }, sortOpt('acc', { k: 'value', dir: 'desc' })));
    C.table($('c-fd'), [
      { k: 'bank', label: 'Bank', sort: function (r) { return r.bank; }, fmt: function (r) { return esc(r.bank); } },
      { k: 'kind', label: 'Type', sort: function (r) { return r.kind; }, fmt: function (r) { return esc(r.kind); } },
      { k: 'start', label: 'Start', sort: function (r) { return r.start; }, fmt: function (r) { return F.dmy(r.start); } },
      { k: 'maturity', label: 'Maturity', sort: function (r) { return r.maturity; }, fmt: function (r) { return F.dmy(r.maturity); } },
      { k: 'rate', label: 'Rate', align: 'r', sort: function (r) { return r.rate; }, fmt: function (r) { return F.num(r.rate, 2) + '%'; } },
      { k: 'principal', label: 'Principal', align: 'r', sort: function (r) { return r.principal; }, fmt: function (r) { return F.num(r.principal, r.ccy === 'INR' ? 0 : 2) + (r.ccy === 'INR' ? '' : ' ' + r.ccy); } },
      { k: 'local', label: 'Value', align: 'r', sort: function (r) { return r.local; }, fmt: function (r) { return F.num(r.local, r.ccy === 'INR' ? 0 : 2) + (r.ccy === 'INR' ? '' : ' ' + r.ccy); } },
      { k: 'value', label: 'In INR', align: 'r', sort: function (r) { return r.value; }, fmt: function (r) { return F.num(r.value, 0); } },
      { k: 'status', label: 'Status', sort: function (r) { return r.daysLeft; }, fmt: function (r) { return r.matured ? '<span class="pill fail">Matured</span>' : r.daysLeft <= 90 ? '<span class="pill warn">Due in ' + r.daysLeft + ' days</span>' : '<span class="pill">Active</span>'; } }
    ], td, Object.assign({ foot: { bank: 'Total', value: F.num(E.sum(td).value, 0) }, onRow: function (r) { toggle('key', r.key); }, activeKey: function (r) { return S.F.key === r.key; } }, sortOpt('fd', { k: 'maturity', dir: 'asc' })));
  }

  /* ---------------------------------------------------------- Property and rent (own page, not in the total) */
  var KIND_COL = { 'SIP': '#2C52AE', 'Insurance': '#8A6FB3', 'House tax and maintenance': '#D69E1E' };
  function inrCr(x) { return '₹ ' + F.cr(x); }
  function fact(label, value) { return '<div class="fact"><span>' + esc(label) + '</span><b>' + value + '</b></div>'; }
  function inDays(from, to) { return Life.days(from, to); }
  function pProperty() {
    var on = data.meta.latest, ps = L.props;
    if (!ps.length) { $('page').innerHTML = '<div class="card"><div class="empty">No house property in this data set.</div></div>'; return; }
    var val = 0, cost = 0, rentM = 0, rentY = 0;
    ps.forEach(function (p) { val += p.value || 0; cost += p.cost || 0; rentM += p.rent; });
    var rc = L.rent, y1 = Life.addMonths(on, -12);
    rc.forEach(function (r) { if (r.date > y1 && r.date <= on) rentY += r.amount; });
    var gain = val - cost, one = ps.length === 1 ? ps[0] : null;
    var h = '<div class="notice">House property is shown here on its own. It is not added to the total value on the Overview.</div>' +
      '<div class="grid g5">' + kpi('Market value', F.inr(val), one ? 'Own estimate as on ' + F.dmy(one.valueDate) : ps.length + ' properties', true) +
      kpi('Cost', F.inr(cost), one ? 'Bought ' + F.dmy(one.costDate) : '') + kpi('Gain or loss', gainKpi({ gain: gain }), cost ? '<span class="' + (gain >= 0 ? 'up' : 'down') + '">' + F.pct(gain / cost) + '</span> on cost' : '') +
      kpi('Rent per month', F.inr(rentM), one ? 'Credited on the ' + one.rentDay + 'th' : '') +
      kpi('Rent received, last 12 months', F.inr(rentY), val ? (100 * rentY / val).toFixed(1) + '% of market value' : '') + '</div>' +
      '<div class="grid g15">' + card('Rent received, month by month', 'c-rent', '') +
      '<div class="card"><h3>Lease, house tax and maintenance</h3><div id="c-facts"></div></div></div>' +
      '<div class="grid" style="grid-template-columns:1fr"><div class="card"><h3>Rent receipts</h3><div id="c-rcpt"></div></div></div>';
    $('page').innerHTML = h;
    var p = ps[0], mine = L.rentOf(p.id), tot = mine.reduce(function (s, r) { return s + r.amount; }, 0);
    C.vbars($('c-rent'), mine.map(function (r) { return { label: F.mon(r.date), value: r.amount, color: '#D69E1E', tip: '<div class="th">' + F.mon(r.date) + '</div>' + C.tipRow('#D69E1E', 'Rent received', F.inr(r.amount)) + '<div class="ts">' + F.dmy(r.date) + '</div>' }; }),
      { fmt: F.cr, height: 250, aria: 'Rent received by month' });
    $('c-rent').insertAdjacentHTML('afterend', '<div class="note">' + mine.length + ' receipts, ' + F.inr(tot) + ' since the lease began on ' + F.dmy(p.leaseStart) + '. Credited to ' + esc(p.account) + '.</div>');
    var nt = L.taxDates(p, on, Life.addMonths(on, 24))[0], nr = (function () { var y = +on.slice(0, 4), m = +on.slice(5, 7), d = Life.iso(y, m, p.rentDay); if (d <= on) { m++; if (m > 12) { m = 1; y++; } d = Life.iso(y, m, p.rentDay); } return d; })();
    $('c-facts').innerHTML = fact('Property', esc(p.name + ', ' + p.city)) + fact('Tenant', esc(p.tenant)) + fact('Rent per month', F.inr(p.rent)) + fact('Next rent due', F.dmy(nr)) +
      fact('Lease', F.dmy(p.leaseStart) + ' to ' + F.dmy(p.leaseEnd)) + fact('Lease ends in', inDays(on, p.leaseEnd) + ' days') +
      fact('House tax and maintenance a year', F.inr(p.tax)) + fact('Next house tax and maintenance', nt ? F.dmy(nt) + ', in ' + inDays(on, nt) + ' days' : '-') + fact('Last paid', p.taxPaid ? F.dmy(p.taxPaid) : '-');
    C.table($('c-rcpt'), [{ k: 'date', label: 'Date', fmt: function (r) { return F.dmy(r.date); } }, { k: 'm', label: 'For the month of', fmt: function (r) { return F.mon(r.date); } },
      { k: 'a', label: 'Amount', align: 'r', fmt: function (r) { return F.num(r.amount, 0); } }],
      mine.slice().reverse(), { foot: { date: 'Total (' + mine.length + ' receipts)', a: F.num(tot, 0) } });
  }

  /* ---------------------------------------------------------- Insurance (own page, not in the total) */
  function pInsurance() {
    var on = data.meta.latest, ins = L.ins;
    if (!ins.length) { $('page').innerHTML = '<div class="card"><div class="empty">No insurance policy in this data set.</div></div>'; return; }
    var life = ins.filter(function (p) { return p.type === 'Term life'; }), med = ins.filter(function (p) { return p.type === 'Health'; }), ret = ins.filter(function (p) { return p.payout; });
    var nxt = null; ins.forEach(function (p) { var d = L.nextDue(p, on); if (d && (!nxt || d < nxt.d)) nxt = { d: d, p: p }; });
    var lc = life.reduce(function (s, p) { return s + p.cover; }, 0), mc = med.reduce(function (s, p) { return s + p.cover; }, 0);
    var h = '<div class="notice">Insurance cover is not an asset. Nothing on this page is added to the total value on the Overview.</div>' +
      '<div class="grid g4">' + kpi('Life cover', inrCr(lc), life.map(function (p) { return esc(p.name); }).join(', '), true) +
      kpi('Medical cover', inrCr(mc), med.length ? esc(med[0].coverNote) : '') +
      kpi('Premiums in ' + on.slice(0, 4), F.inr(L.yearPremiums(on)), ins.length + ' policies') +
      kpi('Next premium', nxt ? F.dmy(nxt.d) : '-', nxt ? esc(nxt.p.name) + ', ' + F.inr(nxt.p.premium) + ', in ' + inDays(on, nxt.d) + ' days' : 'None due') + '</div>' +
      '<div class="grid g3 pol">' + ins.map(function (p, i) { return '<div class="card" id="pol' + i + '"></div>'; }).join('') + '</div>';
    $('page').innerHTML = h;
    ins.forEach(function (p, i) {
      var paid = L.paid(p, on), tot = L.total(p), nd = L.nextDue(p, on), last = (function () { var d = L.premiumDates(p, Life.iso(on.slice(0, 4) - 3, 1, 1), on); return d.length ? d[d.length - 1] : null; })();
      var due = F.num(p.day, 0) + ' ' + F.mon(Life.iso(2000, p.month, 1)).split(' ')[0];
      var f = fact('Premium', F.inr(p.premium) + ' a year') + fact('Due on', p.first == null ? due + ' each year' : due + ', ' + p.first + ' to ' + p.last + ' (' + tot + ' years)');
      if (paid != null) f += fact('Paid so far', paid + ' of ' + tot + ' (' + F.inr(paid * p.premium) + ')') + fact('Still to pay', (tot - paid) + ' (' + F.inr((tot - paid) * p.premium) + ')');
      else f += fact('Last paid', last ? F.dmy(last) : '-');
      f += fact('Next due', nd ? F.dmy(nd) + ', in ' + inDays(on, nd) + ' days' : 'Fully paid');
      if (p.payout) f += fact('Income', F.inr(p.payout) + ' a month, on the ' + p.payoutDay + 'th') + fact('Income runs', F.dmy(p.payoutStart) + ' to ' + F.dmy(p.payoutEnd)) + fact('Payments', L.payments(p) + ' (' + F.inr(L.payments(p) * p.payout) + ') until age 85');
      var bar = paid != null ? '<div class="prog" role="img" aria-label="' + paid + ' of ' + tot + ' premiums paid"><i style="width:' + (100 * paid / tot).toFixed(1) + '%"></i></div>' : '';
      $('pol' + i).innerHTML = '<div class="polhead"><h3>' + esc(p.name) + '</h3><span class="chipk">' + esc(p.type) + '</span></div>' +
        (p.cover ? '<div class="polcover">' + inrCr(p.cover) + '<span> cover' + (p.coverNote ? ', ' + esc(p.coverNote.toLowerCase()) : '') + '</span></div>' : '<div class="polcover"><span>Retirement income policy</span></div>') + bar + f;
    });
  }

  /* ---------------------------------------------------------- Cash calendar */
  var CAL = { m: 0 };
  function agg(ev) {                                   // several SIPs on one day show as one line
    var out = [], idx = {};
    ev.forEach(function (e) {
      var k = e.date + '|' + e.kind;
      if (e.kind === 'SIP' && idx[k] != null) { var o = out[idx[k]]; o.n++; o.amount += e.amount; o.label = 'SIP, ' + o.n + ' funds'; return; }
      idx[k] = out.length; out.push({ date: e.date, kind: e.kind, label: e.kind === 'SIP' ? 'SIP, 1 fund' : e.label, amount: e.amount, n: 1, detail: e.label });
    });
    return out;
  }
  function pCalendar() {
    var on = data.meta.latest, ev = L.calendar(on, 12), rows = agg(ev);
    if (!ev.length) { $('page').innerHTML = '<div class="card"><div class="empty">No commitments in the next 12 months.</div></div>'; return; }
    var months = [], m0 = ev[0].date.slice(0, 7); for (var i = 0; i < 12; i++) months.push(Life.addMonths(m0 + '-01', i).slice(0, 7));
    var by = {}, tot = { 'SIP': 0, 'Insurance': 0, 'House tax and maintenance': 0 }, all = 0;
    months.forEach(function (m) { by[m] = { 'SIP': 0, 'Insurance': 0, 'House tax and maintenance': 0, t: 0 }; });
    ev.forEach(function (e) { var b = by[e.date.slice(0, 7)]; if (b) { b[e.kind] += e.amount; b.t += e.amount; } tot[e.kind] += e.amount; all += e.amount; });
    if (CAL.m < 0 || CAL.m > 11) CAL.m = 0;
    var first = rows[0], cnt = function (k) { return ev.filter(function (e) { return e.kind === k; }).length; };
    var h = '<div class="notice">Money going out in the next 12 months, from ' + F.dmy(Life.addMonths(on, 0)) + '. Rent received and deposits maturing are money coming in, so they are not listed.</div>' +
      '<div class="grid g5">' + kpi('Next 12 months', F.inr(all), 'SIP, premiums, house tax and maintenance', true) +
      kpi('SIP', F.inr(tot['SIP']), L.sip.length + ' funds, ' + F.inr(L.sipTotal) + ' a month') + kpi('Insurance premiums', F.inr(tot['Insurance']), cnt('Insurance') + ' premiums') +
      kpi('House tax and maintenance', F.inr(tot['House tax and maintenance']), cnt('House tax and maintenance') ? cnt('House tax and maintenance') + ' payment' : 'None due') +
      kpi('Next commitment', F.dmy(first.date), esc(first.label) + ', ' + F.inr(first.amount) + ', in ' + inDays(on, first.date) + ' days') + '</div>' +
      '<div class="card"><div class="panelhead"><div><h3>Commitments by month</h3><div class="note" style="margin:2px 0 0">Click a month to see its calendar below.</div></div>' +
      '<div class="keyrow">' + Object.keys(KIND_COL).map(function (k) { return '<span><i style="background:' + KIND_COL[k] + '"></i>' + k + '</span>'; }).join('') + '</div></div><div id="c-mbar"></div></div>' +
      '<div class="card"><div class="panelhead"><h3 id="cal-title"></h3><div class="calnav"><button type="button" id="cal-prev" aria-label="Previous month">‹</button><button type="button" id="cal-next" aria-label="Next month">›</button></div></div><div id="c-cal"></div><div class="note">Dates are the plan dates. A SIP is debited on the next working day when its date is a holiday.</div></div>' +
      '<div class="card"><h3>All commitments, next 12 months</h3><div id="c-list"></div></div>';
    $('page').innerHTML = h;
    var mx = Math.max.apply(null, months.map(function (m) { return by[m].t; }).concat([1])), bh = 170;
    $('c-mbar').innerHTML = '<div class="mbars" role="group" aria-label="Commitments by month">' + months.map(function (m, i) {
      var b = by[m], segs = Object.keys(KIND_COL).filter(function (k) { return b[k] > 0; }).map(function (k) { return '<i title="' + k + ' ' + F.inr(b[k]) + '" style="height:' + Math.max(3, Math.round(bh * b[k] / mx)) + 'px;background:' + KIND_COL[k] + '"></i>'; }).join('');
      return '<button type="button" class="mb' + (i === CAL.m ? ' on' : '') + '" data-m="' + i + '" aria-pressed="' + (i === CAL.m) + '" aria-label="' + F.mon(m + '-01') + ' ' + F.inr(b.t) + '"><span class="mt">' + (b.t ? F.cr(b.t) : '-') + '</span><span class="stack" style="height:' + bh + 'px">' + segs + '</span><span class="ml">' + F.mon(m + '-01') + '</span></button>';
    }).join('') + '</div>';
    $('c-mbar').onclick = function (e) { var b = e.target.closest('.mb'); if (b) { CAL.m = +b.getAttribute('data-m'); pCalendar(); } };
    // month calendar
    var ym = months[CAL.m], y = +ym.slice(0, 4), mo = +ym.slice(5, 7), dim = new Date(Date.UTC(y, mo, 0)).getUTCDate(), lead = (new Date(Date.UTC(y, mo - 1, 1)).getUTCDay() + 6) % 7;
    var mrows = rows.filter(function (r) { return r.date.slice(0, 7) === ym; });
    $('cal-title').textContent = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][mo - 1] + ' ' + y + ': ' + F.inr(by[ym].t);
    var g = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(function (d) { return '<div class="wd">' + d + '</div>'; }).join('');
    for (var k = 0; k < lead; k++) g += '<div class="day off"></div>';
    for (var d = 1; d <= dim; d++) {
      var ds = Life.iso(y, mo, d), es = mrows.filter(function (r) { return r.date === ds; });
      g += '<div class="day' + (es.length ? ' has' : '') + '"><span class="dn">' + d + '</span>' + es.map(function (e) { return '<div class="ev" style="--c:' + KIND_COL[e.kind] + '"><span class="el">' + esc(e.label) + '</span><b>' + F.num(e.amount, 0) + '</b></div>'; }).join('') + '</div>';
    }
    $('c-cal').innerHTML = '<div class="calgrid">' + g + '</div><div class="callist">' + (mrows.length ? mrows.map(function (e) { return '<div class="ev" style="--c:' + KIND_COL[e.kind] + '"><span class="el">' + F.dmy(e.date) + ', ' + esc(e.label) + '</span><b>' + F.num(e.amount, 0) + '</b></div>'; }).join('') : '<div class="empty">Nothing due this month.</div>') + '</div>';
    $('cal-prev').onclick = function () { if (CAL.m > 0) { CAL.m--; pCalendar(); } }; $('cal-next').onclick = function () { if (CAL.m < 11) { CAL.m++; pCalendar(); } };
    $('cal-prev').disabled = CAL.m === 0; $('cal-next').disabled = CAL.m === 11;
    C.table($('c-list'), [{ k: 'd', label: 'Date', fmt: function (r) { return F.dmy(r.date); } },
      { k: 'k', label: 'Type', fmt: function (r) { return '<span class="kdot" style="background:' + KIND_COL[r.kind] + '"></span>' + esc(r.kind); } },
      { k: 'l', label: 'What', fmt: function (r) { return '<span style="white-space:normal">' + esc(r.label) + '</span>'; } },
      { k: 'a', label: 'Amount', align: 'r', fmt: function (r) { return F.num(r.amount, 0); } }], rows,
      { foot: { d: 'Total (' + rows.length + ' dates)', a: F.num(all, 0) }, onRow: function (r) { CAL.m = Math.max(0, months.indexOf(r.date.slice(0, 7))); pCalendar(); window.scrollTo(0, document.getElementById('c-cal').getBoundingClientRect().top + window.scrollY - 120); } });
  }

  /* ---------------------------------------------------------- SIP plan card on the Funds page */
  function sipPlanHtml() { return '<div class="grid g15">' + card('SIP plan', 'c-sipplan', '') + card('SIP money added each month', 'c-sipbar', 'Money added by SIP in each month, from the statements.') + '</div>'; }
  function drawSipPlan() {
    var on = data.meta.latest, plan = L.sip.filter(function (s) {
      var i = E.ins[s.key] || {}; if (S.F.cls && S.F.cls !== 'Mutual funds') return false; if (S.F.sector) return false;
      if (S.F.fh && i.house !== S.F.fh) return false; if (S.F.category && i.group !== S.F.category) return false; if (S.F.key && S.F.key !== s.key) return false; if (S.F.account && S.F.account !== s.folio) return false; return true;
    });
    var tot = plan.reduce(function (s, x) { return s + x.amount; }, 0);
    C.table($('c-sipplan'), [{ k: 'n', label: 'Fund', fmt: function (r) { return esc(r.name); } }, { k: 'f', label: 'Fund house', fmt: function (r) { return esc((E.ins[r.key] || { house: '' }).house.replace(' Mutual Fund', '')); } },
      { k: 'd', label: 'Day', align: 'r', fmt: function (r) { return r.day; } }, { k: 'x', label: 'Next debit', align: 'r', fmt: function (r) { var y = +on.slice(0, 4), m = +on.slice(5, 7), d = Life.iso(y, m, r.day); if (d <= on) { m++; if (m > 12) { m = 1; y++; } d = Life.iso(y, m, r.day); } return F.dmy(d); } },
      { k: 'a', label: 'Per month', align: 'r', fmt: function (r) { return F.num(r.amount, 0); } }], plan,
      { foot: { n: 'Total (' + plan.length + ' funds)', a: F.num(tot, 0) } });
    var tl = E.timeline(S.on);
    C.vbars($('c-sipbar'), tl.map(function (d) { var v = E.sipMonth(d, S.F); return { label: F.mon(d), value: v, color: COL['Mutual funds'], tip: '<div class="th">' + F.mon(d) + '</div>' + C.tipRow(COL['Mutual funds'], 'SIP', F.inr(v)) }; }), { fmt: F.cr, height: 230, aria: 'SIP money added by month' });
  }

  /* ---------------------------------------------------------- Data checks */
  function pChecks() {
    var all = E.lines(S.on), sh = all.filter(function (l) { return l.cls === 'Mutual funds' || l.cls === 'Equity shares'; }), tot = E.sum(all), bc = E.byClass(all);
    var run = [];
    run.push(['Total = sum of the four asset classes (' + F.dmy(S.on) + ')', Math.abs(tot.value - E.CLASSES.reduce(function (s, c) { return s + bc[c].value; }, 0)) < 0.005, F.inr(tot.value)]);
    var off = sh.filter(function (l) { return Math.abs(l.qty * l.price - l.value) > 0.005; }).length;
    run.push(['Value = units x price, recomputed for every fund and share', off === 0, sh.length + ' holdings checked, ' + off + ' differ']);
    var noPx = sh.filter(function (l) { return l.price == null; }).length;
    run.push(['Every fund and share has a price on or before the date', noPx === 0, noPx + ' without a price']);
    var stale = sh.filter(function (l) { return l.pdate !== S.on && (Engine.dn(S.on) - Engine.dn(l.pdate)) > 7; }).length;
    run.push(['Prices are from the chosen date or at most 7 days older', stale === 0, stale + ' older than 7 days']);
    var usd = all.some(function (l) { return l.ccy !== 'INR'; }), fx = E.priceOn('USDINR', S.on);
    run.push(['USD/INR rate found for the date', !usd || !!fx, fx ? F.num(fx.p, 4) + ' on ' + F.dmy(fx.date) : (usd ? 'missing' : 'no USD amount')]);
    var rows = data.checks.map(function (c) { return [c.name, c.ok, c.detail]; }).concat(run);
    var fails = rows.filter(function (r) { return !r[1]; }).length;
    var h = '<div class="grid g2"><div class="card"><h3>How the numbers are worked out</h3><ul class="rules">' +
      '<li>Value on a date = units held on that date x price on that date. Price is the latest one on or before the date.</li>' +
      '<li>Units held = opening balance + purchases and SIPs up to the date, less sales.</li>' +
      '<li>Average cost = total cost / total units. A sale removes units at the average cost. Share cost includes brokerage.</li>' +
      '<li>Fund NAVs are published once a day, so this page shows month ends and the latest date in the prices file. It is not a live ticker.</li>' +
      '<li>Deposits: principal plus simple interest to the date. Interest stops at maturity and the deposit is flagged until it is closed or renewed.</li>' +
      '<li>Foreign currency amounts are converted to INR at the USD/INR rate of the date. USD amounts are shown beside the INR value.</li>' +
      '<li>Return per year (XIRR) counts the opening balance as invested on the opening date at that day’s value, and appears from 6 months after it.</li>' +
      '<li>A slicer keeps only items that carry that attribute: a share has a sector, a fund has a fund house, a bank account has neither.</li>' +
      '<li>Insurance cover is not an asset, and the house sits on its own page. Neither is added to the total value.</li>' +
      '<li>The cash calendar lists money going out in the 12 months after the latest date: SIPs, insurance premiums, house tax and maintenance. Rent and deposit maturities are money coming in.</li></ul></div>' +
      '<div class="card"><h3>Checks <span class="pill ' + (fails ? 'fail' : 'pass') + '">' + (fails ? fails + ' failed' : 'All ' + rows.length + ' pass') + '</span></h3><div id="c-chk"></div></div></div>' +
      '<div class="grid g2"><div class="card"><h3>Data in this file</h3><div id="c-set"></div></div><div class="card"><h3>Two data sets, one dashboard</h3><ul class="rules"><li>This file holds: <b>' + esc(data.meta.label) + '</b>.</li><li>Dummy data set: real company, fund and bank names with invented numbers. This is what goes to GitHub.</li><li>Real data set: built on the owner’s laptop from the real statements with the same code. It is never uploaded.</li><li>Prices come from one separate file, filled by a separate script.</li></ul></div></div>';
    $('page').innerHTML = h;
    C.table($('c-chk'), [{ k: 'n', label: 'Check', fmt: function (r) { return '<span style="white-space:normal">' + esc(r[0]) + '</span>'; } }, { k: 'r', label: 'Result', fmt: function (r) { return '<span class="pill ' + (r[1] ? 'pass' : 'fail') + '">' + (r[1] ? 'PASS' : 'FAIL') + '</span> <span class="mut">' + esc(r[2]) + '</span>'; } }], rows, { flat: true });
    var cnt = [['Holdings (funds and shares)', data.instruments.length], ['Transactions', data.tx.length], ['Price rows', data.prices.length], ['Bank balance rows', data.bank.length], ['Deposits', data.fd.length], ['Broker cash rows', data.cash.length], ['SIP plan lines', L.sip.length], ['Properties', L.props.length], ['Rent receipts', L.rent.length], ['Insurance policies', L.ins.length]];
    C.table($('c-set'), [{ k: 'a', label: 'Table', fmt: function (r) { return esc(r[0]); } }, { k: 'b', label: 'Rows', align: 'r', fmt: function (r) { return F.num(r[1], 0); } }], cnt, {});
  }

  /* ---------------------------------------------------------- DTAA (sample data, shown as its own page) */
  function pDtaa() {
    $('page').innerHTML = '<div class="card" style="padding:0;overflow:hidden"><iframe class="dtaa-frame" id="dtaa" title="NRI DTAA claim on mutual fund redemption" scrolling="no"></iframe></div>';
    var f = $('dtaa');
    function fit() { try { var d = f.contentDocument; f.style.height = Math.max(d.documentElement.scrollHeight, d.body.scrollHeight) + 'px'; } catch (e) { /* cross-origin is not possible for srcdoc */ } }
    f.onload = function () { fit(); setTimeout(fit, 250); };
    f.srcdoc = window.__DTAA;
    window.__dtaaFit = fit;
  }

  /* ---------------------------------------------------------- shell */
  function tabs() {
    $('tabs').innerHTML = TABS.map(function (t, i) {
      return '<button class="tab" role="tab" aria-selected="' + (i === S.tab) + '" data-i="' + i + '" title="' + t + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[i] + '</svg><span class="t">' + t + '</span><span class="ind"></span></button>';
    }).join('');
    $('tabs').onclick = function (e) { var b = e.target.closest('.tab'); if (!b) return; stopReplay(); S.tab = +b.getAttribute('data-i'); S.anim = true; tabs(); buildSlicers(); render(); window.scrollTo(0, 0); };
  }
  function render() {
    var dtaa = S.tab === TAB_DTAA, ns = !!NOSLICE[S.tab];
    $('slicers').style.display = ns ? 'none' : ''; $('chips').style.display = ns ? 'none' : '';
    if (!ns) { syncSlicers(); chips(); }
    C.hideTip();
    var ls = E.filtered(S.on, S.F);
    $('page').className = S.anim ? 'anim' : '';
    [pOverview, pFunds, pShares, pBank, pProperty, pInsurance, pCalendar, pChecks, pDtaa][S.tab](ls);
    S.anim = false;
    $('h1').textContent = TITLES[S.tab];
    $('eyebrow').textContent = 'YOUR WEALTH, IN PERSPECTIVE';
    $('crumb').textContent = TABS[S.tab];
    $('badge').textContent = /dummy|sample/i.test(data.meta.label) ? 'Sample data' : '';
    $('sub').textContent = dtaa ? SUBS[S.tab] + ' All names, folios and dates on this page are made up.' : SUBS[S.tab] + ' ' + data.meta.label + '. Values in INR.';
    $('asof').textContent = dtaa ? 'Sample page' : 'As on ' + F.dmy(ns ? data.meta.latest : S.on);
    var all = E.lines(S.on);
    $('acct-name').textContent = data.owner || data.meta.label;
    $('acct-pan').textContent = data.pan ? 'PAN ' + data.pan : '';
    var nKeys = Object.keys(all.reduce(function (m, l) { m[l.key] = 1; return m; }, {})).length;
    $('acct-sub').textContent = (nKeys === all.length ? nKeys + ' holdings' : nKeys + ' holdings in ' + all.length + ' account lines') + ' · INR' + (/dummy|sample/i.test(data.meta.label) ? ' · sample data' : '');
    var fx = E.priceOn('USDINR', S.on);
    $('foot').textContent = 'Dataset: ' + data.meta.label + '. Latest price date ' + F.dmy(data.meta.latest) + (fx ? '. USD/INR ' + F.num(fx.p, 4) + ' on ' + F.dmy(fx.date) : '') + '. Page built ' + F.dmy(data.meta.built) + '. Illustrative. Not investment advice.';
  }

  /* ---------------------------------------------------------- export: Excel (.xlsx) and PDF (print) */
  var CRC32 = (function () { var t = [], c, n, k; for (n = 0; n < 256; n++) { c = n; for (k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { var c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC32[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function u8(s) { return new TextEncoder().encode(s); }
  function zipStore(files) {                       // a plain, uncompressed zip: all an .xlsx needs
    var parts = [], cen = [], off = 0;
    function u16(v) { return [v & 255, (v >> 8) & 255]; } function u32(v) { return [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255]; }
    files.forEach(function (f) {
      var nm = u8(f.name), crc = crc32(f.data), sz = f.data.length;
      var lh = [0x50, 0x4b, 3, 4].concat(u16(20), u16(0x0800), u16(0), u16(0), u16(0x21), u32(crc), u32(sz), u32(sz), u16(nm.length), u16(0));
      parts.push(new Uint8Array(lh), nm, f.data); cen.push({ nm: nm, crc: crc, sz: sz, off: off }); off += lh.length + nm.length + sz;
    });
    var cs = off, csz = 0;
    cen.forEach(function (c) {
      var h = [0x50, 0x4b, 1, 2].concat(u16(20), u16(20), u16(0x0800), u16(0), u16(0), u16(0x21), u32(c.crc), u32(c.sz), u32(c.sz), u16(c.nm.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(c.off));
      parts.push(new Uint8Array(h), c.nm); csz += h.length + c.nm.length;
    });
    parts.push(new Uint8Array([0x50, 0x4b, 5, 6].concat(u16(0), u16(0), u16(cen.length), u16(cen.length), u32(csz), u32(cs), u16(0))));
    return new Blob(parts, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }
  function xesc(v) { return String(v).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, ''); }
  function colName(i) { var s = ''; i++; while (i > 0) { var m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; }
  function numOf(t) { var x = t.replace(/[₹▲▼\s]/g, '').replace(/−/g, '-').replace(/^\+/, '').replace(/,/g, ''); return /^-?\d+(\.\d+)?$/.test(x) ? parseFloat(x) : null; }
  function sheetXml(rows) {                        // rows: [{cells:[text], head:bool}]
    var w = [], x = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>';
    rows.forEach(function (r) { r.cells.forEach(function (c, i) { w[i] = Math.min(60, Math.max(w[i] || 8, String(c).length + 2)); }); });
    x += '<cols>' + w.map(function (v, i) { return '<col min="' + (i + 1) + '" max="' + (i + 1) + '" width="' + v + '" customWidth="1"/>'; }).join('') + '</cols><sheetData>';
    rows.forEach(function (r, ri) {
      x += '<row r="' + (ri + 1) + '">';
      r.cells.forEach(function (c, ci) {
        var ref = colName(ci) + (ri + 1), t = String(c), n = r.head ? null : numOf(t);
        if (t === '') return;
        x += n != null ? '<c r="' + ref + '"><v>' + n + '</v></c>' : '<c r="' + ref + '" t="inlineStr"' + (r.head ? ' s="1"' : '') + '><is><t xml:space="preserve">' + xesc(t) + '</t></is></c>';
      });
      x += '</row>';
    });
    return x + '</sheetData></worksheet>';
  }
  function cellText(el) { var c = el.cloneNode(true); c.querySelectorAll('.mark,svg,.sr').forEach(function (n) { n.remove(); }); return c.textContent.replace(/[▴▾]/g, '').replace(/\s+/g, ' ').trim(); }
  function exportXlsx() {
    stopReplay(true);
    var sheets = [], used = {};
    function nameFor(base) { var n = (base || 'Table').replace(/[\[\]:*?\/\\]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 28) || 'Table', k = n, i = 2; while (used[k.toLowerCase()]) { k = n.slice(0, 26) + ' ' + i++; } used[k.toLowerCase()] = 1; return k; }
    var fl = Object.keys(S.F).map(function (f) { var v = S.F[f]; if (f === 'key') v = E.ins[v] ? E.ins[v].name : v; return LABELS[f] + ': ' + v; });
    var sum = [{ cells: ['Hisaab Kitaab'], head: true }, { cells: ['Page', TITLES[S.tab]] }, { cells: ['As on', S.tab === TAB_DTAA ? 'Sample page' : F.dmy(NOSLICE[S.tab] ? data.meta.latest : S.on)] }, { cells: ['Data', data.meta.label] }, { cells: ['Filters', fl.length ? fl.join('; ') : 'None'] }, { cells: [] }];
    var kp = document.querySelectorAll('#page .kpi');
    if (kp.length) sum.push({ cells: ['Key figures'], head: true });
    kp.forEach(function (k) { var l = k.querySelector('.l'), n = k.querySelector('.n'); if (l && n) sum.push({ cells: [cellText(l), cellText(n)] }); });
    sheets.push({ name: nameFor('Summary'), rows: sum });
    document.querySelectorAll('#page table').forEach(function (tb, ti) {
      var rows = [], card = tb.closest('.card'), h = card && card.querySelector('h3'), sh = !h && tb.closest('.holdwrap') ? 'Holdings' : null;
      tb.querySelectorAll('tr').forEach(function (tr) {
        var cells = Array.prototype.map.call(tr.children, cellText);
        if (cells.some(function (c) { return c !== ''; })) rows.push({ cells: cells, head: !!tr.closest('thead') });
      });
      if (tb.classList.contains('heat') && rows.length) rows[0].cells[0] = 'Price change, % (month end to month end)';
      if (rows.length > 1) sheets.push({ name: nameFor(h ? h.textContent : (sh || 'Table ' + (ti + 1))), rows: rows });
    });
    var files = [], N = sheets.length;
    files.push({ name: '[Content_Types].xml', data: u8('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + sheets.map(function (s, i) { return '<Override PartName="/xl/worksheets/sheet' + (i + 1) + '.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'; }).join('') + '</Types>') });
    files.push({ name: '_rels/.rels', data: u8('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>') });
    files.push({ name: 'xl/workbook.xml', data: u8('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + sheets.map(function (s, i) { return '<sheet name="' + xesc(s.name) + '" sheetId="' + (i + 1) + '" r:id="rId' + (i + 1) + '"/>'; }).join('') + '</sheets></workbook>') });
    files.push({ name: 'xl/_rels/workbook.xml.rels', data: u8('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + sheets.map(function (s, i) { return '<Relationship Id="rId' + (i + 1) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet' + (i + 1) + '.xml"/>'; }).join('') + '<Relationship Id="rId' + (N + 1) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>') });
    files.push({ name: 'xl/styles.xml', data: u8('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>') });
    sheets.forEach(function (s, i) { files.push({ name: 'xl/worksheets/sheet' + (i + 1) + '.xml', data: u8(sheetXml(s.rows)) }); });
    var url = URL.createObjectURL(zipStore(files)), a = document.createElement('a');
    a.href = url; a.download = 'HisaabKitaab_' + TABS[S.tab].replace(/\s+/g, '') + '_' + (NOSLICE[S.tab] ? data.meta.latest : S.on) + '.xlsx';
    document.body.appendChild(a); a.click(); document.body.removeChild(a); setTimeout(function () { URL.revokeObjectURL(url); }, 800);
  }
  function exportPdf() {
    stopReplay(true);
    var t0 = document.title; document.title = 'Hisaab Kitaab - ' + TABS[S.tab] + ' - ' + (NOSLICE[S.tab] ? data.meta.latest : S.on);
    $('page').className = ''; window.print(); document.title = t0;
  }
  var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { if (S.tab === TAB_DTAA && window.__dtaaFit) window.__dtaaFit(); else render(); }, 150); });
  $('export').onclick = exportXlsx; $('exportpdf').onclick = exportPdf;
  (function () {
    var nm = 'Hisaab Kitaab', ini = 'H';
    document.title = nm; $('brand-name').textContent = nm; $('brand-mark').firstChild.nodeValue = ini; $('brand').setAttribute('aria-label', nm);
  })();
  function setTheme(t, save) {
    document.documentElement.setAttribute('data-theme', t);
    $('theme').setAttribute('aria-pressed', String(t === 'dark')); $('theme-t').textContent = t === 'dark' ? 'Light mode' : 'Dark mode';
    if (save) { try { localStorage.setItem('hk-theme', t); } catch (e) { } }
  }
  var th0 = 'light'; try { th0 = localStorage.getItem('hk-theme') === 'dark' ? 'dark' : 'light'; } catch (e) { }
  setTheme(th0, false);
  $('theme').onclick = function () { setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark', true); render(); };
  tabs(); buildSlicers(); render();
  window.__dash = { E: E, S: S, render: render };      // used by the tests
})();
