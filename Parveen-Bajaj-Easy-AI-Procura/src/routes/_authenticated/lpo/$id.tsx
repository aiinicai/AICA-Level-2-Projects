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

export const Route = createFileRoute("/_authenticated/lpo/$id")({
  head: () => ({meta: [{title: "LPO detail — Easy AI Procura"}, {name: "description", content: "LPO detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "LPO detail — Easy AI Procura"}, {property: "og:description", content: "LPO detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: LpoDetail,
});

function LpoDetail() {
  const { id } = Route.useParams();
  const { user, fullName, hasRole } = useAuth();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["lpo", id],
    queryFn: async () => {
      const [header, lines, log] = await Promise.all([
        supabase
          .from("lpo_header")
          .select("*, suppliers(*), departments(*)")
          .eq("id", id)
          .single(),
        supabase.from("lpo_lines").select("*, items(item_code,item_description,unit)").eq("lpo_id", id),
        supabase
          .from("approval_log")
          .select("*")
          .eq("doc_type", "LPO")
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
        .from("lpo_header")
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
        doc_type: "LPO",
        doc_id: id,
        doc_number: data?.header.lpo_number ?? null,
        action: approve ? "APPROVED" : "REJECTED",
        actor: user!.id,
        actor_name: fullName,
        remarks: approve ? null : reason.trim(),
      });
    },
    onSuccess: () => {
      toast.success("Purchase order updated");
      setReason("");
      void qc.invalidateQueries({ queryKey: ["lpo", id] });
      void qc.invalidateQueries({ queryKey: ["lpo-list"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading purchase order…</p>;

  const h = data.header;
  const canApprove = hasRole("APPROVER", "ADMIN") && h.status === "PENDING" && h.maker !== user?.id;
  const ownPending = h.status === "PENDING" && h.maker === user?.id;

  return (
    <div>
      <PageHeader
        title={h.lpo_number}
        subtitle={`Raised ${shortDate(h.lpo_date)} · ${h.suppliers?.supplier_name ?? ""}`}
        actions={
          <div className="no-print flex items-center gap-2">
            <StatusBadge status={h.status} />
            <Button variant="outline" onClick={() => window.print()}>
              Print
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/lpo">Back to list</Link>
            </Button>
          </div>
        }
      />

      <dl className="grid gap-4 rounded-lg border border-border bg-card p-5 text-sm sm:grid-cols-4">
        {[
          ["Supplier", `${h.suppliers?.supplier_code ?? ""} — ${h.suppliers?.supplier_name ?? ""}`],
          ["Department", h.departments?.department_name ?? "—"],
          ["Delivery location", h.delivery_location || "—"],
          ["Payment terms", h.payment_terms || "—"],
          ["Maker", h.maker_name || "—"],
          ["Approver", h.approver_name || "—"],
          ["Approved at", h.approved_at ? stamp(h.approved_at) : "—"],
          ["Remarks", h.remarks || "—"],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
            <dd className="mt-1 text-foreground">{value}</dd>
          </div>
        ))}
      </dl>

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
              <TableHead>Unit</TableHead>
              <TableHead className="text-right">Qty ordered</TableHead>
              <TableHead className="text-right">Unit price</TableHead>
              <TableHead className="text-right">Line value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.lines.map((l) => (
              <TableRow key={l.id}>
                <TableCell className="num">{l.items?.item_code}</TableCell>
                <TableCell>{l.items?.item_description}</TableCell>
                <TableCell className="num text-sm">{l.items?.unit}</TableCell>
                <TableCell className="num text-right">{qty(l.quantity_ordered)}</TableCell>
                <TableCell className="num text-right">{money(l.unit_price)}</TableCell>
                <TableCell className="num text-right">{money(l.line_value)}</TableCell>
              </TableRow>
            ))}
            <TableRow>
              <TableCell colSpan={5} className="text-right text-sm font-medium">
                Order total
              </TableCell>
              <TableCell className="num text-right text-base font-semibold">{money(h.total_value)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      {canApprove ? (
        <div className="no-print mt-6 rounded-lg border border-warning/30 bg-warning/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">Approval decision</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Approving locks this order and allows goods receipt against it.
          </p>
          <Textarea
            className="mt-3"
            rows={2}
            placeholder="Rejection reason (required to reject)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="mt-3 flex gap-2">
            <Button disabled={decide.isPending} onClick={() => decide.mutate(true)}>
              Approve order
            </Button>
            <Button variant="outline" disabled={decide.isPending} onClick={() => decide.mutate(false)}>
              Reject
            </Button>
          </div>
        </div>
      ) : ownPending ? (
        <p className="no-print mt-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Awaiting approval. A maker cannot approve their own purchase order.
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
          {data.log.length === 0 ? <li className="text-muted-foreground">No entries.</li> : null}
        </ul>
      </section>
    </div>
  );
}
