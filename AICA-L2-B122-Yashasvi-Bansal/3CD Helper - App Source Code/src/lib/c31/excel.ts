// Clause 31 from Excel / CSV (loan register, Tally / Busy / Marg ledger reports): column mapping.
import { parseAmount, parseDate } from "@/lib/format";
import { normalizeParty } from "@/lib/party";
import { isValidPan } from "@/lib/validators";
import type { LoanKind, Mode } from "./engine";

type Cell = string | number | null;
export type C31Field = "date" | "party" | "pan" | "kind" | "amount" | "debit" | "credit" | "mode" | "voucher" | "narration";
export const C31_FIELDS: { key: C31Field; label: string; syn: string[] }[] = [
  { key: "date", label: "Date", syn: ["date", "voucher date", "vch date", "txn date", "transaction date"] },
  { key: "party", label: "Lender / borrower (ledger)", syn: ["party name", "party", "ledger name", "ledger", "account name", "name", "lender", "borrower", "depositor", "particulars"] },
  { key: "pan", label: "PAN", syn: ["pan", "pan no", "income tax no", "it pan"] },
  { key: "kind", label: "Type (taken / repaid …)", syn: ["type", "transaction type", "loan type", "nature", "kind", "dr/cr", "dr / cr"] },
  { key: "amount", label: "Amount", syn: ["amount", "amt", "value"] },
  { key: "debit", label: "Debit", syn: ["debit", "dr", "debit amount", "dr amount", "withdrawal"] },
  { key: "credit", label: "Credit", syn: ["credit", "cr", "credit amount", "cr amount", "deposit"] },
  { key: "mode", label: "Mode / voucher type", syn: ["mode", "payment mode", "mode of payment", "instrument", "vch type", "voucher type"] },
  { key: "voucher", label: "Voucher / cheque no.", syn: ["voucher no", "vch no", "voucher number", "cheque no", "ref no", "reference"] },
  { key: "narration", label: "Narration", syn: ["narration", "remarks", "remark", "description"] },
];
export type C31Map = Partial<Record<C31Field, number>>;

const norm = (v: unknown) => String(v ?? "").toLowerCase().replace(/[^a-z0-9/ ]+/g, " ").replace(/\s+/g, " ").trim();

export function detectHeader(rows: Cell[][]): number {
  let best = 0, score = -1;
  for (let i = 0; i < Math.min(rows.length, 30); i++) {
    const cells = rows[i].map(norm);
    const s = C31_FIELDS.filter((f) => cells.some((c) => f.syn.includes(c))).length;
    if (s > score) { score = s; best = i; }
  }
  return best;
}
export function autoMap(header: Cell[]): C31Map {
  const map: C31Map = {}; const used = new Set<number>();
  for (const f of C31_FIELDS) {
    for (const syn of f.syn) {
      const i = header.findIndex((h, j) => !used.has(j) && norm(h) === syn);
      if (i >= 0) { map[f.key] = i; used.add(i); break; }
    }
  }
  return map;
}

export function parseMode(text: string, fallback: Mode = "electronic"): Mode {
  const s = text.toLowerCase();
  if (/journal|\bjv\b|adjust/.test(s)) return "journal";
  if (/bearer|self cheque|non.?a\/?c|not a\/?c|order cheque/.test(s)) return "non_ac_payee_cheque";
  if (/\bcash\b/.test(s)) return "cash";
  if (/neft|rtgs|imps|upi|ecs|online|e-?fund|net ?banking|electronic|bank transfer|nach/.test(s)) return "electronic";
  if (/a\/?c\.?\s*payee|account payee|crossed|cheque|chq|draft|\bdd\b/.test(s)) return "ac_payee_cheque";
  if (/contra|transfer|conversion/.test(s)) return "transfer";
  return fallback;
}
function parseKind(text: string, credit: boolean | null): LoanKind | null {
  const s = text.toLowerCase();
  if (/\btds\b|tax deducted/.test(s) && credit !== true) return "tds";
  if (/interest/.test(s)) return "interest";
  const spec = /specified|advance (for|against) (sale|land|property)/.test(s);
  if (credit !== null) return spec ? (credit ? "specified_taken" : "specified_repaid") : credit ? "taken" : "repaid";
  if (/repa|returned|refund|given|paid|\bdr\b|debit/.test(s)) return spec ? "specified_repaid" : "repaid";
  if (/taken|received|accepted|borrow|\bcr\b|credit|deposit/.test(s)) return spec ? "specified_taken" : "taken";
  return null;
}

export interface C31Draft { row_no: number; txn_date: string | null; party_name: string; normalized_name: string; pan: string | null; kind: LoanKind; amount: number; mode: Mode; voucher_no: string | null; remark: string | null; problems: string[] }

export function c31FromTable(rows: Cell[][], given?: { headerRow: number; map: C31Map }) {
  const headerRow = given?.headerRow ?? detectHeader(rows);
  const header = rows[headerRow] ?? [];
  const map = given?.map ?? autoMap(header);
  const get = (r: Cell[], k: C31Field) => (map[k] === undefined ? null : r[map[k]!]);
  const txt = (r: Cell[], k: C31Field) => String(get(r, k) ?? "").trim();
  const out: C31Draft[] = []; let skipped = 0;
  let lastParty = "";
  for (let i = headerRow + 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || r.every((c) => c === null || String(c).trim() === "")) continue;
    let party = txt(r, "party") || "";
    if (/^(grand\s*)?total\b|^opening balance|^closing balance|^carried over|^brought forward/i.test(party)) { skipped++; continue; }
    if (!party) party = lastParty; else lastParty = party;
    if (!party) { skipped++; continue; }
    let amount = 0, credit: boolean | null = null;
    const dr = parseAmount(get(r, "debit")), cr = parseAmount(get(r, "credit")), am = parseAmount(get(r, "amount"));
    if ((dr && dr.value) || (cr && cr.value)) { const v = (cr?.value ?? 0) - (dr?.value ?? 0); amount = Math.abs(v); credit = v > 0; }
    else if (am && am.value) { amount = Math.abs(am.value); credit = am.side ? am.side === "cr" : null; }
    if (!amount) { skipped++; continue; }
    const typeText = `${txt(r, "kind")} ${txt(r, "mode")}`;
    const kind = parseKind(txt(r, "kind") || typeText, credit) ?? (credit === false ? "repaid" : "taken");
    const mode = parseMode(`${txt(r, "mode")} ${txt(r, "narration")}`);
    const pan = txt(r, "pan").toUpperCase();
    const problems: string[] = [];
    const date = parseDate(get(r, "date"));
    if (!date) problems.push("Date missing");
    if (pan && !isValidPan(pan)) problems.push("PAN looks wrong");
    if (credit === null && !txt(r, "kind")) problems.push("Debit / credit not known – taken as credit");
    out.push({ row_no: i + 1, txn_date: date, party_name: party.slice(0, 300), normalized_name: (normalizeParty(party) || party.toLowerCase()).slice(0, 300), pan: pan || null,
      kind, amount: Math.round(amount * 100) / 100, mode, voucher_no: txt(r, "voucher") || null, remark: txt(r, "narration") || null, problems });
  }
  return { headerRow, header, map, rows: out, skipped };
}
