/* CA_Buddy front end. Plain JavaScript, no build step. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const main = $("#main");
let STATUS = { ocr: false, ocr_languages: [], providers: {}, categories: {} };

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const ICON = {
  up: '<svg viewBox="0 0 16 16"><path d="M8 12V4M4 7l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  down: '<svg viewBox="0 0 16 16"><path d="M8 4v8M4 9l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  x: '<svg viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  rot: '<svg viewBox="0 0 16 16"><path d="M12.5 8A4.5 4.5 0 1 1 8 3.5h3M9.5 1.5 11.5 3.5 9.5 5.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  undo: '<svg viewBox="0 0 16 16"><path d="M5 6H10a3 3 0 0 1 0 6H6M5 6l2.5-2.5M5 6l2.5 2.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  file: '<svg viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z M14 3v5h5 M12 11v6 M9 14l3-3 3 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>',
  dl: '<svg viewBox="0 0 16 16"><path d="M8 2v8M4.5 7 8 10.5 11.5 7M3 13.5h10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  lock: '<svg viewBox="0 0 20 20"><rect x="4" y="9" width="12" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M7 9V6.5a3 3 0 0 1 6 0V9" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
};
const svg = (name) => { const s = h("span", { html: ICON[name], "aria-hidden": "true" }); return s.firstChild; };

function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "show" + (error ? " error" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = ""), error ? 7000 : 3200);
}

function sizeOf(n) {
  if (n < 1024) return n + " bytes";
  if (n < 1048576) return (n / 1024).toFixed(0) + " KB";
  return (n / 1048576).toFixed(1) + " MB";
}

async function api(url, form, { blob = false } = {}) {
  const fd = form instanceof FormData ? form : Object.entries(form || {}).reduce((f, [k, v]) => {
    if (Array.isArray(v)) v.forEach((x) => f.append(k, x)); else if (v != null) f.append(k, v); return f;
  }, new FormData());
  let res;
  try { res = await fetch(url, { method: "POST", body: fd }); }
  catch { throw new Error("The app isn't responding. Check that the CA_Buddy window is still open."); }
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`, payload = {};
    try { payload = await res.json(); msg = payload.error || msg; } catch {}
    throw Object.assign(new Error(msg), { payload, status: res.status });
  }
  if (!blob) return res.json();
  const disp = res.headers.get("Content-Disposition") || "";
  const m = /filename\*=utf-8''([^;]+)/i.exec(disp) || /filename="?([^";]+)"?/i.exec(disp);
  return { blob: await res.blob(), name: m ? decodeURIComponent(m[1]) : "download",
           info: decodeURIComponent(res.headers.get("X-Result-Info") || "") };
}

function downloadBlob(blob, name) {
  const a = h("a", { href: URL.createObjectURL(blob), download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
}

async function busy(btn, label, fn) {
  const old = btn.innerHTML; btn.disabled = true;
  btn.innerHTML = ""; btn.append(h("span", { class: "spin", "aria-hidden": "true" }), label);
  try { return await fn(); } finally { btn.disabled = false; btn.innerHTML = old; }
}

function dropZone({ multiple = false, accept = ".pdf", title, hint, onFiles }) {
  const input = h("input", { type: "file", accept, multiple, hidden: true });
  const zone = h("div", { class: "drop", tabindex: "0", role: "button" },
    svg("file"), h("strong", {}, title || (multiple ? "Drop files here or click to choose" : "Drop a file here or click to choose")),
    h("span", {}, hint || ""), input);
  const pick = () => input.click();
  zone.addEventListener("click", (e) => { if (e.target !== input) pick(); });
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault(); zone.classList.remove("over");
    const files = [...e.dataTransfer.files];
    if (files.length) onFiles(multiple ? files : files.slice(0, 1));
  });
  input.addEventListener("change", () => { if (input.files.length) onFiles([...input.files]); input.value = ""; });
  return zone;
}

/* ======================================================= PDF TOOLKIT */

const POS_OPTS = [["bottom-center", "Bottom centre"], ["bottom-right", "Bottom right"], ["bottom-left", "Bottom left"],
  ["top-right", "Top right"], ["top-center", "Top centre"], ["top-left", "Top left"]];

const TOOLS = [
  { group: "Organise", id: "merge", name: "Merge PDFs", desc: "Combine notices, replies and annexures into one file. Drag rows to set the order; rename each part to get an index page and bookmarks.",
    endpoint: "/api/pdf/merge", multiple: true, action: "Merge PDFs", titles: true,
    fields: [
      { name: "index", type: "check", label: "Add an index page listing each document and its pages", default: true },
      { name: "bookmarks", type: "check", label: "Add bookmarks for each document", default: true },
      { name: "labels", type: "check", label: "Stamp the document name on its first page (e.g. Annexure A)", default: false },
    ] },
  { group: "Organise", id: "split", name: "Split PDF", desc: "Break a file into parts by page range, a fixed number of pages, or a maximum size for portal uploads.",
    endpoint: "/api/pdf/split", action: "Split PDF",
    fields: [
      { name: "mode", type: "seg", label: "Split by", options: [["ranges", "Page ranges"], ["every", "Every N pages"], ["size", "Max size"], ["each", "Every page"]], default: "ranges" },
      { name: "value", type: "text", label: "Ranges", placeholder: "1-3, 4-10, 11-last", showIf: { mode: "ranges" } },
      { name: "value", type: "number", label: "Pages per file", placeholder: "5", showIf: { mode: "every" } },
      { name: "value", type: "number", label: "Maximum size per file (MB)", placeholder: "5", help: "Handy for GST and income-tax portal upload limits.", showIf: { mode: "size" } },
    ] },
  { group: "Organise", id: "organize", name: "Arrange pages", desc: "Reorder, rotate and remove pages. Drag thumbnails to move them.", endpoint: "/api/pdf/organize", action: "Save arranged PDF", custom: "organize" },
  { group: "Shrink and convert", id: "compress", name: "Compress", desc: "Make scanned files small enough to upload or email. Text stays sharp; images are resampled.",
    endpoint: "/api/pdf/compress", action: "Compress PDF",
    fields: [
      { name: "level", type: "seg", label: "Compression", options: [["light", "Light"], ["recommended", "Recommended"], ["strong", "Strong"], ["maximum", "Maximum"]], default: "recommended" },
      { name: "target", type: "number", label: "Target size in MB (optional)", placeholder: "e.g. 5", help: "The app increases compression until the file fits, if it can." },
      { name: "grayscale", type: "check", label: "Convert images to grayscale (much smaller for scans)", default: false },
    ] },
  { group: "Shrink and convert", id: "to-word", name: "PDF to Word", desc: "Get an editable .docx from a PDF. Works best on digitally generated PDFs; run OCR on scans first.", endpoint: "/api/pdf/to-word", action: "Convert to Word" },
  { group: "Shrink and convert", id: "to-excel", name: "PDF to Excel", desc: "Pull tables (ledgers, GSTR summaries, statements) into an Excel workbook, one sheet per table. Numbers are stored as numbers.", endpoint: "/api/pdf/to-excel", action: "Convert to Excel" },
  { group: "Shrink and convert", id: "to-images", name: "PDF to images", desc: "Save each page as an image.", endpoint: "/api/pdf/to-images", action: "Convert to images",
    fields: [
      { name: "fmt", type: "seg", label: "Format", options: [["png", "PNG"], ["jpg", "JPG"]], default: "jpg" },
      { name: "dpi", type: "number", label: "Resolution (DPI)", default: 150, help: "150 for screen, 300 for print." },
    ] },
  { group: "Shrink and convert", id: "from-images", name: "Images to PDF", desc: "Turn phone photos or scans of documents into one PDF, in the order shown.", endpoint: "/api/pdf/from-images",
    multiple: true, accept: "image/*", action: "Create PDF",
    fields: [{ name: "page_size", type: "seg", label: "Page size", options: [["a4", "Fit on A4"], ["original", "Original size"]], default: "a4" }] },
  { group: "Shrink and convert", id: "office-to-pdf", name: "Word or Excel to PDF", desc: "Convert .docx, .xlsx or .pptx files to PDF. Uses Microsoft Word on Windows, or LibreOffice if installed.", endpoint: "/api/pdf/office-to-pdf",
    accept: ".doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods", action: "Convert to PDF" },
  { group: "Shrink and convert", id: "ocr", name: "OCR scanned PDF", desc: "Make scanned pages searchable and copyable. Pages that already have text are kept as they are.", endpoint: "/api/pdf/ocr", action: "Run OCR", needsOcr: true,
    fields: [{ name: "lang", type: "select", label: "Language", optionsFrom: "ocr", default: "eng" }] },
  { group: "Shrink and convert", id: "to-text", name: "Extract text", desc: "Save all the text in a PDF as a .txt file.", endpoint: "/api/pdf/to-text", action: "Extract text" },
  { group: "Secure", id: "protect", name: "Add password", desc: "Encrypt a PDF with AES-256 before emailing client documents.", endpoint: "/api/pdf/protect", action: "Protect PDF",
    fields: [
      { name: "password", type: "password", label: "Password to open the file", help: "Common practice: first 5 letters of PAN + date of birth. Share it separately." },
      { name: "owner_password", type: "password", label: "Permissions password (optional)", help: "Needed to change the restrictions below." },
      { name: "allow_print", type: "check", label: "Allow printing", default: true },
      { name: "allow_copy", type: "check", label: "Allow copying text", default: false },
    ] },
  { group: "Secure", id: "unlock", name: "Remove password", desc: "Remove the password from a PDF you're allowed to open, such as bank statements or Form 26AS / AIS downloads.", endpoint: "/api/pdf/unlock", action: "Remove password",
    fields: [{ name: "password", type: "password", label: "Current password" }] },
  { group: "Secure", id: "redact", name: "Redact details", desc: "See every page, draw boxes over anything to hide, or find text and black it out or replace it. What you mark is removed from the file, not just covered.", endpoint: "/api/pdf/redact/apply", action: "Redact and download", custom: "redact" },
  { group: "Finish", id: "page-numbers", name: "Page numbers", desc: "Number pages for submissions, e.g. “Annexure A - Page 3 of 12”.", endpoint: "/api/pdf/page-numbers", action: "Add page numbers",
    fields: [
      { name: "fmt", type: "text", label: "Format", default: "Page {n} of {total}", help: "{n} is the page number, {total} the page count." },
      { name: "position", type: "select", label: "Position", options: POS_OPTS, default: "bottom-center" },
      { name: "start", type: "number", label: "Start at", default: 1 },
      { name: "size", type: "number", label: "Font size", default: 9 },
      { name: "skip_first", type: "check", label: "Don't number the first page (cover or index)", default: false },
    ] },
  { group: "Finish", id: "watermark", name: "Watermark", desc: "Mark copies as DRAFT, CONFIDENTIAL or “Submitted to department”.", endpoint: "/api/pdf/watermark", action: "Add watermark",
    fields: [
      { name: "text", type: "text", label: "Text", default: "DRAFT" },
      { name: "opacity", type: "number", label: "Opacity (0.05 to 1)", default: 0.18, step: "0.01" },
      { name: "size", type: "number", label: "Font size", default: 60 },
      { name: "color", type: "color", label: "Colour", default: "#7a7f8c" },
      { name: "pages", type: "text", label: "Pages", default: "all", help: "all, first, last, or ranges like 1-3, 5." },
      { name: "diagonal", type: "check", label: "Diagonal across the page", default: true },
    ] },
  { group: "Finish", id: "stamp", name: "Stamp and sign", desc: "Add “Certified true copy”, your firm name, and a signature or seal image, the way you would with a rubber stamp.", endpoint: "/api/pdf/stamp", action: "Stamp PDF",
    fields: [
      { name: "text", type: "textarea", label: "Stamp text", default: "Certified true copy\nFor [Firm name]\nChartered Accountants", rows: 3 },
      { name: "image", type: "file", label: "Signature or seal image (optional)", accept: "image/png,image/jpeg", help: "A PNG with a transparent background looks best." },
      { name: "position", type: "select", label: "Position", options: POS_OPTS.filter(([v]) => !v.endsWith("center") || true), default: "bottom-right" },
      { name: "pages", type: "text", label: "Pages", default: "all", help: "all, first, last, or ranges like 1-3, 5." },
      { name: "width", type: "number", label: "Stamp width (points)", default: 160 },
      { name: "color", type: "color", label: "Ink colour", default: "#5b3fa8" },
    ] },
];

