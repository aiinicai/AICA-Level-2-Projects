import { afterEach, describe, expect, it } from "vitest";
import {
  ParseError, classifyPurchase, classifyTaxLedger, detectJsonKind, detectPortalFile, guessMapping, parse3bSummaryRows, parseClientRows, parseCsv, parseDate,
  parseDaybookXml, parseGstr1Json, parseGstr2bJson, parseGstr3bJson, parseNoticeRows, registerToInvoices, retPeriodToMonth, rowsToRecords, toNum,
  vouchersToInvoices, CLIENT_TEMPLATE_HEADERS, GSTR3B_TEMPLATE_HEADERS, NOTICE_TEMPLATE_HEADERS,
} from "./parsers";
import { dedupeNotices, noticeFromLibrary, noticeKey, noticeStatus } from "./notices";
import { DEMO_OTP, GspError, decideRoute, needsRefresh, newSession, refreshSession, requestOtp, sessionStatus, verifyOtp } from "./gsp";
import { CLIENTS, getClientData } from "./demo";
import { comparison, summarise, totalTax } from "./recon";
import { setUploadProvider, emptyUploads, type UploadedData } from "./uploads";

const SG = "24ABCDE1234F1Z6";

describe("helpers", () => {
  it("parses amounts and dates", () => {
    expect(toNum("1,23,456.50")).toBe(123456.5);
    expect(toNum("(500)")).toBe(-500);
    expect(toNum("₹ 1,200 Cr")).toBe(-1200);
    expect(parseDate("05-08-2025")).toBe("2025-08-05");
    expect(parseDate("20250805")).toBe("2025-08-05");
    expect(parseDate("5-Aug-2025")).toBe("2025-08-05");
    expect(parseDate(45874)).toBe("2025-08-05");
    expect(retPeriodToMonth("082025")).toBe("2025-08");
  });
  it("reads CSV with quotes", () => {
    expect(parseCsv('a,b\r\n"x, y","z ""q"""')).toEqual([["a", "b"], ["x, y", 'z "q"']]);
  });
});

describe("portal JSON parsers", () => {
  const g1 = {
    gstin: SG, fp: "082025",
    b2b: [{ ctin: "27AAPFU0939F1ZV", inv: [{ inum: "A1", idt: "05-08-2025", itms: [{ itm_det: { txval: 100, iamt: 18 } }] }] }],
    b2cs: [{ pos: "24", rt: 18, txval: 50, camt: 4.5, samt: 4.5 }],
    cdnr: [{ ctin: "27AAPFU0939F1ZV", nt: [{ nt_num: "C1", nt_dt: "06-08-2025", ntty: "C", itms: [{ itm_det: { txval: 10, iamt: 1.8 } }] }] }],
  };
  it("GSTR-1: B2B + B2CS + CDNR, credit notes negative", () => {
    expect(detectJsonKind(g1)).toBe("GSTR-1");
    const p = parseGstr1Json(g1);
    expect(p.month).toBe("2025-08");
    expect(p.rows.map((r) => r.type)).toEqual(["B2B", "B2CS", "CDNR"]);
    expect(p.rows[2]!.taxable).toBe(-10);
    expect(p.rows.reduce((s, r) => s + r.taxable, 0)).toBe(140);
  });
  it("GSTR-2B: month = 2B period, ITC availability kept", () => {
    const b2 = { data: { gstin: SG, rtnprd: "092025", docdata: { b2b: [{ ctin: "27AAPFU0939F1ZV", inv: [{ inum: "X1", dt: "28-08-2025", txval: 100, igst: 18, itcavl: "Y" }, { inum: "X2", dt: "28-08-2025", txval: 50, igst: 9, itcavl: "N" }] }] } } };
    expect(detectJsonKind(b2)).toBe("GSTR-2B");
    const p = parseGstr2bJson(b2);
    expect(p.rows[0]!.month).toBe("2025-09");
    expect(p.rows[0]!.date).toBe("2025-08-28");
    expect(p.rows[1]!.itcAvailable).toBe(false);
  });
  it("GSTR-3B: Table 3.1(a) and 4(C)", () => {
    const b3 = { gstin: SG, ret_period: "082025", sup_details: { osup_det: { txval: 1000, iamt: 180, csamt: 5 } }, itc_elg: { itc_net: { iamt: 50, camt: 10 } } };
    const p = parseGstr3bJson(b3);
    expect(p.summary.out).toEqual({ taxable: 1000, igst: 180, cgst: 0, sgst: 0, cess: 5 });
    expect(p.summary.itc.cgst).toBe(10);
  });
  it("rejects unknown JSON and another client's GSTIN", () => {
    expect(() => detectJsonKind({ foo: 1 })).toThrow(ParseError);
    expect(() => detectPortalFile({ json: JSON.stringify(g1) }, "24AACCP4521K1ZK")).toThrow(/belongs to GSTIN 24ABCDE1234F1Z6/);
    expect(detectPortalFile({ json: JSON.stringify(g1) }, SG).type).toBe("GSTR-1");
  });
});

