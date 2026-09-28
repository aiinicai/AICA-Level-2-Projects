// Global reactive state and API client
const { reactive } = Vue;

function load(key, dflt) { try { const v = localStorage.getItem('lease116.' + key); return v === null ? dflt : JSON.parse(v); } catch (e) { return dflt; } }
function save(key, v) { try { localStorage.setItem('lease116.' + key, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }

export const store = reactive({
  user: null, company: null, entities: [], assetClasses: [], version: '',
  asOf: load('asOf', null), entityId: load('entityId', ''), units: load('units', 'ABSOLUTE'), numberFormat: 'INDIAN',
  theme: load('theme', 'light'), toasts: [], confirm: null, ready: false, approvalsCount: 0,
  can(perm) { const p = this.user?.permissions || []; return p.includes('*') || p.includes(perm); },
  persist() { save('asOf', this.asOf); save('entityId', this.entityId); save('units', this.units); save('theme', this.theme); },
});

let toastId = 0;
export function toast(msg, kind = '', ms = 4200) {
  const id = ++toastId;
  store.toasts.push({ id, msg, kind });
  setTimeout(() => { const i = store.toasts.findIndex(t => t.id === id); if (i >= 0) store.toasts.splice(i, 1); }, ms);
}
export function confirmDialog(title, message, opts = {}) {
  return new Promise(resolve => { store.confirm = { title, message, ...opts, resolve }; });
}

export class ApiError extends Error {
  constructor(message, status, issues) { super(message); this.status = status; this.issues = issues || []; }
}

export async function api(method, url, body, isForm = false) {
  const init = { method, credentials: 'same-origin', headers: {} };
  if (body !== undefined && body !== null) {
    if (isForm) init.body = body;
    else { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
  }
  let res;
  try { res = await fetch(url, init); } catch (e) { throw new ApiError('Cannot reach the Lease116 service. Is it still running?', 0); }
  if (res.status === 401 && !url.includes('/auth/login')) {
    store.user = null;
    location.hash = '#/login';
    throw new ApiError('Please sign in', 401);
  }
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) {
    let msg = 'Request failed', issues = [];
    const d = data && data.detail !== undefined ? data.detail : data;
    if (typeof d === 'string') msg = d;
    else if (d && d.message) { msg = d.message; issues = d.issues || []; }
    else if (Array.isArray(d)) msg = d.map(x => x.msg || JSON.stringify(x)).join('; ');
    throw new ApiError(msg, res.status, issues);
  }
  return data;
}
export const get = (u) => api('GET', u);
export const post = (u, b) => api('POST', u, b ?? {});
export const put = (u, b) => api('PUT', u, b);
export const patch = (u, b) => api('PATCH', u, b);
export const del = (u) => api('DELETE', u);
export const upload = (u, fd) => api('POST', u, fd, true);

export async function download(url, fallbackName = 'download') {
  const res = await fetch(url, { credentials: 'same-origin' });
  if (!res.ok) {
    let m = 'Export failed';
    try { const j = await res.json(); m = j.detail?.message || j.detail || m; } catch (e) { /* ignore */ }
    toast(typeof m === 'string' ? m : 'Export failed', 'bad');
    return;
  }
  const cd = res.headers.get('content-disposition') || '';
  const m = /filename="?([^"]+)"?/.exec(cd);
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = m ? m[1] : fallbackName;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  toast('Downloaded ' + a.download, 'ok', 2500);
}

export function showError(e) {
  const issues = (e.issues || []).map(i => i.message || i).filter(Boolean);
  toast(e.message + (issues.length ? ' — ' + issues.slice(0, 3).join('; ') : ''), 'bad', 7000);
}
