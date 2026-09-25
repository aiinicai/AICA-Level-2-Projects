import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Check,
  Printer,
  ShieldCheck,
  Cpu,
  Layers,
  Database,
  Calculator,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Code2,
  Sparkles,
  ArrowRight,
  ExternalLink,
  BookOpen,
  Calendar,
  User,
  Building,
} from 'lucide-react';
import { CapstoneDeckMetadata } from '../utils/generatePptxDeck';

interface CapstoneReportArtifactProps {
  metadata: CapstoneDeckMetadata;
}

export const CapstoneReportArtifact: React.FC<CapstoneReportArtifactProps> = ({ metadata }) => {
  const [copied, setCopied] = useState(false);

  const fullMarkdownContent = `# CAPSTONE PROJECT SPECIFICATION & TECHNICAL REPORT
## Next-Generation Indian Statutory Payroll & AI Tax Advisory System (AY 2026–27)

- **Candidate / Author:** ${metadata.studentName} (${metadata.studentEmail})
- **Project Title:** ${metadata.projectName}
- **Domain:** Statutory Financial Systems, Deterministic Computation & LLM Augmentation
- **Methodology:** Vibe Coding with Strict Deterministic Decoupling
- **Submission Date:** ${metadata.submissionDate}
- **Target Statutory Framework:** Indian Income Tax Act 1961, Finance Act 2025 / 2026 (Assessment Year 2026–27)

---

### 1. PURPOSE OF THIS REPORT & PROJECT EXECUTIVE SUMMARY

#### 1.1 Purpose of the Report
This technical report and capstone artifact documents the architectural design, algorithmic implementation, statutory compliance, security evaluation, and production readiness of the **Next-Gen Indian Statutory Payroll & AI Tax Advisory System**. 

The purpose of this submission is three-fold:
1. **Demonstrate End-to-End Financial Engineering:** Proving that complex statutory financial logic (dual tax regimes, pro-rata TDS forecasting, Section 87A rebate, progressive surcharges, marginal relief, EPF ceilings, Professional Tax slabs) can be implemented with 100% deterministic precision.
2. **Exemplify Responsible AI Integration:** Establishing a fault-tolerant hybrid architecture where an LLM (Google Gemini) provides intuitive natural language tax advisory and simulation scenarios without touching or hallucinating critical arithmetic calculations.
3. **Showcase Vibe Coding Methodology:** Demonstrating how rapid iterative development with AI assistance can yield a robust, modular, and enterprise-grade software artifact adhering to strict software engineering standards.

#### 1.2 Executive Summary
Indian payroll is globally recognized as one of the most labyrinthine statutory domains due to coexisting dual tax regimes (Old Regime under traditional slabs vs New Regime under Section 115BAC), monthly pro-rata TDS catch-up mechanisms, complex investment deduction ceilings (80C, 80D, 80CCD(1B), HRA, Section 24), and stringent audit requirements.

This project delivers a comprehensive, full-stack payroll and tax intelligence platform designed specifically for the Assessment Year 2026–27. It unifies:
- An enterprise-grade Employee Master directory with automated CTC decomposition into Basic, HRA, Special Allowance, and PF components.
- A deterministic 12-month payroll and statutory tax calculation engine executing monthly pro-rata TDS deductions.
- An interactive Tax Regime Simulator providing real-time side-by-side break-even analysis for employees and HR administrators.
- A multi-model Google Gemini Tax Copilot operating via backend proxy and resilient circuit breakers.
- A cryptographic tax governance module calculating SHA-256 integrity digests of statutory tax slabs to prevent unapproved tampering.
- Seamless multi-format interoperability: bidirectional Excel upload/export, automated statutory PDF payslips with currency-to-words conversion, and automated 16:9 widescreen PowerPoint deck generation.

---

### 2. HOW THE SYSTEM WORKS: ARCHITECTURAL PIPELINE

#### 2.1 The Two-Tier Decoupled Architecture
A fundamental design principle of this platform is the **strict separation of calculation from advisory**:
1. **Deterministic Calculation Tier (Zero-LLM):** All salary components, taxable income calculations, rebate eligibility, marginal relief, and monthly TDS schedules are computed using pure, idempotent TypeScript functions. No language model is ever permitted to perform mathematical calculations.
2. **Semantic & Advisory Tier (LLM-Powered):** Google Gemini 2.5 Flash / 1.5 Flash is invoked solely as an interpretive and advisory copilot. It receives structured, pre-calculated numerical summaries from the deterministic engine and translates them into actionable insights and strategic investment advice for the employee.

#### 2.2 End-to-End Payroll Computation Pipeline
Each payroll run follows a rigorous 7-stage deterministic pipeline:
1. **Salary Structuring:** Decompose monthly CTC into Basic (40-50%), HRA (40-50% of Basic), Employer PF (12% of Basic or ₹1,800 capped), and Special Allowance (balancing balancing figure).
2. **Annualization:** Project 12-month gross earnings by combining Year-to-Date (YTD) historical actuals with future projected months.
3. **Exemptions & Allowances:** Compute House Rent Allowance (HRA) exemption under Section 10(13A) using the minimum of:
   - Actual HRA received
   - Rent paid minus 10% of Basic salary
   - 50% (Metro) or 40% (Non-metro) of Basic salary
4. **Standard Deduction:** Apply statutory standard deduction of ₹75,000 for New Regime (AY 2026–27) or ₹50,000 for Old Regime.
5. **Chapter VI-A Deductions (Old Regime only):**
   - Section 80C: Capped at ₹150,000 (incorporating Employee EPF, PPF, ELSS, Life Insurance).
   - Section 80D: Medical Insurance (₹25,000 self/family + ₹50,000 senior citizen parents).
   - Section 80CCD(1B): Additional NPS deduction capped at ₹50,000.
   - Section 24(b): Self-occupied home loan interest capped at ₹200,000.
6. **Progressive Slab & Rebate Computation:**
   - **New Regime (AY 2026–27):** 
     - ₹0 - ₹4,00,000: Nil
     - ₹4,00,001 - ₹8,00,000: 5%
     - ₹8,00,001 - ₹12,00,000: 10%
     - ₹12,00,001 - ₹16,00,000: 15%
     - ₹16,00,001 - ₹20,00,000: 20%
     - ₹20,00,001 - ₹24,00,000: 25%
     - Above ₹24,00,000: 30%
     - Full tax rebate under Section 87A if taxable income does not exceed ₹12,00,000.
   - **Old Regime:** Slabs of 5%, 20%, 30% with rebate under Section 87A up to ₹5,00,000.
7. **Surcharge, Marginal Relief & Health/Education Cess:**
   - Progressive surcharge (10%, 15%, 25%) applied above threshold incomes (₹50L, ₹1Cr, ₹2Cr).
   - Mathematical marginal relief applied so that tax + surcharge does not exceed the statutory limit on excess income.
   - 4% Health & Education Cess applied on (Base Tax + Surcharge).
8. **Monthly TDS Catch-Up Calculation:**
   - Monthly TDS = (Net Annual Tax Payable - Tax Already Deducted YTD) / Remaining Months in FY.
   - This guarantees that mid-year salary increments or declaration revisions are smoothly amortized across remaining payroll cycles without manual adjustments.

---

### 3. COMPREHENSIVE FEATURES CATALOG

#### Module 1: Employee Master & Salary Structuring
- Centralized registry of employees tracking personal details, PAN, Aadhaar, UAN, Bank Account, IFSC, and Department.
- Dynamic salary structuring auto-allocating CTC into statutory constituents.
- Statutory toggles for Metro/Non-Metro designation and EPF wage ceiling compliance (₹15,000 statutory cap vs full basic).

#### Module 2: Monthly Salary & Payroll Register
- Full-company monthly payroll batch calculation.
- Granular breakdown of Gross Earnings, Net Disbursal, Employee EPF, Professional Tax, and Monthly TDS.
- Employer statutory contributions tracking (Employer EPF, Gratuity accrual, ESI).
- One-click individual payslip modal and bulk Excel export.

#### Module 3: Employee Tax Declarations
- Comprehensive investment submission interface for employees.
- Granular line-item tracking across 80C, 80D, 80CCD, 80E, 80G, and Home Loan Interest.
- HRA declaration with rental address, annual rent paid, and mandatory Landlord PAN validation for annual rent exceeding ₹1,00,000.
- Admin verification and approval workflow with real-time audit trail.

#### Module 4: Dual-Regime Tax Simulator & Break-Even Analysis
- Real-time side-by-side comparison of Old vs New Regime for any employee.
- Dynamic "What-If" slider allowing employees to simulate salary hikes and bonus impacts.
- Break-Even Analysis: Calculates the exact threshold of Chapter VI-A deductions required for the Old Regime to become more beneficial than the New Regime.

#### Module 5: Smart AI Tax Advisor & Floating Copilot
- Context-aware tax copilot powered by Google Gemini (@google/genai SDK).
- Pre-grounded with the active employee's exact deterministic financial figures.
- Provides actionable recommendations (e.g., maximizing NPS Section 80CCD(1B) to save ₹15,600 in tax).
- Resilient backend proxy architecture with multi-model fallback cascade (\`gemini-2.5-flash\` -> \`gemini-1.5-flash\`).

#### Module 6: Tax Governance & Cryptographic Auditing
- System-wide statutory configuration registry for AY 2026–27.
- SHA-256 cryptographic stamp of tax rules to guarantee statutory immutability.
- Legal reference citations (Finance Act, CBDT notifications) attached directly to rules.

#### Module 7: Employee Self-Service (ESS) Portal
- Role-based portal restricting employees to their personal records.
- Instant access to monthly payslip archive and annual tax summary.
- Ability to submit tax declarations and run personalized regime simulations.

#### Module 8: Multi-Format Interoperability & Export Engine
- **Excel Bulk Engine (XLSX):** Two-way synchronization. Export master templates, bulk upload employee records and tax declarations with automated schema validation.
- **Formal PDF Payslips (jsPDF):** Clean corporate payslip documents including breakdown tables, company metadata, and numerical amounts converted to Indian English words.
- **Automated PowerPoint Deck (PptxGenJS):** Generates a professional 16:9 widescreen 10-slide presentation deck covering project architecture, security, and statutory mechanics.

---

### 4. DATA SECURITY, CONFIDENTIALITY & PRIVACY ASSESSMENT

Payroll applications process the most sensitive category of corporate and personal data: Personally Identifiable Information (PII) coupled with direct financial figures. A thorough security analysis was conducted:

| Security Dimension | Current Implementation in Prototype | Production Enterprise Requirement |
| :--- | :--- | :--- |
| **Corporate Authentication & RBAC** | Dedicated Corporate Login Gateway: Employees authenticate using \`firstname@xyz.com\` (strictly scoped to personal records; zero peer data leakage), while HR/Payroll Admin authenticates using \`admin@xyz.com\` (full master & register access). | Enterprise SSO (Okta/Azure AD/Google Workspace OIDC), hardware security keys (FIDO2/WebAuthn), and adaptive MFA. |
| **API Keys & Secrets** | Stored strictly in environment variables; zero client-side exposure; server-side proxy route (\`/api/*\`). | HashiCorp Vault / Google Cloud Secret Manager with automated rotation. |
| **PII Data at Rest** | Stored in isolated local storage / memory; no external telemetry or tracking. | AES-256 column-level database encryption for PAN, Aadhaar, and Bank IFSC. |
| **Arithmetic Integrity** | 100% deterministic pure functions; mathematical tasks blocked from LLM inference. | Immutable append-only financial ledger with cryptographic block verification. |
| **OWASP Top 10** | Sanitized inputs, strict TypeScript types, zero \`dangerouslySetInnerHTML\`, protected server endpoints. | Web Application Firewall (WAF), rate-limiting middleware, and periodic pen-testing. |

---

### 5. PRODUCTION READINESS CHECKLIST

#### What is Ready Today:
- [x] Complete statutory calculation engine compliant with AY 2026–27.
- [x] Dual-regime progressive tax algorithms including 87A rebate and marginal relief.
- [x] Full UI/UX across Admin and Employee Self-Service perspectives.
- [x] Robust Excel import/export validation.
- [x] High-precision PDF payslip generator with words conversion.
- [x] Fault-tolerant Gemini AI integration with model fallback cascade.
- [x] Cryptographic SHA-256 statutory configuration stamp.

#### Enterprise Roadmap Before Live Bank Disbursal:
- [ ] Integration with Relational Database (Cloud SQL / PostgreSQL) with Row-Level Security.
- [ ] Bank Direct Credit API / NACH / NEFT batch file generation (standard banking file formats).
- [ ] State-wise Professional Tax dynamic engine (supporting all 28 states & UTs).
- [ ] Automated Form 16 Part A & Part B generation and TRACES / 24Q quarterly e-TDS filing validation.
- [ ] Biometric attendance and Leave Management System (LMS) synchronization for Loss of Pay (LOP) calculations.

---

### 6. VIBE CODING METHODOLOGY REFLECTION

Building this application through **Vibe Coding** represents a paradigm shift in software delivery:
1. **Architectural Intent Over Boilerplate:** Instead of hand-coding thousands of lines of repetitive styling and boilerplate, effort was directed toward defining strict domain boundaries, statutory precision, and security constraints.
2. **Deterministic Sandboxing:** The critical insight of this capstone is that AI should augment, not replace, core logic. By locking the mathematical calculations inside deterministic pure functions, the application eliminates the primary risk of generative AI (hallucination) while unlocking its primary superpower (contextual explanation and personalized guidance).
3. **Rapid Iteration with Rigorous Validation:** The system was incrementally evolved from basic salary registers to an all-inclusive enterprise suite, continuously verified through automated compiler checks, schema validations, and statutory test scenarios.

---
*Report generated for Capstone Project Evaluation. Copyright © ${new Date().getFullYear()} ${metadata.studentName}. All rights reserved.*`;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullMarkdownContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100 overflow-y-auto">
      {/* Top Action Bar for Report */}
      <div className="sticky top-0 z-20 bg-slate-950/95 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
            <BookOpen className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Comprehensive Capstone Project Specification & Technical Report
              <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-md">
                Formal Artifact
              </span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Purpose, System Architecture, Functional Modules, Security Audit & Production Roadmap
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-xs"
            title="Copy entire report as formatted Markdown"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-300 font-bold">Report Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-slate-400" />
                <span>Copy Markdown</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-xs"
            title="Print or Save as PDF"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>Print / PDF</span>
          </button>
        </div>
      </div>

      {/* Main Report Body */}
      <div className="max-w-4xl mx-auto w-full p-6 sm:p-10 space-y-8 text-slate-300 text-xs sm:text-sm leading-relaxed">
        {/* Document Header Card */}
        <div className="bg-gradient-to-br from-slate-800/90 to-slate-900/90 border border-slate-700 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/80 pb-6 mb-6">
            <div>
              <span className="inline-block px-2.5 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full text-[11px] font-bold uppercase tracking-wider mb-2">
                Capstone Artifact Submission
              </span>
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Next-Gen Indian Statutory Payroll & AI Tax Advisory System
              </h1>
              <p className="text-slate-400 text-xs mt-1">
                Deterministic Dual-Regime Payroll Engine, Google Gemini AI Advisory & Statutory Governance
              </p>
            </div>
            <div className="text-right">
              <span className="inline-block px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-mono font-bold">
                AY 2026–27 Statutory Compliance
              </span>
              <p className="text-[11px] text-slate-400 mt-1.5 font-mono">Date: {metadata.submissionDate}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider block">Candidate</span>
              <p className="text-white font-bold text-sm mt-0.5">{metadata.studentName}</p>
              <p className="text-slate-400 text-[11px] font-mono">{metadata.studentEmail}</p>
            </div>
            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider block">Core Tech Stack</span>
              <p className="text-white font-semibold mt-0.5">React 19 + TypeScript + Express</p>
              <p className="text-slate-400 text-[11px]">@google/genai SDK, SheetJS, jsPDF</p>
            </div>
            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider block">Methodology</span>
              <p className="text-white font-semibold mt-0.5">Vibe Coding Paradigm</p>
              <p className="text-emerald-400 text-[11px]">Strict Deterministic Calculation Sandbox</p>
            </div>
          </div>
        </div>

        {/* Section 1: Purpose of the Report */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <BookOpen className="h-5 w-5" />
            <span>1. Purpose of this Report & Project Genesis</span>
          </div>
          <p>
            The purpose of this capstone report artifact is to provide a complete, transparent, and rigorous technical review of the 
            <strong> Next-Gen Indian Statutory Payroll & AI Tax Advisory System</strong> built via Vibe Coding. It documents the real-world 
            problem being solved, the mathematical and statutory mechanisms driving the engine, the exact feature inventory, 
            the security posture, and the enterprise roadmap required for live production deployment.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1.5 text-indigo-300">The Problem It Solves</h4>
              <p className="text-slate-400 text-xs">
                Indian payroll is notorious for regulatory volatility. With the coexistence of the Old Tax Regime and the revised 
                New Tax Regime under Section 115BAC (Finance Act 2025/2026), employees struggle to pick the optimal regime, while 
                HR teams face severe operational drag calculating monthly pro-rata TDS, marginal relief, and complex HRA exemptions.
              </p>
            </div>
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1.5 text-emerald-300">The Innovative Solution</h4>
              <p className="text-slate-400 text-xs">
                This application solves both pain points simultaneously: a 100% deterministic pure-TypeScript calculation pipeline 
                eliminates computational errors, while a contextual Google Gemini AI copilot delivers personalized tax optimization 
                recommendations without any risk of mathematical hallucination.
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: How It Works */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <Cpu className="h-5 w-5" />
            <span>2. How the System Works: Architectural Pipeline</span>
          </div>

          <p>
            The system operates on a dual-tier architecture that guarantees mathematical precision while providing rich natural language intelligence:
          </p>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between text-indigo-400 font-bold border-b border-slate-800 pb-2">
              <span>SYSTEM ARCHITECTURE DIAGRAM</span>
              <span className="text-[10px] text-slate-500">DECOUPLED TIERS</span>
            </div>
            <div className="text-slate-300 leading-relaxed">
              ┌────────────────────────────────────────────────────────────────────────┐<br />
              │ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; PRESENTATION LAYER (React 19 + Tailwind) &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;│<br />
              │ [Employee Master] &nbsp;[Payroll Register] &nbsp;[Simulator] &nbsp;[ESS Portal] &nbsp;[Tax Governance] │<br />
              └───────────────────┬──────────────────────────────────┬─────────────────┘<br />
              &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; │ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;│ (Pre-calculated JSON)<br />
              &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ▼ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;▼<br />
              ┌──────────────────────────────────────┐ &nbsp; ┌─────────────────────────────┐<br />
              │ &nbsp; &nbsp; DETERMINISTIC ENGINE TIER &nbsp; &nbsp; &nbsp; &nbsp; │ &nbsp; │ &nbsp; &nbsp; &nbsp;AI COPILOT TIER &nbsp; &nbsp; &nbsp; &nbsp;│<br />
              │ • 12-Month Pro-Rata Projection &nbsp; &nbsp; &nbsp; │ &nbsp; │ • Express Proxy (/api/chat) │<br />
              │ • Section 10(13A) HRA Exemption &nbsp; &nbsp; &nbsp;│ &nbsp; │ • @google/genai SDK &nbsp; &nbsp; &nbsp; &nbsp; │<br />
              │ • Dual Slabs (Old vs 115BAC New) &nbsp; &nbsp; │ &nbsp; │ • Primary: gemini-2.5-flash │<br />
              │ • 87A Rebate & Marginal Relief Calc &nbsp;│ &nbsp; │ • Fallback: gemini-1.5-flash│<br />
              │ • 100% Pure TypeScript (Zero Math LLM)│ &nbsp; │ • Grounded Tax Advisory &nbsp; &nbsp; │<br />
              └──────────────────────────────────────┘ &nbsp; └─────────────────────────────┘
            </div>
          </div>

          <div className="space-y-3 mt-4">
            <h4 className="text-white font-bold text-xs uppercase tracking-wider text-indigo-300">
              The 7-Step Monthly Payroll Calculation Cycle:
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">1. CTC Decomposition:</span> Basic salary (40-50%), HRA, and Special Allowance.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">2. Statutory Deductions:</span> Employee EPF (12% with ₹1,800 wage cap option) and Professional Tax.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">3. Annualization:</span> Past actual gross + remaining projected monthly salary.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">4. Exemptions & Deductions:</span> HRA exemption formula, standard deduction (₹75,000 New / ₹50,000 Old), 80C, 80D, 80CCD, Section 24.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">5. Slab Tax & 87A Rebate:</span> AY 2026–27 New Regime (₹12L rebate threshold) vs Old Regime.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70">
                <span className="font-bold text-white">6. Surcharge & Cess:</span> High-income progressive surcharge with exact marginal relief formula + 4% Cess.
              </div>
              <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-700/70 sm:col-span-2">
                <span className="font-bold text-white">7. Monthly TDS Catch-Up:</span> (Total Annual Tax - YTD Tax Already Paid) / Remaining Months.
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Features */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <Layers className="h-5 w-5" />
            <span>3. Detailed Features & Modules Inventory</span>
          </div>

          <div className="space-y-4">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                1. Employee Master & Salary Structuring
              </h4>
              <p className="text-slate-400 text-xs">
                Comprehensive directory supporting multi-tier salary components (Basic, HRA, Special Allowance, Medical, Conveyance), 
                tax identifiers (PAN, Aadhaar, UAN, Bank IFSC), and statutory parameters like Metro vs Non-Metro classification and EPF wage capping.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                2. Monthly Payroll Register & PDF Payslips
              </h4>
              <p className="text-slate-400 text-xs">
                Organization-wide monthly salary processing. Computes gross earnings, net pay, employer contributions (PF, ESI, Gratuity accrual), 
                and taxes. Emits professional, publication-quality PDF payslips with automatic amount-in-words conversion.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                3. Employee Tax Declarations & Verification Workflow
              </h4>
              <p className="text-slate-400 text-xs">
                Self-service submission of investment proofs under Section 80C, 80D, 80CCD, 80E, 80G, and Home Loan Interest. 
                Includes HRA rental address tracking with automated Landlord PAN compliance enforcement for rents exceeding ₹1,00,000 annually.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                4. Dual-Regime Tax Simulator & Dynamic Break-Even Analysis
              </h4>
              <p className="text-slate-400 text-xs">
                Empowers HR and employees to simulate tax liability side-by-side. Dynamic what-if sliders model mid-year salary increments, 
                while the break-even calculator pinpoints the exact Chapter VI-A investment required for the Old Regime to outperform the New Regime.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                5. Smart AI Tax Advisor & Floating Copilot
              </h4>
              <p className="text-slate-400 text-xs">
                Powered by the official Google Gen AI SDK (\`@google/genai\`). The copilot is injected with pre-calculated, deterministic 
                tax summaries to provide contextual recommendations (e.g. voluntary NPS contributions) without the risk of numerical error.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                6. Tax Governance & Cryptographic Auditing
              </h4>
              <p className="text-slate-400 text-xs">
                Features a centralized statutory registry. The entire tax rulebook (slabs, cess, standard deductions) is hashed via 
                SHA-256 to ensure that statutory parameters cannot be modified without generating an audible cryptographic trail.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-700">
              <h4 className="font-bold text-white text-xs mb-1 text-indigo-300">
                7. Multi-Format I/O: Excel Bulk Upload & 16:9 Presentation Generation
              </h4>
              <p className="text-slate-400 text-xs">
                Two-way Excel compatibility using SheetJS allows bulk onboarding of hundreds of employees and declarations. 
                Additionally, built-in PptxGenJS generates a 10-slide widescreen presentation deck for capstone review.
              </p>
            </div>
          </div>
        </div>

        {/* Section 4: Data Security Assessment */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <ShieldCheck className="h-5 w-5" />
            <span>4. Comprehensive Data Security, Confidentiality & Privacy Review</span>
          </div>

          <p>
            Payroll systems handle highly sensitive Personally Identifiable Information (PII) including PAN cards, Aadhaar numbers, 
            bank account credentials, and exact compensation figures. The security architecture addresses the OWASP Top 10 vulnerabilities:
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-700 rounded-xl overflow-hidden">
              <thead className="bg-slate-950 text-indigo-300 uppercase tracking-wider font-bold">
                <tr>
                  <th className="p-3 border-b border-slate-700">OWASP Threat / Area</th>
                  <th className="p-3 border-b border-slate-700">App Implementation</th>
                  <th className="p-3 border-b border-slate-700">Security Evaluation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                <tr className="hover:bg-slate-800/50">
                  <td className="p-3 font-semibold text-white">API Keys & Credentials</td>
                  <td className="p-3 text-slate-300">Isolated in server environment variables; never leaked to frontend browser bundle.</td>
                  <td className="p-3 text-emerald-400 font-semibold">Secure (Compliant)</td>
                </tr>
                <tr className="hover:bg-slate-800/50">
                  <td className="p-3 font-semibold text-white">Broken Access Control (RBAC)</td>
                  <td className="p-3 text-slate-300">Role-based simulation (Admin vs Employee portal lock prevents lateral data inspection).</td>
                  <td className="p-3 text-emerald-400 font-semibold">Enforced in Prototype</td>
                </tr>
                <tr className="hover:bg-slate-800/50">
                  <td className="p-3 font-semibold text-white">Mathematical Hallucination</td>
                  <td className="p-3 text-slate-300">Strict decoupled sandbox: GenAI LLM is blocked from calculating numeric figures.</td>
                  <td className="p-3 text-emerald-400 font-semibold">Architecturally Protected</td>
                </tr>
                <tr className="hover:bg-slate-800/50">
                  <td className="p-3 font-semibold text-white">Input Validation & Injection</td>
                  <td className="p-3 text-slate-300">Strict TypeScript typing, Excel import schema sanitization, zero raw HTML injection.</td>
                  <td className="p-3 text-emerald-400 font-semibold">Protected</td>
                </tr>
                <tr className="hover:bg-slate-800/50">
                  <td className="p-3 font-semibold text-white">Data at Rest (PII Storage)</td>
                  <td className="p-3 text-slate-300">Stored in browser local storage for prototype testing; no external telemetry sent.</td>
                  <td className="p-3 text-amber-400 font-semibold">Requires DB Encryption for Live</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 5: Production Readiness */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <CheckCircle2 className="h-5 w-5" />
            <span>5. Production Readiness Checklist & Deployment Roadmap</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-emerald-950/20 border border-emerald-500/30 p-4 rounded-xl">
              <h4 className="font-bold text-emerald-400 text-xs mb-2 flex items-center gap-2">
                <Check className="h-4 w-4" /> Production-Ready Components
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
                <li>100% deterministic AY 2026–27 Indian tax calculation engine</li>
                <li>Dual-regime comparison and marginal relief formulas</li>
                <li>Responsive, accessible UI with print-optimized CSS</li>
                <li>Robust Excel import and bulk template validation</li>
                <li>Client-side vector PDF generation with word currency parser</li>
                <li>Multi-model GenAI proxy with circuit-breaker fallback</li>
              </ul>
            </div>

            <div className="bg-amber-950/20 border border-amber-500/30 p-4 rounded-xl">
              <h4 className="font-bold text-amber-400 text-xs mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> Roadmap Before Bank Direct Credit
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
                <li>PostgreSQL / Cloud SQL relational persistence with Row-Level Security</li>
                <li>Bank direct credit batch file generator (NACH / NEFT CMS formats)</li>
                <li>State-specific Professional Tax rules for all 28 Indian states</li>
                <li>Quarterly e-TDS 24Q and Form 16 Part A & B generation</li>
                <li>Biometric punch-in / Loss of Pay (LOP) automated synchronization</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Section 6: Vibe Coding Methodology */}
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 text-indigo-400 font-bold text-base border-b border-slate-700 pb-3">
            <Sparkles className="h-5 w-5" />
            <span>6. Technical Reflection: The Vibe Coding Methodology</span>
          </div>
          <p>
            This project represents a benchmark in <strong>Vibe Coding</strong> — moving from conceptual product specification to 
            a fully functional, highly complex statutory platform using prompt-driven software iteration.
          </p>
          <p className="text-slate-400 text-xs">
            The core lesson learned is that Vibe Coding reaches peak efficiency when architectural guardrails are established early:
            by deliberately confining LLMs to conversational advisory and keeping financial computation strictly deterministic, 
            the application achieved rapid development velocity without compromising financial accuracy or statutory compliance.
          </p>
        </div>

        {/* Document Footer */}
        <div className="text-center text-slate-500 text-xs border-t border-slate-800 pt-6">
          <p>Capstone Project Specification & Technical Report Artifact • Assessment Year 2026–27</p>
          <p className="text-[11px] mt-1 font-mono text-slate-600">
            Engineered by {metadata.studentName} ({metadata.studentEmail})
          </p>
        </div>
      </div>
    </div>
  );
};