describe("Excel templates", () => {
  it("GSTR-3B 12-month summary", () => {
    const rows = [["GSTIN", SG], [], GSTR3B_TEMPLATE_HEADERS, ["Apr-25", 1000, 180, 0, 0, 0, 50, 0, 0, 0], ["May-25", 2000, 0, 180, 180, 0, 0, 20, 20, 0], ["Jun-25", null, null]];
    const p = parse3bSummaryRows(rows);
    expect(p.gstin).toBe(SG);
    expect(Object.keys(p.byMonth)).toEqual(["2025-04", "2025-05"]);
    expect(p.byMonth["2025-05"]!.out.cgst).toBe(180);
    expect(p.byMonth["2025-04"]!.itc.igst).toBe(50);
    expect(detectPortalFile({ rows }, SG).type).toBe("GSTR-3B summary");
  });
  it("manual notices template", () => {
    const n = parseNoticeRows([NOTICE_TEMPLATE_HEADERS, [SG, "asmt-10", "R1", "FY 24-25", "01-10-2025", "", "", "", "", "", ""]]);
    expect(n[0]!.form).toBe("ASMT-10");
    expect(n[0]!.due).toBe("");
    expect(noticeFromLibrary(n[0]!, new Date(2025, 9, 1)).due).toBe("2025-10-31");
  });
  it("client master import with row errors and no password column", () => {
    const rows = [CLIENT_TEMPLATE_HEADERS,
      ["A", "", SG, "u", "1234", "a@b.in", "Monthly", "2025-26", "", "Yes", "", "", "Yes", "Yes", "Yes", "Auto", ""],
      ["B", "", SG, "u", "", "", "Monthly", "2025-26", "", "", "", "", "", "", "", "Auto", ""],
      ["", "", "24ABCDE1234F1Z5", "", "12", "bad", "Weekly", "", "", "", "", "", "", "", "", "X", ""]];
    const out = parseClientRows(rows);
    expect(out[0]!.errors).toEqual([]);
    expect(out[0]!.client.apiEnabled).toBe(true);
    expect(out[1]!.errors.some((e) => e.includes("Duplicate"))).toBe(true);
    expect(out[2]!.errors.length).toBeGreaterThanOrEqual(5);
    expect(CLIENT_TEMPLATE_HEADERS.join(" ").toLowerCase()).not.toContain("password");
  });
});

describe("Tally", () => {
  it("guesses mapping and converts registers", () => {
    const hdr = ["Date", "Particulars", "GSTIN/UIN", "Voucher Type", "Voucher No.", "Taxable Value", "IGST", "CGST", "SGST", "Cess"];
    const m = guessMapping(hdr);
    expect(m.taxable).toBe("Taxable Value");
    expect(m.inv_no).toBe("Voucher No.");
    const { records } = rowsToRecords([hdr, ["05-08-2025", "A", "27AAPFU0939F1ZV", "Sales", "S1", "100", "18", "0", "0", "0"], ["06-08-2025", "A", "27AAPFU0939F1ZV", "Credit Note", "C1", "10", "1.8", "0", "0", "0"], ["06-08-2025", "Cash", "", "Sales", "S2", "50", "0", "4.5", "4.5", "0"]]);
    const rows = registerToInvoices(records, m, "sales");
    expect(rows.map((r) => r.type)).toEqual(["B2B", "CDNR", "B2CS"]);
    expect(rows[1]!.taxable).toBe(-10);
  });
  it("classifies ledgers and purchases", () => {
    expect(classifyTaxLedger("Output CGST 9%")).toBe("cgst");
    expect(classifyTaxLedger("UTGST Payable")).toBe("sgst");
    expect(classifyTaxLedger("Cess on goods")).toBe("cess");
    expect(classifyPurchase(["Plant & Machinery (Capital)"])).toBe("Capital goods");
    expect(classifyPurchase(["Freight Services"])).toBe("Input services");
    expect(classifyPurchase(["Purchase - Raw Material"])).toBe("Inputs");
  });
  it("reads a Day Book XML", () => {
    const xml = `<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER VCHTYPE="Purchase"><DATE>20250805</DATE><VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME><VOUCHERNUMBER>P1</VOUCHERNUMBER><REFERENCE>INV-9</REFERENCE><PARTYLEDGERNAME>Supp</PARTYLEDGERNAME><PARTYGSTIN>27AAPFU0939F1ZV</PARTYGSTIN>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>Supp</LEDGERNAME><AMOUNT>1180</AMOUNT></ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>Purchase - Raw Material</LEDGERNAME><AMOUNT>-1000</AMOUNT></ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>Input IGST</LEDGERNAME><AMOUNT>-180</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>`;
    const { purchases } = vouchersToInvoices(parseDaybookXml(xml));
    expect(purchases).toHaveLength(1);
    expect(purchases[0]).toMatchObject({ taxable: 1000, igst: 180, no: "INV-9", itcType: "Inputs", month: "2025-08" });
    expect(() => parseDaybookXml("<x/>")).toThrow(ParseError);
  });
});

