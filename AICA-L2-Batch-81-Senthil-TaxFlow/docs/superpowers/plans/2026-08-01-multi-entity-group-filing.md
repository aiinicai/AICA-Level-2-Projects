# Multi-Entity Group Filing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selecting multiple entities on a compliance create/edit form produce a single group compliance (one tracker line) backed by one `compliance_schedules` row plus one `compliance_entities` row per entity, with a user-chosen filing entity, a searchable/country-filtered entity multi-select, and a recurring end date that stops generation.

**Architecture:** One `compliance_schedules` row represents the group return. Its nullable `entityId` (already documented as "primary for backward compatibility") stores the **filing entity**; `countryId` mirrors the filing entity's country. Every selected entity is recorded in `compliance_entities` (the entity-level fact table for future reports). Recurring generation stops silently once the next occurrence's due date exceeds `recurringEndDate`.

**Tech Stack:** Next.js 16 (App Router), Supabase (PostgREST via `supabaseAdmin`), Radix UI primitives, React 19. No test framework exists in the repo.

## Global Constraints

- **This is NOT the Next.js you know.** Breaking changes. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
- **No test framework.** Verification = `npx tsc --noEmit`, scoped `npx eslint`, and temporary DB-layer reproduction scripts run with `node` (see each task). Final acceptance includes manual browser checks.
- **Lint rule `react-hooks/set-state-in-effect`:** never call setState synchronously in an effect. Use derived values (e.g., `effectiveFilingEntityId`) instead of sync-set effects.
- **Supabase admin env vars** are in `.env` (`NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`). `supabaseAdmin` is a Proxy in `src/lib/supabase.ts`; queries are untyped (`any`).
- **Working tree already contains unrelated uncommitted changes.** Commit steps stage ONLY the files listed in the task. Do not stage or revert unrelated files.
- **Shell is Windows PowerShell (win32).** Use `node` for reproduction scripts placed in the repo root; delete them after running.
- **Migration application:** DDL cannot be run via PostgREST and the `pg` `DATABASE_URL` (localhost:5432) is unreachable. Task 1 requires the human to run one `ALTER TABLE` in the Supabase SQL editor before the rest proceeds.
- Preserve existing code patterns; no unrelated refactoring. All code is TypeScript in `src/`.

---

### Task 1: Schema — add `recurringEndDate` column

**Files:**
- Modify: `supabase-full-schema.sql` (column block for `compliance_schedules`, around line 196 `"isRecurring"`)
- Modify: `supabase-migration.sql`
- Verify: `repro-recurring-column.mjs` (temporary)

**Interfaces:**
- Produces: `compliance_schedules.recurringEndDate TIMESTAMPTZ` (nullable), available on `supabaseAdmin.from("compliance_schedules")` rows as `recurringEndDate: string | null` (ISO string) or `undefined` for legacy rows.

- [ ] **Step 1: Add the column to `supabase-full-schema.sql`**

In the `compliance_schedules` CREATE TABLE, directly after the `"isRecurring" BOOLEAN NOT NULL DEFAULT true,` line, add:

```sql
    "recurringEndDate" TIMESTAMPTZ,
```

- [ ] **Step 2: Add the migration to `supabase-migration.sql`**

Append at the end of the file:

```sql
-- Multi-entity group filing: optional date after which recurring generation stops
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "recurringEndDate" TIMESTAMPTZ;
```

- [ ] **Step 3: Write the column-existence reproduction script**

Create `repro-recurring-column.mjs` in the repo root:

```js
import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })
const { data, error } = await supabase.from("compliance_schedules").select("id, recurringEndDate").limit(1)
if (error) {
  console.error("COLUMN MISSING:", error.message)
  process.exit(1)
}
console.log("COLUMN OK; sample recurringEndDate:", data[0]?.recurringEndDate ?? null)
```

- [ ] **Step 4: Run the script — expect it to FAIL (column not yet in live DB)**

Run: `node repro-recurring-column.mjs`
Expected: `COLUMN MISSING: Could not find the 'recurringEndDate' column of 'compliance_schedules' in the schema cache`

- [ ] **Step 5: Have the human apply the migration to the live DB**

Ask the user to run this in the Supabase SQL editor for project `osupitxzfdcetyvcunqi`:

```sql
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "recurringEndDate" TIMESTAMPTZ;
```

- [ ] **Step 6: Re-run the script — expect it to PASS**

Run: `node repro-recurring-column.mjs`
Expected: `COLUMN OK; sample recurringEndDate: null`

- [ ] **Step 7: Commit**

