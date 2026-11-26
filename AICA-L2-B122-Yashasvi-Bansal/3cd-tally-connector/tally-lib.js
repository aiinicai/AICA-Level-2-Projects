// Read-only TallyPrime requests and helpers, shared by background.js (and the tests).
// Only these fixed "Export" requests are ever sent to Tally – nothing that can create or change data.
(function (root) {
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const unesc = (s) => String(s ?? "")
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d)).replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
  const ymd = (iso) => String(iso).replace(/-/g, "");   // 2025-04-01 → 20250401

  /** Only Tally on this computer may be called. */
  function tallyUrl(raw) {
    let u;
    try { u = new URL(String(raw || "http://localhost:9000")); } catch (e) { throw new Error("Tally address is not valid"); }
    if (u.protocol !== "http:" || !["localhost", "127.0.0.1"].includes(u.hostname)) throw new Error("Only Tally on this computer (localhost) can be used");
    return `http://${u.hostname}:${u.port || "9000"}`;
  }

  const companiesRequest = () =>
    `<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>CMP3CDHelper</ID></HEADER>` +
    `<BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>` +
    `<TDL><TDLMESSAGE><COLLECTION NAME="CMP3CDHelper" ISMODIFY="No"><TYPE>Company</TYPE><FETCH>NAME, STARTINGFROM, BOOKSFROM</FETCH></COLLECTION></TDLMESSAGE></TDL>` +
    `</DESC></BODY></ENVELOPE>`;

  const mastersRequest = (company) =>
    `<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>` +
    `<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><ACCOUNTTYPE>All Masters</ACCOUNTTYPE><SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY></STATICVARIABLES>` +
    `</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>`;

  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const tallyDate = (iso) => { const [y, m, d] = String(iso).split("-"); return `${+d}-${MON[+m - 1]}-${y}`; };   // 2025-04-01 → 1-Apr-2025

  /**
   * Vouchers of a period with all ledger lines and bank details.
   * TallyPrime's "Day Book" report ignores the period over HTTP (it gives only the current date), and a
   * voucher collection gives the whole loaded period – so the period is applied with a TDL filter.
   */
  const vouchersRequest = (company, from, to) =>
    `<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>VCH3CDHelper</ID></HEADER>` +
    `<BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>${ymd(from)}</SVFROMDATE><SVTODATE>${ymd(to)}</SVTODATE>` +
    `<SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY></STATICVARIABLES>` +
    `<TDL><TDLMESSAGE><COLLECTION NAME="VCH3CDHelper" ISMODIFY="No"><TYPE>Voucher</TYPE>` +
    // ALLLEDGERENTRIES alone holds every accounting line once (purchase / sales ledgers of invoices included);
    // asking also for LEDGERENTRIES or inventory allocations would repeat lines.
    `<FETCH>DATE, VOUCHERTYPENAME, VOUCHERNUMBER, NARRATION, PARTYLEDGERNAME, PARTYGSTIN, ISCANCELLED, ISOPTIONAL, ISINVOICE, ALLLEDGERENTRIES.*, ALLLEDGERENTRIES.BANKALLOCATIONS.*</FETCH>` +
    `<FILTERS>VCH3CDInPeriod</FILTERS></COLLECTION>` +
    `<SYSTEM TYPE="Formulae" NAME="VCH3CDInPeriod">$Date &gt;= $$Date:"${tallyDate(from)}" AND $Date &lt;= $$Date:"${tallyDate(to)}"</SYSTEM>` +
    `</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>`;

  /** Drops empty elements (most of Tally's output) – about four times smaller, same data. */
  function slim(xml) {
    let y = String(xml).replace(/\r/g, ""); let prev;
    do {
      prev = y;
      y = y.replace(/<([A-Z0-9._]+)(?:\s+[A-Z]+="[^"]*")*\s*\/>/g, "").replace(/<([A-Z0-9._]+)(?:\s+TYPE="[^"]*")?>\s*<\/\1>/g, "");
    } while (y !== prev);
    return y.replace(/\n\s+/g, "\n").replace(/\n{2,}/g, "\n");
  }

  /** Voucher blocks dated inside the period (a safety net if Tally ignored the filter), each voucher once, slimmed. */
  function vouchersIn(xml, from, to, seen) {
    const f = ymd(from), t = ymd(to);
    return blocks(xml, "VOUCHER").map(slim).filter((v) => {
      const d = /<DATE[^>]*>(\d{8})<\/DATE>/.exec(v);
      if (!d || d[1] < f || d[1] > t) return false;
      const id = (/<GUID[^>]*>([^<]+)<\/GUID>/.exec(v) || /\bVCHKEY="([^"]+)"/.exec(v) || [])[1];
      if (id && seen) { if (seen.has(id)) return false; seen.add(id); }
      return true;
    });
  }

  /** Tally may answer in UTF-16 or UTF-8. */
  function decode(buf) {
    const b = new Uint8Array(buf);
    if (b.length >= 2 && b[0] === 0xff && b[1] === 0xfe) return new TextDecoder("utf-16le").decode(b.subarray(2));
    if (b.length >= 2 && b[0] === 0xfe && b[1] === 0xff) return new TextDecoder("utf-16be").decode(b.subarray(2));
    if (b.length >= 4 && b[1] === 0 && b[3] === 0) return new TextDecoder("utf-16le").decode(b);
    return new TextDecoder("utf-8").decode(b).replace(/^﻿/, "");
  }

  /** Error text Tally puts in its answer (bad company name, wrong request …). */
  function tallyError(xml) {
    const m = /<LINEERROR>([\s\S]*?)<\/LINEERROR>/i.exec(xml) || /<ERRORMSG>([\s\S]*?)<\/ERRORMSG>/i.exec(xml);
    return m ? unesc(m[1]).trim() : "";
  }

  function parseCompanies(xml) {
    const out = []; const seen = new Set();
    const re = /<COMPANY\b([^>]*)>([\s\S]*?)<\/COMPANY>/g; let m;
    while ((m = re.exec(xml))) {
      const attr = /NAME="([^"]*)"/.exec(m[1]);
      const inner = /<NAME[^>]*>([^<]*)<\/NAME>/.exec(m[2]);
      const name = unesc((attr && attr[1]) || (inner && inner[1]) || "").trim();
      if (!name || seen.has(name)) continue;
      seen.add(name);
      const from = /<(?:BOOKSFROM|STARTINGFROM)[^>]*>(\d{8})</.exec(m[2]);
      out.push({ name, booksFrom: from ? `${from[1].slice(0, 4)}-${from[1].slice(4, 6)}-${from[1].slice(6, 8)}` : "" });
    }
    return out;
  }

  /** [from, to] ISO pairs, one per calendar month. */
  function monthRanges(from, to) {
    const out = [];
    let d = new Date(from + "T00:00:00Z"); const end = new Date(to + "T00:00:00Z");
    if (!(d <= end)) return out;
    while (d <= end) {
      const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
      const t = last < end ? last : end;
      out.push([d.toISOString().slice(0, 10), t.toISOString().slice(0, 10)]);
      d = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate() + 1));
    }
    return out;
  }

  const blocks = (xml, tag) => xml.match(new RegExp(`<${tag}\\b[^>]*>[\\s\\S]*?<\\/${tag}>`, "g")) || [];
  const nameOf = (block) => { const a = /^<[A-Z]+\b[^>]*\bNAME="([^"]*)"/.exec(block); const n = /<NAME[^>]*>([^<]*)<\/NAME>/.exec(block); return unesc((a && a[1]) || (n && n[1]) || "").trim(); };
  const parentOf = (block) => { const m = /<PARENT[^>]*>([^<]*)<\/PARENT>/.exec(block); return unesc(m ? m[1] : "").trim(); };

  /** Ledgers whose group chain includes one of the given groups (lower-case names). */
  function ledgersUnder(masters, groupNames) {
    const want = new Set((groupNames || []).map((g) => String(g).trim().toLowerCase()).filter(Boolean));
    const parent = new Map();
    for (const g of blocks(masters, "GROUP")) { const n = nameOf(g); if (n) parent.set(n.toLowerCase(), parentOf(g)); }
    const out = new Set();
    for (const l of blocks(masters, "LEDGER")) {
      const n = nameOf(l); if (!n) continue;
      let p = parentOf(l);
      for (let i = 0; p && i < 12; i++) { if (want.has(p.toLowerCase())) { out.add(n.toLowerCase()); break; } p = parent.get(p.toLowerCase()) || ""; }
    }
    return out;
  }
  const unsecuredLedgers = (masters) => ledgersUnder(masters, ["Unsecured Loans"]);

  /** Every group with its parent and the number of ledgers directly in it. Primary groups have parent "". */
  function groupList(masters) {
    const count = new Map();
    for (const l of blocks(masters, "LEDGER")) { const p = parentOf(l).toLowerCase(); if (p) count.set(p, (count.get(p) || 0) + 1); }
    return blocks(masters, "GROUP").map((g) => { const name = nameOf(g); return { name, parent: parentOf(g), ledgers: count.get(name.toLowerCase()) || 0 }; }).filter((g) => g.name);
  }

  const voucherLedgers = (v) => { const s = new Set(); const re = /<LEDGERNAME[^>]*>([^<]*)<\/LEDGERNAME>/g; let m; while ((m = re.exec(v))) s.add(unesc(m[1]).trim().toLowerCase()); return s; };

  /**
   * One XML file for 3CD Helper: groups, ledger masters and vouchers.
   * mode "groups": only the ledgers under the chosen groups (e.g. Loans (Liability) and its sub-groups)
   * and the vouchers that touch them leave this computer. "unsecured" = groups ["Unsecured Loans"] (older app pages).
   */
  function buildExport({ company, from, to, mode, groups: chosen, masters: rawMasters, voucherXmls, voucherBlocks }) {
    const masters = slim(rawMasters);
    const groups = blocks(masters, "GROUP");
    let ledgers = blocks(masters, "LEDGER");
    let vouchers = voucherBlocks ? voucherBlocks.slice() : [];
    if (!voucherBlocks) for (const x of voucherXmls) vouchers = vouchers.concat(blocks(x, "VOUCHER"));
    let keep = null;
    const only = mode === "unsecured" ? ["Unsecured Loans"] : mode === "groups" ? (chosen || []) : null;
    if (only) {
      keep = ledgersUnder(masters, only);
      vouchers = vouchers.filter((v) => { const s = voucherLedgers(v); for (const k of keep) if (s.has(k)) return true; return false; });
      // masters of the loan ledgers and of the other side of those vouchers (bank, cash, interest) – needed to read the mode
      const used = new Set(keep);
      for (const v of vouchers) voucherLedgers(v).forEach((n) => used.add(n));
      ledgers = ledgers.filter((l) => used.has(nameOf(l).toLowerCase()));
    }
    const what = only ? `Only ${only.join(", ").replace(/--/g, "-")}` : "Day Book";
    const head = `<?xml version="1.0" encoding="UTF-8"?>\n<!-- 3CD Helper Tally Connector · ${esc(company).replace(/--/g, "-")} · ${from} to ${to} · ${esc(what)} -->\n`;
    const xml = head + `<ENVELOPE><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>${only ? "Group Vouchers" : "Day Book"}</REPORTNAME>` +
      `<STATICVARIABLES><SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA>\n` +
      groups.map((g) => `<TALLYMESSAGE>${g}</TALLYMESSAGE>\n`).join("") +
      ledgers.map((l) => `<TALLYMESSAGE>${l}</TALLYMESSAGE>\n`).join("") +
      vouchers.map((v) => `<TALLYMESSAGE>${v}</TALLYMESSAGE>\n`).join("") +
      `</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>\n`;
    return { xml, counts: { groups: groups.length, ledgers: ledgers.length, vouchers: vouchers.length, unsecuredLedgers: keep ? keep.size : null, groupLedgers: keep ? keep.size : null } };
  }

  const api = { esc, unesc, tallyUrl, tallyDate, companiesRequest, mastersRequest, vouchersRequest, vouchersIn, slim, decode, tallyError, parseCompanies, monthRanges, blocks, unsecuredLedgers, ledgersUnder, groupList, buildExport };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.TallyLib = api;
})(typeof self !== "undefined" ? self : globalThis);
