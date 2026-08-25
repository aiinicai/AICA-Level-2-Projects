import { AuditReportData } from '../types';

export interface ChatResponse {
  reply: string;
  suggestedFollowUps?: string[];
}

export function handleOfflineChatQuery(
  question: string,
  report: AuditReportData | null,
  conversationHistory?: Array<{ sender: 'user' | 'assistant'; content: string }>
): ChatResponse {
  const qLower = question.toLowerCase();
  const entityName = report?.summary?.entityName || 'the Audited Entity';
  const scale = report?.summary?.reportingScale || '₹ in Lakhs';

  // 1. Audit Query Memo Request
  if (qLower.includes('memo') || qLower.includes('audit query') || qLower.includes('query to management')) {
    // Find relevant inconsistency if any
    const kmpIncon = report?.part2Inconsistencies.find(i => i.lineItem.toLowerCase().includes('kmp') || i.lineItem.toLowerCase().includes('remuneration'));
    const recIncon = report?.part2Inconsistencies.find(i => i.lineItem.toLowerCase().includes('receivable') || i.lineItem.toLowerCase().includes('ecl'));
    const genIncon = report?.part2Inconsistencies[0];

    const target = kmpIncon || recIncon || genIncon;
    const itemTitle = target ? target.lineItem : 'Financial Statement Disclosure Variance';
    const primaryFig = target ? target.primaryFigure : `${scale} 18,450.00`;
    const noteFig = target ? target.noteFigure : `${scale} 18,250.00`;

    return {
      reply: `### STATUTORY AUDIT QUERY MEMORANDUM
**To:** Chief Financial Officer / Head of Accounts, ${entityName}  
**From:** Statutory Audit Engagement Team  
**Date:** ${new Date().toLocaleDateString('en-IN')}  
**Subject:** Audit Query on ${itemTitle} — Verification of Casting & Statutory Disclosures  
**Reference:** Ind AS 1 / Schedule III to the Companies Act, 2013 / QRB Review Checklist  

---

**1. Matter Observed:**  
During our audit verification of the Financial Statements for the period under review, the following variance/inconsistency was noted:
- **Amount reported on Face of Statement:** ${primaryFig}
- **Amount reported in Notes / Sub-schedule:** ${noteFig}
- **Discrepancy Detail:** ${target?.discrepancy || 'Schedule footing and primary statement cross-reference mismatch.'}

**2. Statutory & Accounting Standards Benchmark:**  
Under Ind AS and Schedule III (Division II) to the Companies Act 2013, figures reported in the primary financial statements must strictly tie in with note sub-schedules and underlying general ledgers without unexplained mathematical variances.

**3. Action Required from Management:**  
Management is requested to provide:
1. Reconciled schedule explaining the underlying variance between the primary statement and note breakups.
2. Necessary correcting adjusting journal entry before final closure and audit committee sign-off.
3. Updated draft Note to Accounts incorporating all mandatory itemized sub-breakups.

*Please furnish your written response along with supporting audit trail vouchers within 24 hours.*`,
      suggestedFollowUps: [
        'Draft MRL clause for this discrepancy',
        'What is the CARO 2020 impact of this issue?',
        'Draft Qualified Opinion paragraph under SA 705',
      ],
    };
  }

  // 2. Management Representation Letter (MRL) Clause Request
  if (qLower.includes('mrl') || qLower.includes('management representation') || qLower.includes('representation letter')) {
    return {
      reply: `### DRAFT MANAGEMENT REPRESENTATION LETTER (MRL) CLAUSES (SA 580)
*To be incorporated in the formal MRL issued on client letterhead to Statutory Auditors:*

---

**1. Ind AS 37 — Provisions & Contingent Liabilities:**
> *"We confirm that all known claims, litigations, tax demands under direct and indirect taxes (Income Tax, GST, Customs), guarantees, and commitments against ${entityName} have been fully evaluated under Ind AS 37. Where a present obligation with probable outflow exists, adequate provision has been recorded. For all other contingent liabilities, complete quantification and expected financial effects have been truthfully disclosed in Note to Accounts, and no other material unrecorded exposures exist."*

**2. Ind AS 24 — Related Party Disclosures:**
> *"We confirm that the disclosures of related party relationships, transactions during the financial year, and outstanding balances at the year-end are complete and accurately categorized across short-term benefits, post-employment benefits, and other statutory heads in accordance with Ind AS 24. No other informal or undeclared transactions with Key Management Personnel (KMPs) or relatives were entered into."*

**3. Title Deeds & Immovable Property (Schedule III MCA 2021):**
> *"We confirm that all title deeds of immovable properties (other than properties where the company is the lessee) are held in the name of ${entityName}. There are no benami properties held or proceedings initiated against the company under the Prohibition of Benami Property Transactions Act, 1988."*

**4. Borrowings & Quarterly Stock Statements:**
> *"We confirm that quarterly returns or statements of current assets filed with banks/financial institutions in respect of sanctioned credit facilities are in complete agreement with the books of account of the company."*`,
      suggestedFollowUps: [
        'Draft Audit Query Memo for management',
        'How does CARO 2020 Clause (ix) apply to borrowings?',
        'Draft Emphasis of Matter (EoM) paragraph',
      ],
    };
  }

  // 3. CARO 2020 Reporting Impact
  if (qLower.includes('caro') || qLower.includes('caro 2020') || qLower.includes('companies auditor report order')) {
    return {
      reply: `### CARO 2020 (COMPANIES AUDITOR'S REPORT ORDER) AUDIT EVALUATION
**Entity:** ${entityName}  

The statutory auditor is required to report on 21 specific clauses under CARO 2020. Based on the audit findings:

1. **Clause (i)(c) - Title Deeds of Immovable Property:**
   - *Requirement:* Auditor must report whether title deeds of all immovable properties (other than leased properties) are held in the name of the company. If not, details (description, gross value, holder name, relationship) must be provided in tabular format.
   - *Audit Status:* Ensure Schedule III additional regulatory note is cross-checked against registered sale deeds.

2. **Clause (ii)(b) - Quarterly Statements to Banks:**
   - *Requirement:* Auditor must report whether quarterly returns/stock statements submitted by the company to banks against working capital limits (>₹5 Cr) are in agreement with the books.
   - *Audit Status:* Any material variance exceeding 5% must be explicitly stated in the CARO annexure with reconciliation.

3. **Clause (vii)(a) - Statutory Dues:**
   - *Requirement:* Undisputed statutory dues (PF, ESI, Income Tax, GST, Cess) outstanding for more than 6 months from the date they became payable must be quantified.

4. **Clause (ix)(a) - Default in Repayment of Borrowings:**
   - *Requirement:* Auditor must report whether the entity has defaulted in repayment of loans or payment of interest to any lender.`,
      suggestedFollowUps: [
        'Draft Audit Query Memo for management',
        'Draft Qualified Opinion if bank reconciliation fails',
        'What are the 11 Schedule III ratios required?',
      ],
    };
  }

  // 4. Qualified / Modified Opinion Drafting (SA 705)
  if (qLower.includes('opinion') || qLower.includes('qualified') || qLower.includes('modified') || qLower.includes('eom') || qLower.includes('emphasis of matter') || qLower.includes('sa 705')) {
    return {
      reply: `### DRAFT INDEPENDENT AUDITOR'S REPORT MODIFICATIONS (SA 705 / SA 706)

#### 1. Qualified Opinion Paragraph (SA 705)
> **"Qualified Opinion:**  
> In our opinion and to the best of our information and according to the explanations given to us, *except for the effects of the matter described in the Basis for Qualified Opinion section of our report*, the aforesaid financial statements give the information required by the Companies Act, 2013 in the manner so required and give a true and fair view in conformity with Ind AS and other accounting principles generally accepted in India..."

> **"Basis for Qualified Opinion:**  
> As detailed in Note X to the financial statements, the Company has reported ${scale} ${report?.part2Inconsistencies[0]?.primaryFigure || 'XX'} on the face of the financial statements, whereas the underlying note schedule computes to ${scale} ${report?.part2Inconsistencies[0]?.noteFigure || 'YY'}. Consequently, profit for the year and net carrying assets are overstated/understated by ${scale} ${report?.part2Inconsistencies[0]?.discrepancy || 'ZZ'}. We were unable to obtain sufficient appropriate audit evidence regarding this variance."

---

#### 2. Emphasis of Matter Paragraph (SA 706)
> **"Emphasis of Matter:**  
> We draw attention to Note Y to the financial statements, which describes the uncertainty relating to pending taxation demands / regulatory litigations under Ind AS 37. Our opinion is not modified in respect of this matter."`,
      suggestedFollowUps: [
        'Draft Audit Query Memo to CFO',
        'Draft MRL clauses under SA 580',
      ],
    };
  }

  // 5. Schedule III 11 Ratios Checklist
  if (qLower.includes('ratio') || qLower.includes('schedule iii') || qLower.includes('variance') || qLower.includes('25%')) {
    return {
      reply: `### ICAI GUIDANCE NOTE ON SCHEDULE III (MCA 2021) — 11 STATUTORY RATIOS
Under MCA Notification GSR 207(E), companies must disclose the following 11 ratios with comparative prior year figures. **Mandatory management explanation is required for any variance exceeding 25%:**

1. **Current Ratio:** Current Assets / Current Liabilities
2. **Debt-Equity Ratio:** Total Debt / Total Shareholders' Equity
3. **Debt Service Coverage Ratio (DSCR):** (PAT + Non-cash exp + Interest) / (Interest + Principal repayments)
4. **Return on Equity (ROE):** Net Profit after Tax / Average Shareholders' Equity
5. **Inventory Turnover Ratio:** Cost of Goods Sold / Average Inventory
6. **Trade Receivables Turnover Ratio:** Net Credit Sales / Average Trade Receivables
7. **Trade Payables Turnover Ratio:** Net Credit Purchases / Average Trade Payables
8. **Net Capital Turnover Ratio:** Total Sales / Working Capital (Current Assets - Current Liabilities)
9. **Net Profit Ratio:** Net Profit after Tax / Total Revenue from Operations
10. **Return on Capital Employed (ROCE):** EBIT / Capital Employed (Net Worth + Total Debt - Deferred Tax)
11. **Return on Investment (ROI):** Income from Investments / Weighted Average Investment Value`,
      suggestedFollowUps: [
        'Draft Audit Query Memo for ratio variance >25%',
        'What are the Trade Payables aging buckets?',
      ],
    };
  }

  // 6. Default Fallback Technical Consultation
  return {
    reply: `### CA TECHNICAL AUDIT ADVISORY
**Context:** ${entityName} | Framework: Ind AS & Schedule III Div II  
**Current Audit Status:** Compliance Score: **${report?.summary?.overallComplianceScore || 'Needs Review'}** with **${report?.summary?.totalDiscrepancies || 0} total exceptions**.

I have analyzed your query: *"${question}"*.

**Key Technical Audit Directives:**
1. **Statutory Standards:** All accounting treatments must strictly conform to Ind AS framework, Guidance Notes issued by ICAI, and relevant NFRA Quality Review Board criteria.
2. **Materiality & Casting:** Numerical discrepancies on the face of the Balance Sheet / P&L vs Notes require either ledger adjustments or documented Audit Query Memos.
3. **Disclosure Completeness:** Disclosures under Ind AS 1, 7, 12, 16, 19, 24, 37, 107, 109, 115, 116 and Schedule III MCA 2021 amendments are mandatory statutory obligations.

*How would you like to proceed? You can ask me to draft a specific Audit Query Memo, MRL clause, CARO evaluation, or SA 705 audit opinion modification.*`,
    suggestedFollowUps: [
      'Draft Audit Query Memo for management',
      'Draft MRL clause under SA 580',
      'Assess CARO 2020 reporting impact',
      'Draft Qualified Audit Opinion under SA 705',
    ],
  };
}
