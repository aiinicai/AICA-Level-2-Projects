import { describe, expect, it } from "vitest";
import { comparison, countKinds, drc03, gstr9, gstr9c, invoiceMatch, normaliseInvoiceNo, statusOf, summarise, supplierSummary, threeWay, totalTax, zero, type RId } from "./recon";
import { CLIENTS, PLANT } from "./demo";
import { validateGstin } from "./gstin";

const SG = "shree-ganesh";
const diffMonths = (client: string, id: RId) =>
  Object.fromEntries(comparison(client, id).rows.filter((r) => r.status === "Difference").map((r) => [r.month, totalTax(r.diff)]));
const S2_TAX = PLANT.S2.cgst + PLANT.S2.sgst;

describe("basics", () => {
  it("normalises invoice numbers", () => {
    expect(normaliseInvoiceNo("SGT/25-26/0093")).toBe("SGT252693");
    expect(normaliseInvoiceNo("sgt-25-26-93")).toBe("SGT252693");
    expect(normaliseInvoiceNo("SGT2526/93")).toBe("SGT252693");
  });
  it("Difference only when |total tax diff| > tolerance", () => {
    expect(statusOf({ ...zero(), igst: 1 }, false, 1)).toBe("Matched");
    expect(statusOf({ ...zero(), igst: 0.6, cgst: 0.6 }, false, 1)).toBe("Difference");
    expect(statusOf({ ...zero(), taxable: 5000 }, false, 1)).toBe("Matched");
    expect(statusOf(zero(), true, 1)).toBe("Partial data");
  });
  it("all demo GSTINs pass the check digit, and a typo fails", () => {
    for (const c of CLIENTS) expect(validateGstin(c.gstin).valid).toBe(true);
    expect(validateGstin("24ABCDE1234F1Z7").valid).toBe(false);
  });
});

describe("Shree Ganesh Traders FY 2025-26", () => {
  it("R1 differences: Oct-25 +9,000, Jan-26 −S2 tax, Mar-26 +4,860", () => {
    expect(diffMonths(SG, "R1")).toEqual({ "2025-10": 9000, "2026-01": -S2_TAX, "2026-03": 4860 });
  });
  it("R2 differences: Aug-25 −28,062, Oct-25 −9,000", () => {
    expect(diffMonths(SG, "R2")).toEqual({ "2025-08": -28062, "2025-10": -9000 });
  });
  it("R3 differences: Aug-25 −28,062, Jan-26 −S2 tax, Mar-26 +4,860", () => {
    expect(diffMonths(SG, "R3")).toEqual({ "2025-08": -28062, "2026-01": -S2_TAX, "2026-03": 4860 });
  });
  it("R5 differences only Dec-25 −74,464 and Feb-26 +20,000", () => {
    expect(diffMonths(SG, "R5")).toEqual({ "2025-12": -74464, "2026-02": 20000 });
  });
  it("R1 meaning for a positive difference mentions DRC-01B", () => {
    expect(comparison(SG, "R1").rows.find((r) => r.month === "2025-10")!.meaning).toBe("Liability reported in GSTR-1 but not paid in 3B: DRC-01B risk");
    expect(comparison(SG, "R5").rows.find((r) => r.month === "2025-12")!.meaning).toBe("ITC claimed beyond GSTR-2B: DRC-01C risk");
  });
  it("three-way signs: 3B−GSTR-1 = −R1, GSTR-1−Books = R3, 3B−Books = R2", () => {
    const oct = threeWay(SG, "sales").find((r) => r.month === "2025-10")!;
    expect(oct.d2).toBe(-9000);
    expect(oct.d3).toBe(-9000);
    const dec = threeWay(SG, "itc").find((r) => r.month === "2025-12")!;
    expect(dec.d2).toBe(74464);
  });
  it("sales matching: 2 Only in Books, 1 Value Mismatch, 1 Probable Match", () => {
    const c = countKinds(invoiceMatch(SG, "sales"));
    expect(c["Only in Books"]).toBe(2);
    expect(c["Value Mismatch"]).toBe(1);
    expect(c["Probable Match (Inv No)"]).toBe(1);
    expect(c["Only in GSTR-1"]).toBeUndefined();
    expect(c["Matched – Period Diff"]).toBeUndefined();
  });
  it("ITC matching: 6 Only in Books, 4 Only in GSTR-2B, 3 Value Mismatch, 5 Period Diff", () => {
    const c = countKinds(invoiceMatch(SG, "itc"));
    expect(c["Only in Books"]).toBe(6);
    expect(c["Only in GSTR-2B"]).toBe(4);
    expect(c["Value Mismatch"]).toBe(3);
    expect(c["Matched – Period Diff"]).toBe(5);
    expect(c["Probable Match (Inv No)"]).toBeUndefined();
  });
  it("supplier follow-up = Only in Books + Value Mismatch, largest first", () => {
    const g = supplierSummary(SG);
    expect(g.reduce((s, x) => s + x.rows.length, 0)).toBe(9);
    for (let i = 1; i < g.length; i++) expect(g[i - 1]!.atRisk).toBeGreaterThanOrEqual(g[i]!.atRisk);
  });
  it("DRC-03 (Table 10/14) = ₹37,062 tax", () => {
    expect(drc03(SG).total).toBe(37062);
    const l = gstr9(SG).find((x) => x.id === "10/14")!;
    expect(totalTax(l.v)).toBe(37062);
  });
  it("interest u/s 50 runs from the 20th of the next month", () => {
    const d = drc03(SG, new Date(2025, 8, 30)); // 30-Sep-25: Aug due 20-Sep → 10 days
    expect(d.months[0]!.days).toBe(10);
    expect(d.interestTotal).toBe(Math.round((28062 * 0.18 * 10) / 365));
  });
});

