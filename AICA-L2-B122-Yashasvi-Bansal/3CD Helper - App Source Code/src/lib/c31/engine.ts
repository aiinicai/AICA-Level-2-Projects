// Clause 31 – loans, deposits and specified sums (s.269SS / 269T) and their repayment.
// Each entry is only a debit or a credit to the party's account. Whether it is a loan taken, a repayment,
// a loan given or a repayment received is worked out from the running balance, so an account that moves
// from credit to debit (or back) is split at zero automatically.

export const LIMIT_269 = 20000;

export type LoanKind = "taken" | "repaid" | "specified_taken" | "specified_repaid" | "given" | "repayment_received" | "interest" | "tds";
export type Mode = "cash" | "non_ac_payee_cheque" | "ac_payee_cheque" | "electronic" | "journal" | "transfer" | "other";

export const MODE_LABEL: Record<Mode, string> = {
  cash: "Cash", non_ac_payee_cheque: "Cheque / draft – not a/c payee", ac_payee_cheque: "A/c payee cheque / draft",
  electronic: "Bank – NEFT / RTGS / UPI / ECS", journal: "Journal entry", transfer: "Transfer / adjustment", other: "Other",
};
/** What the user picks for an entry: the side of the party's account, and whether it is a specified sum or interest. */
export const ENTRY_TYPE_LABEL: Record<LoanKind, string> = {
  taken: "Credit – loan / deposit", repaid: "Debit – loan / deposit", given: "Debit – loan / deposit (given)", repayment_received: "Credit – loan / deposit (received back)",
  specified_taken: "Credit – specified sum (immovable property)", specified_repaid: "Debit – specified sum repaid", interest: "Credit – interest",
  tds: "Debit – TDS on interest",
};
/** Note 1 below clause 31 of Form 3CD (Notification 23/2025) – code for the nature of amount / receipt / repayment. */
export const NOTE1_CODES: Record<string, string> = {
  A: "Cash payment", B: "Cash receipt", C: "Payment through non account payee cheque", D: "Receipt through non account payee cheque",
  E: "Transfer of asset", F: "Transfer of liability", G: "Conversion of assets", H: "Conversion of liabilities",
  I: "Journal entry [Debit]", J: "Journal entry [Credit]", K: "Any other mode [Debit]", L: "Any other mode [Credit]",
};

/** Answer for "If by cheque / draft, whether a/c payee" chosen by the user for an entry paid or received by cheque / draft. */
export type ChequeAnswer = "cheque" | "draft" | "no";
export const CHEQUE_ANSWER_LABEL: Record<ChequeAnswer, string> = { cheque: "Yes – Cheque", draft: "Yes – Bank draft", no: "No" };
const isCheque = (m: Mode) => m === "ac_payee_cheque" || m === "non_ac_payee_cheque";
/** Stable key of an entry (kept across a fresh import of the same books). */
export const txnKey = (t: Pick<LoanTxn, "normalized_name" | "txn_date" | "amount" | "voucher_no">) =>
  `${t.normalized_name}|${t.txn_date ?? ""}|${Math.round(Math.abs(Number(t.amount) || 0) * 100)}|${t.voucher_no ?? ""}`;

/** Lender / borrower name for the report: drops words such as "Loan", "Unsecured Loan", "Deposit A/c" around the ledger name. */
export function lenderName(ledger: string): string {
  const w = String(ledger ?? "").trim();
  const word = "(?:unsecured\\s+|secured\\s+)?(?:loans?|deposits?)(?:\\s+(?:a\\/c|ac|account))?";
  const s = w
    .replace(new RegExp(`^\\(?\\s*${word}\\b\\s*\\)?\\s*(?:from\\s+|[-:–]\\s*)?`, "i"), "")
    .replace(new RegExp(`(?:^|\\s+|\\s*[-:–(]\\s*)\\(?\\s*\\b${word}\\s*\\)?$`, "i"), "")
    .trim();
  return s || w;
}

export const isCredit = (k: LoanKind) => k === "taken" || k === "specified_taken" || k === "interest" || k === "repayment_received";
const banking = (m: Mode) => m === "ac_payee_cheque" || m === "electronic";

export interface LoanTxn {
  id: string; txn_date: string | null; voucher_no?: string | null; party_name: string; normalized_name: string; pan?: string | null;
  kind: LoanKind; amount: number; mode: Mode; nature_code?: string | null; include: boolean; remark?: string | null;
}
export interface LoanParty { normalized_name: string; party_name?: string; pan?: string | null; address?: string | null; is_exempt_lender?: boolean }
export type SameDayOrder = "credit_first" | "debit_first" | "as_entered";

/** One piece of an entry after splitting at zero balance. */
// "interest" and "tds" move the balance but are never reported (they are not loans taken or repaid)
export type PartKind = "taken" | "specified_taken" | "repaid" | "specified_repaid" | "given" | "repayment_received" | "interest" | "tds";
export interface Part { txn: LoanTxn; kind: PartKind; amount: number; before: number /* signed balance before: + owed by assessee */ }