let currentTool = TOOLS[0];

function renderPdf() {
  main.innerHTML = "";
  main.append(h("header", { class: "page-head" }, h("h1", {}, "PDFsmith"),
    h("p", {}, "PDF all-in-one: everyday PDF jobs for notices, replies and client documents. Everything runs on this computer.")));
  const groups = {};
  TOOLS.forEach((t) => (groups[t.group] ||= []).push(t));
  const list = h("nav", { class: "tool-list", "aria-label": "PDF tools" },
    Object.entries(groups).map(([g, ts]) => h("div", { class: "tool-group" }, h("h3", {}, g),
      ts.map((t) => h("button", { class: "tool-btn", "aria-pressed": String(t === currentTool),
        onclick: () => { currentTool = t; renderPdf(); } }, t.name)))));
  const body = h("section", { class: "tool-body" });
  main.append(h("div", { class: "toolkit" }, list, body));
  renderTool(currentTool, body);
}

function renderTool(tool, body) {
  body.append(h("h2", {}, tool.name), h("p", { class: "desc" }, tool.desc));
  if (tool.needsOcr && !STATUS.ocr)
    body.append(h("p", { class: "note warn" }, "OCR needs the free Tesseract OCR program on this computer. The README explains the one-time install; restart the app afterwards."));
  if (tool.custom === "organize") return renderOrganize(tool, body);
  if (tool.custom === "redact") return renderRedact(tool, body);

  const state = { files: [], titles: [], values: {} };
  const form = h("form", { class: "tool-form" });
  const fileArea = h("div");
  const resultArea = h("div");
  form.append(fileArea);

  const accept = tool.accept || ".pdf,application/pdf";
  function drawFiles() {
    fileArea.innerHTML = "";
    fileArea.append(dropZone({ multiple: !!tool.multiple, accept,
      title: state.files.length && !tool.multiple ? "Drop a different file to replace it" : undefined,
      hint: tool.multiple ? "You can add more files in several goes." : "",
      onFiles: (fs) => {
        if (tool.multiple) { state.files.push(...fs); state.titles.push(...fs.map((f) => f.name.replace(/\.[^.]+$/, ""))); }
        else { state.files = fs; }
        drawFiles();
      } }));
    if (!state.files.length) return;
    const ul = h("ul", { class: "file-list", style: "margin-top:12px" });
    state.files.forEach((f, i) => {
      const move = (d) => { const j = i + d; if (j < 0 || j >= state.files.length) return;
        [state.files[i], state.files[j]] = [state.files[j], state.files[i]];
        [state.titles[i], state.titles[j]] = [state.titles[j], state.titles[i]]; drawFiles(); };
      const row = h("li", { class: "file-row", draggable: tool.multiple ? "true" : null },
        h("span", { class: "num" }, tool.multiple ? i + 1 : ""),
        h("div", { class: "meta" }, h("div", { class: "name", title: f.name }, f.name), h("div", { class: "size" }, sizeOf(f.size)),
          tool.titles ? h("input", { type: "text", value: state.titles[i], "aria-label": `Name in index for ${f.name}`,
            oninput: (e) => (state.titles[i] = e.target.value) }) : null),
        h("div", { class: "acts" },
          tool.multiple ? h("button", { type: "button", class: "icon-btn", title: "Move up", "aria-label": "Move up", onclick: () => move(-1) }, svg("up")) : null,
          tool.multiple ? h("button", { type: "button", class: "icon-btn", title: "Move down", "aria-label": "Move down", onclick: () => move(1) }, svg("down")) : null,
          h("button", { type: "button", class: "icon-btn", title: "Remove", "aria-label": `Remove ${f.name}`,
            onclick: () => { state.files.splice(i, 1); state.titles.splice(i, 1); drawFiles(); } }, svg("x"))));
      if (tool.multiple) {
        row.addEventListener("dragstart", (e) => { e.dataTransfer.setData("text/row", i); row.style.opacity = .4; });
        row.addEventListener("dragend", () => (row.style.opacity = 1));
        row.addEventListener("dragover", (e) => e.preventDefault());
        row.addEventListener("drop", (e) => {
          e.preventDefault(); e.stopPropagation();
          const from = +e.dataTransfer.getData("text/row"); if (isNaN(from) || from === i) return;
          const [f2] = state.files.splice(from, 1); const [t2] = state.titles.splice(from, 1);
          state.files.splice(i, 0, f2); state.titles.splice(i, 0, t2); drawFiles();
        });
      }
      ul.append(row);
    });
    fileArea.append(ul);
  }
  drawFiles();

  const fieldWrap = h("div", { class: "fields two" });
  (tool.fields || []).forEach((f) => { if (state.values[f.name] === undefined && f.default !== undefined) state.values[f.name] = f.default; });
  function drawFields() {
    fieldWrap.innerHTML = "";
    (tool.fields || []).forEach((f) => {
      if (f.showIf && !Object.entries(f.showIf).every(([k, v]) => state.values[k] === v)) return;
      fieldWrap.append(fieldEl(f, state.values, drawFields));
    });
  }
  drawFields();
  if (tool.fields?.length) form.append(fieldWrap);

  const go = h("button", { class: "btn primary", type: "submit" }, tool.action);
  form.append(h("div", {}, go), resultArea);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.files.length) return toast(tool.multiple ? "Add the files first." : "Choose a file first.", true);
    const fd = new FormData();
    if (tool.multiple) state.files.forEach((f) => fd.append("files", f)); else fd.append("file", state.files[0]);
    if (tool.titles) fd.append("titles", JSON.stringify(state.titles));
    for (const f of tool.fields || []) {
      if (f.showIf && !Object.entries(f.showIf).every(([k, v]) => state.values[k] === v)) continue;
      const v = state.values[f.name];
      if (f.type === "file") { if (v) fd.append(f.name, v); }
      else if (v !== undefined && v !== null) fd.append(f.name, String(v));
    }
    resultArea.innerHTML = "";
    try {
      const r = await busy(go, "Working…", () => api(tool.endpoint, fd, { blob: true }));
      downloadBlob(r.blob, r.name);
      resultArea.append(h("div", { class: "result" },
        h("p", {}, h("strong", {}, r.name), r.info),
        h("button", { type: "button", class: "btn", onclick: () => downloadBlob(r.blob, r.name) }, svg("dl"), "Download again")));
    } catch (err) { resultArea.append(h("p", { class: "note warn" }, err.message)); }
  });
  body.append(form);
}

