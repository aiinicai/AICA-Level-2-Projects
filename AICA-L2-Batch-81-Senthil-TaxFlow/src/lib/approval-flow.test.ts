import { describe, it, expect } from "vitest"
import {
  normalizeApprovalFlow,
  requiresReviewer,
  requiresApprover,
  buildApprovalRecords,
  effectiveApprovalFlow,
} from "./approval-flow"

describe("normalizeApprovalFlow", () => {
  it("passes through valid flows", () => {
    expect(normalizeApprovalFlow("NONE")).toBe("NONE")
    expect(normalizeApprovalFlow("ONE_LEVEL")).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("TWO_LEVEL")).toBe("TWO_LEVEL")
  })

  it("defaults missing or unknown values to ONE_LEVEL", () => {
    expect(normalizeApprovalFlow(undefined)).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow(null)).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("")).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("THREE_LEVEL")).toBe("ONE_LEVEL")
  })
})

describe("requiresReviewer", () => {
  it("requires a reviewer for one- and two-level approval only", () => {
    expect(requiresReviewer("NONE")).toBe(false)
    expect(requiresReviewer("ONE_LEVEL")).toBe(true)
    expect(requiresReviewer("TWO_LEVEL")).toBe(true)
  })
})

describe("requiresApprover", () => {
  it("requires an approver only for two-level approval", () => {
    expect(requiresApprover("NONE")).toBe(false)
    expect(requiresApprover("ONE_LEVEL")).toBe(false)
    expect(requiresApprover("TWO_LEVEL")).toBe(true)
  })
})

describe("buildApprovalRecords", () => {
  it("builds no records for NONE", () => {
    expect(buildApprovalRecords("NONE", "u1", "u2")).toEqual([])
  })

  it("builds a step-1 reviewer record for ONE_LEVEL", () => {
    expect(buildApprovalRecords("ONE_LEVEL", "u1", "u2")).toEqual([
      { approverId: "u1", step: 1 },
    ])
  })

  it("builds reviewer then approver records for TWO_LEVEL", () => {
    expect(buildApprovalRecords("TWO_LEVEL", "u1", "u2")).toEqual([
      { approverId: "u1", step: 1 },
      { approverId: "u2", step: 2 },
    ])
  })

  it("omits records when a required assignee is missing", () => {
    expect(buildApprovalRecords("ONE_LEVEL", "", "u2")).toEqual([])
    expect(buildApprovalRecords("ONE_LEVEL", null, "u2")).toEqual([])
    expect(buildApprovalRecords("TWO_LEVEL", "u1", "")).toEqual([{ approverId: "u1", step: 1 }])
  })
})

describe("effectiveApprovalFlow", () => {
  it("uses the form flow when set", () => {
    expect(effectiveApprovalFlow("TWO_LEVEL", "NONE")).toBe("TWO_LEVEL")
    expect(effectiveApprovalFlow("NONE", "TWO_LEVEL")).toBe("NONE")
    expect(effectiveApprovalFlow("ONE_LEVEL", "ONE_LEVEL")).toBe("ONE_LEVEL")
  })

  it("falls back to the entity flow when the form flow is unset", () => {
    expect(effectiveApprovalFlow(undefined, "TWO_LEVEL")).toBe("TWO_LEVEL")
    expect(effectiveApprovalFlow(null, "NONE")).toBe("NONE")
    expect(effectiveApprovalFlow("", "ONE_LEVEL")).toBe("ONE_LEVEL")
  })

  it("defaults to ONE_LEVEL when neither is set", () => {
    expect(effectiveApprovalFlow(undefined, undefined)).toBe("ONE_LEVEL")
    expect(effectiveApprovalFlow(null, null)).toBe("ONE_LEVEL")
  })

  it("ignores an invalid form flow value", () => {
    expect(effectiveApprovalFlow("THREE_LEVEL", "NONE")).toBe("NONE")
  })
})