describe("notices", () => {
  const t = new Date(2026, 0, 10);
  it("fills library defaults and the 30-day due date", () => {
    const n = noticeFromLibrary({ form: "drc-01c", ref: "R1", gstin: SG, issued: "2026-01-01" }, t);
    expect(n.due).toBe("2026-01-31");
    expect(n.subject).toMatch(/GSTR-2B/);
    expect(n.priority).toBe("High");
    expect(noticeStatus(n, t, 7)).toBe("Open");
    expect(noticeStatus({ ...n, due: "2026-01-12" }, t, 7)).toBe("Due soon");
    expect(noticeStatus({ ...n, due: "2026-01-01" }, t, 7)).toBe("Overdue");
    expect(noticeStatus({ ...n, status: "Replied" }, t, 7)).toBe("Replied");
  });
  it("deduplicates on form + reference + GSTIN", () => {
    const a = noticeFromLibrary({ form: "DRC-01C", ref: "r1", gstin: "g" });
    const b = noticeFromLibrary({ form: "drc-01c", ref: "R1", gstin: "G" });
    const c = noticeFromLibrary({ form: "ASMT-10", ref: "R1", gstin: "G" });
    expect(noticeKey(a)).toBe(noticeKey(b));
    expect(dedupeNotices([a], [b, c])).toEqual([c]);
  });
});

describe("GSP (OTP, no passwords)", () => {
  const sg = CLIENTS[0]!;
  it("requests and verifies the OTP", () => {
    expect(requestOtp(sg)).toMatch(/4421/);
    expect(() => requestOtp({ ...sg, apiEnabled: false })).toThrow(GspError);
    expect(() => verifyOtp("000000")).toThrow(GspError);
    const s = verifyOtp(DEMO_OTP);
    expect(sessionStatus(s)).toBe("Connected");
  });
  it("refreshes before expiry and stops expired sessions", () => {
    const now = new Date();
    const near = newSession(now, 5 / 60);
    expect(needsRefresh(near, now)).toBe(true);
    expect(sessionStatus(refreshSession(near, now))).toBe("Connected");
    const old = newSession(new Date(now.getTime() - 7 * 3600000));
    expect(sessionStatus(old, now)).toBe("Expired");
    expect(() => refreshSession(old, now)).toThrow(GspError);
  });
  it("routes by data source", () => {
    expect(decideRoute({ ...sg, dataSource: "Auto" }, "Connected").route).toBe("GSP API");
    expect(decideRoute({ ...sg, dataSource: "Auto" }, "Expired").route).toBe("Downloaded files");
    expect(decideRoute({ ...sg, dataSource: "GSP API" }, "Expired").error).toMatch(/Request OTP/);
    expect(decideRoute({ ...sg, dataSource: "Downloaded files" }, "Connected").route).toBe("Downloaded files");
  });
});

describe("uploaded data overlays the demo data", () => {
  afterEach(() => setUploadProvider(() => undefined));
  it("an uploaded March GSTR-1 removes Mehta's partial data", () => {
    expect(summarise("mehta-textiles").partialMonths).toEqual(["2026-03"]);
    const shree = getClientData("mehta-textiles");
    const up: UploadedData = { ...emptyUploads(), gstr1: { "2026-03": shree.sales.filter((s) => s.month === "2026-03").map((s) => ({ ...s })) } };
    setUploadProvider((id) => (id === "mehta-textiles" ? up : undefined));
    expect(getClientData("mehta-textiles").missing.gstr1).toEqual([]);
    expect(summarise("mehta-textiles").reconciled).toBe(true);
  });
  it("a new client runs on uploads only", () => {
    expect(getClientData("new-client").missing.gstr3b).toHaveLength(12);
    const up: UploadedData = { ...emptyUploads(), gstr3b: { "2025-04": { month: "2025-04", out: { taxable: 100, igst: 18, cgst: 0, sgst: 0, cess: 0 }, itc: { taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 } } } };
    setUploadProvider((id) => (id === "new-client" ? up : undefined));
    const r2 = comparison("new-client", "R2").rows[0]!;
    expect(totalTax(r2.a)).toBe(18);
    expect(r2.status).toBe("Difference");
  });
});