export interface PartySummary {
  normalized_name: string; party_name: string; pan: string; address: string; exempt: boolean;
  opening: number; credits: number; debits: number; closing: number;  // + = owed by the assessee (credit balance)
  maxPayable: number; maxReceivable: number; squaredUp: boolean; sideChanged: boolean; review: boolean; entries: number;
}
export interface C31Row {
  txnId: string; party: string; party_name: string; address: string; pan: string; date: string | null; amount: number; code: string;
  squaredUp?: "Yes" | "No"; maxOutstanding: number; otherwise: "Yes" | "No"; acPayee: string; review: boolean; split: boolean;
  /** Entry keys behind this row (more than one when similar entries are combined). */
  keys: string[];
  /** The row is by cheque / draft, so the a/c payee answer can be chosen. */
  cheque: boolean;
  /** The chosen answer for a cheque row ("cheque" when nothing chosen yet). */
  chequeAnswer?: ChequeAnswer;
}
export interface C31Result { parties: PartySummary[]; a: C31Row[]; b: C31Row[]; c: C31Row[]; d: C31Row[]; e: C31Row[]; reviewParties: number }

const r2 = (n: number) => Math.round(n * 100) / 100;

function chequeCell(m: Mode, ans?: ChequeAnswer): { acPayee: string; cheque: boolean; chequeAnswer?: ChequeAnswer } {
  if (!isCheque(m)) return { acPayee: "NA", cheque: false };
  const a: ChequeAnswer = ans ?? (m === "non_ac_payee_cheque" ? "no" : "cheque");
  return { acPayee: CHEQUE_ANSWER_LABEL[a], cheque: true, chequeAnswer: a };
}

export function defaultCode(part: PartKind, mode: Mode): string {
  const received = part === "taken" || part === "specified_taken" || part === "repayment_received" || part === "interest";
  switch (mode) {
    case "cash": return received ? "B" : "A";
    case "non_ac_payee_cheque": return received ? "D" : "C";
    case "journal": return received ? "J" : "I";
    case "transfer": return received ? "F" : "E";
    default: return received ? "L" : "K";
  }
}

/** Walk one party's entries in date order and split each entry into its parts. */
export function splitParty(list: LoanTxn[], opening: number, order: SameDayOrder = "credit_first") {
  const idx = new Map(list.map((t, i) => [t.id, i]));
  const sorted = [...list].sort((x, y) => {
    const d = (x.txn_date ?? "9999").localeCompare(y.txn_date ?? "9999");
    if (d || order === "as_entered") return d || idx.get(x.id)! - idx.get(y.id)!;
    const cx = isCredit(x.kind) ? 0 : 1, cy = isCredit(y.kind) ? 0 : 1;
    return (order === "credit_first" ? cx - cy : cy - cx) || idx.get(x.id)! - idx.get(y.id)!;
  });
  const parts: Part[] = [];
  let bal = opening, maxPay = Math.max(0, opening), maxRec = Math.max(0, -opening), changed = false, squared = false;
  let credits = 0, debits = 0;
  for (const t of sorted) {
    const a = Math.abs(Number(t.amount) || 0);
    if (!a) continue;
    const before = bal;
    if (isCredit(t.kind)) {
      credits += a;
      const back = Math.min(a, Math.max(0, -bal));                     // reduces what the party owes us
      if (back > 0) parts.push({ txn: t, kind: t.kind === "interest" ? "interest" : "repayment_received", amount: r2(back), before });
      const rest = a - back;
      if (rest > 0) parts.push({ txn: t, kind: t.kind === "specified_taken" ? "specified_taken" : t.kind === "interest" ? "interest" : "taken", amount: r2(rest), before: before + back });
      bal += a;
    } else {
      debits += a;
      const repay = Math.min(a, Math.max(0, bal));                      // reduces what we owe the party
      if (repay > 0) parts.push({ txn: t, kind: t.kind === "tds" ? "tds" : t.kind === "specified_repaid" ? "specified_repaid" : "repaid", amount: r2(repay), before });
      const rest = a - repay;
      if (rest > 0) parts.push({ txn: t, kind: t.kind === "tds" ? "tds" : "given", amount: r2(rest), before: before - repay });
      bal -= a;
    }
    if ((before > 0.5 && bal < -0.5) || (before < -0.5 && bal > 0.5)) changed = true;
    if (before > 0.5 && bal <= 0.5) squared = true;
    maxPay = Math.max(maxPay, bal); maxRec = Math.max(maxRec, -bal);
  }
  return { parts, closing: r2(bal), maxPayable: r2(maxPay), maxReceivable: r2(maxRec), sideChanged: changed, squaredUp: squared, credits: r2(credits), debits: r2(debits) };
}

export interface C31Options {
  order?: SameDayOrder;
  /** a/c payee answers chosen by the user, by txnKey. */
  cheque?: Record<string, ChequeAnswer>;
}

