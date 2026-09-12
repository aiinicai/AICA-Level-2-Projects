export function toDateOnlyString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

export function parseDate(input: string): Date {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input)
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const hasOffset = /(?:Z|[+-]\d{2}:?\d{2})$/.test(input)
  const parsed = new Date(hasOffset ? input : `${input}Z`)
  if (isNaN(parsed.getTime())) return parsed
  return new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate())
}

export function computeTaxPeriod(
  filingMonth: string,
  frequency: string
): { start: Date; end: Date } {
  const [year, month] = filingMonth.split("-").map(Number)
  switch (frequency) {
    case "WEEKLY": {
      const first = new Date(year, month - 1, 1)
      const dayOfWeek = first.getDay()
      const start = new Date(first)
      start.setDate(first.getDate() + (dayOfWeek === 0 ? -6 : 1 - dayOfWeek))
      const end = new Date(start)
      end.setDate(start.getDate() + 6)
      return { start, end }
    }
    case "BI_MONTHLY": {
      const blockStartMonth = Math.floor((month - 1) / 2) * 2 + 1
      return {
        start: new Date(year, blockStartMonth - 1, 1),
        end: new Date(year, blockStartMonth + 1, 0),
      }
    }
    case "QUARTERLY": {
      const quarterStartMonth = Math.floor((month - 1) / 3) * 3 + 1
      return {
        start: new Date(year, quarterStartMonth - 1, 1),
        end: new Date(year, quarterStartMonth + 2, 0),
      }
    }
    case "HALF_YEARLY": {
      const halfStartMonth = month <= 6 ? 1 : 7
      return {
        start: new Date(year, halfStartMonth - 1, 1),
        end: new Date(year, halfStartMonth + 5, 0),
      }
    }
    case "ANNUAL":
      return { start: new Date(year, 0, 1), end: new Date(year, 11, 31) }
    case "MONTHLY":
    case "AD_HOC":
    default:
      return { start: new Date(year, month - 1, 1), end: new Date(year, month, 0) }
  }
}

export function computeDueDate(periodEnd: Date, daysAfterPeriodEnd: number): Date {
  const due = new Date(periodEnd)
  due.setDate(due.getDate() + daysAfterPeriodEnd)
  return due
}

export function monthsForFrequency(frequency: string): number {
  switch (frequency) {
    case "MONTHLY":
      return 1
    case "BI_MONTHLY":
      return 2
    case "QUARTERLY":
      return 3
    case "HALF_YEARLY":
      return 6
    case "ANNUAL":
      return 12
    case "WEEKLY":
    case "AD_HOC":
      return 0
    default:
      return 1
  }
}

export function isInMonth(date: Date, filingMonth: string): boolean {
  const [year, month] = filingMonth.split("-").map(Number)
  if (!year || !month) return false
  return date.getFullYear() === year && date.getMonth() === month - 1
}

export function computeFirstPeriod(
  anchorEnd: Date,
  frequency: string
): { start: Date; end: Date } {
  const end = new Date(anchorEnd)
  if (frequency === "WEEKLY") {
    const start = new Date(end)
    start.setDate(end.getDate() - 6)
    return { start, end }
  }
  const months = monthsForFrequency(frequency)
  if (months <= 0) return { start: end, end }
  const start = new Date(end.getFullYear(), end.getMonth() - months + 1, 1)
  return { start, end }
}

export function computeNextPeriod(
  lastEnd: Date,
  frequency: string
): { start: Date; end: Date } {
  const start = new Date(lastEnd)
  start.setDate(start.getDate() + 1)
  if (frequency === "WEEKLY") {
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    return { start, end }
  }
  const months = monthsForFrequency(frequency)
  if (months <= 0) return { start, end: new Date(start) }
  const end = new Date(start.getFullYear(), start.getMonth() + months, 0)
  return { start, end }
}

export function periodsOverlap(
  a: { start: Date; end: Date },
  b: { start: Date; end: Date }
): boolean {
  return a.start <= b.end && b.start <= a.end
}

export type GenerationBucket = "generate" | "future" | "overlap" | "existing"

export interface GenerationResult {
  bucket: GenerationBucket
  periodStart?: Date
  periodEnd?: Date
  dueDate?: Date
  paymentDueDate?: Date
  reason?: string
}

export function computeGeneration(opts: {
  frequency: string
  periodEndDate?: string | null
  dueDaysAfterPeriodEnd?: number | null
  paymentDueDaysAfterPeriodEnd?: number | null
  filingMonth: string
  latestComplianceEnd?: string | null
  existingPeriods?: Array<{ start?: string | null; end?: string | null }>
  existingFilingMonths?: Array<string | null>
  forceFirstPeriod?: boolean
}): GenerationResult {
  const dueDays = opts.dueDaysAfterPeriodEnd ?? 15
  const paymentDueDays = opts.paymentDueDaysAfterPeriodEnd ?? dueDays
  const latestEnd = opts.latestComplianceEnd ? parseDate(opts.latestComplianceEnd) : null
  const hasLatest = !!latestEnd && !isNaN(latestEnd.getTime())

  if ((opts.existingFilingMonths || []).includes(opts.filingMonth)) {
    return { bucket: "existing", reason: `Compliance already exists for ${opts.filingMonth}` }
  }

  if (opts.frequency === "AD_HOC" && hasLatest) {
    return { bucket: "future", reason: "Ad-hoc compliance already generated for this template" }
  }

  let candidate: { start: Date; end: Date }
  if (hasLatest) {
    candidate = computeNextPeriod(latestEnd, opts.frequency)
  } else if (opts.periodEndDate) {
    const anchor = parseDate(opts.periodEndDate)
    candidate = computeFirstPeriod(isNaN(anchor.getTime()) ? new Date() : anchor, opts.frequency)
  } else {
    candidate = computeTaxPeriod(opts.filingMonth, opts.frequency)
  }

  for (const p of opts.existingPeriods || []) {
    const start = p.start ? parseDate(p.start) : null
    const end = p.end ? parseDate(p.end) : null
    if (start && end && !isNaN(start.getTime()) && !isNaN(end.getTime())) {
      if (periodsOverlap(candidate, { start, end })) {
        return { bucket: "overlap", reason: "Period overlaps an already-generated compliance" }
      }
    }
  }

  const dueDate = computeDueDate(candidate.end, dueDays)
  const paymentDueDate = computeDueDate(candidate.end, paymentDueDays)

  const isFirstPeriod = !hasLatest
  const legacyFallback = isFirstPeriod && !opts.periodEndDate

  if ((opts.forceFirstPeriod && isFirstPeriod) || legacyFallback || isInMonth(dueDate, opts.filingMonth)) {
    return { bucket: "generate", periodStart: candidate.start, periodEnd: candidate.end, dueDate, paymentDueDate }
  }
  return { bucket: "future", reason: `Filing due date ${toDateOnlyString(dueDate)} is not within ${opts.filingMonth}` }
}
