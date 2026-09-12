"use client"

import { useState, useCallback } from "react"
import {
  FileSpreadsheet,
  FileText,
  FileBarChart,
  Download,
  Loader2,
  Filter,
  X,
  AlertTriangle,
  Clock,
  UserCheck,
  Timer,
  Users,
  Globe,
  Building,
  ScrollText,
  XCircle,
  BarChart3,
  Layers,
  Activity,
  ShieldCheck,
  Calendar,
  Banknote,
  BadgeCheck,
} from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/components/ui/toast"

interface ReportType {
  id: string
  name: string
  description: string
  icon: React.ElementType
  color: string
  category: "status" | "financial" | "performance" | "distribution" | "summary"
}

interface ReportCategory {
  id: "all" | "status" | "financial" | "performance" | "distribution" | "summary"
  label: string
  icon: React.ElementType
  count?: number
}

const REPORT_CATEGORIES: ReportCategory[] = [
  { id: "all", label: "All Reports", icon: Layers },
  { id: "status", label: "Status & Operational", icon: ShieldCheck },
  { id: "financial", label: "Treasury & Audit", icon: Banknote },
  { id: "performance", label: "Team & SLA (TAT)", icon: Activity },
  { id: "distribution", label: "Jurisdiction & Entity", icon: Globe },
  { id: "summary", label: "Executive Summaries", icon: Calendar },
]

const REPORT_TYPES: ReportType[] = [
  {
    id: "compliance-register",
    name: "Compliance Register",
    description: "Complete list of all compliance schedules with full details",
    icon: FileSpreadsheet,
    color: "blue",
    category: "status",
  },
  {
    id: "pending-compliance",
    name: "Pending Compliance",
    description: "All compliance items that are still pending action",
    icon: Clock,
    color: "yellow",
    category: "status",
  },
  {
    id: "overdue",
    name: "Overdue Report",
    description: "Compliance items past their due date",
    icon: AlertTriangle,
    color: "red",
    category: "status",
  },
  {
    id: "rejected-compliance",
    name: "Rejected Compliance",
    description: "Compliance items that have been rejected in the approval flow",
    icon: XCircle,
    color: "red",
    category: "status",
  },
  {
    id: "compliance-source",
    name: "Compliance Source Breakdown",
    description: "Compliance counts by source and status (Template / Manual / Import)",
    icon: FileSpreadsheet,
    color: "emerald",
    category: "status",
  },
  {
    id: "treasury-forecast",
    name: "Treasury Outflow Forecast",
    description: "Projected tax cash outflows and payment liabilities by entity and due date",
    icon: Banknote,
    color: "teal",
    category: "financial",
  },
  {
    id: "statutory-audit-pack",
    name: "Statutory Filing & Challan Pack",
    description: "Official tax filing register with challan numbers, payment bank references, and ack IDs",
    icon: BadgeCheck,
    color: "blue",
    category: "financial",
  },
  {
    id: "employee-productivity",
    name: "Employee Productivity",
    description: "Compliance completion metrics by employee",
    icon: Users,
    color: "purple",
    category: "performance",
  },
  {
    id: "approval-tat",
    name: "Approval TAT",
    description: "Approval turnaround time and sign-off analysis",
    icon: UserCheck,
    color: "indigo",
    category: "performance",
  },
  {
    id: "preparation-tat",
    name: "Preparation TAT",
    description: "Preparation turnaround time analysis",
    icon: Timer,
    color: "orange",
    category: "performance",
  },
  {
    id: "audit-trail",
    name: "Audit Trail",
    description: "Complete audit log of all system actions and transitions",
    icon: ScrollText,
    color: "slate",
    category: "performance",
  },
  {
    id: "country-compliance",
    name: "Country Compliance",
    description: "Compliance distribution and status across countries",
    icon: Globe,
    color: "emerald",
    category: "distribution",
  },
  {
    id: "entity-compliance",
    name: "Entity Compliance",
    description: "Compliance distribution and status by legal entity",
    icon: Building,
    color: "cyan",
    category: "distribution",
  },
  {
    id: "monthly-summary",
    name: "Monthly Summary",
    description: "Monthly compliance activity and completion summary",
    icon: BarChart3,
    color: "blue",
    category: "summary",
  },
  {
    id: "quarterly-summary",
    name: "Quarterly Summary",
    description: "Quarterly compliance activity and completion summary",
    icon: BarChart3,
    color: "teal",
    category: "summary",
  },
  {
    id: "yearly-summary",
    name: "Yearly Summary",
    description: "Annual compliance activity and completion summary",
    icon: BarChart3,
    color: "green",
    category: "summary",
  },
]

