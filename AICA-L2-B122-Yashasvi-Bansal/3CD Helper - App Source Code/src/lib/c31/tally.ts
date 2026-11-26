// Clause 31: reads loan ledgers and their postings from a Tally XML export.
// Works with the full Day Book and with a Group Vouchers export (e.g. only "Unsecured Loans").
// Export with "Include dependent masters = Yes" so ledger groups, PAN, address and opening balances come along.
import { type XNode, findAll, childText } from "../import/xml";

export type LedgerKind = "loan" | "maybe" | "no";
export interface LoanLedger {
  name: string;
  group: string;             // immediate parent group
  chain: string[];           // parent → … → primary group
  pan: string; address: string;
  opening: number | null;    // + credit (amount owed by the assessee), − debit
  kind: LedgerKind;          // suggestion: loan / maybe a loan / not a loan
  unsecured: boolean;        // under "Unsecured Loans"
  postings: number;
}
export interface LoanPosting {
  ledger: string; date: string; voucherNo: string; voucherType: string; narration: string;
  credit: boolean;           // credited to the loan ledger (loan taken / repayment received)
  amount: number;
  mode: "cash" | "ac_payee_cheque" | "electronic" | "journal" | "transfer" | "other";
  interest: boolean;         // interest credited (counter ledger is an interest expense)
  tds?: boolean;             // TDS deducted on interest (debit to the loan, counter ledger is TDS)
}
export interface LoanExtract { ledgers: LoanLedger[]; postings: LoanPosting[]; vouchers: number; hasMasters: boolean; groups: { name: string; ledgers: number }[] }

