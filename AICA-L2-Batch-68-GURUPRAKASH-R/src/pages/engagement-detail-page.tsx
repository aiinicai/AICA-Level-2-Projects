import { useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ActivityTable } from "@/components/common/activity-table";
import { DetailCard, DetailField } from "@/components/common/detail-card";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LifecycleIndicator } from "@/components/common/lifecycle-indicator";
import { LoadingState } from "@/components/common/loading-state";
import { MetricCard } from "@/components/common/metric-card";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import { ProceduresTable } from "@/components/fieldwork/procedures-table";
import { ClarificationsPage } from "@/pages/clarifications-page";
import { DataRequirementsPage } from "@/pages/data-requirements-page";
import { EvidenceReviewPage } from "@/pages/evidence-review-page";
import { ScopeProgrammePage } from "@/pages/scope-programme-page";
import { ObservationsPage } from "@/pages/observations-page";
import { ManagementResponsesPage } from "@/pages/management-responses-page";
import { ManagementActionsPage } from "@/pages/management-actions-page";
import { ClosureTrackingPage } from "@/pages/closure-tracking-page";
import { FinalReportingPage } from "@/pages/final-reporting-page";
import { EngagementActions } from "@/components/engagements/engagement-actions";
import { EngagementFormDialog } from "@/components/engagements/engagement-form-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate, formatDateTime } from "@/lib/format";
import { canEditEngagement } from "@/lib/permissions";
import { services } from "@/services";
import {
  ENGAGEMENT_STATUS_TONES,
  resolveStage,
  type EngagementFormValues,
} from "@/types/engagement";

const SUMMARY_CARDS = [
  { label: "Scope items", hint: "Stage 3" },
  { label: "Procedures", hint: "Stage 3" },
  { label: "Requirements", hint: "Stage 3" },
  { label: "Clarifications", hint: "Stage 4" },
  { label: "Observations", hint: "Stage 5" },
  { label: "Open actions", hint: "Stage 5" },
];

