import { useMemo, useSyncExternalStore } from "react";
import { CLIENTS, DEMO_IDS, gspNoticeFeed, makeDemoNotices, type Client, type Invoice, type Notice, type Return3B } from "./gst/demo";
import { summarise, type Gstr9cInputs, type RunSummary } from "./gst/recon";
import { decideRoute, needsRefresh, newSession, refreshSession, sessionStatus, verifyOtp, DEFAULT_GSP_ENDPOINTS, type GspSession, type Route, type SessionStatus } from "./gst/gsp";
import { dedupeNotices, noticeFromLibrary } from "./gst/notices";
import { bumpDataVersion, emptyUploads, setUploadProvider, type UploadedData, type UploadedFile } from "./gst/uploads";
import { MONTHS, monthLabel } from "./gst/format";

/* ---------- types ---------- */
export interface Firm {
  name: string;
  frn: string;
  city: string;
  partner: string;
  gstin: string;
}
export interface Run {
  id: string;
  clientId: string;
  fy: string;
  at: string;
  by: string;
  status: "Completed" | "Completed with warnings" | "Failed";
  route?: Route | undefined;
  message?: string | undefined;
  summary?: RunSummary | undefined;
  error?: string | undefined;
}
export interface Activity {
  id: string;
  at: string;
  clientId?: string | undefined;
  action: string;
  by: string;
}
export interface Prefs {
  tolerance: number;
  fy: string;
  defaultFy: string;
  /** "Due soon" window for notices (days) */
  reminderDays: number;
  /** e-mail the assigned staff this many days before the due date */
  emailReminderDays: number;
  retentionYears: number;
}
export interface User {
  id: string;
  name: string;
  email: string;
  role: "Partner" | "Staff";
}
export interface GspSettings {
  baseUrl: string;
  clientId: string;
  /** the secret itself is stored server-side only; the browser keeps just this flag */
  secretConfigured: boolean;
  endpoints: string;
}
export interface Review {
  note: string;
  by: string;
  at: string;
}
export interface AppState {
  firm: Firm | null;
  prefs: Prefs;
  demoLoaded: boolean;
  clients: Client[];
  users: User[];
  currentUserId: string;
  sessions: Record<string, GspSession>;
  gsp: GspSettings;
  runs: Run[];
  activity: Activity[];
  notices: Notice[];
  progress: Record<string, "queued" | "running" | "done" | "failed">;
  dark: boolean;
  followUps: Record<string, string>;
  reviews: Record<string, Review>;
  /** `${clientId}|${form}|${lineId}.${head}` → value */
  draftOverrides: Record<string, number>;
  draftReasons: Record<string, string>;
  gstr9cInputs: Record<string, Gstr9cInputs>;
  /** bumps whenever uploaded data changes so screens recalculate */
  dataVersion: number;
  /** false until saved data has been read from the browser */
  hydrated: boolean;
}

const KEY = "gst-suite-state-v3";
const DATA_KEY = "gst-suite-data-v1";
const OWNER: User = { id: "u-owner", name: "CA Hemant Jadeja", email: "partner@firm.in", role: "Partner" };
const initial: AppState = {
  firm: null,
  prefs: { tolerance: 1, fy: "2025-26", defaultFy: "2025-26", reminderDays: 7, emailReminderDays: 3, retentionYears: 8 },
  demoLoaded: false,
  clients: [],
  users: [OWNER],
  currentUserId: OWNER.id,
  sessions: {},
  gsp: { baseUrl: "", clientId: "", secretConfigured: false, endpoints: JSON.stringify(DEFAULT_GSP_ENDPOINTS, null, 2) },
  runs: [],
  activity: [],
  notices: [],
  progress: {},
  dark: false,
  followUps: {},
  reviews: {},
  draftOverrides: {},
  draftReasons: {},
  gstr9cInputs: {},
  dataVersion: 0,
  hydrated: false,
};
const touchData = () => {
  bumpDataVersion();
  state = { ...state, dataVersion: state.dataVersion + 1 };
};
/** Subscribe a component to uploaded-data changes. */
export const useDataVersion = () => useApp((s) => s.dataVersion);
/** true once saved data has been loaded (avoid flashing empty states) */
export const useHydrated = () => useApp((s) => s.hydrated);

