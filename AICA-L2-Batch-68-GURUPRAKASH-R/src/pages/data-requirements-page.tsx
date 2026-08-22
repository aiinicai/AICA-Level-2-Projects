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
  evidenceFields,
  requirementFields,
  toEvidenceValues,
  toPromptValues,
  toRequirementValues,
} from "@/components/fieldwork/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canAddEvidence, canManageRequirement, canReopenRequirement } from "@/lib/permissions";
import { services } from "@/services";
import type { RequirementListItem, RequirementListQuery } from "@/services/requirement.service";
import {
  DEPARTMENTS,
  PRIORITY_TONES,
  REQUIREMENT_PRIORITIES,
  REVIEW_STATUSES,
  REVIEW_TONES,
  SUBMISSION_STATUSES,
  SUBMISSION_TONES,
  type ReviewStatus,
  type SubmissionStatus,
} from "@/types/fieldwork";

const COLUMNS = [
  { key: "reference", header: "Requirement", width: "110px" },
  { key: "engagement", header: "Engagement" },
  { key: "link", header: "Scope / procedure" },
  { key: "description", header: "Requirement" },
  { key: "department", header: "Department" },
  { key: "owner", header: "Responsible" },
  { key: "due", header: "Due date" },
  { key: "priority", header: "Priority" },
  { key: "submission", header: "Submission" },
  { key: "review", header: "Review" },
  { key: "completion", header: "Completion", width: "120px" },
  { key: "evidence", header: "Evidence", align: "right" as const },
  { key: "actions", header: "Actions", align: "right" as const },
];

type PendingAction =
  | { key: "submission"; row: RequirementListItem; next: SubmissionStatus }
  | { key: "review"; row: RequirementListItem; next: ReviewStatus }
  | { key: "close"; row: RequirementListItem }
  | { key: "reopen"; row: RequirementListItem }
  | { key: "notApplicable"; row: RequirementListItem };

