# CONTINUATION_GUIDE.md
## Hospital CFO Copilot — Developer Handover & Continuation Guide

**Version:** V1 · **Date:** 2026-09-26  
**Firebase Project:** `central-sanctuary-32ts5`  
**Dev Server:** `http://localhost:3000`

---

## A. Project Overview

The Hospital CFO Copilot is a production-grade, real-time financial control and review platform for hospital CFOs. It ingests heterogeneous hospital financial data (CSV/Excel/JSON), runs deterministic financial controls (C01–C08), surfaces exceptions, and orchestrates a 10-stage multi-agent AI review pipeline.

**Key principle:** AI never calculates financial values. All numbers come from deterministic TypeScript engines. AI provides observations and recommendations only.

---

## B. Quick Start

```bash
# Prerequisites: Node.js 18+, npm

# 1. Install dependencies
npm install

# 2. Configure Firebase
# Create firebase-applet-config.json with your project values:
{
  "apiKey": "YOUR_API_KEY",
  "authDomain": "YOUR_PROJECT.firebaseapp.com",
  "projectId": "YOUR_PROJECT_ID",
  "storageBucket": "YOUR_PROJECT.appspot.com",
  "messagingSenderId": "YOUR_SENDER_ID",
  "appId": "YOUR_APP_ID",
  "databaseId": "YOUR_NAMED_DATABASE_ID"
}

# 3. (Optional) Add Gemini API key for AI features
echo "GEMINI_API_KEY=your_key_here" > .env
# Without it, the app uses deterministic fallback responses — fully functional.

# 4. Start dev server
npm run dev   # → http://localhost:3000

# 5. Build for production
npm run build

# 6. TypeScript check
npm run lint   # = tsc --noEmit
```

---

## C. Firebase Configuration

### Named Database (Critical)
This project uses a **named Firestore database**, not `(default)`:
```
ai-studio-hospitalcfocopil-6dd77927-91d6-46ff-b9ac-6c17a8b23fc4
```
Configured in `src/firebase.ts`. Changing to `(default)` will break all Firestore reads/writes.

### Firebase Auth
- Primary auth: Google Sign-in
- Fallback: Institutional session via `signInAsAuthorizedUser()` for `rukminigopakumar@gmail.com`
- Auth domain whitelist: Configure in Firebase Console → Authentication → Settings → Authorized Domains

### Firestore Security Rules
Deploy `firestore.rules` to your Firebase project:
```bash
firebase deploy --only firestore:rules
```

---

## D. Authentication Architecture

### Authentication Model
**Google Sign-In exclusively** via Firebase Authentication popup.
Unknown-User RBAC rule:
`Authenticated Google users without an authorised Firestore user profile are denied access.`

```
Google Authentication (Firebase Auth)
        ↓
Firestore user profile lookup (/users/{uid} or /users/{email})
        ↓
Profile exists and authorized?
   YES → Load assigned role + department from Firestore profile
   NO  → ACCESS DENIED (Immediate signout + error message)
```

### Bootstrap Allowlist (rukminigopakumar@gmail.com)
- **Email:** `rukminigopakumar@gmail.com`
- **Purpose:** Allows the designated CFO bootstrap account to authenticate when the application is deployed on a domain not yet added to Firebase Authorized Domains (e.g. preview environments).
- **Rule:** The allowlist cannot grant CFO privileges by itself. Roles and permissions are strictly governed by the Firestore user profile.
- **Implementation:** Defined in `authService.ts` as `PERMANENT_AUTHORIZED_USERS` and in `firestore.rules` via `isBootstrappedAdmin()`.

### Session Guard Pattern
```typescript
// ALWAYS use hasActiveSession() — not auth.currentUser directly
import { hasActiveSession } from './services/firestoreDataService';
if (!hasActiveSession()) return; // validates active session before Firestore calls
```

---

## E. RBAC System

| Role | Permissions |
|------|-------------|
| CFO | Full access — all views, approve reviews, manage all data |
| Finance/Billing Manager | Run controls, generate reviews, upload data, manage billing/exceptions |
| Department Manager | Read-only — can update clearance for their department only |
| Auditor | Read-only — audit logs and reports only |

Role is stored in Firestore `users/{uid}.role`. Checked in `authService.ts` and enforced in `firestore.rules`.

---

## F. Data Ingestion

### Supported Formats
- CSV, Excel (.xlsx/.xls), JSON
- Heterogeneous column names (AI maps to canonical schema)

