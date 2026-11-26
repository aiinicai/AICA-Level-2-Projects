import { describe, it, expect } from "vitest";
import { isZip } from "@/lib/import/zip";
import { combineRows, computeClause31, lenderName, splitParty, txnKey, type LoanTxn } from "@/lib/c31/engine";
import { extractLoans, presetSelection } from "@/lib/c31/tally";
import { parseXml } from "@/lib/import/xml";
import { c31FromTable } from "@/lib/c31/excel";

let n = 0;
const T = (o: Partial<LoanTxn>): LoanTxn => ({ id: `t${++n}`, txn_date: "2024-04-01", party_name: "Rakesh Agarwal", normalized_name: "rakesh agarwal", kind: "taken", amount: 0, mode: "electronic", include: true, ...o });

describe("Clause 31 engine", () => {
  it("splits an entry that takes the balance across zero (credit → debit → credit)", () => {
    const txns = [
      T({ txn_date: "2024-06-10", kind: "repaid", amount: 350000, mode: "cash" }),
      T({ txn_date: "2024-09-15", kind: "taken", amount: 100000, mode: "non_ac_payee_cheque" }),
      T({ txn_date: "2024-12-20", kind: "taken", amount: 250000, mode: "electronic" }),
    ];
    const s = splitParty(txns, 200000);
    expect(s.parts.map((p) => [p.kind, p.amount])).toEqual([["repaid", 200000], ["given", 150000], ["repayment_received", 100000], ["repayment_received", 50000], ["taken", 200000]]);
    expect(s.sideChanged).toBe(true);
    expect(s.maxPayable).toBe(200000);
    expect(s.maxReceivable).toBe(150000);
    expect(s.closing).toBe(200000);

    const r = computeClause31(txns, { "rakesh agarwal": 200000 }, {});
    expect(r.c.map((x) => [x.amount, x.code, x.otherwise])).toEqual([[200000, "A", "Yes"]]);
    expect(r.e.map((x) => x.amount)).toEqual([100000]);              // non a/c payee cheque → 31(e)
    expect(r.d).toEqual([]);                                          // NEFT part of the receipt is not reported
    expect(r.a.map((x) => [x.amount, x.maxOutstanding, x.squaredUp])).toEqual([[200000, 200000, "Yes"]]);
    expect(r.parties[0].review).toBe(true);
    expect(r.a[0].review).toBe(true);
  });

  it("applies the ₹20,000 limit including the amount already outstanding", () => {
    const txns = [
      T({ normalized_name: "a", party_name: "A", txn_date: "2024-05-01", amount: 15000 }),
      T({ normalized_name: "a", party_name: "A", txn_date: "2024-06-01", amount: 6000, mode: "cash" }),
      T({ normalized_name: "b", party_name: "B", txn_date: "2024-05-01", amount: 19999 }),
      T({ normalized_name: "c", party_name: "C", txn_date: "2024-05-01", amount: 5000, kind: "repaid", mode: "cash" }),
    ];
    const r = computeClause31(txns, { c: 25000 }, {});
    expect(r.a.map((x) => [x.party_name, x.amount])).toEqual([["A", 6000]]);   // 15,000 + 6,000 ≥ 20,000
    expect(r.c.map((x) => [x.party_name, x.amount])).toEqual([["C", 5000]]);   // outstanding 25,000 before repayment
    expect(r.parties.find((p) => p.party_name === "A")!.review).toBe(true);    // cash
    expect(r.parties.find((p) => p.party_name === "B")!.review).toBe(false);
  });

  it("does not report or mark exempt lenders, and journal entries get the review mark", () => {
    const txns = [
      T({ normalized_name: "bank", party_name: "Bhilwara Urban Co-op Bank", amount: 500000, mode: "cash" }),
      T({ normalized_name: "d", party_name: "D", amount: 90000, mode: "journal" }),
    ];
    const r = computeClause31(txns, {}, { bank: { normalized_name: "bank", is_exempt_lender: true } });
    expect(r.a.map((x) => [x.party_name, x.code, x.review])).toEqual([["D", "J", true]]);
    expect(r.reviewParties).toBe(1);
  });

  it("orders same-day entries as chosen", () => {
    const txns = [T({ txn_date: "2024-05-01", kind: "repaid", amount: 30000, mode: "cash" }), T({ txn_date: "2024-05-01", kind: "taken", amount: 30000 })];
    expect(splitParty(txns, 0, "credit_first").parts.map((p) => p.kind)).toEqual(["taken", "repaid"]);
    expect(splitParty(txns, 0, "debit_first").parts.map((p) => p.kind)).toEqual(["given", "repayment_received"]);
  });
});

