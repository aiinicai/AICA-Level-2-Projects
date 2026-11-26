// Runs only on the 3CD Helper app pages (see manifest). Passes the app's requests to the connector
// and the answers back. The app cannot send its own XML to Tally – only the fixed read-only requests
// in background.js can be made.
(() => {
  const VERSION = chrome.runtime.getManifest().version;
  const mark = () => document.documentElement && document.documentElement.setAttribute("data-tally-connector", VERSION);
  mark();
  document.addEventListener("DOMContentLoaded", mark);

  window.addEventListener("message", (ev) => {
    if (ev.source !== window || !ev.data || ev.data.source !== "3cd-helper-app") return;
    const { id, action, params } = ev.data;
    const reply = (msg) => window.postMessage({ source: "3cd-tally-connector", id, ...msg }, window.location.origin);
    let port;
    try { port = chrome.runtime.connect({ name: "tally" }); }
    catch (e) { reply({ type: "error", error: "The Tally Connector was updated or reloaded. Refresh this page and try again." }); return; }
    port.onMessage.addListener((m) => { reply(m); if (m.type === "done" || m.type === "error") port.disconnect(); });
    port.onDisconnect.addListener(() => { if (chrome.runtime.lastError) reply({ type: "error", error: chrome.runtime.lastError.message }); });
    port.postMessage({ action, params });
  });
})();
