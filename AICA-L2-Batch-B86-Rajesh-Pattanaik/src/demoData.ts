import { VerificationReport } from './types';

export const DEMO_CASE = {
  title: "Section 44AB Audit Exemption & Cross-Domain Compliance Case",
  subtitle: "AI Correctly Evaluates Tax Audit But Misses Mandatory GST e-Invoicing & TDS Liabilities",
  question: `A retail trading proprietary concern, M/s Odyssey Retailers (Proprietor: Mr. Aniket Sharma), achieved an annual gross turnover of ₹8.40 Crore during Previous Year 2023-24 (Assessment Year 2024-25).
- Transaction Channels: 98.2% of all business receipts and 98.5% of all business expenditure were executed via account payee bank transfers (NEFT/RTGS/IMPS/UPI); cash transactions accounted for only ~1.5%.
- The business has not opted for presumptive taxation under Section 44AD in previous years.

The client asks:
1. Is a mandatory Tax Audit required under Section 44AB of the Income-tax Act, 1961 for AY 2024-25?
2. What are the immediate compliance, filing, and reporting obligations for the firm?`,

  aiAnswer: `No, a mandatory tax audit under Section 44AB of the Income-tax Act, 1961 is NOT required for M/s Odyssey Retailers for AY 2024-25.

Legal Basis & Analysis:
1. Under Section 44AB(a), the standard turnover threshold for mandatory tax audit in business is ₹1 Crore.
2. However, under the proviso to Section 44AB(a) enacted by the Finance Act, where aggregate cash receipts and aggregate cash payments each do not exceed 5% of total receipts and payments respectively, the audit threshold is enhanced from ₹1 Crore to ₹10 Crore.
3. Since M/s Odyssey Retailers conducts ~98.5% of its transactions digitally (cash accounts for only 1.5%, well within the 5% statutory allowance), the applicable turnover ceiling is ₹10 Crore.
4. Because the turnover of ₹8.40 Crore is below ₹10 Crore, the assessee is completely exempt from tax audit under Section 44AB.
5. The firm can directly file its normal Income Tax Return in Form ITR-3 on or before the regular non-audit due date (31st July 2024) without requiring any Tax Audit Report (Form 3CB-3CD) or Chartered Accountant certification. No additional compliance or reporting is necessary.`,

  sourceMaterial: `PRIMARY AUTHORITATIVE STATUTORY EXTRACTS:

1. THE INCOME-TAX ACT, 1961 — SECTION 44AB
"Every person,—
(a) carrying on business shall, if his total sales, turnover or gross receipts, as the case may be, in business exceed or exceeds one crore rupees in any previous year:
Provided that in the case of a person whose—
(a) aggregate of all amounts received including amount received for sales, turnover or gross receipts during the previous year, in cash, does not exceed five per cent of the said amount; and
(b) aggregate of all payments made including amount incurred for expenditure, in cash, during the previous year does not exceed five per cent of the said payment,
this clause shall have effect as if for the words 'one crore rupees', the words 'ten crore rupees' had been substituted.
Explanation.—For the purposes of this section, payment or receipt by a cheque drawn on a bank or by a bank draft, which is not account payee, shall be deemed to be receipt or payment, as the case may be, in cash."

2. THE CENTRAL GOODS AND SERVICES TAX ACT, 2017 & CGST RULES, 2017
Notification No. 10/2023-Central Tax, dated 10th May, 2023 (Amending Rule 48(4)):
"In exercise of the powers conferred by sub-rule (4) of rule 48 of the Central Goods and Services Tax Rules, 2017, the Government... notifies that a registered person whose aggregate turnover in any preceding financial year from 2017-18 onwards exceeds five crore rupees, as a class of registered person who shall prepare invoice and other prescribed documents in terms of sub-rule (4) of rule 48 in respect of supply of goods or services or both to a registered person (B2B) or for exports, with effect from the 1st day of August, 2023.
Rule 48(5): Every invoice issued by a person to whom sub-rule (4) applies in any manner other than the manner specified in the said sub-rule shall not be treated as an invoice.
Section 122(1): Failure to issue invoice in accordance with provisions attracts a penalty of ten thousand rupees or an amount equivalent to the tax evaded, whichever is higher (subject to section 122(3) general penalty up to twenty-five thousand rupees)."

3. THE INCOME-TAX ACT, 1961 — SECTION 194C & SECTION 194J (TDS LIABILITIES)
"Section 194C(1) / Section 194J(1) Second Proviso:
Provided further that an individual or a Hindu undivided family, whose total sales, gross receipts or turnover from business or profession carried on by him exceed one crore rupees in case of business or fifty lakh rupees in case of profession during the financial year immediately preceding the financial year in which such sum is credited or paid, shall be liable to deduct tax under this section.
[Note: The statutory threshold for individual TDS deduction liability remains ₹1 Crore and is NOT elevated to ₹10 Crore under Section 194C/194J.]
Section 40(a)(ia): 30% of any sum payable to a resident on which tax is deductible at source shall be disallowed in computing business income if tax is not deducted or not paid before the due date specified in section 139(1)."

4. THE INCOME-TAX ACT, 1961 — SECTION 139(1) (DUE DATES)
Explanation 2(a) to Section 139(1): Due date for an assessee whose accounts are not required to be audited is 31st July of the assessment year.`
};

