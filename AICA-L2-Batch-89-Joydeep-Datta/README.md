[README.md](https://github.com/user-attachments/files/32667025/README.md)
# Next-Gen Indian Statutory Payroll & AI Tax Advisory System (AY 2026–27)

[![React](https://img.shields.io/badge/React-19.0-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Google Gemini API](https://img.shields.io/badge/Google_Gemini-@google/genai-8E75C4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Statutory Compliance](https://img.shields.io/badge/Statutory_Compliance-AY_2026--27-10B981)](#statutory-tax-compliance-ay-202627)
[![License](https://img.shields.io/badge/License-Proprietary_Capstone-blue)](#author--capstone-metadata)

> **Candidate / Author:** Joydeep Datta (`joydeep.datta@gmail.com`)  
> **Project Scope:** Full-Stack Enterprise Indian Payroll, Statutory TDS Computation, Multi-Format Export Engine, and Resilient Gemini AI Advisory.

---

## 📌 Executive Summary

The **Next-Gen Indian Statutory Payroll & AI Tax Advisory System** is an enterprise-grade financial engineering application built from the ground up for Indian payroll processing under **Assessment Year 2026–27 (Financial Year 2026–27)**. 

The application decouples **deterministic statutory calculations** (gross-to-net salary, EPF, ESI, Professional Tax, Section 10(13A) HRA, Section 115BAC tax slabs, and Section 87A rebate) from **generative AI advisory**. This guarantees that all monetary outputs, payslips, and tax liabilities remain **100% mathematically exact and zero-hallucination**, while augmenting employee decision-making with context-aware AI tax planning powered by Google Gemini.

---

## 🚀 Key Functional Modules

### 1. Company Salary Register & Payroll Engine
* **Month-by-Month Processing:** Supports full financial year cycle (April to March) with dynamic attendance proration and calendar-day adjustments.
* **Statutory Breakdown:** Automates employee and employer contributions for Provident Fund (EPF 12% with ₹15,000 wage ceiling toggle), Employee State Insurance (ESI 0.75% / 3.25%), State Professional Tax (PT), and monthly TDS.
* **Batch Analytics:** Real-time visibility into company-wide gross pay, total statutory deductions, and net disbursements.

### 2. Employee Master Management
* Comprehensive master record management supporting CTC breakdown (Basic, HRA, Conveyance, Education, LTA, Special Allowances).
* Bank account details (IFSC, Account Number), PAN, UAN, PF number, and Employment Status (Active, New Joiner, Resigned/F&F).

### 3. Tax Declarations & Form 12BB
* Granular line-item tracking across Chapter VI-A deductions: Section 80C (₹1.5L cap), 80D (Mediclaim), 80CCD(1B) Tier-1 NPS (₹50k cap), 80E, 80G, and Section 24(b) Home Loan Interest.
* Automated HRA verification evaluating annual rent, rental location (Metro vs Non-Metro), and mandatory Landlord PAN validation for rent exceeding ₹1,00,000/year.

### 4. Dual-Regime Tax Simulator & Break-Even Analysis
* Side-by-side comparison of **Old Tax Regime** vs. **New Tax Regime (Section 115BAC)** for all employees.
* **Interactive What-If Modeling:** Sliders allowing employees to simulate salary hikes, bonus payouts, and investment changes.
* **Break-Even Calculator:** Calculates the exact threshold of deductions required for the Old Regime to become more beneficial than the default New Regime.

### 5. Smart AI Tax Advisor & Floating Copilot (with CA Fallback)
* Grounded in the employee's active salary and investment declarations using the official `@google/genai` TypeScript SDK.
* Recommends concrete tax-saving strategies (e.g., opting into Section 80CCD(1B) NPS for an extra ₹15,600 tax savings in the 30% slab).
* **Two-Tier Resilient Architecture:** If the upstream LLM times out or is offline, a deterministic **"Chartered Accountant (CA) Fallback"** engine instantly generates verified statutory guidance without interruption.

### 6. Employee Self-Service (ESS) Portal
* Dedicated portal for individual employees to view and download monthly payslips, simulate tax liabilities, and submit tax declarations.
* Full isolation from administrative salary registers and peer records.

### 7. Multi-Format Interoperability & Export Engine
* **Excel Engine (`xlsx`):** Bulk import/export of employee masters and tax declarations with schema validation.
* **Formal PDF Payslips (`jspdf`):** Corporate salary slips with tabular component breakdowns and numerical amounts converted to Indian English words (e.g., *"Rupees One Lakh Twenty Thousand Only"*).
* **PowerPoint Deck Generator (`pptxgenjs`):** Generates a 16:9 widescreen 10-slide capstone presentation deck.
* **Capstone Project Report:** Full in-app technical specification report with 1-click Markdown copy and PDF print capability.

---

## 🏛️ System Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           CLIENT INTERFACE (SPA)                          │
│                                                                           │
│   ┌───────────────────────────────┐     ┌─────────────────────────────┐   │
│   │    Administrator Dashboard    │     │   Employee Portal (Scoped)  │   │
│   │ (Registers, Master, TDS Slabs)│     │  (Payslips, Simulator, ESS) │   │
│   └───────────────┬───────────────┘     └──────────────┬──────────────┘   │
└───────────────────┼────────────────────────────────────┼──────────────────┘
                    │                                    │
                    ▼                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    DETERMINISTIC STATUTORY COMPUTATION CORE               │
│                                                                           │
│  • Gross-to-Net Engine        • Sec 10(13A) HRA Rules                     │
│  • EPF (12% / 15k Ceiling)    • AY 2026-27 Slabs (Old vs New 115BAC)      │
│  • Sec 87A Rebate & Relief    • Break-Even & Surcharge Calculator         │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        SECURE EXPRESS BACKEND PROXY                       │
│                                                                           │
│   POST /api/chat ──► Google Gemini API (@google/genai SDK)                │
│                        │                                                  │
│                        ├──► [Success] ──► Conversational Advice           │
│                        │                                                  │
│                        └──► [Timeout / Offline]                           │
│                                  │                                        │
│                                  ▼                                        │
│                             CA Fallback Engine                            │
│                             (Rule-Based Guidance)                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security & Access Control (RBAC)

The application enforces strict **Role-Based Access Control (RBAC)** and a gatekeeper security perimeter:

| Role | Login Identifier | Access Perimeter |
| :--- | :--- | :--- |
| **Administrator** | `admin@xyz.com` | Full superuser access to company salary register, employee master records, Form 16 / TDS batch approvals, and tax governance. |
| **Employee** | `firstname@xyz.com` | Strictly scoped to personal self-service portal (e.g. `ananya@xyz.com`, `mandeep@xyz.com`, `dilawar@xyz.com`, `joydeep@xyz.com`). Peer records and admin tabs are completely blocked. |

* **Gatekeeper by Default:** Unauthenticated visitors are held at the Corporate Login Gateway; no sensitive payroll or salary data is mounted in the DOM without authentication.
* **1-Click Test Directory:** Built-in review directory allows evaluators to toggle between Administrator and all corporate employees with one click.
* **Server-Side API Key Isolation:** `GEMINI_API_KEY` is retained strictly on the backend Express proxy; zero client-side credential exposure.

---

## ⚖️ Statutory Tax Compliance (AY 2026–27)

### New Tax Regime (Default u/s 115BAC)
* Standard Deduction: **₹75,000**
* Section 87A Tax Rebate ceiling: **₹7,00,000** (Full rebate) with marginal relief provisions.
* Progressive Slabs:
  * Up to ₹3,00,000: **Nil**
  * ₹3,00,001 – ₹7,00,000: **5%**
  * ₹7,00,001 – ₹10,00,000: **10%**
  * ₹10,00,001 – ₹12,00,000: **15%**
  * ₹12,00,001 – ₹15,00,000: **20%**
  * Above ₹15,00,000: **30%**

### Old Tax Regime (Elective)
* Standard Deduction: **₹50,000**
* Full Chapter VI-A deductions: Section 80C (up to ₹1,50,000), Section 80D (₹25,000 self + ₹50,000 senior parents), Section 80CCD(1B) NPS (₹50,000), and Section 24(b) Home Loan Interest (up to ₹2,00,000).
* Section 10(13A) House Rent Allowance exemption with 50% (Metro) and 40% (Non-Metro) limits.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend Framework** | React 19, TypeScript 5.8 |
| **Styling & UI** | Tailwind CSS v4, Lucide React, Motion |
| **Build & Tooling** | Vite 6, TSX, PostCSS |
| **Backend & Proxy** | Node.js, Express, dotenv |
| **Generative AI** | Google Gemini API (`@google/genai` SDK v2.4.0) |
| **Export Formats** | `xlsx` (Excel), `jspdf` (PDF Payslips), `pptxgenjs` (16:9 Presentations) |

---

## 💻 Local Development Setup

### Prerequisites
* **Node.js:** v18.0.0 or higher
* **npm:** v9.0.0 or higher
* **Google Gemini API Key:** (Optional for AI copilot; deterministic calculations function without it)

### 1. Clone & Install Dependencies
```bash
git clone <repository-url>
cd <project-directory>
npm install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` (or set `GEMINI_API_KEY`):
```bash
cp .env.example .env
```
Inside `.env`:
```env
PORT=3000
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Launch the Application
```bash
npm run dev
```
The application will launch on `http://localhost:3000`.

### 4. Build for Production
```bash
npm run build
npm run start
```

---

## 🎓 Capstone Presentation & Report Artifacts

The application includes built-in presentation and documentation tools:

* **Interactive Slide Deck:** Click **"🎓 Capstone Artifact"** in the top navigation or login screen to view the 10-slide 16:9 presentation deck.
* **Downloadable PowerPoint (.pptx):** Generates and downloads a slide deck with speaker notes via PptxGenJS.
* **Comprehensive Project Report:** Switch to the **Project Report Artifact** tab to view the complete technical specification, copy it as formatted Markdown, or print it to PDF.

---

## 👤 Author & Capstone Metadata

* **Author:** Joydeep Datta
* **Email:** [joydeep.datta@gmail.com](mailto:joydeep.datta@gmail.com)
* **Domain:** Statutory Financial Engineering & Generative AI Systems
* **Target Assessment Year:** AY 2026–27 (FY 2026–27)
