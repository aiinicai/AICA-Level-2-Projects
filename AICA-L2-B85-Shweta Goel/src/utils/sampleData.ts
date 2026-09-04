import { 
  InvoiceReviewData, 
  GSTComplianceData, 
  BankStatementData, 
  TDSAnalysisData,
  CAFirmProfile
} from '../types';

export interface SampleDocumentItem {
  id: string;
  name: string;
  module: 'invoice' | 'gst' | 'bank' | 'tds';
  description: string;
  tag: string;
  risk: 'compliant' | 'warning' | 'critical';
  svgPreview: string;
  size: number;
  mimeType: string;
  sampleData: InvoiceReviewData | GSTComplianceData | BankStatementData | TDSAnalysisData;
}

// Sample 1: Invoice Review with Math Mismatch (Critical Alert)
export const SAMPLE_INVOICE_MATH_MISMATCH: InvoiceReviewData = {
  vendorName: 'Bharat Hardware & Enterprise Supplies Pvt Ltd',
  vendorGSTIN: '27AABCB1234F1Z5',
  receiverName: 'Apex Precision Engineering Ltd',
  receiverGSTIN: '27AAECP9876K1Z2',
  invoiceNumber: 'BHE/2024-25/0892',
  invoiceDate: '2024-11-14',
  dueDate: '2024-12-14',
  placeOfSupply: 'Maharashtra (27)',
  taxableAmount: 185000,
  cgstAmount: 16650, // 9%
  sgstAmount: 16650, // 9%
  igstAmount: 0,
  cessAmount: 0,
  totalCalculatedTax: 33300,
  totalInvoiceAmount: 224500, // Stated on invoice is 2,24,500, but 185000 + 33300 = 218300!
  computedTotal: 218300,
  mathDiscrepancy: 6200,
  isMathValid: false,
  lineItems: [
    {
      id: 'li-1',
      description: 'Industrial Stainless Steel Fasteners Grade 316',
      hsnSac: '7318',
      quantity: 500,
      unit: 'Kg',
      unitPrice: 220,
      taxableValue: 110000,
      gstRatePercent: 18,
      cgst: 9900,
      sgst: 9900,
      igst: 0,
      total: 129800
    },
    {
      id: 'li-2',
      description: 'Heavy Duty Pneumatic Actuators',
      hsnSac: '8412',
      quantity: 15,
      unit: 'Nos',
      unitPrice: 5000,
      taxableValue: 75000,
      gstRatePercent: 18,
      cgst: 6750,
      sgst: 6750,
      igst: 0,
      total: 88500
    }
  ],
  riskStatus: 'critical',
  auditIssues: [
    {
      type: 'math_error',
      severity: 'high',
      title: 'Gross Invoice Total Arithmetic Mismatch (₹6,200 Variance)',
      message: 'The stated invoice total of ₹2,24,500 does not match Taxable Value (₹1,85,000) + CGST (₹16,650) + SGST (₹16,650) = ₹2,18,300. Possible unbilled item or manual billing arithmetic error.',
      field: 'totalInvoiceAmount'
    },
    {
      type: 'tax_mismatch',
      severity: 'medium',
      title: 'Tax Ledger Integrity Verification',
      message: 'Individual line item tax sums (₹19,800 + ₹13,500 = ₹33,300) match the tax summary, but the bottom-line invoice total has an unallocated difference of ₹6,200.',
      field: 'totalCalculatedTax'
    }
  ],
  confidenceScore: 0.98,
  summary: 'CRITICAL AUDIT ALERT: Invoice contains an arithmetic reconciliation error of ₹6,200. Stated total ₹2,24,500 exceeds calculated sum of items and taxes (₹2,18,300). Input Tax Credit (ITC) reconciliation in GSTR-3B requires vendor clarification and corrected credit note.',
  suggestedAccountHead: {
    ledgerName: 'Factory Consumables & Mechanical Hardware Spares',
    accountCategory: 'Direct Operating Expenses (Plant & Machinery Maintenance)',
    natureOfExpense: 'Revenue Expenditure',
    costCenter: 'Plant Maintenance / Production Unit 1',
    accountingRationale: 'Line items cover Grade 316 Stainless Steel Fasteners (HSN 7318) and Heavy Duty Pneumatic Actuators (HSN 8412) utilized in machine overhaul and plant operations. Classified as operational revenue expenditure deductible under Section 37(1).',
    recommendedJournalEntry: {
      debitLedger: 'Consumables & Hardware Spares A/c',
      debitAmount: 185000,
      gstInputLedger: 'Input CGST (9%) & Input SGST (9%) Ledgers',
      gstInputAmount: 33300,
      creditLedger: 'Bharat Hardware & Enterprise Supplies Pvt Ltd (Sundry Creditor)',
      creditAmount: 218300
    }
  }
};

