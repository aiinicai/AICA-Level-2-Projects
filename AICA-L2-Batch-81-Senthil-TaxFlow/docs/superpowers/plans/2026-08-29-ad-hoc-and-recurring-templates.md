# Ad-hoc Compliance Page & Recurring Templates Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename Compliance Templates → Recurring Templates, add a dedicated Ad-hoc Compliances page for uploading and tracking one-off items, and update Compliance Tracker buttons accordingly.

**Architecture:** Two sequential phases: (1) rename all "Compliance Templates" labels to "Recurring Templates" across the UI; (2) add the Ad-hoc Compliances page backed by a new `isRecurring=false` filter on the existing compliance API, and rewire the tracker buttons.

**Tech Stack:** Next.js 16 (app router, `"use client"` pages), React 19, Supabase (Postgres), Tailwind CSS, Radix UI primitives, lucide-react icons.

## Global Constraints

- **No URL/route changes**: all existing routes (`/master/compliance-templates`, `/compliance`) stay as-is. Only labels are renamed.
- **No database or schema changes**: the `compliance_schedules.isRecurring` column already exists and is sufficient.
- **No API contract changes** beyond adding an optional `isRecurring` query param to `GET /api/compliance`.
- **Role gating**: only Admins and Preparers may add/edit; all roles may view.
- **Follow existing code conventions**: files under `src/app` are `"use client"`; UI components under `src/components/ui/`; icons from `lucide-react`; data fetched via `fetch()` in `useEffect`/`useCallback`.

---

## File Map

| Action | File |
|--------|------|
| Modify | `src/components/layout/app-sidebar.tsx` |
| Modify | `src/app/master/page.tsx` |
| Modify | `src/app/master/layout.tsx` |
| Modify | `src/app/master/compliance-templates/page.tsx` |
| Modify | `src/app/master/compliance-templates/create/page.tsx` |
| Modify | `src/app/master/compliance-templates/[id]/page.tsx` |
| Modify | `src/app/master/compliance-templates/[id]/edit/page.tsx` |
| Modify | `src/app/compliance/page.tsx` |
| Modify | `src/app/api/compliance/route.ts` |
| Create | `src/app/compliance/ad-hoc/page.tsx` |

---

## Task 1: Rename Compliance Templates → Recurring Templates (labels only)

All changes below are label-only. No functional changes.

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx:61`
- Modify: `src/app/master/page.tsx:52-53`
- Modify: `src/app/master/layout.tsx:22-23,34`
- Modify: `src/app/master/compliance-templates/page.tsx:353-354,469,760`
- Modify: `src/app/master/compliance-templates/create/page.tsx:321`
- Modify: `src/app/master/compliance-templates/[id]/page.tsx:495,499,516`
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx:404,408,423`

- [ ] **Step 1: Update sidebar** (`src/components/layout/app-sidebar.tsx:61`)

Change:
```tsx
{ title: "Compliance Templates", href: "/master/compliance-templates", icon: FileType },
```
To:
```tsx
{ title: "Recurring Templates", href: "/master/compliance-templates", icon: FileType },
```

- [ ] **Step 2: Remove from Master Data overview** (`src/app/master/page.tsx`)

Delete the entire Compliance Templates card from the `overviewCards` array (lines 51-57):
```tsx
  {
    title: "Compliance Templates",
    description: "Manage compliance templates, versioning, and generate compliance trackers.",
    icon: FileType,
    href: "/master/compliance-templates",
    color: "bg-indigo-500",
  },
```
Also remove `FileType` from the lucide-react import if no longer used in this file (it is not).

- [ ] **Step 3: Remove Templates tab from Master layout** (`src/app/master/layout.tsx`)

