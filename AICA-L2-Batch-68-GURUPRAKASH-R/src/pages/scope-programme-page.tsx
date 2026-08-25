import { useState } from "react";
import { Link } from "@tanstack/react-router";
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
import {
  AUDITORS,
  PROCESSES,
  scopeFields,
  toPromptValues,
  toScopeValues,
} from "@/components/fieldwork/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDateTime } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canManageScope, canMarkScopeNotApplicable } from "@/lib/permissions";
import { services } from "@/services";
import type { ScopeListItem, ScopeListQuery } from "@/services/scope.service";
import { SCOPE_STATUSES, SCOPE_STATUS_TONES } from "@/types/fieldwork";

const COLUMNS = [
  { key: "reference", header: "Scope ID", width: "100px" },
  { key: "engagement", header: "Engagement" },
  { key: "process", header: "Process" },
  { key: "objective", header: "Objective" },
  { key: "risk", header: "Key risk" },
  { key: "auditor", header: "Auditor" },
  { key: "procedures", header: "Procedures", align: "right" as const },
  { key: "status", header: "Status" },
  { key: "updated", header: "Updated" },
  { key: "actions", header: "Actions", align: "right" as const },
];

type ScopeAction = "complete" | "notApplicable";

export function ScopeProgrammePage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("scopes.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("scopes.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<ScopeListQuery["sortBy"]>>(
    "scopes.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ScopeListItem | null>(null);
  const [action, setAction] = useState<{ key: ScopeAction; scope: ScopeListItem } | null>(null);

  const query: ScopeListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    process: filters.process,
    auditor: filters.auditor,
    status: filters.status,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["scopes", "list", query],
    queryFn: () => services.scopes.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["scopes"] });
    void queryClient.invalidateQueries({ queryKey: ["procedures"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.scopes.update(editing.id, toScopeValues(values), actor)
        : services.scopes.create(toScopeValues(values), actor),
    onSuccess: (scope) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${scope.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => services.scopes.activate(id, actor),
    onSuccess: (scope) => {
      invalidate();
      toast.success(`${scope.reference} is now Active.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ key, id, reason }: { key: ScopeAction; id: string; reason: string }) =>
      key === "complete"
        ? services.scopes.markCompleted(id, reason, actor)
        : services.scopes.markNotApplicable(id, reason, actor),
    onSuccess: (scope) => {
      setAction(null);
      invalidate();
      toast.success(`${scope.reference} is now ${scope.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageScope(role);
  const rows = data?.items ?? [];

  const addButton = (
    <Button
      size="sm"
      disabled={!manage}
      title={manage ? undefined : "Auditees may only view scope records."}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Add scope
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Scope &amp; Audit Programme"
          description="Process-level audit scope, objectives, key risks and expected controls that anchor every test procedure."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Scope & Audit Programme" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            { key: "process", label: "Process", options: PROCESSES.map((p) => ({ value: p, label: p })) },
            { key: "auditor", label: "Auditor", options: AUDITORS.map((a) => ({ value: a, label: a })) },
            { key: "status", label: "Status", options: SCOPE_STATUSES.map((s) => ({ value: s, label: s })) },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Audit scope register"
        isLoading={isLoading}
        error={isError ? "The scope register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No scope records"
        emptyMessage="Add a scope area to start building the audit programme."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox
              value={search}
              onChange={setSearch}
              placeholder="Search scope ID, process or objective…"
            />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "reference" ? "updatedAt" : "reference")}
              >
                Sort: {sortBy === "reference" ? "Scope ID" : "Last updated"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} scope record(s).`}
      >
        {rows.map((scope) => (
          <TableRow key={scope.id}>
            <TableCell className="font-mono text-xs">
              <Link
                to="/scope-programme/$scopeId"
                params={{ scopeId: scope.id }}
                className="text-primary hover:underline"
              >
                {scope.reference}
              </Link>
            </TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{scope.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{scope.clientName}</span>
              </TableCell>
            )}
            <TableCell className="text-sm">
              {scope.process}
              {scope.subProcess && (
                <span className="block text-xs text-muted-foreground">{scope.subProcess}</span>
              )}
            </TableCell>
            <TableCell className="max-w-[260px] truncate text-sm">{scope.objective}</TableCell>
            <TableCell className="max-w-[220px] truncate text-sm">{scope.keyRisk}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{scope.assignedAuditor}</TableCell>
            <TableCell className="text-right text-sm tabular-nums">{scope.procedureCount}</TableCell>
            <TableCell>
              <StatusBadge status={scope.status} tone={SCOPE_STATUS_TONES[scope.status]} />
            </TableCell>
            <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
              {formatDateTime(scope.updatedAt)}
            </TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${scope.reference}`}
                actions={[
                  {
                    label: "Edit scope",
                    disabled: !manage || scope.status === "Completed" || scope.status === "Not Applicable",
                    onSelect: () => {
                      setEditing(scope);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Activate",
                    disabled: !manage || scope.status !== "Draft",
                    onSelect: () => activateMutation.mutate(scope.id),
                  },
                  {
                    label: "Mark completed",
                    disabled: !manage || scope.status !== "Active",
                    onSelect: () => setAction({ key: "complete", scope }),
                  },
                  {
                    label: "Mark not applicable",
                    disabled: !canMarkScopeNotApplicable(role) || scope.status === "Not Applicable",
                    title: canMarkScopeNotApplicable(role) ? undefined : "Audit Manager only.",
                    onSelect: () => setAction({ key: "notApplicable", scope }),
                    divider: true,
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
        title={editing ? `Edit ${editing.reference}` : "Add scope area"}
        description="Scope defines the process, objective, key risk and expected control under audit."
        fields={scopeFields(engagementOptions, Boolean(editing) || embedded)}
        initialValues={
          editing
            ? toPromptValues(editing)
            : engagementId
              ? { engagementId }
              : undefined
        }
        submitLabel={editing ? "Save scope" : "Create scope"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <ReasonDialog
        open={action !== null}
        onOpenChange={(open) => !open && setAction(null)}
        title={action?.key === "complete" ? "Mark scope completed" : "Mark scope not applicable"}
        description={
          action?.key === "complete"
            ? "All procedures under this scope must be concluded before it can be completed."
            : "The scope is retained for reference and excluded from progress reporting."
        }
        reasonLabel={action?.key === "complete" ? "Completion remarks" : "Reason"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) =>
          action && actionMutation.mutate({ key: action.key, id: action.scope.id, reason })
        }
      />
    </div>
  );
}
