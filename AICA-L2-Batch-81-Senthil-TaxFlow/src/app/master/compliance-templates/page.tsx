"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import {
  Plus,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  MoreHorizontal,
  Loader2,
  XCircle,
  FileText,
  AlertCircle,
  CalendarDays,
  Power,
} from "lucide-react"
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableHeader, TableBody, TableHead, TableRow, TableCell,
} from "@/components/ui/table"
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription, DialogClose,
} from "@/components/ui/dialog"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader,
  AlertDialogFooter, AlertDialogTitle, AlertDialogDescription,
  AlertDialogAction, AlertDialogCancel,
} from "@/components/ui/alert-dialog"
import { useToast } from "@/components/ui/toast"
import { getStatusColor } from "@/lib/utils"
import { TAX_TYPE_OPTIONS, taxTypeLabel } from "@/lib/tax-types"

const PAGE_LIMIT = 15

const STATUS_OPTIONS = [
  { value: "PENDING_ADMIN_APPROVAL", label: "Pending Admin Approval" },
  { value: "PENDING_REVIEW", label: "Pending Review" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
]

const FREQUENCY_OPTIONS = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "BI_MONTHLY", label: "Bi-Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "HALF_YEARLY", label: "Half-Yearly" },
  { value: "ANNUAL", label: "Annual" },
]

const FREQUENCY_LABELS: Record<string, string> = Object.fromEntries(
  FREQUENCY_OPTIONS.map((o) => [o.value, o.label])
)

function frequencyLabel(frequency: string | null | undefined): string {
  if (!frequency) return "-"
  return FREQUENCY_LABELS[frequency] || frequency
}

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

interface Form {
  id: string
  formNumber: string
  formName: string
}

interface TemplateEntity {
  id: string
  entityId: string
  entity: Entity | null
}

interface TemplateItem {
  id: string
  templateNumber: string
  version: number
  status: string
  isActive: boolean
  taxType: string | null
  country: Country | null
  form: Form | null
  frequency: string | null
  isRecurring: boolean
  entities: TemplateEntity[]
  createdBy: { id: string; name: string; email: string } | null
  createdAt: string
}

interface BulkSummary {
  total: number
  created: number
  skipped: number
  futureNotGenerated: number
  overlapSkipped: number
  existingSkipped: number
  failed: number
}

