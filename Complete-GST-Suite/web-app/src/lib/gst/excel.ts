/**
 * Excel (ExcelJS, loaded on demand): read uploaded sheets, build the client workbook
 * (live difference formulas, navy headers, red/green conditional formatting, Indian number
 * format, frozen panes, filters, A4 landscape fit-to-width), the firm workbook and templates.
 */
import type * as ExcelJSTypes from "exceljs";
import type { Client, Notice } from "./demo";
import { MONTHS, fmtDate, monthLabel } from "./format";
import { HEADS, HEAD_LABEL, R_DEFS, R_IDS, TAX_HEADS, comparisons, gstr9, gstr9c, invoiceMatch, supplierSummary, threeWay, totalTax, type Gstr9cInputs, type Overrides } from "./recon";
import { noticeStatus } from "./notices";
import { CLIENT_TEMPLATE_HEADERS, GSTR3B_TEMPLATE_HEADERS, NOTICE_TEMPLATE_HEADERS, parseCsv, type Rows } from "./parsers";
import type { RunSummary } from "./recon";

type WB = ExcelJSTypes.Workbook;
type WS = ExcelJSTypes.Worksheet;

async function excel(): Promise<typeof ExcelJSTypes> {
  if (typeof window === "undefined") {
    // Node (tests / scripts) only — kept out of the bundle
    const name = "exceljs";
    const m = (await import(/* @vite-ignore */ name)) as { default?: typeof ExcelJSTypes } & typeof ExcelJSTypes;
    return m.default ?? m;
  }
  // the pre-built browser bundle avoids Node-only dependencies
  const mod = (await import("exceljs/dist/exceljs.min.js")) as unknown as { default?: typeof ExcelJSTypes } & typeof ExcelJSTypes;
  return mod.default ?? mod;
}

/** Indian digit grouping (12,34,567.89) with ₹. */
export const INR_FORMAT = '[>=10000000]"₹"##\\,##\\,##\\,##0.00;[>=100000]"₹"##\\,##\\,##0.00;"₹"##,##0.00';
const NAVY = "FF1F3864";
const RED_FILL = "FFFEE2E2";
const GREEN_FILL = "FFDCFCE7";
const AMBER_FILL = "FFFEF3C7";

/* ---------- reading ---------- */
export async function readSheetRows(file: File): Promise<Rows> {
  const name = file.name.toLowerCase();
  if (name.endsWith(".csv")) return parseCsv(await file.text());
  const ExcelJS = await excel();
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(await file.arrayBuffer());
  const ws = wb.worksheets[0];
  if (!ws) return [];
  const rows: Rows = [];
  ws.eachRow({ includeEmpty: true }, (row, n) => {
    const vals = (row.values as unknown[]).slice(1).map((v) => {
      if (v && typeof v === "object") {
        const o = v as { result?: unknown; text?: unknown; richText?: { text: string }[] };
        if (v instanceof Date) return v;
        if (o.result !== undefined) return o.result;
        if (o.richText) return o.richText.map((t) => t.text).join("");
        if (o.text !== undefined) return o.text;
      }
      return v ?? "";
    });
    rows[n - 1] = vals;
  });
  return Array.from(rows, (r) => r ?? []);
}

/* ---------- writing helpers ---------- */
function header(ws: WS, row: number, titles: string[]) {
  const r = ws.getRow(row);
  titles.forEach((t, i) => {
    const c = r.getCell(i + 1);
    c.value = t;
    c.font = { bold: true, color: { argb: "FFFFFFFF" } };
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: NAVY } };
    c.alignment = { vertical: "middle", horizontal: "center", wrapText: true };
  });
  r.height = 30;
}

function title(ws: WS, text: string, sub: string) {
  ws.getCell("A1").value = text;
  ws.getCell("A1").font = { bold: true, size: 14, color: { argb: NAVY } };
  ws.getCell("A2").value = sub;
  ws.getCell("A2").font = { italic: true, color: { argb: "FF64748B" } };
}

type Kind = "text" | "money";
function table(ws: WS, startRow: number, titles: string[], rows: (string | number | null | undefined)[][], kinds: Kind[]): number {
  header(ws, startRow, titles);
  rows.forEach((r, i) => {
    const row = ws.getRow(startRow + 1 + i);
    r.forEach((v, j) => {
      const c = row.getCell(j + 1);
      // data text that starts with "=" must stay text, never a formula
      c.value = typeof v === "string" && v.startsWith("=") ? " " + v : (v ?? null);
      if (kinds[j] === "money") c.numFmt = INR_FORMAT;
    });
  });
  titles.forEach((t, j) => {
    const money = kinds[j] === "money";
    const w = money ? 18 : Math.min(60, Math.max(10, t.length, ...rows.slice(0, 200).map((r) => String(r[j] ?? "").length)) + 2);
    ws.getColumn(j + 1).width = w;
  });
  return startRow + rows.length;
}

