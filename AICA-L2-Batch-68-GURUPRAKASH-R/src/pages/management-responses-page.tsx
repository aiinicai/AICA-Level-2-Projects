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
import { responseFields, toResponseInput } from "@/components/reporting/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canAcceptResponse, canAssessResponse, canOpenResponse, canRecordResponse } from "@/lib/permissions";
import { services } from "@/services";
import type { ResponseListItem, ResponseListQuery } from "@/services/management-response.service";
import {
  ACCEPTANCE_TONES,
  MANAGEMENT_ACCEPTANCES,
  RESPONSE_STATUSES,
  RESPONSE_STATUS_TONES,
} from "@/types/reporting";

const COLUMNS = [
  { key: "reference", header: "Response", width: "110px" },
  { key: "observation", header: "Observation" },
  { key: "engagement", header: "Engagement" },
  { key: "respondent", header: "Respondent" },
  { key: "date", header: "Response date" },
  { key: "acceptance", header: "Position" },
  { key: "status", header: "Status" },
  { key: "version", header: "Version", align: "right" as const },
  { key: "actions", header: "Actions", align: "right" as const },
];

export function ManagementResponsesPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("responses.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("responses.filters", {});
  const [recordFor, setRecordFor] = useState<ResponseListItem | null>(null);
  const [pending, setPending] = useState<{ key: "revision" | "accept"; row: ResponseListItem } | null>(null);
  const [openSlot, setOpenSlot] = useState(false);

  const query: ResponseListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    status: filters.status,
    acceptance: filters.acceptance,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["responses", "list", query],
    queryFn: () => services.managementResponses.list(query),
  });

  const observationsQuery = useQuery({
    queryKey: ["observations", "for-response", engagementId ?? "all"],
    queryFn: () =>
      engagementId
        ? services.observations.getByEngagementId(engagementId)
        : services.observations.list({}).then((result) => result.items),
  });

  const awaitingSlot = (observationsQuery.data ?? []).filter(
    (row) => !row.responseReference && row.status !== "Draft" && row.status !== "Dropped",
  );

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["responses"] });
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const openMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      services.managementResponses.create(values.observationId, actor),
    onSuccess: (row) => {
      setOpenSlot(false);
      invalidate();
      toast.success(`${row.reference} opened for response.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const recordMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.managementResponses.recordResponse(id, toResponseInput(values), actor),
    onSuccess: (row) => {
      setRecordFor(null);
      invalidate();
      toast.success(`Version ${row.version} recorded for ${row.reference}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ key, row, reason }: { key: "revision" | "accept"; row: ResponseListItem; reason: string }) =>
      key === "revision"
        ? services.managementResponses.requestRevision(row.id, reason, actor)
        : services.managementResponses.accept(row.id, reason, actor),
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} is now ${row.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const rows = data?.items ?? [];
  const openButton = (
    <Button
      size="sm"
      disabled={!canOpenResponse(role) || awaitingSlot.length === 0}
      title={
        awaitingSlot.length === 0
          ? "Every issued observation already has a response record."
          : undefined
      }
      onClick={() => setOpenSlot(true)}
    >
      Open response record
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Management Responses"
          description="The auditee's position on each observation, the proposed remediation approach and the auditor's assessment."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Management Responses" }]}
          actions={openButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            { key: "status", label: "Status", options: RESPONSE_STATUSES.map((s) => ({ value: s, label: s })) },
            {
              key: "acceptance",
              label: "Management position",
              options: MANAGEMENT_ACCEPTANCES.map((s) => ({ value: s, label: s })),
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Management response register"
        isLoading={isLoading}
        error={isError ? "The management response register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No management responses"
        emptyMessage="Open a response record once an observation has been issued to management."
        emptyAction={canOpenResponse(role) ? openButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search respondent or response text…" />
            {embedded && openButton}
          </>
        }
        footer={`${rows.length} response record(s).`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">{row.reference}</TableCell>
            <TableCell className="max-w-[220px] text-sm">
              <span className="font-mono text-xs">{row.observationRef}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.observationTitle}</span>
            </TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{row.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{row.clientName}</span>
              </TableCell>
            )}
            <TableCell className="text-sm">
              {row.respondent || "—"}
              {row.respondentDesignation && (
                <span className="block text-xs text-muted-foreground">{row.respondentDesignation}</span>
              )}
            </TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {row.responseDate ? formatDate(row.responseDate) : "—"}
            </TableCell>
            <TableCell>
              {row.managementAcceptance ? (
                <StatusBadge
                  status={row.managementAcceptance}
                  tone={ACCEPTANCE_TONES[row.managementAcceptance]}
                />
              ) : (
                <span className="text-xs">—</span>
              )}
            </TableCell>
            <TableCell>
              <StatusBadge status={row.status} tone={RESPONSE_STATUS_TONES[row.status]} />
            </TableCell>
            <TableCell className="text-right font-mono text-xs">{row.version}</TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: row.version === 0 ? "Record response" : "Record revised response",
                    disabled: !canRecordResponse(role) || row.status === "Accepted by Auditor",
                    onSelect: () => setRecordFor(row),
                  },
                  {
                    label: "Request revision",
                    divider: true,
                    disabled: !canAssessResponse(role) || row.status !== "Response Received",
                    onSelect: () => setPending({ key: "revision", row }),
                  },
                  {
                    label: "Accept response",
                    disabled: !canAcceptResponse(role) || row.status !== "Response Received",
                    onSelect: () => setPending({ key: "accept", row }),
                  },
                ]}
              />
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      <PromptDialog
        open={openSlot}
        onOpenChange={setOpenSlot}
        title="Open a management response record"
        description="Select the issued observation awaiting a response from the process owner."
        fields={[
          {
            name: "observationId",
            label: "Observation",
            type: "select",
            required: true,
            options: awaitingSlot.map((row) => ({
              value: row.id,
              label: `${row.reference} · ${row.title}`,
            })),
          },
        ]}
        submitLabel="Open record"
        pending={openMutation.isPending}
        onSubmit={(values) => openMutation.mutate(values)}
      />

      <PromptDialog
        open={recordFor !== null}
        onOpenChange={(open) => !open && setRecordFor(null)}
        wide
        title={`Record response for ${recordFor?.observationRef ?? ""}`}
        description="Earlier versions are preserved in the response history; nothing is overwritten."
        fields={responseFields}
        initialValues={{
          respondent: recordFor?.respondent ?? "",
          respondentDesignation: recordFor?.respondentDesignation ?? "",
          responseDate: new Date().toISOString().slice(0, 10),
          managementAcceptance: recordFor?.managementAcceptance ?? "",
          managementResponse: recordFor?.managementResponse ?? "",
          causeAcknowledged: recordFor?.causeAcknowledged ?? "",
          proposedApproach: recordFor?.proposedApproach ?? "",
          managementRemarks: recordFor?.managementRemarks ?? "",
        }}
        submitLabel="Save response"
        pending={recordMutation.isPending}
        onSubmit={(values) => recordFor && recordMutation.mutate({ id: recordFor.id, values })}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending?.key === "accept" ? "Accept management response" : "Request a revised response"}
        reasonLabel={pending?.key === "accept" ? "Auditor assessment" : "What needs to be revised"}
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) =>
          pending && actionMutation.mutate({ key: pending.key, row: pending.row, reason })
        }
      />
    </div>
  );
}
