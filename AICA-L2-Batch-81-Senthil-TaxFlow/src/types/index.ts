type ComplianceStatus = "DRAFT" | "PENDING_PREPARATION" | "PREPARED" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "FILED" | "CLOSED"
type Priority = "NORMAL" | "HIGH" | "CRITICAL"

export interface OrgInfo {
  id: string
  name: string
  slug: string
  roles: string[]
}

export interface SessionUser {
  id: string
  email: string
  name: string | null
  username: string
  role: string
  roles: string[]
  image: string | null
  employeeId: string | null
  department: string | null
  orgs: OrgInfo[]
}

export interface DashboardCard {
  title: string
  value: number
  description?: string
  icon: string
  trend?: "up" | "down" | "neutral"
  color: string
}

export interface ChartData {
  name: string
  value: number
  [key: string]: string | number
}

export interface ComplianceWithRelations {
  id: string
  complianceId: string
  entity: { id: string; entityName: string; entityNumber: string }
  country: { id: string; name: string; code: string }
  complianceType: { id: string; name: string; taxType: string }
  form: { id: string; formNumber: string; formName: string } | null
  taxPeriod: string
  frequency: string
  dueDate: Date
  priority: Priority
  status: ComplianceStatus
  isRecurring: boolean
  notes: string | null
  submittedAt: Date | null
  filedAt: Date | null
  assignments: {
    id: string
    preparer: { id: string; name: string; email: string }
    startedAt: Date | null
    completedAt: Date | null
  }[]
  approvals: {
    id: string
    approver: { id: string; name: string; email: string }
    status: string
    comments: string | null
    actionAt: Date | null
  }[]
  attachments: {
    id: string
    originalName: string
    fileType: string
    fileSize: number
    version: number
    createdAt: Date
  }[]
  comments: {
    id: string
    content: string
    user: { id: string; name: string }
    createdAt: Date
  }[]
  activities: {
    id: string
    action: string
    fromStatus: string | null
    toStatus: string | null
    user: { id: string; name: string }
    comments: string | null
    createdAt: Date
  }[]
  createdAt: Date
  updatedAt: Date
}

export interface KPIData {
  label: string
  value: number
  unit?: string
  trend?: number
}

export interface FilterState {
  country: string[]
  entity: string[]
  taxType: string[]
  complianceType: string[]
  employee: string[]
  status: string[]
  priority: string[]
  month: string
  quarter: string
  year: string
  search: string
}