function fieldEl(f, values, redraw) {
  const set = (v) => { values[f.name] = v; };
  if (f.type === "check")
    return h("label", { class: "check", style: "grid-column:1/-1" },
      h("input", { type: "checkbox", checked: !!values[f.name], onchange: (e) => set(e.target.checked) }), f.label);
  if (f.type === "seg") {
    const seg = h("div", { class: "seg", role: "group", "aria-label": f.label },
      f.options.map(([v, l]) => h("button", { type: "button", "aria-pressed": String(values[f.name] === v),
        onclick: () => { set(v); redraw(); } }, l)));
    return h("div", { class: "field", style: "grid-column:1/-1;display:grid;gap:6px" }, h("span", { style: "font-weight:600;font-size:14px" }, f.label), h("div", {}, seg));
  }
  let input;
  if (f.type === "select") {
    let opts = f.options;
    if (f.optionsFrom === "ocr") opts = (STATUS.ocr_languages.length ? STATUS.ocr_languages : ["eng"]).map((l) => [l, ({ eng: "English", hin: "Hindi", tam: "Tamil", tel: "Telugu", kan: "Kannada", mal: "Malayalam", mar: "Marathi", guj: "Gujarati", ben: "Bengali" })[l] || l]);
    input = h("select", { onchange: (e) => set(e.target.value) }, opts.map(([v, l]) => h("option", { value: v, selected: values[f.name] === v }, l)));
  } else if (f.type === "textarea") {
    input = h("textarea", { rows: f.rows || 3, oninput: (e) => set(e.target.value) }, values[f.name] ?? "");
  } else if (f.type === "file") {
    input = h("input", { type: "file", accept: f.accept, onchange: (e) => set(e.target.files[0] || null) });
  } else {
    input = h("input", { type: f.type === "color" ? "color" : f.type, value: values[f.name] ?? "", placeholder: f.placeholder || "",
      step: f.step || null, style: f.type === "color" ? "height:40px;padding:3px" : null,
      oninput: (e) => set(e.target.value) });
  }
  return h("label", { class: "field", style: f.type === "textarea" ? "grid-column:1/-1" : null }, f.label, input,
    f.help ? h("span", { class: "help" }, f.help) : null);
}

/* ---------- Arrange pages */
function renderOrganize(tool, body) {
  let file = null, pages = [];
  const area = h("div", { class: "tool-form" });
  const grid = h("div", { class: "pages-grid" });
  const result = h("div");
  const counter = h("span", { class: "help", style: "color:var(--ink-3)" });
  const save = h("button", { class: "btn primary", type: "button", hidden: true }, tool.action);
  const reset = h("button", { class: "btn quiet", type: "button", hidden: true, onclick: () => load(file) }, "Start over");

  async function load(f) {
    file = f; grid.innerHTML = ""; result.innerHTML = "";
    grid.append(h("p", { class: "note" }, "Reading pages…"));
    try {
      const r = await api("/api/pdf/thumbs", { file: f });
      pages = r.thumbs.map((src, i) => ({ index: i, rotate: 0, removed: false, src }));
      draw(); save.hidden = reset.hidden = false;
    } catch (e) { grid.innerHTML = ""; grid.append(h("p", { class: "note warn" }, e.message)); }
  }
  let dragFrom = null;
  function draw() {
    grid.innerHTML = "";
    const kept = pages.filter((p) => !p.removed).length;
    counter.textContent = `${kept} of ${pages.length} pages kept`;
    pages.forEach((p, i) => {
      const card = h("div", { class: "page-card" + (p.removed ? " removed" : ""), draggable: "true" },
        h("div", { class: "thumb" }, h("img", { src: p.src, alt: `Page ${p.index + 1}`, style: `transform:rotate(${p.rotate}deg)` })),
        h("div", { class: "bar" }, h("span", {}, `p. ${p.index + 1}`),
          h("span", {},
            h("button", { class: "icon-btn", type: "button", title: "Move left", "aria-label": `Move page ${p.index + 1} earlier`, onclick: () => move(i, i - 1) }, Object.assign(svg("up"), { style: "transform:rotate(-90deg)" })),
            h("button", { class: "icon-btn", type: "button", title: "Rotate", "aria-label": `Rotate page ${p.index + 1}`, onclick: () => { p.rotate = (p.rotate + 90) % 360; draw(); } }, svg("rot")),
            h("button", { class: "icon-btn", type: "button", title: p.removed ? "Keep page" : "Remove page", "aria-label": p.removed ? `Keep page ${p.index + 1}` : `Remove page ${p.index + 1}`,
              onclick: () => { p.removed = !p.removed; draw(); } }, svg(p.removed ? "undo" : "x")))));
      card.addEventListener("dragstart", () => { dragFrom = i; card.classList.add("dragging"); });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));
      card.addEventListener("dragover", (e) => { e.preventDefault(); card.classList.add("drop-before"); });
      card.addEventListener("dragleave", () => card.classList.remove("drop-before"));
      card.addEventListener("drop", (e) => { e.preventDefault(); if (dragFrom !== null) move(dragFrom, i); dragFrom = null; });
      grid.append(card);
    });
  }
  function move(a, b) { if (b < 0 || b >= pages.length || a === b) return draw(); const [p] = pages.splice(a, 1); pages.splice(b, 0, p); draw(); }
  save.addEventListener("click", async () => {
    const keep = pages.filter((p) => !p.removed).map(({ index, rotate }) => ({ index, rotate }));
    if (!keep.length) return toast("Keep at least one page.", true);
    result.innerHTML = "";
    try {
      const r = await busy(save, "Saving…", () => api(tool.endpoint, { file, pages: JSON.stringify(keep) }, { blob: true }));
      downloadBlob(r.blob, r.name);
      result.append(h("div", { class: "result" }, h("p", {}, h("strong", {}, r.name), r.info),
        h("button", { type: "button", class: "btn", onclick: () => downloadBlob(r.blob, r.name) }, svg("dl"), "Download again")));
    } catch (e) { result.append(h("p", { class: "note warn" }, e.message)); }
  });
  area.append(dropZone({ onFiles: ([f]) => load(f) }), counter, grid, h("div", { style: "display:flex;gap:8px" }, save, reset), result);
  body.append(area);
}

/* ---------- Redact: view pages, draw boxes, find & replace */
const PATTERNS = {
  "": "Quick patterns…",
  "[A-Z]{5}[0-9]{4}[A-Z]": "PAN",
  "[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]": "GSTIN",
  "[2-9][0-9]{3} ?[0-9]{4} ?[0-9]{4}": "Aadhaar",
  "(?:\\+91[ -]?)?[6-9][0-9]{9}": "Mobile number",
  "[\\w.+-]+@[\\w-]+\\.[\\w.]+": "Email address",
  "[A-Z]{4}0[A-Z0-9]{6}": "IFSC",
  "[0-9]{9,18}": "Account / long numbers",
};

