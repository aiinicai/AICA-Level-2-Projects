import { loadSample } from "./parse";
import { calculate, rule15Limit } from "./rpt";
import { sebiThreshold } from "./rules";
export interface AcceptanceRow {
  label: string;
  expected: number;
  actual: number | null;
  passed: boolean;
}
const expectedExceptions: [string, string, string, number][] = [
  ["C2", "Pune Precision Gears Pvt Ltd", "Sale of goods", 60009000],
  ["C3", "Deccan Tooling LLP", "Purchase of goods", 11999352],
  ["C4", "Deccan Tooling LLP", "Purchase of goods", 10894662],
  ["C5", "Deccan Tooling LLP", "Purchase of goods", 71999352],
  ["C6", "Kavya Joshi", "Office or place of profit", 3600000],
  ["C7", "Westghat Realty Pvt Ltd", "Leasing of property", 48000000],
];
export function runAcceptance(): AcceptanceRow[] {
  const data = loadSample();
  const rows: AcceptanceRow[] = [];
  const test = (label: string, expected: number, actual: number | null, tolerance = 0) =>
    rows.push({
      label,
      expected,
      actual,
      passed: actual !== null && Math.abs(expected - actual) <= tolerance,
    });
  test("Rule 15 turnover limit", 480000000, rule15Limit(data.company, "Sale of goods"), 1);
  test("Rule 15 net worth limit", 220000000, rule15Limit(data.company, "Sale of property"), 1);
  test(
    "Office or place of profit monthly limit",
    250000,
    rule15Limit(data.company, "Office or place of profit"),
    1,
  );
  test("SEBI material threshold", 520000000, sebiThreshold(data.company.consolidated), 1);
  for (const mode of ["Unlisted", "Listed"] as const) {
    const r = calculate(data, mode);
    test(`${mode}: RPT total`, mode === "Unlisted" ? 1055618816 : 1157618720, r.total, 1);
    test(`${mode}: parties transacted with`, mode === "Unlisted" ? 6 : 8, r.partyCount);
    test(`${mode}: exception count`, mode === "Unlisted" ? 6 : 8, r.exceptions.length);
    const expected =
      mode === "Unlisted"
        ? expectedExceptions
        : ([
            ...expectedExceptions,
            ["C2", "Konkan Logistics Ltd", "Availing of services", 89999904],
            ["L2", "Sahyadri Castings Pvt Ltd", "Purchase of goods", 552001464],
          ] as [string, string, string, number][]);
    for (const [code, party, nature, amount] of expected) {
      const e = r.exceptions.find(
        (e) =>
          e.code === code &&
          e.party === party &&
          (e.nature === nature || (code === "L2" && e.nature === "All natures")),
      );
      test(`${mode}: ${code} · ${party} · ${nature}`, amount, e?.amount ?? null, 1);
    }
  }
  return rows;
}
