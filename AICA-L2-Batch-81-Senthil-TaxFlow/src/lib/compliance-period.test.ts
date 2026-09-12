import { describe, it, expect } from "vitest"
import {
  computeFirstPeriod,
  computeNextPeriod,
  periodsOverlap,
  monthsForFrequency,
  isInMonth,
  parseDate,
  computeGeneration,
} from "./compliance-period"

describe("parseDate", () => {
  it("keeps a date-only value as local midnight", () => {
    const d = parseDate("2026-07-31")
    expect(d.getFullYear()).toBe(2026)
    expect(d.getMonth()).toBe(6)
    expect(d.getDate()).toBe(31)
    expect(d.getHours()).toBe(0)
  })

  it("treats offset-less stored timestamps as UTC and normalizes to midnight", () => {
    const d = parseDate("2026-07-30T18:30:00")
    expect(d.getHours()).toBe(0)
    expect(d.getMinutes()).toBe(0)
    expect(d.getSeconds()).toBe(0)
    expect(d.getMilliseconds()).toBe(0)
    expect(d.getTime()).toBe(parseDate("2026-07-30T18:30:00+00:00").getTime())
    expect(d.getTime()).toBe(parseDate("2026-07-30T18:30:00.000Z").getTime())
  })

  it("normalizes offset-bearing stored timestamps to midnight", () => {
    const d = parseDate("2026-08-14T18:30:00+00:00")
    expect(d.getHours()).toBe(0)
    expect(d.getMinutes()).toBe(0)
  })
})

describe("monthsForFrequency", () => {
  it("maps each frequency to months", () => {
    expect(monthsForFrequency("MONTHLY")).toBe(1)
    expect(monthsForFrequency("BI_MONTHLY")).toBe(2)
    expect(monthsForFrequency("QUARTERLY")).toBe(3)
    expect(monthsForFrequency("HALF_YEARLY")).toBe(6)
    expect(monthsForFrequency("ANNUAL")).toBe(12)
    expect(monthsForFrequency("WEEKLY")).toBe(0)
    expect(monthsForFrequency("AD_HOC")).toBe(0)
    expect(monthsForFrequency("UNKNOWN")).toBe(1)
  })
})

describe("isInMonth", () => {
  it("checks whether a date falls in the given month", () => {
    expect(isInMonth(new Date(2026, 0, 15), "2026-01")).toBe(true)
    expect(isInMonth(new Date(2026, 1, 15), "2026-01")).toBe(false)
  })
})

describe("computeFirstPeriod", () => {
  it("anchors a quarterly period on the anchor end date", () => {
    const { start, end } = computeFirstPeriod(new Date(2025, 10, 30), "QUARTERLY")
    expect(start).toEqual(new Date(2025, 8, 1))
    expect(end).toEqual(new Date(2025, 10, 30))
  })
  it("anchors a monthly period on the anchor end date", () => {
    const { start, end } = computeFirstPeriod(new Date(2026, 0, 31), "MONTHLY")
    expect(start).toEqual(new Date(2026, 0, 1))
    expect(end).toEqual(new Date(2026, 0, 31))
  })
  it("anchors a bi-monthly period on the anchor end date", () => {
    const { start, end } = computeFirstPeriod(new Date(2026, 2, 31), "BI_MONTHLY")
    expect(start).toEqual(new Date(2026, 1, 1))
    expect(end).toEqual(new Date(2026, 2, 31))
  })
  it("anchors a half-yearly period on the anchor end date", () => {
    const { start, end } = computeFirstPeriod(new Date(2026, 5, 30), "HALF_YEARLY")
    expect(start).toEqual(new Date(2026, 0, 1))
    expect(end).toEqual(new Date(2026, 5, 30))
  })
  it("anchors an annual period to Jan 1", () => {
    const { start, end } = computeFirstPeriod(new Date(2026, 11, 31), "ANNUAL")
    expect(start).toEqual(new Date(2026, 0, 1))
    expect(end).toEqual(new Date(2026, 11, 31))
  })
  it("uses a 7 day window for weekly", () => {
    const { start, end } = computeFirstPeriod(new Date(2026, 0, 8), "WEEKLY")
    expect(start).toEqual(new Date(2026, 0, 2))
    expect(end).toEqual(new Date(2026, 0, 8))
  })
})

