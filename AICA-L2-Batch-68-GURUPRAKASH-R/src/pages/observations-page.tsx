import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { PromptDialog, type PromptValues } from "@/components/common/prompt-dialog";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { RiskBadge } from "@/components/common/risk-badge";
import { RowActions } from "@/components/common/row-actions";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import {
  observationFields,
  observationToPromptValues,
  toObservationValues,
} from "@/components/reporting/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { useCachedState } from "@/lib/list-state";
import {
  canDropObservation,
  canFinaliseObservation,
  canIssueObservation,
  canManageObservation,
  canReopenObservation,
  canReviewObservation,
} from "@/lib/permissions";
import { services } from "@/services";
import type { ObservationListItem, ObservationListQuery } from "@/services/observation.service";
import {
  IMPLEMENTATION_ROLLUPS,
  OBSERVATION_STATUSES,
  OBSERVATION_STATUS_TONES,
  REPORTING_DECISIONS,
  ROLLUP_TONES,
} from "@/types/observation";
import { RISK_RATINGS } from "@/types/common";

const COLUMNS = [
  { key: "reference", header: "Observation", width: "110px" },
  { key: "engagement", header: "Engagement" },
  { key: "title", header: "Title & condition" },
  { key: "process", header: "Process" },
  { key: "risk", header: "Risk" },
  { key: "status", header: "Status" },
  { key: "decision", header: "Reporting decision" },
  { key: "rollup", header: "Implementation" },
  { key: "actions", header: "Actions", align: "right" as const },
];

type PendingKey = "sendBack" | "issue" | "finalise" | "drop" | "reopen" | "include";

interface Pending {
  key: PendingKey;
  row: ObservationListItem;
}

const PENDING_COPY: Record<PendingKey, { title: string; label: string }> = {
  sendBack: { title: "Send observation back to draft", label: "Review comments" },
  issue: { title: "Issue for management response", label: "Confirmation remarks" },
  finalise: { title: "Finalise observation", label: "Finalisation remarks" },
  drop: { title: "Drop observation", label: "Reason for dropping" },
  reopen: { title: "Reopen finalised observation", label: "Reason for reopening" },
  include: { title: "Include in final report", label: "Remarks" },
};

