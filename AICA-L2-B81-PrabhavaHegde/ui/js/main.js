/**
 * Shell and router.
 *
 * Routes are hash-based so the whole interface is static files that a
 * PyInstaller bundle can serve without a server-side router.
 *
 *   #/                         file index
 *   #/new                      new assessment, three steps
 *   #/c/<slug>/ledger          the ledger
 *   #/c/<slug>/position        score, bands, struck claims
 *   #/c/<slug>/report          generate and download
 */

import { api, ApiError } from './api.js';
import { h, fill, announce } from './dom.js';
import { renderFiles } from './views/files.js';
import { renderNew } from './views/new.js';
import { renderLedger } from './views/ledger.js';
import { renderPosition } from './views/position.js';
import { renderReport } from './views/report.js';

/** Process-lifetime cache for things that never change while the app runs. */
export const state = {
  meta: null,
  client: null,    // the open client profile
  score: null,     // the latest score payload, kept live by the ledger
};

const SECTIONS = [
  { id: 'ledger', ref: '1', label: 'Ledger' },
  { id: 'position', ref: '2', label: 'Position' },
  { id: 'report', ref: '3', label: 'Report' },
];

export const go = (hash) => { window.location.hash = hash; };

/** Redraw the running score in the top bar without re-rendering the screen. */
export function setScore(score) {
  state.score = score;
  const el = document.getElementById('running-score');
  if (!el || !score) return;
  fill(el,
    h('span', null, 'Score'),
    h('b', null, score.score.toFixed(1)),
    h('span', { 'data-band': score.band, class: 'band' }, score.band));
}

function topbar() {
  const bar = h('header.topbar',
    h('button.wordmark', { on: { click: () => go('#/') } }, 'DPDP Readiness Assessor'));

  if (state.client) {
    bar.append(
      h('div.topbar-client',
        h('span.faint.xs', null, '/'),
        h('span.name', null, state.client.name),
        h('span.xs.faint', null,
          state.client.role === 'fiduciary' ? 'Fiduciary' : 'Processor')));
  }
  bar.append(h('div.topbar-spacer'));
  bar.append(h('div.running-score#running-score'));
  return bar;
}

function rail(active, slug) {
  const nav = h('nav.rail', { 'aria-label': 'Assessment sections' },
    h('div.rail-head', null, 'Working file'));

  for (const s of SECTIONS) {
    nav.append(h('a', {
      href: `#/c/${slug}/${s.id}`,
      'aria-current': s.id === active ? 'page' : null,
    }, h('span.ref', null, s.ref), s.label));
  }

  nav.append(h('div.rail-note', null,
    h('div', null, h('b', null, 'Recorded on this machine.')),
    h('div', { style: 'margin-top:.35rem' },
      'Assessed against stated criteria on the evidence provided.')));
  return nav;
}

function chrome(active, slug, main) {
  const app = document.getElementById('app');
  const shell = [topbar()];
  if (slug) shell.push(h('div.layout', rail(active, slug), main));
  else shell.push(h('div.layout', main));
  fill(app, ...shell);
  setScore(state.score);
}

/** A screen container. Always the #main skip-link target. */
export const mainEl = (...children) =>
  h('main.main#main', { tabindex: '-1' }, ...children);

function errorScreen(err) {
  state.client = null;
  state.score = null;
  chrome(null, null, mainEl(
    h('div.screen-head', h('h1', null, 'Could not load this screen')),
    h('div.notice.notice-struck', h('p', null, err.message)),
    h('button.btn', { on: { click: () => route() } }, 'Try again')));
}

async function route() {
  const raw = (window.location.hash || '#/').slice(1);
  const parts = raw.split('/').filter(Boolean);

  try {
    if (!state.meta) state.meta = await api.meta();

    // #/ and #/new carry no client context.
    if (parts[0] !== 'c') {
      state.client = null;
      state.score = null;
      const main = mainEl();
      chrome(null, null, main);
      if (parts[0] === 'new') await renderNew(main);
      else await renderFiles(main);
      document.title = 'DPDP Readiness Assessor';
      return;
    }

    const slug = parts[1];
    const section = SECTIONS.some((s) => s.id === parts[2]) ? parts[2] : 'ledger';

    if (!state.client || state.client.slug !== slug) {
      state.client = await api.client(slug);
      state.score = null;
    }
    document.title = `${state.client.name} — DPDP Readiness Assessor`;

    const main = mainEl();
    chrome(section, slug, main);

    if (section === 'ledger')         await renderLedger(main, slug);
    else if (section === 'position')  await renderPosition(main, slug);
    else if (section === 'report')    await renderReport(main, slug);

    announce(`${SECTIONS.find((s) => s.id === section).label} — ${state.client.name}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404 && parts[0] === 'c') {
      go('#/');
      return;
    }
    errorScreen(err instanceof Error ? err : new Error(String(err)));
  }
}

window.addEventListener('hashchange', () => {
  route();
  window.scrollTo(0, 0);
});
route();