### Dataset Types
| Type | Firestore Collection | Key Fields |
|------|---------------------|------------|
| Encounters | `encounters` | Encounter_ID, Admission_Date, Discharge_Date, Department, Payer_Type |
| Services | `services` | Service_ID, Encounter_ID, Revenue_Centre, Expected_Amount |
| Billing | `billing` | Bill_ID, Encounter_ID, Billed_Amount, Discount |
| Claims | `claims` | Claim_ID, Encounter_ID, Claim_Amount, Claim_Status, TPA_Name |
| Collections | `collections` | Receipt_ID, Encounter_ID, Amount, Payment_Mode |
| Tariff Master | `tariff_master` | Service_Code, Payer, Payer_Tariff, Standard_Tariff |
| Budgets | `budgets` | Month, Department, Revenue_Budget, Expense_Budget |

### Data Import Flow
```
DataIntelligenceView.tsx
  → DynamicIngestionWizard.tsx
  → fileImport.ts (parse)
  → geminiMappingService.ts (AI column mapping via /api/ingestion/map-columns)
  → dynamicDataEngine.ts (normalize to canonical schema)
  → importHospitalDataBatch() in firestoreDataService.ts
  → Firestore (batch write)
  → Real-time subscriptions update App.tsx state
```

### Clearing Data
- `clearAllFinancialDataInFirestore()` / `resetDatabaseToBaselineInFirestore` (alias) in `firestoreDataService.ts`
- Clears all financial collections except `users`, `departments`
- Available in `DataControlsView.tsx` (CFO/Finance Manager only)

---

## G. Financial Control Engine (C01–C08)

**File:** `src/engine/controlEngine.ts`

The engine runs deterministically against all Firestore data. No AI involvement.

| Control | ID | Description |
|---------|-----|-------------|
| Unbilled Service | C01 | Clinical service orders delivered without corresponding billing line |
| Qty Mismatch | C02 | Quantity mismatch or duplicate order entries between services and billing |
| Amount Mismatch | C03 | Billed amount deviates from contracted tariff schedule |
| Post-Billing Svc | C04 | Service entered or rendered after initial bill generation |
| Missing Final Bill | C05 | Discharged inpatient encounters with unfinalized or provisional bills |
| TPA Shortfall | C06 | Insurance claim adjudication shortfall and disallowance (>5% tolerance) |
| Overdue Receivables | C07 | Outstanding patient or corporate collections exceeding settlement terms |
| Unusual Discount | C08 | Discount or concession exceeding authorised institutional limits |

### Return Type
```typescript
interface ControlEngineResult {
  runId: string;
  timestamp: string;
  metrics: DashboardMetrics;      // All KPIs
  exceptions: FinancialException[];
  clearanceStatus: DepartmentClearanceSummary;
  auditTrail: AuditTrailRun;
  dischargeMonitor: DischargeMonitorRow[];
}
```

### AS-OF Date
The `now` reference date is dynamically derived from the latest transaction date in the uploaded dataset using `getLatestTransactionDate()` from `src/utils/arCalculations.ts`. Falls back to real wall-clock time.

---

## H. Multi-Agent CFO Review Orchestrator

**File:** `src/services/cfoFinancialReviewAgent.ts`  
**UI:** `src/components/CfoFinancialReviewModal.tsx`  
**Tools:** `src/tools/cfoFinancialTools.ts`

### Stages
1. **CONTROL_POSITION** — Financial position from control engine
2. **REVENUE_REVIEW** — Revenue centre analysis
3. **EXCEPTION_REVIEW** — Exception prioritization
4. **RECEIVABLES** — AR ageing buckets
5. **TPA** — TPA claim status
6. **DEPARTMENT** — Departmental exposure
7. **TARIFF** — Tariff compliance
8. **BUDGET** — Budget vs actual (skipped if no budget data → NO_DATA state)
9. **FINANCIAL_SYNTHESIS** — Cross-stage synthesis
10. **CFO_BRIEFING** — AI generates markdown brief from all evidence

### Stage Status Lifecycle
```
PENDING → RUNNING → COMPLETED
                 → SKIPPED   (conditional: not applicable)
                 → NO_DATA   (conditional: no data for this stage)
                 → ERROR     (unexpected failure)
```

### Output Taxonomy
Every finding must be tagged:
- `[FACT]` — Raw deterministic value
- `[CALCULATED METRIC]` — Derived calculation
- `[AI OBSERVATION]` — Analytical interpretation
- `[SUGGESTED ACTION]` — Management recommendation