// Sample 2: Clean Invoice Review
export const SAMPLE_INVOICE_CLEAN: InvoiceReviewData = {
  vendorName: 'Zenith Cloud & IT Infrastructure LLP',
  vendorGSTIN: '29AAHFZ4567M1Z8',
  receiverName: 'Apex Precision Engineering Ltd',
  receiverGSTIN: '27AAECP9876K1Z2',
  invoiceNumber: 'ZIT/24-25/1102',
  invoiceDate: '2024-12-05',
  dueDate: '2025-01-04',
  placeOfSupply: 'Maharashtra (27)',
  taxableAmount: 350000,
  cgstAmount: 0,
  sgstAmount: 0,
  igstAmount: 63000, // 18% Inter-state
  cessAmount: 0,
  totalCalculatedTax: 63000,
  totalInvoiceAmount: 413000,
  computedTotal: 413000,
  mathDiscrepancy: 0,
  isMathValid: true,
  lineItems: [
    {
      id: 'li-c1',
      description: 'Dedicated Cloud Server Hosting & Enterprise Backup (Annual)',
      hsnSac: '998315',
      quantity: 1,
      unit: 'Year',
      unitPrice: 350000,
      taxableValue: 350000,
      gstRatePercent: 18,
      cgst: 0,
      sgst: 0,
      igst: 63000,
      total: 413000
    }
  ],
  riskStatus: 'compliant',
  auditIssues: [
    {
      type: 'info',
      severity: 'low',
      title: 'Full Arithmetic Reconciliation Passed',
      message: 'Taxable amount (₹3,50,000) + IGST 18% (₹63,000) perfectly matches stated total ₹4,13,000. HSN/SAC 998315 verified.',
      field: 'isMathValid'
    }
  ],
  confidenceScore: 0.99,
  summary: 'CLEAN INVOICE: All math validations, GST rates (18% IGST), SAC codes (998315), and vendor/buyer GSTINs are verified with zero arithmetic discrepancy.',
  suggestedAccountHead: {
    ledgerName: 'Software Subscriptions & Cloud Hosting Charges',
    accountCategory: 'Indirect Expenses (IT & Administrative Overhead)',
    natureOfExpense: 'Revenue Expenditure',
    costCenter: 'IT Infrastructure & Enterprise DevOps',
    accountingRationale: 'SAC 998315 represents recurring enterprise cloud hosting and automated offsite backup infrastructure services. Classified under Operating IT Overhead with 100% allowable business deduction under Section 37(1). Subject to Section 194J(a) TDS review if not already deducted.',
    recommendedJournalEntry: {
      debitLedger: 'Software Subscriptions & Cloud Hosting A/c',
      debitAmount: 350000,
      gstInputLedger: 'Input IGST Ledger @ 18%',
      gstInputAmount: 63000,
      creditLedger: 'Zenith Cloud & IT Infrastructure LLP (Sundry Creditor)',
      creditAmount: 413000
    }
  }
};