describe("Clause 31 Tally import", () => {
  const xml = `<ENVELOPE><BODY><DATA>
  <TALLYMESSAGE><GROUP NAME="Loans (Liability)"><PARENT></PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Unsecured Loans"><PARENT>Loans (Liability)</PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Secured Loans"><PARENT>Loans (Liability)</PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Bank Accounts"><PARENT></PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Cash-in-Hand"><PARENT></PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Sundry Creditors"><PARENT></PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><GROUP NAME="Indirect Expenses"><PARENT></PARENT></GROUP></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="Rakesh Agarwal"><PARENT>Unsecured Loans</PARENT><INCOMETAXNUMBER>ABHPA4521K</INCOMETAXNUMBER><OPENINGBALANCE>500000.00</OPENINGBALANCE></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="HDFC Car Loan"><PARENT>Secured Loans</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="Loan from Director - Sunil"><PARENT>Sundry Creditors</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="Gupta Traders"><PARENT>Sundry Creditors</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="HDFC Bank"><PARENT>Bank Accounts</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="Cash"><PARENT>Cash-in-Hand</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><LEDGER NAME="Interest on Loan"><PARENT>Indirect Expenses</PARENT></LEDGER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Receipt"><DATE>20240515</DATE><VOUCHERNUMBER>1</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Rakesh Agarwal</LEDGERNAME><AMOUNT>1000000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>HDFC Bank</LEDGERNAME><AMOUNT>-1000000</AMOUNT><BANKALLOCATIONS.LIST><TRANSACTIONTYPE>e-Fund Transfer</TRANSACTIONTYPE></BANKALLOCATIONS.LIST></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Payment"><DATE>20240720</DATE><VOUCHERNUMBER>2</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Rakesh Agarwal</LEDGERNAME><AMOUNT>-300000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Cash</LEDGERNAME><AMOUNT>300000</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Journal"><DATE>20250331</DATE><VOUCHERNUMBER>3</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Interest on Loan</LEDGERNAME><AMOUNT>-84000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Rakesh Agarwal</LEDGERNAME><AMOUNT>84000</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Payment"><DATE>20240801</DATE><VOUCHERNUMBER>4</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>HDFC Car Loan</LEDGERNAME><AMOUNT>-25000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>HDFC Bank</LEDGERNAME><AMOUNT>25000</AMOUNT><BANKALLOCATIONS.LIST><TRANSACTIONTYPE>Cheque</TRANSACTIONTYPE></BANKALLOCATIONS.LIST></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Receipt"><DATE>20240901</DATE><VOUCHERNUMBER>5</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Loan from Director - Sunil</LEDGERNAME><AMOUNT>50000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Cash</LEDGERNAME><AMOUNT>-50000</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  <TALLYMESSAGE><VOUCHER VCHTYPE="Payment"><DATE>20240905</DATE><VOUCHERNUMBER>6</VOUCHERNUMBER>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>Gupta Traders</LEDGERNAME><AMOUNT>-80000</AMOUNT></ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST><LEDGERNAME>HDFC Bank</LEDGERNAME><AMOUNT>80000</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></TALLYMESSAGE>
  </DATA></BODY></ENVELOPE>`;

  it("finds loan ledgers by group, suggests loan-like names, and reads mode / opening", () => {
    const x = extractLoans(parseXml(xml));
    const byName = Object.fromEntries(x.ledgers.map((l) => [l.name, l]));
    expect(Object.keys(byName).sort()).toEqual(["HDFC Car Loan", "Loan from Director - Sunil", "Rakesh Agarwal"]);   // Gupta Traders (creditor) not offered
    expect(byName["Rakesh Agarwal"].kind).toBe("loan");
    expect(byName["Rakesh Agarwal"].unsecured).toBe(true);
    expect(byName["Rakesh Agarwal"].opening).toBe(500000);
    expect(byName["Rakesh Agarwal"].pan).toBe("ABHPA4521K");
    expect(byName["Loan from Director - Sunil"].kind).toBe("maybe");
    const rk = x.postings.filter((p) => p.ledger === "Rakesh Agarwal").map((p) => [p.date, p.credit, p.amount, p.mode, p.interest]);
    expect(rk).toEqual([["2024-05-15", true, 1000000, "electronic", false], ["2024-07-20", false, 300000, "cash", false], ["2025-03-31", true, 84000, "journal", true]]);
    expect(x.postings.find((p) => p.ledger === "HDFC Car Loan")!.mode).toBe("ac_payee_cheque");
    expect([...presetSelection(x.ledgers, "daybook")].sort()).toEqual(["hdfc car loan", "rakesh agarwal"]);
    expect([...presetSelection(x.ledgers, "unsecured")]).toEqual(["rakesh agarwal"]);
    expect([...presetSelection(x.ledgers, "custom", ["Rakesh Agarwal", "Loan from Director - Sunil", "Gone Ledger"])].sort()).toEqual(["loan from director - sunil", "rakesh agarwal"]);
  });
});

