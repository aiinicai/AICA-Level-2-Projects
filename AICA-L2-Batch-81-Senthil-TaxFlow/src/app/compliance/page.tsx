"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import {
  Calendar,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  MoreHorizontal,
  Loader2,
  XCircle,
  FileText,
  FileType,
  ArrowUpDown,
  ClipboardPlus,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { toast } from "@/components/ui/toast"
import {
  formatDate,
  daysUntil,
  getStatusColor,
  getPriorityColor,
} from "@/lib/utils"
import { taxTypeLabel } from "@/lib/tax-types"

interface Country {
  id: string
  name: string
  code: string
}

interface Entity {
  id: string
  entityName: string
  entityNumber: string
}

interface ComplianceItem {
  id: string
  complianceId: string
  entity: Entity
  entities: { id: string; entityId: string; entity: Entity }[]
  country: Country
  taxType: string | null
  form: { id: string; formNumber: string; formName: string } | null
  taxPeriod: string
  frequency: string
  dueDate: string
  paymentDueDate: string | null
  requiresPayment: boolean
  priority: string
  status: string
  source?: string
  filedAt: string | null
  paidAt: string | null
  paymentAmount: number | null
  paymentCurrency: string | null
  filingType: string | null
  assignments: { id: string; preparer: { id: string; name: string } }[]
  createdAt: string
}

interface Pagination {
  page: number
  limit: number
  total: number
  totalPages: number
}

const PAGE_LIMIT = 15

const STATUS_OPTIONS = [
  { value: "DRAFT", label: "Draft" },
  { value: "PENDING_ADMIN_APPROVAL", label: "Pending Admin Approval" },
  { value: "PENDING_REVIEW", label: "Pending Review" },
  { value: "PENDING_PREPARATION", label: "Pending Preparation" },
  { value: "PREPARED", label: "Prepared" },
  { value: "PENDING_APPROVAL", label: "Pending Approval" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "FILED", label: "Filed" },
  { value: "PAID", label: "Paid" },
  { value: "CLOSED", label: "Closed" },
]

