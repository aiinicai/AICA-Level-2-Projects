"use client"

import { useState, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import { ArrowLeft, Loader2, Send } from "lucide-react"
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
import { useToast } from "@/components/ui/toast"
import { TAX_TYPE_OPTIONS } from "@/lib/tax-types"
import { APPROVAL_FLOW_OPTIONS, normalizeApprovalFlow, requiresApprover, requiresReviewer, type ApprovalFlow } from "@/lib/approval-flow"

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

const FREQUENCY_OPTIONS = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "BI_MONTHLY", label: "Bi-Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "HALF_YEARLY", label: "Half-Yearly" },
  { value: "ANNUAL", label: "Annual" },
]

const PRIORITY_OPTIONS = [
  { value: "NORMAL", label: "Normal" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
]

export default function CreateComplianceTemplatePage() {
  const router = useRouter()
  const { toast } = useToast()
  const { user: sessionUser } = useAuth()

  const [entityIds, setEntityIds] = useState<string[]>([])
  const [filingEntityId, setFilingEntityId] = useState("")
  const [taxType, setTaxType] = useState("")
  const [formId, setFormId] = useState("")
  const [countryId, setCountryId] = useState("")
  const [frequency, setFrequency] = useState("")
  const [dueDaysAfterPeriodEnd, setDueDaysAfterPeriodEnd] = useState("")
  const [periodEndDate, setPeriodEndDate] = useState("")
  const [paymentDueDaysAfterPeriodEnd, setPaymentDueDaysAfterPeriodEnd] = useState("")
  const [selectedFormRequiresPayment, setSelectedFormRequiresPayment] = useState(true)
  const [priority, setPriority] = useState("NORMAL")
  const [preparerId, setPreparerId] = useState("")
  const [approvalFlow, setApprovalFlow] = useState<ApprovalFlow>("ONE_LEVEL")
  const [complianceReviewerId, setComplianceReviewerId] = useState("")
  const [approverId, setApproverId] = useState("")
  const [recurringEndDate, setRecurringEndDate] = useState("")
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

  const effectivePreparerId = preparerId || sessionUser?.id || ""

  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""

  useEffect(() => {
    if (formId) {
      const form = forms.find((f) => f.id === formId)
      if (form?.approvalFlow) {
        setApprovalFlow(normalizeApprovalFlow(form.approvalFlow))
        return
      }
    }
    if (effectiveFilingEntityId) {
      const entity = entities.find((e) => e.id === effectiveFilingEntityId)
      if (entity?.approvalFlow) {
        setApprovalFlow(normalizeApprovalFlow(entity.approvalFlow))
        return
      }
    }
  }, [formId, effectiveFilingEntityId, forms, entities])

  useEffect(() => {
    if (approvalFlow === "NONE") {
      setComplianceReviewerId("")
      setApproverId("")
    } else if (approvalFlow === "ONE_LEVEL") {
      setApproverId("")
    }
  }, [approvalFlow])

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

  function handleTaxTypeChange(value: string) {
    setTaxType(value)
    setForms([])
    setFormId("")
    setSelectedFormRequiresPayment(true)
    setEntityIds([])
    setCountryId("")
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
    if (entityIds.length === 0 || !taxType || !countryId || !frequency) {
      toast({
        title: "Validation Error",
        description: "Please select at least one entity, a tax type, a country, and a frequency",
        variant: "destructive",
      })
      return
    }
    if (entityIds.length > 1 && !filingEntityId) {
      toast({
        title: "Validation Error",
        description: "Please select the filing entity for this group return",
        variant: "destructive",
      })
      return
    }
    if (requiresReviewer(approvalFlow) && !complianceReviewerId) {
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
    if (dueDaysAfterPeriodEnd && (Number(dueDaysAfterPeriodEnd) < 1 || Number(dueDaysAfterPeriodEnd) > 365)) {
      toast({
        title: "Validation Error",
        description: "Days to file must be between 1 and 365",
        variant: "destructive",
      })
      return
    }
    if (paymentDueDaysAfterPeriodEnd && (Number(paymentDueDaysAfterPeriodEnd) < 1 || Number(paymentDueDaysAfterPeriodEnd) > 365)) {
      toast({
        title: "Validation Error",
        description: "Payment due days must be between 1 and 365",
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
        filingEntityId: filingEntityId || undefined,
        frequency,
        dueDaysAfterPeriodEnd: dueDaysAfterPeriodEnd ? Number(dueDaysAfterPeriodEnd) : undefined,
        periodEndDate: periodEndDate || undefined,
        paymentDueDaysAfterPeriodEnd: selectedFormRequiresPayment
          ? (paymentDueDaysAfterPeriodEnd ? Number(paymentDueDaysAfterPeriodEnd) : undefined)
          : undefined,
        priority,
        isRecurring: true,
        recurringEndDate: recurringEndDate || undefined,
        notes: notes || undefined,
        preparerId: effectivePreparerId || undefined,
        approvalFlow,
        complianceReviewerId: requiresReviewer(approvalFlow) ? (complianceReviewerId || undefined) : undefined,
        approverId: requiresApprover(approvalFlow) ? (approverId || undefined) : undefined,
      }

      const res = await fetch("/api/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || err.message || "Failed to create template")
      }

      toast({ title: "Success", description: "Template created and submitted for approval" })
      router.push("/master/compliance-templates")
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
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => router.push("/master/compliance-templates")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-xl font-semibold">Create Recurring Template</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Define a recurring template for repeated compliance schedules. Submits directly for approval.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Template Details</CardTitle>
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
                    if (v) {
                      const form = forms.find((f) => f.id === v)
                      setSelectedFormRequiresPayment(form?.requiresPayment !== false)
                      if (form?.requiresPayment === false) setPaymentDueDaysAfterPeriodEnd("")
                    }
                  }}
                  disabled={!taxType}
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
                onChange={handleEntityChange}
                searchable
                showCountryFilter
                placeholder="Select one or more entities"
              />
              <p className="text-xs text-[var(--color-muted-foreground)]">
                A template must be linked to at least one entity.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="filingEntity">
                Filing Entity {entityIds.length > 1 && <span className="text-red-500">*</span>}
              </Label>
              <Select
                value={filingEntityId}
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
                The entity the group return is filed under. Determines the primary entity on each compliance.
              </p>
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

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="frequency">
                  Frequency <span className="text-red-500">*</span>
                </Label>
                <Select value={frequency} onValueChange={setFrequency} required>
                  <SelectTrigger id="frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    {FREQUENCY_OPTIONS.map((f) => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dueDaysAfterPeriodEnd">Days to File</Label>
                <Input
                  id="dueDaysAfterPeriodEnd"
                  type="number"
                  min={1}
                  max={365}
                  placeholder="e.g. 15"
                  value={dueDaysAfterPeriodEnd}
                  onChange={(e) => setDueDaysAfterPeriodEnd(e.target.value)}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Days available to file after the tax period ends.
                </p>
              </div>

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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="periodEndDate">First Period End Date</Label>
                <Input
                  id="periodEndDate"
                  type="date"
                  value={periodEndDate}
                  onChange={(e) => setPeriodEndDate(e.target.value)}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  End date of the first tax period. Subsequent periods roll forward from here.
                </p>
              </div>

              {selectedFormRequiresPayment && (
              <div className="space-y-2">
                <Label htmlFor="paymentDueDaysAfterPeriodEnd">Payment Due Days</Label>
                <Input
                  id="paymentDueDaysAfterPeriodEnd"
                  type="number"
                  min={1}
                  max={365}
                  placeholder="e.g. 15"
                  value={paymentDueDaysAfterPeriodEnd}
                  onChange={(e) => setPaymentDueDaysAfterPeriodEnd(e.target.value)}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Days to pay after the tax period ends. Defaults to Days to File.
                </p>
              </div>
            )}
            </div>

            <div className="grid grid-cols-2 gap-4">
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
            </div>

            {(requiresReviewer(approvalFlow) || requiresApprover(approvalFlow)) && (
              <div className="grid grid-cols-2 gap-4">
                {requiresReviewer(approvalFlow) && (
                  <div className="space-y-2">
                    <Label htmlFor="complianceReviewer">
                      Reviewer <span className="text-red-500">*</span>
                    </Label>
                    <Select value={complianceReviewerId} onValueChange={setComplianceReviewerId}>
                      <SelectTrigger id="complianceReviewer">
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
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      Reviewers step-1 approvals on generated compliances.
                    </p>
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
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="recurringEndDate">Recurring End Date</Label>
              <Input
                id="recurringEndDate"
                type="date"
                value={recurringEndDate}
                onChange={(e) => setRecurringEndDate(e.target.value)}
              />
              <p className="text-xs text-[var(--color-muted-foreground)]">
                Templates are recurring by default. Generation stops after this date (optional).
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea id="notes" placeholder="Optional notes..." value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => router.push("/master/compliance-templates")}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
            <Send className="h-4 w-4 mr-1" />
            Submit for Approval
          </Button>
        </div>
      </form>
    </div>
  )
}