export function ObservationsPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions, scopes, procedures, requirements } = useFieldworkOptions();
  const clarificationsQuery = useQuery({
    queryKey: ["clarifications", "options"],
    queryFn: () => services.clarifications.list({}),
  });

  const [search, setSearch] = useCachedState("observations.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("observations.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<ObservationListQuery["sortBy"]>>(
    "observations.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ObservationListItem | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);

  const query: ObservationListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    status: filters.status,
    riskRating: filters.riskRating,
    reportingDecision: filters.reportingDecision,
    implementationRollUp: filters.implementationRollUp,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["observations", "list", query],
    queryFn: () => services.observations.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["reports"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.observations.update(editing.id, toObservationValues(values), actor)
        : services.observations.create(toObservationValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${row.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const submitMutation = useMutation({
    mutationFn: (row: ObservationListItem) => services.observations.submitForReview(row.id, actor),
    onSuccess: (row) => {
      invalidate();
      toast.success(`${row.reference} submitted for review.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ action, reason }: { action: Pending; reason: string }) => {
      const id = action.row.id;
      switch (action.key) {
        case "sendBack":
          return services.observations.sendBackToDraft(id, reason, actor);
        case "issue":
          return services.observations.issueForResponse(id, reason, actor);
        case "finalise":
          return services.observations.finalise(id, reason, actor);
        case "drop":
          return services.observations.drop(id, reason, actor);
        case "reopen":
          return services.observations.reopen(id, reason, actor);
        default:
          return services.observations.includeInReport(id, actor);
      }
    },
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} is now ${row.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageObservation(role);
  const rows = data?.items ?? [];

  const addButton = (
    <Button
      size="sm"
      disabled={!manage}
      title={manage ? undefined : "Auditees may view observations but not raise them."}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Create observation
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Audit Observations"
          description="Condition, criteria, cause, risk and recommendation for each audit finding, with its assessed risk rating and reporting decision."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Audit Observations" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            { key: "status", label: "Status", options: OBSERVATION_STATUSES.map((s) => ({ value: s, label: s })) },
            { key: "riskRating", label: "Risk rating", options: RISK_RATINGS.map((s) => ({ value: s, label: s })) },
            {
              key: "reportingDecision",
              label: "Reporting decision",
              options: REPORTING_DECISIONS.map((s) => ({ value: s, label: s })),
            },
            {
              key: "implementationRollUp",
              label: "Implementation",
              options: IMPLEMENTATION_ROLLUPS.map((s) => ({ value: s, label: s })),
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Observation register"
        isLoading={isLoading}
        error={isError ? "The observation register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No observations recorded"
        emptyMessage="Raise an observation once fieldwork identifies a control weakness or exception worth reporting."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search title, condition or process…" />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "risk" ? "reference" : "risk")}
              >
                Sort: {sortBy === "risk" ? "Risk rating" : "Observation ID"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} observation(s).`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">{row.reference}</TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{row.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{row.clientName}</span>
              </TableCell>
            )}
            <TableCell className="max-w-[280px] text-sm">
              <span className="block truncate font-medium">{row.title}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.condition}</span>
            </TableCell>
            <TableCell className="text-sm">{row.process || "—"}</TableCell>
            <TableCell>
              {row.finalRiskRating ? <RiskBadge rating={row.finalRiskRating} /> : <span className="text-xs">—</span>}
            </TableCell>
            <TableCell>
              <StatusBadge status={row.status} tone={OBSERVATION_STATUS_TONES[row.status]} />
            </TableCell>
            <TableCell className="text-xs">{row.reportingDecision || "—"}</TableCell>
            <TableCell>
              <StatusBadge
                status={row.implementationRollUp}
                tone={ROLLUP_TONES[row.implementationRollUp]}
              />
            </TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Edit observation",
                    disabled: !manage || !["Draft", "Under Auditor Review", "Issued for Management Response", "Awaiting Finalisation"].includes(row.status),
                    onSelect: () => {
                      setEditing(row);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Submit for review",
                    disabled: !manage || row.status !== "Draft",
                    onSelect: () => submitMutation.mutate(row),
                  },
                  {
                    label: "Send back to draft",
                    divider: true,
                    disabled: !canReviewObservation(role) || row.status !== "Under Auditor Review",
                    onSelect: () => setPending({ key: "sendBack", row }),
                  },
                  {
                    label: "Issue for management response",
                    disabled: !canIssueObservation(role) || row.status !== "Under Auditor Review",
                    onSelect: () => setPending({ key: "issue", row }),
                  },
                  {
                    label: "Finalise observation",
                    disabled: !canFinaliseObservation(role) || row.status !== "Awaiting Finalisation",
                    onSelect: () => setPending({ key: "finalise", row }),
                  },
                  {
                    label: "Include in final report",
                    divider: true,
                    disabled: !manage || row.status !== "Finalised",
                    onSelect: () => setPending({ key: "include", row }),
                  },
                  {
                    label: "Reopen observation",
                    disabled:
                      !canReopenObservation(role) ||
                      !["Finalised", "Included in Report", "Reported"].includes(row.status),
                    onSelect: () => setPending({ key: "reopen", row }),
                  },
                  {
                    label: "Drop observation",
                    divider: true,
                    disabled: !canDropObservation(role) || ["Dropped", "Reported"].includes(row.status),
                    onSelect: () => setPending({ key: "drop", row }),
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
        title={editing ? `Edit ${editing.reference}` : "Create observation"}
        description="The final risk rating defaults to the calculated impact × likelihood rating; any override requires a recorded reason."
        fields={observationFields(
          {
            engagements: engagementOptions,
            scopes,
            procedures,
            requirements,
            clarifications: clarificationsQuery.data?.items ?? [],
          },
          Boolean(editing) || embedded,
        )}
        initialValues={
          editing
            ? observationToPromptValues(editing as unknown as Record<string, unknown>)
            : { engagementId: engagementId ?? "", preparedBy: actor.user }
        }
        submitLabel={editing ? "Save observation" : "Create observation"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending ? PENDING_COPY[pending.key].title : ""}
        reasonLabel={pending ? PENDING_COPY[pending.key].label : "Reason"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) => pending && actionMutation.mutate({ action: pending, reason })}
      />
    </div>
  );
}