const PRIORITY_OPTIONS = [
  { value: "NORMAL", label: "Normal" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
]

function getSourceVariant(source: string | undefined): "default" | "secondary" | "outline" {
  switch (source) {
    case "TEMPLATE": return "secondary"
    case "IMPORT": return "default"
    default: return "outline"
  }
}

export default function CompliancePage() {
  const router = useRouter()
  const { user: sessionUser } = useAuth()
  const role = sessionUser?.role

  const [data, setData] = useState<ComplianceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: PAGE_LIMIT,
    total: 0,
    totalPages: 0,
  })

  const [status, setStatus] = useState("")
  const [priority, setPriority] = useState("")
  const [countryId, setCountryId] = useState("")
  const [entityId, setEntityId] = useState("")
  const [search, setSearch] = useState("")

  const [countries, setCountries] = useState<Country[]>([])
  const [entities, setEntities] = useState<Entity[]>([])

  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    Promise.all([
      fetch("/api/countries").then((r) => r.json()),
      fetch("/api/entities").then((r) => r.json()),
    ]).then(([c, e]) => {
      setCountries(Array.isArray(c) ? c : c.countries || c.data || [])
      setEntities(Array.isArray(e) ? e : e.entities || e.data || [])
    })
  }, [])

  useEffect(() => {
    const params = new URLSearchParams()
    if (status) params.set("status", status)
    if (priority) params.set("priority", priority)
    if (countryId) params.set("countryId", countryId)
    if (entityId) params.set("entityId", entityId)
    if (search) params.set("search", search)
    params.set("page", String(pagination.page))
    params.set("limit", String(PAGE_LIMIT))

    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch is async, setLoading is needed for loading state
    setLoading(true)
    fetch(`/api/compliance?${params.toString()}`)
      .then((r) => r.json())
      .then((result) => {
        setData(result.data || result.compliance || result)
        if (result.pagination) setPagination((p) => ({ ...p, ...result.pagination }))
      })
      .catch(() => {
        toast({
          title: "Error",
          description: "Failed to load compliance data",
          variant: "destructive",
        })
      })
      .finally(() => setLoading(false))
  }, [status, priority, countryId, entityId, search, pagination.page, refreshKey])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPagination((p) => ({ ...p, page: 1 }))
  }

  function handleDelete() {
    if (!deleteId) return
    setDeleteLoading(true)
    fetch(`/api/compliance/${deleteId}`, { method: "DELETE" })
      .then((r) => {
        if (!r.ok) throw new Error("Delete failed")
        toast({ title: "Compliance deleted" })
        setDeleteId(null)
        setPagination((p) => ({ ...p, page: 1 }))
        setRefreshKey((k) => k + 1)
      })
      .catch(() => {
        toast({ title: "Error", description: "Failed to delete compliance", variant: "destructive" })
      })
      .finally(() => setDeleteLoading(false))
  }

  function getFilingDueColor(item: ComplianceItem) {
    if (item.filedAt) return ""
    const d = daysUntil(new Date(item.dueDate))
    if (d < 0) return "text-red-600 font-medium"
    if (d <= 3) return "text-orange-600 font-medium"
    return ""
  }

  function getPaymentDueColor(item: ComplianceItem) {
    if (item.requiresPayment === false || item.paidAt || !item.paymentDueDate) return ""
    const d = daysUntil(new Date(item.paymentDueDate))
    if (d < 0) return "text-red-600 font-medium"
    if (d <= 3) return "text-orange-600 font-medium"
    return ""
  }

  const isAdmin = role === "ADMINISTRATOR"
  const isPreparer = role === "PREPARER"
  const canEdit = isAdmin || isPreparer

  return (
    <DashboardLayout title="Obligations Tracker">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-xl font-semibold">Obligations Tracker</h2>
          </div>
          <div className="flex items-center gap-2">
            {(isAdmin || isPreparer) && (
              <Button variant="outline" onClick={() => router.push("/compliance/ad-hoc")}>
                <ClipboardPlus className="h-4 w-4 mr-1" />
                + Add Ad-hoc Templates
              </Button>
            )}
            {(isAdmin || isPreparer) && (
              <Button variant="outline" onClick={() => router.push("/master/compliance-templates/create")}>
                <FileType className="h-4 w-4 mr-1" />
                + Add Recurring Templates
              </Button>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <form onSubmit={handleSearchSubmit} className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
            <Input
              placeholder="Search compliance..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9"
            />
          </form>

          <Select value={status} onValueChange={(v) => { setStatus(v); setPagination((p) => ({ ...p, page: 1 })) }}>
            <SelectTrigger className="w-[170px] h-9">
              <Filter className="h-4 w-4 mr-1" />
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={priority} onValueChange={(v) => { setPriority(v); setPagination((p) => ({ ...p, page: 1 })) }}>
            <SelectTrigger className="w-[150px] h-9">
              <ArrowUpDown className="h-4 w-4 mr-1" />
              <SelectValue placeholder="All Priorities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priorities</SelectItem>
              {PRIORITY_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={countryId} onValueChange={(v) => { setCountryId(v); setPagination((p) => ({ ...p, page: 1 })) }}>
            <SelectTrigger className="w-[170px] h-9">
              <SelectValue placeholder="All Countries" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Countries</SelectItem>
              {countries.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={entityId} onValueChange={(v) => { setEntityId(v); setPagination((p) => ({ ...p, page: 1 })) }}>
            <SelectTrigger className="w-[170px] h-9">
              <SelectValue placeholder="All Entities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Entities</SelectItem>
              {entities.map((e) => (
                <SelectItem key={e.id} value={e.id}>{e.entityName}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
            <h3 className="text-lg font-medium mb-1">No compliance items found</h3>
            <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
              Get started by creating a new compliance schedule.
            </p>
            <Button onClick={() => router.push("/master/compliance-templates/create")}>
              <FileType className="h-4 w-4 mr-1" />
              + Add Recurring Templates
            </Button>
            <Button variant="outline" onClick={() => router.push("/compliance/ad-hoc")}>
              <ClipboardPlus className="h-4 w-4 mr-1" />
              + Add Ad-hoc Templates
            </Button>
          </div>
        ) : (
          <>
            <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Compliance ID</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Country</TableHead>
                    <TableHead>Tax Type</TableHead>
                    <TableHead>Tax Period</TableHead>
                    <TableHead>F Due</TableHead>
                    <TableHead>P Due</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Payment Amount</TableHead>
                    <TableHead>Filing Type</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead>Preparer</TableHead>
                    <TableHead className="w-[70px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.complianceId}</TableCell>
                      <TableCell>
                        {item.entities?.length
                          ? item.entities.map((en) => en.entity?.entityName).join(", ")
                          : item.entity?.entityName}
                      </TableCell>
                      <TableCell>{item.country?.name}</TableCell>
                      <TableCell>{taxTypeLabel(item.taxType)}</TableCell>
                      <TableCell>{item.taxPeriod}</TableCell>
                      <TableCell className={getFilingDueColor(item)}>
                        {formatDate(item.dueDate)}
                        {!item.filedAt && daysUntil(new Date(item.dueDate)) < 0 && (
                          <span className="ml-1 text-xs text-red-500">
                            (Overdue)
                          </span>
                        )}
                        {!item.filedAt &&
                          daysUntil(new Date(item.dueDate)) >= 0 &&
                          daysUntil(new Date(item.dueDate)) <= 3 && (
                            <span className="ml-1 text-xs text-orange-500">
                              ({daysUntil(new Date(item.dueDate))}d left)
                            </span>
                          )}
                      </TableCell>
                      <TableCell className={getPaymentDueColor(item)}>
                        {item.requiresPayment === false || !item.paymentDueDate
                          ? "—"
                          : formatDate(item.paymentDueDate)}
                        {item.requiresPayment !== false &&
                          item.paymentDueDate &&
                          !item.paidAt &&
                          daysUntil(new Date(item.paymentDueDate)) < 0 && (
                            <span className="ml-1 text-xs text-red-500">
                              (Overdue)
                            </span>
                          )}
                        {item.requiresPayment !== false &&
                          item.paymentDueDate &&
                          !item.paidAt &&
                          daysUntil(new Date(item.paymentDueDate)) >= 0 &&
                          daysUntil(new Date(item.paymentDueDate)) <= 3 && (
                            <span className="ml-1 text-xs text-orange-500">
                              ({daysUntil(new Date(item.paymentDueDate))}d left)
                            </span>
                          )}
                      </TableCell>
                      <TableCell>
                        <Badge className={getPriorityColor(item.priority)}>
                          {item.priority}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(item.status)}>
                          {item.status.replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getSourceVariant(item.source)}>
                          {(item.source || "MANUAL").replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell>{item.paymentAmount != null ? item.paymentAmount : "—"}</TableCell>
                      <TableCell>
                        {item.filingType ? item.filingType.replace(/_/g, " ") : "—"}
                      </TableCell>
                      <TableCell>{item.paymentCurrency || "—"}</TableCell>
                      <TableCell>
                        {item.assignments?.[0]?.preparer?.name || "—"}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => router.push(`/compliance/${item.id}`)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View
                            </DropdownMenuItem>
                            {canEdit && (
                              <DropdownMenuItem onClick={() => router.push(`/compliance/${item.id}/edit`)}>
                                <FileText className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                            )}
                            {isAdmin && (
                              <DropdownMenuItem
                                className="text-red-600"
                                onClick={() => setDeleteId(item.id)}
                              >
                                <XCircle className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {pagination.totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  Showing {((pagination.page - 1) * pagination.limit) + 1}
                  {" – "}
                  {Math.min(pagination.page * pagination.limit, pagination.total)}
                  {" of "}
                  {pagination.total}
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={pagination.page <= 1}
                    onClick={() => setPagination((p) => ({ ...p, page: p.page - 1 }))}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  {Array.from({ length: pagination.totalPages }, (_, i) => i + 1).map((page) => (
                    <Button
                      key={page}
                      variant={page === pagination.page ? "default" : "outline"}
                      size="sm"
                      className="h-9 w-9"
                      onClick={() => setPagination((p) => ({ ...p, page }))}
                    >
                      {page}
                    </Button>
                  ))}
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={pagination.page >= pagination.totalPages}
                    onClick={() => setPagination((p) => ({ ...p, page: p.page + 1 }))}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Compliance</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this compliance item? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteLoading && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  )
}