let state: AppState = initial;
let uploads: Record<string, UploadedData> = {};
const listeners = new Set<() => void>();
setUploadProvider((id) => uploads[id]);

function persist() {
  if (typeof window === "undefined") return;
  const { progress: _p, ...rest } = state;
  void _p;
  try {
    localStorage.setItem(KEY, JSON.stringify(rest));
  } catch {
    /* storage full — keep working in memory */
  }
  document.documentElement.classList.toggle("dark", state.dark);
}
function persistData() {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(DATA_KEY, JSON.stringify(uploads));
  } catch {
    throw new Error("Browser storage is full — delete old uploads in Settings › Data, then try again.");
  }
}
function emit() {
  for (const l of listeners) l();
  persist();
}

export function setState(patch: Partial<AppState> | ((s: AppState) => Partial<AppState>)) {
  const p = typeof patch === "function" ? patch(state) : patch;
  state = { ...state, ...p };
  emit();
}

export function hydrateStore() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const saved = JSON.parse(raw) as Partial<AppState>;
      state = { ...initial, ...saved, prefs: { ...initial.prefs, ...saved.prefs }, gsp: { ...initial.gsp, ...saved.gsp }, progress: {} };
    }
    const data = localStorage.getItem(DATA_KEY);
    if (data) uploads = JSON.parse(data) as Record<string, UploadedData>;
    touchData();
  } catch {
    /* ignore corrupt storage */
  }
  state = { ...state, hydrated: true };
  emit();
}

export function useApp<T>(sel: (s: AppState) => T): T {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => sel(state),
    () => sel(initial),
  );
}
export const getState = () => state;

const uid = () => Math.random().toString(36).slice(2, 10);
export const newId = uid;
export const currentUser = (s: AppState = state): User => s.users.find((u) => u.id === s.currentUserId) ?? s.users[0] ?? OWNER;
const who = () => currentUser().name;

export function log(action: string, clientId?: string) {
  setState((s) => ({ activity: [{ id: uid(), at: new Date().toISOString(), clientId, action, by: who() }, ...s.activity].slice(0, 1000) }));
}

/* ---------- clients & roles ---------- */
/** Partner sees all clients; Staff only the clients assigned to them. */
export function visibleClients(s: AppState = state): Client[] {
  const u = currentUser(s);
  return u.role === "Partner" ? s.clients : s.clients.filter((c) => c.staff.trim().toLowerCase() === u.name.trim().toLowerCase() || c.staff.trim().toLowerCase() === u.email.toLowerCase());
}
export function useClients(): Client[] {
  // derive from the subscribed snapshot (not live state) so server and first browser render agree
  const clients = useApp((s) => s.clients);
  const currentUserId = useApp((s) => s.currentUserId);
  const users = useApp((s) => s.users);
  return useMemo(() => visibleClients({ ...state, clients, users, currentUserId }), [clients, users, currentUserId]);
}
/** Current user from the subscribed snapshot (safe to use while rendering). */
export function useCurrentUser(): User {
  const users = useApp((s) => s.users);
  const currentUserId = useApp((s) => s.currentUserId);
  return users.find((u) => u.id === currentUserId) ?? users[0] ?? OWNER;
}
export const findClient = (id: string) => state.clients.find((c) => c.id === id);
export function useClient(id: string): Client | undefined {
  return useApp((s) => s.clients.find((c) => c.id === id));
}
export function canSee(clientId: string) {
  return visibleClients().some((c) => c.id === clientId);
}

