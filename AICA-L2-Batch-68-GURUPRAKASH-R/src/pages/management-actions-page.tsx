import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { PromptDialog, type PromptValues } from "@/components/common/prompt-dialog";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { RowActions } from "@/components/common/row-actions";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import { actionFields, toActionValues } from "@/components/reporting/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import {
  canAgreeAction,
  canEscalateAction,
  canManageAction,
  canReviseTargetDate,
} from "@/lib/permissions";
import { services } from "@/services";
import type { ActionListItem, ActionListQuery } from "@/services/management-action.service";
import {
  AGREEMENT_STATUSES,
  AGREEMENT_TONES,
  DUE_TONES,
  IMPLEMENTATION_STATUSES,
  IMPLEMENTATION_TONES,
} from "@/types/reporting";

const COLUMNS = [
  { key: "reference", header: "Action", width: "100px" },
  { key: "observation", header: "Observation" },
  { key: "title", header: "Action" },
  { key: "owner", header: "Owner" },
  { key: "target", header: "Target date" },
  { key: "due", header: "Due status" },
  { key: "agreement", header: "Agreement" },
  { key: "implementation", header: "Implementation" },
  { key: "actions", header: "Actions", align: "right" as const },
];

type PendingKey = "agree" | "revision" | "reject" | "escalate";

const PENDING_COPY: Record<PendingKey, { title: string; label: string }> = {
  agree: { title: "Agree management action", label: "Auditor assessment" },
  revision: { title: "Request a revised action", label: "What needs to change" },
  reject: { title: "Reject management action", label: "Reason for rejection" },
  escalate: { title: "Escalate management action", label: "Escalation remarks" },
};

