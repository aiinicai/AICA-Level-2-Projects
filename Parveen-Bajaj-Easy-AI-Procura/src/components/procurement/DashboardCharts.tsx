import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { money } from "@/lib/procurement";

type Doc = { status: string; total_value?: number | null; lpo_date?: string; invoice_date?: string; grn_date?: string };

const PERIODS = [
  { id: 3, label: "3 months" },
  { id: 6, label: "6 months" },
  { id: 12, label: "12 months" },
] as const;

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  color: "var(--popover-foreground)",
  fontSize: 12,
};

export function DashboardCharts({ lpos, invoices, grns }: { lpos: Doc[]; invoices: Doc[]; grns: Doc[] }) {
  const [months, setMonths] = useState<number>(6);
  const [doc, setDoc] = useState<"lpo" | "grn" | "invoice">("lpo");

  const trend = useMemo(() => {
    const now = new Date();
    const buckets = Array.from({ length: months }, (_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth() - (months - 1 - i), 1);
      return { key: `${d.getFullYear()}-${d.getMonth()}`, month: d.toLocaleDateString("en-GB", { month: "short" }), lpo: 0, invoice: 0 };
    });
    const add = (rows: Doc[], field: "lpo" | "invoice", dateKey: "lpo_date" | "invoice_date") =>
      rows.forEach((r) => {
        const v = r[dateKey];
        if (!v || r.status === "CANCELLED" || r.status === "REJECTED") return;
        const d = new Date(v);
        const b = buckets.find((x) => x.key === `${d.getFullYear()}-${d.getMonth()}`);
        if (b) b[field] += Number(r.total_value ?? 0);
      });
    add(lpos, "lpo", "lpo_date");
    add(invoices, "invoice", "invoice_date");
    return buckets;
  }, [lpos, invoices, months]);

  const statusMix = useMemo(() => {
    const rows = doc === "lpo" ? lpos : doc === "grn" ? grns : invoices;
    const counts = new Map<string, number>();
    rows.forEach((r) => counts.set(r.status, (counts.get(r.status) ?? 0) + 1));
    return [...counts.entries()].map(([name, value]) => ({ name, value }));
  }, [doc, lpos, grns, invoices]);

  const totalOrdered = trend.reduce((s, b) => s + b.lpo, 0);
  const totalInvoiced = trend.reduce((s, b) => s + b.invoice, 0);

  return (
    <div className="mt-8 grid gap-6 lg:grid-cols-3">
      <section className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Spend trend</h2>
            <p className="num mt-1 text-xs text-muted-foreground">
              Ordered {money(totalOrdered)} · Invoiced {money(totalInvoiced)}
            </p>
          </div>
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p.id}
                onClick={() => setMonths(p.id)}
                className={`rounded px-2.5 py-1 text-xs ${months === p.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} width={60} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => money(v)} />
              <Area type="monotone" dataKey="lpo" name="Ordered (LPO)" stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.2} />
              <Area type="monotone" dataKey="invoice" name="Invoiced" stroke="var(--chart-3)" fill="var(--chart-3)" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Status mix</h2>
          <select
            aria-label="Document type"
            value={doc}
            onChange={(e) => setDoc(e.target.value as typeof doc)}
            className="h-7 rounded border border-input bg-background px-2 text-xs text-foreground"
          >
            <option value="lpo">LPOs</option>
            <option value="grn">GRNs</option>
            <option value="invoice">Invoices</option>
          </select>
        </div>
        {statusMix.length ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusMix} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}>
                  {statusMix.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="var(--card)" />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="py-20 text-center text-sm text-muted-foreground">No documents yet.</p>
        )}
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          {statusMix.map((s, i) => (
            <span key={s.name} className="flex items-center gap-1.5">
              <span className="size-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
              {s.name} ({s.value})
            </span>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5 lg:col-span-3">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Monthly orders vs invoices
        </h2>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trend}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} width={60} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => money(v)} cursor={{ fill: "var(--muted)" }} />
              <Bar dataKey="lpo" name="Ordered (LPO)" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="invoice" name="Invoiced" fill="var(--chart-3)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
