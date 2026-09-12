# Compliance Period Anchoring, Overlap Guard & Payment Due Date — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let compliance templates anchor their first generated compliance on a "Period End Date", roll subsequent compliances forward by frequency from the latest generated period, guard against overlapping periods with a clear "generated vs. future-period-not-generated" summary, and capture a payment due date.

**Architecture:** Pure date/bucket logic lives in `src/lib/compliance-period.ts` (unit-tested with Vitest). A shared insert helper in `src/lib/template-compliance.ts` eliminates the 3 duplicated generation insert blocks (bulk route, per-template route, approval auto-gen). The two generation route handlers and `generateFirstCompliance` are rewritten to call `computeGeneration` + `insertGeneratedCompliance`. New template fields are added to the schema, create/edit forms, detail page, and generate dialogs.

**Tech Stack:** Next.js 16 App Router (route handlers + client components), Supabase (direct via `supabaseAdmin` — NOT Prisma at runtime), TypeScript strict, Tailwind + shadcn/ui components, Vitest for unit tests.

**Spec:** `docs/superpowers/specs/2026-08-08-compliance-period-anchoring-design.md`

## Global Constraints

- **Read Next.js docs before coding.** This is a modified Next.js. Before touching any Next.js file, read the relevant guide under `node_modules/next/dist/docs/` (e.g. `01-app/01-getting-started/15-route-handlers.md` for route handlers, `01-app/02-guides/forms.md` for client forms) and heed deprecation notices.
- **Do not add code comments** unless asked.
- Runtime DB access is always `supabaseAdmin` (`@/lib/supabase`); never Prisma Client at runtime.
- Dates: compute with local-time `Date` objects; store to Supabase as ISO strings (`date.toISOString()`); keep `filingMonth` as `"yyyy-MM"` string.
- New template fields: `periodEndDate` (date, required on new templates), `paymentDueDaysAfterPeriodEnd` (int, default = `dueDaysAfterPeriodEnd`).
- Generation summary shape (returned by both generate routes):
  `{ generated, futureNotGenerated, overlapSkipped, errors, summary: { total, created, skipped, futureNotGenerated, overlapSkipped, failed } }`
- Verify each task with: `npx tsc --noEmit` (typecheck), `npm run lint` (lint), and `npx vitest run` (tests, after Task 1).
- Existing conventions: UI components from `src/components/ui/*`; `toDateOnlyString`/`computeDueDate` from `@/lib/compliance-period`; `newId`/`now` from `@/lib/db`.

---

### Task 1: Test tooling + pure period computation helpers

**Files:**
- Modify: `package.json` (add `test` script)
- Create: `vitest.config.ts`
- Create: `src/lib/compliance-period.test.ts`
- Modify: `src/lib/compliance-period.ts` (append helpers)

**Interfaces:**
- Produces:
  - `monthsForFrequency(frequency: string): number` — `MONTHLY`→1, `BI_MONTHLY`→2, `QUARTERLY`→3, `HALF_YEARLY`→6, `ANNUAL`→12, `WEEKLY`→0, `AD_HOC`→0, default→1.
  - `isInMonth(date: Date, filingMonth: string): boolean`
  - `computeFirstPeriod(anchorEnd: Date, frequency: string): { start: Date; end: Date }`
  - `computeNextPeriod(lastEnd: Date, frequency: string): { start: Date; end: Date }`
  - `periodsOverlap(a: { start: Date; end: Date }, b: { start: Date; end: Date }): boolean`

- [x] **Step 1: Install Vitest and add the test script**

Run: `npm install -D vitest`

Add to `package.json` scripts:
```json
"test": "vitest run"
```

Create `vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config"
import path from "node:path"

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
})
```

- [x] **Step 2: Write the failing tests**

Create `src/lib/compliance-period.test.ts`:
```ts
import { describe, it, expect } from "vitest"
import {
  computeFirstPeriod,
  computeNextPeriod,
  periodsOverlap,
  monthsForFrequency,
  isInMonth,
} from "./compliance-period"

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
```

- [x] **Step 3: Run tests to verify they fail**

Run: `npx vitest run src/lib/compliance-period.test.ts`
Expected: FAIL — functions not exported / not defined.

- [x] **Step 4: Implement the helpers**

Append to `src/lib/compliance-period.ts`:
```ts
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
```

- [x] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/lib/compliance-period.test.ts`
Expected: PASS.

- [x] **Step 6: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 7: Commit**

```bash
git add package.json package-lock.json vitest.config.ts src/lib/compliance-period.ts src/lib/compliance-period.test.ts
git commit -m "feat: add period computation helpers and vitest setup"
```

---

### Task 2: `computeGeneration` — period/bucket decision logic

**Files:**
- Modify: `src/lib/compliance-period.ts` (append `computeGeneration`)
- Modify: `src/lib/compliance-period.test.ts`

**Interfaces:**
- Consumes: `computeFirstPeriod`, `computeNextPeriod`, `periodsOverlap`, `isInMonth`, `monthsForFrequency`, `computeDueDate`, `computeTaxPeriod` (all in `src/lib/compliance-period.ts`).
- Produces:
  ```ts
  export type GenerationBucket = "generate" | "future" | "overlap"
  export interface GenerationResult {
    bucket: GenerationBucket
    periodStart?: Date
    periodEnd?: Date
    dueDate?: Date
    paymentDate?: Date
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
    forceFirstPeriod?: boolean
  }): GenerationResult
  ```

**Decision rules (in order):**
1. `AD_HOC` with an existing compliance → `future` ("Ad-hoc compliance already generated for this template").
2. Candidate period:
   - latest compliance end exists → `computeNextPeriod(latestEnd, frequency)`
   - else anchor `periodEndDate` set → `computeFirstPeriod(anchor, frequency)`
   - else (legacy template, no anchor) → `computeTaxPeriod(filingMonth, frequency)`
3. Overlap guard: if the candidate overlaps **any** existing period (invalid dates skipped) → `overlap`.
4. `dueDate = computeDueDate(periodEnd, dueDays ?? 15)`; `paymentDate = computeDueDate(periodEnd, paymentDueDays ?? dueDays ?? 15)`.
5. Bucket `generate` when: (`forceFirstPeriod` and no latest) OR (legacy fallback — no anchor and no latest) OR `dueDate` is within `filingMonth`. Otherwise `future`.

- [x] **Step 1: Write the failing tests**

Append to `src/lib/compliance-period.test.ts`:
```ts
import { computeGeneration } from "./compliance-period"

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
    expect(result.paymentDate).toEqual(new Date(2025, 11, 15))
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
    expect(result.paymentDate).toEqual(new Date(2026, 1, 10))
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
      filingMonth: "2026-02",
      latestComplianceEnd: "2026-01-31",
      existingPeriods: [
        { start: null, end: null },
        { start: "2026-01-01", end: "2026-01-31" },
      ],
    })
    expect(result.bucket).toBe("generate")
    expect(result.periodStart).toEqual(new Date(2026, 1, 1))
  })
})
```

- [x] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/compliance-period.test.ts`
Expected: FAIL — `computeGeneration` not exported.

