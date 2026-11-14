import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { EmptyState } from "@/components/procurement/EmptyState";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { money, shortDate, type DocStatus } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/lpo/")({
  head: () => ({meta: [{title: "LPO register — Easy AI Procura"}, {name: "description", content: "LPO register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "LPO register — Easy AI Procura"}, {property: "og:description", content: "LPO register for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: LpoList,
});

const statuses: (DocStatus | "ALL")[] = ["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"];

function LpoList() {
  const { hasRole } = useAuth();
  const [filter, setFilter] = useState<DocStatus | "ALL">("ALL");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["lpo-list"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("lpo_header")
        .select("*, suppliers(supplier_name), departments(department_name)")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const visible = filter === "ALL" ? rows : rows.filter((r) => r.status === filter);

  return (
    <div>
      <PageHeader
        title="Local purchase orders"
        subtitle="Makers raise orders against active suppliers; approvers authorise them. Approved orders are locked."
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
            {hasRole("MAKER", "ADMIN") ? (
              <Button asChild>
                <Link to="/lpo/new">New LPO</Link>
              </Button>
            ) : null}
          </div>
        }
      />

      {isLoading ? (
        <EmptyState title="Loading purchase orders…" />
      ) : visible.length === 0 ? (
        <EmptyState title="No purchase orders" hint="Raise an LPO to start the document trail." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>LPO no.</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Department</TableHead>
                <TableHead className="text-right">Value</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Maker</TableHead>
                <TableHead>Approver</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    <Link to="/lpo/$id" params={{ id: r.id }} className="num font-medium text-primary hover:underline">
                      {r.lpo_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm">{shortDate(r.lpo_date)}</TableCell>
                  <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {r.departments?.department_name ?? "—"}
                  </TableCell>
                  <TableCell className="num text-right">{money(r.total_value)}</TableCell>
                  <TableCell>
                    <StatusBadge status={r.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{r.maker_name || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{r.approver_name || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
