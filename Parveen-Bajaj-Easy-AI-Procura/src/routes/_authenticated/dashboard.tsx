import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { money, shortDate } from "@/lib/procurement";
import { useAuth } from "@/hooks/useAuth";
import { DashboardCharts } from "@/components/procurement/DashboardCharts";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Dashboard — Easy AI Procura" },
      { name: "description", content: "Live procurement dashboard: approvals, spend trends and document status." },
      { property: "og:title", content: "Dashboard — Easy AI Procura" },
      { property: "og:description", content: "Live procurement dashboard: approvals, spend trends and document status." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { fullName, roles } = useAuth();

  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const [suppliers, lpos, grns, invoices] = await Promise.all([
        supabase.from("suppliers").select("id,status"),
        supabase.from("lpo_header").select("id,lpo_number,lpo_date,status,total_value").order("created_at", { ascending: false }),
        supabase.from("grn_header").select("id,grn_number,grn_date,status,receipt_status").order("created_at", { ascending: false }),
        supabase.from("invoices").select("id,internal_number,invoice_number,invoice_date,status,total_value").order("created_at", { ascending: false }),
      ]);
      return {
        suppliers: suppliers.data ?? [],
        lpos: lpos.data ?? [],
        grns: grns.data ?? [],
        invoices: invoices.data ?? [],
      };
    },
  });

  const count = (rows: { status: string }[] | undefined, status: string) =>
    (rows ?? []).filter((r) => r.status === status).length;

  const tiles = [
    { label: "Suppliers pending approval", value: count(data?.suppliers, "PENDING"), to: "/suppliers" },
    { label: "LPOs pending approval", value: count(data?.lpos, "PENDING"), to: "/lpo" },
    { label: "GRNs pending approval", value: count(data?.grns, "PENDING"), to: "/grn" },
    { label: "Invoices pending approval", value: count(data?.invoices, "PENDING"), to: "/invoices" },
  ] as const;

  return (
    <div>
      <PageHeader
        title={`Welcome, ${fullName}`}
        subtitle={`Signed in with roles: ${roles.join(", ") || "none assigned"}`}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {tiles.map((t) => (
          <Link
            key={t.label}
            to={t.to}
            className="rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/40"
          >
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{t.label}</p>
            <p className="num mt-3 text-3xl font-semibold text-primary">{t.value}</p>
          </Link>
        ))}
      </div>

      <DashboardCharts lpos={data?.lpos ?? []} invoices={data?.invoices ?? []} grns={data?.grns ?? []} />

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Recent LPOs</h2>
          <ul className="space-y-3">
            {(data?.lpos ?? []).slice(0, 6).map((l) => (
              <li key={l.id} className="flex items-center justify-between gap-3 text-sm">
                <Link to="/lpo/$id" params={{ id: l.id }} className="num text-foreground hover:text-primary">
                  {l.lpo_number}
                </Link>
                <span className="num text-xs text-muted-foreground">{money(l.total_value)}</span>
                <StatusBadge status={l.status} />
              </li>
            ))}
            {(data?.lpos ?? []).length === 0 ? <li className="text-sm text-muted-foreground">No orders yet.</li> : null}
          </ul>
        </section>

        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Recent GRNs</h2>
          <ul className="space-y-3">
            {(data?.grns ?? []).slice(0, 6).map((g) => (
              <li key={g.id} className="flex items-center justify-between gap-3 text-sm">
                <Link to="/grn/$id" params={{ id: g.id }} className="num text-foreground hover:text-primary">
                  {g.grn_number}
                </Link>
                <span className="text-xs text-muted-foreground">{shortDate(g.grn_date)}</span>
                <StatusBadge status={g.status} />
              </li>
            ))}
            {(data?.grns ?? []).length === 0 ? <li className="text-sm text-muted-foreground">No receipts yet.</li> : null}
          </ul>
        </section>

        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Recent invoices</h2>
          <ul className="space-y-3">
            {(data?.invoices ?? []).slice(0, 6).map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3 text-sm">
                <Link to="/invoices/$id" params={{ id: i.id }} className="num text-foreground hover:text-primary">
                  {i.invoice_number}
                </Link>
                <span className="num text-xs text-muted-foreground">{money(i.total_value)}</span>
                <StatusBadge status={i.status} />
              </li>
            ))}
            {(data?.invoices ?? []).length === 0 ? (
              <li className="text-sm text-muted-foreground">No invoices yet.</li>
            ) : null}
          </ul>
        </section>
      </div>
    </div>
  );
}