- [x] **Step 3: Implement `computeGeneration`**

Append to `src/lib/compliance-period.ts`:
```ts
export type GenerationBucket = "generate" | "future" | "overlap"

export interface GenerationResult {
  bucket: GenerationBucket
  periodStart?: Date
  periodEnd?: Date
  dueDate?: Date
  paymentDate?: Date
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
  forceFirstPeriod?: boolean
}): GenerationResult {
  const dueDays = opts.dueDaysAfterPeriodEnd ?? 15
  const paymentDueDays = opts.paymentDueDaysAfterPeriodEnd ?? dueDays
  const latestEnd = opts.latestComplianceEnd ? new Date(opts.latestComplianceEnd) : null
  const hasLatest = !!latestEnd && !isNaN(latestEnd.getTime())

  if (opts.frequency === "AD_HOC" && hasLatest) {
    return { bucket: "future", reason: "Ad-hoc compliance already generated for this template" }
  }

  let candidate: { start: Date; end: Date }
  if (hasLatest) {
    candidate = computeNextPeriod(latestEnd, opts.frequency)
  } else if (opts.periodEndDate) {
    const anchor = new Date(opts.periodEndDate)
    candidate = computeFirstPeriod(isNaN(anchor.getTime()) ? new Date() : anchor, opts.frequency)
  } else {
    candidate = computeTaxPeriod(opts.filingMonth, opts.frequency)
  }

  for (const p of opts.existingPeriods || []) {
    const start = p.start ? new Date(p.start) : null
    const end = p.end ? new Date(p.end) : null
    if (start && end && !isNaN(start.getTime()) && !isNaN(end.getTime())) {
      if (periodsOverlap(candidate, { start, end })) {
        return { bucket: "overlap", reason: "Period overlaps an already-generated compliance" }
      }
    }
  }

  const dueDate = computeDueDate(candidate.end, dueDays)
  const paymentDate = computeDueDate(candidate.end, paymentDueDays)

  const isFirstPeriod = !hasLatest
  const legacyFallback = isFirstPeriod && !opts.periodEndDate

  if ((opts.forceFirstPeriod && isFirstPeriod) || legacyFallback || isInMonth(dueDate, opts.filingMonth)) {
    return { bucket: "generate", periodStart: candidate.start, periodEnd: candidate.end, dueDate, paymentDate }
  }
  return { bucket: "future", reason: `Filing due date ${dueDate.toISOString().slice(0, 10)} is not within ${opts.filingMonth}` }
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/compliance-period.test.ts`
Expected: PASS.

- [x] **Step 5: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/lib/compliance-period.ts src/lib/compliance-period.test.ts
git commit -m "feat: add computeGeneration period and bucket logic"
```

---

### Task 3: Schema — add `periodEndDate` and `paymentDueDaysAfterPeriodEnd`

**Files:**
- Modify: `prisma/schema.prisma`
- Modify: `supabase-migration.sql`

**Interfaces:**
- Produces: `compliance_templates.periodEndDate` (`DateTime?`) and `compliance_templates.paymentDueDaysAfterPeriodEnd` (`Int?`) — column names exactly as written (Supabase reads them via `snake_case`; the code accesses `template.periodEndDate` / `template.paymentDueDaysAfterPeriodEnd`).

- [x] **Step 1: Update the Prisma schema**

In `prisma/schema.prisma`, in `model ComplianceTemplate`, immediately after `dueDaysAfterPeriodEnd Int?` (line 86) add:
```prisma
  periodEndDate            DateTime?
  paymentDueDaysAfterPeriodEnd Int?
```

- [x] **Step 2: Update the Supabase migration SQL**

In `supabase-migration.sql`, add near the other `ALTER TABLE "compliance_templates"` statements:
```sql
ALTER TABLE "compliance_templates" ADD COLUMN IF NOT EXISTS "periodEndDate" TIMESTAMP;
ALTER TABLE "compliance_templates" ADD COLUMN IF NOT EXISTS "paymentDueDaysAfterPeriodEnd" INTEGER;
```

- [x] **Step 3: Apply the migration**

Apply the two `ALTER TABLE` statements to the Supabase project referenced by `NEXT_PUBLIC_SUPABASE_URL` (via the Supabase SQL editor, or the same process used previously for `supabase-migration.sql`). Verify with:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'compliance_templates' AND column_name IN ('periodEndDate', 'paymentDueDaysAfterPeriodEnd');
```
Expected: both rows returned. **Do not proceed past this step if the columns do not exist** — later tasks write these columns.

- [x] **Step 4: Validate Prisma schema**

Run: `npx prisma validate`
Expected: valid.

- [x] **Step 5: Commit**

```bash
git add prisma/schema.prisma supabase-migration.sql
git commit -m "feat: add periodEndDate and paymentDueDaysAfterPeriodEnd to compliance templates"
```

---

### Task 4: Shared insert helper + refactor `generateFirstCompliance`

**Files:**
- Modify: `src/lib/template-compliance.ts`