```bash
git add supabase-full-schema.sql supabase-migration.sql
git commit -m "feat(db): add recurringEndDate to compliance_schedules"
```

---

### Task 2: MultiSelect — search box and country filter

**Files:**
- Modify: `src/components/multi-select.tsx`

**Interfaces:**
- Consumes: existing `selected: string[]`, `onChange: (selected: string[]) => void`, `placeholder`, `label`, `disabled`.
- Produces: `Option` becomes `{ value: string; label: string; country?: string }`; new optional props `searchable?: boolean` and `showCountryFilter?: boolean`. When `searchable` is set, a text input filters options by label (and country) text. When `showCountryFilter` is set, a country dropdown (distinct countries derived from options) filters by `option.country`. Default behavior (no search/filter) unchanged.

- [ ] **Step 1: Extend the `Option` interface and `MultiSelectProps`**

```ts
interface Option {
  value: string
  label: string
  country?: string
}

interface MultiSelectProps {
  options: Option[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  label?: string
  disabled?: boolean
  searchable?: boolean
  showCountryFilter?: boolean
}
```

- [ ] **Step 2: Update the component signature and add state**

```ts
export default function MultiSelect({
  options, selected, onChange, placeholder = "Select...", label, disabled = false,
  searchable = false, showCountryFilter = false,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [countryFilter, setCountryFilter] = useState("")
  const ref = useRef<HTMLDivElement>(null)
```

- [ ] **Step 3: Add `useMemo` for countries and filtered options**

Import `useMemo` from `react`. Add after `toggle`:

```ts
  const countries = useMemo(
    () => Array.from(new Set(options.map((o) => o.country).filter(Boolean) as string[])).sort(),
    [options]
  )

  const filteredOptions = useMemo(() => {
    let list = options
    if (countryFilter) list = list.filter((o) => o.country === countryFilter)
    if (query) {
      const q = query.toLowerCase()
      list = list.filter((o) => o.label.toLowerCase().includes(q) || (o.country || "").toLowerCase().includes(q))
    }
    return list
  }, [options, query, countryFilter])
```

- [ ] **Step 4: Render the search input and country filter inside the dropdown**

Replace the `<div className="p-1">` block (currently containing the "No options" text and `options.map`) so that the dropdown opens with a filter header. The `options.map` loop must iterate `filteredOptions` instead of `options`:

```tsx
          <div className="p-1">
            {(searchable || showCountryFilter) && (
              <div className="border-b pb-1.5 mb-1 space-y-1.5">
                {searchable && (
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search..."
                    className="h-8 text-sm"
                  />
                )}
                {showCountryFilter && countries.length > 1 && (
                  <select
                    value={countryFilter}
                    onChange={(e) => setCountryFilter(e.target.value)}
                    className="w-full h-8 text-sm rounded-md border bg-background px-2"
                  >
                    <option value="">All countries</option>
                    {countries.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                )}
              </div>
            )}
            {filteredOptions.length === 0 && (
              <div className="px-2 py-4 text-sm text-center text-muted-foreground">No options</div>
            )}
            {filteredOptions.map((option) => { /* existing row markup, unchanged */ })}
          </div>
```

Add `import { Input } from "@/components/ui/input"` at the top.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/components/multi-select.tsx`
Expected: both pass with no errors.

- [ ] **Step 6: Commit**

```bash
git add src/components/multi-select.tsx
git commit -m "feat(multi-select): add search and country filter"
```

---

### Task 3: POST `/api/compliance` — one group schedule + filing entity

**Files:**
- Modify: `src/app/api/compliance/route.ts` (body destructure ~159-174; filing-entity resolution + insert ~196-306)
- Verify: `repro-post.mjs` (temporary)

**Interfaces:**
- Consumes: request body fields `entityIds: string[]`, `filingEntityId?: string`, `recurringEndDate?: string` (YYYY-MM-DD), plus existing fields.
- Produces: a single `compliance_schedules` row where `entityId` = filing entity, `countryId` = filing entity's country, `recurringEndDate` persisted (ISO or null); one `compliance_entities` row per selected entity; HTTP 201 body `{ data: scheduleObject }` (single object, not an array). HTTP 400 `{ error: "Filing entity is required when multiple entities are selected" }` when >1 entity without a filing entity.

- [ ] **Step 1: Write the failing DB-layer reproduction**

Create `repro-post.mjs` in the repo root. It mirrors the CURRENT POST logic (the per-entity loop) with 2 entities and asserts the NEW end-state:

```js
import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })
const newId = () => crypto.randomUUID()
const now = () => new Date().toISOString()

