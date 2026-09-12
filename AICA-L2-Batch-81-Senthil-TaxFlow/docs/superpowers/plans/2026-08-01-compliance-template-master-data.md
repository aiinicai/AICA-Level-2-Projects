# Compliance Template Master Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a versioned Compliance Template system under Master Data that serves as the single source for generating compliance trackers, with approval workflows, audit trails, and admin-triggered bulk generation.

**Architecture:** New `compliance_templates`, `compliance_template_entities`, and `compliance_template_versions` tables created via Supabase migration SQL. Two new fields (`templateId`, `templateVersion`) added to `compliance_schedules`. API routes under `/api/templates/` follow existing compliance route patterns (auth, supabaseAdmin, activities, audit_trails). Frontend adds a Master Data sub-section at `/master/compliance-templates` with list, detail, create/edit views, plus a "Create Template" button on the Compliance Tracker page.

**Tech Stack:** Next.js 16, Supabase (PostgreSQL via supabaseAdmin), Prisma schema (for types/generation only — runtime uses Supabase client), React 19, Radix UI, Tailwind CSS v4, Lucide icons.

## Global Constraints

- All new DB rows use `id: newId()` (crypto.randomUUID) and `updatedAt: now()` from `@/lib/db`
- Auth: `auth()` from `@/lib/auth`, org context from `getActiveContextFromRequest(request)` in `@/lib/auth-context`
- DB access: `supabaseAdmin` from `@/lib/supabase` (service-role, lazy proxy)
- API responses: `NextResponse.json({ data } | { error }, { status })`, `try/catch` with `console.error`
- Activities: `activities` table with `action, fromStatus, toStatus, comments`
- Audit: `audit_trails` table with `action, entity, entityId, oldValue, newValue`
- Notifications: `notifications` table with `id, userId, title, message, type, link`
- Template number format: `TPL-{TAXTYPE}-{COUNTRY_CODE}-###` (zero-padded 3-digit sequence per tax-type+country)
- Only ADMINISTRATOR role can edit approved templates, delete compliances, or trigger generation
- No test framework exists in the project — verification is manual via browser + API calls
- Existing Prisma schema is for type generation only; runtime queries use Supabase client directly

---

### Task 1: Database Migration — New Tables and Schema Changes

**Files:**
- Create: `supabase/migrations/20260801000000_compliance_templates.sql`
- Modify: `prisma/schema.prisma`

**Interfaces:**
- Consumes: Nothing (foundation task)
- Produces: Tables `compliance_templates`, `compliance_template_entities`, `compliance_template_versions`; columns `templateId`, `templateVersion` on `compliance_schedules`

- [ ] **Step 1: Create the Supabase migration SQL**

Create `supabase/migrations/20260801000000_compliance_templates.sql`:

```sql
-- Compliance Templates
CREATE TABLE IF NOT EXISTS compliance_templates (
  id TEXT PRIMARY KEY,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "templateNumber" TEXT UNIQUE,
  version INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  "isActive" BOOLEAN NOT NULL DEFAULT true,

  "taxType" TEXT,
  "complianceTypeId" TEXT REFERENCES compliance_types(id),
  "formId" TEXT REFERENCES form_master(id),
  "countryId" TEXT NOT NULL REFERENCES countries(id),
  frequency TEXT NOT NULL,
  "dueDateDay" INTEGER,
  priority TEXT NOT NULL DEFAULT 'NORMAL',
  "isRecurring" BOOLEAN NOT NULL DEFAULT true,
  "recurringEndDate" TIMESTAMPTZ,
  notes TEXT,

  "preparerId" TEXT REFERENCES users(id),
  "approverId" TEXT REFERENCES users(id),

  "submittedAt" TIMESTAMPTZ,
  "submittedById" TEXT REFERENCES users(id),
  "adminApprovedAt" TIMESTAMPTZ,
  "adminApprovedById" TEXT REFERENCES users(id),
  "reviewerId" TEXT REFERENCES users(id),
  "reviewerActionAt" TIMESTAMPTZ,
  "reviewerComments" TEXT,
  "adminComments" TEXT,
  "approvedAt" TIMESTAMPTZ,
  "approvedById" TEXT REFERENCES users(id),
  "rejectedAt" TIMESTAMPTZ,
  "rejectedById" TEXT REFERENCES users(id),

  "createdById" TEXT NOT NULL REFERENCES users(id),
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_templates_org ON compliance_templates("orgId");
CREATE INDEX idx_templates_status ON compliance_templates(status);
CREATE INDEX idx_templates_country ON compliance_templates("countryId");
CREATE INDEX idx_templates_tax_type ON compliance_templates("taxType");

-- Template ↔ Entity junction
CREATE TABLE IF NOT EXISTS compliance_template_entities (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "entityId" TEXT NOT NULL REFERENCES legal_entities(id),
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("templateId", "entityId")
);

-- Template version history
CREATE TABLE IF NOT EXISTS compliance_template_versions (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  "changedById" TEXT NOT NULL REFERENCES users(id),
  "changedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("templateId", version)
);

-- Link compliance_schedules back to template
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "templateId" TEXT REFERENCES compliance_templates(id),
  ADD COLUMN IF NOT EXISTS "templateVersion" INTEGER;

CREATE INDEX idx_schedules_template ON compliance_schedules("templateId");
```

- [ ] **Step 2: Run the migration against Supabase**

```powershell
# Copy the SQL and run it via the Supabase SQL editor or CLI
# Verify tables exist:
# SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'compliance_template%';
```

- [ ] **Step 3: Update Prisma schema with new models**

Add to `prisma/schema.prisma`:

