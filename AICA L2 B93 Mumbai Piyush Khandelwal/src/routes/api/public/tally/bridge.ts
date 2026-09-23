import { createFileRoute } from "@tanstack/react-router";

/**
 * Serves the on-premise sync bridge script. Tally runs on the user's own
 * machine/LAN, so nothing in the cloud can reach it directly: this small Node
 * script reads Tally's XML gateway locally and pushes normalised data up.
 */
const SCRIPT = String.raw`#!/usr/bin/env node
// The DASH — Tally sync bridge
// Run on the machine where TallyPrime is running (Gateway of Tally → F1 →
// Settings → Connectivity → "Tally.ERP 9 is acting as: Both").
//
//   node dash-tally-bridge.mjs
//
// Configure with environment variables:
//   DASH_TOKEN   (required) sync token shown when you connected Tally in The DASH
//   DASH_URL     (required) ingest URL shown alongside the token
//   TALLY_URL    default http://localhost:9000
//   TALLY_COMPANY  optional company name, defaults to the open company
//   FROM_DATE / TO_DATE  in YYYYMMDD, default: last 24 months to today

const TOKEN = process.env.DASH_TOKEN;
const INGEST = process.env.DASH_URL;
const TALLY = process.env.TALLY_URL || "http://localhost:9000";
const COMPANY = process.env.TALLY_COMPANY || "";

if (!TOKEN || !INGEST) {
  console.error("Set DASH_TOKEN and DASH_URL first (both are shown in The DASH).");
  process.exit(1);
}

const pad = (n) => String(n).padStart(2, "0");
const ymd = (d) => d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate());
const today = new Date();
const from = process.env.FROM_DATE || ymd(new Date(today.getFullYear() - 2, today.getMonth(), 1));
const to = process.env.TO_DATE || ymd(today);

async function tally(xml) {
  const res = await fetch(TALLY, {
    method: "POST",
    headers: { "Content-Type": "text/xml;charset=utf-8" },
    body: xml,
  });
  if (!res.ok) throw new Error("Tally replied " + res.status + " — is the gateway switched on?");
  return await res.text();
}

const envelope = (reportName, extra = "") => \`<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>\${reportName}</REPORTNAME>
    <STATICVARIABLES>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      \${COMPANY ? "<SVCURRENTCOMPANY>" + COMPANY + "</SVCURRENTCOMPANY>" : ""}
      \${extra}
    </STATICVARIABLES>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>\`;

const tag = (block, name) => {
  const m = block.match(new RegExp("<" + name + "[^>]*>([\\\\s\\\\S]*?)</" + name + ">"));
  return m ? m[1].replace(/&amp;/g, "&").replace(/&#\d+;/g, "").trim() : "";
};
const blocks = (xml, name) =>
  xml.match(new RegExp("<" + name + "[^>]*>[\\\\s\\\\S]*?</" + name + ">", "g")) || [];

async function readVouchers() {
  const xml = await tally(
    envelope("Day Book", "<SVFROMDATE>" + from + "</SVFROMDATE><SVTODATE>" + to + "</SVTODATE>")
  );
  return blocks(xml, "VOUCHER").map((v) => {
    const entries = blocks(v, "ALLLEDGERENTRIES.LIST").concat(blocks(v, "LEDGERENTRIES.LIST"));
    let amount = 0;
    let cgst = 0, sgst = 0, igst = 0;
    for (const e of entries) {
      const ledger = tag(e, "LEDGERNAME").toLowerCase();
      const value = Math.abs(parseFloat(tag(e, "AMOUNT") || "0")) || 0;
      if (ledger.includes("cgst")) cgst += value;
      else if (ledger.includes("sgst")) sgst += value;
      else if (ledger.includes("igst")) igst += value;
      if (tag(e, "ISPARTYLEDGER") === "Yes") amount = value;
    }
    if (!amount) {
      amount = entries.reduce((s, e) => s + (Math.abs(parseFloat(tag(e, "AMOUNT") || "0")) || 0), 0) / 2;
    }
    return {
      date: tag(v, "DATE"),
      type: tag(v, "VOUCHERTYPENAME"),
      number: tag(v, "VOUCHERNUMBER"),
      party: tag(v, "PARTYLEDGERNAME") || tag(v, "PARTYNAME"),
      amount: Math.round(amount),
      cgst: Math.round(cgst),
      sgst: Math.round(sgst),
      igst: Math.round(igst),
      narration: tag(v, "NARRATION").slice(0, 120),
    };
  });
}

async function readLedgers() {
  const xml = await tally(envelope("List of Accounts", "<ACCOUNTTYPE>All Ledgers</ACCOUNTTYPE>"));
  return blocks(xml, "LEDGER").map((l) => ({
    name: (l.match(/NAME="([^"]+)"/) || [])[1] || tag(l, "NAME"),
    group: tag(l, "PARENT"),
    closing: parseFloat(tag(l, "CLOSINGBALANCE") || "0") || 0,
  })).filter((l) => l.name);
}

async function main() {
  console.log("Reading Tally at " + TALLY + " …");
  const vouchers = await readVouchers();
  const ledgers = await readLedgers();
  console.log("Found " + vouchers.length + " vouchers and " + ledgers.length + " ledgers.");

  const res = await fetch(INGEST, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-dash-token": TOKEN },
    body: JSON.stringify({ company: COMPANY || undefined, vouchers, ledgers }),
  });
  const body = await res.text();
  if (!res.ok) {
    console.error("Upload failed (" + res.status + "): " + body);
    process.exit(1);
  }
  console.log("Synced to The DASH: " + body);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
`;

export const Route = createFileRoute("/api/public/tally/bridge")({
  server: {
    handlers: {
      GET: async () =>
        new Response(SCRIPT, {
          headers: {
            "content-type": "text/javascript; charset=utf-8",
            "content-disposition": 'attachment; filename="dash-tally-bridge.mjs"',
          },
        }),
    },
  },
});
