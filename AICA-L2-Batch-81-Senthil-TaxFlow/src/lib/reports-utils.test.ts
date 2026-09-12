import { describe, it, expect } from "vitest"
import {
  formatDate,
  dayDiff,
  getFilingTimeliness,
  getPaymentTimeliness,
  getPaymentUrgency,
} from "./reports-utils"

describe("reports-utils", () => {
  describe("formatDate", () => {
    it("returns formatted ISO date string YYYY-MM-DD", () => {
      expect(formatDate("2025-06-15T10:30:00.000Z")).toBe("2025-06-15")
    })

    it("returns empty string for null or empty values", () => {
      expect(formatDate(null)).toBe("")
      expect(formatDate(undefined)).toBe("")
      expect(formatDate("")).toBe("")
    })
  })

  describe("dayDiff", () => {
    it("returns positive days difference when actual date is past due date", () => {
      const actual = "2025-06-20T00:00:00Z"
      const due = "2025-06-15T00:00:00Z"
      expect(dayDiff(actual, due)).toBe("5")
    })

    it("returns 0 when actual date is earlier than or equal to due date", () => {
      const actual = "2025-06-10T00:00:00Z"
      const due = "2025-06-15T00:00:00Z"
      expect(dayDiff(actual, due)).toBe("0")
    })

    it("returns empty string when either date is missing", () => {
      expect(dayDiff(null, "2025-06-15")).toBe("")
      expect(dayDiff("2025-06-15", null)).toBe("")
    })
  })

  describe("getFilingTimeliness", () => {
    it("returns On-Time when filedAt <= dueDate", () => {
      expect(getFilingTimeliness("2025-06-14T00:00:00Z", "2025-06-15T00:00:00Z")).toBe("On-Time")
      expect(getFilingTimeliness("2025-06-15T00:00:00Z", "2025-06-15T00:00:00Z")).toBe("On-Time")
    })

    it("returns Delayed when filedAt > dueDate", () => {
      expect(getFilingTimeliness("2025-06-18T00:00:00Z", "2025-06-15T00:00:00Z")).toBe("Delayed")
    })

    it("returns Overdue when not filed and past due date", () => {
      expect(getFilingTimeliness(null, "2020-01-01T00:00:00Z")).toBe("Overdue")
    })

    it("returns Pending when not filed and due in future", () => {
      expect(getFilingTimeliness(null, "2099-01-01T00:00:00Z")).toBe("Pending")
    })
  })

  describe("getPaymentTimeliness", () => {
    it("returns N/A when requiresPayment is false", () => {
      expect(getPaymentTimeliness(false, null, null)).toBe("N/A")
      expect(getPaymentTimeliness(false, "2025-06-15", "2025-06-15")).toBe("N/A")
    })

    it("returns On-Time when paymentDate <= paymentDueDate", () => {
      expect(getPaymentTimeliness(true, "2025-06-14T00:00:00Z", "2025-06-15T00:00:00Z")).toBe("On-Time")
    })

    it("returns Delayed when paymentDate > paymentDueDate", () => {
      expect(getPaymentTimeliness(true, "2025-06-18T00:00:00Z", "2025-06-15T00:00:00Z")).toBe("Delayed")
    })

    it("returns Overdue when unpaid and paymentDueDate has passed", () => {
      expect(getPaymentTimeliness(true, null, "2020-01-01T00:00:00Z")).toBe("Overdue")
    })

    it("returns Pending when unpaid and paymentDueDate is in future", () => {
      expect(getPaymentTimeliness(true, null, "2099-01-01T00:00:00Z")).toBe("Pending")
    })
  })

  describe("getPaymentUrgency", () => {
    const mockToday = new Date("2025-06-15T00:00:00.000Z")

    it("returns Overdue when target date is in past", () => {
      const res = getPaymentUrgency("2025-06-10T00:00:00.000Z", null, mockToday)
      expect(res.urgency).toBe("Overdue")
      expect(res.daysLeft).toContain("Late")
    })

    it("returns Due Today when target date matches today", () => {
      const res = getPaymentUrgency("2025-06-15T00:00:00.000Z", null, mockToday)
      expect(res.urgency).toBe("Due Today")
      expect(res.daysLeft).toBe("0d")
    })

    it("returns Due in 7 Days when within a week", () => {
      const res = getPaymentUrgency("2025-06-20T00:00:00.000Z", null, mockToday)
      expect(res.urgency).toBe("Due in 7 Days")
      expect(res.daysLeft).toBe("5d")
    })

    it("returns Due in 30 Days when within a month", () => {
      const res = getPaymentUrgency("2025-07-05T00:00:00.000Z", null, mockToday)
      expect(res.urgency).toBe("Due in 30 Days")
      expect(res.daysLeft).toBe("20d")
    })

    it("returns Future (> 30 Days) when more than 30 days away", () => {
      const res = getPaymentUrgency("2025-08-15T00:00:00.000Z", null, mockToday)
      expect(res.urgency).toBe("Future (> 30 Days)")
    })
  })
})