// Sample 3: GST Compliance with Place of Supply Mismatch & ITC Blockage
export const SAMPLE_GST_COMPLIANCE_POS_ERROR: GSTComplianceData = {
  vendorName: 'Mahindra Logistics Tech Hub Pvt Ltd',
  vendorGSTIN: '27AAACM5432E1Z7', // Maharashtra (27)
  vendorState: 'Maharashtra',
  vendorStateCode: '27',
  isVendorGSTINValid: true,
  receiverName: 'Karnataka Warehousing Solutions Ltd',
  receiverGSTIN: '29AAACK7654P1Z3', // Karnataka (29)
  receiverState: 'Karnataka',
  receiverStateCode: '29',
  isReceiverGSTINValid: true,
  invoiceNumber: 'MLT/2024/9021',
  invoiceDate: '2024-10-22',
  placeOfSupply: 'Karnataka (29)',
  placeOfSupplyStateCode: '29',
  transactionType: 'INTER_STATE',
  expectedTaxType: 'IGST',
  appliedTaxType: 'CGST_SGST', // ERROR! Charged CGST + SGST on Inter-state transaction
  isPoSCompliant: false,
  taxableValue: 420000,
  cgstCharged: 37800,
  sgstCharged: 37800,
  igstCharged: 0,
  appliedTaxRates: [18],
  areTaxRatesStandard: true,
  gstr2bMatchStatus: 'MISMATCH_TAX',
  riskStatus: 'critical',
  complianceFlags: [
    {
      rule: 'Section 7(1) IGST Act - Inter-State Supply Mandate',
      status: 'FAIL',
      message: 'Inter-State supply from Maharashtra (27) to Place of Supply in Karnataka (29) must be charged with IGST, but vendor charged CGST (₹37,800) and SGST (₹37,800).',
      impact: 'Recipient in Karnataka cannot claim CGST/SGST of Maharashtra. Total ITC of ₹75,600 is at risk of disallowance under GST Section 16(2).',
      remedy: 'Reject invoice or request supplier to issue credit note and reissue invoice with IGST @ 18% (₹75,600).'
    },
    {
      rule: 'Section 31 CGST Act - Tax Invoice Rules',
      status: 'WARNING',
      message: 'Place of Supply (PoS) is indicated as Karnataka (29), but tax classification violates Section 8 of the IGST Act.',
      impact: 'Will cause GSTR-2B matching rejection and mismatch in GSTR-3B Table 4(B).',
      remedy: 'Amend in next GSTR-1 filing cycle.'
    },
    {
      rule: 'GSTIN 15-Digit Structural Validation',
      status: 'PASS',
      message: 'Both Supplier (27AAACM5432E1Z7) and Recipient (29AAACK7654P1Z3) GSTINs are structurally valid.',
      impact: 'Entity identity verified.',
      remedy: 'None.'
    }
  ],
  itcEligibility: {
    overallEligibility: 'BLOCKED_POS_ERROR',
    totalGstPaid: 75600,
    eligibleITCAmount: 0,
    blockedITCAmount: 75600,
    gstr3bReportingTable: 'Table 4(B)(2) - Ineligible / Reversals under Others (PoS Error)',
    gstr2bReconciliationNote: 'ITC blocked because Maharashtra CGST+SGST cannot be cross-utilized or claimed by Karnataka GSTIN 29AAACK7654P1Z3.',
    timeLimitSection16_4: {
      maxAvailmentDate: '30-Nov-2025',
      isWithinTimeLimit: true,
      statutoryDeadlineNote: 'ITC claim window for FY 2024-25 closes on 30th November 2025 under Section 16(4).'
    },
    rule37_180DaysReversal: {
      invoiceDate: '2024-10-22',
      paymentDueDate180Days: '2025-04-20',
      interestRatePercent: 18,
      riskStatus: 'SAFE'
    },
    blockedCreditClauses: [
      {
        clause: 'Sec 17(5)(a)',
        title: 'Motor Vehicles & Conveyances',
        category: 'Motor Vehicles',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Motor vehicles for transportation of persons having approved seating capacity <= 13 persons.',
        reason: 'Service is inter-state freight logistics, not executive passenger car purchase/lease.'
      },
      {
        clause: 'Sec 17(5)(b)(i)',
        title: 'Food, Beverages & Outdoor Catering',
        category: 'Food & Catering',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Food and beverages, outdoor catering, beauty treatment, health services.',
        reason: 'Supply is commercial transport logistics.'
      },
      {
        clause: 'Sec 17(5)(b)(ii)',
        title: 'Club / Fitness Memberships',
        category: 'Memberships',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Membership of a club, health and fitness centre.',
        reason: 'No recreational or club facilities.'
      },
      {
        clause: 'Sec 17(5)(c) & (d)',
        title: 'Works Contract / Civil Immovable Property',
        category: 'Works Contract',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Works contract services supplied for construction of an immovable property.',
        reason: 'Freight service not capitalized to immovable property civil structure.'
      },
      {
        clause: 'Sec 17(5)(g)',
        title: 'Personal / Non-Business Consumption',
        category: 'Personal Use',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Goods or services used for personal consumption.',
        reason: 'Procured strictly for commercial warehouse logistics operations.'
      },
      {
        clause: 'Sec 17(5)(h)',
        title: 'Free Samples, Gifts or Written Off Goods',
        category: 'Gifts/Samples',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Goods lost, stolen, destroyed, written off or disposed of by way of gift or free samples.',
        reason: 'Commercial supply against consideration.'
      }
    ],
    section16GoldenConditions: [
      {
        conditionNumber: 'Condition 1',
        title: 'Tax Invoice / Debit Note in Hand',
        requirement: 'Possession of a tax invoice or debit note issued by supplier under Rule 46.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(a)',
        notes: 'Tax Invoice #MLT/2024/9021 available on record.'
      },
      {
        conditionNumber: 'Condition 2',
        title: 'Receipt of Goods / Services',
        requirement: 'Actual physical or constructive receipt of goods or rendering of services.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(b)',
        notes: 'Consignment tracking and delivery proof acknowledged.'
      },
      {
        conditionNumber: 'Condition 3',
        title: 'Tax Actually Paid to Govt & GSTR-2B Reflection',
        requirement: 'Tax charged has been actually deposited into Government exchequer and reflected in GSTR-2B.',
        isSatisfied: false,
        status: 'NOT_SATISFIED',
        statutoryRef: 'Sec 16(2)(aa) & (c)',
        notes: 'FATAL: Erroneous CGST/SGST of MH (27) cannot be matched or credited into Karnataka (29) GSTR-2B.'
      },
      {
        conditionNumber: 'Condition 4',
        title: 'Filing of Return under Section 39',
        requirement: 'Supplier has filed GSTR-3B and recipient files GSTR-3B return.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(d)',
        notes: 'Both entities regular GSTR-3B monthly filers.'
      },
      {
        conditionNumber: 'Condition 5',
        title: '180-Day Payment Compliance (Rule 37)',
        requirement: 'Payment of value + tax within 180 days from invoice date to avoid reversal with 18% interest.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: '2nd Proviso to Sec 16(2)',
        notes: 'Within credit period. Vendor settlement due before 20-Apr-2025.'
      }
    ],
    itemClassifications: [
      {
        description: 'Interstate Warehouse Freight & Logistics Transport',
        hsnSac: '996511',
        taxableValue: 420000,
        taxRatePercent: 18,
        totalTax: 75600,
        nature: 'Input Services',
        itcEligibility: 'BLOCKED_POS',
        sectionRef: 'Section 7 IGST Act / Section 16(2)',
        eligibleTaxAmount: 0,
        blockedTaxAmount: 75600,
        reason: 'Wrong jurisdiction tax charged (CGST+SGST instead of IGST). Ineligible for claim in Karnataka.'
      }
    ],
    caWorkpaperFinding: 'BLOCKED / INELIGIBLE ITC OF ₹75,600: Inadmissible due to wrong tax heads charged by vendor. CGST/SGST of Maharashtra cannot be set off against output liability in Karnataka.',
    actionRequired: 'Do NOT claim ₹75,600 in GSTR-3B Table 4(A)(5). Reject invoice and instruct supplier to issue Credit Note and fresh Tax Invoice with IGST 18%.'
  },
  auditNotes: 'CRITICAL STATUTORY VIOLATION: Place of Supply error. The supplier is in Maharashtra (27) and PoS is Karnataka (29), making it an Inter-State supply requiring IGST. The invoice erroneously charged intra-state CGST+SGST. ITC cannot be legally availed in recipient state jurisdiction.'
};