describe("Clause 31 Excel import", () => {
  it("maps a ledger-style sheet with debit / credit columns", () => {
    const rows = [["Loan register"], [], ["Date", "Particulars", "PAN", "Debit", "Credit", "Vch Type", "Narration"],
      ["15-05-2024", "Rakesh Agarwal", "ABHPA4521K", "", 1000000, "Receipt", "NEFT received"],
      ["20-07-2024", "Rakesh Agarwal", "ABHPA4521K", 300000, "", "Payment", "Paid in cash"],
      ["01-08-2024", "Sunita Agarwal", "", "", "1,50,000.00", "Receipt", "cash"],
      ["", "Total", "", 300000, 1150000, "", ""]];
    const r = c31FromTable(rows);
    expect(r.rows.map((x) => [x.txn_date, x.party_name, x.kind, x.amount, x.mode])).toEqual([
      ["2024-05-15", "Rakesh Agarwal", "taken", 1000000, "electronic"], ["2024-07-20", "Rakesh Agarwal", "repaid", 300000, "cash"], ["2024-08-01", "Sunita Agarwal", "taken", 150000, "cash"]]);
  });
});

describe("ZIP upload", () => {
  it("reads deflated and stored files, skips macOS junk and opens nested ZIPs", async () => {
    const { unzip, isZip } = await import("@/lib/import/zip");
    const bin = Uint8Array.from(atob("UEsDBBQAAAAIAChaeF02YZ6eKQAAAJ0TAAARAAAAZGF5Ym9vay9hcHJpbC54bWzt2DENACAMADBJGFj49hHYhRbk8+GAr5XRyLlzrMp+AAAAAIDvor2Su1BLAwQUAAAACAAoWnhdOZz7BgYAAAAEAAAAFAAAAF9fTUFDT1NYLy5fYXByaWwueG1syyrNywYAUEsDBBQAAAAIAChaeF0oADgfSQAAAHgAAAAIAAAAbW9yZS56aXAL8GZmEWEAAY2oithq9ulcHAwMDCDMzsDAkJtYqZdcXJaok8RlqGPEFeDNyCTCjFs5DDQwMiA0B3izsoG4jAyMDKYMDAy6YCUAUEsBAhQDFAAAAAgAKFp4XTZhnp4pAAAAnRMAABEAAAAAAAAAAAAAAIABAAAAAGRheWJvb2svYXByaWwueG1sUEsBAhQDFAAAAAgAKFp4XTmc+wYGAAAABAAAABQAAAAAAAAAAAAAAIABWAAAAF9fTUFDT1NYLy5fYXByaWwueG1sUEsBAhQDFAAAAAgAKFp4XSgAOB9JAAAAeAAAAAgAAAAAAAAAAAAAAIABkAAAAG1vcmUuemlwUEsFBgAAAAADAAMAtwAAAP8AAAAAAA=="), (c) => c.charCodeAt(0)).buffer;
    expect(isZip("x.bin", bin)).toBe(true);
    const files = await unzip(bin);
    expect(files.map((f) => [f.name, f.data.byteLength])).toEqual([["april.xml", 5021], ["more.zip/may.csv", 8]]);
    expect(new TextDecoder().decode(files[1].data)).toBe("a,b\n1,2\n");
  });
});

