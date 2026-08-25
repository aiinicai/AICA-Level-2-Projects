import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import { EngagementActions } from "@/components/engagements/engagement-actions";
import { EngagementFormDialog } from "@/components/engagements/engagement-form-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate, formatDateTime } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canCreateEngagement } from "@/lib/permissions";
import { services } from "@/services";
import type { EngagementListItem, EngagementListQuery } from "@/services/engagement.service";
import { LIFECYCLE_STAGES } from "@/types/common";
import {
  AUDIT_AREAS,
  AUDIT_TYPES,
  ENGAGEMENT_STATUSES,
  ENGAGEMENT_STATUS_TONES,
  resolveStage,
  type EngagementFormValues,
} from "@/types/engagement";

const COLUMNS = [
  { key: "ref", header: "Reference", width: "110px" },
  { key: "client", header: "Client" },
  { key: "title", header: "Engagement title", width: "260px" },
  { key: "type", header: "Audit type" },
  { key: "area", header: "Audit area" },
  { key: "period", header: "Audit period" },
  { key: "location", header: "Location" },
  { key: "manager", header: "Engagement manager" },
  { key: "owner", header: "Process owner" },
  { key: "start", header: "Planned start" },
  { key: "completion", header: "Planned completion" },
  { key: "due", header: "Reporting due" },
  { key: "stage", header: "Lifecycle stage" },
  { key: "status", header: "Status" },
  { key: "updated", header: "Last updated" },
  { key: "actions", header: "Actions", align: "right" as const },
];