**Interfaces:**
- Consumes: `computeGeneration`, `GenerationResult` from `@/lib/compliance-period`; `supabaseAdmin` from `@/lib/supabase`; `newId`/`now` from `@/lib/db`; `toDateOnlyString` from `@/lib/compliance-period`.
- Produces:
  ```ts
  export interface GeneratedComplianceInput {
    template: {
      id: string
      templateNumber?: string | null
      version?: number | null
      taxType?: string | null
      formId?: string | null
      countryId?: string | null
      frequency?: string | null
      priority?: string | null
      isRecurring?: boolean | null
      recurringEndDate?: string | null
      notes?: string | null
      preparerId?: string | null
      approverId?: string | null
    }
    entityIds: string[]
    countryId: string
    orgId: string
    userId: string
    filingMonth: string
    generation: { periodStart: Date; periodEnd: Date; dueDate: Date; paymentDate: Date }
  }
  export async function insertGeneratedCompliance(
    input: GeneratedComplianceInput
  ): Promise<{ scheduleId: string; complianceId: string }>
  ```
  Plus: `findLatestCompliance(rows: Array<{ taxPeriodEnd: string | null }>): (typeof rows)[number] | null` — returns the row with the max non-null `taxPeriodEnd`.

- [x] **Step 1: Rewrite `src/lib/template-compliance.ts`**

Replace the whole file body (keep the existing `generateFirstCompliance` export signature but reimplement it). Full file:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { newId, now } from "@/lib/db"
import {
  computeGeneration,
  computeDueDate,
  toDateOnlyString,
  type GenerationResult,
} from "@/lib/compliance-period"

export interface GeneratedComplianceInput {
  template: {
    id: string
    templateNumber?: string | null
    version?: number | null
    taxType?: string | null
    formId?: string | null
    countryId?: string | null
    frequency?: string | null
    priority?: string | null
    isRecurring?: boolean | null
    recurringEndDate?: string | null
    notes?: string | null
    preparerId?: string | null
    approverId?: string | null
  }
  entityIds: string[]
  countryId: string
  orgId: string
  userId: string
  filingMonth: string
  generation: { periodStart: Date; periodEnd: Date; dueDate: Date; paymentDate: Date }
}

export async function insertGeneratedCompliance(
  input: GeneratedComplianceInput
): Promise<{ scheduleId: string; complianceId: string }> {
  const { template, entityIds, countryId, orgId, userId, filingMonth, generation } = input
  const digits = Math.floor(10000 + Math.random() * 90000)
  const complianceId = `TAX-${digits}`
  const scheduleId = newId()

  const { error: scheduleError } = await supabaseAdmin.from("compliance_schedules").insert({
    id: scheduleId,
    orgId,
    complianceId,
    entityId: entityIds[0] || null,
    countryId,
    taxType: template.taxType,
    formId: template.formId || null,
    taxPeriod: `${toDateOnlyString(generation.periodStart)}–${toDateOnlyString(generation.periodEnd)}`,
    taxPeriodStart: generation.periodStart.toISOString(),
    taxPeriodEnd: generation.periodEnd.toISOString(),
    filingMonth,
    frequency: template.frequency,
    dueDate: generation.dueDate.toISOString(),
    paymentDate: generation.paymentDate.toISOString(),
    priority: template.priority || "NORMAL",
    status: "PENDING_PREPARATION",
    isRecurring: template.isRecurring ?? true,
    recurringEndDate: template.recurringEndDate || null,
    notes: template.notes || null,
    templateId: template.id,
    templateVersion: template.version ?? 0,
    updatedAt: now(),
    createdById: userId,
  })
  if (scheduleError) throw scheduleError

  for (const entityId of entityIds) {
    const { error: linkError } = await supabaseAdmin.from("compliance_entities").insert({
      id: newId(),
      complianceId: scheduleId,
      entityId,
    })
    if (linkError) throw linkError
  }

  if (template.preparerId) {
    const { error: assignmentError } = await supabaseAdmin.from("compliance_assignments").insert({
      id: newId(),
      complianceId: scheduleId,
      preparerId: template.preparerId,
      updatedAt: now(),
    })
    if (assignmentError) throw assignmentError
  }

  if (template.approverId) {
    const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert({
      id: newId(),
      complianceId: scheduleId,
      approverId: template.approverId,
      status: "PENDING_APPROVAL",
      updatedAt: now(),
    })
    if (approvalError) throw approvalError
  }

  const { error: activityError } = await supabaseAdmin.from("activities").insert({
    id: newId(),
    complianceId: scheduleId,
    userId,
    action: "CREATED",
    toStatus: "PENDING_PREPARATION",
    comments: `Generated from template ${template.templateNumber} v${template.version} for ${filingMonth}`,
  })
  if (activityError) throw activityError

  return { scheduleId, complianceId }
}

export function findLatestCompliance(
  rows: Array<{ taxPeriodEnd: string | null }>
): (typeof rows)[number] | null {
  return rows.reduce<(typeof rows)[number] | null>((acc, row) => {
    if (!row.taxPeriodEnd) return acc
    if (!acc || new Date(row.taxPeriodEnd) > new Date(acc.taxPeriodEnd as string)) return row
    return acc
  }, null)
}

