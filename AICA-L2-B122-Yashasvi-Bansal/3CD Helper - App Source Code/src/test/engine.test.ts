// Clause 44 engine tests (ported from the original project).
import { describe, it } from "vitest";
import assert from "node:assert/strict";
import { isValidGstin, gstinStatus, isValidPan, gstinChecksum } from "@/lib/validators";
import { parseAmount, parseDate, formatINR, assessmentYearOptions } from "@/lib/format";
import { normalizeParty, similarity, suggestMerges } from "@/lib/party";
import { parseDelimited, parseTextFile, jsonToTable } from "@/lib/import/sources";
import { detectHeaderRow, autoMap, applyMapping, distinctParties } from "@/lib/import/mapping";
import { summarize } from "@/lib/clause44";

const t = (name: string, fn: () => void) => it(name, fn);

t("GSTIN checksum", () => {
  assert.equal(isValidGstin("27AAPFU0939F1ZV"), true);
  assert.equal(isValidGstin("29AAGCB7383J1Z4"), true);
  assert.equal(isValidGstin("27AAPFU0939F1ZA"), false);
  assert.equal(isValidGstin("27aapfu0939f1zv"), true);
  assert.equal(gstinStatus(""), "blank");
  assert.equal(gstinStatus("NA"), "invalid");
});
t("PAN", () => { assert.ok(isValidPan("AAAPA1234A")); assert.ok(!isValidPan("AAAP1234A")); });
t("amount parsing", () => {
  assert.deepEqual(parseAmount("1,23,456.50"), { value: 123456.5, side: null });
  assert.deepEqual(parseAmount("₹ 5,000"), { value: 5000, side: null });
  assert.deepEqual(parseAmount("(2,000)"), { value: -2000, side: null });
  assert.deepEqual(parseAmount("2,000.00 Dr"), { value: 2000, side: "dr" });
  assert.deepEqual(parseAmount("1500 Cr"), { value: 1500, side: "cr" });
  assert.equal(parseAmount("abc"), null);
  assert.equal(parseAmount(""), null);
});
t("date parsing", () => {
  assert.equal(parseDate("01-04-2024"), "2024-04-01");
  assert.equal(parseDate("31/03/25"), "2025-03-31");
  assert.equal(parseDate("1-Apr-2024"), "2024-04-01");
  assert.equal(parseDate("20240401"), "2024-04-01");
  assert.equal(parseDate(45383), "2024-04-01");
  assert.equal(parseDate("2024-04-01T00:00:00Z"), "2024-04-01");
  assert.equal(parseDate("31-02-2024"), null);
});
t("INR format", () => { assert.equal(formatINR(1234567.5), "₹12,34,567.50"); });
t("AY options", () => { assert.ok(assessmentYearOptions().every((a) => /^\d{4}-\d{2}$/.test(a))); });
t("party normalisation & similarity", () => {
  assert.equal(normalizeParty("M/s. A.B.C. Traders"), "abc traders");
  assert.equal(normalizeParty("ABC Traders Private Limited"), "abc traders pvt ltd");
  assert.equal(similarity("abc traders", "abc traders pvt ltd"), 1);
  assert.ok(similarity("sharma electricals", "sharma electrical") > 0.86);
  assert.ok(similarity("sharma electricals", "verma electricals") < 0.86);
  const s = suggestMerges(["abc traders", "abc traders pvt ltd", "xyz ltd"]);
  assert.equal(s.length, 1);
});
t("CSV with title rows, Dr/Cr and totals", () => {
  const csv = `Sharma & Co\nLedger: Expenses 2024-25\n\nDate,Particulars,GSTIN,Ledger,Debit,Credit\n01-04-2024,"ABC Traders, Pune",27AAPFU0939F1ZV,Purchases,"1,00,000.00",\n02-04-2024,Local Kirana,,Office Expenses,"3,000",\n03-04-2024,ABC Traders,27AAPFU0939F1ZA,Purchases,,500\n,Grand Total,,,"1,03,000","500"\n`;
  const rows = parseDelimited(csv);
  assert.equal(detectHeaderRow(rows), 2);
  const map = autoMap(rows);
  assert.equal(map.party, 1); assert.equal(map.gstin, 2); assert.equal(map.head, 3);
  assert.equal(map.debit, 4); assert.equal(map.credit, 5); assert.equal(map.date, 0);
  const out = applyMapping(rows, map);
  assert.equal(out.length, 3);
  assert.equal(out[0].party_name, "ABC Traders, Pune");
  assert.equal(out[0].amount, 100000);
  assert.equal(out[1].gstin_status, "blank");
  assert.equal(out[2].amount, -500);
  assert.equal(out[2].gstin_status, "invalid");
  assert.ok(out[2].warnings.length >= 1);
  assert.equal(distinctParties(out).length, 3);
});
t("pipe-delimited text with amount + Dr/Cr column", () => {
  const txt = "Vendor|GST No|Head|Amt|Dr/Cr|Date\nX Ltd|29AAGCB7383J1Z4|Rent|50000|Dr|2024-05-01\nX Ltd|29AAGCB7383J1Z4|Rent|5000|Cr|2024-05-02\n";
  const rows = parseDelimited(txt);
  const map = autoMap(rows);
  assert.equal(map.drcr, 4);
  const out = applyMapping(rows, map);
  assert.deepEqual(out.map((r) => r.amount), [50000, -5000]);
});
t("Tally XML vouchers + ledger GSTIN", () => {
  const xml = `<?xml version="1.0"?><ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>
  <TALLYMESSAGE><LEDGER NAME="ABC Traders"><PARTYGSTIN>27AAPFU0939F1ZV</PARTYGSTIN></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Purchase"><DATE>20240401</DATE><VOUCHERNUMBER>P-1</VOUCHERNUMBER>
   <PARTYLEDGERNAME>ABC Traders</PARTYLEDGERNAME><NARRATION>Bill &amp; freight</NARRATION>
   <ALLLEDGERENTRIES.LIST><LEDGERNAME>ABC Traders</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>11800.00</AMOUNT></ALLLEDGERENTRIES.LIST>
   <ALLLEDGERENTRIES.LIST><LEDGERNAME>Purchase @18%</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-10000.00</AMOUNT></ALLLEDGERENTRIES.LIST>
   <ALLLEDGERENTRIES.LIST><LEDGERNAME>Input IGST</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-1800.00</AMOUNT></ALLLEDGERENTRIES.LIST>
  </VOUCHER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`;
  // encode as UTF-16LE with BOM, as Tally does
  const u16 = new Uint8Array(2 + xml.length * 2); u16[0] = 0xff; u16[1] = 0xfe;
  for (let i = 0; i < xml.length; i++) { u16[2 + i * 2] = xml.charCodeAt(i) & 255; u16[3 + i * 2] = xml.charCodeAt(i) >> 8; }
  const pf = parseTextFile("daybook.xml", u16.buffer);
  assert.equal(pf.software, "Tally (XML)");
  const rows = pf.sheets[0].rows;
  assert.equal(rows.length, 3);
  const out = applyMapping(rows, autoMap(rows));
  assert.equal(out[0].party_name, "ABC Traders");
  assert.equal(out[0].gstin, "27AAPFU0939F1ZV");
  assert.equal(out[0].expense_head, "Purchase @18%");
  assert.equal(out[0].amount, 10000);
  assert.equal(out[0].txn_date, "2024-04-01");
});
t("GSTR-2B JSON", () => {
  const j = { data: { docdata: { b2b: [{ ctin: "27AAPFU0939F1ZV", trdnm: "ABC Traders", inv: [{ inum: "1", dt: "01-04-2024", txval: 1000, val: 1180 }] }],
    cdnr: [{ ctin: "27AAPFU0939F1ZV", trdnm: "ABC Traders", nt: [{ ntnum: "C1", dt: "05-04-2024", typ: "C", txval: 100, val: 118 }] }] } } };
  const pf = jsonToTable(j);
  const rows = pf.sheets[0].rows;
  const map = autoMap(rows);
  const out = applyMapping(rows, map);
  assert.equal(out.length, 2);
  assert.equal(out[0].amount, 1000);
  assert.equal(out[1].amount, -100);
  assert.equal(out[0].gstin_status, "valid");
});
t("Clause 44 summary (client-side mirror of SQL)", () => {
  const s = summarize([
    { amount: 100000, include: true, category: "other_registered" },
    { amount: 20000, include: true, category: "composition" },
    { amount: 4000, include: true, category: "exempt" },
    { amount: 10000, include: true, category: "unregistered" },
    { amount: 50000, include: false, category: "unregistered" },
  ]);
  assert.equal(s.registered_total, 124000);
  assert.equal(s.reported_total, 134000);
  assert.equal(s.reported_total, s.registered_total + s.unregistered);
  assert.equal(s.excluded, 50000);
});
