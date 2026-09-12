"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { useAuth } from "@/components/layout/providers"
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Flag,
  Globe,
  History,
  Loader2,
  Pencil,
  Power,
  Send,
  Tag,
  User,
  XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useToast } from "@/components/ui/toast"
import {
  formatDate,
  formatDateTime,
  getStatusColor,
  getPriorityColor,
} from "@/lib/utils"
import { taxTypeLabel } from "@/lib/tax-types"
import { APPROVAL_FLOW_OPTIONS } from "@/lib/approval-flow"

interface User {
  id: string
  name: string
  email?: string
}

interface TemplateEntity {
  id: string
  entityId: string
  entity: {
    id: string
    entityName: string
    entityNumber: string
    approvalFlow?: string | null
    country?: { name: string }
  } | null
}

interface TemplateVersion {
  id: string
  version: number
  changedAt: string | null
  changedById: string | null
  changeReason: string | null
  fieldDiffs: Record<string, { old: unknown; new: unknown }> | null
  changedBy: User | null
}

interface GeneratedCompliance {
  id: string
  complianceId: string
  status: string
  filingMonth: string | null
  dueDate: string | null
  createdAt: string | null
}

interface TemplateDetail {
  id: string
  templateNumber: string | null
  version: number
  status: string
  isActive: boolean
  approvalFlow?: string | null
  taxType: string | null
  complianceTypeId: string | null
  complianceType: { id: string; name: string; taxType: string } | null
  formId: string | null
  form: { id: string; formNumber: string; formName: string; approvalFlow?: string | null; requiresPayment?: boolean } | null
  countryId: string | null
  country: { id: string; name: string; code: string } | null
  frequency: string | null
  dueDaysAfterPeriodEnd: number | null
  periodEndDate: string | null
  paymentDueDaysAfterPeriodEnd: number | null
  filingEntityId: string | null
  priority: string | null
  isRecurring: boolean
  recurringEndDate: string | null
  notes: string | null
  preparerId: string | null
  preparer: User | null
  approverId: string | null
  approver: User | null
  complianceReviewerId: string | null
  complianceReviewer: User | null
  createdById: string | null
  createdBy: User | null
  reviewerId: string | null
  reviewer: User | null
  reviewerActionAt: string | null
  reviewerComments: string | null
  adminComments: string | null
  createdAt: string
  updatedAt: string
  submittedAt: string | null
  submittedById: string | null
  adminApprovedAt: string | null
  adminApprovedById: string | null
  approvedAt: string | null
  approvedById: string | null
  rejectedAt: string | null
  rejectedById: string | null
  entities: TemplateEntity[]
  versions: TemplateVersion[]
  generatedCompliances: GeneratedCompliance[]
}

type ActionType =
  | "submit"
  | "adminApprove"
  | "sendToReviewer"
  | "reviewerApprove"
  | "reject"
  | "generate"
  | "activate"

const FREQUENCY_LABELS: Record<string, string> = {
  WEEKLY: "Weekly",
  MONTHLY: "Monthly",
  BI_MONTHLY: "Bi-Monthly",
  QUARTERLY: "Quarterly",
  HALF_YEARLY: "Half-Yearly",
  ANNUAL: "Annual",
  AD_HOC: "Ad-Hoc",
}

function frequencyLabel(frequency: string | null | undefined): string {
  if (!frequency) return "—"
  return FREQUENCY_LABELS[frequency] || frequency.replace(/_/g, " ")
}

function humanizeLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDiffValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "object") return JSON.stringify(value)
  if (typeof value === "boolean") return value ? "Yes" : "No"
  return String(value)
}

function approvalFlowLabel(value: string | null | undefined): string {
  if (!value) return "N/A"
  return APPROVAL_FLOW_OPTIONS.find((o) => o.value === value)?.label || value
}

