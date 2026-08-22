import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  evidenceFields,
  evidenceReviewFields,
  toEvidenceValues,
  toPromptValues,
} from "@/components/fieldwork/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canAddEvidence, canReviewEvidence } from "@/lib/permissions";
import { services } from "@/services";
import type { EvidenceListItem, EvidenceListQuery } from "@/services/evidence.service";
import {
  AUDIT_RESULTS,
  AUDIT_RESULT_TONES,
  EVIDENCE_REVIEW_STATUSES,
  EVIDENCE_REVIEW_TONES,
  type AuditResult,
  type EvidenceReviewStatus,
} from "@/types/fieldwork";

const COLUMNS = [
  { key: "reference", header: "Evidence", width: "110px" },
  { key: "requirement", header: "Requirement" },
  { key: "engagement", header: "Engagement" },
  { key: "file", header: "File" },
  { key: "category", header: "Category" },
  { key: "submitted", header: "Submitted" },
  { key: "reviewer", header: "Reviewer" },
  { key: "review", header: "Review status" },
  { key: "result", header: "Audit result" },
  { key: "version", header: "Ver.", align: "right" as const },
  { key: "actions", header: "Actions", align: "right" as const },
];

type PendingAction =
  | { key: "revision"; row: EvidenceListItem }
  | { key: "accept"; row: EvidenceListItem };