export default function ComplianceTemplatesPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { activeRole } = useAuth()
  const isAdmin = activeRole === "ADMINISTRATOR"

  const [data, setData] = useState<TemplateItem[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const [status, setStatus] = useState("")
  const [countryId, setCountryId] = useState("")
  const [entityId, setEntityId] = useState("")
  const [taxType, setTaxType] = useState("")
  const [formId, setFormId] = useState("")
  const [frequency, setFrequency] = useState("")
  const [search, setSearch] = useState("")

  const [countries, setCountries] = useState<Country[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [forms, setForms] = useState<Form[]>([])

  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkFilingMonth, setBulkFilingMonth] = useState("")
  const [bulkCountryId, setBulkCountryId] = useState("")
  const [bulkEntityId, setBulkEntityId] = useState("")
  const [bulkTaxType, setBulkTaxType] = useState("")
  const [bulkSubmitting, setBulkSubmitting] = useState(false)
  const [bulkResult, setBulkResult] = useState<BulkSummary | null>(null)

  const [rowTarget, setRowTarget] = useState<TemplateItem | null>(null)
  const [rowFilingMonth, setRowFilingMonth] = useState("")
  const [rowSubmitting, setRowSubmitting] = useState(false)
  const [rowResult, setRowResult] = useState<{
    created: number
    skipped: number
    futureNotGenerated: number
    overlapSkipped: number
    existingSkipped: number
  } | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT))

  useEffect(() => {
    const parseData = (r: PromiseSettledResult<{ data?: unknown[] }>) =>
      r.status === "fulfilled" ? r.value.data || [] : []
    Promise.allSettled([
      fetch("/api/countries").then((r) => r.json()),
      fetch("/api/entities").then((r) => r.json()),
      fetch("/api/forms").then((r) => r.json()),
    ]).then(([c, e, f]) => {
      setCountries(parseData(c) as Country[])
      setEntities(parseData(e) as Entity[])
      setForms(parseData(f) as Form[])
    })
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (status) params.set("status", status)
      if (countryId) params.set("countryId", countryId)
      if (entityId) params.set("entityId", entityId)
      if (taxType) params.set("taxType", taxType)
      if (formId) params.set("formId", formId)
      if (frequency) params.set("frequency", frequency)
      if (search) params.set("search", search)
      params.set("page", String(page))
      params.set("limit", String(PAGE_LIMIT))

      const res = await fetch(`/api/templates?${params.toString()}`)
      if (!res.ok) throw new Error("Failed to fetch")
      const result = await res.json()
      setData(result.data || [])
      setTotal(result.total || 0)
    } catch {
      toast({
        title: "Error",
        description: "Failed to load recurring templates",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }, [status, countryId, entityId, taxType, formId, frequency, search, page, toast])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchData()
  }, [fetchData])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
  }

  function openBulkGenerate() {
    setBulkFilingMonth("")
    setBulkCountryId("")
    setBulkEntityId("")
    setBulkTaxType("")
    setBulkResult(null)
    setBulkOpen(true)
  }

  function openRowGenerate(item: TemplateItem) {
    setRowTarget(item)
    setRowFilingMonth("")
    setRowResult(null)
  }

  async function handleBulkGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!bulkFilingMonth) return
    setBulkSubmitting(true)
    setBulkResult(null)
    try {
      const filters = {
        countryIds: bulkCountryId && bulkCountryId !== "all" ? [bulkCountryId] : [],
        entityIds: bulkEntityId && bulkEntityId !== "all" ? [bulkEntityId] : [],
        taxTypes: bulkTaxType && bulkTaxType !== "all" ? [bulkTaxType] : [],
      }
      const res = await fetch("/api/templates/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filingMonth: bulkFilingMonth, filters }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || "Generation failed")
      const summary = json.data?.summary as BulkSummary
      setBulkResult(summary)
      toast({
        title: "Success",
        description: `Generated ${summary?.created ?? 0} compliance(s) for ${bulkFilingMonth}. ${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0) + (summary?.existingSkipped ?? 0)} skipped.`,
      })
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setBulkSubmitting(false)
    }
  }

  async function handleRowGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!rowTarget || !rowFilingMonth) return
    setRowSubmitting(true)
    setRowResult(null)
    try {
      const res = await fetch(`/api/templates/${rowTarget.id}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filingMonth: rowFilingMonth }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || "Generation failed")
      const summary = json.data?.summary as {
        created: number
        skipped: number
        futureNotGenerated: number
        overlapSkipped: number
        existingSkipped: number
      }
      setRowResult(summary)
      toast({
        title: "Success",
        description: `Generated ${summary?.created ?? 0} compliance(s) for ${rowFilingMonth}. ${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0) + (summary?.existingSkipped ?? 0)} skipped.`,
      })
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setRowSubmitting(false)
    }
  }

  async function handleToggleActive(item: TemplateItem) {
    const next = !item.isActive
    try {
      const res = await fetch(`/api/templates/${item.id}/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isActive: next }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || "Request failed")
      toast({
        title: "Success",
        description: next ? "Template activated" : "Template deactivated",
      })
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    setDeleteLoading(true)
    try {
      const res = await fetch(`/api/templates/${deleteId}`, { method: "DELETE" })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || "Delete failed")
      toast({ title: "Success", description: "Template deleted" })
      setDeleteId(null)
      setPage(1)
      fetchData()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recurring Templates</CardTitle>
            <CardDescription>Manage recurring template schedules and generate by month.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <Button variant="outline" onClick={openBulkGenerate}>
                <CalendarDays className="h-4 w-4 mr-2" />
                Generate for Month
              </Button>
            )}
            {isAdmin && (
              <Button onClick={() => router.push("/master/compliance-templates/create")}>
                <Plus className="h-4 w-4 mr-2" />
                + Add Recurring Templates
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <form onSubmit={handleSearchSubmit} className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
              <Input
                placeholder="Search templates..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9"
              />
            </form>

            <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1) }}>
              <SelectTrigger className="w-[180px] h-9">
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

            <Select value={countryId} onValueChange={(v) => { setCountryId(v); setPage(1) }}>
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

            <Select value={entityId} onValueChange={(v) => { setEntityId(v); setPage(1) }}>
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

            <Select value={taxType} onValueChange={(v) => { setTaxType(v); setPage(1) }}>
              <SelectTrigger className="w-[170px] h-9">
                <SelectValue placeholder="All Tax Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tax Types</SelectItem>
                {TAX_TYPE_OPTIONS.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={formId} onValueChange={(v) => { setFormId(v); setPage(1) }}>
              <SelectTrigger className="w-[170px] h-9">
                <SelectValue placeholder="All Forms" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Forms</SelectItem>
                {forms.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.formNumber}{f.formName ? ` – ${f.formName}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={frequency} onValueChange={(v) => { setFrequency(v); setPage(1) }}>
              <SelectTrigger className="w-[170px] h-9">
                <SelectValue placeholder="All Frequencies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Frequencies</SelectItem>
                {FREQUENCY_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : data.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto text-slate-300" />
              <p className="mt-3 text-sm text-slate-500">
                {search ? "No templates match your search." : "No recurring templates yet."}
              </p>
              {!search && isAdmin && (
                <Button variant="outline" className="mt-4" onClick={() => router.push("/master/compliance-templates/create")}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create your first template
                </Button>
              )}
            </div>
          ) : (
            <>
              <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Template Number</TableHead>
                        <TableHead>Version</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Tax Type</TableHead>
                        <TableHead>Country</TableHead>
                        <TableHead>Form</TableHead>
                        <TableHead>Frequency</TableHead>
                        <TableHead>Entities</TableHead>
                        <TableHead>Recurring</TableHead>
                        <TableHead>Created By</TableHead>
                        <TableHead className="w-[70px]">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium">{item.templateNumber}</TableCell>
                          <TableCell>v{item.version}</TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(item.status)}>
                              {item.status.replace(/_/g, " ")}
                            </Badge>
                          </TableCell>
                          <TableCell>{taxTypeLabel(item.taxType)}</TableCell>
                          <TableCell>{item.country?.name || "-"}</TableCell>
                          <TableCell>
                            {item.form
                              ? `${item.form.formNumber}${item.form.formName ? ` – ${item.form.formName}` : ""}`
                              : "-"}
                          </TableCell>
                          <TableCell>{frequencyLabel(item.frequency)}</TableCell>
                          <TableCell>{item.entities?.length ?? 0}</TableCell>
                          <TableCell>{item.isRecurring ? "Yes" : "No"}</TableCell>
                          <TableCell>{item.createdBy?.name || "—"}</TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => router.push(`/master/compliance-templates/${item.id}`)}>
                                  <Eye className="h-4 w-4 mr-2" />
                                  View
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => router.push(`/master/compliance-templates/${item.id}/edit`)}>
                                  <FileText className="h-4 w-4 mr-2" />
                                  Edit
                                </DropdownMenuItem>
                                {isAdmin && (
                                  <>
                                    <DropdownMenuItem onClick={() => openRowGenerate(item)}>
                                      <CalendarDays className="h-4 w-4 mr-2" />
                                      Generate for Month
                                    </DropdownMenuItem>
                                    {item.status === "APPROVED" && (
                                      <DropdownMenuItem onClick={() => handleToggleActive(item)}>
                                        <Power className="h-4 w-4 mr-2" />
                                        {item.isActive ? "Deactivate" : "Activate"}
                                      </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem
                                      className="text-red-600"
                                      onClick={() => setDeleteId(item.id)}
                                    >
                                      <XCircle className="h-4 w-4 mr-2" />
                                      Delete
                                    </DropdownMenuItem>
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <p className="text-sm text-[var(--color-muted-foreground)]">
                    Showing {((page - 1) * PAGE_LIMIT) + 1}
                    {" – "}
                    {Math.min(page * PAGE_LIMIT, total)}
                    {" of "}
                    {total}
                  </p>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
                      <Button
                        key={pg}
                        variant={pg === page ? "default" : "outline"}
                        size="sm"
                        className="h-9 w-9"
                        onClick={() => setPage(pg)}
                      >
                        {pg}
                      </Button>
                    ))}
                    <Button
                      variant="outline"
                      size="icon"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
        <DialogContent className="sm:max-w-lg">
          <form onSubmit={handleBulkGenerate}>
            <DialogHeader>
              <DialogTitle>Generate Compliances for Month</DialogTitle>
              <DialogDescription>
                Generate compliance schedules from approved templates for the selected filing month.
                Optional filters limit which templates are used.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="bulkFilingMonth">Filing Month *</Label>
                <Input
                  id="bulkFilingMonth"
                  type="month"
                  value={bulkFilingMonth}
                  onChange={(e) => setBulkFilingMonth(e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Country</Label>
                  <Select value={bulkCountryId} onValueChange={setBulkCountryId}>
                    <SelectTrigger>
                      <SelectValue placeholder="All countries" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All countries</SelectItem>
                      {countries.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Tax Type</Label>
                  <Select value={bulkTaxType} onValueChange={setBulkTaxType}>
                    <SelectTrigger>
                      <SelectValue placeholder="All tax types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All tax types</SelectItem>
                      {TAX_TYPE_OPTIONS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Entity</Label>
                <Select value={bulkEntityId} onValueChange={setBulkEntityId}>
                  <SelectTrigger>
                    <SelectValue placeholder="All entities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All entities</SelectItem>
                    {entities.map((e) => (
                      <SelectItem key={e.id} value={e.id}>{e.entityName}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {bulkResult && (
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm">
                  <p className="font-medium mb-1">Generation summary</p>
                  <p>{bulkResult.created} compliance(s) created for the selected filing month</p>
                  {bulkResult.futureNotGenerated > 0 && (
                    <p>{bulkResult.futureNotGenerated} will be generated when the next period becomes due</p>
                  )}
                  {bulkResult.overlapSkipped > 0 && (
                    <p>{bulkResult.overlapSkipped} skipped (period overlaps an existing compliance)</p>
                  )}
                  {bulkResult.existingSkipped > 0 && (
                    <p>{bulkResult.existingSkipped} skipped (a compliance already exists for the filing month)</p>
                  )}
                  {bulkResult.failed > 0 && <p>{bulkResult.failed} failed</p>}
                </div>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">Close</Button>
              </DialogClose>
              <Button type="submit" disabled={bulkSubmitting}>
                {bulkSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Generate
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!rowTarget} onOpenChange={(o) => !o && setRowTarget(null)}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleRowGenerate}>
            <DialogHeader>
              <DialogTitle>Generate for {rowTarget?.templateNumber || ""}</DialogTitle>
              <DialogDescription>
                Generate compliance schedules for this template for the selected filing month.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="rowFilingMonth">Filing Month *</Label>
                <Input
                  id="rowFilingMonth"
                  type="month"
                  value={rowFilingMonth}
                  onChange={(e) => setRowFilingMonth(e.target.value)}
                  required
                />
              </div>
              {rowResult && (
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm">
                  <p className="font-medium mb-1">Generation summary</p>
                  <p>{rowResult.created} compliance(s) created for the selected filing month</p>
                  {rowResult.futureNotGenerated > 0 && (
                    <p>{rowResult.futureNotGenerated} will be generated when the next period becomes due</p>
                  )}
                  {rowResult.overlapSkipped > 0 && (
                    <p>{rowResult.overlapSkipped} skipped (period overlaps an existing compliance)</p>
                  )}
                  {rowResult.existingSkipped > 0 && (
                    <p>A compliance already exists for the selected filing month</p>
                  )}
                </div>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">Close</Button>
              </DialogClose>
              <Button type="submit" disabled={rowSubmitting}>
                {rowSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Generate
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this recurring template? This action cannot be undone.
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
    </div>
  )
}
