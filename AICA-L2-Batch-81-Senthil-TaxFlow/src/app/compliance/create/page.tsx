"use client"

import { useState, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import {
  Loader2,
  ArrowLeft,
  Save,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
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
import { Checkbox } from "@/components/ui/checkbox"
import MultiSelect from "@/components/multi-select"
import { toast } from "@/components/ui/toast"
import {
  calcFrequencyFromPeriod,
  calcFilingMonth,
  formatPeriodLabel,
} from "@/lib/utils"
import { TAX_TYPE_OPTIONS } from "@/lib/tax-types"
import {
  APPROVAL_FLOW_OPTIONS,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
  type ApprovalFlow,
} from "@/lib/approval-flow"

interface Entity {
  id: string
  entityName: string
  entityNumber: string
  approvalFlow?: string
  country?: { name: string; code: string }
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

const FREQUENCY_OPTIONS = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "BI_MONTHLY", label: "Bi-Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "HALF_YEARLY", label: "Half-Yearly" },
  { value: "ANNUAL", label: "Annual" },
  { value: "AD_HOC", label: "Ad-Hoc" },
]

const PRIORITY_OPTIONS = [
  { value: "NORMAL", label: "Normal" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
]

export default function CreateCompliancePage() {
  const router = useRouter()
  const { user: sessionUser } = useAuth()

  const [entityIds, setEntityIds] = useState<string[]>([])
  const [taxType, setTaxType] = useState("")
  const [formId, setFormId] = useState("")
  const [taxPeriodStart, setTaxPeriodStart] = useState("")
  const [taxPeriodEnd, setTaxPeriodEnd] = useState("")
  const [frequency, setFrequency] = useState("")
  const [dueDate, setDueDate] = useState("")
  const [paymentDueDate, setPaymentDueDate] = useState("")
  const [requiresPayment, setRequiresPayment] = useState(true)
  const [priority, setPriority] = useState("NORMAL")
  const [approvalFlow, setApprovalFlow] = useState<ApprovalFlow>("ONE_LEVEL")
  const [preparerId, setPreparerId] = useState("")
  const [reviewerId, setReviewerId] = useState("")
  const [approverId, setApproverId] = useState("")
  const [isRecurring, setIsRecurring] = useState(false)
  const [notes, setNotes] = useState("")
  const [filingEntityId, setFilingEntityId] = useState("")
  const [recurringEndDate, setRecurringEndDate] = useState("")

  const filingMonth = useMemo(() => calcFilingMonth(dueDate), [dueDate])
  const taxPeriodLabel = useMemo(
    () => formatPeriodLabel(taxPeriodStart, taxPeriodEnd),
    [taxPeriodStart, taxPeriodEnd]
  )

  // Filing entity: user-chosen, auto-locked to the single selection, or blank.
  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""

  function handleTaxPeriodStartChange(value: string) {
    setTaxPeriodStart(value)
    const next = calcFrequencyFromPeriod(value, taxPeriodEnd)
    if (next) setFrequency(next)
  }

  function handleTaxPeriodEndChange(value: string) {
    setTaxPeriodEnd(value)
    const next = calcFrequencyFromPeriod(taxPeriodStart, value)
    if (next) setFrequency(next)
  }

  const [entities, setEntities] = useState<Entity[]>([])
  const [forms, setForms] = useState<Form[]>([])
  const [preparers, setPreparers] = useState<User[]>([])
  const [reviewers, setReviewers] = useState<User[]>([])
  const [approvers, setApprovers] = useState<User[]>([])

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

  const selectedEntityFlow = useMemo(() => {
    if (!effectiveFilingEntityId) return ""
    return entities.find((e) => e.id === effectiveFilingEntityId)?.approvalFlow || ""
  }, [entities, effectiveFilingEntityId])

  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])

  useEffect(() => {
    if (selectedFormFlow) {
      setApprovalFlow(normalizeApprovalFlow(selectedFormFlow))
    } else if (selectedEntityFlow) {
      setApprovalFlow(normalizeApprovalFlow(selectedEntityFlow))
    }
  }, [selectedFormFlow, selectedEntityFlow])

  // Default the preparer to the current user without a state-sync effect.
  const effectivePreparerId = preparerId || sessionUser?.id || ""

  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch("/api/entities").then((r) => r.json()),
      fetch("/api/users?role=PREPARER").then((r) => r.json()),
      fetch("/api/users?role=REVIEWER").then((r) => r.json()),
      fetch("/api/users?role=APPROVER").then((r) => r.json()),
    ]).then(([e, p, rv, a]) => {
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (entityIds.length === 0 || !taxType || !formId || !taxPeriodStart || !taxPeriodEnd || !dueDate) {
      toast({
        title: "Validation Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      })
      return
    }
    if (!effectivePreparerId) {
      toast({
        title: "Validation Error",
        description: "Please tag a preparer",
        variant: "destructive",
      })
      return
    }
    if (entityIds.length > 1 && !effectiveFilingEntityId) {
      toast({
        title: "Validation Error",
        description: "Please select a filing entity",
        variant: "destructive",
      })
      return
    }
    if (requiresReviewer(approvalFlow) && !reviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (requiresApprover(approvalFlow) && !approverId) {
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
        taxPeriod: taxPeriodLabel || undefined,
        taxPeriodStart,
        taxPeriodEnd,
        frequency: frequency || "AD_HOC",
        dueDate,
        paymentDueDate: requiresPayment ? paymentDueDate || undefined : undefined,
        requiresPayment,
        filingMonth: filingMonth || undefined,
        priority,
        approvalFlow,
        preparerId: effectivePreparerId || undefined,
        reviewerId: requiresReviewer(approvalFlow) ? (reviewerId || undefined) : undefined,
        approverId: requiresApprover(approvalFlow) ? (approverId || undefined) : undefined,
        isRecurring,
        notes: notes || undefined,
        filingEntityId: effectiveFilingEntityId || undefined,
        recurringEndDate: recurringEndDate || undefined,
      }

      const res = await fetch("/api/compliance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.message || "Failed to create compliance")
      }

      toast({ title: "Compliance created successfully" })
      router.push("/compliance")
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

  return (
    <DashboardLayout title="New Compliance">
      <div className="space-y-6 max-w-3xl">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => router.push("/compliance")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-xl font-semibold">New Compliance Schedule</h2>
            <div className="text-sm text-[var(--color-muted-foreground)]">
              ID: <Badge variant="secondary" className="ml-1 font-mono">Auto-generated on save</Badge>
            </div>
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
                  <Select
                    value={taxType}
                    onValueChange={(v) => {
                      setTaxType(v)
                      setForms([])
                      setFormId("")
                      setEntityIds([])
                    }}
                    required
                  >
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
                  <Label htmlFor="form">
                    Form <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formId}
                    onValueChange={(v) => {
                      setFormId(v)
                      setRequiresPayment(forms.find((f) => f.id === v)?.requiresPayment ?? true)
                      setEntityIds([])
                    }}
                    disabled={!taxType}
                    required
                  >
                    <SelectTrigger id="form">
                      <SelectValue placeholder={taxType ? "Select a form" : "Select a tax type first"} />
                    </SelectTrigger>
                    <SelectContent>
                      {forms.map((f) => (
                        <SelectItem key={f.id} value={f.id}>
                          {f.formNumber} – {f.formName}
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
                  onChange={setEntityIds}
                  disabled={!formId}
                  searchable
                  showCountryFilter
                  placeholder={formId ? "Select one or more entities" : "Select a form first"}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Select multiple entities to file a single group return
                </p>
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
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  The entity the group return is filed from. Determines the country.
                </p>
              </div>

              {isRecurring && (
                <div className="space-y-2">
                  <Label htmlFor="recurringEndDate">Recurring End Date</Label>
                  <Input
                    id="recurringEndDate"
                    type="date"
                    value={recurringEndDate}
                    onChange={(e) => setRecurringEndDate(e.target.value)}
                  />
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Generation stops after this date (optional).
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="taxPeriodStart">
                    Tax Period Start <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="taxPeriodStart"
                    type="date"
                    value={taxPeriodStart}
                    onChange={(e) => handleTaxPeriodStartChange(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="taxPeriodEnd">
                    Tax Period End <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="taxPeriodEnd"
                    type="date"
                    value={taxPeriodEnd}
                    min={taxPeriodStart || undefined}
                    onChange={(e) => handleTaxPeriodEndChange(e.target.value)}
                    required
                  />
                </div>
              </div>

              {taxPeriodLabel && (
                <div className="text-xs text-[var(--color-muted-foreground)] -mt-2">
                  Period: <span className="font-medium">{taxPeriodLabel}</span>
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="frequency">Frequency (auto)</Label>
                  <Select value={frequency} onValueChange={setFrequency}>
                    <SelectTrigger id="frequency">
                      <SelectValue placeholder="Auto from period" />
                    </SelectTrigger>
                    <SelectContent>
                      {FREQUENCY_OPTIONS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dueDate">
                    Due Date <span className="text-red-500">*</span>
                  </Label>
                  <Input id="dueDate" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
                </div>

                {requiresPayment && (
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
                  <Label htmlFor="filingMonth">Filing Month (auto)</Label>
                  <Input
                    id="filingMonth"
                    value={filingMonth}
                    placeholder="Auto from due date"
                    readOnly
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
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

                <div className="space-y-2">
                  <Label htmlFor="preparer">
                    Preparer <span className="text-red-500">*</span>
                  </Label>
                  <Select value={effectivePreparerId} onValueChange={setPreparerId} required>
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
              </div>

              <div className="space-y-2">
                <Label htmlFor="approvalFlow">Approval Flow</Label>
                <Select value={approvalFlow} onValueChange={(v) => setApprovalFlow(v as ApprovalFlow)}>
                  <SelectTrigger id="approvalFlow">
                    <SelectValue placeholder="Select approval flow" />
                  </SelectTrigger>
                  <SelectContent>
                    {APPROVAL_FLOW_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {requiresReviewer(approvalFlow) && (
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
                  {reviewerOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No reviewers available</p>
                  )}
                </div>
              )}

              {requiresApprover(approvalFlow) && (
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

              <div className="flex items-center gap-2">
                <Checkbox
                  id="isRecurring"
                  checked={isRecurring}
                  onCheckedChange={(v) => setIsRecurring(v === true)}
                />
                <Label htmlFor="isRecurring" className="cursor-pointer">Is Recurring</Label>
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" placeholder="Optional notes..." value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => router.push("/compliance")}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              <Save className="h-4 w-4 mr-1" />
              Create Compliance
            </Button>
          </div>
          <p className="text-xs text-[var(--color-muted-foreground)] pt-1">
            New compliances are created as drafts and move to pending preparation once approved by an administrator.
          </p>
        </form>
      </div>
    </DashboardLayout>
  )
}
