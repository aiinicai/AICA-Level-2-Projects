/* Service worker: routes the downloads that WhatsApp Web starts into the export folders,
   tracks them until Chrome reports them complete, and writes transcripts/indexes. */
importScripts('shared/util.js');
const W = self.WDRE;

// ---------------------------------------------------------------------------
// State. Kept in memory and mirrored to storage.session so a restarted worker
// can pick up where it left off.
// ---------------------------------------------------------------------------
let st = null; // { armed, tokens: {token: rec}, byDownload: {id: token} }
let saveTimer = null;

async function load() {
  if (st) return st;
  const s = await chrome.storage.session.get('wdreDl');
  st = s.wdreDl || { armed: null, tokens: {}, byDownload: {} };
  return st;
}

function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => chrome.storage.session.set({ wdreDl: st }).catch(() => {}), 50);
}

function prune() {
  const cutoff = Date.now() - 6 * 3600 * 1000;
  for (const [tok, rec] of Object.entries(st.tokens)) {
    if ((rec.updatedAt || 0) < cutoff) {
      delete st.tokens[tok];
      if (rec.downloadId != null) delete st.byDownload[rec.downloadId];
    }
  }
}

// Report files we write ourselves: blob URL -> planned relative path.
const ownPlanned = new Map();

// ---------------------------------------------------------------------------
// Matching WhatsApp downloads to the item the exporter is saving
// ---------------------------------------------------------------------------
function isWhatsAppDownload(item, armed) {
  const u = String(item.finalUrl || item.url || '');
  const r = String(item.referrer || '');
  return (
    u.startsWith('blob:https://web.whatsapp.com/') ||
    u.startsWith('https://web.whatsapp.com/') ||
    /^https:\/\/[^/]*\.whatsapp\.net\//.test(u) ||
    r.startsWith('https://web.whatsapp.com/') ||
    // A sticker saved from its data: URL (no referrer) while a sticker download is armed.
    (u.startsWith('data:image/') && !r && armed && armed.kind === 'sticker')
  );
}

const alnum = (s) => W.norm(s).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

// Only documents carry a visible filename we can compare. Lenient on purpose:
// we refuse a download only when both the name and the extension disagree.
function hintMatches(hint, suggested) {
  if (!hint) return true;
  const [hb, he] = W.splitExt(hint);
  const [sb, se] = W.splitExt(suggested);
  const a = alnum(hb);
  const b = alnum(sb);
  if (!a || !b) return true;
  if (a === b || a.includes(b) || b.includes(a)) return true;
  return he.toLowerCase() === se.toLowerCase();
}

function plannedName(armed, item) {
  const original = W.basename(item.filename) || '';
  let [, ext] = W.splitExt(original);
  if (!ext) ext = W.extForMime(item.mime) || W.KIND_DEFAULT_EXT[armed.kind] || '';
  let base;
  if (armed.renameBase && armed.renameBase.trim()) {
    base = armed.renameBase.trim();
    // "Invoice March.pdf" for a .pdf file: don't end up with ".pdf.pdf".
    if (ext && base.toLowerCase().endsWith(ext.toLowerCase())) base = base.slice(0, -ext.length);
  } else {
    base = W.splitExt(original)[0] || armed.fallbackBase || 'WhatsApp file';
  }
  return { original, saveAs: W.cleanSegment(base, 100, 'WhatsApp file') + ext };
}

chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
  (async () => {
    await load();
    if (item.byExtensionId && item.byExtensionId === chrome.runtime.id) {
      const planned = ownPlanned.get(item.url) || ownPlanned.get(item.finalUrl);
      if (planned) suggest({ filename: planned, conflictAction: 'uniquify' });
      else suggest();
      return;
    }
    const armed = st.armed;
    if (!armed || Date.now() > armed.expiresAt || !isWhatsAppDownload(item, armed)) {
      suggest(); // not ours: the user's own downloads are left exactly as Chrome would save them
      return;
    }
    const original = W.basename(item.filename) || '';
    if (!hintMatches(armed.hintName, original)) {
      st.tokens[armed.token] = {
        ...(st.tokens[armed.token] || {}),
        mismatch: original,
        updatedAt: Date.now(),
      };
      save();
      suggest();
      return;
    }
    const name = plannedName(armed, item);
    const filename = `${armed.dir}/${name.saveAs}`;
    suggest({ filename, conflictAction: 'uniquify' });
    st.tokens[armed.token] = {
      state: 'started',
      downloadId: item.id,
      originalName: name.original,
      plannedPath: filename,
      mime: item.mime || '',
      totalBytes: item.totalBytes || 0,
      bytesReceived: 0,
      updatedAt: Date.now(),
    };
    st.byDownload[item.id] = armed.token;
    st.armed = null;
    save();
  })().catch((e) => {
    console.warn('onDeterminingFilename failed', e);
    try {
      suggest();
    } catch (_) {}
  });
  return true; // we call suggest asynchronously
});

