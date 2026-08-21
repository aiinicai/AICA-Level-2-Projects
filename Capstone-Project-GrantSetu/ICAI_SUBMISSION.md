# ICAI AI Training - Keystone Capstone Project Submission

**Project Title**: GrantSetu — NGO Governance, Financial Audit & Grant Management ERP  
**Level**: Level 2 Keystone Capstone Project  
**Domain**: Non-Profit Accounting, Statutory Audit, FCRA Compliance & AI-Assisted Grant Management  
**Trainee / Author**: Subhasis  
**Evaluating Body**: Institute of Chartered Accountants of India (ICAI)  

---

## 🏛️ Project Objective & Relevance to ICAI Trainees

Chartered Accountants in India frequently perform statutory audits, tax compliance reviews, and financial due diligence for Non-Governmental Organizations (NGOs) and Charitable Trusts. Non-profits operate under unique regulatory constraints:
1. **FCRA 2010**: Strict prohibition against mixing foreign contributions with domestic funds.
2. **Income Tax Act (Sec 11, 12A, 80G)**: Mandatory minimum 85% application of income towards charitable purposes.
3. **General Financial Rules (GFR 2017)**: Mandatory submission of **Form GFR 12-A** Utilization Certificates for public/government grants.
4. **Sub-Recipient Risk**: Due diligence and monitoring of downstream NGOs receiving sub-grants.

**GrantSetu** was developed as an offline-first ERP solution to solve these exact accounting and governance challenges. It provides CAs and NGO management with a single interface to manage grants from proposal to audit sign-off.

---

## 🔍 Key Architectural & Statutory Features Evaluated

### 1. Statutory Registration & Profile Vault (`ProfileVault.jsx`)
- Registry for 12A, 80G, FCRA Registration, NITI Aayog DARPAN ID, CSR-1, and 10AC certificates.
- Automated expiry warning indicators to prevent compliance lapses.

### 2. Dual-Ledger Expense & Voucher Management (`ExpenseTracker.jsx`)
- Enforces strict ledger separation between **FCRA Foreign Contributions** and **Domestic INR Funds**.
- Captures GST/TDS tax deductions per voucher.
- Digital voucher attachment storage for audit trails.

### 3. Automated Form GFR 12-A UC Compilation (`UCGenerator.jsx`)
- Automatically compiles standard Form GFR 12-A Utilization Certificates:
  - Opening unspent balance
  - Grants received during the period
  - Interest earned
  - Actual expenditure incurred
  - Closing unspent balance to be refunded/carried forward
- Formatted directly for CA verification and signature.

### 4. AI-Assisted Proposal & Logframe Builder (`ProposalBuilder.jsx`)
- Generates structured Logical Framework (Logframe) matrices (Objectives, Indicators, Verification, Assumptions).
- Multi-tranche budget matrix creation for donor approval.

### 5. Downstream NGO Sub-Granting Engine (`SubGranting.jsx`)
- Monitors sub-recipient NGO compliance, tranche disbursemnt conditions, and assigns a **Risk Scorecard** (Low/Medium/High Risk) based on financial reporting history.

### 6. Grant Closure & Audit Sign-Off (`GrantClosure.jsx`)
- Verifies physical asset transfers, donor unspent balance refunds, and completes a pre-audit checklist before formal grant sign-off.

---

## 🧪 Evaluation Checklist for ICAI Instructors

Evaluators can test and verify the system using the following steps:

1. **Web Live Preview**:
   - Run `npm run dev` and open `http://localhost:5173`.
2. **Interactive Sandbox**:
   - Navigate to the **User Guide** module and click **"Load Demo Dataset"**.
   - Inspect pre-populated grants (e.g., *Clean Water Initiative*, *Rural Education Project*).
3. **FCRA Compliance Verification**:
   - Open **Expense Tracker**, attempt to log an expense under an FCRA grant, and verify that the ledger automatically tags the fund type as `FCRA Foreign`.
4. **GFR 12-A UC Generation**:
   - Open **UC Generator**, select a grant, click **"Generate UC"**, and preview the statutory Form GFR 12-A preview ready for printing/exporting.
5. **Standalone Windows App**:
   - Launch via `npm run electron` to test offline desktop behavior.

---

## 📁 Repository Deliverables & Verification

- `src/components/`: Modular React components for all 10 ERP modules.
- `src/context/GrantContext.jsx`: Central state management and persistent LocalStorage database engine.
- `src/utils/sampleData.js`: Comprehensive sample dataset designed for demonstration.
- `electron-main.cjs`: Desktop container script.
- `README.md`: Complete technical specification and run guide.

---

*Submitted in partial fulfillment of the requirements for the ICAI AI Training Program (Level 2 Keystone Capstone).*
