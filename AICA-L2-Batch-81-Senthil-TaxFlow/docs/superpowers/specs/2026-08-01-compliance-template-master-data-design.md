# Compliance Template Master Data Design

## Overview

This design introduces a **Compliance Template** system that serves as the master definition for generating compliance trackers. Templates are created by preparers (from Compliance Tracker) or admins (from Master Data), approved by admin/reviewer, versioned, and used by admins to bulk-generate compliance trackers for specific filing months.

---

## 1. Data Model

### 1.1 New Prisma Models

```prisma
enum ComplianceTemplateStatus {
  DRAFT
  PENDING_ADMIN_APPROVAL
  PENDING_REVIEW
  APPROVED
  REJECTED
}

model ComplianceTemplate {
  id                  String                     @id @default(cuid())
  orgId               String
  org                 Organization               @relation(fields: [orgId], references: [id])
  
  // Template identification
  templateNumber      String                     @unique  // TPL-{TAXTYPE}-{COUNTRY}-###
  version             Int                        @default(1)
  status              ComplianceTemplateStatus   @default(DRAFT)
  isActive            Boolean                    @default(true)
  
  // Configuration (mirrors ComplianceSchedule fields)
  taxType             TaxType?
  complianceTypeId    String?
  complianceType      ComplianceType?            @relation(fields: [complianceTypeId], references: [id])
  formId              String?
  form                FormMaster?                @relation(fields: [formId], references: [id])
  countryId           String
  country             Country                    @relation(fields: [countryId], references: [id])
  frequency           Frequency
  dueDateRule         String?                    // e.g., "15th of following month"
  priority            Priority                   @default(NORMAL)
  isRecurring         Boolean                    @default(true)
  recurringEndDate    DateTime?
  notes               String?
  
  // Approval tracking
  submittedAt         DateTime?
  submittedById       String?
  submittedBy         User?                      @relation("TemplateSubmittedBy", fields: [submittedById], references: [id])
  adminApprovedAt     DateTime?
  adminApprovedById   String?
  adminApprovedBy     User?                      @relation("TemplateAdminApprovedBy", fields: [adminApprovedById], references: [id])
  reviewerId          String?
  reviewer            User?                      @relation("TemplateReviewer", fields: [reviewerId], references: [id])
  reviewerActionAt    DateTime?
  reviewerComments    String?
  adminComments       String?
  approvedAt          DateTime?
  approvedById        String?
  approvedBy          User?                      @relation("TemplateApprovedBy", fields: [approvedById], references: [id])
  rejectedAt          DateTime?
  rejectedById        String?
  rejectedBy          User?                      @relation("TemplateRejectedBy", fields: [rejectedById], references: [id])
  
  // Audit
  createdById         String
  createdBy           User                       @relation("TemplateCreatedBy", fields: [createdById], references: [id])
  createdAt           DateTime                   @default(now())
  updatedAt           DateTime                   @updatedAt
  
  // Relations
  entities            ComplianceTemplateEntity[]
  versions            ComplianceTemplateVersion[]
  generatedCompliances ComplianceSchedule[]      // Track which compliances were generated from this template
  
  @@unique([orgId, templateNumber])
  @@map("compliance_templates")
}

model ComplianceTemplateEntity {
  id              String               @id @default(cuid())
  templateId      String
  template        ComplianceTemplate   @relation(fields: [templateId], references: [id], onDelete: Cascade)
  entityId        String
  entity          LegalEntity          @relation(fields: [entityId], references: [id])
  createdAt       DateTime             @default(now())
  
  @@unique([templateId, entityId])
  @@map("compliance_template_entities")
}

model ComplianceTemplateVersion {
  id              String               @id @default(cuid())
  templateId      String
  template        ComplianceTemplate   @relation(fields: [templateId], references: [id], onDelete: Cascade)
  version         Int
  
  // Snapshot of all template fields at this version
  snapshot        Json                 // Full template field snapshot
  
  // Change tracking
  changedById     String
  changedBy       User                 @relation("TemplateVersionChangedBy", fields: [changedById], references: [id])
  changedAt       DateTime             @default(now())
  changeReason    String?              // Optional reason for version change
  fieldDiffs      Json?                // Detailed field-level diffs
  
  @@unique([templateId, version])
  @@map("compliance_template_versions")
}

// Extend ComplianceSchedule to link back to template
model ComplianceSchedule {
  // ... existing fields ...
  templateId          String?
  template            ComplianceTemplate?   @relation("GeneratedCompliances", fields: [templateId], references: [id])
  templateVersion     Int?
  // ... rest of model ...
}
```

### 1.2 Template Number Format

`TPL-{TAXTYPE}-{COUNTRY_CODE}-###`

Examples:
- `TPL-GST-IN-001` (GST, India)
- `TPL-VAT-AE-002` (VAT, UAE)
- `TPL-WHT-US-001` (WHT, USA)

Sequence resets per tax-type + country combination.

---

## 2. Template Creation Flow

