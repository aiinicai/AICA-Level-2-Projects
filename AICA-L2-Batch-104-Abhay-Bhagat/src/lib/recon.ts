import type { AppSettings } from "./db";
import type { MismatchStatus, Txn } from "./types";

export const tax = (t: Txn) => (t.cgst || 0) + (t.sgst || 0) + (t.igst || 0) + (t.cess || 0);
const sum = (rows: Txn[], f: (t: Txn) => number) => rows.reduce((a, b) => a + (f(b) || 0), 0);
const isCN = (t: Txn) => /credit/i.test(t.doc_type);
const isDN = (t: Txn) => /debit/i.test(t.doc_type);
const isAmend = (t: Txn) => /amend/i.test(t.doc_type);
const signed = (t: Txn, v: number) => (isCN(t) ? -v : v);

export interface SummaryRow {
  section: string;
  label: string;
  books: number;
  gst: number;
  diff: number;
  note?: string;
}

export interface MatchItem {
  section: string;
  key_label: string;
  party: string;
  status: MismatchStatus;
  books_taxable: number;
  books_tax: number;
  gst_taxable: number;
  gst_tax: number;
}

export interface ReconResult {
  summaries: SummaryRow[];
  items: MatchItem[];
  totals: {
    turnover: number;
    liability: number;
    itc: number;
    variance: number;
    unreconciled: number;
    additionalTax: number;
    unclaimedItc: number;
  };
}

const keyOf = (s: string) => s.toUpperCase().replace(/[^A-Z0-9]/g, "");

function matchSet(
  section: string,
  books: Txn[],
  returns: Txn[],
  s: AppSettings,
): MatchItem[] {
  const out: MatchItem[] = [];
  const retByKey = new Map<string, Txn[]>();
  for (const r of returns) {
    const k = keyOf(r.invoice_no);
    retByKey.set(k, [...(retByKey.get(k) ?? []), r]);
  }
  const used = new Set<Txn>();

  for (const b of books) {
    const k = keyOf(b.invoice_no);
    let cand = (retByKey.get(k) ?? []).find((r) => !used.has(r));
    let invoiceNoMismatch = false;
    if (!cand) {
      // fall back: same party + same taxable value but different invoice number
      cand = returns.find(
        (r) =>
          !used.has(r) &&
          keyOf(r.party_gstin || r.party_name) === keyOf(b.party_gstin || b.party_name) &&
          Math.abs(r.taxable_value - b.taxable_value) <= s.valueTolerance &&
          keyOf(r.invoice_no) !== k,
      );
      invoiceNoMismatch = !!cand;
    }

    if (!cand) {
      out.push({
        section,
        key_label: b.invoice_no,
        party: b.party_name || b.party_gstin,
        status: "missing_in_return",
        books_taxable: b.taxable_value,
        books_tax: tax(b),
        gst_taxable: 0,
        gst_tax: 0,
      });
      continue;
    }
    used.add(cand);
    const vDiff = Math.abs(cand.taxable_value - b.taxable_value);
    const tDiff = Math.abs(tax(cand) - tax(b));
    const gstinDiff =
      !!b.party_gstin && !!cand.party_gstin && keyOf(b.party_gstin) !== keyOf(cand.party_gstin);
    const dateDiff =
      b.invoice_date && cand.invoice_date && b.invoice_date.slice(0, 7) !== cand.invoice_date.slice(0, 7);

    let status: MismatchStatus = "matched";
    if (invoiceNoMismatch) status = "invoice_no_mismatch";
    else if (gstinDiff) status = "gstin_mismatch";
    else if (vDiff > s.valueTolerance) status = "value_mismatch";
    else if (tDiff > s.taxTolerance) status = "tax_mismatch";
    else if (dateDiff) status = "timing_difference";

    out.push({
      section,
      key_label: b.invoice_no,
      party: b.party_name || b.party_gstin,
      status,
      books_taxable: b.taxable_value,
      books_tax: tax(b),
      gst_taxable: cand.taxable_value,
      gst_tax: tax(cand),
    });
  }

  for (const r of returns) {
    if (used.has(r)) continue;
    out.push({
      section,
      key_label: r.invoice_no,
      party: r.party_name || r.party_gstin,
      status: "missing_in_tally",
      books_taxable: 0,
      books_tax: 0,
      gst_taxable: r.taxable_value,
      gst_tax: tax(r),
    });
  }
  return out;
}

const bucket = (t: Txn, word: RegExp) => word.test(t.supply_type || "");