describe("computeNextPeriod", () => {
  it("rolls quarterly forward contiguously", () => {
    const { start, end } = computeNextPeriod(new Date(2025, 10, 30), "QUARTERLY")
    expect(start).toEqual(new Date(2025, 11, 1))
    expect(end).toEqual(new Date(2026, 1, 28))
  })
  it("rolls monthly forward to month end", () => {
    const { start, end } = computeNextPeriod(new Date(2026, 0, 31), "MONTHLY")
    expect(start).toEqual(new Date(2026, 1, 1))
    expect(end).toEqual(new Date(2026, 1, 28))
  })
  it("rolls annually", () => {
    const { start, end } = computeNextPeriod(new Date(2025, 11, 31), "ANNUAL")
    expect(start).toEqual(new Date(2026, 0, 1))
    expect(end).toEqual(new Date(2026, 11, 31))
  })
  it("handles leap year month end", () => {
    const { start, end } = computeNextPeriod(new Date(2024, 0, 31), "MONTHLY")
    expect(start).toEqual(new Date(2024, 1, 1))
    expect(end).toEqual(new Date(2024, 1, 29))
  })
  it("rolls bi-monthly", () => {
    const { start, end } = computeNextPeriod(new Date(2026, 2, 31), "BI_MONTHLY")
    expect(start).toEqual(new Date(2026, 3, 1))
    expect(end).toEqual(new Date(2026, 4, 31))
  })
  it("rolls half-yearly", () => {
    const { start, end } = computeNextPeriod(new Date(2025, 11, 31), "HALF_YEARLY")
    expect(start).toEqual(new Date(2026, 0, 1))
    expect(end).toEqual(new Date(2026, 5, 30))
  })
})

describe("periodsOverlap", () => {
  it("detects overlapping ranges", () => {
    const a = { start: new Date(2025, 8, 1), end: new Date(2025, 10, 30) }
    const b = { start: new Date(2025, 9, 1), end: new Date(2025, 11, 31) }
    expect(periodsOverlap(a, b)).toBe(true)
  })
  it("detects non-overlapping ranges", () => {
    const a = { start: new Date(2025, 8, 1), end: new Date(2025, 10, 30) }
    const b = { start: new Date(2025, 11, 1), end: new Date(2026, 1, 28) }
    expect(periodsOverlap(a, b)).toBe(false)
  })
})

