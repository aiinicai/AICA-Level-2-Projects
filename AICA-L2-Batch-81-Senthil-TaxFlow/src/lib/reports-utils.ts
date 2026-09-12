export function formatDate(value: unknown): string {
  if (!value) return ""
  return new Date(value as string).toISOString().split("T")[0]
}

export function dayDiff(value: string | null, due: string | null): string {
  if (!value || !due) return ""
  const ms = new Date(value).getTime() - new Date(due).getTime()
  if (ms <= 0) return "0"
  return String(Math.floor(ms / 86400000))
}

export function getFilingTimeliness(filedAt: string | null, dueDate: string | null): string {
  if (filedAt) {
    if (!dueDate) return "Completed"
    return new Date(filedAt) <= new Date(dueDate) ? "On-Time" : "Delayed"
  }
  if (dueDate && new Date() > new Date(dueDate)) return "Overdue"
  return "Pending"
}

export function getPaymentTimeliness(
  requiresPayment: boolean | null,
  paymentDate: string | null,
  paymentDueDate: string | null
): string {
  if (requiresPayment === false) return "N/A"
  if (paymentDate) {
    if (!paymentDueDate) return "Paid"
    return new Date(paymentDate) <= new Date(paymentDueDate) ? "On-Time" : "Delayed"
  }
  if (paymentDueDate && new Date() > new Date(paymentDueDate)) return "Overdue"
  return "Pending"
}

export function getPaymentUrgency(
  paymentDueDate: string | null,
  dueDate: string | null,
  referenceNow: Date = new Date()
): { urgency: string; daysLeft: string } {
  const target = paymentDueDate || dueDate
  if (!target) return { urgency: "Scheduled", daysLeft: "—" }

  const targetDate = new Date(target)
  const targetUtc = Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth(), targetDate.getUTCDate())
  const refUtc = Date.UTC(referenceNow.getUTCFullYear(), referenceNow.getUTCMonth(), referenceNow.getUTCDate())

  const ms = targetUtc - refUtc
  const days = Math.round(ms / (1000 * 60 * 60 * 24))
  if (days < 0) return { urgency: "Overdue", daysLeft: `${days}d (Late)` }
  if (days === 0) return { urgency: "Due Today", daysLeft: "0d" }
  if (days <= 7) return { urgency: "Due in 7 Days", daysLeft: `${days}d` }
  if (days <= 30) return { urgency: "Due in 30 Days", daysLeft: `${days}d` }
  return { urgency: "Future (> 30 Days)", daysLeft: `${days}d` }
}
