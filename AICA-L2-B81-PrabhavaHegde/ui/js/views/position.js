/**
 * Position — score, band, rule-wise breakdown, and the struck list.
 *
 * The struck list is the most useful screen for the closing meeting. It is the
 * shortest route from "we have all this" to "then show me", so it leads.
 */

import { api } from '../api.js';
import { h, fill, ruleOrder } from '../dom.js';
import { state, setScore, go } from '../main.js';
import { words } from '../wording.js';

export async function renderPosition(main, slug) {
  const [score, controls] = await Promise.all([api.score(slug), api.controls(slug)]);
  setScore(score);

  const byId = new Map(controls.map((c) => [c.id, c]));
  // The catalogue orders ids lexically, which puts R11 ahead of R3. The closing
  // meeting works down the rules in order, so the struck list must too.
  const struck = score.gated_for_no_evidence
    .map((id) => byId.get(id))
    .filter(Boolean)
    .sort((a, b) => ruleOrder(a.rule_id) - ruleOrder(b.rule_id) || a.id.localeCompare(b.id));
  const assessed = controls.filter((c) => c.status).length;
  const unassessed = controls.length - assessed;
  const w = words();

  const byRule = [...score.by_rule].sort((a, b) => ruleOrder(a.rule_id) - ruleOrder(b.rule_id));

  fill(main,
    h('div', { style: 'max-width:62rem' },
      h('div.screen-head',
        h('h1', null, 'Position'),
        h('p.sub', null, `${state.client.name} · ${assessed} of ${controls.length} controls assessed`)),

      h('div.pos-head',
        h('div',
          h('div.pos-label', null, 'Readiness score'),
          h('div.pos-score', { 'data-band': score.band }, score.score.toFixed(1))),
        h('div',
          h('div.pos-label', null, 'Band'),
          h('div', { style: 'font-size:1.1875rem;font-weight:600' }, score.band)),
        h('div',
          h('div.pos-label', null, 'Weight earned'),
          h('div', { style: 'font-size:1.1875rem;font-weight:600' },
            `${score.earned} / ${score.available}`)),
        h('div',
          h('div.pos-label', null, 'Claims struck'),
          h('div', {
            style: `font-size:1.1875rem;font-weight:600${struck.length ? ';color:var(--struck)' : ''}`,
          }, String(struck.length)))),

      // An unanswered control counts in the score at nil. Said beside the score,
      // in ink, so a score that fell because controls were added is explained.
      unassessed > 0 ? h('p.prose.small', null, h('b', null, w.unassessedNote(unassessed))) : null,

      h('p.prose.small.muted', null,
        'Assessed against stated criteria on the evidence provided. The score is weighted '
        + 'by control, and a control at weight 4 or above earns nothing without an attached '
        + 'evidence file, whatever status was recorded.'),

      /* -- struck claims -------------------------------------------------- */

      h('h2.h-sec', null, 'Claims struck for want of evidence'),

      struck.length
        ? h('div',
            h('p.prose.small.muted', null,
              'Each of these was recorded as Present or Partial and scored nil because nothing '
              + 'was produced. Attaching the document named against the control restores its weight.'),
            h('div.tw',
              h('table.ruled',
                h('thead', h('tr',
                  h('th', { style: 'width:4rem' }, 'Ref'),
                  h('th', null, 'Control'),
                  h('th', { style: 'width:5rem' }, 'Claimed'),
                  h('th', { class: 'num', style: 'width:4rem' }, 'Weight'),
                  h('th', null, 'Evidence sought'))),
                h('tbody', struck.map((c) => h('tr', { 'data-risk': '1' },
                  h('td', h('b', null, c.id)),
                  h('td', c.title),
                  h('td', h('span.risk-mark', null, c.status)),
                  h('td.num', String(c.weight)),
                  h('td.muted', (c.evidence_required || []).join('; '))))))))
        : h('div.empty',
            h('p', { style: 'margin:0' },
              assessed === 0
                ? 'Nothing assessed yet, so nothing has been struck.'
                : 'No claim has been struck. Every control recorded as Present or Partial at '
                  + 'weight 4 or above carries an attached file.')),

      /* -- rule-wise ------------------------------------------------------ */

      h('h2.h-sec', null, 'Rule-wise position'),
      h('div.tw',
        h('table.ruled',
          h('thead', h('tr',
            h('th', { style: 'width:4rem' }, 'Rule'),
            h('th', null, 'Title'),
            h('th', { class: 'num' }, 'Present'),
            h('th', { class: 'num' }, 'Partial'),
            h('th', { class: 'num' }, 'Absent'),
            h('th', { class: 'num' }, 'Struck'),
            h('th', { class: 'num' }, 'Weight'))),
          h('tbody', byRule.map((r) => {
            const s = struck.filter((c) => c.rule_id === r.rule_id).length;
            return h('tr',
              h('td', h('b', null, r.rule_id)),
              h('td', r.title),
              h('td.num', String(r.Present)),
              h('td.num', String(r.Partial)),
              h('td.num', String(r.Absent)),
              h('td.num', s ? h('span.risk-mark', null, String(s)) : h('span.faint', null, '—')),
              h('td.num', String(r.weight)));
          })))),

      h('div.row-actions', { style: 'margin-top:2rem' },
        h('button.btn', {
          type: 'button', on: { click: () => go(`#/c/${slug}/ledger`) },
        }, 'Back to the ledger'),
        h('button.btn.btn-quiet', {
          type: 'button', on: { click: () => go(`#/c/${slug}/report`) },
        }, 'Go to report'))));
}