// Sample 3B: Explicit Section 17(5) Blocked Credit Sample (5-Seater Passenger Vehicle & Outdoor Catering)
export const SAMPLE_GST_BLOCKED_CREDIT_SEC17_5: GSTComplianceData = {
  vendorName: 'Royal Auto & Luxury Catering Services LLP',
  vendorGSTIN: '27AABCR9876Q1Z4',
  vendorState: 'Maharashtra',
  vendorStateCode: '27',
  isVendorGSTINValid: true,
  receiverName: 'Apex Precision Engineering Ltd',
  receiverGSTIN: '27AAECP9876K1Z2',
  receiverState: 'Maharashtra',
  receiverStateCode: '27',
  isReceiverGSTINValid: true,
  invoiceNumber: 'RGH/2025/0412',
  invoiceDate: '2025-01-15',
  placeOfSupply: 'Maharashtra (27)',
  placeOfSupplyStateCode: '27',
  transactionType: 'INTRA_STATE',
  expectedTaxType: 'CGST_SGST',
  appliedTaxType: 'CGST_SGST',
  isPoSCompliant: true,
  taxableValue: 1550000,
  cgstCharged: 214500,
  sgstCharged: 214500,
  igstCharged: 0,
  appliedTaxRates: [28, 18],
  areTaxRatesStandard: true,
  gstr2bMatchStatus: 'MATCHED',
  riskStatus: 'critical',
  complianceFlags: [
    {
      rule: 'Section 17(5)(a) CGST Act - Motor Vehicles Blocked Credit',
      status: 'FAIL',
      message: 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.',
      impact: 'Critical Red (Blocked Credit): ITC of ₹4,20,000 (CGST ₹2,10,000 + SGST ₹2,10,000) must be permanently reversed / disallowed in GSTR-3B Table 4(B)(1).',
      remedy: 'Book tax amount as business expense in Profit & Loss Account. Do NOT claim in GSTR-3B Table 4(A)(5).'
    },
    {
      rule: 'Section 17(5)(b)(i) CGST Act - Food, Beverages & Catering Blocked Credit',
      status: 'FAIL',
      message: 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.',
      impact: 'Critical Red (Blocked Credit): ITC of ₹9,000 (CGST ₹4,500 + SGST ₹4,500) is statutorily ineligible.',
      remedy: 'Disallow credit and classify under Ineligible ITC in GSTR-3B Table 4(B)(1) and Annual Return GSTR-9 Table 8E.'
    },
    {
      rule: 'Section 16(2) CGST Act - Golden Conditions',
      status: 'PASS',
      message: 'Tax invoice particulars and GSTR-2B reflection are verified.',
      impact: 'Documentation is complete, but statutory Section 17(5) negative list overrides general Section 16 eligibility.',
      remedy: 'Maintain in Section 17(5) Blocked Credit Workpaper Register for statutory audit.'
    }
  ],
  itcEligibility: {
    overallEligibility: 'BLOCKED_17_5',
    totalGstPaid: 429000,
    eligibleITCAmount: 0,
    blockedITCAmount: 429000,
    gstr3bReportingTable: 'Table 4(B)(1) - Ineligible as per Section 17(5)',
    gstr2bReconciliationNote: 'Appears in GSTR-2B Part A, but company is legally obligated to reverse/disallow ₹4,29,000 under Table 4(B)(1) of GSTR-3B.',
    timeLimitSection16_4: {
      maxAvailmentDate: '30-Nov-2026',
      isWithinTimeLimit: true,
      statutoryDeadlineNote: 'Statutory deadline is N/A due to absolute blockage under Section 17(5).'
    },
    rule37_180DaysReversal: {
      invoiceDate: '2025-01-15',
      paymentDueDate180Days: '2025-07-14',
      interestRatePercent: 18,
      riskStatus: 'SAFE'
    },
    blockedCreditClauses: [
      {
        clause: 'Sec 17(5)(a)',
        title: 'Motor Vehicles & Passenger Conveyances',
        category: 'Motor Vehicles',
        isTriggered: true,
        status: 'BLOCKED',
        statutoryText: 'Motor vehicles for transportation of persons having approved seating capacity <= 13 persons.',
        reason: 'BLOCKED: 5-Seater Passenger Vehicle (28% GST) used for executive corporate transport. Blocked under Section 17(5)(a).'
      },
      {
        clause: 'Sec 17(5)(b)(i)',
        title: 'Food, Beverages & Outdoor Catering',
        category: 'Food & Catering',
        isTriggered: true,
        status: 'BLOCKED',
        statutoryText: 'Food and beverages, outdoor catering, beauty treatment, health services.',
        reason: 'BLOCKED: Outdoor catering and beverage hospitality services. Blocked under Section 17(5)(b)(i).'
      },
      {
        clause: 'Sec 17(5)(b)(ii)',
        title: 'Club / Fitness Centre Memberships',
        category: 'Memberships',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Membership of a club, health and fitness centre.',
        reason: 'No gym or country club membership billed.'
      },
      {
        clause: 'Sec 17(5)(c) & (d)',
        title: 'Works Contract / Civil Construction',
        category: 'Works Contract',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Works contract services supplied for construction of an immovable property.',
        reason: 'No civil construction of immovable property.'
      },
      {
        clause: 'Sec 17(5)(g)',
        title: 'Personal Consumption',
        category: 'Personal Use',
        isTriggered: true,
        status: 'BLOCKED',
        statutoryText: 'Goods or services used for personal consumption.',
        reason: 'Hospitality & passenger transport benefits consumed by directors/executives.'
      },
      {
        clause: 'Sec 17(5)(h)',
        title: 'Gifts, Free Samples & Lost Goods',
        category: 'Gifts/Samples',
        isTriggered: false,
        status: 'CLEAR',
        statutoryText: 'Goods lost, stolen, destroyed, written off or disposed of by way of gift or free samples.',
        reason: 'Billed service against commercial tax invoice.'
      }
    ],
    section16GoldenConditions: [
      {
        conditionNumber: 'Condition 1',
        title: 'Tax Invoice in Hand',
        requirement: 'Possession of tax invoice issued by supplier.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(a)',
        notes: 'Tax Invoice #RGH/2025/0412 in possession.'
      },
      {
        conditionNumber: 'Condition 2',
        title: 'Receipt of Goods/Services',
        requirement: 'Services and vehicle physically availed.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(b)',
        notes: 'Vehicle delivery and catering executed on 15-Jan-2025.'
      },
      {
        conditionNumber: 'Condition 3',
        title: 'Tax Deposited & 2B Reflection',
        requirement: 'Tax paid to Govt and reflected in GSTR-2B.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(aa) & (c)',
        notes: 'Reflected in GSTR-2B, but blocked by overriding non-obstante clause of Section 17(5).'
      },
      {
        conditionNumber: 'Condition 4',
        title: 'Return Furnished under Sec 39',
        requirement: 'GSTR-3B filing.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Sec 16(2)(d)',
        notes: 'Included in monthly tax period return.'
      },
      {
        conditionNumber: 'Condition 5',
        title: '180-Day Rule 37 Settlement',
        requirement: 'Payment to vendor within 180 days.',
        isSatisfied: true,
        status: 'SATISFIED',
        statutoryRef: 'Rule 37 CGST Rules',
        notes: 'Due for settlement within standard credit terms.'
      }
    ],
    itemClassifications: [
      {
        description: '5-Seater Passenger Vehicle',
        hsnSac: '870323',
        taxableValue: 1500000,
        taxRatePercent: 28,
        totalTax: 420000,
        nature: 'Motor Vehicle',
        itcEligibility: 'BLOCKED_17_5',
        sectionRef: 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.',
        eligibleTaxAmount: 0,
        blockedTaxAmount: 420000,
        reason: 'Section 17(5)(a) of CGST Act: ITC on motor vehicles for transportation of persons (≤ 13 seats) is blocked, unless the business is in vehicle reselling, passenger transport, or driving school operations.',
        alertLevel: '🔴 Critical Red (Blocked Credit)'
      },
      {
        description: 'Outdoor Catering & Beverages',
        hsnSac: '996331',
        taxableValue: 50000,
        taxRatePercent: 18,
        totalTax: 9000,
        nature: 'Food & Catering',
        itcEligibility: 'BLOCKED_17_5',
        sectionRef: 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.',
        eligibleTaxAmount: 0,
        blockedTaxAmount: 9000,
        reason: 'Section 17(5)(b)(i) of CGST Act: Food, beverages, and outdoor catering credits are strictly blocked unless mandated by law for employees or used for taxable outward supply of the same.',
        alertLevel: '🔴 Critical Red (Blocked Credit)'
      }
    ],
    caWorkpaperFinding: '100% BLOCKED CREDIT (₹4,29,000): Ineligible for Input Tax Credit under Section 17(5)(a) (Motor Vehicle: ₹4,20,000) & Section 17(5)(b)(i) (Outdoor Catering: ₹9,000). Must be reported in GSTR-3B Table 4(B)(1) as Permanent Ineligible Credit.',
    actionRequired: 'Expense total tax amount of ₹4,29,000 to P&L account. Do NOT avail in GSTR-3B Table 4(A)(5) to prevent demand notice under Section 73/74 with 18% mandatory interest and 10% penalty.'
  },
  auditNotes: 'SECTION 17(5) STATUTORY BLOCKAGE: Although PoS is intra-state (Maharashtra 27) and GSTIN is valid, both line items are covered under the statutory negative list of Section 17(5) (Passenger motor vehicles <= 13 seats and outdoor catering). Direct availment will trigger GSTR-3B vs 2B audit red flags.'
};