const LOAN_LIAB = ["loans (liability)", "secured loans", "unsecured loans"];
const LOAN_ASSET = ["loans & advances (asset)", "deposits (asset)"];
const MAYBE_NAME = /\b(loan|icd|inter.?corporate|deposit|unsecured|advance from|director|partner'?s? loan|borrowing)\b/i;

const num = (s: string) => { const v = parseFloat(String(s ?? "").replace(/,/g, "").replace(/[^\d.-]/g, "")); return isFinite(v) ? v : null; };
const isoDate = (d: string) => (/^\d{8}$/.test(d) ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : d || "");

function ledgerKind(name: string, chain: string[]): LedgerKind {
  const c = chain.map((x) => x.toLowerCase());
  if (c.some((x) => LOAN_LIAB.includes(x) || LOAN_ASSET.includes(x))) return "loan";
  if (c.length && c.some((x) => ["bank od a/c", "bank occ a/c", "bank accounts", "cash-in-hand", "duties & taxes"].includes(x))) return "no";
  if (MAYBE_NAME.test(name) && !/interest|bank|cash|tds|gst/i.test(name)) return "maybe";
  return "no";
}

/** A TDS ledger: named TDS / tax deducted, or a non-GST ledger under Duties & Taxes. */
export function isTdsLedger(name: string, chain: string[]): boolean {
  if (/\btds\b|t\.\s?d\.\s?s|tax\s+deducted|\b194\s?a\b/i.test(name)) return true;
  return chain.some((x) => x.toLowerCase() === "duties & taxes") && !/gst|cess|vat|excise|customs|duty/i.test(name);
}

export function extractLoans(root: XNode): LoanExtract {
  // groups and ledger masters
  const groupParent = new Map<string, string>();
  for (const g of findAll(root, "GROUP")) { const n = (g.attrs["NAME"] || childText(g, "NAME")).trim(); if (n) groupParent.set(n.toLowerCase(), childText(g, "PARENT")); }
  const masters = new Map<string, { name: string; parent: string; chain: string[]; pan: string; address: string; opening: number | null }>();
  for (const l of findAll(root, "LEDGER")) {
    const name = (l.attrs["NAME"] || childText(l, "NAME")).trim();
    if (!name) continue;
    const parent = childText(l, "PARENT");
    const chain: string[] = []; let p = parent;
    for (let i = 0; p && i < 10; i++) { chain.push(p); p = groupParent.get(p.toLowerCase()) ?? ""; }
    const addr = findAll(l, "ADDRESS").map((a) => a.text.trim()).filter(Boolean).join(", ");
    const ob = num(childText(l, "OPENINGBALANCE"));
    // Tally: negative = debit, positive = credit
    masters.set(name.toLowerCase(), { name, parent, chain, pan: (childText(l, "INCOMETAXNUMBER") || "").toUpperCase(), address: addr, opening: ob });
  }
  const clsOf = (ledger: string) => {
    const m = masters.get(ledger.toLowerCase());
    const c = (m?.chain ?? []).map((x) => x.toLowerCase());
    if (c.includes("cash-in-hand") || /^(petty )?cash\b|cash[\s-]*in[\s-]*hand/i.test(ledger)) return "cash";
    if (c.some((x) => ["bank accounts", "bank od a/c", "bank occ a/c"].includes(x)) || (!c.length && /\bbank\b|a\/c no/i.test(ledger) && !/charges|interest|loan/i.test(ledger))) return "bank";
    return "other";
  };

  const postings: LoanPosting[] = [];
  const count = new Map<string, number>();
  let vouchers = 0;
  for (const v of findAll(root, "VOUCHER")) {
    const vtype = v.attrs["VCHTYPE"] || childText(v, "VOUCHERTYPENAME");
    if (/order|memo|delivery|receipt note|stock|physical|rejection/i.test(vtype)) continue;
    if (/^yes$/i.test(childText(v, "ISCANCELLED")) || /^yes$/i.test(childText(v, "ISOPTIONAL"))) continue;
    vouchers++;
    const lines: { ledger: string; amount: number; node: XNode }[] = [];
    for (const l of v.children.filter((c) => c.name === "ALLLEDGERENTRIES.LIST" || c.name === "LEDGERENTRIES.LIST")) {
      const ledger = childText(l, "LEDGERNAME").trim();
      const a = num(childText(l, "AMOUNT"));
      if (!ledger || a === null || a === 0) continue;
      lines.push({ ledger, amount: -a, node: l }); // + debit, − credit
    }
    const cls = lines.map((l) => clsOf(l.ledger));
    const date = isoDate(childText(v, "DATE"));
    lines.forEach((l, i) => {
      // cash / bank are never loan ledgers. With masters, keep loan-group ledgers and loan-like names;
      // without masters (e.g. a Group Vouchers export) keep every other ledger – the user picks.
      if (cls[i] !== "other") return;
      if (masters.size && ledgerKind(l.ledger, masters.get(l.ledger.toLowerCase())?.chain ?? []) === "no") return;
      const others = lines.filter((_, j) => j !== i);
      const oc = cls.filter((_, j) => j !== i);
      let mode: LoanPosting["mode"] = "other";
      if (oc.includes("cash")) mode = "cash";
      else if (oc.includes("bank")) {
        const bankLine = others.find((_, j) => oc[j] === "bank");
        const tt = bankLine ? findAll(bankLine.node, "BANKALLOCATIONS.LIST").map((b) => childText(b, "TRANSACTIONTYPE")).join(" ") : "";
        mode = /cheque|dd|draft/i.test(tt) ? "ac_payee_cheque" : "electronic";
      } else if (/journal/i.test(vtype)) mode = "journal";
      else if (/contra/i.test(vtype)) mode = "transfer";
      const interest = l.amount < 0 && others.some((o, j) => oc[j] === "other" && /interest/i.test(o.ledger));
      // debit to the loan against a TDS ledger: tax deducted on interest, not a repayment
      const tds = l.amount > 0 && others.some((o, j) => oc[j] === "other" && isTdsLedger(o.ledger, masters.get(o.ledger.toLowerCase())?.chain ?? []));
      postings.push({ ledger: l.ledger, date, voucherNo: childText(v, "VOUCHERNUMBER"), voucherType: vtype, narration: childText(v, "NARRATION"),
        credit: l.amount < 0, amount: Math.round(Math.abs(l.amount) * 100) / 100, mode, interest, ...(tds ? { tds } : {}) });
      count.set(l.ledger.toLowerCase(), (count.get(l.ledger.toLowerCase()) ?? 0) + 1);
    });
  }

  const names = new Map<string, string>();
  postings.forEach((p) => names.set(p.ledger.toLowerCase(), p.ledger));
  // ledgers in loan groups with only an opening balance
  masters.forEach((m, k) => { if (ledgerKind(m.name, m.chain) === "loan" && m.opening) names.set(k, m.name); });
  const ledgers: LoanLedger[] = Array.from(names.entries()).map(([k, name]) => {
    const m = masters.get(k);
    const chain = m?.chain ?? [];
    return { name: m?.name ?? name, group: m?.parent ?? "", chain, pan: m?.pan ?? "", address: m?.address ?? "", opening: m?.opening ?? null,
      kind: ledgerKind(name, chain), unsecured: chain.some((c) => c.toLowerCase() === "unsecured loans"), postings: count.get(k) ?? 0 };
  }).sort((a, b) => ({ loan: 0, maybe: 1, no: 2 }[a.kind] - { loan: 0, maybe: 1, no: 2 }[b.kind]) || a.name.localeCompare(b.name));

  const gc = new Map<string, number>();
  ledgers.forEach((l) => { const g = l.group || "(group not in file)"; gc.set(g, (gc.get(g) ?? 0) + 1); });
  return { ledgers, postings, vouchers, hasMasters: masters.size > 0, groups: Array.from(gc.entries()).map(([name, n]) => ({ name, ledgers: n })).sort((a, b) => b.ledgers - a.ledgers) };
}

export function mergeLoanExtracts(list: LoanExtract[]): LoanExtract {
  const ledgers = new Map<string, LoanLedger>();
  for (const x of list) for (const l of x.ledgers) {
    const k = l.name.toLowerCase(); const e = ledgers.get(k);
    if (!e) ledgers.set(k, { ...l });
    else { e.postings += l.postings; if (!e.chain.length && l.chain.length) Object.assign(e, { ...l, postings: e.postings }); if (e.opening === null) e.opening = l.opening; }
  }
  const all = Array.from(ledgers.values());
  const gc = new Map<string, number>();
  all.forEach((l) => { const g = l.group || "(group not in file)"; gc.set(g, (gc.get(g) ?? 0) + 1); });
  return { ledgers: all, postings: list.flatMap((x) => x.postings), vouchers: list.reduce((s, x) => s + x.vouchers, 0), hasMasters: list.some((x) => x.hasMasters),
    groups: Array.from(gc.entries()).map(([name, n]) => ({ name, ledgers: n })).sort((a, b) => b.ledgers - a.ledgers) };
}

/** Which ledgers to import for a preset. */
export type LedgerPreset = "daybook" | "unsecured" | "custom";
export function presetSelection(ledgers: LoanLedger[], preset: LedgerPreset, saved?: string[]): Set<string> {
  if (preset === "custom" && saved) return new Set(saved.map((s) => s.toLowerCase()).filter((s) => ledgers.some((l) => l.name.toLowerCase() === s)));
  if (preset === "unsecured") return new Set(ledgers.filter((l) => l.unsecured).map((l) => l.name.toLowerCase()));
  return new Set(ledgers.filter((l) => l.kind === "loan").map((l) => l.name.toLowerCase()));
}
