# PROJECT_STRUCTURE.md
## Hospital CFO Copilot — Complete File Structure

**Total source files:** 51 · **Root config files:** 8 · **Generated:** 2026-09-26

---

## Root Directory

```
hospital-cfo-copilot (1)/
├── index.html                          # Vite HTML entry point
├── vite.config.ts                      # Vite + Tailwind + PWA + Gemini API middleware config
├── tsconfig.json                       # TypeScript configuration
├── package.json                        # Dependencies (React 19, Firebase 12, Recharts, jsPDF, xlsx)
├── package-lock.json                   # Exact dependency tree lock file
├── firestore.rules                     # Firestore RBAC security rules
├── firebase-blueprint.json             # Firebase project blueprint/metadata (safe to share)
├── metadata.json                       # Project metadata
├── .env.example                        # Environment variable template (no real values)
├── README.md                           # Project README
├── BACKUP_VALIDATION_REPORT.md         # Pre-export validation results [this backup]
├── PROJECT_MANIFEST.json               # Machine-readable project metadata [this backup]
├── PROJECT_STRUCTURE.md                # This file [this backup]
├── CONTINUATION_GUIDE.md               # Developer handover guide [this backup]
├── AI_CONTEXT.md                       # Context for next AI agent [this backup]
│
├── public/                             # Static assets (served as-is)
│   ├── apple-touch-icon.png            # iOS PWA icon
│   ├── icon.svg                        # SVG icon
│   ├── pwa-192x192.png                 # PWA icon 192px
│   ├── pwa-512x512.png                 # PWA icon 512px
│   └── pwa-maskable-512x512.png        # PWA maskable icon 512px
│
└── src/                                # All TypeScript/React source code
    ├── App.tsx                         # Root orchestrator component (1100+ lines)
    ├── firebase.ts                     # Firebase initialization (Auth + Firestore)
    ├── main.tsx                        # Vite app entry point
    ├── index.css                       # Global styles + Tailwind base
    │
    ├── types/
    │   ├── index.ts                    # All core TypeScript interfaces/types
    │   └── ingestion.ts                # Data ingestion pipeline types
    │
    ├── engine/                         # Deterministic financial calculation engines
    │   ├── controlEngine.ts            # C01–C08 financial controls (main engine)
    │   ├── clearanceEngine.ts          # Discharge financial clearance engine
    │   ├── tariffEngine.ts             # Tariff comparison and variance engine
    │   └── budgetEngine.ts             # Budget vs actual variance engine
    │
    ├── services/
    │   ├── authService.ts              # Firebase Auth + institutional session management
    │   ├── firestoreDataService.ts     # All Firestore CRUD + real-time subscriptions
    │   ├── cfoFinancialReviewAgent.ts  # 10-stage multi-agent CFO review orchestrator
    │   ├── copilotService.ts           # CFO Copilot AI Q&A service (deterministic fallback)
    │   ├── auditService.ts             # Audit log service (Firestore + localStorage cache)
    │   └── geminiMappingService.ts     # Gemini AI column mapping for data ingestion
    │
    ├── tools/
    │   └── cfoFinancialTools.ts        # Controlled read-only tools used by multi-agent
    │
    ├── components/                     # All React UI components
    │   ├── LoginView.tsx               # Login screen (Google Sign-In with Firestore RBAC authorization)
    │   ├── Sidebar.tsx                 # Navigation sidebar with RBAC-filtered tabs
    │   ├── TopBar.tsx                  # Top bar with user info and controls
    │   ├── DashboardView.tsx           # Main financial dashboard (KPIs, charts)
    │   ├── DataIntelligenceView.tsx    # Heterogeneous data import hub
    │   ├── DynamicIngestionWizard.tsx  # Step-by-step data upload wizard
    │   ├── DataControlsView.tsx        # Dataset management and clear controls
    │   ├── ExceptionsView.tsx          # Exception review with Accept/Dispute/Waive
    │   ├── RevenueControlsView.tsx     # Revenue controls summary view
    │   ├── ReceivablesCollectionsView.tsx  # Receivables and collections view
    │   ├── TpaCollectionsView.tsx      # TPA/insurance claim status view
    │   ├── ArWorkingCapitalView.tsx    # AR ageing and working capital analysis
    │   ├── DepartmentClearanceView.tsx # Departmental discharge clearance view
    │   ├── DischargeMonitorView.tsx    # Real-time discharge financial monitor
    │   ├── DischargeFinancialView.tsx  # Per-discharge financial detail view
    │   ├── FinancialPerformanceView.tsx  # Financial performance analytics
    │   ├── BudgetVsActualView.tsx      # Budget vs actual variance view
    │   ├── TariffIntelligenceView.tsx  # Tariff schedule management and analysis
    │   ├── CfoCopilotView.tsx          # AI CFO Q&A chat interface
    │   ├── CfoFinancialReviewModal.tsx # Multi-agent CFO Financial Review modal
    │   ├── CfoManagementPackModal.tsx  # CFO Management Pack (printable report)
    │   ├── AuditEvidenceView.tsx       # Audit trail and evidence viewer
    │   ├── ControlSettingsView.tsx     # Financial control rule configuration
    │   ├── EmptyWorkspaceState.tsx     # Empty state when no data uploaded
    │   ├── OfflineIndicator.tsx        # PWA offline status indicator
    │   └── PWAInstallButton.tsx        # PWA install prompt button
    │
    ├── data/
    │   └── syntheticDataset.ts         # Development/UAT benchmark fixture only (not loaded in production)
    │
    ├── hooks/
    │   └── usePWAInstall.ts            # Custom hook for PWA install prompt
    │
    └── utils/
        ├── arCalculations.ts           # AR ageing buckets + TPA pending filter (canonical)
        ├── departmentMapping.ts        # Revenue centre → department canonical mapping
        ├── dynamicDataEngine.ts        # Heterogeneous data parsing and normalization
        ├── fileImport.ts               # CSV/Excel/JSON file parsing utilities
        ├── formatters.ts               # INR formatting, date formatting helpers
        └── reportExportUtils.ts        # PDF (jsPDF) + Excel (xlsx) export utilities
```

---

## Key Architecture Relationships

```
App.tsx
  ├── firestoreDataService.ts  →  Firestore DB (real-time subscriptions)
  ├── authService.ts           →  Firebase Auth / institutional session
  ├── controlEngine.ts         →  C01–C08 calculations → DashboardMetrics
  ├── clearanceEngine.ts       →  Discharge clearance status
  ├── tariffEngine.ts          →  Tariff variance results
  ├── budgetEngine.ts          →  Budget vs actual results
  └── cfoFinancialReviewAgent.ts →  10-stage orchestrator
        └── cfoFinancialTools.ts → Controlled read-only data access
```

---

## File Size Reference (approximate)

| File | Size |
|------|------|
| `src/services/cfoFinancialReviewAgent.ts` | ~900 lines |
| `src/services/firestoreDataService.ts` | ~1,120 lines |
| `src/App.tsx` | ~1,110 lines |
| `src/engine/controlEngine.ts` | ~680 lines |
| `src/components/DashboardView.tsx` | ~760 lines |
| `vite.config.ts` | ~507 lines |
| `src/tools/cfoFinancialTools.ts` | ~600 lines |
| `src/data/syntheticDataset.ts` | ~950 lines |
