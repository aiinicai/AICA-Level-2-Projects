import { ReactNode } from "react";
import { Card, cn } from "@/components/ui";
import { formatDate, formatINR } from "@/lib/format";
import { sheetFromAoa, writeWorkbook, workbookBlob, safeFileName } from "@/lib/export";
const NOTE = "Prepared from the books of account and the information and explanations given; verify before reporting in Form 3CD.";

export function SubTabs<T extends string>({ tabs, value, onChange }: { tabs: [T, string, ReactNode?][]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
      {tabs.map(([k, l, badge]) => (
        <button key={k} onClick={() => onChange(k)} className={cn("flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium", value === k ? "bg-white text-navy-900 shadow-sm" : "text-slate-600")}>
          {l}{badge}
        </button>
      ))}
    </div>
  );
}

export type Col = { label: string; num?: boolean; date?: boolean };
export type Cellv = string | number | null | undefined;

/** A prescribed-format table with a heading, shown on screen and reused for Excel export. */
export function ReportTable({ id, title, subtitle, cols, rows, footer, empty = "Nil" }: { id?: string; title: string; subtitle?: string; cols: Col[]; rows: Cellv[][]; footer?: Cellv[]; empty?: string }) {
  return (
    <Card className="overflow-hidden" >
      <div id={id} className="border-b border-slate-100 px-5 py-3">
        <h3 className="font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
      {rows.length === 0 ? <p className="px-5 py-4 text-sm text-slate-500">{empty}</p> : (
        <div className="overflow-x-auto">
          <table className="table-pro">
            <thead><tr><th className="w-10">Sr.</th>{cols.map((c) => <th key={c.label} className={c.num ? "text-right" : ""}>{c.label}</th>)}</tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}><td className="text-xs text-slate-400">{i + 1}</td>{r.map((v, j) => <td key={j} className={cols[j]?.num ? "num" : ""}>{fmt(v, cols[j])}</td>)}</tr>
              ))}
              {footer && <tr className="bg-slate-50 font-semibold"><td></td>{footer.map((v, j) => <td key={j} className={cols[j]?.num ? "num" : ""}>{fmt(v, cols[j])}</td>)}</tr>}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function fmt(v: Cellv, c?: Col) {
  if (v === null || v === undefined || v === "") return "";
  if (c?.num && typeof v === "number") return formatINR(v, { symbol: false });
  if (c?.date && typeof v === "string") return formatDate(v);
  return v;
}

export function Kpi({ label, value, tone }: { label: string; value: ReactNode; tone?: "bad" | "warn" | "good" | "navy" }) {
  return (
    <div className={cn("rounded-xl border p-4", tone === "bad" ? "border-red-200 bg-red-50" : tone === "warn" ? "border-amber-200 bg-amber-50" : tone === "good" ? "border-emerald-200 bg-emerald-50" : tone === "navy" ? "border-navy-950 bg-navy-950 text-white" : "border-slate-200 bg-white")}>
      <div className={cn("text-xs font-medium uppercase tracking-wide", tone === "navy" ? "text-navy-200" : "text-slate-500")}>{label}</div>
      <div className="mt-1 text-lg font-bold tabular-nums">{value}</div>
    </div>
  );
}

export interface ExportSection { sheet: string; title: string; cols: Col[]; rows: Cellv[][]; footer?: Cellv[] }

/** One workbook: a sheet per section, each with the assessee header, the table and the verification note. */
export function exportClauseWorkbook(fileBase: string, meta: { client: string; pan: string | null; ay: string; firm?: string }, sections: ExportSection[]): void;
export function exportClauseWorkbook(fileBase: string, meta: { client: string; pan: string | null; ay: string; firm?: string }, sections: ExportSection[], asFile: true): { blob: Blob; fileName: string };
export function exportClauseWorkbook(fileBase: string, meta: { client: string; pan: string | null; ay: string; firm?: string }, sections: ExportSection[], asFile?: boolean) {
  const sheets = sections.map((s) => {
    const aoa: Cellv[][] = [
      [meta.firm ?? ""], ["Name of assessee", meta.client], ["PAN", meta.pan ?? ""], ["Assessment year", meta.ay], [],
      [s.title], [],
      ["Sr.", ...s.cols.map((c) => c.label)],
      ...s.rows.map((r, i) => [i + 1, ...r.map((v, j) => (s.cols[j]?.date && typeof v === "string" && v ? formatDate(v) : v ?? ""))]),
    ];
    if (s.footer) aoa.push(["", ...s.footer.map((v) => v ?? "")]);
    if (!s.rows.length) aoa.push(["", "Nil"]);
    aoa.push([], [NOTE], ["Prepared using 3CD Helper – subject to verification by the auditor."]);
    return { name: s.sheet, ws: sheetFromAoa(aoa as (string | number | null)[][], [6, ...s.cols.map((c) => (c.num ? 16 : c.date ? 12 : 28))]) };
  });
  const fileName = `${fileBase}_${safeFileName(meta.client)}_AY${meta.ay}.xlsx`;
  if (asFile) return { blob: workbookBlob(sheets), fileName };
  writeWorkbook(sheets, fileName);
}