export async function generateFirstCompliance(
  template: Record<string, unknown>,
  entities: Array<{ entityId: string }>,
  orgId: string,
  userId: string,
  filingMonth: string
) {
  const results: Array<{ entityId: string | null; complianceId: string; status: string }> = []
  const skipped: Array<{ entityId: string | null; reason: string }> = []

  const entityIds = entities.map((e) => e.entityId)
  if (!entityIds.length) {
    return { generated: results, skipped }
  }

  const { data: existingRows } = await supabaseAdmin
    .from("compliance_schedules")
    .select("id, complianceId, taxPeriodStart, taxPeriodEnd")
    .eq("templateId", template.id as string)

  const rows = existingRows || []
  const existingPeriods = rows.map((r) => ({ start: r.taxPeriodStart, end: r.taxPeriodEnd }))
  const latest = findLatestCompliance(rows)

  const generation: GenerationResult = computeGeneration({
    frequency: template.frequency as string,
    periodEndDate: (template.periodEndDate as string | null | undefined) ?? null,
    dueDaysAfterPeriodEnd: template.dueDaysAfterPeriodEnd as number | undefined,
    paymentDueDaysAfterPeriodEnd: template.paymentDueDaysAfterPeriodEnd as number | undefined,
    filingMonth,
    latestComplianceEnd: latest?.taxPeriodEnd ?? null,
    existingPeriods,
    forceFirstPeriod: true,
  })

  if (generation.bucket !== "generate" || !generation.periodStart || !generation.periodEnd || !generation.dueDate || !generation.paymentDate) {
    skipped.push({ entityId: entityIds[0] || null, reason: generation.reason || "Not generated" })
    return { generated: results, skipped }
  }

  const { data: entitiesData } = await supabaseAdmin
    .from("legal_entities")
    .select("id, countryId")
    .in("id", entityIds)
  const countryId = entitiesData?.[0]?.countryId || template.countryId || ""

  await insertGeneratedCompliance({
    template: template as GeneratedComplianceInput["template"],
    entityIds,
    countryId,
    orgId,
    userId,
    filingMonth,
    generation: {
      periodStart: generation.periodStart,
      periodEnd: generation.periodEnd,
      dueDate: generation.dueDate,
      paymentDate: generation.paymentDate,
    },
  })

  results.push({ entityId: entityIds[0] || null, complianceId: "", status: "created" })
  return { generated: results, skipped }
}
```

Note: `generateFirstCompliance` still returns `{ generated, skipped }` so `admin-approve`/`reviewer-approve` callers keep working. `complianceId` is returned as `""` since the insert helper returns it but the original return shape is preserved for compatibility.

- [x] **Step 2: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 3: Verify approval flow still compiles end-to-end**

Run: `npx tsc --noEmit`
Expected: the existing `admin-approve`/`reviewer-approve` route imports (`generateFirstCompliance`) resolve.

- [x] **Step 4: Commit**

```bash
git add src/lib/template-compliance.ts
git commit -m "feat: extract shared compliance insert helper and use rolling period logic at approval"
```

---

### Task 5: Rewrite bulk generation route

**Files:**
- Modify: `src/app/api/templates/generate/route.ts`

**Interfaces:**
- Consumes: `computeGeneration`, `GenerationResult`, `toDateOnlyString` from `@/lib/compliance-period`; `insertGeneratedCompliance` from `@/lib/template-compliance`.
- Produces: POST response with summary shape from Global Constraints. Keeps `skipped` (sum of future + overlap) for compatibility.

- [x] **Step 1: Rewrite the file**

Replace the body of the `POST` function in `src/app/api/templates/generate/route.ts` from the line `const generated: Array<...>` (line 60) through the end of the `POST` function. Keep lines 1–58 (auth, org/role checks, body parsing, template query with filters) unchanged, except update the import on line 5 to:
```ts
import { computeGeneration, toDateOnlyString, type GenerationResult } from "@/lib/compliance-period"
import { insertGeneratedCompliance } from "@/lib/template-compliance"
```

New logic (replacing lines 60–224):
```ts
    const generated: Array<{ templateId: string; templateNumber: string; entityId: string; complianceId: string }> = []
    const futureNotGenerated: Array<{ templateId: string; templateNumber: string; entityId: string; reason: string }> = []
    const overlapSkipped: Array<{ templateId: string; templateNumber: string; entityId: string; reason: string }> = []
    const errors: Array<{ templateId: string; error: string }> = []

    const templateIds = (filteredTemplates || []).map((t: { id: string }) => t.id)

    const { data: existingRows } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, templateId, entityId, taxPeriodStart, taxPeriodEnd")
      .in("templateId", templateIds.length ? templateIds : ["__none__"])

    const existingByKey = new Map<string, Array<Record<string, unknown>>>()
    for (const row of existingRows || []) {
      const key = `${row.templateId}|${row.entityId}`
      const list = existingByKey.get(key) || []
      list.push(row)
      existingByKey.set(key, list)
    }

    const allEntityIds = Array.from(
      new Set((filteredTemplates || []).flatMap((t: Record<string, unknown>) =>
        (t.entities as Array<{ entityId: string }> || []).map((e) => e.entityId)
      ))
    )

    const { data: entityRows } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId")
      .in("id", allEntityIds.length ? allEntityIds : ["__none__"])

    const countryByEntity = new Map<string, string>()
    for (const e of entityRows || []) countryByEntity.set(e.id, e.countryId)

    const [fYear, fMonth] = filingMonth.split("-").map(Number)

    for (const template of filteredTemplates) {
      if (template.recurringEndDate) {
        const endDate = new Date(template.recurringEndDate)
        const filingDate = new Date(fYear, fMonth - 1, 1)
        if (filingDate > endDate) {
          futureNotGenerated.push({
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            entityId: "",
            reason: "Filing month exceeds recurring end date",
          })
          continue
        }
      }

      const templateEntities = (template.entities || []) as Array<{ entityId: string }>

      for (const te of templateEntities) {
        try {
          const rows = existingByKey.get(`${template.id}|${te.entityId}`) || []
          const existingPeriods = rows.map((r) => ({ start: r.taxPeriodStart as string | null, end: r.taxPeriodEnd as string | null }))
          const latest = rows.reduce<(typeof rows)[number] | null>((acc, r) => {
            if (!r.taxPeriodEnd) return acc
            if (!acc || new Date(r.taxPeriodEnd as string) > new Date(acc.taxPeriodEnd as string)) return r
            return acc
          }, null)

          const generation: GenerationResult = computeGeneration({
            frequency: template.frequency as string,
            periodEndDate: (template.periodEndDate as string | null | undefined) ?? null,
            dueDaysAfterPeriodEnd: template.dueDaysAfterPeriodEnd as number | undefined,
            paymentDueDaysAfterPeriodEnd: template.paymentDueDaysAfterPeriodEnd as number | undefined,
            filingMonth,
            latestComplianceEnd: (latest?.taxPeriodEnd as string | null) ?? null,
            existingPeriods,
          })

          if (generation.bucket === "overlap") {
            overlapSkipped.push({
              templateId: template.id,
              templateNumber: template.templateNumber || "N/A",
              entityId: te.entityId,
              reason: generation.reason || "Overlap",
            })
            continue
          }

          if (generation.bucket === "future") {
            futureNotGenerated.push({
              templateId: template.id,
              templateNumber: template.templateNumber || "N/A",
              entityId: te.entityId,
              reason: generation.reason || "Future period",
            })
            continue
          }

          if (!generation.periodStart || !generation.periodEnd || !generation.dueDate || !generation.paymentDate) {
            throw new Error("Generation result missing period or due dates")
          }

          const { complianceId } = await insertGeneratedCompliance({
            template: template as {
              id: string
              templateNumber?: string | null
              version?: number | null
              taxType?: string | null
              formId?: string | null
              countryId?: string | null
              frequency?: string | null
              priority?: string | null
              isRecurring?: boolean | null
              recurringEndDate?: string | null
              notes?: string | null
              preparerId?: string | null
              approverId?: string | null
            },
            entityIds: [te.entityId],
            countryId: countryByEntity.get(te.entityId) || template.countryId,
            orgId,
            userId: session.user.id,
            filingMonth,
            generation: {
              periodStart: generation.periodStart,
              periodEnd: generation.periodEnd,
              dueDate: generation.dueDate,
              paymentDate: generation.paymentDate,
            },
          })

          generated.push({
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            entityId: te.entityId,
            complianceId,
          })
        } catch (err) {
          errors.push({
            templateId: template.id,
            error: err instanceof Error ? err.message : "Unknown error",
          })
        }
      }
    }

    const { error: auditError } = await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "BULK_GENERATE_COMPLIANCES",
      entity: "ComplianceTemplate",
      newValue: JSON.stringify({
        filingMonth,
        generated: generated.length,
        futureNotGenerated: futureNotGenerated.length,
        overlapSkipped: overlapSkipped.length,
        errors: errors.length,
      }),
    })
    if (auditError) throw auditError

    return NextResponse.json({
      data: {
        generated,
        futureNotGenerated,
        overlapSkipped,
        errors,
        summary: {
          total: generated.length + futureNotGenerated.length + overlapSkipped.length + errors.length,
          created: generated.length,
          skipped: futureNotGenerated.length + overlapSkipped.length,
          futureNotGenerated: futureNotGenerated.length,
          overlapSkipped: overlapSkipped.length,
          failed: errors.length,
        },
      },
    })
