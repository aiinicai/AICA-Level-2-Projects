// Page side of the "3CD Helper – Tally Connector" Chrome extension (folder tally-connector/).
// The extension's content script marks the page and relays window messages to its background worker,
// which talks to TallyPrime on this computer. Only fixed read-only requests are possible.

export interface TallyCompany { name: string; booksFrom: string }
export type TallyMode = "daybook" | "loans";
export interface TallyCounts { groups: number; ledgers: number; vouchers: number; unsecuredLedgers: number | null; groupLedgers?: number | null }
export interface TallyGroup { name: string; parent: string; ledgers: number }
export interface GroupNode { name: string; depth: number; ledgers: number; total: number }

/** Connector version a feature needs ("1.0.3" ≥ "1.0.2"). */
export function versionAtLeast(v: string | null, min: string): boolean {
  if (!v) return false;
  const a = v.split(".").map(Number), b = min.split(".").map(Number);
  for (let i = 0; i < 3; i++) { if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0); }
  return true;
}
/** First connector version that fills the GST portal search and sends the taxpayer type back. */
export const GST_VERSION = "1.0.4";
export interface PortalResult { gstin: string; taxpayerType: string; status: string; legalName: string; at: number }
/** First connector version with the "groups" request. */
export const GROUPS_VERSION = "1.0.3";

/** A group and everything under it, in tree order; total = ledgers in the group and its sub-groups. */
export function groupTree(groups: TallyGroup[], root: string): GroupNode[] {
  const kids = new Map<string, TallyGroup[]>();
  groups.forEach((g) => { const p = g.parent.toLowerCase(); kids.set(p, [...(kids.get(p) ?? []), g]); });
  const start = groups.find((g) => g.name.toLowerCase() === root.toLowerCase());
  if (!start) return [];
  const out: GroupNode[] = [];
  const walk = (g: TallyGroup, depth: number, seen: Set<string>): number => {
    const k = g.name.toLowerCase();
    if (seen.has(k) || depth > 12) return 0;
    seen.add(k);
    const node: GroupNode = { name: g.name, depth, ledgers: g.ledgers, total: g.ledgers };
    out.push(node);
    for (const c of (kids.get(k) ?? []).sort((a, b) => a.name.localeCompare(b.name))) node.total += walk(c, depth + 1, seen);
    return node.total;
  };
  walk(start, 0, new Set());
  return out;
}
/** Primary groups offered for Clause 31, and whether they are ticked at first. */
export const LOAN_ROOTS: [string, boolean][] = [["Loans (Liability)", true], ["Loans & Advances (Asset)", false], ["Deposits (Asset)", false]];

/** Version of the installed connector, or null. */
export function connectorVersion(): string | null {
  if (typeof document === "undefined") return null;
  return document.documentElement.getAttribute("data-tally-connector");
}

let seq = 0;

/** One request to the connector. Large answers arrive in chunks and are joined. */
export function callConnector<R = any>(action: "ping" | "companies" | "groups" | "fetch" | "gstOpen" | "gstResults", params: Record<string, unknown> = {}, onProgress?: (text: string) => void, timeoutMs = 30 * 60 * 1000): Promise<{ result: R; data: string }> {
  return new Promise((resolve, reject) => {
    if (!connectorVersion()) { reject(new Error("The Tally Connector is not installed in this browser")); return; }
    const id = `t${Date.now()}_${++seq}`;
    const parts: string[] = [];
    let timer: ReturnType<typeof setTimeout>;
    const arm = () => { clearTimeout(timer); timer = setTimeout(() => { done(); reject(new Error("The Tally Connector stopped answering")); }, action === "ping" ? 3000 : timeoutMs); };
    const done = () => { clearTimeout(timer); window.removeEventListener("message", on); };
    const on = (ev: MessageEvent) => {
      const m = ev.data;
      if (ev.source !== window || !m || m.source !== "3cd-tally-connector" || m.id !== id) return;
      arm();
      if (m.type === "progress") onProgress?.(m.text);
      else if (m.type === "chunk") parts.push(m.data);
      else if (m.type === "error") { done(); reject(new Error(m.error || "Tally Connector error")); }
      else if (m.type === "done") { done(); resolve({ result: m.result, data: parts.join("") }); }
    };
    window.addEventListener("message", on);
    arm();
    window.postMessage({ source: "3cd-helper-app", id, action, params }, window.location.origin);
  });
}

/** Financial year of an assessment year: "2026-27" → 2025-04-01 … 2026-03-31. */
export function fyOfAy(ay: string): { from: string; to: string } {
  const y = parseInt(String(ay).slice(0, 4), 10);
  if (!isFinite(y)) return { from: "", to: "" };
  return { from: `${y - 1}-04-01`, to: `${y}-03-31` };
}

/** Company in Tally that best matches the client's name. */
export function matchCompany(companies: TallyCompany[], clientName: string): string {
  const n = (s: string) => s.toLowerCase().replace(/\b(private|pvt|limited|ltd|llp|m\/s)\b/g, "").replace(/[^a-z0-9]+/g, "");
  const c = n(clientName);
  const hit = companies.find((x) => n(x.name) === c) ?? companies.find((x) => c && (n(x.name).includes(c) || c.includes(n(x.name))));
  return (hit ?? companies[0])?.name ?? "";
}