export function EvidenceReviewPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions, requirements } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("evidence.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("evidence.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<EvidenceListQuery["sortBy"]>>(
    "evidence.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [newVersionFor, setNewVersionFor] = useState<EvidenceListItem | null>(null);
  const [reviewFor, setReviewFor] = useState<EvidenceListItem | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);

  const query: EvidenceListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    reviewStatus: filters.reviewStatus,
    auditResult: filters.auditResult,
    reviewer: filters.reviewer,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["evidence", "list", query],
    queryFn: () => services.evidence.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["evidence"] });
    void queryClient.invalidateQueries({ queryKey: ["requirements"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const requirementOptions = requirements.map((row) => ({
    value: row.id,
    label: `${row.reference} · ${row.description.slice(0, 60)}`,
  }));

  const createMutation = useMutation({
    mutationFn: (values: PromptValues) => services.evidence.create(toEvidenceValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      invalidate();
      toast.success(`${row.reference} recorded.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const revisionMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.evidence.addRevision(id, toEvidenceValues(values), actor),
    onSuccess: (row) => {
      setNewVersionFor(null);
      invalidate();
      toast.success(`${row.reference} recorded as version ${row.version}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const startReviewMutation = useMutation({
    mutationFn: (id: string) => services.evidence.startReview(id, actor),
    onSuccess: (row) => {
      invalidate();
      toast.success(`${row.reference} is now Under Review.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.evidence.recordReview(
        id,
        {
          reviewStatus: values.reviewStatus as EvidenceReviewStatus,
          auditResult: values.auditResult as AuditResult,
          reviewRemarks: values.reviewRemarks,
        },
        actor,
      ),
    onSuccess: (row) => {
      setReviewFor(null);
      invalidate();
      toast.success(`${row.reference} reviewed — ${row.auditResult}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: async ({ action, reason }: { action: PendingAction; reason: string }) => {
      if (action.key === "revision") {
        const result = await services.evidence.requestRevision(action.row.id, reason, actor);
        return "evidence" in result ? result.evidence : result;
      }
      return services.evidence.accept(action.row.id, reason, actor);
    },
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} is now ${row.reviewStatus}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const rows = data?.items ?? [];
  const review = canReviewEvidence(role);

  const addButton = (
    <Button size="sm" disabled={!canAddEvidence(role)} onClick={() => setFormOpen(true)}>
      Record evidence
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Evidence Review"
          description="Evidence submitted against each data requirement, its review status and the auditor's result. Metadata only — no files are stored."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Evidence Review" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            {
              key: "reviewStatus",
              label: "Review status",
              options: EVIDENCE_REVIEW_STATUSES.map((s) => ({ value: s, label: s })),
            },
            { key: "auditResult", label: "Audit result", options: AUDIT_RESULTS.map((s) => ({ value: s, label: s })) },
            { key: "reviewer", label: "Reviewer", options: AUDITORS.map((a) => ({ value: a, label: a })) },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Evidence register"
        isLoading={isLoading}
        error={isError ? "The evidence register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No evidence recorded"
        emptyMessage="Record the documents received against the open data requirements."
        emptyAction={addButton}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search evidence, file name or submitter…" />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "submissionDate" ? "reference" : "submissionDate")}
              >
                Sort: {sortBy === "submissionDate" ? "Submission date" : "Evidence ID"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} evidence record(s).`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">
              {row.reference}
              {row.supersedes && (
                <span className="block text-[10px] text-muted-foreground">supersedes {row.supersedes}</span>
              )}
            </TableCell>
            <TableCell className="text-xs">
              <span className="font-mono">{row.requirementRef}</span>
              <span className="block max-w-[200px] truncate text-muted-foreground">
                {row.requirementDescription}
              </span>
            </TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{row.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{row.clientName}</span>
              </TableCell>
            )}
            <TableCell className="max-w-[200px] truncate text-sm">
              {row.fileName}
              <span className="block text-xs text-muted-foreground">
                {row.fileType}
                {row.fileSize ? ` · ${row.fileSize}` : ""}
              </span>
            </TableCell>
            <TableCell className="text-sm">{row.documentCategory}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {formatDate(row.submissionDate)}
              <span className="block text-muted-foreground">{row.submittedBy}</span>
            </TableCell>
            <TableCell className="text-sm whitespace-nowrap">{row.assignedReviewer}</TableCell>
            <TableCell>
              <StatusBadge status={row.reviewStatus} tone={EVIDENCE_REVIEW_TONES[row.reviewStatus]} />
            </TableCell>
            <TableCell>
              <StatusBadge status={row.auditResult} tone={AUDIT_RESULT_TONES[row.auditResult]} />
            </TableCell>
            <TableCell className="text-right text-sm tabular-nums">v{row.version}</TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Start review",
                    disabled: !review || row.reviewStatus !== "Awaiting Review",
                    onSelect: () => startReviewMutation.mutate(row.id),
                  },
                  {
                    label: "Record review outcome",
                    disabled: !review || row.reviewStatus === "Accepted",
                    onSelect: () => setReviewFor(row),
                  },
                  {
                    label: "Request revision",
                    disabled: !review || row.reviewStatus === "Accepted",
                    onSelect: () => setPending({ key: "revision", row }),
                  },
                  {
                    label: "Accept evidence",
                    disabled: !review || row.reviewStatus === "Accepted",
                    onSelect: () => setPending({ key: "accept", row }),
                  },
                  {
                    label: "Submit revised version",
                    divider: true,
                    disabled: !canAddEvidence(role) || row.reviewStatus === "Accepted",
                    onSelect: () => setNewVersionFor(row),
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
        title="Record evidence"
        description="Evidence is recorded as metadata only — no file is uploaded or stored."
        fields={evidenceFields(requirementOptions)}
        submitLabel="Record evidence"
        pending={createMutation.isPending}
        onSubmit={(values) => createMutation.mutate(values)}
      />

      <PromptDialog
        open={newVersionFor !== null}
        onOpenChange={(open) => !open && setNewVersionFor(null)}
        wide
        title={`Submit revised version of ${newVersionFor?.reference ?? ""}`}
        description="A revision creates a new evidence record; the earlier version is retained for the audit trail."
        fields={evidenceFields(
          newVersionFor ? [{ value: newVersionFor.requirementId, label: newVersionFor.requirementRef }] : [],
          true,
        )}
        initialValues={newVersionFor ? toPromptValues(newVersionFor) : undefined}
        submitLabel="Record revision"
        pending={revisionMutation.isPending}
        onSubmit={(values) => newVersionFor && revisionMutation.mutate({ id: newVersionFor.id, values })}
      />

      <PromptDialog
        open={reviewFor !== null}
        onOpenChange={(open) => !open && setReviewFor(null)}
        title={`Review ${reviewFor?.reference ?? ""}`}
        description="Record the review status, the audit result and the reviewer's remarks."
        fields={evidenceReviewFields}
        submitLabel="Save review"
        pending={reviewMutation.isPending}
        onSubmit={(values) => reviewFor && reviewMutation.mutate({ id: reviewFor.id, values })}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending?.key === "revision" ? "Request evidence revision" : "Accept evidence"}
        reasonLabel={pending?.key === "revision" ? "What must be corrected?" : "Acceptance remarks"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) => pending && actionMutation.mutate({ action: pending, reason })}
      />
    </div>
  );
}