Remove this entry from `navItems` (line 22):
```tsx
  { href: "/master/compliance-templates", label: "Templates", icon: FileType },
```
Remove `FileType` from the lucide-react import. Update the `DashboardLayout` title (line 34) from:
```tsx
<DashboardLayout title={isComplianceTemplates ? "Compliance Templates" : undefined}>
```
To:
```tsx
<DashboardLayout title={isComplianceTemplates ? "Recurring Templates" : undefined}>
```

- [ ] **Step 4: Update templates list page** (`src/app/master/compliance-templates/page.tsx`)

Update these exact strings:

Line 353 — CardTitle:
```tsx
<CardTitle>Compliance Templates</CardTitle>
```
→
```tsx
<CardTitle>Recurring Templates</CardTitle>
```

Line 354 — CardDescription:
```tsx
<CardDescription>Manage compliance templates and generate schedules by month.</CardDescription>
```
→
```tsx
<CardDescription>Manage recurring template schedules and generate by month.</CardDescription>
```

Line 366 — Create button:
```tsx
Create Recurring Template
```
→
```tsx
+ Add Recurring Templates
```

Line 469 — empty state text:
```tsx
{search ? "No templates match your search." : "No compliance templates yet."}
```
→
```tsx
{search ? "No templates match your search." : "No recurring templates yet."}
```

Line 760 — delete dialog description:
```tsx
Are you sure you want to delete this compliance template? This action cannot be undone.
```
→
```tsx
Are you sure you want to delete this recurring template? This action cannot be undone.
```

- [ ] **Step 5: Update create page** (`src/app/master/compliance-templates/create/page.tsx`)

Line 321:
```tsx
<h2 className="text-xl font-semibold">Create Compliance Template</h2>
```
→
```tsx
<h2 className="text-xl font-semibold">Create Recurring Template</h2>
```

- [ ] **Step 6: Update detail page** (`src/app/master/compliance-templates/[id]/page.tsx`)

Line 495:
```tsx
The compliance template you&apos;re looking for doesn&apos;t exist or has been deleted.
```
→
```tsx
The recurring template you&apos;re looking for doesn&apos;t exist or has been deleted.
```

Line 499:
```tsx
Back to Compliance Templates
```
→
```tsx
Back to Recurring Templates
```

Line 516 — fallback heading:
```tsx
<h2 className="text-xl font-semibold">{data.templateNumber || "Compliance Template"}</h2>
```
→
```tsx
<h2 className="text-xl font-semibold">{data.templateNumber || "Recurring Template"}</h2>
```

- [ ] **Step 7: Update edit page** (`src/app/master/compliance-templates/[id]/edit/page.tsx`)

Line 404:
```tsx
The compliance template you&apos;re looking for doesn&apos;t exist or has been deleted.
```
→
```tsx
The recurring template you&apos;re looking for doesn&apos;t exist or has been deleted.
```

Line 408:
```tsx
Back to Compliance Templates
```
→
```tsx
Back to Recurring Templates
```

Line 423:
```tsx
<h2 className="text-xl font-semibold">Edit Compliance Template</h2>
```
→
```tsx
<h2 className="text-xl font-semibold">Edit Recurring Template</h2>
```

- [ ] **Step 8: Run lint and typecheck**

