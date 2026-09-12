"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import {
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Download,
  Upload,
  Send,
  Loader2,
  Building2,
  Globe,
  User,
  Tag,
  Flag,
  MessageSquare,
  Activity,
  History,
  ArrowLeft,
  Pencil,
  Check,
} from "lucide-react"
import {
  validatePaymentSubmission,
  FILING_TYPE_LABELS,
  REFUND_TYPE_LABELS,
  CONFIRMATION_STAGE_LABELS,
} from "@/lib/payment"
import { Checkbox } from "@/components/ui/checkbox"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
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
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { toast } from "@/components/ui/toast"
import {
  formatDate,
  formatDateTime,
  daysUntil,
  getStatusColor,
  getPriorityColor,
  cn,
} from "@/lib/utils"
import { taxTypeLabel } from "@/lib/tax-types"
import { APPROVAL_FLOW_OPTIONS } from "@/lib/approval-flow"

interface User {
  id: string
  name: string
  email?: string
  image?: string | null
}

interface Assignment {
  id: string
  preparer: User
  startedAt: string | null
  completedAt: string | null
}

interface Approval {
  id: string
  approver: User
  status: string
  step?: number
  comments: string | null
  actionAt: string | null
}

interface Attachment {
  id: string
  originalName: string
  fileType: string
  fileSize: number
  version: number
  stage?: string | null
  createdAt: string
  uploadedBy?: User
}

interface Comment {
  id: string
  content: string
  user: User
  createdAt: string
}

interface ActivityEntry {
  id: string
  action: string
  fromStatus: string | null
  toStatus: string | null
  user: User
  comments: string | null
  createdAt: string
}

interface ComplianceDetail {
  id: string
  complianceId: string
  approvalFlow?: string | null
  entity: { id: string; entityName: string; entityNumber: string; currency?: string | null; approvalFlow?: string | null; country?: { name: string } } | null
  entities: { id: string; entityId: string; entity: { id: string; entityName: string; entityNumber: string; currency?: string | null; approvalFlow?: string | null; country?: { name: string } } }[]
  country: { id: string; name: string; code: string }
  taxType: string | null
  form: { id: string; formNumber: string; formName: string; approvalFlow?: string | null } | null
  taxPeriod: string
  taxPeriodStart: string | null
  taxPeriodEnd: string | null
  filingMonth: string | null
  frequency: string
  dueDate: string
  paymentDueDate: string | null
  requiresPayment: boolean
  priority: string
  status: string
  source?: string
  isRecurring: boolean
  recurringEndDate: string | null
  notes: string | null
  submittedAt: string | null
  filedAt: string | null
  createdById: string | null
  createdBy?: User | null
  reviewerId: string | null
  reviewer?: User | null
  reviewerActionAt: string | null
  reviewerComments: string | null
  adminActionAt: string | null
  adminComments: string | null
  paidAt: string | null
  paymentDate: string | null
  paymentAmount: number | null
  paymentReference: string | null
  paymentMethod: string | null
  refundAmount: number | null
  refundReference: string | null
  paymentNotes: string | null
  filingType?: string | null
  refundType?: string | null
  paymentCurrency?: string | null
  confirmations?: {
    id: string
    stage: string
    confirmedAt: string
    confirmedBy: User
  }[]
  assignments: Assignment[]
  approvals: Approval[]
  attachments: Attachment[]
  comments: Comment[]
  activities: ActivityEntry[]
  createdAt: string
  updatedAt: string
}

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  created: Calendar,
  submitted: Send,
  submitted_to_admin: Send,
  admin_approved: CheckCircle2,
  sent_to_reviewer: Send,
  reviewer_approved: CheckCircle2,
  approved: CheckCircle2,
  rejected: XCircle,
  filed: FileText,
  marked_paid: CheckCircle2,
}

const ACTIVITY_COLORS: Record<string, string> = {
  created: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
  submitted: "text-purple-600 bg-purple-100 dark:bg-purple-900/30",
  submitted_to_admin: "text-purple-600 bg-purple-100 dark:bg-purple-900/30",
  admin_approved: "text-green-600 bg-green-100 dark:bg-green-900/30",
  sent_to_reviewer: "text-cyan-600 bg-cyan-100 dark:bg-cyan-900/30",
  reviewer_approved: "text-green-600 bg-green-100 dark:bg-green-900/30",
  approved: "text-green-600 bg-green-100 dark:bg-green-900/30",
  rejected: "text-red-600 bg-red-100 dark:bg-red-900/30",
  filed: "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30",
  marked_paid: "text-teal-600 bg-teal-100 dark:bg-teal-900/30",
}

function getActivityIcon(action: string) {
  return ACTIVITY_ICONS[action.toLowerCase()] || Activity
}

function getActivityColor(action: string) {
  return ACTIVITY_COLORS[action.toLowerCase()] || "text-gray-600 bg-gray-100 dark:bg-gray-900/30"
}

function getInitials(name: string | null | undefined): string {
  if (!name) return "U"
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
}

function approvalFlowLabel(value: string | null | undefined): string {
  if (!value) return "N/A"
  return APPROVAL_FLOW_OPTIONS.find((o) => o.value === value)?.label || value
}

