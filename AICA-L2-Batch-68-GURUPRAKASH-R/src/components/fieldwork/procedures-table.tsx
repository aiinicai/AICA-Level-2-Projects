import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { PromptDialog, type PromptValues } from "@/components/common/prompt-dialog";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { RowActions } from "@/components/common/row-actions";
import { StatusBadge } from "@/components/common/status-badge";
import { procedureFields, toProcedureValues, toPromptValues } from "@/components/fieldwork/form-configs";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate } from "@/lib/format";
import { canManageProcedure, canReopenProcedure } from "@/lib/permissions";
import { services } from "@/services";
import type { ProcedureListItem, ProcedureListQuery } from "@/services/procedure.service";
import {
  PROCEDURE_FINAL_STATUSES,
  PROCEDURE_STATUS_TONES,
  PROCEDURE_TRANSITIONS,
  type ProcedureStatus,
} from "@/types/fieldwork";

const COLUMNS = [
  { key: "reference", header: "Procedure", width: "100px" },
  { key: "scope", header: "Scope" },
  { key: "description", header: "Procedure description" },
  { key: "risk", header: "Risk addressed" },
  { key: "sample", header: "Sample" },
  { key: "auditor", header: "Auditor" },
  { key: "target", header: "Target date" },
  { key: "requirements", header: "Reqs", align: "right" as const },
  { key: "status", header: "Status" },
  { key: "actions", header: "Actions", align: "right" as const },
];

export interface ProceduresTableProps {
  /** Restrict to a single scope; enables inline creation with the scope locked. */
  scopeId?: string;
  engagementId?: string;
  scopeOptions?: { value: string; label: string }[];
  title?: string;
}

type PendingAction =
  | { key: "status"; procedure: ProcedureListItem; next: ProcedureStatus }
  | { key: "notApplicable"; procedure: ProcedureListItem }
  | { key: "reopen"; procedure: ProcedureListItem }
  | { key: "conclude"; procedure: ProcedureListItem };

