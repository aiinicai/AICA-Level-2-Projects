import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { PromptDialog, type PromptField, type PromptValues } from "@/components/common/prompt-dialog";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { RowActions } from "@/components/common/row-actions";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import {
  clarificationFields,
  toClarificationValues,
  toPromptValues,
} from "@/components/fieldwork/form-configs";
import { useFieldworkOptions } from "@/components/fieldwork/use-fieldwork-options";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import {
  canConvertClarification,
  canManageClarification,
  canRespondToClarification,
} from "@/lib/permissions";
import { services } from "@/services";
import type { ClarificationListItem, ClarificationListQuery } from "@/services/clarification.service";
import { CLARIFICATION_STATUSES, CLARIFICATION_TONES } from "@/types/fieldwork";

const COLUMNS = [
  { key: "reference", header: "Clarification", width: "110px" },
  { key: "engagement", header: "Engagement" },
  { key: "subject", header: "Subject" },
  { key: "linked", header: "Linked record" },
  { key: "raised", header: "Raised" },
  { key: "respondent", header: "Respondent" },
  { key: "due", header: "Response due" },
  { key: "status", header: "Status" },
  { key: "observation", header: "Observation" },
  { key: "actions", header: "Actions", align: "right" as const },
];

const OPEN_FIELDS: PromptField[] = [
  { name: "respondent", label: "Respondent", required: true },
  { name: "responseDueDate", label: "Response due date", type: "date", required: true },
];

const RESPONSE_FIELDS: PromptField[] = [
  { name: "responseDate", label: "Response date", type: "date", required: true },
  { name: "auditeeResponse", label: "Auditee response", type: "textarea", required: true, rows: 4, minLength: 5 },
];

type PendingAction =
  | { key: "further"; row: ClarificationListItem }
  | { key: "resolve"; row: ClarificationListItem }
  | { key: "close"; row: ClarificationListItem }
  | { key: "convert"; row: ClarificationListItem };