Run: `npm run lint && npx tsc --noEmit`
Expected: PASS (no functional changes, only label edits)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(labels): rename Compliance Templates → Recurring Templates, remove from Master Data"
```

---

## Task 2: Add `isRecurring` filter to GET /api/compliance

**Files:**
- Modify: `src/app/api/compliance/route.ts:94-137`

- [ ] **Step 1: Add the `isRecurring` query param**

In the GET handler, after the existing `approverId` param parsing block (around line 103), add:
```ts
const isRecurringParam = searchParams.get("isRecurring") || ""
```

Then, after the `if (approverId && approverId !== "all")` block (after line 135), add:
```ts
if (isRecurringParam !== "") {
  query = query.eq("isRecurring", isRecurringParam === "true")
}
```

- [ ] **Step 2: Run lint and typecheck**

Run: `npm run lint && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/app/api/compliance/route.ts
git commit -m "feat(api): add isRecurring filter to GET /api/compliance"
```

---

## Task 3: Update Compliance Tracker buttons

**Files:**
- Modify: `src/app/compliance/page.tsx:310-326,397-408`

- [ ] **Step 1: Replace DataImport dropdown with navigation button**

Replace the DataImport dropdown block (lines 311-318):
```tsx
{(isAdmin || isPreparer) && (
  <DataImport
    entityName="Compliance"
    columns={IMPORT_COLUMNS}
    uploadEndpoint="/api/compliance/import"
    onComplete={fetchData}
    dropdownTrigger="Create Ad-hoc Compliance"
  />
)}
```
With:
```tsx
{(isAdmin || isPreparer) && (
  <Button variant="outline" onClick={() => router.push("/compliance/ad-hoc")}>
    <ClipboardPlus className="h-4 w-4 mr-1" />
    + Add Ad-hoc Compliances
  </Button>
)}
```
Add `ClipboardPlus` to the lucide-react import at the top of the file.

- [ ] **Step 2: Rename the Recurring Template button (header)**

Replace lines 320-325:
```tsx
{(isAdmin || isPreparer) && (
  <Button variant="outline" onClick={() => router.push("/master/compliance-templates/create")}>
    <FileType className="h-4 w-4 mr-1" />
    Create Recurring Template
  </Button>
)}
```
With:
```tsx
{(isAdmin || isPreparer) && (
  <Button variant="outline" onClick={() => router.push("/master/compliance-templates/create")}>
    <FileType className="h-4 w-4 mr-1" />
    + Add Recurring Templates
  </Button>
)}
```

- [ ] **Step 3: Update the empty state**

Replace the empty state button (lines 404-407):
```tsx
<Button onClick={() => router.push("/master/compliance-templates/create")}>
  <FileType className="h-4 w-4 mr-1" />
  Create Recurring Template
</Button>
```
With:
```tsx
<Button onClick={() => router.push("/master/compliance-templates/create")}>
  <FileType className="h-4 w-4 mr-1" />
  + Add Recurring Templates
</Button>
```

- [ ] **Step 4: Run lint and typecheck**

Run: `npm run lint && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/compliance/page.tsx
git commit -m "feat(compliance): rewire tracker buttons to navigate to ad-hoc page and rename recurring button"
```

---

## Task 4: Create the Ad-hoc Compliances page

**Files:**
- Create: `src/app/compliance/ad-hoc/page.tsx`

This page is a focused tracking view for non-recurring compliance items. It reuses the same `DataImport` component for CSV uploads and mirrors the Compliance Tracker's table structure, filters, and actions. The page is approximately 550 lines following the same `"use client"` pattern as `compliance/page.tsx`.

- [ ] **Step 1: Create the page file**

Create `src/app/compliance/ad-hoc/page.tsx` with the following content:

```tsx
"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import {
  ClipboardPlus,
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
  ArrowUpDown,
  CheckCircle2,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import DataImport from "@/components/data-import"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { toast } from "@/components/ui/toast"
