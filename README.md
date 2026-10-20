# Paras Accounting & Auditing Advisory
## Performance Appraisal & Human Capital Intelligence Hub
### AICA Level 2 Capstone Assessment Submission — Batch 120 (Abu Dhabi, UAE)

**Principal Architect:** CA Pankaj Rai Madhra  
**ICAI Membership No.:** 86829  
**Cohort:** AICA Level 2 — Batch 120 (Abu Dhabi, United Arab Emirates)  
**Jurisdiction:** Abu Dhabi Global Market (ADGM) & MOHRE UAE Registered Practice  
**Scope:** Small & Medium Enterprise (SME) Practice Baseline — 50 Personnel  

---

## 1. Executive Summary & Business Case

In knowledge-intensive professional practices—such as chartered accountancy, statutory auditing, and taxation advisory—conventional annual appraisal systems frequently fail due to three core weaknesses:
1. **Subjectivity & Evaluation Bias:** Performance evaluated on vague partner impressions rather than objective audit engagement workpapers, turnaround times, and statutory technical sign-offs.
2. **High Professional Attrition:** Competition for qualified chartered auditors (ACA, ACCA, CPA, CTA) creates turnover unless structured tenure loyalty multipliers and tangible certification incentives are institutionalized.
3. **Punitive Fear vs. Constructive Development:** Traditional review systems penalize skill deficiencies rather than prescribing sponsored retraining and progressive mentorship under UAE labor regulations.

### The Proposed Solution
**Paras Advisory Performance & Human Capital Intelligence Hub** introduces an enterprise-grade performance management and governance platform tailored for an SME practice of 50 staff members. It replaces arbitrary reviews with an **objective, multi-pillar mathematical matrix**, an institutionalized **Two-Tier 90-Day Improvement Framework**, a **Chartered Certification Incentive of AED 15,000**, and an **ISA 230-compliant cryptographic audit trail**.

---

## 2. Core Valuation Formula & Mathematical Logic

The platform calculates overall performance using an objective formula free from subjective bias:

$$\text{Final Weighted Score} = \text{Base Score} \times \text{Tenure Loyalty Multiplier}$$

Where:
$$\text{Base Score} = (S \times 0.50) + (T \times 0.25) + (A \times 0.15) + (G \times 0.10)$$

### Pillar Breakdown
1. **Service Delivery Deliverables Matrix ($S$ — 50% Weight):** Points earned based on standardized catalog tasks (e.g., IFRS Audit Sign-Offs, Corporate Tax Filings, QoE Due Diligence, Forensic Anti-Fraud Reports) adjusted by quality weightages ($1.0\times$ to $1.4\times$).
2. **Task Turnaround SLA Adherence ($T$ — 25% Weight):** Actual engagement turnaround hours logged against strict practice SLA benchmarks.
3. **HR Attendance & Biometric Punctuality ($A$ — 15% Weight):** Prefilled directly from firm attendance logs (08:30 AM arrival with a 15-minute grace window). Zero subjective partner override.
4. **Cycle Growth Delta ($G$ — 10% Weight):** Normalized cycle-over-cycle progression rewarding continuous upward trajectory.
5. **Tenure Loyalty & Retention Multipliers:**
   - **0 – 2 Years:** `1.00x` (Foundation Onboarding Tier)
   - **2 – 5 Years:** `1.05x` (+5% Growth Contributor Multiplier)
   - **5 – 8 Years:** `1.10x` (+10% Tenure Distinction Boost + Loyalty Bonus)
   - **8+ Years:** `1.15x` (+15% Senior Merit Circle)

---

## 3. Statutory Compliance with UAE Labor Law

The platform adheres to **UAE Federal Decree-Law No. 33 of 2021 on the Regulation of Labour Relations** and Cabinet Resolution No. 1 of 2022:

- **Article 27 (Continuous Professional Development):** Mandatory provision of firm-sponsored training through accredited institutions (ADGM Academy, ICAEW, ADSM).
- **Article 29 (Performance Standards & Remediation):** Transparent two-tier improvement protocol before any adverse employment decision:
  - **Tier 1 (90-Day Skill Upgrade Plan):** 100% firm-sponsored training, dedicated partner mentorship, and bi-weekly checkpoints with zero financial penalty.
  - **Tier 2 (Extended 90-Day PIP):** Secondary 90-day remediation track under senior partner oversight if Tier 1 targets remain partially unmet.
- **Article 43 & 44 (Statutory Notice & Hearings):** Generation of bilingual legal notices with full right to written employee statements and peer accompaniment.

---

## 4. Role of Gemini AI Models (`@google/genai`)

The application integrates Google's modern **`@google/genai` TypeScript SDK** using the **`gemini-2.5-flash`** model:

- **AI Executive Talent Synthesis:** Generates multi-pillar performance evaluations, synthesizing complex audit timesheets and SLA turnaround metrics into concise executive partner memorandums.
- **Remediation & Mentorship Pathfinding:** Formulates tailored learning interventions mapped directly to observed fieldwork deficiencies.
- **UAE Labor Law Regulatory Validation:** Automatically audits proposed performance interventions against Articles 27 and 29 of UAE Decree-Law 33/2021 to ensure due process.
- **Security & Privacy:** The integration uses server/build-time environment variables (`GEMINI_API_KEY` or `VITE_GEMINI_API_KEY`). No secrets or API credentials are hardcoded. If an API key is not present in the evaluator's environment, the system provides domain-grounded synthesis fallback to ensure uninterrupted review.