const { data: user } = await supabase.from("users").select("id, email").eq("role", "PREPARER").limit(1).maybeSingle()
const { data: membership } = await supabase.from("organization_members").select("orgId").eq("userId", user.id).limit(1).maybeSingle()
const { data: entities } = await supabase.from("legal_entities").select("id, countryId").eq("orgId", membership.orgId).limit(2)
const filingEntityId = entities[0].id
const entityIds = entities.map((e) => e.id)
const dueDate = "2026-09-20"
const recurringEndDate = "2026-12-31"
const taxPeriod = "Sep 2026"

// Mirror CURRENT handler logic (per-entity loop) -- this must FAIL the assertions below.
let scheduleId = null
for (const entity of entityIds) {
  const digits = Math.floor(10000 + Math.random() * 90000)
  const res = await supabase.from("compliance_schedules").insert({
    id: newId(), orgId: membership.orgId, complianceId: `TAX-${digits}`, entityId: entity,
    countryId: entities.find((e) => e.id === entity).countryId, taxType: "VAT", complianceTypeId: null,
    formId: null, taxPeriod, frequency: "MONTHLY", dueDate: new Date(dueDate).toISOString(),
    priority: "NORMAL", status: "DRAFT", isRecurring: true, notes: null, updatedAt: now(),
  }).select("id").single()
  if (res.error) { console.error("INSERT ERROR:", res.error.message); process.exit(1) }
  scheduleId = res.data.id
}

const { data: created } = await supabase.from("compliance_schedules").select("id, entityId, countryId, recurringEndDate, entities:compliance_entities(entityId)").eq("orgId", membership.orgId).order("createdAt", { ascending: false }).limit(10)
const lastGroup = created.filter((c) => c.entities?.length > 1)[0]

console.log("lastGroup schedule:", JSON.stringify(lastGroup, null, 2))

if (!lastGroup) { console.error("FAIL: expected ONE schedule with multiple compliance_entities rows"); process.exit(1) }
const expectedCountry = entities.find((e) => e.id === filingEntityId).countryId
if (lastGroup.entityId !== filingEntityId) { console.error("FAIL: entityId != filing entity"); process.exit(1) }
if (lastGroup.countryId !== expectedCountry) { console.error("FAIL: countryId != filing entity country"); process.exit(1) }
if (lastGroup.recurringEndDate !== new Date(recurringEndDate).toISOString()) { console.error("FAIL: recurringEndDate not persisted"); process.exit(1) }
const linked = new Set(lastGroup.entities.map((x) => x.entityId))
if (entityIds.length !== linked.size || !entityIds.every((id) => linked.has(id))) { console.error("FAIL: compliance_entities does not contain all entities"); process.exit(1) }

// cleanup any schedules created by this run
for (const row of created) {
  await supabase.from("compliance_entities").delete().eq("complianceId", row.id)
  await supabase.from("compliance_schedules").delete().eq("id", row.id)
}
console.log("PASS")
```

- [ ] **Step 2: Run it — expect it to FAIL (current logic fans out)**

Run: `node repro-post.mjs`
Expected: prints a schedule with `entities: [ { entityId } ]` (length 1) and exits `FAIL: expected ONE schedule with multiple compliance_entities rows`.

- [ ] **Step 3: Implement the new POST body destructure**

Add `filingEntityId: bodyFilingEntityId, recurringEndDate,` to the existing destructure block (after `approverIds,`):

```ts
    const {
      entityId,
      entityIds,
      taxType,
      formId,
      taxPeriod,
      taxPeriodStart,
      taxPeriodEnd,
      frequency,
      dueDate,
      priority,
      isRecurring,
      notes,
      preparerId: bodyPreparerId,
      approverIds,
      filingEntityId: bodyFilingEntityId,
      recurringEndDate,
    } = body
