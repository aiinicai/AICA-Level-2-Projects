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
  closureUpdateFields,
  toClosureUpdateInput,
  toVerificationInput,
  verificationFields,
} from "@/components/reporting/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import { canRecordClosureUpdate, canReopenAction, canVerifyClosure } from "@/lib/permissions";
import { services } from "@/services";
import type { ClosureListItem, ClosureListQuery } from "@/services/closure-update.service";
import { IMPLEMENTATION_STATUSES, IMPLEMENTATION_TONES } from "@/types/reporting";

const COLUMNS = [
  { key: "reference", header: "Update", width: "100px" },
  { key: "action", header: "Management action" },
  { key: "engagement", header: "Engagement" },
  { key: "date", header: "Update date" },
  { key: "update", header: "Progress reported" },
  { key: "status", header: "Status" },
  { key: "verification", header: "Verification" },
  { key: "actions", header: "Actions", align: "right" as const },
];

export function ClosureTrackingPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("closure.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("closure.filters", {});
  const [addOpen, setAddOpen] = useState(false);
  const [verifyFor, setVerifyFor] = useState<ClosureListItem | null>(null);
  const [reopenFor, setReopenFor] = useState<string | null>(null);

  const query: ClosureListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    implementationStatus: filters.implementationStatus,
    verification: (filters.verification as ClosureListQuery["verification"]) ?? "all",
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["closure", "list", query],
    queryFn: () => services.closureUpdates.list(query),
  });

  const actionsQuery = useQuery({
    queryKey: ["actions", "for-closure", engagementId ?? "all"],
    queryFn: () =>
      engagementId
        ? services.managementActions.getByEngagementId(engagementId)
        : services.managementActions.list({}).then((result) => result.items),
  });

  const openActions = (actionsQuery.data ?? []).filter(
    (row) => row.agreementStatus === "Agreed by Auditor" && row.implementationStatus !== "Closed",
  );
  const closedActions = (actionsQuery.data ?? []).filter((row) => row.implementationStatus === "Closed");

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["closure"] });
    void queryClient.invalidateQueries({ queryKey: ["actions"] });
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const addMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      services.closureUpdates.addUpdate(values.actionId, toClosureUpdateInput(values, actor.user), actor),
    onSuccess: (row) => {
      setAddOpen(false);
      invalidate();
      toast.success(`${row.reference} recorded.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const verifyMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.closureUpdates.verify(id, toVerificationInput(values), actor),
    onSuccess: (row) => {
      setVerifyFor(null);
      invalidate();
      toast.success(`${row.reference} verified as ${row.implementationStatus}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const reopenMutation = useMutation({
    mutationFn: ({ actionId, reason }: { actionId: string; reason: string }) =>
      services.closureUpdates.reopenAction(actionId, reason, actor),
    onSuccess: () => {
      setReopenFor(null);
      invalidate();
      toast.success("Management action reopened.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const rows = data?.items ?? [];

  const addButton = (
    <Button
      size="sm"
      disabled={!canRecordClosureUpdate(role) || openActions.length === 0}
      title={openActions.length === 0 ? "No agreed, open management actions to update." : undefined}
      onClick={() => setAddOpen(true)}
    >
      Record closure update
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Closure Tracking"
          description="Follow-up updates from management, the auditor's verification of implementation, and the formal closure of each agreed action."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Closure Tracking" }]}
          actions={
            <div className="flex flex-wrap gap-2">
              {addButton}
              <Button
                variant="outline"
                size="sm"
                disabled={!canReopenAction(role) || closedActions.length === 0}
                onClick={() => setReopenFor(closedActions[0]?.id ?? null)}
              >
                Reopen a closed action
              </Button>
            </div>
          }
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            {
              key: "implementationStatus",
              label: "Implementation",
              options: IMPLEMENTATION_STATUSES.map((s) => ({ value: s, label: s })),
            },
            {
              key: "verification",
              label: "Verification",
              options: [
                { value: "pending", label: "Awaiting verification" },
                { value: "verified", label: "Verified" },
              ],
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Closure update register"
        isLoading={isLoading}
        error={isError ? "The closure register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No closure updates"
        emptyMessage="Record progress against agreed management actions to build the closure trail."
        emptyAction={canRecordClosureUpdate(role) ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search action, update or person…" />
            {embedded && addButton}
          </>
        }
        footer={`${rows.length} update(s). Closure updates are append-only and are never edited or deleted.`}
      >
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs">{row.reference}</TableCell>
            <TableCell className="max-w-[220px] text-sm">
              <span className="font-mono text-xs">{row.actionRef}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.actionTitle}</span>
            </TableCell>
            {!embedded && (
              <TableCell className="text-sm">
                <span className="font-mono text-xs">{row.engagementRef}</span>
                <span className="block text-xs text-muted-foreground">{row.clientName}</span>
              </TableCell>
            )}
            <TableCell className="text-xs whitespace-nowrap">
              {formatDate(row.updateDate)}
              <span className="block text-muted-foreground">{row.updatedByPerson}</span>
            </TableCell>
            <TableCell className="max-w-[260px] text-sm">
              <span className="block truncate">{row.managementUpdate}</span>
              {row.closureEvidence && (
                <span className="block truncate text-xs text-muted-foreground">
                  Evidence: {row.closureEvidence.fileName}
                </span>
              )}
            </TableCell>
            <TableCell>
              <StatusBadge
                status={row.implementationStatus}
                tone={IMPLEMENTATION_TONES[row.implementationStatus]}
              />
            </TableCell>
            <TableCell className="max-w-[220px] text-xs">
              {row.verified ? (
                <>
                  <span className="block truncate">{row.auditorVerification}</span>
                  <span className="block text-muted-foreground">
                    {formatDate(row.auditorVerificationDate)}
                  </span>
                </>
              ) : (
                <span className="text-muted-foreground">Awaiting verification</span>
              )}
            </TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Verify update",
                    disabled: !canVerifyClosure(role) || row.verified,
                    onSelect: () => setVerifyFor(row),
                  },
                  {
                    label: "Reopen this action",
                    divider: true,
                    disabled: !canReopenAction(role),
                    onSelect: () => setReopenFor(row.actionId),
                  },
                ]}
              />
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      <PromptDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        wide
        title="Record closure update"
        description="Updates are appended to the action's history; earlier updates remain unchanged."
        fields={[
          {
            name: "actionId",
            label: "Management action",
            type: "select",
            required: true,
            options: openActions.map((row) => ({
              value: row.id,
              label: `${row.reference} · ${row.title}`,
            })),
          },
          ...closureUpdateFields,
        ]}
        initialValues={{
          updateDate: new Date().toISOString().slice(0, 10),
          updatedByPerson: actor.user,
          implementationStatus: "Update Received",
        }}
        submitLabel="Record update"
        pending={addMutation.isPending}
        onSubmit={(values) => addMutation.mutate(values)}
      />

      <PromptDialog
        open={verifyFor !== null}
        onOpenChange={(open) => !open && setVerifyFor(null)}
        wide
        title={`Verify ${verifyFor?.reference ?? ""}`}
        description="Closing an action requires a conclusion; accepting the residual risk requires a rationale."
        fields={verificationFields}
        initialValues={{ implementationStatus: verifyFor?.implementationStatus ?? "Implemented" }}
        submitLabel="Save verification"
        pending={verifyMutation.isPending}
        onSubmit={(values) => verifyFor && verifyMutation.mutate({ id: verifyFor.id, values })}
      />

      <ReasonDialog
        open={reopenFor !== null}
        onOpenChange={(open) => !open && setReopenFor(null)}
        title="Reopen management action"
        description="A new closure update is appended recording the reopening; nothing in the history is altered."
        reasonLabel="Reason for reopening"
        confirmLabel="Reopen action"
        pending={reopenMutation.isPending}
        onConfirm={(reason) => reopenFor && reopenMutation.mutate({ actionId: reopenFor, reason })}
      />
    </div>
  );
}
