import type { Analysis } from "./schema";
import type { LocalMetrics } from "./audio";

export interface Session {
  id: string;
  createdAt: number;
  mode: string;
  title: string;
  referenceText?: string | undefined;
  audio: Blob;
  mimeType: string;
  metrics: LocalMetrics;
  analysis: Analysis;
  wpm: number;
}

const DB = "speakwell";
const STORE = "sessions";

function open(): Promise<IDBDatabase> {
  return new Promise((res, rej) => {
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "id" });
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}

async function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open();
  return new Promise((res, rej) => {
    const req = fn(db.transaction(STORE, mode).objectStore(STORE));
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
  });
}

export const saveSession = (s: Session) => tx("readwrite", (st) => st.put(s));
export const getSession = (id: string) => tx<Session | undefined>("readonly", (st) => st.get(id));
export const deleteSession = (id: string) => tx("readwrite", (st) => st.delete(id));
export async function listSessions(): Promise<Session[]> {
  const all = await tx<Session[]>("readonly", (st) => st.getAll());
  return all.sort((a, b) => b.createdAt - a.createdAt);
}
export async function deleteAll() {
  await tx("readwrite", (st) => st.clear());
  localStorage.removeItem("speakwell-goal");
}

export function streak(sessions: Session[]): number {
  const days = new Set(sessions.map((s) => new Date(s.createdAt).toDateString()));
  let n = 0;
  const d = new Date();
  if (!days.has(d.toDateString())) d.setDate(d.getDate() - 1);
  while (days.has(d.toDateString())) { n++; d.setDate(d.getDate() - 1); }
  return n;
}
