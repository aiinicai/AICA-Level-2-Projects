/**
 * Report — one action. Generate, then download.
 *
 * The screen states plainly which provider drafted the finding prose, or that
 * the catalogue text was used. A missing key is not an error condition: the
 * report is produced in full either way.
 */

import { api } from '../api.js';
import { h, fill, toast, announce } from '../dom.js';
import { state, setScore, go } from '../main.js';
import { words } from '../wording.js';

export async function renderReport(main, slug) {
  const [score, controls] = await Promise.all([api.score(slug), api.controls(slug)]);
  setScore(score);
  const w = words();

  const assessed = controls.filter((c) => c.status).length;
  const struck = score.gated_for_no_evidence.length;
  const meta = state.meta;

  const result = h('div', { style: 'margin-top:1.5rem' });
  const btn = h('button.btn.btn-primary', { type: 'button' }, 'Generate report');

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = 'Generating…';
    fill(result, h('p.muted.small', null, 'Drafting the observations and writing the document…'));
    announce('Generating the report.');
    try {
      const res = await api.generateReport(slug, meta.ai_active);
      toast('Report generated.');
      fill(result,
        h('div.notice',
          h('p', null, h('b', null, 'Report generated.'), ` ${res.file}`),
          h('p', { style: 'margin-bottom:0' },
            res.ai_used
              ? `Findings drafted by ${res.provider} — ${res.findings_drafted} observations redrafted. `
                + 'Status, score and band were computed from the catalogue and are not model output.'
              : 'Findings use the catalogue text. AI drafting was not active for this run.')),
        h('div.row-actions', { style: 'margin-top:1rem' },
          h('a.btn.btn-primary', { href: api.downloadUrl(slug), download: '' }, 'Download the report'),
          h('button.btn.btn-quiet', {
            type: 'button',
            on: { click: () => { btn.disabled = false; btn.textContent = 'Generate again'; } },
          }, 'Generate again')));
    } catch (e) {
      fill(result, h('div.notice.notice-struck', h('p', { style: 'margin:0' }, e.message)));
      btn.disabled = false;
      btn.textContent = 'Generate report';
    }
  });

  fill(main,
    h('div', { style: 'max-width:52rem' },
      h('div.screen-head',
        h('h1', null, 'Report'),
        h('p.sub', null, state.client.name)),

      h('div.tw',
        h('table.ruled',
          h('tbody',
            h('tr', h('th', { style: 'width:16rem' }, w.entityRow), h('td', state.client.name)),
            h('tr', h('th', null, 'Entity type'), h('td', state.client.entity_type)),
            h('tr', h('th', null, w.roleRow),
              h('td', state.client.role === 'fiduciary' ? 'Data Fiduciary' : 'Data Processor')),
            h('tr', h('th', null, 'Report type'), h('td', w.reportKind)),
            h('tr', h('th', null, 'Controls assessed'),
              h('td', `${assessed} of ${controls.length}`)),
            h('tr', h('th', null, 'Readiness score'),
              h('td', `${score.score.toFixed(1)} — ${score.band}`)),
            h('tr', h('th', null, 'Claims struck for want of evidence'),
              h('td', struck
                ? h('span.risk-mark', null, String(struck))
                : h('span.faint', null, 'None'))),
            h('tr', h('th', null, 'Finding prose'),
              h('td', meta.ai_active
                ? `Drafted by ${meta.ai_provider}. Status, score and band are computed, never modelled.`
                : 'Catalogue text. AI drafting is off (no GEMINI_API_KEY set), and none is required.'))))),

      assessed < controls.length
        ? h('div.notice', { style: 'margin-top:1.5rem' },
            h('p', { style: 'margin:0' },
              `${controls.length - assessed} controls have not been assessed. They will be `
              + 'reported as Absent. ',
              h('button.btn.btn-quiet', {
                type: 'button', style: 'padding:.1rem .5rem',
                on: { click: () => go(`#/c/${slug}/ledger`) },
              }, 'Return to the ledger')))
        : null,

      struck
        ? h('div.notice.notice-struck', { style: 'margin-top:1rem' },
            h('p', { style: 'margin:0' },
              struck === 1
                ? '1 claim was struck for want of evidence and scored nil. '
                : `${struck} claims were struck for want of evidence and scored nil. `,
              'They are listed separately in the report.'))
        : null,

      h('p.prose.small.muted', { style: 'margin-top:1.5rem' }, w.reportProse),

      h('div.row-actions', { style: 'margin-top:1rem' }, btn),
      result));
}