### Human Review & Approval
After AI synthesis, CFO must review and approve/reject via `CfoFinancialReviewModal.tsx`. Approval is RBAC-gated (CFO role only). Saved to `cfo_reports` Firestore collection.

---

## I. Firestore Collections Schema

### `encounters`
```
Encounter_ID: string (primary key)
Admission_Date: string (YYYY-MM-DD)
Discharge_Date: string (YYYY-MM-DD) | null
Department: string
Ward: string
Bed_Type: string
Payer_Type: string (Self Pay / Mediclaim / TPA / Corporate / Government)
Discharge_Status: string (Discharged / Admitted / Absconded / LAMA / Deceased)
```

### `services`
```
Service_ID: string
Encounter_ID: string (FK → encounters)
Service_DateTime: string
Revenue_Centre: string
Service_Code: string
Description: string
Quantity: number
Expected_Amount: number
```

### `billing`
```
Bill_ID: string
Encounter_ID: string (FK → encounters)
Service_ID: string (FK → services)
Bill_DateTime: string
Bill_Date: string
Billed_Quantity: number
Billed_Amount: number
Discount: number
Bill_Status: string
```

### `claims`
```
Claim_ID: string
Encounter_ID: string (FK → encounters)
Claim_Amount: number
Approved_Amount: number | null
Rejected_Amount: number | null
Claim_Status: string (Submitted / Approved / Rejected / Pending Info / Under Query / In Adjudication)
Submission_Date: string
Approval_Date: string | null
TPA_Name: string
```

### `collections`
```
Receipt_ID: string
Encounter_ID: string (FK → encounters)
Receipt_Date: string
Amount: number
Payment_Mode: string (Cash / Card / UPI / NEFT / Cheque / Insurance)
```

### `tariff_master`
```
Service_Code: string
Service_Description: string
Revenue_Centre: string
Standard_Tariff: number
Effective_From: string
Effective_To: string
Payer: string (Standard / TPA name)
Payer_Tariff: number
```

### `budgets`
```
Month: string (YYYY-MM)
Department: string
Revenue_Budget: number
Expense_Budget: number
```

### `exceptions`
```
Exception_ID: string
Encounter_ID: string
Control_ID: ControlId (C01-C08)
Revenue_Centre: string
Department: string
Description: string
Exposure_Amount: number
Severity: Severity (CRITICAL / HIGH / MEDIUM / LOW)
Status: string (Open / Accepted / Disputed / Waived / Resolved)
Created_At: string
```

### `users`
```
uid: string (Firebase Auth UID)
email: string
displayName: string
role: string (CFO / Finance/Billing Manager / Department Manager / Auditor)
department: string (for Department Manager role)
photoURL: string
createdAt: Timestamp
lastLoginAt: Timestamp
```

---

## J. AR Ageing

**File:** `src/utils/arCalculations.ts`

Canonical AR ageing uses 4 buckets: `0-30`, `31-60`, `61-90`, `90+`

```typescript
// Use canonical function everywhere — TpaCollectionsView, CfoManagementPackModal, ArWorkingCapitalView
import { calculateArAgeing, getClaimsPendingAdjudication } from './utils/arCalculations';
const arSummary = calculateArAgeing(encounters, billings, collections, claims, asOfDateStr);
```

**TPA Pending:** Use `getClaimsPendingAdjudication(claims)` — includes Submitted, Pending Info, Under Query, In Adjudication states.

---

## K. Export Features

**File:** `src/utils/reportExportUtils.ts`

- **PDF Export:** Uses `jsPDF` — generates multi-page CFO management pack
- **Excel Export:** Uses `xlsx` — generates multi-sheet workbooks
- Available from CFO Financial Review modal and CFO Management Pack modal

---

## L. PWA

- **Plugin:** `vite-plugin-pwa`
- **Config:** `vite.config.ts` — VitePWA configuration with icons, workbox settings
- **Install button:** `src/components/PWAInstallButton.tsx` + `src/hooks/usePWAInstall.ts`
- **Offline support:** Service worker caches JS, CSS, HTML, images (max 5MB per file)
- **Dev mode:** PWA is disabled in dev (`devOptions.enabled: false`)

---

## M. Gemini AI Integration

### Endpoints (in `vite.config.ts`)
| Endpoint | Purpose |
|----------|---------|
| `POST /api/copilot/query` | CFO Q&A (Copilot chat) |
| `POST /api/ingestion/map-columns` | AI column mapping for data import |
| `POST /api/cfo-review/generate` | CFO Financial Review AI synthesis |

