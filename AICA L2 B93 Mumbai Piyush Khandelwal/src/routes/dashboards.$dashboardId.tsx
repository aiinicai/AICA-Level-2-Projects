import { useMemo, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ChevronRight,
  Copy,
  Download,
  Eye,
  LayoutDashboard,
  Pencil,
  Plus,
  Redo2,
  Share2,
  Trash2,
  Undo2,
} from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState, PageHeader } from "@/components/common/states";
import { DashboardGrid, WIDTH_STEPS } from "@/components/dashboard/DashboardGrid";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { WidgetConfigPanel } from "@/components/dashboard/WidgetConfigPanel";
import { DrilldownSheet } from "@/components/dashboard/DrilldownSheet";
import { useWorkspace } from "@/lib/store";
import { uid } from "@/lib/data/seed";
import type { Dashboard, DashboardFilterDef, Widget } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboards/$dashboardId")({
  head: () => ({
    meta: [
      { title: "Dashboard builder — The DASH" },
      { name: "description", content: "Arrange widgets, apply global filters and drill into the records behind every number." },
      { property: "og:title", content: "Dashboard builder — The DASH" },
      { property: "og:description", content: "Arrange widgets, apply filters and drill into your records." },
    ],
  }),
  component: DashboardDetail,
});

function newWidget(): Widget {
  return {
    id: uid(),
    type: "bar",
    title: "New widget",
    options: { format: "currency", showGrid: true, colorIndex: 0, drilldown: true },
    layout: { w: 6, h: 4 },
    query: {
      sourceId: "tally",
      dataset: "sales_invoices",
      groupBy: ["region"],
      measures: [{ field: "invoice_amount", aggregation: "sum" }],
      limit: 10,
    },
  };
}