export function saveClient(c: Client, isNew: boolean) {
  setState((s) => ({ clients: isNew ? [...s.clients, c] : s.clients.map((x) => (x.id === c.id ? c : x)) }));
  log(`${isNew ? "Added" : "Changed"} client ${c.name}`, c.id);
}
export function updateClients(ids: string[], patch: Partial<Client>, what: string) {
  setState((s) => ({ clients: s.clients.map((c) => (ids.includes(c.id) ? { ...c, ...patch } : c)) }));
  log(`${what} for ${ids.length} client(s)`);
}

/** Delete a client's uploads, runs, notices, sessions and drafts (optionally the client itself). */
export function deleteClientData(clientId: string, removeClient: boolean) {
  const c = findClient(clientId);
  delete uploads[clientId];
  persistData();
  touchData();
  setState((s) => {
    const drop = <T,>(o: Record<string, T>) => Object.fromEntries(Object.entries(o).filter(([k]) => !k.startsWith(clientId + "|") && k !== clientId));
    const sessions = { ...s.sessions };
    delete sessions[clientId];
    return {
      clients: removeClient ? s.clients.filter((x) => x.id !== clientId) : s.clients,
      runs: s.runs.filter((r) => r.clientId !== clientId),
      notices: s.notices.filter((n) => n.clientId !== clientId),
      sessions,
      reviews: drop(s.reviews),
      draftOverrides: drop(s.draftOverrides),
      draftReasons: drop(s.draftReasons),
      gstr9cInputs: drop(s.gstr9cInputs),
      followUps: drop(s.followUps),
    };
  });
  log(`Deleted client data${removeClient ? " and removed the client" : ""}: ${c?.name ?? clientId}`);
}

export function saveUser(u: User) {
  setState((s) => ({ users: s.users.some((x) => x.id === u.id) ? s.users.map((x) => (x.id === u.id ? u : x)) : [...s.users, u] }));
  log(`Staff ${u.name} saved as ${u.role}`);
}
export function removeUser(id: string) {
  if (id === state.currentUserId) throw new Error("You cannot remove the user you are signed in as.");
  setState((s) => ({ users: s.users.filter((u) => u.id !== id) }));
  log("Removed a staff member");
}
export function switchUser(id: string) {
  setState({ currentUserId: id });
  log(`Signed in as ${currentUser().name} (${currentUser().role})`);
}

/* ---------- demo firm ---------- */
export const DEMO_FIRM: Firm = {
  name: "Jadeja & Associates, Chartered Accountants",
  frn: "123456W",
  city: "Ahmedabad",
  partner: "CA Hemant Jadeja",
  gstin: "",
};
const DEMO_STAFF: User[] = [
  { id: "u-riya", name: "Riya Shah", email: "riya.shah@demofirm.in", role: "Staff" },
  { id: "u-amit", name: "Amit Desai", email: "amit.desai@demofirm.in", role: "Staff" },
];

export function loadDemoFirm() {
  const now = new Date();
  for (const id of DEMO_IDS) delete uploads[id];
  persistData();
  touchData();
  setState((s) => ({
    firm: s.firm ?? DEMO_FIRM,
    demoLoaded: true,
    clients: [...CLIENTS.map((c) => ({ ...c })), ...s.clients.filter((c) => !DEMO_IDS.has(c.id))],
    users: [...s.users.filter((u) => !DEMO_STAFF.some((d) => d.id === u.id)), ...DEMO_STAFF],
    notices: [...makeDemoNotices(now, (n) => noticeFromLibrary(n, now)), ...s.notices.filter((n) => !DEMO_IDS.has(n.clientId))],
    // Shree Ganesh: connected for 6 hours; Patel: 25 minutes left (auto-refresh demo); Mehta: API not enabled
    sessions: { ...s.sessions, "shree-ganesh": newSession(now), "patel-polymers": newSession(now, 25 / 60) },
    runs: s.runs.filter((r) => !DEMO_IDS.has(r.clientId)),
  }));
  log(`Loaded demo firm with ${CLIENTS.length} clients and 6 notices`);
}

export function resetAll() {
  uploads = {};
  persistData();
  touchData();
  state = { ...initial, dark: state.dark, dataVersion: state.dataVersion + 1, hydrated: true };
  emit();
}

