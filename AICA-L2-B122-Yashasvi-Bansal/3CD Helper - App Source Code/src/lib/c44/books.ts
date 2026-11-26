// Clause 44 – "ledger method": reads Tally books (groups, ledger masters, vouchers) and builds the
// break-up ledger by ledger instead of line by line.
//  1. Expense ledgers (Purchase Accounts, Direct / Indirect Expenses) and Fixed Assets are chosen;
//     salary, wages, PF / ESIC, government fees, depreciation, provisions, write-offs are left out.
//  2. Each expense line is tied to the party of its voucher; no party (cash / direct bank) → unregistered.
//  3. The party's GST status comes from its Tally master (registration type, GSTIN).
//  4. Exempt comes from the expense ledger's GST taxability.
//  5. Amounts are the expense only (input GST is a separate ledger); debit notes reduce the expense.
//     For Fixed Assets only additions (debits) count – sales and depreciation are not expenditure.
import { type XNode, findAll, childText } from "../import/xml";
import { isValidGstin as gstinValid } from "../validators";
import { normalizeParty } from "../party";
import type { Category } from "../clause44";

export type RegType = "regular" | "composition" | "unregistered" | "unknown" | "";
export type Taxability = "taxable" | "exempt" | "nil" | "nongst" | "";
export type LedgerKind = "revenue" | "capital";

export interface BookLedger {
  name: string; parent: string; chain: string[]; primary: string;
  gstin: string; reg: RegType; tax: Taxability; pan: string;
}
export interface BookLine { ledger: string; amount: number }   // + debit, − credit
export interface BookVoucher { date: string; type: string; no: string; party: string; partyGstin: string; lines: BookLine[] }
export interface Books { company: string; groups: { name: string; parent: string }[]; ledgers: BookLedger[]; vouchers: BookVoucher[] }

const num = (s: string) => { const v = parseFloat(String(s ?? "").replace(/,/g, "")); return isFinite(v) ? v : 0; };
const r2 = (n: number) => Math.round(n * 100) / 100;
const low = (s: string) => s.trim().toLowerCase();
/** Tally writes the parent of a primary group as nothing or as "&#4; Primary". */
const isPrimary = (p: string) => /^\W*primary$/i.test(p.trim());

function regOf(s: string): RegType {
  const t = low(s);
  if (!t) return "";
  if (t.startsWith("regular")) return "regular";
  if (t.startsWith("composition")) return "composition";
  if (t.startsWith("unregistered") || t.startsWith("consumer")) return "unregistered";
  return "unknown";
}
function taxOf(s: string): Taxability {
  const t = low(s);
  if (!t) return "";
  if (t.startsWith("exempt")) return "exempt";
  if (t.startsWith("nil")) return "nil";
  if (t.includes("non") && t.includes("gst")) return "nongst";
  return "taxable";
}