// Sample 4: Bank Statement with Cash > ₹50,000 and Duplicates
export const SAMPLE_BANK_STATEMENT: BankStatementData = {
  bankName: 'HDFC Bank Ltd - Corporate Banking Branch',
  accountNumber: '50200049281742',
  accountHolder: 'Apex Precision Engineering Ltd',
  ifscCode: 'HDFC0000240',
  period: { from: '2024-10-01', to: '2024-10-31' },
  openingBalance: 1485200.50,
  closingBalance: 2314900.50,
  totalInflows: 3845000.00,
  totalOutflows: 3015300.00,
  netCashFlow: 829700.00,
  totalTransactionsCount: 14,
  highCashTransactionsCount: 3,
  duplicateTransactionsCount: 2,
  riskStatus: 'critical',
  transactions: [
    {
      id: 'tx-1',
      date: '2024-10-03',
      description: 'NEFT CR-CITIBANK-TECHFLOW SOLUTIONS-INVOICE 4491',
      referenceNo: 'CITIN24918231',
      credit: 650000,
      balance: 2135200.50,
      mode: 'NEFT',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Customer Receipts'
    },
    {
      id: 'tx-2',
      date: '2024-10-07',
      description: 'CASH DEPOSIT BY SELF - CASH SALES COLLECTION',
      referenceNo: 'DEP-CASH-081',
      credit: 180000, // CASH > 50k Alert!
      balance: 2315200.50,
      mode: 'CASH',
      isCashAbove50k: true,
      isDuplicate: false,
      category: 'Cash Deposit',
      notes: 'SFT Reportable & Sec 269ST threshold check required'
    },
    {
      id: 'tx-3',
      date: '2024-10-10',
      description: 'RTGS DR-STEEL AUTHORITY OF INDIA-RAW MATERIAL',
      referenceNo: 'RTGS241010041',
      debit: 1250000,
      balance: 1065200.50,
      mode: 'RTGS',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Vendor Payment'
    },
    {
      id: 'tx-4',
      date: '2024-10-12',
      description: 'CASH WITHDRAWAL - SELF FOR SITE EXPENSES',
      referenceNo: 'CHQ-449102',
      debit: 75000, // CASH > 50k Alert!
      balance: 990200.50,
      mode: 'CASH',
      isCashAbove50k: true,
      isDuplicate: false,
      category: 'Cash Withdrawal',
      notes: 'Cash withdrawal > ₹50k; verify vouchers for Sec 40A(3) disallowance'
    },
    {
      id: 'tx-5',
      date: '2024-10-15',
      description: 'UPI/428910281/Vendor Payment Cloud Server/Razorpay',
      referenceNo: 'UPI428910281',
      debit: 18500,
      balance: 971700.50,
      mode: 'UPI',
      isCashAbove50k: false,
      isDuplicate: true,
      category: 'Software & IT'
    },
    {
      id: 'tx-6',
      date: '2024-10-15',
      description: 'UPI/428910281/Vendor Payment Cloud Server/Razorpay',
      referenceNo: 'UPI428910281',
      debit: 18500, // DUPLICATE ENTRY!
      balance: 953200.50,
      mode: 'UPI',
      isCashAbove50k: false,
      isDuplicate: true,
      category: 'Software & IT',
      notes: 'Potential double debit of ₹18,500 on 2024-10-15'
    },
    {
      id: 'tx-7',
      date: '2024-10-18',
      description: 'CASH DEPOSIT - COUNTER RECEIPT FACTORY OUTLET',
      referenceNo: 'DEP-CASH-095',
      credit: 95000, // CASH > 50k Alert!
      balance: 1048200.50,
      mode: 'CASH',
      isCashAbove50k: true,
      isDuplicate: false,
      category: 'Cash Deposit',
      notes: 'Cash deposit > ₹50,000. Check single person single day limit.'
    },
    {
      id: 'tx-8',
      date: '2024-10-22',
      description: 'NEFT CR-OMKAR ENTERPRISES-ADVANCE FOR WORK',
      referenceNo: 'NEFT241022091',
      credit: 820000,
      balance: 1868200.50,
      mode: 'NEFT',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Customer Advance'
    },
    {
      id: 'tx-9',
      date: '2024-10-25',
      description: 'SALARY DISBURSEMENT OCTOBER 2024 BATCH 1',
      referenceNo: 'CMS-SAL-OCT',
      debit: 980000,
      balance: 888200.50,
      mode: 'OTHER',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Payroll'
    },
    {
      id: 'tx-10',
      date: '2024-10-27',
      description: 'DIRECT TAX PAYMENT - ADVANCE TAX Q2 FY2425',
      referenceNo: 'CHAL-ITX-2710',
      debit: 450000,
      balance: 438200.50,
      mode: 'OTHER',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Statutory Taxes'
    },
    {
      id: 'tx-11',
      date: '2024-10-29',
      description: 'RTGS CR-GLOBAL EXPORTS LTD-EXPORT PROCEEDS',
      referenceNo: 'RTGS241029012',
      credit: 2100000,
      balance: 2538200.50,
      mode: 'RTGS',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Export Inflows'
    },
    {
      id: 'tx-12',
      date: '2024-10-30',
      description: 'MONTHLY LOAN EMI - HDFC COMM LOAN A/C 9918',
      referenceNo: 'ACH-EMI-9918',
      debit: 223300,
      balance: 2314900.50,
      mode: 'OTHER',
      isCashAbove50k: false,
      isDuplicate: false,
      category: 'Debt Servicing'
    }
  ],
  cashAuditAlerts: [
    {
      date: '2024-10-07',
      amount: 180000,
      type: 'DEPOSIT',
      section: 'Sec 269ST',
      ruleViolation: 'Cash Deposit of ₹1,80,000 exceeds ₹50,000 single transaction threshold',
      description: 'Section 269ST prohibits receiving cash of ₹2,00,000 or more in aggregate from a person in a day or in respect of a single transaction. Bank requires SFT reporting; verify sales bills split.'
    },
    {
      date: '2024-10-12',
      amount: 75000,
      type: 'WITHDRAWAL',
      section: 'SFT Reporting',
      ruleViolation: 'Cash Withdrawal of ₹75,000 exceeds ₹50,000 audit attention limit',
      description: 'Section 40A(3) disallows business payments in cash exceeding ₹10,000 per day per person. CA must audit expenditure cash vouchers.'
    },
    {
      date: '2024-10-18',
      amount: 95000,
      type: 'DEPOSIT',
      section: 'Sec 269ST',
      ruleViolation: 'Cash Deposit of ₹95,000',
      description: 'High cash transaction flagged for SFT/AIS reconciliation to avoid high-risk scrutiny notice from Income Tax Dept under Section 68.'
    }
  ],
  duplicateGroups: [
    {
      date: '2024-10-15',
      amount: 18500,
      type: 'DEBIT',
      descriptions: [
        'UPI/428910281/Vendor Payment Cloud Server/Razorpay',
        'UPI/428910281/Vendor Payment Cloud Server/Razorpay'
      ],
      count: 2
    }
  ],
  auditSummary: 'HIGH AUDIT RISK: Bank statement audit revealed 3 cash transactions exceeding ₹50,000 (Totaling ₹3,50,000) requiring Statement of Financial Transactions (SFT) scrutiny & Section 269ST / 40A(3) review. Also identified 1 duplicate payment instance of ₹18,500 on 15-Oct requiring reconciliation with vendor ledger.'
};