```

- [ ] **Step 4: Replace the per-entity loop with a single group insert**

Replace everything from `const created = []` through the closing `}` of the `for (const entity of entities)` loop and the `return NextResponse.json({ data: entities.length === 1 ? created[0] : created }, { status: 201 })` line with:

```ts
    const filingEntityId =
      bodyFilingEntityId && entities.includes(bodyFilingEntityId)
        ? bodyFilingEntityId
        : entities.length === 1
          ? entities[0]
          : null

    if (!filingEntityId) {
      return NextResponse.json(
        { error: "Filing entity is required when multiple entities are selected" },
        { status: 400 }
      )
    }

    const digits = Math.floor(10000 + Math.random() * 90000)
    const generatedComplianceId = `TAX-${digits}`

    const { data: schedule, error: createError } = await supabaseAdmin
      .from("compliance_schedules")
      .insert({
        id: newId(),
        orgId,
        complianceId: generatedComplianceId,
        entityId: filingEntityId,
        countryId: countryByEntity.get(filingEntityId) ?? null,
        taxType,
        complianceTypeId: null,
        formId: formId || null,
        taxPeriod: taxPeriod || (taxPeriodStart && taxPeriodEnd ? `${taxPeriodStart}–${taxPeriodEnd}` : ""),
        frequency,
        dueDate: new Date(dueDate).toISOString(),
        priority: priority || "NORMAL",
        status: "DRAFT",
        isRecurring: isRecurring ?? true,
        recurringEndDate: recurringEndDate ? new Date(recurringEndDate).toISOString() : null,
        notes: notes || null,
        updatedAt: now(),
      })
      .select("id, complianceId, status")
      .single()

    if (createError) throw createError

    const { error: entityLinkError } = await supabaseAdmin
      .from("compliance_entities")
      .insert(
        entities.map((entity) => ({
          id: newId(),
          complianceId: schedule.id,
          entityId: entity,
        }))
      )

    if (entityLinkError) throw entityLinkError

    if (preparerId) {
      const { error: assignError } = await supabaseAdmin
        .from("compliance_assignments")
        .insert({ id: newId(), complianceId: schedule.id, preparerId, updatedAt: now() })

      if (assignError) throw assignError

      await ensureOrgMember(orgId, preparerId, ["PREPARER"])
    }

    if (approverIds?.length > 0) {
      const { error: approvalError } = await supabaseAdmin
        .from("compliance_approvals")
        .insert(
          approverIds.map((approverId: string) => ({
            id: newId(),
            complianceId: schedule.id,
            approverId,
            status: "PENDING_APPROVAL",
            updatedAt: now(),
          }))
        )

      if (approvalError) throw approvalError

      for (const approverId of approverIds) {
        await ensureOrgMember(orgId, approverId, ["APPROVER"])
      }
    }

    const { data: fullData, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", schedule.id)
      .single()

    if (fetchError) throw fetchError

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: schedule.id,
        userId: session.user.id,
        action: "CREATED",
        toStatus: schedule.status,
        comments: `Compliance ${generatedComplianceId} created`,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "CREATE",
        entity: "ComplianceSchedule",
        entityId: schedule.id,
        newValue: JSON.stringify({ complianceId: generatedComplianceId, entityId: filingEntityId, taxType, taxPeriod, frequency, dueDate }),
      })

    if (auditError) throw auditError

    return NextResponse.json({ data: sortNestedRelations(fullData) }, { status: 201 })
```

The existing `countryByEntity` map (added previously for the `countryId` NOT NULL fix) stays where it is and is used above via `countryByEntity.get(filingEntityId)`.

- [ ] **Step 5: Update the reproduction to mirror the NEW handler, then run it**

In `repro-post.mjs`, replace the `for (const entity of entityIds) { ... }` block with a single insert using `entityId: filingEntityId` and `recurringEndDate`, then a batch insert of all `entityIds` into `compliance_entities` (mirroring the new code). Run: `node repro-post.mjs`
Expected: `PASS` (one schedule, `entityId` = filing entity, `countryId` = filing entity's country, `recurringEndDate` persisted, all entities linked).

- [ ] **Step 6: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/route.ts`
Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/api/compliance/route.ts
git commit -m "feat(compliance): create one group schedule with filing entity"
```

---

### Task 4: PUT `/api/compliance/[id]` — filing entity + recurring end date

**Files:**
- Modify: `src/app/api/compliance/[id]/route.ts` (destructure ~109-127; updateData logic ~150-164)
- Verify: `repro-put.mjs` (temporary)

**Interfaces:**
- Consumes: request body `filingEntityId?: string`, `recurringEndDate?: string`, `countryId?: string`, `entityIds?: string[]` plus existing fields.
- Produces: when `filingEntityId` provided, `entityId` set to it and `countryId` set to the filing entity's country (unless `countryId` also provided in body, which wins). `recurringEndDate` persisted as ISO (null clears it). `compliance_entities` still replaced by delete + re-insert of all `entityIds`.

- [ ] **Step 1: Write the failing DB-layer reproduction**

Create `repro-put.mjs`:

```js
import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })
const newId = () => crypto.randomUUID()
const now = () => new Date().toISOString()