describe("computeGeneration", () => {
  it("generates first compliance from the period end anchor when due in the filing month", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      periodEndDate: "2025-11-30",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2025-12",
      existingPeriods: [],
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2025, 8, 1))
    expect(result.periodEnd).toEqual(new Date(2025, 10, 30))
    expect(result.dueDate).toEqual(new Date(2025, 11, 15))
    expect(result.paymentDueDate).toEqual(new Date(2025, 11, 15))
  })

  it("marks first compliance as future when not due in the filing month", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      periodEndDate: "2025-11-30",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-01",
      existingPeriods: [],
    })
    expect(result.bucket).toBe("future")
  })

  it("rolls to the next period from the latest compliance and generates when due in month", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      periodEndDate: "2025-11-30",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-03",
      latestComplianceEnd: "2025-11-30",
      existingPeriods: [{ start: "2025-09-01", end: "2025-11-30" }],
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2025, 11, 1))
    expect(result.periodEnd).toEqual(new Date(2026, 1, 28))
    expect(result.dueDate).toEqual(new Date(2026, 2, 15))
  })

  it("marks the next period as future when its due date is not in the filing month", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-01",
      latestComplianceEnd: "2025-11-30",
      existingPeriods: [{ start: "2025-09-01", end: "2025-11-30" }],
    })
    expect(result.bucket).toBe("future")
  })

  it("rejects a period that overlaps an already-generated compliance", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      periodEndDate: "2025-12-31",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-01",
      existingPeriods: [{ start: "2025-09-01", end: "2025-11-30" }],
    })
    expect(result.bucket).toBe("overlap")
  })

  it("honors a separate payment due days value", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-01-31",
      dueDaysAfterPeriodEnd: 15,
      paymentDueDaysAfterPeriodEnd: 10,
      filingMonth: "2026-02",
      existingPeriods: [],
    })
    expect(result.bucket).toBe("generate")
    expect(result.dueDate).toEqual(new Date(2026, 1, 15))
    expect(result.paymentDueDate).toEqual(new Date(2026, 1, 10))
  })

  it("generates the first period even when not yet due when forceFirstPeriod is set", () => {
    const result = computeGeneration({
      frequency: "QUARTERLY",
      periodEndDate: "2025-11-30",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-01",
      existingPeriods: [],
      forceFirstPeriod: true,
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2025, 8, 1))
  })

  it("falls back to the filing month period for legacy templates without an anchor", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-01",
      existingPeriods: [],
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2026, 0, 1))
    expect(result.periodEnd).toEqual(new Date(2026, 0, 31))
  })

  it("does not roll ad-hoc templates once generated", () => {
    const result = computeGeneration({
      frequency: "AD_HOC",
      periodEndDate: "2026-01-31",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-02",
      latestComplianceEnd: "2026-01-31",
      existingPeriods: [{ start: "2026-01-01", end: "2026-01-31" }],
    })
    expect(result.bucket).toBe("future")
  })

  it("ignores existing periods with invalid dates in the overlap guard", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-01-31",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-03",
      latestComplianceEnd: "2026-01-31",
      existingPeriods: [
        { start: null, end: null },
        { start: "2026-01-01", end: "2026-01-31" },
      ],
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2026, 1, 1))
  })

  it("marks existing when a compliance already exists for the filing month", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-01-31",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-03",
      latestComplianceEnd: "2026-01-31",
      existingPeriods: [{ start: "2026-01-01", end: "2026-01-31" }],
      existingFilingMonths: ["2026-03"],
    })
    expect(result.bucket).toBe("existing")
    expect(result.reason).toContain("2026-03")
  })

  it("still generates when the filing month has no compliance yet", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-01-31",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-04",
      latestComplianceEnd: "2026-01-31",
      existingPeriods: [{ start: "2026-01-01", end: "2026-01-31" }],
      existingFilingMonths: ["2026-03"],
    })
    expect(result.bucket).toBe("future")
  })

  it("generates the next period from stored timestamps (IST-midnight as UTC)", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-07-30T18:30:00+00:00",
      dueDaysAfterPeriodEnd: 15,
      paymentDueDaysAfterPeriodEnd: 21,
      filingMonth: "2026-09",
      latestComplianceEnd: "2026-07-30T18:30:00",
      existingPeriods: [{ start: "2026-06-30T18:30:00", end: "2026-07-30T18:30:00" }],
      existingFilingMonths: ["2026-08"],
    })
    expect(result.bucket).toBe("generate")
    expect(result.dueDate).toBeDefined()
    expect(isInMonth(result.dueDate as Date, "2026-09")).toBe(true)
    expect(result.periodStart).toBeDefined()
    expect((result.periodEnd as Date).getTime()).toBeGreaterThan((result.periodStart as Date).getTime())
  })

  it("reports existing when generating for a filing month already covered by stored data", () => {
    const result = computeGeneration({
      frequency: "MONTHLY",
      periodEndDate: "2026-07-30T18:30:00+00:00",
      dueDaysAfterPeriodEnd: 15,
      filingMonth: "2026-08",
      latestComplianceEnd: "2026-07-30T18:30:00",
      existingPeriods: [{ start: "2026-06-30T18:30:00", end: "2026-07-30T18:30:00" }],
      existingFilingMonths: ["2026-08"],
    })
    expect(result.bucket).toBe("existing")
    expect(result.reason).toContain("2026-08")
  })
})
