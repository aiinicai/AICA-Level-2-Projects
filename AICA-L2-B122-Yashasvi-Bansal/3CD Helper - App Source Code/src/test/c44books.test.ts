import { describe, it, expect } from "vitest";
import { parseXml } from "@/lib/import/xml";
import { readBooks, candidateLedgers, buildBreakup, gstinsIn2B, reviewReasons, statusOf, categoryOf } from "@/lib/c44/books";
import { prepareImport, buildLedgerReport, rowCategory, rowsToSync, rowState, DEFAULT_SETTINGS } from "@/lib/c44/ledgerMethod";

const G = (n: string, p = "") => `<TALLYMESSAGE><GROUP NAME="${n}"><PARENT>${p}</PARENT></GROUP></TALLYMESSAGE>`;
const L = (n: string, p: string, extra = "") => `<TALLYMESSAGE><LEDGER NAME="${n}"><PARENT>${p}</PARENT>${extra}</LEDGER></TALLYMESSAGE>`;
const line = (l: string, a: number) => `<ALLLEDGERENTRIES.LIST><LEDGERNAME>${l}</LEDGERNAME><AMOUNT>${-a}</AMOUNT></ALLLEDGERENTRIES.LIST>`;
const V = (type: string, party: string, lines: [string, number][]) => `<TALLYMESSAGE><VOUCHER VCHTYPE="${type}"><DATE>20250510</DATE><VOUCHERNUMBER>1</VOUCHERNUMBER><PARTYLEDGERNAME>${party}</PARTYLEDGERNAME>${lines.map(([l, a]) => line(l, a)).join("")}</VOUCHER></TALLYMESSAGE>`;
const REG = "24AACCO9042L1Z9", COMP = "24HWMFM4762B1ZZ";
const XML = `<ENVELOPE>
${G("Purchase Accounts")}${G("Indirect Expenses")}${G("Direct Expenses")}${G("Fixed Assets")}${G("Current Liabilities")}${G("Current Assets")}
${G("Sundry Creditors", "Current Liabilities")}${G("Duties &amp; Taxes", "Current Liabilities")}${G("Bank Accounts", "Current Assets")}${G("Cash-in-Hand", "Current Assets")}${G("Salary Exp.", "Indirect Expenses")}
${L("Purchase", "Purchase Accounts", "<GSTDETAILS.LIST><TAXABILITY>Taxable</TAXABILITY></GSTDETAILS.LIST>")}
${L("Rent", "Indirect Expenses")}${L("Bank Charges", "Indirect Expenses")}${L("Depreciation", "Indirect Expenses")}${L("Salary Ramesh", "Salary Exp.")}
${L("Milk", "Direct Expenses", "<GSTDETAILS.LIST><TAXABILITY>Exempt</TAXABILITY></GSTDETAILS.LIST>")}
${L("Machinery", "Fixed Assets")}
${L("Regular Co", "Sundry Creditors", `<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE><PARTYGSTIN>${REG}</PARTYGSTIN>`)}
${L("Small Shop", "Sundry Creditors", `<GSTREGISTRATIONTYPE>Composition</GSTREGISTRATIONTYPE><PARTYGSTIN>${COMP}</PARTYGSTIN>`)}
${L("Landlord", "Sundry Creditors", "<GSTREGISTRATIONTYPE>Unregistered/Consumer</GSTREGISTRATIONTYPE>")}
${L("HDFC Bank", "Bank Accounts")}${L("Cash", "Cash-in-Hand")}${L("Input IGST", "Duties &amp; Taxes")}
${V("Purchase", "Regular Co", [["Purchase", 1000], ["Input IGST", 180], ["Regular Co", -1180]])}
${V("Debit Note", "Regular Co", [["Purchase", -100], ["Input IGST", -18], ["Regular Co", 118]])}
${V("Journal", "Small Shop", [["Purchase", 500], ["Small Shop", -500]])}
${V("Journal", "Landlord", [["Rent", 2000], ["Landlord", -2000]])}
${V("Payment", "", [["Bank Charges", 50], ["HDFC Bank", -50]])}
${V("Payment", "", [["Rent", 300], ["Cash", -300]])}
${V("Purchase", "Regular Co", [["Milk", 400], ["Regular Co", -400]])}
${V("Journal", "Regular Co", [["Machinery", 5000], ["Input IGST", 900], ["Regular Co", -5900]])}
${V("Journal", "", [["Depreciation", 700], ["Machinery", -700]])}
${V("Payment", "", [["Salary Ramesh", 900], ["HDFC Bank", -900]])}
</ENVELOPE>`;

