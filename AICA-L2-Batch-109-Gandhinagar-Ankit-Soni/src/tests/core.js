var BCG = (function () {
  'use strict';

  /* ---------------------------------------------------------------- utils */
  var MONTHS = ['January','February','March','April','May','June','July',
                'August','September','October','November','December'];
  var BAD_TOKENS = /^(undefined|null|nan|nil|n\/a|na|-|--|#n\/a|#value!|#ref!|\[object object\])$/i;

  function clean(v) {
    if (v === null || v === undefined) return '';
    if (v instanceof Date) return isNaN(v.getTime()) ? '' : fmtDateLong(v);
    if (typeof v === 'number') return isFinite(v) ? String(v) : '';
    var s = String(v).replace(/\u00a0/g, ' ').trim().replace(/\s+/g, ' ');
    if (BAD_TOKENS.test(s)) return '';
    return s;
  }

  function toDate(v) {
    if (!v) return null;
    if (v instanceof Date) return isNaN(v.getTime()) ? null : v;
    var s = String(v).trim();
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
    if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function fmtDateLong(v) {
    var d = toDate(v);
    if (!d) return '';
    return d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear();
  }

  function isoDate(v) {
    var d = toDate(v);
    if (!d) return '';
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  var EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;
  function validEmail(s) { return EMAIL_RE.test(String(s || '').trim()); }

  /* Header text normalisation: case, punctuation, spacing, abbreviations. */
  var ABBR = {
    'amt': 'amount', 'bal': 'balance', 'addr': 'address', 'ccy': 'currency',
    'curr': 'currency', 'cur': 'currency', 'a/c': 'account', 'acc': 'account',
    'acct': 'account', 'nm': 'name', 'pty': 'party', 'cust': 'customer',
    'vend': 'vendor', 'supp': 'supplier', 'o/s': 'outstanding', 'os': 'outstanding',
    'adv': 'advance', 'mob': 'mobile', 'ph': 'phone', 'no': 'number', 'nos': 'number',
    'sr': 'serial', 'srno': 'serial number', 'desc': 'description', 'partic': 'particulars'
  };
  function normHeader(s) {
    var t = String(s === null || s === undefined ? '' : s).toLowerCase();
    t = t.replace(/\u00a0/g, ' ').replace(/[_\-.]/g, ' ').replace(/[^a-z0-9/ ]/g, ' ');
    t = t.replace(/\s+/g, ' ').trim();
    t = t.split(' ').map(function (w) { return ABBR[w] || w; }).join(' ');
    t = t.replace(/\be mail\b/g, 'email').replace(/\s+/g, ' ').trim();
    return t;
  }

  function isNumericLike(s) {
    var t = String(s).replace(/[\s,]/g, '').replace(/[₹$€£¥]/g, '');
    return t !== '' && /^-?\(?\d*\.?\d+\)?$/.test(t);
  }

  /* ------------------------------------------------------- header detection */
  var HEADER_TERMS = ['party', 'name', 'address', 'amount', 'balance', 'currency',
    'category', 'type', 'email', 'contact', 'vendor', 'customer', 'supplier',
    'debtor', 'creditor', 'outstanding', 'receivable', 'payable', 'advance',
    'nature', 'classification', 'particulars', 'account', 'city', 'state',
    'pincode', 'gstin', 'code', 'serial', 'phone', 'mobile'];

  function scoreHeaderRow(row) {
    var cells = (row || []).map(clean).filter(function (c) { return c !== ''; });
    if (cells.length < 2) return -Infinity;
    var uniq = {}, numeric = 0, kw = 0, longs = 0;
    cells.forEach(function (c) {
      uniq[c.toLowerCase()] = 1;
      if (isNumericLike(c)) numeric++;
      if (c.length > 45) longs++;
      var n = normHeader(c);
      for (var i = 0; i < HEADER_TERMS.length; i++) {
        if (n.indexOf(HEADER_TERMS[i]) >= 0) { kw++; break; }
      }
    });
    var score = cells.length + Object.keys(uniq).length * 0.6 + kw * 4.5;
    score -= numeric * 3.5 + longs * 2.5;
    return score;
  }

  /* Returns {index, confidence:'high'|'low', keywordHits, scores[]} */
  function detectHeaderRow(grid) {
    var limit = Math.min(grid.length, 20), best = -1, bestScore = -Infinity, second = -Infinity;
    var scores = [];
    for (var r = 0; r < limit; r++) {
      var hasBelow = false;
      for (var k = r + 1; k < grid.length; k++) {
        if ((grid[k] || []).some(function (c) { return clean(c) !== ''; })) { hasBelow = true; break; }
      }
      var s = hasBelow ? scoreHeaderRow(grid[r]) - r * 0.35 : -Infinity;
      scores.push(s);
      if (s > bestScore) { second = bestScore; bestScore = s; best = r; }
      else if (s > second) { second = s; }
    }
    if (best < 0) return { index: 0, confidence: 'low', keywordHits: 0, scores: scores };
    var hits = 0;
    (grid[best] || []).map(clean).forEach(function (c) {
      if (!c) return;
      var n = normHeader(c);
      for (var i = 0; i < HEADER_TERMS.length; i++) { if (n.indexOf(HEADER_TERMS[i]) >= 0) { hits++; break; } }
    });
    var conf = (hits >= 2 && bestScore >= second + 3) ? 'high' : 'low';
    return { index: best, confidence: conf, keywordHits: hits, scores: scores };
  }

  /* Build header labels, data rows and column descriptors. */
  function buildColumns(grid, headerIndex) {
    var headerRow = grid[headerIndex] || [];
    var width = 0;
    grid.forEach(function (r) { if (r && r.length > width) width = r.length; });
    var headers = [];
    for (var i = 0; i < width; i++) headers.push(clean(headerRow[i]));
    var dataRows = grid.slice(headerIndex + 1).filter(function (r) {
      return (r || []).some(function (c) { return clean(c) !== ''; });
    });
    var seen = {}, columns = [];
    for (var c = 0; c < width; c++) {
      var vals = dataRows.map(function (r) { return clean((r || [])[c]); });
      var nonEmpty = vals.filter(function (v) { return v !== ''; });
      if (headers[c] === '' && nonEmpty.length === 0) continue;   /* blank column */
      var label = headers[c] || ('Column ' + colLetter(c));
      if (seen[label.toLowerCase()]) { seen[label.toLowerCase()]++; label = label + ' (' + seen[label.toLowerCase()] + ')'; }
      else { seen[label.toLowerCase()] = 1; }
      columns.push({ index: c, header: headers[c], label: label, values: vals, filled: nonEmpty.length });
    }
    return { headers: headers, dataRows: dataRows, columns: columns };
  }

  function colLetter(n) {
    var s = '';
    n = n + 1;
    while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - m) / 26); }
    return s;
  }

  /* --------------------------------------------------------- column mapping */
  var FIELD_DEFS = {
    partyName: {
      label: 'Party / Name', required: true, multi: false,
      exact: ['party name', 'name of party', 'name of the party', 'party', 'name', 'customer name',
        'vendor name', 'supplier name', 'account name', 'counterparty', 'counter party', 'legal name',
        'customer', 'vendor', 'supplier', 'debtor name', 'creditor name', 'party account', 'account'],
      contains: ['party', 'counterparty', 'legal name', 'account name', 'customer', 'vendor',
        'supplier', 'debtor', 'creditor', 'name'],
      penalty: ['contact', 'email', 'bank', 'file', 'user', 'city', 'state', 'employee', 'signatory']
    },
    address: {
      label: 'Address', required: false, multi: true,
      exact: ['address', 'address 1', 'address 2', 'address 3', 'address line 1', 'address line 2',
        'billing address', 'mailing address', 'registered address', 'location', 'city', 'state',
        'pincode', 'pin code', 'postal code', 'zip', 'country'],
      contains: ['address', 'location', 'city', 'state', 'pincode', 'postal', 'zip', 'country'],
      penalty: ['email', 'website', 'ip']
    },
    amount: {
      label: 'Amount / Balance', required: false, multi: false,
      exact: ['amount', 'balance', 'outstanding', 'closing balance', 'balance amount', 'receivable',
        'payable', 'advance', 'outstanding amount', 'closing bal', 'amount outstanding',
        'balance as per books', 'net balance', 'value'],
      contains: ['amount', 'balance', 'outstanding', 'receivable', 'payable', 'advance', 'value', 'debit', 'credit'],
      penalty: ['number', 'gstin', 'pan', 'invoice number', 'code', 'serial', 'phone', 'mobile', 'days']
    },
    currency: {
      label: 'Currency', required: false, multi: false,
      exact: ['currency', 'currency code', 'ccy'], contains: ['currency', 'ccy'], penalty: []
    },
    category: {
      label: 'Category', required: false, multi: false,
      exact: ['category', 'type', 'account type', 'nature', 'balance type', 'classification',
        'nature of balance', 'head', 'group'],
      contains: ['category', 'type', 'nature', 'classification', 'balance type', 'group', 'head'],
      penalty: ['gst', 'tax type', 'document type', 'file type']
    },
    email: {
      label: 'Email', required: false, multi: false,
      exact: ['email', 'email id', 'email address', 'mail id', 'contact email'],
      contains: ['email', 'mail id'], penalty: []
    },
    contactPerson: {
      label: 'Contact person', required: false, multi: false,
      exact: ['contact', 'contact person', 'contact name', 'attention', 'kind attention', 'attn', 'concerned person'],
      contains: ['contact person', 'contact name', 'attention', 'contact'], penalty: ['email', 'number', 'phone', 'mobile']
    }
  };
  var FIELD_ORDER = ['partyName', 'amount', 'category', 'currency', 'email', 'contactPerson', 'address'];

  var ISO_CCY = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'SAR', 'ZAR', 'NZD', 'SEK', 'THB', 'MYR', 'LKR', 'BDT', 'NPR'];

  /* Whole-word prefix / suffix test — "address 1" matches "address line 1",
     but "serial number" must not match anything merely by length.            */
  function edgeWordMatch(n, t) {
    if (!t || t.length > n.length) return false;
    if (n.slice(0, t.length) === t && (n.length === t.length || n.charAt(t.length) === ' ')) return true;
    var at = n.length - t.length;
    return n.slice(at) === t && (at === 0 || n.charAt(at - 1) === ' ');
  }

  function headerScore(def, header) {
    var n = normHeader(header);
    if (!n) return 0;
    var s = 0, i;
    for (i = 0; i < def.exact.length; i++) { if (n === def.exact[i]) { s = 100; break; } }
    if (!s) for (i = 0; i < def.exact.length; i++) {
      if (edgeWordMatch(n, def.exact[i])) { s = Math.max(s, 78); }
    }
    if (s < 78) for (i = 0; i < def.contains.length; i++) {
      if (n.indexOf(def.contains[i]) >= 0) s = Math.max(s, 55 + Math.min(def.contains[i].length, 14));
    }
    for (i = 0; i < def.penalty.length; i++) { if (n.indexOf(def.penalty[i]) >= 0) s -= 45; }
    return s;
  }

  function valueScore(field, values) {
    var nz = values.filter(function (v) { return v !== ''; });
    if (!nz.length) return 0;
    var hit = 0, i;
    if (field === 'email') {
      for (i = 0; i < nz.length; i++) if (validEmail(nz[i])) hit++;
      return hit / nz.length > 0.5 ? 85 : 0;
    }
    if (field === 'currency') {
      for (i = 0; i < nz.length; i++) if (ISO_CCY.indexOf(nz[i].toUpperCase()) >= 0) hit++;
      return hit / nz.length > 0.6 ? 85 : 0;
    }
    if (field === 'category') {
      for (i = 0; i < nz.length; i++) if (normalizeCategory(nz[i])) hit++;
      return hit / nz.length > 0.5 ? 85 : 0;
    }
    if (field === 'amount') {
      for (i = 0; i < nz.length; i++) if (parseAmount(nz[i]).value !== null) hit++;
      return hit / nz.length > 0.75 ? 45 : 0;
    }
    if (field === 'partyName') {
      var uniq = {}, texty = 0, len = 0;
      for (i = 0; i < nz.length; i++) {
        uniq[nz[i].toLowerCase()] = 1; len += nz[i].length;
        if (!isNumericLike(nz[i]) && /[A-Za-z]/.test(nz[i])) texty++;
      }
      var u = Object.keys(uniq).length / nz.length;
      return (texty / nz.length > 0.85 && u > 0.6 && len / nz.length > 4) ? 25 : 0;
    }
    return 0;
  }

  /* Greedy, conflict-free assignment. Returns per-field mapping objects. */
  function detectMapping(columns) {
    var cand = [];
    FIELD_ORDER.forEach(function (f) {
      var def = FIELD_DEFS[f];
      columns.forEach(function (col) {
        var hs = headerScore(def, col.header);
        var vs = valueScore(f, col.values);
        var total = hs + (hs > 0 ? vs * 0.6 : vs);
        if (total > 20) cand.push({ field: f, col: col.index, score: Math.round(total), header: col.label });
      });
    });
    cand.sort(function (a, b) { return b.score - a.score; });

    var map = {}, usedCols = {};
    FIELD_ORDER.forEach(function (f) {
      map[f] = { field: f, label: FIELD_DEFS[f].label, cols: [], status: 'missing', score: 0, candidates: [] };
    });
    cand.forEach(function (c) { map[c.field].candidates.push(c); });

    cand.forEach(function (c) {
      var m = map[c.field];
      if (FIELD_DEFS[c.field].multi) {
        if (usedCols[c.col]) return;
        if (m.cols.length >= 4) return;
        /* extra address columns need a solid header match, never a weak one */
        if (m.cols.length && c.score < 70) return;
        usedCols[c.col] = c.field; m.cols.push(c.col); m.score = Math.max(m.score, c.score);
      } else {
        if (m.cols.length) return;
        if (usedCols[c.col]) return;
        usedCols[c.col] = c.field; m.cols.push(c.col); m.score = c.score;
      }
    });

    FIELD_ORDER.forEach(function (f) {
      var m = map[f];
      if (!m.cols.length) { m.status = 'missing'; return; }
      var rivals = m.candidates.filter(function (c) { return c.col !== m.cols[0]; });
      var near = rivals.length ? rivals[0].score : 0;
      m.status = (m.score >= 70 && m.score - near >= 12) ? 'detected' : 'review';
      if (m.score >= 95) m.status = 'detected';
    });
    return map;
  }

  /* ------------------------------------------------- category normalisation */
  var CATEGORIES = ['Trade Receivable', 'Trade Payable', 'Advance from Customers', 'Advance to Vendors'];

  var ADV_FROM = [/advance\s*(amount\s*)?received/, /advances?\s*from\s*(customer|client|buyer|debtor|party|parties)/,
    /(customer|client|buyer|debtor)s?\s*advances?/, /advances?\s*received\s*from/, /unearned\s*(revenue|income)/,
    /income\s*received\s*in\s*advance/, /advance\s*from\s*cust/];
  var ADV_TO = [/advances?\s*(amount\s*)?paid/, /advances?\s*to\s*(vendor|supplier|creditor|contractor|party|parties)/,
    /(vendor|supplier|creditor|contractor)s?\s*advances?/, /advances?\s*paid\s*to/, /prepaid\s*to\s*(vendor|supplier)/,
    /advance\s*to\s*vend/, /capital\s*advance/];
  var TR_RULES = [/trade\s*receivable/, /accounts?\s*receivable/, /(^|\s)receivables?(\s|$)/, /(^|\s)a\s*r(\s|$)/,
    /(^|\s)ar(\s|$)/, /trade\s*ar(\s|$)/, /(sundry\s*)?debtors?/, /(^|\s)customers?(\s|$)/, /(^|\s)dr(\s|$)/];
  var TP_RULES = [/trade\s*payable/, /accounts?\s*payable/, /(^|\s)payables?(\s|$)/, /(^|\s)a\s*p(\s|$)/,
    /(^|\s)ap(\s|$)/, /trade\s*ap(\s|$)/, /(sundry\s*)?creditors?/, /(^|\s)(vendors?|suppliers?)(\s|$)/, /(^|\s)cr(\s|$)/];

  function anyMatch(rules, t) { for (var i = 0; i < rules.length; i++) if (rules[i].test(t)) return true; return false; }

  /* Returns one of CATEGORIES, or null when the value cannot be classified. */
  function normalizeCategory(raw) {
    var t = normHeader(raw);
    if (!t) return null;
    for (var i = 0; i < CATEGORIES.length; i++) if (t === normHeader(CATEGORIES[i])) return CATEGORIES[i];
    var isAdv = /advance/.test(t) || /\bprepaid\b/.test(t) || /unearned/.test(t);
    if (isAdv) {
      if (anyMatch(ADV_FROM, t)) return 'Advance from Customers';
      if (anyMatch(ADV_TO, t)) return 'Advance to Vendors';
      if (/receivable|debtor|customer|client|buyer/.test(t)) return 'Advance from Customers';
      if (/payable|creditor|vendor|supplier/.test(t)) return 'Advance to Vendors';
      return null;                                   /* bare "Advance" — ambiguous */
    }
    if (anyMatch(TR_RULES, t)) return 'Trade Receivable';
    if (anyMatch(TP_RULES, t)) return 'Trade Payable';
    return null;
  }

  /* ------------------------------------------------------ amount + currency */
  var SYMBOLS = [['₹', 'INR'], ['rs.', 'INR'], ['rs', 'INR'], ['inr', 'INR'], ['us$', 'USD'], ['usd', 'USD'],
    ['$', 'USD'], ['€', 'EUR'], ['eur', 'EUR'], ['£', 'GBP'], ['gbp', 'GBP'], ['¥', 'JPY'], ['jpy', 'JPY'],
    ['aed', 'AED'], ['sgd', 'SGD'], ['aud', 'AUD'], ['cad', 'CAD'], ['chf', 'CHF']];

  /* Returns {value:Number|null, currency:String|null, note:String|null} */
  function parseAmount(raw) {
    if (raw === null || raw === undefined || raw === '') return { value: null, currency: null, note: null };
    if (typeof raw === 'number') return { value: isFinite(raw) ? raw : null, currency: null, note: null };
    var s = String(raw).replace(/\u00a0/g, ' ').trim();
    if (!s || BAD_TOKENS.test(s)) return { value: null, currency: null, note: null };
    var low = s.toLowerCase(), cur = null, i;
    for (i = 0; i < SYMBOLS.length; i++) { if (low.indexOf(SYMBOLS[i][0]) >= 0) { cur = SYMBOLS[i][1]; break; } }

    var neg = false, note = null;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
    if (/(^|[\s\d])cr\.?$/i.test(s)) { note = 'Cr'; s = s.replace(/cr\.?$/i, ''); }
    else if (/(^|[\s\d])dr\.?$/i.test(s)) { note = 'Dr'; s = s.replace(/dr\.?$/i, ''); }

    var body = s.replace(/[^0-9.,\-]/g, '');
    if (!body) return { value: null, currency: cur, note: null };
    if (/^-?\d{1,3}(\.\d{3})+(,\d+)?$/.test(body)) {           /* 1.234.567,89 */
      body = body.replace(/\./g, '').replace(',', '.');
    } else {
      body = body.replace(/,/g, '');
    }
    if ((body.match(/\./g) || []).length > 1) body = body.replace(/\.(?=.*\.)/g, '');
    var v = parseFloat(body);
    if (!isFinite(v)) return { value: null, currency: cur, note: null };
    if (neg) v = -Math.abs(v);
    return { value: v, currency: cur, note: note };
  }

  function fmtAmount(v, ccy) {
    if (v === null || v === undefined || !isFinite(v)) return null;
    var loc = (String(ccy || '').toUpperCase() === 'INR') ? 'en-IN' : 'en-US';
    try {
      return new Intl.NumberFormat(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);
    } catch (e) {
      return v.toFixed(2);
    }
  }
  function amountLabel(v, ccy) {
    var f = fmtAmount(v, ccy);
    if (f === null) return null;
    return (ccy ? String(ccy).toUpperCase() + ' ' : '') + f;
  }

  /* -------------------------------------------------------- letter language */
  /* Economic direction is authoritative: "our books" = the audit client's
     books; "your books" = the responding party's books.                       */
  /* --------------------------------------------------- category wording */
  /* Taken from the firm's own four confirmation formats.  The letter is
     written by the CLIENT COMPANY to the party and signed by the company's
     own officer; the auditors are named as the people the reply must go to. */
  var CATEGORY_LANGUAGE = {
    'Trade Receivable': {
      code: 'TR',
      title: 'ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION',
      partyLabel: 'Customer Name',
      /* "...they desire that <request> as of <date> ..." */
      request: 'you confirm directly to them the amount payable by you to us',
      statementClause: 'a statement of our account in your books as at that date',
      recordLine: 'the amount due from you',
      /* debtor format carries an extra clause the others do not */
      noPayment: true,
      differenceClause: 'If the amount is not in agreement with your records, '
        + 'please notify our auditors directly, with a copy to us, of the amount '
        + 'shown by your records and, if possible, provide full particulars of '
        + 'the difference and reconciliation to your records.',
      slip: function (c) { return 'We hereby confirm that the amount payable by us to ' + c; },
      meaning: 'Client is owed money by the party.'
    },
    'Trade Payable': {
      code: 'TP',
      title: 'ACCOUNTS PAYABLE/CREDITOR CONFIRMATION',
      partyLabel: 'Vendor Name',
      request: 'you furnish directly to them the amount of our liability to you (if any)',
      statementClause: 'a statement of our account as at that date',
      recordLine: 'the amount due to you',
      noPayment: false,
      differenceClause: 'If the amount is not in agreement with your records, '
        + 'please notify our auditors directly, with a copy to us, of the amount '
        + 'shown by your records and, if possible, provide full particulars of '
        + 'the difference and reconciliation to your records.',
      slip: function (c) { return 'We hereby confirm that the amount receivable by us from ' + c; },
      meaning: 'Client owes money to the party.'
    },
    'Advance from Customers': {
      code: 'AFC',
      title: 'ADVANCE FROM CUSTOMER',
      partyLabel: 'Name',
      request: 'you furnish directly to them the amount of advance received from you (if any)',
      statementClause: 'a statement of our account as at that date',
      recordLine: 'the advance amount received from you',
      noPayment: false,
      differenceClause: 'If the amount is not in agreement with your records, '
        + 'please notify our auditors directly, with a copy to us, of the amount '
        + 'shown by your records and, if possible, provide full particulars of '
        + 'the difference and reconciliation to your records.',
      slip: function (c) { return 'We hereby confirm that the advance amount paid by us to ' + c; },
      meaning: 'Client has received an advance from the party.'
    },
    'Advance to Vendors': {
      code: 'ATV',
      title: 'ADVANCE PAID TO VENDOR',
      partyLabel: 'Vendor Name',
      request: 'you furnish directly to them the amount of advance paid to you (if any)',
      statementClause: 'a statement of our account as at that date',
      recordLine: 'the advance amount paid to you',
      noPayment: false,
      differenceClause: 'If the amount is not in agreement with your records, '
        + 'please notify our auditors directly, with a copy to us, of the amount '
        + 'shown by your records and, if possible, provide full particulars of '
        + 'the difference and reconciliation to your records.',
      slip: function (c) { return 'We hereby confirm that the advance amount received by us from ' + c; },
      meaning: 'Client has paid an advance to the party.'
    }
  };

  /* --------------------------------------------- audit type and period basis */
  /* The engagement type drives the opening sentence of every letter and the
     default signature line; the basis drives how the reporting span is cited. */
  /* auditors  - how the firm is described in "Our ..., [Firm], are engaged"
     engagement - what follows "are engaged in ... of our financial statements" */
  var AUDIT_TYPES = {
    'Statutory Audit':       { phrase: 'statutory audit',       designation: 'Statutory Auditor',
                               auditors: 'statutory auditors',  engagement: 'an audit' },
    'Interim Audit':         { phrase: 'interim audit',         designation: 'Statutory Auditor',
                               auditors: 'auditors',            engagement: 'an interim audit' },
    'Special Purpose Audit': { phrase: 'special purpose audit', designation: 'Auditor',
                               auditors: 'auditors',            engagement: 'a special purpose audit' },
    'Limited Review':        { phrase: 'limited review',        designation: 'Auditor',
                               auditors: 'auditors',            engagement: 'a limited review' },
    'Tax Audit':             { phrase: 'tax audit',             designation: 'Tax Auditor',
                               auditors: 'tax auditors',        engagement: 'a tax audit' },
    'Other':                 { phrase: 'audit',                 designation: 'Auditor',
                               auditors: 'auditors',            engagement: 'an audit' }
  };
  var AUDIT_TYPE_ORDER = ['Statutory Audit', 'Interim Audit', 'Special Purpose Audit',
                          'Limited Review', 'Tax Audit', 'Other'];

  /* Lower-case noun phrase that reads naturally after "As part of the ". */
  function auditPhrase(type, other) {
    if (type === 'Other') {
      var t = clean(other);
      if (!t) return 'audit';
      return t.replace(/^the\s+/i, '').replace(/^[A-Z][a-z]/, function (m) { return m.toLowerCase(); });
    }
    var d = AUDIT_TYPES[type];
    return d ? d.phrase : 'statutory audit';
  }
  function auditDesignation(type) {
    var d = AUDIT_TYPES[type];
    return d ? d.designation : 'Auditor';
  }

  /* "Our Statutory auditors" / "Our auditors" / "Our tax auditors" */
  function auditorsLabel(type) {
    var d = AUDIT_TYPES[type];
    return d ? d.auditors : 'auditors';
  }

  /* what the firm is engaged in: "an audit", "a limited review", ... */
  function engagementPhrase(type, other) {
    if (type === 'Other') {
      var t = clean(other);
      if (!t) return 'an audit';
      t = t.replace(/^(a|an|the)\s+/i, '');
      t = t.replace(/^[A-Z][a-z]/, function (m) { return m.toLowerCase(); });
      return (/^[aeiou]/i.test(t) ? 'an ' : 'a ') + t;
    }
    var d = AUDIT_TYPES[type];
    return d ? d.engagement : 'an audit';
  }

  /* basis 'year'  -> "for the year ended 31 March 2026"
     basis 'period'-> "for the period from 01 April 2026 to 30 September 2026"
                      (or "for the period ended …" when no start date is given) */
  function periodPhrase(basis, asAt, periodStart) {
    var end = fmtDateLong(asAt);
    if (!end) return '';
    if (basis === 'period') {
      var st = fmtDateLong(periodStart);
      return st ? 'for the period from ' + st + ' to ' + end : 'for the period ended ' + end;
    }
    return 'for the year ended ' + end;
  }
  function periodLabel(basis, asAt, periodStart) {
    var p = periodPhrase(basis, asAt, periodStart).replace(/^for the /, '');
    return p ? p.charAt(0).toUpperCase() + p.slice(1) : '';
  }

  /* ------------------------------------------------------ amount in words */
  /* The confirmation formats carry "(In Words: ... only)".  Rupee amounts use
     the Indian system (lakh, crore); every other currency uses the
     international system (million, billion).                                */
  var ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
    'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
    'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
  var TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy',
    'Eighty', 'Ninety'];

  function twoDigits(n) {
    if (n < 20) return ONES[n];
    var t = TENS[Math.floor(n / 10)];
    return n % 10 ? t + ' ' + ONES[n % 10] : t;
  }
  function threeDigits(n) {
    var out = [];
    if (n >= 100) { out.push(ONES[Math.floor(n / 100)] + ' Hundred'); n = n % 100; }
    if (n) out.push(twoDigits(n));
    return out.join(' ');
  }

  /* 1,23,45,678 -> "One Crore Twenty Three Lakh Forty Five Thousand ..." */
  function indianWords(n) {
    if (n === 0) return 'Zero';
    var parts = [];
    var crore = Math.floor(n / 10000000); n = n % 10000000;
    var lakh = Math.floor(n / 100000);    n = n % 100000;
    var thousand = Math.floor(n / 1000);  n = n % 1000;
    if (crore) parts.push((crore > 999 ? indianWords(crore) : threeDigits(crore)) + ' Crore');
    if (lakh) parts.push(threeDigits(lakh) + ' Lakh');
    if (thousand) parts.push(threeDigits(thousand) + ' Thousand');
    if (n) parts.push(threeDigits(n));
    return parts.join(' ');
  }

  function internationalWords(n) {
    if (n === 0) return 'Zero';
    var scales = [[1000000000000, 'Trillion'], [1000000000, 'Billion'],
                  [1000000, 'Million'], [1000, 'Thousand']];
    var parts = [], i;
    for (i = 0; i < scales.length; i++) {
      var unit = Math.floor(n / scales[i][0]);
      if (unit) {
        parts.push((unit > 999 ? internationalWords(unit) : threeDigits(unit))
                   + ' ' + scales[i][1]);
        n = n % scales[i][0];
      }
    }
    if (n) parts.push(threeDigits(n));
    return parts.join(' ');
  }

  var SUBUNITS = { INR: 'Paise', USD: 'Cents', EUR: 'Cents', GBP: 'Pence',
    AED: 'Fils', SGD: 'Cents', AUD: 'Cents', CAD: 'Cents', JPY: '', CHF: 'Rappen' };

  /* Returns e.g. "Rupees One Lakh Twenty Five Thousand only" */
  function amountInWords(value, currency) {
    if (value === null || value === undefined || !isFinite(value)) return '';
    var code = String(currency || '').toUpperCase();
    var negative = value < 0;
    var abs = Math.abs(Number(value));
    var whole = Math.floor(abs + 1e-9);
    var fraction = Math.round((abs - whole) * 100);
    if (fraction === 100) { whole += 1; fraction = 0; }

    var major = { INR: 'Rupees', USD: 'US Dollars', EUR: 'Euros', GBP: 'Pounds',
      AED: 'Dirhams', SGD: 'Singapore Dollars', AUD: 'Australian Dollars',
      CAD: 'Canadian Dollars', JPY: 'Yen', CHF: 'Swiss Francs' }[code] || code;

    var body = (code === 'INR' ? indianWords(whole) : internationalWords(whole));
    var text = (major ? major + ' ' : '') + body;
    var minor = SUBUNITS[code];
    if (fraction && minor !== '') {
      text += ' and ' + twoDigits(fraction) + ' ' + (minor || 'Cents');
    }
    if (negative) text = 'Minus ' + text;
    return text.replace(/\s+/g, ' ').trim() + ' only';
  }

  /* ---------------------------------------------------------- page fitting */
  /* A4 less 2 cm top and bottom margins, in twips. Letters are laid out at
     normal density and only tightened when the estimate overruns the page,
     so a short letter keeps its white space and a long one still signs off
     on page one.                                                            */
  var USABLE_HEIGHT = 16838 - 2 * 1134;
  var LINE = 264;                 /* one body line at 10.5 pt, 1.1 spacing   */
  var BODY_CPL = 92;              /* characters per line across 9,638 twips  */
  var LABEL_CPL = 36;             /* bold label inside the 4,100 twip column */
  var SUB_CPL = 46;               /* 9.5 pt italic inside the same column    */

  function wrapped(text, cpl) { return Math.max(1, Math.ceil(String(text || '').length / cpl)); }

  function estimateHeight(party, paras, attention, rows, notes) {
    var h = 0;
    h += party.length * 240 + 240;                                   /* address block   */
    h += LINE + 160;                                                  /* subject + rule  */
    h += LINE + 140;                                                  /* salutation      */
    h += wrapped(paras[1], BODY_CPL) * LINE + 140;                    /* opening para    */
    h += wrapped(paras[2], BODY_CPL) * LINE + 90;                     /* instruction     */
    h += attention.length * (240 + 40);
    h += 140 + LINE + 20 + 240 + 100;                                 /* form heading    */
    rows.forEach(function (r) {
      var inner = wrapped(r.label, LABEL_CPL) * 240 + (r.sub ? wrapped(r.sub, SUB_CPL) * 240 : 0) + 120;
      h += Math.max(357 + (r.tall === 1 ? 300 : r.tall === 2 ? 620 : 0), inner);
    });
    h += 140 + LINE + 50;                                             /* "Note:"         */
    notes.forEach(function (n) { h += wrapped(n, BODY_CPL - 6) * LINE + 40; });
    h += 140 + LINE + 120 + LINE + 220 + LINE + 40 + LINE + 40;       /* sign-off block  */
    return h;
  }

  /* ------------------------------------------------------------ letter model */
  /* Single source of truth consumed by BOTH the HTML preview and the DOCX.
     The shape follows the firm's own confirmation formats:

        (on the letter head of the Company)        <- optional note
        ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION    <- title, centred, bold
                                        Date: ...  <- right
        Customer Name                              <- left
        [ADDRESS]
        Dear Sir,
        ... four to five body paragraphs ...
        [Partner's Name] / [Firm's Name] (Chartered Accountants) / Email ID:
        Yours faithfully / [Company's Name] / Mr. XX / Director / CFO
        We hereby confirm ... + Name and Title / Company / Signature / Date   */
  function buildLetterModel(conf) {
    var L = CATEGORY_LANGUAGE[conf.category];
    if (!L) throw new Error('Unknown category: ' + conf.category);

    var client = conf.clientName;
    var asAt = conf.asAt || conf.yearEnd;
    var dateLabel = conf.yearEndLabel || fmtDateLong(asAt);
    var firm = conf.firmName;
    var auditors = auditorsLabel(conf.auditType);
    var engagement = engagementPhrase(conf.auditType, conf.auditTypeOther);

    /* party block, top left */
    var party = [{ t: conf.partyName, b: false }];
    (conf.addressLines || []).forEach(function (l) { if (l) party.push({ t: l, b: false }); });
    if (conf.contactPerson) party.push({ t: 'Kind Attn: ' + conf.contactPerson, b: false });

    /* body */
    var amtLbl = amountLabel(conf.amount, conf.currency);
    var words = amountInWords(conf.amount, conf.currency);
    var ccy = String(conf.currency || '').toUpperCase();

    var paras = [];
    paras.push('Our ' + auditors + ', ' + firm + ', are engaged in ' + engagement +
               ' of our financial statements. In connection therewith, they desire that ' +
               L.request + ' as at ' + dateLabel + ' and ' + L.statementClause + '.');
    if (amtLbl !== null) {
      paras.push('According to our records, ' + L.recordLine + ' as at ' + dateLabel +
                 ' is ' + amtLbl + ' (In Words: ' + words + ')');
    } else {
      paras.push('According to our records, the ' + L.recordLine.replace(/^amount /, 'amount ') +
                 ' as at ' + dateLabel + ' is as per the statement of account enclosed. ' +
                 'Kindly confirm the balance appearing in your books as at that date.');
    }
    paras.push('After signing your reply, please e-mail this letter directly to our ' +
               'auditors at the following e-mail address:');

    /* auditor block */
    var emails = (conf.auditors || []).map(function (a) { return a.email; })
      .filter(validEmail);
    var auditorBlock = [];
    if (conf.partnerName) auditorBlock.push({ t: conf.partnerName, b: false });
    auditorBlock.push({ t: firm + ' (Chartered Accountants)', b: false });
    auditorBlock.push({ t: 'Email ID: ' + emails.join('; '), b: false });

    var closingParas = [L.differenceClause];
    if (L.noPayment) {
      closingParas.push('This letter is not a request for payment and accordingly ' +
                        'please do not enclose a cheque or other payment with your confirmation.');
    }
    closingParas.push('We thank you in advance for your co-operation in complying ' +
                      'with this request and apologise for any inconvenience caused.');

    /* signature block - the client company signs, not the auditor */
    var signature = [{ t: 'Yours faithfully', b: false },
                     { t: client, b: false }];
    if (conf.signatoryName) signature.push({ t: conf.signatoryName, b: false, gap: true });
    if (conf.signatoryDesignation) signature.push({ t: conf.signatoryDesignation, b: false });

    /* tear-off confirmation slip */
    var slip = {
      sentence: L.slip(client) + ' as on ' + dateLabel + ' is ' +
                (ccy ? ccy + ' ' : '') + '______________',
      rows: ['Name and Title', 'Company / Firm', 'Signature', 'Date']
    };

    var bulk = party.length + auditorBlock.length + signature.length +
               wrapped(paras[0], BODY_CPL) + wrapped(paras[1], BODY_CPL) +
               closingParas.reduce(function (n, t) { return n + wrapped(t, BODY_CPL); }, 0);

    return {
      letterheadNote: conf.letterheadNote ? '(on the letter head of the Company)' : '',
      title: L.title,
      dateLine: 'Date: ' + (conf.letterDateLabel || ''),
      partyBlock: party,
      salutation: 'Dear Sir,',
      paras: paras,
      auditorBlock: auditorBlock,
      closingParas: closingParas,
      signature: signature,
      slip: slip,
      compact: bulk >= 26,
      /* kept so saved records and file names stay unchanged */
      category: conf.category
    };
  }

  /* ------------------------------------------------------------ OOXML parts */
  function xe(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }

  /* rPr children must follow the schema order: rFonts, b, i, caps, color, sz, u */
  function run(text, o) {
    o = o || {};
    var p = '';
    if (o.b) p += '<w:b/>';
    if (o.i) p += '<w:i/>';
    if (o.caps) p += '<w:caps/>';
    if (o.color) p += '<w:color w:val="' + o.color + '"/>';
    if (o.sz) p += '<w:sz w:val="' + o.sz + '"/><w:szCs w:val="' + o.sz + '"/>';
    if (o.u) p += '<w:u w:val="single"/>';
    return '<w:r>' + (p ? '<w:rPr>' + p + '</w:rPr>' : '') + '<w:t xml:space="preserve">' + xe(text) + '</w:t></w:r>';
  }

  /* pPr children order: keepNext, keepLines, pBdr, spacing, ind, jc */
  function para(runs, o) {
    o = o || {};
    var p = '';
    if (o.keepNext) p += '<w:keepNext/>';
    if (o.keepLines) p += '<w:keepLines/>';
    if (o.rule) p += '<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="3" w:color="9A9A9A"/></w:pBdr>';
    p += '<w:spacing w:before="' + (o.before || 0) + '" w:after="' + (o.after === undefined ? 120 : o.after) +
         '" w:line="' + (o.line || 264) + '" w:lineRule="auto"/>';
    if (o.ind) p += '<w:ind w:left="' + o.ind + '"' + (o.hanging ? ' w:hanging="' + o.hanging + '"' : '') + '/>';
    if (o.jc) p += '<w:jc w:val="' + o.jc + '"/>';
    return '<w:p><w:pPr>' + p + '</w:pPr>' + (runs || '') + '</w:p>';
  }

  var COL_L = 4100, COL_R = 5538;   /* twips; A4 with 2 cm margins = 9638 usable */

  function cell(width, contentXml, shaded) {
    return '<w:tc><w:tcPr><w:tcW w:w="' + width + '" w:type="dxa"/>' +
      (shaded ? '<w:shd w:val="clear" w:color="auto" w:fill="F2F0EA"/>' : '') +
      '<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>' +
      '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tcMar>' +
      '<w:vAlign w:val="center"/></w:tcPr>' + contentXml + '</w:tc>';
  }

  /* Two-column borderless grid used for the slip: "Name and Title  : ____" */
  function slipTable(rows, compact) {
    var xml = '<w:tbl><w:tblPr><w:tblW w:w="6600" w:type="dxa"/>' +
      '<w:tblBorders>' +
      ['top', 'left', 'bottom', 'right', 'insideH', 'insideV'].map(function (k) {
        return '<w:' + k + ' w:val="none" w:sz="0" w:space="0" w:color="auto"/>';
      }).join('') +
      '</w:tblBorders><w:tblLayout w:type="fixed"/>' +
      '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/>' +
      '</w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr>' +
      '<w:tblGrid><w:gridCol w:w="2600"/><w:gridCol w:w="4000"/></w:tblGrid>';
    rows.forEach(function (label) {
      xml += '<w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="' +
        (compact ? 300 : 340) + '" w:hRule="atLeast"/></w:trPr>' +
        '<w:tc><w:tcPr><w:tcW w:w="2600" w:type="dxa"/></w:tcPr>' +
        para(run(label), { after: 0, line: 240 }) + '</w:tc>' +
        '<w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>' +
        para(run(':  ______________________'), { after: 0, line: 240 }) + '</w:tc></w:tr>';
    });
    return xml + '</w:tbl>';
  }

  function documentXml(m) {
    var body = '';
    var k = m.compact ? 0.78 : 1;
    var sp = function (v) { return Math.round(v * k); };

    if (m.letterheadNote) {
      body += para(run(m.letterheadNote), { jc: 'center', after: sp(40), line: 240 });
    }
    body += para(run(m.title, { b: true }), { jc: 'center', after: sp(260), line: 240,
                                              keepNext: true });
    body += para(run(m.dateLine), { jc: 'right', after: sp(60), line: 240 });
    m.partyBlock.forEach(function (l, i) {
      body += para(run(l.t, { b: l.b }),
                   { after: i === m.partyBlock.length - 1 ? sp(240) : 0, line: 240 });
    });
    body += para(run(m.salutation), { after: sp(200), line: 240 });
    m.paras.forEach(function (t, i) {
      body += para(run(t), { jc: 'both', after: sp(i === m.paras.length - 1 ? 150 : 200),
                             keepNext: i === m.paras.length - 1 });
    });
    m.auditorBlock.forEach(function (l, i) {
      body += para(run(l.t, { b: l.b }),
                   { after: i === m.auditorBlock.length - 1 ? sp(200) : 0, line: 240 });
    });
    m.closingParas.forEach(function (t) {
      body += para(run(t), { jc: 'both', after: sp(200) });
    });
    m.signature.forEach(function (l, i) {
      body += para(run(l.t, { b: l.b }),
                   { before: l.gap ? sp(360) : 0,
                     after: i === m.signature.length - 1 ? sp(420) : sp(20), line: 240,
                     keepLines: true, keepNext: i < m.signature.length - 1 });
    });
    body += para(run(m.slip.sentence), { jc: 'both', after: sp(160), keepNext: true });
    body += slipTable(m.slip.rows, m.compact);
    body += '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>';

    var mg = m.compact ? 1021 : 1134;        /* 1.8 cm when tight, else 2 cm */
    var top = m.letterheadNote ? mg : Math.round(mg * 1.25);
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>' +
      '<w:pgMar w:top="' + top + '" w:right="1134" w:bottom="' + mg +
      '" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/>' +
      '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>';
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>' +
      body + '</w:body></w:document>';
  }

  var STYLES_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
    '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>' +
    '<w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="en-IN"/></w:rPr></w:rPrDefault>' +
    '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>' +
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>' +
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/>' +
    '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>' +
    '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style></w:styles>';

  var CONTENT_TYPES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
    '</Types>';

  var PKG_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>' +
    '</Relationships>';

  var DOC_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
    '</Relationships>';

  var APP_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" ' +
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
    '<Application>Balance Confirmation Generator</Application><Company></Company></Properties>';

  function coreXml(conf, stamp) {
    var t = stamp || new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
      'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
      '<dc:title>' + xe('Balance confirmation — ' + conf.partyName + ' — ' + conf.category) + '</dc:title>' +
      '<dc:subject>' + xe(conf.auditType + ' of ' + conf.clientName + ' — ' +
        (periodLabel(conf.basis, conf.asAt || conf.yearEnd, conf.periodStart) || 'year ended ' + conf.yearEndLabel)) + '</dc:subject>' +
      '<dc:creator>' + xe(conf.firmName) + '</dc:creator>' +
      '<cp:lastModifiedBy>' + xe(conf.firmName) + '</cp:lastModifiedBy>' +
      '<dcterms:created xsi:type="dcterms:W3CDTF">' + t + '</dcterms:created>' +
      '<dcterms:modified xsi:type="dcterms:W3CDTF">' + t + '</dcterms:modified></cp:coreProperties>';
  }

  /* Returns the complete set of package parts for one .docx */
  function docxParts(model, conf, stamp) {
    return {
      '[Content_Types].xml': CONTENT_TYPES,
      '_rels/.rels': PKG_RELS,
      'docProps/core.xml': coreXml(conf, stamp),
      'docProps/app.xml': APP_XML,
      'word/document.xml': documentXml(model),
      'word/_rels/document.xml.rels': DOC_RELS,
      'word/styles.xml': STYLES_XML
    };
  }

  /* ---------------------------------------------------------------- naming */
  function sanitizeFilename(s) {
    var t = String(s === null || s === undefined ? '' : s)
      .replace(/[\\/:*?"<>|]/g, ' ')
      .replace(/[\x00-\x1F\x7F]/g, '')
      .replace(/\s+/g, ' ')
      .replace(/^[.\s]+|[.\s]+$/g, '')
      .trim();
    if (t.length > 110) t = t.slice(0, 110).trim();
    if (!t) t = 'Party';
    if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(t)) t = t + '_';
    return t;
  }

  function uniqueFilename(base, ext, used) {
    var name = base + ext, key = name.toLowerCase(), n = 1;
    while (used[key]) { n++; name = base + ' (' + n + ')' + ext; key = name.toLowerCase(); }
    used[key] = true;
    return name;
  }

  /* ------------------------------------------------------------ email text */
  var DEFAULT_SUBJECT = 'Balance confirmation request as at {date} — {client}';
  /* The attached letter is issued by the client company; this covering mail
     goes out from the audit firm's own mailbox. */
  var DEFAULT_BODY = [
    'Dear Sir/Madam,',
    '',
    'We are the auditors of {client} and are carrying out {audittype_article} of its financial statements {period}.',
    '',
    'Please find attached a balance confirmation request issued by {client} in respect of the {category} balance appearing in its books as at {date}, being {amount}.',
    '',
    'Kindly sign the attached letter and e-mail it directly to us at:',
    '{auditors}',
    '',
    'Should the amount not agree with your records, please let us know the balance as per your books together with particulars of the difference.',
    '',
    'We thank you in advance for your co-operation.',
    '',
    'Yours faithfully,',
    'For {firm}',
    '{designation}'
  ].join('\n');
  var DEFAULT_BODY_V3 = DEFAULT_BODY;

  function fillTemplate(tpl, conf) {
    var amt = amountLabel(conf.amount, conf.currency);
    var auditors = (conf.auditors || []).map(function (a) {
      return '  ' + (a.name ? a.name + ' — ' : '') + a.email;
    }).join('\n');
    return String(tpl || '')
      .replace(/\{party\}/g, conf.partyName || '')
      .replace(/\{client\}/g, conf.clientName || '')
      .replace(/\{category\}/g, conf.category || '')
      .replace(/\{date\}/g, conf.yearEndLabel || '')
      .replace(/\{audittype\}/g, auditPhrase(conf.auditType, conf.auditTypeOther))
      .replace(/\{audittype_article\}/g, engagementPhrase(conf.auditType, conf.auditTypeOther))
      .replace(/\{words\}/g, amountInWords(conf.amount, conf.currency))
      .replace(/\{period\}/g, periodPhrase(conf.basis, conf.asAt || conf.yearEnd, conf.periodStart) ||
        (conf.yearEndLabel ? 'for the year ended ' + conf.yearEndLabel : ''))
      .replace(/\{amount\}/g, amt === null ? 'not available' : amt)
      .replace(/\{currency\}/g, conf.currency || '')
      .replace(/\{firm\}/g, conf.firmName || '')
      .replace(/\{designation\}/g, conf.firmDesignation || '')
      .replace(/\{auditors\}/g, auditors);
  }

  function buildEmailDraft(conf, opts) {
    opts = opts || {};
    var team = (conf.auditors || []).map(function (a) { return a.email; }).filter(validEmail);
    return {
      to: conf.partyEmail || '',
      cc: opts.ccTeam === false ? [] : team,
      replyTo: opts.replyToTeam === false ? [] : team,
      subject: fillTemplate(opts.subject || DEFAULT_SUBJECT, conf),
      body: fillTemplate(opts.body || DEFAULT_BODY, conf)
    };
  }

  /* base64 helpers usable in both browser and Node */
  function bytesToB64(bytes) {
    var bin = '', chunk = 0x8000;
    for (var i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray ? bytes.subarray(i, i + chunk) : bytes.slice(i, i + chunk));
    }
    if (typeof btoa === 'function') return btoa(bin);
    return Buffer.from(bin, 'binary').toString('base64');
  }
  function utf8ToB64(str) { return bytesToB64(new TextEncoder().encode(str)); }
  function b64Url(b64) { return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
  function encodeHeaderWord(s) {
    return /^[\x20-\x7E]*$/.test(s) ? s : '=?UTF-8?B?' + utf8ToB64(s) + '?=';
  }

  /* RFC 2822 multipart/mixed message with the .docx attached */
  function buildMime(o) {
    var bnd = 'bcg' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    var L = [];
    if (o.from) L.push('From: ' + o.from);
    L.push('To: ' + o.to);
    if (o.cc && o.cc.length) L.push('Cc: ' + o.cc.join(', '));
    if (o.replyTo && o.replyTo.length) L.push('Reply-To: ' + o.replyTo.join(', '));
    L.push('Subject: ' + encodeHeaderWord(o.subject));
    L.push('MIME-Version: 1.0');
    L.push('Content-Type: multipart/mixed; boundary="' + bnd + '"');
    L.push('');
    L.push('--' + bnd);
    L.push('Content-Type: text/plain; charset="UTF-8"');
    L.push('Content-Transfer-Encoding: base64');
    L.push('');
    L.push(utf8ToB64(o.body).replace(/(.{76})/g, '$1\r\n'));
    L.push('--' + bnd);
    L.push('Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document; name="' + o.filename + '"');
    L.push('Content-Disposition: attachment; filename="' + o.filename + '"');
    L.push('Content-Transfer-Encoding: base64');
    L.push('');
    L.push(o.attachmentB64.replace(/(.{76})/g, '$1\r\n'));
    L.push('--' + bnd + '--');
    return L.join('\r\n');
  }

  function mailtoUrl(d) {
    var q = [];
    if (d.cc && d.cc.length) q.push('cc=' + encodeURIComponent(d.cc.join(',')));
    q.push('subject=' + encodeURIComponent(d.subject));
    q.push('body=' + encodeURIComponent(d.body));
    return 'mailto:' + encodeURIComponent(d.to || '') + '?' + q.join('&');
  }

  return {
    MONTHS: MONTHS, CATEGORIES: CATEGORIES, CATEGORY_LANGUAGE: CATEGORY_LANGUAGE,
    AUDIT_TYPES: AUDIT_TYPES, AUDIT_TYPE_ORDER: AUDIT_TYPE_ORDER,
    auditPhrase: auditPhrase, auditDesignation: auditDesignation,
    auditorsLabel: auditorsLabel, engagementPhrase: engagementPhrase,
    amountInWords: amountInWords,
    periodPhrase: periodPhrase, periodLabel: periodLabel,
    FIELD_DEFS: FIELD_DEFS, FIELD_ORDER: FIELD_ORDER,
    DEFAULT_SUBJECT: DEFAULT_SUBJECT, DEFAULT_BODY: DEFAULT_BODY,
    DEFAULT_BODY_V3: DEFAULT_BODY_V3,
    clean: clean, toDate: toDate, fmtDateLong: fmtDateLong, isoDate: isoDate,
    validEmail: validEmail, normHeader: normHeader, isNumericLike: isNumericLike,
    colLetter: colLetter, detectHeaderRow: detectHeaderRow, buildColumns: buildColumns,
    detectMapping: detectMapping, normalizeCategory: normalizeCategory,
    parseAmount: parseAmount, fmtAmount: fmtAmount, amountLabel: amountLabel,
    buildLetterModel: buildLetterModel, documentXml: documentXml, docxParts: docxParts,
    sanitizeFilename: sanitizeFilename, uniqueFilename: uniqueFilename,
    fillTemplate: fillTemplate, buildEmailDraft: buildEmailDraft, buildMime: buildMime,
    mailtoUrl: mailtoUrl, bytesToB64: bytesToB64, utf8ToB64: utf8ToB64, b64Url: b64Url,
    xe: xe
  };
})();
if(typeof module!=="undefined"&&module.exports){module.exports=BCG;}