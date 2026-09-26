// Thin wrapper around the Local Host REST API. Always resolves to JSON or throws Error(message).
const API = {
  async request(method, path, body, isForm = false) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      if (isForm) opts.body = body;
      else { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
    }
    let resp;
    try {
      resp = await fetch(path, opts);
    } catch (e) {
      throw new Error("The BRMCo Local Host is not responding. Is the uvicorn window still running?");
    }
    let data = null;
    try { data = await resp.json(); } catch (e) { /* non-JSON */ }
    if (!resp.ok) throw new Error((data && data.detail) || `Request failed (HTTP ${resp.status})`);
    return data;
  },
  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  upload(path, file) {
    const fd = new FormData();
    fd.append("file", file);
    return this.request("POST", path, fd, true);
  },
  // Downloads go through fetch so server-side errors can be shown instead of a broken file.
  async download(path) {
    const resp = await fetch(path);
    if (!resp.ok) {
      let msg = `Download failed (HTTP ${resp.status})`;
      try { msg = (await resp.json()).detail || msg; } catch (e) { /* ignore */ }
      throw new Error(msg);
    }
    const cd = resp.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename="([^"]+)"/);
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = m ? m[1] : "download";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  },
};