/** Groups, ledger masters and vouchers of a Tally XML (Day Book with masters, or the Tally Connector file). */
export function readBooks(root: XNode): Books {
  const parentOf = new Map<string, { name: string; parent: string }>();
  for (const g of findAll(root, "GROUP")) {
    const name = (g.attrs["NAME"] || childText(g, "NAME")).trim();
    const par = childText(g, "PARENT").trim();
    if (name && !parentOf.has(low(name))) parentOf.set(low(name), { name, parent: isPrimary(par) ? "" : par });
  }
  const chainOf = (parent: string) => {
    const c: string[] = []; let p = parent;
    for (let i = 0; p && !isPrimary(p) && i < 15; i++) { c.push(parentOf.get(low(p))?.name ?? p); p = parentOf.get(low(p))?.parent ?? ""; }
    return c;
  };
  const ledgers: BookLedger[] = [];
  const seen = new Set<string>();
  for (const l of findAll(root, "LEDGER")) {
    const name = (l.attrs["NAME"] || childText(l, "NAME")).trim();
    if (!name || seen.has(low(name))) continue;
    seen.add(low(name));
    const par = childText(l, "PARENT").trim();
    const parent = isPrimary(par) ? "" : par;
    const chain = chainOf(parent);
    // newer TallyPrime keeps registration in LEDGSTREGDETAILS (latest last); older in the ledger itself
    const regs = findAll(l, "LEDGSTREGDETAILS.LIST");
    const lastReg = regs[regs.length - 1];
    const gstin = ((lastReg && childText(lastReg, "GSTIN")) || childText(l, "PARTYGSTIN") || childText(l, "GSTIN")).trim().toUpperCase();
    const reg = regOf((lastReg && childText(lastReg, "GSTREGISTRATIONTYPE")) || childText(l, "GSTREGISTRATIONTYPE"));
    const det = findAll(l, "GSTDETAILS.LIST").filter((d) => childText(d, "TAXABILITY"));
    let tax = det.length ? taxOf(childText(det[det.length - 1], "TAXABILITY")) : "";
    if (/^yes$/i.test(childText(l, "ISNONGSTGOODS"))) tax = "nongst";
    ledgers.push({ name, parent, chain, primary: chain[chain.length - 1] ?? "", gstin, reg, tax, pan: childText(l, "INCOMETAXNUMBER").trim().toUpperCase() });
  }

  const vouchers: BookVoucher[] = [];
  for (const v of findAll(root, "VOUCHER")) {
    const type = v.attrs["VCHTYPE"] || childText(v, "VOUCHERTYPENAME");
    if (/order|memo|delivery|receipt note|stock|physical|rejection/i.test(type)) continue;
    if (/^yes$/i.test(childText(v, "ISCANCELLED")) || /^yes$/i.test(childText(v, "ISOPTIONAL"))) continue;
    const take = (names: string[]) => v.children.filter((c) => names.includes(c.name)).map((l) => ({ ledger: childText(l, "LEDGERNAME").trim(), amount: -num(childText(l, "AMOUNT")) }));
    let lines = take(["ALLLEDGERENTRIES.LIST"]);
    if (!lines.length) lines = take(["LEDGERENTRIES.LIST"]);
    // invoice-mode vouchers exported from the Day Book keep the purchase ledger under the stock lines
    const alloc = v.children.filter((c) => c.name === "ALLINVENTORYENTRIES.LIST" || c.name === "INVENTORYENTRIES.LIST")
      .flatMap((i) => i.children.filter((c) => c.name === "ACCOUNTINGALLOCATIONS.LIST"))
      .map((l) => ({ ledger: childText(l, "LEDGERNAME").trim(), amount: -num(childText(l, "AMOUNT")) }));
    const sum = (ls: BookLine[]) => ls.reduce((s, l) => s + l.amount, 0);
    if (alloc.length && Math.abs(sum(lines)) > 0.5 && Math.abs(sum(lines) + sum(alloc)) < Math.abs(sum(lines))) lines = lines.concat(alloc);
    lines = lines.filter((l) => l.ledger && l.amount);
    if (!lines.length) continue;
    const d = childText(v, "DATE");
    vouchers.push({ date: /^\d{8}$/.test(d) ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : d, type, no: childText(v, "VOUCHERNUMBER"),
      party: (childText(v, "PARTYLEDGERNAME") || childText(v, "PARTYNAME")).trim(), partyGstin: childText(v, "PARTYGSTIN").trim().toUpperCase(), lines });
  }
  return { company: "", groups: Array.from(parentOf.values()), ledgers, vouchers };
}

export function mergeBooks(list: Books[]): Books {
  const ledgers = new Map<string, BookLedger>(); const groups = new Map<string, { name: string; parent: string }>();
  for (const b of list) { b.ledgers.forEach((l) => { if (!ledgers.has(low(l.name)) || (!ledgers.get(low(l.name))!.chain.length && l.chain.length)) ledgers.set(low(l.name), l); }); b.groups.forEach((g) => groups.set(low(g.name), g)); }
  return { company: list.find((b) => b.company)?.company ?? "", groups: Array.from(groups.values()), ledgers: Array.from(ledgers.values()), vouchers: list.flatMap((b) => b.vouchers) };
}