function renderRedact(tool, body) {
  const R = { sid: null, name: "", pages: [], items: [], marks: [], hits: [], hitIdx: -1, sel: null,
              zoom: 1, fill: "black", history: [], seq: 0 };
  const wrap = h("div", { class: "tool-form" });
  body.append(wrap);
  const pw = h("input", { type: "password", placeholder: "Only if the PDF is password-protected", autocomplete: "off" });

  function intro() {
    wrap.innerHTML = "";
    body.closest(".toolkit")?.classList.remove("wide");
    wrap.append(dropZone({ title: "Drop the PDF to redact here or click to choose",
      hint: "You'll see every page. Draw boxes over anything to hide, or use Find to mark text.", onFiles: ([f]) => open(f) }),
      h("label", { class: "field" }, h("span", {}, "PDF password"), pw));
  }

  async function open(f) {
    wrap.innerHTML = ""; wrap.append(h("p", { class: "note" }, "Opening the PDF…"));
    try {
      const r = await api("/api/pdf/redact/open", { file: f, password: pw.value });
      Object.assign(R, { sid: r.session, name: r.name, pages: r.pages, items: r.items.map((i) => ({ ...i })),
                         marks: [], hits: [], hitIdx: -1, sel: null, history: [] });
      editor();
    } catch (e) { intro(); wrap.append(h("p", { class: "note warn" }, e.message)); }
  }

  async function close() {
    if (R.sid) api("/api/pdf/redact/close", { session: R.sid }).catch(() => {});
    R.sid = null; document.removeEventListener("keydown", onKey); intro();
  }

  /* ---- editor layout */
  let viewer, inner, pageEls = [], side, markList, hitInfo, applyBtn, result, zoomLbl;
  function editor() {
    wrap.innerHTML = "";
    body.closest(".toolkit")?.classList.add("wide");
    zoomLbl = h("span", { class: "zoom-lbl" }, "100%");
    const toolbar = h("div", { class: "rd-toolbar" },
      h("strong", { class: "rd-name", title: R.name }, R.name),
      h("span", { class: "rd-meta" }, `${R.pages.length} page${R.pages.length === 1 ? "" : "s"}`),
      h("span", { class: "rd-spacer" }),
      h("button", { class: "btn small", type: "button", title: "Zoom out", onclick: () => setZoom(R.zoom - 0.25) }, "−"),
      zoomLbl,
      h("button", { class: "btn small", type: "button", title: "Zoom in", onclick: () => setZoom(R.zoom + 0.25) }, "+"),
      h("button", { class: "btn small", type: "button", title: "Undo (Ctrl+Z)", onclick: undo }, svg("undo"), "Undo"),
      h("button", { class: "btn small quiet", type: "button", onclick: close }, "Close document"));
    inner = h("div", { class: "rd-inner" });
    viewer = h("div", { class: "rd-viewer" }, inner);
    pageEls = R.pages.map(([w, hgt], i) => {
      const layer = h("div", { class: "rd-layer" });
      const pg = h("div", { class: "rd-page", style: `aspect-ratio:${w}/${hgt}` },
        h("img", { src: `/api/pdf/redact/page/${R.sid}/${i}`, loading: "lazy", alt: `Page ${i + 1}`, draggable: "false" }), layer);
      attachDraw(layer, i);
      return h("div", { class: "rd-pagewrap" }, h("div", { class: "rd-pno" }, `Page ${i + 1}`), pg);
    });
    inner.append(...pageEls);
    side = h("aside", { class: "rd-side" });
    wrap.append(toolbar, h("div", { class: "rd-grid" }, viewer, side));
    buildSide();
    drawAll();
    document.removeEventListener("keydown", onKey);
    document.addEventListener("keydown", onKey);
  }

  function setZoom(z) {
    R.zoom = Math.min(3, Math.max(0.5, Math.round(z * 4) / 4));
    inner.style.width = R.zoom * 100 + "%";
    zoomLbl.textContent = Math.round(R.zoom * 100) + "%";
  }

  /* ---- drawing boxes with the mouse */
  function attachDraw(layer, pageNo) {
    let start = null, ghost = null;
    layer.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || e.target !== layer) return;
      e.preventDefault();
      const b = layer.getBoundingClientRect();
      start = { x: (e.clientX - b.left) / b.width, y: (e.clientY - b.top) / b.height, b };
      ghost = h("div", { class: "rd-mark ghost" });
      layer.append(ghost);
      layer.setPointerCapture(e.pointerId);
    });
    layer.addEventListener("pointermove", (e) => {
      if (!start) return;
      const { b } = start;
      const x = Math.min(1, Math.max(0, (e.clientX - b.left) / b.width)), y = Math.min(1, Math.max(0, (e.clientY - b.top) / b.height));
      Object.assign(ghost.style, { left: Math.min(x, start.x) * 100 + "%", top: Math.min(y, start.y) * 100 + "%",
        width: Math.abs(x - start.x) * 100 + "%", height: Math.abs(y - start.y) * 100 + "%" });
      start.end = { x, y };
    });
    const finish = () => {
      if (!start) return;
      const s = start, end = s.end; start = null; ghost?.remove();
      if (!end || Math.abs(end.x - s.x) * s.b.width < 5 || Math.abs(end.y - s.y) * s.b.height < 5) return;
      const [w, hgt] = R.pages[pageNo];
      const rect = [Math.min(s.x, end.x) * w, Math.min(s.y, end.y) * hgt, Math.max(s.x, end.x) * w, Math.max(s.y, end.y) * hgt];
      addMarks([{ page: pageNo, rect, text: "", replace: "", source: "box" }]);
    };
    layer.addEventListener("pointerup", finish);
    layer.addEventListener("pointercancel", () => { start = null; ghost?.remove(); });
  }

  /* ---- marks */
  const sameRect = (a, b) => a.page === b.page && a.rect.every((v, i) => Math.abs(v - b.rect[i]) < 0.6);
  function addMarks(list) {
    const added = [];
    list.forEach((m) => { if (!R.marks.some((x) => sameRect(x, m))) { const mk = { id: ++R.seq, ...m }; R.marks.push(mk); added.push(mk.id); } });
    if (added.length) R.history.push(added);
    drawAll();
    return added.length;
  }
  function removeMark(id) { R.marks = R.marks.filter((m) => m.id !== id); if (R.sel === id) R.sel = null; drawAll(); }
  function undo() {
    const last = R.history.pop();
    if (!last) return toast("Nothing to undo.");
    R.marks = R.marks.filter((m) => !last.includes(m.id)); drawAll();
  }
  function onKey(e) {
    if (!R.sid || !document.body.contains(viewer)) return document.removeEventListener("keydown", onKey);
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !typing) { e.preventDefault(); undo(); }
    if ((e.key === "Delete" || e.key === "Backspace") && R.sel && !typing) { e.preventDefault(); removeMark(R.sel); }
  }

  function pct(page, rect) {
    const [w, hgt] = R.pages[page];
    return `left:${rect[0] / w * 100}%;top:${rect[1] / hgt * 100}%;width:${(rect[2] - rect[0]) / w * 100}%;height:${(rect[3] - rect[1]) / hgt * 100}%`;
  }
  function drawAll() {
    pageEls.forEach((pe) => pe.querySelectorAll(".rd-mark:not(.ghost)").forEach((n) => n.remove()));
    R.hits.forEach((hit, i) => {
      if (R.marks.some((m) => sameRect(m, hit))) return;
      const el = h("div", { class: "rd-mark hit" + (i === R.hitIdx ? " current" : ""), style: pct(hit.page, hit.rect),
        title: "Click to mark this match", onclick: () => addMarks([{ ...hit, replace: $("#rd-rep")?.value || "", source: "find" }]) });
      layer(hit.page).append(el);
    });
    R.marks.forEach((m) => {
      const el = h("div", { class: `rd-mark on ${m.replace ? "rep" : R.fill}` + (R.sel === m.id ? " sel" : ""), style: pct(m.page, m.rect),
        title: m.replace ? `Replaced with “${m.replace}”` : "Will be removed. Click to select; Delete removes the mark.",
        onclick: (e) => { e.stopPropagation(); R.sel = R.sel === m.id ? null : m.id; drawAll();
          markList.querySelector(`[data-id="${m.id}"]`)?.scrollIntoView({ block: "nearest" }); } },
        m.replace ? h("span", {}, m.replace) : null,
        R.sel === m.id ? h("button", { class: "rd-x", type: "button", "aria-label": "Remove this mark",
          onclick: (e) => { e.stopPropagation(); removeMark(m.id); } }, "×") : null);
      layer(m.page).append(el);
    });
    drawList();
  }
  const layer = (p) => pageEls[p].querySelector(".rd-layer");
  function scrollToRect(page, rect) {
    const pg = pageEls[page].querySelector(".rd-page");
    const y = pg.offsetTop + (rect[1] / R.pages[page][1]) * pg.offsetHeight - viewer.clientHeight / 3;
    const x = pg.offsetLeft + (rect[0] / R.pages[page][0]) * pg.offsetWidth - viewer.clientWidth / 3;
    viewer.scrollTo({ top: Math.max(0, y), left: Math.max(0, x), behavior: "smooth" });
  }

  /* ---- side panel */
  function buildSide() {
    side.innerHTML = "";
    const q = h("input", { type: "text", id: "rd-q", placeholder: "Text to find, e.g. LNV Technology" });
    const rep = h("input", { type: "text", id: "rd-rep", placeholder: "Leave empty to black out" });
    const mc = h("input", { type: "checkbox" }), ww = h("input", { type: "checkbox" }), rx = h("input", { type: "checkbox" });
    const preset = h("select", { "aria-label": "Quick patterns", onchange: () => {
      if (!preset.value) return; q.value = preset.value; rx.checked = true; mc.checked = true; preset.value = ""; find(); } },
      Object.entries(PATTERNS).map(([v, l]) => h("option", { value: v }, l)));
    const findBtn = h("button", { class: "btn", type: "button", onclick: () => find() }, "Find");
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); find(); } });
    hitInfo = h("div", { class: "rd-hits" });

    async function find(value) {
      if (value != null) q.value = value;
      try {
        const r = await busy(findBtn, "Finding…", () => api("/api/pdf/redact/find", { session: R.sid, query: q.value,
          match_case: mc.checked, whole_word: ww.checked, pattern: rx.checked }));
        R.hits = r.hits; R.hitIdx = r.hits.length ? 0 : -1;
        drawAll(); showHits(r);
        if (r.hits.length) scrollToRect(r.hits[0].page, r.hits[0].rect);
      } catch (e) { toast(e.message, true); }
    }
    side._find = find;

    function showHits(r) {
      hitInfo.innerHTML = "";
      if (!r) return;
      if (!r.hits.length) {
        hitInfo.append(h("p", { class: "note" + (r.text_pages ? "" : " warn") }, r.text_pages
          ? "No matches. Check the spelling, or untick Match case / Whole word."
          : "This PDF has no text layer (it's a scan), so Find can't read it. Draw boxes on the pages instead, or run OCR first."));
        return;
      }
      const pagesHit = new Set(r.hits.map((x) => x.page)).size;
      const step = (d) => { R.hitIdx = (R.hitIdx + d + R.hits.length) % R.hits.length; drawAll();
        const x = R.hits[R.hitIdx]; scrollToRect(x.page, x.rect); counter.textContent = `${R.hitIdx + 1} of ${R.hits.length}`; };
      const counter = h("span", {}, `1 of ${r.hits.length}`);
      hitInfo.append(h("p", { class: "rd-hitline" }, h("strong", {}, `${r.hits.length} match${r.hits.length === 1 ? "" : "es"}`), ` on ${pagesHit} page${pagesHit === 1 ? "" : "s"}. Yellow boxes show them; click one to mark just that match.`),
        h("div", { class: "rd-row" },
          h("button", { class: "btn small", type: "button", onclick: () => step(-1), "aria-label": "Previous match" }, "‹"), counter,
          h("button", { class: "btn small", type: "button", onclick: () => step(1), "aria-label": "Next match" }, "›"),
          h("span", { class: "rd-spacer" }),
          h("button", { class: "btn small primary", type: "button", onclick: () => {
            const n = addMarks(R.hits.map((x) => ({ ...x, replace: rep.value.trim(), source: "find" })));
            toast(rep.value.trim() ? `${n} match${n === 1 ? "" : "es"} will be replaced with “${rep.value.trim()}”.` : `Marked ${n} match${n === 1 ? "" : "es"}.`);
            R.hits = []; drawAll(); hitInfo.innerHTML = ""; } }, rep.value.trim() ? "Replace all" : "Mark all")));
    }
    rep.addEventListener("input", () => { const b = hitInfo.querySelector(".btn.primary"); if (b) b.textContent = rep.value.trim() ? "Replace all" : "Mark all"; });

    // detected details
    const det = h("div", { class: "rd-det" });
    if (R.items.length) {
      det.append(h("div", { class: "rd-row" }, h("h3", {}, `Found automatically (${R.items.length})`), h("span", { class: "rd-spacer" }),
        h("button", { class: "btn small quiet", type: "button", onclick: markDetected }, "Mark all")),
        h("div", { class: "rd-chips" }, R.items.map((it) => h("button", { class: "rd-chip", type: "button", title: `${it.label}: find and show it`,
          onclick: () => { rx.checked = false; find(it.value.split("\n")[0]); } }, h("small", {}, it.label), it.value.split("\n")[0]))));
    }
    async function markDetected() {
      let n = 0;
      for (const it of R.items) {
        try {
          const r = await api("/api/pdf/redact/find", { session: R.sid, query: it.value, match_case: false, whole_word: false, pattern: false });
          n += addMarks(r.hits.map((x) => ({ ...x, replace: "", source: "find" })));
        } catch {}
      }
      toast(`Marked ${n} place${n === 1 ? "" : "s"} for ${R.items.length} detected detail${R.items.length === 1 ? "" : "s"}.`);
    }

    markList = h("div", { class: "rd-list" });
    const fillSel = h("div", { class: "rd-row rd-fill" }, h("span", {}, "Marked areas become"),
      ...[["black", "Black boxes"], ["white", "White (blank)"]].map(([v, l]) => h("label", {},
        h("input", { type: "radio", name: "rd-fill", value: v, checked: R.fill === v, onchange: () => { R.fill = v; drawAll(); } }), l)));
    applyBtn = h("button", { class: "btn primary rd-apply", type: "button", onclick: apply }, "Redact and download");
    result = h("div");

    side.append(
      h("section", { class: "rd-sec" }, h("h3", {}, "Find and replace"),
        h("div", { class: "find-row" }, q, findBtn),
        h("label", { class: "field" }, h("span", {}, "Replace with (optional)"), rep,
          h("span", { class: "help" }, "Works best when about as long as the original. Longer text is written smaller to fit.")),
        h("div", { class: "rd-opts" }, h("label", {}, mc, "Match case"), h("label", {}, ww, "Whole word"), h("label", {}, rx, "Pattern")),
        preset, hitInfo),
      R.items.length ? h("section", { class: "rd-sec" }, det) : null,
      h("section", { class: "rd-sec" }, h("h3", {}, "Draw on the page"),
        h("p", { class: "rd-help" }, "Drag across any part of a page (text, a photo, a signature or a seal) to hide it. Click a box to select it; press Delete to remove it, or Ctrl+Z to undo.")),
      h("section", { class: "rd-sec" }, h("div", { class: "rd-row" }, h("h3", { id: "rd-count" }, "Marked (0)"), h("span", { class: "rd-spacer" }),
        h("button", { class: "btn small quiet", type: "button", onclick: () => { if (R.marks.length && confirmClear()) { R.history.push([]); R.marks = []; drawAll(); } } }, "Clear all")),
        markList, fillSel, applyBtn, result));
    function confirmClear() { return R.marks.length < 3 || window.confirm?.("Remove all marks?") !== false; }
  }

  function drawList() {
    if (!markList) return;
    $("#rd-count").textContent = `Marked (${R.marks.length})`;
    applyBtn.disabled = !R.marks.length;
    applyBtn.textContent = R.marks.length ? `Redact ${R.marks.length} mark${R.marks.length === 1 ? "" : "s"} and download` : "Redact and download";
    markList.innerHTML = "";
    if (!R.marks.length) { markList.append(h("p", { class: "rd-help" }, "Nothing marked yet.")); return; }
    [...R.marks].sort((a, b) => a.page - b.page || a.rect[1] - b.rect[1]).forEach((m) => {
      const repIn = h("input", { type: "text", value: m.replace, placeholder: "Replace with…", "aria-label": "Replacement text",
        oninput: (e) => { m.replace = e.target.value; drawMarksOnly(); } });
      markList.append(h("div", { class: "rd-item" + (R.sel === m.id ? " sel" : ""), "data-id": m.id },
        h("button", { class: "rd-goto", type: "button", onclick: () => { R.sel = m.id; drawAll(); scrollToRect(m.page, m.rect); } },
          h("small", {}, `Page ${m.page + 1}`), m.text ? m.text : h("em", {}, "Drawn area")),
        repIn,
        h("button", { class: "icon-btn", type: "button", "aria-label": "Remove mark", onclick: () => removeMark(m.id) }, svg("x"))));
    });
  }
  function drawMarksOnly() { const keep = markList; markList = null; drawAll(); markList = keep; }

  async function apply() {
    result.innerHTML = "";
    try {
      const r = await busy(applyBtn, "Redacting…", () => api("/api/pdf/redact/apply", { session: R.sid, fill: R.fill,
        marks: JSON.stringify(R.marks.map(({ page, rect, replace }) => ({ page, rect, replace }))) }, { blob: true }));
      downloadBlob(r.blob, r.name);
      result.append(h("div", { class: "result" }, h("p", {}, h("strong", {}, r.name), r.info),
        h("button", { type: "button", class: "btn", onclick: () => downloadBlob(r.blob, r.name) }, svg("dl"), "Download again")));
    } catch (e) { result.append(h("p", { class: "note warn" }, e.message)); }
    drawList();
  }

  intro();
}

