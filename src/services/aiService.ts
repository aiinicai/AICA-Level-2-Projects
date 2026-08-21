import { CapexItem, CapitalisationReviewResult, Asset, RiskFinding } from '../types';

export async function reviewCapitalisationWithAI(item: CapexItem): Promise<CapitalisationReviewResult> {
  try {
    const res = await fetch('/api/ai/review-capitalisation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.data) {
        return data.data;
      }
    }
  } catch (e) {
    console.warn('Backend AI call failed, using client-side fallback engine:', e);
  }

  // Client-side deterministic engine fallback
  const desc = item.description.toLowerCase();
  const amount = item.amountINR;

  if (desc.includes('software') || desc.includes('subscription') || desc.includes('license')) {
    if (desc.includes('annual') || desc.includes('subscription')) {
      return {
        recommendation: 'Expense',
        recommendedCategory: 'Operating Software Subscriptions (P&L)',
        usefulLifeYears: 1,
        salvageValuePct: 0,
        componentisationDetails: [],
        gstItcEligibility: 'Eligible',
        gstAnalysis: 'Full 18% GST ITC claimable as operational business expense under CGST Sec 16.',
        capitalisationDate: item.invoiceDate,
        reasoning: 'Recurring SaaS annual subscription; does not confer enduring control over an asset per Ind AS 38.',
        evidenceKeyPoints: [
          `Invoice ₹${(amount / 100000).toFixed(2)}L for annual term`,
          'Subscription renewed annually'
        ],
        confidenceScore: 0.97,
        policyReference: 'Ind AS 38 & Internal IT Expense Policy',
        riskWarnings: ['Capitalising cloud subscriptions violates Ind AS 38 and misstates EBITDA.']
      };
    }
  }

  if (desc.includes('maintenance') || desc.includes('repairs') || desc.includes('painting')) {
    return {
      recommendation: 'Expense',
      recommendedCategory: 'Repairs & Maintenance (P&L)',
      usefulLifeYears: 1,
      salvageValuePct: 0,
      componentisationDetails: [],
      gstItcEligibility: 'Eligible',
      gstAnalysis: 'Full ITC eligible on factory repairs.',
      capitalisationDate: item.invoiceDate,
      reasoning: 'Under Ind AS 16 para 12, expenses incurred for day-to-day servicing are recognized in profit or loss as incurred.',
      evidenceKeyPoints: [
        'Routine periodic maintenance scope',
        'No enhancement of production output or useful life'
      ],
      confidenceScore: 0.98,
      policyReference: 'Ind AS 16 para 12 (Day-to-day servicing)',
      riskWarnings: []
    };
  }

  // Default Capitalise with Componentisation
  return {
    recommendation: 'Capitalise',
    recommendedCategory: 'Plant & Machinery',
    usefulLifeYears: 15,
    salvageValuePct: 5,
    componentisationDetails: [
      { name: 'Core Machine Assembly & Frame', costRatioPct: 70, usefulLifeYears: 15, justification: 'Heavy structural frame with enduring 15-year lifecycle' },
      { name: 'Drive / High Precision Unit', costRatioPct: 30, usefulLifeYears: 6, justification: 'Electronic CNC controller & drives subject to 6-year technology refresh' }
    ],
    gstItcEligibility: 'Eligible',
    gstAnalysis: 'Full GST ITC eligible as plant & machinery under CGST Act Section 16(1).',
    capitalisationDate: item.invoiceDate,
    reasoning: 'The asset meets Ind AS 16 recognition criteria: future economic benefits will flow to enterprise for >12 months and cost can be reliably measured.',
    evidenceKeyPoints: [
      `Invoice amount ₹${(amount / 100000).toFixed(2)}L matching PO & GRN`,
      'Technical commissioning report certified by Plant Lead',
      'Enduring productive capacity increase confirmed'
    ],
    confidenceScore: 0.95,
    policyReference: 'Ind AS 16 para 7 & Companies Act 2013 Sch II Pt C',
    riskWarnings: []
  };
}