const books = readBooks(parseXml(XML));

describe("Clause 44 ledger method – books", () => {
  it("reads masters: registration type, GSTIN, taxability", () => {
    const by = Object.fromEntries(books.ledgers.map((l) => [l.name, l]));
    expect(by["Small Shop"].reg).toBe("composition");
    expect(by["Regular Co"].gstin).toBe(REG);
    expect(by["Landlord"].reg).toBe("unregistered");
    expect(by["Milk"].tax).toBe("exempt");
    expect(by["Salary Ramesh"].primary).toBe("Indirect Expenses");
    expect(books.vouchers.length).toBe(10);
  });
  it("chooses expense and Fixed Asset ledgers, leaves out salary and depreciation", () => {
    const c = Object.fromEntries(candidateLedgers(books).map((x) => [x.name, x]));
    expect(c["Salary Ramesh"].exclusion).toBe("Salary / wages");
    expect(c["Depreciation"].exclusion).toBe("Depreciation / amortisation");
    expect(c["Rent"].exclusion).toBe(null);
    expect(c["Machinery"].kind).toBe("capital");
    expect(c["HDFC Bank"]).toBe(undefined);
  });
  it("ties lines to parties: debit note reduces, cash → no party, bank charges → bank, FA credits not counted", () => {
    const r = buildBreakup(books, new Set(candidateLedgers(books).map((x) => x.name.toLowerCase())));
    const amt = (ledger: string, party: string) => r.rows.find((x) => x.ledger === ledger && r.parties[x.party].name === party)?.amount;
    expect(amt("Purchase", "Regular Co")).toBe(900);
    expect(amt("Purchase", "Small Shop")).toBe(500);
    expect(amt("Rent", "Cash / bank payments (no party)")).toBe(300);
    expect(amt("Bank Charges", "HDFC Bank")).toBe(50);
    expect(amt("Machinery", "Regular Co")).toBe(5000);
    expect(r.notCounted["Machinery"]).toBe(700);
    expect(r.parties["regular co"].gstBills).toBe(3);
    expect(r.parties["small shop"].gstBills).toBe(0);
  });
});

describe("Clause 44 ledger method – edge cases", () => {
  it("'Primary' parents, transfers between Fixed Assets, asset returns, look-alike party names", () => {
    const x = `<ENVELOPE>${G("Fixed Assets", "&#4; Primary")}${G("Sundry Creditors", "&#4; Primary")}
${L("Building", "Fixed Assets")}${L("CWIP", "Fixed Assets")}${L("Sharma Traders (Delhi)", "Sundry Creditors", `<PARTYGSTIN>${REG}</PARTYGSTIN>`)}${L("Sharma Traders (Jaipur)", "Sundry Creditors")}
${V("Journal", "", [["CWIP", 5000], ["Sharma Traders (Delhi)", -5000]])}
${V("Journal", "", [["Building", 5000], ["CWIP", -5000]])}
${V("Debit Note", "Sharma Traders (Delhi)", [["CWIP", -1000], ["Sharma Traders (Delhi)", 1000]])}
${V("Journal", "", [["Building", 800], ["Sharma Traders (Jaipur)", -800]])}</ENVELOPE>`;
    const b = readBooks(parseXml(x));
    expect(b.ledgers.find((l) => l.name === "Building")?.primary).toBe("Fixed Assets");
    const r = buildBreakup(b, new Set(["building", "cwip"]));
    expect(r.capitalAdded).toEqual({ CWIP: 4000, Building: 800 });
    const keys = r.rows.map((x) => r.parties[x.party].name).sort();
    expect(keys).toEqual(["Sharma Traders (Delhi)", "Sharma Traders (Jaipur)"]);
    expect(new Set(r.rows.map((x) => x.party)).size).toBe(2);
  });
});