---

## 5. Software Architecture & Directory Structure

```
├── .env.example                # Documented environment variable templates
├── .gitignore                  # Git exclusion rules
├── index.html                  # HTML entry point with synchronized metadata
├── metadata.json               # Applet capability descriptor
├── package.json                # Project dependencies and npm scripts
├── tsconfig.json               # TypeScript compiler options (strict ES2022)
├── vite.config.ts              # Vite 8 bundler configuration
├── public/                     # Static distribution assets
│   └── paras_advisory_capstone.zip  # Downloadable submission package
└── src/
    ├── main.tsx                # Application bootstrap
    ├── App.tsx                 # Root coordinator, session router & modal hub
    ├── index.css               # Tailwind CSS v4 styling rules
    ├── types/
    │   └── index.ts            # TypeScript interfaces & domain models
    ├── data/
    │   └── mockData.ts         # 50-personnel SME practice enterprise data
    ├── services/
    │   └── geminiService.ts    # @google/genai SDK integration
    ├── utils/
    │   ├── scoringEngine.ts    # Mathematical 4-pillar valuation engine
    │   ├── sessionStore.ts     # Resilient localStorage session manager
    │   └── reportExporter.ts   # Microsoft Word (.doc) & PDF export engine
    ├── assets/
    │   └── images/             # High-fidelity HR performance visual assets
    └── components/
        ├── Header.tsx                  # 3-Zone top bar with persona switcher
        ├── LandingLoginScreen.tsx      # Enterprise login screen with password policy
        ├── EmployeeGrowthHub.tsx       # Auditor personal scorecard & AI insights
        ├── KPIProgressChart.tsx        # 3-view interactive progress & velocity charts
        ├── AnnualPerformanceMatrix.tsx # 4-step annual objective workflow
        ├── CertificationBonusPanel.tsx # AED 15,000 chartered bonus tracker
        ├── ManagerDashboard.tsx        # Practice evaluations desk & sliders
        ├── HRIntelligenceDashboard.tsx # Practice analytics & T&D budget sandbox
        ├── StatutoryComplianceModal.tsx# Bilingual UAE Labor Law notice generator
        ├── QuickEvaluationModal.tsx    # Standardized deliverable point awarder
        ├── AddCoachingModal.tsx        # Constructive mentorship logger
        ├── ReportsCenter.tsx           # Centralized Word/PDF export desk
        ├── AuditTrailView.tsx          # SHA-256 tamper-evident governance log
        └── ScoreSimulator.tsx          # What-If scoring sandbox
```

---

## 6. Evaluator Installation & Execution Guide

### Prerequisites
- **Node.js:** v18.0.0 or higher
- **Package Manager:** npm (v9+) or bun

### Step 1: Clone Repository
```bash
git clone https://github.com/<YOUR-USERNAME>/paras-advisory-capstone.git
cd paras-advisory-capstone
```

### Step 2: Configure Environment Variables
```bash
cp .env.example .env
```
*(Optional: Insert your Gemini API Key in `.env` to enable live LLM generation; if left empty, the built-in domain synthesizer functions seamlessly).*

### Step 3: Install Dependencies
```bash
npm install
```

### Step 4: Run Development Server
```bash
npm run dev
```
Open your browser to `http://localhost:3000`.

### Step 5: Build for Production
```bash
npm run build
npm run preview
```

---

## 7. Step-by-Step Jury Evaluation Tour

1. **Enterprise Landing Screen:**
   - Review the corporate branding and workforce performance photography.
   - Test custom password validation: Minimum 8 characters, at least 1 uppercase letter (`A-Z`), and 1 special symbol (`@`, `#`, `!`).
2. **1-Click Jury Personas:**
   - **Auditor / Employee:** `Zayed Al Dhaheri` — Inspect scorecards, tenure multipliers, and AED 15,000 bonus tracks.
   - **Practice Leader / Manager:** `Tariq Al Hammadi` — Adjust evaluation sliders, award deliverable points, and approve matrices.
   - **Head of People & Governance:** `Mariam Al Shamsi` — Simulate the AED 450,000 T&D budget and review statutory notices.
   - **Managing Partner:** `Mansoor Al Nuaimi` — Conduct executive review and inspect the SHA-256 audit trail.
3. **Annual Performance Matrix:**
   - Follow the 4-step cycle: Goal Setup $\rightarrow$ Manager Approval $\rightarrow$ Achievement Entry $\rightarrow$ Final Score Sealing.
4. **Export Engine:**
   - Download audit-ready evaluation dossiers in **Microsoft Word (`.doc`)** and **PDF** formats from the Reports Center.
5. **Gemini AI Synthesis:**
   - Click **"AI Executive Insights"** in the Growth Hub to observe `gemini-2.5-flash` performance synthesis.

---

*Paras Accounting & Auditing Advisory • Abu Dhabi, UAE • AICA Level 2 Capstone Assessment Submission*