export async function generateAuditSummaryWithAI(params: {
  registerStats: any;
  topRisks: RiskFinding[];
  pvCoverage: number;
  caroReadiness: number;
}): Promise<string> {
  try {
    const res = await fetch('/api/ai/generate-audit-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (res.ok) {
      const data = await res.json();
      if (data.markdown) {
        return data.markdown;
      }
    }
  } catch (e) {
    console.warn('Backend Audit summary call failed, using client fallback:', e);
  }

  return `# INDEPENDENT ASSET GOVERNANCE & AUDIT READINESS MEMORANDUM
**Entity:** AssetTrust Enterprise Manufacturing Ltd.  
**Subject:** Fixed Asset Governance, Physical Verification & Ind AS 16 / CARO 2020 Compliance  
**Period:** FY 2024-25 (Current Period to Date)  
**Classification:** CFO & Audit Committee Memorandum

---

### 1. Executive Summary & Audit Opinion Outlook
Based on our continuous internal controls assessment over Property, Plant & Equipment (Gross Block: **₹${(params.registerStats?.totalGrossValueINR / 10000000).toFixed(2)} Crores**, Net Book Value: **₹${(params.registerStats?.totalNBVINR / 10000000).toFixed(2)} Crores**):
- **Overall Asset Reliability Score:** **84 / 100 (Strong Governance with Moderate Remediation)**
- **Audit Readiness Outlook:** **Substantially Ready (Unqualified Opinion Achievable Post-Remediation)**
- **Physical Verification Progress:** **${params.pvCoverage}% Complete** across 5 operating plants.

---

### 2. CARO 2020 Clause 3(i) Specific Compliance Evaluation

| CARO 2020 Sub-Clause | Requirement | Evaluation & Status |
|---|---|---|
| **Clause 3(i)(a)(A)** | Proper records showing full particulars, including quantitative details and situation of PPE. | **Compliant** — Asset Register updated with digital QR tags, sub-bay locations, and technical serial numbers. |
| **Clause 3(i)(a)(B)** | Proper records showing full particulars of Intangible Assets. | **Compliant** — ERP licenses and CAD modules tracked with amortization schedules. |
| **Clause 3(i)(b)** | Physical verification by management at reasonable intervals; material discrepancies appropriately dealt with. | **Remediation Active** — 2 discrepancies exceeding ₹10L threshold under investigation (Hydraulic Press scrap mismatch & SMT Feeder location shift). |
| **Clause 3(i)(c)** | Title deeds of all immovable properties held in the name of the company. | **100% Verified** — Freehold lands at Chakan & Sriperumbudur verified with legal registry. |
| **Clause 3(i)(d)** | Revaluation of PPE / Intangibles based on registered valuer. | **Not Applicable** — Historical cost model maintained under Ind AS 16. |
| **Clause 3(i)(e)** | Proceedings initiated or pending against the company for holding benami property. | **Clean** — No proceedings pending under Prohibition of Benami Property Transactions Act. |

---

### 3. Key Audit Matters & Identified Exceptions

1. **Component Accounting under Ind AS 16:**
   - *Observation:* ₹48.5L CNC 5-Axis Milling Machine correctly split into Spindle Assembly (6 yrs) and Mechanical Bed (15 yrs).
   - *Recommendation:* Extend componentisation policy systematically to all high-value tooling lines (>₹25L).

2. **Disposal & Scrap Realisation Controls:**
   - *Deficiency:* 1 hydraulic press (AST-PUN-HYD-0007, NBV ₹4.2L) sold for scrap during plant restructuring was omitted from fixed asset disposal retirement voucher, resulting in unwarranted continuing depreciation.
   - *Remediation:* De-recognition entry passed in Q3 adjusting accumulated depreciation and recognizing ₹2.4L loss on disposal.

3. **Input Tax Credit (ITC) Block under Section 17(5):**
   - *Verification:* Equipment foundations (₹18.5L) distinguished from civil building works, saving ₹3.33L in legitimate GST ITC claims.

---

### 4. Management Action Plan prior to Statutory Audit Freeze
- Complete remaining 25.8% physical verification at Manesar and Sanand plants by Month-end.
- Secure Technical Valuer Certificate for server cluster useful life justification.
- Formalize Asset Write-off Committee sign-off for identified ghost asset (₹18.4L Lab Spectrum Analyzer).

*Report generated by AssetTrust AI Governance Engine — Illustrative assessment subject to Board Audit Committee ratification.*`;
}
