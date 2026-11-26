// Runs only on the GST portal's "Search Taxpayer" page. When 3CD Helper opened this tab to check a party,
// it fills the GSTIN (the auditor still types the captcha and presses Search) and, once the result shows,
// sends the taxpayer type back to 3CD Helper. It never submits anything by itself.
(() => {
  const ask = (m) => new Promise((res) => { try { chrome.runtime.sendMessage(m, (r) => res(chrome.runtime.lastError ? null : r)); } catch (e) { res(null); } });
  let note;
  const show = (text) => {
    if (!note) {
      note = document.createElement("div");
      note.style.cssText = "position:fixed;z-index:2147483647;left:50%;top:12px;transform:translateX(-50%);max-width:640px;padding:10px 16px;border-radius:10px;background:#0f1f3d;color:#fff;font:14px/1.4 system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25)";
      document.documentElement.appendChild(note);
    }
    note.textContent = text;
  };
  const fill = (gstin, tries = 0) => {
    const el = document.getElementById("for_gstin");
    if (!el) { if (tries < 60) setTimeout(() => fill(gstin, tries + 1), 250); return; }
    el.focus();
    el.value = gstin;
    ["input", "change", "keyup", "blur"].forEach((t) => el.dispatchEvent(new Event(t, { bubbles: true })));
    setTimeout(() => { const c = document.querySelector("input[id*='captcha' i], input[name*='captcha' i]"); if (c) c.focus(); }, 700);
  };
  const pick = (txt, label) => { const m = new RegExp(label + "\\s*:?\\s*\\n+\\s*([^\\n]+)", "i").exec(txt) || new RegExp(label + "\\s*:\\s*([^\\n]+)", "i").exec(txt); return m ? m[1].trim() : ""; };
  const watch = (gstin) => {
    const t = setInterval(() => {
      const txt = (document.body && document.body.innerText) || "";
      if (!txt.toUpperCase().includes(gstin)) return;
      const type = pick(txt, "Taxpayer Type");
      if (!type || /taxpayer type/i.test(type)) return;
      clearInterval(t);
      const status = pick(txt, "GSTIN\\s*/\\s*UIN\\s*Status");
      const legalName = pick(txt, "Legal Name of Business");
      chrome.runtime.sendMessage({ type: "gstResult", gstin, taxpayerType: type.slice(0, 80), status: status.slice(0, 40), legalName: legalName.slice(0, 200) }, () => void chrome.runtime.lastError);
      show(`3CD Helper: ${type}${status ? " · " + status : ""} – sent back to 3CD Helper. You can close this tab.`);
    }, 1000);
    setTimeout(() => clearInterval(t), 15 * 60 * 1000);
  };
  (async () => {
    const r = await ask({ type: "gstPending" });
    if (!r || !r.gstin) return;
    show(`3CD Helper: GSTIN ${r.gstin} is filled in. Type the captcha and press SEARCH – the result goes back to 3CD Helper.`);
    fill(r.gstin);
    watch(r.gstin);
  })();
})();