const { data: membership } = await supabase.from("organization_members").select("orgId").limit(1).maybeSingle()
const { data: entities } = await supabase.from("legal_entities").select("id, countryId").eq("orgId", membership.orgId).limit(2)
const entityIds = entities.map((e) => e.id)
const filingEntityId = entities[1].id
const expectedCountry = entities.find((e) => e.id === filingEntityId).countryId
const recurringEndDate = "2026-12-31"

// create a throwaway group schedule directly (single insert + join rows)
const sres = await supabase.from("compliance_schedules").insert({
  id: newId(), orgId: membership.orgId, complianceId: `TAX-${Math.floor(10000 + Math.random() * 90000)}`,
  entityId: entities[0].id, countryId: entities[0].countryId, taxType: "VAT", complianceTypeId: null,
  formId: null, taxPeriod: "Sep 2026", frequency: "MONTHLY", dueDate: new Date("2026-09-20").toISOString(),
  priority: "NORMAL", status: "DRAFT", isRecurring: true, notes: null, updatedAt: now(),
}).select("id").single()
if (sres.error) { console.error("setup insert error:", sres.error.message); process.exit(1) }
const id = sres.data.id
await supabase.from("compliance_entities").insert(entityIds.map((entity) => ({ id: newId(), complianceId: id, entityId: entity })))

// Mirror the CURRENT PUT update logic (entityId = nextEntityIds[0], ignores filingEntityId)
const nextEntityIds = Array.from(new Set(entityIds))
const updateData = {}
updateData.entityId = nextEntityIds[0] || null
updateData.updatedAt = now()
const { error: upErr } = await supabase.from("compliance_schedules").update(updateData).eq("id", id)
if (upErr) { console.error("update error:", upErr.message); process.exit(1) }

const { data: row } = await supabase.from("compliance_schedules").select("entityId, countryId, recurringEndDate").eq("id", id).single()

// clean up
await supabase.from("compliance_entities").delete().eq("complianceId", id)
await supabase.from("compliance_schedules").delete().eq("id", id)

if (row.entityId !== filingEntityId) { console.error("FAIL: entityId != filingEntityId"); process.exit(1) }
if (row.countryId !== expectedCountry) { console.error("FAIL: countryId != filing entity country"); process.exit(1) }
if (row.recurringEndDate !== new Date(recurringEndDate).toISOString()) { console.error("FAIL: recurringEndDate not persisted"); process.exit(1) }
console.log("PASS")
```

- [ ] **Step 2: Run it — expect it to FAIL (PUT ignores filing entity)**

Run: `node repro-put.mjs`
Expected: `FAIL: entityId != filingEntityId`

- [ ] **Step 3: Implement the PUT changes**

Add `filingEntityId, recurringEndDate,` to the body destructure (after `approverIds,`). Then replace the primary-entity block (currently `if (nextEntityIds !== null) updateData.entityId = nextEntityIds[0] || null; else if (entityId !== undefined) updateData.entityId = entityId`) and add `recurringEndDate` persistence:

```ts
    if (filingEntityId !== undefined) {
      updateData.entityId = filingEntityId
      if (countryId === undefined) {
        const { data: filingEntity } = await supabaseAdmin
          .from("legal_entities")
          .select("countryId")
          .eq("id", filingEntityId)
          .maybeSingle()
        if (filingEntity?.countryId) updateData.countryId = filingEntity.countryId
      }
    } else if (nextEntityIds !== null) {
      updateData.entityId = nextEntityIds[0] || null
    } else if (entityId !== undefined) {
      updateData.entityId = entityId
    }
    if (countryId !== undefined) updateData.countryId = countryId
    if (recurringEndDate !== undefined) {
      updateData.recurringEndDate = recurringEndDate ? new Date(recurringEndDate).toISOString() : null
    }
```

The `compliance_entities` delete/re-insert block later in the handler is unchanged.

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

In `repro-put.mjs`, replace the mirror block so `updateData.entityId = filingEntityId`, set `countryId` from the lookup when not passed, and set `recurringEndDate`. Run: `node repro-put.mjs`
Expected: `PASS`

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/[id]/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/compliance/[id]/route.ts
git commit -m "feat(compliance): respect filing entity and recurring end date on edit"
```

---

### Task 5: `generate/route.ts` — stop after recurring end date

**Files:**
- Modify: `src/app/api/compliance/generate/route.ts` (next-occurrence check ~60-61)
- Verify: `repro-generate.mjs` (temporary)

**Interfaces:**
- Consumes: `compliance_schedules.recurringEndDate` on the parent schedule.
- Produces: when a schedule has `recurringEndDate` and the computed next due date is strictly after it, the occurrence is skipped; `isRecurring` is left unchanged.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-generate.mjs`:

```js
import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })
const newId = () => crypto.randomUUID()
const now = () => new Date().toISOString()

