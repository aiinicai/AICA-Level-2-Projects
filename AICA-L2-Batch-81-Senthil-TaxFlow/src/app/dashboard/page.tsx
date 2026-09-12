"use client"

import { useState, useEffect, useMemo, useCallback } from "react"
import { useAuth } from "@/components/layout/providers"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts"
import {
  Briefcase,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Calendar,
  CalendarDays,
  Timer,
  FileCheck,
  XCircle,
  TrendingUp,
  Users,
  Globe,
  Building,
  Receipt,
  UserCheck,
  Loader2,
  RefreshCw,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/ui/toast"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { formatDate, daysUntil } from "@/lib/utils"

const COLORS = {
  blue: "#3b82f6",
  green: "#22c55e",
  yellow: "#eab308",
  red: "#ef4444",
  purple: "#8b5cf6",
  orange: "#f97316",
  indigo: "#6366f1",
  emerald: "#10b981",
  pink: "#ec4899",
  cyan: "#06b6d4",
} as const

const CHART_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#eab308",
  "#ef4444",
  "#8b5cf6",
  "#f97316",
  "#6366f1",
  "#10b981",
  "#ec4899",
  "#06b6d4",
]

const COLOR_MAP: Record<string, string> = {
  blue: "#3b82f6",
  green: "#22c55e",
  yellow: "#eab308",
  red: "#ef4444",
  purple: "#8b5cf6",
  orange: "#f97316",
  indigo: "#6366f1",
  emerald: "#10b981",
  pink: "#ec4899",
  cyan: "#06b6d4",
}

const ICON_MAP: Record<string, React.ElementType> = {
  Briefcase,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Calendar,
  CalendarDays,
  Timer,
  FileCheck,
  XCircle,
  TrendingUp,
  Users,
  Globe,
  Building,
  Receipt,
  UserCheck,
  Loader2,
  RefreshCw,
}

const MONTHS_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

interface KPICard {
  title: string
  value: number
  unit?: string
  icon: string
  color: string
}

interface MonthlyProgress {
  month: string
  completed: number
  pending: number
}

interface UpcomingDueDate {
  id: string
  complianceId: string
  title?: string
  dueDate: string
  entity?: { entityName: string }
  priority?: string
  status?: string
}

interface RecentActivity {
  id: string
  action: string
  complianceId?: string
  compliance?: { id: string; complianceId: string }
  createdAt: string
  user?: { id: string; name: string }
}

interface ApprovalTrend {
  date: string
  approved: number
  rejected: number
}

interface PendingByCountry {
  name: string
  value: number
  count?: number
  country?: { id: string; name: string; code: string }
}

interface PendingByEntity {
  name: string
  value: number
  count?: number
  entity?: { id: string; entityName: string; entityNumber: string }
}

interface PreparerCharts {
  monthlyProgress: MonthlyProgress[]
  pendingVsCompleted: { pending: number; completed: number }
  upcomingDueDates: UpcomingDueDate[]
  recentActivity: RecentActivity[]
}

interface ApproverCharts {
  approvalTrend: ApprovalTrend[]
  pendingByCountry: PendingByCountry[]
  pendingByEntity: PendingByEntity[]
  recentActivities: RecentActivity[]
}

interface ComplianceStatus {
  status: string
  count: number
}

interface CountryWise {
  count: number
  country?: { id: string; name: string; code: string }
}

interface EntityWise {
  count: number
  entity?: { id: string; entityName: string; entityNumber: string }
}

interface TaxTypeDist {
  count: number
  complianceType?: { id: string; name: string; taxType: string }
}

interface MonthlyTrend {
  month: string
  total: number
  completed: number
}

interface EmployeeWorkload {
  assigned: number
  pending: number
  completed: number
  overdue: number
  employee: { id: string; name: string | null; email: string; role: string }
}

interface OverdueItem {
  id: string
  complianceId: string
  dueDate: string
  countryId?: string
  entityId?: string
  daysOverdue?: number
}

interface BottleneckApproval {
  id: string
  complianceId: string
  submittedAt: string | null
  entity: { entityName: string }
  approvals: { approver: { id: string; name: string; email: string } }[]
}

interface DelayedCountry {
  overdueCount: number
  country?: { id: string; name: string; code: string }
}

interface DelayedEntity {
  overdueCount: number
  entity?: { id: string; entityName: string; entityNumber: string }
}