export function EngagementDetailPage() {
  const { engagementId } = useParams({ from: "/engagements/$engagementId" });
  const { role } = useRole();
  const actor = useActor();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);

  const engagementQuery = useQuery({
    queryKey: ["engagements", "detail", engagementId],
    queryFn: () => services.engagements.getById(engagementId),
  });
  const activityQuery = useQuery({
    queryKey: ["activity", "engagement", engagementId],
    queryFn: () => services.activity.getByEngagementId(engagementId),
  });
  const scopesQuery = useQuery({
    queryKey: ["scopes", "engagement", engagementId],
    queryFn: () => services.scopes.getByEngagementId(engagementId),
  });
  const clientsQuery = useQuery({
    queryKey: ["clients", "options"],
    queryFn: () => services.clients.list({ pageSize: 500 }),
  });

  const scopeOptions = (scopesQuery.data ?? []).map((scope) => ({
    value: scope.id,
    label: `${scope.reference} · ${scope.process}`,
  }));

  const saveMutation = useMutation({
    mutationFn: (values: EngagementFormValues) =>
      services.engagements.update(engagementId, values, actor),
    onSuccess: () => {
      setFormOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["engagements"] });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      void queryClient.invalidateQueries({ queryKey: ["activity"] });
      toast.success("Engagement updated.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (engagementQuery.isLoading) return <LoadingState label="Loading engagement…" />;
  if (engagementQuery.isError) return <ErrorState onRetry={() => void engagementQuery.refetch()} />;

  const engagement = engagementQuery.data;
  if (!engagement) {
    return (
      <EmptyState
        title="Engagement not found"
        message="This engagement record does not exist in the current data set."
        action={
          <Button variant="outline" size="sm" onClick={() => void navigate({ to: "/engagements" })}>
            Back to engagements
          </Button>
        }
      />
    );
  }

  const stage = resolveStage(engagement.status, engagement.lifecycleStage);

  return (
    <div className="space-y-6">
      <PageHeader
        title={engagement.title}
        description={`${engagement.reference} · ${engagement.auditType} · ${engagement.auditArea}`}
        breadcrumbs={[
          { label: "AuditFlow", to: "/" },
          { label: "Audit Engagements", to: "/engagements" },
          { label: engagement.reference },
        ]}
        meta={
          <>
            <StatusBadge status={engagement.status} tone={ENGAGEMENT_STATUS_TONES[engagement.status]} />
            <span className="text-xs text-muted-foreground">Lifecycle stage: {stage}</span>
            {engagement.status === "On Hold" && engagement.priorStatus && (
              <span className="text-xs text-muted-foreground">
                On hold from {engagement.priorStatus}
              </span>
            )}
          </>
        }
        actions={
          <EngagementActions
            engagement={engagement}
            onEdit={canEditEngagement(role) ? () => setFormOpen(true) : undefined}
          />
        }
      />

      {engagement.status === "Cancelled" && (
        <div
          role="status"
          className="rounded-md border border-critical-foreground/25 bg-critical px-4 py-3 text-sm text-critical-foreground"
        >
          This engagement was cancelled at the {engagement.lifecycleStage} stage. The record is retained
          for reference and no further workflow transitions are available.
        </div>
      )}

      <DetailCard title="Engagement lifecycle">
        <LifecycleIndicator currentStage={stage} />
      </DetailCard>

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="scope">Scope &amp; Procedures</TabsTrigger>
          <TabsTrigger value="requirements">Requirements &amp; Evidence</TabsTrigger>
          <TabsTrigger value="clarifications">Clarifications</TabsTrigger>
          <TabsTrigger value="observations">Observations</TabsTrigger>
          <TabsTrigger value="reporting">Reporting</TabsTrigger>
          <TabsTrigger value="closure">Actions &amp; Closure</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {SUMMARY_CARDS.map((card) => (
              <MetricCard
                key={card.label}
                metric={{ key: card.label, label: card.label, value: 0, hint: card.hint, tone: "neutral" }}
              />
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <DetailCard title="Engagement details" className="lg:col-span-2">
              <dl className="grid gap-4 sm:grid-cols-3">
                <DetailField
                  label="Reference"
                  value={<span className="font-mono">{engagement.reference}</span>}
                />
                <DetailField
                  label="Client"
                  value={
                    <Link
                      to="/clients/$clientId"
                      params={{ clientId: engagement.clientId }}
                      className="text-primary hover:underline"
                    >
                      {engagement.clientName}
                    </Link>
                  }
                />
                <DetailField label="Location" value={engagement.location || "—"} />
                <DetailField label="Audit type" value={engagement.auditType} />
                <DetailField label="Audit area" value={engagement.auditArea} />
                <DetailField
                  label="Audit period"
                  value={`${formatDate(engagement.auditPeriodFrom)} – ${formatDate(engagement.auditPeriodTo)}`}
                />
                <DetailField label="Planned start" value={formatDate(engagement.plannedStartDate)} />
                <DetailField
                  label="Planned completion"
                  value={formatDate(engagement.plannedCompletionDate)}
                />
                <DetailField label="Reporting due" value={formatDate(engagement.reportingDueDate)} />
              </dl>
              <div className="mt-4 border-t border-border pt-4">
                <p className="label-caps">Audit objective</p>
                <p className="mt-1 text-sm text-foreground">{engagement.objective || "—"}</p>
              </div>
              {engagement.remarks && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="label-caps">Remarks</p>
                  <p className="mt-1 text-sm text-foreground">{engagement.remarks}</p>
                </div>
              )}
              {engagement.closureRemarks && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="label-caps">Closure remarks</p>
                  <p className="mt-1 text-sm text-foreground">{engagement.closureRemarks}</p>
                </div>
              )}
            </DetailCard>

            <div className="space-y-4">
              <DetailCard title="Team">
                <dl className="grid gap-4">
                  <DetailField label="Engagement manager" value={engagement.engagementManager} />
                  <DetailField label="Process owner" value={engagement.processOwner} />
                  <DetailField label="Audit coordinator" value={engagement.auditCoordinator || "—"} />
                  <DetailField
                    label="Audit team"
                    value={
                      engagement.auditTeam.length > 0 ? (
                        <ul className="flex flex-wrap gap-1.5">
                          {engagement.auditTeam.map((member) => (
                            <li
                              key={member}
                              className="rounded-sm border border-border bg-surface px-2 py-0.5 text-xs"
                            >
                              {member}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        "—"
                      )
                    }
                  />
                </dl>
              </DetailCard>
              <DetailCard title="Record metadata">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField
                    label="Created"
                    value={`${formatDateTime(engagement.createdAt)} · ${engagement.createdBy}`}
                  />
                  <DetailField
                    label="Last updated"
                    value={`${formatDateTime(engagement.updatedAt)} · ${engagement.updatedBy}`}
                  />
                </dl>
              </DetailCard>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="scope" className="mt-4 space-y-6">
          <ScopeProgrammePage engagementId={engagementId} />
          <ProceduresTable
            engagementId={engagementId}
            title="All test procedures for this engagement"
            scopeOptions={scopeOptions}
          />
        </TabsContent>
        <TabsContent value="requirements" className="mt-4 space-y-6">
          <DataRequirementsPage engagementId={engagementId} />
          <EvidenceReviewPage engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="clarifications" className="mt-4">
          <ClarificationsPage engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="observations" className="mt-4 space-y-6">
          <ObservationsPage engagementId={engagementId} />
          <ManagementResponsesPage engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="reporting" className="mt-4">
          <FinalReportingPage engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="closure" className="mt-4 space-y-6">
          <ManagementActionsPage engagementId={engagementId} />
          <ClosureTrackingPage engagementId={engagementId} />
        </TabsContent>
        <TabsContent value="activity" className="mt-4">
          <ActivityTable
            entries={activityQuery.data ?? []}
            isLoading={activityQuery.isLoading}
            emptyMessage="No engagement activity has been recorded yet."
          />
        </TabsContent>
      </Tabs>

      <EngagementFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        engagement={engagement}
        clients={clientsQuery.data?.items ?? []}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />
    </div>
  );
}