function nextDue(dueDate, frequency) {
  const n = new Date(dueDate)
  n.setMonth(n.getMonth() + 1)
  return n
}

const { data: membership } = await supabase.from("organization_members").select("orgId").limit(1).maybeSingle()
const { data: ent } = await supabase.from("legal_entities").select("id, countryId").limit(1).maybeSingle()
const id = newId()
const due = new Date("2026-08-20")
const end = new Date("2026-08-31") // next occurrence (Sep 20) is AFTER end -> should be skipped
await supabase.from("compliance_schedules").insert({
  id, orgId: membership.orgId, complianceId: `TAX-${Math.floor(10000 + Math.random() * 90000)}`,
  entityId: ent.id, countryId: ent.countryId, taxType: "VAT", complianceTypeId: null,
  formId: null, taxPeriod: "Aug 2026", frequency: "MONTHLY", dueDate: due.toISOString(),
  priority: "NORMAL", status: "FILED", isRecurring: true, recurringEndDate: end.toISOString(), updatedAt: now(),
})

const nextDueDate = nextDue(due, "MONTHLY")

// Mirror CURRENT generate logic: creates the next occurrence regardless of end date.
let created = false
if (nextDueDate > due) {
  const res = await supabase.from("compliance_schedules").insert({
    id: newId(), orgId: membership.orgId, complianceId: `TAX-${Math.floor(10000 + Math.random() * 90000)}`,
    entityId: ent.id, countryId: ent.countryId, taxType: "VAT", complianceTypeId: null,
    formId: null, taxPeriod: "Sep 2026", frequency: "MONTHLY", dueDate: nextDueDate.toISOString(),
    priority: "NORMAL", status: "PENDING_PREPARATION", isRecurring: true, updatedAt: now(),
  }).select("id").single()
  created = !res.error
}

// clean up the child + parent
const { data: children } = await supabase.from("compliance_schedules").select("id").eq("orgId", membership.orgId).eq("dueDate", nextDueDate.toISOString()).in("status", ["PENDING_PREPARATION"])
for (const c of children || []) {
  await supabase.from("compliance_entities").delete().eq("complianceId", c.id)
  await supabase.from("compliance_schedules").delete().eq("id", c.id)
}
await supabase.from("compliance_entities").delete().eq("complianceId", id)
await supabase.from("compliance_schedules").delete().eq("id", id)

if (created) { console.error("FAIL: generated occurrence despite nextDueDate > recurringEndDate"); process.exit(1) }
console.log("PASS")
```

- [ ] **Step 2: Run it — expect it to FAIL (generate ignores end date)**

Run: `node repro-generate.mjs`
Expected: `FAIL: generated occurrence despite nextDueDate > recurringEndDate`

- [ ] **Step 3: Implement the end-date check**

In the loop, immediately after the existing guard line `if (!nextDueDate || nextDueDate <= currentTime) continue`, add:

```ts
      if (schedule.recurringEndDate && nextDueDate > new Date(schedule.recurringEndDate)) continue
```

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

In `repro-generate.mjs`, guard the child insert with `if (!(end && nextDueDate > end))`. Run: `node repro-generate.mjs`
Expected: `PASS`

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/generate/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/compliance/generate/route.ts
git commit -m "feat(compliance): stop recurring generation after end date"
```

---

### Task 6: Create form — filing entity, recurring end date, searchable entity picker

**Files:**
- Modify: `src/app/compliance/create/page.tsx`

**Interfaces:**
- Consumes: `MultiSelect` props `searchable`, `showCountryFilter`, options with `country`; POST body fields `filingEntityId`, `recurringEndDate`.
- Produces: create form sends `entityIds`, `filingEntityId` (single schedule) and `recurringEndDate`; filing entity auto-locked when one entity selected, required when >1.

- [ ] **Step 1: Extend the `Entity` interface**

```ts
interface Entity {
  id: string
  entityName: string
  entityNumber: string
  country?: { name: string; code: string }
}
```

- [ ] **Step 2: Add state**

Add `const [filingEntityId, setFilingEntityId] = useState("")` and `const [recurringEndDate, setRecurringEndDate] = useState("")` near the other state declarations (after `notes`).

- [ ] **Step 3: Add a derived filing-entity value (no setState-in-effect)**

After the existing `const effectivePreparerId = ...` line:

```ts
  // Filing entity: user-chosen, auto-locked to the single selection, or blank.
  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""
```

- [ ] **Step 4: Make the entity MultiSelect searchable and country-filterable**

