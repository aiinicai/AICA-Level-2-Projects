// Offline outbox (live mode). A document picked while offline — or whose upload failed on the network — is kept on this
// device (IndexedDB) and the record points at "pending:<id>". When the connection returns the file is uploaded and every
// "pending:<id>" in the app data is replaced by the real Drive file id. Nothing is dropped silently: the shell shows how
// many files are waiting, and a file that keeps failing stays in the outbox with its last error.

export interface OutboxItem { id: string; clientId: string; folder: string; name: string; blob: Blob; queuedAt: string; tries: number; lastError?: string }

const DB = 'vouchr-outbox', STORE = 'uploads';
export const PENDING = 'pending:';
export const isPending = (fileId?: string) => !!fileId?.startsWith(PENDING);

function idb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function tx<T>(mode: IDBTransactionMode, run: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const r = run(db.transaction(STORE, mode).objectStore(STORE));
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

const listeners = new Set<(n: number) => void>();
async function notify() { const n = (await list()).length; listeners.forEach((f) => f(n)); }
/** Subscribe to the number of files waiting. Returns an unsubscribe function. */
export function onOutboxChange(f: (n: number) => void) { listeners.add(f); list().then((l) => f(l.length)).catch(() => f(0)); return () => { listeners.delete(f); }; }

export async function list(): Promise<OutboxItem[]> { return (await tx('readonly', (s) => s.getAll())) as OutboxItem[]; }
export async function get(id: string): Promise<OutboxItem | undefined> { return (await tx('readonly', (s) => s.get(id))) as OutboxItem | undefined; }

export async function enqueue(item: Omit<OutboxItem, 'id' | 'queuedAt' | 'tries'>): Promise<string> {
  const id = PENDING + crypto.randomUUID();
  await tx('readwrite', (s) => s.put({ ...item, id, queuedAt: new Date().toISOString(), tries: 0 }));
  void notify();
  return id;
}

/** A network failure (worth retrying), as opposed to the server refusing the file. */
export const isNetworkError = (e: unknown) => !navigator.onLine || e instanceof TypeError || (e as { retryable?: boolean })?.retryable === true || /fetch|network|Failed to send|timed? ?out/i.test(String((e as Error)?.message ?? e));

let flushing = false;
/** Upload every waiting file, oldest first. `upload` returns the real file id; `resolved` swaps it into the app data. */
export async function flush(upload: (it: OutboxItem) => Promise<string>, resolved: (pendingId: string, fileId: string) => void): Promise<{ sent: number; left: number }> {
  if (flushing || !navigator.onLine) return { sent: 0, left: (await list()).length };
  flushing = true;
  let sent = 0;
  try {
    for (const it of (await list()).sort((a, b) => a.queuedAt.localeCompare(b.queuedAt))) {
      try {
        const fileId = await upload(it);
        resolved(it.id, fileId);
        await tx('readwrite', (s) => s.delete(it.id));
        sent++;
      } catch (e) {
        await tx('readwrite', (s) => s.put({ ...it, tries: it.tries + 1, lastError: String((e as Error)?.message ?? e).slice(0, 200) }));
        if (isNetworkError(e)) break; // still offline — try again later
      }
    }
  } finally { flushing = false; void notify(); }
  return { sent, left: (await list()).length };
}