```

- [x] **Step 2: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 3: Commit**

```bash
git add src/app/api/templates/generate/route.ts
git commit -m "feat: rolling period generation with overlap guard in bulk route"
```

---

### Task 6: Rewrite per-template generation route

**Files:**
- Modify: `src/app/api/templates/[id]/generate/route.ts`

**Interfaces:**
- Consumes: `computeGeneration`, `GenerationResult` from `@/lib/compliance-period`; `insertGeneratedCompliance`, `findLatestCompliance` from `@/lib/template-compliance`.
- Produces: POST response `{ data: { generated, futureNotGenerated, overlapSkipped, errors, summary: { created, skipped, futureNotGenerated, overlapSkipped } } }`. One schedule per template covering all its entities (primary = first entity), preserving the existing single-schedule behavior.

- [x] **Step 1: Rewrite the file**

Replace the body of the `POST` function from the `generated`/`skipped` declarations (line 64) to the end of the function. Keep lines 1–62 unchanged except update the imports:
```ts
import { computeGeneration, type GenerationResult } from "@/lib/compliance-period"
import { insertGeneratedCompliance, findLatestCompliance } from "@/lib/template-compliance"
```

New logic:
```ts
    const templateEntities = (template.entities || []) as Array<{ entityId: string }>
    const entityIds = templateEntities.map((te) => te.entityId)

    const generated: Array<{ entityId: string | null; complianceId: string }> = []
    const futureNotGenerated: Array<{ entityId: string | null; reason: string }> = []
    const overlapSkipped: Array<{ entityId: string | null; reason: string }> = []

    const { data: existingRows } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, taxPeriodStart, taxPeriodEnd")
      .eq("templateId", template.id)

    const rows = existingRows || []
    const latest = findLatestCompliance(rows)

    const generation: GenerationResult = computeGeneration({
      frequency: template.frequency as string,
      periodEndDate: (template.periodEndDate as string | null | undefined) ?? null,
      dueDaysAfterPeriodEnd: template.dueDaysAfterPeriodEnd as number | undefined,
      paymentDueDaysAfterPeriodEnd: template.paymentDueDaysAfterPeriodEnd as number | undefined,
      filingMonth,
      latestComplianceEnd: (latest?.taxPeriodEnd as string | null) ?? null,
      existingPeriods: rows.map((r) => ({ start: r.taxPeriodStart, end: r.taxPeriodEnd })),
    })

    if (generation.bucket === "overlap") {
      overlapSkipped.push({ entityId: entityIds[0] || null, reason: generation.reason || "Overlap" })
      return NextResponse.json({
        data: {
          generated,
          futureNotGenerated,
          overlapSkipped,
          errors: [],
          summary: { created: 0, skipped: 1, futureNotGenerated: 0, overlapSkipped: 1 },
        },
      })
    }

    if (generation.bucket === "future") {
      futureNotGenerated.push({ entityId: entityIds[0] || null, reason: generation.reason || "Future period" })
      return NextResponse.json({
        data: {
          generated,
          futureNotGenerated,
          overlapSkipped,
          errors: [],
          summary: { created: 0, skipped: 1, futureNotGenerated: 1, overlapSkipped: 0 },
        },
      })
    }

    if (!generation.periodStart || !generation.periodEnd || !generation.dueDate || !generation.paymentDate) {
      return NextResponse.json({ error: "Generation result missing period or due dates" }, { status: 500 })
    }

    const { data: entities } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId")
      .in("id", entityIds)

    const { complianceId } = await insertGeneratedCompliance({
      template: template as {
        id: string
        templateNumber?: string | null
        version?: number | null
        taxType?: string | null
        formId?: string | null
        countryId?: string | null
        frequency?: string | null
        priority?: string | null
        isRecurring?: boolean | null
        recurringEndDate?: string | null
        notes?: string | null
        preparerId?: string | null
        approverId?: string | null
      },
      entityIds,
      countryId: entities?.[0]?.countryId || template.countryId,
      orgId,
      userId: session.user.id,
      filingMonth,
      generation: {
        periodStart: generation.periodStart,
        periodEnd: generation.periodEnd,
        dueDate: generation.dueDate,
        paymentDate: generation.paymentDate,
      },
    })

    generated.push({ entityId: entityIds[0] || null, complianceId })

    return NextResponse.json({
      data: {
        generated,
        futureNotGenerated,
        overlapSkipped,
        errors: [],
        summary: {
          created: generated.length,
          skipped: futureNotGenerated.length + overlapSkipped.length,
          futureNotGenerated: futureNotGenerated.length,
          overlapSkipped: overlapSkipped.length,
        },
      },
    })
