import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Mail, ShieldCheck, Trash2, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/common/states";
import { useWorkspace } from "@/lib/store";
import { uid } from "@/lib/data/seed";
import type { Role } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/team")({
  head: () => ({
    meta: [
      { title: "Team & roles — The DASH" },
      { name: "description", content: "Invite teammates and control who can view, edit or administer your workspace." },
      { property: "og:title", content: "Team & roles — The DASH" },
      { property: "og:description", content: "Owner, admin, editor and viewer roles for your workspace." },
    ],
  }),
  component: TeamPage,
});

const ROLES: { id: Role; label: string; description: string }[] = [
  { id: "owner", label: "Owner", description: "Full control, including billing and deleting the workspace." },
  { id: "admin", label: "Admin", description: "Manage integrations, members and every dashboard." },
  { id: "editor", label: "Editor", description: "Create and edit dashboards and reports." },
  { id: "viewer", label: "Viewer", description: "View shared dashboards and reports only." },
];

function TeamPage() {
  const { members, upsertMember, removeMember, settings } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");

  return (
    <div className="pb-10">
      <PageHeader
        title="Team"
        description={`Members of ${settings.workspaceName} and what they're allowed to do.`}
        actions={
          <Button onClick={() => setOpen(true)}>
            <UserPlus className="size-4" aria-hidden /> Invite member
          </Button>
        }
      />

      <div className="space-y-5 px-4 py-6 sm:px-6 lg:px-8">
        <div className="panel overflow-x-auto">
          <table className="w-full min-w-[34rem] text-sm">
            <caption className="sr-only">Workspace members and their roles</caption>
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th scope="col" className="px-4 py-3 font-medium">Member</th>
                <th scope="col" className="px-4 py-3 font-medium">Role</th>
                <th scope="col" className="px-4 py-3 font-medium">Status</th>
                <th scope="col" className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium">{m.name}</p>
                    <p className="text-xs text-muted-foreground">{m.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      value={m.role}
                      disabled={m.role === "owner"}
                      onValueChange={(v) => {
                        upsertMember({ ...m, role: v as Role });
                        toast.success(`${m.name} is now ${v}`);
                      }}
                    >
                      <SelectTrigger className="h-9 w-[130px]" aria-label={`Role for ${m.name}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((r) => (
                          <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs capitalize text-muted-foreground">
                      {m.status === "invited" ? "Invite pending" : m.lastActive ?? "Active"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {m.role !== "owner" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Remove ${m.name}`}
                        onClick={() => {
                          removeMember(m.id);
                          toast.success(`${m.name} removed`);
                        }}
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <section className="panel p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="size-4 text-primary" aria-hidden /> What each role can do
          </h2>
          <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {ROLES.map((r) => (
              <div key={r.id} className="rounded-lg border bg-surface p-3">
                <dt className="text-sm font-medium">{r.label}</dt>
                <dd className="text-xs text-muted-foreground">{r.description}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-muted-foreground">
            Roles are stored per member so they can be enforced server-side once your workspace is connected to a
            backend.
          </p>
        </section>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Invite a teammate</DialogTitle>
            <DialogDescription>They'll get access as soon as they accept.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="invite-email">Work email</Label>
              <Input
                id="invite-email"
                type="email"
                value={email}
                placeholder="name@company.in"
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={role} onValueChange={(v) => setRole(v as Role)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROLES.filter((r) => r.id !== "owner").map((r) => (
                    <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={!email.includes("@")}
              onClick={() => {
                upsertMember({
                  id: uid(),
                  name: email.split("@")[0].replace(/[._]/g, " "),
                  email,
                  role,
                  status: "invited",
                });
                setOpen(false);
                setEmail("");
                toast.success("Invite recorded — email delivery needs a mail sender on your workspace");
              }}
            >
              <Mail className="size-4" aria-hidden /> Send invite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