// Sample 5: TDS Analyser Sample with Short Deduction (Sec 194J vs Sec 194C)
export const SAMPLE_TDS_ANALYSIS: TDSAnalysisData = {
  deductorName: 'Apex Precision Engineering Ltd',
  deductorTAN: 'PNEP12345E',
  deducteeName: 'Adv. K. R. Ramanathan & Partners (Legal Firm)',
  deducteePAN: 'AAAFR8921K',
  invoiceOrRefNumber: 'LEG/2024/0481',
  date: '2024-11-20',
  grossServiceAmount: 250000,
  natureOfService: 'Corporate Legal Advisory, Contract Drafting & Arbitration Representation',
  declaredTDSSection: 'Sec 194C (Contractors)',
  recommendedTDSSection: 'Sec 194J(b) (Professional Services)',
  sectionTitle: 'Fees for Professional Services',
  standardRate: 10.0,
  appliedRate: 2.0,
  isRateCorrect: false,
  actualTDSDeducted: 5000, // 2% of 2,50,000
  expectedTDSDeducted: 25000, // 10% of 2,50,000
  tdsVariance: 20000, // Shortfall of ₹20,000
  thresholdLimit: 30000,
  isThresholdExceeded: true,
  isTDSMissed: false,
  isShortDeduction: true,
  lowerDeductionCertStatus: 'NO_CERTIFICATE',
  sectionWiseBreakdown: [
    {
      section: 'Sec 194J(b)',
      description: 'Legal & Professional Consultancy Fees',
      natureOfPayment: 'Professional Services',
      taxableAmount: 250000,
      applicableRate: 10.0,
      deductedRate: 2.0,
      expectedTDS: 25000,
      actualTDS: 5000,
      variance: 20000,
      status: 'SHORT_DEDUCTION',
      remarks: 'Incorrectly deducted @ 2% under Sec 194C instead of statutory 10% under Sec 194J(b). Short deduction ₹20,000.'
    }
  ],
  riskStatus: 'critical',
  caAuditRecommendations: [
    'Section 194J(b) specifically mandates 10% TDS deduction for legal and professional services. Applying Sec 194C (2%) is a non-compliance resulting in short deduction.',
    'Interest liability under Section 201(1A) @ 1% per month is applicable on the short-deducted amount of ₹20,000 from the date of deduction to actual payment.',
    'Risk of 30% expenditure disallowance under Section 40(a)(ia) in the client\'s Income Tax assessment unless corrected before filing Form 26Q.',
    'Action Required: Deduct the differential TDS of ₹20,000 from subsequent payments or request payee to remit and file Form 26A certification.'
  ],
  form26ASDeclarationStatus: 'UNMATCHED'
};

