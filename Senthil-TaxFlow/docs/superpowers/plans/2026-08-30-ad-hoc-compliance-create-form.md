# Ad-hoc Compliance Create Form Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated form page at `/compliance/ad-hoc/create` for creating individual ad-hoc compliances manually, complementing the existing CSV upload flow.

**Architecture:** New standalone client component page modeled after the existing `/compliance/create` page and `/master/compliance-templates/create` page. Submits to the existing `POST /api/compliance` endpoint with `isRecurring: false` and `frequency: "AD_HOC"`. No backend changes.

**Tech Stack:** Next.js (App Router), React, TypeScript, shadcn/ui components, lucide-react icons.

## Global Constraints

- All components are client components (`"use client"` at top of file)
- Use `@/` path alias for imports
- Use `toast` from `@/components/ui/toast` (not `useToast` hook — matches compliance tracker page pattern)
- Use `DashboardLayout` from `@/components/layout/dashboard-layout` for page layout
- Use `useAuth` from `@/components/layout/providers` for session user
- ESLint must pass with 0 errors after each task
- No backend/API changes required

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/app/compliance/ad-hoc/create/page.tsx` | Create | Ad-hoc compliance creation form page |
| `src/app/compliance/ad-hoc/page.tsx` | Modify | Add "+ Add Individual" button linking to create page |

---

### Task 1: Create the Ad-hoc Compliance Create Form Page

**Files:**
- Create: `src/app/compliance/ad-hoc/create/page.tsx`

**Interfaces:**
- Consumes: `POST /api/compliance` (existing endpoint), `GET /api/countries`, `GET /api/entities`, `GET /api/users?role=PREPARER`, `GET /api/users?role=REVIEWER`, `GET /api/users?role=APPROVER`, `GET /api/forms?taxType=`
- Produces: A page component at route `/compliance/ad-hoc/create` that creates ad-hoc compliances and redirects to `/compliance/ad-hoc`

- [ ] **Step 1: Create the page file with all imports, interfaces, and constants**

Create `src/app/compliance/ad-hoc/create/page.tsx`:

```tsx
"use client"

