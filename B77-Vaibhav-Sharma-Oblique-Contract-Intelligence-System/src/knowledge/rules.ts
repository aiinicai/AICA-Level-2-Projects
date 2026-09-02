import { ComplianceRule } from '../types/contract';
export type { ComplianceRule };

export const INDIAN_COMPLIANCE_RULES: ComplianceRule[] = [
  // Accounting & Financial Reporting
  {
    id: 'IND-AS-115',
    ruleName: 'Revenue from Contracts with Customers',
    title: 'Revenue Recognition & 5-Step Model (Ind AS 115)',
    jurisdiction: 'India (MCA / ICAI)',
    domain: 'Accounting',
    effectiveDate: '2018-04-01',
    statutoryReference: 'Ind AS 115 / AS 9 / AS 7',
    statutoryCitation: 'Ind AS 115 / AS 9 (Revenue Recognition)',
    applicabilitySummary: 'Applicable to entities preparing Ind AS financial statements. Requires 5-step model: Identify contract, identify performance obligations, determine transaction price, allocate transaction price, and recognize revenue as/when performance obligations are satisfied.',
    summary: 'Requires 5-step revenue recognition model. Demands careful unbundling of equipment supply from installation, AMC, and warranty services. Variable consideration (rebates, liquidated damages, milestone penalties) must be estimated and constrained.',
    triggerKeywords: ['milestone', 'retention', 'warranty', 'liquidated damages', 'performance obligation', 'supply and installation', 'turnkey', 'acceptance certificate'],
    keyVerificationPoints: [
      'Identification of distinct performance obligations (supply vs installation vs AMC)',
      'Variable consideration estimates (rebates, discounts, liquidated damages)',
      'Significant financing component if payment spans multiple reporting periods',
      'Contract assets vs Trade receivables distinction',
      'Assurance-type vs Service-type warranty obligations'
    ],
    caVerificationSteps: [
      'Evaluate whether equipment supply and installation are separate performance obligations.',
      'Estimate variable consideration including volume rebates and potential liquidated damages.',
      'Review contract asset vs trade receivable recognition upon milestone billings.'
    ],
    requiredEvidence: [
      'Client Acceptance / Completion Certificate',
      'Itemized price allocation breakdown',
      'Historical warranty claim records'
    ],
    managementQuestions: [
      'Can the customer benefit from the equipment independently of installation?',
      'What is the management estimate of achieving milestone delivery on schedule?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'IND-AS-37',
    ruleName: 'Provisions, Contingent Liabilities and Contingent Assets',
    title: 'Provisions, Contingent Liabilities & Onerous Contracts (Ind AS 37)',
    jurisdiction: 'India (MCA / ICAI)',
    domain: 'Financial Reporting',
    effectiveDate: '2016-04-01',
    statutoryReference: 'Ind AS 37 / AS 29',
    statutoryCitation: 'Ind AS 37 / AS 29 (Provisions & Contingencies)',
    applicabilitySummary: 'Governs recognition criteria for provisions (present obligation from past event, probable outflow, reliable estimate) and disclosure of contingent liabilities.',
    summary: 'Governs recognition of provisions for warranties, liquidated damages, onerous contracts, and pending claims. Demands disclosure of contingent liabilities where obligation is possible or cannot be reliably estimated.',
    triggerKeywords: ['liquidated damages', 'indemnity', 'penalty', 'warranty claim', 'defect liability', 'contingent liability'],
    keyVerificationPoints: [
      'Liquidated damages exposure from project delays',
      'Onerous contract evaluation',
      'Warranty provision estimation',
      'Indemnity and guarantee commitments'
    ],
    caVerificationSteps: [
      'Assess probability of outflow for delay penalties or liquidated damages.',
      'Determine warranty provision adequacy against historical defect rates.',
      'Ensure contingent liabilities are disclosed in Notes to Accounts.'
    ],
    requiredEvidence: [
      'Project status reports and delay correspondence',
      'Actuarial or engineering warranty defect estimate',
      'Legal counsel assessment of indemnity claims'
    ],
    managementQuestions: [
      'Has the project timeline slipped past the contractual deadline?',
      'Has the customer formally waived or reserved liquidated damages rights?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'IND-AS-109',
    ruleName: 'Financial Instruments - Recognition, Measurement & Impairment',
    title: 'Financial Instruments, ECL & Retention Discounting (Ind AS 109)',
    jurisdiction: 'India (MCA / ICAI)',
    domain: 'Accounting',
    effectiveDate: '2018-04-01',
    statutoryReference: 'Ind AS 109 / Ind AS 32 / AS 30',
    statutoryCitation: 'Ind AS 109 / Ind AS 32 (Financial Instruments)',
    applicabilitySummary: 'Governs initial recognition at fair value and subsequent measurement of financial assets/liabilities, expected credit loss (ECL), and retention money discounting.',
    summary: 'Governs fair value measurement and discounting of long-term retention receivables (e.g. 10% withheld for 24 months) and Expected Credit Loss (ECL) provisioning on extended credit terms.',
    triggerKeywords: ['retention money', 'security deposit', 'credit period', 'ECL', 'discounting', 'interest free advance'],
    keyVerificationPoints: [
      'Retention money discounting if retention spans multi-year warranty',
      'ECL matrix evaluation on extended credit balances',
      'Security deposits amortized cost recognition'
    ],
    caVerificationSteps: [
      'Calculate present value of retention receivable if deferred beyond 12 months.',
      'Apply ECL provision rate on overdue or 90+ day credit balances.',
      'Amortize discount to finance income over the retention period.'
    ],
    requiredEvidence: [
      'Retention release milestone schedule',
      'Customer credit rating and historical default matrix',
      'Discount rate computation benchmark'
    ],
    managementQuestions: [
      'When is the retention money realistically expected to be received?',
      'Is there any dispute impacting the recoverability of the retention asset?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'GST-SEC-15',
    ruleName: 'Value of Taxable Supply & Discount Treatment',
    title: 'GST Valuation & Post-Supply Discounts (CGST Section 15)',
    jurisdiction: 'India (CBIC)',
    domain: 'GST',
    effectiveDate: '2017-07-01',
    statutoryReference: 'Section 15 of CGST Act 2017',
    statutoryCitation: 'Section 15(3) CGST Act 2017 (Discounts & Valuation)',
    applicabilitySummary: 'Post-supply discounts must be established in terms of an agreement entered into at or before time of supply, linked to relevant invoices, and proportionate ITC reversed by recipient.',
    summary: 'Post-supply discounts (volume rebates, turnover incentives) are eligible for GST reduction ONLY if pre-agreed in writing prior to supply, linked to invoice numbers, and recipient reverses corresponding ITC.',
    triggerKeywords: ['volume rebate', 'post supply discount', 'incentive', 'credit note', 'turnover discount'],
    keyVerificationPoints: [
      'Pre-agreement of rebate in contract before supply',
      'Invoice linkage in financial vs GST credit notes',
      'ITC reversal confirmation from buyer'
    ],
    caVerificationSteps: [
      'Verify written contract date precedes invoice supply date for volume rebates.',
      'Check credit note GST compliance under Section 34 of CGST Act.',
      'Ensure commercial credit notes without GST are issued if conditions not met.'
    ],
    requiredEvidence: [
      'Executed commercial agreement stating rebate formula',
      'GSTR-1 credit note filings',
      'Recipient ITC reversal declaration'
    ],
    managementQuestions: [
      'Has the recipient confirmed reversal of ITC on discount credit notes?',
      'Is the rebate calculated strictly per the contractual tier slabs?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'GST-COMPOSITE-MIXED',
    ruleName: 'Composite Supply vs Mixed Supply',
    title: 'Composite vs Mixed Supply Bundling (CGST Section 8)',
    jurisdiction: 'India (CBIC)',
    domain: 'GST',
    effectiveDate: '2017-07-01',
    statutoryReference: 'Section 2(30), 2(74), Section 8 CGST Act 2017',
    statutoryCitation: 'Section 8 CGST Act 2017 (Composite vs Mixed Supply)',
    applicabilitySummary: 'Naturally bundled supplies with a principal supply are taxed at principal rate. Non-naturally bundled single-price supplies are taxed at highest applicable rate.',
    summary: 'Turnkey contracts bundling machinery, installation, freight, and maintenance must be analyzed for composite supply (taxable at principal supply rate) vs mixed supply (taxable at highest rate).',
    triggerKeywords: ['composite supply', 'mixed supply', 'turnkey supply', 'freight', 'installation and commissioning'],
    keyVerificationPoints: [
      'Bundling evaluation of equipment supply and erection',
      'Single lump-sum vs itemized billing structure',
      'Principal supply HSN rate alignment'
    ],
    caVerificationSteps: [
      'Identify principal supply (e.g. equipment supply vs works contract).',
      'Confirm whether contract constitutes works contract under Section 2(119).',
      'Verify GST rate applied on composite invoices.'
    ],
    requiredEvidence: [
      'Contract scope of work annexure',
      'Itemized price schedule and BoQ',
      'SAC / HSN classification review note'
    ],
    managementQuestions: [
      'Is installation integral to the functionality of the supplied machinery?',
      'Are invoices raised as single composite billing or split itemizations?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'GST-CIRCULAR-178',
    ruleName: 'Taxability of Liquidated Damages & Penalties',
    title: 'Liquidated Damages GST Taxability (CBIC Circular 178)',
    jurisdiction: 'India (CBIC)',
    domain: 'GST',
    effectiveDate: '2022-08-03',
    statutoryReference: 'CBIC Circular No. 178/10/2022-GST',
    statutoryCitation: 'CBIC Circular 178/10/2022-GST (Liquidated Damages)',
    applicabilitySummary: 'Clarifies that liquidated damages, penalties for delay/breach, or forfeiture of earnest money are payments towards damages and not consideration for agreeing to tolerate an act, hence NOT taxable.',
    summary: 'Liquidated damages and delay penalties deducted from vendor milestones are non-taxable compensation for contract breach. Charging or deducting GST on delay penalties is incorrect per CBIC guidance.',
    triggerKeywords: ['liquidated damages', 'delay penalty', 'forfeiture', 'breach of contract', 'deduction'],
    keyVerificationPoints: [
      'Compensation for breach vs consideration for optional service',
      'Debit note treatment for liquidated damages'
    ],
    caVerificationSteps: [
      'Ensure liquidated damages debit notes do not levy GST.',
      'Verify accounting classification of damages as other income / cost reduction rather than taxable supply.'
    ],
    requiredEvidence: [
      'Vendor debit note for liquidated damages',
      'Correspondence documenting milestone delay',
      'GSTR-1 and GSTR-3B reconciliation'
    ],
    managementQuestions: [
      'Was GST incorrectly charged or claimed on the penalty deduction?',
      'Has the vendor accepted the penalty deduction in writing?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'TDS-SEC-194C-194J',
    ruleName: 'TDS on Works Contract vs Technical Fees',
    title: 'TDS Classification: Works Contract (194C) vs Technical Fees (194J)',
    jurisdiction: 'India (Income Tax Department)',
    domain: 'TDS',
    effectiveDate: '1961-04-01',
    statutoryReference: 'Section 194C vs 194J Income Tax Act 1961',
    statutoryCitation: 'Section 194C / 194J Income Tax Act 1961',
    applicabilitySummary: 'Works contracts involving supply of labour/work fall under 194C (1%/2%). Professional or technical consultancy fees fall under 194J (2%/10%).',
    summary: 'Turnkey contracts often bundle civil works/fabrication (194C at 2%) with specialized engineering, supervision, or software design (194J at 2% or 10%). Incorrect classification leads to TDS default notices.',
    triggerKeywords: ['TDS', '194C', '194J', 'works contract', 'technical services', 'consultancy', 'withholding'],
    keyVerificationPoints: [
      'Fabrication works vs engineering consultancy segregation',
      'Dual TDS rate verification on composite contracts'
    ],
    caVerificationSteps: [
      'Examine scope of work to separate physical execution from professional engineering.',
      'Verify TDS deduction at appropriate rates under 194C / 194J / 194Q.',
      'Check timely deposit of TDS and quarterly Form 26Q filings.'
    ],
    requiredEvidence: [
      'Vendor PAN and TAN verification',
      'Split billing breakdown for supply vs service',
      'Form 26AS / AIS reconciliation'
    ],
    managementQuestions: [
      'Is technical engineering consultancy billed separately from execution?',
      'Has lower withholding certificate under Section 197 been provided by vendor?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'MSME-SEC-15-43BH',
    ruleName: 'MSME 45-Day Payment Mandate & Sec 43B(h) Disallowance',
    title: 'MSME Payment Ceiling & Sec 43B(h) Tax Disallowance',
    jurisdiction: 'India (MSMED Act / CBDT)',
    domain: 'MSME',
    effectiveDate: '2023-04-01 (AY 2024-25)',
    statutoryReference: 'Section 15/16/22 MSMED Act 2006 & Section 43B(h) Income Tax Act',
    statutoryCitation: 'Section 43B(h) Income Tax Act & Section 15 MSMED Act',
    applicabilitySummary: 'Payments to Micro/Small enterprises must be made within 45 days. Unpaid dues at year-end beyond 45 days are disallowed as tax deductions in year of accrual.',
    summary: 'Contractual payment terms exceeding 45 days (e.g. 60 or 90 days) with registered Micro or Small suppliers are overridden by Section 15 of MSMED Act. Unpaid dues at year end are added back to taxable income under Sec 43B(h) + 3x compound monthly interest.',
    triggerKeywords: ['MSME', 'Udyam', '43B(h)', 'credit period', '45 days', 'delayed payment', 'interest'],
    keyVerificationPoints: [
      'Contractual 90-day credit period void against Micro/Small suppliers',
      '3x compound interest calculation under Section 16',
      'Udyam enterprise classification verification'
    ],
    caVerificationSteps: [
      'Obtain and verify vendor Udyam registration certificate (Micro/Small vs Medium).',
      'Compute MSME dues outstanding as of March 31 for Section 43B(h) tax disallowance.',
      'Accrue interest liability under Section 16 of MSMED Act in the books.'
    ],
    requiredEvidence: [
      'Vendor Udyam Registration Certificate',
      'AP Aging report with invoice receipt dates',
      'Bank payment confirmation timestamps'
    ],
    managementQuestions: [
      'Has the vendor provided an active Udyam certificate showing Micro or Small status?',
      'Will all invoices from this supplier be cleared within 45 days of invoice date?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'COMPANIES-ACT-188',
    ruleName: 'Related Party Transactions & Approval Framework',
    title: 'Related Party Contracts & Arm’s Length Compliance (Sec 188)',
    jurisdiction: 'India (MCA)',
    domain: 'Related Party',
    effectiveDate: '2014-04-01',
    statutoryReference: 'Section 188, 177, 184 Companies Act 2013 & Ind AS 24',
    statutoryCitation: 'Section 188 Companies Act 2013 / Ind AS 24 (Related Parties)',
    applicabilitySummary: 'Related party transactions require Audit Committee and Board approval unless on arm\'s length basis in ordinary course of business. Shareholder approval required if exceeding turnover thresholds.',
    summary: 'Contracts with entities having common directors, promoters, or subsidiaries require prior Audit Committee approval and robust arm\'s length benchmark documentation to avoid Section 188 penalties and CARO 2020 qualifications.',
    triggerKeywords: ['related party', 'common director', 'arm length', 'ordinary course', 'Section 188', 'Audit Committee'],
    keyVerificationPoints: [
      'Common directorship or shareholding identification',
      'Arm\'s length pricing documentation and comparable market quotes',
      'Audit committee and Board resolution minutes'
    ],
    caVerificationSteps: [
      'Check director disclosure in Form MBP-1 for common interest.',
      'Verify prior Audit Committee approval under Section 177.',
      'Inspect arm\'s length price justification benchmarking file.'
    ],
    requiredEvidence: [
      'Audit Committee & Board Approval Resolutions',
      'Form MBP-1 / MBP-4 Register of Contracts',
      'Arm\'s Length Pricing Comparable Quotations'
    ],
    managementQuestions: [
      'Was this contract approved by the Audit Committee prior to execution?',
      'What documentary evidence supports the arm’s length nature of the contract pricing?'
    ],
    lastReviewedDate: '2026-04-01'
  },
  {
    id: 'AUDIT-CARO-SA',
    ruleName: 'Statutory Audit Assertions & CARO 2020 Reporting',
    title: 'Audit Assertions, Cut-Off & CARO 2020 Verification',
    jurisdiction: 'India (ICAI / NFRA)',
    domain: 'Audit',
    effectiveDate: '2020-04-01',
    statutoryReference: 'CARO 2020 & Standards on Auditing (SA 240, 315, 500, 505)',
    statutoryCitation: 'CARO 2020 & SA 500 / SA 505 (Audit Evidence)',
    applicabilitySummary: 'Auditor must obtain sufficient appropriate audit evidence on cut-off, unbilled revenue, milestone verification, external confirmations, and contingent liability disclosures.',
    summary: 'Demands rigorous verification of CWIP capitalization, unbilled milestone revenues, external balance confirmations (SA 505) for retention money, and CARO 2020 reporting on statutory dues and title deeds.',
    triggerKeywords: ['audit', 'cut off', 'confirmation', 'CARO', 'CWIP', 'substantive testing'],
    keyVerificationPoints: [
      'Cut-off testing around March 31 reporting date',
      'Direct external confirmation under SA 505 for retention & advances',
      'CWIP readiness and depreciation commencement date'
    ],
    caVerificationSteps: [
      'Perform cut-off procedures on milestone invoicing around balance sheet date.',
      'Send direct balance confirmation requests for retention money receivables.',
      'Verify trial run expenses are properly treated under Ind AS 16 / AS 10.'
    ],
    requiredEvidence: [
      'Third-party external balance confirmation',
      'Engineer readiness and commissioning certificates',
      'Trial run production logs and cost sheets'
    ],
    managementQuestions: [
      'Has the asset commenced commercial production before the reporting year-end?',
      'Are there any unrecorded customer claims or delay liabilities?'
    ],
    lastReviewedDate: '2026-04-01'
  }
];
