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
import { ExportFiles } from "@/components/procurement/ExportFiles";
import { shortDate, type DocStatus } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/grn/")({
  head: () => ({meta: [{title: "GRN register — Easy AI Procura"}, {name: "description", content: "GRN register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "GRN register — Easy AI Procura"}, {property: "og:description", content: "GRN register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: GrnList,
});

const statuses: (DocStatus | "ALL")[] = ["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"];

function GrnList() {
  const { hasRole } = useAuth();
  const [filter, setFilter] = useState<DocStatus | "ALL">("ALL");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["grn-list"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("grn_header")
        .select("*, suppliers(supplier_name), departments(department_name), lpo_header(lpo_number)")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const visible = filter === "ALL" ? rows : rows.filter((r) => r.status === filter);

  return (
    <div>
      <PageHeader
        title="Goods received notes"
        subtitle="Receipts are entered only against approved purchase orders, with quantities pre-loaded from the order."
        actions={
          <div className="flex items-center gap-2">
            <ExportFiles filename="grn-register" rows={visible.map(r=>({grn_number:r.grn_number,date:r.grn_date,lpo_number:r.lpo_header?.lpo_number,supplier:r.suppliers?.supplier_name,department:r.departments?.department_name,receipt_status:r.receipt_status,status:r.status,delivery_note:r.delivery_note_no}))}/>
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
            {hasRole("STOREKEEPER", "MAKER", "ADMIN") ? (
              <Button asChild>
                <Link to="/grn/new">New GRN</Link>
              </Button>
            ) : null}
          </div>
        }
      />

      {isLoading ? (
        <EmptyState title="Loading receipts…" />
      ) : visible.length === 0 ? (
        <EmptyState title="No goods received notes" hint="Receive goods against an approved purchase order." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>GRN no.</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>LPO</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Receipt</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Maker</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    <Link to="/grn/$id" params={{ id: r.id }} className="num font-medium text-primary hover:underline">
                      {r.grn_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm">{shortDate(r.grn_date)}</TableCell>
                  <TableCell className="num text-sm">{r.lpo_header?.lpo_number ?? "—"}</TableCell>
                  <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {r.departments?.department_name ?? "—"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={r.receipt_status} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={r.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{r.maker_name || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