### Model Cascade
```
gemini-3.8-flash → gemini-flash-latest → gemini-3.1-flash-lite
```
Each model is tried twice. Falls back to deterministic response if all fail.

### Without API Key
The app is **fully functional without a Gemini API key**:
- CFO Copilot: returns deterministic rule-based analysis from `copilotService.ts`
- Column Mapping: uses heuristic mapping from `geminiMappingService.ts`
- CFO Review: uses multi-agent orchestrator output as-is without AI synthesis

---

## N. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | No | Gemini AI API key. App works without it via deterministic fallback. |
| `VITE_SEED_DEMO_DATA` | No | Set `true` to seed synthetic demo data. MUST be absent/`false` in production. |
| `VITE_CONFIG_NATIVE_IGNORE_WARNING` | No | Suppresses Vite `__dirname` warning. |

Firebase config is in `firebase-applet-config.json` (JSON file, not env vars).

---

## O. Synthetic Data Isolation

`syntheticDataset.ts is a development/UAT fixture only and is not automatically loaded into production.`

- **File:** `src/data/syntheticDataset.ts`
- **Purpose:** Unit testing, control algorithm validation, and developer benchmarking only.
- **Production State:** Fresh production workspaces begin completely empty. Zero production execution path exists to load this fixture.
- **Guard in `firestoreDataService.ts`:**
```typescript
export async function initializeAndSeedFirestoreIfNeeded() {
  // Production requirement: Never seed synthetic or demo records into Firestore.
  return { seeded: false, message: 'Clean workspace awaiting user import.' };
}
```

---

## O.1 Scope & Terminology Standards

The application is a financial-control and revenue intelligence layer only. It never exercises clinical authority or patient release control.

- **Prohibited Terminology:** Do NOT use Gate Pass, Financial Discharge Gate, Patient Release Control, or Discharge Without Clearance.
- **Approved Terminology:**
  - `Discharge Financial Monitor`
  - `Departmental Billing Review` (describe departmental review as financial review and billing completeness associated with discharged encounters, not patient-release control)
  - `Financial Completeness Review`
  - `Financial Exception Review`
  - `Financial Review associated with discharged encounters`

---

## P. Data Not Reflecting After Upload — Troubleshooting

1. Check that `hasHospitalData` in `App.tsx` includes your dataset type
2. Check that `effectiveEncounters` useMemo in `App.tsx` is deriving encounter shells from your uploaded data
3. Check that Firestore subscriptions are active (check browser Network tab for Firestore WebSocket)
4. Check that `hasActiveSession()` returns true (check localStorage for `cfo_copilot_session_v2`)
5. The dashboard empty state only blocks on `!hasData` — not on `totalExpectedAmount === 0`

---

## Q. Adding a New Dataset Type

1. Add type to `src/types/ingestion.ts` (DatasetType enum)
2. Add schema definition to `geminiMappingService.ts` (schema context)
3. Add normalization logic to `dynamicDataEngine.ts`
4. Add Firestore CRUD in `firestoreDataService.ts` (subscription + batch import)
5. Add collection to `COLLECTIONS` constant in `firestoreDataService.ts`
6. Add Firestore rules in `firestore.rules`
7. Add real-time subscription in `App.tsx`
8. Add to `hasHospitalData` in `App.tsx`

---

## R. Adding a New Financial Control

1. Add `ControlId` to `src/types/index.ts`
2. Add control logic in `src/engine/controlEngine.ts` — follow the pattern of existing C01–C08
3. Add to `CONTROL_RULE_CONFIGS` in `controlEngine.ts` for UI display
4. Add tool in `src/tools/cfoFinancialTools.ts` if needed for multi-agent access
5. Add to relevant agent stage in `cfoFinancialReviewAgent.ts`
6. Update `RevenueControlsView.tsx` for display

---

## S. Adding a New RBAC Role

1. Add to `UserRole` type in `src/types/index.ts`
2. Add helper function in `firestore.rules` (e.g., `isNewRole()`)
3. Add permissions to relevant collections in `firestore.rules`
4. Add to role display map in `Sidebar.tsx` and `TopBar.tsx`
5. Handle in `authService.ts` role assignment

---

## T. Known Caveats & Notes

