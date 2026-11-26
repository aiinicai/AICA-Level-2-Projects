// 3CD Helper – Tally Connector (service worker).
// Talks to TallyPrime's built-in HTTP server on this computer (F1 Help → Settings → Connectivity:
// "TallyPrime acts as Server", port 9000) and returns read-only exports to the 3CD Helper page.
importScripts("tally-lib.js");
const T = self.TallyLib;
const CHUNK = 4 * 1024 * 1024;   // characters per message

async function post(url, body, ms = 180000) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);
  let res;
  try {
    res = await fetch(url, { method: "POST", headers: { "Content-Type": "text/xml; charset=utf-8" }, body, signal: ctl.signal });
  } catch (e) {
    throw new Error(e && e.name === "AbortError"
      ? "Tally took too long to answer. Try a shorter period."
      : `Tally is not answering at ${url}. Open TallyPrime, open the company, and turn on F1 Help → Settings → Connectivity → "TallyPrime acts as" Server / Both, port 9000.`);
  } finally { clearTimeout(timer); }
  if (!res.ok) throw new Error(`Tally answered with error ${res.status}`);
  const text = T.decode(await res.arrayBuffer());
  const err = T.tallyError(text);
  if (err) throw new Error(`Tally: ${err}`);
  return text;
}

async function savedUrl(given) {
  const st = await chrome.storage.local.get("tallyUrl");
  return T.tallyUrl(given || st.tallyUrl || "http://localhost:9000");
}

const handlers = {
  async ping(_, send) {
    send({ type: "done", result: { version: chrome.runtime.getManifest().version, tallyUrl: await savedUrl() } });
  },

  async companies(p, send) {
    const url = await savedUrl(p.tallyUrl);
    const xml = await post(url, T.companiesRequest(), 30000);
    await chrome.storage.local.set({ tallyUrl: url });
    send({ type: "done", result: { tallyUrl: url, companies: T.parseCompanies(xml) } });
  },

  /** Ledger groups of a company (to choose which loan groups to bring). */
  async groups(p, send) {
    const url = await savedUrl(p.tallyUrl);
    if (!p.company) throw new Error("Choose the company");
    const masters = await post(url, T.mastersRequest(p.company));
    const groups = T.groupList(T.slim(masters));
    if (!groups.length) throw new Error(`No ledger groups came from Tally for "${p.company}". Open this company in Tally and try again.`);
    send({ type: "done", result: { groups } });
  },

  /** Opens the GST portal's taxpayer search; gst.js fills this GSTIN there. */
  async gstOpen(p, send) {
    const gstin = String(p.gstin || "").trim().toUpperCase();
    if (!GSTIN.test(gstin)) throw new Error("GSTIN is not valid");
    await chrome.storage.local.set({ gstPending: { gstin, at: Date.now() } });
    await chrome.tabs.create({ url: "https://services.gst.gov.in/services/searchtp" });
    send({ type: "done", result: { opened: true } });
  },

  /** Results read from the GST portal for these GSTINs. */
  async gstResults(p, send) {
    const want = Array.isArray(p.gstins) ? p.gstins.map((g) => String(g).toUpperCase()).slice(0, 500) : [];
    const { gstResults = {} } = await chrome.storage.local.get("gstResults");
    const results = {};
    want.forEach((g) => { if (gstResults[g]) results[g] = gstResults[g]; });
    send({ type: "done", result: { results } });
  },

  async fetch(p, send) {
    const url = await savedUrl(p.tallyUrl);
    const { company, from, to } = p;
    const mode = p.mode === "unsecured" ? "unsecured" : p.mode === "groups" ? "groups" : "daybook";
    const groups = Array.isArray(p.groups) ? p.groups.map(String).filter(Boolean).slice(0, 200) : [];
    if (mode === "groups" && !groups.length) throw new Error("Choose at least one group");
    if (!company) throw new Error("Choose the company");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(from || "") || !/^\d{4}-\d{2}-\d{2}$/.test(to || "") || from > to) throw new Error("Enter a valid period");

    send({ type: "progress", text: "Reading ledger groups and masters…" });
    const masters = await post(url, T.mastersRequest(company));
    if (!T.blocks(masters, "LEDGER").length) throw new Error(`No ledgers came from Tally for "${company}". Open this company in Tally and try again.`);

    // month by month, so a big company's year does not come as one huge answer
    const months = T.monthRanges(from, to);
    const voucherBlocks = [];
    const seen = new Set();
    for (let i = 0; i < months.length; i++) {
      const [f, t] = months[i];
      send({ type: "progress", text: `Reading vouchers ${f.slice(0, 7)} (${i + 1} of ${months.length})…` });
      const x = await post(url, T.vouchersRequest(company, f, t));
      for (const v of T.vouchersIn(x, f, t, seen)) voucherBlocks.push(v);
    }
    if (!voucherBlocks.length) throw new Error(`No vouchers found in "${company}" from ${from} to ${to}. Check the period, and that this period's books are loaded in Tally.`);

    send({ type: "progress", text: mode === "daybook" ? "Preparing the file…" : "Keeping only the chosen groups…" });
    const { xml, counts } = T.buildExport({ company, from, to, mode, groups, masters, voucherBlocks });
    if (mode === "unsecured" && !counts.unsecuredLedgers) throw new Error(`There is no ledger under the "Unsecured Loans" group in "${company}". Choose Day Book instead.`);
    if (mode === "groups" && !counts.groupLedgers) throw new Error(`There is no ledger under the chosen groups in "${company}".`);
    for (let i = 0; i < xml.length; i += CHUNK) send({ type: "chunk", data: xml.slice(i, i + CHUNK) });
    await chrome.storage.local.set({ tallyUrl: url });
    send({ type: "done", result: { counts, chars: xml.length } });
  },
};