async function refreshToken(token) {
  const rec = st.tokens[token];
  if (!rec || rec.downloadId == null || rec.state === 'complete' || rec.state === 'interrupted') return rec;
  const [it] = await chrome.downloads.search({ id: rec.downloadId });
  if (!it) {
    rec.state = 'interrupted';
    rec.error = 'Download disappeared from Chrome (removed or cancelled)';
  } else {
    rec.bytesReceived = it.bytesReceived;
    rec.totalBytes = it.totalBytes;
    if (it.filename) rec.savedPath = it.filename;
    if (it.state === 'complete') {
      rec.state = 'complete';
      rec.bytes = it.fileSize || it.bytesReceived;
    } else if (it.state === 'interrupted') {
      rec.state = 'interrupted';
      rec.error = it.error || 'INTERRUPTED';
    } else if (it.danger && !['safe', 'accepted'].includes(it.danger)) {
      rec.state = 'dangerous';
      rec.danger = it.danger;
    } else {
      rec.state = 'started';
    }
  }
  rec.updatedAt = Date.now();
  save();
  return rec;
}

chrome.downloads.onChanged.addListener((delta) => {
  (async () => {
    await load();
    const token = st.byDownload[delta.id];
    if (token) await refreshToken(token);
  })().catch(() => {});
});

// ---------------------------------------------------------------------------
// Writing generated files (transcripts, indexes) through an offscreen blob URL
// ---------------------------------------------------------------------------
async function ensureOffscreen() {
  if (chrome.offscreen.hasDocument && (await chrome.offscreen.hasDocument())) return;
  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['BLOBS'],
      justification: 'Builds transcript and index files locally so they can be saved to Downloads.',
    });
  } catch (e) {
    if (!/single offscreen|already/i.test(String(e && e.message))) throw e;
  }
}

async function waitForComplete(id, timeoutMs) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const [it] = await chrome.downloads.search({ id });
    if (!it) return { ok: false, error: 'Download vanished' };
    if (it.state === 'complete') return { ok: true, savedPath: it.filename, downloadId: id };
    if (it.state === 'interrupted') return { ok: false, error: it.error || 'INTERRUPTED' };
    await new Promise((r) => setTimeout(r, 150));
  }
  return { ok: false, error: 'Timed out waiting for Chrome to finish saving the file' };
}

async function writeFile(path, content, mime) {
  await ensureOffscreen();
  const { url } = await chrome.runtime.sendMessage({ target: 'offscreen', type: 'makeUrl', content, mime });
  ownPlanned.set(url, path);
  try {
    const id = await chrome.downloads.download({ url, filename: path, conflictAction: 'uniquify', saveAs: false });
    return await waitForComplete(id, 60000);
  } finally {
    ownPlanned.delete(url);
    chrome.runtime.sendMessage({ target: 'offscreen', type: 'revoke', url }).catch(() => {});
  }
}

// ---------------------------------------------------------------------------
// Messages from the content script / popup
// ---------------------------------------------------------------------------
async function handle(msg, sender) {
  await load();
  switch (msg.type) {
    case 'arm': {
      prune();
      st.armed = {
        token: msg.token,
        dir: msg.dir,
        renameBase: msg.renameBase || '',
        fallbackBase: msg.fallbackBase || '',
        hintName: msg.hintName || '',
        kind: msg.kind || 'unknown',
        tabId: sender.tab ? sender.tab.id : null,
        expiresAt: Date.now() + (msg.timeoutMs || 60000) + 5000,
      };
      st.tokens[msg.token] = { state: 'armed', updatedAt: Date.now() };
      save();
      return { ok: true };
    }
    case 'disarm': {
      if (st.armed && st.armed.token === msg.token) st.armed = null;
      save();
      return { ok: true };
    }
    case 'dlStatus': {
      const rec = await refreshToken(msg.token);
      return rec || { state: 'unknown' };
    }
    case 'cancelDownload': {
      if (st.armed && st.armed.token === msg.token) st.armed = null;
      const rec = st.tokens[msg.token];
      if (rec && rec.downloadId != null && rec.state !== 'complete') {
        try {
          await chrome.downloads.cancel(rec.downloadId);
        } catch (_) {}
        rec.state = 'interrupted';
        rec.error = 'Cancelled';
      }
      save();
      return { ok: true };
    }
    case 'writeFile':
      return await writeFile(msg.path, msg.content, msg.mime || 'text/html;charset=utf-8');
    case 'badge': {
      await chrome.action.setBadgeText({ text: msg.text || '' });
      if (msg.color) await chrome.action.setBadgeBackgroundColor({ color: msg.color });
      return { ok: true };
    }
    default:
      return undefined;
  }
}

const HANDLED = new Set(['arm', 'disarm', 'dlStatus', 'cancelDownload', 'writeFile', 'badge']);

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.target === 'offscreen' || !HANDLED.has(msg.type)) return false;
  handle(msg, sender).then(sendResponse, (e) => sendResponse({ ok: false, error: String((e && e.message) || e) }));
  return true;
});
