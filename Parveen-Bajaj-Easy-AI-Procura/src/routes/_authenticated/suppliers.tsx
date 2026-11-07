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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { stamp } from "@/lib/procurement";
import { CsvUploadDialog } from "@/components/procurement/CsvUploadDialog";
import { parseSupplierImport, SUPPLIER_TEMPLATE, type SupplierImportRow } from "@/lib/master-import";

export const Route = createFileRoute("/_authenticated/suppliers")({
  head: () => ({meta: [{title: "Suppliers — Easy AI Procura"}, {name: "description", content: "Suppliers for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Suppliers — Easy AI Procura"}, {property: "og:description", content: "Suppliers for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: SuppliersPage,
});

const blank = {
  supplier_code: "",
  supplier_name: "",
  address: "",
  contact_person: "",
  phone: "",
  email: "",
  vat_pin: "",
  payment_terms: "",
};

function SuppliersPage() {
  const { user, fullName, hasRole } = useAuth();
  const qc = useQueryClient();
  const [portalEmail, setPortalEmail] = useState("");
  const [portalSupplier, setPortalSupplier] = useState("");
  const [linking, setLinking] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blank);

  const canSubmit = hasRole("MAKER", "ADMIN");
  const isApprover = hasRole("APPROVER");

  const { data: suppliers = [], isLoading } = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const { data, error } = await supabase.from("suppliers").select("*").order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from("suppliers").insert({
        ...form,
        status: "PENDING",
        maker: user!.id,
        maker_name: fullName,
      });
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Supplier submitted for approval");
      setForm(blank);
      setOpen(false);
      void qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const decide = useMutation({
    mutationFn: async ({ id, code, approve }: { id: string; code: string; approve: boolean }) => {
      const { error } = await supabase
        .from("suppliers")
        .update({
          status: approve ? "ACTIVE" : "INACTIVE",
          approver: user!.id,
          approver_name: fullName,
          approved_at: new Date().toISOString(),
        })
        .eq("id", id);
      if (error) throw error;
      await supabase.from("approval_log").insert({
        doc_type: "SUPPLIER",
        doc_id: id,
        doc_number: code,
        action: approve ? "APPROVED" : "REJECTED",
        actor: user!.id,
        actor_name: fullName,
      });
    },
    onSuccess: () => {
      toast.success("Supplier status updated");
      void qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const upload = useMutation({
    mutationFn: async (rows: SupplierImportRow[]) => {
      const { error } = await supabase.from("suppliers").insert(
        rows.map((row) => ({
          ...row,
          status: "PENDING" as const,
          maker: user!.id,
          maker_name: fullName,
        })),
      );
      if (error) throw error;
    },
    onSuccess: (_data, rows) => {
      toast.success(
        `${rows.length} supplier${rows.length === 1 ? "" : "s"} submitted for approval`,
        { description: "An approver who did not upload the file must activate them." },
      );
      void qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });

  const field = (key: keyof typeof blank, label: string, required = false, type = "text") => (
    <div className="space-y-2">
      <Label htmlFor={key}>{label}</Label>
      <Input
        id={key}
        type={type}
        required={required}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </div>
  );

  return (
    <div>
      <PageHeader
        title="Supplier master"
        subtitle="Makers register suppliers; approvers activate them. Only ACTIVE suppliers appear on purchase orders."
        actions={
          canSubmit ? (
            <>
            <CsvUploadDialog
              triggerLabel="Upload from file"
              title="Upload suppliers from Excel or CSV"
              description="Each supplier is saved as PENDING. An approver who did not upload the file must activate them."
              templateHeaders={SUPPLIER_TEMPLATE}
              templateExample={[
                "S-001",
                "Acme Stationers",
                "Jane Mwangi",
                "0700111222",
                "jane@acme.co.ke",
                "P000123456",
                "Net 30",
                "Naivasha Road, Nairobi",
              ]}
              templateFileName="supplier-template.csv"
              existingCodes={suppliers.map((s) => s.supplier_code)}
              parse={parseSupplierImport}
              onImport={async (rows) => {
                await upload.mutateAsync(rows);
              }}
              isPending={upload.isPending}
            />
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button>New supplier</Button>
              </DialogTrigger>
              <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Register supplier</DialogTitle>
                  <DialogDescription>Saved as PENDING until an approver activates it.</DialogDescription>
                </DialogHeader>
                <form
                  className="grid gap-4 sm:grid-cols-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    create.mutate();
                  }}
                >
                  {field("supplier_code", "Supplier code", true)}
                  {field("supplier_name", "Supplier name", true)}
                  {field("contact_person", "Contact person")}
                  {field("phone", "Phone")}
                  {field("email", "Email", false, "email")}
                  {field("vat_pin", "VAT / PIN")}
                  {field("payment_terms", "Payment terms")}
                  {field("address", "Address")}
                  <DialogFooter className="sm:col-span-2">
                    <Button type="submit" disabled={create.isPending}>
                      {create.isPending ? "Saving…" : "Submit for approval"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
            </>
          ) : null
        }
      />

      {hasRole("ADMIN") ? <form className="mb-6 flex flex-wrap items-end gap-3" onSubmit={e => {
        e.preventDefault(); setLinking(true);
        void Promise.resolve(supabase.rpc('link_supplier_account', {p_email: portalEmail, p_supplier: portalSupplier})).then(({error}) => {
          if(error) toast.error(error.message); else {toast.success('Supplier portal access granted');setPortalEmail('');}
        }).finally(() => setLinking(false));
      }}><div><Label htmlFor="portal-supplier">Approved supplier</Label><select id="portal-supplier" required value={portalSupplier} onChange={e=>setPortalSupplier(e.target.value)} className="block h-9 max-w-full rounded border border-input bg-background px-2 text-sm"><option value="">Select supplier</option>{suppliers.filter(s=>s.status==='ACTIVE').map(s=><option key={s.id} value={s.id}>{s.supplier_code} · {s.supplier_name}</option>)}</select></div><div><Label htmlFor="portal-email">Registered supplier email</Label><Input id="portal-email" type="email" required value={portalEmail} onChange={e=>setPortalEmail(e.target.value)}/></div><Button disabled={linking}>Grant portal access</Button></form> : null}
      {isLoading ? (
        <EmptyState title="Loading suppliers…" />
      ) : suppliers.length === 0 ? (
        <EmptyState title="No suppliers yet" hint="A maker must register the first supplier." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>VAT / PIN</TableHead>
                <TableHead>Terms</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Maker</TableHead>
                <TableHead>Approved</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {suppliers.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="num">{s.supplier_code}</TableCell>
                  <TableCell className="font-medium">{s.supplier_name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {s.contact_person || "—"}
                    {s.phone ? ` · ${s.phone}` : ""}
                  </TableCell>
                  <TableCell className="num text-sm">{s.vat_pin || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.payment_terms || "—"}</TableCell>
                  <TableCell>
                    <StatusBadge status={s.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.maker_name || "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {s.approved_at ? `${s.approver_name ?? ""} ${stamp(s.approved_at)}` : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {s.status === "PENDING" && isApprover && s.maker !== user?.id ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          onClick={() => decide.mutate({ id: s.id, code: s.supplier_code, approve: true })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => decide.mutate({ id: s.id, code: s.supplier_code, approve: false })}
                        >
                          Reject
                        </Button>
                      </div>
                    ) : s.status === "PENDING" && s.maker === user?.id ? (
                      <span className="text-xs text-muted-foreground">Awaiting another approver</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">Locked</span>
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
