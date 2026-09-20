/* =============================================================================
 * ui.js — Presentation and interaction
 * -----------------------------------------------------------------------------
 * The only module that touches the DOM. It contains no legal rule and no
 * threshold. It reads the engine's result and renders it — including the list
 * of answers still needed, each of which can take the user straight to its
 * field.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS;
  var calc = TAS.calc, rs = TAS.ruleset, state = TAS.state, esc = TAS.workingpaper.esc;
  var S = TAS.engine.STATUS;

  var PANELS = [
    { id: 'overview',   label: 'Overview' },
    { id: 'profile',    label: 'Assessee Profile' },
    { id: 'financials', label: 'Financial Inputs' },
    { id: 'tests',      label: 'Legal Tests' },
    { id: 'decision',   label: 'Decision' },
    { id: 'references', label: 'Section References' },
    { id: 'paper',      label: 'Working Paper' },
    { id: 'review',     label: 'Review & Export' }
  ];

  var lastResult = null;

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function ico(n, cls) { return '<svg class="ico' + (cls ? ' ' + cls : '') + '" aria-hidden="true"><use href="#i-' + n + '"></use></svg>'; }

  function toast(msg) {
    var t = $('#toast');
    t.textContent = msg;
    t.classList.add('is-on');
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove('is-on'); }, 3200);
  }

  /* ===========================================================================
   * BOOT
   * ======================================================================== */
  function init() {
    state.applyTheme(state.readTheme());
    syncThemeButtons();
    buildAySelect();
    buildSelect('#in-constitution', rs.constitutions, false);
    buildSelect('#in-profession', rs.professionCategories, true);
    buildFlagList();
    buildNav();
    buildCaseList();
    bindInputs();
    bindActions();
    syncInputs();
    show('overview');
    render();
  }

  function buildAySelect() {
    var sel = $('#ay-select');
    sel.innerHTML = rs.assessmentYears().map(function (ay) {
      return '<option value="' + esc(ay) + '">' + esc(ay) + '</option>';
    }).join('');
    sel.value = state.get().assessmentYear;
    sel.addEventListener('change', function () { state.set({ assessmentYear: sel.value }); render(); });
  }

  function buildSelect(sel, list, withBlank) {
    $(sel).innerHTML = (withBlank ? '<option value="">Select…</option>' : '') + list.map(function (c) {
      return '<option value="' + esc(c.id) + '">' + esc(c.label) + '</option>';
    }).join('');
  }

  function buildFlagList() {
    function row(c, bizOnly) {
      return '<label class="checkrow' + (bizOnly ? ' biz-only' : '') + '" data-flagrow="' + esc(c.id) + '">' +
        '<input type="checkbox" data-flag="' + esc(c.id) + '">' +
        '<span><span class="t">' + esc(c.label) + '</span>' +
        '<span class="n">' + esc(c.note) + (c.cite ? ' <span class="faint">(' + esc(c.cite) + ')</span>' : '') + '</span></span></label>';
    }
    $('#flag-list').innerHTML =
      rs.businessConditions.map(function (c) { return row(c, true); }).join('') +
      rs.generalConditions.map(function (c) { return row(c, false); }).join('');
    $$('[data-flag]').forEach(function (cb) {
      cb.addEventListener('change', function () { state.toggleFlag(cb.getAttribute('data-flag'), cb.checked); render(); });
    });
  }

  function buildNav() {
    $('#navlist').innerHTML = PANELS.map(function (p, i) {
      return '<li><button type="button" class="navstep" data-go="' + p.id + '">' +
        '<span class="n">' + (i + 1) + '</span><span>' + esc(p.label) + '</span></button></li>';
    }).join('');
    $$('[data-go]').forEach(function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-go')); }); });
    $('#progress').innerHTML = PANELS.map(function () {
      return '<span class="progress-seg"><span class="f"></span></span>';
    }).join('');
  }

  function buildCaseList() {
    $('#case-list').innerHTML = TAS.samples.cases.map(function (c) {
      return '<button type="button" class="case" data-case="' + esc(c.id) + '">' +
        '<span><span class="ttl">' + esc(c.title) + '</span>' +
        '<span class="path">' + esc(c.path) + '</span></span>' +
        '<span class="pill ' + pillFor(c.expect) + '">' + esc(c.expect) + (c.ground ? ' · ' + esc(c.ground) : '') + '</span></button>';
    }).join('');
    $$('[data-case]').forEach(function (b) {
      b.addEventListener('click', function () {
        var c = TAS.samples.byId(b.getAttribute('data-case'));
        if (!c) return;
        state.replace(c.input);
        syncInputs();
        render();
        show('decision');
        toast('Loaded: ' + c.title);
      });
    });
  }

  function pillFor(status) {
    if (status === S.APPLICABLE) return 'pill-bad';
    if (status === S.NOT_APPLICABLE) return 'pill-ok';
    return 'pill-warn';
  }

  /* ---- Binding ------------------------------------------------------------ */
  function bindInputs() {
    $$('[data-bind]').forEach(function (el) {
      var key = el.getAttribute('data-bind');
      el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', function () {
        var patch = {}; patch[key] = el.value; state.set(patch); render();
      });
    });
    $$('[data-nature]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.set({ nature: b.getAttribute('data-nature'), declarePresumptive: '' });
        render();
      });
    });
  }

  function bindActions() {
    $$('[data-theme-btn]').forEach(function (b) {
      b.addEventListener('click', function () { state.applyTheme(b.getAttribute('data-theme-btn')); syncThemeButtons(); });
    });
    $('#btn-reset').addEventListener('click', function () {
      if (!global.confirm('Clear all entered information and start again?')) return;
      state.reset(); syncInputs(); render(); show('profile'); toast('Cleared.');
    });
    $('#btn-help').addEventListener('click', function () { show('overview'); });
    $('#btn-export-top').addEventListener('click', function () { show('paper'); });
    $('#nav-status').addEventListener('click', function () {
      if (lastResult && lastResult.required.length) goTo(lastResult.required[0]);
      else show('decision');
    });

    $('#btn-wp-detailed').addEventListener('click', function () { if (gateOpen()) TAS.exporter.printDocument(lastResult, 'detailed'); });
    $('#btn-wp-executive').addEventListener('click', function () { if (gateOpen()) TAS.exporter.printDocument(lastResult, 'executive'); });
    $('#btn-wp-word').addEventListener('click', function () {
      if (!gateOpen()) return;
      TAS.exporter.exportWord(lastResult); toast('Word document generated.');
    });
    $('#btn-audit-json').addEventListener('click', function () {
      TAS.exporter.exportAuditTrail(lastResult); toast('Audit trail downloaded.');
    });
  }

  /* A working paper needs a decision AND the assessee's name. */
  function gateOpen() {
    if (!lastResult) return false;
    if (lastResult.status === S.INCOMPLETE) {
      toast('Answer the remaining questions first — taking you to the first one.');
      goTo(lastResult.required[0]);
      return false;
    }
    if (!state.get().clientName.trim()) {
      toast('Enter the assessee name for the working paper.');
      goTo({ field: 'clientName', panel: 'profile' });
      return false;
    }
    return true;
  }

  function syncThemeButtons() {
    var t = document.documentElement.getAttribute('data-theme');
    $$('[data-theme-btn]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-theme-btn') === t)); });
  }

  function syncInputs() {
    var i = state.get();
    $$('[data-bind]').forEach(function (el) {
      var k = el.getAttribute('data-bind');
      if (i[k] !== undefined && el.value !== i[k]) el.value = i[k];
    });
    $('#ay-select').value = i.assessmentYear;
    $$('[data-flag]').forEach(function (cb) { cb.checked = i.flags.indexOf(cb.getAttribute('data-flag')) !== -1; });
  }

  /* ---- Navigation --------------------------------------------------------- */
  function show(id) {
    $$('.panel').forEach(function (p) { p.classList.toggle('is-active', p.getAttribute('data-panel') === id); });
    var idx = PANELS.map(function (p) { return p.id; }).indexOf(id);
    $$('.navstep').forEach(function (b, i) {
      b.setAttribute('aria-current', String(b.getAttribute('data-go') === id));
      b.classList.toggle('done', i < idx);
    });
    $$('#progress .progress-seg').forEach(function (s, i) {
      s.classList.toggle('done', i < idx); s.classList.toggle('current', i === idx);
    });
    $('#progress-label').textContent = 'Step ' + (idx + 1) + ' of ' + PANELS.length + ' · ' + PANELS[idx].label;
    global.scrollTo({ top: 0, behavior: 'auto' });
  }

  /** Takes the user to a field: opens its panel, scrolls to it, focuses it and
   *  briefly highlights it. Works for inputs, selects and yes/no questions. */
  function goTo(req) {
    if (!req) return;
    show(req.panel || 'financials');
    var host = $('[data-field="' + req.field + '"]') || $('[data-q="' + req.field + '"]');
    if (!host) return;
    host.scrollIntoView({ behavior: 'auto', block: 'center' });
    var target = $('input, select', host) || $('button', host);
    if (target) { try { target.focus({ preventScroll: true }); } catch (e) { target.focus(); } }
    host.classList.remove('flash');
    void host.offsetWidth;
    host.classList.add('flash');
  }

  /* ===========================================================================
   * RENDER
   * ======================================================================== */
  function render() {
    var i = state.get();
    var isBusiness = i.nature === 'business';
    var c = rs.constitutionById(i.constitution);

    $$('[data-nature]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-nature') === i.nature)); });
    $('#wrap-profession-category').hidden = isBusiness;
    $$('.biz-only').forEach(function (el) { el.style.display = isBusiness ? '' : 'none'; });
    $('#lbl-turnover').textContent = isBusiness ? 'Turnover' : 'Gross receipts';
    $('#lbl-turnover-card').textContent = isBusiness ? 'Turnover and receipts' : 'Gross receipts';
    $('#hint-turnover').textContent = isBusiness
      ? 'Total sales, turnover or gross receipts of the business for the year, as per the books.'
      : 'Gross receipts of the profession for the year, as per the books.';
    $('#constitution-note').textContent = c && c.note ? c.note : '';

    var f = state.facts();
    $('#in-fy').value = f.financialYear;

    /* Basic exemption: only an individual or HUF has one. */
    var params = rs.forAssessmentYear(i.assessmentYear);
    var wrapEx = $('#wrap-exemption');
    if (c.hasBEL) {
      wrapEx.style.display = '';
      var ex = $('#in-exemption');
      ex.innerHTML = params.basicExemption.options.filter(function (o) {
        return o.appliesTo.indexOf(c.id) !== -1 && (!o.residentOnly || i.residentialStatus === 'resident');
      }).map(function (o) {
        return '<option value="' + esc(o.id) + '">' + esc(o.label) + ' — ' + calc.inr(o.amount) + '</option>';
      }).join('');
      ex.value = f.exemptionOption;
      $('#exemption-note').textContent = 'Used only on the low-profit limbs, ss. 44AB(d) and (e).';
    } else {
      wrapEx.style.display = 'none';
    }

    var result = state.evaluate();
    lastResult = result;

    renderBanners(result);
    renderFieldStates(result);
    renderDerivedNotices(result);
    renderQuestions(result);
    renderCashTests(result);
    renderThresholdMeter(result);
    renderVerdict(result);
    renderKpis(result);
    renderChain(result);
    renderMatrix(result);
    renderReferences(result);
    renderNotes(result);
    renderOutline(result);
    renderTrailSummary(result);
    renderStatus(result);
    renderGate(result);
  }

  /* ---- Banners: two compact strips --------------------------------------- */
  function renderBanners(result) {
    $('#banners').innerHTML =
      '<div class="strip strip-ok">' + ico('shield') + '<div><b>Legal basis:</b> ' +
        esc(rs.verificationStatement(result.facts.assessmentYear)) +
        ' <a href="../legal/sources.md" target="_blank" rel="noopener">Sources</a></div></div>' +
      '<div class="strip strip-warn">' + ico('alert') + '<div><b>Confidentiality:</b> this tool runs only in your browser ' +
        'and sends nothing anywhere. Do not paste client figures into chat assistants or other uncontrolled AI services.</div></div>';
    $('#foot-verification').innerHTML = esc(rs.verificationStatement(result.facts.assessmentYear));
  }

  /* ---- "Needed" tags, validation messages ---------------------------------- */
  function renderFieldStates(result) {
    var needed = {};
    result.required.forEach(function (r) { needed[r.field] = r; });

    $$('[data-req]').forEach(function (t) {
      var on = !!needed[t.getAttribute('data-req')];
      t.classList.toggle('is-on', on);
      t.textContent = on ? (needed[t.getAttribute('data-req')].error ? 'Correct' : 'Needed') : '';
    });

    var messages = {};
    result.validation.errors.forEach(function (e) { messages[e.field] = { kind: 'error', text: e.message }; });
    result.validation.cautions.forEach(function (w) { if (!messages[w.field]) messages[w.field] = { kind: 'caution', text: w.message }; });

    $$('[data-field]').forEach(function (w) {
      var key = w.getAttribute('data-field');
      w.classList.toggle('is-needed', !!needed[key] && !needed[key].error);
      w.classList.toggle('is-error', !!messages[key] && messages[key].kind === 'error');
      var old = $('.field-msg', w); if (old) old.remove();
      var m = messages[key];
      if (!m) return;
      var d = document.createElement('div');
      d.className = 'field-msg ' + m.kind;
      d.innerHTML = ico(m.kind === 'error' ? 'cross' : 'info') + '<span>' + esc(m.text) + '</span>';
      w.appendChild(d);
    });
  }

  function renderDerivedNotices(result) {
    if (!result.isBusiness) return;
    var f = result.facts, d = result.derived, A = result.params.business44AB;
    $('#derived-receipts').innerHTML = ico('info') + '<div>' + (f.totalReceipts === null || f.cashReceipts === null
      ? 'Enter both figures to see the cash receipt percentage.'
      : 'Cash received is <span class="strong">' + esc(f.totalReceipts > 0 ? calc.pct(d.cashReceiptRatio.value) : '0.00% (nil of nil)') +
        '</span> of all amounts received — limit ' + A.cashReceiptPct + '%.') + '</div>';
    $('#derived-payments').innerHTML = ico('info') + '<div>' + (f.totalPayments === null || f.cashPayments === null
      ? 'Enter both figures to see the cash payment percentage.'
      : 'Cash paid is <span class="strong">' + esc(f.totalPayments > 0 ? calc.pct(d.cashPaymentRatio.value) : '0.00% (nil of nil)') +
        '</span> of all payments — limit ' + A.cashPaymentPct + '%.') + '</div>';
  }

  /* ---- Legal Tests panel: the questions the law turns on ------------------- */
  function yesNo(key, value) {
    return '<div class="yesno" role="group">' +
      ['yes', 'no'].map(function (v) {
        return '<button type="button" data-yn="' + key + '" data-value="' + v + '" aria-pressed="' + String(value === v) + '">' +
          (v === 'yes' ? 'Yes' : 'No') + '</button>';
      }).join('') + '</div>';
  }

  function question(key, q, why, value, needed) {
    return '<div class="question' + (needed ? ' is-needed' : '') + '" data-q="' + key + '">' +
      '<div class="q">' + esc(q) + (needed ? ' <span class="req-tag is-on">Needed</span>' : '') + '</div>' +
      '<div class="why">' + esc(why) + '</div>' + yesNo(key, value) + '</div>';
  }

  function renderQuestions(result) {
    var f = result.facts, an = result.analysis, c = f.constitutionMeta, i = state.get();
    var needed = {}; result.required.forEach(function (r) { needed[r.field] = r; });
    var scheme = result.isBusiness ? 's. 44AD' : 's. 44ADA';
    var D = result.params.section44AD;
    $('#presumptive-title').textContent = 'Presumptive taxation — ' + scheme;

    var h = [];

    if (an.eligible === false) {
      h.push('<div class="notice notice-info">' + ico('info') + '<div><b>' + esc(scheme) + ' is not available:</b> ' +
             esc(an.exclusions.join('; ')) + '. Only the ' + (result.isBusiness ? 's. 44AB(a) turnover' : 's. 44AB(b) gross receipts') +
             ' limb applies' + (result.isBusiness && c.can44AD ? ', together with s. 44AB(e) if the assessee is within a s. 44AD(4) bar' : '') + '.</div></div>');
    } else {
      h.push('<p class="xs muted" style="margin-bottom:var(--s-3)">Eligibility is worked out from the profile: constitution, ' +
             'residential status' + (result.isBusiness ? ' and the conditions ticked' : ' and the profession') + '. The questions below ' +
             'appear only when their answer can change the outcome.</p>');
    }

    if (result.isBusiness && c.can44AD) {
      h.push(question('bar44AD',
        'Is AY 2026-27 within a five-year bar under s. 44AD(4)?',
        'Yes if the assessee declared income under s. 44AD in some year and then, within the next five years, declared less than ' +
        'the deemed rate — and AY 2026-27 falls in the five assessment years after that lower declaration. If barred, audit ' +
        'applies whenever total income exceeds the basic exemption, whatever the turnover.',
        i.bar44AD, !!needed.bar44AD));
    }
    if (result.isBusiness && (needed.prior44AD || (i.prior44AD && an.live === true && an.meets === false))) {
      h.push(question('prior44AD',
        'Was income declared under s. 44AD for any of ' + D.lookbackFrom + ' to ' + D.lookbackTo + '?',
        'Declared profit is below the s. 44AD deemed income. If s. 44AD was used in any of the five preceding assessment years, ' +
        'declaring less now attracts s. 44AD(4) and audit under s. 44AB(e).',
        i.prior44AD, !!needed.prior44AD));
    }
    if (needed.declarePresumptive || an.canDeclare) {
      h.push(question('declarePresumptive',
        'Will income be declared under ' + scheme + '(1) in the return?',
        an.declareMatters
          ? 'This decides the outcome. Under the first proviso to s. 44AB (Finance Act 2023), a person declaring under ' + scheme +
            '(1) is outside s. 44AB altogether. If income is not declared that way, audit applies.'
          : 'Optional here — the outcome is the same either way on these facts.',
        i.declarePresumptive, !!needed.declarePresumptive));
    }

    /* Figures behind the presumptive test */
    if (an.live !== false && an.eligible !== false) {
      var deemedText = an.deemed !== null && an.deemed !== undefined ? calc.inr(an.deemed)
        : (an.deemedLow ? calc.inr(an.deemedLow) + ' – ' + calc.inr(an.deemedHigh) : '—');
      h.push('<div class="kv" style="margin-top:var(--s-4);padding-top:var(--s-4);border-top:1px solid var(--border)">' +
        kvCell('Applicable ceiling', an.ceilingLabel || '—') +
        kvCell('Deemed income', result.isBusiness ? deemedText : (an.deemed ? calc.inr(an.deemed) : '—')) +
        kvCell('Declared profit', calc.inr(f.profit)) +
        kvCell('Profit %', calc.pct(result.derived.profitRatio.value)) +
        kvCell('Profit meets deemed', an.meets === null || an.meets === undefined ? '—' : (an.meets ? 'Yes' : 'No')) +
        kvCell('Basic exemption', f.exemptionAmount === 0 ? 'Nil' : calc.inr(f.exemptionAmount)) +
        '</div>');
    }

    $('#presumptive-body').innerHTML = h.join('');
    $$('[data-yn]', $('#presumptive-body')).forEach(function (b) {
      b.addEventListener('click', function () {
        var patch = {}; patch[b.getAttribute('data-yn')] = b.getAttribute('data-value');
        state.set(patch); render();
      });
    });
  }

  function kvCell(k, v) { return '<div><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>'; }

  /* ---- Cash meters --------------------------------------------------------- */
  function renderCashTests(result) {
    var f = result.facts, A = result.params.business44AB, P = result.params.section44ADA, D = result.params.section44AD;
    var h = [];
    if (result.isBusiness) {
      $('#cash-title').textContent = 'Cash transaction tests';
      h.push(pctMeter('s. 44AB(a) — cash received', f.cashReceipts, f.totalReceipts, A.cashReceiptPct, 'of all amounts received'));
      h.push(pctMeter('s. 44AB(a) — cash paid', f.cashPayments, f.totalPayments, A.cashPaymentPct, 'of all payments'));
      h.push(pctMeter('s. 44AD ceiling — cash received', f.cashReceipts, f.turnover, D.enhancedCashPctOfTurnover, 'of turnover'));
    } else {
      $('#cash-title').textContent = 'Cash receipt test — s. 44ADA';
      h.push(pctMeter('s. 44ADA ceiling — cash received', f.cashReceipts, f.turnover, P.enhancedCashPct, 'of gross receipts'));
    }
    $('#cash-tests').innerHTML = h.join('');
  }

  function pctMeter(title, cash, total, ceiling, basis) {
    var ok = calc.cashWithin(cash, total, ceiling);
    var known = ok !== null;
    var value = known ? (total > 0 ? cash / total * 100 : 0) : null;
    var scaleMax = Math.max(ceiling * 2, 10);
    var pos = calc.meterPosition(known ? value : 0, scaleMax);
    var limitPos = calc.meterPosition(ceiling, scaleMax);
    return '<div class="meter" style="margin-bottom:var(--s-5)">' +
      '<div class="row-between" style="margin-bottom:var(--s-2)"><span class="micro">' + esc(title) + '</span>' +
      '<span class="micro">' + esc(basis) + '</span></div>' +
      '<div class="meter-read" style="margin-bottom:var(--s-2)">' +
        '<span class="actual ' + (known ? (ok ? 'ok' : 'bad') : '') + '">' + esc(known ? calc.pct(value) : 'Not entered') + '</span>' +
        '<span class="verdict-word ' + (known ? (ok ? 'ok' : 'bad') : '') + '">' +
          (known ? (ok ? 'Within ' + ceiling + '%' : 'Above ' + ceiling + '%') : '—') + '</span></div>' +
      '<div class="meter-track">' +
        (known ? '<span class="meter-fill ' + (ok ? 'ok' : 'bad') + '" style="width:' + pos.toFixed(1) + '%"></span>' : '') +
        '<span class="meter-limit" style="left:' + limitPos.toFixed(1) + '%"></span></div>' +
      '<div class="meter-scale"><span>0%</span><span>Limit ' + ceiling + '%</span><span>' + scaleMax + '%</span></div></div>';
  }

  /* ---- Threshold meter ------------------------------------------------------ */
  function renderThresholdMeter(result) {
    var f = result.facts, t = result.thresholdTest, host = $('#threshold-meter');
    var limit = result.isBusiness ? result.analysis.limitValue : result.params.profession44AB.limit;
    if (f.turnover === null || limit === null || limit === undefined) {
      host.innerHTML = '<div class="notice">' + ico('info') + '<div>' + esc(t ? t.reason : 'Enter turnover.') + '</div></div>';
      return;
    }
    var scaleMax = Math.max(limit * 1.5, f.turnover * 1.12);
    var within = f.turnover <= limit;
    var room = limit - f.turnover;
    host.innerHTML =
      '<div class="meter-read" style="margin-bottom:var(--s-2)">' +
        '<span class="actual ' + (within ? 'ok' : 'bad') + '">' + esc(calc.inr(f.turnover)) + '</span>' +
        '<span class="verdict-word ' + (within ? 'ok' : 'bad') + '">' + (within ? 'Within limit' : 'Above limit') + '</span></div>' +
      '<div class="meter-track">' +
        '<span class="meter-fill ' + (within ? 'ok' : 'bad') + '" style="width:' + calc.meterPosition(f.turnover, scaleMax).toFixed(1) + '%"></span>' +
        '<span class="meter-limit" style="left:' + calc.meterPosition(limit, scaleMax).toFixed(1) + '%"></span></div>' +
      '<div class="meter-scale"><span>Nil</span><span>Limit ' + esc(calc.inrWords(limit)) + '</span><span>' + esc(calc.inrWords(scaleMax)) + '</span></div>' +
      '<div class="kv" style="margin-top:var(--s-4)">' +
        kvCell(result.isBusiness ? 'Turnover' : 'Gross receipts', calc.inr(f.turnover)) +
        kvCell('Limit applied', calc.inrWords(limit)) +
        kvCell(within ? 'Headroom' : 'Excess', calc.inr(Math.abs(room)) + ' (' + calc.inrWords(Math.abs(room)) + ')') +
      '</div>' +
      (result.analysis.firstProviso ? '<div class="notice notice-info" style="margin-top:var(--s-4)">' + ico('info') +
        '<div>The limit is crossed, but income is declared under the presumptive scheme — the first proviso takes the assessee ' +
        'outside s. 44AB.</div></div>' : '');
  }

  /* ---- Verdict, or the list of answers still needed ------------------------- */
  function renderVerdict(result) {
    var host = $('#verdict-host');

    if (result.status === S.INCOMPLETE) {
      var n = result.required.length;
      host.innerHTML = '<div class="needs">' +
        '<div class="needs-head"><div class="needs-count">' + n + '</div><div>' +
        '<div class="micro">Tax audit applicability</div>' +
        '<div class="needs-title">' + (n === 1 ? 'One more answer needed' : n + ' more answers needed') + '</div>' +
        '<div class="needs-lead">The decision appears here as soon as these are filled. Select <b>Go to</b> to jump straight to each one.</div>' +
        '</div></div>' +
        result.required.map(function (r, idx) {
          return '<div class="need-item' + (r.error ? ' is-error' : '') + '">' +
            '<span class="num">' + (idx + 1) + '</span>' +
            '<div><div class="lbl">' + esc(r.label) + '</div><div class="why">' + esc(r.why) + '</div></div>' +
            '<button type="button" class="btn btn-sm btn-primary" data-goto="' + idx + '">Go to ' + ico('chevron') + '</button></div>';
        }).join('') + '</div>';
      $$('[data-goto]', host).forEach(function (b) {
        b.addEventListener('click', function () { goTo(result.required[+b.getAttribute('data-goto')]); });
      });
      return;
    }

    var con = TAS.reasoning.generateConclusion(result);
    var applicable = result.status === S.APPLICABLE;
    var sectionLine = applicable
      ? 'Under ' + result.triggers.map(function (t) { return t.provision; }).join(' and ')
      : (result.analysis.firstProviso ? 'First proviso to s. 44AB — presumptive declaration' : 'No limb of s. 44AB applies');

    var h = ['<div class="verdict ' + (applicable ? 'is-applicable' : 'is-not-applicable') + '">'];
    h.push('<div class="verdict-head"><div class="verdict-mark">' + ico(applicable ? 'cross' : 'check') + '</div><div>');
    h.push('<div class="micro">Tax audit applicability · ' + esc(result.facts.financialYear) + ' · ' + esc(result.params.act) + '</div>');
    h.push('<div class="verdict-status">' + esc(result.status) + '</div>');
    h.push('<div class="verdict-lead"><b>' + esc(sectionLine) + '.</b> ' + esc(con.lead) + '</div>');
    h.push('</div></div>');

    h.push('<div class="verdict-body"><h4>Why</h4>');
    con.body.forEach(function (p) { h.push('<p>' + esc(p) + '</p>'); });
    if (con.grounds.length) {
      h.push('<ol>' + con.grounds.map(function (g) {
        return '<li><span class="strong">' + esc(g.provision) + '</span> — ' + esc(g.reason) + '</li>';
      }).join('') + '</ol>');
    }
    if (con.reasons.length) h.push('<ol>' + con.reasons.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ol>');
    h.push('</div>');

    h.push('<div class="verdict-body"><h4>What this means</h4><ul>' +
      con.consequences.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>');
    if (con.caveat) h.push('<div class="verdict-body"><h4>Basis</h4><p>' + esc(con.caveat) + '</p></div>');
    h.push('</div>');
    host.innerHTML = h.join('');
  }

  function renderKpis(result) {
    var wp = TAS.workingpaper.generateWorkingPaper(result);
    $('#kpi-host').innerHTML = wp.metrics.map(function (m) {
      return '<div class="metric"><div class="micro">' + esc(m.k) + '</div>' +
        '<div class="metric-value' + (m.sm ? ' sm' : '') + (m.cls ? ' ' + m.cls : '') + '">' + esc(m.v) + '</div></div>';
    }).join('');
  }

  function renderChain(result) {
    $('#chain-host').innerHTML = TAS.reasoning.generateReasoning(result).map(function (s) {
      return '<li><span class="chain-num ' + esc(s.status) + '">' + s.number + '</span>' +
        '<div class="chain-head"><span class="h">' + esc(s.heading) + '</span>' +
        (s.value && s.value !== '—' ? '<span class="v">' + esc(s.value) + '</span>' : '') +
        (s.provision ? '<span class="p">' + esc(s.provision) + '</span>' : '') + '</div>' +
        '<div class="chain-text">' + esc(s.text) + '</div></li>';
    }).join('');
  }

  function matrixPill(s) {
    if (s === 'TRIGGERS AUDIT') return 'pill-bad';
    if (s === 'NO AUDIT' || s === 'CONDITION MET' || s === 'EXCLUDED BY PROVISO') return 'pill-ok';
    if (s === 'AWAITING INPUT' || s === 'CONDITION NOT MET') return 'pill-warn';
    return 'pill-neutral';
  }

  function renderMatrix(result) {
    $('#matrix-host').innerHTML =
      '<thead><tr><th>Test</th><th>Input</th><th>Threshold</th><th>Status</th><th>Provision</th><th>Finding</th></tr></thead><tbody>' +
      TAS.reasoning.generateMatrix(result).map(function (r) {
        return '<tr><td class="test-name">' + esc(r.test) + '</td><td class="num">' + esc(r.input) + '</td>' +
          '<td>' + esc(r.threshold) + '</td><td><span class="pill ' + matrixPill(r.status) + '">' + esc(r.status) + '</span></td>' +
          '<td class="xs">' + esc(r.provision) + '</td><td class="reason">' + esc(r.reason) + '</td></tr>';
      }).join('') + '</tbody>';
  }

  function refPill(s) {
    if (s === 'breached') return 'pill-bad';
    if (s === 'satisfied') return 'pill-ok';
    if (s === 'review') return 'pill-warn';
    return 'pill-neutral';
  }

  function renderReferences(result) {
    var cards = TAS.reasoning.generateLegalReferences(result);
    $('#refs-host').innerHTML = cards.map(function (r, idx) {
      var open = idx === 0;
      return '<div class="ref">' +
        '<button type="button" class="ref-head" aria-expanded="' + open + '" data-ref="' + idx + '">' +
          ico('chevron', 'chev') + '<span class="prov">' + esc(r.provision) + '</span>' +
          '<span class="ttl">' + esc(r.title) + '</span>' +
          '<span class="pill ' + refPill(r.conclusionStatus) + '">' + esc(r.conclusion.replace(/\.$/, '')) + '</span></button>' +
        '<div class="ref-body" data-refbody="' + idx + '"' + (open ? '' : ' hidden') + '>' +
          block('Applicability', '<p>' + esc(r.applicability) + '</p>') +
          block('Statutory text', r.statutoryText
            ? '<div class="ref-quote">' + esc(r.statutoryText) + '</div><div class="ref-source">Source: ' + esc(r.statutorySource) + '</div>'
            : '<div class="ref-missing"><b>Not reproduced.</b> The verbatim text of ' + esc(r.provision) +
              ' was not retrieved from a source for this tool. Read it from the bare Act.</div>') +
          block('Practical interpretation', '<span class="label-simplified">Simplified professional explanation</span><p>' +
            esc(r.practicalInterpretation) + '</p>') +
          block('Application to these facts', '<p>' + esc(r.applicationToFacts) + '</p>') +
          block('Conclusion on this provision', '<p class="strong">' + esc(r.conclusion) + '</p>') +
        '</div></div>';
    }).join('');
    $$('[data-ref]').forEach(function (b) {
      b.addEventListener('click', function () {
        var body = $('[data-refbody="' + b.getAttribute('data-ref') + '"]');
        var open = b.getAttribute('aria-expanded') === 'true';
        b.setAttribute('aria-expanded', String(!open));
        body.hidden = open;
      });
    });
  }

  function block(h, body) { return '<div class="ref-block"><h5>' + esc(h) + '</h5>' + body + '</div>'; }

  function renderNotes(result) {
    var order = { medium: 0, low: 1, info: 2 };
    var notes = result.notes.slice().sort(function (a, b) { return (order[a.severity] || 3) - (order[b.severity] || 3); });
    $('#review-host').innerHTML = notes.length ? notes.map(function (p) {
      return '<div class="review-item"><div class="review-sev ' + (p.severity === 'info' ? 'low' : esc(p.severity)) + '"></div>' +
        '<div><div class="h">' + esc(p.heading) + '</div><div class="t">' + esc(p.text) + '</div></div></div>';
    }).join('') : '<div class="notice">' + ico('check') + '<div>No notes on these facts.</div></div>';
  }

  function renderOutline(result) {
    var wp = TAS.workingpaper.generateWorkingPaper(result);
    var rows = [
      ['1', 'Executive conclusion', wp.result.status], ['2', 'Assessee profile', wp.assessee.name],
      ['3', 'Financial data', wp.financials.length + ' figures'], ['4', 'Statutory tests', wp.matrix.length + ' tests'],
      ['5', 'Detailed reasoning', wp.reasoning.length + ' steps'], ['6', 'Section-wise legal references', wp.references.length + ' provisions'],
      ['7', 'Applicability analysis', wp.conclusion.headline], ['8', 'Professional notes', wp.reviewPoints.length + ' note(s)'],
      ['9', 'Conclusion', 'With sign-off block'], ['10', 'Disclaimer', 'Standard firm disclaimer']
    ];
    $('#wp-outline').innerHTML = '<div class="table-wrap"><table class="matrix" style="min-width:0"><thead><tr>' +
      '<th style="width:44px">#</th><th>Section</th><th>Content</th></tr></thead><tbody>' +
      rows.map(function (s) {
        return '<tr><td class="num">' + s[0] + '</td><td class="test-name">' + esc(s[1]) + '</td><td class="reason">' + esc(s[2]) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }

  function renderGate(result) {
    var decided = result.status !== S.INCOMPLETE;
    var named = !!state.get().clientName.trim();
    var ok = decided && named;
    ['#btn-wp-detailed', '#btn-wp-executive', '#btn-wp-word'].forEach(function (s) { $(s).disabled = !ok; });
    var host = $('#gate-notice');
    if (ok) {
      host.innerHTML = '<div class="notice">' + ico('check') + '<div>Ready. The working paper records the decision: <b>' +
        esc(result.status) + '</b>.</div></div>';
    } else {
      host.innerHTML = '<div class="notice notice-warn">' + ico('alert') + '<div>' +
        (!decided ? 'Answer the ' + result.required.length + ' remaining question(s) to reach the decision. '
                  : 'Enter the assessee name — the working paper must identify the assessee. ') +
        '<button type="button" class="btn btn-sm" id="gate-go" style="margin-left:var(--s-2)">Take me there</button></div></div>';
      $('#gate-go').addEventListener('click', function () {
        goTo(!decided ? result.required[0] : { field: 'clientName', panel: 'profile' });
      });
    }
  }

  function renderTrailSummary(result) {
    var t = TAS.state.auditTrail(result);
    $('#trail-summary').innerHTML = '<div class="kv">' +
      kvCell('Tests evaluated', String(t.testsEvaluated.length)) +
      kvCell('Grounds for audit', t.groundsForAudit.length ? String(t.groundsForAudit.length) : 'None') +
      kvCell('Outstanding answers', t.outstanding.length ? String(t.outstanding.length) : 'None') + '</div>';
  }

  function renderStatus(result) {
    var pill = $('#nav-status');
    if (result.status === S.INCOMPLETE) {
      pill.textContent = result.required.length + ' answer' + (result.required.length > 1 ? 's' : '') + ' needed →';
      pill.className = 'pill pill-warn status-btn';
      pill.title = 'Go to the first missing answer';
    } else {
      pill.textContent = result.status;
      pill.className = 'pill ' + pillFor(result.status) + ' status-btn';
      pill.title = 'Open the decision';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

})(window);
