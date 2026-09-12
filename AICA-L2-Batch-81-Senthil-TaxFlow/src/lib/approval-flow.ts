export type ApprovalFlow = "NONE" | "ONE_LEVEL" | "TWO_LEVEL"

export interface ApprovalRecord {
  approverId: string
  step: number
}

export const APPROVAL_FLOWS: ApprovalFlow[] = ["NONE", "ONE_LEVEL", "TWO_LEVEL"]

export const APPROVAL_FLOW_OPTIONS: Array<{ value: ApprovalFlow; label: string }> = [
  { value: "NONE", label: "None (no approval)" },
  { value: "ONE_LEVEL", label: "One-Level (Reviewer only)" },
  { value: "TWO_LEVEL", label: "Two-Level (Reviewer then Approver)" },
]

export function normalizeApprovalFlow(value?: string | null): ApprovalFlow {
  return APPROVAL_FLOWS.includes(value as ApprovalFlow) ? (value as ApprovalFlow) : "ONE_LEVEL"
}

export function effectiveApprovalFlow(
  formFlow?: string | null,
  entityFlow?: string | null
): ApprovalFlow {
  if (formFlow && APPROVAL_FLOWS.includes(formFlow as ApprovalFlow)) {
    return formFlow as ApprovalFlow
  }
  return normalizeApprovalFlow(entityFlow)
}

export function requiresReviewer(flow: ApprovalFlow): boolean {
  return flow === "ONE_LEVEL" || flow === "TWO_LEVEL"
}

export function requiresApprover(flow: ApprovalFlow): boolean {
  return flow === "TWO_LEVEL"
}

export function buildApprovalRecords(
  flow: ApprovalFlow,
  reviewerId?: string | null,
  approverId?: string | null
): ApprovalRecord[] {
  const records: ApprovalRecord[] = []
  if (requiresReviewer(flow) && reviewerId) {
    records.push({ approverId: reviewerId, step: 1 })
  }
  if (requiresApprover(flow) && approverId) {
    records.push({ approverId, step: 2 })
  }
  return records
}