### 2.1 From Compliance Tracker (Preparer)

1. Preparer clicks **"Create Template"** button on Compliance Tracker page
2. Opens template creation form (mirrors "New Compliance" form)
3. Preparer fills: entities, tax type, form, period, frequency, due date, priority, preparer, approver, recurring settings
4. On submit: Creates `ComplianceTemplate` with `status = DRAFT`
5. Preparer can then **"Submit for Approval"** → status becomes `PENDING_ADMIN_APPROVAL`

### 2.2 From Master Data (Admin)

1. Admin navigates to **Master Data → Compliance Templates**
2. Clicks **"Create Template"** → same form
3. Admin can:
   - Save as DRAFT
   - **Approve directly** → status = `APPROVED`, version = 1, template number assigned
   - **Send to Reviewer** → status = `PENDING_REVIEW`

---

## 3. Approval Flow

```
DRAFT
  │
  ├─(Preparer submits)──→ PENDING_ADMIN_APPROVAL
  │                          │
  │                          ├─(Admin approves)──→ APPROVED (version 1) ──→ Generate first compliance
  │                          │
  │                          └─(Admin sends to reviewer)──→ PENDING_REVIEW
  │                                                            │
  │                                                            ├─(Reviewer approves)──→ APPROVED (version 1) ──→ Generate first compliance
  │                                                            │
  │                                                            └─(Reviewer rejects)──→ REJECTED
  │
  └─(Admin creates directly)──→ APPROVED (version 1) ──→ Generate first compliance
```

**On Approval (version 1):**
- Generate context-aware template number
- Set `version = 1`
- Create `ComplianceTemplateVersion` v1 snapshot
- **Immediately create first ComplianceSchedule** using template data
- Set compliance's `templateId` and `templateVersion = 1`

---

## 4. Versioning & Audit Trail

### 4.1 Version Creation Rules

A new version is created when:
- Any field on an **APPROVED** template is modified and saved
- Template is re-approved after rejection (version increments)

### 4.2 Version Snapshot

`ComplianceTemplateVersion` stores:
- Full field snapshot (JSON)
- `fieldDiffs`: `{ fieldName: { old: ..., new: ... } }`
- `changedBy`, `changedAt`, `changeReason`

### 4.3 Generation Uses Latest Version

When generating compliances for a filing month, the system **always uses the latest approved version** of the template.

---

## 5. Generation Engine

### 5.1 Generation Options (Master Data → Compliance Templates)

| Option | Description |
|--------|-------------|
| **Bulk Generate All** | Admin clicks "Generate for Month" → picks filing month → generates for ALL active approved templates |
| **Filtered Generate** | Admin picks filing month + filters (country, entity, form, tax type, status) → generates matching templates |
| **Per-Template Generate** | Each template row has "Generate for Month" button → picks filing month → generates for that template only |

### 5.2 Generation Logic

For each selected template:
1. Verify template is `APPROVED` and `isActive = true`
2. Verify filing month ≤ `recurringEndDate` (if set)
3. For each entity in `ComplianceTemplateEntity`:
   - Check if `ComplianceSchedule` already exists for this `entityId` + `filingMonth`
   - **If exists: HARD BLOCK** - log error, skip this entity, continue with others
   - **If not exists:** Create `ComplianceSchedule` using latest template version data:
     - Copy all config fields from template
     - Set `entityId` = template entity
     - Set `templateId` = template.id
     - Set `templateVersion` = template.version
     - Set `taxPeriod`, `taxPeriodStart`, `taxPeriodEnd` based on filing month + frequency
     - Set `dueDate` based on template's `dueDateRule`
     - Set `filingMonth` = selected filing month
     - Set `status = DRAFT`
     - Create `ComplianceEntity` links
     - Create `ComplianceAssignment` for template's default preparer
     - Create `ComplianceApproval` for template's default approvers
     - Create audit trail entry

### 5.3 Duplicate Handling

**HARD BLOCK**: If compliance for same `entityId` + `filingMonth` already exists, generation fails for that entity with clear error message. Admin must resolve manually (delete existing or skip).

---

## 6. Permissions

| Role | Master Data: Templates | Compliance Tracker: Create Template | Approve Template | Generate Compliances |
|------|------------------------|-------------------------------------|------------------|---------------------|
| Admin | Full CRUD | ✅ | ✅ (direct or via reviewer) | ✅ |
| Preparer | ❌ | ✅ (creates DRAFT) | ❌ | ❌ |
| Reviewer | View assigned | ❌ | ✅ (approve/reject) | ❌ |
| Approver | ❌ | ❌ | ❌ | ❌ |
| Manager | View only | ❌ | ❌ | ❌ |

---

## 7. UI Specification

### 7.1 Master Data Overview Page
Add card: **"Compliance Templates"** with icon `FileText`, color `bg-indigo-500`, link to `/master/compliance-templates`

### 7.2 Compliance Templates List Page (`/master/compliance-templates`)