// pages of 3CD Helper (the content script runs only there; this double-checks the sender)
const APP_ORIGINS = new Set(chrome.runtime.getManifest().content_scripts
  .filter((c) => c.js.includes("content.js")).flatMap((c) => c.matches).map((m) => m.replace(/\/\*$/, "")));
const GSTIN = /^[0-9]{2}[A-Z0-9]{13}$/;

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "tally") return;
  const origin = (port.sender && (port.sender.origin || (port.sender.url && new URL(port.sender.url).origin))) || "";
  if (!APP_ORIGINS.has(origin)) { port.disconnect(); return; }
  let open = true;
  port.onDisconnect.addListener(() => { open = false; });
  const send = (m) => { if (open) port.postMessage(m); };
  port.onMessage.addListener(async ({ action, params }) => {
    const h = handlers[action];
    if (!h) return send({ type: "error", error: "Unknown request" });
    try { await h(params || {}, send); }
    catch (e) { send({ type: "error", error: (e && e.message) || String(e) }); }
  });
});

// messages from gst.js on the GST portal page
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  const url = (sender && sender.url) || "";
  if (!url.startsWith("https://services.gst.gov.in/")) return false;
  (async () => {
    if (msg && msg.type === "gstPending") {
      const { gstPending } = await chrome.storage.local.get("gstPending");
      if (gstPending && Date.now() - gstPending.at < 10 * 60 * 1000) { await chrome.storage.local.remove("gstPending"); reply({ gstin: gstPending.gstin }); }
      else reply({});
    } else if (msg && msg.type === "gstResult" && GSTIN.test(String(msg.gstin || ""))) {
      const { gstResults = {} } = await chrome.storage.local.get("gstResults");
      gstResults[msg.gstin] = { gstin: msg.gstin, taxpayerType: String(msg.taxpayerType || "").slice(0, 80), status: String(msg.status || "").slice(0, 40), legalName: String(msg.legalName || "").slice(0, 200), at: Date.now() };
      // keep the latest 500
      const keys = Object.keys(gstResults).sort((a, b) => gstResults[b].at - gstResults[a].at);
      keys.slice(500).forEach((k) => delete gstResults[k]);
      await chrome.storage.local.set({ gstResults });
      reply({ ok: true });
    } else reply({});
  })();
  return true;
});
