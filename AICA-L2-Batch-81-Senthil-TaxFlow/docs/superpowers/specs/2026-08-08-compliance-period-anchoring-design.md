# Compliance Template Period Anchoring, Overlap Guard & Payment Due Date

Date: 2026-08-08
Status: Approved

## Problem

1. Compliance generation is anchored on a **filing month** (`yyyy-MM`). The tax period is
   derived from the frequency using calendar boundaries (e.g. quarterly always = Jan–Mar,
   Apr–Jun). There is no way for the admin to specify "the date up to which the return is
   being filed."
2. The duplicate check is an exact match on `(entityId, filingMonth, templateId)`. It does
   **not** detect overlapping periods, so an admin can accidentally generate a compliance
   whose tax period overlaps an already-generated one.
3. There is no payment due date captured on the template.

## Goal

- Add a **Period End Date** to the compliance template — the date up to which the return
  is being filed. It seeds the **first** generated compliance only. Every later compliance
  rolls forward from the latest generated compliance's period end by the frequency.
- Guard generation against **period overlaps**; report a clear summary:
  "Y current month due compliance(s) generated" and "X compliance(s) for future period
  not generated."
- Add a **Payment Due** field to the template (days after period end), defaulting to the
  same value as Days to File, and populate `compliance_schedules.paymentDate` on
  generation.

## Data model

### `compliance_templates` (new columns)

| Column | Type | Notes |
|---|---|---|
| `periodEndDate` | `DateTime?` | Date up to which the return is filed. Seeds first compliance only. Required on new templates (validation). |
| `paymentDueDaysAfterPeriodEnd` | `Int?` | Payment offset in days. Defaults to `dueDaysAfterPeriodEnd` at creation. |

Mirror in `prisma/schema.prisma` (`ComplianceTemplate`) and `supabase-migration.sql`
(`ALTER TABLE compliance_templates ADD COLUMN IF NOT EXISTS ...`).

### `compliance_schedules`

No schema change. Populate the existing `paymentDate` column on generation:
`paymentDate = periodEnd + paymentDueDaysAfterPeriodEnd`.

`AD_HOC` frequency: single generation from the anchor; if a compliance already exists for
the template, generation is skipped (no cadence to roll).

## Period computation (`src/lib/compliance-period.ts` — new helpers)

- `addMonthsClamped(date, months)` — month arithmetic clamping to end-of-month
  (e.g. Jan 31 + 1 month → Feb 28/29).
- `monthsForFrequency(frequency)` — `WEEKLY` → 7 days, `MONTHLY` → 1, `BI_MONTHLY` → 2,
  `QUARTERLY` → 3, `HALF_YEARLY` → 6, `ANNUAL` → 12.
- `computeFirstPeriod(anchorEnd, frequency)` — `start = addMonthsClamped(anchorEnd, -n) + 1d; end = anchorEnd`.
- `computeNextPeriod(lastEnd, frequency)` — `start = lastEnd + 1d; end = addMonthsClamped(start, n) - 1d`.
- `periodsOverlap(aStart, aEnd, bStart, bEnd)` — boolean overlap check.

## Generation logic

Applies to: bulk `/api/templates/generate`, per-template `/api/templates/[id]/generate`,
and approval-time `generateFirstCompliance` (`src/lib/template-compliance.ts`).

Input stays **"Generate for Month M"** (`yyyy-MM`). For each template + entity:

1. Fetch the **latest existing compliance** for `(templateId, entityId)` ordered by
   `taxPeriodEnd`.
2. **No compliance exists** → first period from `template.periodEndDate` (anchor). If
   `periodEndDate` is unset (legacy template), fall back to the existing
   `computeTaxPeriod(M, frequency)` and generate it (backward compatibility).
3. **Compliance exists** → next period via `computeNextPeriod(latestEnd, frequency)`.
4. `dueDate = periodEnd + dueDaysAfterPeriodEnd` (default 15);
   `paymentDate = periodEnd + paymentDueDaysAfterPeriodEnd` (default = dueDays value).
5. **Overlap guard** — if the computed period overlaps *any* existing compliance period
   for that template+entity → skip, reason "period overlaps already-generated compliance".
6. **Month check** — if `dueDate` falls within month M → **generate** (bucket:
   current-month due). Otherwise → **skip** (bucket: future period).

Response summary: `{ generated, futureNotGenerated, overlapSkipped, failed }`.
UI message: "Y current month due compliance(s) generated" and "X compliance(s) for
future period not generated".

Existing guards remain: only APPROVED + active templates; `recurringEndDate` respected;
`filingMonth` keeps its current meaning (generation input month).

## Approval-time auto-generation

On admin/reviewer approval, seed the first compliance from `periodEndDate` (period end,
due date, payment date) when set. Fall back to the current-month behavior when not set.
Only generate if no compliance exists for the template yet.

## UI changes

- **Create form** (`src/app/master/compliance-templates/create/page.tsx`): add
  **Period End Date** (date input, required) just before Frequency; add **Payment Due
  Days** (number input, defaults to the Days to File value) beside Days to File.
  Field order: Period End Date → Frequency → Days to File / Payment Due Days.
- **Edit form** (`src/app/master/compliance-templates/[id]/edit/page.tsx`): same two
  fields.
- **Detail page** (`src/app/master/compliance-templates/[id]/page.tsx`): display Period
  End Date and Payment Due Days.
- **Generate dialogs** (list page bulk + per-row, detail page): replace summary block
  with the two-line message above.
- **API routes**: `POST /api/templates`, `PUT /api/templates/[id]` accept
  `periodEndDate` and `paymentDueDaysAfterPeriodEnd`.

## Backward compatibility

- Legacy templates without `periodEndDate`: first generation uses the existing
  month-anchored logic; rolling applies once a compliance exists.
- All other template/compliance fields and workflows unchanged.

## Out of scope

- Changing the meaning of `filingMonth`.
- Per-period payment dates (stored as relative days so they roll automatically).
- Migration of existing generated compliances (no backfill).