import {
  formatDate, daysUntil, getStatusColor, getPriorityColor,
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

const IMPORT_COLUMNS = [
  { key: "entityNumber", label: "Entity Number", required: true, description: "e.g. ENT-001" },
  { key: "taxType", label: "Tax Type", required: true, description: "VAT / GST / SALES_TAX / WHT / CORPORATE_TAX / STATUTORY" },
  { key: "taxPeriod", label: "Tax Period", required: true, description: "e.g. 2026-03 or Q1 2026" },
  { key: "dueDate", label: "Due Date", required: true, description: "YYYY-MM-DD" },
  { key: "country", label: "Country", description: "Name or code; defaults to entity country" },
  { key: "frequency", label: "Frequency", description: "Defaults to AD_HOC" },
  { key: "priority", label: "Priority", description: "NORMAL / HIGH / CRITICAL" },
  { key: "reviewer", label: "Reviewer Email", description: "Step-1 approver email" },
  { key: "approver", label: "Approver Email", description: "Step-2 approver email (two-level flow)" },
  { key: "notes", label: "Notes", description: "Optional notes" },
]

function getSourceVariant(source: string | undefined): "default" | "secondary" | "outline" {
  switch (source) {
    case "TEMPLATE": return "secondary"
    case "IMPORT": return "default"
    default: return "outline"
  }
}

export default function AdHocCompliancesPage() {
  const router = useRouter()
  const { user: sessionUser } = useAuth()
  const role = sessionUser?.role

  const [data, setData] = useState<ComplianceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState<Pagination>({
    page: 1, limit: PAGE_LIMIT, total: 0, totalPages: 0,
  })

  const [status, setStatus] = useState("")
  const [priority, setPriority] = useState("")
  const [countryId, setCountryId] = useState("")
  const [entityId, setEntityId] = useState("")
  const [search, setSearch] = useState("")

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [bulkApproving, setBulkApproving] = useState(false)

  const [countries, setCountries] = useState<Country[]>([])
  const [entities, setEntities] = useState<Entity[]>([])

  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch("/api/countries").then((r) => r.json()),
      fetch("/api/entities").then((r) => r.json()),
    ]).then(([c, e]) => {
      setCountries(Array.isArray(c) ? c : c.countries || c.data || [])
      setEntities(Array.isArray(e) ? e : e.entities || e.data || [])
    })
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("isRecurring", "false")
      if (status) params.set("status", status)
      if (priority) params.set("priority", priority)
      if (countryId) params.set("countryId", countryId)
      if (entityId) params.set("entityId", entityId)
      if (search) params.set("search", search)
      params.set("page", String(pagination.page))
      params.set("limit", String(PAGE_LIMIT))

      const res = await fetch(`/api/compliance?${params.toString()}`)
      if (!res.ok) throw new Error("Failed to fetch")
      const result = await res.json()
      setData(result.data || result.compliance || result)
      if (result.pagination) setPagination((p) => ({ ...p, ...result.pagination }))
    } catch {
      toast({
        title: "Error",
        description: "Failed to load ad-hoc compliance data",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }, [status, priority, countryId, entityId, search, pagination.page])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchData()
  }, [fetchData])

  function toggleSelect(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleBulkApprove() {
    if (selectedIds.length === 0) return
    setBulkApproving(true)
    try {
      const res = await fetch("/api/compliance/bulk-approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: selectedIds }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || "Bulk approval failed")
      toast({
        title: "Bulk approval complete",
        description: `${json.data.approved} approved, ${json.data.skipped} skipped`,
      })
      setSelectedIds([])
      fetchData()
    } catch (e) {
      toast({
        title: "Error",
        description: e instanceof Error ? e.message : "Bulk approval failed",
        variant: "destructive",
      })
    } finally {
      setBulkApproving(false)
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSelectedIds([])
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
        fetchData()
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
    <DashboardLayout title="Ad-hoc Compliances">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardPlus className="h-5 w-5 text-[var(--color-primary)]" />
            <div>
              <h2 className="text-xl font-semibold">Ad-hoc Compliances</h2>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                One-off compliance items uploaded for tracking
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {(isAdmin || isPreparer) && (
              <DataImport
                entityName="Compliance"
                columns={IMPORT_COLUMNS}
                uploadEndpoint="/api/compliance/import"
                onComplete={fetchData}
                dropdownTrigger="+ Add Ad-hoc Compliances"
              />
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

          <Select value={status} onValueChange={(v) => { setStatus(v); setSelectedIds([]); setPagination((p) => ({ ...p, page: 1 })) }}>
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

          <Select value={priority} onValueChange={(v) => { setPriority(v); setSelectedIds([]); setPagination((p) => ({ ...p, page: 1 })) }}>
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

          <Select value={countryId} onValueChange={(v) => { setCountryId(v); setSelectedIds([]); setPagination((p) => ({ ...p, page: 1 })) }}>
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

          <Select value={entityId} onValueChange={(v) => { setEntityId(v); setSelectedIds([]); setPagination((p) => ({ ...p, page: 1 })) }}>
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
            <h3 className="text-lg font-medium mb-1">No ad-hoc compliance items found</h3>
            <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
              Upload a CSV to import one-off compliance items for tracking.
            </p>
            {(isAdmin || isPreparer) && (
              <DataImport
                entityName="Compliance"
                columns={IMPORT_COLUMNS}
                uploadEndpoint="/api/compliance/import"
                onComplete={fetchData}
                dropdownTrigger="+ Add Ad-hoc Compliances"
              />
            )}
          </div>
        ) : (
          <>
            {isAdmin && selectedIds.length > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2">
                <span className="text-sm text-[var(--color-muted-foreground)]">
                  {selectedIds.length} selected
                </span>
                <Button size="sm" onClick={handleBulkApprove} disabled={bulkApproving}>
                  {bulkApproving ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                  )}
                  Approve Selected
                </Button>
              </div>
            )}
            <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    {isAdmin && (
                      <TableHead className="w-[40px]">
                        <Checkbox
                          checked={data.length > 0 && data.every((i) => selectedIds.includes(i.id))}
                          onCheckedChange={(v) => setSelectedIds(v ? data.map((i) => i.id) : [])}
                        />
                      </TableHead>
                    )}
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
                    <TableHead>Preparer</TableHead>
                    <TableHead className="w-[70px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((item) => (
                    <TableRow key={item.id}>
                      {isAdmin && (
                        <TableCell>
                          <Checkbox
                            checked={selectedIds.includes(item.id)}
                            onCheckedChange={() => toggleSelect(item.id)}
                          />
                        </TableCell>
                      )}
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
                          <span className="ml-1 text-xs text-red-500">(Overdue)</span>
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
                            <span className="ml-1 text-xs text-red-500">(Overdue)</span>
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
                    onClick={() => { setSelectedIds([]); setPagination((p) => ({ ...p, page: p.page - 1 })) }}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  {Array.from({ length: pagination.totalPages }, (_, i) => i + 1).map((page) => (
                    <Button
                      key={page}
                      variant={page === pagination.page ? "default" : "outline"}
                      size="sm"
                      className="h-9 w-9"
                      onClick={() => { setSelectedIds([]); setPagination((p) => ({ ...p, page })) }}
                    >
                      {page}
                    </Button>
                  ))}
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={pagination.page >= pagination.totalPages}
                    onClick={() => { setSelectedIds([]); setPagination((p) => ({ ...p, page: p.page + 1 })) }}
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
```

- [ ] **Step 2: Run lint and typecheck**

Run: `npm run lint && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/app/compliance/ad-hoc/page.tsx
git commit -m "feat(compliance): add dedicated Ad-hoc Compliances page with upload and tracking table"
```

---

## Task 5: Final lint, typecheck, and verify

- [ ] **Step 1: Run full lint and typecheck**

Run: `npm run lint && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 2: Verify all renamed labels in the browser**

Navigate to:
- `/compliance` — confirm "+ Add Ad-hoc Compliances" and "+ Add Recurring Templates" buttons appear
- `/compliance/ad-hoc` — confirm page loads with heading "Ad-hoc Compliances" and upload button
- `/master` — confirm no Compliance Templates card
- `/master/compliance-templates` — confirm "Recurring Templates" heading
- Sidebar — confirm "Recurring Templates" and "Ad-hoc Compliances" under Compliance Home; no "Compliance Templates" in Master Data section

- [ ] **Step 3: Commit any fixes if lint/typecheck found issues**

```bash
git add -A && git commit -m "fix: lint and typecheck cleanup"
```