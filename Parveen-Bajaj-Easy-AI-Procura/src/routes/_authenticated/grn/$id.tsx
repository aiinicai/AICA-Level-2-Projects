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
import { qty, shortDate, stamp } from "@/lib/procurement";
import { ExportFiles } from "@/components/procurement/ExportFiles";
import { buildSupplierNotice, findSupplyProblems, mailtoLink } from "@/lib/supplier-notice";

export const Route = createFileRoute("/_authenticated/grn/$id")({
  head: () => ({meta: [{title: "GRN detail — Easy AI Procura"}, {name: "description", content: "GRN detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "GRN detail — Easy AI Procura"}, {property: "og:description", content: "GRN detail for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: GrnDetail,
});

function GrnDetail() {
  const { id } = Route.useParams();
  const { user, fullName, hasRole } = useAuth();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["grn", id],
    queryFn: async () => {
      const [header, lines, log] = await Promise.all([
        supabase
          .from("grn_header")
          .select("*, suppliers(*), departments(*), lpo_header(lpo_number)")
          .eq("id", id)
          .single(),
        supabase.from("grn_lines").select("*, items(item_code,item_description,unit)").eq("grn_id", id),
        supabase
          .from("approval_log")
          .select("*")
          .eq("doc_type", "GRN")
          .eq("doc_id", id)
          .order("created_at", { ascending: true }),
      ]);
      if (header.error) throw header.error;
      return { header: header.data, lines: lines.data ?? [], log: log.data ?? [] };
    },
  });

  const decide = useMutation({
    mutationFn: async (approve: boolean) => {
      if (!user) throw new Error("Sign in required");
      if (!approve && !reason.trim()) throw new Error("A rejection reason is required");
      const { error } = await supabase
        .from("grn_header")
        .update({
          status: approve ? "APPROVED" : "REJECTED",
          approver: user.id,
          approver_name: fullName,
          approved_at: new Date().toISOString(),
          reject_reason: approve ? null : reason.trim(),
        })
        .eq("id", id);
      if (error) throw error;
      await supabase.from("approval_log").insert({
        doc_type: "GRN",
        doc_id: id,
        doc_number: data?.header.grn_number ?? null,
        action: approve ? "APPROVED" : "REJECTED",
        actor: user.id,
        actor_name: fullName,
        remarks: approve ? null : reason.trim(),
      });
    },
    onSuccess: () => {
      toast.success("Goods received note updated");
      setReason("");
      void qc.invalidateQueries({ queryKey: ["grn", id] });
      void qc.invalidateQueries({ queryKey: ["grn-list"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });


  if (isLoading || !data) return <p className="text-sm text-muted-foreground">Loading receipt…</p>;

  const h = data.header;
  const canApprove = hasRole("APPROVER", "ADMIN") && h.status === "PENDING" && h.maker !== user?.id;

  const problems = findSupplyProblems(
    data.lines.map((l) => ({
      itemCode: l.items?.item_code ?? "—",
      description: l.items?.item_description ?? "—",
      unit: l.items?.unit ?? "",
      ordered: Number(l.qty_ordered ?? 0),
      received: Number(l.qty_received ?? 0),
      condition: l.item_condition,
      remarks: l.remarks,
    })),
  );

  const notice =
    problems.length > 0
      ? buildSupplierNotice({
          grnNumber: h.grn_number,
          lpoNumber: h.lpo_header?.lpo_number ?? "—",
          supplierName: h.suppliers?.supplier_name ?? "Supplier",
          contactPerson: h.suppliers?.contact_person,
          receivedDate: shortDate(h.grn_date),
          deliveryNoteNo: h.delivery_note_no,
          receivedBy: h.received_by,
          departmentName: h.departments?.department_name,
          problems,
        })
      : null;

  const supplierEmail = h.suppliers?.email ?? null;

  return (
    <div>
      <PageHeader
        title={h.grn_number}
        subtitle={`Received ${shortDate(h.grn_date)} against ${h.lpo_header?.lpo_number ?? "—"}`}
        actions={
          <div className="no-print flex items-center gap-2">
            <ExportFiles filename={h.grn_number} rows={data.lines.map(l=>({grn_number:h.grn_number,grn_date:h.grn_date,lpo_number:h.lpo_header?.lpo_number,supplier:h.suppliers?.supplier_name,delivery_note:h.delivery_note_no,status:h.status,item_code:l.items?.item_code,description:l.items?.item_description,unit:l.items?.unit,qty_ordered:l.qty_ordered,qty_received:l.qty_received,shortage_excess:l.shortage_excess,condition:l.item_condition,remarks:l.remarks}))}/>
            <StatusBadge status={h.receipt_status} />
            <StatusBadge status={h.status} />
            <Button variant="outline" onClick={() => window.print()}>
              Print
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/grn">Back to list</Link>
            </Button>
          </div>
        }
      />

      <dl className="grid gap-4 rounded-lg border border-border bg-card p-5 text-sm sm:grid-cols-4">
        {[
          ["Supplier", h.suppliers?.supplier_name ?? "—"],
          ["Department", h.departments?.department_name ?? "—"],
          ["Delivery note", h.delivery_note_no || "—"],
          ["Received by", h.received_by || "—"],
          ["Checked by", h.checked_by || "—"],
          ["Maker", h.maker_name || "—"],
          ["Approver", h.approver_name || "—"],
          ["Over-receipt override", h.over_receipt_override ? "Yes" : "No"],
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
              <TableHead className="text-right">Ordered</TableHead>
              <TableHead className="text-right">Received</TableHead>
              <TableHead className="text-right">Shortage / excess</TableHead>
              <TableHead>Condition</TableHead>
              <TableHead>Remarks</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.lines.map((l) => (
              <TableRow key={l.id}>
                <TableCell className="num">{l.items?.item_code}</TableCell>
                <TableCell>{l.items?.item_description}</TableCell>
                <TableCell className="num text-sm">{l.items?.unit}</TableCell>
                <TableCell className="num text-right">{qty(l.qty_ordered)}</TableCell>
                <TableCell className="num text-right">{qty(l.qty_received)}</TableCell>
                <TableCell className="num text-right">{qty(l.shortage_excess)}</TableCell>
                <TableCell>
                  <StatusBadge status={l.item_condition} />
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{l.remarks || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {notice ? (
        <section className="no-print mt-6 rounded-lg border border-warning/30 bg-warning/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">Supply problem noticed</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {problems.length} problem{problems.length === 1 ? "" : "s"} on this delivery. Send the notice below to{" "}
            {h.suppliers?.supplier_name ?? "the supplier"}.
          </p>
          <ul className="mt-3 space-y-1 text-sm text-foreground">
            {problems.map((problem, index) => (
              <li key={`${problem.itemCode}-${problem.kind}-${index}`}>
                <span className="num text-primary">{problem.itemCode}</span> — {problem.description}:{" "}
                {problem.detail}
              </li>
            ))}
          </ul>
          <pre className="mt-4 max-h-60 overflow-y-auto whitespace-pre-wrap rounded-md border border-border bg-background p-4 font-mono text-xs leading-relaxed text-muted-foreground">
            {notice.body}
          </pre>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              onClick={() => {
                void navigator.clipboard
                  .writeText(notice.body)
                  .then(() => toast.success("Message copied"))
                  .catch(() => toast.error("Could not copy the message"));
              }}
            >
              Copy message
            </Button>
            {supplierEmail ? (
              <Button size="sm" variant="outline" asChild>
                <a href={mailtoLink(supplierEmail, notice.subject, notice.body)}>Email {supplierEmail}</a>
              </Button>
            ) : (
              <span className="text-xs text-muted-foreground">
                No email address is on file for this supplier.
              </span>
            )}
          </div>
        </section>
      ) : null}

      {canApprove ? (
        <div className="no-print mt-6 rounded-lg border border-warning/30 bg-warning/5 p-5">
          <h2 className="text-sm font-semibold text-foreground">Approval decision</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Approving locks this receipt and allows invoice matching against it.
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
              Approve receipt
            </Button>
            <Button variant="outline" disabled={decide.isPending} onClick={() => decide.mutate(false)}>
              Reject
            </Button>
          </div>
        </div>
      ) : h.status === "PENDING" && h.maker === user?.id ? (
        <p className="no-print mt-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Awaiting approval. A maker cannot approve their own receipt.
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
