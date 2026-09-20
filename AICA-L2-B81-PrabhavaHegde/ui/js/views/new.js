/**
 * New assessment — three steps: profile, role, determination.
 *
 * Step 3 is never skipped into the ledger. The role decides which controls
 * apply, and the assessor has to see and accept that before starting.
 */

import { api } from '../api.js';
import { h, fill, field, textInput, select, toast, announce } from '../dom.js';
import { state, go } from '../main.js';
import { words } from '../wording.js';

const STEPS = ['Profile', 'Role', 'Determination'];

function stepbar(current) {
  return h('ol.steps',
    STEPS.map((label, i) => h('li', {
      'aria-current': i === current ? 'step' : null,
      'data-done': i < current ? '1' : null,
    }, h('span.n', null, `${i + 1}`), ` ${label}`)));
}

/* -- Step 1: profile ----------------------------------------------------- */

function stepProfile(main, draft, next) {
  const today = new Date().toISOString().slice(0, 10);
  const name = textInput('name', draft.name || '', { required: true, autocomplete: 'off' });
  const entity = select('entity_type', state.meta.entity_types, draft.entity_type);
  const sector = textInput('sector', draft.sector || '');
  const contact = textInput('contact_person', draft.contact_person || '');
  const by = textInput('assessed_by', draft.assessed_by || '');
  const when = h('input', { type: 'date', name: 'assessment_date', value: draft.assessment_date || today });

  const w = words();

  const nameErr = h('div.err', { id: 'name-err', hidden: true });

  const form = h('form', {
    novalidate: true,
    on: {
      submit: (e) => {
        e.preventDefault();
        if (!name.value.trim()) {
          // Inline error, at the field, with focus moved to it.
          const message = w.entityNameError;
          nameErr.textContent = message;
          nameErr.hidden = false;
          name.setAttribute('aria-invalid', 'true');
          name.setAttribute('aria-describedby', 'name-err');
          name.focus();
          announce(message);
          return;
        }
        Object.assign(draft, {
          name: name.value.trim(),
          entity_type: entity.value,
          sector: sector.value.trim() || null,
          contact_person: contact.value.trim() || null,
          assessed_by: by.value.trim() || null,
          assessment_date: when.value || today,
          flags: [],
        });
        next();
      },
      input: () => {
        if (name.value.trim() && !nameErr.hidden) {
          nameErr.hidden = true;
          name.removeAttribute('aria-invalid');
          name.removeAttribute('aria-describedby');
        }
      },
    },
  },
    field(w.entityName, name, { required: true }),
    nameErr,
    field('Entity type', entity, { required: true }),
    field('Sector', sector),
    field('Contact person', contact),
    field(w.assessedBy, by),
    field('Date of assessment', when, { required: true }),

    h('div.row-actions', { style: 'margin-top:1.5rem' },
      h('button.btn.btn-primary', { type: 'submit' }, 'Continue to role'),
      h('button.btn.btn-quiet', { type: 'button', on: { click: () => go('#/') } }, 'Cancel')));

  fill(main,
    h('div.screen-head', h('h1', null, w.newTitle)),
    stepbar(0), form);
  name.focus();
}

/* -- Step 2: role -------------------------------------------------------- */

async function stepRole(main, draft, next, back) {
  const { questions, note } = await api.roleQuestions();
  const answers = { ...(draft.answers || {}) };
  const err = h('div.err', { hidden: true });

  const rows = questions.map((q) => {
    const mk = (label, val) => h('button', {
      type: 'button',
      'aria-pressed': answers[q.id] === val ? 'true' : 'false',
      'aria-label': `${q.id}: ${label}`,
      on: {
        click: (e) => {
          answers[q.id] = val;
          const grp = e.currentTarget.parentElement;
          for (const b of grp.children) b.setAttribute('aria-pressed', 'false');
          e.currentTarget.setAttribute('aria-pressed', 'true');
          err.hidden = true;
        },
      },
    }, label);

    return h('div.qrow',
      h('div', h('span.qref', null, q.id), h('p', null, q.text)),
      h('div.yesno', { role: 'group', 'aria-label': q.text }, mk('Yes', true), mk('No', false)));
  });

  fill(main,
    h('div.screen-head', h('h1', null, words().roleTitle),
      h('p.sub', null, draft.name)),
    stepbar(1),
    h('div.notice', h('p', null, note)),
    h('div', { style: 'max-width:48rem' }, rows),
    err,
    h('div.row-actions', { style: 'margin-top:1.5rem' },
      h('button.btn.btn-primary', {
        type: 'button',
        on: {
          click: () => {
            const missing = questions.filter((q) => !(q.id in answers)).map((q) => q.id);
            if (missing.length) {
              err.textContent = `Answer every question before continuing. Outstanding: ${missing.join(', ')}.`;
              err.hidden = false;
              announce(err.textContent);
              return;
            }
            draft.answers = answers;
            next();
          },
        },
      }, 'Determine role'),
      h('button.btn.btn-quiet', { type: 'button', on: { click: back } }, 'Back')));
}

/* -- Step 3: determination ----------------------------------------------- */

async function stepDetermination(main, draft, back) {
  const w = words();
  fill(main,
    h('div.screen-head', h('h1', null, 'Determination')),
    stepbar(2),
    h('p.muted', null, 'Creating the working file…'));

  let slug;
  try {
    ({ slug } = await api.createClient(draft));
  } catch (e) {
    fill(main,
      h('div.screen-head', h('h1', null, 'Determination')),
      stepbar(2),
      h('div.notice.notice-struck', h('p', null, e.message)),
      h('button.btn', { type: 'button', on: { click: back } }, 'Back'));
    return;
  }

  const finding = await api.submitRole(slug, draft.answers);
  const scope = state.meta.rules; // control counts come from the ledger itself

  fill(main,
    h('div.screen-head', h('h1', null, 'Determination'),
      h('p.sub', null, draft.name)),
    stepbar(2),

    h('div.determination',
      h('div.role-label', null, w.roleLabel),
      h('div.role', null, finding.role === 'fiduciary' ? 'Data Fiduciary' : 'Data Processor'),
      // Report prose, displayed as prose. Not a badge.
      h('p.reasoning', null, finding.reasoning)),

    finding.borderline
      ? h('div.notice', h('p', null, w.borderlineNote))
      : null,

    h('p.prose.muted.small', null,
      'The role decides which controls apply. Accepting it opens the ledger.'),

    h('div.row-actions', { style: 'margin-top:1.5rem' },
      h('button.btn.btn-primary', {
        type: 'button',
        on: {
          click: () => {
            toast('Working file created.');
            go(`#/c/${slug}/ledger`);
          },
        },
      }, 'Accept and open the ledger')));

  void scope;
}

/* -- Flow ---------------------------------------------------------------- */

export async function renderNew(main) {
  const draft = { entity_type: state.meta.entity_types[0], flags: [] };
  const profile = () => stepProfile(main, draft, role);
  const role = () => stepRole(main, draft, determination, profile);
  const determination = () => stepDetermination(main, draft, role);
  profile();
}
