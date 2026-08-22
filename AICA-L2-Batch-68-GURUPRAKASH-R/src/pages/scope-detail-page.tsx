import { useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { DetailCard, DetailField } from "@/components/common/detail-card";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading-state";
import { PageHeader } from "@/components/common/page-header";
import { PromptDialog, type PromptValues } from "@/components/common/prompt-dialog";
import { StatusBadge } from "@/components/common/status-badge";
import { ProceduresTable } from "@/components/fieldwork/procedures-table";
import { scopeFields, toPromptValues, toScopeValues } from "@/components/fieldwork/form-configs";
import { Button } from "@/components/ui/button";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDateTime } from "@/lib/format";
import { canManageScope } from "@/lib/permissions";
import { services } from "@/services";
import { SCOPE_STATUS_TONES } from "@/types/fieldwork";

export function ScopeDetailPage() {
  const { scopeId } = useParams({ from: "/scope-programme/$scopeId" });
  const { role } = useRole();
  const actor = useActor();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);

  const scopeQuery = useQuery({
    queryKey: ["scopes", "detail", scopeId],
    queryFn: () => services.scopes.getById(scopeId),
  });

  const saveMutation = useMutation({
    mutationFn: (values: PromptValues) => services.scopes.update(scopeId, toScopeValues(values), actor),
    onSuccess: () => {
      setFormOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["scopes"] });
      void queryClient.invalidateQueries({ queryKey: ["activity"] });
      toast.success("Scope updated.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (scopeQuery.isLoading) return <LoadingState label="Loading scope…" />;
  if (scopeQuery.isError) return <ErrorState onRetry={() => void scopeQuery.refetch()} />;

  const scope = scopeQuery.data;
  if (!scope) {
    return (
      <EmptyState
        title="Scope not found"
        message="This scope record does not exist in the current data set."
        action={
          <Button variant="outline" size="sm" onClick={() => void navigate({ to: "/scope-programme" })}>
            Back to scope register
          </Button>
        }
      />
    );
  }

  const editable = canManageScope(role) && scope.status !== "Completed" && scope.status !== "Not Applicable";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${scope.reference} · ${scope.process}`}
        description={scope.objective}
        breadcrumbs={[
          { label: "AuditFlow", to: "/" },
          { label: "Scope & Audit Programme", to: "/scope-programme" },
          { label: scope.reference },
        ]}
        meta={
          <>
            <StatusBadge status={scope.status} tone={SCOPE_STATUS_TONES[scope.status]} />
            <Link
              to="/engagements/$engagementId"
              params={{ engagementId: scope.engagementId }}
              className="text-xs text-primary hover:underline"
            >
              {scope.engagementRef} · {scope.clientName}
            </Link>
          </>
        }
        actions={
          <Button size="sm" variant="outline" disabled={!editable} onClick={() => setFormOpen(true)}>
            Edit scope
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <DetailCard title="Scope definition" className="lg:col-span-2">
          <dl className="grid gap-4 sm:grid-cols-2">
            <DetailField label="Process" value={scope.process} />
            <DetailField label="Sub-process" value={scope.subProcess || "—"} />
            <DetailField label="Key risk" value={scope.keyRisk} />
            <DetailField label="Expected control" value={scope.expectedControl} />
            <DetailField label="Scope inclusion" value={scope.inclusion || "—"} />
            <DetailField label="Scope exclusion" value={scope.exclusion || "—"} />
            <DetailField label="Applicable policy" value={scope.applicablePolicy || "—"} />
            <DetailField label="Remarks" value={scope.remarks || "—"} />
          </dl>
        </DetailCard>
        <DetailCard title="Ownership">
          <dl className="grid gap-4">
            <DetailField label="Assigned auditor" value={scope.assignedAuditor} />
            <DetailField label="Procedures" value={String(scope.procedureCount)} />
            <DetailField
              label="Created"
              value={`${formatDateTime(scope.createdAt)} · ${scope.createdBy}`}
            />
            <DetailField
              label="Last updated"
              value={`${formatDateTime(scope.updatedAt)} · ${scope.updatedBy}`}
            />
          </dl>
        </DetailCard>
      </div>

      <ProceduresTable scopeId={scope.id} title="Test procedures under this scope" />

      <PromptDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        wide
        title={`Edit ${scope.reference}`}
        fields={scopeFields([{ value: scope.engagementId, label: scope.engagementRef }], true)}
        initialValues={toPromptValues(scope)}
        submitLabel="Save scope"
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />
    </div>
  );
}