interface ManagerCharts {
  complianceStatus: ComplianceStatus[]
  countryWiseCompliance: CountryWise[]
  entityWiseCompliance: EntityWise[]
  taxTypeDistribution: TaxTypeDist[]
  monthlyComplianceTrend: MonthlyTrend[]
  employeeWorkload: EmployeeWorkload[]
  overdueHeatMap: OverdueItem[]
  approvalBottlenecks: BottleneckApproval[]
  topDelayedCountries: DelayedCountry[]
  topDelayedEntities: DelayedEntity[]
  complianceSource: { name: string; value: number }[]
}

interface ManagerFilters {
  countries: { id: string; name: string; code: string }[]
  entities: { id: string; entityName: string; entityNumber: string }[]
  taxTypes: { id: string; name: string; taxType: string }[]
  complianceTypes: { id: string; name: string }[]
  employees: { id: string; name: string | null; email: string; role: string }[]
}

interface PreparerData {
  role: "PREPARER"
  cards: KPICard[]
  charts: PreparerCharts
}

interface ApproverData {
  role: "APPROVER" | "REVIEWER"
  cards: KPICard[]
  charts: ApproverCharts
}

interface ManagerData {
  role: "MANAGER" | "ADMINISTRATOR"
  cards: KPICard[]
  charts: ManagerCharts
  filters: ManagerFilters
}

type DashboardData = PreparerData | ApproverData | ManagerData

interface ManagerFilterState {
  country: string
  entity: string
  taxType: string
  complianceType: string
  employee: string
  period: string
}

interface KpiApiCard {
  title?: string
  value?: number
  unit?: string
  icon?: string
  color?: string
}

interface KpiApiCharts {
  monthlyProgress?: MonthlyProgress[]
  pendingVsCompleted?: { pending: number; completed: number }
  upcomingDueDates?: UpcomingDueDate[]
  recentActivity?: RecentActivity[]
  approvalTrend?: ApprovalTrend[]
  pendingByCountry?: PendingByCountry[]
  pendingByEntity?: PendingByEntity[]
  recentActivities?: RecentActivity[]
  complianceStatus?: ComplianceStatus[]
  countryWiseCompliance?: CountryWise[]
  entityWiseCompliance?: EntityWise[]
  taxTypeDistribution?: TaxTypeDist[]
  monthlyComplianceTrend?: MonthlyTrend[]
  employeeWorkload?: EmployeeWorkload[]
  overdueHeatMap?: OverdueItem[]
  approvalBottlenecks?: BottleneckApproval[]
  topDelayedCountries?: DelayedCountry[]
  topDelayedEntities?: DelayedEntity[]
  complianceSource?: { name: string; value: number }[]
  filters?: ManagerFilters
}

interface KpiApiData extends KpiApiCharts {
  role?: string
  cards?: KpiApiCard[]
  charts?: KpiApiCharts
  assignedCompliances?: number
  completed?: number
  pending?: number
  overdue?: number
  dueToday?: number
  dueThisWeek?: number
  avgTurnaroundTime?: number
  pendingApproval?: number
  rejected?: number
  approvedToday?: number
  avgApprovalTime?: number
  totalCompliances?: number
  filedLate?: number
  paidLate?: number
  awaitingApproval?: number
  avgProcessingTime?: number
  countries?: ManagerFilters["countries"]
  entities?: ManagerFilters["entities"]
  taxTypes?: ManagerFilters["taxTypes"]
  complianceTypes?: ManagerFilters["complianceTypes"]
  employees?: ManagerFilters["employees"]
}

interface KpiApiResponse {
  data?: KpiApiData
}

function getDaysUntil(dueDate: string): number {
  return daysUntil(new Date(dueDate))
}

function getDueDateBadge(days: number) {
  if (days < 0) return { label: `${Math.abs(days)}d overdue`, variant: "destructive" as const }
  if (days === 0) return { label: "Due today", variant: "default" as const }
  if (days <= 3) return { label: `${days}d left`, variant: "secondary" as const }
  return { label: `${days}d left`, variant: "outline" as const }
}

function parseMonthKey(key: string): string {
  const parts = key.split("-")
  if (parts.length === 2) {
    const monthIndex = parseInt(parts[1], 10) - 1
    return MONTHS_SHORT[monthIndex] || key
  }
  return key
}

