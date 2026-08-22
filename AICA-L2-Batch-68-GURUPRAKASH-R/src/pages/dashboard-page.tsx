import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  FileSignature,
  FilePlus2,
  HelpCircle,
  ListChecks,
  MessageSquareReply,
  ClipboardCheck,
  FolderPlus,
} from "lucide-react";
import { ActivityTimeline } from "@/components/common/activity-timeline";
import { DetailCard } from "@/components/common/detail-card";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading-state";
import { MetricCard } from "@/components/common/metric-card";
import { PageHeader } from "@/components/common/page-header";
import { RiskBadge } from "@/components/common/risk-badge";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRole } from "@/context/role-context";
import { formatDate, percentage } from "@/lib/format";
import { services } from "@/services";

const QUICK_ACTIONS = [
  { label: "Add client", to: "/clients", icon: Building2 },
  { label: "Create engagement", to: "/engagements", icon: FileSignature },
  { label: "Add data requirement", to: "/data-requirements", icon: FolderPlus },
  { label: "Raise clarification", to: "/clarifications", icon: HelpCircle },
  { label: "Create observation", to: "/observations", icon: FilePlus2 },
  { label: "Record management response", to: "/management-responses", icon: MessageSquareReply },
  { label: "Add management action", to: "/management-actions", icon: ListChecks },
  { label: "Record closure update", to: "/closure-tracking", icon: ClipboardCheck },
];

export function DashboardPage() {
  const { role } = useRole();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard", "snapshot"],
    queryFn: () => services.dashboard.getSnapshot(),
  });

  const totalRisk = data?.riskDistribution.reduce((sum, row) => sum + row.count, 0) ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit dashboard"
        description="Portfolio position across all live internal audit engagements. Figures shown are placeholders for Stage 1."
        breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Dashboard" }]}
        meta={
          <span className="text-xs text-muted-foreground">
            Interface view: <span className="font-medium text-foreground">{role}</span>
          </span>
        }
      />

      <section aria-label="Quick actions" className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action) => (
          <Button key={action.label} asChild variant="outline" size="sm">
            <Link to={action.to}>
              <action.icon className="size-3.5" aria-hidden />
              {action.label}
            </Link>
          </Button>
        ))}
      </section>

      {isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : isLoading || !data ? (
        <LoadingState label="Loading dashboard…" rows={6} />
      ) : (
        <>
          <section
            aria-label="Summary metrics"
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"
          >
            {data.metrics.map((metric) => (
              <MetricCard key={metric.key} metric={metric} />
            ))}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <DetailCard
              title="Engagement-stage summary"
              description="Live engagements by lifecycle stage"
            >
              <ul className="space-y-2.5">
                {data.stageSummary.map((row) => (
                  <li key={row.stage} className="flex items-center gap-3">
                    <span className="w-32 shrink-0 text-sm text-foreground">{row.stage}</span>
                    <Progress
                      value={percentage(row.engagements, 12)}
                      className="h-2 flex-1"
                      aria-label={`${row.stage} engagements`}
                    />
                    <span className="w-6 text-right text-sm tabular-nums text-muted-foreground">
                      {row.engagements}
                    </span>
                  </li>
                ))}
              </ul>
            </DetailCard>

            <DetailCard title="Risk-rating distribution" description="Observations raised to date">
              <ul className="space-y-3">
                {data.riskDistribution.map((row) => (
                  <li key={row.rating} className="flex items-center gap-3">
                    <RiskBadge rating={row.rating} className="w-28 justify-center" />
                    <Progress
                      value={percentage(row.count, totalRisk)}
                      className="h-2 flex-1"
                      aria-label={`${row.rating} risk observations`}
                    />
                    <span className="w-16 text-right text-sm tabular-nums text-muted-foreground">
                      {row.count} ({percentage(row.count, totalRisk)}%)
                    </span>
                  </li>
                ))}
              </ul>
            </DetailCard>
          </div>

          <DetailCard
            title="Pending items by department"
            description="Open requests awaiting auditee action"
            bodyClassName="p-0"
          >
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-surface hover:bg-surface">
                    <TableHead className="label-caps h-9">Department</TableHead>
                    <TableHead className="label-caps h-9 text-right">Data requirements</TableHead>
                    <TableHead className="label-caps h-9 text-right">Clarifications</TableHead>
                    <TableHead className="label-caps h-9 text-right">Responses</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.departmentPending.map((row) => (
                    <TableRow key={row.department}>
                      <TableCell className="font-medium">{row.department}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {row.dataRequirements}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{row.clarifications}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.responses}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </DetailCard>

          <DetailCard
            title="Upcoming due dates"
            description="Next items falling due across all engagements"
            bodyClassName="p-0"
          >
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-surface hover:bg-surface">
                    <TableHead className="label-caps h-9">Reference</TableHead>
                    <TableHead className="label-caps h-9">Particulars</TableHead>
                    <TableHead className="label-caps h-9">Owner</TableHead>
                    <TableHead className="label-caps h-9">Due on</TableHead>
                    <TableHead className="label-caps h-9">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.upcomingDueDates.map((row) => (
                    <TableRow key={row.reference}>
                      <TableCell className="font-mono text-xs">{row.reference}</TableCell>
                      <TableCell>{row.title}</TableCell>
                      <TableCell className="text-muted-foreground">{row.owner}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatDate(row.dueOn)}</TableCell>
                      <TableCell>
                        <StatusBadge status={row.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </DetailCard>

          <div className="grid gap-4 lg:grid-cols-2">
            <DetailCard
              title="Audit execution completion"
              description="Fieldwork progress across live engagements"
            >
              <CompletionList items={data.auditExecution} />
            </DetailCard>
            <DetailCard
              title="Management action closure completion"
              description="Remediation progress and verification"
            >
              <CompletionList items={data.actionClosure} />
            </DetailCard>
          </div>

          <DetailCard title="Recent activity" description="Latest changes recorded in the system">
            <ActivityTimeline entries={data.recentActivity} />
          </DetailCard>
        </>
      )}
    </div>
  );
}

function CompletionList({
  items,
}: {
  items: { label: string; completed: number; total: number }[];
}) {
  return (
    <ul className="space-y-4">
      {items.map((item) => (
        <li key={item.label}>
          <div className="mb-1.5 flex items-center justify-between text-sm">
            <span className="text-foreground">{item.label}</span>
            <span className="tabular-nums text-muted-foreground">
              {item.completed}/{item.total} · {percentage(item.completed, item.total)}%
            </span>
          </div>
          <Progress value={percentage(item.completed, item.total)} className="h-2" />
        </li>
      ))}
    </ul>
  );
}
