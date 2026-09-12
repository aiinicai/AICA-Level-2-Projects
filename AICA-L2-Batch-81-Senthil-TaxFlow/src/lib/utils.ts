import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { parseDate } from "./compliance-period"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: Date | string): string {
  const d = typeof date === "string" ? parseDate(date) : date
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d)
}

export function formatDateTime(date: Date | string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date))
}

export function formatCurrency(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount)
}

export function generateComplianceId(): string {
  const prefix = "TAX"
  const num = Math.floor(Math.random() * 99999).toString().padStart(5, "0")
  return `${prefix}-${num}`
}

export function calcFrequencyFromPeriod(startDate: string, endDate: string): string {
  if (!startDate || !endDate) return ""
  const start = new Date(startDate)
  const end = new Date(endDate)
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || end < start) return ""

  const dayDiff = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
  if (dayDiff <= 7) return "WEEKLY"

  const monthDiff =
    (end.getFullYear() - start.getFullYear()) * 12 +
    (end.getMonth() - start.getMonth()) +
    1

  switch (monthDiff) {
    case 1:
      return "MONTHLY"
    case 2:
      return "BI_MONTHLY"
    case 3:
      return "QUARTERLY"
    case 6:
      return "HALF_YEARLY"
    case 12:
      return "ANNUAL"
    default:
      return "AD_HOC"
  }
}

export function calcFilingMonth(dueDate: string): string {
  if (!dueDate) return ""
  const d = new Date(dueDate)
  if (isNaN(d.getTime())) return ""
  return d.toLocaleString("en-US", { month: "long", year: "numeric" })
}

export function formatPeriodLabel(startDate: string, endDate: string): string {
  if (!startDate || !endDate) return ""
  const start = new Date(startDate)
  const end = new Date(endDate)
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return ""
  const startLabel = start.toLocaleString("en-US", { month: "short", year: "numeric" })
  const endLabel = end.toLocaleString("en-US", { month: "short", year: "numeric" })
  if (startLabel === endLabel) return startLabel
  return `${startLabel} – ${endLabel}`
}

export function calculateDueDate(
  startDate: Date,
  frequency: string,
  preparationDays: number
): Date {
  const due = new Date(startDate)
  switch (frequency) {
    case "WEEKLY":
      due.setDate(due.getDate() + 7 + preparationDays)
      break
    case "MONTHLY":
      due.setMonth(due.getMonth() + 1)
      due.setDate(due.getDate() + preparationDays)
      break
    case "BI_MONTHLY":
      due.setMonth(due.getMonth() + 2)
      due.setDate(due.getDate() + preparationDays)
      break
    case "QUARTERLY":
      due.setMonth(due.getMonth() + 3)
      due.setDate(due.getDate() + preparationDays)
      break
    case "HALF_YEARLY":
      due.setMonth(due.getMonth() + 6)
      due.setDate(due.getDate() + preparationDays)
      break
    case "ANNUAL":
      due.setFullYear(due.getFullYear() + 1)
      due.setDate(due.getDate() + preparationDays)
      break
    default:
      due.setDate(due.getDate() + preparationDays)
  }
  return due
}

export function isOverdue(dueDate: Date): boolean {
  return new Date() > new Date(dueDate)
}

export function daysUntil(dueDate: Date): number {
  const diff = new Date(dueDate).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    DRAFT: "bg-gray-100 text-gray-800",
    PENDING_ADMIN_APPROVAL: "bg-amber-100 text-amber-800",
    PENDING_REVIEW: "bg-cyan-100 text-cyan-800",
    PENDING_PREPARATION: "bg-yellow-100 text-yellow-800",
    PREPARED: "bg-blue-100 text-blue-800",
    PENDING_APPROVAL: "bg-purple-100 text-purple-800",
    APPROVED: "bg-green-100 text-green-800",
    REJECTED: "bg-red-100 text-red-800",
    FILED: "bg-emerald-100 text-emerald-800",
    PAID: "bg-teal-100 text-teal-800",
    CLOSED: "bg-slate-100 text-slate-800",
  }
  return colors[status] || "bg-gray-100 text-gray-800"
}

export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    NORMAL: "bg-blue-100 text-blue-800",
    HIGH: "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800",
  }
  return colors[priority] || "bg-gray-100 text-gray-800"
}