```

- [x] **Step 2: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 3: Commit**

```bash
git add src/app/api/templates/[id]/generate/route.ts
git commit -m "feat: rolling period generation with overlap guard in per-template route"
```

---

### Task 7: Template create/update API accepts new fields

**Files:**
- Modify: `src/app/api/templates/route.ts` (POST)
- Modify: `src/app/api/templates/[id]/route.ts` (PUT)
- Modify: `src/app/api/templates/[id]/admin-approve/route.ts` (snapshot object only)

- [x] **Step 1: Accept new fields on POST `/api/templates`**

In `src/app/api/templates/route.ts` POST, update the destructure (line 102–106) to include:
```ts
    const {
      entityIds, taxType, formId, countryId, frequency, dueDaysAfterPeriodEnd,
      periodEndDate, paymentDueDaysAfterPeriodEnd,
      priority, isRecurring, recurringEndDate, notes,
      preparerId, approverId,
    } = body
```
And add to the insert object (after `dueDaysAfterPeriodEnd`):
```ts
        periodEndDate: periodEndDate ? new Date(periodEndDate).toISOString() : null,
        paymentDueDaysAfterPeriodEnd: paymentDueDaysAfterPeriodEnd ?? null,
```

- [x] **Step 2: Accept new fields on PUT `/api/templates/[id]`**

In `src/app/api/templates/[id]/route.ts` PUT:
- Add `"paymentDueDaysAfterPeriodEnd"` to the `fields` array (line 119–122):
```ts
    const fields = [
      "taxType", "formId", "countryId", "frequency", "dueDaysAfterPeriodEnd",
      "paymentDueDaysAfterPeriodEnd",
      "priority", "isRecurring", "notes", "preparerId", "approverId",
    ]
```
- Add date handling after the `recurringEndDate` block (line 126–128):
```ts
    if (body.periodEndDate !== undefined) {
      updates.periodEndDate = body.periodEndDate ? new Date(body.periodEndDate).toISOString() : null
    }
```

- [x] **Step 3: Include new fields in the approval snapshot**

In `src/app/api/templates/[id]/admin-approve/route.ts`, extend the `snapshot` object (line 82–88) to:
```ts
    const snapshot = {
      taxType: approved.taxType, formId: approved.formId, countryId: approved.countryId,
      frequency: approved.frequency, dueDaysAfterPeriodEnd: approved.dueDaysAfterPeriodEnd,
      periodEndDate: approved.periodEndDate, paymentDueDaysAfterPeriodEnd: approved.paymentDueDaysAfterPeriodEnd,
      priority: approved.priority,
      isRecurring: approved.isRecurring, recurringEndDate: approved.recurringEndDate,
      notes: approved.notes, preparerId: approved.preparerId, approverId: approved.approverId,
      entityIds: (existing.entities || []).map((e: { entityId: string }) => e.entityId),
    }
```

- [x] **Step 4: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 5: Commit**

```bash
git add src/app/api/templates/route.ts "src/app/api/templates/[id]/route.ts" "src/app/api/templates/[id]/admin-approve/route.ts"
git commit -m "feat: accept period end date and payment due days in template APIs"
```

---

### Task 8: Create template form — Period End Date + Payment Due Days

**Files:**
- Modify: `src/app/master/compliance-templates/create/page.tsx`

**Interfaces:**
- Produces form fields `periodEndDate` (date string `yyyy-MM-dd`, required) and `paymentDueDaysAfterPeriodEnd` (number string), sent to `POST /api/templates`.

- [x] **Step 1: Add state**

In `create/page.tsx`, after `const [dueDaysAfterPeriodEnd, setDueDaysAfterPeriodEnd] = useState("")` (line 80) add:
```ts
  const [periodEndDate, setPeriodEndDate] = useState("")
  const [paymentDueDaysAfterPeriodEnd, setPaymentDueDaysAfterPeriodEnd] = useState("")
```

- [x] **Step 2: Add validation**

In `handleSubmit`, change the first validation (line 172) to include the period end date:
```ts
    if (entityIds.length === 0 || !taxType || !countryId || !frequency || !periodEndDate) {
      toast({
        title: "Validation Error",
        description: "Please select at least one entity, a tax type, a country, a frequency, and a period end date",
        variant: "destructive",
      })
      return
    }
```
Add after the existing days-to-file validation block (line 187):
```ts
    if (paymentDueDaysAfterPeriodEnd && (Number(paymentDueDaysAfterPeriodEnd) < 1 || Number(paymentDueDaysAfterPeriodEnd) > 365)) {
      toast({
        title: "Validation Error",
        description: "Payment due days must be between 1 and 365",
        variant: "destructive",
      })
      return
    }
```

- [x] **Step 3: Include new fields in the request body**

In `handleSubmit`, add to `body` (after `dueDaysAfterPeriodEnd`):
```ts
        periodEndDate,
        paymentDueDaysAfterPeriodEnd: paymentDueDaysAfterPeriodEnd ? Number(paymentDueDaysAfterPeriodEnd) : undefined,