function detList(items, onChange, { removable = true } = {}) {
  const groups = {};
  items.forEach((it) => (groups[it.label || it.category] ||= []).push(it));
  if (!items.length) return h("p", { class: "note" }, "Nothing detected yet. Add details below, or select text in the preview.");
  return h("div", { class: "det-list" }, Object.entries(groups).map(([g, its]) => h("div", { class: "det-group" }, h("h3", {}, g),
    its.map((it) => h("div", { class: "det-item" + (it.enabled ? "" : " off") },
      h("input", { type: "checkbox", checked: it.enabled, "aria-label": `Mask ${it.value}`, onchange: (e) => { it.enabled = e.target.checked; onChange(); } }),
      h("div", {}, h("div", { class: "v" }, it.value),
        h("div", { class: "n" }, [it.count != null ? `Appears ${it.count} time${it.count === 1 ? "" : "s"}` : null, it.note].filter(Boolean).join("; "))),
      h("div", { style: "display:flex;gap:4px;align-items:center" },
        it.token ? h("span", { class: "tok" }, it.token) : null,
        removable && it.category === "custom" ? h("button", { class: "icon-btn", type: "button", "aria-label": `Remove ${it.value}`,
          onclick: () => { items.splice(items.indexOf(it), 1); onChange(); } }, svg("x")) : null))))));
}