export default function ComplianceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user: sessionUser, activeRole } = useAuth()
  const role = sessionUser?.role
  const userId = sessionUser?.id
  const id = params?.id as string

  const isAdminActive = activeRole === "ADMINISTRATOR" || role === "ADMINISTRATOR"
  const isManagerActive = activeRole === "MANAGER" || role === "MANAGER"

  const [data, setData] = useState<ComplianceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionDialog, setActionDialog] = useState<{
    type: "approve" | "reject" | "submit" | "resubmit" | "file" | "submitToAdmin" | "adminApprove" | "sendToReviewer" | "reviewerApprove" | "markPaid" | "close"
  } | null>(null)
  const [actionComment, setActionComment] = useState("")
  const [reviewerId, setReviewerId] = useState("")
  const [reviewers, setReviewers] = useState<User[]>([])
  const [paymentForm, setPaymentForm] = useState({
    paymentDate: "",
    paymentAmount: "",
    paymentReference: "",
    paymentMethod: "",
    refundAmount: "",
    refundReference: "",
    paymentNotes: "",
    filingType: "PAYMENT",
    refundType: "",
    paymentCurrency: "",
    confirmAmount: false,
    confirmPayment: false,
    filedDate: "",
  })
  const [currencies, setCurrencies] = useState<string[]>([])

  function resetPaymentForm() {
    setPaymentForm({
      paymentDate: "",
      paymentAmount: "",
      paymentReference: "",
      paymentMethod: "",
      refundAmount: "",
      refundReference: "",
      paymentNotes: "",
      filingType: "PAYMENT",
      refundType: "",
      paymentCurrency: "",
      confirmAmount: false,
      confirmPayment: false,
      filedDate: "",
    })
  }

  const [newComment, setNewComment] = useState("")
  const [commentSubmitting, setCommentSubmitting] = useState(false)

  const [uploadLoading, setUploadLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!id) return
    fetch(`/api/compliance/${id}`)
      .then((r) => {
        if (r.status === 404) { setNotFound(true); return null }
        if (!r.ok) throw new Error("Failed to load")
        return r.json()
      })
      .then((d) => {
        if (!d) return
        setData(d.data || d)
      })
      .catch(() => {
        toast({ title: "Error", description: "Failed to load compliance details", variant: "destructive" })
        setNotFound(true)
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    fetch("/api/exchange-rates?limit=500")
      .then((r) => r.json())
      .then((json) => {
        const unique = [...new Set<string>((json.data || []).map((r: { fromCurrency: string }) => r.fromCurrency))].sort()
        setCurrencies(unique)
      })
      .catch(() => {})
  }, [])

  function isPreparer() {
    return role === "PREPARER" || data?.assignments?.some((a) => a.preparer.id === userId)
  }

  function isApprover() {
    return role === "APPROVER" || data?.approvals?.some((a) => a.approver.id === userId)
  }

  // True when the user holds a pending approval record at the current step
  // (i.e. all lower approval steps are already approved).
  function canApproveAtCurrentStep() {
    if (!data?.approvals || data.approvals.length === 0) return false
    const myPending = data.approvals.filter(
      (a) => a.approver.id === userId && a.status !== "APPROVED"
    )
    if (myPending.length === 0) return false
    return myPending.some((a) => {
      const step = a.step || 1
      const priorSteps = data.approvals.filter((p) => (p.step || 1) < step)
      return priorSteps.every((p) => p.status === "APPROVED")
    })
  }

  function isAdminOrManager() {
    return isAdminActive || isManagerActive
  }

  function isReviewer() {
    return !!data?.reviewerId && data.reviewerId === userId
  }

  const existingStep1Approver = data?.approvals?.find((a) => (a.step || 1) === 1)
  const existingStep2Approver = data?.approvals?.find((a) => a.step === 2)

  // Load potential reviewers (org members) for admin actions
  useEffect(() => {
    if (!isAdminActive) return
    fetch("/api/users")
      .then((r) => r.json())
      .then((d) => setReviewers(d.data || d.users || []))
      .catch(() => {})
  }, [isAdminActive])

  async function handleAction(action: string) {
    if (!data) return
    setActionLoading(action)
    try {
      const body: Record<string, unknown> = {}
      if (actionComment) body.comments = actionComment

      if (action === "approve" || action === "reject") {
        body.approverId = userId
      }
      if (action === "approve") {
        body.confirmAmount = paymentForm.confirmAmount
      }
      if (action === "submit" || action === "resubmit") {
        if (data.requiresPayment !== false) {
          const resolvedCurrency = paymentForm.paymentCurrency || data?.entity?.currency || "USD"
          const resolvedAmount = paymentForm.filingType === "NIL_RETURN" ? "0" : paymentForm.paymentAmount
          body.filingType = paymentForm.filingType
          body.refundType = paymentForm.filingType === "REFUND_RETURN" ? paymentForm.refundType : null
          body.paymentCurrency = resolvedCurrency
          body.paymentAmount = resolvedAmount
        }
      }
      if (action === "admin-approve") {
        body.reviewerId = data.reviewerId || existingStep1Approver?.approver?.id || reviewerId || null
      }
      if (action === "send-to-reviewer") {
        if (!reviewerId) throw new Error("Please select a reviewer")
        body.reviewerId = reviewerId
      }
      if (action === "mark-paid") {
        if (paymentForm.paymentDate) body.paymentDate = paymentForm.paymentDate
        if (paymentForm.paymentReference) body.paymentReference = paymentForm.paymentReference
        if (paymentForm.paymentMethod) body.paymentMethod = paymentForm.paymentMethod
        if (paymentForm.paymentNotes) body.paymentNotes = paymentForm.paymentNotes
        body.confirmPayment = paymentForm.confirmPayment
      }
      if (action === "file") {
        if (paymentForm.filedDate) body.filedDate = paymentForm.filedDate
      }

      const res = await fetch(`/api/compliance/${data.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || err.message || `Failed to ${action}`)
      }

      const updated = await res.json()
      setData(updated.data || updated)
      toast({
        title: "Success",
        description: "Action completed successfully.",
      })
      setActionDialog(null)
      setActionComment("")
      setReviewerId("")
      resetPaymentForm()
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

  async function handleAddComment() {
    if (!data || !newComment.trim()) return
    setCommentSubmitting(true)
    try {
      const res = await fetch("/api/comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ complianceId: data.id, content: newComment.trim() }),
      })
      if (!res.ok) throw new Error("Failed to add comment")
      const result = await res.json()
      setData((prev) =>
        prev ? { ...prev, comments: [...prev.comments, result.data || result] } : prev
      )
      setNewComment("")
      toast({ title: "Comment added" })
    } catch {
      toast({ title: "Error", description: "Failed to add comment", variant: "destructive" })
    } finally {
      setCommentSubmitting(false)
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !data) return
    setUploadLoading(true)
    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("complianceId", data.id)

      const res = await fetch("/api/attachments", {
        method: "POST",
        body: formData,
      })
      if (!res.ok) throw new Error("Upload failed")
      const result = await res.json()
      setData((prev) =>
        prev ? { ...prev, attachments: [...prev.attachments, result.data || result] } : prev
      )
      toast({ title: "File uploaded" })
    } catch {
      toast({ title: "Error", description: "Failed to upload file", variant: "destructive" })
    } finally {
      setUploadLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  function renderActionButtons() {
    if (!data) return null
    const buttons: React.ReactNode[] = []
    const status = data.status

    // DRAFT: non-admin creator submits to admin; admin approves directly or sends to reviewer.
    // Template-sourced compliances are approved through the template, not directly.
    if (status === "DRAFT" && data.source !== "TEMPLATE") {
      if (isAdminActive) {
        buttons.push(
          <Button key="adminApprove" onClick={() => setActionDialog({ type: "adminApprove" })}>
            <CheckCircle2 className="h-4 w-4 mr-1" />
            Approve
          </Button>
        )
        buttons.push(
          <Button key="sendToReviewer" variant="outline" onClick={() => setActionDialog({ type: "sendToReviewer" })}>
            <Send className="h-4 w-4 mr-1" />
            Send to Reviewer
          </Button>
        )
      } else if (isPreparer()) {
        buttons.push(
          <Button key="submitToAdmin" onClick={() => setActionDialog({ type: "submitToAdmin" })}>
            <Send className="h-4 w-4 mr-1" />
            Submit to Admin
          </Button>
        )
      }
    }

    if (status === "PENDING_ADMIN_APPROVAL" && isAdminActive && data.source !== "TEMPLATE") {
      buttons.push(
        <Button key="adminApprove" onClick={() => setActionDialog({ type: "adminApprove" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>
      )
      buttons.push(
        <Button key="sendToReviewer" variant="outline" onClick={() => setActionDialog({ type: "sendToReviewer" })}>
          <Send className="h-4 w-4 mr-1" />
          Send to Reviewer
        </Button>
      )
      buttons.push(
        <Button key="reject" variant="destructive" onClick={() => setActionDialog({ type: "reject" })}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "PENDING_REVIEW" && isReviewer()) {
      buttons.push(
        <Button key="reviewerApprove" onClick={() => setActionDialog({ type: "reviewerApprove" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>
      )
      buttons.push(
        <Button key="reject" variant="destructive" onClick={() => setActionDialog({ type: "reject" })}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "PENDING_PREPARATION" && isPreparer()) {
      buttons.push(
        <Button key="submit" onClick={() => setActionDialog({ type: "submit" })}>
          <Send className="h-4 w-4 mr-1" />
          Submit for Approval
        </Button>
      )
    }

    if (status === "PENDING_APPROVAL" && canApproveAtCurrentStep()) {
      buttons.push(
        <Button key="approve" onClick={() => setActionDialog({ type: "approve" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>
      )
      buttons.push(
        <Button key="reject" variant="destructive" onClick={() => setActionDialog({ type: "reject" })}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "REJECTED" && isPreparer()) {
      buttons.push(
        <Button key="resubmit" onClick={() => setActionDialog({ type: "resubmit" })}>
          <Send className="h-4 w-4 mr-1" />
          Resubmit
        </Button>
      )
    }

    if (status === "APPROVED" && isAdminOrManager()) {
      buttons.push(
        <Button key="file" onClick={() => setActionDialog({ type: "file" })}>
          <FileText className="h-4 w-4 mr-1" />
          File
        </Button>
      )
      if (data.requiresPayment !== false) {
        buttons.push(
          <Button key="markPaid" variant="outline" onClick={() => setActionDialog({ type: "markPaid" })}>
            <CheckCircle2 className="h-4 w-4 mr-1" />
            Mark Paid
          </Button>
        )
      }
    }

    if (status === "PAID" && isAdminOrManager() && !data.filedAt) {
      buttons.push(
        <Button key="file" onClick={() => setActionDialog({ type: "file" })}>
          <FileText className="h-4 w-4 mr-1" />
          File
        </Button>
      )
    }

    if (status === "FILED" && isAdminOrManager() && data.requiresPayment !== false && !data.paidAt) {
      buttons.push(
        <Button key="markPaid" onClick={() => setActionDialog({ type: "markPaid" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Mark Paid
        </Button>
      )
    }

    if (
      isAdminOrManager() &&
      ((data.requiresPayment !== false && ((status === "FILED" && data.paidAt) || (status === "PAID" && data.filedAt))) ||
        (data.requiresPayment === false && (status === "FILED" || (status === "PAID" && data.filedAt))))
    ) {
      buttons.push(
        <Button key="close" variant="outline" onClick={() => setActionDialog({ type: "close" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Close
        </Button>
      )
    }

    return buttons.length > 0 ? (
      <div className="flex items-center gap-2 flex-wrap">{buttons}</div>
    ) : null
  }

  function getActionLabel() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "approve": return "Approve Compliance"
      case "reject": return "Reject Compliance"
      case "submit": return "Submit for Approval"
      case "resubmit": return "Resubmit Compliance"
      case "file": return "File Compliance"
      case "submitToAdmin": return "Submit to Admin"
      case "adminApprove": return "Approve Compliance"
      case "sendToReviewer": return "Send to Reviewer"
      case "reviewerApprove": return "Approve as Reviewer"
      case "markPaid": return "Mark as Paid"
      case "close": return "Close Compliance"
    }
  }

  function getActionDescription() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "approve": return "Are you sure you want to approve this compliance? You can add an optional comment."
      case "reject": return "Please provide a reason for rejecting this compliance."
      case "submit": return "Submit this compliance for approval?"
      case "resubmit": return "Resubmit this compliance for approval?"
      case "file": return "File this compliance?"
      case "submitToAdmin": return "Submit this compliance to the admin for approval? It will remain in review until the admin approves it."
      case "adminApprove": return "Approve this compliance and move it to preparation. You can optionally tag a reviewer."
      case "sendToReviewer": return "Select a reviewer to review and approve this compliance on your behalf."
      case "reviewerApprove": return "Approve this compliance as the assigned reviewer?"
      case "markPaid": return "Record payment/refund details for this compliance."
      case "close": return "Close this compliance? It is fully filed and paid."
    }
  }

  function getActionApiEndpoint() {
    if (!actionDialog) return ""
    switch (actionDialog.type) {
      case "approve": return "approve"
      case "reject": return "reject"
      case "submit": return "submit"
      case "resubmit": return "resubmit"
      case "file": return "file"
      case "submitToAdmin": return "submit-to-admin"
      case "adminApprove": return "admin-approve"
      case "sendToReviewer": return "send-to-reviewer"
      case "reviewerApprove": return "reviewer-approve"
      case "markPaid": return "mark-paid"
      case "close": return "close"
    }
  }

  if (loading) {
    return (
      <DashboardLayout title="Compliance Details">
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
      </DashboardLayout>
    )
  }

  if (notFound || !data) {
    return (
      <DashboardLayout title="Not Found">
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <AlertTriangle className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
          <h2 className="text-xl font-semibold mb-1">Compliance Not Found</h2>
          <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
            The compliance item you&apos;re looking for doesn&apos;t exist or has been deleted.
          </p>
          <Button onClick={() => router.push("/compliance")}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Obligations Tracker
          </Button>
        </div>
      </DashboardLayout>
    )
  }

  const dueDays = daysUntil(new Date(data.dueDate))
  const isOverdue = dueDays < 0
  const paymentDueDays = data.paymentDueDate ? daysUntil(new Date(data.paymentDueDate)) : null
  const isPaymentOverdue = paymentDueDays !== null && paymentDueDays < 0

  const primaryEntity = data.entity || data.entities?.[0]?.entity
  const entityApprovalFlow = primaryEntity?.approvalFlow
  const formApprovalFlow = data.form?.approvalFlow
  const activeFlow = data.approvalFlow
  const hasMismatch = Boolean(
    (entityApprovalFlow && activeFlow !== entityApprovalFlow) ||
    (formApprovalFlow && activeFlow !== formApprovalFlow)
  )

  return (
    <DashboardLayout title={`Compliance ${data.complianceId}`}>
      <div className="space-y-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => router.push("/compliance")}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">{data.complianceId}</h2>
                <Badge className={getStatusColor(data.status)}>
                  {data.status.replace(/_/g, " ")}
                </Badge>
                <Badge className={getPriorityColor(data.priority)}>
                  <Flag className="h-3 w-3 mr-1" />
                  {data.priority}
                </Badge>
              </div>
              <p className="text-sm text-[var(--color-muted-foreground)] mt-0.5">
                Created {formatDateTime(data.createdAt)}
              </p>
            </div>
          </div>
          {renderActionButtons()}
          <Button variant="outline" onClick={() => router.push(`/compliance/${data.id}/edit`)}>
            <Pencil className="h-4 w-4 mr-1" />
            Edit
          </Button>
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
              {(data.entities?.length
                ? data.entities
                : data.entity
                  ? [{ id: data.entity.id, entityId: data.entity.id, entity: data.entity }]
                  : []
              ).map((en) => {
                const isFilingEntity = en.entityId === data.entity?.id || en.id === data.entity?.id
                const mismatch =
                  isFilingEntity &&
                  !!data.form?.approvalFlow &&
                  !!en.entity?.approvalFlow &&
                  data.form.approvalFlow !== en.entity.approvalFlow
                return (
                  <div key={en.id}>
                    <p className="font-medium">{en.entity?.entityName}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      {en.entity?.entityNumber}
                    </p>
                    {en.entity?.country && (
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        <Globe className="h-3 w-3 inline mr-1" />
                        {en.entity.country.name}
                      </p>
                    )}
                    {mismatch && (
                      <div className="flex items-start gap-2 mt-2 rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2 text-xs text-amber-800 dark:text-amber-200">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span>
                          Approval flow mismatch — Form is {approvalFlowLabel(data.form?.approvalFlow)}, entity master is{" "}
                          {approvalFlowLabel(en.entity?.approvalFlow)}. The form&apos;s approval flow applies.
                        </span>
                      </div>
                    )}
                  </div>
                )
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Compliance Info</CardTitle>
              <Tag className="h-4 w-4 text-[var(--color-muted-foreground)]" />
            </CardHeader>
            <CardContent>
              <p className="font-medium">{taxTypeLabel(data.taxType)}</p>
              {data.form && (
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Form: {data.form.formNumber} – {data.form.formName}
                </p>
              )}
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                Period: {data.taxPeriod} | Frequency: {data.frequency?.replace(/_/g, " ")}
              </p>
              <p className={cn("text-xs mt-1", isOverdue ? "text-red-600 font-medium" : "text-[var(--color-muted-foreground)]")}>
                <FileText className="h-3 w-3 inline mr-1" />
                F Due: {formatDate(data.dueDate)}
                {isOverdue ? (
                  <span className="text-red-600 ml-1">
                    ({Math.abs(dueDays)} days overdue)
                  </span>
                ) : (
                  <span className="ml-1">
                    ({dueDays} days left)
                  </span>
                )}
              </p>
              {data.requiresPayment !== false && (
                <p className={cn("text-xs mt-1", isPaymentOverdue ? "text-red-600 font-medium" : "text-[var(--color-muted-foreground)]")}>
                  <Clock className="h-3 w-3 inline mr-1" />
                  P Due: {data.paymentDueDate ? formatDate(data.paymentDueDate) : "—"}
                  {paymentDueDays !== null &&
                    (isPaymentOverdue ? (
                      <span className="text-red-600 ml-1">
                        ({Math.abs(paymentDueDays)} days overdue)
                      </span>
                    ) : (
                      <span className="ml-1">
                        ({paymentDueDays} days left)
                      </span>
                    ))}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Preparer</CardTitle>
              <User className="h-4 w-4 text-[var(--color-muted-foreground)]" />
            </CardHeader>
            <CardContent>
              {data.assignments?.[0] ? (
                <>
                  <p className="font-medium">{data.assignments[0].preparer.name}</p>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    {data.assignments[0].preparer.email}
                  </p>
                  {data.assignments[0].startedAt && (
                    <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                      Started: {formatDate(data.assignments[0].startedAt)}
                    </p>
                  )}
                  {data.assignments[0].completedAt && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      Completed: {formatDate(data.assignments[0].completedAt)}
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
              <CardTitle className="text-sm font-medium">Approvers</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-[var(--color-muted-foreground)]" />
            </CardHeader>
            <CardContent className="space-y-1">
              {data.approvals && data.approvals.length > 0 ? (
                data.approvals.map((app) => (
                  <div key={app.id} className="flex items-center justify-between text-xs">
                    <span className="font-medium truncate max-w-[120px]">
                      <span className="text-[var(--color-muted-foreground)]">
                        Step {app.step || 1} ({app.step === 2 ? "Approver" : "Reviewer"}):
                      </span>{" "}
                      {app.approver.name}
                    </span>
                    <Badge
                      className={cn(
                        "text-[10px] px-1.5 py-0",
                        app.status === "APPROVED" && "bg-green-100 text-green-700",
                        app.status === "REJECTED" && "bg-red-100 text-red-700",
                        app.status === "PENDING" && "bg-yellow-100 text-yellow-700"
                      )}
                    >
                      {app.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[var(--color-muted-foreground)]">No approvers</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">
              <FileText className="h-4 w-4 mr-1" />
              Details
            </TabsTrigger>
            <TabsTrigger value="timeline">
              <Activity className="h-4 w-4 mr-1" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="documents">
              <Download className="h-4 w-4 mr-1" />
              Documents
              {data.attachments?.length > 0 && (
                <span className="ml-1 text-xs bg-[var(--color-primary)] text-[var(--color-primary-foreground)] rounded-full px-1.5">
                  {data.attachments.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="comments">
              <MessageSquare className="h-4 w-4 mr-1" />
              Comments
              {data.comments?.length > 0 && (
                <span className="ml-1 text-xs bg-[var(--color-primary)] text-[var(--color-primary-foreground)] rounded-full px-1.5">
                  {data.comments.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="audit">
              <History className="h-4 w-4 mr-1" />
              Audit Trail
            </TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-4 pt-4">
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
                      3. Active Compliance Flow (Driving Flow)
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
                      The active compliance flow ({approvalFlowLabel(data.approvalFlow)}) overrides the entity/form master placeholder settings.
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Compliance Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Compliance ID</Label>
                    <p className="font-medium">{data.complianceId}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Country</Label>
                    <p className="font-medium">{data.country?.name} ({data.country?.code})</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Tax Period</Label>
                    <p className="font-medium">
                      {data.taxPeriodStart || data.taxPeriodEnd
                        ? `${data.taxPeriodStart ? formatDate(data.taxPeriodStart) : "—"} – ${data.taxPeriodEnd ? formatDate(data.taxPeriodEnd) : "—"}`
                        : data.taxPeriod}
                    </p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Frequency</Label>
                    <p className="font-medium capitalize">{data.frequency?.replace(/_/g, " ").toLowerCase()}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Due Date</Label>
                    <p className={cn("font-medium", isOverdue && "text-red-600")}>
                      {formatDate(data.dueDate)}
                    </p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Filing Month</Label>
                    <p className="font-medium">{data.filingMonth || "—"}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Recurring</Label>
                    <p className="font-medium">{data.isRecurring ? "Yes" : "No"}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Recurring End Date</Label>
                    <p className="font-medium">{data.recurringEndDate ? formatDate(data.recurringEndDate) : "—"}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Status</Label>
                    <Badge className={getStatusColor(data.status)}>
                      {data.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Source</Label>
                    <Badge variant={data.source === "TEMPLATE" ? "secondary" : data.source === "IMPORT" ? "default" : "outline"}>
                      {(data.source || "MANUAL").replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Priority</Label>
                    <Badge className={getPriorityColor(data.priority)}>
                      {data.priority}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Created</Label>
                    <p className="font-medium">{formatDateTime(data.createdAt)}</p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Last Updated</Label>
                    <p className="font-medium">{formatDateTime(data.updatedAt)}</p>
                  </div>
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
                  {data.adminActionAt && (
                    <div>
                      <Label className="text-[var(--color-muted-foreground)]">Admin Approved</Label>
                      <p className="font-medium">{formatDateTime(data.adminActionAt)}</p>
                    </div>
                  )}
                  {data.submittedAt && (
                    <div>
                      <Label className="text-[var(--color-muted-foreground)]">Submitted</Label>
                      <p className="font-medium">{formatDateTime(data.submittedAt)}</p>
                    </div>
                  )}
                  {data.filedAt && (
                    <div>
                      <Label className="text-[var(--color-muted-foreground)]">Filed</Label>
                      <p className="font-medium">{formatDateTime(data.filedAt)}</p>
                    </div>
                  )}
                </div>
                {data.notes && (
                  <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                    <Label className="text-[var(--color-muted-foreground)]">Notes</Label>
                    <p className="text-sm mt-1 whitespace-pre-wrap">{data.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {(data.requiresPayment !== false && (data.paymentAmount != null || data.paidAt || data.filedAt)) && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Payment Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <Label className="text-[var(--color-muted-foreground)]">Filing Type</Label>
                      <div className="font-medium">
                        <Badge variant="outline" className="font-normal">
                          {FILING_TYPE_LABELS[(data.filingType as keyof typeof FILING_TYPE_LABELS) || "PAYMENT"] || data.filingType || "Payment"}
                        </Badge>
                      </div>
                    </div>
                    {data.refundType && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Refund Type</Label>
                        <p className="font-medium">
                          {REFUND_TYPE_LABELS[data.refundType as keyof typeof REFUND_TYPE_LABELS] || data.refundType}
                        </p>
                      </div>
                    )}
                    {data.paymentAmount != null && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Amount</Label>
                        <p className="font-medium">
                          {data.paymentAmount} {data.paymentCurrency || data.entity?.currency || ""}
                        </p>
                      </div>
                    )}
                    {data.paidAt && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Marked Paid</Label>
                        <p className="font-medium">{formatDateTime(data.paidAt)}</p>
                      </div>
                    )}
                    {data.paymentDate && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Payment Date</Label>
                        <p className="font-medium">{formatDate(data.paymentDate)}</p>
                      </div>
                    )}
                    {data.paymentReference && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Payment Reference</Label>
                        <p className="font-medium">{data.paymentReference}</p>
                      </div>
                    )}
                    {data.paymentMethod && (
                      <div>
                        <Label className="text-[var(--color-muted-foreground)]">Payment Method</Label>
                        <p className="font-medium">{data.paymentMethod}</p>
                      </div>
                    )}
                  </div>
                  {data.confirmations && data.confirmations.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                      <Label className="text-[var(--color-muted-foreground)]">Amount Confirmations</Label>
                      <ul className="mt-2 space-y-1.5 text-sm">
                        {data.confirmations.map((c) => (
                          <li key={c.id} className="flex items-center gap-2">
                            <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                            <span className="capitalize">
                              {CONFIRMATION_STAGE_LABELS[c.stage as keyof typeof CONFIRMATION_STAGE_LABELS] || c.stage.replace(/_/g, " ").toLowerCase()}
                            </span>
                            <span className="text-[var(--color-muted-foreground)]">
                              by {c.confirmedBy?.name} on {formatDateTime(c.confirmedAt)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {data.paymentNotes && (
                    <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                      <Label className="text-[var(--color-muted-foreground)]">Payment Notes</Label>
                      <p className="text-sm mt-1 whitespace-pre-wrap">{data.paymentNotes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="timeline" className="pt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Activity Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                {data.activities && data.activities.length > 0 ? (
                  <div className="relative">
                    <div className="absolute left-[19px] top-2 bottom-2 w-0.5 bg-[var(--color-border)]" />
                    <div className="space-y-6">
                      {data.activities.map((activity) => {
                        const Icon = getActivityIcon(activity.action)
                        const colorClass = getActivityColor(activity.action)
                        return (
                          <div key={activity.id} className="relative flex items-start gap-4">
                            <div className={cn("relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-white", colorClass)}>
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0 pt-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-medium text-sm">{activity.user.name}</span>
                                <span className="text-sm text-[var(--color-muted-foreground)]">
                                  {activity.action.replace(/_/g, " ")}
                                </span>
                                {activity.fromStatus && activity.toStatus && (
                                  <span className="text-xs text-[var(--color-muted-foreground)]">
                                    ({activity.fromStatus.replace(/_/g, " ")} → {activity.toStatus.replace(/_/g, " ")})
                                  </span>
                                )}
                              </div>
                              {activity.comments && (
                                <p className="text-sm mt-1 text-[var(--color-muted-foreground)]">
                                  {activity.comments}
                                </p>
                              )}
                              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                                {formatDateTime(activity.createdAt)}
                              </p>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Activity className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                    <p className="text-sm text-[var(--color-muted-foreground)]">No activity recorded yet.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="documents" className="pt-4 space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">Attachments</CardTitle>
                {(isPreparer() || isApprover() || isAdminActive || isReviewer()) && (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      hidden
                      onChange={handleFileUpload}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={uploadLoading}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {uploadLoading ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4 mr-1" />
                      )}
                      Upload
                    </Button>
                  </div>
                )}
              </CardHeader>
              <CardContent>
                {data.attachments && data.attachments.length > 0 ? (
                  <div className="divide-y divide-[var(--color-border)]">
                    {data.attachments.map((att) => (
                      <div key={att.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="h-8 w-8 text-[var(--color-muted-foreground)] shrink-0" />
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{att.originalName}</p>
                            <p className="text-xs text-[var(--color-muted-foreground)]">
                              {formatFileSize(att.fileSize)} · v{att.version} · {formatDate(att.createdAt)}
                              {att.stage && (
                                <> · <span className="font-medium">{att.stage.replace(/_/g, " ")}</span></>
                              )}
                              {att.uploadedBy && ` · by ${att.uploadedBy.name}`}
                            </p>
                          </div>
                        </div>
                        <Button variant="ghost" size="icon" asChild>
                          <a href={`/api/attachments/${att.id}/download`} download>
                            <Download className="h-4 w-4" />
                          </a>
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <FileText className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                    <p className="text-sm text-[var(--color-muted-foreground)]">No documents attached.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="comments" className="pt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Comments</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.comments && data.comments.length > 0 ? (
                  <div className="space-y-4">
                    {data.comments.map((comment) => (
                      <div key={comment.id} className="flex gap-3">
                        <Avatar className="h-8 w-8 shrink-0">
                          <AvatarFallback className="text-xs bg-blue-100 text-blue-600">
                            {getInitials(comment.user.name)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{comment.user.name}</span>
                            <span className="text-xs text-[var(--color-muted-foreground)]">
                              {formatDateTime(comment.createdAt)}
                            </span>
                          </div>
                          <p className="text-sm mt-0.5 whitespace-pre-wrap">{comment.content}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <MessageSquare className="h-8 w-8 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                    <p className="text-sm text-[var(--color-muted-foreground)]">No comments yet.</p>
                  </div>
                )}

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="newComment">Add a Comment</Label>
                  <Textarea
                    id="newComment"
                    placeholder="Write your comment..."
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    rows={3}
                  />
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      disabled={!newComment.trim() || commentSubmitting}
                      onClick={handleAddComment}
                    >
                      {commentSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                      <MessageSquare className="h-4 w-4 mr-1" />
                      Post Comment
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="audit" className="pt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Audit Trail</CardTitle>
              </CardHeader>
              <CardContent>
                {data.activities && data.activities.length > 0 ? (
                  <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Date/Time</TableHead>
                          <TableHead>User</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead>From Status</TableHead>
                          <TableHead>To Status</TableHead>
                          <TableHead>Comments</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.activities.map((entry) => (
                          <TableRow key={entry.id}>
                            <TableCell className="whitespace-nowrap">
                              {formatDateTime(entry.createdAt)}
                            </TableCell>
                            <TableCell className="font-medium">{entry.user.name}</TableCell>
                            <TableCell className="capitalize">
                              {entry.action.replace(/_/g, " ")}
                            </TableCell>
                            <TableCell>
                              {entry.fromStatus ? (
                                <Badge className={getStatusColor(entry.fromStatus)}>
                                  {entry.fromStatus.replace(/_/g, " ")}
                                </Badge>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                            <TableCell>
                              {entry.toStatus ? (
                                <Badge className={getStatusColor(entry.toStatus)}>
                                  {entry.toStatus.replace(/_/g, " ")}
                                </Badge>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {entry.comments || "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <History className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] opacity-40 mb-2" />
                    <p className="text-sm text-[var(--color-muted-foreground)]">No audit trail entries.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog
        open={!!actionDialog}
        onOpenChange={(o) => {
          if (!o) { setActionDialog(null); setActionComment(""); setReviewerId(""); resetPaymentForm() }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{getActionLabel()}</DialogTitle>
            <DialogDescription>{getActionDescription()}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {(actionDialog?.type === "adminApprove" || actionDialog?.type === "sendToReviewer") && (
              <div className="space-y-2">
                {actionDialog?.type === "adminApprove" && (data?.reviewerId || existingStep1Approver) ? (
                  <div className="space-y-1">
                    <Label htmlFor="reviewer">Reviewer (already assigned)</Label>
                    <Input
                      id="reviewer"
                      value={existingStep1Approver?.approver?.name || data?.reviewer?.name || "Assigned"}
                      disabled
                    />
                    {existingStep2Approver && (
                      <>
                        <Label htmlFor="approver" className="pt-2">Approver (already assigned)</Label>
                        <Input
                          id="approver"
                          value={existingStep2Approver.approver?.name || "Assigned"}
                          disabled
                        />
                      </>
                    )}
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      Reviewer{existingStep2Approver ? " and approver" : ""} {"were"} already selected in draft. No need to select again.
                    </p>
                  </div>
                ) : (
                  <>
                    <Label htmlFor="reviewer">
                      Reviewer {actionDialog.type === "sendToReviewer" && <span className="text-red-500">*</span>}
                    </Label>
                    <Select
                      value={reviewerId || existingStep1Approver?.approver?.id || ""}
                      onValueChange={setReviewerId}
                    >
                      <SelectTrigger id="reviewer">
                        <SelectValue placeholder={actionDialog.type === "adminApprove" ? "Select reviewer (optional)" : "Select reviewer"} />
                      </SelectTrigger>
                      <SelectContent>
                        {reviewers
                          .filter((r) => r.id !== userId || r.id === reviewerId || r.id === existingStep1Approver?.approver?.id)
                          .map((r) => (
                            <SelectItem key={r.id} value={r.id}>
                              {r.name} ({r.email})
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    {existingStep2Approver && (
                      <>
                        <Label htmlFor="approver" className="pt-2">Approver (already assigned)</Label>
                        <Input
                          id="approver"
                          value={existingStep2Approver.approver?.name || "Assigned"}
                          disabled
                        />
                      </>
                    )}
                  </>
                )}
              </div>
            )}

            {(actionDialog?.type === "submit" || actionDialog?.type === "resubmit") && data?.requiresPayment !== false && (
              <div className="space-y-3 border rounded-md p-3">
                <p className="text-xs font-medium text-[var(--color-muted-foreground)]">
                  Payment Details (required)
                </p>
                <div className="space-y-1">
                  <Label htmlFor="filingType">Filing Type</Label>
                  <Select
                    value={paymentForm.filingType}
                    onValueChange={(v) => setPaymentForm((p) => ({ ...p, filingType: v }))}
                  >
                    <SelectTrigger id="filingType">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(FILING_TYPE_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {paymentForm.filingType === "REFUND_RETURN" && (
                  <div className="space-y-1">
                    <Label htmlFor="refundType">Refund Type</Label>
                    <Select
                      value={paymentForm.refundType}
                      onValueChange={(v) => setPaymentForm((p) => ({ ...p, refundType: v }))}
                    >
                      <SelectTrigger id="refundType">
                        <SelectValue placeholder="Select refund type" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(REFUND_TYPE_LABELS).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="paymentAmount">Amount</Label>
                    {paymentForm.filingType === "NIL_RETURN" ? (
                      <Input id="paymentAmount" type="number" value="0" disabled />
                    ) : (
                      <Input
                        id="paymentAmount"
                        type="number"
                        min="0"
                        step="0.01"
                        value={paymentForm.paymentAmount}
                        onChange={(e) => setPaymentForm((p) => ({ ...p, paymentAmount: e.target.value }))}
                      />
                    )}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="paymentCurrency">Currency</Label>
                    <Select
                      value={paymentForm.paymentCurrency || data?.entity?.currency || "USD"}
                      onValueChange={(v) => setPaymentForm((p) => ({ ...p, paymentCurrency: v }))}
                    >
                      <SelectTrigger id="paymentCurrency">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {currencies.length === 0 && (
                          <SelectItem value={data?.entity?.currency || "USD"}>
                            {data?.entity?.currency || "USD"}
                          </SelectItem>
                        )}
                        {currencies.map((c) => (
                          <SelectItem key={c} value={c}>
                            {c}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}

            {actionDialog?.type === "approve" && data?.paymentAmount != null && data?.requiresPayment !== false && (
              <div className="space-y-2 border rounded-md p-3">
                <p className="text-xs font-medium text-[var(--color-muted-foreground)]">
                  Submitted Payment Details
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Filing Type</Label>
                    <p className="font-medium">
                      {FILING_TYPE_LABELS[(data.filingType as keyof typeof FILING_TYPE_LABELS) || "PAYMENT"] || data.filingType || "Payment"}
                    </p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Amount</Label>
                    <p className="font-medium">
                      {data.paymentAmount} {data.paymentCurrency || data.entity?.currency || ""}
                    </p>
                  </div>
                  {data.refundType && (
                    <div className="col-span-2">
                      <Label className="text-[var(--color-muted-foreground)]">Refund Type</Label>
                      <p className="font-medium">
                        {REFUND_TYPE_LABELS[data.refundType as keyof typeof REFUND_TYPE_LABELS] || data.refundType}
                      </p>
                    </div>
                  )}
                </div>
                <label className="flex items-start gap-2 pt-1">
                  <Checkbox
                    checked={paymentForm.confirmAmount}
                    onCheckedChange={(v) => setPaymentForm((p) => ({ ...p, confirmAmount: v === true }))}
                  />
                  <span className="text-sm">
                    I reconfirm this amount is correct before sending the compliance to the next step.
                  </span>
                </label>
              </div>
            )}

            {actionDialog?.type === "markPaid" && (
              <div className="space-y-3 border rounded-md p-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Submitted Filing Type</Label>
                    <p className="font-medium">
                      {FILING_TYPE_LABELS[(data?.filingType as keyof typeof FILING_TYPE_LABELS) || "PAYMENT"] || data?.filingType || "Payment"}
                    </p>
                  </div>
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Submitted Amount</Label>
                    <p className="font-medium">
                      {data?.paymentAmount} {data?.paymentCurrency || data?.entity?.currency || ""}
                    </p>
                  </div>
                  {data?.refundType && (
                    <div className="col-span-2">
                      <Label className="text-[var(--color-muted-foreground)]">Refund Type</Label>
                      <p className="font-medium">
                        {REFUND_TYPE_LABELS[data.refundType as keyof typeof REFUND_TYPE_LABELS] || data.refundType}
                      </p>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="paymentDate">Payment Date</Label>
                    <Input
                      id="paymentDate"
                      type="date"
                      value={paymentForm.paymentDate}
                      onChange={(e) => setPaymentForm((p) => ({ ...p, paymentDate: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="paymentReference">Payment Reference</Label>
                    <Input
                      id="paymentReference"
                      value={paymentForm.paymentReference}
                      onChange={(e) => setPaymentForm((p) => ({ ...p, paymentReference: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="paymentMethod">Payment Method</Label>
                    <Input
                      id="paymentMethod"
                      value={paymentForm.paymentMethod}
                      onChange={(e) => setPaymentForm((p) => ({ ...p, paymentMethod: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="paymentNotes">Payment Notes</Label>
                  <Textarea
                    id="paymentNotes"
                    rows={2}
                    value={paymentForm.paymentNotes}
                    onChange={(e) => setPaymentForm((p) => ({ ...p, paymentNotes: e.target.value }))}
                  />
                </div>
                <label className="flex items-start gap-2">
                  <Checkbox
                    checked={paymentForm.confirmPayment}
                    onCheckedChange={(v) => setPaymentForm((p) => ({ ...p, confirmPayment: v === true }))}
                  />
                  <span className="text-sm">
                    I confirm the same amount has been paid.
                  </span>
                </label>
              </div>
            )}

            {actionDialog?.type === "file" && (
              <div className="space-y-1">
                <Label htmlFor="filedDate">Filing Date</Label>
                <Input
                  id="filedDate"
                  type="date"
                  value={paymentForm.filedDate}
                  onChange={(e) => setPaymentForm((p) => ({ ...p, filedDate: e.target.value }))}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Leave blank to use today date.
                </p>
              </div>
            )}

            {actionDialog?.type !== "markPaid" && (
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
              onClick={() => { setActionDialog(null); setActionComment("") }}
            >
              Cancel
            </Button>
            <Button
              variant={actionDialog?.type === "reject" ? "destructive" : "default"}
              disabled={
                actionLoading === getActionApiEndpoint() ||
                (actionDialog?.type === "reject" && !actionComment.trim()) ||
                (actionDialog?.type === "sendToReviewer" && !reviewerId) ||
                (actionDialog?.type === "approve" && data?.requiresPayment !== false && (data?.paymentAmount == null || !paymentForm.confirmAmount)) ||
                (actionDialog?.type === "markPaid" && !paymentForm.confirmPayment) ||
                ((actionDialog?.type === "submit" || actionDialog?.type === "resubmit") &&
                  data?.requiresPayment !== false &&
                  validatePaymentSubmission({
                    filingType: paymentForm.filingType,
                    amount: paymentForm.filingType === "NIL_RETURN" ? 0 : Number(paymentForm.paymentAmount || 0),
                    currency: paymentForm.paymentCurrency || data?.entity?.currency || "USD",
                    refundType: paymentForm.filingType === "REFUND_RETURN" ? paymentForm.refundType : null,
                  }).length > 0)
              }
              onClick={() => handleAction(getActionApiEndpoint())}
            >
              {actionLoading === getActionApiEndpoint() && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              {getActionLabel()}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  )
}
