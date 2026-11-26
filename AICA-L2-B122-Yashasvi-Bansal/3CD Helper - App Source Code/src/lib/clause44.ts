// Clause 44 configuration (labels can be updated here if CBDT amends Form 3CD) and helpers.

export type Category = "exempt" | "composition" | "other_registered" | "unregistered";

export const CLAUSE44 = {
  clause: "44",
  title: "Break-up of total expenditure of entities registered or not registered under the GST",
  note: "Verify against the latest notified Form 3CD before filing.",
  columns: {
    sr: "Sr. No.",
    total: "Total amount of Expenditure incurred during the year",
    registeredGroup: "Expenditure in respect of entities registered under GST",
    exempt: "Relating to goods or services exempt from GST",
    composition: "Relating to entities falling under composition scheme",
    other_registered: "Relating to other registered entities",
    registered_total: "Total payment to registered entities",
    unregistered: "Expenditure relating to entities not registered under GST",
  },
};

export const CATEGORY_LABEL: Record<Category, string> = {
  exempt: "Exempt supplies",
  composition: "Composition dealer",
  other_registered: "Other registered",
  unregistered: "Unregistered",
};

export const CATEGORY_COLOR: Record<Category, string> = {
  exempt: "bg-sky-100 text-sky-800",
  composition: "bg-amber-100 text-amber-800",
  other_registered: "bg-emerald-100 text-emerald-800",
  unregistered: "bg-slate-200 text-slate-700",
};

export const EXCLUSION_REASONS = [
  "Depreciation / amortisation",
  "Provisions (not actual expenditure)",
  "Salary, wages & employee benefits",
  "Statutory dues (taxes, duties)",
  "Interest & finance cost",
  "Capital expenditure",
  "Not an expense (balance sheet item)",
  "Duplicate entry",
  "Other",
];

export interface Clause44Summary {
  total_uploaded: number;
  excluded: number;
  reported_total: number;
  exempt: number;
  composition: number;
  other_registered: number;
  registered_total: number;
  unregistered: number;
  row_count: number;
  excluded_count: number;
  invalid_gstin_count: number;
  negative_count: number;
  party_count: number;
}

export const EMPTY_SUMMARY: Clause44Summary = {
  total_uploaded: 0, excluded: 0, reported_total: 0, exempt: 0, composition: 0, other_registered: 0,
  registered_total: 0, unregistered: 0, row_count: 0, excluded_count: 0, invalid_gstin_count: 0,
  negative_count: 0, party_count: 0,
};

/** Numbers come back from Postgres as strings for numeric columns – coerce safely. */
export function toSummary(raw: Record<string, unknown> | null | undefined): Clause44Summary {
  const s = { ...EMPTY_SUMMARY };
  if (!raw) return s;
  (Object.keys(s) as (keyof Clause44Summary)[]).forEach((k) => { s[k] = Number(raw[k] ?? 0); });
  return s;
}

/** Client-side mirror of public.clause44_summary (used for previews and tests). */
export function summarize(rows: { amount: number; include: boolean; category: Category }[]): Clause44Summary {
  const s = { ...EMPTY_SUMMARY };
  for (const r of rows) {
    s.total_uploaded += r.amount;
    s.row_count++;
    if (!r.include) { s.excluded += r.amount; s.excluded_count++; continue; }
    s.reported_total += r.amount;
    s[r.category] += r.amount;
  }
  s.registered_total = s.exempt + s.composition + s.other_registered;
  return s;
}

export const EXCEPTION_LABEL: Record<string, string> = {
  invalid_gstin: "Invalid GSTIN",
  multiple_gstins: "Same party, different GSTINs",
  gstin_partly_missing: "GSTIN missing on some rows",
  duplicate: "Possible duplicate entry",
  negative_amount: "Negative amount",
};