/* ---------- GSP sessions (OTP based, no passwords) ---------- */
export const sessionOf = (clientId: string): SessionStatus => sessionStatus(state.sessions[clientId]);
export function verifyClientOtp(clientId: string, otp: string) {
  const s = verifyOtp(otp);
  setState((st) => ({ sessions: { ...st.sessions, [clientId]: s } }));
  log("GSP connected (OTP verified)", clientId);
  return s;
}
export function refreshClientSession(clientId: string, auto = false) {
  const s = refreshSession(state.sessions[clientId]);
  setState((st) => ({ sessions: { ...st.sessions, [clientId]: s } }));
  log(`GSP token ${auto ? "auto-" : ""}refreshed`, clientId);
  return s;
}
/** Called every minute: refresh tokens that are about to expire. */
export function autoRefreshSessions() {
  for (const c of state.clients) if (needsRefresh(state.sessions[c.id])) refreshClientSession(c.id, true);
}

/* ---------- uploads ---------- */
export const uploadsOf = (clientId: string): UploadedData => uploads[clientId] ?? emptyUploads();
function writeUploads(clientId: string, fn: (u: UploadedData) => void) {
  const u = structuredClone(uploadsOf(clientId));
  fn(u);
  uploads[clientId] = u;
  persistData();
  touchData();
  emit();
}
export function addUploadedFile(clientId: string, f: Omit<UploadedFile, "id" | "at" | "by">) {
  writeUploads(clientId, (u) => {
    u.files.unshift({ ...f, id: uid(), at: new Date().toISOString(), by: who() });
  });
  log(`${f.status === "Rejected" ? "Rejected file" : "Uploaded"} ${f.name}${f.message ? ` — ${f.message}` : ""}`, clientId);
}
export function storeReturnRows(clientId: string, kind: "gstr1" | "gstr2b", month: string, rows: Invoice[]) {
  writeUploads(clientId, (u) => {
    u[kind][month] = rows;
  });
}
export function store3b(clientId: string, byMonth: Record<string, Return3B>) {
  writeUploads(clientId, (u) => {
    Object.assign(u.gstr3b, byMonth);
  });
}
export function storeBooks(clientId: string, kind: "sales" | "purchases", rows: Invoice[], label: string) {
  writeUploads(clientId, (u) => {
    u[kind] = rows;
    u.booksLabel = { ...u.booksLabel, [kind]: label };
  });
  log(`Books loaded: ${rows.length} ${kind === "sales" ? "sales" : "purchase"} vouchers (${label})`, clientId);
}
export function saveMapping(clientId: string, kind: "sales" | "purchase", mapping: Record<string, string>) {
  writeUploads(clientId, (u) => {
    u.mapping = { ...u.mapping, [kind]: mapping };
  });
}
export function deleteUploadedFile(clientId: string, fileId: string) {
  writeUploads(clientId, (u) => {
    u.files = u.files.filter((f) => f.id !== fileId);
  });
  log("Removed a file from the list", clientId);
}
/** Manual override of a purchase category (Inputs / Capital goods / Input services). */
export function setPurchaseCategory(clientId: string, invoices: Invoice[], ids: string[], itcType: Invoice["itcType"]) {
  writeUploads(clientId, (u) => {
    u.purchases = invoices.map((p) => (ids.includes(p.id) ? { ...p, itcType } : p));
    u.booksLabel = { ...u.booksLabel, purchases: u.booksLabel?.purchases ?? "Books (with category edits)" };
  });
  log(`Purchase category set to ${itcType} for ${ids.length} invoice(s)`, clientId);
}

