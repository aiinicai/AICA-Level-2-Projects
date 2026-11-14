import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { money, qty } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/invoices/new")({
  head: () => ({meta: [{title: "Invoice entry — Easy AI Procura"}, {name: "description", content: "Invoice entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Invoice entry — Easy AI Procura"}, {property: "og:description", content: "Invoice entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: NewInvoice,
});

type LineDraft = {
  grn_line_id: string;
  item_id: string;
  item_code: string;
  item_description: string;
  quantity: number;
  lpo_price: number;
  invoice_price: string;
};

function NewInvoice() {
  const { user, fullName } = useAuth();
  const navigate = useNavigate();

  const [grnId, setGrnId] = useState("");
  const [header, setHeader] = useState({
    invoice_number: "",
    invoice_date: new Date().toISOString().slice(0, 10),
    vat_rate: "16",
  });
  const [lines, setLines] = useState<LineDraft[]>([]);

  const { data: grns = [] } = useQuery({
    queryKey: ["approved-grns"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("grn_header")
        .select("id,grn_number,supplier_id,lpo_id,suppliers(supplier_name)")
        .eq("status", "APPROVED")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const { data: grnLines } = useQuery({
    queryKey: ["grn-lines-for-invoice", grnId],
    enabled: Boolean(grnId),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("grn_lines")
        .select("id,item_id,qty_received,items(item_code,item_description),lpo_lines(unit_price)")
        .eq("grn_id", grnId);
      if (error) throw error;
      return data;
    },
  });

  useEffect(() => {
    if (!grnLines) return;
    setLines(
      grnLines
        .filter((l) => Number(l.qty_received) > 0)
        .map((l) => ({
          grn_line_id: l.id,
          item_id: l.item_id,
          item_code: l.items?.item_code ?? "",
          item_description: l.items?.item_description ?? "",
          quantity: Number(l.qty_received),
          lpo_price: Number(l.lpo_lines?.unit_price ?? 0),
          invoice_price: String(l.lpo_lines?.unit_price ?? 0),
        })),
    );
  }, [grnLines]);

  const net = lines.reduce((s, l) => s + l.quantity * Number(l.invoice_price || 0), 0);
  const vat = (net * Number(header.vat_rate || 0)) / 100;
  const selectedGrn = grns.find((g) => g.id === grnId);

  const submit = useMutation({
    mutationFn: async () => {
      if (!selectedGrn) throw new Error("Select an approved goods received note");
      if (!header.invoice_number.trim()) throw new Error("Supplier invoice number is required");
      if (lines.length === 0) throw new Error("No received lines to invoice");

      const { data: created, error } = await supabase
        .from("invoices")
        .insert({
          invoice_number: header.invoice_number.trim(),
          invoice_date: header.invoice_date,
          supplier_id: selectedGrn.supplier_id,
          grn_id: selectedGrn.id,
          lpo_id: selectedGrn.lpo_id,
          invoice_value: net,
          vat_amount: vat,
          status: "PENDING",
          maker: user!.id,
          maker_name: fullName,
        })
        .select("id,internal_number")
        .single();
      if (error) throw error;

      const { error: lineError } = await supabase.from("invoice_lines").insert(
        lines.map((l) => ({
          invoice_id: created.id,
          grn_line_id: l.grn_line_id,
          item_id: l.item_id,
          quantity: l.quantity,
          lpo_price: l.lpo_price,
          invoice_price: Number(l.invoice_price || 0),
        })),
      );
      if (lineError) throw lineError;

      await supabase.from("approval_log").insert({
        doc_type: "INVOICE",
        doc_id: created.id,
        doc_number: created.internal_number,
        action: "SUBMITTED",
        actor: user!.id,
        actor_name: fullName,
      });

      return created;
    },
    onSuccess: (created) => {
      toast.success(`${created.internal_number} submitted for approval`);
      void navigate({ to: "/invoices/$id", params: { id: created.id } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div>
      <PageHeader
        title="New supplier invoice"
        subtitle="Quantities are fixed by the goods received note. Any price above the order price is flagged as a variance."
      />

      <div className="grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-4">
        <div className="space-y-2 sm:col-span-2">
          <Label>Approved goods received note</Label>
          <Select value={grnId} onValueChange={setGrnId}>
            <SelectTrigger>
              <SelectValue placeholder="Select approved GRN" />
            </SelectTrigger>
            <SelectContent>
              {grns.map((g) => (
                <SelectItem key={g.id} value={g.id}>
                  {g.grn_number} — {g.suppliers?.supplier_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="inv_no">Supplier invoice no.</Label>
          <Input
            id="inv_no"
            value={header.invoice_number}
            onChange={(e) => setHeader({ ...header, invoice_number: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="inv_date">Invoice date</Label>
          <Input
            id="inv_date"
            type="date"
            value={header.invoice_date}
            onChange={(e) => setHeader({ ...header, invoice_date: e.target.value })}
          />
        </div>
      </div>

      {lines.length > 0 ? (
        <>
          <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead className="text-right">Qty (GRN)</TableHead>
                  <TableHead className="text-right">LPO price</TableHead>
                  <TableHead className="w-36">Invoice price</TableHead>
                  <TableHead className="text-right">Variance</TableHead>
                  <TableHead className="text-right">Line value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lines.map((l, index) => {
                  const variance = Number(l.invoice_price || 0) - l.lpo_price;
                  return (
                    <TableRow key={l.grn_line_id}>
                      <TableCell>
                        <span className="num text-xs text-muted-foreground">{l.item_code}</span>
                        <p className="text-sm">{l.item_description}</p>
                      </TableCell>
                      <TableCell className="num text-right">{qty(l.quantity)}</TableCell>
                      <TableCell className="num text-right">{money(l.lpo_price)}</TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          value={l.invoice_price}
                          onChange={(e) =>
                            setLines((prev) =>
                              prev.map((x, i) => (i === index ? { ...x, invoice_price: e.target.value } : x)),
                            )
                          }
                        />
                      </TableCell>
                      <TableCell
                        className={`num text-right ${variance > 0 ? "text-destructive font-medium" : variance < 0 ? "text-success" : "text-muted-foreground"}`}
                      >
                        {variance > 0 ? `+${money(variance)}` : money(variance)}
                      </TableCell>
                      <TableCell className="num text-right">
                        {money(l.quantity * Number(l.invoice_price || 0))}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex flex-wrap items-end justify-between gap-4 rounded-lg border border-border bg-card p-5">
            <div className="w-32 space-y-2">
              <Label htmlFor="vat">VAT rate %</Label>
              <Input
                id="vat"
                type="number"
                min="0"
                step="0.01"
                value={header.vat_rate}
                onChange={(e) => setHeader({ ...header, vat_rate: e.target.value })}
              />
            </div>
            <dl className="grid grid-cols-3 gap-8 text-sm">
              <div>
                <dt className="text-xs uppercase text-muted-foreground">Net</dt>
                <dd className="num mt-1 text-base">{money(net)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-muted-foreground">VAT</dt>
                <dd className="num mt-1 text-base">{money(vat)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-muted-foreground">Total</dt>
                <dd className="num mt-1 text-lg font-semibold">{money(net + vat)}</dd>
              </div>
            </dl>
            <Button disabled={submit.isPending} onClick={() => submit.mutate()}>
              {submit.isPending ? "Saving…" : "Submit for approval"}
            </Button>
          </div>
        </>
      ) : (
        <p className="mt-6 rounded-md border border-dashed border-border bg-card/40 px-6 py-10 text-center text-sm text-muted-foreground">
          Select an approved goods received note to load its received quantities.
        </p>
      )}
    </div>
  );
}
