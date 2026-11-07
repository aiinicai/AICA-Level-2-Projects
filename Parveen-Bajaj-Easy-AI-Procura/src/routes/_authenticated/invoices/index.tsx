import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { EmptyState } from "@/components/procurement/EmptyState";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { money, shortDate, type DocStatus } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/invoices/")({
  head: () => ({meta: [{title: "Invoice register — Easy AI Procura"}, {name: "description", content: "Invoice register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Invoice register — Easy AI Procura"}, {property: "og:description", content: "Invoice register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: InvoiceList,
});

const statuses: (DocStatus | "ALL")[] = ["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"];

function InvoiceList() {
  const { hasRole } = useAuth();
  const [filter, setFilter] = useState<DocStatus | "ALL">("ALL");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["invoice-list"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("invoices")
        .select("*, suppliers(supplier_name), grn_header(grn_number), lpo_header(lpo_number)")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const visible = filter === "ALL" ? rows : rows.filter((r) => r.status === filter);

  return (
    <div>
      <PageHeader
        title="Supplier invoices"
        subtitle="Invoices are matched to approved receipts; quantities are fixed by the GRN and price variances are highlighted."
        actions={
          <div className="flex items-center gap-2">
            <Select value={filter} onValueChange={(v) => setFilter(v as DocStatus | "ALL")}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {statuses.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s === "ALL" ? "All statuses" : s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {hasRole("FINANCE_MAKER", "MAKER", "ADMIN") ? (
              <Button asChild>
                <Link to="/invoices/new">New invoice</Link>
              </Button>
            ) : null}
          </div>
        }
      />

      {isLoading ? (
        <EmptyState title="Loading invoices…" />
      ) : visible.length === 0 ? (
        <EmptyState title="No invoices" hint="Match a supplier invoice against an approved goods received note." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Internal no.</TableHead>
                <TableHead>Invoice no.</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>GRN</TableHead>
                <TableHead className="text-right">Net</TableHead>
                <TableHead className="text-right">VAT</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    <Link
                      to="/invoices/$id"
                      params={{ id: r.id }}
                      className="num font-medium text-primary hover:underline"
                    >
                      {r.internal_number}
                    </Link>
                  </TableCell>
                  <TableCell className="num text-sm">{r.invoice_number}</TableCell>
                  <TableCell className="text-sm">{shortDate(r.invoice_date)}</TableCell>
                  <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                  <TableCell className="num text-sm">{r.grn_header?.grn_number ?? "—"}</TableCell>
                  <TableCell className="num text-right">{money(r.invoice_value)}</TableCell>
                  <TableCell className="num text-right">{money(r.vat_amount)}</TableCell>
                  <TableCell className="num text-right font-medium">{money(r.total_value)}</TableCell>
                  <TableCell>
                    <StatusBadge status={r.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
