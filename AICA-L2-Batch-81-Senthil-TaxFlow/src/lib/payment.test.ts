import { describe, it, expect } from "vitest"
import {
  validatePaymentSubmission,
  confirmationStageForStep,
  FILING_TYPE_LABELS,
  REFUND_TYPE_LABELS,
  CONFIRMATION_STAGE_LABELS,
} from "./payment"

describe("validatePaymentSubmission", () => {
  it("accepts a valid payment filing", () => {
    expect(
      validatePaymentSubmission({ filingType: "PAYMENT", amount: 1500.5, currency: "USD" })
    ).toEqual([])
  })

  it("accepts a NIL return with amount 0", () => {
    expect(
      validatePaymentSubmission({ filingType: "NIL_RETURN", amount: 0, currency: "EUR" })
    ).toEqual([])
  })

  it("rejects a NIL return with a non-zero amount", () => {
    expect(
      validatePaymentSubmission({ filingType: "NIL_RETURN", amount: 100, currency: "EUR" })
    ).toContain("NIL return amount must be 0")
  })

  it("accepts a refund return claimed from the tax authority", () => {
    expect(
      validatePaymentSubmission({
        filingType: "REFUND_RETURN",
        amount: 250,
        currency: "GBP",
        refundType: "CLAIMED",
      })
    ).toEqual([])
  })

  it("accepts a refund return carried forward", () => {
    expect(
      validatePaymentSubmission({
        filingType: "REFUND_RETURN",
        amount: 80,
        currency: "USD",
        refundType: "CARRIED_FORWARD",
      })
    ).toEqual([])
  })

  it("rejects a refund return without a refund type", () => {
    const errors = validatePaymentSubmission({
      filingType: "REFUND_RETURN",
      amount: 50,
      currency: "USD",
    })
    expect(errors).toContain("Refund type must be CLAIMED or CARRIED_FORWARD")
  })

  it("rejects a refund return with an invalid refund type", () => {
    const errors = validatePaymentSubmission({
      filingType: "REFUND_RETURN",
      amount: 50,
      currency: "USD",
      refundType: "REFUNDED",
    })
    expect(errors).toContain("Refund type must be CLAIMED or CARRIED_FORWARD")
  })

  it("rejects a refund type on a non-refund filing", () => {
    expect(
      validatePaymentSubmission({
        filingType: "PAYMENT",
        amount: 100,
        currency: "USD",
        refundType: "CLAIMED",
      })
    ).toContain("Refund type is only allowed for refund returns")
  })

  it("rejects an invalid filing type", () => {
    expect(
      validatePaymentSubmission({ filingType: "GIFT", amount: 100, currency: "USD" })
    ).toContain("Filing type must be PAYMENT, NIL_RETURN, or REFUND_RETURN")
  })

  it("rejects a negative amount", () => {
    expect(
      validatePaymentSubmission({ filingType: "PAYMENT", amount: -1, currency: "USD" })
    ).toContain("Amount must be a non-negative number")
  })

  it("rejects a missing currency", () => {
    expect(
      validatePaymentSubmission({ filingType: "PAYMENT", amount: 100, currency: "" })
    ).toContain("Payment currency is required")
  })
})

describe("confirmationStageForStep", () => {
  it("maps step 1 to the reviewer stage", () => {
    expect(confirmationStageForStep(1)).toBe("REVIEWER")
  })

  it("maps step 2 to the approver stage", () => {
    expect(confirmationStageForStep(2)).toBe("APPROVER")
  })
})

describe("labels", () => {
  it("provides a label for every filing type", () => {
    expect(Object.keys(FILING_TYPE_LABELS).sort()).toEqual(["NIL_RETURN", "PAYMENT", "REFUND_RETURN"])
  })

  it("provides a label for every refund type", () => {
    expect(Object.keys(REFUND_TYPE_LABELS).sort()).toEqual(["CARRIED_FORWARD", "CLAIMED"])
  })

  it("provides a label for every confirmation stage", () => {
    expect(Object.keys(CONFIRMATION_STAGE_LABELS).sort()).toEqual([
      "APPROVER",
      "PREPARER_PAYMENT",
      "PREPARER_SUBMIT",
      "REVIEWER",
    ])
  })
})
