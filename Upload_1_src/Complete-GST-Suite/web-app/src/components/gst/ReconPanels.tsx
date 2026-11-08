import { useMemo, useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Money, Panel, StatusBadge, Term, openDrill, type DrillRow } from "./common";
import { DataTable, type Column } from "./DataTable";
import { getClientData } from "@/lib/gst/demo";
import { fmtDate, inr, monthLabel } from "@/lib/gst/format";
import { HEADS, HEAD_LABEL, MATCH_KINDS, R_DEFS, comparisons, invoiceMatch, invoicesFor, threeWay, totalTax, type Comparison, type MatchKind, type MatchRow, type RId } from "@/lib/gst/recon";
import { setReview, useApp, useDataVersion } from "@/lib/store";
import { cn } from "@/lib/utils";

const diffCls = (v: number, tol = 1) => (Math.abs(v) > tol ? "font-medium text-destructive bg-destructive/5" : "text-muted-foreground");
const matchNote = (r: MatchRow) => (r.kind === "Matched" ? undefined : r.kind);
const lakh = (v: number) => "₹" + (v / 100000).toFixed(1) + "L";
const chartTip = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 };

async function exportGrid(name: string, titles: string[], rows: (string | number | null)[][], money: boolean[]) {
  const x = await import("@/lib/gst/excel");
  x.downloadBlob(`${name}.xlsx`, await x.buildTableWorkbook(name, titles, rows, money.map((m) => (m ? "money" : "text"))));
}

/** Invoices behind one month of one check, both sides. */
function monthDrill(clientId: string, comp: Comparison, m: string, tol: number) {
  const a = invoicesFor(clientId, comp.sourceA, m) ?? [];
  const b = invoicesFor(clientId, comp.sourceB, m) ?? [];
  const rows: DrillRow[] = [...a.map((i) => ({ ...i, note: comp.sideA })), ...b.map((i) => ({ ...i, note: comp.sideB }))];
  const row = comp.rows.find((r) => r.month === m)!;
  const only3b = comp.sourceA === "gstr3b" || comp.sourceB === "gstr3b";
  openDrill(`${comp.id} · ${monthLabel(m)} — invoices behind this month`, rows, `${comp.sideA} ${inr(totalTax(row.a))} vs ${comp.sideB} ${inr(totalTax(row.b))} · ${Math.abs(totalTax(row.diff)) > tol ? row.meaning : "matched"}${only3b ? " · GSTR-3B is a summary return (no invoice rows)" : ""}`);
}

