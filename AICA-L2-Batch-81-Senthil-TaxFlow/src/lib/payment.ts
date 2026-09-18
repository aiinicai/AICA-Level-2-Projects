export const FILING_TYPES = ["PAYMENT", "NIL_RETURN", "REFUND_RETURN"] as const
export type FilingType = (typeof FILING_TYPES)[number]

export const REFUND_TYPES = ["CLAIMED", "CARRIED_FORWARD"] as const
export type RefundType = (typeof REFUND_TYPES)[number]

export const CONFIRMATION_STAGES = [
  "PREPARER_SUBMIT",
  "REVIEWER",
  "APPROVER",
  "PREPARER_PAYMENT",
] as const
export type ConfirmationStage = (typeof CONFIRMATION_STAGES)[number]

export const FILING_TYPE_LABELS: Record<FilingType, string> = {
  PAYMENT: "Payment",
  NIL_RETURN: "NIL Return",
  REFUND_RETURN: "Refund Return",
}

export const REFUND_TYPE_LABELS: Record<RefundType, string> = {
  CLAIMED: "Claimed from tax authority",
  CARRIED_FORWARD: "Carried forward for adjustment",
}

export const CONFIRMATION_STAGE_LABELS: Record<ConfirmationStage, string> = {
  PREPARER_SUBMIT: "Amount entered",
  REVIEWER: "Reconfirmed by reviewer",
  APPROVER: "Reconfirmed by approver",
  PREPARER_PAYMENT: "Payment confirmed",
}

export interface PaymentSubmission {
  filingType: string
  amount: number
  currency: string
  refundType?: string | null
}

export function validatePaymentSubmission(input: PaymentSubmission): string[] {
  const errors: string[] = []

  if (!FILING_TYPES.includes(input.filingType as FilingType)) {
    errors.push("Filing type must be PAYMENT, NIL_RETURN, or REFUND_RETURN")
  }

  if (!Number.isFinite(input.amount) || input.amount < 0) {
    errors.push("Amount must be a non-negative number")
  }

  if (input.filingType === "NIL_RETURN" && input.amount !== 0) {
    errors.push("NIL return amount must be 0")
  }

  if (!input.currency || !input.currency.trim()) {
    errors.push("Payment currency is required")
  }

  if (input.filingType === "REFUND_RETURN") {
    if (!input.refundType || !REFUND_TYPES.includes(input.refundType as RefundType)) {
      errors.push("Refund type must be CLAIMED or CARRIED_FORWARD")
    }
  } else if (input.refundType) {
    errors.push("Refund type is only allowed for refund returns")
  }

  return errors
}

export function confirmationStageForStep(step: number): ConfirmationStage {
  return step <= 1 ? "REVIEWER" : "APPROVER"
}