export function EngagementsPage() {
  const { role } = useRole();
  const actor = useActor();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useCachedState("engagements.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("engagements.filters", {});
  const [dateRange, setDateRange] = useCachedState("engagements.dates", { from: "", to: "" });
  const [sortBy, setSortBy] = useCachedState<NonNullable<EngagementListQuery["sortBy"]>>(
    "engagements.sortBy",
    "reference",
  );
  const [pageSize, setPageSize] = useCachedState("engagements.pageSize", 10);
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<EngagementListItem | null>(null);

  const clientsQuery = useQuery({
    queryKey: ["clients", "options"],
    queryFn: () => services.clients.list({ pageSize: 500 }),
  });
  const clients = clientsQuery.data?.items ?? [];

  const query: EngagementListQuery = {
    search,
    clientId: filters.clientId,
    auditType: filters.auditType,
    auditArea: filters.auditArea,
    status: filters.status,
    stage: filters.stage,
    manager: filters.manager,
    plannedFrom: dateRange.from || undefined,
    plannedTo: dateRange.to || undefined,
    sortBy,
    page,
    pageSize,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["engagements", "list", query],
    queryFn: () => services.engagements.list(query),
  });

  const managers = Array.from(
    new Set((clientsQuery.isSuccess ? data?.items ?? [] : []).map((item) => item.engagementManager)),
  );

  const saveMutation = useMutation({
    mutationFn: (values: EngagementFormValues) =>
      editing
        ? services.engagements.update(editing.id, values, actor)
        : services.engagements.create(values, actor),
    onSuccess: (record) => {
      setFormOpen(false);
      setEditing(null);
      void queryClient.invalidateQueries({ queryKey: ["engagements"] });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      void queryClient.invalidateQueries({ queryKey: ["activity"] });
      toast.success(`${record.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const total = data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Engagements"
        description="Audit assignments recorded against each client, with period covered, team allocation, planned dates and controlled lifecycle transitions."
        breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Audit Engagements" }]}
        actions={
          <Button
            size="sm"
            disabled={!canCreateEngagement(role)}
            title={canCreateEngagement(role) ? undefined : "Auditees may only view engagement records."}
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus className="size-4" aria-hidden />
            Create engagement
          </Button>
        }
      />

      <FilterPanel
        filters={[
          {
            key: "clientId",
            label: "Client",
            options: clients.map((client) => ({ value: client.id, label: client.legalName })),
          },
          { key: "auditType", label: "Audit type", options: AUDIT_TYPES.map((i) => ({ value: i, label: i })) },
          { key: "auditArea", label: "Audit area", options: AUDIT_AREAS.map((i) => ({ value: i, label: i })) },
          { key: "status", label: "Status", options: ENGAGEMENT_STATUSES.map((i) => ({ value: i, label: i })) },
          { key: "stage", label: "Lifecycle stage", options: LIFECYCLE_STAGES.map((i) => ({ value: i, label: i })) },
          { key: "manager", label: "Manager", options: managers.map((i) => ({ value: i, label: i })) },
        ]}
        values={filters}
        onChange={(key, value) => {
          setPage(1);
          setFilters({ ...filters, [key]: value });
        }}
        onReset={() => {
          setFilters({});
          setDateRange({ from: "", to: "" });
          setPage(1);
        }}
      />

      <div className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface px-4 py-3">
        <div className="space-y-1.5">
          <Label htmlFor="planned-from" className="text-xs text-muted-foreground">
            Planned start from
          </Label>
          <Input
            id="planned-from"
            type="date"
            className="h-9 w-[170px] bg-card"
            value={dateRange.from}
            onChange={(event) => setDateRange({ ...dateRange, from: event.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="planned-to" className="text-xs text-muted-foreground">
            Planned start to
          </Label>
          <Input
            id="planned-to"
            type="date"
            className="h-9 w-[170px] bg-card"
            value={dateRange.to}
            onChange={(event) => setDateRange({ ...dateRange, to: event.target.value })}
          />
        </div>
      </div>

      <DataTableShell
        columns={COLUMNS}
        caption="Engagement register"
        isLoading={isLoading}
        error={isError ? "The engagement register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={(data?.items.length ?? 0) === 0}
        emptyTitle="No engagements match these filters"
        emptyMessage="Adjust the search or filters, or create a new engagement."
        toolbar={
          <>
            <SearchBox
              value={search}
              onChange={(value) => {
                setSearch(value);
                setPage(1);
              }}
              placeholder="Search reference, title or client…"
            />
            <div className="flex flex-wrap items-center gap-2">
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as typeof sortBy)}>
                <SelectTrigger className="h-9 w-[200px]" aria-label="Sort by">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reference">Sort: Reference</SelectItem>
                  <SelectItem value="clientName">Sort: Client</SelectItem>
                  <SelectItem value="plannedStartDate">Sort: Planned start</SelectItem>
                  <SelectItem value="plannedCompletionDate">Sort: Planned completion</SelectItem>
                  <SelectItem value="status">Sort: Status</SelectItem>
                  <SelectItem value="updatedAt">Sort: Last updated</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={String(pageSize)}
                onValueChange={(value) => {
                  setPageSize(Number(value));
                  setPage(1);
                }}
              >
                <SelectTrigger className="h-9 w-[110px]" aria-label="Rows per page">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[10, 25, 50].map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} / page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={() => toast.success("Export queued — file generation arrives with the Google integration.")}
              >
                Export
              </Button>
            </div>
          </>
        }
        footer={`Showing ${data?.items.length ?? 0} of ${total} engagement(s) — page ${page} of ${lastPage}.`}
      >
        {data?.items.map((engagement) => (
          <TableRow key={engagement.id}>
            <TableCell className="font-mono text-xs">
              <Link
                to="/engagements/$engagementId"
                params={{ engagementId: engagement.id }}
                className="text-primary hover:underline"
              >
                {engagement.reference}
              </Link>
            </TableCell>
            <TableCell className="text-sm">
              <Link
                to="/clients/$clientId"
                params={{ clientId: engagement.clientId }}
                className="hover:underline"
              >
                {engagement.clientName}
              </Link>
            </TableCell>
            <TableCell className="min-w-[240px] text-sm font-medium">{engagement.title}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{engagement.auditType}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{engagement.auditArea}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {formatDate(engagement.auditPeriodFrom)} – {formatDate(engagement.auditPeriodTo)}
            </TableCell>
            <TableCell className="text-sm">{engagement.location || "—"}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{engagement.engagementManager}</TableCell>
            <TableCell className="text-sm">{engagement.processOwner}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">{formatDate(engagement.plannedStartDate)}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">{formatDate(engagement.plannedCompletionDate)}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">{formatDate(engagement.reportingDueDate)}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">
              {resolveStage(engagement.status, engagement.lifecycleStage)}
            </TableCell>
            <TableCell>
              <StatusBadge status={engagement.status} tone={ENGAGEMENT_STATUS_TONES[engagement.status]} />
            </TableCell>
            <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
              {formatDateTime(engagement.updatedAt)}
            </TableCell>
            <TableCell className="text-right">
              <EngagementActions
                engagement={engagement}
                variant="menu"
                onView={() =>
                  void navigate({ to: "/engagements/$engagementId", params: { engagementId: engagement.id } })
                }
                onEdit={
                  canCreateEngagement(role)
                    ? () => {
                        setEditing(engagement);
                        setFormOpen(true);
                      }
                    : undefined
                }
              />
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>
          Next
        </Button>
      </div>

      <EngagementFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        engagement={editing}
        clients={clients}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />
    </div>
  );
}
