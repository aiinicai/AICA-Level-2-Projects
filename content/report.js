/* Builds the offline files: Transcript.html, Index.html, Index.csv and the export summary.
   Every file is self-contained (inline CSS/JS) and links to attachments by relative path. */
(function (g) {
  'use strict';
  const W = g.WDRE;
  const esc = W.escapeHtml;

  const URL_RE = /(https?:\/\/[^\s<>"']+|www\.[^\s<>"']+\.[^\s<>"']+)/gi;

  function linkify(text) {
    let out = '';
    let last = 0;
    String(text || '').replace(URL_RE, (m, _u, idx) => {
      let url = m;
      let trail = '';
      while (/[).,;:!?\]}'"]$/.test(url)) {
        trail = url.slice(-1) + trail;
        url = url.slice(0, -1);
      }
      out += esc(text.slice(last, idx));
      const href = /^www\./i.test(url) ? 'https://' + url : url;
      out += `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>${esc(trail)}`;
      last = idx + m.length;
      return m;
    });
    out += esc(String(text || '').slice(last));
    return out.replace(/\n/g, '<br>');
  }

  function hue(name) {
    let h = 0;
    for (const ch of String(name)) h = (h * 31 + ch.codePointAt(0)) % 360;
    return h;
  }

  const BASE_CSS = `
:root{--blue:#00338D;--blue2:#005EB8;--sky:#E8F0FB;--ink:#1F2937;--muted:#6B7280;--line:#D9E2EF;--bg:#F4F7FB;--card:#fff;
--ok:#15803D;--warn:#B45309;--bad:#B91C1C;--mine:#E1F0FF}
@media (prefers-color-scheme:dark){:root{--ink:#E5E7EB;--muted:#9CA3AF;--line:#2B3A55;--bg:#0E1626;--card:#16213A;--sky:#1C2B4A;--mine:#1D3557}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",Tahoma,"Noto Sans Arabic","Segoe UI Emoji","Apple Color Emoji",sans-serif}
header.top{background:var(--blue);color:#fff;padding:20px 24px 16px}
header.top h1{margin:0 0 4px;font-weight:300;font-size:26px}
header.top .meta{opacity:.9;font-size:13px}
.wrap{max-width:980px;margin:0 auto;padding:16px}
.banner{border-radius:8px;padding:10px 14px;margin:12px 0;font-size:13px}
.banner.ok{background:#E7F6EC;color:#14532D;border:1px solid #A7E3BA}
.banner.partial{background:#FFF4E5;color:#7C2D12;border:1px solid #F5C37A}
@media (prefers-color-scheme:dark){.banner.ok{background:#0F2F1E;color:#BBF7D0;border-color:#166534}.banner.partial{background:#3A2410;color:#FED7AA;border-color:#9A3412}}
.tools{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--line)}
.tools input[type=search],.tools select{padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);font:inherit}
.tools input[type=search]{flex:1;min-width:200px}
.tools .count{color:var(--muted);font-size:12px}
table{border-collapse:collapse;width:100%;background:var(--card)}
th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:start;vertical-align:top;font-size:13px}
th{background:var(--sky);color:var(--blue);font-weight:600;position:sticky;top:58px}
@media (prefers-color-scheme:dark){th{color:#BFD3F5}}
.st-saved{color:var(--ok);font-weight:600}.st-skipped{color:var(--warn);font-weight:600}.st-failed{color:var(--bad);font-weight:600}
.totals{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.totals div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 14px;min-width:110px}
.totals b{display:block;font-size:20px;font-weight:600;color:var(--blue2)}
.totals span{font-size:12px;color:var(--muted)}
a{color:var(--blue2)}
mark{background:#FDE68A;color:#111;border-radius:2px}
footer{color:var(--muted);font-size:12px;padding:20px 0 40px;text-align:center}
@media print{.tools{display:none}header.top{background:#fff;color:#000;border-bottom:2px solid #000}th{position:static}}
`;

  const TRANSCRIPT_CSS = `
.day{text-align:center;margin:18px 0 8px}
.day span{background:var(--sky);color:var(--blue);padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600}
@media (prefers-color-scheme:dark){.day span{color:#BFD3F5}}
.msg{display:flex;margin:4px 0}
.msg.me{justify-content:flex-end}
.bubble{max-width:78%;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 10px 4px;box-shadow:0 1px 1px rgba(0,0,0,.04)}
.msg.me .bubble{background:var(--mine)}
.sender{font-size:12px;font-weight:600;margin-bottom:2px}
.text{white-space:normal;word-wrap:break-word;overflow-wrap:anywhere}
.quote{border-inline-start:3px solid var(--blue2);background:rgba(0,94,184,.07);padding:4px 8px;margin:2px 0 4px;font-size:12px;color:var(--muted);border-radius:4px}
.time{font-size:11px;color:var(--muted);text-align:end;margin-top:2px}
.note{font-style:italic;color:var(--muted)}
.sys{text-align:center;color:var(--muted);font-size:12px;margin:6px 0}
.att{margin:4px 0;padding:6px 8px;border:1px dashed var(--line);border-radius:6px;font-size:13px}
.att img{display:block;max-width:100%;max-height:320px;border-radius:6px;margin-top:4px}
.att video{display:block;max-width:100%;max-height:320px;margin-top:4px}
.att audio{display:block;width:100%;margin-top:4px}
.att .why{color:var(--warn);font-size:12px}
.att.failed .why{color:var(--bad)}
.hidden{display:none!important}
`;

  function coverageBanner(ctx) {
    if (ctx.coverage === 'partial') {
      return `<div class="banner partial"><b>Partial export.</b> WhatsApp Web did not provide history all the way back to ${esc(ctx.from)}.
 Earliest message reached: <b>${esc(ctx.earliest || 'unknown')}</b>. ${esc(ctx.coverageNote || '')}
 Messages before that date may be missing; check the phone or an official WhatsApp chat export.</div>`;
    }
    return `<div class="banner ok"><b>Complete for the selected dates.</b> ${esc(ctx.coverageNote || '')}</div>`;
  }

  function attStatusText(a) {
    if (a.status === 'saved') return 'Saved';
    if (a.status === 'skipped') return 'Skipped';
    if (a.status === 'failed') return 'Failed';
    return 'Not processed';
  }

  function attHtml(a) {
    const label = `${W.KIND_LABEL[a.kind] || 'Attachment'} (${a.fromMe ? 'sent' : 'received'})`;
    if (a.status === 'saved' && a.savedName) {
      const rel = 'Media/' + W.encodeRelPath(a.savedName);
      let preview = '';
      if (a.kind === 'image' || a.kind === 'sticker') preview = `<img loading="lazy" src="${esc(rel)}" alt="${esc(label)}">`;
      else if (a.kind === 'video' || a.kind === 'gif') preview = `<video controls preload="metadata" src="${esc(rel)}"></video>`;
      else if (a.kind === 'voice' || a.kind === 'audio') preview = `<audio controls preload="none" src="${esc(rel)}"></audio>`;
      const orig = a.originalName && a.originalName !== a.savedName ? ` <span class="note">(original: ${esc(a.originalName)})</span>` : '';
      return `<div class="att saved">📎 ${esc(label)}: <a href="${esc(rel)}" target="_blank">${esc(a.savedName)}</a>${orig}${preview}</div>`;
    }
    const name = a.originalName ? ` “${esc(a.originalName)}”` : '';
    return `<div class="att ${esc(a.status)}">📎 ${esc(label)}${name} — <span class="why">${esc(attStatusText(a))}: ${esc(a.reason || 'not downloaded')}</span></div>`;
  }

  W.report = {};

  W.report.transcript = function (ctx) {
    const tz = ctx.tz;
    const attsByRec = new Map();
    for (const a of ctx.atts) {
      if (!attsByRec.has(a.recId)) attsByRec.set(a.recId, []);
      attsByRec.get(a.recId).push(a);
    }
    const senders = Array.from(new Set(ctx.records.filter((r) => !r.system).map((r) => r.sender))).sort();
    const parts = [];
    let lastDay = '';
    let n = 0;
    for (const r of ctx.records) {
      const ms = r.ts != null ? r.ts : r.localDate ? W.tz.localWallToEpoch(r.localDate.y, r.localDate.m, r.localDate.d, 12, 0) : null;
      const day = ms != null ? W.tz.fmtDayHeading(tz, ms) : 'Date unknown';
      if (day !== lastDay) {
        parts.push(`<div class="day"><span>${esc(day)}</span></div>`);
        lastDay = day;
      }
      if (r.system) {
        parts.push(`<div class="sys" data-kind="system">${linkify(r.text)}</div>`);
        continue;
      }
      n++;
      const atts = attsByRec.get(r.id) || [];
      const color = `hsl(${hue(r.sender)},55%,38%)`;
      const showSender = ctx.isGroup || !r.fromMe;
      const time = r.ts != null ? W.tz.fmtTime(tz, r.ts) : '';
      const iso = r.ts != null ? new Date(r.ts).toISOString() : '';
      const textCls = r.note === 'deleted' ? 'text note' : 'text';
      parts.push(
        `<div class="msg${r.fromMe ? ' me' : ''}" data-sender="${esc(r.sender)}" data-att="${atts.length ? 1 : 0}" id="m${n}">` +
          `<div class="bubble">` +
          (showSender ? `<div class="sender" style="color:${color}" dir="auto">${esc(r.sender)}</div>` : '') +
          (r.quoted ? `<div class="quote" dir="auto">↪ ${linkify(r.quoted)}</div>` : '') +
          atts.map(attHtml).join('') +
          (r.text ? `<div class="${textCls}" dir="auto">${linkify(r.text)}</div>` : '') +
          `<div class="time"><time datetime="${esc(iso)}">${esc(time)}</time></div>` +
          `</div></div>`
      );
    }
    const t = { saved: 0, skipped: 0, failed: 0 };
    for (const a of ctx.atts) if (t[a.status] != null) t[a.status]++;
    const senderOpts = senders.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join('');
    const title = `${ctx.chatName} — ${ctx.rangeLabel}`;
    return `<!doctype html>
<html lang="en" dir="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="WhatsApp Date Range Exporter ${esc(ctx.version)}">
<title>${esc(title)}</title>
<style>${BASE_CSS}${TRANSCRIPT_CSS}</style>
</head>
<body>
<header class="top">
<h1 dir="auto">${esc(ctx.chatName)}</h1>
<div class="meta">${esc(ctx.isGroup ? 'Group chat' : 'Chat')} · ${esc(ctx.rangeLabel)} (both dates included) · Times shown in ${esc(tz)} (${esc(W.tz.fmtOffset(tz, ctx.generatedAt))})${ctx.client ? ' · Client: ' + esc(ctx.client) : ''}</div>
</header>
<div class="wrap">
${coverageBanner(ctx)}
<div class="totals">
<div><b>${n}</b><span>messages</span></div>
<div><b>${ctx.atts.length}</b><span>attachments</span></div>
<div><b>${t.saved}</b><span>files saved</span></div>
<div><b>${t.skipped}</b><span>skipped</span></div>
<div><b>${t.failed}</b><span>failed</span></div>
</div>
<div class="tools">
<input type="search" id="q" placeholder="Search messages, senders, file names…  (press / to focus)" autocomplete="off">
${senders.length > 1 ? `<select id="who"><option value="">All senders</option>${senderOpts}</select>` : ''}
<label><input type="checkbox" id="onlyAtt"> With attachments</label>
<span class="count" id="count"></span>
</div>
<main id="log">
${parts.join('\n') || '<p class="note">No messages were found in this date range.</p>'}
</main>
<footer>Exported ${esc(W.tz.fmtDateTime(tz, ctx.generatedAt))} (${esc(tz)}) with WhatsApp Date Range Exporter ${esc(ctx.version)}. Attachment links point to the Media folder next to this file. See Index.html for the full attachment list.</footer>
</div>
<script>
(function(){
  var q=document.getElementById('q'),who=document.getElementById('who'),only=document.getElementById('onlyAtt'),count=document.getElementById('count');
  var msgs=[].slice.call(document.querySelectorAll('.msg')),days=[].slice.call(document.querySelectorAll('.day,.sys'));
  function clearMarks(root){[].slice.call(root.querySelectorAll('mark')).forEach(function(m){m.replaceWith(document.createTextNode(m.textContent));});root.normalize();}
  function mark(root,term){
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),nodes=[],n;
    while((n=w.nextNode()))nodes.push(n);
    nodes.forEach(function(node){
      var text=node.nodeValue,low=text.toLowerCase(),i=low.indexOf(term);
      if(i<0)return;
      var frag=document.createDocumentFragment(),last=0;
      while(i>=0){frag.appendChild(document.createTextNode(text.slice(last,i)));var m=document.createElement('mark');m.textContent=text.slice(i,i+term.length);frag.appendChild(m);last=i+term.length;i=low.indexOf(term,last);}
      frag.appendChild(document.createTextNode(text.slice(last)));node.replaceWith(frag);
    });
  }
  function run(){
    var term=(q.value||'').trim().toLowerCase(),s=who?who.value:'',a=only.checked,shown=0;
    msgs.forEach(function(m){
      clearMarks(m);
      var ok=(!s||m.getAttribute('data-sender')===s)&&(!a||m.getAttribute('data-att')==='1')&&(!term||m.textContent.toLowerCase().indexOf(term)>=0);
      m.classList.toggle('hidden',!ok);
      if(ok){shown++;if(term)mark(m.querySelector('.bubble'),term);}
    });
    var filtering=!!(term||s||a);
    days.forEach(function(d){d.classList.toggle('hidden',filtering);});
    count.textContent=filtering?(shown+' of '+msgs.length+' messages'):(msgs.length+' messages');
  }
  q.addEventListener('input',run);if(who)who.addEventListener('change',run);only.addEventListener('change',run);
  document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();}});
  run();
})();
</script>
</body>
</html>
`;
  };

  function indexRows(ctx) {
    const tz = ctx.tz;
    return ctx.atts.map((a, i) => ({
      n: i + 1,
      chat: ctx.chatName,
      sender: a.sender || '',
      direction: a.fromMe ? 'Sent' : 'Received',
      date: a.ts != null ? W.tz.fmtDateTime(tz, a.ts) : '',
      type: W.KIND_LABEL[a.kind] || 'Attachment',
      fileType: W.fileTypeLabel(W.fileTypeKey(a.kind, a.originalName || a.whatsappName || a.savedName || a.name)),
      original: a.originalName || a.whatsappName || '',
      saved: a.status === 'saved' ? a.savedName : '',
      rel: a.status === 'saved' && a.savedName ? 'Media/' + a.savedName : '',
      status: attStatusText(a),
      statusKey: a.status,
      reason: a.reason || '',
      id: a.recId,
    }));
  }

  W.report.indexHtml = function (ctx) {
    const rows = indexRows(ctx);
    const t = { saved: 0, skipped: 0, failed: 0 };
    for (const r of rows) if (t[r.statusKey] != null) t[r.statusKey]++;
    const msgCount = ctx.records.filter((r) => !r.system).length;
    const body = rows
      .map(
        (r) =>
          `<tr data-status="${esc(r.statusKey)}" data-dir="${esc(r.direction.toLowerCase())}"><td>${r.n}</td><td dir="auto">${esc(r.chat)}</td><td dir="auto">${esc(r.sender)}</td><td>${esc(r.direction)}</td><td>${esc(r.date)}</td><td>${esc(r.type)}${r.type === 'Document' ? ` · ${esc(r.fileType)}` : ''}</td>` +
          `<td dir="auto">${esc(r.original)}</td><td dir="auto">${r.rel ? `<a href="${esc(W.encodeRelPath(r.rel))}" target="_blank">${esc(r.saved)}</a>` : ''}</td>` +
          `<td class="st-${esc(r.statusKey)}">${esc(r.status)}</td><td>${esc(r.reason)}</td></tr>`
      )
      .join('\n');
    return `<!doctype html>
<html lang="en" dir="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(ctx.chatName)} — attachment index — ${esc(ctx.rangeLabel)}</title>
<style>${BASE_CSS}</style>
</head>
<body>
<header class="top">
<h1 dir="auto">Attachment index — ${esc(ctx.chatName)}</h1>
<div class="meta">${esc(ctx.rangeLabel)} (both dates included) · Dates in ${esc(ctx.tz)}${ctx.client ? ' · Client: ' + esc(ctx.client) : ''}</div>
</header>
<div class="wrap">
${coverageBanner(ctx)}
<div class="totals">
<div><b>${msgCount}</b><span>messages exported</span></div>
<div><b>${rows.length}</b><span>attachments found</span></div>
<div><b>${t.saved}</b><span>files saved</span></div>
<div><b>${t.skipped}</b><span>skipped</span></div>
<div><b>${t.failed}</b><span>failed</span></div>
</div>
<div class="tools">
<input type="search" id="q" placeholder="Filter by sender, file name, status…" autocomplete="off">
<select id="st"><option value="">All statuses</option><option value="saved">Saved</option><option value="skipped">Skipped</option><option value="failed">Failed</option></select>
<select id="dir"><option value="">Sent and received</option><option value="received">Received</option><option value="sent">Sent</option></select>
<span class="count" id="count"></span>
</div>
<table>
<thead><tr><th>#</th><th>Chat</th><th>Sender</th><th>Sent / received</th><th>Message date</th><th>Type</th><th>Original filename</th><th>Saved filename</th><th>Download status</th><th>Notes</th></tr></thead>
<tbody>
${body || '<tr><td colspan="10">No attachments in this date range.</td></tr>'}
</tbody>
</table>
<footer>A file counts as saved only after Chrome reported the download complete. ${ctx.mode !== 'media' ? 'The conversation is in Transcript.html.' : ''} Generated ${esc(W.tz.fmtDateTime(ctx.tz, ctx.generatedAt))} (${esc(ctx.tz)}).</footer>
</div>
<script>
(function(){var q=document.getElementById('q'),st=document.getElementById('st'),dir=document.getElementById('dir'),c=document.getElementById('count'),rows=[].slice.call(document.querySelectorAll('tbody tr[data-status]'));
function run(){var t=q.value.trim().toLowerCase(),s=st.value,d=dir.value,n=0;rows.forEach(function(r){var ok=(!s||r.getAttribute('data-status')===s)&&(!d||r.getAttribute('data-dir')===d)&&(!t||r.textContent.toLowerCase().indexOf(t)>=0);r.style.display=ok?'':'none';if(ok)n++;});c.textContent=n+' of '+rows.length+' attachments';}
q.addEventListener('input',run);st.addEventListener('change',run);dir.addEventListener('change',run);run();})();
</script>
</body>
</html>
`;
  };

  function csvCell(v) {
    const s = String(v == null ? '' : v);
    return /[",\r\n]/.test(s) || /^[=+\-@]/.test(s) ? `"${(/^[=+\-@]/.test(s) ? "'" : '') + s.replace(/"/g, '""')}"` : s;
  }

  W.report.indexCsv = function (ctx) {
    const head = ['#', 'Chat', 'Sender', 'Sent / received', `Message date (${ctx.tz})`, 'Type', 'File type', 'Original filename', 'Saved filename', 'Saved path (relative)', 'Download status', 'Notes', 'Message ID'];
    const lines = [head.map(csvCell).join(',')];
    for (const r of indexRows(ctx)) {
      lines.push([r.n, r.chat, r.sender, r.direction, r.date, r.type, r.fileType, r.original, r.saved, r.rel, r.status, r.reason, r.id].map(csvCell).join(','));
    }
    return '﻿' + lines.join('\r\n') + '\r\n';
  };

  W.report.summary = function (status) {
    const o = status.options;
    const rows = status.chats
      .map((c) => {
        const cov = c.state === 'failed' ? 'Failed' : c.state === 'cancelled' ? 'Cancelled' : c.coverage === 'partial' ? 'Partial' : c.coverage === 'complete' ? 'Complete' : c.state;
        const link = c.transcriptPath || c.indexPath;
        return (
          `<tr><td dir="auto">${esc(c.name)}</td><td class="${cov === 'Complete' ? 'st-saved' : cov === 'Partial' ? 'st-skipped' : 'st-failed'}">${esc(cov)}</td>` +
          `<td>${esc(c.earliest || '')}</td><td>${c.messagesInRange || 0}</td><td>${c.att.total}</td><td>${c.att.saved}</td><td>${c.att.skipped}</td><td>${c.att.failed}</td>` +
          // The summary sits in the export root; chat files are at <chat>/<range>/<file>.
          `<td dir="auto">${link ? `<a href="${esc(W.encodeRelPath(String(link).split(/[\\/]/).slice(-3).join('/')))}">${esc(String(link).split(/[\\/]/).slice(-3).join(' / '))}</a>` : esc(c.error || c.phase || '')}</td></tr>`
        );
      })
      .join('\n');
    const t = status.totals;
    return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WhatsApp export summary — ${esc(status.rangeLabel)}</title><style>${BASE_CSS}</style></head>
<body>
<header class="top"><h1>WhatsApp export summary</h1>
<div class="meta">${esc(status.rangeLabel)} (both dates included) · ${esc(o.tz)} · ${esc({ both: 'Messages and media', messages: 'Messages only', media: 'Media only' }[o.mode] || o.mode)} · Result: ${esc(status.state)}</div></header>
<div class="wrap">
<div class="totals">
<div><b>${status.chats.length}</b><span>chats</span></div>
<div><b>${t.messages}</b><span>messages</span></div>
<div><b>${t.saved}</b><span>files saved</span></div>
<div><b>${t.skipped}</b><span>skipped</span></div>
<div><b>${t.failed}</b><span>failed</span></div>
</div>
<table><thead><tr><th>Chat</th><th>History coverage</th><th>Earliest message reached</th><th>Messages in range</th><th>Attachments</th><th>Saved</th><th>Skipped</th><th>Failed</th><th>Transcript</th></tr></thead>
<tbody>${rows}</tbody></table>
<footer>Each chat has its own folder with Transcript.html, Index.html, Index.csv and a Media folder.</footer>
</div></body></html>
`;
  };
})(globalThis);