/* ======================================================= NOTICE ASSISTANT */

const N = {
  step: 1, file: null, data: null, task: "summary", answer: null, editing: false, showMasked: false, showOrig: false,
  provider: localStorage.getItem("cawb_provider") || "anthropic",
  model: {}, key: {}, instructions: "", tone: "balanced", password: "", lang: "eng",
};
try { N.model = JSON.parse(localStorage.getItem("cawb_models") || "{}"); } catch {}
try { N.key = JSON.parse(localStorage.getItem("cawb_keys") || "{}"); } catch {}
N.remember = Object.keys(N.key).length > 0;

function persistAI() {
  try {
    localStorage.setItem("cawb_provider", N.provider);
    localStorage.setItem("cawb_models", JSON.stringify(N.model));
    if (N.remember) localStorage.setItem("cawb_keys", JSON.stringify(N.key)); else localStorage.removeItem("cawb_keys");
  } catch {}
}

function renderNotice() {
  main.innerHTML = "";
  main.append(h("header", { class: "page-head" }, h("h1", {}, "SafeAsk"),
    h("p", {}, "AI need not know everything. Summarise a GST or income-tax notice, or draft a reply. Personal details are replaced with codes before anything leaves this computer, and put back in the answer.")));
  const labels = ["Upload notice", "Check masking", "Choose task", "Review answer"];
  main.append(h("ol", { class: "steps", "aria-label": "Progress" }, labels.map((l, i) =>
    h("li", { class: i + 1 < N.step ? "done" : i + 1 === N.step ? "now" : "", "aria-current": i + 1 === N.step ? "step" : null },
      h("span", { class: "dot" }, i + 1 < N.step ? "✓" : i + 1), l))));
  const body = h("div");
  main.append(body);
  [null, stepUpload, stepMask, stepAsk, stepAnswer][N.step](body);
  main.focus({ preventScroll: true });
}

function noticeHeader() {
  const c = N.data.classification;
  return h("div", { class: "notice-id" },
    h("span", { class: "file" }, N.data.filename),
    c.law !== "Unknown" ? h("span", { class: "chip law" }, c.law) : null,
    c.form ? h("span", { class: "chip" }, c.form) : null,
    c.description ? h("span", { class: "chip" }, c.description) : null,
    c.reply_window ? h("span", { class: "chip" }, `Reply within ${c.reply_window}`) : null,
    h("button", { class: "btn quiet small", onclick: () => { N.step = 1; N.data = null; N.answer = null; renderNotice(); } }, "Use a different notice"));
}

function stepUpload(body) {
  const status = h("div");
  const pw = h("input", { type: "password", placeholder: "Only if the PDF is password-protected", value: N.password, oninput: (e) => (N.password = e.target.value) });
  const opts = h("div", { class: "fields two", style: "margin-top:16px" },
    h("label", { class: "field" }, "PDF password", pw),
    STATUS.ocr ? fieldEl({ name: "lang", type: "select", label: "Language for scanned notices", optionsFrom: "ocr" }, N, () => {}) : null);
  async function load(f) {
    N.file = f; status.innerHTML = "";
    status.append(h("p", { class: "note", style: "margin-top:16px;display:flex;gap:10px;align-items:center" }, h("span", { class: "spin" }), `Reading ${f.name} and looking for personal details…`));
    try {
      N.data = await api("/api/notice/load", { file: f, password: N.password, lang: N.lang || "eng" });
      N.step = 2; N.answer = null; renderNotice();
    } catch (e) { status.innerHTML = ""; status.append(h("p", { class: "note warn", style: "margin-top:16px" }, e.message)); }
  }
  body.append(h("div", { class: "panel" },
    dropZone({ title: "Drop the notice PDF here or click to choose", hint: "GST (ASMT-10, DRC-01A, DRC-01, REG-17 and others) or income-tax notices. Scanned notices are read with OCR.", onFiles: ([f]) => load(f) }),
    opts, !STATUS.ocr ? h("p", { class: "note", style: "margin-top:14px" }, "Scanned notices need Tesseract OCR installed (see README). Digital notices from the GST and income-tax portals work without it.") : null,
    status));
}

/* ---------- Step 2: masking */
function originalText() {
  return N.data.segments.map((s) => (typeof s === "string" ? s : s.orig)).join("");
}
function countIn(text, value) {
  const parts = value.trim().split(/\s+/).map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!parts.length || !parts[0]) return 0;
  const lead = /^[A-Za-z0-9]/.test(value.trim()) ? "(?<![A-Za-z0-9])" : "";
  const tail = /[A-Za-z0-9]$/.test(value.trim()) ? "(?![A-Za-z0-9])" : "";
  try { return (text.match(new RegExp(lead + parts.join("[\\s,]*\\s+") + tail, "gi")) || []).length; } catch { return 0; }
}

async function saveItems() {
  try { N.data = await api("/api/notice/items", { session: N.data.session, items: JSON.stringify(N.data.items) }); }
  catch (e) { toast(e.message, true); }
  renderNotice();
}
function addMask(value) {
  value = value.trim();
  if (!value) return;
  if (N.data.items.some((i) => i.value.toLowerCase() === value.toLowerCase())) {
    const it = N.data.items.find((i) => i.value.toLowerCase() === value.toLowerCase()); it.enabled = true;
  } else {
    N.data.items.push({ category: "custom", value, enabled: true });
  }
  saveItems();
}

async function maskValues(values) {
  for (const v of values) {
    const it = N.data.items.find((i) => i.value.toLowerCase() === v.toLowerCase());
    if (it) it.enabled = true; else N.data.items.push({ category: "custom", value: v, enabled: true });
  }
  await saveItems();
}
async function allowValues(values, undo = false) {
  try { N.data = await api("/api/notice/allow", { session: N.data.session, values: JSON.stringify(values), undo: undo ? "true" : "false" }); }
  catch (e) { toast(e.message, true); }
  renderNotice();
}
function leakPanel(leaks, { compact = false } = {}) {
  return h("div", { class: "panel leak-panel", role: "alert" },
    h("h2", {}, `Still visible: ${leaks.length} item${leaks.length === 1 ? "" : "s"} that may identify the client`),
    h("p", { class: "sub" }, "A second check of the masked text found these. Nothing is sent while they're listed. Mask them, or mark them as fine to send."),
    h("div", { class: "leak-list" }, leaks.slice(0, compact ? 6 : 50).map((l) => h("div", { class: "leak-item" },
      h("div", {}, h("div", { class: "v" }, l.value), h("div", { class: "n" }, `${l.reason}${l.count ? `; appears ${l.count} time${l.count === 1 ? "" : "s"}` : ""}`)),
      h("div", { style: "display:flex;gap:4px" },
        h("button", { class: "btn small primary", type: "button", onclick: () => maskValues([l.value]) }, "Mask"),
        h("button", { class: "btn small", type: "button", onclick: () => allowValues([l.value]) }, "Fine to send"))))),
    leaks.length > 1 ? h("div", { style: "margin-top:12px" },
      h("button", { class: "btn primary", type: "button", onclick: () => maskValues(leaks.map((l) => l.value)) }, `Mask all ${leaks.length}`)) : null);
}
function markLeaks(text, leaks) {
  if (!leaks?.length) return [text];
  const esc = leaks.map((l) => l.value.trim().split(/\s+/).map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("[\\s,]*\\s+"))
    .sort((a, b) => b.length - a.length);
  let rx;
  try { rx = new RegExp(`(?<![A-Za-z0-9])(${esc.join("|")})(?![A-Za-z0-9])`, "gi"); } catch { return [text]; }
  const out = []; let pos = 0, m;
  while ((m = rx.exec(text))) {
    if (m.index > pos) out.push(text.slice(pos, m.index));
    out.push(h("mark", { class: "leak", title: "Still visible. Select it and click Mask this, or use the list on the right." }, m[0]));
    pos = m.index + m[0].length;
    if (!m[0].length) rx.lastIndex++;
  }
  out.push(text.slice(pos));
  return out;
}

