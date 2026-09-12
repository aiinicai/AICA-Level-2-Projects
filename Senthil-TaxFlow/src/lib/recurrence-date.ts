export function addMonthsPreservingDay(date: Date, months: number): Date {
  const year = date.getFullYear()
  const month = date.getMonth()
  const day = date.getDate()

  const targetMonthIndex = month + months
  const targetYear = year + Math.floor(targetMonthIndex / 12)
  const normalizedMonth = ((targetMonthIndex % 12) + 12) % 12

  const lastDayOfTargetMonth = new Date(targetYear, normalizedMonth + 1, 0).getDate()
  const targetDay = Math.min(day, lastDayOfTargetMonth)

  const result = new Date(date)
  result.setFullYear(targetYear, normalizedMonth, targetDay)
  return result
}

export function calculateNextDueDate(dueDate: Date, frequency: string): Date | null {
  const next = new Date(dueDate)
  switch (frequency) {
    case "WEEKLY":
      next.setDate(next.getDate() + 7)
      return next
    case "BI_MONTHLY":
      next.setDate(next.getDate() + 14)
      return next
    case "MONTHLY":
      return addMonthsPreservingDay(dueDate, 1)
    case "QUARTERLY":
      return addMonthsPreservingDay(dueDate, 3)
    case "HALF_YEARLY":
      return addMonthsPreservingDay(dueDate, 6)
    case "ANNUAL":
      return addMonthsPreservingDay(dueDate, 12)
    default:
      return null
  }
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
]
const SHORT_MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

export function advanceTaxPeriod(currentPeriod: string | null | undefined, frequency: string): string {
  if (!currentPeriod || typeof currentPeriod !== "string") return ""
  const trimmed = currentPeriod.trim()

  const quarterMatch = trimmed.match(/^Q([1-4])(?:\s+|-)?(\d{4})$/i)
  if (quarterMatch) {
    let q = parseInt(quarterMatch[1], 10)
    let y = parseInt(quarterMatch[2], 10)
    const step = frequency === "HALF_YEARLY" ? 2 : frequency === "ANNUAL" ? 4 : 1
    q += step
    while (q > 4) {
      q -= 4
      y += 1
    }
    return `Q${q} ${y}`
  }

  const monthMatch = trimmed.match(/^([A-Za-z]+)\s+(\d{4})$/)
  if (monthMatch) {
    const rawMonth = monthMatch[1]
    let y = parseInt(monthMatch[2], 10)
    let mIdx = MONTH_NAMES.findIndex((m) => m.toLowerCase() === rawMonth.toLowerCase())
    const isShort = mIdx === -1
    if (isShort) {
      mIdx = SHORT_MONTH_NAMES.findIndex((m) => m.toLowerCase() === rawMonth.toLowerCase())
    }
    if (mIdx !== -1) {
      const step = frequency === "QUARTERLY" ? 3 : frequency === "HALF_YEARLY" ? 6 : frequency === "ANNUAL" ? 12 : 1
      mIdx += step
      while (mIdx >= 12) {
        mIdx -= 12
        y += 1
      }
      return `${isShort ? SHORT_MONTH_NAMES[mIdx] : MONTH_NAMES[mIdx]} ${y}`
    }
  }

  const yearMatch = trimmed.match(/^(?:FY\s*)?(\d{4})$/i)
  if (yearMatch) {
    const nextYear = parseInt(yearMatch[1], 10) + 1
    return trimmed.toUpperCase().startsWith("FY") ? `FY ${nextYear}` : `${nextYear}`
  }

  return currentPeriod
}
