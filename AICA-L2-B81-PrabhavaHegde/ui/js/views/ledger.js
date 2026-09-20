/**
 * The ledger — the main screen, where 90% of the assessment time is spent.
 *
 * Two things govern every decision in this file:
 *
 *  1. Autosave. There is no save button. A status change writes immediately
 *     and the response carries the live score.
 *  2. The struck state. When a heavyweight control is claimed with nothing
 *     attached, the row changes the moment it happens — not silently at report
 *     time. The assessor must see that their input was recorded and then
 *     discounted, not ignored.
 */

import { api } from '../api.js';
import { h, fill, toast, announce, debounce, ruleOrder } from '../dom.js';
import { state, setScore } from '../main.js';
import { words } from '../wording.js';

const STATUSES = ['Present', 'Partial', 'Absent'];
const KEY_TO_STATUS = { p: 'Present', r: 'Partial', a: 'Absent' };

export async function renderLedger(main, slug) {
  const w = words();
  const [controls, score, evidence] = await Promise.all([
    api.controls(slug),
    api.score(slug),
    api.evidence(slug),
  ]);
  setScore(score);

  const evByControl = new Map();
  for (const e of evidence) {
    if (!evByControl.has(e.control_id)) evByControl.set(e.control_id, []);
    evByControl.get(e.control_id).push(e);
  }

  // Rule order is numeric. R10 follows R9, it does not sit between R1 and R2.
  const rules = [...new Set(controls.map((c) => c.rule_id))]
    .sort((a, b) => ruleOrder(a) - ruleOrder(b));

  const rows = [];            // in visual order, for J/K navigation
  let focused = -1;

  /* -- filtering -------------------------------------------------------- */

  const filter = { q: '', view: 'all' };

  function matches(c) {
    if (filter.view === 'unassessed' && c.status) return false;
    if (filter.view === 'struck' && !c.evidence_missing) return false;
    if (filter.view === 'gate' && !c.needs_evidence) return false;
    if (!filter.q) return true;
    const hay = `${c.id} ${c.title} ${c.question} ${c.rule_title}`.toLowerCase();
    return hay.includes(filter.q.toLowerCase());
  }

  function applyFilter() {
    let shown = 0;
    for (const r of rows) {
      const ok = matches(r.c);
      r.el.hidden = !ok;
      if (ok) shown += 1;
    }
    for (const g of groups) {
      g.el.hidden = !g.rows.some((r) => !r.el.hidden);
    }
    countEl.textContent = shown === controls.length
      ? `${controls.length} controls`
      : `${shown} of ${controls.length} controls`;
    emptyEl.hidden = shown > 0;
  }

  /* -- focus ------------------------------------------------------------ */

  /**
   * The focused control follows the document, not a remembered index. Clicking
   * Guidance or Attach file inside a row puts focus on that button; without
   * this, the next P/R/A keystroke would mark a different control.
   */
  function markFocused(row) {
    for (const r of rows) r.el.removeAttribute('data-focused');
    if (!row) { focused = -1; return; }
    row.el.setAttribute('data-focused', '1');
    focused = rows.indexOf(row);
  }

  function currentRow() {
    const host = document.activeElement?.closest?.('.ldg-row');
    const byFocus = host && rows.find((r) => r.el === host);
    if (byFocus) { if (rows[focused] !== byFocus) markFocused(byFocus); return byFocus; }
    return rows[focused];
  }

  function focusRow(i, { scroll = true } = {}) {
    const visible = rows.filter((r) => !r.el.hidden);
    if (!visible.length) return;
    const target = rows[i] && !rows[i].el.hidden
      ? rows[i]
      : visible[Math.max(0, Math.min(visible.length - 1, 0))];
    markFocused(target);
    target.el.focus({ preventScroll: !scroll });
  }

  function move(delta) {
    const visible = rows.filter((r) => !r.el.hidden);
    if (!visible.length) return;
    const here = visible.indexOf(currentRow());
    const nextIdx = here === -1
      ? 0
      : Math.max(0, Math.min(visible.length - 1, here + delta));
    focusRow(rows.indexOf(visible[nextIdx]));
  }

  /* -- persistence ------------------------------------------------------ */

  // Only called once a status exists (see paintNotesLock below). Defaulting a
  // missing status here would record a determination nobody made.
  function body(c) {
    return {
      status: c.status,
      assessor_note: c.assessor_note || '',
      mgmt_response: c.mgmt_response || '',
      mgmt_owner: c.mgmt_owner || '',
      mgmt_target_date: c.mgmt_target_date || '',
    };
  }

  async function save(row, { announceAs } = {}) {
    const c = row.c;
    if (!c.status) return;   // nothing to save until the control is assessed
    try {
      const res = await api.saveControl(slug, c.id, body(c));
      setScore(res.score);
      if (announceAs) announce(announceAs);
    } catch (e) {
      toast(e.message, 'struck');
    }
  }

  /* -- the struck state ------------------------------------------------- */

  function recomputeStruck(row, { quiet = false } = {}) {
    const c = row.c;
    const was = row.struckShown;
    c.evidence_missing = c.needs_evidence
      && c.evidence_count === 0
      && (c.status === 'Present' || c.status === 'Partial');

    row.el.setAttribute('data-struck', c.evidence_missing ? '1' : '0');
    row.strikeNote.hidden = !c.evidence_missing;
    row.count.setAttribute('data-zero', c.evidence_count === 0 ? '1' : '0');
    row.count.textContent = c.evidence_count === 1
      ? '1 attached' : `${c.evidence_count} attached`;
    row.struckShown = c.evidence_missing;

    // Announced only on the transition, so a run of status changes does not
    // produce a stream of identical messages, and a reopened file does not
    // greet the assessor with a queue of them.
    if (c.evidence_missing && !was && !quiet) {
      toast(`${c.id} claimed without evidence — scored nil.`, 'struck');
    }
  }

  /* -- one control row --------------------------------------------------- */

  function buildRow(c) {
    const row = { c, struckShown: false };

    /* status — the filled ink mark */
    const statusBtns = STATUSES.map((s) => h('button', {
      type: 'button',
      'data-v': s,
      'aria-pressed': c.status === s ? 'true' : 'false',
      'aria-label': `${c.id}: ${s}`,
      on: { click: () => setStatus(s) },
    }, s));

    function setStatus(s) {
      c.status = s;
      for (const b of statusBtns) b.setAttribute('aria-pressed', b.dataset.v === s ? 'true' : 'false');
      row.paintNotesLock();
      recomputeStruck(row);
      save(row, { announceAs: `${c.id} ${s}${c.evidence_missing ? ', claimed without evidence, scored nil' : ''}` });
    }
    row.setStatus = setStatus;

    /* evidence */
    const count = h('span.count', {
      'data-zero': c.evidence_count === 0 ? '1' : '0',
    }, c.evidence_count === 1 ? '1 attached' : `${c.evidence_count} attached`);
    row.count = count;

    const fileInput = h('input', {
      type: 'file', hidden: true,
      on: { change: (e) => { if (e.target.files[0]) upload(e.target.files[0]); e.target.value = ''; } },
    });

    const evList = h('ul.ev-list');
    function paintEvidence() {
      fill(evList, (evByControl.get(c.id) || []).map((e) => h('li', null, e.filename)));
    }
    paintEvidence();

    async function upload(file) {
      // The server refuses this too (evidence belongs to an answer); saying it
      // here saves a round trip and keeps the file picker from looking broken.
      if (!c.status) {
        toast(`Choose a status for ${c.id} before attaching evidence.`);
        announce(`Choose a status for ${c.id} before attaching evidence.`);
        return;
      }
      try {
        const res = await api.uploadEvidence(slug, c.id, file);
        c.evidence_count = res.evidence_count;
        setScore(res.score);
        if (!evByControl.has(c.id)) evByControl.set(c.id, []);
        evByControl.get(c.id).push({ control_id: c.id, filename: file.name });
        paintEvidence();
        recomputeStruck(row);
        announce(`${file.name} attached to ${c.id}.`);
        toast(`${file.name} attached to ${c.id}.`);
      } catch (e) {
        toast(e.message, 'struck');
      }
    }
    row.pickFile = () => fileInput.click();

    const dropzone = h('div.dropzone', {
      on: {
        dragover: (e) => { e.preventDefault(); dropzone.setAttribute('data-over', '1'); },
        dragleave: () => dropzone.removeAttribute('data-over'),
        drop: (e) => {
          e.preventDefault();
          dropzone.removeAttribute('data-over');
          if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]);
        },
      },
    },
      h('button.btn.btn-quiet', {
        type: 'button',
        style: 'padding:.15rem .6rem',
        on: { click: () => fileInput.click() },
      }, 'Attach file'),
      h('span.xs', null, 'or drop one here'),
      count, fileInput);

    /* the reason line — what happened, and what fixes it */
    const strikeNote = h('div.strike-note', { hidden: true },
      h('b', null, 'Claimed without evidence — scored nil.'),
      ' Attach the configuration or policy extract to score this control.');
    row.strikeNote = strikeNote;

    /* guidance, on demand */
    const guidance = h('div.guidance', { hidden: true }, c.guidance.trim());
    const gBtn = h('button', {
      type: 'button', 'aria-expanded': 'false',
      on: { click: () => toggleGuidance() },
    }, 'Guidance');
    function toggleGuidance(force) {
      const open = force ?? guidance.hidden;
      guidance.hidden = !open;
      gBtn.setAttribute('aria-expanded', String(open));
    }
    row.toggleGuidance = toggleGuidance;

    /* note and response — two separate things */
    const saveNotes = debounce(() => save(row), 700);

    const noteBox = h('textarea', {
      'aria-label': `${w.noteLabel} for ${c.id}`,
      on: {
        input: (e) => { c.assessor_note = e.target.value; saveNotes(); },
        blur: () => saveNotes.flush(),
      },
    });
    noteBox.value = c.assessor_note || '';

    const mgmtBox = h('textarea', {
      'aria-label': `${w.responseLabel} for ${c.id}`,
      on: {
        input: (e) => { c.mgmt_response = e.target.value; saveNotes(); },
        blur: () => saveNotes.flush(),
      },
    });
    mgmtBox.value = c.mgmt_response || '';

    const ownerBox = h('input', {
      type: 'text', 'aria-label': `${w.ownerLabel} for ${c.id}`, placeholder: w.ownerLabel,
      on: { input: (e) => { c.mgmt_owner = e.target.value; saveNotes(); }, blur: () => saveNotes.flush() },
    });
    ownerBox.value = c.mgmt_owner || '';

    const dateBox = h('input', {
      type: 'date', 'aria-label': `${w.targetLabel} for ${c.id}`,
      on: { input: (e) => { c.mgmt_target_date = e.target.value; saveNotes(); }, blur: () => saveNotes.flush() },
    });
    dateBox.value = c.mgmt_target_date || '';

    /*
     * Notes wait for a status. A note is saved together with the control's
     * answer, and the record has no answer without a status, so typing into an
     * unassessed control would otherwise have to invent one (it used to save
     * "Absent" under the person's name while the row still showed unassessed).
     * The fields stay visible but read-only, with the reason beside them, and
     * open the moment a status is chosen.
     */
    const lockHint = h('p.small.muted.notes-lock', { hidden: true },
      `Choose a status for ${c.id} first. ${w.noteLabel} and the fields beside it open once it is assessed.`);
    row.paintNotesLock = () => {
      const locked = !c.status;
      for (const box of [noteBox, mgmtBox, ownerBox, dateBox]) box.disabled = locked;
      lockHint.hidden = !locked;
    };

    const panes = h('div.panes', { hidden: true },
      lockHint,
      h('div.pane',
        h('div.hd', null, w.noteLabel,
          h('span.note', null, w.noteHint)),
        noteBox),
      h('div.pane.pane-mgmt',
        h('div.hd', null, w.responseLabel,
          h('span.note', null, w.responseHint)),
        mgmtBox,
        h('div.mgmt-grid', ownerBox, dateBox)));

    const nBtn = h('button', {
      type: 'button', 'aria-expanded': 'false',
      on: { click: () => togglePanes() },
    }, w.notesButton);

    function togglePanes(force) {
      const open = force ?? panes.hidden;
      panes.hidden = !open;
      nBtn.setAttribute('aria-expanded', String(open));
      if (open) (c.status ? noteBox : statusBtns[0]).focus();
      if (open && !c.status) announce(lockHint.textContent);
    }
    row.paintNotesLock();
    row.togglePanes = togglePanes;

    const marks = [];
    if (c.assessor_note) marks.push(w.noteMark);
    if (c.mgmt_response) marks.push(w.responseMark);

    const el = h('article.ldg-row', {
      tabindex: '0',
      id: `ctl-${c.id}`,
      'data-struck': '0',
      'aria-label': `${c.id} ${c.title}`,
    },
      h('div.ldg-ref', null, c.id),
      h('div.ldg-body',
        h('div.ldg-title-line',
          h('h3.ldg-title', null, c.title),
          h('span.ldg-weight', { 'data-gate': c.needs_evidence ? '1' : null,
                                 title: c.needs_evidence
                                   ? 'Weight 4 or above — scores nil without evidence'
                                   : 'Weight below the evidence gate' },
            `w${c.weight}${c.needs_evidence ? ' · gated' : ''}`),
          c.citation_status === 'pending'
            ? h('span.ldg-cite', { title: 'The legal citation for this control has not yet been checked against the gazette text.' },
                'Citation pending verification')
            : null),
        h('p.ldg-q', null, c.question),

        h('div.ldg-controls',
          h('div.status', { role: 'group', 'aria-label': `Status for ${c.id}` }, statusBtns),
          h('div.ldg-tools', gBtn, nBtn,
            marks.length ? h('span.mark', null, h('b', null, marks.join(' · '))) : null)),

        strikeNote,

        c.evidence_required?.length
          ? h('div.ev-sought',
              h('span.lbl', null, 'Evidence sought: '), c.evidence_required.join('; '))
          : null,

        dropzone, evList, guidance, panes));

    row.el = el;
    recomputeStruck(row, { quiet: true });   // first paint never toasts
    return row;
  }

  /* -- groups ------------------------------------------------------------ */

  const groups = rules.map((rid) => {
    const inRule = controls.filter((c) => c.rule_id === rid);
    const first = inRule[0];
    const built = inRule.map(buildRow);
    rows.push(...built);

    const counter = h('span.rcount');
    const g = {
      rid,
      rows: built,
      counter,
      el: h('section.rule-group', { 'aria-labelledby': `rh-${rid}` },
        h('div.rule-head',
          h('span.rid', null, rid),
          h('h2.rtitle', { id: `rh-${rid}` }, first.rule_title),
          counter,
          h('span.rref', null, first.rule_ref)),
        built.map((r) => r.el)),
    };
    return g;
  });

  function paintCounters() {
    for (const g of groups) {
      const done = g.rows.filter((r) => r.c.status).length;
      g.counter.textContent = `${done} / ${g.rows.length} assessed`;
    }
  }
  paintCounters();

  // Keep the rule counters and the file strip honest as statuses change.
  const origSave = save;
  save = async (row, opts) => { await origSave(row, opts); paintCounters(); };

  /* -- bar -------------------------------------------------------------- */

  const countEl = h('span.small.muted');
  const emptyEl = h('div.empty', { hidden: true },
    h('p', { style: 'margin:0' }, 'No control matches this filter.'));

  const search = h('input', {
    type: 'text', 'aria-label': 'Search controls',
    placeholder: 'Search controls',
    on: { input: (e) => { filter.q = e.target.value; applyFilter(); } },
  });

  const viewSel = h('select', {
    'aria-label': 'Filter the ledger',
    on: { change: (e) => { filter.view = e.target.value; applyFilter(); } },
  },
    h('option', { value: 'all' }, 'All controls'),
    h('option', { value: 'unassessed' }, 'Not yet assessed'),
    h('option', { value: 'struck' }, 'Struck for want of evidence'),
    h('option', { value: 'gate' }, 'Evidence-gated only'));

  const answered = controls.filter((c) => c.status).length;
  const firstOpen = controls.findIndex((c) => !c.status);

  const bar = h('div.ledger-bar',
    h('div.f', search),
    h('div.f', viewSel),
    countEl,
    h('div.topbar-spacer'),
    // Shown once, unobtrusively. Never a modal.
    h('div.keys',
      h('span', null, h('kbd', null, 'P'), ' ', h('kbd', null, 'R'), ' ', h('kbd', null, 'A'), ' status'),
      h('span', null, h('kbd', null, 'J'), ' ', h('kbd', null, 'K'), ' move'),
      h('span', null, h('kbd', null, 'N'), ' note'),
      h('span', null, h('kbd', null, 'G'), ' guidance'),
      h('span', null, h('kbd', null, 'E'), ' evidence'),
      h('span', null, h('kbd', null, '/'), ' search')));

  /* -- resume line — where the file stopped ------------------------------ */

  const resume = answered === 0
    ? h('div.notice', h('p', null,
        `Nothing assessed yet. ${controls.length} controls apply to ${w.scopePhrase}.`))
    : firstOpen === -1
      ? h('div.notice', h('p', null,
          `All ${controls.length} controls assessed. Review the position before generating the report.`))
      : h('div.notice',
          h('p', { style: 'margin:0' },
            `Stopped at ${answered} of ${controls.length}. `,
            h('button.btn.btn-quiet', {
              type: 'button', style: 'padding:.1rem .5rem;margin-left:.25rem',
              on: { click: () => focusRow(firstOpen) },
            }, `Resume at ${controls[firstOpen].id}`)));

  fill(main,
    h('div.ledger',
      h('div.screen-head',
        h('h1', null, 'Ledger'),
        h('p.sub', null,
          `${state.client.name} · `,
          state.client.role === 'fiduciary' ? 'Data Fiduciary' : 'Data Processor',
          ` · ${controls.length} applicable controls`)),
      bar, resume,
      groups.map((g) => g.el),
      emptyEl,
      h('div.ldg-foot', null,
        'Every change is written to the working file as it is made. There is no save step. '
        + 'Assessed against stated criteria on the evidence provided.')));

  applyFilter();

  // focusin bubbles, so this catches focus landing on a row or on any control
  // inside one — which is what keeps the marked row and the keyboard in step.
  main.addEventListener('focusin', (e) => {
    const host = e.target.closest?.('.ldg-row');
    const row = host && rows.find((r) => r.el === host);
    if (row) markFocused(row);
  });

  /* -- keyboard ---------------------------------------------------------- */

  const onKey = (e) => {
    if (!main.isConnected) { document.removeEventListener('keydown', onKey); return; }
    const t = e.target;
    const typing = t instanceof HTMLElement
      && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT');

    if (e.key === 'Escape' && typing) { t.blur(); if (focused >= 0) focusRow(focused, { scroll: false }); return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;

    if (e.key === '/') { e.preventDefault(); search.focus(); search.select(); return; }
    if (e.key === 'j' || e.key === 'ArrowDown') { e.preventDefault(); move(1); return; }
    if (e.key === 'k' || e.key === 'ArrowUp') { e.preventDefault(); move(-1); return; }

    const row = currentRow();
    if (!row || row.el.hidden) return;

    const key = e.key.toLowerCase();
    if (KEY_TO_STATUS[key]) { e.preventDefault(); row.setStatus(KEY_TO_STATUS[key]); }
    else if (key === 'n') { e.preventDefault(); row.togglePanes(true); }
    else if (key === 'g') { e.preventDefault(); row.toggleGuidance(); }
    else if (key === 'e') { e.preventDefault(); row.pickFile(); }
  };
  document.addEventListener('keydown', onKey);

  // A half-finished file opens where it stopped.
  if (firstOpen !== -1 && answered > 0) focusRow(firstOpen);
}
