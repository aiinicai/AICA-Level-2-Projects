import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { PageHeader } from "@/components/procurement/PageHeader";
import { EmptyState } from "@/components/procurement/EmptyState";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth, type AppRole } from "@/hooks/useAuth";

export const Route = createFileRoute("/_authenticated/users")({
  head: () => ({meta: [{title: "Users — Easy AI Procura"}, {name: "description", content: "Users for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Users — Easy AI Procura"}, {property: "og:description", content: "Users for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),
  component: UsersPage,
});

const allRoles: AppRole[] = ["ADMIN", "MAKER", "APPROVER", "STOREKEEPER", "FINANCE_MAKER", "FINANCE_APPROVER"];

function UsersPage() {
  const { hasRole, refreshRoles, user } = useAuth();
  const isAdmin = hasRole("ADMIN");
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["users-roles"],
    queryFn: async () => {
      const [profiles, roles] = await Promise.all([
        supabase.from("profiles").select("id,full_name,email").order("full_name"),
        supabase.from("user_roles").select("id,user_id,role"),
      ]);
      if (profiles.error) throw profiles.error;
      return { profiles: profiles.data, roles: roles.data ?? [] };
    },
  });

  const toggle = useMutation({
    mutationFn: async ({ userId, role, on }: { userId: string; role: AppRole; on: boolean }) => {
      if (on) {
        const { error } = await supabase.from("user_roles").insert({ user_id: userId, role });
        if (error) throw error;
      } else {
        const { error } = await supabase.from("user_roles").delete().eq("user_id", userId).eq("role", role);
        if (error) throw error;
      }
    },
    onSuccess: async () => {
      toast.success("Roles updated");
      await qc.invalidateQueries({ queryKey: ["users-roles"] });
      await refreshRoles();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const has = (userId: string, role: AppRole) =>
    (data?.roles ?? []).some((r) => r.user_id === userId && r.role === role);

  return (
    <div>
      <PageHeader
        title="Users and roles"
        subtitle="Roles are stored separately from profiles and control every maker–checker action in the system."
      />

      {!isAdmin ? (
        <p className="mb-6 rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Only administrators can change role assignments.
        </p>
      ) : null}

      {isLoading ? (
        <EmptyState title="Loading users…" />
      ) : (data?.profiles ?? []).length === 0 ? (
        <EmptyState title="No users" />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                {allRoles.map((r) => (
                  <TableHead key={r} className="text-center text-[11px] uppercase">
                    {r.replace("_", " ")}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.profiles ?? []).map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <p className="font-medium">
                      {p.full_name}
                      {p.id === user?.id ? <span className="ml-2 text-xs text-muted-foreground">(you)</span> : null}
                    </p>
                    <p className="text-xs text-muted-foreground">{p.email}</p>
                  </TableCell>
                  {allRoles.map((role) => (
                    <TableCell key={role} className="text-center">
                      <Checkbox
                        checked={has(p.id, role)}
                        disabled={!isAdmin || toggle.isPending}
                        onCheckedChange={(v) => toggle.mutate({ userId: p.id, role, on: Boolean(v) })}
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