/* ---------- runs ---------- */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Run one client end-to-end. Throws only for unexpected errors; GSP problems give a Failed run. */
export async function runClient(clientId: string): Promise<Run> {
  setState((s) => ({ progress: { ...s.progress, [clientId]: "running" } }));
  const c = findClient(clientId);
  let run: Run;
  const base = { id: uid(), clientId, fy: state.prefs.fy, at: new Date().toISOString(), by: who() };
  try {
    if (!c) throw new Error("Client not found");
    if (needsRefresh(state.sessions[clientId])) refreshClientSession(clientId, true);
    const decision = decideRoute(c, sessionOf(clientId));
    if (decision.error) throw new Error(decision.error);
    await sleep(decision.route === "GSP API" ? 700 + Math.random() * 500 : 350 + Math.random() * 300);
    if (decision.route === "GSP API" && c.fetchReturns) log("Returns fetched through the GSP (GSTR-1, GSTR-2B, GSTR-3B)", clientId);
    const summary = summarise(clientId, state.prefs.tolerance);
    const missing = Object.entries(summary.missing).flatMap(([k, ms]) => ms.map((m) => `${k.toUpperCase().replace("GSTR", "GSTR-")} ${monthLabel(m)}`));
    const message = summary.partialMonths.length
      ? `Partial data — missing ${missing.slice(0, 6).join(", ")}${missing.length > 6 ? "…" : ""}`
      : summary.differences
        ? `Differences in ${Object.entries(summary.byR).filter(([, v]) => v === "Difference").map(([k]) => k).join(", ")}`
        : "All six reconciliations matched";
    run = { ...base, status: summary.partialMonths.length ? "Completed with warnings" : "Completed", route: decision.route, message: `${decision.reason}. ${message}`, summary };
  } catch (e) {
    run = { ...base, status: "Failed", error: e instanceof Error ? e.message : "Unknown error" };
  }
  setState((s) => ({ runs: [run, ...s.runs].slice(0, 300), progress: { ...s.progress, [clientId]: run.status === "Failed" ? "failed" : "done" } }));
  log(`Reconciliation ${run.status.toLowerCase()}${run.error ? ` — ${run.error}` : run.summary ? ` — ${run.summary.differences} difference(s)` : ""}`, clientId);
  return run;
}

export async function runAll(ids?: string[]) {
  const list = (ids ? visibleClients().filter((c) => ids.includes(c.id)) : visibleClients().filter((c) => c.active)).map((c) => c.id);
  setState({ progress: Object.fromEntries(list.map((id) => [id, "queued" as const])) });
  for (const id of list) {
    // one client failing never stops the rest
    try {
      await runClient(id);
    } catch {
      setState((s) => ({ progress: { ...s.progress, [id]: "failed" } }));
    }
  }
}

/** "Check notices only": fetch notices of the last 60 days for GSP-connected clients. */
export async function checkNotices(): Promise<{ added: number; skipped: string[] }> {
  let added = 0;
  const skipped: string[] = [];
  const list = visibleClients().filter((c) => c.active);
  setState({ progress: Object.fromEntries(list.map((c) => [c.id, "queued" as const])) });
  for (const c of list) {
    setState((s) => ({ progress: { ...s.progress, [c.id]: "running" } }));
    await sleep(300);
    const d = decideRoute(c, sessionOf(c.id));
    if (!c.fetchNotices || d.route !== "GSP API" || d.error) {
      skipped.push(`${c.name}: ${!c.fetchNotices ? "fetch notices is off" : "not connected to the GSP — upload the notices template instead"}`);
      setState((s) => ({ progress: { ...s.progress, [c.id]: "done" } }));
      continue;
    }
    const feed = gspNoticeFeed(c.gstin).map((n) => noticeFromLibrary({ ...n, clientId: c.id, source: "GSP notices API", assignedTo: c.staff }));
    const fresh = dedupeNotices(state.notices, feed);
    if (fresh.length) setState((s) => ({ notices: [...fresh, ...s.notices] }));
    added += fresh.length;
    log(`Notices checked through the GSP: ${feed.length} on portal, ${fresh.length} new`, c.id);
    setState((s) => ({ progress: { ...s.progress, [c.id]: "done" } }));
  }
  return { added, skipped };
}

export function latestRun(runs: Run[], clientId: string, okOnly = false): Run | undefined {
  return runs.find((r) => r.clientId === clientId && (!okOnly || r.status !== "Failed"));
}