export function ManagementActionsPage({
  engagementId,
  observationId,
}: {
  engagementId?: string;
  observationId?: string;
}) {
  const embedded = Boolean(engagementId || observationId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("actions.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("actions.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<ActionListQuery["sortBy"]>>(
    "actions.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ActionListItem | null>(null);
  const [pending, setPending] = useState<{ key: PendingKey; row: ActionListItem } | null>(null);
  const [reviseFor, setReviseFor] = useState<ActionListItem | null>(null);

  const query: ActionListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    agreementStatus: filters.agreementStatus,
    implementationStatus: filters.implementationStatus,
    dueStatus: filters.dueStatus,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["actions", "list", query, observationId],
    queryFn: () =>
      observationId
        ? services.managementActions
            .getByObservationId(observationId)
            .then((items) => ({ items, total: items.length, page: 1, pageSize: items.length }))
        : services.managementActions.list(query),
  });

  const observationsQuery = useQuery({
    queryKey: ["observations", "for-action", engagementId ?? "all"],
    queryFn: () =>
      engagementId
        ? services.observations.getByEngagementId(engagementId)
        : services.observations.list({}).then((result) => result.items),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["actions"] });
    void queryClient.invalidateQueries({ queryKey: ["closure"] });
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.managementActions.update(editing.id, toActionValues(values), actor)
        : services.managementActions.create(toActionValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${row.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ key, row, reason }: { key: PendingKey; row: ActionListItem; reason: string }) => {
      if (key === "escalate") return services.managementActions.escalate(row.id, reason, actor);
      const next =
        key === "agree" ? "Agreed by Auditor" : key === "revision" ? "Revision Requested" : "Rejected";
      return services.managementActions.setAgreement(row.id, next, reason, actor);
    },
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} updated.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const reviseMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.managementActions.reviseTargetDate(id, values.revisedTargetDate, values.reason, actor),
    onSuccess: (row) => {
      setReviseFor(null);
      invalidate();
      toast.success(`Target date revised for ${row.reference}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageAction(role);
  const rows = data?.items ?? [];
  const observationOptions = (observationsQuery.data ?? [])
    .filter((row) => row.status !== "Dropped")
    .map((row) => ({ value: row.id, label: `${row.reference} · ${row.title}` }));

  const addButton = (
    <Button
      size="sm"
      disabled={!manage}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Add management action
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Management Actions"
          description="Agreed corrective actions with their owners, target dates, revisions and current implementation status."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Management Actions" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            {
              key: "agreementStatus",
              label: "Agreement",
              options: AGREEMENT_STATUSES.map((s) => ({ value: s, label: s })),
            },
            {
              key: "implementationStatus",
              label: "Implementation",
              options: IMPLEMENTATION_STATUSES.map((s) => ({ value: s, label: s })),
            },
            {
              key: "dueStatus",
              label: "Due status",
              options: ["Not Due", "Due Soon", "Overdue"].map((s) => ({ value: s, label: s })),
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={COLUMNS}
        caption="Management action register"
        isLoading={isLoading}
        error={isError ? "The management action register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No management actions"
        emptyMessage="Record the corrective actions management commits to for each accepted observation."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search action, owner or observation…" />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "targetDate" ? "reference" : "targetDate")}
              >
                Sort: {sortBy === "targetDate" ? "Target date" : "Action ID"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} action(s).`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">{row.reference}</TableCell>
            <TableCell className="max-w-[200px] text-sm">
              <span className="font-mono text-xs">{row.observationRef}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.observationTitle}</span>
            </TableCell>
            <TableCell className="max-w-[240px] text-sm">
              <span className="block truncate font-medium">{row.title}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.description}</span>
            </TableCell>
            <TableCell className="text-sm">
              {row.actionOwner}
              <span className="block text-xs text-muted-foreground">{row.department}</span>
            </TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {formatDate(row.effectiveTargetDate)}
              {row.revisedTargetDate && (
                <span className="block text-muted-foreground line-through">
                  {formatDate(row.originalTargetDate)}
                </span>
              )}
            </TableCell>
            <TableCell>
              <StatusBadge status={row.dueStatus} tone={DUE_TONES[row.dueStatus]} />
            </TableCell>
            <TableCell>
              <StatusBadge status={row.agreementStatus} tone={AGREEMENT_TONES[row.agreementStatus]} />
            </TableCell>
            <TableCell>
              <StatusBadge
                status={row.implementationStatus}
                tone={IMPLEMENTATION_TONES[row.implementationStatus]}
              />
              {row.escalated && (
                <span className="mt-1 block text-xs text-critical-foreground">Escalated</span>
              )}
            </TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Edit action",
                    disabled:
                      !manage ||
                      row.agreementStatus === "Agreed by Auditor" ||
                      row.implementationStatus === "Closed",
                    onSelect: () => {
                      setEditing(row);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Agree action",
                    divider: true,
                    disabled: !canAgreeAction(role) || row.agreementStatus === "Agreed by Auditor",
                    onSelect: () => setPending({ key: "agree", row }),
                  },
                  {
                    label: "Request revision",
                    disabled: !canAgreeAction(role) || row.agreementStatus === "Agreed by Auditor",
                    onSelect: () => setPending({ key: "revision", row }),
                  },
                  {
                    label: "Reject action",
                    disabled: !canAgreeAction(role) || row.agreementStatus === "Agreed by Auditor",
                    onSelect: () => setPending({ key: "reject", row }),
                  },
                  {
                    label: "Revise target date",
                    divider: true,
                    disabled: !canReviseTargetDate(role) || row.implementationStatus === "Closed",
                    onSelect: () => setReviseFor(row),
                  },
                  {
                    label: "Escalate action",
                    disabled: !canEscalateAction(role) || row.implementationStatus === "Closed",
                    onSelect: () => setPending({ key: "escalate", row }),
                  },
                ]}
              />
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      <PromptDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        wide
        title={editing ? `Edit ${editing.reference}` : "Add management action"}
        description="Actions are recorded against an observation and only take effect once the auditor agrees them."
        fields={actionFields(observationOptions, Boolean(editing) || Boolean(observationId))}
        initialValues={
          editing
            ? {
                observationId: editing.observationId,
                title: editing.title,
                description: editing.description,
                actionType: editing.actionType,
                priority: editing.priority,
                actionOwner: editing.actionOwner,
                ownerDesignation: editing.ownerDesignation,
                department: editing.department,
                originalTargetDate: editing.originalTargetDate,
              }
            : { observationId: observationId ?? "", priority: "Medium", actionType: "Corrective" }
        }
        submitLabel={editing ? "Save action" : "Create action"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <PromptDialog
        open={reviseFor !== null}
        onOpenChange={(open) => !open && setReviseFor(null)}
        title={`Revise target date for ${reviseFor?.reference ?? ""}`}
        description="The original target date is retained for reporting; only the revised date is applied."
        fields={[
          { name: "revisedTargetDate", label: "Revised target date", type: "date", required: true },
          { name: "reason", label: "Reason for revision", type: "textarea", rows: 3, required: true, minLength: 10 },
        ]}
        submitLabel="Save revised date"
        pending={reviseMutation.isPending}
        onSubmit={(values) => reviseFor && reviseMutation.mutate({ id: reviseFor.id, values })}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending ? PENDING_COPY[pending.key].title : ""}
        reasonLabel={pending ? PENDING_COPY[pending.key].label : "Reason"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) =>
          pending && actionMutation.mutate({ key: pending.key, row: pending.row, reason })
        }
      />
    </div>
  );
}
