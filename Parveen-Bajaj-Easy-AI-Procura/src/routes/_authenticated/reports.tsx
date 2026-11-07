import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { EmptyState } from "@/components/procurement/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { downloadCsv, money, shortDate, type DocStatus } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/reports")({
  head: () => ({meta: [{title: "Reports — Easy AI Procura"}, {name: "description", content: "Reports for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Reports — Easy AI Procura"}, {property: "og:description", content: "Reports for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: Reports,
});

const statuses: (DocStatus | "ALL")[] = ["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"];

function Reports() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [status, setStatus] = useState<DocStatus | "ALL">("ALL");
  const [supplierId, setSupplierId] = useState("ALL");

  const { data: suppliers = [] } = useQuery({
    queryKey: ["report-suppliers"],
    queryFn: async () => {
      const { data, error } = await supabase.from("suppliers").select("id,supplier_name").order("supplier_name");
      if (error) throw error;
      return data;
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: async () => {
      const [lpos, grns, invoices] = await Promise.all([
        supabase
          .from("lpo_header")
          .select("*, suppliers(supplier_name), departments(department_name)")
          .order("lpo_date", { ascending: false }),
        supabase
          .from("grn_header")
          .select("*, suppliers(supplier_name), departments(department_name), lpo_header(lpo_number)")
          .order("grn_date", { ascending: false }),
        supabase
          .from("invoices")
          .select("*, suppliers(supplier_name), grn_header(grn_number)")
          .order("invoice_date", { ascending: false }),
      ]);
      return { lpos: lpos.data ?? [], grns: grns.data ?? [], invoices: invoices.data ?? [] };
    },
  });

  const match = (row: { status: string; supplier_id: string }, date: string) => {
    if (status !== "ALL" && row.status !== status) return false;
    if (supplierId !== "ALL" && row.supplier_id !== supplierId) return false;
    if (from && date < from) return false;
    if (to && date > to) return false;
    return true;
  };

  const lpos = useMemo(() => (data?.lpos ?? []).filter((r) => match(r, r.lpo_date)), [data, status, supplierId, from, to]);
  const grns = useMemo(() => (data?.grns ?? []).filter((r) => match(r, r.grn_date)), [data, status, supplierId, from, to]);
  const invoices = useMemo(
    () => (data?.invoices ?? []).filter((r) => match(r, r.invoice_date)),
    [data, status, supplierId, from, to],
  );

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Filter the document trail by date, supplier and status, then export to CSV."
      />

      <div className="mb-6 grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="from">From date</Label>
          <Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="to">To date</Label>
          <Input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Supplier</Label>
          <Select value={supplierId} onValueChange={setSupplierId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All suppliers</SelectItem>
              {suppliers.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.supplier_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Status</Label>
          <Select value={status} onValueChange={(v) => setStatus(v as DocStatus | "ALL")}>
            <SelectTrigger>
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
        </div>
      </div>

      {isLoading ? (
        <EmptyState title="Loading report data…" />
      ) : (
        <Tabs defaultValue="lpo">
          <TabsList>
            <TabsTrigger value="lpo">Purchase orders ({lpos.length})</TabsTrigger>
            <TabsTrigger value="grn">Receipts ({grns.length})</TabsTrigger>
            <TabsTrigger value="inv">Invoices ({invoices.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="lpo" className="mt-4">
            <div className="mb-3 flex justify-end">
              <Button
                variant="outline"
                onClick={() =>
                  downloadCsv(
                    "lpo-report.csv",
                    lpos.map((r) => ({
                      lpo_number: r.lpo_number,
                      lpo_date: r.lpo_date,
                      supplier: r.suppliers?.supplier_name ?? "",
                      department: r.departments?.department_name ?? "",
                      total_value: r.total_value,
                      status: r.status,
                      maker: r.maker_name ?? "",
                      approver: r.approver_name ?? "",
                    })),
                  )
                }
              >
                Export CSV
              </Button>
            </div>
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
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lpos.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="num">{r.lpo_number}</TableCell>
                      <TableCell className="text-sm">{shortDate(r.lpo_date)}</TableCell>
                      <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {r.departments?.department_name ?? "—"}
                      </TableCell>
                      <TableCell className="num text-right">{money(r.total_value)}</TableCell>
                      <TableCell>
                        <StatusBadge status={r.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="grn" className="mt-4">
            <div className="mb-3 flex justify-end">
              <Button
                variant="outline"
                onClick={() =>
                  downloadCsv(
                    "grn-report.csv",
                    grns.map((r) => ({
                      grn_number: r.grn_number,
                      grn_date: r.grn_date,
                      lpo_number: r.lpo_header?.lpo_number ?? "",
                      supplier: r.suppliers?.supplier_name ?? "",
                      department: r.departments?.department_name ?? "",
                      receipt_status: r.receipt_status,
                      status: r.status,
                      maker: r.maker_name ?? "",
                      approver: r.approver_name ?? "",
                    })),
                  )
                }
              >
                Export CSV
              </Button>
            </div>
            <div className="overflow-x-auto rounded-lg border border-border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>GRN no.</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>LPO</TableHead>
                    <TableHead>Supplier</TableHead>
                    <TableHead>Receipt</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {grns.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="num">{r.grn_number}</TableCell>
                      <TableCell className="text-sm">{shortDate(r.grn_date)}</TableCell>
                      <TableCell className="num text-sm">{r.lpo_header?.lpo_number ?? "—"}</TableCell>
                      <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                      <TableCell>
                        <StatusBadge status={r.receipt_status} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={r.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="inv" className="mt-4">
            <div className="mb-3 flex justify-end">
              <Button
                variant="outline"
                onClick={() =>
                  downloadCsv(
                    "invoice-report.csv",
                    invoices.map((r) => ({
                      internal_number: r.internal_number,
                      invoice_number: r.invoice_number,
                      invoice_date: r.invoice_date,
                      supplier: r.suppliers?.supplier_name ?? "",
                      grn_number: r.grn_header?.grn_number ?? "",
                      invoice_value: r.invoice_value,
                      vat_amount: r.vat_amount,
                      total_value: r.total_value,
                      status: r.status,
                    })),
                  )
                }
              >
                Export CSV
              </Button>
            </div>
            <div className="overflow-x-auto rounded-lg border border-border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Internal no.</TableHead>
                    <TableHead>Invoice no.</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Supplier</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="num">{r.internal_number}</TableCell>
                      <TableCell className="num text-sm">{r.invoice_number}</TableCell>
                      <TableCell className="text-sm">{shortDate(r.invoice_date)}</TableCell>
                      <TableCell>{r.suppliers?.supplier_name ?? "—"}</TableCell>
                      <TableCell className="num text-right">{money(r.total_value)}</TableCell>
                      <TableCell>
                        <StatusBadge status={r.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
