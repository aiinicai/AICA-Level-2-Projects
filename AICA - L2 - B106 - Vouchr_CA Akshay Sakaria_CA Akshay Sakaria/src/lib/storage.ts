// Document storage. Every major file (bills, challan receipts, bank statements, GSTR-2B, logos) is filed
// client-wise and FY-wise:   Vouchr / <Client> / FY <yyyy-yy> / <Kind> / <yyyy-mm-dd>_<vendor>_<ref>.<ext>
//   • Live: Supabase Edge Function `drive-upload` → Google Drive (credentials never reach the browser).
//   • Demo: the same path, stored on this device in IndexedDB (not in localStorage — that holds only ~5 MB).
// App data keeps only the file id, the Drive path and a small thumbnail.

import { supabase } from './backend';
import { optimiseForArchive } from './image';
import * as outbox from './outbox';

export type DocKind = 'Bills' | 'TDS Challans' | 'Bank Statements' | 'GSTR-2B' | 'Branding';

const safe = (s: string) => s.normalize('NFKD').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-').slice(0, 40) || 'file';

/** Folder path for a document — the same in Drive and in demo storage. */
export function docFolder(clientName: string, fy: string, kind: DocKind): string {
  return kind === 'Branding' ? `Vouchr/${safe(clientName)}/Branding` : `Vouchr/${safe(clientName)}/FY ${fy}/${kind}`;
}

/** Self-explaining file name, e.g. 2026-10-05_Paper-House-Stationers_PH-2302.jpg */
export function docName(date: string, party: string | undefined, ref: string | undefined, originalName: string): string {
  const ext = (/\.([a-z0-9]{2,5})$/i.exec(originalName)?.[1] ?? 'bin').toLowerCase();
  return [date, party && safe(party), ref && safe(ref)].filter(Boolean).join('_') + '.' + ext;
}

export interface StoredDoc {
  fileId: string; // Drive file id, or "local:<id>" in demo mode
  path: string;   // folder/name
  viewUrl?: string;
  /** Bytes before / after archive compression (photos of bills and challans only). */
  before?: number;
  after?: number;
}

// ---------------------------------------------------------------- demo storage (IndexedDB)
const DB = 'vouchr-docs', STORE = 'files';

function idb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(key: string, value: { blob: Blob; path: string }) {
  const db = await idb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function idbGet(key: string): Promise<{ blob: Blob; path: string } | undefined> {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE).objectStore(STORE).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// ---------------------------------------------------------------- public API
export async function saveDocument(opts: { clientId: string; clientName: string; fy: string; kind: DocKind; file: Blob; name: string }): Promise<StoredDoc> {
  const folder = docFolder(opts.clientName, opts.fy, opts.kind);
  // photos of bills / challans are shrunk for the archive; statements, GSTR-2B files, logos and all PDFs stay as they are
  const opt = opts.kind === 'Bills' || opts.kind === 'TDS Challans' ? await optimiseForArchive(opts.file, opts.name) : { blob: opts.file, name: opts.name, before: opts.file.size, after: opts.file.size };
  const path = `${folder}/${opt.name}`;
  const sizes = { before: opt.before, after: opt.after };
  if (supabase) {
    const item = { clientId: opts.clientId, folder, name: opt.name, blob: opt.blob };
    // offline → keep it in the outbox; it is sent when the connection returns
    if (!navigator.onLine) return { fileId: await outbox.enqueue(item), path, ...sizes };
    try {
      const up = await driveUpload(item);
      return { fileId: up.fileId, path, viewUrl: up.viewUrl, ...sizes };
    } catch (e) {
      if (outbox.isNetworkError(e)) return { fileId: await outbox.enqueue(item), path, ...sizes };
      throw e;
    }
  }
  const id = `local:${crypto.randomUUID()}`;
  await idbPut(id, { blob: opt.blob, path });
  return { fileId: id, path, ...sizes };
}

async function driveUpload(it: { clientId: string; folder: string; name: string; blob: Blob }): Promise<{ fileId: string; viewUrl?: string }> {
  const form = new FormData();
  form.append('file', it.blob, it.name);
  form.append('clientId', it.clientId);
  form.append('folder', it.folder);
  const { data, error } = await supabase!.functions.invoke('drive-upload', { body: form });
  if (error) {
    const status = (error as { context?: { status?: number } }).context?.status;
    // 5xx = Google Drive or the server had a problem: keep the file and retry. 4xx = refused (type, size, access): tell the user.
    throw Object.assign(new Error(`Upload to Google Drive failed: ${error.message}`), { retryable: !status || status >= 500 });
  }
  return { fileId: data.fileId, viewUrl: data.webViewLink };
}

/** Send files waiting in the outbox (live mode). `resolved` swaps "pending:<id>" for the Drive file id in app data. */
export async function flushOutbox(resolved: (pendingId: string, fileId: string) => void) {
  if (!supabase) return { sent: 0, left: 0 };
  return outbox.flush(async (it) => (await driveUpload(it)).fileId, resolved);
}

/** Opens the original document (Drive viewer, or the locally stored copy in demo mode). */
export async function openDocument(fileId: string, viewUrl?: string): Promise<boolean> {
  if (viewUrl) { window.open(viewUrl, '_blank', 'noopener'); return true; }
  if (outbox.isPending(fileId)) {
    const it = await outbox.get(fileId);
    if (!it) return false;
    window.open(URL.createObjectURL(it.blob), '_blank', 'noopener');
    return true;
  }
  if (fileId.startsWith('local:')) {
    const rec = await idbGet(fileId);
    if (!rec) return false;
    window.open(URL.createObjectURL(rec.blob), '_blank', 'noopener');
    return true;
  }
  window.open(`https://drive.google.com/file/d/${encodeURIComponent(fileId)}/view`, '_blank', 'noopener');
  return true;
}

/** The stored original as a Blob (demo storage only; live files are read on the server from Drive). */
export async function getDocumentBlob(fileId?: string): Promise<Blob | undefined> {
  if (outbox.isPending(fileId)) return (await outbox.get(fileId!))?.blob;
  if (!fileId?.startsWith('local:')) return undefined;
  return (await idbGet(fileId))?.blob;
}