const FORMAT_OPTIONS = [
  { value: "excel", label: "Excel (.xlsx)", icon: FileSpreadsheet },
  { value: "csv", label: "CSV (.csv)", icon: FileText },
  { value: "pdf", label: "PDF (.pdf)", icon: FileBarChart },
] as const

const COLOR_MAP: Record<string, string> = {
  blue: "#3b82f6",
  yellow: "#eab308",
  red: "#ef4444",
  purple: "#8b5cf6",
  indigo: "#6366f1",
  orange: "#f97316",
  emerald: "#10b981",
  cyan: "#06b6d4",
  slate: "#64748b",
  teal: "#14b8a6",
  green: "#22c55e",
}

export default function ReportsPage() {
  const [generating, setGenerating] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [format, setFormat] = useState<string>("excel")
  const [filters, setFilters] = useState({
    dateFrom: "",
    dateTo: "",
    countryId: "",
    entityId: "",
    status: "",
    priority: "",
    complianceTypeId: "",
  })

  const handleFilterChange = useCallback(
    (key: string, value: string) => {
      setFilters((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  const clearFilters = useCallback(() => {
    setFilters({
      dateFrom: "",
      dateTo: "",
      countryId: "",
      entityId: "",
      status: "",
      priority: "",
      complianceTypeId: "",
    })
  }, [])

  const hasActiveFilters = Object.values(filters).some((v) => v !== "")

  const generateReport = useCallback(
    async (reportType: ReportType) => {
      try {
        setGenerating(reportType.id)
        const res = await fetch("/api/reports", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: reportType.id,
            format,
            filters,
          }),
        })

        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.error || "Failed to generate report")
        }

        const blob = await res.blob()
        const disposition = res.headers.get("Content-Disposition") || ""
        const match = disposition.match(/filename="(.+)"/)
        const fileName = match?.[1] || `${reportType.id}.${format}`

        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)

        toast({
          title: "Report generated",
          description: `${reportType.name} has been downloaded as ${format.toUpperCase()}`,
        })
      } catch (err) {
        toast({
          title: "Generation failed",
          description: err instanceof Error ? err.message : "Something went wrong",
          variant: "destructive",
        })
      } finally {
        setGenerating(null)
      }
    },
    [format, filters]
  )

  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [reportSearch, setReportSearch] = useState("")

  const filteredReports = REPORT_TYPES.filter((r) => {
    const matchesCategory = selectedCategory === "all" || r.category === selectedCategory
    const matchesSearch =
      !reportSearch ||
      r.name.toLowerCase().includes(reportSearch.toLowerCase()) ||
      r.description.toLowerCase().includes(reportSearch.toLowerCase())
    return matchesCategory && matchesSearch
  })

  return (
    <DashboardLayout title="Reports">
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger className="w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORMAT_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <span className="flex items-center gap-2">
                      <opt.icon className="h-4 w-4" />
                      {opt.label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={showFilters ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-1.5" />
              Data Filters
              {hasActiveFilters && (
                <span className="ml-1.5 h-2 w-2 rounded-full bg-current" />
              )}
            </Button>
          </div>

          <div className="w-full sm:w-72">
            <Input
              placeholder="Search reports..."
              value={reportSearch}
              onChange={(e) => setReportSearch(e.target.value)}
              className="h-9"
            />
          </div>
        </div>

        {showFilters && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-[var(--color-foreground)]">
                  Data Scope Filters
                </h3>
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    <X className="h-3.5 w-3.5 mr-1" />
                    Clear
                  </Button>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <label className="text-xs text-[var(--color-muted-foreground)] mb-1 block">
                    Date From
                  </label>
                  <Input
                    type="date"
                    value={filters.dateFrom}
                    onChange={(e) => handleFilterChange("dateFrom", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted-foreground)] mb-1 block">
                    Date To
                  </label>
                  <Input
                    type="date"
                    value={filters.dateTo}
                    onChange={(e) => handleFilterChange("dateTo", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted-foreground)] mb-1 block">
                    Status
                  </label>
                  <Select
                    value={filters.status}
                    onValueChange={(v) => handleFilterChange("status", v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="DRAFT">Draft</SelectItem>
                      <SelectItem value="PENDING_PREPARATION">
                        Pending Preparation
                      </SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="PENDING_APPROVAL">
                        Pending Approval
                      </SelectItem>
                      <SelectItem value="APPROVED">Approved</SelectItem>
                      <SelectItem value="REJECTED">Rejected</SelectItem>
                      <SelectItem value="FILED">Filed</SelectItem>
                      <SelectItem value="PAID">Paid</SelectItem>
                      <SelectItem value="CLOSED">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted-foreground)] mb-1 block">
                    Priority
                  </label>
                  <Select
                    value={filters.priority}
                    onValueChange={(v) => handleFilterChange("priority", v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="NORMAL">Normal</SelectItem>
                      <SelectItem value="HIGH">High</SelectItem>
                      <SelectItem value="CRITICAL">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="w-full space-y-4">
          <TabsList className="h-auto p-1 bg-[var(--color-muted)] flex flex-wrap gap-1">
            {REPORT_CATEGORIES.map((cat) => {
              const count = cat.id === "all"
                ? REPORT_TYPES.length
                : REPORT_TYPES.filter((r) => r.category === cat.id).length
              const CatIcon = cat.icon
              return (
                <TabsTrigger
                  key={cat.id}
                  value={cat.id}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-medium"
                >
                  <CatIcon className="h-4 w-4" />
                  {cat.label}
                  <span className="text-[11px] px-1.5 py-0.2 rounded-full bg-[var(--color-background)] text-[var(--color-muted-foreground)] font-mono">
                    {count}
                  </span>
                </TabsTrigger>
              )
            })}
          </TabsList>

          <TabsContent value={selectedCategory} className="mt-0">
            {filteredReports.length === 0 ? (
              <Card className="p-8 text-center text-[var(--color-muted-foreground)]">
                No reports found matching your search.
              </Card>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredReports.map((report) => {
                  const Icon = report.icon
                  const borderColor = COLOR_MAP[report.color] || COLOR_MAP.blue
                  const isGenerating = generating === report.id
                  return (
                    <Card
                      key={report.id}
                      className="flex flex-col"
                      style={{ borderTop: `3px solid ${borderColor}` }}
                    >
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between">
                          <div
                            className="h-10 w-10 rounded-lg flex items-center justify-center"
                            style={{ backgroundColor: `${borderColor}15` }}
                          >
                            <Icon className="h-5 w-5" style={{ color: borderColor }} />
                          </div>
                        </div>
                        <CardTitle className="text-sm mt-2">{report.name}</CardTitle>
                        <CardDescription className="text-xs leading-relaxed">
                          {report.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="mt-auto pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full"
                          onClick={() => generateReport(report)}
                          disabled={isGenerating}
                        >
                          {isGenerating ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Download className="h-4 w-4 mr-1.5" />
                              Generate
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}
