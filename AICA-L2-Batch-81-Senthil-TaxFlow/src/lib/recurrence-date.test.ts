import { describe, it, expect } from "vitest"
import { addMonthsPreservingDay, calculateNextDueDate, advanceTaxPeriod } from "./recurrence-date"

describe("addMonthsPreservingDay", () => {
  it("preserves regular day across months", () => {
    const d = new Date(2026, 0, 15) // Jan 15, 2026
    const next = addMonthsPreservingDay(d, 1)
    expect(next.getFullYear()).toBe(2026)
    expect(next.getMonth()).toBe(1) // Feb
    expect(next.getDate()).toBe(15)
  })

  it("clamps month-end on January 31 to February 28 (non-leap year)", () => {
    const d = new Date(2026, 0, 31) // Jan 31, 2026
    const next = addMonthsPreservingDay(d, 1)
    expect(next.getFullYear()).toBe(2026)
    expect(next.getMonth()).toBe(1) // Feb
    expect(next.getDate()).toBe(28)
  })

  it("clamps month-end on January 31 to February 29 in a leap year (2028)", () => {
    const d = new Date(2028, 0, 31) // Jan 31, 2028
    const next = addMonthsPreservingDay(d, 1)
    expect(next.getFullYear()).toBe(2028)
    expect(next.getMonth()).toBe(1) // Feb
    expect(next.getDate()).toBe(29)
  })

  it("clamps March 31 to April 30", () => {
    const d = new Date(2026, 2, 31) // Mar 31, 2026
    const next = addMonthsPreservingDay(d, 1)
    expect(next.getFullYear()).toBe(2026)
    expect(next.getMonth()).toBe(3) // Apr
    expect(next.getDate()).toBe(30)
  })
})

describe("calculateNextDueDate", () => {
  it("advances weekly by 7 days", () => {
    const d = new Date(2026, 0, 10)
    const next = calculateNextDueDate(d, "WEEKLY")
    expect(next?.getDate()).toBe(17)
  })

  it("advances quarterly preserving month-end", () => {
    const d = new Date(2026, 0, 31) // Jan 31
    const next = calculateNextDueDate(d, "QUARTERLY")
    expect(next?.getMonth()).toBe(3) // Apr
    expect(next?.getDate()).toBe(30)
  })
})

describe("advanceTaxPeriod", () => {
  it("advances quarter within the same year", () => {
    expect(advanceTaxPeriod("Q1 2026", "QUARTERLY")).toBe("Q2 2026")
  })

  it("rolls over quarter to the next year", () => {
    expect(advanceTaxPeriod("Q4 2025", "QUARTERLY")).toBe("Q1 2026")
  })

  it("advances month within the same year", () => {
    expect(advanceTaxPeriod("Jan 2026", "MONTHLY")).toBe("Feb 2026")
    expect(advanceTaxPeriod("January 2026", "MONTHLY")).toBe("February 2026")
  })

  it("rolls over month to next year", () => {
    expect(advanceTaxPeriod("Dec 2025", "MONTHLY")).toBe("Jan 2026")
  })

  it("advances annual financial year", () => {
    expect(advanceTaxPeriod("FY 2025", "ANNUAL")).toBe("FY 2026")
    expect(advanceTaxPeriod("2025", "ANNUAL")).toBe("2026")
  })
})
