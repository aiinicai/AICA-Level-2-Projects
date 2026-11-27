/* Dashboard engine. Pure calculation, no screen code, so it runs in the browser and in Node (tests).
 *
 * Rules (same as app/portfolio.py, which the tests use as the independent check):
 *   Holdings on a date = OPENING + BUY + SIP up to the date, less SELL.
 *   Average cost       = total cost / total units. A SELL removes units at the average cost.
 *   Value on a date    = units on that date x latest price on or before that date.
 *   Deposit value      = principal + simple interest to the date; stops growing at maturity.
 *   Foreign currency   = amount x USDINR on or before the date.
 */
(function (root) {
  'use strict';
  var DAY = 86400000;
  function dn(s) { return Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / DAY; }
  var CLASSES = ['Mutual funds', 'Equity shares', 'Bank balances', 'Term deposits'];

  function Engine(data) {
    var self = this;
    this.data = data;
    this.CLASSES = CLASSES;
    this.ins = {};
    data.instruments.forEach(function (i) { self.ins[i.key] = i; });
    this.prices = {};
    var tmp = {};
    data.prices.forEach(function (r) { (tmp[r.key] = tmp[r.key] || []).push([dn(r.date), +r.price, r.date]); });
    Object.keys(tmp).forEach(function (k) { tmp[k].sort(function (a, b) { return a[0] - b[0]; }); self.prices[k] = tmp[k]; });
    this.latest = data.prices.reduce(function (m, r) { return r.date > m ? r.date : m; }, '0000-00-00');
    this.tx = data.tx.map(function (t) {
      return { date: t.date, n: dn(t.date), account: t.account, key: t.key, action: t.action, qty: +t.qty, price: +t.price };
    });
    this.tx.sort(function (a, b) { return a.n - b.n; });          // stable: file order kept inside a day
    this.series = {};                                              // "account|key" -> events with running units and cost
    this.tx.forEach(function (t) {
      var id = t.account + '|' + t.key, s = (self.series[id] = self.series[id] || { account: t.account, key: t.key, ev: [] });
      var last = s.ev.length ? s.ev[s.ev.length - 1] : { units: 0, cost: 0 }, units = last.units, cost = last.cost;
      if (t.action === 'SELL') { var avg = units ? cost / units : 0; cost -= t.qty * avg; units -= t.qty; }
      else { cost += t.qty * t.price; units += t.qty; }
      s.ev.push({ date: t.date, n: t.n, action: t.action, qty: t.qty, price: t.price, units: units, cost: cost, avg: units > 1e-9 ? cost / units : 0 });
    });
    this.bank = data.bank.map(function (r) { return Object.assign({}, r, { n: dn(r.as_of), balance: +r.balance }); });
    this.cash = data.cash.map(function (r) { return Object.assign({}, r, { n: dn(r.as_of), cash: +r.cash }); });
    this.fd = data.fd.map(function (r) {
      return Object.assign({}, r, { sn: dn(r.start), mn: dn(r.maturity), rate: +r.rate_pct,
        principal: r.principal === '' || r.principal == null ? null : +r.principal, current_value: +r.current_value });
    });
  }

  Engine.prototype.priceOn = function (key, on) {
    var a = this.prices[key]; if (!a) return null;
    var n = dn(on), lo = 0, hi = a.length - 1, best = -1;
    while (lo <= hi) { var m = (lo + hi) >> 1; if (a[m][0] <= n) { best = m; lo = m + 1; } else hi = m - 1; }
    return best < 0 ? null : { p: a[best][1], date: a[best][2] };
  };
  Engine.prototype.fxOn = function (ccy, on) {
    if (ccy === 'INR') return 1;
    var r = this.priceOn(ccy + 'INR', on); return r ? r.p : null;
  };
  Engine.prototype.state = function (id, on) {          // running units/cost of one holding on a date
    var s = this.series[id]; if (!s) return null;
    var n = dn(on), last = null;
    for (var i = 0; i < s.ev.length; i++) { if (s.ev[i].n <= n) last = s.ev[i]; else break; }
    return last;
  };

  /* Every holding on a date, in INR. */
  Engine.prototype.lines = function (on) {
    var self = this, res = [], n = dn(on);
    Object.keys(this.series).sort().forEach(function (id) {
      var s = self.series[id], st = self.state(id, on);
      if (!st || st.units <= 1e-9) return;
      var ins = self.ins[s.key], pr = self.priceOn(s.key, on), mf = ins.kind === 'MF';
      res.push({ cls: mf ? 'Mutual funds' : 'Equity shares', account: s.account, key: s.key, name: ins.name,
        fh: mf ? ins.house : null, sector: mf ? null : ins.group, category: mf ? ins.group : null, ccy: 'INR', fx: 1,
        qty: st.units, avg: st.avg, cost: st.cost, price: pr ? pr.p : null, pdate: pr ? pr.date : null,
        value: pr ? st.units * pr.p : 0, bank: null });
    });
    var seen = {};
    this.bank.forEach(function (r) {
      if (r.n <= n) { var k = r.bank + '|' + r.account_last4; if (!seen[k] || r.n >= seen[k].n) seen[k] = r; }
    });
    Object.keys(seen).sort().forEach(function (k) {
      var r = seen[k], fx = self.fxOn(r.currency, on), nm = r.bank + ' ' + r.kind + ' XX' + r.account_last4;
      res.push({ cls: 'Bank balances', account: nm, key: r.bank + '|' + r.account_last4, name: nm, fh: null, sector: null,
        category: null, ccy: r.currency, fx: fx, local: r.balance, cost: r.balance * fx, value: r.balance * fx,
        pdate: r.as_of, bank: r.bank, kind: r.kind });
    });
    seen = {};
    this.cash.forEach(function (r) {
      if (r.n <= n) { var k = r.broker + '|' + r.account; if (!seen[k] || r.n >= seen[k].n) seen[k] = r; }
    });
    Object.keys(seen).sort().forEach(function (k) {
      var r = seen[k], nm = r.broker + ' cash ' + r.account;
      res.push({ cls: 'Bank balances', account: 'Demat ' + r.account, key: r.broker + '|' + r.account, name: nm, fh: null,
        sector: null, category: null, ccy: 'INR', fx: 1, local: r.cash, cost: r.cash, value: r.cash, pdate: r.as_of,
        bank: r.broker, kind: 'Broker cash' });
    });
    this.fd.forEach(function (r) {
      if (r.sn > n) return;
      var fx = self.fxOn(r.currency, on), end = Math.min(n, r.mn), local, costLocal;
      if (r.principal != null) { local = r.principal * (1 + r.rate / 100 * (end - r.sn) / 365); costLocal = r.principal; }
      else { local = r.current_value; costLocal = r.current_value; }
      var nm = r.bank + ' ' + r.kind + ' XX' + r.account_last4;
      res.push({ cls: 'Term deposits', account: nm, key: r.bank + '|' + r.account_last4 + '|FD', name: nm, fh: null,
        sector: null, category: null, ccy: r.currency, fx: fx, local: local, principal: costLocal, cost: costLocal * fx,
        value: local * fx, bank: r.bank, kind: r.kind, start: r.start, maturity: r.maturity, rate: r.rate,
        matured: r.mn <= n, daysLeft: r.mn - n });
    });
    res.forEach(function (l) { l.atype = atypeOf(l); l.bank = bankOf(l); });
    return res;
  };
  /* Where the money is held: the account type as the statements state it. Funds sit in folios and shares in demat accounts. */
  function bankOf(l) { var m = /^(.*?)\s+(NRE|NRO|FCNR|Foreign currency)\b/.exec(l.account || ''); return m ? m[1] : null; }
  function atypeOf(l) {
    if (l.cls === 'Mutual funds') return 'Fund folios';
    if (l.cls === 'Equity shares') return 'Demat shares';
    var k = String(l.kind || '');
    if (k === 'Broker cash') return 'Broker cash';
    if (/^NRE/i.test(k)) return 'NRE bank and FD';
    if (/^NRO/i.test(k)) return 'NRO bank and FD';
    if (/^FCNR/i.test(k)) return 'FCNR deposits';
    if (/^Foreign currency/i.test(k)) return 'Foreign currency account';
    return k || 'Other';
  }

  /* Slicer rule: a line passes only if it carries the attribute that was chosen and the value matches. */
  var FIELDS = ['account', 'bank', 'fh', 'sector', 'category', 'ccy', 'cls', 'key', 'atype'];
  Engine.prototype.match = function (x, F) {
    for (var i = 0; i < FIELDS.length; i++) { var f = FIELDS[i]; if (F[f] && x[f] !== F[f]) return false; }
    return true;
  };
  Engine.prototype.filtered = function (on, F) { var self = this; return this.lines(on).filter(function (x) { return self.match(x, F || {}); }); };

  Engine.prototype.sum = function (ls) {
    var v = 0, c = 0; ls.forEach(function (x) { v += x.value; c += x.cost; });
    return { value: v, cost: c, gain: v - c, pct: c ? (v - c) / c : null };
  };
  Engine.prototype.byClass = function (ls) {
    var o = {}; CLASSES.forEach(function (c) { o[c] = { value: 0, cost: 0 }; });
    ls.forEach(function (x) { o[x.cls].value += x.value; o[x.cls].cost += x.cost; });
    return o;
  };

  /* Month-end dates up to and including `on` (plus `on` itself when it is not a month end). */
  Engine.prototype.timeline = function (on) {
    var s = {}; this.data.prices.forEach(function (r) { s[r.date] = 1; });
    var ds = Object.keys(s).filter(function (d) { return d <= on; }).sort();
    // keep month ends only: last price date of each month, plus the chosen date
    var byM = {}; ds.forEach(function (d) { byM[d.slice(0, 7)] = d; });
    var out = Object.keys(byM).sort().map(function (m) { return byM[m]; });
    if (out.indexOf(on) < 0) out.push(on);
    return out;
  };
  Engine.prototype.timeSeries = function (on, F) {
    var self = this, G = Object.assign({}, F);
    return this.timeline(on).map(function (d) { var s = self.sum(self.filtered(d, G)); return { date: d, value: s.value, cost: s.cost }; });
  };

  /* Cash flows of the chosen funds/shares; opening units count as bought on the opening date at that day's price. */
  Engine.prototype.flows = function (on, kind, F) {
    var self = this, n = dn(on), flows = [], end = 0, pairs = {};
    this.tx.forEach(function (t) {
      var ins = self.ins[t.key]; if (ins.kind !== kind) return;
      var probe = { account: t.account, key: t.key, fh: kind === 'MF' ? ins.house : null, sector: kind === 'MF' ? null : ins.group,
        category: kind === 'MF' ? ins.group : null, ccy: 'INR', cls: kind === 'MF' ? 'Mutual funds' : 'Equity shares' };
      if (self.match(probe, F)) pairs[t.account + '|' + t.key] = 1;
    });
    this.tx.forEach(function (t) {
      if (!pairs[t.account + '|' + t.key] || t.n > n) return;
      if (t.action === 'OPENING') { var p = self.priceOn(t.key, t.date); flows.push([t.n, -t.qty * p.p]); }
      else if (t.action === 'SELL') flows.push([t.n, t.qty * t.price]);
      else flows.push([t.n, -t.qty * t.price]);
    });
    Object.keys(pairs).forEach(function (id) {
      var st = self.state(id, on);
      if (st && st.units > 1e-9) end += st.units * self.priceOn(self.series[id].key, on).p;
    });
    if (end) flows.push([n, end]);
    return flows;
  };
  Engine.prototype.xirr = function (flows) {
    if (!flows.length) return null;
    var hasNeg = flows.some(function (f) { return f[1] < 0; }), hasPos = flows.some(function (f) { return f[1] > 0; });
    if (!hasNeg || !hasPos) return null;
    var t0 = Math.min.apply(null, flows.map(function (f) { return f[0]; }));
    function npv(r) { return flows.reduce(function (s, f) { return s + f[1] / Math.pow(1 + r, (f[0] - t0) / 365); }, 0); }
    var lo = -0.99, hi = 10, flo = npv(lo), fhi = npv(hi);
    if (flo * fhi > 0) return null;
    for (var i = 0; i < 200; i++) {
      var mid = (lo + hi) / 2, fm = npv(mid);
      if (flo * fm <= 0) { hi = mid; fhi = fm; } else { lo = mid; flo = fm; }
    }
    return (lo + hi) / 2;
  };
  /* XIRR is shown only when the opening date is at least 180 days before the chosen date. */
  Engine.prototype.xirrFor = function (on, F) {
    var open = this.openDate(); if (!open || dn(on) - dn(open) < 180) return null;
    return this.xirr(this.flows(on, 'MF', F));
  };
  Engine.prototype.openDate = function () {
    var o = this.tx.filter(function (t) { return t.action === 'OPENING'; }); return o.length ? o[0].date : null;
  };

  /* SIP total: money put in through SIP transactions during the calendar month of `on`, up to `on`. */
  Engine.prototype.sipMonth = function (on, F) {
    var self = this, tot = 0, ym = on.slice(0, 7);
    this.tx.forEach(function (t) {
      if (t.action !== 'SIP' || t.date.slice(0, 7) !== ym || t.date > on) return;
      var ins = self.ins[t.key];
      if (self.match({ account: t.account, key: t.key, fh: ins.house, sector: null, category: ins.group, ccy: 'INR', cls: 'Mutual funds' }, F)) tot += t.qty * t.price;
    });
    return tot;
  };
  /* Buys of shares by month up to `on` (OPENING is not a buy). */
  Engine.prototype.buysByMonth = function (on, F, kind) {
    var self = this, o = {};
    this.tx.forEach(function (t) {
      if ((t.action !== 'BUY' && t.action !== 'SIP') || t.date > on) return;
      var ins = self.ins[t.key]; if (ins.kind !== kind) return;
      var mf = kind === 'MF';
      if (self.match({ account: t.account, key: t.key, fh: mf ? ins.house : null, sector: mf ? null : ins.group,
        category: mf ? ins.group : null, ccy: 'INR', cls: mf ? 'Mutual funds' : 'Equity shares' }, F)) {
        var m = t.date.slice(0, 7); o[m] = (o[m] || 0) + t.qty * t.price;
      }
    });
    return o;
  };
  /* Units and average cost after each transaction of one holding. */
  Engine.prototype.ledger = function (account, key, on) {
    var s = this.series[account + '|' + key]; if (!s) return [];
    var n = dn(on); return s.ev.filter(function (e) { return e.n <= n; });
  };

  /* Needs attention list for the chosen date. */
  Engine.prototype.attention = function (on, F) {
    var ls = this.filtered(on, F), out = [];
    ls.filter(function (x) { return x.cls === 'Term deposits' && !x.matured && x.daysLeft <= 90; })
      .sort(function (a, b) { return a.daysLeft - b.daysLeft; })
      .forEach(function (x) { out.push({ kind: 'warn', text: x.name + ' matures ' + x.maturity + ' (' + x.daysLeft + ' days)', key: x.key }); });
    ls.filter(function (x) { return x.matured; }).forEach(function (x) { out.push({ kind: 'bad', text: x.name + ' matured ' + x.maturity + '. Confirm credit or renewal.', key: x.key }); });
    ls.filter(function (x) { return (x.cls === 'Equity shares' || x.cls === 'Mutual funds') && x.cost > 0 && (x.value - x.cost) / x.cost < -0.10; })
      .sort(function (a, b) { return (a.value - a.cost) / a.cost - (b.value - b.cost) / b.cost; })
      .forEach(function (x) { out.push({ kind: 'bad', text: x.name + ' is down ' + (100 * (x.cost - x.value) / x.cost).toFixed(1) + '% on cost', key: x.key }); });
    ls.filter(function (x) { return x.cls === 'Bank balances' && x.value < 0; }).forEach(function (x) { out.push({ kind: 'bad', text: x.name + ' is overdrawn', key: x.key }); });
    return out;
  };

  Engine.CLASSES = CLASSES;
  Engine.dn = dn;
  if (typeof module !== 'undefined' && module.exports) module.exports = Engine; else root.Engine = Engine;
})(typeof window !== 'undefined' ? window : this);