// Sample 6: Clean Compliant TDS Sample (Sec 194J(a) Technical Services @ 2%)
export const SAMPLE_TDS_CLEAN: TDSAnalysisData = {
  deductorName: 'Apex Precision Engineering Ltd',
  deductorTAN: 'PNEP12345E',
  deducteeName: 'Infosys Tech Consulting Services Ltd',
  deducteePAN: 'AAACI1928K',
  invoiceOrRefNumber: 'INF/2024/7712',
  date: '2024-11-28',
  grossServiceAmount: 500000,
  natureOfService: 'Enterprise IT Architecture, Cloud API Integration & Technical Consulting',
  declaredTDSSection: 'Sec 194J(a) (Fees for Technical Services)',
  recommendedTDSSection: 'Sec 194J(a)',
  sectionTitle: 'Fees for Technical Services (FTS)',
  standardRate: 2.0,
  appliedRate: 2.0,
  isRateCorrect: true,
  actualTDSDeducted: 10000, // 2% of 5,00,000
  expectedTDSDeducted: 10000,
  tdsVariance: 0,
  thresholdLimit: 30000,
  isThresholdExceeded: true,
  isTDSMissed: false,
  isShortDeduction: false,
  lowerDeductionCertStatus: 'NO_CERTIFICATE',
  sectionWiseBreakdown: [
    {
      section: 'Sec 194J(a)',
      description: 'Fees for Technical Services (FTS)',
      natureOfPayment: 'Technical Services',
      taxableAmount: 500000,
      applicableRate: 2.0,
      deductedRate: 2.0,
      expectedTDS: 10000,
      actualTDS: 10000,
      variance: 0,
      status: 'CORRECT',
      remarks: 'Accurately deducted @ statutory 2% under Section 194J(a) for FTS. Zero variance.'
    }
  ],
  riskStatus: 'compliant',
  caAuditRecommendations: [
    'Statutory TDS of ₹10,000 correctly deducted @ statutory 2% rate under Section 194J(a).',
    'Ensure remittance into Government Treasury by 7th of subsequent month via Challan ITNS 281.',
    'Verified Form 26AS matching status - No interest or penalty liability under Chapter XVII-B.'
  ],
  form26ASDeclarationStatus: 'MATCHED'
};