export const DEMO_VERIFICATION_REPORT: VerificationReport = {
  isLimitedVerification: false,
  sourceReliability: 'Primary Authoritative',
  sourceReliabilityDetails: 'Grounded in Primary Acts and Notifications: Income-tax Act, 1961 (Sec 44AB, 194C, 194J, 139) and CGST Act/Rules (Notification No. 10/2023-CT).',
  overallStatus: 'Generally Supported — Verify',
  verificationScore: 74,
  scoreExplanation: 'This score reflects support, consistency and completeness against the supplied information and sources. It is NOT a probability of legal correctness.',
  scoreBreakdown: {
    sourceSupport: 'High',
    completeness: 'Partial',
    professionalRisk: 'Elevated'
  },
  executiveVerdict: 'The AI answered the primary question on Section 44AB correctly (turnover of ₹8.40 Cr with <5% cash is exempt from Section 44AB tax audit). However, the AI committed critical cross-domain omissions: it advised that "no additional compliance is necessary", overlooking mandatory GST e-Invoicing under Rule 48(4) (triggered at ₹5 Cr turnover) and continuing TDS deduction obligations under Section 194C/194J (triggered at ₹1 Cr turnover for individuals).',
  
  keyFacts: [
    { id: 'kf-1', fact: 'Annual turnover is ₹8.40 Crore for FY 2023-24 (AY 2024-25)', category: 'Turnover' },
    { id: 'kf-2', fact: 'Digital transactions account for 98.2% receipts and 98.5% payments (cash is only ~1.5%)', category: 'Payment Mode' },
    { id: 'kf-3', fact: 'Legal constitution is an individual proprietary concern (Mr. Aniket Sharma)', category: 'Entity Constitution' },
    { id: 'kf-4', fact: 'Business has not claimed presumptive taxation under Section 44AD in preceding years', category: 'Tax History' }
  ],

  applicableDomains: [
    {
      domain: 'Income Tax (Tax Audit)',
      whyItApplies: 'Proprietorship turnover is ₹8.40 Cr, which sits between the ₹1 Cr general limit and the ₹10 Cr digital limit.',
      relevantProvision: 'Section 44AB(a) Proviso',
      impact: 'Exempts the firm from obtaining Form 3CB-3CD audit report because cash transactions are <= 5%.',
      aiAddressedStatus: 'Addressed',
      verificationRequired: 'Verify that non-account payee cheques or bearer drafts do not breach the 5% threshold.'
    },
    {
      domain: 'GST / Indirect Tax',
      whyItApplies: 'Aggregate annual turnover exceeds ₹5 Crore in Previous Year 2023-24.',
      relevantProvision: 'Rule 48(4) of CGST Rules, 2017 & Notification No. 10/2023-Central Tax',
      impact: 'Mandatory e-Invoicing for all B2B supplies effective from 1st August 2023. Non-compliance invalidates invoices.',
      aiAddressedStatus: 'Missed / Omitted',
      verificationRequired: 'Verify whether the firm has registered on the IRP portal and is generating IRN for B2B invoices.'
    },
    {
      domain: 'TDS / TCS Compliance',
      whyItApplies: 'Individual carrying on business whose turnover exceeded ₹1 Crore in the financial year.',
      relevantProvision: 'Section 194C, 194J, 194Q & Section 40(a)(ia) of Income-tax Act, 1961',
      impact: 'Firm is mandatorily required to deduct TDS on contractor/professional payments despite Section 44AB audit exemption.',
      aiAddressedStatus: 'Missed / Omitted',
      verificationRequired: 'Audit TAN registration, monthly TDS deductions, quarterly Form 26Q filings, and check Section 40(a)(ia) disallowance.'
    },
    {
      domain: 'Auditing & Standards on Auditing',
      whyItApplies: 'Cash vs Digital classification under the Explanation to Section 44AB.',
      relevantProvision: 'Explanation to Section 44AB & ICAI Guidance Note on Tax Audit',
      impact: 'Requires verification of bank statements to ensure crossed cheques / non-account payee drafts are treated as cash.',
      aiAddressedStatus: 'Partially Addressed',
      verificationRequired: 'Obtain management representation and perform sample checks of bank clearing instruments.'
    }
  ],

  supportedClaims: [
    {
      id: 'sup-1',
      claim: 'Baseline turnover limit for business tax audit under Section 44AB(a) is ₹1 Crore.',
      status: 'SUPPORTED',
      sourceEvidence: 'carrying on business shall, if his total sales, turnover or gross receipts... exceed or exceeds one crore rupees in any previous year',
      analysis: 'Accurately quotes the baseline statutory limit under Section 44AB(a).',
      professionalImplication: 'Establishes the default statutory benchmark before considering digital relaxation provisos.'
    },
    {
      id: 'sup-2',
      claim: 'Proviso to Section 44AB(a) substitutes ₹10 Crore for ₹1 Crore where cash transactions do not exceed 5%.',
      status: 'SUPPORTED',
      sourceEvidence: 'Provided that in the case of a person whose aggregate of all amounts received... and payments made... in cash, does not exceed five per cent... this clause shall have effect as if for the words \'one crore rupees\', the words \'ten crore rupees\' had been substituted.',
      analysis: 'Correctly applies the active ₹10 Crore threshold for entities with <= 5% cash receipts and payments.',
      professionalImplication: 'Firm turnover of ₹8.40 Crore qualifies for relief from Section 44AB(a) tax audit.'
    },
    {
      id: 'sup-3',
      claim: 'Due date for filing return of income for non-audit assessees is 31st July of the assessment year.',
      status: 'SUPPORTED',
      sourceEvidence: 'Explanation 2(a) to Section 139(1): Due date for an assessee whose accounts are not required to be audited is 31st July.',
      analysis: 'Correctly identifies the general filing deadline under Section 139(1).',
      professionalImplication: 'ITR-3 must be filed by 31st July 2024 to avoid late fees under Section 234F and interest under Section 234A.'
    }
  ],

  questionableClaims: [
    {
      id: 'ques-1',
      claim: 'Assessee is completely exempt from tax audit and no additional compliance or reporting is necessary.',
      status: 'REQUIRES VERIFICATION',
      sourceEvidence: 'Not established by the supplied sources. In fact, directly contradicted by GST Notification 10/2023 and Section 194C/194J.',
      analysis: 'The AI inappropriately equated exemption from Section 44AB with complete exemption from all business compliances.',
      professionalImplication: 'Failing to alert the client to other statutory regimes exposes the practitioner to professional negligence.',
      missingEvidenceNotice: 'Omitted connected statutory obligations.'
    }
  ],

  potentialErrors: [
    {
      id: 'err-1',
      errorType: 'statutory_misstatement',
      statementInAIAnswer: 'No additional compliance or reporting is necessary. You can file your ITR-3 without any audit report or CA certification.',
      contradictingSourceEvidence: 'Notification No. 10/2023-Central Tax (Mandatory e-invoicing for turnover > ₹5 Cr) and Section 194C/194J Second Proviso (Mandatory TDS for individual turnover > ₹1 Cr).',
      analysis: 'The statement that "no additional compliance is necessary" is false and dangerous. While Section 44AB audit is exempt, mandatory GST e-invoicing and TDS deduction obligations remain legally enforceable.',
      professionalImplication: 'Client could face substantial financial penalties under Section 122 of CGST Act and 30% expenditure disallowance under Section 40(a)(ia) of the Income-tax Act.',
      severity: 'high'
    }
  ],

  missedIssues: [
    {
      id: 'miss-1',
      domain: 'GST / Indirect Tax',
      issueTitle: 'Mandatory GST e-Invoicing under Rule 48(4)',
      applicableProvision: 'Rule 48(4) & (5) of CGST Rules, 2017 read with Notification No. 10/2023-Central Tax',
      description: 'Since M/s Odyssey Retailers has an annual turnover of ₹8.40 Crore (exceeding the ₹5 Crore threshold), it is mandatorily required to issue e-invoices with IRN and QR code for all B2B supplies.',
      whyMissedByAI: 'AI suffered from siloed domain vision: it focused solely on the specific Income Tax section asked in the prompt and neglected indirect tax consequences triggered by the factual turnover.',
      consequenceOrPenalty: 'Invoices issued without IRN are deemed non-existent under Rule 48(5). Attracts a penalty up to ₹25,000 per invoice under Section 122, and recipients cannot claim Input Tax Credit (ITC).',
      severity: 'high',
      actionRequired: 'Ensure the firm integrates with the Invoice Registration Portal (IRP) immediately and generates IRNs for all B2B supplies.'
    },
    {
      id: 'miss-2',
      domain: 'TDS / TCS Compliance',
      issueTitle: 'Mandatory TDS Deduction Liability for Individuals (Turnover > ₹1 Crore)',
      applicableProvision: 'Second Proviso to Section 194C(1) and Section 194J(1), Section 194Q & Section 40(a)(ia)',
      description: 'Under the Income-tax Act, an individual carrying on business whose turnover exceeds ₹1 Crore in the preceding financial year is legally required to deduct TDS on payments to contractors (194C) and professionals (194J). This threshold was NOT elevated to ₹10 Crore.',
      whyMissedByAI: 'AI assumed that exemption from Section 44AB tax audit simultaneously exempted the entity from withholding tax responsibilities.',
      consequenceOrPenalty: '30% disallowance of all non-deducted expenditures under Section 40(a)(ia), plus mandatory interest at 1% / 1.5% per month under Section 201(1A), and penalty under Section 271C.',
      severity: 'high',
      actionRequired: 'Verify that the firm holds an active TAN, has deducted TDS on applicable expense heads, and has remitted dues into the government treasury.'
    },
    {
      id: 'miss-3',
      domain: 'Income Tax (Statutory Due Diligence)',
      issueTitle: 'Instrument Verification under Explanation to Section 44AB',
      applicableProvision: 'Explanation to Section 44AB of Income-tax Act, 1961',
      description: 'The Explanation specifies that payment or receipt by a cheque or bank draft which is NOT an account payee instrument is deemed as cash.',
      whyMissedByAI: 'AI accepted raw client percentages (1.5% cash) as uncontroverted legal facts without highlighting the statutory verification condition.',
      consequenceOrPenalty: 'If bearer or crossed cheques push total cash receipts or payments beyond 5%, the ₹10 Crore concession vanishes and the ₹1 Crore limit applies retroactively, triggering Section 271B penalty (₹1.5 Lakhs).',
      severity: 'medium',
      actionRequired: 'Review bank deposit slips and clearing records to verify that all banking transactions were strictly through account payee instruments or electronic clearing systems.'
    }
  ],

  sourceEvidenceList: [
    {
      id: 'ev-1',
      aiClaim: 'Section 44AB tax audit is not mandatory for turnover of ₹8.40 Cr with 1.5% cash transactions.',
      status: 'SUPPORTED',
      sourceHierarchy: 'PRIMARY / AUTHORITATIVE',
      sourceEvidence: 'aggregate of all amounts received... in cash, does not exceed five per cent... and aggregate of all payments made... does not exceed five per cent... words \'ten crore rupees\' had been substituted.',
      analysis: 'Statute directly corroborates that ₹10 Crore is the threshold for businesses operating with <= 5% cash.',
      professionalImplication: 'Section 44AB audit is indeed not attracted on this specific turnover parameter.'
    },
    {
      id: 'ev-2',
      aiClaim: 'No additional compliance or reporting is necessary for this business.',
      status: 'POTENTIAL ERROR',
      sourceHierarchy: 'PRIMARY / AUTHORITATIVE',
      sourceEvidence: 'Notification No. 10/2023-Central Tax: registered person whose aggregate turnover... exceeds five crore rupees... shall prepare invoice in terms of sub-rule (4) of rule 48. Rule 48(5): shall not be treated as an invoice.',
      analysis: 'Direct statutory conflict. With ₹8.40 Cr turnover, mandatory GST e-invoicing is triggered. Advising no additional compliance misleads the client.',
      professionalImplication: 'Exposure to severe operational disruption and statutory penalties under CGST Act.'
    },
    {
      id: 'ev-3',
      aiClaim: 'Firm can file normal ITR-3 by 31st July 2024.',
      status: 'SUPPORTED',
      sourceHierarchy: 'PRIMARY / AUTHORITATIVE',
      sourceEvidence: 'Explanation 2(a) to Section 139(1): In the case of an assessee other than an assessee whose accounts are required to be audited... 31st day of July of the assessment year.',
      analysis: 'Accurately identifies the statutory due date for non-corporate, non-audit assessees.',
      professionalImplication: 'Sets the statutory target date for return filing.'
    },
    {
      id: 'ev-4',
      aiClaim: 'Omission of TDS deduction liabilities under Section 194C / 194J.',
      status: 'NOT ESTABLISHED BY SUPPLIED SOURCES',
      sourceHierarchy: 'PRIMARY / AUTHORITATIVE',
      sourceEvidence: 'Section 194C/194J Proviso: an individual or a Hindu undivided family, whose total sales, gross receipts or turnover... exceed one crore rupees... shall be liable to deduct tax.',
      analysis: 'AI made no mention of withholding tax provisions which are legally active due to turnover exceeding ₹1 Crore.',
      professionalImplication: 'High exposure to disallowance under Section 40(a)(ia).'
    }
  ],

  consequencesAndPenalties: [
    {
      id: 'cp-1',
      area: 'GST / Indirect Tax',
      provision: 'Rule 48(5) & Section 122(1) / 122(3) of CGST Act, 2017',
      riskLevel: 'Critical',
      description: 'Failure to issue e-Invoices with IRN for B2B transactions when turnover exceeds ₹5 Crore.',
      statutoryPenaltyOrImpact: 'Penalty of 100% of tax evaded or ₹10,000 (whichever is higher), plus up to ₹25,000 general penalty per invoice. Invoices are invalid; buyer loses ITC.'
    },
    {
      id: 'cp-2',
      area: 'Income Tax (TDS)',
      provision: 'Section 40(a)(ia) & Section 201(1A) of Income-tax Act, 1961',
      riskLevel: 'Critical',
      description: 'Failure to deduct or deposit TDS on contractor and professional payments.',
      statutoryPenaltyOrImpact: '30% of total expenditure disallowed from business income; penal interest at 1% - 1.5% per month; potential penalty under Section 271C.'
    },
    {
      id: 'cp-3',
      area: 'Income Tax (Threshold Audit)',
      provision: 'Section 271B of Income-tax Act, 1961',
      riskLevel: 'Moderate',
      description: 'If non-account payee instruments push cash component above 5%, audit becomes mandatory.',
      statutoryPenaltyOrImpact: 'Penalty of 0.5% of gross turnover (capped at ₹1,50,000) for failure to obtain tax audit report.'
    }
  ],

  recommendedProfessionalActions: [
    'Confirm that all digital banking transactions were executed exclusively through account payee cheques or electronic clearing mechanisms as per the Explanation to Section 44AB.',
    'Enroll the client immediately on the GST Invoice Registration Portal (IRP) and verify compliance with mandatory e-Invoicing under Notification No. 10/2023-Central Tax.',
    'Obtain the trial balance to review all contractor (194C) and professional fees (194J) to ensure TDS has been correctly deducted and deposited to avoid Section 40(a)(ia) disallowances.',
    'Verify applicability of Section 194Q / Section 206C(1H) if aggregate purchase or sale of goods with any single party exceeds ₹50 Lakhs.',
    'Prepare and file Form ITR-3 well before the 31st July 2024 statutory deadline.'
  ],

  professionalRelianceWarning: 'CA VerifyAI is an AI-assisted professional verification and risk-identification tool. It does not replace professional judgement, authoritative legal research or independent verification.',
  verificationTimestamp: new Date().toISOString()
};