function finish(ws: WS, freezeRow: number, freezeCol: number, filter?: { from: string; to: string }) {
  ws.views = [{ state: "frozen", xSplit: freezeCol, ySplit: freezeRow }];
  if (filter) ws.autoFilter = filter;
  ws.pageSetup = { ...ws.pageSetup, orientation: "landscape", paperSize: 9, fitToPage: true, fitToWidth: 1, fitToHeight: 0 };
}

function diffRule(ws: WS, ref: string, tol: number) {
  ws.addConditionalFormatting({
    ref,
    rules: [
      { type: "cellIs", operator: "greaterThan", formulae: [String(tol)], priority: 1, style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: RED_FILL } }, font: { color: { argb: "FFB91C1C" }, bold: true } } },
      { type: "cellIs", operator: "lessThan", formulae: [String(-tol)], priority: 2, style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: RED_FILL } }, font: { color: { argb: "FFB91C1C" }, bold: true } } },
      { type: "cellIs", operator: "between", formulae: [String(-tol), String(tol)], priority: 3, style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: GREEN_FILL } }, font: { color: { argb: "FF166534" } } } },
    ],
  });
}
function statusRule(ws: WS, ref: string) {
  const fill = (argb: string) => ({ fill: { type: "pattern" as const, pattern: "solid" as const, bgColor: { argb } } });
  ws.addConditionalFormatting({
    ref,
    rules: [
      { type: "containsText", operator: "containsText", text: "Difference", priority: 1, style: fill(RED_FILL) },
      { type: "containsText", operator: "containsText", text: "Partial", priority: 2, style: fill(AMBER_FILL) },
      { type: "containsText", operator: "containsText", text: "Matched", priority: 3, style: fill(GREEN_FILL) },
      { type: "containsText", operator: "containsText", text: "Overdue", priority: 4, style: fill(RED_FILL) },
      { type: "containsText", operator: "containsText", text: "Due soon", priority: 5, style: fill(AMBER_FILL) },
      { type: "containsText", operator: "containsText", text: "Only in", priority: 6, style: fill(RED_FILL) },
      { type: "containsText", operator: "containsText", text: "Mismatch", priority: 7, style: fill(RED_FILL) },
    ],
  });
}
const col = (n: number) => {
  let s = "";
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
};

export interface ClientWorkbookInput {
  client: Client;
  firmName: string;
  tolerance: number;
  dueSoonDays: number;
  notices: Notice[];
  overrides9: Overrides;
  overrides9c: Overrides;
  inputs9c: Gstr9cInputs;
  reasons: Record<string, string>;
  summary?: RunSummary | undefined;
}