export function DataRequirementsPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions, scopes, procedures } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("requirements.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("requirements.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<RequirementListQuery["sortBy"]>>(
    "requirements.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<RequirementListItem | null>(null);
  const [evidenceFor, setEvidenceFor] = useState<RequirementListItem | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);

  const query: RequirementListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    department: filters.department,
    priority: filters.priority,
    submissionStatus: filters.submissionStatus,
    reviewStatus: filters.reviewStatus,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["requirements", "list", query],
    queryFn: () => services.requirements.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["requirements"] });
    void queryClient.invalidateQueries({ queryKey: ["evidence"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.requirements.update(editing.id, toRequirementValues(values), actor)
        : services.requirements.create(toRequirementValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${row.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const evidenceMutation = useMutation({
    mutationFn: (values: PromptValues) => services.evidence.create(toEvidenceValues(values), actor),
    onSuccess: (row) => {
      setEvidenceFor(null);
      invalidate();
      toast.success(`${row.reference} recorded.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const issueMutation = useMutation({
    mutationFn: (id: string) => services.requirements.issue(id, actor),
    onSuccess: (row) => {
      invalidate();
      toast.success(`${row.reference} issued to the auditee.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const reminderMutation = useMutation({
    mutationFn: (id: string) => services.requirements.sendReminder(id, actor),
    onSuccess: (row) => {
      invalidate();
      toast.success(`Reminder logged for ${row.reference}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ action, reason }: { action: PendingAction; reason: string }) => {
      const id = action.row.id;
      if (action.key === "submission")
        return services.requirements.setSubmissionStatus(id, action.next, reason, actor);
      if (action.key === "review")
        return services.requirements.setReviewStatus(id, action.next, reason, actor);
      if (action.key === "close") return services.requirements.close(id, reason, actor);
      if (action.key === "reopen") return services.requirements.reopen(id, reason, actor);
      return services.requirements.markNotApplicable(id, reason, actor);
    },
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} updated.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageRequirement(role);
  const rows = data?.items ?? [];

  const addButton = (
    <Button
      size="sm"
      disabled={!manage}
      title={manage ? undefined : "Auditees may only view and respond to requirements."}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Add requirement
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Data Requirements"
          description="Information requested from the auditee for each test procedure, with submission and review progress."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Data Requirements" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            { key: "department", label: "Department", options: DEPARTMENTS.map((d) => ({ value: d, label: d })) },
            { key: "priority", label: "Priority", options: REQUIREMENT_PRIORITIES.map((p) => ({ value: p, label: p })) },
            {
              key: "submissionStatus",
              label: "Submission status",
              options: SUBMISSION_STATUSES.map((s) => ({ value: s, label: s })),
            },
            {
              key: "reviewStatus",
              label: "Review status",
              options: REVIEW_STATUSES.map((s) => ({ value: s, label: s })),
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Data requirement register"
        isLoading={isLoading}
        error={isError ? "The requirement register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No data requirements"
        emptyMessage="Raise the information requests needed to execute the audit procedures."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search requirement, department or owner…" />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "dueDate" ? "reference" : "dueDate")}
              >
                Sort: {sortBy === "dueDate" ? "Due date" : "Requirement ID"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} requirement(s).`}
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
            <TableCell className="text-xs">
              <Link
                to="/scope-programme/$scopeId"
                params={{ scopeId: row.scopeId }}
                className="font-mono text-primary hover:underline"
              >
                {row.scopeRef}
              </Link>
              <span className="block font-mono text-muted-foreground">{row.procedureRef}</span>
            </TableCell>
            <TableCell className="max-w-[260px] truncate text-sm">{row.description}</TableCell>
            <TableCell className="text-sm">{row.department}</TableCell>
            <TableCell className="text-sm">{row.responsiblePerson}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{formatDate(row.dueDate)}</TableCell>
            <TableCell>
              <StatusBadge status={row.priority} tone={PRIORITY_TONES[row.priority]} />
            </TableCell>
            <TableCell>
              <StatusBadge status={row.submissionStatus} tone={SUBMISSION_TONES[row.submissionStatus]} />
            </TableCell>
            <TableCell>
              <StatusBadge status={row.reviewStatus} tone={REVIEW_TONES[row.reviewStatus]} />
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <Progress value={row.completionPercentage} className="h-1.5" />
                <span className="text-xs tabular-nums text-muted-foreground">
                  {row.completionPercentage}%
                </span>
              </div>
            </TableCell>
            <TableCell className="text-right text-sm tabular-nums">{row.evidenceCount}</TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Edit requirement",
                    disabled: !manage || row.reviewStatus === "Closed",
                    onSelect: () => {
                      setEditing(row);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Issue to auditee",
                    disabled: !manage || row.submissionStatus !== "Draft",
                    onSelect: () => issueMutation.mutate(row.id),
                  },
                  {
                    label: "Send reminder",
                    disabled: !manage || row.submissionStatus === "Received",
                    onSelect: () => reminderMutation.mutate(row.id),
                  },
                  {
                    label: "Record evidence",
                    divider: true,
                    disabled: !canAddEvidence(role) || row.submissionStatus === "Draft",
                    onSelect: () => setEvidenceFor(row),
                  },
                  {
                    label: "Mark partially received",
                    disabled: !manage,
                    onSelect: () => setPending({ key: "submission", row, next: "Partially Received" }),
                  },
                  {
                    label: "Mark received",
                    disabled: !manage,
                    onSelect: () => setPending({ key: "submission", row, next: "Received" }),
                  },
                  {
                    label: "Start review",
                    divider: true,
                    disabled: !manage,
                    onSelect: () => setPending({ key: "review", row, next: "Under Review" }),
                  },
                  {
                    label: "Request additional data",
                    disabled: !manage,
                    onSelect: () => setPending({ key: "review", row, next: "Additional Data Required" }),
                  },
                  {
                    label: "Mark reviewed",
                    disabled: !manage,
                    onSelect: () => setPending({ key: "review", row, next: "Reviewed" }),
                  },
                  {
                    label: "Close requirement",
                    disabled: !manage || row.reviewStatus === "Closed",
                    onSelect: () => setPending({ key: "close", row }),
                  },
                  {
                    label: "Reopen requirement",
                    divider: true,
                    disabled: !canReopenRequirement(role) || row.reviewStatus !== "Closed",
                    title: canReopenRequirement(role) ? undefined : "Audit Manager only.",
                    onSelect: () => setPending({ key: "reopen", row }),
                  },
                  {
                    label: "Mark not applicable",
                    disabled: !manage || row.submissionStatus === "Not Applicable",
                    onSelect: () => setPending({ key: "notApplicable", row }),
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
        title={editing ? `Edit ${editing.reference}` : "Add data requirement"}
        description="A requirement always belongs to a procedure so evidence can be traced back to the test."
        fields={requirementFields({ engagements: engagementOptions, scopes, procedures })}
        initialValues={
          editing
            ? { ...toPromptValues(editing), scopeId: editing.scopeId }
            : engagementId
              ? { engagementId }
              : undefined
        }
        submitLabel={editing ? "Save requirement" : "Create requirement"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <PromptDialog
        open={evidenceFor !== null}
        onOpenChange={(open) => !open && setEvidenceFor(null)}
        wide
        title={`Record evidence for ${evidenceFor?.reference ?? ""}`}
        description="Evidence is recorded as metadata only — no file is uploaded or stored."
        fields={evidenceFields(
          evidenceFor ? [{ value: evidenceFor.id, label: evidenceFor.reference }] : [],
          true,
        )}
        initialValues={evidenceFor ? { requirementId: evidenceFor.id } : undefined}
        submitLabel="Record evidence"
        pending={evidenceMutation.isPending}
        onSubmit={(values) => evidenceMutation.mutate(values)}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending?.key === "submission"
            ? `Set submission status to ${pending.next}`
            : pending?.key === "review"
              ? `Set review status to ${pending.next}`
              : pending?.key === "close"
                ? "Close requirement"
                : pending?.key === "reopen"
                  ? "Reopen requirement"
                  : "Mark requirement not applicable"
        }
        reasonLabel="Remarks"
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) => pending && actionMutation.mutate({ action: pending, reason })}
      />
    </div>
  );
}