function getGreeting(role: string): string {
  const hour = new Date().getHours()
  const timeGreeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"
  const roleGreeting: Record<string, string> = {
    ADMIN: "administrator",
    ADMINISTRATOR: "administrator",
    MANAGER: "manager",
    PREPARER: "preparer",
    APPROVER: "approver",
    REVIEWER: "reviewer",
    VIEWER: "user",
  }
  return `${timeGreeting}, ${roleGreeting[role] || "user"}`
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { color?: string; name?: string | number; value?: string | number }[]
  label?: string | number
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 shadow-sm text-sm">
      <p className="font-medium text-[var(--color-foreground)] mb-1">{label}</p>
      {payload.map((entry, i: number) => (
        <p key={i} style={{ color: entry.color }} className="text-xs">
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  )
}

function CardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-1" />
        <Skeleton className="h-3 w-32" />
      </CardContent>
    </Card>
  )
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </CardContent>
    </Card>
  )
}

function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 7 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <ChartSkeleton key={i} />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <ChartSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}

function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <AlertTriangle className="h-16 w-16 text-red-400 mb-4" />
      <h3 className="text-lg font-semibold text-[var(--color-foreground)] mb-1">
        Failed to load dashboard
      </h3>
      <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
        Something went wrong while fetching your dashboard data.
      </p>
      <Button onClick={onRetry}>
        <RefreshCw className="h-4 w-4 mr-2" />
        Retry
      </Button>
    </div>
  )
}