import { useState, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import { ArrowLeft, Loader2, Save } from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import MultiSelect from "@/components/multi-select"
import { toast } from "@/components/ui/toast"
import { TAX_TYPE_OPTIONS } from "@/lib/tax-types"
import { normalizeApprovalFlow, requiresApprover, requiresReviewer } from "@/lib/approval-flow"

interface Country {
  id: string
  name: string
  code: string
}

interface Entity {
  id: string
  entityName: string
  entityNumber: string
  approvalFlow?: string
  country?: { id: string; name: string; code: string } | null
}

interface Form {
  id: string
  formNumber: string
  formName: string
  requiresPayment?: boolean
  approvalFlow?: string
}

interface User {
  id: string
  name: string
  email: string
}

const PRIORITY_OPTIONS = [
  { value: "NORMAL", label: "Normal" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
]
```

- [ ] **Step 2: Add the component function with state and data fetching**

Append to the same file:

```tsx
export default function CreateAdHocCompliancePage() {
  const router = useRouter()
  const { user: sessionUser } = useAuth()

  const [entityIds, setEntityIds] = useState<string[]>([])
  const [filingEntityId, setFilingEntityId] = useState("")
  const [taxType, setTaxType] = useState("")
  const [formId, setFormId] = useState("")
  const [countryId, setCountryId] = useState("")
  const [taxPeriod, setTaxPeriod] = useState("")
  const [dueDate, setDueDate] = useState("")
  const [paymentDueDate, setPaymentDueDate] = useState("")
  const [selectedFormRequiresPayment, setSelectedFormRequiresPayment] = useState(true)
  const [priority, setPriority] = useState("NORMAL")
  const [preparerId, setPreparerId] = useState("")
  const [reviewerId, setReviewerId] = useState("")
  const [approverId, setApproverId] = useState("")
  const [notes, setNotes] = useState("")

  const [countries, setCountries] = useState<Country[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [forms, setForms] = useState<Form[]>([])
  const [preparers, setPreparers] = useState<User[]>([])
  const [reviewers, setReviewers] = useState<User[]>([])
  const [approvers, setApprovers] = useState<User[]>([])
  const [submitting, setSubmitting] = useState(false)

  const preparerOptions = useMemo(() => {
    const map = new Map<string, User>()
    preparers.forEach((p) => map.set(p.id, { id: p.id, name: p.name, email: p.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [preparers, sessionUser])

  const reviewerOptions = useMemo(() => {
    const map = new Map<string, User>()
    reviewers.forEach((r) => map.set(r.id, { id: r.id, name: r.name, email: r.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [reviewers, sessionUser])

  const approverOptions = useMemo(() => {
    const map = new Map<string, User>()
    approvers.forEach((a) => map.set(a.id, { id: a.id, name: a.name, email: a.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [approvers, sessionUser])

  const effectivePreparerId = preparerId || sessionUser?.id || ""

  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""

  const selectedEntityFlow = useMemo(() => {
    if (!effectiveFilingEntityId) return ""
    return entities.find((e) => e.id === effectiveFilingEntityId)?.approvalFlow || ""
  }, [entities, effectiveFilingEntityId])

  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])

  const flow = normalizeApprovalFlow(selectedFormFlow || selectedEntityFlow)

  useEffect(() => {
    Promise.all([
      fetch("/api/countries").then((r) => r.json()),
      fetch("/api/entities").then((r) => r.json()),
      fetch("/api/users?role=PREPARER").then((r) => r.json()),
      fetch("/api/users?role=REVIEWER").then((r) => r.json()),
      fetch("/api/users?role=APPROVER").then((r) => r.json()),
    ]).then(([c, e, p, rv, a]) => {
      setCountries(Array.isArray(c) ? c : c.countries || c.data || [])
      setEntities(Array.isArray(e) ? e : e.entities || e.data || [])
      setPreparers(Array.isArray(p) ? p : p.users || p.data || [])
      setReviewers(Array.isArray(rv) ? rv : rv.users || rv.data || [])
      setApprovers(Array.isArray(a) ? a : a.users || a.data || [])
    })
  }, [])

  useEffect(() => {
    if (!taxType) return
    fetch(`/api/forms?taxType=${taxType}`)
      .then((r) => r.json())
      .then((d) => {
        setForms(Array.isArray(d) ? d : d.forms || d.data || [])
      })
  }, [taxType])
```

- [ ] **Step 3: Add handler functions**

Append to the same file:

```tsx
  function handleTaxTypeChange(value: string) {
    setTaxType(value)
    setForms([])
    setFormId("")
    setSelectedFormRequiresPayment(true)
  }

  function handleEntityChange(ids: string[]) {
    setEntityIds(ids)
    if (!ids.includes(filingEntityId)) {
      setFilingEntityId("")
    }
    if (ids.length === 0) {
      setCountryId("")
      return
    }
    const first = entities.find((e) => e.id === ids[0])
    if (first?.country?.id) {
      setCountryId(first.country.id)
    } else if (first?.country?.name) {
      const match = countries.find((c) => c.name === first.country?.name)
      if (match) setCountryId(match.id)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (entityIds.length === 0 || !taxType || !countryId || !taxPeriod || !dueDate) {
      toast({
        title: "Validation Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      })
      return
    }
    if (entityIds.length > 1 && !effectiveFilingEntityId) {
      toast({
        title: "Validation Error",
        description: "Please select a filing entity for this group return",
        variant: "destructive",
      })
      return
    }
    if (requiresReviewer(flow) && !reviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (requiresApprover(flow) && !approverId) {
      toast({
        title: "Validation Error",
        description: "Please select an approver for two-level approval",
        variant: "destructive",
      })
      return
    }

    setSubmitting(true)
    try {
      const body = {
        entityIds,
        taxType,
        formId: formId || undefined,
        countryId,
        filingEntityId: effectiveFilingEntityId || undefined,
        frequency: "AD_HOC",
        isRecurring: false,
        taxPeriod,
        dueDate,
        paymentDueDate: selectedFormRequiresPayment ? paymentDueDate || undefined : undefined,
        priority,
        notes: notes || undefined,
        preparerId: effectivePreparerId || undefined,
        reviewerId: reviewerId || undefined,
        approverId: approverId || undefined,
      }

      const res = await fetch("/api/compliance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || err.message || "Failed to create compliance")
      }

      toast({ title: "Success", description: "Ad-hoc compliance created successfully" })
      router.push("/compliance/ad-hoc")
    } catch (err) {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Something went wrong",
        variant: "destructive",
      })
    } finally {
      setSubmitting(false)
    }
  }
```

- [ ] **Step 4: Add the JSX render section**

Append to the same file:

```tsx
  return (
    <DashboardLayout title="Add Ad-hoc Compliance">
      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => router.push("/compliance/ad-hoc")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-xl font-semibold">Add Ad-hoc Compliance</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Create a one-off compliance item for tracking. Submits as a draft.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Compliance Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="taxType">
                    Tax Type <span className="text-red-500">*</span>
                  </Label>
                  <Select value={taxType} onValueChange={handleTaxTypeChange} required>
                    <SelectTrigger id="taxType">
                      <SelectValue placeholder="Select tax type" />
                    </SelectTrigger>
                    <SelectContent>
                      {TAX_TYPE_OPTIONS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="form">Form</Label>
                  <Select
                    value={formId}
                    onValueChange={(v) => {
                      setFormId(v)
                      const form = forms.find((f) => f.id === v)
                      setSelectedFormRequiresPayment(form?.requiresPayment !== false)
                      if (form?.requiresPayment === false) setPaymentDueDate("")
                    }}
                    disabled={!taxType}
                  >
                    <SelectTrigger id="form">
                      <SelectValue placeholder={taxType ? "Select a form" : "Select a tax type first"} />
                    </SelectTrigger>
                    <SelectContent>
                      {forms.map((f) => (
                        <SelectItem key={f.id} value={f.id}>
                          {f.formNumber} - {f.formName}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="entities">
                  Entities <span className="text-red-500">*</span>
                </Label>
                <MultiSelect
                  options={entities.map((e) => ({
                    value: e.id,
                    label: `${e.entityName} (${e.entityNumber})`,
                    country: e.country?.name,
                  }))}
                  selected={entityIds}
                  onChange={handleEntityChange}
                  searchable
                  showCountryFilter
                  placeholder="Select one or more entities"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="filingEntity">
                  Filing Entity {entityIds.length > 1 && <span className="text-red-500">*</span>}
                </Label>
                <Select
                  value={effectiveFilingEntityId}
                  onValueChange={setFilingEntityId}
                  disabled={entityIds.length === 0 || entityIds.length === 1}
                >
                  <SelectTrigger id="filingEntity">
                    <SelectValue placeholder={entityIds.length === 0 ? "Select entities first" : "Select filing entity"} />
                  </SelectTrigger>
                  <SelectContent>
                    {entities
                      .filter((e) => entityIds.includes(e.id))
                      .map((e) => (
                        <SelectItem key={e.id} value={e.id}>
                          {e.entityName} ({e.entityNumber})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="country">
                  Country <span className="text-red-500">*</span>
                </Label>
                <Select value={countryId} onValueChange={setCountryId} required>
                  <SelectTrigger id="country">
                    <SelectValue placeholder="Select country" />
                  </SelectTrigger>
                  <SelectContent>
                    {countries.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Auto-detected from the selected entities. Override if needed.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="taxPeriod">
                    Tax Period <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="taxPeriod"
                    placeholder="e.g. 2026-03 or Q1 2026"
                    value={taxPeriod}
                    onChange={(e) => setTaxPeriod(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dueDate">
                    Due Date <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="dueDate"
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Payment & Priority</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {selectedFormRequiresPayment && (
                  <div className="space-y-2">
                    <Label htmlFor="paymentDueDate">Payment Due Date</Label>
                    <Input
                      id="paymentDueDate"
                      type="date"
                      value={paymentDueDate}
                      onChange={(e) => setPaymentDueDate(e.target.value)}
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Select value={priority} onValueChange={setPriority}>
                    <SelectTrigger id="priority">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      {PRIORITY_OPTIONS.map((p) => (
                        <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Assignment & Approval</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="preparer">Preparer</Label>
                  <Select value={effectivePreparerId} onValueChange={setPreparerId}>
                    <SelectTrigger id="preparer">
                      <SelectValue placeholder="Select preparer" />
                    </SelectTrigger>
                    <SelectContent>
                      {preparerOptions.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name} ({p.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {requiresReviewer(flow) && (
                  <div className="space-y-2">
                    <Label htmlFor="reviewer">
                      Reviewer <span className="text-red-500">*</span>
                    </Label>
                    <Select value={reviewerId} onValueChange={setReviewerId}>
                      <SelectTrigger id="reviewer">
                        <SelectValue placeholder="Select reviewer" />
                      </SelectTrigger>
                      <SelectContent>
                        {reviewerOptions.map((r) => (
                          <SelectItem key={r.id} value={r.id}>
                            {r.name} ({r.email})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              {requiresApprover(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="approver">
                    Approver <span className="text-red-500">*</span>
                  </Label>
                  <Select value={approverId} onValueChange={setApproverId}>
                    <SelectTrigger id="approver">
                      <SelectValue placeholder="Select approver" />
                    </SelectTrigger>
                    <SelectContent>
                      {approverOptions.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name} ({a.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {approverOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No approvers available</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                id="notes"
                placeholder="Optional notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
              />
            </CardContent>
          </Card>

          <div className="flex items-center justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => router.push("/compliance/ad-hoc")}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              <Save className="h-4 w-4 mr-1" />
              Create Compliance
            </Button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 5: Run ESLint to verify no errors**

Run: `npx eslint "src/app/compliance/ad-hoc/create/page.tsx"`
Expected: 0 errors (warnings acceptable for unused vars if any)

- [ ] **Step 6: Commit**

```bash
git add src/app/compliance/ad-hoc/create/page.tsx
git commit -m "feat(compliance): add ad-hoc compliance create form page"
```

---

### Task 2: Add "+ Add Individual" Button to the Ad-hoc List Page

**Files:**
- Modify: `src/app/compliance/ad-hoc/page.tsx` (header button area, around line 293-303)

**Interfaces:**
- Consumes: The new `/compliance/ad-hoc/create` route from Task 1
- Produces: A button on the ad-hoc list page that navigates to the create form

- [ ] **Step 1: Add the Plus icon import**

In `src/app/compliance/ad-hoc/page.tsx`, add `Plus` to the lucide-react imports. Find the existing import block (lines 8-21) and add `Plus` to it:

Find:
```tsx
import {
  ClipboardPlus,
  Download,
  Eye,
  Filter,
  Loader2,
  MoreHorizontal,
  Search,
  Upload,
  XCircle,
} from "lucide-react"
```

Replace with:
```tsx
import {
  ClipboardPlus,
  Download,
  Eye,
  Filter,
  Loader2,
  MoreHorizontal,
  Plus,
  Search,
  Upload,
  XCircle,
} from "lucide-react"
```

Note: The exact icon list may vary — check the actual imports in the file and add `Plus` alphabetically.

- [ ] **Step 2: Add the "+ Add Individual" button next to the existing DataImport component**

Find the header button area (around line 293-303):

```tsx
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
```

Replace with:

```tsx
          <div className="flex items-center gap-2">
            {(isAdmin || isPreparer) && (
              <Button variant="outline" onClick={() => router.push("/compliance/ad-hoc/create")}>
                <Plus className="h-4 w-4 mr-1" />
                Add Individual
              </Button>
            )}
            {(isAdmin || isPreparer) && (
              <DataImport
                entityName="Compliance"
                columns={IMPORT_COLUMNS}
                uploadEndpoint="/api/compliance/import"
                onComplete={fetchData}
                dropdownTrigger="+ Upload CSV"
              />
            )}
          </div>
```

Key changes:
1. Added a new `Button` with `Plus` icon that links to `/compliance/ad-hoc/create`
2. Changed the `DataImport` dropdown trigger from `"+ Add Ad-hoc Compliances"` to `"+ Upload CSV"` for clarity
3. Ensure `Button` is imported (it should already be — check the existing imports at the top of the file)

- [ ] **Step 3: Verify Button is imported**

Check that `Button` from `@/components/ui/button` is already imported. If not, add it:

```tsx
import { Button } from "@/components/ui/button"
```

Also verify `useRouter` is imported. If not, add:

```tsx
import { useRouter } from "next/navigation"
```

And if `router` is not already defined in the component, add:

```tsx
const router = useRouter()
```

- [ ] **Step 4: Run ESLint to verify no errors**

Run: `npx eslint "src/app/compliance/ad-hoc/page.tsx"`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add src/app/compliance/ad-hoc/page.tsx
git commit -m "feat(compliance): add 'Add Individual' button to ad-hoc list page"
```

---

### Task 3: Manual Verification

- [ ] **Step 1: Start the dev server and verify the page loads**

Run: `npm run dev`

Navigate to `/compliance/ad-hoc` in the browser. Verify:
1. The "+ Add Individual" button appears next to "+ Upload CSV" for admin/preparer users
2. Clicking "+ Add Individual" navigates to `/compliance/ad-hoc/create`
3. The form page renders with all 4 cards (Compliance Details, Payment & Priority, Assignment & Approval, Notes)
4. The Cancel button returns to `/compliance/ad-hoc`

- [ ] **Step 2: Test form submission**

Fill in the form:
1. Select a tax type
2. Select an entity (country should auto-populate)
3. Enter a tax period (e.g. "2026-03")
4. Select a due date
5. Select priority
6. Click "Create Compliance"

Verify:
1. Success toast appears
2. Redirect to `/compliance/ad-hoc` occurs
3. The new compliance appears in the ad-hoc list

- [ ] **Step 3: Test approval flow conditional fields**

1. Select an entity with a ONE_LEVEL approval flow
2. Verify the Reviewer field appears
3. Select an entity with a TWO_LEVEL approval flow
4. Verify both Reviewer and Approver fields appear
5. Select an entity with NONE approval flow
6. Verify neither field appears

- [ ] **Step 4: Test validation**

1. Try submitting with empty fields — verify validation error toast
2. Select multiple entities without choosing a filing entity — verify validation error
3. Select an entity requiring a reviewer but don't choose one — verify validation error
