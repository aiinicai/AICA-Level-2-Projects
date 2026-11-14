import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { money, qty, shortDate, stamp } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/invoices/$id")({
  head: () => ({meta: [{title: "Invoice detail — Easy AI Procura"}, {name: "description", content: "Invoice detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Invoice detail — Easy AI Procura"}, {property: "og:description", content: "Invoice detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: InvoiceDetail,
});

function InvoiceDetail() {
  const { id } = Route.useParams();
  const { user, fullName, hasRole } = useAuth();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: async () => {
      const [header, lines, log] = await Promise.all([
        supabase
          .from("invoices")
          .select("*, suppliers(*), grn_header(grn_number), lpo_header(lpo_number)")
          .eq("id", id)
          .single(),
        supabase.from("invoice_lines").select("*, items(item_code,item_description)").eq("invoice_id", id),
        supabase
          .from("approval_log")
          .select("*")
          .eq("doc_type", "INVOICE")
          .eq("doc_id", id)
          .order("created_at", { ascending: true }),
      ]);
      if (header.error) throw header.error;
      return { header: header.data, lines: lines.data ?? [], log: log.data ?? [] };
    },
  });

  const decide = useMutation({
    mutationFn: async (approve: boolean) => {
      if (!approve && !reason.trim()) throw new Error("A rejection reason is required");
      const { error } = await supabase
        .from("invoices")
        .update({
          status: approve ? "APPROVED" : "REJECTED",
          approver: user!.id,
          approver_name: fullName,
          approved_at: new Date().toISOString(),
          reject_reason: approve ? null : reason.trim(),
        })
        .eq("id", id);
      if (error) throw error;
      await supabase.from("approval_log").insert({
        doc_type: "INVOICE",
        doc_id: id,
        doc_number: data?.header.internal_number ?? null,
        action: approve ? "APPROVED" : "REJECTED",
        actor: user!.id,
        actor_name: fullName,
        remarks: approve ? null : reason.trim(),
      });
    },
    onSuccess: () => {
      toast.success("Invoice updated");
      setReason("");
      void qc.invalidateQueries({ queryKey: ["invoice", id] });
      void qc.invalidateQueries({ queryKey: ["invoice-list"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading invoice…</p>;

  const h = data.header;
  const canApprove =
    hasRole("FINANCE_APPROVER", "APPROVER", "ADMIN") && h.status === "PENDING" && h.maker !== user?.id;
  const hasVariance = data.lines.some((l) => Number(l.price_variance ?? 0) > 0);

  return (
    <div>
      <PageHeader
        title={h.internal_number}
        subtitle={`Supplier invoice ${h.invoice_number} · ${shortDate(h.invoice_date)}`}
        actions={
          <div className="no-print flex items-center gap-2">
            <StatusBadge status={h.status} />
            <Button variant="outline" onClick={() => window.print()}>
              Print
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/invoices">Back to list</Link>
            </Button>
          </div>
        }
      />

      <dl className="grid gap-4 rounded-lg border border-border bg-card p-5 text-sm sm:grid-cols-4">
        {[
          ["Supplier", h.suppliers?.supplier_name ?? "—"],
          ["Goods received note", h.grn_header?.grn_number ?? "—"],
          ["Purchase order", h.lpo_header?.lpo_number ?? "—"],
          ["Maker", h.maker_name || "—"],
          ["Approver", h.approver_name || "—"],
          ["Approved at", h.approved_at ? stamp(h.approved_at) : "—"],
          ["Net value", money(h.invoice_value)],
          ["VAT", money(h.vat_amount)],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
            <dd className="mt-1 text-foreground">{value}</dd>
          </div>
        ))}
      </dl>

      {hasVariance ? (
        <p className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          Price variance detected: one or more invoice prices exceed the approved order price.
        </p>
      ) : null}

      {h.status === "REJECTED" && h.reject_reason ? (
        <p className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          Rejected: {h.reject_reason}
        </p>
      ) : null}

      <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item code</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead className="text-right">LPO price</TableHead>
              <TableHead className="text-right">Invoice price</TableHead>
              <TableHead className="text-right">Variance</TableHead>
              <TableHead className="text-right">Line value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.lines.map((l) => (
              <TableRow key={l.id}>
                <TableCell className="num">{l.items?.item_code}</TableCell>
                <TableCell>{l.items?.item_description}</TableCell>
                <TableCell className="num text-right">{qty(l.quantity)}</TableCell>
                <TableCell className="num text-right">{money(l.lpo_price)}</TableCell>
                <TableCell className="num text-right">{money(l.invoice_price)}</TableCell>
                <TableCell
                  className={`num text-right ${Number(l.price_variance ?? 0) > 0 ? "font-medium text-destructive" : "text-muted-foreground"}`}
                >
                  {money(l.price_variance)}
                </TableCell>
                <TableCell className="num text-right">{money(l.line_value)}</TableCell>
              </TableRow>
            ))}
            <TableRow>
              <TableCell colSpan={6} className="text-right text-sm font-medium">
                Total payable (incl. VAT)
              </TableCell>
              <TableCell className="num text-right text-base font-semibold">{money(h.total_value)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      {canApprove ? (
        <div className="no-print mt-6 rounded-lg border border-warning/30 bg-warning/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">Approval decision</h2>
          <Textarea
            className="mt-3"
            rows={2}
            placeholder="Rejection reason (required to reject)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="mt-3 flex gap-2">
            <Button disabled={decide.isPending} onClick={() => decide.mutate(true)}>
              Approve invoice
            </Button>
            <Button variant="outline" disabled={decide.isPending} onClick={() => decide.mutate(false)}>
              Reject
            </Button>
          </div>
        </div>
      ) : h.status === "PENDING" && h.maker === user?.id ? (
        <p className="no-print mt-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Awaiting approval. A maker cannot approve their own invoice.
        </p>
      ) : null}

      <section className="no-print mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Audit trail</h2>
        <ul className="space-y-2 text-sm">
          {data.log.map((entry) => (
            <li key={entry.id} className="flex flex-wrap gap-x-3 text-muted-foreground">
              <span className="num text-xs">{stamp(entry.created_at)}</span>
              <span className="font-medium text-foreground">{entry.action.replace("_", " ")}</span>
              <span>{entry.actor_name ?? ""}</span>
              {entry.remarks ? <span className="italic">“{entry.remarks}”</span> : null}
            </li>
          ))}
          {data.log.length === 0 ? <li>No entries.</li> : null}
        </ul>
      </section>
    </div>
  );
}