function StatCard({ card }: { card: KPICard }) {
  const Icon = ICON_MAP[card.icon] || FileCheck
  const borderColor = COLOR_MAP[card.color] || COLORS.blue
  return (
    <Card
      className="overflow-hidden"
      style={{ borderLeft: `4px solid ${borderColor}` }}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-[var(--color-muted-foreground)]">
          {card.title}
        </CardTitle>
        <div
          className="h-8 w-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${borderColor}20` }}
        >
          <Icon className="h-4 w-4" style={{ color: borderColor }} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-bold text-[var(--color-foreground)]">
            {card.value.toLocaleString()}
          </span>
          {card.unit && (
            <span className="text-sm text-[var(--color-muted-foreground)]">
              {card.unit}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function PreparerDashboard({ data }: { data: PreparerData }) {
  const { cards, charts } = data

  const pendingVsCompletedData = useMemo(
    () => [
      { name: "Completed", value: charts.pendingVsCompleted.completed },
      { name: "Pending", value: charts.pendingVsCompleted.pending },
    ],
    [charts.pendingVsCompleted]
  )

  const monthlyProgressData = useMemo(
    () =>
      charts.monthlyProgress.map((m) => ({
        ...m,
        month: parseMonthKey(m.month),
      })),
    [charts.monthlyProgress]
  )

  return (
    <div className="space-y-6">
      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {cards.map((card, i) => (
          <StatCard key={i} card={card} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Monthly Progress</CardTitle>
            <CardDescription>Completed vs pending tasks over the last 6 months</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyProgressData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <YAxis tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="completed" name="Completed" fill={COLORS.green} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="pending" name="Pending" fill={COLORS.yellow} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pending vs Completed</CardTitle>
            <CardDescription>Overall completion status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pendingVsCompletedData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: { name?: string | number; percent?: number }) =>
                      `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine
                  >
                    {pendingVsCompletedData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.name === "Completed" ? COLORS.green : COLORS.yellow}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upcoming Due Dates</CardTitle>
            <CardDescription>Your next upcoming deadlines</CardDescription>
          </CardHeader>
          <CardContent>
            {charts.upcomingDueDates.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Calendar className="h-12 w-12 text-[var(--color-muted-foreground)] mb-2 opacity-40" />
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  No upcoming due dates
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {charts.upcomingDueDates.map((item) => {
                  const days = getDaysUntil(item.dueDate)
                  const badge = getDueDateBadge(days)
                  return (
                    <div
                      key={item.id}
                      className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[var(--color-accent)] transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--color-foreground)] truncate">
                          {item.complianceId}
                        </p>
                        <p className="text-xs text-[var(--color-muted-foreground)] truncate">
                          {item.entity?.entityName || "—"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        <span className="text-xs text-[var(--color-muted-foreground)]">
                          {formatDate(item.dueDate)}
                        </span>
                        <Badge variant={badge.variant}>{badge.label}</Badge>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
            <CardDescription>Latest actions on your tasks</CardDescription>
          </CardHeader>
          <CardContent>
            {charts.recentActivity.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <FileCheck className="h-12 w-12 text-[var(--color-muted-foreground)] mb-2 opacity-40" />
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  No recent activity
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {charts.recentActivity.map((activity) => {
                  const complianceId =
                    activity.complianceId || activity.compliance?.complianceId || ""
                  return (
                    <div
                      key={activity.id}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-accent)] transition-colors"
                    >
                      <div className="h-8 w-8 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                        <FileCheck className="h-4 w-4 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[var(--color-foreground)]">
                          <span className="font-medium">
                            {activity.user?.name || "System"}
                          </span>{" "}
                          {activity.action}{" "}
                          {complianceId && (
                            <span className="font-medium">{complianceId}</span>
                          )}
                        </p>
                        <p className="text-xs text-[var(--color-muted-foreground)]">
                          {formatDate(activity.createdAt)}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ApproverDashboard({ data }: { data: ApproverData }) {
  const { cards, charts } = data

  const approvalTrendData = useMemo(
    () =>
      charts.approvalTrend.map((a) => ({
        date: a.date?.slice(5) || a.date,
        approved: a.approved,
        rejected: a.rejected,
      })),
    [charts.approvalTrend]
  )

  return (
    <div className="space-y-6">
      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {cards.map((card, i) => (
          <StatCard key={i} card={card} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Approval Trend (Last 30 Days)</CardTitle>
            <CardDescription>Daily approved and rejected items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={approvalTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    stroke="var(--color-muted-foreground)"
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    allowDecimals={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="approved"
                    name="Approved"
                    stroke={COLORS.green}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="rejected"
                    name="Rejected"
                    stroke={COLORS.red}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pending by Country</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={charts.pendingByCountry.map((c) => ({
                      name: c.country?.name || c.name || "Unknown",
                      value: c.value || c.count || 0,
                    }))}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 12 }}
                      stroke="var(--color-muted-foreground)"
                      width={80}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" name="Pending" fill={COLORS.orange} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pending by Entity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={charts.pendingByEntity.map((e) => ({
                      name: e.entity?.entityName || e.name || "Unknown",
                      value: e.value || e.count || 0,
                    }))}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 12 }}
                      stroke="var(--color-muted-foreground)"
                      width={100}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" name="Pending" fill={COLORS.purple} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activities</CardTitle>
        </CardHeader>
        <CardContent>
          {charts.recentActivities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <FileCheck className="h-12 w-12 text-[var(--color-muted-foreground)] mb-2 opacity-40" />
              <p className="text-sm text-[var(--color-muted-foreground)]">
                No recent activity
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {charts.recentActivities.map((activity) => {
                const complianceId =
                  activity.complianceId || activity.compliance?.complianceId || ""
                return (
                  <div
                    key={activity.id}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[var(--color-accent)] transition-colors"
                  >
                    <div className="h-8 w-8 rounded-full bg-purple-50 flex items-center justify-center shrink-0">
                      <FileCheck className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--color-foreground)]">
                        <span className="font-medium">
                          {activity.user?.name || "System"}
                        </span>{" "}
                        {activity.action}{" "}
                        {complianceId && (
                          <span className="font-medium">{complianceId}</span>
                        )}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        {formatDate(activity.createdAt)}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ManagerFiltersBar({
  filters,
  filterState,
  onFilterChange,
}: {
  filters: ManagerFilters
  filterState: ManagerFilterState
  onFilterChange: (key: keyof ManagerFilterState, value: string) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={filterState.country}
        onValueChange={(v) => onFilterChange("country", v)}
      >
        <SelectTrigger className="w-[160px] h-9">
          <Globe className="h-4 w-4 mr-1" />
          <SelectValue placeholder="All Countries" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Countries</SelectItem>
          {filters.countries.map((c) => (
            <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterState.entity}
        onValueChange={(v) => onFilterChange("entity", v)}
      >
        <SelectTrigger className="w-[160px] h-9">
          <Building className="h-4 w-4 mr-1" />
          <SelectValue placeholder="All Entities" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Entities</SelectItem>
          {filters.entities.map((e) => (
            <SelectItem key={e.id} value={e.id}>{e.entityName}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterState.taxType}
        onValueChange={(v) => onFilterChange("taxType", v)}
      >
        <SelectTrigger className="w-[160px] h-9">
          <Receipt className="h-4 w-4 mr-1" />
          <SelectValue placeholder="All Tax Types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Tax Types</SelectItem>
          {filters.taxTypes.map((t) => (
            <SelectItem key={t.id} value={t.id}>{t.taxType || t.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterState.complianceType}
        onValueChange={(v) => onFilterChange("complianceType", v)}
      >
        <SelectTrigger className="w-[160px] h-9">
          <FileCheck className="h-4 w-4 mr-1" />
          <SelectValue placeholder="All Types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          {filters.complianceTypes.map((t) => (
            <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterState.employee}
        onValueChange={(v) => onFilterChange("employee", v)}
      >
        <SelectTrigger className="w-[160px] h-9">
          <Users className="h-4 w-4 mr-1" />
          <SelectValue placeholder="All Employees" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Employees</SelectItem>
          {filters.employees.map((emp) => (
            <SelectItem key={emp.id} value={emp.id}>{emp.name || emp.email}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterState.period}
        onValueChange={(v) => onFilterChange("period", v)}
      >
        <SelectTrigger className="w-[140px] h-9">
          <Calendar className="h-4 w-4 mr-1" />
          <SelectValue placeholder="This Year" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="year">This Year</SelectItem>
          <SelectItem value="quarter">This Quarter</SelectItem>
          <SelectItem value="month">This Month</SelectItem>
          <SelectItem value="all">All Time</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}

function ManagerDashboard({ data }: { data: ManagerData }) {
  const { cards, charts, filters } = data
  const [filterState, setFilterState] = useState<ManagerFilterState>({
    country: "all",
    entity: "all",
    taxType: "all",
    complianceType: "all",
    employee: "all",
    period: "year",
  })

  const handleFilterChange = useCallback(
    (key: keyof ManagerFilterState, value: string) => {
      setFilterState((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  const complianceStatusData = useMemo(
    () =>
      charts.complianceStatus.map((s) => ({
        name: s.status.replace(/_/g, " "),
        value: s.count,
      })),
    [charts.complianceStatus]
  )

  const complianceSourceData = useMemo(
    () =>
      charts.complianceSource.map((s) => ({
        name: s.name.replace(/_/g, " "),
        value: s.value,
      })),
    [charts.complianceSource]
  )

  const countryWiseData = useMemo(
    () =>
      charts.countryWiseCompliance.map((c) => ({
        name: c.country?.name || "Unknown",
        value: c.count,
      })),
    [charts.countryWiseCompliance]
  )

  const entityWiseData = useMemo(
    () =>
      charts.entityWiseCompliance.map((e) => ({
        name: e.entity?.entityName || "Unknown",
        value: e.count,
      })),
    [charts.entityWiseCompliance]
  )

  const taxTypeData = useMemo(
    () =>
      charts.taxTypeDistribution.map((t) => ({
        name: t.complianceType?.taxType || t.complianceType?.name || "Unknown",
        value: t.count,
      })),
    [charts.taxTypeDistribution]
  )

  const monthlyTrendData = useMemo(
    () =>
      charts.monthlyComplianceTrend.map((m) => ({
        month: parseMonthKey(m.month),
        total: m.total,
        completed: m.completed,
        pending: m.total - m.completed,
      })),
    [charts.monthlyComplianceTrend]
  )

  const workloadData = useMemo(
    () =>
      charts.employeeWorkload.map((w) => ({
        name: w.employee.name || w.employee.email,
        tasks: w.assigned,
        completed: w.completed,
      })),
    [charts.employeeWorkload]
  )

  const overdueHeatMapData = useMemo(() => {
    const grouped: Record<string, number> = {}
    charts.overdueHeatMap.forEach((item) => {
      const key = `${item.daysOverdue || Math.floor(Math.abs(getDaysUntil(item.dueDate)))} days`
      grouped[key] = (grouped[key] || 0) + 1
    })
    return Object.entries(grouped)
      .sort(([a], [b]) => parseInt(a) - parseInt(b))
      .slice(0, 10)
      .map(([name, value]) => ({ name, value }))
  }, [charts.overdueHeatMap])

  const bottleneckData = useMemo(() => {
    const grouped: Record<string, { pending: number; avgHours: number }> = {}
    charts.approvalBottlenecks.forEach((item) => {
      const approver = item.approvals?.[0]?.approver
      const name = approver?.name || "Unknown"
      if (!grouped[name]) {
        grouped[name] = { pending: 0, avgHours: 0 }
      }
      grouped[name].pending += 1
      if (item.submittedAt) {
        const hours =
          (new Date().getTime() - new Date(item.submittedAt).getTime()) / 3600000
        grouped[name].avgHours = Math.max(grouped[name].avgHours, hours)
      }
    })
    return Object.entries(grouped)
      .map(([name, data]) => ({ name, pending: data.pending, avgHours: Math.round(data.avgHours) }))
      .sort((a, b) => b.pending - a.pending)
      .slice(0, 10)
  }, [charts.approvalBottlenecks])

  const topDelayedCountriesData = useMemo(
    () =>
      charts.topDelayedCountries.map((c) => ({
        name: c.country?.name || "Unknown",
        value: c.overdueCount,
      })),
    [charts.topDelayedCountries]
  )

  const topDelayedEntitiesData = useMemo(
    () =>
      charts.topDelayedEntities.map((e) => ({
        name: e.entity?.entityName || "Unknown",
        value: e.overdueCount,
      })),
    [charts.topDelayedEntities]
  )

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-[var(--color-foreground)] mb-1">
          Executive Dashboard
        </h3>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Organization-wide compliance overview and analytics
        </p>
      </div>

      <ManagerFiltersBar
        filters={filters}
        filterState={filterState}
        onFilterChange={handleFilterChange}
      />

      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {cards.map((card, i) => (
          <StatCard key={i} card={card} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Compliance Status</CardTitle>
            <CardDescription>Distribution by status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={complianceStatusData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: { name?: string | number; percent?: number }) =>
                      (percent ?? 0) > 0.05 ? `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%` : ""
                    }
                    labelLine
                  >
                    {complianceStatusData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Country Wise Compliance</CardTitle>
            <CardDescription>Compliance items by country</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={countryWiseData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    width={80}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Compliances" fill={COLORS.blue} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Compliance Source</CardTitle>
            <CardDescription>Distribution by origin</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={complianceSourceData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: { name?: string | number; percent?: number }) =>
                      (percent ?? 0) > 0.05 ? `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%` : ""
                    }
                    labelLine
                  >
                    {complianceSourceData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Entity Wise Compliance</CardTitle>
            <CardDescription>Compliance items by entity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={entityWiseData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    width={100}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Compliances" fill={COLORS.emerald} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tax Type Distribution</CardTitle>
            <CardDescription>Compliance by tax type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={taxTypeData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }: { name?: string | number; percent?: number }) =>
                      (percent ?? 0) > 0.05 ? `${name || ""} ${((percent ?? 0) * 100).toFixed(0)}%` : ""
                    }
                    labelLine
                  >
                    {taxTypeData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Monthly Compliance Trend (12 Months)</CardTitle>
            <CardDescription>Total vs completed compliance items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                  />
                  <YAxis tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke={COLORS.blue}
                    fill={COLORS.blue}
                    fillOpacity={0.1}
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="completed"
                    name="Completed"
                    stroke={COLORS.green}
                    fill={COLORS.green}
                    fillOpacity={0.1}
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Employee Workload</CardTitle>
            <CardDescription>Tasks assigned vs completed per employee</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={workloadData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    stroke="var(--color-muted-foreground)"
                    interval={0}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="tasks" name="Total Tasks" fill={COLORS.blue} radius={[4, 4, 0, 0]} />
                  <Bar
                    dataKey="completed"
                    name="Completed"
                    fill={COLORS.green}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overdue Heat Map</CardTitle>
            <CardDescription>Overdue items by days past due</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overdueHeatMapData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    stroke="var(--color-muted-foreground)"
                    interval={0}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Count" fill={COLORS.red} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Approval Bottlenecks</CardTitle>
            <CardDescription>Pending approvals by approver</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bottleneckData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    width={100}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="pending" name="Pending" fill={COLORS.orange} radius={[0, 4, 4, 0]} />
                  <Bar dataKey="avgHours" name="Avg Hours" fill={COLORS.purple} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Delayed Countries</CardTitle>
            <CardDescription>Countries with most overdue items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topDelayedCountriesData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    width={80}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Overdue" fill={COLORS.red} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Delayed Entities</CardTitle>
            <CardDescription>Entities with most overdue items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topDelayedEntitiesData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-muted-foreground)" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="var(--color-muted-foreground)"
                    width={100}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Overdue" fill={COLORS.orange} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function transformApiResponse(apiData: KpiApiResponse, requestedRole?: string): DashboardData {
  const rawData = (apiData.data ?? apiData) as unknown as KpiApiData
  const role = rawData.role || requestedRole

  if (role === "PREPARER" || (!role && "assignedCompliances" in rawData && !("pendingApproval" in rawData) && !("totalCompliances" in rawData))) {
    return {
      role: "PREPARER",
      cards: [
        { title: "Assigned Tasks", value: rawData.assignedCompliances ?? rawData.cards?.[0]?.value ?? 0, icon: "Briefcase", color: "blue" },
        { title: "Completed", value: rawData.completed ?? 0, icon: "CheckCircle2", color: "green" },
        { title: "Pending", value: rawData.pending ?? 0, icon: "Clock", color: "yellow" },
        { title: "Overdue", value: rawData.overdue ?? 0, icon: "AlertTriangle", color: "red" },
        { title: "Due Today", value: rawData.dueToday ?? 0, icon: "Calendar", color: "orange" },
        { title: "Due This Week", value: rawData.dueThisWeek ?? 0, icon: "CalendarDays", color: "purple" },
        { title: "Avg Turnaround", value: rawData.avgTurnaroundTime ?? 0, unit: "days", icon: "Timer", color: "indigo" },
      ],
      charts: {
        monthlyProgress: rawData.monthlyProgress || rawData.charts?.monthlyProgress || [],
        pendingVsCompleted: rawData.pendingVsCompleted || rawData.charts?.pendingVsCompleted || { pending: 0, completed: 0 },
        upcomingDueDates: rawData.upcomingDueDates || rawData.charts?.upcomingDueDates || [],
        recentActivity: rawData.recentActivity || rawData.charts?.recentActivity || [],
      },
    }
  }

  if (role === "APPROVER" || role === "REVIEWER" || (!role && "pendingApproval" in rawData && !("totalCompliances" in rawData))) {
    return {
      role: "APPROVER",
      cards: [
        { title: role === "REVIEWER" ? "Pending Review" : "Pending Approval", value: rawData.pendingApproval ?? rawData.cards?.[0]?.value ?? 0, icon: "Clock", color: "yellow" },
        { title: "Rejected", value: rawData.rejected ?? 0, icon: "XCircle", color: "red" },
        { title: role === "REVIEWER" ? "Reviewed Today" : "Approved Today", value: rawData.approvedToday ?? 0, icon: "CheckCircle2", color: "green" },
        { title: role === "REVIEWER" ? "Avg Review Time" : "Avg Approval Time", value: rawData.avgApprovalTime ?? 0, unit: "hrs", icon: "Timer", color: "indigo" },
      ],
      charts: {
        approvalTrend: rawData.approvalTrend || rawData.charts?.approvalTrend || [],
        pendingByCountry: rawData.pendingByCountry || rawData.charts?.pendingByCountry || [],
        pendingByEntity: rawData.pendingByEntity || rawData.charts?.pendingByEntity || [],
        recentActivities: rawData.recentActivities || rawData.charts?.recentActivities || [],
      },
    }
  }

  return {
    role: "MANAGER",
    cards: [
      { title: "Total Compliances", value: rawData.totalCompliances ?? rawData.cards?.[0]?.value ?? 0, icon: "Briefcase", color: "blue" },
      { title: "Completed", value: rawData.completed ?? 0, icon: "CheckCircle2", color: "green" },
      { title: "Pending", value: rawData.pending ?? 0, icon: "Clock", color: "yellow" },
      { title: "Overdue", value: rawData.overdue ?? 0, icon: "AlertTriangle", color: "red" },
      { title: "Filed Late", value: rawData.filedLate ?? 0, icon: "AlertTriangle", color: "orange" },
      { title: "Paid Late", value: rawData.paidLate ?? 0, icon: "AlertTriangle", color: "red" },
      { title: "Rejected", value: rawData.rejected ?? 0, icon: "XCircle", color: "red" },
      { title: "Awaiting Approval", value: rawData.awaitingApproval ?? 0, icon: "UserCheck", color: "purple" },
      { title: "Avg Processing", value: rawData.avgProcessingTime ?? 0, unit: "days", icon: "Timer", color: "indigo" },
    ],
    charts: {
      complianceStatus: rawData.complianceStatus || rawData.charts?.complianceStatus || [],
      countryWiseCompliance: rawData.countryWiseCompliance || rawData.charts?.countryWiseCompliance || [],
      entityWiseCompliance: rawData.entityWiseCompliance || rawData.charts?.entityWiseCompliance || [],
      taxTypeDistribution: rawData.taxTypeDistribution || rawData.charts?.taxTypeDistribution || [],
      monthlyComplianceTrend: rawData.monthlyComplianceTrend || rawData.charts?.monthlyComplianceTrend || [],
      employeeWorkload: rawData.employeeWorkload || rawData.charts?.employeeWorkload || [],
      overdueHeatMap: rawData.overdueHeatMap || rawData.charts?.overdueHeatMap || [],
      approvalBottlenecks: rawData.approvalBottlenecks || rawData.charts?.approvalBottlenecks || [],
      topDelayedCountries: rawData.topDelayedCountries || rawData.charts?.topDelayedCountries || [],
      topDelayedEntities: rawData.topDelayedEntities || rawData.charts?.topDelayedEntities || [],
      complianceSource: rawData.complianceSource || rawData.charts?.complianceSource || [],
    },
    filters: rawData.filters || rawData.charts?.filters || {
      countries: rawData.countries || [],
      entities: rawData.entities || [],
      taxTypes: rawData.taxTypes || [],
      complianceTypes: rawData.complianceTypes || [],
      employees: rawData.employees || [],
    },
  }
}

function NoOrgsView() {
  const [creating, setCreating] = useState(false)
  const [orgName, setOrgName] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const { refresh } = useAuth()
  const { toast } = useToast()

  async function handleCreateOrg(e: React.FormEvent) {
    e.preventDefault()
    if (!orgName.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch("/api/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: orgName.trim() }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || "Failed to create organization")
      }
      await refresh()
      setCreating(false)
      setOrgName("")
      toast({ title: "Success", description: "Organization created! Select it to get started." })
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
      <Building className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
      <h3 className="text-xl font-semibold text-[var(--color-foreground)] mb-2">
        Welcome to TaxFlow
      </h3>
      <p className="text-sm text-[var(--color-muted-foreground)] mb-6">
        You are not part of any organization yet. Create your first organization to get started.
      </p>
      {creating ? (
        <form onSubmit={handleCreateOrg} className="w-full space-y-3">
          <Input
            placeholder="Organization name"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            required
            autoFocus
          />
          <div className="flex gap-2">
            <Button type="submit" disabled={submitting} className="flex-1">
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Organization
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Button onClick={() => setCreating(true)}>
          <Building className="h-4 w-4 mr-2" />
          Create Organization
        </Button>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { user: sessionUser, activeOrgId, activeRole } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)

  const fetchDashboard = useCallback(async (roleToFetch?: string) => {
    setLoading(true)
    setError(false)
    try {
      const role = roleToFetch || activeRole
      const query = new URLSearchParams()
      if (activeOrgId) query.set("orgId", activeOrgId)
      if (role) query.set("role", role)
      const res = await fetch(`/api/kpi/dashboard?${query.toString()}`, {
        cache: "no-store",
      })
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setDashboardData(transformApiResponse(json, role))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [activeOrgId, activeRole])

  useEffect(() => {
    if (activeOrgId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
      fetchDashboard(activeRole)
    } else {
      setLoading(false)
    }
  }, [fetchDashboard, activeOrgId, activeRole])

  const user = sessionUser
  const role = activeRole || user?.role || "VIEWER"
  const userName = user?.name || user?.username || "User"

  if (!user) return null

  if (!user.orgs || user.orgs.length === 0) {
    return (
      <DashboardLayout title="Dashboard">
        <NoOrgsView />
      </DashboardLayout>
    )
  }

  if (!activeOrgId) {
    return (
      <DashboardLayout title="Dashboard">
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Building className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
          <h3 className="text-xl font-semibold text-[var(--color-foreground)] mb-2">
            Select an Organization
          </h3>
          <p className="text-sm text-[var(--color-muted-foreground)] mb-6">
            Choose an organization from the sidebar to view its dashboard.
          </p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--color-foreground)]">
            {getGreeting(role)}, {userName}
          </h2>
          <p className="text-sm text-[var(--color-muted-foreground)] mt-1">
            Here&apos;s what&apos;s happening with your compliance tasks today.
          </p>
        </div>

        {!activeOrgId ? null : loading ? (
          <DashboardLoading />
        ) : error ? (
          <DashboardError onRetry={() => fetchDashboard(activeRole)} />
        ) : dashboardData?.role === "PREPARER" ? (
          <PreparerDashboard data={dashboardData as PreparerData} />
        ) : dashboardData?.role === "APPROVER" || dashboardData?.role === "REVIEWER" ? (
          <ApproverDashboard data={dashboardData as ApproverData} />
        ) : dashboardData?.role === "MANAGER" || dashboardData?.role === "ADMINISTRATOR" ? (
          <ManagerDashboard data={dashboardData as ManagerData} />
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <AlertTriangle className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
            <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-1">
              No dashboard data available
            </h3>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Unable to determine your role-specific dashboard view.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