```prisma
enum ComplianceTemplateStatus {
  DRAFT
  PENDING_ADMIN_APPROVAL
  PENDING_REVIEW
  APPROVED
  REJECTED
}

model ComplianceTemplate {
  id                  String   @id @default(cuid())
  orgId               String
  org                 Organization @relation(fields: [orgId], references: [id])
  templateNumber      String?  @unique
  version             Int      @default(0)
  status              String   @default("DRAFT")
  isActive            Boolean  @default(true)

  taxType             String?
  complianceTypeId    String?
  complianceType      ComplianceType? @relation(fields: [complianceTypeId], references: [id])
  formId              String?
  form                FormMaster?     @relation(fields: [formId], references: [id])
  countryId           String
  country             Country         @relation(fields: [countryId], references: [id])
  frequency           Frequency
  dueDateDay          Int?
  priority            Priority @default(NORMAL)
  isRecurring         Boolean  @default(true)
  recurringEndDate    DateTime?
  notes               String?

  preparerId          String?
  preparer            User?    @relation("TemplatePreparer", fields: [preparerId], references: [id])
  approverId          String?
  approver            User?    @relation("TemplateApprover", fields: [approverId], references: [id])

  submittedAt         DateTime?
  submittedById       String?
  submittedBy         User?    @relation("TemplateSubmittedBy", fields: [submittedById], references: [id])
  adminApprovedAt     DateTime?
  adminApprovedById   String?
  adminApprovedBy     User?    @relation("TemplateAdminApprovedBy", fields: [adminApprovedById], references: [id])
  reviewerId          String?
  reviewer            User?    @relation("TemplateReviewer", fields: [reviewerId], references: [id])
  reviewerActionAt    DateTime?
  reviewerComments    String?
  adminComments       String?
  approvedAt          DateTime?
  approvedById        String?
  approvedBy          User?    @relation("TemplateApprovedBy", fields: [approvedById], references: [id])
  rejectedAt          DateTime?
  rejectedById        String?
  rejectedBy          User?    @relation("TemplateRejectedBy", fields: [rejectedById], references: [id])

  createdById         String
  createdBy           User     @relation("TemplateCreatedBy", fields: [createdById], references: [id])
  createdAt           DateTime @default(now())
  updatedAt           DateTime @updatedAt

  entities            ComplianceTemplateEntity[]
  versions            ComplianceTemplateVersion[]
  generatedCompliances ComplianceSchedule[]

  @@map("compliance_templates")
}

model ComplianceTemplateEntity {
  id         String             @id @default(cuid())
  templateId String
  template   ComplianceTemplate @relation(fields: [templateId], references: [id], onDelete: Cascade)
  entityId   String
  entity     LegalEntity        @relation(fields: [entityId], references: [id])
  createdAt  DateTime           @default(now())

  @@unique([templateId, entityId])
  @@map("compliance_template_entities")
}

model ComplianceTemplateVersion {
  id           String             @id @default(cuid())
  templateId   String
  template     ComplianceTemplate @relation(fields: [templateId], references: [id], onDelete: Cascade)
  version      Int
  snapshot     Json
  fieldDiffs   Json?
  changeReason String?
  changedById  String
  changedBy    User               @relation("TemplateVersionChangedBy", fields: [changedById], references: [id])
  changedAt    DateTime           @default(now())

  @@unique([templateId, version])
  @@map("compliance_template_versions")
}
```

Add relation fields to existing models:

On `ComplianceSchedule`, add:
```prisma
  templateId          String?
  template            ComplianceTemplate? @relation(fields: [templateId], references: [id])
  templateVersion     Int?
```

On `Organization`, add to relations:
```prisma
  templates ComplianceTemplate[]
```

On `Country`, add:
```prisma
  templates ComplianceTemplate[]
```

On `ComplianceType`, add:
```prisma
  templates ComplianceTemplate[]
```

On `FormMaster`, add:
```prisma
  templates ComplianceTemplate[]
```

On `LegalEntity`, add:
```prisma
  templateEntities ComplianceTemplateEntity[]
```

On `User`, add all relation fields:
```prisma
  templatesPreparer         ComplianceTemplate[] @relation("TemplatePreparer")
  templatesApprover         ComplianceTemplate[] @relation("TemplateApprover")
  templatesSubmittedBy      ComplianceTemplate[] @relation("TemplateSubmittedBy")
  templatesAdminApprovedBy  ComplianceTemplate[] @relation("TemplateAdminApprovedBy")
  templatesReviewer         ComplianceTemplate[] @relation("TemplateReviewer")
  templatesApprovedBy       ComplianceTemplate[] @relation("TemplateApprovedBy")
  templatesRejectedBy       ComplianceTemplate[] @relation("TemplateRejectedBy")
  templatesCreatedBy        ComplianceTemplate[] @relation("TemplateCreatedBy")
  templateVersionsChangedBy ComplianceTemplateVersion[] @relation("TemplateVersionChangedBy")
```

- [ ] **Step 4: Verify Prisma schema validates**

```powershell
npx prisma validate
```

- [ ] **Step 5: Commit**

```powershell
git add supabase/migrations/20260801000000_compliance_templates.sql prisma/schema.prisma
git commit -m "feat: add compliance_templates tables and prisma schema"
```

---

### Task 2: Template CRUD API Routes

**Files:**
- Create: `src/app/api/templates/route.ts`
- Create: `src/app/api/templates/[id]/route.ts`

**Interfaces:**
- Consumes: Tables from Task 1, `auth()`, `supabaseAdmin`, `newId()`, `now()`, `getActiveContextFromRequest()`
- Produces: `GET /api/templates` (list with filters), `POST /api/templates` (create), `GET /api/templates/[id]` (detail), `PUT /api/templates/[id]` (update with versioning), `DELETE /api/templates/[id]` (admin only)

- [ ] **Step 1: Create the template list/create route at `src/app/api/templates/route.ts`**

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const templateSelect = `
  *,
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber, country:countries(name), businessUnit)),
  versions:compliance_template_versions(id, version, changedAt, changedById, changeReason),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email),
  reviewer:users!compliance_templates_reviewerId_fkey(id, name, email),
  preparer:users!compliance_templates_preparerId_fkey(id, name, email),
  approver:users!compliance_templates_approverId_fkey(id, name, email)
`