function stepMask(body) {
  const d = N.data;
  body.append(noticeHeader());
  const warn = [];
  if (d.meta.ocr_pages.length) warn.push(h("p", { class: "note" }, `Pages ${d.meta.ocr_pages.join(", ")} were scanned and read with OCR. Check the text for misread names or numbers and add them below if needed.`));
  if (d.meta.unreadable_pages.length) warn.push(h("p", { class: "note warn" }, `Pages ${d.meta.unreadable_pages.join(", ")} couldn't be read (scanned image, no OCR). They won't be included.`));

  const preview = h("div", { class: "preview" + (N.showOrig ? " show-orig" : ""), tabindex: "0", "aria-label": "Notice text as it will be sent" });
  d.segments.forEach((s) => {
    if (typeof s === "string") preview.append(...markLeaks(s, d.leaks));
    else preview.append(h("span", { class: "tok", title: N.showOrig ? s.token : s.orig }, N.showOrig ? s.orig : s.token));
  });
  const pop = h("button", { class: "btn primary small sel-pop", hidden: true, type: "button" }, "Mask this");
  let selected = "";
  preview.addEventListener("mouseup", () => setTimeout(() => {
    const sel = window.getSelection(); const txt = sel.toString().trim();
    if (!txt || txt.length > 200 || !preview.contains(sel.anchorNode)) { pop.hidden = true; return; }
    selected = txt;
    const r = sel.getRangeAt(0).getBoundingClientRect(), pr = preview.parentElement.getBoundingClientRect();
    pop.style.left = Math.max(0, r.left - pr.left) + "px"; pop.style.top = (r.bottom - pr.top + 6) + "px"; pop.hidden = false;
  }, 10));
  pop.addEventListener("mousedown", (e) => e.preventDefault());
  pop.addEventListener("click", () => { pop.hidden = true; addMask(selected); });

  const enabled = d.items.filter((i) => i.enabled).length;
  const left = h("section", { style: "position:relative" },
    h("div", { class: "preview-head" }, h("h2", {}, "What the AI will see"),
      h("label", { class: "check" }, h("input", { type: "checkbox", checked: N.showOrig, onchange: (e) => { N.showOrig = e.target.checked; renderNotice(); } }), "Show real values")),
    preview, pop,
    h("p", { class: "help", style: "color:var(--ink-3);font-size:13px;margin:8px 0 0" }, "Select any text in the preview and click “Mask this” to hide it too."));

  const find = h("input", { type: "text", placeholder: "Name, number, place…", "aria-label": "Text to find and mask" });
  const findCount = h("div", { class: "find-count", "aria-live": "polite" });
  const text = originalText();
  find.addEventListener("input", () => {
    const v = find.value.trim();
    findCount.textContent = v.length < 2 ? "" : (() => { const n = countIn(text, v); return n ? `Found ${n} time${n > 1 ? "s" : ""} in the notice` : "Not found in the notice"; })();
  });
  const addBtn = h("button", { class: "btn", type: "button", onclick: () => addMask(find.value) }, "Mask");
  find.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addBtn.click(); } });

  const allowedNote = d.allowed?.length ? h("p", { class: "note" }, `Left visible on purpose: ${d.allowed.join(", ")}. `,
    h("button", { class: "btn quiet small", type: "button", onclick: () => allowValues(d.allowed, true) }, "Check these again")) : null;
  const side = h("aside", { class: "mask-side" },
    d.leaks?.length ? leakPanel(d.leaks) : h("p", { class: "note ok" }, "Second check passed: nothing else in the masked text looks like a name, ID, address, phone, email or account number."),
    allowedNote,
    h("div", { class: "panel" },
      h("h2", {}, "Find and mask"),
      h("p", { class: "sub" }, "Hide anything else that identifies the client: a project name, site, director, invoice number."),
      h("div", { class: "find-row" }, find, addBtn), findCount),
    h("div", { class: "panel" },
      h("h2", {}, `Masked details (${enabled})`),
      h("p", { class: "sub" }, "Untick anything the AI needs to see as is. Notice reference numbers are left visible by default."),
      detList(d.items, saveItems)),
    h("div", { style: "display:flex;gap:8px;flex-wrap:wrap" },
      h("button", { class: "btn primary", onclick: () => {
        if (d.leaks?.length) { toast(`Deal with the ${d.leaks.length} item${d.leaks.length === 1 ? "" : "s"} under “Still visible” first.`, true); return; }
        N.step = 3; renderNotice(); } }, "Masking looks right, continue"),
      h("button", { class: "btn", title: "A copy of the notice PDF with the masked details permanently blacked out",
        onclick: async (e) => { try { const r = await busy(e.currentTarget, "Preparing…", () => api("/api/notice/masked-pdf", { session: d.session }, { blob: true })); downloadBlob(r.blob, r.name); toast(r.info); } catch (err) { toast(err.message, true); } } },
        svg("dl"), "Redacted PDF")));

  body.append(...warn, h("div", { class: "mask-grid", style: warn.length ? "margin-top:16px" : null }, left, side));
}

/* ---------- Step 3: choose task & model */
function stepAsk(body) {
  const d = N.data, P = STATUS.providers;
  body.append(noticeHeader());
  const prov = P[N.provider] || P.anthropic;

  const cards = h("div", { class: "task-cards" },
    h("button", { class: "task-card", "aria-pressed": String(N.task === "summary"), onclick: () => { N.task = "summary"; renderNotice(); } },
      h("strong", {}, "Summarise the notice"), h("span", {}, "Allegations, amounts, due dates, documents asked for, and what to check before replying.")),
    h("button", { class: "task-card", "aria-pressed": String(N.task === "draft"), onclick: () => { N.task = "draft"; renderNotice(); } },
      h("strong", {}, "Draft a reply"), h("span", {}, "A point-wise reply with preliminary objections, prayer and annexure list, ready to edit.")));

  const instr = h("textarea", { rows: N.task === "draft" ? 7 : 3, oninput: (e) => (N.instructions = e.target.value),
    placeholder: N.task === "draft"
      ? "Your facts and line of argument, e.g.\n• ITC difference of ₹4.56 lakh is because the supplier filed GSTR-1 late; it reflects in 2B of April 2023. Reconciliation as Annexure A.\n• RCM on legal services was paid in March 2023 via DRC-03.\n• Notice for FY 2022-23 under 73: check limitation."
      : "Optional: anything specific to look at, e.g. “Is the notice within time limit?”" }, N.instructions);

  const taskPanel = h("div", { class: "panel" }, h("h2", {}, "What do you need?"), h("p", { class: "sub" }, "You can run the other one afterwards without re-masking."),
    cards,
    h("div", { class: "fields", style: "margin-top:18px" },
      h("label", { class: "field" }, N.task === "draft" ? "Your facts and instructions for the reply" : "Extra question (optional)",
        instr, h("span", { class: "help" }, "Names you type here are masked too.")),
      N.task === "draft" ? h("div", { class: "field", style: "display:grid;gap:6px" }, h("span", { style: "font-weight:600;font-size:14px" }, "Tone"),
        h("div", {}, h("div", { class: "seg", role: "group", "aria-label": "Tone" },
          [["conciliatory", "Conciliatory"], ["balanced", "Balanced"], ["assertive", "Assertive"]].map(([v, l]) =>
            h("button", { type: "button", "aria-pressed": String(N.tone === v), onclick: () => { N.tone = v; renderNotice(); } }, l))))) : null));

  // model panel
  const modelList = h("datalist", { id: "model-list" }, prov.suggested.map((m) => h("option", { value: m })));
  const modelInput = h("input", { type: "text", list: "model-list", value: N.model[N.provider] || prov.default,
    oninput: (e) => { N.model[N.provider] = e.target.value; persistAI(); } });
  const keyInput = h("input", { type: "password", placeholder: prov.key_hint, value: N.key[N.provider] || "", autocomplete: "off",
    oninput: (e) => { N.key[N.provider] = e.target.value; persistAI(); } });
  const showKey = h("button", { class: "btn small", type: "button", onclick: () => { keyInput.type = keyInput.type === "password" ? "text" : "password"; showKey.textContent = keyInput.type === "password" ? "Show" : "Hide"; } }, "Show");
  const loadModels = h("button", { class: "btn small", type: "button", onclick: async () => {
    try {
      const r = await busy(loadModels, "Loading…", () => api("/api/models", { provider: N.provider, api_key: keyInput.value }));
      modelList.innerHTML = ""; r.models.forEach((m) => modelList.append(h("option", { value: m })));
      toast(`${r.models.length} models available. Click the model box to pick one.`);
    } catch (e) { toast(e.message, true); } } }, "Load models");

  const aiPanel = h("div", { class: "panel" }, h("h2", {}, "AI model"), h("p", { class: "sub" }, "Uses your own API key. You pay the provider directly."),
    h("div", { class: "fields" },
      h("div", { class: "seg", role: "group", "aria-label": "Provider" }, Object.entries(P).map(([k, v]) =>
        h("button", { type: "button", "aria-pressed": String(N.provider === k), onclick: () => { N.provider = k; persistAI(); renderNotice(); } }, v.label.replace(" (Anthropic)", "")))),
      h("label", { class: "field" }, "API key", h("div", { class: "key-row" }, keyInput, showKey),
        h("span", { class: "help" }, "Get one at ", h("a", { href: prov.key_url, target: "_blank", rel: "noopener" }, new URL(prov.key_url).host))),
      h("label", { class: "check" }, h("input", { type: "checkbox", checked: N.remember, onchange: (e) => { N.remember = e.target.checked; persistAI(); } }),
        "Remember my keys on this computer"),
      h("label", { class: "field" }, "Model", h("div", { class: "key-row" }, modelInput, loadModels), modelList)));

  const sentBox = h("div", { hidden: true });
  const viewSent = h("button", { class: "btn quiet small", type: "button", onclick: async () => {
    if (!sentBox.hidden) { sentBox.hidden = true; viewSent.textContent = "See exactly what will be sent"; return; }
    const r = await api("/api/notice/masked-text", { session: d.session });
    sentBox.innerHTML = ""; sentBox.append(h("div", { class: "sent-preview" }, r.text)); sentBox.hidden = false; viewSent.textContent = "Hide";
  } }, "See exactly what will be sent");

  const go = h("button", { class: "btn primary", style: "width:100%;padding:12px" }, N.task === "draft" ? "Draft reply" : "Summarise notice");
  const err = h("div");
  go.addEventListener("click", () => ask(go, err, false));

  const masked = d.items.filter((i) => i.enabled).length;
  const places = d.items.filter((i) => i.enabled).reduce((n, i) => n + (i.count || 0), 0);
  body.append(h("div", { class: "ask-grid" },
    h("div", { style: "display:grid;gap:18px" }, taskPanel,
      h("div", {}, h("button", { class: "btn quiet small", onclick: () => { N.step = 2; renderNotice(); } }, "Back to masking"))),
    h("aside", { class: "side-stack" }, aiPanel,
      h("div", { class: "privacy" }, svg("lock"), h("div", {},
        `${masked} detail${masked === 1 ? "" : "s"} masked in ${places} place${places === 1 ? "" : "s"}, and the second check found nothing else identifying. Only the masked text (about ${Math.round(d.masked_chars / 1000) || 1}k characters) goes to ${prov.label.replace(" (Anthropic)", "")}; real values are put back on this computer.`,
        h("div", {}, viewSent), sentBox)),
      go, err)));
}

