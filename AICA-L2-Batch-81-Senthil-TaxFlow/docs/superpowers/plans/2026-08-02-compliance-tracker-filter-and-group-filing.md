# Compliance Tracker: Group Filing, Templates Filter, and Workflow Refinements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make template generation produce exactly one compliance per template per filing month (group filing), add a Templates/Compliances toggle in the Compliance Tracker with non-editable compliances, add Mark-as-Prepared + 2nd-level-review + flexible payment/filing ordering + Close to the compliance workflow, and route non-admin template edits through admin approval.

**Architecture:** All three template-generation paths (`templates/[id]/generate`, `templates/generate`, `template-compliance.ts`) currently loop per entity and insert one `compliance_schedules` row each. They are rewritten to insert one schedule (filing entity = first entity, status `PENDING_PREPARATION`, `reviewerId` copied) and link every entity via `compliance_entities`. The Compliance Tracker page gains a `Tabs` (Compliances | Templates) control. New compliance workflow routes follow the existing route-file pattern (`newId`, `now`, `supabaseAdmin`, activity + audit trail + notifications). Non-admin edits to APPROVED templates are stored as rows in a new `template_change_requests` table and applied only after an admin approves.

**Tech Stack:** Next.js 16 (App Router), Supabase (PostgREST via `supabaseAdmin`), Radix UI primitives, React 19, TypeScript. No test framework exists in the repo.

## Global Constraints

- **This is NOT the Next.js you know.** Breaking changes. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
- **No test framework.** Verification = `npx tsc --noEmit`, scoped `npx eslint`, and temporary DB-layer reproduction scripts run with `node` (see each task). Final acceptance includes manual browser checks.
- **Lint rule `react-hooks/set-state-in-effect`:** never call setState synchronously in an effect. Use derived values instead of sync-set effects.
- **Supabase admin env vars** are in `.env` (`NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`). `supabaseAdmin` is a Proxy in `src/lib/supabase.ts`; queries are untyped (`any`).
- **Working tree already contains unrelated uncommitted changes.** Commit steps stage ONLY the files listed in the task. Do not stage or revert unrelated files.
- **Shell is Windows PowerShell (win32).** Use `node` for reproduction scripts placed in the repo root; delete them after running.
- **Migration application:** DDL cannot be run via PostgREST and the `pg` `DATABASE_URL` (localhost:5432) is unreachable. Task 1 requires the human to run SQL in the Supabase SQL editor before the rest proceeds.
- Preserve existing code patterns; no unrelated refactoring. All code is TypeScript in `src/`.
- `ComplianceStatus` is a Postgres ENUM. `CLOSED` already exists; `REVIEWED` must be added by migration (Task 1).
- Status colors are mapped in `src/lib/utils.ts` `getStatusColor` (add `REVIEWED`).
- PostgREST supports embedded-resource filters in this codebase (existing code uses `query.eq("compliance_assignments.preparerId", ...)`).

---

### Task 1: DB migration — `REVIEWED` enum value + `template_change_requests` table

**Files:**
- Create: `supabase/migrations/20260802000000_compliance_reviewed_and_change_requests.sql`
- Modify: `supabase-full-schema.sql`
- Modify: `supabase-migration.sql`
- Verify: `repro-enum.mjs` (temporary)

**Interfaces:**
- Produces: `ComplianceStatus` enum gains `'REVIEWED'`; new table `template_change_requests` with columns `id, templateId, orgId, requestedById, snapshot, fieldDiffs, changeReason, status, reviewedById, reviewedAt, reviewComments, requestedAt`. Available via `supabaseAdmin.from("template_change_requests")`.

- [ ] **Step 1: Create the migration file**

Create `supabase/migrations/20260802000000_compliance_reviewed_and_change_requests.sql`:

```sql
-- Compliance workflow: add REVIEWED status (2nd-level review completed)
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'REVIEWED';
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Template change requests: non-admin edits to approved templates await admin approval
CREATE TABLE IF NOT EXISTS template_change_requests (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "requestedById" TEXT NOT NULL,
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  "reviewedById" TEXT,
  "reviewedAt" TIMESTAMPTZ,
  "reviewComments" TEXT,
  "requestedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT template_change_requests_requestedById_fkey FOREIGN KEY ("requestedById") REFERENCES users(id),
  CONSTRAINT template_change_requests_reviewedById_fkey FOREIGN KEY ("reviewedById") REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_change_requests_template ON template_change_requests("templateId");
CREATE INDEX IF NOT EXISTS idx_change_requests_status ON template_change_requests(status);
```

- [ ] **Step 2: Update `supabase-full-schema.sql`**

1. In the `CREATE TYPE "ComplianceStatus"` line (line 34), change the value list to include `'REVIEWED'` after `'PENDING_APPROVAL'`:

```sql
CREATE TYPE "ComplianceStatus" AS ENUM ('DRAFT','PENDING_ADMIN_APPROVAL','PENDING_REVIEW','PENDING_PREPARATION','PREPARED','PENDING_APPROVAL','REVIEWED','APPROVED','REJECTED','FILED','PAID','CLOSED');
```

2. Append the `template_change_requests` CREATE TABLE (the exact SQL from Step 1) near the other compliance tables (after the `compliance_approvals` table block, ~line 257).

- [ ] **Step 3: Update `supabase-migration.sql`**

Append at the end of the file:

```sql
-- Compliance workflow: add REVIEWED status (2nd-level review completed)
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'REVIEWED';
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Template change requests: non-admin edits to approved templates await admin approval
CREATE TABLE IF NOT EXISTS template_change_requests (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "requestedById" TEXT NOT NULL,
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  "reviewedById" TEXT,
  "reviewedAt" TIMESTAMPTZ,
  "reviewComments" TEXT,
  "requestedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT template_change_requests_requestedById_fkey FOREIGN KEY ("requestedById") REFERENCES users(id),
  CONSTRAINT template_change_requests_reviewedById_fkey FOREIGN KEY ("reviewedById") REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_change_requests_template ON template_change_requests("templateId");
CREATE INDEX IF NOT EXISTS idx_change_requests_status ON template_change_requests(status);
```

- [ ] **Step 4: Write the enum/table reproduction script**

Create `repro-enum.mjs` in the repo root:

```js
import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })

const { data, error } = await supabase.from("template_change_requests").select("id").limit(1)
if (error && error.code === "42P01") {
  console.error("TABLE MISSING")
  process.exit(1)
}

const { data: sched, error: schedErr } = await supabase.from("compliance_schedules").select("status").limit(1)
if (schedErr) {
  console.error("SCHEDULE QUERY FAILED:", schedErr.message)
  process.exit(1)
}
const { data: seed } = await supabase.rpc("get_pg_type_value", { p_typname: "compliance_status" }).catch(() => ({ data: null }))
console.log("TABLE OK; enum check sample status:", sched?.[0]?.status ?? null)
```

- [ ] **Step 5: Run the script — expect it to FAIL (table/enum not yet in live DB)**

Run: `node repro-enum.mjs`
Expected: `TABLE MISSING` (the `template_change_requests` table does not exist yet).

- [ ] **Step 6: Have the human apply the migration to the live DB**

Ask the user to run the SQL from Step 1 in the Supabase SQL editor for the project.

- [ ] **Step 7: Re-run the script — expect it to PASS**

Run: `node repro-enum.mjs`
Expected: `TABLE OK; enum check sample status: ...`

- [ ] **Step 8: Commit**

```bash
git add supabase/migrations/20260802000000_compliance_reviewed_and_change_requests.sql supabase-full-schema.sql supabase-migration.sql
git commit -m "feat(db): add REVIEWED status and template_change_requests table"
```

---

### Task 2: Group filing — `templates/[id]/generate/route.ts`

**Files:**
- Modify: `src/app/api/templates/[id]/generate/route.ts`
- Verify: `repro-gen-one.mjs` (temporary)

