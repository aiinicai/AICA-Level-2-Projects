import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { StatusBadge } from "@/components/procurement/StatusBadge";
import { EmptyState } from "@/components/procurement/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { money } from "@/lib/procurement";
import { CsvUploadDialog } from "@/components/procurement/CsvUploadDialog";
import { ITEM_TEMPLATE, parseItemImport, type ItemImportRow } from "@/lib/master-import";

export const Route = createFileRoute("/_authenticated/items")({
  head: () => ({meta: [{title: "Items — Easy AI Procura"}, {name: "description", content: "Items for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Items — Easy AI Procura"}, {property: "og:description", content: "Items for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: ItemsPage,
});

function ItemsPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole("ADMIN");
  const qc = useQueryClient();
  const [form, setForm] = useState({ item_code: "", item_description: "", unit: "", standard_price: "" });

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["items"],
    queryFn: async () => {
      const { data, error } = await supabase.from("items").select("*").order("item_code");
      if (error) throw error;
      return data;
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from("items").insert({
        item_code: form.item_code,
        item_description: form.item_description,
        unit: form.unit,
        standard_price: form.standard_price === "" ? null : Number(form.standard_price),
      });
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Item added");
      setForm({ item_code: "", item_description: "", unit: "", standard_price: "" });
      void qc.invalidateQueries({ queryKey: ["items"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggle = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "ACTIVE" | "INACTIVE" }) => {
      const { error } = await supabase.from("items").update({ status }).eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["items"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  const upload = useMutation({
    mutationFn: async (rows: ItemImportRow[]) => {
      const { error } = await supabase
        .from("items")
        .insert(rows.map((row) => ({ ...row, status: "ACTIVE" as const })));
      if (error) throw error;
    },
    onSuccess: (_data, rows) => {
      toast.success(`${rows.length} item${rows.length === 1 ? "" : "s"} added to the master`);
      void qc.invalidateQueries({ queryKey: ["items"] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Item master"
        subtitle="Administrator-controlled. Units auto-fill on purchase order lines; standard price is optional."
        actions={
          isAdmin ? (
            <CsvUploadDialog
              triggerLabel="Upload from file"
              title="Upload items from Excel or CSV"
              description="Rows that pass the checks are added straight to the item master as ACTIVE."
              templateHeaders={ITEM_TEMPLATE}
              templateExample={["PEN-01", "Ballpoint pen", "PCS", "120.50"]}
              templateFileName="item-template.csv"
              existingCodes={items.map((i) => i.item_code)}
              parse={parseItemImport}
              onImport={async (rows) => {
                await upload.mutateAsync(rows);
              }}
              isPending={upload.isPending}
            />
          ) : null
        }
      />

      {isAdmin ? (
        <form
          className="mb-8 grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="icode">Item code</Label>
            <Input
              id="icode"
              required
              value={form.item_code}
              onChange={(e) => setForm({ ...form, item_code: e.target.value })}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="idesc">Description</Label>
            <Input
              id="idesc"
              required
              value={form.item_description}
              onChange={(e) => setForm({ ...form, item_description: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="iunit">Unit</Label>
            <Input
              id="iunit"
              required
              placeholder="PCS"
              value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value.toUpperCase() })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="iprice">Standard price</Label>
            <Input
              id="iprice"
              type="number"
              step="0.01"
              min="0"
              value={form.standard_price}
              onChange={(e) => setForm({ ...form, standard_price: e.target.value })}
            />
          </div>
          <div className="sm:col-span-5">
            <Button type="submit" disabled={create.isPending}>
              Add item
            </Button>
          </div>
        </form>
      ) : (
        <p className="mb-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Only administrators can maintain the item master.
        </p>
      )}

      {isLoading ? (
        <EmptyState title="Loading items…" />
      ) : items.length === 0 ? (
        <EmptyState title="No items" hint="An administrator must add the first item." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead className="text-right">Standard price</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((i) => (
                <TableRow key={i.id}>
                  <TableCell className="num">{i.item_code}</TableCell>
                  <TableCell className="font-medium">{i.item_description}</TableCell>
                  <TableCell className="num text-sm">{i.unit}</TableCell>
                  <TableCell className="num text-right">
                    {i.standard_price === null ? "—" : money(i.standard_price)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={i.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    {isAdmin ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          toggle.mutate({ id: i.id, status: i.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" })
                        }
                      >
                        {i.status === "ACTIVE" ? "Deactivate" : "Activate"}
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
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
