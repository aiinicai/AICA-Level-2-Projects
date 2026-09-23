import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Copy, LayoutDashboard, MoreHorizontal, Plus, Star, Trash2 } from "lucide-react";
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
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState, PageHeader } from "@/components/common/states";
import { useWorkspace } from "@/lib/store";
import { relativeTime } from "@/lib/format";
import { SEED_DASHBOARDS } from "@/lib/data/seed";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboards/")({
  head: () => ({
    meta: [
      { title: "Dashboards — The DASH" },
      { name: "description", content: "Create, duplicate and share interactive business dashboards built on live data." },
      { property: "og:title", content: "Dashboards — The DASH" },
      { property: "og:description", content: "Create, duplicate and share interactive business dashboards." },
    ],
  }),
  component: DashboardsPage,
});

function DashboardsPage() {
  const { dashboards, hydrated, createDashboard, duplicateDashboard, deleteDashboard, updateDashboard } = useWorkspace();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [template, setTemplate] = useState<string>("blank");

  const create = () => {
    const from = template === "blank" ? undefined : SEED_DASHBOARDS.find((d) => d.id === template);
    const created = createDashboard(name.trim() || "Untitled dashboard", from);
    setOpen(false);
    setName("");
    toast.success("Dashboard created");
    navigate({ to: "/dashboards/$dashboardId", params: { dashboardId: created.id } });
  };

  return (
    <div className="pb-10">
      <PageHeader
        title="Dashboards"
        description="Interactive views of your business, built from reusable widgets."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="size-4" aria-hidden /> New dashboard
          </Button>
        }
      />

      <div className="px-4 py-6 sm:px-6 lg:px-8">
        {dashboards.length === 0 ? (
          <EmptyState
            icon={LayoutDashboard}
            title="No dashboards"
            description="Build your first dashboard from a template, or start with a blank canvas."
            action={<Button onClick={() => setOpen(true)}>Create dashboard</Button>}
          />
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {dashboards.map((d) => (
              <li key={d.id} className="panel group flex flex-col p-4 transition hover:shadow-soft">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to="/dashboards/$dashboardId"
                    params={{ dashboardId: d.id }}
                    className="min-w-0 flex-1"
                  >
                    <h2 className="truncate text-sm font-semibold">{d.name}</h2>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {d.description || "No description yet."}
                    </p>
                  </Link>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="size-7" aria-label={`${d.name} options`}>
                        <MoreHorizontal className="size-4" aria-hidden />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onSelect={() => updateDashboard(d.id, { favourite: !d.favourite })}>
                        <Star className="size-4" aria-hidden /> {d.favourite ? "Unfavourite" : "Favourite"}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={() => {
                          duplicateDashboard(d.id);
                          toast.success("Dashboard duplicated");
                        }}
                      >
                        <Copy className="size-4" aria-hidden /> Duplicate
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onSelect={() => {
                          deleteDashboard(d.id);
                          toast.success("Dashboard deleted");
                        }}
                      >
                        <Trash2 className="size-4" aria-hidden /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <dl className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  <div>
                    <dt className="sr-only">Widgets</dt>
                    <dd className="num">{d.widgets.length} widgets</dd>
                  </div>
                  <div>
                    <dt className="sr-only">Visibility</dt>
                    <dd className="capitalize">{d.visibility}</dd>
                  </div>
                  <div className="ml-auto">
                    <dt className="sr-only">Updated</dt>
                    <dd>{hydrated ? relativeTime(d.updatedAt) : ""}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New dashboard</DialogTitle>
            <DialogDescription>Start blank or from one of the ready-made templates.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dash-name">Name</Label>
              <Input
                id="dash-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Monthly P&L"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Template</Label>
              <div className="grid grid-cols-1 gap-2">
                {[{ id: "blank", name: "Blank dashboard", description: "Start with an empty grid." }, ...SEED_DASHBOARDS].map(
                  (t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setTemplate(t.id)}
                      className={`rounded-lg border p-3 text-left transition ${
                        template === t.id ? "border-primary bg-primary-soft" : "hover:border-border-strong"
                      }`}
                    >
                      <p className="text-sm font-medium">{t.name}</p>
                      <p className="text-xs text-muted-foreground">{t.description}</p>
                    </button>
                  ),
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={create}>Create dashboard</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