// ---------- which ledgers ----------
const REVENUE = ["purchase accounts", "direct expenses", "indirect expenses"];
const CAPITAL = ["fixed assets"];
const CASH = ["cash-in-hand"];
const BANK = ["bank accounts", "bank od a/c", "bank occ a/c"];
const TAXES = ["duties & taxes"];

/** Why a ledger is left out of Clause 44 by default (null = included). */
export function defaultExclusion(name: string, chain: string[]): string | null {
  const s = [name, ...chain.slice(0, -1)].join(" | ").toLowerCase();
  if (/depreciation|amorti[sz]ation/.test(s)) return "Depreciation / amortisation";
  if (/provision/.test(s)) return "Provision";
  if (/written\s*off|write\s*off|w\/off|bad\s*debt/.test(s)) return "Write-off";
  if (/salar|wages|bonus|gratuity|leave\s*encash|remuneration|stipend|incentive to staff|staff\s*incentive/.test(s)) return "Salary / wages";
  if (/\b(esic?|e\.s\.i\.?c?|epf|pf|p\.f\.|provident|employees?'? state insurance|labour welfare|lwf)\b/.test(s)) return "PF / ESIC";
  if (/\b(roc|mca)\b|government|govt|stamp\s*duty|court\s*fee|registration\s*fee|municipal|property\s*tax|professional\s*tax|\bp\.?\s?tax\b|licen[cs]e\s*fee|land\s*revenue|late\s*fee|penalt|income\s*tax|deferred\s*tax|current\s*tax|\btds\b|\b(gst|igst|cgst|sgst)\s*(rcm|payable|paid|tax|late|interest|penalt)|rcm\s*tax|interest\s*on\s*(tds|gst|income|delayed\s*payment\s*of\s*tax)/.test(s)) return "Government fees / taxes";
  if (/loss\s*on\s*(sale|discard|disposal)|loss\s*by\s*fire|exchange\s*(loss|fluctuation)|prior\s*period/.test(s)) return "Book entry, not a payment";
  if (/discount\s*allowed|rate\s*difference\s*allowed|sales\s*return/.test(s)) return "Not a purchase (customer side)";
  if (/round(ed)?[\s-]*off|rounding/.test(s)) return "Round off";
  if (/opening\s*stock|closing\s*stock/.test(s)) return "Stock";
  return null;
}

export interface LedgerPick { name: string; group: string; primary: string; kind: LedgerKind; tax: Taxability; exclusion: string | null }

/** Ledgers that can go into Clause 44: P&L expense ledgers and Fixed Assets, in the books' order of groups. */
export function candidateLedgers(b: Books): LedgerPick[] {
  return b.ledgers.flatMap((l) => {
    const p = low(l.primary);
    const kind: LedgerKind | null = REVENUE.includes(p) ? "revenue" : CAPITAL.includes(p) ? "capital" : null;
    if (!kind) return [];
    // interest is an exempt supply (financial service) when Tally does not say otherwise
    const tax: Taxability = l.tax || (/non[\s-]*gst|exempt|nil[\s-]*rated/i.test(l.name) ? "exempt" : kind === "revenue" && /\binterest\b/i.test(l.name) ? "exempt" : "");
    return [{ name: l.name, group: l.parent, primary: l.primary, kind, tax, exclusion: kind === "revenue" ? defaultExclusion(l.name, l.chain) : null }];
  });
}

// ---------- tying expense lines to parties ----------
export interface BookParty { key: string; name: string; gstin: string; reg: RegType; pan: string; via: "party" | "bank" | "cash" | "none"; gstBills: number; bills: number; trade: boolean }
export interface LedgerPartyAmount { ledger: string; kind: LedgerKind; party: string; amount: number; entries: number }
export interface BookResult {
  rows: LedgerPartyAmount[];          // ledger × party, net amount (capital: additions only)
  parties: Record<string, BookParty>;
  ledgerTotals: Record<string, number>;  // every candidate ledger's own net (debit +) for the period – for the reconciliation
  notCounted: Record<string, number>;    // Fixed Asset credits (sales, depreciation) left out
  capitalAdded: Record<string, number>;  // Fixed Asset additions counted (after returns, without transfers)
}

export const NO_PARTY = "Cash / bank payments (no party)";

/** Ties each line of the chosen ledgers to its voucher's party. `chosen` = lower-case ledger names. */
export function buildBreakup(b: Books, chosen: Set<string>): BookResult {
  const led = new Map(b.ledgers.map((l) => [low(l.name), l]));
  const prim = (n: string) => low(led.get(low(n))?.primary ?? "");
  const chainHas = (n: string, list: string[]) => (led.get(low(n))?.chain ?? []).some((c) => list.includes(low(c)));
  const isCash = (n: string) => chainHas(n, CASH) || (!led.has(low(n)) && /^(petty\s*)?cash\b/i.test(n));
  const isBank = (n: string) => chainHas(n, BANK);
  const isTax = (n: string) => chainHas(n, TAXES);
  const isGstTax = (n: string) => isTax(n) && /gst|cess/i.test(n);
  const candidates = new Map(candidateLedgers(b).map((c) => [low(c.name), c]));
  /** Ledgers that are never a "party": expenses, incomes, fixed assets, taxes, cash, bank, stock. */
  const notParty = (n: string) => {
    const p = prim(n);
    return candidates.has(low(n)) || ["sales accounts", "direct incomes", "indirect incomes", "purchase accounts", "direct expenses", "indirect expenses", "fixed assets"].includes(p)
      || isTax(n) || isCash(n) || isBank(n) || chainHas(n, ["stock-in-hand", "provisions"]);
  };

  const parties: Record<string, BookParty> = {};
  const keyOwner = new Map<string, string>();   // key → the ledger name that holds it
  const keyFor = (name: string) => {
    const k = normalizeParty(name) || low(name);
    const owner = keyOwner.get(k);
    if (!owner) { keyOwner.set(k, low(name)); return k; }
    return owner === low(name) ? k : low(name).slice(0, 300);
  };
  const partyOf = (name: string, via: BookParty["via"], gstinOnVoucher = ""): BookParty => {
    const key = via === "cash" || via === "none" ? normalizeParty(NO_PARTY) || NO_PARTY.toLowerCase() : keyFor(name);
    if (!parties[key]) {
      const m = led.get(low(name));
      parties[key] = via === "cash" || via === "none"
        ? { key, name: NO_PARTY, gstin: "", reg: "unregistered", pan: "", via, gstBills: 0, bills: 0, trade: false }
        : { key, name, gstin: m?.gstin || gstinOnVoucher, reg: via === "bank" ? "" : (m?.reg ?? ""), pan: m?.pan ?? "", via, gstBills: 0, bills: 0,
            trade: chainHas(name, ["sundry creditors", "sundry debtors"]) };
    } else if (!parties[key].gstin && gstinOnVoucher) parties[key].gstin = gstinOnVoucher;
    return parties[key];
  };

  const acc = new Map<string, LedgerPartyAmount>();
  const ledgerTotals: Record<string, number> = {};
  const notCounted: Record<string, number> = {};
  const capitalAdded: Record<string, number> = {};
  const add = (ledger: string, kind: LedgerKind, party: BookParty, amount: number) => {
    const k = `${low(ledger)}|${party.key}`;
    const e = acc.get(k) ?? { ledger, kind, party: party.key, amount: 0, entries: 0 };
    e.amount += amount; e.entries++;
    if (kind === "capital") capitalAdded[ledger] = (capitalAdded[ledger] ?? 0) + amount;
    acc.set(k, e);
  };

  for (const v of b.vouchers) {
    for (const l of v.lines) {
      const c = candidates.get(low(l.ledger));
      if (c) ledgerTotals[c.name] = (ledgerTotals[c.name] ?? 0) + l.amount;
    }
    const exp = v.lines.filter((l) => chosen.has(low(l.ledger)) && candidates.has(low(l.ledger)));
    if (!exp.length) continue;
    // the other side: party ledgers (credited for a purchase / expense; debited for a debit note)
    const others = v.lines.filter((l) => !candidates.has(low(l.ledger)));
    const partyLines = others.filter((l) => !notParty(l.ledger));
    const hasGst = v.lines.some((l) => isGstTax(l.ledger));
    let split: { p: BookParty; share: number }[];
    const vp = v.party && partyLines.find((l) => low(l.ledger) === low(v.party));
    if (vp) split = [{ p: partyOf(vp.ledger, "party", v.partyGstin), share: 1 }];
    else if (partyLines.length) {
      const tot = partyLines.reduce((s, l) => s + Math.abs(l.amount), 0) || 1;
      const byName = new Map<string, number>();
      partyLines.forEach((l) => byName.set(l.ledger, (byName.get(l.ledger) ?? 0) + Math.abs(l.amount)));
      split = Array.from(byName.entries()).map(([n, a]) => ({ p: partyOf(n, "party", partyLines.length === 1 ? v.partyGstin : ""), share: a / tot }));
    } else {
      const bank = others.find((l) => isBank(l.ledger));
      if (bank) split = [{ p: partyOf(bank.ledger, "bank"), share: 1 }];
      else split = [{ p: partyOf(NO_PARTY, others.some((l) => isCash(l.ledger)) ? "cash" : "none"), share: 1 }];
    }
    const touched = new Set<BookParty>();
    // Fixed Assets: a voucher with no other side than asset ledgers (CWIP → Building) is a transfer, not spending;
    // a debit note / purchase return to a party reduces the addition; other credits (sale, depreciation) are left out
    const capOnly = others.length === 0 && exp.every((l) => candidates.get(low(l.ledger))!.kind === "capital");
    const isReturn = /debit\s*note|purchase\s*return|rejection\s*out/i.test(v.type) && partyLines.length > 0;
    for (const l of exp) {
      const c = candidates.get(low(l.ledger))!;
      if (c.kind === "capital" && capOnly) { if (l.amount < 0) notCounted[c.name] = (notCounted[c.name] ?? 0) - l.amount; continue; }
      if (c.kind === "capital" && l.amount < 0 && !isReturn) { notCounted[c.name] = (notCounted[c.name] ?? 0) - l.amount; continue; }
      // a payment straight from the bank with no party: only bank charges belong to the bank itself
      const parts = split.length === 1 && split[0].p.via === "bank" && !isBankCharges(c.name) ? [{ p: partyOf(NO_PARTY, "none"), share: 1 }] : split;
      for (const s of parts) { add(c.name, c.kind, s.p, l.amount * s.share); touched.add(s.p); }
    }
    touched.forEach((p) => { p.bills++; if (hasGst) p.gstBills++; });
  }

  const rows = Array.from(acc.values()).map((r) => ({ ...r, amount: r2(r.amount) })).filter((r) => Math.abs(r.amount) >= 0.005);
  Object.keys(ledgerTotals).forEach((k) => { ledgerTotals[k] = r2(ledgerTotals[k]); });
  Object.keys(notCounted).forEach((k) => { notCounted[k] = r2(notCounted[k]); });
  Object.keys(capitalAdded).forEach((k) => { capitalAdded[k] = r2(capitalAdded[k]); });
  return { rows, parties, ledgerTotals, notCounted, capitalAdded };
}

// ---------- GST category and review ----------
export type GstStatus = "regular" | "composition" | "unregistered";
export const GST_STATUS_LABEL: Record<GstStatus, string> = { regular: "Regular", composition: "Composition", unregistered: "Unregistered" };

export interface PartyFacts {
  name: string; gstin: string | null;            // GSTIN as known (party master first, then Tally)
  tallyReg: RegType; via: BookParty["via"]; trade?: boolean;
  gstBills: number; bills: number;
  isComposition: boolean;                         // party master
  isExempt: boolean;                              // party master: supplies only exempt goods / services
  checked?: GstStatus | null;                     // the auditor's own decision (kept for the client)
}

/** GST status used in the report. */
export function statusOf(f: PartyFacts): GstStatus {
  if (f.checked) return f.checked;
  if (f.via === "cash" || f.via === "none") return "unregistered";
  if (f.isComposition || f.tallyReg === "composition") return gstinValid(f.gstin ?? "") ? "composition" : "unregistered";
  if (f.tallyReg === "unregistered") return "unregistered";
  return gstinValid(f.gstin ?? "") ? "regular" : "unregistered";
}

export interface CategoryOptions { bankChargesRegular: boolean }
export const isBankCharges = (ledger: string) => /bank\s*(charges?|commission)|bank\s*chgs?|processing\s*(fee|charge)/i.test(ledger);
export const exemptTax = (t: Taxability | string) => t === "exempt" || t === "nil" || t === "nongst";

/** Clause 44 column of one ledger × party amount. */
export function categoryOf(f: PartyFacts, ledger: string, ledgerTax: Taxability | string, o: CategoryOptions): Category {
  if (f.via === "bank" && !f.checked && o.bankChargesRegular && isBankCharges(ledger)) return exemptTax(ledgerTax) ? "exempt" : "other_registered";
  const s = statusOf(f);
  if (s === "unregistered") return "unregistered";
  if (exemptTax(ledgerTax) || f.isExempt) return "exempt";
  return s === "composition" ? "composition" : "other_registered";
}

/** Reasons to look at a party on the GST portal (empty = nothing to check). in2b: null when no GSTR-2B was given. */
export function reviewReasons(f: PartyFacts, in2b: boolean | null): string[] {
  if (f.checked || f.via === "cash" || f.via === "none" || f.via === "bank") return [];
  const out: string[] = [];
  const valid = gstinValid(f.gstin ?? "");
  const s = statusOf(f);
  if (f.gstin && !valid) out.push("GSTIN is not valid");
  // Tally marks most ledgers "Regular" by default, so this only matters for creditors / debtors
  if (f.tallyReg === "regular" && !f.gstin && f.trade) out.push("Regular in Tally but no GSTIN");
  if (f.tallyReg === "unknown" && valid) out.push("Registration type not set in Tally");
  if (s === "regular" && in2b === false) out.push("Not in GSTR-2B");
  if (s === "regular" && f.bills > 0 && f.gstBills === 0) out.push("No GST in any bill");
  if (s === "composition" && f.gstBills > 0) out.push("Composition, but GST charged");
  return out;
}

/** GST portal page to look up a taxpayer (the auditor enters the GSTIN and captcha there). */
export const GST_PORTAL_SEARCH = "https://services.gst.gov.in/services/searchtp";

/** Supplier GSTINs in GSTR-2B (JSON from the portal: "ctin" fields; any other file: GSTIN-looking cells). */
export function gstinsIn2B(input: unknown, own?: string): string[] {
  const out = new Set<string>();
  const walk = (x: unknown, depth: number) => {
    if (depth > 12 || x === null || x === undefined) return;
    if (typeof x === "string") { const t = x.trim().toUpperCase(); if (t.length === 15 && gstinValid(t)) out.add(t); return; }
    if (Array.isArray(x)) { x.forEach((y) => walk(y, depth + 1)); return; }
    if (typeof x === "object") Object.values(x as Record<string, unknown>).forEach((y) => walk(y, depth + 1));
  };
  walk(input, 0);
  if (own) out.delete(own.trim().toUpperCase());
  // the recipient's own GSTIN ("gstin" at the top of a 2B JSON)
  const top = input && typeof input === "object" && !Array.isArray(input) ? ((input as any).data?.gstin ?? (input as any).gstin) : null;
  if (typeof top === "string") out.delete(top.toUpperCase());
  return Array.from(out).sort();
}

/** Label of the ledger kind / group for the report. */
export const KIND_LABEL: Record<LedgerKind, string> = { revenue: "Revenue expenditure (P&L)", capital: "Capital expenditure (Fixed Assets)" };