export function computeClause31(txns: LoanTxn[], openings: Record<string, number>, parties: Record<string, LoanParty>, opts: SameDayOrder | C31Options = "credit_first"): C31Result {
  const o: C31Options = typeof opts === "string" ? { order: opts } : opts;
  const order = o.order ?? "credit_first";
  const res: C31Result = { parties: [], a: [], b: [], c: [], d: [], e: [], reviewParties: 0 };
  const byParty = new Map<string, LoanTxn[]>();
  for (const raw of txns) {
    if (!raw.include) continue;
    // an entry by cheque / draft follows the user's a/c payee answer (Tally only knows "cheque / DD")
    const ans = isCheque(raw.mode) ? o.cheque?.[txnKey(raw)] : undefined;
    const t: LoanTxn = ans ? { ...raw, mode: ans === "no" ? "non_ac_payee_cheque" : "ac_payee_cheque" } : raw;
    if (!byParty.has(t.normalized_name)) byParty.set(t.normalized_name, []);
    byParty.get(t.normalized_name)!.push(t);
  }
  for (const k of Object.keys(openings)) if (!byParty.has(k) && openings[k]) byParty.set(k, []);

  byParty.forEach((list, key) => {
    const info = parties[key] ?? { normalized_name: key };
    // a name changed by the user is used as it is; the ledger name is cleaned of "Loan" etc.
    const ledger = list[0]?.party_name;
    const name = info.party_name && info.party_name !== ledger ? info.party_name : lenderName(info.party_name || ledger || key);
    const pan = (info.pan || list.find((t) => t.pan)?.pan || "").toUpperCase();
    const address = info.address || "";
    const exempt = !!info.is_exempt_lender;
    const opening = Number(openings[key] ?? 0);
    const s = splitParty(list, opening, order);

    const rows: { list: C31Row[]; row: C31Row; mode: Mode }[] = [];
    if (!exempt) for (const p of s.parts) {
      const t = p.txn;
      const owedBefore = Math.max(0, p.before), dueBefore = Math.max(0, -p.before);
      const split = s.parts.filter((x) => x.txn.id === t.id).length > 1;
      const base = { txnId: t.id, party: key, party_name: name, address, pan, date: t.txn_date, amount: p.amount,
        code: t.nature_code && !split ? t.nature_code : defaultCode(p.kind, t.mode),
        otherwise: (banking(t.mode) ? "No" : "Yes") as "Yes" | "No", review: false, split, keys: [txnKey(t)], ...chequeCell(t.mode, o.cheque?.[txnKey(t)]) };
      if (p.kind === "taken" || p.kind === "specified_taken") {
        if (p.amount < LIMIT_269 && owedBefore + p.amount < LIMIT_269) continue;
        rows.push({ list: p.kind === "taken" ? res.a : res.b, row: { ...base, squaredUp: s.squaredUp ? "Yes" : "No", maxOutstanding: s.maxPayable }, mode: t.mode });
      } else if (p.kind === "repaid" || p.kind === "specified_repaid") {
        if (p.amount < LIMIT_269 && owedBefore < LIMIT_269) continue;
        rows.push({ list: res.c, row: { ...base, maxOutstanding: s.maxPayable }, mode: t.mode });
      } else if (p.kind === "repayment_received") {
        if (p.amount < LIMIT_269 && dueBefore < LIMIT_269) continue;
        if (t.mode === "non_ac_payee_cheque") rows.push({ list: res.e, row: { ...base, maxOutstanding: s.maxReceivable }, mode: t.mode });
        else if (!banking(t.mode)) rows.push({ list: res.d, row: { ...base, maxOutstanding: s.maxReceivable }, mode: t.mode });
      }
    }
    // Review mark on the account: a reportable entry not through a/c payee cheque / draft / bank, or the balance changed side
    const review = !exempt && (s.sideChanged || rows.some((r) => !banking(r.mode)));
    rows.forEach((r) => { r.row.review = review; r.list.push(r.row); });
    if (review) res.reviewParties++;
    res.parties.push({ normalized_name: key, party_name: name, pan, address, exempt, opening: r2(opening), credits: s.credits, debits: s.debits, closing: s.closing,
      maxPayable: s.maxPayable, maxReceivable: s.maxReceivable, squaredUp: s.squaredUp, sideChanged: s.sideChanged, review, entries: list.length });
  });
  res.parties.sort((x, y) => x.party_name.localeCompare(y.party_name));
  const by = (x: C31Row, y: C31Row) => x.party_name.localeCompare(y.party_name) || (x.date ?? "").localeCompare(y.date ?? "");
  [res.a, res.b, res.c, res.d, res.e].forEach((l) => l.sort(by));
  return res;
}

/** Combine a party's rows that carry the same answers in every column (code, mode answers, review) into one row. */
export function combineRows(rows: C31Row[]): C31Row[] {
  const out: C31Row[] = [];
  const at = new Map<string, number>();
  for (const r of rows) {
    const k = [r.party, r.code, r.squaredUp ?? "", r.maxOutstanding, r.otherwise, r.acPayee, r.review ? 1 : 0].join("|");
    const i = at.get(k);
    if (i === undefined) { at.set(k, out.length); out.push({ ...r, keys: [...r.keys] }); continue; }
    const c = out[i];
    c.amount = r2(c.amount + r.amount);
    c.keys.push(...r.keys);
    c.split = c.split || r.split;
  }
  return out;
}
