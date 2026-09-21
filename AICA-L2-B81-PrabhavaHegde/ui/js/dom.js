/**
 * A small DOM helper. Deliberately not a framework — the tool ships as plain
 * files inside a PyInstaller bundle and must not acquire a build step.
 */

/**
 * h('div.cls', { attrs }, ...children)
 * Attribute keys are written as they appear in HTML ('aria-label', 'data-on').
 * `on` takes an object of event handlers. Strings are escaped as text nodes.
 */
export function h(spec, attrs, ...children) {
  // tag, .class (repeatable) and a trailing #id, in any order after the tag.
  const parts = String(spec).split(/(?=[.#])/);
  const tag = parts[0].startsWith('.') || parts[0].startsWith('#') ? 'div' : parts[0];
  const el = document.createElement(tag || 'div');
  const classes = [];
  for (const p of parts) {
    if (p.startsWith('.')) classes.push(p.slice(1));
    else if (p.startsWith('#')) el.id = p.slice(1);
  }
  if (classes.length) el.className = classes.join(' ');

  if (attrs && (attrs.constructor === Object)) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'on') {
        for (const [evt, fn] of Object.entries(v)) el.addEventListener(evt, fn);
      } else if (k === 'class') {
        el.className = el.className ? `${el.className} ${v}` : v;
      } else if (k === 'html') {
        el.innerHTML = v;                       // only ever used with literals in this codebase
      } else if (k === 'text') {
        el.textContent = v;
      } else if (k in el && (k === 'value' || k === 'checked' || k === 'disabled' || k === 'type')) {
        el[k] = v;
      } else {
        el.setAttribute(k, v === true ? '' : String(v));
      }
    }
  } else if (attrs !== null && attrs !== undefined) {
    children.unshift(attrs);
  }

  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    if (Array.isArray(c)) append(el, c);
    else el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

/** Replace an element's children in one pass. */
export function fill(el, ...children) {
  el.replaceChildren();
  append(el, children);
  return el;
}

/** A labelled form field. Every input gets a real <label for>, never a placeholder. */
let uid = 0;
export function field(label, input, { hint, required } = {}) {
  const id = input.id || `f${++uid}`;
  input.id = id;
  const lbl = h('label.field', { for: id },
    h('span', null, label, required ? null : h('span.req', null, ' (optional)')));
  lbl.append(input);
  if (hint) lbl.append(h('div.xs.faint', { style: 'margin-top:.25rem' }, hint));
  return lbl;
}

export function textInput(name, value = '', attrs = {}) {
  return h('input', { type: 'text', name, value, ...attrs });
}

export function select(name, options, value) {
  const el = h('select', { name });
  for (const o of options) {
    const opt = typeof o === 'string' ? { value: o, label: o } : o;
    el.append(h('option', { value: opt.value, selected: opt.value === value }, opt.label));
  }
  el.value = value ?? (typeof options[0] === 'string' ? options[0] : options[0]?.value);
  return el;
}

/** Announce an async change to assistive technology. Autosave has no button. */
export function announce(message) {
  const live = document.getElementById('live');
  if (!live) return;
  live.textContent = '';
  // Clear first, or a repeated identical message is not re-read. A timer rather
  // than requestAnimationFrame: rAF is throttled when the window is not visible,
  // which would silently drop the announcement.
  clearTimeout(announce._t);
  announce._t = setTimeout(() => { live.textContent = message; }, 40);
}

let toastTimer;
export function toast(message, kind = '') {
  document.querySelector('.toast')?.remove();
  const el = h('div.toast', { 'data-kind': kind }, message);
  document.body.append(el);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.remove(), 3200);
  announce(message);
}

/** Debounce, used for the free-text fields that autosave as the assessor types. */
export function debounce(fn, ms = 600) {
  let t;
  const wrapped = (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  wrapped.flush = (...args) => { clearTimeout(t); fn(...args); };
  wrapped.cancel = () => clearTimeout(t);
  return wrapped;
}

/** Rules sort numerically: R3, R6, R7, R8, R9, R10, R11 — never lexically. */
export const ruleOrder = (id) => parseInt(String(id).slice(1), 10) || 0;

/** '2026-09-15' -> '15 Sep 2026'. Report language, not ISO. */
export function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${String(d.getDate()).padStart(2, '0')} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

export const titleCase = (s) => (s ? s[0].toUpperCase() + s.slice(1) : '');
