import { describe, it, expect } from "vitest";
import { zipDeflate } from "@/lib/import/bundle";
import { unzip } from "@/lib/import/zip";
import { driveScript, isDriveUrl } from "@/lib/driveScript";
import { computeClause31, splitParty, type LoanTxn } from "@/lib/c31/engine";
import { extractLoans, isTdsLedger } from "@/lib/c31/tally";
import { parseXml } from "@/lib/import/xml";

describe("Client data to Google Drive", () => {
  it("compressed ZIP opens again with the same content", async () => {
    const text = "<ENVELOPE>" + "<VOUCHER><AMOUNT>-100</AMOUNT></VOUCHER>".repeat(5000) + "</ENVELOPE>";
    const data = new TextEncoder().encode(text);
    const z = await zipDeflate([{ name: "Tally_Aeron_DayBook.xml", data }]);
    expect(z.length < data.length / 5).toBe(true);
    const e = await unzip(z.buffer.slice(z.byteOffset, z.byteOffset + z.byteLength) as ArrayBuffer);
    expect(e.map((x) => x.name)).toEqual(["Tally_Aeron_DayBook.xml"]);
    expect(new TextDecoder().decode(e[0].data)).toBe(text);
  });
  it("script is valid JavaScript with the address filled in", () => {
    const s = driveScript("https://x.lovable.cloud/", "pk_123");
    expect(s.includes('const SUPABASE_URL = "https://x.lovable.cloud";')).toBe(true);
    // parses as JavaScript (Apps Script is plain JS)
    let ok = true; try { new Function(s); } catch { ok = false; }
    expect(s.includes("function setup()")).toBe(true);
    expect(s.includes("DriveApp")).toBe(false);
    expect(ok).toBe(true);
    expect(isDriveUrl("https://script.google.com/macros/s/AKfycbx-12_ab/exec")).toBe(true);
    expect(isDriveUrl("https://evil.example.com/exec")).toBe(false);
  });
});

describe("Clause 31 – TDS on interest", () => {
  const t = (id: string, date: string, kind: LoanTxn["kind"], amount: number, mode: LoanTxn["mode"] = "electronic"): LoanTxn =>
    ({ id, txn_date: date, party_name: "Taruna Bansal (Loan)", normalized_name: "taruna bansal", kind, amount, mode, include: true, voucher_no: id });
  const list = [t("1", "2025-02-08", "taken", 100000), t("2", "2025-03-31", "interest", 170262, "journal"), t("3", "2025-03-31", "tds", 17026, "journal")];
  it("reduces the balance but is not reported in 31(c)", () => {
    const r = computeClause31(list, { "taruna bansal": 1079065 }, {});
    expect(r.c.length).toBe(0);
    expect(r.parties[0].closing).toBe(1079065 + 100000 + 170262 - 17026);
    const s = splitParty(list, 1079065);
    expect(s.parts.find((p) => p.txn.id === "3")?.kind).toBe("tds");
  });
  it("import marks a debit against a TDS ledger as TDS", () => {
    expect(isTdsLedger("TDS", [])).toBe(true);
    expect(isTdsLedger("TDS on Interest 194A", [])).toBe(true);
    expect(isTdsLedger("Output CGST", ["Duties & Taxes"])).toBe(false);
    const xml = `<ENVELOPE>
<TALLYMESSAGE><GROUP NAME="Loans (Liability)"><PARENT></PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><GROUP NAME="Duties &amp; Taxes"><PARENT>Current Liabilities</PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="Taruna Bansal (Loan)"><PARENT>Loans (Liability)</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="TDS"><PARENT>Duties &amp; Taxes</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="Interest Expenses"><PARENT>Indirect Expenses</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><VOUCHER VCHTYPE="Journal"><DATE>20250331</DATE><VOUCHERNUMBER>113</VOUCHERNUMBER>
<ALLLEDGERENTRIES.LIST><LEDGERNAME>Taruna Bansal (Loan)</LEDGERNAME><AMOUNT>-17026</AMOUNT></ALLLEDGERENTRIES.LIST>
<ALLLEDGERENTRIES.LIST><LEDGERNAME>TDS</LEDGERNAME><AMOUNT>17026</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
<TALLYMESSAGE><VOUCHER VCHTYPE="Journal"><DATE>20250331</DATE><VOUCHERNUMBER>85</VOUCHERNUMBER>
<ALLLEDGERENTRIES.LIST><LEDGERNAME>Interest Expenses</LEDGERNAME><AMOUNT>-170262</AMOUNT></ALLLEDGERENTRIES.LIST>
<ALLLEDGERENTRIES.LIST><LEDGERNAME>Taruna Bansal (Loan)</LEDGERNAME><AMOUNT>170262</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
</ENVELOPE>`;
    const ex = extractLoans(parseXml(xml));
    const p = ex.postings.filter((x) => x.ledger === "Taruna Bansal (Loan)");
    expect(p.map((x) => [x.voucherNo, x.credit, !!x.tds, x.interest])).toEqual([["113", false, true, false], ["85", true, false, true]]);
  });
});
