import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { DetailCard, DetailField } from "@/components/common/detail-card";
import { EmptyState } from "@/components/common/empty-state";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { PromptDialog, type PromptValues } from "@/components/common/prompt-dialog";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { RiskBadge } from "@/components/common/risk-badge";
import { RowActions } from "@/components/common/row-actions";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import { reportFields, toReportValues } from "@/components/reporting/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canFinaliseReport, canManageReport, canReviewReport } from "@/lib/permissions";
import { services } from "@/services";
import type { ReportListItem, ReportListQuery } from "@/services/report.service";
import { REPORT_STATUSES, REPORT_STATUS_TONES } from "@/types/reporting";

const COLUMNS = [
  { key: "reference", header: "Report", width: "100px" },
  { key: "title", header: "Title" },
  { key: "engagement", header: "Engagement" },
  { key: "period", header: "Period" },
  { key: "addressee", header: "Addressee" },
  { key: "issue", header: "Issue date" },
  { key: "observations", header: "Observations", align: "right" as const },
  { key: "status", header: "Status" },
  { key: "actions", header: "Actions", align: "right" as const },
];

export function FinalReportingPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("reports.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("reports.filters", {});
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ReportListItem | null>(null);
  const [contentsFor, setContentsFor] = useState<ReportListItem | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [previewFor, setPreviewFor] = useState<ReportListItem | null>(null);
  const [pending, setPending] = useState<{ key: "sendBack" | "finalise"; row: ReportListItem } | null>(null);

  const query: ReportListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    status: filters.status,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reports", "list", query],
    queryFn: () => services.reports.list(query),
  });

  const eligibleQuery = useQuery({
    queryKey: ["reports", "eligible", contentsFor?.engagementId],
    queryFn: () => services.reports.eligibleObservations(contentsFor!.engagementId),
    enabled: Boolean(contentsFor),
  });

  const previewQuery = useQuery({
    queryKey: ["reports", "preview", previewFor?.id],
    queryFn: () => services.reports.preview(previewFor!.id),
    enabled: Boolean(previewFor),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["reports"] });
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.reports.update(editing.id, toReportValues(values), actor)
        : services.reports.create(toReportValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${row.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const contentsMutation = useMutation({
    mutationFn: (ids: string[]) => services.reports.setObservations(contentsFor!.id, ids, actor),
    onSuccess: (row) => {
      setContentsFor(null);
      invalidate();
      toast.success(`${row.observationIds.length} observation(s) included in ${row.reference}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const submitMutation = useMutation({
    mutationFn: (row: ReportListItem) => services.reports.submitForReview(row.id, actor),
    onSuccess: (row) => {
      invalidate();
      toast.success(`${row.reference} submitted for review.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ key, row, reason }: { key: "sendBack" | "finalise"; row: ReportListItem; reason: string }) =>
      key === "sendBack"
        ? services.reports.sendBackToDraft(row.id, reason, actor)
        : services.reports.finalise(row.id, reason, actor, reason),
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} is now ${row.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageReport(role);
  const rows = data?.items ?? [];

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
      Create report
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Final Reporting"
          description="Assemble finalised observations into the internal audit report, route it for review and issue it to management."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Final Reporting" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            { key: "status", label: "Status", options: REPORT_STATUSES.map((s) => ({ value: s, label: s })) },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Report register"
        isLoading={isLoading}
        error={isError ? "The report register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No reports drafted"
        emptyMessage="Create a report once observations for the engagement have been finalised."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search report title or addressee…" />
            {embedded && addButton}
          </>
        }
        footer={`${rows.length} report(s).`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">{row.reference}</TableCell>
            <TableCell className="max-w-[240px] text-sm">
              <span className="block truncate font-medium">{row.title}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.executiveSummary}</span>
            </TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{row.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{row.clientName}</span>
              </TableCell>
            )}
            <TableCell className="text-sm">{row.reportPeriod}</TableCell>
            <TableCell className="text-sm">{row.addressee}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {row.issueDate ? formatDate(row.issueDate) : "—"}
            </TableCell>
            <TableCell className="text-right font-mono text-xs">{row.observationCount}</TableCell>
            <TableCell>
              <StatusBadge status={row.status} tone={REPORT_STATUS_TONES[row.status]} />
            </TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Edit report",
                    disabled: !manage || row.status === "Finalised",
                    onSelect: () => {
                      setEditing(row);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Select observations",
                    disabled: !manage || row.status === "Finalised",
                    onSelect: () => {
                      setSelected(row.observationIds);
                      setContentsFor(row);
                    },
                  },
                  { label: "Preview report", divider: true, onSelect: () => setPreviewFor(row) },
                  {
                    label: "Submit for review",
                    divider: true,
                    disabled: !manage || row.status !== "Draft",
                    onSelect: () => submitMutation.mutate(row),
                  },
                  {
                    label: "Return to draft",
                    disabled: !canReviewReport(role) || row.status !== "Under Review",
                    onSelect: () => setPending({ key: "sendBack", row }),
                  },
                  {
                    label: "Finalise and issue",
                    disabled: !canFinaliseReport(role) || row.status !== "Under Review",
                    onSelect: () => setPending({ key: "finalise", row }),
                  },
                ]}
              />
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      {previewFor && (
        <DetailCard
          title={`${previewFor.reference} — ${previewFor.title}`}
          actions={
            <Button variant="outline" size="sm" onClick={() => setPreviewFor(null)}>
              Close preview
            </Button>
          }
        >
          <dl className="mb-4 grid gap-4 sm:grid-cols-4">
            <DetailField label="Client" value={previewFor.clientName} />
            <DetailField label="Engagement" value={previewFor.engagementRef} />
            <DetailField label="Period" value={previewFor.reportPeriod} />
            <DetailField label="Addressee" value={previewFor.addressee} />
          </dl>
          <div className="space-y-4">
            <section>
              <h3 className="label-caps mb-1">Executive summary</h3>
              <p className="text-sm whitespace-pre-line">{previewFor.executiveSummary || "—"}</p>
            </section>
            <section>
              <h3 className="label-caps mb-1">Overall conclusion</h3>
              <p className="text-sm whitespace-pre-line">{previewFor.overallConclusion || "—"}</p>
            </section>
            {(previewQuery.data ?? []).length === 0 ? (
              <EmptyState
                title="No observations included"
                message="Select finalised observations to build the report contents."
              />
            ) : (
              (previewQuery.data ?? []).map((line, index) => (
                <article key={line.observation.id} className="rounded-md border border-border p-4">
                  <header className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs">{line.observation.reference}</span>
                    <h4 className="text-sm font-medium">
                      {index + 1}. {line.observation.title}
                    </h4>
                    {line.observation.finalRiskRating && (
                      <RiskBadge rating={line.observation.finalRiskRating} />
                    )}
                    {!line.responseAccepted && (
                      <span className="text-xs text-critical-foreground">
                        Response not accepted by the auditor
                      </span>
                    )}
                  </header>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <DetailField label="Condition" value={line.observation.condition} />
                    <DetailField label="Criteria" value={line.observation.criteria || "—"} />
                    <DetailField label="Root cause" value={line.observation.rootCause || "—"} />
                    <DetailField label="Recommendation" value={line.observation.recommendation} />
                    <DetailField label="Management response" value={line.responseSummary} />
                    <DetailField
                      label="Agreed actions"
                      value={
                        line.actionSummary.length ? (
                          <ul className="space-y-1 text-xs">
                            {line.actionSummary.map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          "No actions recorded."
                        )
                      }
                    />
                  </dl>
                </article>
              ))
            )}
          </div>
        </DetailCard>
      )}

      <PromptDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        wide
        title={editing ? `Edit ${editing.reference}` : "Create report"}
        fields={reportFields(engagementOptions, Boolean(editing) || embedded)}
        initialValues={
          editing
            ? {
                engagementId: editing.engagementId,
                title: editing.title,
                reportPeriod: editing.reportPeriod,
                addressee: editing.addressee,
                issueDate: editing.issueDate,
                preparedBy: editing.preparedBy,
                executiveSummary: editing.executiveSummary,
                overallConclusion: editing.overallConclusion,
              }
            : { engagementId: engagementId ?? "", preparedBy: actor.user }
        }
        submitLabel={editing ? "Save report" : "Create report"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      {contentsFor && (
        <div
          role="dialog"
          aria-label="Select observations"
          className="rounded-md border border-border bg-surface p-4"
        >
          <h2 className="mb-1 text-sm font-medium">Observations for {contentsFor.reference}</h2>
          <p className="mb-3 text-xs text-muted-foreground">
            Only finalised observations may be included in a report.
          </p>
          <div className="space-y-2">
            {(eligibleQuery.data ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No finalised observations are available for this engagement yet.
              </p>
            )}
            {(eligibleQuery.data ?? []).map((row) => (
              <div key={row.id} className="flex items-start gap-2">
                <Checkbox
                  id={`obs-${row.id}`}
                  checked={selected.includes(row.id)}
                  onCheckedChange={(checked) =>
                    setSelected((current) =>
                      checked ? [...current, row.id] : current.filter((id) => id !== row.id),
                    )
                  }
                />
                <Label htmlFor={`obs-${row.id}`} className="text-sm font-normal">
                  <span className="font-mono text-xs">{row.reference}</span> · {row.title}
                </Label>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <Button
              size="sm"
              disabled={contentsMutation.isPending}
              onClick={() => contentsMutation.mutate(selected)}
            >
              Save selection
            </Button>
            <Button variant="outline" size="sm" onClick={() => setContentsFor(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending?.key === "finalise" ? "Finalise and issue report" : "Return report to draft"}
        description={
          pending?.key === "finalise"
            ? "Finalising locks the report and marks every included observation as Reported. Where an observation has no accepted management response, these remarks stand as the Audit Manager's justification."
            : undefined
        }
        reasonLabel={pending?.key === "finalise" ? "Approval remarks" : "Review comments"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) =>
          pending && actionMutation.mutate({ key: pending.key, row: pending.row, reason })
        }
      />
    </div>
  );
}