**Interfaces:**
- Consumes: POST body `{ filingMonth: "YYYY-MM" }`; template row with `entities: [{ entityId }]`.
- Produces: exactly ONE `compliance_schedules` row per template+filingMonth with `entityId` = first entity, `countryId` from that entity (fallback `template.countryId`), `status` = `PENDING_PREPARATION`, `reviewerId` = `template.reviewerId`; one `compliance_entities` row per entity; activity/assignment/approval rows as today. Response `{ data: { generated, skipped, summary } }` where `generated` is an array of one item `{ templateId, templateNumber, entityId, complianceId }`.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-gen-one.mjs` in the repo root. It mirrors the CURRENT per-entity logic against a real approved template with ≥2 entities and asserts the NEW end-state (one schedule, all entities linked, status `PENDING_PREPARATION`):

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

const { data: template } = await supabase
  .from("compliance_templates")
  .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
  .eq("status", "APPROVED")
  .eq("isActive", true)
  .limit(20)
const t = (template || []).find((x) => (x.entities || []).length > 1)
if (!t) { console.error("NO TEMPLATE with >1 entity found"); process.exit(1) }

const filingMonth = "2026-09"
const tEntities = t.entities || []
const scheduleIds = []
for (const te of tEntities) {
  const digits = Math.floor(10000 + Math.random() * 90000)
  const res = await supabase.from("compliance_schedules").insert({
    id: newId(), orgId: t.orgId, complianceId: `TAX-${digits}`, entityId: te.entityId,
    countryId: t.countryId, taxType: t.taxType, formId: t.formId || null,
    taxPeriod: "Sep 2026", filingMonth, frequency: t.frequency,
    dueDate: new Date("2026-09-28").toISOString(), priority: t.priority || "NORMAL",
    status: "PENDING_PREPARATION", isRecurring: true, templateId: t.id,
    templateVersion: t.version, updatedAt: new Date().toISOString(), createdById: t.createdById,
  }).select("id").single()
  if (res.error) { console.error("INSERT ERROR:", res.error.message); process.exit(1) }
  scheduleIds.push(res.data.id)
  await supabase.from("compliance_entities").insert({ id: newId(), complianceId: res.data.id, entityId: te.entityId })
}

const { data: rows } = await supabase.from("compliance_schedules")
  .select("id, entityId, status, entities:compliance_entities(entityId)")
  .in("id", scheduleIds)

// cleanup
for (const r of rows || []) {
  await supabase.from("compliance_entities").delete().eq("complianceId", r.id)
  await supabase.from("compliance_schedules").delete().eq("id", r.id)
}

const count = (rows || []).length
console.log(`created ${count} schedules for ${tEntities.length} entities`)
if (count !== 1) { console.error("FAIL: expected exactly ONE schedule"); process.exit(1) }
if ((rows || [])[0].status !== "PENDING_PREPARATION") { console.error("FAIL: status != PENDING_PREPARATION"); process.exit(1) }
const linked = new Set((rows || [])[0].entities.map((x) => x.entityId))
if (tEntities.length !== linked.size || !tEntities.every((e) => linked.has(e.entityId))) {
  console.error("FAIL: compliance_entities does not link all entities"); process.exit(1)
}
console.log("PASS")
```

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-gen-one.mjs`
Expected: `created 2 schedules for 2 entities` then `FAIL: expected exactly ONE schedule`.

- [ ] **Step 3: Rewrite the generation body**

Replace the `generated`/`skipped` declarations through the end of the `for (const te of ...)` loop (lines ~60–152) with:

```ts
    const templateEntities = (template.entities || []) as Array<{ entityId: string }>
    const generated: Array<{ templateId: string; templateNumber: string; entityId: string; complianceId: string }> = []
    const skipped: Array<{ templateId: string; templateNumber: string; entityId: string; reason: string }> = []
    const [fYear, fMonth] = filingMonth.split("-").map(Number)

    if (templateEntities.length === 0) {
      skipped.push({
        templateId: template.id,
        templateNumber: template.templateNumber || "N/A",
        entityId: "",
        reason: "Template has no entities",
      })
    } else {
      const { data: existingCompliance, error: existingError } = await supabaseAdmin
        .from("compliance_schedules")
        .select("id, complianceId")
        .eq("filingMonth", filingMonth)
        .eq("templateId", template.id)
        .maybeSingle()
      if (existingError) throw existingError

      if (existingCompliance) {
        skipped.push({
          templateId: template.id,
          templateNumber: template.templateNumber || "N/A",
          entityId: "",
          reason: `Compliance ${existingCompliance.complianceId} already exists for ${filingMonth}`,
        })
      } else {
        const filingEntityId = templateEntities[0].entityId
        const { data: entity, error: entityError } = await supabaseAdmin
          .from("legal_entities")
          .select("id, countryId")
          .eq("id", filingEntityId)
          .single()
        if (entityError && entityError.code !== "PGRST116") throw entityError

        const digits = Math.floor(10000 + Math.random() * 90000)
        const complianceId = `TAX-${digits}`
        const scheduleId = newId()

        const dueDate = new Date(fYear, fMonth - 1, template.dueDateDay || 28)
        if (dueDate.getMonth() !== fMonth - 1) dueDate.setDate(0)

        const periodStart = new Date(fYear, fMonth - 1, 1)
        const periodEnd = new Date(fYear, fMonth, 0)

        const { error: scheduleError } = await supabaseAdmin.from("compliance_schedules").insert({
          id: scheduleId,
          orgId,
          complianceId,
          entityId: filingEntityId,
          countryId: entity?.countryId || template.countryId,
          taxType: template.taxType,
          formId: template.formId || null,
          taxPeriod: `${periodStart.toISOString().split("T")[0]}–${periodEnd.toISOString().split("T")[0]}`,
          taxPeriodStart: periodStart.toISOString(),
          taxPeriodEnd: periodEnd.toISOString(),
          filingMonth,
          frequency: template.frequency,
          dueDate: dueDate.toISOString(),
          priority: template.priority || "NORMAL",
          status: "PENDING_PREPARATION",
          isRecurring: template.isRecurring ?? true,
          recurringEndDate: template.recurringEndDate || null,
          notes: template.notes || null,
          templateId: template.id,
          templateVersion: template.version,
          reviewerId: template.reviewerId || null,
          updatedAt: now(),
          createdById: session.user.id,
        })
        if (scheduleError) throw scheduleError

        const { error: entitiesError } = await supabaseAdmin.from("compliance_entities").insert(
          templateEntities.map((te) => ({
            id: newId(),
            complianceId: scheduleId,
            entityId: te.entityId,
          }))
        )
        if (entitiesError) throw entitiesError

        if (template.preparerId) {
          const { error: assignmentError } = await supabaseAdmin.from("compliance_assignments").insert({
            id: newId(), complianceId: scheduleId, preparerId: template.preparerId, updatedAt: now(),
          })
          if (assignmentError) throw assignmentError
        }

        if (template.approverId) {
          const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert({
            id: newId(), complianceId: scheduleId, approverId: template.approverId, status: "PENDING_APPROVAL", updatedAt: now(),
          })
          if (approvalError) throw approvalError
        }

        const { error: activityError } = await supabaseAdmin.from("activities").insert({
          id: newId(), complianceId: scheduleId, userId: session.user.id,
          action: "CREATED", toStatus: "PENDING_PREPARATION",
          comments: `Generated from template ${template.templateNumber} v${template.version} for ${filingMonth}`,
        })
        if (activityError) throw activityError

        generated.push({
          templateId: template.id,
          templateNumber: template.templateNumber || "N/A",
          entityId: filingEntityId,
          complianceId,
        })
      }
    }
```

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

In `repro-gen-one.mjs`, replace the per-entity loop with a single insert (`entityId: tEntities[0].entityId`, `status: "PENDING_PREPARATION"`, `reviewerId: t.reviewerId`) plus a batch insert of all `tEntities` into `compliance_entities`. Run: `node repro-gen-one.mjs`
Expected: `created 1 schedules for 2 entities` then `PASS`.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/templates/[id]/generate/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/templates/[id]/generate/route.ts
git commit -m "fix(templates): generate one group compliance per template"
```

---

### Task 3: Group filing — `templates/generate/route.ts` (bulk)