**Filters (collapsible sidebar):**
- Status: All / Draft / Pending Admin / Pending Review / Approved / Rejected
- Country: Multi-select
- Entity: Multi-select (filtered by selected countries)
- Form: Multi-select
- Tax Type: Multi-select
- Frequency: Multi-select
- Template Number: Text search
- Version: Number input (filter by version)

**Table Columns:**
| Column | Description |
|--------|-------------|
| Template Number | TPL-GST-IN-001 (link to detail) |
| Version | Current version badge |
| Status | Colored badge |
| Tax Type | GST, VAT, etc. |
| Country | India, UAE, etc. |
| Form | Form number + name |
| Frequency | Monthly, Quarterly, etc. |
| Entities | Count + tooltip with names |
| Recurring | Yes/No + end date |
| Created By | User name |
| Approved At | Date |
| Actions | View, Edit (if draft), Generate, Version History |

**Bulk Actions:**
- "Generate for Month" button (top-right) → opens modal with filing month picker + filter options

### 7.3 Template Detail Page (`/master/compliance-templates/[id]`)

**Tabs:**
1. **Overview** - All template fields, entities list, approval history
2. **Versions** - Version table with: Version, Changed By, Changed At, Change Reason, "View Diff" action
3. **Audit Trail** - Detailed field-level changes per version
4. **Generated Compliances** - List of compliances created from this template

**Actions:**
- Edit (only if DRAFT or ADMIN)
- Submit for Approval (if DRAFT)
- Approve / Send to Reviewer / Reject (if PENDING_ADMIN_APPROVAL, admin only)
- Approve / Reject (if PENDING_REVIEW, reviewer only)
- Generate for Month
- Deactivate/Activate (admin only)

### 7.4 Template Create/Edit Form

Mirrors "New Compliance" form with additions:
- Template-specific fields: Recurring End Date, Due Date Rule
- No filing entity selection (template is per-country)
- Entities: Multi-select with country filter
- Save as Draft / Submit for Approval / Approve (admin only)

### 7.5 Compliance Tracker Page - Add "Create Template" Button

- Visible to: Preparer, Admin
- Opens same template creation form
- On submit: Creates DRAFT template, redirects to template detail or list

---

## 8. API Endpoints

### 8.1 Template CRUD
```
GET    /api/templates                    # List with filters, pagination
POST   /api/templates                    # Create template (DRAFT)
GET    /api/templates/[id]               # Get template detail
PATCH  /api/templates/[id]               # Update template (creates new version if approved)
DELETE /api/templates/[id]               # Delete (admin only, only if no generated compliances)
```

### 8.2 Template Actions
```
POST   /api/templates/[id]/submit        # Submit for approval
POST   /api/templates/[id]/approve       # Admin approve
POST   /api/templates/[id]/send-to-reviewer  # Admin send to reviewer
POST   /api/templates/[id]/reviewer-approve  # Reviewer approve
POST   /api/templates/[id]/reject        # Reject (admin or reviewer)
POST   /api/templates/[id]/activate      # Activate template
POST   /api/templates/[id]/deactivate    # Deactivate template
```

### 8.3 Version History
```
GET    /api/templates/[id]/versions      # List versions
GET    /api/templates/[id]/versions/[version]  # Get version snapshot
GET    /api/templates/[id]/versions/[version]/diff  # Get field diffs
```

### 8.4 Generation
```
POST   /api/templates/generate           # Bulk generate for filing month
POST   /api/templates/[id]/generate      # Generate for single template
```

**Generate Request Body:**
```json
{
  "filingMonth": "2026-08",
  "filters": {
    "countryIds": ["..."],
    "entityIds": ["..."],
    "formIds": ["..."],
    "taxTypes": ["GST", "VAT"]
  }
}
```

**Generate Response:**
```json
{
  "success": true,
  "generated": [
    { "templateId": "...", "entityId": "...", "complianceId": "TAX-12345", "status": "created" }
  ],
  "skipped": [
    { "templateId": "...", "entityId": "...", "reason": "Compliance already exists for 2026-08" }
  ],
  "errors": []
}
```

---

## 9. Migration Notes

- **No migration** of existing compliance schedules to templates
- Existing compliances remain as-is with `templateId = null`
- New templates created going forward will have `templateId` set on generated compliances

---

## 10. Acceptance Criteria

1. ✅ Preparer can create template from Compliance Tracker page
2. ✅ Admin can create/manage templates from Master Data
3. ✅ Template approval flow: Draft → Admin Approve/Reviewer → Approved (v1)
4. ✅ Template number format: `TPL-{TAXTYPE}-{COUNTRY}-###`
5. ✅ Version created on any edit to approved template
6. ✅ Audit log shows field-level diffs between versions
7. ✅ Generation uses latest template version
8. ✅ Three generation options work (bulk, filtered, per-template)
9. ✅ Hard block on duplicate entity+filing month
10. ✅ Generated compliance linked to template + version
11. ✅ Only admin can edit approved templates
12. ✅ Recurring end date respected during generation
13. ✅ Filters work in Master Data template list