1. **`package.json` name is `react-example`** — This is the Antigravity scaffolding name. Rename to `hospital-cfo-copilot` if publishing.
2. **`bun.lock` present** — The project was last used with Bun package manager. Use `npm install` for standard Node.js environments.
3. **`vite.config.ts` uses `__dirname`** — This requires `@types/node`. Already included in devDependencies.
4. **`syntheticDataset.ts` service codes** — Aligned to match `INITIAL_SERVICES` Revenue_Centre values (OT / Surgery, ICU / Critical Care, Room Rent / Nursing, etc.)
5. **`resetDatabaseToBaseline`** — This is an alias for `clearAllFinancialDataInFirestore`. It does NOT seed demo data unless `VITE_SEED_DEMO_DATA=true`.
6. **No `firestore.indexes.json`** — Not present in the project. If you add complex queries (multi-field orderBy), create and deploy this file.

---

## U. Performance Notes

- Firestore subscriptions use real-time listeners (not polling)
- `useMemo` in `App.tsx` gates expensive control engine runs on data changes
- AR calculations are memoized per view
- Exception list is filtered client-side (no server-side query for exceptions)
- For hospitals with >10,000 records, consider adding Firestore pagination

---

## V. Security Notes

1. **Firebase API key in `firebase-applet-config.json`** — This is a client-side key (safe to expose in browser, protected by Firestore rules). Still excluded from ZIP to follow best practices.
2. **Gemini API key in `.env`** — Server-side only (accessed in `vite.config.ts` middleware, never sent to browser). Never expose in frontend code.
3. **Firestore rules enforce RBAC** — Even if frontend code is bypassed, Firestore rules block unauthorized writes.
4. **Audit logs are immutable** — `update, delete: if false` in `firestore.rules` for `audit_logs` collection.

---

## W. Deployment

### Firebase Hosting (Recommended)
```bash
npm run build
firebase deploy --only hosting
```

### Static Hosting (Vercel / Netlify)
```bash
npm run build
# Deploy `dist/` folder
# Set GEMINI_API_KEY as server-side environment variable
```

### Important: Vite Dev Server Middleware
The Gemini AI endpoints (`/api/copilot/query`, `/api/ingestion/map-columns`, `/api/cfo-review/generate`) are implemented as **Vite dev server middleware** in `vite.config.ts`. For production deployment, these must be deployed as serverless functions or Express API routes.

---

## X. Testing

No automated test suite exists. Manual testing workflow:
1. Upload sample data via Data Intelligence → Data Import
2. Navigate to Finance Control Tower → Run Financial Controls
3. Review Dashboard KPIs
4. Open Exceptions view → Accept/Dispute items
5. Run CFO Financial Review → review 10-stage output
6. Generate CFO Management Pack → download PDF/Excel

---

## Y. CFO Management Pack

**Component:** `src/components/CfoManagementPackModal.tsx`

Printable HTML-based management pack rendered in a modal:
- Section 1: Financial Position Summary
- Section 2: Exception Analysis  
- Section 3: Departmental Exposure
- Section 4: AR Ageing Schedule
- Section 5: Governance & Sign-off (uses authenticated user identity)

Export to PDF via `jsPDF` and Excel via `xlsx` through `reportExportUtils.ts`.

---

## Z. Tariff Intelligence

**View:** `src/components/TariffIntelligenceView.tsx`  
**Engine:** `src/engine/tariffEngine.ts`  
**Investigations:** `tariff_investigations` Firestore collection

Allows CFO to compare billed amounts against tariff master, flag discrepancies, and raise formal tariff investigations with status tracking.

---

## AA. Budget vs Actual

**View:** `src/components/BudgetVsActualView.tsx`  
**Engine:** `src/engine/budgetEngine.ts`  
**Collection:** `budgets`

- Requires upload of monthly budget records (Department, Month, Revenue_Budget, Expense_Budget)
- Management commentary persists to localStorage per reporting period
- Shows variance by department with variance % and RAG status

---

## AB. Audit Trail

**Service:** `src/services/auditService.ts`  
**View:** `src/components/AuditEvidenceView.tsx`  
**Firestore:** `audit_logs` (immutable — no delete/update allowed)

All significant actions are logged: data imports, control runs, exception resolutions, CFO review approvals, user sign-ins.

---

## AC. Support & Contact

- **Authorized CFO User:** Rukmini Gopakumar (`rukminigopakumar@gmail.com`)
- **Firebase Project:** `central-sanctuary-32ts5`
- **Firestore DB:** `ai-studio-hospitalcfocopil-6dd77927-91d6-46ff-b9ac-6c17a8b23fc4`
- **Dev Server:** `http://localhost:3000`