```

- [x] **Step 4: Restructure the form layout**

Replace the frequency grid block (lines 324–370) — the `<div className="grid grid-cols-3 gap-4">` containing Frequency, Days to File, and Priority — with:

```tsx
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="periodEndDate">
                  Period End Date <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="periodEndDate"
                  type="date"
                  value={periodEndDate}
                  onChange={(e) => setPeriodEndDate(e.target.value)}
                  required
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  The date up to which the return is filed. Used to anchor the first compliance.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="frequency">
                  Frequency <span className="text-red-500">*</span>
                </Label>
                <Select value={frequency} onValueChange={setFrequency} required>
                  <SelectTrigger id="frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    {FREQUENCY_OPTIONS.map((f) => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dueDaysAfterPeriodEnd">Days to File</Label>
                <Input
                  id="dueDaysAfterPeriodEnd"
                  type="number"
                  min={1}
                  max={365}
                  placeholder="e.g. 15"
                  value={dueDaysAfterPeriodEnd}
                  onChange={(e) => {
                    setDueDaysAfterPeriodEnd(e.target.value)
                    if (!paymentDueDaysAfterPeriodEnd) setPaymentDueDaysAfterPeriodEnd(e.target.value)
                  }}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Days available to file after the tax period ends.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="paymentDueDaysAfterPeriodEnd">Payment Due Days</Label>
                <Input
                  id="paymentDueDaysAfterPeriodEnd"
                  type="number"
                  min={1}
                  max={365}
                  placeholder="e.g. 15"
                  value={paymentDueDaysAfterPeriodEnd}
                  onChange={(e) => setPaymentDueDaysAfterPeriodEnd(e.target.value)}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Days after the tax period ends by which payment is due. Defaults to Days to File.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger id="priority">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_OPTIONS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
```

- [x] **Step 5: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 6: Commit**

```bash
git add src/app/master/compliance-templates/create/page.tsx
git commit -m "feat: add period end date and payment due days to create template form"
```

---

### Task 9: Edit template form — Period End Date + Payment Due Days

**Files:**
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `periodEndDate: string | null`, `paymentDueDaysAfterPeriodEnd: number | null` from `GET /api/templates/[id]`.
- Produces: PUT body fields `periodEndDate`, `paymentDueDaysAfterPeriodEnd`.

- [x] **Step 1: Extend the `TemplateDetail` interface**

Add to `TemplateDetail` (after `dueDaysAfterPeriodEnd`, line 75):
```ts
  periodEndDate: string | null
  paymentDueDaysAfterPeriodEnd: number | null
```

- [x] **Step 2: Add state**

After `const [dueDaysAfterPeriodEnd, setDueDaysAfterPeriodEnd] = useState("")` (line 120) add:
```ts
  const [periodEndDate, setPeriodEndDate] = useState("")
  const [paymentDueDaysAfterPeriodEnd, setPaymentDueDaysAfterPeriodEnd] = useState("")
```

- [x] **Step 3: Load values in the fetch effect**

After `setDueDaysAfterPeriodEnd(...)` (line 195) add:
```ts
        setPeriodEndDate(d.periodEndDate ? d.periodEndDate.slice(0, 10) : "")
        setPaymentDueDaysAfterPeriodEnd(
          d.paymentDueDaysAfterPeriodEnd != null ? String(d.paymentDueDaysAfterPeriodEnd) : ""
        )
```

- [x] **Step 4: Add validation**

After the days-to-file validation block (line 251) add:
```ts
    if (paymentDueDaysAfterPeriodEnd && (Number(paymentDueDaysAfterPeriodEnd) < 1 || Number(paymentDueDaysAfterPeriodEnd) > 365)) {
      toast({
        title: "Validation Error",
        description: "Payment due days must be between 1 and 365",
        variant: "destructive",
      })
      return
    }
