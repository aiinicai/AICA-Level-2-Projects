/* Small status panel inside the WhatsApp tab, so progress stays visible after the popup closes. */
(function (g) {
  'use strict';
  const W = g.WDRE;
  const esc = W.escapeHtml;
  let host = null;
  let root = null;
  let job = null;

  const CSS = `
:host{all:initial}
.p{position:fixed;left:16px;bottom:16px;z-index:2147483646;width:330px;background:#fff;color:#1F2937;border:1px solid #C9D6EA;
border-radius:10px;box-shadow:0 8px 28px rgba(0,30,80,.25);font:13px/1.45 "Segoe UI",Tahoma,sans-serif;overflow:hidden}
.h{background:#00338D;color:#fff;padding:8px 12px;display:flex;align-items:center;gap:8px}
.h b{font-weight:600;flex:1}
.b{padding:10px 12px}
.row{margin:2px 0}
.muted{color:#6B7280;font-size:12px}
.warn{background:#FFF4E5;color:#7C2D12;border-radius:6px;padding:6px 8px;margin-top:6px;font-size:12px}
.bar{height:6px;background:#E8F0FB;border-radius:3px;margin:8px 0 4px;overflow:hidden}
.bar i{display:block;height:100%;background:#005EB8;width:0;transition:width .3s}
button{font:inherit;border:1px solid #C9D6EA;background:#fff;color:#00338D;border-radius:6px;padding:4px 10px;cursor:pointer}
button:hover{background:#E8F0FB}
.h button{background:transparent;color:#fff;border-color:rgba(255,255,255,.5);padding:2px 8px}
.ok{color:#15803D;font-weight:600}.bad{color:#B91C1C;font-weight:600}.part{color:#B45309;font-weight:600}
`;

  function ensure() {
    if (host && document.documentElement.contains(host)) return;
    host = document.createElement('div');
    host.id = 'wdre-overlay-host';
    root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>${CSS}</style><div class="p"><div class="h"><b>WhatsApp Date Range Exporter <small style="font-weight:400;opacity:.8">v${W.VERSION}</small></b><button id="x">Cancel</button></div><div class="b" id="body"></div></div>`;
    root.getElementById('x').addEventListener('click', () => {
      if (job && (job.status.state === 'running' || job.status.state === 'review')) job.cancel();
      else hide();
    });
    document.documentElement.appendChild(host);
  }

  function hide() {
    if (host) host.remove();
    host = null;
  }

  function render(s) {
    if (!root) return;
    const body = root.getElementById('body');
    const btn = root.getElementById('x');
    const c = s.chats[s.current] || null;
    const total = s.chats.length || 1;
    const done = s.chats.filter((x) => ['done', 'partial', 'failed', 'cancelled'].includes(x.state)).length;
    const pct = s.state === 'done' ? 100 : Math.round((done / total) * 100);
    const t = s.totals;
    let html = '';
    if (s.state === 'running' || s.state === 'review') {
      html += `<div class="row"><b>${s.state === 'review' ? 'Waiting for you' : 'Exporting'}</b> · chat ${Math.max(1, s.current + 1)} of ${s.chats.length || '…'}</div>`;
      if (c) html += `<div class="row" dir="auto">${esc(c.name)}</div><div class="row muted">${esc(c.phase || '')}</div>`;
      else html += `<div class="row muted">${esc(s.log[s.log.length - 1] || 'Starting…')}</div>`;
      html += `<div class="bar"><i style="width:${pct}%"></i></div>`;
      html += `<div class="row muted">Files saved ${t.saved} · skipped ${t.skipped} · failed ${t.failed}</div>`;
      if (s.state === 'review') html += `<div class="warn">Open the extension (toolbar icon) to choose which attachments to save, then click Save.</div>`;
      if (s.blockWarning) html += `<div class="warn">${esc(s.blockWarning)}</div>`;
      html += `<div class="row muted" style="margin-top:6px">Please leave this tab alone until the export finishes. You can close the extension popup.</div>`;
      if (s.warning) html += `<div class="warn">${esc(s.warning)}</div>`;
      btn.textContent = 'Cancel';
    } else {
      const cls = s.state === 'done' ? (t.failed ? 'part' : 'ok') : s.state === 'cancelled' ? 'part' : 'bad';
      const label = { done: 'Export finished', cancelled: 'Export cancelled', error: 'Export stopped' }[s.state] || s.state;
      html += `<div class="row ${cls}">${esc(label)}</div>`;
      html += `<div class="row">${t.messages} messages · ${t.saved} files saved · ${t.skipped} skipped · ${t.failed} failed</div>`;
      const partial = s.chats.filter((x) => x.coverage === 'partial');
      if (partial.length) html += `<div class="warn">Partial history for ${partial.map((x) => esc(x.name) + ' (back to ' + esc(x.earliest || '?') + ')').join(', ')}</div>`;
      if (s.error) html += `<div class="warn">${esc(s.error)}</div>`;
      html += `<div class="row muted">Saved under Downloads/${esc(s.root)}</div>`;
      btn.textContent = 'Close';
    }
    body.innerHTML = html;
  }

  W.overlay = {
    show(j) {
      job = j;
      ensure();
      render(j.status);
    },
    update(s) {
      if (!host) ensure();
      render(s);
    },
    done(s) {
      render(s);
    },
    hide,
  };
})(globalThis);
