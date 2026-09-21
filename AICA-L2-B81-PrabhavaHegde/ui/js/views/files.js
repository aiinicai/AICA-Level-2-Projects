/**
 * Files — the opening screen.
 *
 * An index, the way an audit file index reads. Not a card grid.
 * The strip is one cell per applicable control, filled when assessed: it
 * carries progress and scope size in a single object, so a Processor
 * engagement is visibly shorter than a Fiduciary one.
 */

import { api } from '../api.js';
import { h, fill, formatDate } from '../dom.js';
import { go } from '../main.js';

function strip(answered, total) {
  const el = h('div.strip', { 'aria-hidden': 'true' });
  for (let i = 0; i < total; i += 1) el.append(h('i', { 'data-on': i < answered ? '1' : '0' }));
  return el;
}

function fileRow(c) {
  const done = c.answered >= c.total && c.total > 0;
  return h('button.file-row', {
    type: 'button',
    on: { click: () => go(`#/c/${c.slug}/ledger`) },
  },
    h('div.file-line',
      h('span.file-name', null, c.name),
      h('span.file-meta', null, c.role === 'fiduciary' ? 'Fiduciary' : 'Processor'),
      h('span.file-meta', null, formatDate(c.assessment_date))),
    h('div.file-line-2',
      strip(c.answered, c.total),
      h('span.file-stat', null, h('b', null, `${c.answered} / ${c.total}`), ' assessed'),
      // A score is only meaningful once the file is finished. Until then the
      // interface says where it stopped, rather than implying a result.
      done
        ? [h('span.file-stat', null, h('b', null, c.score.toFixed(1))),
           h('span.band', { 'data-band': c.band }, c.band)]
        : h('span.file-stat.faint', null, '—  In progress')));
}

export async function renderFiles(main) {
  const clients = await api.clients();

  fill(main,
    h('div.files',
      h('div.files-head',
        h('div.screen-head', { style: 'margin:0' },
          h('h1', null, 'DPDP Readiness Assessor'),
          h('p.sub', null,
            clients.length === 1 ? '1 assessment on file' : `${clients.length} assessments on file`)),
        h('button.btn.btn-primary', {
          type: 'button',
          on: { click: () => go('#/new') },
        }, 'New assessment')),

      clients.length
        ? h('div', { role: 'list' }, clients.map((c) => h('div', { role: 'listitem' }, fileRow(c))))
        : h('div.empty', { style: 'margin-top:2rem' },
            h('p', null, 'No assessments on file.'),
            h('p', { style: 'margin-bottom:0' },
              "Start one to record the organisation's profile, settle its role under the Act and open the ledger."))));
}