export default function TemplateDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user: sessionUser, activeRole } = useAuth()
  const { toast } = useToast()

  const id = params?.id as string
  const isAdmin = activeRole === "ADMINISTRATOR"

  const [data, setData] = useState<TemplateDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionDialog, setActionDialog] = useState<{ type: ActionType } | null>(null)
  const [actionComment, setActionComment] = useState("")
  const [reviewerId, setReviewerId] = useState("")
  const [reviewers, setReviewers] = useState<User[]>([])
  const [filingMonth, setFilingMonth] = useState("")
  const [generateResult, setGenerateResult] = useState<{
    created: number
    skipped: number
    futureNotGenerated: number
    overlapSkipped: number
    existingSkipped: number
  } | null>(null)
  const [expandedVersion, setExpandedVersion] = useState<string | null>(null)

  const userId = sessionUser?.id
  const isReviewer = !!data?.reviewerId && data.reviewerId === userId

  const loadTemplate = useCallback(async () => {
    try {
      const res = await fetch(`/api/templates/${id}`)
      if (res.status === 404) {
        setNotFound(true)
        return
      }
      if (!res.ok) throw new Error("Failed to load")
      const json = await res.json()
      setData(json.data || json)
    } catch {
      toast({
        title: "Error",
        description: "Failed to load template details",
        variant: "destructive",
      })
      setNotFound(true)
    } finally {
      setLoading(false)
    }
  }, [id, toast])

  useEffect(() => {
    if (!id) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    loadTemplate()
  }, [id, loadTemplate])

  useEffect(() => {
    if (!isAdmin) return
    fetch("/api/users?role=REVIEWER")
      .then((r) => r.json())
      .then((d) => setReviewers(d.data || d.users || []))
      .catch(() => {})
  }, [isAdmin])

  function openDialog(type: ActionType) {
    setActionComment("")
    setReviewerId(
      type === "adminApprove"
        ? data?.complianceReviewerId || data?.reviewerId || ""
        : type === "sendToReviewer"
          ? data?.complianceReviewerId || data?.reviewerId || ""
          : ""
    )
    setFilingMonth("")
    setGenerateResult(null)
    setActionDialog({ type })
  }

  async function handleAction(action: string) {
    if (!data) return
    setActionLoading(action)
    try {
      const body: Record<string, unknown> = {}
      if (actionComment) body.comments = actionComment

      if (action === "admin-approve") {
        body.reviewerId = data.reviewerId || reviewerId || null
      }
      if (action === "send-to-reviewer") {
        if (!reviewerId) throw new Error("Please select a reviewer")
        body.reviewerId = reviewerId
      }
      if (action === "reject") {
        if (!actionComment.trim()) throw new Error("Please provide a reason for rejection")
      }
      if (action === "generate") {
        if (!filingMonth) throw new Error("Please select a filing month")
        body.filingMonth = filingMonth
      }
      if (action === "activate") {
        body.isActive = !data.isActive
      }

      const res = await fetch(`/api/templates/${data.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || err.message || `Failed to ${action}`)
      }

      const json = await res.json()

      if (action === "generate") {
        const summary = json.data?.summary as
          | { created?: number; skipped?: number; futureNotGenerated?: number; overlapSkipped?: number; existingSkipped?: number }
          | undefined
        setGenerateResult({
          created: summary?.created ?? 0,
          skipped: summary?.skipped ?? 0,
          futureNotGenerated: summary?.futureNotGenerated ?? 0,
          overlapSkipped: summary?.overlapSkipped ?? 0,
          existingSkipped: summary?.existingSkipped ?? 0,
        })
        toast({
          title: "Success",
          description: `Generated ${summary?.created ?? 0} compliance(s) for ${filingMonth}. ${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0) + (summary?.existingSkipped ?? 0)} skipped.`,
        })
      } else {
        toast({
          title: "Success",
          description:
            action === "activate"
              ? data.isActive
                ? "Template deactivated"
                : "Template activated"
              : "Action completed successfully.",
        })
        setActionDialog(null)
        setActionComment("")
        setReviewerId("")
        setFilingMonth("")
        setGenerateResult(null)
      }

      await loadTemplate()
    } catch (err) {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Something went wrong",
        variant: "destructive",
      })
    } finally {
      setActionLoading(null)
    }
  }

  function getActionLabel() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "submit": return "Submit for Approval"
      case "adminApprove": return "Approve Template"
      case "sendToReviewer": return "Send to Reviewer"
      case "reviewerApprove": return "Approve as Reviewer"
      case "reject": return "Reject Template"
      case "generate": return "Generate Compliances for Month"
      case "activate": return data?.isActive ? "Deactivate Template" : "Activate Template"
    }
  }

  function getActionDescription() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "submit": return "Submit this template for admin approval? You can add an optional comment."
      case "adminApprove": return "Approve this template. You can optionally tag a reviewer and add a comment."
      case "sendToReviewer": return "Select a reviewer to review and approve this template on your behalf."
      case "reviewerApprove": return "Approve this template as the assigned reviewer?"
      case "reject": return "Please provide a reason for rejecting this template."
      case "generate": return "Generate compliance schedules from this template for the selected filing month."
      case "activate": return data?.isActive
        ? "Deactivating this template prevents generating new compliances from it."
        : "Activating this template allows generating new compliances from it."
    }
  }

  function getActionApiEndpoint() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "submit": return "submit"
      case "adminApprove": return "admin-approve"
      case "sendToReviewer": return "send-to-reviewer"
      case "reviewerApprove": return "reviewer-approve"
      case "reject": return "reject"
      case "generate": return "generate"
      case "activate": return "activate"
    }
  }

  function getConfirmLabel() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "generate": return "Generate"
      case "activate": return data?.isActive ? "Deactivate" : "Activate"
      default: return getActionLabel()
    }
  }

  function renderActionButtons() {
    if (!data) return null
    const buttons: React.ReactNode[] = []
    const status = data.status

    if (status === "DRAFT") {
      buttons.push(
        <Button key="submit" onClick={() => openDialog("submit")}>
          <Send className="h-4 w-4 mr-1" />
          Submit for Approval
        </Button>
      )
    }

    if (status === "PENDING_ADMIN_APPROVAL" && isAdmin) {
      buttons.push(
        <Button key="adminApprove" onClick={() => openDialog("adminApprove")}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>,
        <Button key="sendToReviewer" variant="outline" onClick={() => openDialog("sendToReviewer")}>
          <Send className="h-4 w-4 mr-1" />
          Send to Reviewer
        </Button>,
        <Button key="reject" variant="destructive" onClick={() => openDialog("reject")}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "PENDING_REVIEW" && isReviewer) {
      buttons.push(
        <Button key="reviewerApprove" onClick={() => openDialog("reviewerApprove")}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>,
        <Button key="reject" variant="destructive" onClick={() => openDialog("reject")}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "APPROVED" && isAdmin) {
      if (data.isActive) {
        buttons.push(
          <Button key="generate" onClick={() => openDialog("generate")}>
            <CalendarDays className="h-4 w-4 mr-1" />
            Generate for Month
          </Button>
        )
      }
      buttons.push(
        <Button key="activate" variant="outline" onClick={() => openDialog("activate")}>
          <Power className="h-4 w-4 mr-1" />
          {data.isActive ? "Deactivate" : "Activate"}
        </Button>
      )
    }

    return buttons.length > 0 ? (
      <div className="flex items-center gap-2 flex-wrap">{buttons}</div>
    ) : null
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  if (notFound || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
        <h2 className="text-xl font-semibold mb-1">Template Not Found</h2>
        <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
          The recurring template you&apos;re looking for doesn&apos;t exist or has been deleted.
        </p>
        <Button onClick={() => router.push("/master/compliance-templates")}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Recurring Templates
        </Button>
      </div>
    )
  }

  const endpoint = getActionApiEndpoint()

  const primaryEntity =
    (data.filingEntityId
      ? data.entities?.find((en) => en.entityId === data.filingEntityId)?.entity
      : null) || data.entities?.[0]?.entity
  const entityApprovalFlow = primaryEntity?.approvalFlow
  const formApprovalFlow = data.form?.approvalFlow
  const activeFlow = data.approvalFlow
  const hasMismatch = Boolean(
    (entityApprovalFlow && activeFlow !== entityApprovalFlow) ||
    (formApprovalFlow && activeFlow !== formApprovalFlow)
  )

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/master/compliance-templates")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-semibold">{data.templateNumber || "Recurring Template"}</h2>
              {data.version > 0 && (
                <Badge variant="secondary" className="font-mono">v{data.version}</Badge>
              )}
              <Badge className={getStatusColor(data.status)}>
                {data.status.replace(/_/g, " ")}
              </Badge>
              {data.status === "APPROVED" && (
                <Badge className={data.isActive ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}>
                  {data.isActive ? "Active" : "Inactive"}
                </Badge>
              )}
            </div>
            <p className="text-sm text-[var(--color-muted-foreground)] mt-0.5">
              Created {formatDateTime(data.createdAt)}
              {data.createdBy?.name ? ` by ${data.createdBy.name}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {renderActionButtons()}
          {(data.status === "DRAFT" || isAdmin) && (
            <Button variant="outline" onClick={() => router.push(`/master/compliance-templates/${data.id}/edit`)}>
              <Pencil className="h-4 w-4 mr-1" />
              Edit
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">
              {(data.entities?.length ?? 0) > 1 ? "Entities" : "Entity"}
            </CardTitle>
            <Building2 className="h-4 w-4 text-[var(--color-muted-foreground)]" />
          </CardHeader>
          <CardContent className="space-y-2">
            {data.entities && data.entities.length > 0 ? (
              data.entities.map((en) => (
                <div key={en.id}>
                  <p className="font-medium">{en.entity?.entityName || "—"}</p>
                  {en.entity?.entityNumber && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      {en.entity.entityNumber}
                    </p>
                  )}
                  {en.entity?.country?.name && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      <Globe className="h-3 w-3 inline mr-1" />
                      {en.entity.country.name}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">No entities</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Template Info</CardTitle>
            <Tag className="h-4 w-4 text-[var(--color-muted-foreground)]" />
          </CardHeader>
          <CardContent>
            <p className="font-medium">{taxTypeLabel(data.taxType)}</p>
            {data.form && (
              <p className="text-xs text-[var(--color-muted-foreground)]">
                Form: {data.form.formNumber}
                {data.form.formName ? ` – ${data.form.formName}` : ""}
              </p>
            )}
            <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
              {data.country?.name || "—"} | {frequencyLabel(data.frequency)}
            </p>
            {data.dueDaysAfterPeriodEnd != null && (
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                Due: {data.dueDaysAfterPeriodEnd} day(s) after period end
              </p>
            )}
            {data.form?.requiresPayment === false ? (
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                No payment required
              </p>
            ) : (
              data.paymentDueDaysAfterPeriodEnd != null && data.paymentDueDaysAfterPeriodEnd !== data.dueDaysAfterPeriodEnd && (
                <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                  Payment due: {data.paymentDueDaysAfterPeriodEnd} day(s) after period end
                </p>
              )
            )}
            {data.periodEndDate && (
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                First period ends {formatDate(data.periodEndDate)}
              </p>
            )}
            {data.priority && (
              <Badge className={`mt-2 ${getPriorityColor(data.priority)}`}>
                <Flag className="h-3 w-3 mr-1" />
                {data.priority}
              </Badge>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Preparer</CardTitle>
            <User className="h-4 w-4 text-[var(--color-muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {data.preparer ? (
              <>
                <p className="font-medium">{data.preparer.name}</p>
                {data.preparer.email && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    {data.preparer.email}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">Not assigned</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Approver</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-[var(--color-muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {data.approver ? (
              <>
                <p className="font-medium">{data.approver.name}</p>
                {data.approver.email && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    {data.approver.email}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">Not assigned</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">Reviewer</CardTitle>
            <User className="h-4 w-4 text-[var(--color-muted-foreground)]" />
          </CardHeader>
          <CardContent>
            {data.complianceReviewer ? (
              <>
                <p className="font-medium">{data.complianceReviewer.name}</p>
                {data.complianceReviewer.email && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    {data.complianceReviewer.email}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">Not assigned</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">
            <FileText className="h-4 w-4 mr-1" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="versions">
            <History className="h-4 w-4 mr-1" />
            Versions
            {(data.versions?.length ?? 0) > 0 && (
              <span className="ml-1 text-xs bg-[var(--color-primary)] text-[var(--color-primary-foreground)] rounded-full px-1.5">
                {data.versions.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="generated">
            <CalendarDays className="h-4 w-4 mr-1" />
            Generated Compliances
            {(data.generatedCompliances?.length ?? 0) > 0 && (
              <span className="ml-1 text-xs bg-[var(--color-primary)] text-[var(--color-primary-foreground)] rounded-full px-1.5">
                {data.generatedCompliances.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 pt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle className="text-base font-semibold">Approval Flow Mechanism</CardTitle>
                {hasMismatch && (
                  <Badge variant="outline" className="border-amber-500 text-amber-700 bg-amber-50 dark:bg-amber-950/40 dark:text-amber-300">
                    <AlertTriangle className="h-3 w-3 mr-1 text-amber-500" />
                    Flow Override Active
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="rounded-lg border border-[var(--color-border)] p-3 bg-[var(--color-muted)]/20">
                  <Label className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider block mb-1">
                    1. Entity Master Flow (Placeholder)
                  </Label>
                  <p className="font-medium text-sm">
                    {approvalFlowLabel(entityApprovalFlow)}
                  </p>
                </div>

                <div className="rounded-lg border border-[var(--color-border)] p-3 bg-[var(--color-muted)]/20">
                  <Label className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider block mb-1">
                    2. Form Master Flow (Placeholder)
                  </Label>
                  <p className="font-medium text-sm">
                    {data.form ? approvalFlowLabel(data.form.approvalFlow) : "N/A"}
                  </p>
                </div>

                <div className="rounded-lg border-2 border-[var(--color-primary)]/50 p-3 bg-[var(--color-primary)]/5">
                  <Label className="text-xs text-[var(--color-primary)] font-semibold uppercase tracking-wider block mb-1">
                    3. Active Template Flow (Driving Flow)
                  </Label>
                  <p className="font-semibold text-sm">
                    {approvalFlowLabel(data.approvalFlow)}
                  </p>
                </div>
              </div>

              {hasMismatch && (
                <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2.5 text-xs text-amber-800 dark:text-amber-200">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                  <span>
                    The active template flow ({approvalFlowLabel(data.approvalFlow)}) overrides the entity/form master placeholder settings.
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Template Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Template Number</Label>
                  <p className="font-medium">{data.templateNumber || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Version</Label>
                  <p className="font-medium">{data.version > 0 ? `v${data.version}` : "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Status</Label>
                  <Badge className={getStatusColor(data.status)}>
                    {data.status.replace(/_/g, " ")}
                  </Badge>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Entities</Label>
                  <p className="font-medium">
                    {data.entities?.length
                      ? data.entities.map((en) => en.entity?.entityName).filter(Boolean).join(", ")
                      : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Filing Entity</Label>
                  <p className="font-medium">
                    {data.filingEntityId
                      ? data.entities?.find((en) => en.entityId === data.filingEntityId)?.entity?.entityName || "—"
                      : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Tax Type</Label>
                  <p className="font-medium">{taxTypeLabel(data.taxType)}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Compliance Type</Label>
                  <p className="font-medium">{data.complianceType?.name || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Form</Label>
                  <p className="font-medium">
                    {data.form
                      ? `${data.form.formNumber}${data.form.formName ? ` – ${data.form.formName}` : ""}`
                      : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Country</Label>
                  <p className="font-medium">
                    {data.country ? `${data.country.name} (${data.country.code})` : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Frequency</Label>
                  <p className="font-medium">{frequencyLabel(data.frequency)}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Days to File</Label>
                  <p className="font-medium">
                    {data.dueDaysAfterPeriodEnd != null ? `${data.dueDaysAfterPeriodEnd} day(s) after period end` : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Payment Due Days</Label>
                  <p className="font-medium">
                    {data.form?.requiresPayment === false
                      ? "-"
                      : data.paymentDueDaysAfterPeriodEnd != null
                        ? `${data.paymentDueDaysAfterPeriodEnd} day(s) after period end`
                        : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">First Period End</Label>
                  <p className="font-medium">
                    {data.periodEndDate ? formatDate(data.periodEndDate) : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Priority</Label>
                  <Badge className={getPriorityColor(data.priority || "NORMAL")}>
                    {data.priority || "—"}
                  </Badge>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Active</Label>
                  <p className="font-medium">{data.isActive ? "Yes" : "No"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Recurring</Label>
                  <p className="font-medium">{data.isRecurring ? "Yes" : "No"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Recurring End Date</Label>
                  <p className="font-medium">
                    {data.recurringEndDate ? formatDate(data.recurringEndDate) : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Preparer</Label>
                  <p className="font-medium">{data.preparer?.name || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Approver</Label>
                  <p className="font-medium">{data.approver?.name || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Reviewer</Label>
                  <p className="font-medium">{data.complianceReviewer?.name || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Created By</Label>
                  <p className="font-medium">{data.createdBy?.name || "—"}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Created</Label>
                  <p className="font-medium">{formatDateTime(data.createdAt)}</p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Last Updated</Label>
                  <p className="font-medium">{formatDateTime(data.updatedAt)}</p>
                </div>
                {data.submittedAt && (
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Submitted</Label>
                    <p className="font-medium">{formatDateTime(data.submittedAt)}</p>
                  </div>
                )}
                {data.adminApprovedAt && (
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Admin Approved</Label>
                    <p className="font-medium">{formatDateTime(data.adminApprovedAt)}</p>
                  </div>
                )}
                {data.reviewer && (
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Reviewer</Label>
                    <p className="font-medium">{data.reviewer.name}</p>
                    {data.reviewerActionAt && (
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        Reviewed {formatDateTime(data.reviewerActionAt)}
                      </p>
                    )}
                  </div>
                )}
                {data.approvedAt && (
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Approved</Label>
                    <p className="font-medium">{formatDateTime(data.approvedAt)}</p>
                  </div>
                )}
                {data.rejectedAt && (
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Rejected</Label>
                    <p className="font-medium">{formatDateTime(data.rejectedAt)}</p>
                  </div>
                )}
              </div>
              {data.adminComments && (
                <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                  <Label className="text-[var(--color-muted-foreground)]">Admin Comments</Label>
                  <p className="text-sm mt-1 whitespace-pre-wrap">{data.adminComments}</p>
                </div>
              )}
              {data.reviewerComments && (
                <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                  <Label className="text-[var(--color-muted-foreground)]">Reviewer Comments</Label>
                  <p className="text-sm mt-1 whitespace-pre-wrap">{data.reviewerComments}</p>
                </div>
              )}
              {data.notes && (
                <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                  <Label className="text-[var(--color-muted-foreground)]">Notes</Label>
                  <p className="text-sm mt-1 whitespace-pre-wrap">{data.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="versions" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Template Versions</CardTitle>
            </CardHeader>
            <CardContent>
              {data.versions && data.versions.length > 0 ? (
                <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Version</TableHead>
                        <TableHead>Changed By</TableHead>
                        <TableHead>Changed At</TableHead>
                        <TableHead>Change Reason</TableHead>
                        <TableHead className="w-[90px]">Field Diffs</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.versions.map((v) => {
                        const diffs = v.fieldDiffs
                        const diffKeys = diffs ? Object.keys(diffs) : []
                        const expanded = expandedVersion === v.id
                        return (
                          <FragmentRow
                            key={v.id}
                            expanded={expanded}
                            colSpan={5}
                            diffKeys={diffKeys}
                            diffs={diffs}
                            row={
                              <>
                                <TableCell className="font-medium">v{v.version}</TableCell>
                                <TableCell>{v.changedBy?.name || "—"}</TableCell>
                                <TableCell className="whitespace-nowrap">
                                  {v.changedAt ? formatDateTime(v.changedAt) : "—"}
                                </TableCell>
                                <TableCell className="max-w-[240px] truncate">
                                  {v.changeReason || "—"}
                                </TableCell>
                                <TableCell>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={diffKeys.length === 0}
                                    onClick={() => setExpandedVersion(expanded ? null : v.id)}
                                  >
                                    {expanded ? (
                                      <ChevronDown className="h-4 w-4" />
                                    ) : (
                                      <ChevronRight className="h-4 w-4" />
                                    )}
                                    {diffKeys.length > 0 ? `${diffKeys.length}` : "None"}
                                  </Button>
                                </TableCell>
                              </>
                            }
                          />
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <History className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                  <p className="text-sm text-[var(--color-muted-foreground)]">No versions recorded yet.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="generated" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Generated Compliances</CardTitle>
            </CardHeader>
            <CardContent>
              {data.generatedCompliances && data.generatedCompliances.length > 0 ? (
                <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Compliance ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Filing Month</TableHead>
                        <TableHead>Due Date</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.generatedCompliances.map((c) => (
                        <TableRow key={c.id}>
                          <TableCell>
                            <Link
                              href={`/compliance/${c.id}`}
                              className="font-medium text-[var(--color-primary)] hover:underline"
                            >
                              {c.complianceId}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(c.status)}>
                              {c.status.replace(/_/g, " ")}
                            </Badge>
                          </TableCell>
                          <TableCell>{c.filingMonth || "—"}</TableCell>
                          <TableCell>{c.dueDate ? formatDate(c.dueDate) : "—"}</TableCell>
                          <TableCell>{c.createdAt ? formatDate(c.createdAt) : "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <CalendarDays className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                  <p className="text-sm text-[var(--color-muted-foreground)]">
                    No compliances have been generated from this template yet.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog
        open={!!actionDialog}
        onOpenChange={(o) => {
          if (!o) {
            setActionDialog(null)
            setActionComment("")
            setReviewerId("")
            setFilingMonth("")
            setGenerateResult(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{getActionLabel()}</DialogTitle>
            <DialogDescription>{getActionDescription()}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {(actionDialog?.type === "adminApprove" || actionDialog?.type === "sendToReviewer") && (
              <div className="space-y-4">
                {actionDialog?.type === "adminApprove" && data?.complianceReviewerId ? (
                  <>
                    <div className="space-y-1">
                      <Label htmlFor="reviewer">Reviewer (already assigned)</Label>
                      <Input
                        id="reviewer"
                        value={data.complianceReviewer?.name || "Assigned"}
                        disabled
                      />
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        Reviewer was already selected. No need to select again.
                      </p>
                    </div>
                    {data?.approverId && (
                      <div className="space-y-1">
                        <Label htmlFor="approver">Approver (already assigned)</Label>
                        <Input
                          id="approver"
                          value={data.approver?.name || "Assigned"}
                          disabled
                        />
                        <p className="text-xs text-[var(--color-muted-foreground)]">
                          Approver was already selected. No need to select again.
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <Label htmlFor="reviewer">
                      Reviewer {actionDialog?.type === "sendToReviewer" && <span className="text-red-500">*</span>}
                    </Label>
                    <Select value={reviewerId} onValueChange={setReviewerId}>
                      <SelectTrigger id="reviewer">
                        <SelectValue
                          placeholder={
                            actionDialog?.type === "adminApprove"
                              ? "Select reviewer (optional)"
                              : "Select reviewer"
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {reviewers
                          .filter((r) => r.id !== userId || r.id === reviewerId)
                          .map((r) => (
                            <SelectItem key={r.id} value={r.id}>
                              {r.name} ({r.email})
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </>
                )}
              </div>
            )}

            {actionDialog?.type === "generate" && (
              <div className="space-y-2">
                <Label htmlFor="filingMonth">
                  Filing Month <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="filingMonth"
                  type="month"
                  value={filingMonth}
                  onChange={(e) => setFilingMonth(e.target.value)}
                />
                {generateResult && (
                  <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm">
                    <p className="font-medium mb-1">Generation summary</p>
                    <p>{generateResult.created} compliance(s) created for the selected filing month</p>
                    {generateResult.futureNotGenerated > 0 && (
                      <p>{generateResult.futureNotGenerated} will be generated when the next period becomes due</p>
                    )}
                    {generateResult.overlapSkipped > 0 && (
                      <p>{generateResult.overlapSkipped} skipped (period overlaps an existing compliance)</p>
                    )}
                    {generateResult.existingSkipped > 0 && (
                      <p>A compliance already exists for the selected filing month</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {actionDialog?.type === "activate" && (
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Are you sure you want to {data?.isActive ? "deactivate" : "activate"} template{" "}
                <strong>{data?.templateNumber || ""}</strong>?
              </p>
            )}

            {actionDialog?.type !== "activate" && actionDialog?.type !== "generate" && (
              <>
                <Label htmlFor="actionComment">
                  {actionDialog?.type === "reject" ? "Reason (required)" : "Comment (optional)"}
                </Label>
                <Textarea
                  id="actionComment"
                  placeholder={
                    actionDialog?.type === "reject"
                      ? "Please provide a reason for rejection..."
                      : "Add a comment..."
                  }
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  rows={3}
                />
                {actionDialog?.type === "reject" && !actionComment.trim() && (
                  <p className="text-xs text-red-500">A reason is required for rejection.</p>
                )}
              </>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setActionDialog(null)
                setActionComment("")
                setReviewerId("")
                setFilingMonth("")
                setGenerateResult(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant={actionDialog?.type === "reject" ? "destructive" : "default"}
              disabled={
                actionLoading === endpoint ||
                (actionDialog?.type === "reject" && !actionComment.trim()) ||
                (actionDialog?.type === "sendToReviewer" && !reviewerId) ||
                (actionDialog?.type === "generate" && !filingMonth)
              }
              onClick={() => handleAction(endpoint)}
            >
              {actionLoading === endpoint && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              {getConfirmLabel()}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function FragmentRow({
  row,
  expanded,
  colSpan,
  diffKeys,
  diffs,
}: {
  row: React.ReactNode
  expanded: boolean
  colSpan: number
  diffKeys: string[]
  diffs: Record<string, { old: unknown; new: unknown }> | null
}) {
  return (
    <>
      <TableRow>{row}</TableRow>
      {expanded && diffKeys.length > 0 && diffs && (
        <TableRow>
          <TableCell colSpan={colSpan}>
            <div className="rounded-md border border-[var(--color-border)] overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/3">Field</TableHead>
                    <TableHead className="w-1/3">Old</TableHead>
                    <TableHead>New</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {diffKeys.map((key) => {
                    const diff = diffs[key]
                    return (
                      <TableRow key={key}>
                        <TableCell className="font-medium">{humanizeLabel(key)}</TableCell>
                        <TableCell className="text-[var(--color-muted-foreground)] break-all">
                          {formatDiffValue(diff?.old)}
                        </TableCell>
                        <TableCell className="font-medium break-all">
                          {formatDiffValue(diff?.new)}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  )
}
