const $ = (id) => document.getElementById(id);
chrome.storage.local.get("tallyUrl").then(({ tallyUrl }) => { $("url").value = tallyUrl || "http://localhost:9000"; });

$("test").addEventListener("click", async () => {
  const s = $("status");
  s.className = ""; s.textContent = "Checking…";
  try {
    const url = self.TallyLib.tallyUrl($("url").value.trim());
    await chrome.storage.local.set({ tallyUrl: url });
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "text/xml; charset=utf-8" }, body: self.TallyLib.companiesRequest() });
    const list = self.TallyLib.parseCompanies(self.TallyLib.decode(await res.arrayBuffer()));
    s.className = "ok";
    s.textContent = list.length ? `Tally is connected.\nOpen companies:\n• ${list.map((c) => c.name).join("\n• ")}` : "Tally is connected, but no company is open.";
  } catch (e) {
    s.className = "bad";
    s.textContent = `Tally is not answering. ${e && e.message ? e.message : ""}\nCheck that TallyPrime is open and the port is right.`;
  }
});