export function reconcile(txns: Txn[], s: AppSettings): ReconResult {
  const by = (src: string) => txns.filter((t) => t.source === src);
  const sales = by("tally_sales");
  const purchase = by("tally_purchase");
  const ledger = by("tally_gst_ledger");
  const g1 = by("gstr1");
  const g3b = by("gstr3b");
  const g2b = by("gstr2b");
  const g9 = by("gstr9");
  const prev = by("prev_year_adj");

  const g3bItc = g3b.filter((t) => /itc|input/i.test(t.supply_type));
  const g3bOut = g3b.filter((t) => !/itc|input/i.test(t.supply_type));

  const S: SummaryRow[] = [];
  const push = (section: string, label: string, books: number, gst: number, note?: string) =>
    S.push({ section, label, books, gst, diff: +(books - gst).toFixed(2), ...(note ? { note } : {}) });

  const salesTaxable = sum(sales, (t) => signed(t, t.taxable_value));
  const salesTax = sum(sales, (t) => signed(t, tax(t)));
  const g1Taxable = sum(g1, (t) => signed(t, t.taxable_value));
  const g1Tax = sum(g1, (t) => signed(t, tax(t)));

  push("Turnover", "Total outward turnover (taxable value)", salesTaxable, g1Taxable, "Tally sales register vs GSTR-1");
  push("Turnover", "Turnover as per GSTR-3B", salesTaxable, sum(g3bOut, (t) => signed(t, t.taxable_value)));
  push("Turnover", "Turnover as per GSTR-9", salesTaxable, sum(g9, (t) => signed(t, t.taxable_value)));

  push("Tax Liability", "Output tax on outward supplies", salesTax, sum(g3bOut, (t) => signed(t, tax(t))), "Tally vs GSTR-3B");
  push("Tax Liability", "IGST", sum(sales, (t) => signed(t, t.igst)), sum(g3bOut, (t) => signed(t, t.igst)));
  push("Tax Liability", "CGST", sum(sales, (t) => signed(t, t.cgst)), sum(g3bOut, (t) => signed(t, t.cgst)));
  push("Tax Liability", "SGST / UTGST", sum(sales, (t) => signed(t, t.sgst)), sum(g3bOut, (t) => signed(t, t.sgst)));
  push("Tax Liability", "Cess", sum(sales, (t) => signed(t, t.cess)), sum(g3bOut, (t) => signed(t, t.cess)));

  const purchaseItc = sum(purchase, (t) => signed(t, tax(t)));
  push("Input Tax Credit", "ITC as per books vs GSTR-3B", purchaseItc, sum(g3bItc, (t) => signed(t, tax(t))));
  push("Input Tax Credit", "ITC as per books vs GSTR-2B", purchaseItc, sum(g2b, (t) => signed(t, tax(t))));
  push("Input Tax Credit", "ITC claimed in GSTR-3B vs GSTR-2B", sum(g3bItc, (t) => signed(t, tax(t))), sum(g2b, (t) => signed(t, tax(t))), "Both figures are from GST returns");

  const natures: [string, RegExp][] = [
    ["Taxable supplies", /b2b|b2c|taxable|export|sez/i],
    ["Exempt supplies", /exempt/i],
    ["Nil rated supplies", /nil/i],
    ["Non-GST supplies", /non.?gst/i],
  ];
  for (const [label, re] of natures)
    push(
      "Nature of Supply",
      label,
      sum(sales.filter((t) => bucket(t, re)), (t) => signed(t, t.taxable_value)),
      sum(g1.filter((t) => bucket(t, re)), (t) => signed(t, t.taxable_value)),
    );

  const cats: [string, RegExp][] = [
    ["B2B supplies", /b2b/i],
    ["B2C supplies", /b2c/i],
    ["Exports", /export/i],
    ["SEZ supplies", /sez/i],
  ];
  for (const [label, re] of cats)
    push(
      "Supply Category",
      label,
      sum(sales.filter((t) => bucket(t, re)), (t) => signed(t, t.taxable_value)),
      sum(g1.filter((t) => bucket(t, re)), (t) => signed(t, t.taxable_value)),
    );

  push("Notes & Amendments", "Credit notes (taxable value)", sum(sales.filter(isCN), (t) => t.taxable_value), sum(g1.filter(isCN), (t) => t.taxable_value));
  push("Notes & Amendments", "Debit notes (taxable value)", sum(sales.filter(isDN), (t) => t.taxable_value), sum(g1.filter(isDN), (t) => t.taxable_value));
  push("Notes & Amendments", "Amendments (taxable value)", sum(sales.filter(isAmend), (t) => t.taxable_value), sum(g1.filter(isAmend), (t) => t.taxable_value));

  push("Reverse Charge", "Inward supplies liable to reverse charge (taxable value)", sum(purchase.filter((t) => t.reverse_charge === 1), (t) => t.taxable_value), sum(g3b.filter((t) => t.reverse_charge === 1), (t) => t.taxable_value));
  push("Reverse Charge", "Reverse charge tax payable", sum(purchase.filter((t) => t.reverse_charge === 1), tax), sum(g3b.filter((t) => t.reverse_charge === 1), tax));

  const hsnKeys = Array.from(new Set([...sales, ...g1].map((t) => t.hsn).filter(Boolean)));
  for (const h of hsnKeys)
    push(
      "HSN Summary (Outward)",
      `HSN ${h}`,
      sum(sales.filter((t) => t.hsn === h), (t) => signed(t, t.taxable_value)),
      sum(g1.filter((t) => t.hsn === h), (t) => signed(t, t.taxable_value)),
    );

  const ledgerNames = Array.from(new Set(ledger.map((t) => t.voucher_type || t.supply_type || "Ledger")));
  for (const name of ledgerNames)
    push(
      "Electronic Ledgers",
      name,
      sum(ledger.filter((t) => (t.voucher_type || t.supply_type || "Ledger") === name), (t) => t.taxable_value),
      sum(g9.filter((t) => new RegExp(name.replace(/[^\w ]/g, ""), "i").test(t.supply_type || "")), (t) => t.taxable_value),
      "Books balance vs annual return",
    );

  for (const t9 of s.gstr9Tables) {
    const re = new RegExp(t9.sourceHint.replace(/[^\w ]/g, ""), "i");
    const booksVal = /itc/i.test(t9.sourceHint)
      ? sum(purchase, (t) => signed(t, tax(t)))
      : sum(sales.filter((t) => re.test(t.supply_type) || re.test(t.doc_type)), (t) => t.taxable_value);
    const g9Val = sum(g9.filter((t) => re.test(t.supply_type) || re.test(t.doc_type) || t.invoice_no === t9.table), (t) => t.taxable_value + (/itc/i.test(t9.sourceHint) ? tax(t) : 0));
    push("GSTR-9 Table-wise", `Table ${t9.table} — ${t9.description}`, booksVal, g9Val);
  }

  push("GSTR-9C Reconciliation", "Turnover as per audited financial statements (books)", salesTaxable, sum(g9, (t) => signed(t, t.taxable_value)));
  push("GSTR-9C Reconciliation", "Previous year adjustments considered", sum(prev, (t) => signed(t, t.taxable_value)), 0);
  push("GSTR-9C Reconciliation", "Tax paid as per books vs annual return", salesTax, sum(g9, (t) => signed(t, tax(t))));
  push("GSTR-9C Reconciliation", "ITC as per books vs annual return", purchaseItc, sum(g9.filter((t) => /itc/i.test(t.supply_type)), tax));

  const items = [
    ...matchSet("Outward — Tally vs GSTR-1", sales, g1, s),
    ...matchSet("Inward ITC — Tally vs GSTR-2B", purchase, g2b, s),
  ].map((i) =>
    i.status === "matched" && !i.books_taxable && !i.gst_taxable ? { ...i, status: "manual_review" as MismatchStatus } : i,
  );

  const unreconciled = items.filter((i) => i.status !== "matched").length;
  const variance = S.filter((r) => r.section === "Turnover" || r.section === "Tax Liability" || r.section === "Input Tax Credit")
    .reduce((a, r) => a + Math.abs(r.diff), 0);
  const additionalTax = Math.max(0, salesTax - sum(g3bOut, (t) => signed(t, tax(t))));
  const unclaimedItc = Math.max(0, sum(g2b, (t) => signed(t, tax(t))) - sum(g3bItc, (t) => signed(t, tax(t))));

  return {
    summaries: S,
    items,
    totals: {
      turnover: salesTaxable,
      liability: salesTax,
      itc: sum(g3bItc, (t) => signed(t, tax(t))) || purchaseItc,
      variance: +variance.toFixed(2),
      unreconciled,
      additionalTax: +additionalTax.toFixed(2),
      unclaimedItc: +unclaimedItc.toFixed(2),
    },
  };
}

export const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(n || 0);
