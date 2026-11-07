import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { qty, receiptStatusFor, type ItemCondition } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/grn/new")({
  head: () => ({meta: [{title: "GRN entry — Easy AI Procura"}, {name: "description", content: "GRN entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "GRN entry — Easy AI Procura"}, {property: "og:description", content: "GRN entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: NewGrn,
});

type LineDraft = {
  lpo_line_id: string;
  item_id: string;
  item_code: string;
  item_description: string;
  unit: string;
  qty_ordered: number;
  qty_received: string;
  item_condition: ItemCondition;
  remarks: string;
};

const conditions: ItemCondition[] = ["OK", "DAMAGED", "WRONG_ITEM"];

function NewGrn() {
  const { user, fullName, hasRole } = useAuth();
  const navigate = useNavigate();
  const canOverride = hasRole("APPROVER", "ADMIN");

  const [lpoId, setLpoId] = useState("");
  const [header, setHeader] = useState({
    grn_date: new Date().toISOString().slice(0, 10),
    delivery_note_no: "",
    received_by: "",
    checked_by: "",
  });
  const [override, setOverride] = useState(false);
  const [lines, setLines] = useState<LineDraft[]>([]);

  const { data: lpos = [] } = useQuery({
    queryKey: ["approved-lpos"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("lpo_header")
        .select("id,lpo_number,supplier_id,department_id,suppliers(supplier_name)")
        .eq("status", "APPROVED")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const { data: lpoLines } = useQuery({
    queryKey: ["lpo-lines", lpoId],
    enabled: Boolean(lpoId),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("lpo_lines")
        .select("id,item_id,quantity_ordered,items(item_code,item_description,unit)")
        .eq("lpo_id", lpoId);
      if (error) throw error;
      return data;
    },
  });

  useEffect(() => {
    if (!lpoLines) return;
    setLines(
      lpoLines.map((l) => ({
        lpo_line_id: l.id,
        item_id: l.item_id,
        item_code: l.items?.item_code ?? "",
        item_description: l.items?.item_description ?? "",
        unit: l.items?.unit ?? "",
        qty_ordered: Number(l.quantity_ordered),
        qty_received: String(l.quantity_ordered),
        item_condition: "OK",
        remarks: "",
      })),
    );
  }, [lpoLines]);

  const update = (index: number, patch: Partial<LineDraft>) =>
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)));

  const selectedLpo = lpos.find((l) => l.id === lpoId);

  const submit = useMutation({
    mutationFn: async () => {
      if (!selectedLpo) throw new Error("Select an approved purchase order");
      if (lines.length === 0) throw new Error("This order has no lines");
      const excess = lines.some((l) => Number(l.qty_received) > l.qty_ordered);
      if (excess && !override) throw new Error("Received quantity exceeds ordered quantity — approver override required");

      const receipt = receiptStatusFor(
        lines.map((l) => ({ qty_ordered: l.qty_ordered, qty_received: Number(l.qty_received || 0) })),
      );

      const { data: created, error } = await supabase
        .from("grn_header")
        .insert({
          grn_date: header.grn_date,
          lpo_id: selectedLpo.id,
          supplier_id: selectedLpo.supplier_id,
          department_id: selectedLpo.department_id,
          delivery_note_no: header.delivery_note_no || null,
          received_by: header.received_by || fullName,
          checked_by: header.checked_by || null,
          receipt_status: receipt,
          status: "PENDING",
          over_receipt_override: override,
          maker: user!.id,
          maker_name: fullName,
        })
        .select("id,grn_number")
        .single();
      if (error) throw error;

      const { error: lineError } = await supabase.from("grn_lines").insert(
        lines.map((l) => ({
          grn_id: created.id,
          lpo_line_id: l.lpo_line_id,
          item_id: l.item_id,
          qty_ordered: l.qty_ordered,
          qty_received: Number(l.qty_received || 0),
          item_condition: l.item_condition,
          remarks: l.remarks || null,
        })),
      );
      if (lineError) throw lineError;

      await supabase.from("approval_log").insert({
        doc_type: "GRN",
        doc_id: created.id,
        doc_number: created.grn_number,
        action: "SUBMITTED",
        actor: user!.id,
        actor_name: fullName,
      });

      return created;
    },
    onSuccess: (created) => {
      toast.success(`${created.grn_number} submitted for approval`);
      void navigate({ to: "/grn/$id", params: { id: created.id } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div>
      <PageHeader
        title="New goods received note"
        subtitle="Quantities load from the approved order. Shortages and excess are computed automatically."
      />

      <div className="grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-5">
        <div className="space-y-2 sm:col-span-2">
          <Label>Approved purchase order</Label>
          <Select value={lpoId} onValueChange={setLpoId}>
            <SelectTrigger>
              <SelectValue placeholder="Select approved LPO" />
            </SelectTrigger>
            <SelectContent>
              {lpos.map((l) => (
                <SelectItem key={l.id} value={l.id}>
                  {l.lpo_number} — {l.suppliers?.supplier_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="grn_date">GRN date</Label>
          <Input
            id="grn_date"
            type="date"
            value={header.grn_date}
            onChange={(e) => setHeader({ ...header, grn_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="dn">Delivery note no.</Label>
          <Input
            id="dn"
            value={header.delivery_note_no}
            onChange={(e) => setHeader({ ...header, delivery_note_no: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="rb">Received by</Label>
          <Input
            id="rb"
            placeholder={fullName}
            value={header.received_by}
            onChange={(e) => setHeader({ ...header, received_by: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cb">Checked by</Label>
          <Input id="cb" value={header.checked_by} onChange={(e) => setHeader({ ...header, checked_by: e.target.value })} />
        </div>
      </div>

      {lines.length > 0 ? (
        <>
          <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead className="text-right">Ordered</TableHead>
                  <TableHead className="w-32">Received</TableHead>
                  <TableHead className="text-right">Shortage / excess</TableHead>
                  <TableHead className="w-40">Condition</TableHead>
                  <TableHead>Remarks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lines.map((l, index) => {
                  const diff = Number(l.qty_received || 0) - l.qty_ordered;
                  return (
                    <TableRow key={l.lpo_line_id}>
                      <TableCell>
                        <span className="num text-xs text-muted-foreground">{l.item_code}</span>
                        <p className="text-sm">{l.item_description}</p>
                      </TableCell>
                      <TableCell className="num text-sm">{l.unit}</TableCell>
                      <TableCell className="num text-right">{qty(l.qty_ordered)}</TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.001"
                          value={l.qty_received}
                          onChange={(e) => update(index, { qty_received: e.target.value })}
                        />
                      </TableCell>
                      <TableCell
                        className={`num text-right ${diff === 0 ? "text-muted-foreground" : diff > 0 ? "text-warning" : "text-destructive"}`}
                      >
                        {diff > 0 ? `+${qty(diff)}` : qty(diff)}
                      </TableCell>
                      <TableCell>
                        <Select
                          value={l.item_condition}
                          onValueChange={(v) => update(index, { item_condition: v as ItemCondition })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {conditions.map((c) => (
                              <SelectItem key={c} value={c}>
                                {c.replace("_", " ")}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Input value={l.remarks} onChange={(e) => update(index, { remarks: e.target.value })} />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={override}
                disabled={!canOverride}
                onCheckedChange={(v) => setOverride(Boolean(v))}
              />
              Allow over-receipt beyond ordered quantity
              {canOverride ? "" : " (approver only)"}
            </label>
            <Button disabled={submit.isPending} onClick={() => submit.mutate()}>
              {submit.isPending ? "Saving…" : "Submit for approval"}
            </Button>
          </div>
        </>
      ) : (
        <p className="mt-6 rounded-md border border-dashed border-border bg-card/40 px-6 py-10 text-center text-sm text-muted-foreground">
          Select an approved purchase order to load its lines.
        </p>
      )}
    </div>
  );
}