async function ask(btn, errBox, refine, refineText = "") {
  errBox.innerHTML = "";
  const key = N.key[N.provider] || "";
  if (!key.trim()) { errBox.append(h("p", { class: "note warn" }, "Paste your API key first.")); return; }
  const label = STATUS.providers[N.provider].label.replace(" (Anthropic)", "");
  const t0 = Date.now();
  let timer;
  try {
    const r = await busy(btn, `Asking ${label}…`, () => {
      timer = setInterval(() => { const s = Math.round((Date.now() - t0) / 1000); btn.lastChild.textContent = ` Asking ${label}… ${s}s`; }, 1000);
      return api("/api/notice/ask", { session: N.data.session, task: N.task, provider: N.provider,
        model: N.model[N.provider] || STATUS.providers[N.provider].default, api_key: key,
        instructions: refine ? refineText : N.instructions, tone: N.tone, refine: refine ? "true" : "false" });
    });
    N.answer = r; N.editing = false; N.showMasked = false; N.step = 4; renderNotice();
    window.scrollTo({ top: 0 });
  } catch (e) {
    if (e.status === 409 && e.payload?.leaks?.length) {
      const vals = e.payload.leaks.map((l) => l.value);
      errBox.append(h("div", { class: "note warn", style: "margin-top:10px;display:grid;gap:10px" },
        h("div", {}, e.message),
        h("div", { style: "display:flex;gap:6px;flex-wrap:wrap" },
          h("button", { class: "btn small primary", type: "button", onclick: async () => { await maskValues(vals); } }, "Mask these"),
          h("button", { class: "btn small", type: "button", onclick: async () => { await allowValues(vals); } }, "They're fine to send"))));
    } else errBox.append(h("p", { class: "note warn", style: "margin-top:10px" }, e.message));
  }
  finally { clearInterval(timer); }
}

/* ---------- Step 4: answer */
function stepAnswer(body) {
  const a = N.answer;
  body.append(noticeHeader());
  const sheet = h("article", { class: "sheet" + (N.showMasked ? " masked" : "") });
  if (N.editing) {
    const ta = h("textarea", { class: "md-edit", "aria-label": "Edit the answer" }, a.markdown);
    ta.addEventListener("input", () => { a.markdown = ta.value; a.dirty = true; });
    sheet.append(ta);
  } else if (N.showMasked) {
    sheet.append(h("pre", { style: "white-space:pre-wrap;font:13.5px/1.6 var(--mono);margin:0" }, a.masked_markdown));
  } else {
    sheet.innerHTML = a.html;
  }

  const copyBtn = h("button", { class: "btn small", onclick: async () => {
    try {
      if (window.ClipboardItem) {
        await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([a.html], { type: "text/html" }), "text/plain": new Blob([a.markdown], { type: "text/plain" }) })]);
      } else await navigator.clipboard.writeText(a.markdown);
      toast("Copied. Paste into Word or an email; formatting is kept.");
    } catch { toast("Your browser blocked copying. Use Download Word instead.", true); }
  } }, "Copy");
  const wordBtn = h("button", { class: "btn small primary", onclick: async (e) => {
    try { const r = await busy(e.currentTarget, "Preparing…", () => api("/api/notice/docx", { markdown: a.markdown, task: a.task, filename: N.data.filename }, { blob: true })); downloadBlob(r.blob, r.name); }
    catch (err) { toast(err.message, true); } } }, svg("dl"), "Download Word");
  const editBtn = h("button", { class: "btn small", onclick: async () => {
    if (N.editing && a.dirty) { a.html = (await api("/api/render", { markdown: a.markdown })).html; a.dirty = false; }
    N.editing = !N.editing; N.showMasked = false; renderNotice(); } }, N.editing ? "Done editing" : "Edit text");
  const maskBtn = h("button", { class: "btn small quiet", onclick: () => { N.showMasked = !N.showMasked; N.editing = false; renderNotice(); } },
    N.showMasked ? "Show final version" : "Show what the AI returned");

  const refineTa = h("textarea", { rows: 4, placeholder: N.answer.task === "draft"
    ? "e.g. Add a ground that ITC can't be denied only for supplier's default, citing the relevant circular. Make the prayer ask for a personal hearing."
    : "e.g. Put the amounts in a single table by financial year." });
  const refineBtn = h("button", { class: "btn primary", style: "width:100%" }, "Revise");
  const err = h("div");
  refineBtn.addEventListener("click", () => {
    if (!refineTa.value.trim()) return toast("Describe what to change.", true);
    ask(refineBtn, err, true, refineTa.value);
  });
  const other = a.task === "summary" ? "draft" : "summary";
  const side = h("aside", { class: "side-stack" },
    h("div", { class: "panel" }, h("h2", {}, "Ask for changes"), h("p", { class: "sub" }, "The model keeps the same notice and masking."), refineTa,
      h("div", { style: "margin-top:10px" }, refineBtn), err),
    h("div", { class: "panel" }, h("h2", {}, other === "draft" ? "Next: draft the reply" : "Need a summary?"),
      h("p", { class: "sub" }, other === "draft" ? "Add your facts and get a point-wise reply." : "Get the at-a-glance view of this notice."),
      h("button", { class: "btn", onclick: () => { N.task = other; N.step = 3; renderNotice(); } }, other === "draft" ? "Draft a reply" : "Summarise notice")),
    h("p", { class: "disclaimer" }, "AI output can be wrong. Check sections, dates, amounts and every citation against the notice and the law before filing. Highlighted [[…]] items need your input."));

  body.append(h("div", { class: "answer-wrap" },
    h("section", {},
      h("div", { class: "answer-tools" }, wordBtn, copyBtn, editBtn, maskBtn,
        h("span", { class: "meta" }, `${a.model}, ${a.seconds}s`)),
      sheet),
    side));
}

/* ======================================================= boot */

function route(view) {
  $$(".rail-link").forEach((b) => b.setAttribute("aria-current", b.dataset.view === view ? "page" : "false"));
  location.hash = view;
  (view === "pdf" ? renderPdf : renderNotice)();
}
$$(".rail-link").forEach((b) => b.addEventListener("click", () => route(b.dataset.view)));

(async () => {
  try { STATUS = await (await fetch("/api/status")).json(); } catch {}
  route(location.hash === "#pdf" ? "pdf" : "notice");
})();
