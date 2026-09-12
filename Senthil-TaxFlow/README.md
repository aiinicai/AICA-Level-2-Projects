# TaxFlow — Indirect Tax Compliance Management Platform

**AICA Level 2 Capstone Project**  
**Author**: Senthil (`senrocks`)  
**Project Folder**: `Senthil-TaxFlow`

---

## 1. Project Overview

**TaxFlow** is an enterprise-grade indirect-tax compliance management platform designed to help organizations plan, assign, prepare, review, approve, file, and track payments for recurring and ad-hoc tax obligations across multiple legal entities and jurisdictions (e.g., VAT/GST, sales tax, withholding tax, corporate/income tax, statutory returns).

### The Problem
Tax teams across multi-entity organizations routinely struggle with:
- Tracking high volumes of recurring filings (monthly/quarterly/annual) across jurisdictions.
- Fragmented ownership, spreadsheets, and lost evidence in email chains.
- Lack of clear maker-checker controls, review gates, and audit trails.
- Risk of statutory penalties from missed filing or payment deadlines.

### The Solution
TaxFlow centralizes and automates the entire indirect tax compliance lifecycle:
- **Codified Workflows**: Who prepares, reviews, approves, and files.
- **Dual Due Date Management**: Independent tracking for statutory filing deadlines vs. tax payment deadlines.
- **Audit-Ready Repository**: Centralized storage of return calculations, attachments, filing acknowledgments, and payment proofs.
- **Real-Time Visibility**: Visual compliance calendar, KPI dashboards, overdue tracking, and automated status alerts.

---

## 2. Core Features & Capabilities

- **Multi-Tenant & Multi-Entity Master Data**:
  - Manage multiple legal entities, operating countries, currencies, and exchange rates.
  - Form registry mapping statutory forms, jurisdictions, frequencies, and baseline approval requirements.
- **Recurring Compliance Templates**:
  - Configurable standing templates with period anchoring rules (e.g., calendar month, quarter, fiscal year).
  - Configurable filing and payment due dates relative to period end.
  - Automated generation of monthly/quarterly compliance schedules.
- **Ad-Hoc Filings & CSV Import**:
  - Ability to create one-off or ad-hoc compliance requirements on demand.
  - Bulk import capabilities for legacy or external schedules via CSV.
- **Multi-Stage Approval Lifecycle (Maker-Checker)**:
  - Supports configurable approval flows: None, 1-Level (Reviewer), or 2-Level (Reviewer + Approver).
  - Status progression: `Draft` &rarr; `In Preparation` &rarr; `Submitted for Review` &rarr; `Reviewed` &rarr; `Approved` &rarr; `Filed` &rarr; `Paid` &rarr; `Closed`.
  - Rejection and resubmission flows with mandatory change notes.
- **Filing & Payment Confirmation**:
  - Upload of statutory filing acknowledgements and challans.
  - Strict verification of payment amounts and payment confirmation attachments.
- **Dashboards, Calendar & Reporting**:
  - Interactive compliance calendar displaying upcoming, overdue, and completed filings.
  - Executive KPI cards: Total Filings, Pending Approvals, Overdue Items, Payment Totals.
  - Exportable reports catalog for compliance audits.
- **Activity & Audit Trail**:
  - Granular audit logging on every compliance schedule modification and transition.

---

## 3. Technology Stack

- **Framework**: [Next.js](https://nextjs.org/) (App Router, React 19)
- **Language**: TypeScript
- **Styling & UI**: Tailwind CSS, CSS Variables, [Radix UI](https://www.radix-ui.com/) / [shadcn/ui](https://ui.shadcn.com/) primitives, Lucide Icons
- **Database & ORM**: PostgreSQL via [Supabase](https://supabase.com/), [Prisma ORM](https://www.prisma.io/)
- **Testing**: Vitest (`npm test`)
- **Deployment Compatibility**: Cloudflare Workers / OpenNext / Vercel

---

## 4. Project Structure

```text
Senthil-TaxFlow/
├── docs/                   # Functional specs, architecture notes & design blueprints
├── prisma/
│   └── schema.prisma       # Database schema definition
├── public/                 # Static assets & icons
├── src/
│   ├── app/                # Next.js App Router (pages, layouts, route handlers)
│   │   ├── (auth)/         # Authentication routes (login, session handling)
│   │   ├── api/            # REST API endpoints (compliance, templates, master data)
│   │   ├── calendar/       # Interactive compliance calendar
│   │   ├── compliance/     # Compliance tracker, detail view, ad-hoc creator
│   │   ├── dashboard/      # Executive KPI dashboard
│   │   ├── master/         # Master data management (entities, countries, forms, templates)
│   │   ├── notifications/  # Notification center
│   │   ├── reports/        # Reports catalog
│   │   └── settings/       # Organization and user settings
│   ├── components/         # Reusable UI components & layouts
│   ├── lib/                # Core business logic (approval flow, date calculation, db client)
│   └── types/              # TypeScript domain types & interfaces
├── supabase/               # SQL migrations and schema definitions
├── package.json            # Project dependencies and npm scripts
├── tsconfig.json           # TypeScript configuration
└── vitest.config.ts        # Unit test configuration
```

---

## 5. Getting Started

### Prerequisites
- Node.js 20+ (LTS recommended)
- PostgreSQL database (or a Supabase project instance)

### Installation
```bash
# Clone the repository
git clone https://github.com/aiinicai/AICA-Level-2-Projects.git
cd AICA-Level-2-Projects/Senthil-TaxFlow

# Install dependencies
npm install
```

### Environment Configuration
Create a `.env` file in the `Senthil-TaxFlow` root directory:
```env
DATABASE_URL="postgresql://postgres:password@localhost:5432/taxflow"
NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

### Database Migration
```bash
# Apply Prisma migrations / schema push
npx prisma db push

# (Optional) Seed demo master data
node src/scripts/seed-scenarios.mjs
```

### Running the Application
```bash
# Start the Next.js development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### Running Tests
```bash
npm run test
```

---

## 6. Author
- **Author**: Senthil
- **GitHub**: [@senrocks](https://github.com/senrocks)
- **Capstone Track**: AICA Level 2