describe("GSTR-9 and 9C rules", () => {
  const l9 = (id: string, c = SG) => gstr9(c).find((l) => l.id === id)!;
  it("4N = 4A + 4B − 4I", () => {
    expect(l9("4N").v.taxable).toBe(l9("4A").v.taxable + l9("4B").v.taxable - l9("4I").v.taxable);
  });
  it("6B split totals 6A exactly and 6J = 0; 7J = 6A; 8B = 6B", () => {
    const b = ["6B-0", "6B-1", "6B-2"].reduce((s, id) => s + totalTax(l9(id).v), 0);
    expect(b).toBe(totalTax(l9("6A").v));
    expect(totalTax(l9("6J").v)).toBe(0);
    expect(l9("7J").v).toEqual(l9("6A").v);
    expect(totalTax(l9("8B").v)).toBe(b);
  });
  it("8D = 8A − (8B + 8C)", () => {
    expect(totalTax(l9("8D").v)).toBe(totalTax(l9("8A").v) - totalTax(l9("8B").v) - totalTax(l9("8C").v));
  });
  it("overrides flow into derived lines", () => {
    const lines = gstr9(SG, { "4A.taxable": 100 });
    const g = (id: string) => lines.find((l) => l.id === id)!;
    expect(g("4A").overridden).toEqual(["taxable"]);
    expect(g("4N").v.taxable).toBe(100 + g("4B").v.taxable - g("4I").v.taxable);
  });
  it("9C defaults reconcile turnover and ITC; 9R equals Books − 3B", () => {
    const c = gstr9c(SG);
    const g = (id: string) => c.find((l) => l.id === id)!;
    expect(g("5S").v.taxable).toBe(0);
    expect(g("12G").v.taxable).toBe(0);
    expect(totalTax(g("9R").v)).toBe(37062);
    const c2 = gstr9c(SG, { unbilled: 5000, otherIncome: 2000 });
    expect(c2.find((l) => l.id === "5S")!.v.taxable).toBe(3000);
  });
});

describe("other clients", () => {
  it("Patel Polymers: every check and invoice matched", () => {
    expect(summarise("patel-polymers").differences).toBe(0);
    expect(summarise("patel-polymers").pending).toBe(0);
    for (const side of ["sales", "itc"] as const) expect(invoiceMatch("patel-polymers", side).every((r) => r.kind === "Matched")).toBe(true);
  });
  it("Mehta Textiles: only Mar-26 R1 and R3 are Partial data; GSTR-2B complete", () => {
    const partial = (["R1", "R2", "R3", "R4", "R5", "R6"] as RId[]).flatMap((id) =>
      comparison("mehta-textiles", id).rows.filter((r) => r.status !== "Matched").map((r) => `${id}:${r.month}:${r.status}`),
    );
    expect(partial).toEqual(["R1:2026-03:Partial data", "R3:2026-03:Partial data"]);
  });
});