**Files:**
- Modify: `src/app/api/templates/generate/route.ts`
- Verify: `repro-gen-bulk.mjs` (temporary)

**Interfaces:**
- Consumes: POST body `{ filingMonth, filters }`.
- Produces: same single-schedule behavior as Task 2, applied inside the per-template loop. Response `generated` array holds one entry per template; `skipped` holds template-level reasons.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-gen-bulk.mjs` mirroring the CURRENT per-entity fan-out for one template with ≥2 entities (same shape as Task 2 Step 1, but asserting the response of the new bulk handler: exactly one created entry for the template). Assert `created === 1` for a template with ≥2 entities.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-gen-bulk.mjs`
Expected: `FAIL: expected exactly ONE schedule`.

- [ ] **Step 3: Rewrite the inner per-template loop**

Replace the inner `for (const te of templateEntities) { ... }` block (lines ~82–198) so it does NOT loop per entity. Replace it with the same single-schedule logic from Task 2 Step 3, but reading `template` (the bulk template object) and pushing into the existing `generated`/`skipped` arrays which now carry `templateId, templateNumber, entityId, reason` / `templateId, templateNumber, entityId, complianceId`. The dedup check and insert must match Task 2 exactly (dedup on `templateId` + `filingMonth`, `entityId` = `templateEntities[0].entityId`, batch link all entities, status `PENDING_PREPARATION`, `reviewerId` copied).

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-gen-bulk.mjs`
Expected: `PASS`.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/templates/generate/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/templates/generate/route.ts
git commit -m "fix(templates): group filing in bulk generation"
```

---

### Task 4: Group filing — `src/lib/template-compliance.ts`

**Files:**
- Modify: `src/lib/template-compliance.ts`
- Verify: `repro-first.mjs` (temporary)

**Interfaces:**
- Consumes: `generateFirstCompliance(template, entities, orgId, userId, filingMonth)`.
- Produces: returns `{ generated: Array<{ entityId: string; complianceId: string; status: string }>, skipped: Array<{ entityId: string; reason: string }> }` where `generated` has exactly ONE entry for a multi-entity template; creates one schedule (status `PENDING_PREPARATION`, `reviewerId` copied) + batch `compliance_entities` links.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-first.mjs` that calls the current `generateFirstCompliance` logic (mirroring its per-entity loop) against a real approved template with ≥2 entities and asserts the new end-state (one schedule, status `PENDING_PREPARATION`, all entities linked). Cleanup created rows afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-first.mjs`
Expected: `FAIL: expected exactly ONE schedule`.

- [ ] **Step 3: Rewrite `generateFirstCompliance`**

Replace the `for (const te of entities)` loop body so the function:
1. Dedups by querying `compliance_schedules` where `templateId = template.id` AND `filingMonth = filingMonth` (`.maybeSingle()`); if found, push `{ entityId: "", reason: "Compliance already exists for <filingMonth>" }` and return.
2. Uses `entities[0].entityId` as the filing entity; fetches its `countryId`.
3. Inserts ONE schedule with `status: "PENDING_PREPARATION"` and `reviewerId: template.reviewerId || null`.
4. Batch-inserts all `entities` into `compliance_entities`.
5. Inserts assignment/approval/activity rows as today (guarded by `template.preparerId` / `template.approverId`).
6. Pushes exactly one `{ entityId: entities[0].entityId, complianceId, status: "created" }`.

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-first.mjs`
Expected: `PASS`.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/lib/template-compliance.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/lib/template-compliance.ts
git commit -m "fix(templates): generateFirstCompliance creates one group schedule"
```

---

### Task 5: `GET /api/compliance` — entityId filter matches group members

**Files:**
- Modify: `src/app/api/compliance/route.ts` (entityId filter, line ~112-114)
- Verify: `repro-filter.mjs` (temporary)

**Interfaces:**
- Consumes: `?entityId=<id>`.
- Produces: returns schedules where `entityId = <id>` OR `<id>` appears in the schedule's `compliance_entities` (so filtering by any group member returns the group compliance).

- [ ] **Step 1: Write the failing reproduction**

Create `repro-filter.mjs` that creates a group schedule (one schedule + 2 `compliance_entities` rows), then runs the CURRENT filter (`eq("entityId", nonFilingEntityId)`) and asserts the new behavior (the group row IS returned). Clean up afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-filter.mjs`
Expected: `FAIL: group compliance not returned for member entity`.

- [ ] **Step 3: Update the filter**

Replace:

```ts
    if (entityId && entityId !== "all") {
      query = query.eq("entityId", entityId)
    }
```

with:

```ts
    if (entityId && entityId !== "all") {
      query = query.or(`entityId.eq.${entityId},entities.entityId.eq.${entityId}`)
    }
```

- [ ] **Step 4: Update the reproduction to use the NEW filter, then run it**

Run: `node repro-filter.mjs`
Expected: `PASS`.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/compliance/route.ts
git commit -m "fix(compliance): entity filter includes group members"
```

---

### Task 6: Status/type updates

**Files:**
- Modify: `src/types/index.ts`
- Modify: `src/lib/utils.ts`
- Modify: `src/app/compliance/page.tsx` (STATUS_OPTIONS only)

**Interfaces:**
- Produces: `ComplianceStatus` type includes `REVIEWED`; `getStatusColor` maps `REVIEWED` and `CLOSED`; tracker status filter includes `REVIEWED` and `CLOSED`.

- [ ] **Step 1: Add `REVIEWED` to the TS type**

In `src/types/index.ts` line 2, change:

```ts
type ComplianceStatus = "DRAFT" | "PENDING_PREPARATION" | "PREPARED" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "FILED" | "CLOSED"
```

to:

```ts
type ComplianceStatus = "DRAFT" | "PENDING_ADMIN_APPROVAL" | "PENDING_REVIEW" | "PENDING_PREPARATION" | "PREPARED" | "PENDING_APPROVAL" | "REVIEWED" | "APPROVED" | "REJECTED" | "FILED" | "PAID" | "CLOSED"
```

- [ ] **Step 2: Add color mapping**

In `src/lib/utils.ts`, add `REVIEWED: "bg-violet-100 text-violet-800"` to the `colors` object in `getStatusColor` (after `PENDING_APPROVAL`). (`CLOSED` already has an entry.)

- [ ] **Step 3: Add tracker status options**

In `src/app/compliance/page.tsx`, in the `STATUS_OPTIONS` array, add after the `APPROVED` entry:

```ts
  { value: "REVIEWED", label: "Reviewed" },
```

`CLOSED` already exists in the array.

- [ ] **Step 4: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/types/index.ts src/lib/utils.ts src/app/compliance/page.tsx`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add src/types/index.ts src/lib/utils.ts src/app/compliance/page.tsx
git commit -m "feat(compliance): add REVIEWED status to types, colors, filter"
```

---

### Task 7: Mark-as-Prepared route + submit guard

**Files:**
- Create: `src/app/api/compliance/[id]/prepare/route.ts`
- Modify: `src/app/api/compliance/[id]/submit/route.ts` (allowed-status guard, line 43-48)
- Verify: `repro-prepare.mjs` (temporary)

**Interfaces:**
- Consumes: POST with no body.
- Produces: `POST /api/compliance/[id]/prepare` moves `PENDING_PREPARATION` → `PREPARED` (activity `PREPARED`, from `PENDING_PREPARATION`; audit). `POST /api/compliance/[id]/submit` now only accepts `PREPARED`.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-prepare.mjs` that (a) inserts a `PENDING_PREPARATION` schedule directly, (b) mirrors the CURRENT submit guard (which would allow submit from `PENDING_PREPARATION`) and asserts the NEW behavior (submit must reject `PENDING_PREPARATION` and a `prepare` transition must exist). Clean up afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-prepare.mjs`
Expected: `FAIL: submit should not accept PENDING_PREPARATION`.

- [ ] **Step 3: Create the prepare route**