/* ---------- Three-way view ---------- */
export function ThreeWay({ clientId }: { clientId: string }) {
  const [kind, setKind] = useState<"sales" | "itc">("sales");
  const tol = useApp((s) => s.prefs.tolerance);
  const v = useDataVersion();
  const rows = useMemo(() => threeWay(clientId, kind, tol), [clientId, kind, tol, v]);
  const cd = getClientData(clientId);
  const firstLabel = kind === "sales" ? "GSTR-1" : "GSTR-2B";
  const labels = kind === "sales" ? ["GSTR-1 − Books (R3)", "3B − GSTR-1 (−R1)", "3B − Books (R2)"] : ["2B − Books (R4)", "3B − 2B (−R5)", "3B − Books (R6)"];

  const monthRows = (m: string): DrillRow[] => {
    const match = invoiceMatch(clientId, kind, tol).filter((r) => r.books?.month === m || r.ret?.month === m);
    const list: DrillRow[] = match.map((r) => ({ ...(r.books ?? r.ret)!, note: matchNote(r) }));
    if (kind === "sales") list.push(...cd.sales.filter((i) => i.month === m && i.type === "B2CS").map((i) => ({ ...i, note: "B2C (checked in total)" })));
    return list;
  };
  const chart = rows.map((r) => ({ month: monthLabel(r.month), Books: totalTax(r.books), [firstLabel]: r.partial && totalTax(r.first) === 0 ? null : totalTax(r.first), "GSTR-3B": totalTax(r.r3b) }));
  const sum = (f: (r: (typeof rows)[number]) => number) => rows.reduce((s, r) => s + f(r), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-md border p-0.5" role="tablist">
          {(["sales", "itc"] as const).map((k) => (
            <button key={k} role="tab" aria-selected={kind === k} onClick={() => setKind(k)} className={cn("rounded px-4 py-1.5 text-sm", kind === k ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
              {k === "sales" ? "Sales (output tax)" : "Purchases (ITC)"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <p className="text-sm text-muted-foreground"><Term k="Three-way view">{kind === "sales" ? "Books | GSTR-1 | GSTR-3B" : "Books | GSTR-2B | GSTR-3B"} — total tax per month</Term></p>
          <Button size="sm" variant="outline" onClick={() => void exportGrid(`${clientId}_${kind}_3way`, ["Month", "Books", firstLabel, "GSTR-3B", ...labels, "Status", "What it means"], rows.map((r) => [monthLabel(r.month), totalTax(r.books), totalTax(r.first), totalTax(r.r3b), r.d1, r.d2, r.d3, r.status, r.meaning]), [false, true, true, true, true, true, true, false, false])}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> Excel
          </Button>
        </div>
      </div>

      <Panel title={`${kind === "sales" ? "Sales" : "ITC"} three-way reconciliation`}>
        <div className="max-h-[70vh] overflow-auto">
          <table className="w-full min-w-[1000px] text-sm">
            <thead className="sticky top-0 z-10 bg-card text-left text-xs text-muted-foreground">
              <tr className="border-b">
                <th className="py-2 pr-2 font-medium">Month</th>
                <th className="py-2 pr-2 text-right font-medium"><Term k="Books" /></th>
                <th className="py-2 pr-2 text-right font-medium"><Term k={firstLabel} /></th>
                <th className="py-2 pr-2 text-right font-medium"><Term k={kind === "sales" ? "Table 3.1(a)" : "Table 4(C)"}>GSTR-3B</Term></th>
                {labels.map((l) => <th key={l} className="py-2 pr-2 text-right font-medium">{l}</th>)}
                <th className="py-2 pr-2 font-medium">Status</th>
                <th className="py-2 font-medium">What it means</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.month} tabIndex={0} className="cursor-pointer border-b align-top last:border-0 hover:bg-accent/40" onKeyDown={(e) => e.key === "Enter" && openDrill(`${monthLabel(r.month)} — invoices`, monthRows(r.month))} onClick={() => openDrill(`${monthLabel(r.month)} — ${kind === "sales" ? "sales invoices: books vs GSTR-1" : "purchase invoices: books vs GSTR-2B"}`, monthRows(r.month))}>
                  <td className="whitespace-nowrap py-2 pr-2 font-medium text-primary underline decoration-dotted underline-offset-4">{monthLabel(r.month)}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right tabular-nums">{inr(totalTax(r.books))}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right tabular-nums">{r.partial && totalTax(r.first) === 0 ? <span className="text-muted-foreground">Not available</span> : inr(totalTax(r.first))}</td>
                  <td className="whitespace-nowrap py-2 pr-2 text-right tabular-nums">{inr(totalTax(r.r3b))}</td>
                  {[r.d1, r.d2, r.d3].map((d, i) => <td key={i} className={cn("whitespace-nowrap py-2 pr-2 text-right tabular-nums", diffCls(r.partial ? 0 : d, tol))}>{inr(d)}</td>)}
                  <td className="py-2 pr-2"><StatusBadge status={r.status} /></td>
                  <td className="max-w-sm py-2 text-xs leading-relaxed text-muted-foreground">{r.meaning}</td>
                </tr>
              ))}
              <tr className="border-t-2 font-semibold">
                <td className="py-2 pr-2">Total</td>
                {[sum((r) => totalTax(r.books)), sum((r) => totalTax(r.first)), sum((r) => totalTax(r.r3b)), sum((r) => r.d1), sum((r) => r.d2), sum((r) => r.d3)].map((v2, i) => <td key={i} className="whitespace-nowrap py-2 pr-2 text-right tabular-nums">{inr(v2)}</td>)}
                <td colSpan={2} />
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Click any month to see the invoices behind it. GSTR-2B rows count in their 2B return period. Differences within ₹{tol} are treated as rounding.</p>
      </Panel>

      <Panel title="Books vs returns — month by month">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart} margin={{ left: 10, right: 10, top: 5 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
              <YAxis tickFormatter={lakh} tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} width={60} />
              <RTooltip formatter={(x) => inr(Number(x))} contentStyle={chartTip} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="Books" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey={firstLabel} stroke="var(--chart-2)" strokeWidth={2} dot={false} strokeDasharray="5 4" />
              <Line type="monotone" dataKey="GSTR-3B" stroke="var(--chart-4)" strokeWidth={2} dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

/* ---------- R1–R6: month × head grid (A, B, Difference) ---------- */
export function ComparisonPanel({ clientId, comp }: { clientId: string; comp: Comparison }) {
  const tol = useApp((s) => s.prefs.tolerance);
  const heads = comp.taxOnly ? HEADS.filter((h) => h !== "taxable") : HEADS;
  const nDiff = comp.rows.filter((r) => r.status === "Difference").length;
  const chart = comp.rows.map((r) => ({ month: monthLabel(r.month), key: r.month, diff: totalTax(r.diff), partial: r.status === "Partial data" }));
  const exportIt = () =>
    void exportGrid(`${clientId}_${comp.id}`, ["Month", ...heads.flatMap((h) => [`${comp.sideA} ${HEAD_LABEL[h]}`, `${comp.sideB} ${HEAD_LABEL[h]}`, `Diff ${HEAD_LABEL[h]}`]), "Total tax diff", "Status", "What it means"],
      comp.rows.map((r) => [monthLabel(r.month), ...heads.flatMap((h) => [r.a[h], r.b[h], r.diff[h]]), totalTax(r.diff), r.status, r.meaning]),
      [false, ...heads.flatMap(() => [true, true, true]), true, false, false]);
  return (
    <div className="space-y-6">
      <Panel
        title={<Term k={comp.id}>{comp.id} · {comp.title}</Term>}
        actions={<div className="flex items-center gap-2"><StatusBadge status={nDiff ? "Difference" : comp.rows.some((r) => r.status === "Partial data") ? "Partial data" : "Matched"} label={nDiff ? `${nDiff} month(s) differ` : undefined} /><Button size="sm" variant="outline" onClick={exportIt}><Download className="mr-1.5 h-3.5 w-3.5" /> Excel</Button></div>}
      >
        <div className="mb-3 grid gap-1 text-xs text-muted-foreground md:grid-cols-2">
          <p><span className="font-medium text-foreground">A</span> = {comp.sideA} · <span className="font-medium text-foreground">B</span> = {comp.sideB} · Difference = A − B · tolerance ₹{tol}</p>
          <p><span className="text-destructive">+</span> {comp.pos} · <span className="text-destructive">−</span> {comp.neg}</p>
        </div>
        <div className="max-h-[70vh] overflow-auto">
          <table className="w-full min-w-[1200px] text-sm">
            <thead className="sticky top-0 z-10 bg-card text-xs text-muted-foreground">
              <tr className="border-b">
                <th rowSpan={2} className="py-2 pr-2 text-left font-medium">Month</th>
                {heads.map((h) => <th key={h} colSpan={3} className="border-l px-2 py-1 text-center font-medium"><Term k={h === "taxable" ? "Taxable value" : HEAD_LABEL[h]}>{HEAD_LABEL[h]}</Term></th>)}
                <th rowSpan={2} className="border-l px-2 py-2 text-right font-medium">Total tax diff</th>
                <th rowSpan={2} className="px-2 py-2 text-left font-medium">Status</th>
                <th rowSpan={2} className="py-2 text-left font-medium">What it means</th>
              </tr>
              <tr className="border-b">
                {heads.map((h) => ["A", "B", "Diff"].map((x) => <th key={h + x} className={cn("px-2 py-1 text-right font-medium", x === "A" && "border-l")}>{x}</th>))}
              </tr>
            </thead>
            <tbody>
              {comp.rows.map((r) => (
                <tr key={r.month} className="border-b align-top last:border-0 hover:bg-accent/30">
                  <td className="whitespace-nowrap py-2 pr-2"><button className="font-medium text-primary underline decoration-dotted underline-offset-4" onClick={() => monthDrill(clientId, comp, r.month, tol)}>{monthLabel(r.month)}</button></td>
                  {heads.map((h) => (
                    <FragmentCells key={h}>
                      <td className="whitespace-nowrap border-l px-2 py-2 text-right tabular-nums"><Money value={r.a[h]} rows={invoicesFor(clientId, comp.sourceA, r.month)} title={`${comp.sideA} — ${monthLabel(r.month)}`} /></td>
                      <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums"><Money value={r.b[h]} rows={invoicesFor(clientId, comp.sourceB, r.month)} title={`${comp.sideB} — ${monthLabel(r.month)}`} /></td>
                      <td className={cn("whitespace-nowrap px-2 py-2 text-right tabular-nums", r.status === "Difference" ? diffCls(r.diff[h], tol) : "text-muted-foreground")}>{inr(r.diff[h])}</td>
                    </FragmentCells>
                  ))}
                  <td className={cn("whitespace-nowrap border-l px-2 py-2 text-right tabular-nums", r.status === "Difference" ? diffCls(totalTax(r.diff), tol) : "text-muted-foreground")}>{inr(totalTax(r.diff))}</td>
                  <td className="px-2 py-2"><StatusBadge status={r.status} /></td>
                  <td className="min-w-72 py-2 text-xs leading-snug text-muted-foreground">{r.meaning}</td>
                </tr>
              ))}
              <tr className="border-t-2 font-semibold">
                <td className="py-2 pr-2">Total</td>
                {heads.map((h) => (
                  <FragmentCells key={h}>
                    <td className="whitespace-nowrap border-l px-2 py-2 text-right tabular-nums"><Money value={comp.total.a[h]} rows={invoicesFor(clientId, comp.sourceA)} title={`${comp.sideA} — FY 2025-26`} /></td>
                    <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums"><Money value={comp.total.b[h]} rows={invoicesFor(clientId, comp.sourceB)} title={`${comp.sideB} — FY 2025-26`} /></td>
                    <td className={cn("whitespace-nowrap px-2 py-2 text-right tabular-nums", diffCls(comp.total.diff[h], tol))}>{inr(comp.total.diff[h])}</td>
                  </FragmentCells>
                ))}
                <td className={cn("whitespace-nowrap border-l px-2 py-2 text-right tabular-nums", diffCls(totalTax(comp.total.diff), tol))}>{inr(totalTax(comp.total.diff))}</td>
                <td colSpan={2} />
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">A month shows “Difference” when the total tax difference is more than ₹{tol}.{comp.taxOnly ? " Tax heads only." : ""} Click a month or any underlined amount to see the invoices behind it; GSTR-3B is a summary return with no invoice rows.</p>
      </Panel>
      <Panel title={`${comp.id} — month-wise tax difference (A − B)`}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ left: 10, right: 10, top: 5 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
              <YAxis tickFormatter={lakh} tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} width={60} />
              <RTooltip formatter={(x) => inr(Number(x))} contentStyle={chartTip} />
              <Bar dataKey="diff" name="Tax difference" cursor="pointer" onClick={(d: { key?: string }) => d.key && monthDrill(clientId, comp, d.key, tol)}>
                {chart.map((c) => <Cell key={c.key} fill={c.partial ? "var(--warning)" : Math.abs(c.diff) > tol ? "var(--destructive)" : "var(--success)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs text-muted-foreground">Red = difference, green = matched, amber = partial data. Click a bar to open its invoices.</p>
      </Panel>
    </div>
  );
}
function FragmentCells({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

/* ---------- invoice matching ---------- */
const rowKey = (r: MatchRow) => `${r.kind}|${r.books?.id ?? ""}|${r.ret?.id ?? ""}`;

export function InvoiceMatchPanel({ clientId }: { clientId: string }) {
  const tol = useApp((s) => s.prefs.tolerance);
  const reviews = useApp((s) => s.reviews);
  const v = useDataVersion();
  const [side, setSide] = useState<"sales" | "itc">("sales");
  const all = useMemo(() => invoiceMatch(clientId, side, tol), [clientId, side, tol, v]);
  const [filter, setFilter] = useState<MatchKind | "Exceptions" | "All">("Exceptions");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const kinds = MATCH_KINDS[side];
  const retLabel = side === "sales" ? "GSTR-1" : "GSTR-2B";
  const shown = filter === "All" ? all : filter === "Exceptions" ? all.filter((r) => r.kind !== "Matched") : all.filter((r) => r.kind === filter);
  const rv = (r: MatchRow) => reviews[`${clientId}|${side}|${rowKey(r)}`];

  const cols: Column<MatchRow>[] = [
    { key: "kind", title: "Result", header: "Result", value: (r) => r.kind, filter: true, cell: (r) => <StatusBadge status={r.kind} /> },
    { key: "bno", title: "Invoice in books", header: "Invoice in books", value: (r) => r.books?.no ?? "", cell: (r) => <span className="font-mono text-xs">{r.books?.no ?? "—"}</span> },
    { key: "rno", title: `Invoice in ${retLabel}`, header: `Invoice in ${retLabel}`, value: (r) => r.ret?.no ?? "", cell: (r) => <span className={cn("font-mono text-xs", r.kind === "Probable Match (Inv No)" && "text-warning-foreground")}>{r.ret?.no ?? "—"}</span> },
    { key: "party", title: side === "sales" ? "Customer" : "Supplier", header: side === "sales" ? "Customer" : "Supplier", value: (r) => (r.books ?? r.ret)!.party, filter: true, cell: (r) => <span>{(r.books ?? r.ret)!.party}<div className="font-mono text-[11px] text-muted-foreground">{(r.books ?? r.ret)!.gstin}</div></span> },
    { key: "gstin", title: "GSTIN", header: "GSTIN", value: (r) => (r.books ?? r.ret)!.gstin, cell: () => null, className: "hidden" },
    { key: "date", title: "Date (books / return)", header: "Date", value: (r) => r.books?.date ?? r.ret?.date ?? "", cell: (r) => <span className="whitespace-nowrap text-xs">{r.books ? fmtDate(r.books.date) : "—"}<div className="text-muted-foreground">{r.ret?.date ? fmtDate(r.ret.date) : "—"}</div></span> },
    { key: "month", title: `Month (books / ${retLabel})`, header: `Month (books / ${retLabel})`, value: (r) => `${r.books ? monthLabel(r.books.month) : "—"} / ${r.ret ? monthLabel(r.ret.month) : "—"}` },
    { key: "btx", title: "Taxable (books)", header: "Taxable (books)", value: (r) => r.books?.taxable ?? null, money: true, align: "right", cell: (r) => (r.books ? inr(r.books.taxable) : "—") },
    { key: "rtx", title: `Taxable (${retLabel})`, header: `Taxable (${retLabel})`, value: (r) => r.ret?.taxable ?? null, money: true, align: "right", cell: (r) => (r.ret ? inr(r.ret.taxable) : "—") },
    { key: "btax", title: "Tax (books)", header: "Tax (books)", value: (r) => (r.books ? totalTax(r.books) : null), money: true, align: "right", cell: (r) => (r.books ? inr(totalTax(r.books)) : "—") },
    { key: "rtax", title: `Tax (${retLabel})`, header: `Tax (${retLabel})`, value: (r) => (r.ret ? totalTax(r.ret) : null), money: true, align: "right", cell: (r) => (r.ret ? inr(totalTax(r.ret)) : "—") },
    { key: "diff", title: "Tax difference", header: "Difference", value: (r) => r.taxDiff, money: true, align: "right", cell: (r) => <span className={diffCls(r.taxDiff, tol)}>{inr(r.taxDiff)}</span> },
    { key: "rev", title: "Reviewed", header: "Reviewed", value: (r) => (rv(r) ? `Reviewed: ${rv(r)!.note}` : ""), cell: (r) => (rv(r) ? <span className="text-xs"><StatusBadge status="Matched" label="Reviewed" /><div className="mt-0.5 max-w-48 text-muted-foreground">{rv(r)!.note} — {rv(r)!.by}</div></span> : <span className="text-xs text-muted-foreground">—</span>) },
  ];

  return (
    <Panel
      title={<Term k="Invoice matching">Invoice matching: {side === "sales" ? "sales register vs GSTR-1 (B2B)" : "purchase register vs GSTR-2B"}</Term>}
      actions={
        <div className="inline-flex rounded-md border p-0.5" role="tablist">
          {(["sales", "itc"] as const).map((k) => (
            <button key={k} role="tab" aria-selected={side === k} onClick={() => { setSide(k); setFilter("Exceptions"); setSel(new Set()); }} className={cn("rounded px-3 py-1 text-xs", side === k ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
              {k === "sales" ? "Sales" : "ITC"}
            </button>
          ))}
        </div>
      }
    >
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {kinds.map((k) => {
          const rows = all.filter((r) => r.kind === k);
          const amt = rows.reduce((s, r) => s + Math.abs(r.taxDiff), 0);
          return (
            <button key={k} onClick={() => setFilter(k)} className={cn("rounded-md border p-3 text-left hover:bg-accent/40", filter === k && "border-primary ring-1 ring-primary")}>
              <StatusBadge status={k} />
              <div className="mt-2 text-xl font-semibold tabular-nums">{rows.length}</div>
              <div className="text-xs text-muted-foreground">{inr(amt)} difference</div>
            </button>
          );
        })}
      </div>
      <div className="mb-3 flex flex-wrap gap-3 text-xs">
        {(["Exceptions", "All"] as const).map((f) => <button key={f} onClick={() => setFilter(f)} className={cn("text-primary hover:underline", filter === f && "font-semibold")}>{f === "Exceptions" ? "Show all exceptions" : "Show every invoice"}</button>)}
      </div>
      <DataTable
        rows={shown}
        columns={cols.filter((c) => c.key !== "gstin")}
        rowKey={rowKey}
        exportName={`${clientId}_inv_match_${side}`}
        selection={{ selected: sel, onChange: setSel }}
        empty={{ message: `Nothing here — every invoice matched ${retLabel}.` }}
        onRowClick={(r) => openDrill(`${r.kind}`, [r.books, r.ret].filter(Boolean).map((i, k) => ({ ...i!, note: k === 0 && r.books ? "Books" : retLabel })))}
        toolbar={
          <div className="flex items-center gap-2">
            <Input className="h-8 w-48" placeholder="Review note" value={note} onChange={(e) => setNote(e.target.value)} aria-label="Review note" />
            <Button size="sm" disabled={!sel.size} onClick={() => { setReview(clientId, side, [...sel], note.trim() || "Reviewed"); toast.success(`${sel.size} row(s) marked reviewed`); setSel(new Set()); setNote(""); }}>Mark reviewed</Button>
            <Button size="sm" variant="ghost" disabled={!sel.size} onClick={() => { setReview(clientId, side, [...sel], null); setSel(new Set()); }}>Clear</Button>
          </div>
        }
      />
      <p className="mt-3 text-xs text-muted-foreground">Matched on GSTIN + normalised invoice number (upper case, leading zeros dropped, separators removed: “SGT/25-26/0093” = “sgt-25-26-93”). Probable Match = same GSTIN, same values, dates within 3 days. {side === "itc" ? "Next month's GSTR-2B is included, so late-reported invoices show as “Matched – Period Diff”." : "B2C sales are checked in total only."}</p>
    </Panel>
  );
}

export function useComparisons(clientId: string) {
  const tol = useApp((s) => s.prefs.tolerance);
  const v = useDataVersion();
  return useMemo(() => comparisons(clientId, tol), [clientId, tol, v]);
}

export const rDefs = R_DEFS as Record<RId, (typeof R_DEFS)[RId]>;
