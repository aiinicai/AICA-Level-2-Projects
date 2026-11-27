/* Property, rent, insurance and the calendar of cash commitments. Pure calculation, no screen code, so it runs in the
 * browser and in Node (tests). Same rules as app/life.py, which the tests use as the independent check.
 *
 * None of this is added to the consolidated total. Insurance cover is not an asset, and the house has its own page.
 *
 *   Window       = the 12 months after the latest data date.
 *   SIP          = every SIP plan line, on its day of the month.
 *   Premium      = each policy on its due day, in every year from its first year to its last year.
 *                  A policy with no first and last year (medical) runs every year.
 *   House tax and maintenance = each property on its due day (month-day), every year.
 *   Rent and deposit maturities are money coming in, so they are not commitments.
 */
(function (root) {
  'use strict';
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(y, m, d) { return y + '-' + pad(m) + '-' + pad(d); }
  function dim(y, m) { return new Date(Date.UTC(y, m, 0)).getUTCDate(); }            // m is 1 to 12
  function addMonths(s, n) {
    var y = +s.slice(0, 4), m = +s.slice(5, 7) - 1 + n, d = +s.slice(8, 10);
    y += Math.floor(m / 12); m = ((m % 12) + 12) % 12 + 1;
    return iso(y, m, Math.min(d, dim(y, m)));
  }
  function days(a, b) { return Math.round((Date.UTC(+b.slice(0, 4), +b.slice(5, 7) - 1, +b.slice(8, 10)) - Date.UTC(+a.slice(0, 4), +a.slice(5, 7) - 1, +a.slice(8, 10))) / 86400000); }
  function num(s) { return s === '' || s == null ? null : +s; }

  function Life(data) {
    var self = this;
    this.latest = data.meta.latest;
    this.owner = data.owner || '';
    this.birth = data.birth || '';
    var names = {};
    data.instruments.forEach(function (i) { names[i.key] = i.name.replace(' - Direct Growth', ''); });
    this.sip = (data.sip || []).map(function (s) { return { key: s.key, name: names[s.key] || s.key, folio: s.folio, amount: +s.amount, day: +s.day }; });
    this.props = (data.props || []).map(function (p) {
      return { id: p.id, name: p.name, city: p.city, tenant: p.tenant, rent: +p.rent_monthly, rentDay: +p.rent_day, leaseStart: p.lease_start, leaseEnd: p.lease_end,
        tax: +p.tax_yearly, taxMd: p.tax_due, taxPaid: p.tax_last_paid || '', cost: num(p.cost), costDate: p.cost_date, value: num(p.value), valueDate: p.value_date, account: p.rent_account };
    });
    this.rent = (data.rent || []).map(function (r) { return { date: r.date, property: r.property, amount: +r.amount }; });
    this.ins = (data.ins || []).map(function (p) {
      return { id: p.id, name: p.name, type: p.type, cover: num(p.cover), coverNote: p.cover_note, premium: +p.premium, first: num(p.first_year), last: num(p.last_year),
        month: +p.due_month, day: +p.due_day, payout: num(p.payout_monthly), payoutDay: num(p.payout_day), payoutStart: p.payout_start, payoutEnd: p.payout_end };
    });
    this.sipTotal = this.sip.reduce(function (s, x) { return s + x.amount; }, 0);
    this.has = this.sip.length + this.props.length + this.ins.length > 0;
    this.hasIns = this.ins.length > 0;
    this.hasProps = this.props.length > 0;
    void self;
  }

  /* premium due dates after lo and on or before hi */
  Life.prototype.premiumDates = function (p, lo, hi) {
    var out = [];
    for (var y = +lo.slice(0, 4); y <= +hi.slice(0, 4); y++) {
      if ((p.first != null && y < p.first) || (p.last != null && y > p.last)) continue;
      var dt = iso(y, p.month, p.day);
      if (dt > lo && dt <= hi) out.push(dt);
    }
    return out;
  };
  Life.prototype.paid = function (p, on) { return p.first == null ? null : this.premiumDates(p, iso(p.first - 1, 12, 31), on).length; };
  Life.prototype.total = function (p) { return p.first == null || p.last == null ? null : p.last - p.first + 1; };
  Life.prototype.nextDue = function (p, on) { var d = this.premiumDates(p, on, addMonths(on, 12 * 3)); return d.length ? d[0] : null; };
  /* premiums due in the calendar year of `on` */
  Life.prototype.yearPremiums = function (on) {
    var y = +on.slice(0, 4), self = this, t = 0;
    this.ins.forEach(function (p) { t += self.premiumDates(p, iso(y - 1, 12, 31), iso(y, 12, 31)).length * p.premium; });
    return t;
  };
  Life.prototype.taxDates = function (p, lo, hi) {
    var mm = +p.taxMd.slice(0, 2), dd = +p.taxMd.slice(3, 5), out = [];
    for (var y = +lo.slice(0, 4); y <= +hi.slice(0, 4); y++) { var dt = iso(y, mm, dd); if (dt > lo && dt <= hi) out.push(dt); }
    return out;
  };

  /* cash commitments in the `months` months after `from`. Rows: {date, kind, label, amount}, sorted. */
  Life.prototype.calendar = function (from, months) {
    from = from || this.latest; months = months || 12;
    var hi = addMonths(from, months), ev = [], self = this, y = +from.slice(0, 4), m = +from.slice(5, 7);
    for (var i = 0; i < months + 2; i++) {
      this.sip.forEach(function (s) { var dt = iso(y, m, Math.min(s.day, dim(y, m))); if (dt > from && dt <= hi) ev.push({ date: dt, kind: 'SIP', label: s.name, amount: s.amount }); });
      m++; if (m > 12) { m = 1; y++; }
    }
    this.ins.forEach(function (p) { self.premiumDates(p, from, hi).forEach(function (dt) { ev.push({ date: dt, kind: 'Insurance', label: p.name, amount: p.premium }); }); });
    this.props.forEach(function (p) { self.taxDates(p, from, hi).forEach(function (dt) { ev.push({ date: dt, kind: 'House tax and maintenance', label: p.name + ', ' + p.city, amount: p.tax }); }); });
    ev.sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : a.kind < b.kind ? -1 : a.kind > b.kind ? 1 : a.label < b.label ? -1 : a.label > b.label ? 1 : 0; });
    return ev;
  };

  /* retirement income: number of payments between two dates, counting one on the same day of each month */
  Life.prototype.payments = function (p) {
    if (!p.payout) return 0;
    return (+p.payoutEnd.slice(0, 4) - +p.payoutStart.slice(0, 4)) * 12 + (+p.payoutEnd.slice(5, 7) - +p.payoutStart.slice(5, 7)) + 1;
  };
  Life.prototype.rentOf = function (id) { return this.rent.filter(function (r) { return r.property === id; }); };

  Life.addMonths = addMonths; Life.days = days; Life.iso = iso;
  if (typeof module !== 'undefined' && module.exports) module.exports = Life; else root.Life = Life;
})(typeof window !== 'undefined' ? window : this);