export function ClarificationsPage({ engagementId }: { engagementId?: string }) {
  const embedded = Boolean(engagementId);
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const { engagementOptions, scopes, procedures, requirements, evidence } = useFieldworkOptions();

  const [search, setSearch] = useCachedState("clarifications.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("clarifications.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<ClarificationListQuery["sortBy"]>>(
    "clarifications.sortBy",
    "reference",
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ClarificationListItem | null>(null);
  const [openFor, setOpenFor] = useState<ClarificationListItem | null>(null);
  const [responseFor, setResponseFor] = useState<ClarificationListItem | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);

  const query: ClarificationListQuery = {
    search,
    engagementId: engagementId ?? filters.engagementId,
    status: filters.status,
    sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["clarifications", "list", query],
    queryFn: () => services.clarifications.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["clarifications"] });
    void queryClient.invalidateQueries({ queryKey: ["observations"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.clarifications.update(editing.id, toClarificationValues(values), actor)
        : services.clarifications.create(toClarificationValues(values), actor),
    onSuccess: (row) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${row.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const openMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.clarifications.open(
        id,
        { respondent: values.respondent, responseDueDate: values.responseDueDate },
        actor,
      ),
    onSuccess: (row) => {
      setOpenFor(null);
      invalidate();
      toast.success(`${row.reference} is now Open.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const responseMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: PromptValues }) =>
      services.clarifications.recordResponse(
        id,
        { auditeeResponse: values.auditeeResponse, responseDate: values.responseDate },
        actor,
      ),
    onSuccess: (row) => {
      setResponseFor(null);
      invalidate();
      toast.success(`Response recorded for ${row.reference}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: async ({ action, reason }: { action: PendingAction; reason: string }) => {
      const id = action.row.id;
      if (action.key === "further") return services.clarifications.seekFurther(id, reason, actor);
      if (action.key === "resolve") return services.clarifications.resolve(id, reason, actor);
      if (action.key === "close") return services.clarifications.closeWithoutObservation(id, reason, actor);
      const result = await services.clarifications.convertToObservation(id, actor);
      toast.success(`Observation ${result.observation.reference} reserved.`);
      return result.clarification;
    },
    onSuccess: (row) => {
      setPending(null);
      invalidate();
      toast.success(`${row.reference} is now ${row.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageClarification(role);
  const rows = data?.items ?? [];

  const addButton = (
    <Button
      size="sm"
      disabled={!manage}
      title={manage ? undefined : "Auditees may respond to clarifications but not raise them."}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Raise clarification
    </Button>
  );

  return (
    <div className="space-y-6">
      {!embedded && (
        <PageHeader
          title="Audit Clarifications"
          description="Queries raised with the auditee during fieldwork, their responses, the auditor's conclusion and any resulting observation."
          breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Audit Clarifications" }]}
          actions={addButton}
        />
      )}

      {!embedded && (
        <FilterPanel
          filters={[
            { key: "engagementId", label: "Engagement", options: engagementOptions },
            {
              key: "status",
              label: "Status",
              options: CLARIFICATION_STATUSES.map((s) => ({ value: s, label: s })),
            },
          ]}
          values={filters}
          onChange={(key, value) => setFilters({ ...filters, [key]: value })}
          onReset={() => setFilters({})}
        />
      )}

      <DataTableShell
        columns={embedded ? COLUMNS.filter((column) => column.key !== "engagement") : COLUMNS}
        caption="Clarification register"
        isLoading={isLoading}
        error={isError ? "The clarification register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No clarifications raised"
        emptyMessage="Raise a clarification when evidence or a test result needs an explanation from the auditee."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder="Search subject, query or respondent…" />
            <div className="flex flex-wrap items-center gap-2">
              {embedded && addButton}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortBy(sortBy === "responseDueDate" ? "reference" : "responseDueDate")}
              >
                Sort: {sortBy === "responseDueDate" ? "Response due" : "Clarification ID"}
              </Button>
            </div>
          </>
        }
        footer={`${rows.length} clarification(s).`}
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
            <TableCell className="max-w-[240px] text-sm">
              <span className="block truncate font-medium">{row.subject}</span>
              <span className="block truncate text-xs text-muted-foreground">
                {row.clarificationRaised}
              </span>
            </TableCell>
            <TableCell className="font-mono text-xs">{row.linkedRecord}</TableCell>
            <TableCell className="text-xs whitespace-nowrap">
              {formatDate(row.dateRaised)}
              <span className="block text-muted-foreground">{row.raisedBy}</span>
            </TableCell>
            <TableCell className="text-sm">{row.respondent || "—"}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">
              {row.responseDueDate ? formatDate(row.responseDueDate) : "—"}
            </TableCell>
            <TableCell>
              <StatusBadge status={row.status} tone={CLARIFICATION_TONES[row.status]} />
            </TableCell>
            <TableCell className="font-mono text-xs">{row.observationId ?? "—"}</TableCell>
            <TableCell className="text-right">
              <RowActions
                label={`Actions for ${row.reference}`}
                actions={[
                  {
                    label: "Edit clarification",
                    disabled: !manage || row.status !== "Draft",
                    onSelect: () => {
                      setEditing(row);
                      setFormOpen(true);
                    },
                  },
                  {
                    label: "Open clarification",
                    disabled: !manage || row.status !== "Draft",
                    onSelect: () => setOpenFor(row),
                  },
                  {
                    label: "Record response",
                    divider: true,
                    disabled:
                      !canRespondToClarification(role) ||
                      (row.status !== "Open" && row.status !== "Further Clarification Required"),
                    onSelect: () => setResponseFor(row),
                  },
                  {
                    label: "Seek further clarification",
                    disabled: !manage || row.status !== "Response Received",
                    onSelect: () => setPending({ key: "further", row }),
                  },
                  {
                    label: "Resolve clarification",
                    disabled: !manage || row.status !== "Response Received",
                    onSelect: () => setPending({ key: "resolve", row }),
                  },
                  {
                    label: "Convert to observation",
                    divider: true,
                    disabled: !canConvertClarification(role) || row.status !== "Resolved",
                    onSelect: () => setPending({ key: "convert", row }),
                  },
                  {
                    label: "Close without observation",
                    disabled: !manage || row.status !== "Resolved",
                    onSelect: () => setPending({ key: "close", row }),
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
        title={editing ? `Edit ${editing.reference}` : "Raise clarification"}
        description="Link the clarification to the scope, procedure, requirement or evidence it relates to."
        fields={clarificationFields(
          { engagements: engagementOptions, scopes, procedures, requirements, evidence },
          Boolean(editing) || embedded,
        )}
        initialValues={
          editing
            ? toPromptValues(editing)
            : engagementId
              ? { engagementId, dateRaised: new Date().toISOString().slice(0, 10), raisedBy: actor.user }
              : { dateRaised: new Date().toISOString().slice(0, 10), raisedBy: actor.user }
        }
        submitLabel={editing ? "Save clarification" : "Create clarification"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <PromptDialog
        open={openFor !== null}
        onOpenChange={(open) => !open && setOpenFor(null)}
        title={`Open ${openFor?.reference ?? ""}`}
        description="Issuing the clarification requires a named respondent and a response due date."
        fields={OPEN_FIELDS}
        initialValues={
          openFor ? { respondent: openFor.respondent, responseDueDate: openFor.responseDueDate } : undefined
        }
        submitLabel="Open clarification"
        pending={openMutation.isPending}
        onSubmit={(values) => openFor && openMutation.mutate({ id: openFor.id, values })}
      />

      <PromptDialog
        open={responseFor !== null}
        onOpenChange={(open) => !open && setResponseFor(null)}
        title={`Record response for ${responseFor?.reference ?? ""}`}
        fields={RESPONSE_FIELDS}
        initialValues={{ responseDate: new Date().toISOString().slice(0, 10) }}
        submitLabel="Save response"
        pending={responseMutation.isPending}
        onSubmit={(values) => responseFor && responseMutation.mutate({ id: responseFor.id, values })}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending?.key === "further"
            ? "Seek further clarification"
            : pending?.key === "resolve"
              ? "Resolve clarification"
              : pending?.key === "convert"
                ? "Convert to observation"
                : "Close without observation"
        }
        description={
          pending?.key === "convert"
            ? "A draft observation reference is reserved and carried into the observations module."
            : undefined
        }
        reasonLabel={
          pending?.key === "resolve"
            ? "Auditor conclusion"
            : pending?.key === "convert"
              ? "Conversion remarks"
              : "Reason"
        }
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) => pending && actionMutation.mutate({ action: pending, reason })}
      />
    </div>
  );
}