export const SAMPLE_DOCUMENTS: SampleDocumentItem[] = [
  {
    id: 'sample-inv-clean',
    name: 'Clean IT Services Invoice (Fully Reconciled)',
    module: 'invoice',
    description: 'Annual Cloud Infrastructure bill with accurate 18% IGST and HSN validation.',
    tag: '100% Compliant',
    risk: 'compliant',
    svgPreview: 'invoice-clean',
    size: 198400,
    mimeType: 'image/png',
    sampleData: SAMPLE_INVOICE_CLEAN
  },
  {
    id: 'sample-inv-math-error',
    name: 'Vendor Invoice (Math Mismatch - ₹6,200 Discrepancy)',
    module: 'invoice',
    description: 'Hardware Supply Invoice with arithmetic error between line items and total.',
    tag: 'Math Audit',
    risk: 'critical',
    svgPreview: 'invoice-math-error',
    size: 245760,
    mimeType: 'image/png',
    sampleData: SAMPLE_INVOICE_MATH_MISMATCH
  },
  {
    id: 'sample-gst-pos-error',
    name: 'Logistics Tax Invoice (Place of Supply Inter/Intra Mismatch)',
    module: 'gst',
    description: 'Maharashtra to Karnataka transaction with wrong CGST/SGST charged instead of IGST.',
    tag: 'PoS Violation',
    risk: 'critical',
    svgPreview: 'gst-pos-error',
    size: 312000,
    mimeType: 'image/png',
    sampleData: SAMPLE_GST_COMPLIANCE_POS_ERROR
  },
  {
    id: 'sample-gst-blocked-17-5',
    name: 'Executive Fleet & Catering (Sec 17(5) Blocked Credit)',
    module: 'gst',
    description: 'Director luxury car lease and corporate catering invoice statutorily ineligible for ITC under Section 17(5).',
    tag: 'Sec 17(5) Blocked',
    risk: 'critical',
    svgPreview: 'gst-blocked-17-5',
    size: 276000,
    mimeType: 'image/png',
    sampleData: SAMPLE_GST_BLOCKED_CREDIT_SEC17_5
  },
  {
    id: 'sample-tds-clean',
    name: 'IT Tech Services Bill (Sec 194J Compliant 2% TDS)',
    module: 'tds',
    description: 'Enterprise IT consulting bill with 100% accurate 2% TDS deduction under Sec 194J(a).',
    tag: '100% Compliant',
    risk: 'compliant',
    svgPreview: 'tds-clean',
    size: 192000,
    mimeType: 'image/png',
    sampleData: SAMPLE_TDS_CLEAN
  },
  {
    id: 'sample-tds-short-deduction',
    name: 'Legal Services Bill (Sec 194J vs 194C Short Deduction)',
    module: 'tds',
    description: 'Professional fee bill deducted @ 2% instead of mandatory 10% under Sec 194J.',
    tag: 'Sec 194J Shortfall',
    risk: 'critical',
    svgPreview: 'tds-bill',
    size: 185000,
    mimeType: 'image/png',
    sampleData: SAMPLE_TDS_ANALYSIS
  },
  {
    id: 'sample-bank-statement',
    name: 'Current Bank Statement (Q3 - Cash >₹50k & Duplicates)',
    module: 'bank',
    description: 'HDFC Current A/C with ₹1.8L & ₹95k Cash deposits + duplicate UPI debit.',
    tag: 'SFT & Duplicate Flag',
    risk: 'critical',
    svgPreview: 'bank-statement',
    size: 428000,
    mimeType: 'application/pdf',
    sampleData: SAMPLE_BANK_STATEMENT
  }
];

export const SAMPLE_AUDIT_DATA = {
  invoice: SAMPLE_INVOICE_CLEAN,
  gst: SAMPLE_GST_COMPLIANCE_POS_ERROR,
  tds: SAMPLE_TDS_CLEAN,
  bank: SAMPLE_BANK_STATEMENT
};

export const DEFAULT_CA_FIRM_PROFILE: CAFirmProfile = {
  firmName: 'Shweta Goel & Co.',
  frnNumber: '102938W',
  partnerName: 'CA. SHWETA GOEL, FCA',
  membershipNo: '084920',
  clientName: 'Apex Precision Engineering Ltd',
  clientGSTIN: '27AAECP9876K1Z2',
  clientPAN: 'AAECP9876K',
  financialYear: 'FY 2025-26 (AY 2026-27)',
  assessmentYear: 'AY 2026-27'
};