Replace the `MultiSelect` usage with:

```tsx
                <MultiSelect
                  options={entities.map((e) => ({
                    value: e.id,
                    label: `${e.entityName} (${e.entityNumber})`,
                    country: e.country?.name,
                  }))}
                  selected={entityIds}
                  onChange={setEntityIds}
                  disabled={!formId}
                  searchable
                  showCountryFilter
                  placeholder={formId ? "Select one or more entities" : "Select a form first"}
                />
```

- [ ] **Step 5: Add the Filing Entity selector and Recurring End Date field**

Directly after the Entities `</div>` (the one closing the Entities field, following the helper `<p>`), add:

```tsx
              <div className="space-y-2">
                <Label htmlFor="filingEntity">
                  Filing Entity {entityIds.length > 1 && <span className="text-red-500">*</span>}
                </Label>
                <Select
                  value={effectiveFilingEntityId}
                  onValueChange={setFilingEntityId}
                  disabled={entityIds.length === 0 || entityIds.length === 1}
                >
                  <SelectTrigger id="filingEntity">
                    <SelectValue placeholder={entityIds.length === 0 ? "Select entities first" : "Select filing entity"} />
                  </SelectTrigger>
                  <SelectContent>
                    {entities
                      .filter((e) => entityIds.includes(e.id))
                      .map((e) => (
                        <SelectItem key={e.id} value={e.id}>
                          {e.entityName} ({e.entityNumber})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  The entity the group return is filed from. Determines the country.
                </p>
              </div>

              {isRecurring && (
                <div className="space-y-2">
                  <Label htmlFor="recurringEndDate">Recurring End Date</Label>
                  <Input
                    id="recurringEndDate"
                    type="date"
                    value={recurringEndDate}
                    onChange={(e) => setRecurringEndDate(e.target.value)}
                  />
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Generation stops after this date (optional).
                  </p>
                </div>
              )}
```

- [ ] **Step 6: Add submit validation and body fields**

In `handleSubmit`, after the `effectivePreparerId` check, add:

```ts
    if (entityIds.length > 1 && !effectiveFilingEntityId) {
      toast({
        title: "Validation Error",
        description: "Please select a filing entity",
        variant: "destructive",
      })
      return
    }
```

In the `body` object add:

```ts
        filingEntityId: effectiveFilingEntityId || undefined,
        recurringEndDate: recurringEndDate || undefined,
```

- [ ] **Step 7: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/compliance/create/page.tsx`
Expected: both pass. Note: `entities.filter(...)` in Step 5 references `Entity` which now includes `country` — fine.

- [ ] **Step 8: Commit**

```bash
git add src/app/compliance/create/page.tsx
git commit -m "feat(compliance): filing entity, recurring end date, searchable entity picker on create"
```

---

### Task 7: Edit form — filing entity + recurring end date

**Files:**
- Modify: `src/app/compliance/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: PUT body fields `filingEntityId`, `recurringEndDate`; the schedule's existing `entityId` (primary) and `countryId`.
- Produces: edit form pre-fills filing entity from the schedule's `entityId`, keeps the country select in sync when the filing entity changes, sends `filingEntityId` and `recurringEndDate`.

- [ ] **Step 1: Extend the `Entity` interface and add state**

Extend `Entity` (already declared in this file) with `country?: { name: string; code: string }`. Add state:

```ts
  const [filingEntityId, setFilingEntityId] = useState("")
  const [recurringEndDate, setRecurringEndDate] = useState("")
```

- [ ] **Step 2: Pre-fill from the loaded record**

Where the load effect sets the other fields (around `setIsRecurring(!!d.isRecurring)`), add:

```ts
        setFilingEntityId(d.entityId || (d.entities?.[0]?.entityId) || "")
        setRecurringEndDate(d.recurringEndDate ? d.recurringEndDate.slice(0, 10) : "")
```

- [ ] **Step 3: Add a filing-entity change handler that syncs the country**

Add near the other handlers:

```ts
  function handleFilingEntityChange(value: string) {
    setFilingEntityId(value)
    const entity = entities.find((e) => e.id === value)
    if (entity?.country?.name) {
      const country = countries.find((c) => c.name === entity.country?.name)
      if (country) setCountryId(country.id)
    }
  }
```

- [ ] **Step 4: Make the entity MultiSelect searchable/country-filterable and add the Filing Entity selector + Recurring End Date field**

Replace the entity `MultiSelect` options to include `country: e.country?.name` and add `searchable` and `showCountryFilter` props. Below the Entities/Country grid, add the Filing Entity selector:

```tsx
              <div className="space-y-2">
                <Label htmlFor="filingEntity">
                  Filing Entity {entityIds.length > 1 && <span className="text-red-500">*</span>}
                </Label>
                <Select
                  value={filingEntityId}
                  onValueChange={handleFilingEntityChange}
                  disabled={entityIds.length === 0 || entityIds.length === 1}
                >
                  <SelectTrigger id="filingEntity">
                    <SelectValue placeholder={entityIds.length === 0 ? "Select entities first" : "Select filing entity"} />
                  </SelectTrigger>
                  <SelectContent>
                    {entities
                      .filter((e) => entityIds.includes(e.id))
                      .map((e) => (
                        <SelectItem key={e.id} value={e.id}>
                          {e.entityName} ({e.entityNumber})
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  The entity the group return is filed from.
                </p>
              </div>
```

Below the `Is Recurring` checkbox block (around line 556-563), add:

```tsx
              {isRecurring && (
                <div className="space-y-2">
                  <Label htmlFor="recurringEndDate">Recurring End Date</Label>
                  <Input
                    id="recurringEndDate"
                    type="date"
                    value={recurringEndDate}
                    onChange={(e) => setRecurringEndDate(e.target.value)}
                  />
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Generation stops after this date (optional).
                  </p>
                </div>
              )}
```

- [ ] **Step 5: Add submit validation and body fields**

In `handleSubmit`, after the existing required-fields check, add:

```ts
    if (entityIds.length > 1 && !filingEntityId) {
      toast({
        title: "Validation Error",
        description: "Please select a filing entity",
        variant: "destructive",
      })
      return
    }
```

In the `body` object add:

```ts
        filingEntityId: filingEntityId || undefined,
        recurringEndDate: recurringEndDate || undefined,
```

- [ ] **Step 6: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/compliance/[id]/edit/page.tsx`
Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/compliance/[id]/edit/page.tsx
git commit -m "feat(compliance): filing entity and recurring end date on edit"
```

---

### Task 8: Detail page — recurring end date readout

**Files:**
- Modify: `src/app/compliance/[id]/page.tsx` (info grid near "Recurring", ~858-861)

**Interfaces:**
- Consumes: `data.recurringEndDate?: string` from the compliance GET.
- Produces: displays the recurring end date (formatted) when set.

- [ ] **Step 1: Add the readout**

After the existing "Recurring" row, add:

```tsx
                  <div>
                    <Label className="text-[var(--color-muted-foreground)]">Recurring End Date</Label>
                    <p className="font-medium">{data.recurringEndDate ? formatDate(data.recurringEndDate) : "—"}</p>
                  </div>
```

(`formatDate` is already imported in this file.)

- [ ] **Step 2: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/compliance/[id]/page.tsx`
Expected: both pass.

- [ ] **Step 3: Commit**

```bash
git add src/app/compliance/[id]/page.tsx
git commit -m "feat(compliance): show recurring end date on detail page"
```

---

### Task 9: End-to-end verification

**Files:**
- Verify: temporary reproduction scripts removed; manual browser checks

- [ ] **Step 1: Remove all temporary reproduction scripts**

```bash
Remove-Item repro-recurring-column.mjs, repro-post.mjs, repro-put.mjs, repro-generate.mjs -ErrorAction SilentlyContinue
```

- [ ] **Step 2: Full typecheck and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/route.ts src/app/api/compliance/[id]/route.ts src/app/api/compliance/generate/route.ts src/components/multi-select.tsx src/app/compliance/create/page.tsx "src/app/compliance/[id]/edit/page.tsx" "src/app/compliance/[id]/page.tsx"`
Expected: all pass.

- [ ] **Step 3: Confirm git state is clean of stray artifacts**

Run: `git status --porcelain`
Expected: only the intended feature files plus the pre-existing unrelated working-tree changes (no `repro-*.mjs`).

- [ ] **Step 4: Ask the user to perform manual browser verification (logged in at `http://localhost:3000`)**

1. Create a compliance selecting **2+ entities**; choose a **Filing Entity**; save → tracker shows **one row** with all entity names comma-separated; the Country column shows the filing entity's country; open the detail page → all entities listed under "Entities".
2. On the create form, confirm the entity multi-select has a **search box** and a **country filter**.
3. Create a compliance with **Is Recurring** checked and a **Recurring End Date** in the past; run `POST /api/compliance/generate` (or the recurring job) and confirm no new occurrence is created.
4. Edit a group compliance → filing entity is pre-filled from the schedule's primary entity; changing it updates the country select.
