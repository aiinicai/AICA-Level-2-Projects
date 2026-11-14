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

export const Route = createFileRoute("/_authenticated/departments")({
  head: () => ({meta: [{title: "Departments — Easy AI Procura"}, {name: "description", content: "Departments for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Departments — Easy AI Procura"}, {property: "og:description", content: "Departments for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: DepartmentsPage,
});

function DepartmentsPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole("ADMIN");
  const qc = useQueryClient();
  const [form, setForm] = useState({ department_code: "", department_name: "", hod: "" });

  const { data: departments = [], isLoading } = useQuery({
    queryKey: ["departments"],
    queryFn: async () => {
      const { data, error } = await supabase.from("departments").select("*").order("department_code");
      if (error) throw error;
      return data;
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from("departments").insert(form);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Department added");
      setForm({ department_code: "", department_name: "", hod: "" });
      void qc.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggle = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: "ACTIVE" | "INACTIVE" }) => {
      const { error } = await supabase.from("departments").update({ status }).eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["departments"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div>
      <PageHeader
        title="Department master"
        subtitle="Administrator-controlled. Departments are selected from a dropdown on every purchase order."
      />

      {isAdmin ? (
        <form
          className="mb-8 grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-4"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="code">Department code</Label>
            <Input
              id="code"
              required
              value={form.department_code}
              onChange={(e) => setForm({ ...form, department_code: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Department name</Label>
            <Input
              id="name"
              required
              value={form.department_name}
              onChange={(e) => setForm({ ...form, department_name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hod">Head of department</Label>
            <Input id="hod" value={form.hod} onChange={(e) => setForm({ ...form, hod: e.target.value })} />
          </div>
          <div className="flex items-end">
            <Button type="submit" className="w-full" disabled={create.isPending}>
              Add department
            </Button>
          </div>
        </form>
      ) : (
        <p className="mb-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Only administrators can add or deactivate departments.
        </p>
      )}

      {isLoading ? (
        <EmptyState title="Loading departments…" />
      ) : departments.length === 0 ? (
        <EmptyState title="No departments" hint="An administrator must add the first department." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Head of department</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {departments.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="num">{d.department_code}</TableCell>
                  <TableCell className="font-medium">{d.department_name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.hod || "—"}</TableCell>
                  <TableCell>
                    <StatusBadge status={d.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    {isAdmin ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          toggle.mutate({ id: d.id, status: d.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" })
                        }
                      >
                        {d.status === "ACTIVE" ? "Deactivate" : "Activate"}
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