const listSelect = `
  *,
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email)
`

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""
    const status = searchParams.get("status") || ""
    const countryId = searchParams.get("countryId") || ""
    const entityId = searchParams.get("entityId") || ""
    const taxType = searchParams.get("taxType") || ""
    const formId = searchParams.get("formId") || ""
    const frequency = searchParams.get("frequency") || ""
    const page = parseInt(searchParams.get("page") || "1", 10)
    const limit = parseInt(searchParams.get("limit") || "15", 10)
    const from = (page - 1) * limit
    const to = from + limit - 1

    let query = supabaseAdmin
      .from("compliance_templates")
      .select(listSelect, { count: "exact" })
      .eq("orgId", orgId)

    if (search) query = query.ilike("templateNumber", `%${search}%`)
    if (status && status !== "all") query = query.eq("status", status)
    if (countryId && countryId !== "all") query = query.eq("countryId", countryId)
    if (taxType && taxType !== "all") query = query.eq("taxType", taxType)
    if (formId && formId !== "all") query = query.eq("formId", formId)
    if (frequency && frequency !== "all") query = query.eq("frequency", frequency)
    if (entityId && entityId !== "all") {
      const { data: templateIds } = await supabaseAdmin
        .from("compliance_template_entities")
        .select("templateId")
        .eq("entityId", entityId)
      const ids = (templateIds || []).map((t: { templateId: string }) => t.templateId)
      if (ids.length > 0) {
        query = query.in("id", ids)
      } else {
        return NextResponse.json({ data: [], total: 0 })
      }
    }

    query = query.order("createdAt", { ascending: false }).range(from, to)

    const { data, error, count } = await query
    if (error) throw error

    return NextResponse.json({ data: data || [], total: count || 0 })
  } catch (error) {
    console.error("GET /api/templates error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const body = await request.json()
    const {
      entityIds, taxType, formId, countryId, frequency, dueDateDay,
      priority, isRecurring, recurringEndDate, notes,
      preparerId, approverId,
    } = body

    const entities = Array.isArray(entityIds) && entityIds.length > 0
      ? Array.from(new Set(entityIds)) : []

    if (entities.length === 0 || !taxType || !countryId || !frequency) {
      return NextResponse.json(
        { error: "entityIds, taxType, countryId, and frequency are required" },
        { status: 400 }
      )
    }

    const templateId = newId()

    const { error: createError } = await supabaseAdmin
      .from("compliance_templates")
      .insert({
        id: templateId,
        orgId,
        status: "DRAFT",
        version: 0,
        taxType,
        formId: formId || null,
        countryId,
        frequency,
        dueDateDay: dueDateDay || null,
        priority: priority || "NORMAL",
        isRecurring: isRecurring ?? true,
        recurringEndDate: recurringEndDate ? new Date(recurringEndDate).toISOString() : null,
        notes: notes || null,
        preparerId: preparerId || null,
        approverId: approverId || null,
        createdById: session.user.id,
        updatedAt: now(),
      })

    if (createError) throw createError

    if (entities.length > 0) {
      const { error: entityError } = await supabaseAdmin
        .from("compliance_template_entities")
        .insert(entities.map((eid: string) => ({
          id: newId(),
          templateId,
          entityId: eid,
        })))
      if (entityError) throw entityError
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "CREATE",
      entity: "ComplianceTemplate",
      entityId: templateId,
      newValue: JSON.stringify({ taxType, countryId, frequency, entities }),
    })

    const { data: full, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", templateId)
      .single()

    if (fetchError) throw fetchError

    return NextResponse.json({ data: full }, { status: 201 })
  } catch (error) {
    console.error("POST /api/templates error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 2: Create the template detail/update/delete route at `src/app/api/templates/[id]/route.ts`**

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const templateSelect = `
  *,
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber, country:countries(name), businessUnit)),
  versions:compliance_template_versions(id, version, changedAt, changedById, changeReason, fieldDiffs, changedBy:users!compliance_template_versions_changedById_fkey(id, name)),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email),
  reviewer:users!compliance_templates_reviewerId_fkey(id, name, email),
  preparer:users!compliance_templates_preparerId_fkey(id, name, email),
  approver:users!compliance_templates_approverId_fkey(id, name, email),
  generatedCompliances:compliance_schedules(id, complianceId, status, filingMonth, dueDate, createdAt)
`

function buildSnapshot(row: Record<string, unknown>) {
  const { id, orgId, createdAt, updatedAt, versions, entities, generatedCompliances, createdBy, reviewer, preparer, approver, country, form, complianceType, ...rest } = row as Record<string, unknown>
  void id; void orgId; void createdAt; void updatedAt; void versions; void entities; void generatedCompliances; void createdBy; void reviewer; void preparer; void approver; void country; void form; void complianceType
  return rest
}

function computeDiffs(oldSnap: Record<string, unknown>, newSnap: Record<string, unknown>) {
  const diffs: Record<string, { old: unknown; new: unknown }> = {}
  const allKeys = new Set([...Object.keys(oldSnap), ...Object.keys(newSnap)])
  for (const key of allKeys) {
    if (JSON.stringify(oldSnap[key]) !== JSON.stringify(newSnap[key])) {
      diffs[key] = { old: oldSnap[key], new: newSnap[key] }
    }
  }
  return Object.keys(diffs).length > 0 ? diffs : null
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", id)
      .single()

    if (error || !data) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (data.versions) {
      (data.versions as Array<Record<string, unknown>>).sort(
        (a, b) => (b.version as number) - (a.version as number)
      )
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
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

    const { id } = await params
    const body = await request.json()

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(*)")
      .eq("id", id)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const isAdmin = activeRole === "ADMINISTRATOR"

    if (existing.status === "APPROVED" && !isAdmin) {
      return NextResponse.json(
        { error: "Only administrators can edit approved templates" },
        { status: 403 }
      )
    }

    const oldSnapshot = buildSnapshot(existing)

    const updates: Record<string, unknown> = { updatedAt: now() }
    const fields = [
      "taxType", "formId", "countryId", "frequency", "dueDateDay",
      "priority", "isRecurring", "notes", "preparerId", "approverId",
    ]
    for (const f of fields) {
      if (body[f] !== undefined) updates[f] = body[f] === "" ? null : body[f]
    }
    if (body.recurringEndDate !== undefined) {
      updates.recurringEndDate = body.recurringEndDate ? new Date(body.recurringEndDate).toISOString() : null
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update(updates)
      .eq("id", id)

    if (updateError) throw updateError

    if (body.entityIds !== undefined) {
      await supabaseAdmin.from("compliance_template_entities").delete().eq("templateId", id)
      const entities = Array.from(new Set(body.entityIds as string[]))
      if (entities.length > 0) {
        const { error: entityError } = await supabaseAdmin
          .from("compliance_template_entities")
          .insert(entities.map((eid: string) => ({
            id: newId(),
            templateId: id,
            entityId: eid,
          })))
        if (entityError) throw entityError
      }
    }

    if (existing.status === "APPROVED") {
      const { data: updated } = await supabaseAdmin
        .from("compliance_templates")
        .select("*")
        .eq("id", id)
        .single()

      const newSnapshot = buildSnapshot(updated || {})
      const diffs = computeDiffs(oldSnapshot, newSnapshot as Record<string, unknown>)

      if (diffs) {
        const newVersion = existing.version + 1
        await supabaseAdmin.from("compliance_templates").update({ version: newVersion, updatedAt: now() }).eq("id", id)

        await supabaseAdmin.from("compliance_template_versions").insert({
          id: newId(),
          templateId: id,
          version: newVersion,
          snapshot: newSnapshot,
          fieldDiffs: diffs,
          changeReason: body.changeReason || null,
          changedById: session.user.id,
        })

        await supabaseAdmin.from("audit_trails").insert({
          id: newId(),
          userId: session.user.id,
          action: "TEMPLATE_VERSION_CREATED",
          entity: "ComplianceTemplate",
          entityId: id,
          oldValue: JSON.stringify(oldSnapshot),
          newValue: JSON.stringify(newSnapshot),
          comments: `Version ${newVersion} created`,
        })
      }
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "UPDATE",
      entity: "ComplianceTemplate",
      entityId: id,
      oldValue: JSON.stringify(oldSnapshot),
      newValue: JSON.stringify(updates),
    })

    const { data: full, error: refetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", id)
      .single()

    if (refetchError) throw refetchError

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("PUT /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
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
      return NextResponse.json({ error: "Only administrators can delete templates" }, { status: 403 })
    }

    const { id } = await params

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("id, templateNumber")
      .eq("id", id)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const { count } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id", { count: "exact", head: true })
      .eq("templateId", id)

    if ((count || 0) > 0) {
      return NextResponse.json(
        { error: "Cannot delete template with generated compliances. Deactivate it instead." },
        { status: 400 }
      )
    }

    await supabaseAdmin.from("compliance_template_versions").delete().eq("templateId", id)
    await supabaseAdmin.from("compliance_template_entities").delete().eq("templateId", id)
    await supabaseAdmin.from("compliance_templates").delete().eq("id", id)

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "DELETE",
      entity: "ComplianceTemplate",
      entityId: id,
      oldValue: JSON.stringify({ templateNumber: existing.templateNumber }),
    })

    return NextResponse.json({ data: { success: true } })
  } catch (error) {
    console.error("DELETE /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 3: Verify API routes compile**

```powershell
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add src/app/api/templates/route.ts src/app/api/templates/[id]/route.ts
git commit -m "feat: add template CRUD API routes"
```

---

### Task 3: Template Workflow API Routes (Submit, Approve, Reviewer, Reject)

**Files:**
- Create: `src/app/api/templates/[id]/submit/route.ts`
- Create: `src/app/api/templates/[id]/admin-approve/route.ts`
- Create: `src/app/api/templates/[id]/send-to-reviewer/route.ts`
- Create: `src/app/api/templates/[id]/reviewer-approve/route.ts`
- Create: `src/app/api/templates/[id]/reject/route.ts`
- Create: `src/app/api/templates/[id]/activate/route.ts`

**Interfaces:**
- Consumes: Tables from Task 1, `auth()`, `supabaseAdmin`, `newId()`, `now()`; `generateTemplateNumber()` defined in this task
- Produces: POST endpoints for each workflow action; `generateTemplateNumber(taxType, countryCode, orgId)` helper used by approve routes

- [ ] **Step 1: Create `src/app/api/templates/[id]/submit/route.ts`**

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

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
    const body = await request.json().catch(() => ({}))

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (existing.status !== "DRAFT") {
      return NextResponse.json({ error: "Only draft templates can be submitted" }, { status: 400 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "PENDING_ADMIN_APPROVAL",
        submittedAt: now(),
        submittedById: session.user.id,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_SUBMITTED",
      entity: "ComplianceTemplate",
      entityId: id,
      comments: body.comments || "Template submitted for admin approval",
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/submit error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 2: Create helper for template number generation**

Create `src/lib/template-number.ts`:

```typescript
import { supabaseAdmin } from "@/lib/supabase"

export async function generateTemplateNumber(
  taxType: string,
  countryCode: string,
  orgId: string
): Promise<string> {
  const prefix = `TPL-${taxType}-${countryCode}`

  const { data: existing } = await supabaseAdmin
    .from("compliance_templates")
    .select("templateNumber")
    .eq("orgId", orgId)
    .ilike("templateNumber", `${prefix}-%`)
    .order("templateNumber", { ascending: false })
    .limit(1)

  let seq = 1
  if (existing && existing.length > 0) {
    const last = existing[0].templateNumber as string
    const parts = last.split("-")
    const lastNum = parseInt(parts[parts.length - 1], 10)
    if (!isNaN(lastNum)) seq = lastNum + 1
  }

  return `${prefix}-${String(seq).padStart(3, "0")}`
}
```

- [ ] **Step 3: Create `src/app/api/templates/[id]/admin-approve/route.ts`**

This is the most complex route — it approves the template, assigns template number + version 1, creates the version snapshot, and generates the first compliance.

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { generateTemplateNumber } from "@/lib/template-number"
import { NextResponse } from "next/server"

async function generateFirstCompliance(
  template: Record<string, unknown>,
  entities: Array<{ entityId: string }>,
  orgId: string,
  userId: string,
  filingMonth: string
) {
  const results: Array<{ entityId: string; complianceId: string; status: string }> = []
  const skipped: Array<{ entityId: string; reason: string }> = []

  for (const te of entities) {
    const { data: existingCompliance } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id")
      .eq("entityId", te.entityId)
      .eq("filingMonth", filingMonth)
      .eq("templateId", template.id as string)
      .maybeSingle()

    if (existingCompliance) {
      skipped.push({ entityId: te.entityId, reason: `Compliance already exists for ${filingMonth}` })
      continue
    }

    const { data: entity } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId")
      .eq("id", te.entityId)
      .single()

    const digits = Math.floor(10000 + Math.random() * 90000)
    const complianceId = `TAX-${digits}`
    const scheduleId = newId()

    const dueDate = new Date()
    if (template.dueDateDay) {
      const [year, month] = filingMonth.split("-").map(Number)
      dueDate.setFullYear(year, month - 1, template.dueDateDay as number)
    } else {
      const [year, month] = filingMonth.split("-").map(Number)
      dueDate.setFullYear(year, month, 0)
    }

    const periodStart = new Date(dueDate.getFullYear(), dueDate.getMonth(), 1)
    const periodEnd = new Date(dueDate.getFullYear(), dueDate.getMonth() + 1, 0)

    const { error: createError } = await supabaseAdmin
      .from("compliance_schedules")
      .insert({
        id: scheduleId,
        orgId,
        complianceId,
        entityId: te.entityId,
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
        status: "DRAFT",
        isRecurring: template.isRecurring ?? true,
        recurringEndDate: template.recurringEndDate || null,
        notes: template.notes || null,
        templateId: template.id,
        templateVersion: template.version,
        updatedAt: now(),
        createdById: userId,
      })

    if (createError) throw createError

    await supabaseAdmin.from("compliance_entities").insert({
      id: newId(),
      complianceId: scheduleId,
      entityId: te.entityId,
    })

    if (template.preparerId) {
      await supabaseAdmin.from("compliance_assignments").insert({
        id: newId(),
        complianceId: scheduleId,
        preparerId: template.preparerId,
        updatedAt: now(),
      })
    }

    if (template.approverId) {
      await supabaseAdmin.from("compliance_approvals").insert({
        id: newId(),
        complianceId: scheduleId,
        approverId: template.approverId,
        status: "PENDING_APPROVAL",
        updatedAt: now(),
      })
    }

    await supabaseAdmin.from("activities").insert({
      id: newId(),
      complianceId: scheduleId,
      userId,
      action: "CREATED",
      toStatus: "DRAFT",
      comments: `Generated from template ${template.templateNumber} v${template.version}`,
    })

    results.push({ entityId: te.entityId, complianceId, status: "created" })
  }

  return { generated: results, skipped }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
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
      return NextResponse.json({ error: "Only administrators can approve templates" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json().catch(() => ({}))

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
      .eq("id", id)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (!["DRAFT", "PENDING_ADMIN_APPROVAL"].includes(existing.status)) {
      return NextResponse.json({ error: "Template cannot be approved in its current state" }, { status: 400 })
    }

    if (body.reviewerId) {
      const { error: updateError } = await supabaseAdmin
        .from("compliance_templates")
        .update({
          reviewerId: body.reviewerId,
          updatedAt: now(),
        })
        .eq("id", id)
      if (updateError) throw updateError
    }

    const countryCode = (existing.country as { code: string })?.code || "XX"
    const templateNumber = existing.templateNumber || await generateTemplateNumber(existing.taxType || "TAX", countryCode, orgId)

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "APPROVED",
        templateNumber,
        version: 1,
        approvedAt: now(),
        approvedById: session.user.id,
        adminApprovedAt: now(),
        adminApprovedById: session.user.id,
        adminComments: body.comments || null,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    const { data: approved } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    const snapshot = {
      taxType: approved.taxType, formId: approved.formId, countryId: approved.countryId,
      frequency: approved.frequency, dueDateDay: approved.dueDateDay, priority: approved.priority,
      isRecurring: approved.isRecurring, recurringEndDate: approved.recurringEndDate,
      notes: approved.notes, preparerId: approved.preparerId, approverId: approved.approverId,
      entityIds: (existing.entities || []).map((e: { entityId: string }) => e.entityId),
    }

    await supabaseAdmin.from("compliance_template_versions").insert({
      id: newId(),
      templateId: id,
      version: 1,
      snapshot,
      changeReason: "Initial approval",
      changedById: session.user.id,
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_APPROVED",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify({ templateNumber, version: 1 }),
      comments: body.comments || "Template approved",
    })

    const currentDate = new Date()
    const filingMonth = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`

    const generationResult = await generateFirstCompliance(
      { ...approved, templateNumber, version: 1 },
      existing.entities || [],
      orgId,
      session.user.id,
      filingMonth
    )

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), versions:compliance_template_versions(id, version, changedAt, changeReason), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full, generation: generationResult })
  } catch (error) {
    console.error("POST /api/templates/[id]/admin-approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 4: Create `src/app/api/templates/[id]/send-to-reviewer/route.ts`**

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

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
      return NextResponse.json({ error: "Only administrators can send templates for review" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()

    if (!body.reviewerId) {
      return NextResponse.json({ error: "reviewerId is required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (!["DRAFT", "PENDING_ADMIN_APPROVAL"].includes(existing.status)) {
      return NextResponse.json({ error: "Template cannot be sent for review in its current state" }, { status: 400 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "PENDING_REVIEW",
        reviewerId: body.reviewerId,
        adminComments: body.comments || null,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    await supabaseAdmin.from("notifications").insert({
      id: newId(),
      userId: body.reviewerId,
      title: "Template Review Requested",
      message: `You have been assigned to review a compliance template`,
      type: "REVIEW",
      link: `/master/compliance-templates/${id}`,
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_SENT_TO_REVIEWER",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify({ reviewerId: body.reviewerId }),
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email), reviewer:users!compliance_templates_reviewerId_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/send-to-reviewer error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 5: Create `src/app/api/templates/[id]/reviewer-approve/route.ts`**

This follows the same pattern as admin-approve but for the assigned reviewer. On approval, it assigns template number + version 1 and generates the first compliance.

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { generateTemplateNumber } from "@/lib/template-number"
import { NextResponse } from "next/server"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { id } = await params
    const body = await request.json().catch(() => ({}))

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
      .eq("id", id)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (existing.status !== "PENDING_REVIEW") {
      return NextResponse.json({ error: "Template is not pending review" }, { status: 400 })
    }

    if (existing.reviewerId !== session.user.id) {
      return NextResponse.json({ error: "You are not the assigned reviewer" }, { status: 403 })
    }

    const countryCode = (existing.country as { code: string })?.code || "XX"
    const templateNumber = existing.templateNumber || await generateTemplateNumber(existing.taxType || "TAX", countryCode, orgId)

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "APPROVED",
        templateNumber,
        version: 1,
        approvedAt: now(),
        approvedById: session.user.id,
        reviewerActionAt: now(),
        reviewerComments: body.comments || null,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    const { data: approved } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    const snapshot = {
      taxType: approved.taxType, formId: approved.formId, countryId: approved.countryId,
      frequency: approved.frequency, dueDateDay: approved.dueDateDay, priority: approved.priority,
      isRecurring: approved.isRecurring, recurringEndDate: approved.recurringEndDate,
      notes: approved.notes, preparerId: approved.preparerId, approverId: approved.approverId,
      entityIds: (existing.entities || []).map((e: { entityId: string }) => e.entityId),
    }

    await supabaseAdmin.from("compliance_template_versions").insert({
      id: newId(),
      templateId: id,
      version: 1,
      snapshot,
      changeReason: "Reviewer approval",
      changedById: session.user.id,
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_REVIEWER_APPROVED",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify({ templateNumber, version: 1 }),
      comments: body.comments || "Template approved by reviewer",
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), versions:compliance_template_versions(id, version, changedAt, changeReason), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/reviewer-approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 6: Create `src/app/api/templates/[id]/reject/route.ts`**

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

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
    const { id } = await params
    const body = await request.json()

    if (!body.comments) {
      return NextResponse.json({ error: "Rejection reason is required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const isAdmin = activeRole === "ADMINISTRATOR"
    const isReviewer = existing.reviewerId === session.user.id

    if (existing.status === "PENDING_ADMIN_APPROVAL" && !isAdmin) {
      return NextResponse.json({ error: "Only administrators can reject" }, { status: 403 })
    }
    if (existing.status === "PENDING_REVIEW" && !isReviewer && !isAdmin) {
      return NextResponse.json({ error: "Only the assigned reviewer can reject" }, { status: 403 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "REJECTED",
        rejectedAt: now(),
        rejectedById: session.user.id,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    if (existing.createdById) {
      await supabaseAdmin.from("notifications").insert({
        id: newId(),
        userId: existing.createdById,
        title: "Template Rejected",
        message: `Your compliance template has been rejected: ${body.comments}`,
        type: "REJECTION",
        link: `/master/compliance-templates/${id}`,
      })
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_REJECTED",
      entity: "ComplianceTemplate",
      entityId: id,
      comments: body.comments,
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/reject error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 7: Create `src/app/api/templates/[id]/activate/route.ts`** (handles both activate and deactivate via `isActive` in body)

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

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
      return NextResponse.json({ error: "Only administrators can activate/deactivate templates" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()

    const isActive = body.isActive ?? true

    const { error } = await supabaseAdmin
      .from("compliance_templates")
      .update({ isActive, updatedAt: now() })
      .eq("id", id)

    if (error) throw error

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: isActive ? "TEMPLATE_ACTIVATED" : "TEMPLATE_DEACTIVATED",
      entity: "ComplianceTemplate",
      entityId: id,
    })

    return NextResponse.json({ data: { success: true, isActive } })
  } catch (error) {
    console.error("POST /api/templates/[id]/activate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 8: Verify all routes compile**

```powershell
npm run build
```

- [ ] **Step 9: Commit**

```powershell
git add src/app/api/templates/ src/lib/template-number.ts
git commit -m "feat: add template workflow API routes (submit, approve, review, reject, activate)"
```

---

### Task 4: Template Generation API Route

**Files:**
- Create: `src/app/api/templates/generate/route.ts`
- Create: `src/app/api/templates/[id]/generate/route.ts`

**Interfaces:**
- Consumes: Tables from Task 1, `auth()`, `supabaseAdmin`, `newId()`, `now()`
- Produces: `POST /api/templates/generate` (bulk/filtered), `POST /api/templates/[id]/generate` (single template)

- [ ] **Step 1: Create `src/app/api/templates/generate/route.ts`** (bulk + filtered generation)

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
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
      return NextResponse.json({ error: "Only administrators can generate compliances" }, { status: 403 })
    }

    const body = await request.json()
    const { filingMonth, filters } = body

    if (!filingMonth) {
      return NextResponse.json({ error: "filingMonth is required (e.g. 2026-08)" }, { status: 400 })
    }

    let query = supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
      .eq("orgId", orgId)
      .eq("status", "APPROVED")
      .eq("isActive", true)

    if (filters?.countryIds?.length > 0) {
      query = query.in("countryId", filters.countryIds)
    }
    if (filters?.taxTypes?.length > 0) {
      query = query.in("taxType", filters.taxTypes)
    }
    if (filters?.formIds?.length > 0) {
      query = query.in("formId", filters.formIds)
    }

    const { data: templates, error: fetchError } = await query
    if (fetchError) throw fetchError

    let filteredTemplates = templates || []

    if (filters?.entityIds?.length > 0) {
      filteredTemplates = filteredTemplates.filter((t: Record<string, unknown>) =>
        (t.entities as Array<{ entityId: string }>)?.some((e) =>
          filters.entityIds.includes(e.entityId)
        )
      )
    }

    const generated: Array<{ templateId: string; templateNumber: string; entityId: string; complianceId: string }> = []
    const skipped: Array<{ templateId: string; templateNumber: string; entityId: string; reason: string }> = []
    const errors: Array<{ templateId: string; error: string }> = []

    const [fYear, fMonth] = filingMonth.split("-").map(Number)

    for (const template of filteredTemplates) {
      if (template.recurringEndDate) {
        const endDate = new Date(template.recurringEndDate)
        const filingDate = new Date(fYear, fMonth - 1, 1)
        if (filingDate > endDate) {
          skipped.push({
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
          const { data: existingCompliance } = await supabaseAdmin
            .from("compliance_schedules")
            .select("id, complianceId")
            .eq("entityId", te.entityId)
            .eq("filingMonth", filingMonth)
            .eq("templateId", template.id)
            .maybeSingle()

          if (existingCompliance) {
            skipped.push({
              templateId: template.id,
              templateNumber: template.templateNumber,
              entityId: te.entityId,
              reason: `Compliance ${existingCompliance.complianceId} already exists for ${filingMonth}`,
            })
            continue
          }

          const { data: entity } = await supabaseAdmin
            .from("legal_entities")
            .select("id, countryId")
            .eq("id", te.entityId)
            .single()

          const digits = Math.floor(10000 + Math.random() * 90000)
          const complianceId = `TAX-${digits}`
          const scheduleId = newId()

          const dueDate = new Date(fYear, fMonth - 1, template.dueDateDay || 28)
          if (dueDate.getMonth() !== fMonth - 1) {
            dueDate.setDate(0)
          }

          const periodStart = new Date(fYear, fMonth - 1, 1)
          const periodEnd = new Date(fYear, fMonth, 0)

          await supabaseAdmin.from("compliance_schedules").insert({
            id: scheduleId,
            orgId,
            complianceId,
            entityId: te.entityId,
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
            status: "DRAFT",
            isRecurring: template.isRecurring ?? true,
            recurringEndDate: template.recurringEndDate || null,
            notes: template.notes || null,
            templateId: template.id,
            templateVersion: template.version,
            updatedAt: now(),
            createdById: session.user.id,
          })

          await supabaseAdmin.from("compliance_entities").insert({
            id: newId(),
            complianceId: scheduleId,
            entityId: te.entityId,
          })

          if (template.preparerId) {
            await supabaseAdmin.from("compliance_assignments").insert({
              id: newId(),
              complianceId: scheduleId,
              preparerId: template.preparerId,
              updatedAt: now(),
            })
          }

          if (template.approverId) {
            await supabaseAdmin.from("compliance_approvals").insert({
              id: newId(),
              complianceId: scheduleId,
              approverId: template.approverId,
              status: "PENDING_APPROVAL",
              updatedAt: now(),
            })
          }

          await supabaseAdmin.from("activities").insert({
            id: newId(),
            complianceId: scheduleId,
            userId: session.user.id,
            action: "CREATED",
            toStatus: "DRAFT",
            comments: `Generated from template ${template.templateNumber} v${template.version} for ${filingMonth}`,
          })

          generated.push({
            templateId: template.id,
            templateNumber: template.templateNumber,
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

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "BULK_GENERATE_COMPLIANCES",
      entity: "ComplianceTemplate",
      newValue: JSON.stringify({
        filingMonth,
        filters,
        generated: generated.length,
        skipped: skipped.length,
        errors: errors.length,
      }),
    })

    return NextResponse.json({
      data: {
        generated,
        skipped,
        errors,
        summary: {
          total: generated.length + skipped.length + errors.length,
          created: generated.length,
          skipped: skipped.length,
          failed: errors.length,
        },
      },
    })
  } catch (error) {
    console.error("POST /api/templates/generate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 2: Create `src/app/api/templates/[id]/generate/route.ts`** (single template generation)

```typescript
import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
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
      return NextResponse.json({ error: "Only administrators can generate compliances" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()
    const { filingMonth } = body

    if (!filingMonth) {
      return NextResponse.json({ error: "filingMonth is required (e.g. 2026-08)" }, { status: 400 })
    }

    const { data: template } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId)")
      .eq("id", id)
      .single()

    if (!template) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }
    if (template.status !== "APPROVED") {
      return NextResponse.json({ error: "Only approved templates can generate compliances" }, { status: 400 })
    }
    if (!template.isActive) {
      return NextResponse.json({ error: "Template is inactive" }, { status: 400 })
    }

    if (template.recurringEndDate) {
      const [fYear, fMonth] = filingMonth.split("-").map(Number)
      const filingDate = new Date(fYear, fMonth - 1, 1)
      if (filingDate > new Date(template.recurringEndDate)) {
        return NextResponse.json({ error: "Filing month exceeds recurring end date" }, { status: 400 })
      }
    }

    const generated: Array<{ entityId: string; complianceId: string }> = []
    const skipped: Array<{ entityId: string; reason: string }> = []
    const [fYear, fMonth] = filingMonth.split("-").map(Number)

    for (const te of (template.entities || []) as Array<{ entityId: string }>) {
      const { data: existingCompliance } = await supabaseAdmin
        .from("compliance_schedules")
        .select("id, complianceId")
        .eq("entityId", te.entityId)
        .eq("filingMonth", filingMonth)
        .eq("templateId", template.id)
        .maybeSingle()

      if (existingCompliance) {
        skipped.push({
          entityId: te.entityId,
          reason: `Compliance ${existingCompliance.complianceId} already exists for ${filingMonth}`,
        })
        continue
      }

      const { data: entity } = await supabaseAdmin
        .from("legal_entities")
        .select("id, countryId")
        .eq("id", te.entityId)
        .single()

      const digits = Math.floor(10000 + Math.random() * 90000)
      const complianceId = `TAX-${digits}`
      const scheduleId = newId()

      const dueDate = new Date(fYear, fMonth - 1, template.dueDateDay || 28)
      if (dueDate.getMonth() !== fMonth - 1) dueDate.setDate(0)

      const periodStart = new Date(fYear, fMonth - 1, 1)
      const periodEnd = new Date(fYear, fMonth, 0)

      await supabaseAdmin.from("compliance_schedules").insert({
        id: scheduleId,
        orgId,
        complianceId,
        entityId: te.entityId,
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
        status: "DRAFT",
        isRecurring: template.isRecurring ?? true,
        recurringEndDate: template.recurringEndDate || null,
        notes: template.notes || null,
        templateId: template.id,
        templateVersion: template.version,
        updatedAt: now(),
        createdById: session.user.id,
      })

      await supabaseAdmin.from("compliance_entities").insert({
        id: newId(), complianceId: scheduleId, entityId: te.entityId,
      })

      if (template.preparerId) {
        await supabaseAdmin.from("compliance_assignments").insert({
          id: newId(), complianceId: scheduleId, preparerId: template.preparerId, updatedAt: now(),
        })
      }

      if (template.approverId) {
        await supabaseAdmin.from("compliance_approvals").insert({
          id: newId(), complianceId: scheduleId, approverId: template.approverId, status: "PENDING_APPROVAL", updatedAt: now(),
        })
      }

      await supabaseAdmin.from("activities").insert({
        id: newId(), complianceId: scheduleId, userId: session.user.id,
        action: "CREATED", toStatus: "DRAFT",
        comments: `Generated from template ${template.templateNumber} v${template.version} for ${filingMonth}`,
      })

      generated.push({ entityId: te.entityId, complianceId })
    }

    return NextResponse.json({
      data: { generated, skipped, summary: { created: generated.length, skipped: skipped.length } },
    })
  } catch (error) {
    console.error("POST /api/templates/[id]/generate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

- [ ] **Step 3: Verify build**

```powershell
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add src/app/api/templates/generate/ src/app/api/templates/[id]/generate/
git commit -m "feat: add template generation API routes (bulk and single)"
```

---

### Task 5: Navigation & Layout Updates

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx` (add Compliance Templates child under Master Data)
- Modify: `src/app/master/layout.tsx` (add tab link)
- Modify: `src/app/master/page.tsx` (add card)

**Interfaces:**
- Consumes: Nothing (UI scaffolding)
- Produces: Navigation entry at `/master/compliance-templates`

- [ ] **Step 1: Add sidebar nav item**

In `src/components/layout/app-sidebar.tsx`, add to the `Master Data` children array (after `Exchange Rates`):

```typescript
{ title: "Compliance Templates", href: "/master/compliance-templates", icon: FileType },
```

- [ ] **Step 2: Add `FileType` import if not already present**

`FileType` is already imported in the sidebar icon list.

- [ ] **Step 3: Add tab link in master layout**

In `src/app/master/layout.tsx`, add to `navItems` array and add `FileType` import:

```typescript
import { Globe, Building2, Tag, BookOpen, Users, DollarSign, FileType } from "lucide-react"

const navItems = [
  { href: "/master/countries", label: "Countries", icon: Globe },
  { href: "/master/entities", label: "Entities", icon: Building2 },
  { href: "/master/forms", label: "Forms", icon: BookOpen },
  { href: "/master/employees", label: "Employees", icon: Users },
  { href: "/master/exchange-rates", label: "Exchange Rates", icon: DollarSign },
  { href: "/master/compliance-templates", label: "Templates", icon: FileType },
]
```

- [ ] **Step 4: Add overview card in master page**

In `src/app/master/page.tsx`, add import and card:

```typescript
import { Building2, Globe, Tag, BookOpen, Users, Coins, FileType } from "lucide-react"

// Add to overviewCards array:
{
  title: "Compliance Templates",
  description: "Manage compliance templates, versioning, and generate compliance trackers.",
  icon: FileType,
  href: "/master/compliance-templates",
  color: "bg-indigo-500",
},
```

- [ ] **Step 5: Verify build**

```powershell
npm run build
```

- [ ] **Step 6: Commit**

```powershell
git add src/components/layout/app-sidebar.tsx src/app/master/layout.tsx src/app/master/page.tsx
git commit -m "feat: add compliance templates to navigation and master data overview"
```

---

### Task 6: Compliance Templates List Page

**Files:**
- Create: `src/app/master/compliance-templates/page.tsx`

**Interfaces:**
- Consumes: `GET /api/templates` from Task 2, `POST /api/templates/generate` from Task 4, `DELETE /api/templates/[id]` from Task 2
- Produces: List page at `/master/compliance-templates` with filters, table, bulk generate modal, per-row actions

- [ ] **Step 1: Create `src/app/master/compliance-templates/page.tsx`**

This is a large file (~600 lines). It follows the same pattern as `src/app/compliance/page.tsx` with:
- Filter bar (status, country, entity, tax type, form, frequency, search)
- Table with template data, version badge, entity count, actions dropdown
- "Create Template" button (admin only)
- "Generate for Month" bulk button → modal with filing month picker + optional filters
- Per-row "Generate for Month" action
- Delete with AlertDialog (admin only, blocked if has generated compliances)

The page should use `useAuth()` to check `activeRole === "ADMINISTRATOR"` for admin-only actions, fetch countries/entities/forms on mount for filter dropdowns, and paginate results.

Create the file at `src/app/master/compliance-templates/page.tsx` following the exact patterns from `src/app/compliance/page.tsx` (state management, fetch pattern, table structure, dialog patterns) and `src/app/master/forms/page.tsx` (master data card style).

Key sections:
1. **State**: `data`, `loading`, `filters` (status, countryId, entityId, taxType, formId, frequency, search), `page`, `total`, `generateDialog` (open, filingMonth, filters), `deleteId`
2. **Data fetching**: `fetchData` builds query params from filters, calls `GET /api/templates`
3. **Generate modal**: Filing month input + optional country/entity/tax type filters, calls `POST /api/templates/generate` or `POST /api/templates/[id]/generate`
4. **Table columns**: Template Number, Version, Status, Tax Type, Country, Form, Frequency, Entities (count), Recurring, Created By, Actions
5. **Actions dropdown**: View (`/master/compliance-templates/[id]`), Edit (`/master/compliance-templates/[id]/edit`), Generate for Month, Activate/Deactivate, Delete

- [ ] **Step 2: Verify build**

```powershell
npm run build
```

- [ ] **Step 3: Commit**

```powershell
git add src/app/master/compliance-templates/page.tsx
git commit -m "feat: add compliance templates list page with filters and generation"
```

---

### Task 7: Template Detail Page

**Files:**
- Create: `src/app/master/compliance-templates/[id]/page.tsx`

**Interfaces:**
- Consumes: `GET /api/templates/[id]` from Task 2, all workflow routes from Task 3
- Produces: Detail page with overview, versions, audit trail, generated compliances tabs; action buttons for approval workflow

- [ ] **Step 1: Create `src/app/master/compliance-templates/[id]/page.tsx`**

This follows the same pattern as `src/app/compliance/[id]/page.tsx` with:
- **Tabs**: Overview, Versions, Generated Compliances
- **Overview**: All template fields in card grid (entities, tax type, form, frequency, due date day, priority, recurring settings, preparer, approver, created by, approval info)
- **Versions**: Table of versions with version number, changed by, changed at, change reason, field diffs (expandable)
- **Generated Compliances**: Table of compliance schedules linked to this template (complianceId, status, filingMonth, dueDate, link to `/compliance/[id]`)
- **Action buttons** (top bar):
  - Submit for Approval (if DRAFT, any user)
  - Approve / Send to Reviewer / Reject (if PENDING_ADMIN_APPROVAL, admin)
  - Approve / Reject (if PENDING_REVIEW, reviewer)
  - Generate for Month (if APPROVED, admin)
  - Edit (if DRAFT or admin)
  - Activate/Deactivate (if APPROVED, admin)
- **Action dialogs**: Same Dialog pattern as compliance detail page with comment fields, reviewer select

- [ ] **Step 2: Verify build**

```powershell
npm run build
```

- [ ] **Step 3: Commit**

```powershell
git add src/app/master/compliance-templates/[id]/page.tsx
git commit -m "feat: add compliance template detail page with versions and actions"
```

---

### Task 8: Template Create/Edit Pages

**Files:**
- Create: `src/app/master/compliance-templates/create/page.tsx`
- Create: `src/app/master/compliance-templates/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `POST /api/templates` from Task 2, `PUT /api/templates/[id]` from Task 2, `GET /api/templates/[id]` from Task 2
- Produces: Create page at `/master/compliance-templates/create`, Edit page at `/master/compliance-templates/[id]/edit`

- [ ] **Step 1: Create `src/app/master/compliance-templates/create/page.tsx`**

This mirrors `src/app/compliance/create/page.tsx` with adjustments:
- Fields: Tax Type, Form (filtered by tax type), Country (inferred from entities), Entities (multi-select), Frequency, Due Date Day (1-31 number input instead of date picker), Priority, Preparer, Approver, Is Recurring, Recurring End Date, Notes
- On submit: POST to `/api/templates`
- Redirect to `/master/compliance-templates` on success

- [ ] **Step 2: Create `src/app/master/compliance-templates/[id]/edit/page.tsx`**

This mirrors `src/app/compliance/[id]/edit/page.tsx` with:
- Load existing template via `GET /api/templates/[id]`
- Same form fields as create
- If template is APPROVED and user is not admin: show read-only view with message "Only administrators can edit approved templates"
- If template is APPROVED and user is admin: show edit form with optional "Change Reason" textarea
- On submit: PUT to `/api/templates/[id]`
- Redirect to `/master/compliance-templates/[id]` on success

- [ ] **Step 3: Verify build**

```powershell
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add src/app/master/compliance-templates/create/ src/app/master/compliance-templates/[id]/edit/
git commit -m "feat: add compliance template create and edit pages"
```

---

### Task 9: "Create Template" Button on Compliance Tracker Page

**Files:**
- Modify: `src/app/compliance/page.tsx`

**Interfaces:**
- Consumes: Nothing new (just adds a navigation button)
- Produces: "Create Template" button visible to preparers and admins on the compliance tracker page

- [ ] **Step 1: Add "Create Template" button to compliance tracker header**

In `src/app/compliance/page.tsx`, find the header area where the "Add New Compliance" button is rendered. Add a second button next to it:

```tsx
{(isAdmin || isPreparer) && (
  <Button variant="outline" onClick={() => router.push("/master/compliance-templates/create")}>
    <FileType className="h-4 w-4 mr-1" />
    Create Template
  </Button>
)}
```

Import `FileType` from `lucide-react` at the top of the file.

- [ ] **Step 2: Add admin-only delete gate on compliance tracker**

In `src/app/compliance/page.tsx`, ensure the delete action in the actions dropdown is only visible to admins (it already checks `isAdmin` based on the codebase exploration — verify and fix if needed).

- [ ] **Step 3: Verify build**

```powershell
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add src/app/compliance/page.tsx
git commit -m "feat: add create template button to compliance tracker page"
```

---

### Task 10: Compliance Tracker Delete Restriction (Admin Only)

**Files:**
- Modify: `src/app/api/compliance/[id]/route.ts` (DELETE handler)

**Interfaces:**
- Consumes: `auth()`, `getActiveContextFromRequest()`
- Produces: DELETE restricted to ADMINISTRATOR role only

- [ ] **Step 1: Add admin check to DELETE handler**

In `src/app/api/compliance/[id]/route.ts`, in the `DELETE` function, add role check after auth:

```typescript
const { activeRole } = getActiveContextFromRequest(request)
if (activeRole !== "ADMINISTRATOR") {
  return NextResponse.json({ error: "Only administrators can delete compliances" }, { status: 403 })
}
```

Ensure `getActiveContextFromRequest` is imported (it may already be imported for other handlers in the same file).

- [ ] **Step 2: Verify build**

```powershell
npm run build
```

- [ ] **Step 3: Commit**

```powershell
git add src/app/api/compliance/[id]/route.ts
git commit -m "feat: restrict compliance deletion to administrators only"
```

---

### Task 11: End-to-End Verification

**Files:** None (manual testing)

**Interfaces:**
- Consumes: All previous tasks
- Produces: Verified working system

- [ ] **Step 1: Run the migration SQL against Supabase**

Execute the contents of `supabase/migrations/20260801000000_compliance_templates.sql` in the Supabase SQL editor.

- [ ] **Step 2: Start dev server and verify navigation**

```powershell
npm run dev
```

Open `http://localhost:3000`, verify:
1. Sidebar shows "Compliance Templates" under Master Data
2. Master Data overview page shows "Compliance Templates" card
3. Master Data tab bar shows "Templates" tab
4. Click through to `/master/compliance-templates` — page loads without errors

- [ ] **Step 3: Create a template**

1. Navigate to `/master/compliance-templates/create`
2. Fill in: Tax Type = GST, Country (select from entities), Entities (select one), Frequency = Monthly, Due Date Day = 15, Priority = Normal, Is Recurring = Yes
3. Submit — should create DRAFT template

- [ ] **Step 4: Approve the template (as admin)**

1. Navigate to template detail page
2. Click "Approve" button
3. Verify: template gets template number (TPL-GST-XX-001), version = 1
4. Verify: first compliance is generated in compliance tracker

- [ ] **Step 5: Generate for next month**

1. On template detail or list page, click "Generate for Month"
2. Select next month
3. Verify: compliance created for next month
4. Try generating again for same month — verify HARD BLOCK (skipped)

- [ ] **Step 6: Edit approved template and verify versioning**

1. Edit template (as admin) — change priority from NORMAL to HIGH
2. Save
3. Verify: version incremented to 2
4. Check version history tab — shows v1 and v2 with field diff

- [ ] **Step 7: Verify compliance tracker delete restriction**

1. Log in as non-admin user
2. Try to delete a compliance — should get 403 error
3. Log in as admin — delete should work

- [ ] **Step 8: Final build check**

```powershell
npm run build
npm run lint
```

- [ ] **Step 9: Commit any remaining fixes**

```powershell
git add -A
git commit -m "feat: compliance template system - end-to-end verified"
```