/* ---------- notices ---------- */
export function saveNotice(n: Notice) {
  const exists = state.notices.some((x) => x.id === n.id);
  setState((s) => ({ notices: exists ? s.notices.map((x) => (x.id === n.id ? n : x)) : [n, ...s.notices] }));
  log(`${exists ? "Updated" : "Added"} ${n.form} notice ${n.ref} — ${n.status}`, n.clientId);
}
export function addNotices(list: Notice[]): number {
  const fresh = dedupeNotices(state.notices, list);
  if (fresh.length) setState((s) => ({ notices: [...fresh, ...s.notices] }));
  for (const n of fresh) log(`Added ${n.form} notice ${n.ref} (${n.source})`, n.clientId);
  return fresh.length;
}
export function deleteNotice(id: string) {
  const n = state.notices.find((x) => x.id === id);
  setState((s) => ({ notices: s.notices.filter((x) => x.id !== id) }));
  if (n) log(`Deleted ${n.form} notice ${n.ref}`, n.clientId);
}
export function markReplied(id: string) {
  const n = state.notices.find((x) => x.id === id);
  if (n) saveNotice({ ...n, status: "Replied", replied: true, repliedOn: new Date().toISOString().slice(0, 10) });
}

/* ---------- supplier follow-up & reviews ---------- */
export function markFollowUp(key: string, clientId: string, supplier: string) {
  setState((s) => ({ followUps: { ...s.followUps, [key]: new Date().toISOString() } }));
  log(`Reminder sent to supplier ${supplier}`, clientId);
}
export function setReview(clientId: string, side: string, keys: string[], note: string | null) {
  setState((s) => {
    const next = { ...s.reviews };
    for (const k of keys) {
      const rk = `${clientId}|${side}|${k}`;
      if (note === null) delete next[rk];
      else next[rk] = { note, by: who(), at: new Date().toISOString() };
    }
    return { reviews: next };
  });
  log(`${note === null ? "Cleared review on" : "Marked reviewed"} ${keys.length} ${side === "sales" ? "sales" : "ITC"} invoice row(s)${note ? `: ${note}` : ""}`, clientId);
}

/* ---------- GSTR-9 / 9C draft edits ---------- */
export function setOverride(clientId: string, form: string, key: string, value: number | undefined) {
  const k = `${clientId}|${form}|${key}`;
  setState((s) => {
    const next = { ...s.draftOverrides };
    if (value === undefined) delete next[k];
    else next[k] = value;
    return { draftOverrides: next };
  });
  log(`${value === undefined ? "Reset" : "Manually overrode"} ${form} ${key}${value === undefined ? "" : ` to ${value}`}`, clientId);
}
export function overridesFor(all: Record<string, number>, clientId: string, form: string): Record<string, number> {
  const p = `${clientId}|${form}|`;
  return Object.fromEntries(Object.entries(all).filter(([k]) => k.startsWith(p)).map(([k, v]) => [k.slice(p.length), v]));
}
export function setReason(clientId: string, lineId: string, reason: string) {
  setState((s) => ({ draftReasons: { ...s.draftReasons, [`${clientId}|${lineId}`]: reason } }));
  log(`Reason recorded for ${lineId}`, clientId);
}
export function set9cInputs(clientId: string, inputs: Gstr9cInputs) {
  setState((s) => ({ gstr9cInputs: { ...s.gstr9cInputs, [clientId]: inputs } }));
}

/* ---------- retention ---------- */
export function applyRetention(years: number) {
  const cutoff = new Date();
  cutoff.setFullYear(cutoff.getFullYear() - years);
  const c = cutoff.toISOString();
  setState((s) => ({ prefs: { ...s.prefs, retentionYears: years }, runs: s.runs.filter((r) => r.at >= c), activity: s.activity.filter((a) => a.at >= c) }));
  log(`Retention applied: run history and activity older than ${years} years removed`);
}

export const FY_MONTHS = MONTHS;