Create `src/app/api/compliance/[id]/prepare/route.ts`:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError
    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }
    if (existing.status !== "PENDING_PREPARATION") {
      return NextResponse.json(
        { error: "Only PENDING_PREPARATION compliance can be marked as prepared" },
        { status: 400 }
      )
    }

    const isPreparer = existing.assignments?.some(
      (a: { preparerId: string }) => a.preparerId === session.user.id
    )
    if (!isPreparer) {
      return NextResponse.json(
        { error: "Only the assigned preparer can mark this compliance as prepared" },
        { status: 403 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "PREPARED", updatedAt: now() })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    await supabaseAdmin.from("activities").insert({
      id: newId(),
      complianceId: id,
      userId: session.user.id,
      action: "PREPARED",
      fromStatus: "PENDING_PREPARATION",
      toStatus: "PREPARED",
      comments: "Compliance marked as prepared",
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "MARK_PREPARED",
      entity: "ComplianceSchedule",
      entityId: id,
      oldValue: "PENDING_PREPARATION",
      newValue: "PREPARED",
    })

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/prepare error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 4: Update the submit guard**

In `src/app/api/compliance/[id]/submit/route.ts`, replace the guard:

```ts
    if (existing.status !== "PREPARED" && existing.status !== "PENDING_PREPARATION") {
```

with:

```ts
    if (existing.status !== "PREPARED") {
```

- [ ] **Step 5: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-prepare.mjs`
Expected: `PASS`.

- [ ] **Step 6: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/[id]/prepare/route.ts src/app/api/compliance/[id]/submit/route.ts`
Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/api/compliance/[id]/prepare/route.ts src/app/api/compliance/[id]/submit/route.ts
git commit -m "feat(compliance): add mark-as-prepared step"
```

---

### Task 8: Flexible payment/filing ordering + Close route

**Files:**
- Modify: `src/app/api/compliance/[id]/file/route.ts` (guard, line 43-48)
- Modify: `src/app/api/compliance/[id]/mark-paid/route.ts` (guard, line 59-64)
- Create: `src/app/api/compliance/[id]/close/route.ts`
- Verify: `repro-order.mjs` (temporary)

**Interfaces:**
- Produces: `file` accepts `APPROVED | REVIEWED | PAID`; `mark-paid` accepts `FILED | APPROVED | REVIEWED`; new `close` accepts `FILED | PAID` → `CLOSED`.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-order.mjs` that inserts a schedule directly in `PAID` status and (a) mirrors the CURRENT `file` guard (rejects `PAID`) asserting the NEW behavior (PAID → FILED allowed), and (b) checks a `close` transition exists (`FILED`/`PAID` → `CLOSED`). Clean up afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-order.mjs`
Expected: `FAIL: file should accept PAID`.

- [ ] **Step 3: Update the file guard**

In `src/app/api/compliance/[id]/file/route.ts`, replace:

```ts
    if (existing.status !== "APPROVED") {
```

with:

```ts
    if (!["APPROVED", "REVIEWED", "PAID"].includes(existing.status)) {
```

- [ ] **Step 4: Update the mark-paid guard**

In `src/app/api/compliance/[id]/mark-paid/route.ts`, replace:

```ts
    if (existing.status !== "FILED" && existing.status !== "PAID") {
```

with:

```ts
    if (!["FILED", "APPROVED", "REVIEWED"].includes(existing.status)) {
```

- [ ] **Step 5: Create the close route**

Create `src/app/api/compliance/[id]/close/route.ts`:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { activeRole } = getActiveContextFromRequest(_request)
    if (activeRole !== "ADMINISTRATOR" && activeRole !== "MANAGER") {
      return NextResponse.json({ error: "Only administrators or managers can close compliance" }, { status: 403 })
    }

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, status, complianceId")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError
    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }
    if (!["FILED", "PAID"].includes(existing.status)) {
      return NextResponse.json(
        { error: "Only FILED or PAID compliance can be closed" },
        { status: 400 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "CLOSED", updatedAt: now() })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    await supabaseAdmin.from("activities").insert({
      id: newId(),
      complianceId: id,
      userId: session.user.id,
      action: "CLOSED",
      fromStatus: existing.status,
      toStatus: "CLOSED",
      comments: "Compliance closed",
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "CLOSE",
      entity: "ComplianceSchedule",
      entityId: id,
      oldValue: existing.status,
      newValue: "CLOSED",
    })

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/close error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 6: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-order.mjs`
Expected: `PASS`.

- [ ] **Step 7: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/[id]/file/route.ts src/app/api/compliance/[id]/mark-paid/route.ts src/app/api/compliance/[id]/close/route.ts`
Expected: both pass.

- [ ] **Step 8: Commit**

```bash
git add src/app/api/compliance/[id]/file/route.ts src/app/api/compliance/[id]/mark-paid/route.ts src/app/api/compliance/[id]/close/route.ts
git commit -m "feat(compliance): flexible file/pay ordering and close action"
```

---

### Task 9: 2nd-level review routes + reject extension

**Files:**
- Create: `src/app/api/compliance/[id]/request-second-review/route.ts`
- Create: `src/app/api/compliance/[id]/approve-second-review/route.ts`
- Modify: `src/app/api/compliance/[id]/reject/route.ts`
- Verify: `repro-2nd.mjs` (temporary)

**Interfaces:**
- Produces: `request-second-review` (`APPROVED` → `PENDING_REVIEW`, admin, requires `reviewerId`); `approve-second-review` (`PENDING_REVIEW` → `REVIEWED`, reviewer only); `reject` extended to allow `PENDING_REVIEW` → `REJECTED` (reviewer or admin).

- [ ] **Step 1: Write the failing reproduction**

Create `repro-2nd.mjs` that inserts an `APPROVED` schedule with `reviewerId`, mirrors the CURRENT state (no second-review path; `reject` rejects `PENDING_REVIEW`), and asserts the new behavior (second-review request + approve transitions exist). Clean up afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-2nd.mjs`
Expected: `FAIL: second review path missing`.

- [ ] **Step 3: Create the request-second-review route**

Create `src/app/api/compliance/[id]/request-second-review/route.ts`:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { activeRole } = getActiveContextFromRequest(request)
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can request a second review" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()
    const { reviewerId, comments } = body

    if (!reviewerId) {
      return NextResponse.json({ error: "reviewerId is required" }, { status: 400 })
    }

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError
    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }
    if (existing.status !== "APPROVED") {
      return NextResponse.json(
        { error: "Only APPROVED compliance can be sent for a second review" },
        { status: 400 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "PENDING_REVIEW", reviewerId, adminComments: comments || null, updatedAt: now() })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    await supabaseAdmin.from("activities").insert({
      id: newId(),
      complianceId: id,
      userId: session.user.id,
      action: "SENT_FOR_SECOND_REVIEW",
      fromStatus: "APPROVED",
      toStatus: "PENDING_REVIEW",
      comments: comments || "Sent for second-level review",
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "REQUEST_SECOND_REVIEW",
      entity: "ComplianceSchedule",
      entityId: id,
      oldValue: "APPROVED",
      newValue: "PENDING_REVIEW",
    })

    await supabaseAdmin.from("notifications").insert({
      id: newId(),
      userId: reviewerId,
      title: "Compliance Second Review Requested",
      message: `Compliance ${existing.complianceId} has been sent to you for a second-level review`,
      type: "APPROVAL",
      link: `/compliance/${id}`,
    })

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/request-second-review error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 4: Create the approve-second-review route**

Create `src/app/api/compliance/[id]/approve-second-review/route.ts`:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params
    const body = await request.json()
    const { comments } = body

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError
    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }
    if (existing.status !== "PENDING_REVIEW") {
      return NextResponse.json(
        { error: "Compliance must be in PENDING_REVIEW status" },
        { status: 400 }
      )
    }
    if (existing.reviewerId !== session.user.id) {
      return NextResponse.json(
        { error: "Only the assigned reviewer can approve this compliance" },
        { status: 403 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({
        status: "REVIEWED",
        reviewerActionAt: now(),
        reviewerComments: comments || null,
        updatedAt: now(),
      })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    await supabaseAdmin.from("activities").insert({
      id: newId(),
      complianceId: id,
      userId: session.user.id,
      action: "REVIEWER_APPROVED",
      fromStatus: "PENDING_REVIEW",
      toStatus: "REVIEWED",
      comments: comments || "Approved in second-level review",
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "APPROVE_SECOND_REVIEW",
      entity: "ComplianceSchedule",
      entityId: id,
      oldValue: "PENDING_REVIEW",
      newValue: "REVIEWED",
    })

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/approve-second-review error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 5: Extend the reject route**

In `src/app/api/compliance/[id]/reject/route.ts`, the guard at line 53-58 is:

```ts
    if (existing.status !== "PENDING_APPROVAL") {
```

Replace with:

```ts
    if (existing.status !== "PENDING_APPROVAL" && existing.status !== "PENDING_REVIEW") {
```

And update the approval-record lookup so that when status is `PENDING_REVIEW`, the rejection is authorized by reviewer role instead of an approval record. Replace the block that does `existing.approvals.find(...)` and the `approvalRecord` error with a role check:

```ts
    if (existing.status === "PENDING_REVIEW") {
      if (existing.reviewerId !== session.user.id) {
        return NextResponse.json({ error: "Only the assigned reviewer can reject this compliance" }, { status: 403 })
      }
    } else {
      const approvalRecord = existing.approvals.find((a: { approverId: string }) => a.approverId === approverId)
      if (!approvalRecord) {
        return NextResponse.json({ error: "Approver not assigned to this compliance" }, { status: 400 })
      }
      const { error: approvalUpdateError } = await supabaseAdmin
        .from("compliance_approvals")
        .update({
          status: "REJECTED",
          actionAt: new Date().toISOString(),
          comments,
        })
        .eq("id", approvalRecord.id)
      if (approvalUpdateError) throw approvalUpdateError
    }
```

- [ ] **Step 6: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-2nd.mjs`
Expected: `PASS`.

- [ ] **Step 7: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/compliance/[id]/request-second-review/route.ts src/app/api/compliance/[id]/approve-second-review/route.ts src/app/api/compliance/[id]/reject/route.ts`
Expected: both pass.

- [ ] **Step 8: Commit**

```bash
git add src/app/api/compliance/[id]/request-second-review/route.ts src/app/api/compliance/[id]/approve-second-review/route.ts src/app/api/compliance/[id]/reject/route.ts
git commit -m "feat(compliance): add second-level review after approval"
```

---

### Task 10: Compliance detail page — workflow action buttons, remove Edit

**Files:**
- Modify: `src/app/compliance/[id]/page.tsx`

**Interfaces:**
- Consumes: new action endpoints `prepare`, `file` (APPROVED/REVIEWED/PAID), `mark-paid` (FILED/APPROVED/REVIEWED), `close`, `request-second-review`, `approve-second-review`; `data.status`, `data.reviewerId`, `data.reviewer`.
- Produces: action buttons per status; header Edit button removed; reviewer state for second-review dialog.

- [ ] **Step 1: Extend the action dialog type union**

Find the `actionDialog` state type (line 242-244). Add the new types:

```ts
    type: "approve" | "reject" | "submit" | "resubmit" | "file" | "submitToAdmin" | "adminApprove" | "sendToReviewer" | "reviewerApprove" | "markPaid" | "prepare" | "close" | "requestSecondReview" | "approveSecondReview"
```

- [ ] **Step 2: Update `renderActionButtons`**

Replace the `PENDING_PREPARATION` block (lines 488-495):

```ts
    if (status === "PENDING_PREPARATION" && isPreparer()) {
      buttons.push(
        <Button key="submit" onClick={() => setActionDialog({ type: "submit" })}>
          <Send className="h-4 w-4 mr-1" />
          Submit for Approval
        </Button>
      )
    }
```

with:

```ts
    if (status === "PENDING_PREPARATION" && isPreparer()) {
      buttons.push(
        <Button key="prepare" onClick={() => setActionDialog({ type: "prepare" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Mark as Prepared
        </Button>
      )
    }

    if (status === "PREPARED" && isPreparer()) {
      buttons.push(
        <Button key="submit" onClick={() => setActionDialog({ type: "submit" })}>
          <Send className="h-4 w-4 mr-1" />
          Submit for Approval
        </Button>
      )
    }
```

Replace the `APPROVED` block (lines 521-528) and `FILED` block (lines 530-537) with flexible ordering + second review + close:

```ts
    if ((status === "APPROVED" || status === "REVIEWED") && isAdminOrManager()) {
      buttons.push(
        <Button key="file" onClick={() => setActionDialog({ type: "file" })}>
          <FileText className="h-4 w-4 mr-1" />
          File
        </Button>,
        <Button key="markPaid" variant="outline" onClick={() => setActionDialog({ type: "markPaid" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Mark Paid
        </Button>
      )
    }

    if (status === "APPROVED" && isAdminActive && data.reviewerId) {
      buttons.push(
        <Button key="requestSecondReview" variant="outline" onClick={() => setActionDialog({ type: "requestSecondReview" })}>
          <Send className="h-4 w-4 mr-1" />
          Send for 2nd-Level Review
        </Button>
      )
    }

    if (status === "PENDING_REVIEW" && isReviewer()) {
      buttons.push(
        <Button key="approveSecondReview" onClick={() => setActionDialog({ type: "approveSecondReview" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Approve
        </Button>,
        <Button key="reject" variant="destructive" onClick={() => setActionDialog({ type: "reject" })}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      )
    }

    if (status === "FILED" && isAdminOrManager()) {
      buttons.push(
        <Button key="markPaid" onClick={() => setActionDialog({ type: "markPaid" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Mark Paid
        </Button>,
        <Button key="close" variant="outline" onClick={() => setActionDialog({ type: "close" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Close
        </Button>
      )
    }

    if (status === "PAID" && isAdminOrManager()) {
      buttons.push(
        <Button key="file" onClick={() => setActionDialog({ type: "file" })}>
          <FileText className="h-4 w-4 mr-1" />
          File
        </Button>,
        <Button key="close" variant="outline" onClick={() => setActionDialog({ type: "close" })}>
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Close
        </Button>
      )
    }
```

- [ ] **Step 3: Extend the dialog label/description/endpoint maps**

In `getActionLabel`, add:

```ts
      case "prepare": return "Mark as Prepared"
      case "close": return "Close Compliance"
      case "requestSecondReview": return "Send for 2nd-Level Review"
      case "approveSecondReview": return "Approve as Reviewer"
```

In `getActionDescription`, add:

```ts
      case "prepare": return "Mark this compliance as prepared and ready for approval?"
      case "close": return "Close this compliance? It is fully filed/paid."
      case "requestSecondReview": return "Select a reviewer for the second-level review. The compliance moves to Pending Review."
      case "approveSecondReview": return "Approve this compliance as the second-level reviewer?"
```

In `getActionApiEndpoint`, add:

```ts
      case "prepare": return "prepare"
      case "close": return "close"
      case "requestSecondReview": return "request-second-review"
      case "approveSecondReview": return "approve-second-review"
```

- [ ] **Step 4: Wire the request-second-review dialog reviewer select**

In the `handleAction` function, add before the fetch for `request-second-review`:

```ts
      if (action === "request-second-review") {
        if (!reviewerId) throw new Error("Please select a reviewer")
        body.reviewerId = reviewerId
      }
```

In the dialog body render, extend the condition that shows the reviewer `Select` (currently `(actionDialog?.type === "adminApprove" || actionDialog?.type === "sendToReviewer")`) to also include `"requestSecondReview"`, and make the reviewer required for `requestSecondReview`:

```tsx
            {(actionDialog?.type === "adminApprove" || actionDialog?.type === "sendToReviewer" || actionDialog?.type === "requestSecondReview") && (
              ...
              <Select value={reviewerId} onValueChange={setReviewerId}>
                <SelectTrigger id="reviewer">
                  <SelectValue placeholder="Select reviewer" />
                </SelectTrigger>
                ...
              </Select>
            )}
```

Remove the `data?.reviewerId` disabled-input special case (it applies only to `adminApprove`; for the new flow we always show the select).

- [ ] **Step 5: Remove the header Edit button**

Find (lines 657-660):

```tsx
          <Button variant="outline" onClick={() => router.push(`/compliance/${data.id}/edit`)}>
            <Pencil className="h-4 w-4 mr-1" />
            Edit
          </Button>
```

Delete it. Remove the now-unused `Pencil` import from the lucide import list (line 26).

- [ ] **Step 6: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/compliance/[id]/page.tsx`
Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/compliance/[id]/page.tsx
git commit -m "feat(compliance): workflow action buttons, 2nd-level review, close, non-editable"
```

---

### Task 11: Compliance Tracker — Tabs toggle, button removal, non-editable compliance

**Files:**
- Modify: `src/app/compliance/page.tsx`

**Interfaces:**
- Consumes: `GET /api/templates` (listSelect shape), `GET /api/compliance`.
- Produces: `Tabs` with `Compliances` / `Templates`; compliances list loses Edit; "Add New Compliance Template" button removed; template list with Edit (admin/preparer/approver), View, Delete (admin).

- [ ] **Step 1: Add state and imports**

Add `useState` for a `view` toggle and template data. Add imports for `Tabs, TabsContent, TabsList, TabsTrigger` from `@/components/ui/tabs` and `frequencyLabel`/`template` helpers as needed. Add near the existing state:

```ts
  const [view, setView] = useState<"compliances" | "templates">("compliances")

  // template tab state
  const [templates, setTemplates] = useState<TemplateItem[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [templateFilters, setTemplateFilters] = useState({ status: "", countryId: "", entityId: "", taxType: "", frequency: "", search: "" })
  const [templatePage, setTemplatePage] = useState(1)
  const [templateTotal, setTemplateTotal] = useState(0)
```

Add a `TemplateItem` interface (mirror `src/app/master/compliance-templates/page.tsx` lines 104-118) and a `TEMPLATE_STATUS_OPTIONS` constant (DRAFT, PENDING_ADMIN_APPROVAL, PENDING_REVIEW, APPROVED, REJECTED) and a `FREQUENCY_OPTIONS`-based label helper (copy `frequencyLabel` from `src/app/master/compliance-templates/page.tsx` lines 61-78).

- [ ] **Step 2: Add the templates fetch**

Add a `fetchTemplates` callback (patterned after `fetchData` in `src/app/master/compliance-templates/page.tsx` lines 184-212) that calls `/api/templates?<params>` and sets `templates`/`templateTotal`. Reset `templatePage` to 1 when a template filter changes. Use `useCallback` and a `useEffect` keyed on the template filters + page.

- [ ] **Step 3: Replace the header buttons**

Replace the header action div (lines 233-244) with only the Create Template button, shown to admins/preparers/approvers:

```tsx
          <div className="flex items-center gap-2">
            {canCreateTemplate && (
              <Button variant="outline" onClick={() => router.push("/master/compliance-templates/create")}>
                <FileType className="h-4 w-4 mr-1" />
                Create Template
              </Button>
            )}
          </div>
```

where `const canCreateTemplate = isAdmin || role === "PREPARER" || role === "APPROVER"`. The `isPreparer`/`canEdit` variables are no longer needed for compliance Edit — replace `canEdit` usage accordingly (Step 6).

- [ ] **Step 4: Add the Tabs wrapper**

Wrap the existing content (filters + table) inside `Tabs`. Insert after the header div:

```tsx
        <Tabs value={view} onValueChange={(v) => setView(v as "compliances" | "templates")}>
          <TabsList>
            <TabsTrigger value="compliances">
              <FileText className="h-4 w-4 mr-1" />
              Compliances
            </TabsTrigger>
            <TabsTrigger value="templates">
              <FileType className="h-4 w-4 mr-1" />
              Templates
            </TabsTrigger>
          </TabsList>

          <TabsContent value="compliances" className="space-y-4 pt-4">
            {/* existing compliance filters + table, with Edit removed */}
          </TabsContent>

          <TabsContent value="templates" className="space-y-4 pt-4">
            {/* template filters + table */}
          </TabsContent>
        </Tabs>
```

Move the compliance filters + table inside `TabsContent value="compliances"`. Update the search placeholder to `"Search compliance..."` (unchanged). The status `Select` for compliances uses the existing `STATUS_OPTIONS` (now including `REVIEWED` from Task 6).

- [ ] **Step 5: Add the Templates tab content**

Inside `TabsContent value="templates"`, render a filter bar with search, status, country, entity, tax type, frequency (reuse the `countryId`/`entityId` state and add `templateTaxType`/`templateFrequency`/`templateSearch` state), then a table with columns: Template Number, Version, Status, Tax Type, Country, Frequency, Entities (count), Created By, Actions. Actions: View → `/master/compliance-templates/[id]`, Edit → `/master/compliance-templates/[id]/edit` (shown for admin/preparer/approver), Delete (admin) → confirm via AlertDialog (reuse `handleDelete` pattern calling `DELETE /api/templates/[id]`), Generate for Month (admin) optional — link to the templates list page's behavior by navigating to `/master/compliance-templates` (keep scope tight: View/Edit/Delete only).

Use the template pagination controls (mirror the compliance pagination markup but bound to `templatePage`/`templateTotal`).

- [ ] **Step 6: Remove compliance Edit and fix permission vars**

In the compliance table dropdown (lines 396-401), remove the `canEdit` Edit `DropdownMenuItem`. Change:

```ts
  const isAdmin = role === "ADMINISTRATOR"
  const isPreparer = role === "PREPARER"
  const canEdit = isAdmin || isPreparer
```

to:

```ts
  const isAdmin = role === "ADMINISTRATOR"
  const canCreateTemplate = isAdmin || role === "PREPARER" || role === "APPROVER"
```

- [ ] **Step 7: Replace the compliance empty state**

Replace the empty-state block (lines 315-326) so it no longer links to `/compliance/create`:

```tsx
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
            <h3 className="text-lg font-medium mb-1">No compliance items found</h3>
            <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
              Compliances are generated from approved templates.
            </p>
            <Button onClick={() => router.push("/master/compliance-templates")}>
              <FileType className="h-4 w-4 mr-1" />
              Go to Templates
            </Button>
          </div>
```

- [ ] **Step 8: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/compliance/page.tsx`
Expected: both pass.

- [ ] **Step 9: Commit**

```bash
git add src/app/compliance/page.tsx
git commit -m "feat(compliance): tracker tabs for compliances and templates"
```

---

### Task 12: Template PUT — non-admin edits to APPROVED templates become change requests

**Files:**
- Modify: `src/app/api/templates/[id]/route.ts` (PUT, lines 107-114)
- Verify: `repro-changereq.mjs` (temporary)

**Interfaces:**
- Consumes: PUT body (existing fields) + `changeReason`.
- Produces: when caller is non-admin and `existing.status === "APPROVED"`, the template is NOT mutated; a `template_change_requests` row (status `PENDING`) is inserted with `snapshot`, `fieldDiffs`, `changeReason`; org admins are notified; response `{ data: { ...full, changeRequested: true } }`.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-changereq.mjs` that mirrors the CURRENT PUT behavior (non-admin + APPROVED → 403) and asserts the NEW behavior (a `template_change_requests` row is created, template unchanged). Use a real APPROVED template and an org admin user id fetched from `organization_members`. Clean up the created change-request row afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-changereq.mjs`
Expected: `FAIL: change request row not created`.

- [ ] **Step 3: Implement the change-request path in PUT**

In `src/app/api/templates/[id]/route.ts`, replace the admin gate (lines 107-114):

```ts
    const isAdmin = activeRole === "ADMINISTRATOR"

    if (existing.status === "APPROVED" && !isAdmin) {
      return NextResponse.json(
        { error: "Only administrators can edit approved templates" },
        { status: 403 }
      )
    }
```

with:

```ts
    const isAdmin = activeRole === "ADMINISTRATOR"

    if (existing.status === "APPROVED" && !isAdmin) {
      const changeReason = body.changeReason || ""
      if (!changeReason.trim()) {
        return NextResponse.json(
          { error: "changeReason is required for non-admin changes to an approved template" },
          { status: 400 }
        )
      }

      const oldSnapshot = buildSnapshot(existing)
      const proposed: Record<string, unknown> = { ...oldSnapshot }
      const fields = [
        "taxType", "formId", "countryId", "frequency", "dueDateDay",
        "priority", "isRecurring", "notes", "preparerId", "approverId",
      ]
      for (const f of fields) {
        if (body[f] !== undefined) proposed[f] = body[f] === "" ? null : body[f]
      }
      if (body.recurringEndDate !== undefined) {
        proposed.recurringEndDate = body.recurringEndDate ? new Date(body.recurringEndDate).toISOString() : null
      }
      const proposedEntities = Array.isArray(body.entityIds)
        ? Array.from(new Set(body.entityIds as string[])).sort()
        : (existing.entities || []).map((e: { entityId: string }) => e.entityId).sort()

      const diffs = computeDiffs(oldSnapshot, proposed) || {}
      const oldEntityIds = (existing.entities || []).map((e: { entityId: string }) => e.entityId).sort()
      if (JSON.stringify(oldEntityIds) !== JSON.stringify(proposedEntities)) {
        diffs.entityIds = { old: oldEntityIds, new: proposedEntities }
      }

      const { error: crError } = await supabaseAdmin.from("template_change_requests").insert({
        id: newId(),
        templateId: id,
        orgId,
        requestedById: session.user.id,
        snapshot: { ...proposed, entityIds: proposedEntities },
        fieldDiffs: Object.keys(diffs).length > 0 ? diffs : null,
        changeReason,
      })
      if (crError) throw crError

      const { data: admins } = await supabaseAdmin
        .from("organization_members")
        .select("userId")
        .eq("orgId", orgId)
        .contains("roles", ["ADMINISTRATOR"])

      if (admins && admins.length > 0) {
        await supabaseAdmin.from("notifications").insert(
          admins
            .filter((a: { userId: string }) => a.userId !== session.user.id)
            .map((a: { userId: string }) => ({
              id: newId(),
              userId: a.userId,
              title: "Template Change Request",
              message: `${session.user.name || "A user"} requested changes to ${existing.templateNumber || "a template"}`,
              type: "APPROVAL",
              link: `/master/compliance-templates/${id}`,
            }))
        )
      }

      await supabaseAdmin.from("audit_trails").insert({
        id: newId(),
        userId: session.user.id,
        action: "TEMPLATE_CHANGE_REQUESTED",
        entity: "ComplianceTemplate",
        entityId: id,
        oldValue: JSON.stringify(oldSnapshot),
        newValue: JSON.stringify({ ...proposed, entityIds: proposedEntities }),
        comments: changeReason,
      })

      const { data: full } = await supabaseAdmin
        .from("compliance_templates")
        .select(templateSelect)
        .eq("id", id)
        .single()

      return NextResponse.json({ data: { ...full, changeRequested: true } })
    }
```

- [ ] **Step 4: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-changereq.mjs`
Expected: `PASS`.

- [ ] **Step 5: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/templates/[id]/route.ts`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add src/app/api/templates/[id]/route.ts
git commit -m "feat(templates): non-admin edits to approved templates become change requests"
```

---

### Task 13: Template change-request approve/reject routes

**Files:**
- Create: `src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts`
- Create: `src/app/api/templates/[id]/change-requests/[cid]/reject/route.ts`
- Verify: `repro-cr-apply.mjs` (temporary)

**Interfaces:**
- Consumes: `POST /api/templates/[id]/change-requests/[cid]/approve` (admin) and `.../reject` (admin).
- Produces: approve applies the stored `snapshot` (template fields + `entityIds`) to the template, bumps `version`, inserts a `compliance_template_versions` row, marks the request `APPROVED`. Reject marks it `REJECTED`.

- [ ] **Step 1: Write the failing reproduction**

Create `repro-cr-apply.mjs` that inserts a `template_change_requests` row for an APPROVED template and asserts the approve transition applies `snapshot` + bumps version. Clean up afterwards.

- [ ] **Step 2: Run it — expect it to FAIL**

Run: `node repro-cr-apply.mjs`
Expected: `FAIL: change request not applied`.

- [ ] **Step 3: Create the approve route**

Create `src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts`:

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; cid: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId, activeRole } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can approve change requests" }, { status: 403 })
    }

    const { id, cid } = await params
    const body = await request.json().catch(() => ({}))

    const { data: changeRequest, error: crError } = await supabaseAdmin
      .from("template_change_requests")
      .select("*")
      .eq("id", cid)
      .eq("templateId", id)
      .eq("orgId", orgId)
      .single()

    if (crError || !changeRequest) {
      return NextResponse.json({ error: "Change request not found" }, { status: 404 })
    }
    if (changeRequest.status !== "PENDING") {
      return NextResponse.json({ error: "Change request is not pending" }, { status: 400 })
    }

    const { data: template, error: templateError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (templateError || !template) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const snapshot = changeRequest.snapshot || {}
    const { entityIds, ...fieldUpdates } = snapshot
    const updateData: Record<string, unknown> = {
      ...fieldUpdates,
      version: (template.version || 0) + 1,
      updatedAt: now(),
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update(updateData)
      .eq("id", id)
    if (updateError) throw updateError

    if (Array.isArray(entityIds)) {
      await supabaseAdmin.from("compliance_template_entities").delete().eq("templateId", id)
      if (entityIds.length > 0) {
        const { error: entityError } = await supabaseAdmin
          .from("compliance_template_entities")
          .insert(entityIds.map((entityId: string) => ({
            id: newId(),
            templateId: id,
            entityId,
          })))
        if (entityError) throw entityError
      }
    }

    await supabaseAdmin.from("compliance_template_versions").insert({
      id: newId(),
      templateId: id,
      version: (template.version || 0) + 1,
      snapshot,
      fieldDiffs: changeRequest.fieldDiffs,
      changeReason: changeRequest.changeReason || null,
      changedById: changeRequest.requestedById,
    })

    await supabaseAdmin.from("template_change_requests").update({
      status: "APPROVED",
      reviewedById: session.user.id,
      reviewedAt: now(),
      reviewComments: body.comments || null,
    }).eq("id", cid)

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "CHANGE_REQUEST_APPROVED",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify(snapshot),
    })

    return NextResponse.json({ data: { success: true } })
  } catch (error) {
    console.error("POST /api/templates/[id]/change-requests/[cid]/approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 4: Create the reject route**

Create `src/app/api/templates/[id]/change-requests/[cid]/reject/route.ts` (same scaffolding as approve):

```ts
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; cid: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId, activeRole } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can reject change requests" }, { status: 403 })
    }

    const { id, cid } = await params
    const body = await request.json().catch(() => ({}))

    const { data: changeRequest, error: crError } = await supabaseAdmin
      .from("template_change_requests")
      .select("*")
      .eq("id", cid)
      .eq("templateId", id)
      .eq("orgId", orgId)
      .single()

    if (crError || !changeRequest) {
      return NextResponse.json({ error: "Change request not found" }, { status: 404 })
    }
    if (changeRequest.status !== "PENDING") {
      return NextResponse.json({ error: "Change request is not pending" }, { status: 400 })
    }

    await supabaseAdmin.from("template_change_requests").update({
      status: "REJECTED",
      reviewedById: session.user.id,
      reviewedAt: now(),
      reviewComments: body.comments || null,
    }).eq("id", cid)

    if (changeRequest.requestedById) {
      await supabaseAdmin.from("notifications").insert({
        id: newId(),
        userId: changeRequest.requestedById,
        title: "Template Change Request Rejected",
        message: body.comments || "Your requested template change was rejected by an admin",
        type: "REJECTION",
        link: `/master/compliance-templates/${id}`,
      })
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "CHANGE_REQUEST_REJECTED",
      entity: "ComplianceTemplate",
      entityId: id,
      comments: body.comments || null,
    })

    return NextResponse.json({ data: { success: true } })
  } catch (error) {
    console.error("POST /api/templates/[id]/change-requests/[cid]/reject error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 5: Update the reproduction to mirror the NEW logic, then run it**

Run: `node repro-cr-apply.mjs`
Expected: `PASS`.

- [ ] **Step 6: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts src/app/api/templates/[id]/change-requests/[cid]/reject/route.ts`
Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts src/app/api/templates/[id]/change-requests/[cid]/reject/route.ts
git commit -m "feat(templates): admin approve/reject change requests"
```

---

### Task 14: Template edit page + detail page change-request UI

**Files:**
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx`
- Modify: `src/app/api/templates/[id]/route.ts` (GET select — include `changeRequests` embedded)
- Modify: `src/app/master/compliance-templates/[id]/page.tsx`

**Interfaces:**
- Consumes: `template_change_requests` rows embedded on GET; `changeRequested` flag from PUT.
- Produces: non-admins can edit approved templates (PUT stores a change request); detail page shows pending change requests with Approve/Reject for admins.

- [ ] **Step 1: Include change requests in the template GET**

In `src/app/api/templates/[id]/route.ts`, add to `templateSelect` (line 7-19):

```ts
  changeRequests:template_change_requests(*, requestedBy:users!template_change_requests_requestedById_fkey(id, name, email))
```

- [ ] **Step 2: Allow non-admin edits on the edit page**

In `src/app/master/compliance-templates/[id]/edit/page.tsx`:
1. Replace `const readOnly = approved && !isAdmin` (line 136) with `const readOnly = false`.
2. Replace the amber read-only banner (lines 344-349) with:

```tsx
      {approved && !isAdmin && (
        <div className="flex items-start gap-2 rounded-md border border-blue-300 bg-blue-50 dark:bg-blue-950/40 p-4 text-sm text-blue-800 dark:text-blue-200">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>Your changes will be submitted for admin approval before being applied to this approved template.</span>
        </div>
      )}
```

3. Change the `changeReason` block visibility (lines 567-581) to show for non-admin too, and make it required:

```tsx
            {approved && (
              <div className="space-y-2">
                <Label htmlFor="changeReason">
                  Change Reason {!isAdmin && <span className="text-red-500">*</span>}
                </Label>
                <Textarea
                  id="changeReason"
                  placeholder="Reason for this change (required for admin approval)..."
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  rows={3}
                />
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  {isAdmin
                    ? "Saving this approved template creates a new version with the reason recorded."
                    : "Required. An admin will review and approve your changes before they are applied."}
                </p>
              </div>
            )}
```

4. Update the body to always include `changeReason` (remove the `if (approved && isAdmin && ...)` guard):

```ts
      if (changeReason.trim()) body.changeReason = changeReason.trim()
```

5. Update submit validation: if `approved && !isAdmin && !changeReason.trim()`, show a validation toast and return.
6. Update the success handling: when the response has `changeRequested`, show `"Changes submitted for admin approval"` and still navigate to the detail page:

```ts
      const json = await res.json()
      toast({
        title: "Success",
        description: json.data?.changeRequested ? "Changes submitted for admin approval" : "Template updated successfully",
      })
      router.push(`/master/compliance-templates/${id}`)
```

- [ ] **Step 3: Add the change-request section to the detail page**

In `src/app/master/compliance-templates/[id]/page.tsx`:
1. Add a `ChangeRequest` interface:

```ts
interface ChangeRequest {
  id: string
  templateId: string
  requestedById: string
  requestedBy?: User | null
  changeReason: string | null
  fieldDiffs: Record<string, { old: unknown; new: unknown }> | null
  status: string
  requestedAt: string | null
}
```

Add `changeRequests: ChangeRequest[]` to the `TemplateDetail` interface and state `const [changeRequestComment, setChangeRequestComment] = useState("")` and `const [actingRequestId, setActingRequestId] = useState<string | null>(null)`.

2. Add handlers:

```ts
  async function handleChangeRequest(cid: string, action: "approve" | "reject") {
    if (!data) return
    setActingRequestId(cid)
    try {
      const res = await fetch(`/api/templates/${data.id}/change-requests/${cid}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comments: changeRequestComment || undefined }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || "Request failed")
      }
      toast({ title: "Success", description: action === "approve" ? "Change request approved" : "Change request rejected" })
      setChangeRequestComment("")
      await loadTemplate()
    } catch (err) {
      toast({ title: "Error", description: (err as Error).message, variant: "destructive" })
    } finally {
      setActingRequestId(null)
    }
  }
```

3. Add a `changeRequests` `TabsTrigger` (with count) and a `TabsContent` showing pending requests (or all) in a table: Requested By, Reason, Requested At, Status, Field Diffs (reuse `FragmentRow`), and for `PENDING` + `isAdmin`: a comment `Textarea` + Approve / Reject buttons.

- [ ] **Step 4: Verify types and lint**

Run: `npx tsc --noEmit` then `npx eslint src/app/master/compliance-templates/[id]/edit/page.tsx src/app/master/compliance-templates/[id]/page.tsx src/app/api/templates/[id]/route.ts`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add src/app/master/compliance-templates/[id]/edit/page.tsx src/app/master/compliance-templates/[id]/page.tsx src/app/api/templates/[id]/route.ts
git commit -m "feat(templates): non-admin edits route to admin approval with change-request UI"
```

---

### Task 15: End-to-end verification

**Files:**
- Verify: temporary reproduction scripts removed; full typecheck + lint; manual browser checks

- [ ] **Step 1: Remove all temporary reproduction scripts**

```bash
Remove-Item repro-enum.mjs, repro-gen-one.mjs, repro-gen-bulk.mjs, repro-first.mjs, repro-filter.mjs, repro-prepare.mjs, repro-order.mjs, repro-2nd.mjs, repro-changereq.mjs, repro-cr-apply.mjs -ErrorAction SilentlyContinue
```

- [ ] **Step 2: Full typecheck and lint**

Run: `npx tsc --noEmit`
Then:
```bash
npx eslint src/app/api/templates/[id]/generate/route.ts src/app/api/templates/generate/route.ts src/lib/template-compliance.ts src/app/api/compliance/route.ts src/types/index.ts src/lib/utils.ts src/app/compliance/page.tsx src/app/compliance/[id]/page.tsx "src/app/api/compliance/[id]/prepare/route.ts" "src/app/api/compliance/[id]/submit/route.ts" "src/app/api/compliance/[id]/file/route.ts" "src/app/api/compliance/[id]/mark-paid/route.ts" "src/app/api/compliance/[id]/close/route.ts" "src/app/api/compliance/[id]/request-second-review/route.ts" "src/app/api/compliance/[id]/approve-second-review/route.ts" "src/app/api/compliance/[id]/reject/route.ts" "src/app/api/templates/[id]/route.ts" "src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts" "src/app/api/templates/[id]/change-requests/[cid]/reject/route.ts" "src/app/master/compliance-templates/[id]/edit/page.tsx" "src/app/master/compliance-templates/[id]/page.tsx"
```
Expected: all pass.

- [ ] **Step 3: Confirm git state is clean of stray artifacts**

Run: `git status --porcelain`
Expected: only intended feature files plus pre-existing unrelated working-tree changes (no `repro-*.mjs`).

- [ ] **Step 4: Ask the user to perform manual browser verification (logged in at `http://localhost:3000`)**

1. As admin, generate compliances for a month from a template with **2+ entities** → the Compliance Tracker shows **one** row listing all entity names, starting at **Pending Preparation**.
2. In the Compliance Tracker, confirm the **Templates / Compliances** tabs switch views; templates show View + Edit for preparer/approver; compliances show only View + Delete (no Edit).
3. As a preparer, open a Pending Preparation compliance → **Mark as Prepared**, then **Submit for Approval**; approver approves; admin files; mark paid; close.
4. From **Approved**, admin sends a compliance to a reviewer → reviewer approves → status **Reviewed** → can File / Mark Paid.
5. Non-admin edits an **approved template** → gets "submitted for admin approval" toast; admin sees the change request on the template detail page and Approves → template version bumps and fields update.
