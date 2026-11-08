import { useSyncExternalStore, type ReactNode } from "react";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { GLOSSARY } from "@/lib/gst/glossary";
import { fmtDate, inr } from "@/lib/gst/format";
import type { Invoice } from "@/lib/gst/demo";
import { cn } from "@/lib/utils";

/* ---------- ⓘ glossary tooltip ---------- */
export function Term({ k, children, className }: { k: string; children?: ReactNode; className?: string }) {
  const text = GLOSSARY[k];
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      {children ?? k}
      {text && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" aria-label={`What is ${k}?`} className="text-muted-foreground hover:text-primary">
              <Info className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs leading-relaxed">{text}</TooltipContent>
        </Tooltip>
      )}
    </span>
  );
}

/* ---------- status badge ---------- */
const TONE: Record<string, string> = {
  success: "bg-success/12 text-success border-success/30",
  warning: "bg-warning/15 text-warning-foreground border-warning/40",
  danger: "bg-destructive/10 text-destructive border-destructive/30",
  info: "bg-info/10 text-info border-info/30",
  neutral: "bg-muted text-muted-foreground border-border",
};
export function toneFor(status: string): keyof typeof TONE {
  if (["Matched", "Completed", "Replied", "Imported", "done"].includes(status)) return "success";
  if (["Matched – Period Diff"].includes(status)) return "success";
  if (["Partial data", "Completed with warnings", "Due soon", "Probable Match (Inv No)", "running", "queued"].includes(status)) return "warning";
  if (["Difference", "Failed", "Overdue", "Value Mismatch", "Only in Books", "Missing", "failed"].includes(status)) return "danger";
  if (["Open", "Only in GSTR-1", "Only in GSTR-2B"].includes(status)) return "info";
  return "neutral";
}
export function StatusBadge({ status, label }: { status: string; label?: string | undefined }) {
  return (
    <span className={cn("inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium", TONE[toneFor(status)])}>
      {label ?? status}
    </span>
  );
}

/* ---------- loading skeleton (shown until saved data is read) ---------- */
export function LoadingPage() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div>
      <Skeleton className="h-72" />
    </div>
  );
}

/* ---------- page header & cards ---------- */
export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({ title, actions, children, className }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("min-w-0 rounded-lg border bg-card text-card-foreground shadow-soft", className)}>
      {title && (
        <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          {actions}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Kpi({ label, value, hint, onClick, tone }: { label: ReactNode; value: ReactNode; hint?: ReactNode; onClick?: (() => void) | undefined; tone?: "danger" | "warning" | "success" | undefined }) {
  const Comp = onClick ? "button" : "div";
  return (
    <Comp
      onClick={onClick}
      className={cn(
        "rounded-lg border bg-card p-4 text-left shadow-soft transition-colors",
        onClick && "hover:border-primary/40 hover:bg-accent/40",
      )}
    >
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div
        className={cn(
          "mt-2 text-2xl font-semibold tabular-nums",
          tone === "danger" && "text-destructive",
          tone === "warning" && "text-warning-foreground",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </Comp>
  );
}

/* ---------- drill-down (every number opens its rows) ---------- */
export interface DrillRow extends Invoice {
  note?: string | undefined;
}
interface Drill {
  open: boolean;
  title: string;
  subtitle?: string | undefined;
  rows: DrillRow[];
}
let drill: Drill = { open: false, title: "", rows: [] };
const dl = new Set<() => void>();
export function openDrill(title: string, rows: DrillRow[], subtitle?: string) {
  drill = { open: true, title, rows, subtitle };
  dl.forEach((l) => l());
}
function closeDrill() {
  drill = { ...drill, open: false };
  dl.forEach((l) => l());
}

export function Money({ value, rows, title, subtitle, className, signed }: { value: number; rows?: DrillRow[] | undefined; title?: string | undefined; subtitle?: string | undefined; className?: string | undefined; signed?: boolean | undefined }) {
  const text = signed && value > 0 ? "+" + inr(value) : inr(value);
  if (!rows) return <span className={cn("tabular-nums", className)}>{text}</span>;
  return (
    <button
      type="button"
      onClick={() => openDrill(title ?? "Invoices", rows, subtitle)}
      className={cn("tabular-nums underline decoration-border decoration-dotted underline-offset-4 hover:text-primary hover:decoration-primary", className)}
      title="Show the invoices behind this number"
    >
      {text}
    </button>
  );
}

export function DrillSheet() {
  const d = useSyncExternalStore(
    (l) => {
      dl.add(l);
      return () => dl.delete(l);
    },
    () => drill,
    () => drill,
  );
  const tax = d.rows.reduce((s, r) => s + r.igst + r.cgst + r.sgst + (r.cess ?? 0), 0);
  const taxable = d.rows.reduce((s, r) => s + r.taxable, 0);
  return (
    <Sheet open={d.open} onOpenChange={(o) => !o && closeDrill()}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-3xl">
        <SheetHeader>
          <SheetTitle>{d.title}</SheetTitle>
          <SheetDescription>
            {d.subtitle ? d.subtitle + " · " : ""}
            {d.rows.length} invoice(s) · Taxable {inr(taxable)} · Tax {inr(tax)}
          </SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-6">
          {d.rows.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No invoices behind this number — it comes from the GSTR-3B summary or is zero.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr className="border-b">
                  <th className="py-2 pr-2 font-medium">Invoice</th>
                  <th className="py-2 pr-2 font-medium">Date</th>
                  <th className="py-2 pr-2 font-medium">Party</th>
                  <th className="py-2 pr-2 text-right font-medium">Taxable</th>
                  <th className="py-2 text-right font-medium">Tax</th>
                </tr>
              </thead>
              <tbody>
                {d.rows.map((r) => (
                  <tr key={r.id + r.no + (r.note ?? "")} className="border-b last:border-0 align-top">
                    <td className="py-2 pr-2 font-mono text-xs">
                      {r.no}
                      {r.note && <div className="mt-1"><StatusBadge status={r.note} /></div>}
                    </td>
                    <td className="py-2 pr-2 whitespace-nowrap">{fmtDate(r.date)}</td>
                    <td className="py-2 pr-2">
                      {r.party}
                      <div className="font-mono text-[11px] text-muted-foreground">{r.gstin}</div>
                    </td>
                    <td className="py-2 pr-2 text-right tabular-nums">{inr(r.taxable)}</td>
                    <td className="py-2 text-right tabular-nums">{inr(r.igst + r.cgst + r.sgst + (r.cess ?? 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