/** One workbook per client with all working-paper sheets. */
export async function buildClientWorkbook(p: ClientWorkbookInput): Promise<Blob> {
  const ExcelJS = await excel();
  const wb: WB = new ExcelJS.Workbook();
  wb.creator = "Complete GST Suite";
  const { client: c, tolerance: tol } = p;
  const sub = `${c.name} · GSTIN ${c.gstin} · FY 2025-26 · ${p.firmName} · generated ${new Date().toLocaleString("en-IN")}`;
  const comps = comparisons(c.id, tol);

  // Dashboard
  let ws = wb.addWorksheet("Dashboard");
  title(ws, "GST Reconciliation Dashboard", sub);
  const s = p.summary;
  table(ws, 4, ["Key figure", "Value"], [
    ["Tax difference (GSTR-3B vs books)", s?.netTaxDiff ?? 0], ["ITC at risk", s?.itcAtRisk ?? 0], ["DRC-03 payable", s?.drc03 ?? 0], ["Interest u/s 50 (estimate)", s?.interest ?? 0],
    ["Partial data months", s?.partialMonths.map(monthLabel).join(", ") || "None"],
  ], ["text", "money"]);
  const end = table(ws, 11, ["#", "Reconciliation", "Side A tax", "Side B tax", "Difference (A − B)", "Months with difference", "What it means"],
    comps.map((cp) => {
      const dm = cp.rows.filter((r) => r.status === "Difference").map((r) => monthLabel(r.month));
      return [cp.id, cp.title, totalTax(cp.total.a), totalTax(cp.total.b), null, dm.join(", ") || "-", dm.length ? (totalTax(cp.total.diff) > 0 ? R_DEFS[cp.id].pos : R_DEFS[cp.id].neg) : "Matched"];
    }), ["text", "text", "money", "money", "money", "text", "text"]);
  for (let r = 12; r <= end; r++) ws.getCell(`E${r}`).value = { formula: `C${r}-D${r}` };
  diffRule(ws, `E12:E${end}`, tol);
  ws.getColumn(1).width = 32;
  ws.getColumn(7).width = 70;
  finish(ws, 4, 0);

  // 3-way sheets
  for (const [kind, name, first] of [["sales", "Sales 3-Way", "GSTR-1"], ["itc", "ITC 3-Way", "GSTR-2B"]] as const) {
    ws = wb.addWorksheet(name);
    title(ws, `${name} — Books | ${first} | GSTR-3B (total tax and taxable value)`, sub);
    const rows = threeWay(c.id, kind, tol);
    const e = table(ws, 4, ["Month", "Books taxable", "Books tax", `${first} taxable`, `${first} tax`, "GSTR-3B taxable", "GSTR-3B tax", `${first} − Books (tax)`, `3B − ${first} (tax)`, "3B − Books (tax)", "Status", "What it means"],
      rows.map((r) => [monthLabel(r.month), r.books.taxable, totalTax(r.books), r.first.taxable, totalTax(r.first), r.r3b.taxable, totalTax(r.r3b), null, null, null, r.status, r.meaning]),
      ["text", "money", "money", "money", "money", "money", "money", "money", "money", "money", "text", "text"]);
    for (let i = 5; i <= e; i++) {
      ws.getCell(`H${i}`).value = { formula: `E${i}-C${i}` };
      ws.getCell(`I${i}`).value = { formula: `G${i}-E${i}` };
      ws.getCell(`J${i}`).value = { formula: `G${i}-C${i}` };
    }
    const t = e + 1;
    ws.getCell(`A${t}`).value = "Total";
    ws.getCell(`A${t}`).font = { bold: true };
    for (const k of "BCDEFGHIJ") {
      ws.getCell(`${k}${t}`).value = { formula: `SUM(${k}5:${k}${e})` };
      ws.getCell(`${k}${t}`).numFmt = INR_FORMAT;
      ws.getCell(`${k}${t}`).font = { bold: true };
    }
    diffRule(ws, `H5:J${t}`, tol);
    statusRule(ws, `K5:K${e}`);
    ws.getColumn(12).width = 80;
    finish(ws, 4, 1, { from: "A4", to: `L${e}` });
  }

  // R1–R6 with live difference formulas
  for (const cp of comps) {
    ws = wb.addWorksheet(cp.id);
    const heads = cp.taxOnly ? [...TAX_HEADS] : [...HEADS];
    const n = heads.length;
    title(ws, `${cp.id}: ${cp.title} (Difference = ${cp.sideA} − ${cp.sideB})`, sub);
    const titles = ["Month", ...heads.map((h) => `${cp.sideA} ${HEAD_LABEL[h]}`), ...heads.map((h) => `${cp.sideB} ${HEAD_LABEL[h]}`), ...heads.map((h) => `Diff ${HEAD_LABEL[h]}`), "Total tax diff", "Status", "What it means"];
    const e = table(ws, 4, titles, cp.rows.map((r) => [monthLabel(r.month), ...heads.map((h) => r.a[h]), ...heads.map((h) => r.b[h]), ...heads.map(() => null), null, r.status === "Partial data" ? "Partial data" : null, r.meaning]),
      ["text", ...Array(3 * n + 1).fill("money"), "text", "text"] as Kind[]);
    const taxCols = heads.map((h, j) => (h === "taxable" ? null : col(2 + 2 * n + j))).filter(Boolean) as string[];
    const tcol = col(2 + 3 * n);
    const scol = col(3 + 3 * n);
    for (let i = 5; i <= e; i++) {
      for (let j = 0; j < n; j++) ws.getCell(`${col(2 + 2 * n + j)}${i}`).value = { formula: `${col(2 + j)}${i}-${col(2 + n + j)}${i}` };
      ws.getCell(`${tcol}${i}`).value = { formula: taxCols.map((k) => `${k}${i}`).join("+") };
      if (!ws.getCell(`${scol}${i}`).value) ws.getCell(`${scol}${i}`).value = { formula: `IF(ABS(${tcol}${i})>${tol},"Difference","Matched")` };
    }
    const t = e + 1;
    ws.getCell(`A${t}`).value = "Total";
    ws.getCell(`A${t}`).font = { bold: true };
    for (let j = 2; j <= 2 + 3 * n; j++) {
      const k = col(j);
      ws.getCell(`${k}${t}`).value = { formula: `SUM(${k}5:${k}${e})` };
      ws.getCell(`${k}${t}`).numFmt = INR_FORMAT;
      ws.getCell(`${k}${t}`).font = { bold: true };
    }
    diffRule(ws, `${col(2 + 2 * n)}5:${tcol}${t}`, tol);
    statusRule(ws, `${scol}5:${scol}${e}`);
    ws.getColumn(4 + 3 * n).width = 70;
    finish(ws, 4, 1, { from: "A4", to: `${col(4 + 3 * n)}${e}` });
  }

  // invoice matching
  for (const [side, name] of [["sales", "Inv Match – Sales"], ["itc", "Inv Match – ITC"]] as const) {
    ws = wb.addWorksheet(name);
    title(ws, name, sub);
    const rows = invoiceMatch(c.id, side, tol);
    const e = table(ws, 4, ["Result", "Party", "GSTIN", "Books inv no", "Return inv no", "Books date", "Return date", "Books month", "Return month", "Books taxable", "Return taxable", "Books tax", "Return tax", "Tax difference"],
      rows.map((r) => { const i = (r.books ?? r.ret)!; return [r.kind, i.party, i.gstin, r.books?.no ?? "", r.ret?.no ?? "", r.books ? fmtDate(r.books.date) : "", r.ret?.date ? fmtDate(r.ret.date) : "", r.books ? monthLabel(r.books.month) : "", r.ret ? monthLabel(r.ret.month) : "", r.books?.taxable ?? null, r.ret?.taxable ?? null, r.books ? totalTax(r.books) : 0, r.ret ? totalTax(r.ret) : 0, null]; }),
      ["text", "text", "text", "text", "text", "text", "text", "text", "text", "money", "money", "money", "money", "money"]);
    for (let i = 5; i <= e; i++) ws.getCell(`N${i}`).value = { formula: `L${i}-M${i}` };
    diffRule(ws, `N5:N${Math.max(e, 5)}`, tol);
    statusRule(ws, `A5:A${Math.max(e, 5)}`);
    finish(ws, 4, 1, { from: "A4", to: `N${Math.max(e, 5)}` });
  }

  // supplier follow-up
  ws = wb.addWorksheet("Supplier Follow-up");
  title(ws, "Supplier-wise ITC at risk (Only in Books + Value Mismatch), largest first", sub);
  const sup = supplierSummary(c.id, tol);
  const se = table(ws, 4, ["Supplier", "GSTIN", "Issue", "Invoice no", "Date", "Taxable (books)", "GST (books)", "GST in GSTR-2B"],
    sup.flatMap((g) => g.rows.map((r) => [g.party, g.gstin, r.kind, r.books!.no, fmtDate(r.books!.date), r.books!.taxable, totalTax(r.books!), r.ret ? totalTax(r.ret) : 0])),
    ["text", "text", "text", "text", "text", "money", "money", "money"]);
  ws.getCell(`A${se + 1}`).value = "Total GST of listed invoices";
  ws.getCell(`G${se + 1}`).value = { formula: se >= 5 ? `SUM(G5:G${se})` : "0" };
  ws.getCell(`G${se + 1}`).numFmt = INR_FORMAT;
  ws.getRow(se + 1).font = { bold: true };
  finish(ws, 4, 1, { from: "A4", to: `H${Math.max(se, 5)}` });

  // GSTR-9
  ws = wb.addWorksheet("GSTR-9");
  title(ws, "GSTR-9 draft (by table number)", sub);
  const g9 = gstr9(c.id, p.overrides9);
  const g9e = table(ws, 4, ["Table", "Particulars", "Taxable", "IGST", "CGST", "SGST", "Cess", "Source", "Note / reason"],
    g9.map((l) => [l.id, l.label, ...HEADS.map((h) => (l.heads.includes(h) ? l.v[h] : null)), l.overridden.length ? "Manual override" : l.source, [l.note, p.reasons[`${c.id}|GSTR-9:${l.id}`]].filter(Boolean).join(" · ")]),
    ["text", "text", "money", "money", "money", "money", "money", "text", "text"]);
  g9.forEach((l, i) => l.overridden.forEach((h) => { ws.getCell(`${col(3 + HEADS.indexOf(h))}${5 + i}`).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFEF08A" } }; }));
  ws.getColumn(2).width = 60;
  ws.getColumn(9).width = 60;
  finish(ws, 4, 2, { from: "A4", to: `I${g9e}` });

  // GSTR-9C
  ws = wb.addWorksheet("GSTR-9C");
  title(ws, "GSTR-9C draft (reconciliation statement)", sub);
  const c9 = gstr9c(c.id, p.inputs9c, p.overrides9c, p.overrides9);
  const c9e = table(ws, 4, ["Table", "Particulars", "Amount / Taxable", "IGST", "CGST", "SGST", "Cess", "Source", "Reason (if unreconciled)"],
    c9.map((l) => [l.id, l.label, ...HEADS.map((h) => (l.heads.includes(h) ? l.v[h] : null)), l.source, [l.note, p.reasons[`${c.id}|GSTR-9C:${l.id}`]].filter(Boolean).join(" · ")]),
    ["text", "text", "money", "money", "money", "money", "money", "text", "text"]);
  ws.getColumn(2).width = 60;
  ws.getColumn(9).width = 50;
  finish(ws, 4, 2, { from: "A4", to: `I${c9e}` });

  // Notices
  ws = wb.addWorksheet("Notices");
  title(ws, "GST notices", sub);
  const ne = table(ws, 4, ["Status", "Form", "Nature", "Reference", "Tax period", "Issued", "Reply due", "Days left", "Priority", "Action required", "Portal status", "Source", "Assigned to", "Internal status", "Amount", "Notes"],
    p.notices.map((n) => [noticeStatus(n, new Date(), p.dueSoonDays), n.form, n.subject, n.ref, n.taxPeriod, fmtDate(n.issued), fmtDate(n.due), Math.round((new Date(n.due).getTime() - Date.now()) / 86400000), n.priority, n.action, n.portalStatus, n.source, n.assignedTo, n.status, n.amount, n.notes]),
    ["text", "text", "text", "text", "text", "text", "text", "text", "text", "text", "text", "text", "text", "text", "money", "text"]);
  statusRule(ws, `A5:A${Math.max(ne, 5)}`);
  finish(ws, 4, 2, { from: "A4", to: `P${Math.max(ne, 5)}` });

  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export interface FirmRow {
  client: Client;
  status: string;
  route: string;
  summary?: RunSummary | undefined;
  openNotices: number;
  overdue: number;
  lastRun: string;
}

export async function buildFirmWorkbook(firmName: string, rows: FirmRow[], notices: (Notice & { clientName: string })[], tol: number, dueSoonDays: number): Promise<Blob> {
  const ExcelJS = await excel();
  const wb = new ExcelJS.Workbook();
  let ws = wb.addWorksheet("Firm Dashboard");
  title(ws, "Firm dashboard — FY 2025-26", `${firmName} · generated ${new Date().toLocaleString("en-IN")}`);
  const e = table(ws, 4, ["Client", "GSTIN", "Staff", "Data source used", "Status", ...R_IDS.map((r) => `${r} year diff`), "ITC at risk", "DRC-03 payable", "Open notices", "Overdue notices", "Last run"],
    rows.map((r) => [r.client.name, r.client.gstin, r.client.staff, r.route, r.status, ...R_IDS.map((k) => r.summary?.yearDiff[k] ?? null), r.summary?.itcAtRisk ?? null, r.summary?.drc03 ?? null, r.openNotices, r.overdue, r.lastRun]),
    ["text", "text", "text", "text", "text", ...R_IDS.map(() => "money" as Kind), "money", "money", "text", "text", "text"]);
  const t = e + 1;
  ws.getCell(`A${t}`).value = "Total";
  for (const k of ["F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]) {
    ws.getCell(`${k}${t}`).value = { formula: `SUM(${k}5:${k}${e})` };
    if ("FGHIJKLM".includes(k)) ws.getCell(`${k}${t}`).numFmt = INR_FORMAT;
  }
  ws.getRow(t).font = { bold: true };
  diffRule(ws, `F5:K${Math.max(e, 5)}`, tol);
  statusRule(ws, `E5:E${Math.max(e, 5)}`);
  finish(ws, 4, 1, { from: "A4", to: `P${Math.max(e, 5)}` });
  ws = wb.addWorksheet("Notices");
  title(ws, "All notices", "");
  const ne = table(ws, 4, ["Status", "Client", "GSTIN", "Form", "Nature", "Reference", "Reply due", "Priority", "Assigned to", "Internal status"],
    notices.map((n) => [noticeStatus(n, new Date(), dueSoonDays), n.clientName, n.gstin, n.form, n.subject, n.ref, fmtDate(n.due), n.priority, n.assignedTo, n.status]),
    Array(10).fill("text") as Kind[]);
  statusRule(ws, `A5:A${Math.max(ne, 5)}`);
  finish(ws, 4, 2, { from: "A4", to: `J${Math.max(ne, 5)}` });
  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

/** Simple export of any on-screen table. */
export async function buildTableWorkbook(sheet: string, titles: string[], rows: (string | number | null)[][], kinds: Kind[]): Promise<Blob> {
  const ExcelJS = await excel();
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(sheet.slice(0, 31).replace(/[\\/?*[\]:]/g, "-") || "Export");
  const e = table(ws, 1, titles, rows, kinds);
  finish(ws, 1, 0, { from: "A1", to: `${col(titles.length)}${Math.max(e, 1)}` });
  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export type TemplateKind = "client-master" | "gstr3b-summary" | "notices";
export const TEMPLATE_NAMES: Record<TemplateKind, string> = {
  "client-master": "Client_Master_Template.xlsx",
  "gstr3b-summary": "GSTR3B_12_Month_Summary_Template.xlsx",
  notices: "Manual_Notices_Template.xlsx",
};

export async function buildTemplate(kind: TemplateKind): Promise<Blob> {
  const ExcelJS = await excel();
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("Template");
  if (kind === "client-master") {
    table(ws, 1, CLIENT_TEMPLATE_HEADERS, [["Shree Ganesh Traders", "Shree Ganesh Traders", "24ABCDE1234F1Z6", "shreeganesh_gst", "4421", "accounts@shreeganesh.in", "Monthly", "2025-26", "Shree Ganesh Traders 25-26", "Yes", "31-03-2026", "Riya Shah", "Yes", "Yes", "Yes", "Auto", "Example row — delete before import"]], CLIENT_TEMPLATE_HEADERS.map(() => "text"));
    const help = wb.addWorksheet("Instructions");
    ["* = required. GSTIN is checked (format and check digit). Duplicate GSTINs are rejected.", "Return Frequency: Monthly or QRMP. Data Source: Auto, GSP API or Downloaded files.", "API Access Enabled / Fetch Returns / Fetch Notices / Active: Yes or No.", "There is NO password column: portal access is only through a GSP using the client's OTP."]
      .forEach((t, i) => { help.getCell(`A${i + 1}`).value = t; });
    help.getColumn(1).width = 110;
    ws.views = [{ state: "frozen", ySplit: 1 }];
  } else if (kind === "gstr3b-summary") {
    ws.getCell("A1").value = "GSTIN";
    ws.getCell("A1").font = { bold: true };
    ws.getCell("C1").value = "← enter the client GSTIN in B1. Table 3.1(a) = outward taxable supplies; Table 4(C) = net ITC available.";
    table(ws, 3, GSTR3B_TEMPLATE_HEADERS, MONTHS.map((m) => [monthLabel(m), null, null, null, null, null, null, null, null, null]), ["text", ...Array(9).fill("money")] as Kind[]);
    ws.views = [{ state: "frozen", ySplit: 3 }];
  } else {
    table(ws, 1, NOTICE_TEMPLATE_HEADERS, [["24ABCDE1234F1Z6", "ASMT-10", "ZA2409250012345", "FY 2024-25", "15-10-2025", "14-11-2025", "Scrutiny of returns", "High", "Riya Shah", 0, "Example row — delete before upload"]], NOTICE_TEMPLATE_HEADERS.map((h) => (h === "Amount" ? "money" : "text")));
    ws.views = [{ state: "frozen", ySplit: 1 }];
  }
  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export function downloadBlob(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function downloadCsv(name: string, titles: string[], rows: (string | number | null)[][]) {
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = "﻿" + [titles, ...rows].map((r) => r.map(esc).join(",")).join("\r\n");
  downloadBlob(name, new Blob([csv], { type: "text/csv;charset=utf-8" }));
}
