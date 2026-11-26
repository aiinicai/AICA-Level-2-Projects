import { describe, it, expect } from "vitest";
import { groupTree, versionAtLeast } from "@/lib/tallyConnector";
import { zipStored } from "@/lib/import/bundle";
import { unzip } from "@/lib/import/zip";
import { combineSameLayout } from "@/lib/import/combine";
import { createRequire } from "node:module";
const T = createRequire(import.meta.url)("../../tally-connector/tally-lib.js");

const MASTERS = `<ENVELOPE>
<TALLYMESSAGE><GROUP NAME="Loans (Liability)"><PARENT></PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><GROUP NAME="Unsecured Loans"><PARENT>Loans (Liability)</PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><GROUP NAME="Secured Loans"><PARENT>Loans (Liability)</PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><GROUP NAME="Bank Accounts"><PARENT></PARENT></GROUP></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="Kunal Bhatia"><PARENT>Loans (Liability)</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="Rakesh"><PARENT>Unsecured Loans</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="HDFC Car Loan"><PARENT>Secured Loans</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="HDFC Bank"><PARENT>Bank Accounts</PARENT></LEDGER></TALLYMESSAGE>
<TALLYMESSAGE><LEDGER NAME="Rent"><PARENT>Indirect Expenses</PARENT></LEDGER></TALLYMESSAGE>
</ENVELOPE>`;
const v = (no: string, a: string, b: string) => `<VOUCHER><DATE>20250510</DATE><VOUCHERNUMBER>${no}</VOUCHERNUMBER><ALLLEDGERENTRIES.LIST><LEDGERNAME>${a}</LEDGERNAME><AMOUNT>-100</AMOUNT></ALLLEDGERENTRIES.LIST><ALLLEDGERENTRIES.LIST><LEDGERNAME>${b}</LEDGERNAME><AMOUNT>100</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER>`;

describe("Connector loan groups", () => {
  it("finds ledgers directly under Loans (Liability) and in sub-groups", () => {
    expect([...T.ledgersUnder(MASTERS, ["Loans (Liability)"])].sort()).toEqual(["hdfc car loan", "kunal bhatia", "rakesh"]);
    expect([...T.unsecuredLedgers(MASTERS)]).toEqual(["rakesh"]);
    const g = T.groupList(MASTERS);
    expect(g.find((x: any) => x.name === "Loans (Liability)")).toEqual({ name: "Loans (Liability)", parent: "", ledgers: 1 });
  });
  it("exports only the chosen groups' vouchers", () => {
    const blocks = [v("1", "Kunal Bhatia", "HDFC Bank"), v("2", "Rent", "HDFC Bank"), v("3", "HDFC Car Loan", "HDFC Bank")];
    const r = T.buildExport({ company: "Aeron", from: "2025-04-01", to: "2026-03-31", mode: "groups", groups: ["Loans (Liability)", "Unsecured Loans"], masters: MASTERS, voucherBlocks: blocks });
    expect(r.counts.vouchers).toBe(2);
    expect(r.counts.groupLedgers).toBe(3);
    expect(r.xml.includes("Rent")).toBe(false);
    const u = T.buildExport({ company: "Aeron", from: "2025-04-01", to: "2026-03-31", mode: "unsecured", masters: MASTERS, voucherBlocks: blocks });
    expect(u.counts.vouchers).toBe(0);
  });
  it("group tree with totals, and version check", () => {
    const t = groupTree(T.groupList(MASTERS), "Loans (Liability)");
    expect(t.map((n) => `${n.depth}:${n.name}:${n.total}`)).toEqual(["0:Loans (Liability):3", "1:Secured Loans:1", "1:Unsecured Loans:1"]);
    expect(groupTree([], "Loans (Liability)")).toEqual([]);
    expect(versionAtLeast("1.0.3", "1.0.3")).toBe(true);
    expect(versionAtLeast("1.0.2", "1.0.3")).toBe(false);
    expect(versionAtLeast("1.1.0", "1.0.3")).toBe(true);
    expect(versionAtLeast(null, "1.0.3")).toBe(false);
  });
});

describe("Several files together", () => {
  it("bundles files into a ZIP the reader opens", async () => {
    const enc = new TextEncoder();
    const z = zipStored([{ name: "a.csv", data: enc.encode("x,y\n1,2") }, { name: "a.csv", data: enc.encode("x,y\n3,4") }]);
    const e = await unzip(z.buffer as ArrayBuffer);
    expect(e.map((x) => x.name)).toEqual(["a.csv", "a (2).csv"]);
    expect(new TextDecoder().decode(e[1].data)).toBe("x,y\n3,4");
  });
  it("combines sheets of the same layout from different files", () => {
    const s = [
      { name: "apr", rows: [["Report"], ["Date", "Party", "Amount"], ["1-4", "A", 10]] },
      { name: "may", rows: [["Date", "Party", "Amount"], ["1-5", "B", 20], ["2-5", "C", 30]] },
      { name: "other", rows: [["Name", "PAN"], ["X", "Y"]] },
    ];
    const out = combineSameLayout(s, ["apr.xlsx", "may.xlsx", "may.xlsx"]);
    expect(out[0].name).toBe("All 2 files combined");
    expect(out[0].rows).toEqual([["Date", "Party", "Amount"], ["1-4", "A", 10], ["1-5", "B", 20], ["2-5", "C", 30]]);
    expect(out.length).toBe(4);
    expect(combineSameLayout(s.slice(0, 1), ["a"]).length).toBe(1);
  });
});
