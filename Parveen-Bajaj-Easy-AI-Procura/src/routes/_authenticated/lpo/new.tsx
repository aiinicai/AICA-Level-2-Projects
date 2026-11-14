import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { money } from "@/lib/procurement";

export const Route = createFileRoute("/_authenticated/lpo/new")({
  head: () => ({meta: [{title: "LPO entry — Easy AI Procura"}, {name: "description", content: "LPO entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "LPO entry — Easy AI Procura"}, {property: "og:description", content: "LPO entry for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: NewLpo,
});

type Line = { item_id: string; quantity_ordered: string; unit_price: string };

const emptyLine: Line = { item_id: "", quantity_ordered: "", unit_price: "" };

function NewLpo() {
  const { user, fullName } = useAuth();
  const navigate = useNavigate();

  const [header, setHeader] = useState({
    lpo_date: new Date().toISOString().slice(0, 10),
    supplier_id: "",
    department_id: "",
    delivery_location: "",
    payment_terms: "",
    remarks: "",
  });
  const [lines, setLines] = useState<Line[]>([{ ...emptyLine }]);

  const { data: suppliers = [] } = useQuery({
    queryKey: ["active-suppliers"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("suppliers")
        .select("id,supplier_code,supplier_name,payment_terms")
        .eq("status", "ACTIVE")
        .order("supplier_name");
      if (error) throw error;
      return data;
    },
  });

  const { data: departments = [] } = useQuery({
    queryKey: ["active-departments"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("departments")
        .select("id,department_code,department_name")
        .eq("status", "ACTIVE")
        .order("department_name");
      if (error) throw error;
      return data;
    },
  });

  const { data: items = [] } = useQuery({
    queryKey: ["active-items"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("items")
        .select("id,item_code,item_description,unit,standard_price")
        .eq("status", "ACTIVE")
        .order("item_code");
      if (error) throw error;
      return data;
    },
  });

  const itemById = useMemo(() => new Map(items.map((i) => [i.id, i])), [items]);

  const lineValue = (l: Line) => Number(l.quantity_ordered || 0) * Number(l.unit_price || 0);
  const total = lines.reduce((sum, l) => sum + lineValue(l), 0);

  const updateLine = (index: number, patch: Partial<Line>) =>
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)));

  const submit = useMutation({
    mutationFn: async (asDraft: boolean) => {
      const valid = lines.filter((l) => l.item_id && Number(l.quantity_ordered) > 0 && Number(l.unit_price) >= 0);
      if (!header.supplier_id || !header.department_id) throw new Error("Supplier and department are required");
      if (valid.length === 0) throw new Error("Add at least one line with item, quantity and price");

      const { data: created, error } = await supabase
        .from("lpo_header")
        .insert({
          lpo_date: header.lpo_date,
          supplier_id: header.supplier_id,
          department_id: header.department_id,
          delivery_location: header.delivery_location || null,
          payment_terms: header.payment_terms || null,
          remarks: header.remarks || null,
          total_value: valid.reduce((s, l) => s + lineValue(l), 0),
          status: asDraft ? "DRAFT" : "PENDING",
          maker: user!.id,
          maker_name: fullName,
        })
        .select("id,lpo_number")
        .single();
      if (error) throw error;

      const { error: lineError } = await supabase.from("lpo_lines").insert(
        valid.map((l) => ({
          lpo_id: created.id,
          item_id: l.item_id,
          quantity_ordered: Number(l.quantity_ordered),
          unit_price: Number(l.unit_price),
        })),
      );
      if (lineError) throw lineError;

      await supabase.from("approval_log").insert({
        doc_type: "LPO",
        doc_id: created.id,
        doc_number: created.lpo_number,
        action: asDraft ? "SAVED_DRAFT" : "SUBMITTED",
        actor: user!.id,
        actor_name: fullName,
      });

      return created;
    },
    onSuccess: (created) => {
      toast.success(`${created.lpo_number} saved`);
      void navigate({ to: "/lpo/$id", params: { id: created.id } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div>
      <PageHeader
        title="New purchase order"
        subtitle="The order number is generated by the system on save. Only active suppliers, departments and items are selectable."
      />

      <div className="grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="lpo_date">LPO date</Label>
          <Input
            id="lpo_date"
            type="date"
            value={header.lpo_date}
            onChange={(e) => setHeader({ ...header, lpo_date: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label>Supplier</Label>
          <Select
            value={header.supplier_id}
            onValueChange={(v) => {
              const s = suppliers.find((x) => x.id === v);
              setHeader((h) => ({ ...h, supplier_id: v, payment_terms: h.payment_terms || s?.payment_terms || "" }));
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select active supplier" />
            </SelectTrigger>
            <SelectContent>
              {suppliers.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.supplier_code} — {s.supplier_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Department</Label>
          <Select value={header.department_id} onValueChange={(v) => setHeader({ ...header, department_id: v })}>
            <SelectTrigger>
              <SelectValue placeholder="Select department" />
            </SelectTrigger>
            <SelectContent>
              {departments.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.department_code} — {d.department_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="loc">Delivery location</Label>
          <Input
            id="loc"
            value={header.delivery_location}
            onChange={(e) => setHeader({ ...header, delivery_location: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="terms">Payment terms</Label>
          <Input
            id="terms"
            value={header.payment_terms}
            onChange={(e) => setHeader({ ...header, payment_terms: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="rem">Remarks</Label>
          <Textarea
            id="rem"
            rows={1}
            value={header.remarks}
            onChange={(e) => setHeader({ ...header, remarks: e.target.value })}
          />
        </div>
      </div>

      <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[38%]">Item</TableHead>
              <TableHead>Unit</TableHead>
              <TableHead className="w-32">Quantity</TableHead>
              <TableHead className="w-36">Unit price</TableHead>
              <TableHead className="text-right">Line value</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {lines.map((l, index) => {
              const item = itemById.get(l.item_id);
              return (
                <TableRow key={index}>
                  <TableCell>
                    <Select
                      value={l.item_id}
                      onValueChange={(v) => {
                        const picked = itemById.get(v);
                        updateLine(index, {
                          item_id: v,
                          unit_price: l.unit_price || (picked?.standard_price ?? "").toString(),
                        });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select item" />
                      </SelectTrigger>
                      <SelectContent>
                        {items.map((i) => (
                          <SelectItem key={i.id} value={i.id}>
                            {i.item_code} — {i.item_description}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="num text-sm text-muted-foreground">{item?.unit ?? "—"}</TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min="0"
                      step="0.001"
                      value={l.quantity_ordered}
                      onChange={(e) => updateLine(index, { quantity_ordered: e.target.value })}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={l.unit_price}
                      onChange={(e) => updateLine(index, { unit_price: e.target.value })}
                    />
                  </TableCell>
                  <TableCell className="num text-right">{money(lineValue(l))}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setLines((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)))}
                    >
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <Button variant="outline" onClick={() => setLines((prev) => [...prev, { ...emptyLine }])}>
          Add line
        </Button>
        <div className="flex items-center gap-6">
          <p className="text-sm text-muted-foreground">
            Order total <span className="num ml-2 text-lg font-semibold text-foreground">{money(total)}</span>
          </p>
          <Button variant="outline" disabled={submit.isPending} onClick={() => submit.mutate(true)}>
            Save draft
          </Button>
          <Button disabled={submit.isPending} onClick={() => submit.mutate(false)}>
            Submit for approval
          </Button>
        </div>
      </div>
    </div>
  );
}
