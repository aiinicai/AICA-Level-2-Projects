/**
 * In-memory stand-in for Cloud Firestore, used ONLY by "Try Demo" mode.
 *
 * It implements just the subset of the Firestore API that this app uses
 * (collection / doc / query / where / onSnapshot / getDocs / setDoc / addDoc /
 * updateDoc / deleteDoc / writeBatch / runTransaction / serverTimestamp) so the
 * rest of the app runs unchanged. Nothing here ever touches the network or the
 * real database; data lives in browser memory and is reset on page reload.
 */

export type DemoRole = 'admin' | 'manager' | 'employee';

const ROLE_KEY = 'trs_demo_role';

export function getDemoRole(): DemoRole | null {
  try {
    const v = sessionStorage.getItem(ROLE_KEY);
    return v === 'admin' || v === 'manager' || v === 'employee' ? v : null;
  } catch {
    return null;
  }
}

export function isDemoMode(): boolean {
  return getDemoRole() !== null;
}

export function setDemoRole(role: DemoRole | null): void {
  try {
    if (role) sessionStorage.setItem(ROLE_KEY, role);
    else sessionStorage.removeItem(ROLE_KEY);
  } catch {
    /* storage unavailable: demo then lasts until reload only */
  }
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

type Data = Record<string, unknown>;
const collections = new Map<string, Map<string, Data>>();
let seeded = false;
let idCounter = 0;

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

function col(name: string): Map<string, Data> {
  let c = collections.get(name);
  if (!c) {
    c = new Map();
    collections.set(name, c);
  }
  return c;
}

export function serverTimestamp(): Data {
  const ms = Date.now();
  return { seconds: Math.floor(ms / 1000), nanoseconds: (ms % 1000) * 1e6 };
}

/** Seeds the store once per page load. `seed` receives a raw setter. */
export function ensureSeeded(seed: (set: (c: string, id: string, d: Data) => void) => void): void {
  if (seeded) return;
  seeded = true;
  seed((c, id, d) => {
    col(c).set(id, clone(d));
  });
}

export function resetDemoStore(): void {
  collections.clear();
  seeded = false;
}

// ---------------------------------------------------------------------------
// Refs, snapshots, queries
// ---------------------------------------------------------------------------

interface ColRef {
  __kind: 'col';
  path: string;
}
interface DocRef {
  __kind: 'doc';
  col: string;
  id: string;
  path: string;
}
interface Constraint {
  __kind: 'where';
  field: string;
  op: string;
  value: unknown;
}
interface QueryRef {
  __kind: 'query';
  col: string;
  filters: Constraint[];
}
type AnyRef = ColRef | DocRef | QueryRef;

export function collection(_db: unknown, path: string): ColRef {
  return { __kind: 'col', path };
}

export function doc(_db: unknown, c: string, id: string): DocRef {
  return { __kind: 'doc', col: c, id, path: `${c}/${id}` };
}

export function where(field: string, op: string, value: unknown): Constraint {
  return { __kind: 'where', field, op, value };
}

export function query(base: ColRef | QueryRef, ...constraints: unknown[]): QueryRef {
  const colName = base.__kind === 'col' ? base.path : base.col;
  const prior = base.__kind === 'query' ? base.filters : [];
  const filters = constraints.filter(
    (c): c is Constraint => !!c && (c as Constraint).__kind === 'where'
  );
  return { __kind: 'query', col: colName, filters: [...prior, ...filters] };
}

function matches(data: Data, f: Constraint): boolean {
  const v = data[f.field];
  switch (f.op) {
    case '==':
      return v === f.value;
    case '!=':
      return v !== f.value;
    case 'in':
      return Array.isArray(f.value) && f.value.includes(v);
    case 'array-contains':
      return Array.isArray(v) && v.includes(f.value);
    case '<':
      return (v as number) < (f.value as number);
    case '<=':
      return (v as number) <= (f.value as number);
    case '>':
      return (v as number) > (f.value as number);
    case '>=':
      return (v as number) >= (f.value as number);
    default:
      return false;
  }
}

function docSnap(id: string, data: Data | undefined) {
  return {
    id,
    exists: () => data !== undefined,
    data: () => (data === undefined ? undefined : clone(data)),
  };
}

function querySnap(ref: ColRef | QueryRef) {
  const name = ref.__kind === 'col' ? ref.path : ref.col;
  const filters = ref.__kind === 'query' ? ref.filters : [];
  const docs = [...col(name).entries()]
    .filter(([, d]) => filters.every((f) => matches(d, f)))
    .map(([id, d]) => docSnap(id, d));
  return {
    docs,
    size: docs.length,
    empty: docs.length === 0,
    forEach: (fn: (d: (typeof docs)[number]) => void) => docs.forEach(fn),
  };
}

function snapshotFor(ref: AnyRef) {
  if (ref.__kind === 'doc') return docSnap(ref.id, col(ref.col).get(ref.id));
  return querySnap(ref);
}

// ---------------------------------------------------------------------------
// Realtime listeners
// ---------------------------------------------------------------------------

interface Listener {
  ref: AnyRef;
  next: (snap: unknown) => void;
  active: boolean;
}
const listeners = new Set<Listener>();

function notify(): void {
  for (const l of [...listeners]) {
    if (l.active) l.next(snapshotFor(l.ref));
  }
}

export function onSnapshot(
  ref: AnyRef,
  next: (snap: unknown) => void,
  _error?: (err: unknown) => void
): () => void {
  const l: Listener = { ref, next, active: true };
  listeners.add(l);
  Promise.resolve().then(() => {
    if (l.active) l.next(snapshotFor(ref));
  });
  return () => {
    l.active = false;
    listeners.delete(l);
  };
}

// ---------------------------------------------------------------------------
// Reads and writes
// ---------------------------------------------------------------------------

export async function getDocs(ref: ColRef | QueryRef) {
  return querySnap(ref);
}

export async function getDoc(ref: DocRef) {
  return snapshotFor(ref);
}

function applySet(ref: DocRef, data: Data): void {
  col(ref.col).set(ref.id, clone(data));
}

function applyUpdate(ref: DocRef, data: Data): void {
  const existing = col(ref.col).get(ref.id);
  if (!existing) throw new Error(`No document to update: ${ref.path}`);
  col(ref.col).set(ref.id, { ...existing, ...clone(data) });
}

function applyDelete(ref: DocRef): void {
  col(ref.col).delete(ref.id);
}

export async function setDoc(ref: DocRef, data: Data): Promise<void> {
  applySet(ref, data);
  notify();
}

export async function addDoc(ref: ColRef, data: Data): Promise<{ id: string }> {
  idCounter += 1;
  const id = `demo_${Date.now().toString(36)}_${idCounter}`;
  col(ref.path).set(id, clone(data));
  notify();
  return { id };
}

export async function updateDoc(ref: DocRef, data: Data): Promise<void> {
  applyUpdate(ref, data);
  notify();
}

export async function deleteDoc(ref: DocRef): Promise<void> {
  applyDelete(ref);
  notify();
}

export function writeBatch(_db: unknown) {
  const ops: Array<() => void> = [];
  const batch = {
    set(ref: DocRef, data: Data) {
      ops.push(() => applySet(ref, data));
      return batch;
    },
    update(ref: DocRef, data: Data) {
      ops.push(() => applyUpdate(ref, data));
      return batch;
    },
    delete(ref: DocRef) {
      ops.push(() => applyDelete(ref));
      return batch;
    },
    async commit() {
      ops.forEach((op) => op());
      notify();
    },
  };
  return batch;
}

export async function runTransaction<T>(
  _db: unknown,
  fn: (tx: {
    get: (ref: DocRef) => Promise<ReturnType<typeof docSnap>>;
    set: (ref: DocRef, data: Data) => unknown;
    update: (ref: DocRef, data: Data) => unknown;
    delete: (ref: DocRef) => unknown;
  }) => Promise<T>
): Promise<T> {
  const tx = {
    get: async (ref: DocRef) => snapshotFor(ref) as ReturnType<typeof docSnap>,
    set: (ref: DocRef, data: Data) => applySet(ref, data),
    update: (ref: DocRef, data: Data) => applyUpdate(ref, data),
    delete: (ref: DocRef) => applyDelete(ref),
  };
  const result = await fn(tx);
  notify();
  return result;
}