function DashboardDetail() {
  const { dashboardId } = Route.useParams();
  const navigate = useNavigate();
  const {
    dashboards,
    updateDashboard,
    deleteDashboard,
    duplicateDashboard,
    addWidget,
    updateWidget,
    removeWidget,
    moveWidget,
  } = useWorkspace();

  const dashboard = dashboards.find((d) => d.id === dashboardId);
  const [editing, setEditing] = useState(false);
  const [configWidget, setConfigWidget] = useState<Widget | null>(null);
  const [drilldown, setDrilldown] = useState<Widget | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [name, setName] = useState(dashboard?.name ?? "");
  const [history, setHistory] = useState<Dashboard[]>([]);
  const [future, setFuture] = useState<Dashboard[]>([]);

  const filterValues = dashboard?.filters ?? [];
  const snapshot = useMemo(() => dashboard && JSON.parse(JSON.stringify(dashboard)), [dashboard]);

  if (!dashboard) {
    return (
      <div className="p-6">
        <EmptyState
          icon={LayoutDashboard}
          title="Dashboard not found"
          description="It may have been deleted or the link is out of date."
          action={
            <Button asChild>
              <Link to="/dashboards">Back to dashboards</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const pushHistory = () => {
    setHistory((h) => [...h.slice(-19), snapshot as Dashboard]);
    setFuture([]);
  };

  const undo = () => {
    const prev = history[history.length - 1];
    if (!prev) return;
    setHistory((h) => h.slice(0, -1));
    setFuture((f) => [...f, snapshot as Dashboard]);
    updateDashboard(dashboard.id, { widgets: prev.widgets, filters: prev.filters });
  };

  const redo = () => {
    const next = future[future.length - 1];
    if (!next) return;
    setFuture((f) => f.slice(0, -1));
    setHistory((h) => [...h, snapshot as Dashboard]);
    updateDashboard(dashboard.id, { widgets: next.widgets, filters: next.filters });
  };

  const setFilters = (filters: DashboardFilterDef[]) => updateDashboard(dashboard.id, { filters });

  return (
    <div className="pb-14">
      <PageHeader
        breadcrumb={
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
            <Link to="/dashboards" className="hover:text-foreground">
              Dashboards
            </Link>
            <ChevronRight className="size-3" aria-hidden />
            <span className="text-foreground">{dashboard.name}</span>
          </nav>
        }
        title={dashboard.name}
        description={dashboard.description}
        actions={
          <>
            {editing && (
              <>
                <Button variant="ghost" size="icon" aria-label="Undo" disabled={!history.length} onClick={undo}>
                  <Undo2 className="size-4" aria-hidden />
                </Button>
                <Button variant="ghost" size="icon" aria-label="Redo" disabled={!future.length} onClick={redo}>
                  <Redo2 className="size-4" aria-hidden />
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    pushHistory();
                    const w = newWidget();
                    addWidget(dashboard.id, w);
                    setConfigWidget(w);
                  }}
                >
                  <Plus className="size-4" aria-hidden /> Add widget
                </Button>
              </>
            )}
            <Button variant="outline" onClick={() => setRenaming(true)}>
              <Pencil className="size-4" aria-hidden />
              <span className="sr-only sm:not-sr-only">Rename</span>
            </Button>
            <Button variant="outline" onClick={() => setShareOpen(true)}>
              <Share2 className="size-4" aria-hidden />
              <span className="sr-only sm:not-sr-only">Share</span>
            </Button>
            <Button variant={editing ? "default" : "outline"} onClick={() => setEditing((e) => !e)}>
              {editing ? (
                <>
                  <Eye className="size-4" aria-hidden /> Save &amp; preview
                </>
              ) : (
                <>
                  <Pencil className="size-4" aria-hidden /> Edit layout
                </>
              )}
            </Button>
          </>
        }
      />

      <div className="space-y-4 px-4 py-5 sm:px-6 lg:px-8">
        <FilterBar
          filters={filterValues}
          onChange={(id, value) => setFilters(filterValues.map((f) => (f.id === id ? { ...f, value } : f)))}
          onAdd={(filter) => setFilters([...filterValues, filter])}
          onRemove={(id) => setFilters(filterValues.filter((f) => f.id !== id))}
        />

        {dashboard.widgets.length === 0 ? (
          <EmptyState
            icon={LayoutDashboard}
            title="This dashboard is empty"
            description="Add your first widget, or build a query in Data Explorer and push it here."
            action={
              <div className="flex gap-2">
                <Button
                  onClick={() => {
                    setEditing(true);
                    const w = newWidget();
                    addWidget(dashboard.id, w);
                    setConfigWidget(w);
                  }}
                >
                  <Plus className="size-4" aria-hidden /> Add widget
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/explorer">Open Data Explorer</Link>
                </Button>
              </div>
            }
          />
        ) : (
          <DashboardGrid
            widgets={dashboard.widgets}
            filters={filterValues}
            editing={editing}
            onEdit={(w) => setConfigWidget(w)}
            onDrilldown={(w) => setDrilldown(w)}
            onDuplicate={(w) => {
              pushHistory();
              addWidget(dashboard.id, { ...w, id: uid(), title: `${w.title} (copy)` });
              toast.success("Widget duplicated");
            }}
            onDelete={(w) => {
              pushHistory();
              removeWidget(dashboard.id, w.id);
              toast.success("Widget removed");
            }}
            onResize={(w, delta) => {
              pushHistory();
              const i = WIDTH_STEPS.indexOf(w.layout.w);
              const next = WIDTH_STEPS[Math.min(WIDTH_STEPS.length - 1, Math.max(0, (i < 0 ? 2 : i) + delta))];
              updateWidget(dashboard.id, w.id, { layout: { ...w.layout, w: next } });
            }}
            onReorder={(from, to) => {
              pushHistory();
              moveWidget(dashboard.id, from, to);
            }}
          />
        )}

        {editing && (
          <p className="text-xs text-muted-foreground">
            Drag a widget onto another to reorder. Use the widget menu to resize, duplicate, export or delete.
          </p>
        )}

        <div className="flex flex-wrap gap-2 border-t pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const copy = duplicateDashboard(dashboard.id);
              if (copy) navigate({ to: "/dashboards/$dashboardId", params: { dashboardId: copy.id } });
            }}
          >
            <Copy className="size-4" aria-hidden /> Duplicate dashboard
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Download className="size-4" aria-hidden /> Export / print
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={() => {
              deleteDashboard(dashboard.id);
              toast.success("Dashboard deleted");
              navigate({ to: "/dashboards" });
            }}
          >
            <Trash2 className="size-4" aria-hidden /> Delete
          </Button>
        </div>
      </div>

      {configWidget && (
        <WidgetConfigPanel
          key={configWidget.id}
          widget={configWidget}
          open
          onOpenChange={(o) => !o && setConfigWidget(null)}
          onSave={(w) => {
            pushHistory();
            updateWidget(dashboard.id, w.id, w);
            toast.success("Widget saved");
          }}
        />
      )}

      <DrilldownSheet widget={drilldown} filters={filterValues} onOpenChange={(o) => !o && setDrilldown(null)} />

      <Dialog open={renaming} onOpenChange={setRenaming}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename dashboard</DialogTitle>
            <DialogDescription>Give this dashboard a clear, shareable name.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="rename">Name</Label>
            <Input id="rename" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRenaming(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                updateDashboard(dashboard.id, { name: name.trim() || dashboard.name });
                setRenaming(false);
                toast.success("Dashboard renamed");
              }}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Share “{dashboard.name}”</DialogTitle>
            <DialogDescription>Choose who can open this dashboard.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>Visibility</Label>
              <Select
                value={dashboard.visibility}
                onValueChange={(v) => updateDashboard(dashboard.id, { visibility: v as Dashboard["visibility"] })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">Private — only me</SelectItem>
                  <SelectItem value="workspace">Workspace — everyone in Acme</SelectItem>
                  <SelectItem value="link">Anyone with the link (view only)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {dashboard.visibility === "link" && (
              <div className="space-y-2">
                <Label htmlFor="share-link">Share link</Label>
                <div className="flex gap-2">
                  <Input
                    id="share-link"
                    readOnly
                    value={typeof window === "undefined" ? "" : `${window.location.origin}/dashboards/${dashboard.id}`}
                  />
                  <Button
                    variant="outline"
                    onClick={() => {
                      navigator.clipboard
                        ?.writeText(`${window.location.origin}/dashboards/${dashboard.id}`)
                        .then(() => toast.success("Link copied"))
                        .catch(() => toast.error("Couldn't copy the link"));
                    }}
                  >
                    Copy
                  </Button>
                </div>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Roles are enforced per workspace member in Team settings.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setShareOpen(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