export function ProceduresTable({ scopeId, engagementId, scopeOptions = [], title }: ProceduresTableProps) {
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ProcedureListItem | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);

  const query: ProcedureListQuery = { scopeId, engagementId };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["procedures", "list", query],
    queryFn: () => services.procedures.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["procedures"] });
    void queryClient.invalidateQueries({ queryKey: ["scopes"] });
    void queryClient.invalidateQueries({ queryKey: ["requirements"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) =>
      editing
        ? services.procedures.update(editing.id, toProcedureValues(values, editing.conclusion), actor)
        : services.procedures.create(toProcedureValues(values), actor),
    onSuccess: (procedure) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${procedure.reference} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ action, reason }: { action: PendingAction; reason: string }) => {
      const id = action.procedure.id;
      if (action.key === "status") return services.procedures.changeStatus(id, action.next, reason, actor);
      if (action.key === "notApplicable") return services.procedures.markNotApplicable(id, reason, actor);
      if (action.key === "reopen") return services.procedures.reopen(id, reason, actor);
      return services.procedures.recordConclusion(id, reason, actor);
    },
    onSuccess: (procedure) => {
      setPending(null);
      invalidate();
      toast.success(`${procedure.reference} is now ${procedure.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const manage = canManageProcedure(role);
  const rows = data?.items ?? [];
  const options = scopeOptions.length > 0 ? scopeOptions : [];

  const addButton = (
    <Button
      size="sm"
      disabled={!manage || (!scopeId && options.length === 0)}
      title={manage ? undefined : "Auditees may only view test procedures."}
      onClick={() => {
        setEditing(null);
        setFormOpen(true);
      }}
    >
      <Plus className="size-4" aria-hidden />
      Add procedure
    </Button>
  );

  return (
    <>
      <DataTableShell
        columns={scopeId ? COLUMNS.filter((column) => column.key !== "scope") : COLUMNS}
        caption={title ?? "Test procedures"}
        isLoading={isLoading}
        error={isError ? "Test procedures could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={rows.length === 0}
        emptyTitle="No test procedures"
        emptyMessage="Add the audit steps that will test the controls in this scope."
        emptyAction={manage ? addButton : undefined}
        toolbar={
          <>
            <p className="text-sm font-medium">{title ?? "Test procedures"}</p>
            {addButton}
          </>
        }
        footer={`${rows.length} procedure(s).`}
      >
        {rows.map((procedure) => {
          const isFinal = PROCEDURE_FINAL_STATUSES.includes(procedure.status);
          const nextStatuses = PROCEDURE_TRANSITIONS[procedure.status] ?? [];
          return (
            <TableRow key={procedure.id}>
              <TableCell className="font-mono text-xs">{procedure.reference}</TableCell>
              {!scopeId && (
                <TableCell className="text-sm">
                  <span className="font-mono text-xs">{procedure.scopeRef}</span>
                  <span className="block text-xs text-muted-foreground">{procedure.process}</span>
                </TableCell>
              )}
              <TableCell className="max-w-[280px] truncate text-sm">{procedure.description}</TableCell>
              <TableCell className="max-w-[200px] truncate text-sm">{procedure.riskAddressed}</TableCell>
              <TableCell className="text-xs">
                {procedure.sampleSize || "—"}
                {procedure.sampleMethod && (
                  <span className="block text-muted-foreground">{procedure.sampleMethod}</span>
                )}
              </TableCell>
              <TableCell className="text-sm whitespace-nowrap">{procedure.assignedAuditor}</TableCell>
              <TableCell className="text-sm whitespace-nowrap">{formatDate(procedure.targetDate)}</TableCell>
              <TableCell className="text-right text-sm tabular-nums">{procedure.requirementCount}</TableCell>
              <TableCell>
                <StatusBadge status={procedure.status} tone={PROCEDURE_STATUS_TONES[procedure.status]} />
              </TableCell>
              <TableCell className="text-right">
                <RowActions
                  label={`Actions for ${procedure.reference}`}
                  actions={[
                    {
                      label: "Edit procedure",
                      disabled: !manage || isFinal,
                      onSelect: () => {
                        setEditing(procedure);
                        setFormOpen(true);
                      },
                    },
                    ...nextStatuses
                      .filter((next) => next !== "Not Applicable")
                      .map((next) => ({
                        label: `Move to ${next}`,
                        disabled: !manage,
                        onSelect: () => setPending({ key: "status", procedure, next }),
                      })),
                    {
                      label: "Record conclusion",
                      disabled: !manage || procedure.status === "Not Applicable",
                      divider: true,
                      onSelect: () => setPending({ key: "conclude", procedure }),
                    },
                    {
                      label: "Mark not applicable",
                      disabled: !manage || isFinal,
                      onSelect: () => setPending({ key: "notApplicable", procedure }),
                    },
                    {
                      label: "Reopen procedure",
                      disabled: !canReopenProcedure(role) || !isFinal,
                      title: canReopenProcedure(role) ? undefined : "Audit Manager only.",
                      onSelect: () => setPending({ key: "reopen", procedure }),
                    },
                  ]}
                />
              </TableCell>
            </TableRow>
          );
        })}
      </DataTableShell>

      <PromptDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        wide
        title={editing ? `Edit ${editing.reference}` : "Add test procedure"}
        description="Each procedure tests a control within a scope area and drives the data requirements."
        fields={procedureFields(
          scopeId ? [{ value: scopeId, label: scopeId }] : options,
          Boolean(scopeId) || Boolean(editing),
        )}
        initialValues={editing ? toPromptValues(editing) : scopeId ? { scopeId } : undefined}
        submitLabel={editing ? "Save procedure" : "Create procedure"}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <ReasonDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={
          pending?.key === "status"
            ? `Move procedure to ${pending.next}`
            : pending?.key === "conclude"
              ? "Record procedure conclusion"
              : pending?.key === "reopen"
                ? "Reopen procedure"
                : "Mark procedure not applicable"
        }
        reasonLabel={
          pending?.key === "conclude" ? "Conclusion" : pending?.key === "status" ? "Remarks" : "Reason"
        }
        confirmLabel="Confirm"
        pending={actionMutation.isPending}
        onConfirm={(reason) => pending && actionMutation.mutate({ action: pending, reason })}
      />
    </>
  );
}