describe("Clause 44 ledger method – categories, review, report", () => {
  const imp = prepareImport(books, DEFAULT_SETTINGS, { upload_id: "u", file: "f.xml" });
  const rows = imp.rows.map((d, i) => ({ id: `r${i}`, ...d, upload_id: "u", category: "", category_override: null as string | null }));
  rows.forEach((r) => { r.category_override = rowCategory(r as any, imp.books, undefined, DEFAULT_SETTINGS); });

  it("puts each ledger × party in its column", () => {
    const cat = (ledger: string, party: string) => rows.find((r) => r.expense_head === ledger && r.party_name === party)?.category_override;
    expect(cat("Purchase", "Regular Co")).toBe("other_registered");
    expect(cat("Purchase", "Small Shop")).toBe("composition");
    expect(cat("Rent", "Landlord")).toBe("unregistered");
    expect(cat("Rent", "Cash / bank payments (no party)")).toBe("unregistered");
    expect(cat("Milk", "Regular Co")).toBe("exempt");
    expect(cat("Bank Charges", "HDFC Bank")).toBe("other_registered");
    expect(rows.find((r) => r.expense_head === "Salary Ramesh")?.include).toBe(false);
  });
  it("report totals and reconciliation tie", () => {
    const rep = buildLedgerReport(rows as any, imp.books, {}, DEFAULT_SETTINGS);
    expect(rep.totals.all).toEqual({ total: 9150, exempt: 400, composition: 500, other_registered: 5950, unregistered: 2300 });
    expect(rep.recon.booksRevenue).toBe(5750);          // 900+500+2300+50+400+700+900
    expect(rep.recon.excludedRevenue).toBe(1600);       // depreciation + salary
    expect(rep.recon.capitalAdditions).toBe(5000);
    expect(rep.recon.booksRevenue - rep.recon.excludedRevenue + rep.recon.capitalAdditions).toBe(rep.recon.reported);
  });
  it("checked status and ledger choice flow into rows to save", () => {
    const s = { ...DEFAULT_SETTINGS, checked: { "regular co": "composition" as const }, sel: { rent: false } };
    const d = rowsToSync(rows as any, imp.books, {}, s);
    expect(d.filter((x) => x.category === "composition").length).toBe(2);   // Purchase + Machinery (Milk stays exempt)
    expect(d.filter((x) => !x.include).length).toBe(2);                      // Rent rows
    const bank = rowsToSync(rows as any, imp.books, {}, { ...DEFAULT_SETTINGS, bankRegular: false });
    expect(bank.map((x) => x.category)).toEqual(["unregistered"]);
  });
  it("a row changed by hand in Review is kept; the report reads the saved rows and still ties", () => {
    const synced = Object.fromEntries(rows.map((r) => [r.id, rowState(r.category_override!, r.include)]));
    const hand = rows.map((r) => r.expense_head === "Rent" && r.party_name === "Landlord" ? { ...r, include: false } : r);
    const books = { ...imp.books, synced };
    expect(rowsToSync(hand as any, books, {}, { ...DEFAULT_SETTINGS, checked: { landlord: "regular" } })).toEqual([]);
    const rep = buildLedgerReport(hand as any, books, {}, DEFAULT_SETTINGS);
    expect(rep.excluded.find((e) => e.name === "Rent")).toEqual({ name: "Rent", reason: "Some entries left out in Review", amount: 2000 });
    expect(rep.recon.booksRevenue - rep.recon.excludedRevenue + rep.recon.capitalAdditions).toBe(rep.recon.reported);
    expect(rep.recon.reported).toBe(7150);
  });
  it("review reasons and GSTR-2B", () => {
    const base = { name: "X", gstin: REG, tallyReg: "regular" as const, via: "party" as const, gstBills: 0, bills: 2, isComposition: false, isExempt: false };
    expect(reviewReasons(base, false)).toEqual(["Not in GSTR-2B", "No GST in any bill"]);
    expect(reviewReasons({ ...base, gstBills: 1 }, true)).toEqual([]);
    expect(reviewReasons({ ...base, checked: "regular" }, false)).toEqual([]);
    expect(reviewReasons({ ...base, tallyReg: "composition", gstBills: 1 }, null)).toEqual(["Composition, but GST charged"]);
    expect(statusOf({ ...base, gstin: "BAD" })).toBe("unregistered");
    expect(statusOf({ ...base, gstin: "", tallyReg: "composition" })).toBe("unregistered");
    expect(statusOf({ ...base, gstin: "", tallyReg: "composition", checked: "composition" })).toBe("composition");
    expect(categoryOf({ ...base, via: "bank", gstin: "" }, "Bank Charges", "", { bankChargesRegular: true })).toBe("other_registered");
    expect(gstinsIn2B({ data: { gstin: REG, docdata: { b2b: [{ ctin: COMP }, { ctin: "24AACCO9042L1Z9" }] } } })).toEqual([COMP]);
  });
});