```
Also add `|| !periodEndDate` to the first validation condition (line 236):
```ts
    if (entityIds.length === 0 || !taxType || !countryId || !frequency || !periodEndDate) {
```
and update its message to "Please select at least one entity, a tax type, a country, a frequency, and a period end date".

- [x] **Step 5: Include new fields in the request body**

Add to `body` (after `dueDaysAfterPeriodEnd`, line 261):
```ts
        periodEndDate,
        paymentDueDaysAfterPeriodEnd: paymentDueDaysAfterPeriodEnd ? Number(paymentDueDaysAfterPeriodEnd) : null,
```

- [x] **Step 6: Restructure the form layout**

Apply the same layout change as Task 8 Step 4, but every `Select`/`Input` additionally gets `disabled={readOnly}`. The grid currently at lines 443–490 (Frequency, Days to File, Priority) becomes: a `grid-cols-2` row with **Period End Date** (date input, `disabled={readOnly}`) and **Frequency** (`disabled={readOnly}`), then a `grid-cols-3` row with **Days to File** (add `disabled={readOnly}` and the payment-sync `onChange`), **Payment Due Days** (`disabled={readOnly}`), and **Priority** (`disabled={readOnly}`). Copy the JSX from Task 8 Step 4 and add `disabled={readOnly}` to each control.

- [x] **Step 7: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 8: Commit**

```bash
git add "src/app/master/compliance-templates/[id]/edit/page.tsx"
git commit -m "feat: add period end date and payment due days to edit template form"
```

---

### Task 10: Template detail page — display new fields

**Files:**
- Modify: `src/app/master/compliance-templates/[id]/page.tsx`

**Interfaces:**
- Consumes: `periodEndDate: string | null`, `paymentDueDaysAfterPeriodEnd: number | null` from `GET /api/templates/[id]`.

- [x] **Step 1: Extend the `TemplateDetail` interface**

Add after `dueDaysAfterPeriodEnd` (line 123):
```ts
  periodEndDate: string | null
  paymentDueDaysAfterPeriodEnd: number | null
```

- [x] **Step 2: Show the fields in the Template Info card**

After the `dueDaysAfterPeriodEnd` block (lines 583–587) add:
```tsx
            {data.periodEndDate && (
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                Period End: {formatDate(data.periodEndDate)}
              </p>
            )}
            {data.paymentDueDaysAfterPeriodEnd != null && (
              <p className="text-xs text-[var(--color-muted-foreground)] mt-1">
                Payment Due: {data.paymentDueDaysAfterPeriodEnd} day(s) after period end
              </p>
            )}
```

- [x] **Step 3: Show the fields in the Overview grid**

After the "Days to File" Overview block (lines 721–726) add:
```tsx
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Period End Date</Label>
                  <p className="font-medium">
                    {data.periodEndDate ? formatDate(data.periodEndDate) : "—"}
                  </p>
                </div>
                <div>
                  <Label className="text-[var(--color-muted-foreground)]">Payment Due Days</Label>
                  <p className="font-medium">
                    {data.paymentDueDaysAfterPeriodEnd != null
                      ? `${data.paymentDueDaysAfterPeriodEnd} day(s) after period end`
                      : "—"}
                  </p>
                </div>
```

- [x] **Step 4: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 5: Commit**

```bash
git add "src/app/master/compliance-templates/[id]/page.tsx"
git commit -m "feat: show period end date and payment due days on template detail"
```

---

### Task 11: Generate dialogs — two-line summary message

**Files:**
- Modify: `src/app/master/compliance-templates/page.tsx`
- Modify: `src/app/master/compliance-templates/[id]/page.tsx`

**Interfaces:**
- Consumes: `summary: { created, skipped, futureNotGenerated, overlapSkipped, failed }` (list page) and `{ created, skipped, futureNotGenerated, overlapSkipped }` (detail page).

- [x] **Step 1: List page — update `BulkSummary` interface**

In `src/app/master/compliance-templates/page.tsx`, change `BulkSummary` (lines 119–124) to:
```ts
interface BulkSummary {
  total: number
  created: number
  skipped: number
  failed: number
  futureNotGenerated: number
  overlapSkipped: number
}
```

- [x] **Step 2: List page — update bulk result display**

Replace the bulk summary block (lines 662–669) with:
```tsx
              {bulkResult && (
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm space-y-1">
                  <p className="font-medium mb-1">Generation summary</p>
                  <p>{bulkResult.created} current month due compliance(s) generated</p>
                  <p>
                    {bulkResult.futureNotGenerated + bulkResult.overlapSkipped} compliance(s)
                    for future period not generated
                  </p>
                  {bulkResult.failed > 0 && <p>{bulkResult.failed} failed</p>}
                </div>
              )}
```

- [x] **Step 3: List page — update bulk toast**

Replace the success toast in `handleBulkGenerate` (lines 257–260) with:
```ts
      toast({
        title: "Success",
        description:
          `${summary?.created ?? 0} current month due compliance(s) generated; ` +
          `${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0)} compliance(s) for future period not generated`,
      })
```

- [x] **Step 4: List page — update row dialog result display**

Update the row result type (line 163) to:
```ts
  const [rowResult, setRowResult] = useState<{
    created: number
    skipped: number
    futureNotGenerated: number
    overlapSkipped: number
  } | null>(null)
```
Update the row summary block (lines 704–710) to:
```tsx
              {rowResult && (
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm space-y-1">
                  <p className="font-medium mb-1">Generation summary</p>
                  <p>{rowResult.created} current month due compliance(s) generated</p>
                  <p>
                    {rowResult.futureNotGenerated + rowResult.overlapSkipped} compliance(s)
                    for future period not generated
                  </p>
                </div>
              )}
```
And the row toast (lines 284–287) to:
```ts
      toast({
        title: "Success",
        description:
          `${summary?.created ?? 0} current month due compliance(s) generated; ` +
          `${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0)} compliance(s) for future period not generated`,
      })
```

- [x] **Step 5: Detail page — update generate result display**

In `src/app/master/compliance-templates/[id]/page.tsx`, change the state (line 211) to:
```ts
  const [generateResult, setGenerateResult] = useState<{
    created: number
    skipped: number
    futureNotGenerated: number
    overlapSkipped: number
  } | null>(null)
```
Update the summary block (lines 1026–1032) to:
```tsx
                {generateResult && (
                  <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-secondary)]/40 p-3 text-sm space-y-1">
                    <p className="font-medium mb-1">Generation summary</p>
                    <p>{generateResult.created} current month due compliance(s) generated</p>
                    <p>
                      {generateResult.futureNotGenerated + generateResult.overlapSkipped} compliance(s)
                      for future period not generated
                    </p>
                  </div>
                )}
```
Update the toast (lines 307–310) to:
```ts
        toast({
          title: "Success",
          description:
            `${summary?.created ?? 0} current month due compliance(s) generated; ` +
            `${(summary?.futureNotGenerated ?? 0) + (summary?.overlapSkipped ?? 0)} compliance(s) for future period not generated`,
        })
```

- [x] **Step 6: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 7: Commit**

```bash
git add src/app/master/compliance-templates/page.tsx "src/app/master/compliance-templates/[id]/page.tsx"
git commit -m "feat: show generated vs future-period-not-generated summary in generate dialogs"
```

---

### Task 12: End-to-end verification

**Files:** (none — manual verification)

**Interfaces:**
- Verifies: full feature against the running dev server and the Supabase project (columns from Task 3 must already be applied).

- [x] **Step 1: Run the test suite**

Run: `npx vitest run`
Expected: all pass.

- [x] **Step 2: Typecheck and lint**

Run: `npx tsc --noEmit`
Run: `npm run lint`
Expected: no errors.

- [x] **Step 3: Start the dev server**

Run: `npm run dev`
Expected: app serves at http://localhost:3000.

- [x] **Step 4: Verify template creation**

Navigate to `/master/compliance-templates/create`. Confirm:
- Period End Date field appears before Frequency and is required.
- Payment Due Days auto-fills to match Days to File when Days to File is entered.
- Submitting persists the template (check Supabase row has `periodEndDate` and `paymentDueDaysAfterPeriodEnd`).

- [x] **Step 5: Verify first-compliance seeding on approval**

Approve the template as admin. Confirm a compliance is created whose `taxPeriodStart`/`taxPeriodEnd` matches the anchor (e.g. Period End `2025-11-30` + QUARTERLY → `2025-09-01`–`2025-11-30`), `dueDate` = period end + days, and `paymentDate` = period end + payment due days.

- [x] **Step 6: Verify rolling + future-period behavior**

From the template list, run "Generate for Month" for a month where the next compliance is not yet due (e.g. Jan 2026 after the Sep–Nov quarter). Confirm the summary shows "0 current month due compliance(s) generated" and "1 compliance(s) for future period not generated", and no new compliance row is created.

Run it again for the month in which the next compliance is due. Confirm it creates the contiguous next period (e.g. `2025-12-01`–`2026-02-28`).

- [x] **Step 7: Verify overlap guard**

Manually insert a compliance via the Supabase dashboard for the same template+entity with a period overlapping an existing one, then run "Generate for Month". Confirm the response reports it under the overlap/skipped count and no duplicate row is created.

- [x] **Step 8: Verify payment date populated**

Open a generated compliance in `/compliance/[id]`. Confirm the Payment Date shown equals period end + payment due days.

- [x] **Step 9: Report findings**

Summarize verification results back to the user, including any issues found.