describe("Clause 31 report choices", () => {
  // Like the Aeron Medicare books: big opening, six bank transfers, one cheque and quarterly interest
  const K = (o: Partial<LoanTxn>) => T({ party_name: "Loan Kunal Bhatia", normalized_name: "loan kunal bhatia", ...o });
  const txns = [
    K({ txn_date: "2025-06-30", kind: "interest", amount: 20250, mode: "journal" }),
    ...[482400, 375600, 360000, 300000, 480000, 600000].map((a, i) => K({ txn_date: `2025-10-${String(10 + i).padStart(2, "0")}`, amount: a, voucher_no: String(10 + i) })),
    K({ txn_date: "2026-01-22", amount: 360000, mode: "ac_payee_cheque", voucher_no: "33" }),
  ];
  const openings = { "loan kunal bhatia": 23001224.4 };

  it("drops the word Loan from the ledger name, keeps a name changed by the user", () => {
    expect(lenderName("Loan Kunal Bhatia")).toBe("Kunal Bhatia");
    expect(lenderName("Kunal Bhatia (Unsecured Loan A/c)")).toBe("Kunal Bhatia");
    expect(lenderName("Loanstar Pvt Ltd")).toBe("Loanstar Pvt Ltd");
    expect(computeClause31(txns, openings, {}).a[0].party_name).toBe("Kunal Bhatia");
    const renamed = { "loan kunal bhatia": { normalized_name: "loan kunal bhatia", party_name: "Kunal Bhatia (HUF)" } };
    expect(computeClause31(txns, openings, renamed).a[0].party_name).toBe("Kunal Bhatia (HUF)");
  });

  it("asks a/c payee only for cheque rows and follows the answer", () => {
    const r = computeClause31(txns, openings, {});
    expect(r.a.map((x) => [x.amount, x.code, x.otherwise, x.acPayee, x.cheque])).toEqual([
      ...[482400, 375600, 360000, 300000, 480000, 600000].map((a) => [a, "L", "No", "NA", false]), [360000, "L", "No", "Yes – Cheque", true]]);
    expect(r.reviewParties).toBe(0);
    const chq = txns[txns.length - 1];
    const draft = computeClause31(txns, openings, {}, { cheque: { [txnKey(chq)]: "draft" } });
    expect(draft.a[6].acPayee).toBe("Yes – Bank draft");
    const no = computeClause31(txns, openings, {}, { cheque: { [txnKey(chq)]: "no" } });
    expect([no.a[6].code, no.a[6].otherwise, no.a[6].acPayee, no.a[6].review]).toEqual(["D", "Yes", "No", true]);
    expect(no.reviewParties).toBe(1);
  });

  it("combines entries with the same answers – bank transfers in one line, the cheque in another", () => {
    const rows = combineRows(computeClause31(txns, openings, {}).a);
    expect(rows.map((x) => [x.amount, x.acPayee, x.keys.length, x.maxOutstanding])).toEqual([[2598000, "NA", 6, 25979474.4], [360000, "Yes – Cheque", 1, 25979474.4]]);
  });
});

describe("ZIP detection", () => {
  it("reads .xlsx as a workbook even though it is a ZIP inside", () => {
    const pk = new Uint8Array([0x50, 0x4b, 0x03, 0x04, 0, 0, 0, 0]).buffer;
    expect(isZip("Clients.xlsx", pk)).toBe(false);
    expect(isZip("Book.ODS", pk)).toBe(false);
    expect(isZip("DayBook.zip")).toBe(true);
    expect(isZip("data.bin", pk)).toBe(true);
    expect(isZip("ledger.csv", new Uint8Array([65, 66, 67, 68, 69]).buffer)).toBe(false);
  });
});
