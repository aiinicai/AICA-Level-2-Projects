/**
 * ITR Parser Engine
 * Handles rule-based Regex & tabular parsing for PDF texts,
 * JSON e-filing payloads from the IT Department portal,
 * AI-assisted extraction via Gemini server endpoint,
 * and live tax recalculation with exact Indian tax slabs.
 */

import { CompleteITRData, ITRPersonalInfo, ITRIncomeHeads, ITRDeductions, ITRTaxComputation, ITRTaxesPaid } from '../itr-types';
import { parseIndianNumber, roundOff288A, roundOff288B } from './numberParsing';
import { calculateNewRegimeTax, calculateOldRegimeTax } from './taxCalculator';

/**
 * Creates default / empty ITR dataset
 */
export function getDefaultITRData(): CompleteITRData {
  return {
    id: `itr_${Date.now()}`,
    sourceFileName: 'ITR2_AY2026-27_ATUPP0297R.pdf',
    extractionConfidence: 1.0,
    extractionMethod: 'manual_sample',
    personalInfo: {
      pan: 'ATUPP0297R',
      aadhaar: '4xxx xxxx 6668',
      name: 'JAIMIN NAYANBHAI PATEL',
      fatherName: 'NAYANBHAI RAMESHCHANDRA PATEL',
      dob: '11/04/1988',
      formType: 'ITR-2',
      assessmentYear: '2026-27',
      financialYear: '2025-26',
      filingStatus: '139(1) - On or before due date',
      filingType: 'Original',
      taxRegime: 'New Regime',
      ackNumber: '294544750090726',
      filingDate: '09/07/2026',
      address: 'D-4, YASHPAL APPARTMENT, NEAR VIJAY CROSS ROAD, Gujarat University S.O, Ahmadabad City',
      city: 'AHMEDABAD',
      state: 'Gujarat',
      pincode: '380009',
      mobile: '+91 9727750617',
      email: 'pateljaimin1104@yahoo.com',
      status: 'Individual',
      residentialStatus: 'Resident',
      bankName: 'HDFC Bank',
      bankAccountNumber: '01901130000303',
      bankIfsc: 'HDFC0000190',
    },
    incomeHeads: {
      salaryGross: 2708105,
      salaryExemptAllowances: 0,
      salaryStandardDeduction: 75000,
      salaryProfessionalTax: 0,
      salaryNet: 2633105,
      housePropertyGross: 0,
      housePropertyTaxes: 0,
      housePropertyStandardDeduction: 0,
      housePropertyInterest: 0,
      housePropertyNet: 0,
      businessGrossReceipts: 0,
      businessGrossProfit: 0,
      businessExpenses: 0,
      businessNetProfit: 0,
      businessPresumptive44AD: 0,
      businessPresumptive44ADA: 0,
      capitalGainsSTCG_15Pct: 0,
      capitalGainsSTCG_20Pct: 116015, // STCG u/s 111A @ 20%
      capitalGainsSTCG_Slab: 0,
      capitalGainsLTCG_10Pct: 0,
      capitalGainsLTCG_20Pct: 0,
      capitalGainsLTCG_12_5Pct: 11710, // LTCG u/s 112A @ 12.5%
      capitalGainsNet: 127725,
      otherSourcesInterestSavings: 1087,
      otherSourcesInterestDeposits: 0,
      otherSourcesDividends: 13541,
      otherSourcesFamilyPension: 0,
      otherSourcesOthers: 0,
      otherSourcesDeductions: 0,
      otherSourcesNet: 14628,
      grossTotalIncome: 2775458,
    },
    deductions: {
      sec80C: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 0,
      sec80CCD2: 0,
      sec80D: 0,
      sec80DD: 0,
      sec80DDB: 0,
      sec80E: 0,
      sec80EE: 0,
      sec80EEA: 0,
      sec80G: 0,
      sec80GG: 0,
      sec80GGA: 0,
      sec80TTA: 0,
      sec80TTB: 0,
      sec80U: 0,
      otherDeductions: 0,
      totalDeductions: 0,
    },
    taxComputation: {
      totalTaxableIncome: 2775460,
      taxOnTotalIncome: 374321,
      specialRateTax: 23203,
      rebate87A: 0,
      taxAfterRebate: 397524,
      surcharge: 0,
      cess: 15901,
      grossTaxLiability: 413425,
      relief89: 0,
      relief90_91: 0,
      netTaxLiability: 413425,
      interest234A: 0,
      interest234B: 0,
      interest234C: 0,
      fee234F: 0,
      totalTaxAndInterest: 413425,
    },
    taxesPaid: {
      advanceTax: 0,
      tdsSalary: 445299,
      tdsNonSalary: 1336,
      tcs: 0,
      selfAssessmentTax: 0,
      totalTaxesPaid: 446635,
      refundDue: 33210,
      taxPayable: 0,
    },
    caDetails: {
      includeCASection: false,
      caName: '',
      firmName: '',
      membershipNo: '',
      firmRegistrationNo: '',
      udin: '',
      place: '',
      date: '',
    },
    styleConfig: {
      documentTitle: 'COMPUTATION OF TOTAL INCOME & TAX LIABILITY',
      subtitle: 'Prepared for Income Tax Return Assessment Year 2026-27 (FY 2025-26)',
      themeColor: 'navy',
      fontFamily: 'Calibri',
      includeHeaderFooter: true,
      includeIndianRupeeWords: true,
      includeTaxComputationTable: true,
      includeDeductionsBreakdown: true,
      includeTaxesPaidBreakdown: true,
      includeBankDetails: true,
      includeVerificationClause: false,
      includeRegimeComparison: false,
      watermarkText: '',
      fontSize: 'standard',
      layoutType: 'standard_computation',
    },
    notes: '',
  };
}

/**
 * Creates completely empty / blank ITR dataset for starting from scratch
 */
export function getBlankITRData(): CompleteITRData {
  return {
    id: `itr_${Date.now()}`,
    sourceFileName: 'Blank_Computation.pdf',
    extractionConfidence: 1.0,
    extractionMethod: 'manual_sample',
    personalInfo: {
      pan: '',
      aadhaar: '',
      name: '',
      fatherName: '',
      dob: '',
      formType: 'ITR-1',
      assessmentYear: '2024-25',
      financialYear: '2023-24',
      filingStatus: '139(1) - On or before due date',
      filingType: 'Original',
      taxRegime: 'New Regime',
      ackNumber: '',
      filingDate: new Date().toLocaleDateString('en-GB'),
      address: '',
      city: '',
      state: '',
      pincode: '',
      mobile: '',
      email: '',
      status: 'Individual',
      residentialStatus: 'Resident',
      bankName: '',
      bankAccountNumber: '',
      bankIfsc: '',
    },
    incomeHeads: {
      salaryGross: 0,
      salaryExemptAllowances: 0,
      salaryStandardDeduction: 0,
      salaryProfessionalTax: 0,
      salaryNet: 0,
      housePropertyGross: 0,
      housePropertyTaxes: 0,
      housePropertyStandardDeduction: 0,
      housePropertyInterest: 0,
      housePropertyNet: 0,
      businessGrossReceipts: 0,
      businessGrossProfit: 0,
      businessExpenses: 0,
      businessNetProfit: 0,
      businessPresumptive44AD: 0,
      businessPresumptive44ADA: 0,
      capitalGainsSTCG_15Pct: 0,
      capitalGainsSTCG_Slab: 0,
      capitalGainsLTCG_10Pct: 0,
      capitalGainsLTCG_20Pct: 0,
      capitalGainsLTCG_12_5Pct: 0,
      capitalGainsNet: 0,
      otherSourcesInterestSavings: 0,
      otherSourcesInterestDeposits: 0,
      otherSourcesDividends: 0,
      otherSourcesFamilyPension: 0,
      otherSourcesOthers: 0,
      otherSourcesDeductions: 0,
      otherSourcesNet: 0,
      grossTotalIncome: 0,
    },
    deductions: {
      sec80C: 0,
      sec80CCC: 0,
      sec80CCD1: 0,
      sec80CCD1B: 0,
      sec80CCD2: 0,
      sec80D: 0,
      sec80DD: 0,
      sec80DDB: 0,
      sec80E: 0,
      sec80EE: 0,
      sec80EEA: 0,
      sec80G: 0,
      sec80GG: 0,
      sec80GGA: 0,
      sec80TTA: 0,
      sec80TTB: 0,
      sec80U: 0,
      otherDeductions: 0,
      totalDeductions: 0,
    },
    taxComputation: {
      totalTaxableIncome: 0,
      taxOnTotalIncome: 0,
      specialRateTax: 0,
      rebate87A: 0,
      taxAfterRebate: 0,
      surcharge: 0,
      cess: 0,
      grossTaxLiability: 0,
      relief89: 0,
      relief90_91: 0,
      netTaxLiability: 0,
      interest234A: 0,
      interest234B: 0,
      interest234C: 0,
      fee234F: 0,
      totalTaxAndInterest: 0,
    },
    taxesPaid: {
      advanceTax: 0,
      tdsSalary: 0,
      tdsNonSalary: 0,
      tcs: 0,
      selfAssessmentTax: 0,
      totalTaxesPaid: 0,
      refundDue: 0,
      taxPayable: 0,
    },
    caDetails: {
      includeCASection: true,
      caName: 'CA. JAIMIN PATEL',
      firmName: 'Chartered Accountants',
      membershipNo: '184920',
      firmRegistrationNo: '',
      udin: '',
      place: '',
      date: new Date().toLocaleDateString('en-GB'),
    },
    styleConfig: {
      documentTitle: 'COMPUTATION OF TOTAL INCOME & TAX LIABILITY',
      subtitle: 'Assessment Year 2024-25',
      themeColor: 'navy',
      fontFamily: 'Calibri',
      includeHeaderFooter: true,
      includeIndianRupeeWords: true,
      includeTaxComputationTable: true,
      includeDeductionsBreakdown: true,
      includeTaxesPaidBreakdown: true,
      includeBankDetails: true,
      includeVerificationClause: true,
      watermarkText: '',
      fontSize: 'standard',
      layoutType: 'standard_computation',
    },
  };
}

/**
 * Recomputes all totals mathematically while strictly preserving parsed or manually entered tax amounts
 */
export function recalculateITR(data: CompleteITRData, autoComputeTax: boolean = false): CompleteITRData {
  const inc = { ...data.incomeHeads };
  const ded = { ...data.deductions };
  const tax = { ...data.taxComputation };
  const paid = { ...data.taxesPaid };
  const p = data.personalInfo;

  // 1. Salary Net
  if (inc.salaryGross > 0 && inc.salaryStandardDeduction === 0) {
    inc.salaryStandardDeduction = p.assessmentYear >= '2025-26' ? 75000 : 50000;
  }
  inc.salaryNet = Math.max(0, inc.salaryGross - inc.salaryExemptAllowances - inc.salaryStandardDeduction - inc.salaryProfessionalTax);

  // 2. House Property Net
  const nav = Math.max(0, inc.housePropertyGross - inc.housePropertyTaxes);
  if (inc.housePropertyStandardDeduction === 0 && nav > 0) {
    inc.housePropertyStandardDeduction = Math.round(nav * 0.3);
  }
  inc.housePropertyNet = nav - inc.housePropertyStandardDeduction - inc.housePropertyInterest;

  // 3. Business Net
  if (inc.businessPresumptive44AD > 0 || inc.businessPresumptive44ADA > 0) {
    inc.businessNetProfit = inc.businessPresumptive44AD + inc.businessPresumptive44ADA;
  } else if (inc.businessGrossProfit > 0 || inc.businessExpenses > 0) {
    inc.businessNetProfit = inc.businessGrossProfit - inc.businessExpenses;
  }

  // 4. Capital Gains Net
  inc.capitalGainsNet =
    inc.capitalGainsSTCG_15Pct +
    (inc.capitalGainsSTCG_20Pct || 0) +
    inc.capitalGainsSTCG_Slab +
    inc.capitalGainsLTCG_10Pct +
    inc.capitalGainsLTCG_20Pct +
    inc.capitalGainsLTCG_12_5Pct;

  // 5. Other Sources Net
  const otherGross =
    inc.otherSourcesInterestSavings +
    inc.otherSourcesInterestDeposits +
    inc.otherSourcesDividends +
    inc.otherSourcesFamilyPension +
    inc.otherSourcesOthers;
  inc.otherSourcesNet = Math.max(0, otherGross - inc.otherSourcesDeductions);

  // Gross Total Income
  inc.grossTotalIncome =
    inc.salaryNet +
    inc.housePropertyNet +
    inc.businessNetProfit +
    inc.capitalGainsNet +
    inc.otherSourcesNet;

  // Total Deductions
  ded.totalDeductions =
    ded.sec80C +
    ded.sec80CCC +
    ded.sec80CCD1 +
    ded.sec80CCD1B +
    ded.sec80CCD2 +
    ded.sec80D +
    ded.sec80DD +
    ded.sec80DDB +
    ded.sec80E +
    ded.sec80EE +
    ded.sec80EEA +
    ded.sec80G +
    ded.sec80GG +
    ded.sec80GGA +
    ded.sec80TTA +
    ded.sec80TTB +
    ded.sec80U +
    ded.otherDeductions;

  // Total Taxable Income
  const isNewRegime = p.taxRegime.includes('New');
  const allowedDeductions = isNewRegime ? ded.sec80CCD2 : ded.totalDeductions;
  const taxableUnrounded = Math.max(0, inc.grossTotalIncome - allowedDeductions);
  tax.totalTaxableIncome = roundOff288A(taxableUnrounded);

  // Auto Tax Computation (only when explicitly requested and tax is 0)
  if (autoComputeTax && tax.taxOnTotalIncome === 0) {
    const specialRateIncome =
      inc.capitalGainsSTCG_15Pct +
      (inc.capitalGainsSTCG_20Pct || 0) +
      inc.capitalGainsLTCG_10Pct +
      inc.capitalGainsLTCG_20Pct +
      inc.capitalGainsLTCG_12_5Pct;

    const specialTax =
      Math.round(inc.capitalGainsSTCG_15Pct * 0.15) +
      Math.round((inc.capitalGainsSTCG_20Pct || 0) * 0.20) +
      Math.round(Math.max(0, inc.capitalGainsLTCG_10Pct - 100000) * 0.1) +
      Math.round(Math.max(0, inc.capitalGainsLTCG_12_5Pct - 125000) * 0.125) +
      Math.round(inc.capitalGainsLTCG_20Pct * 0.2);
    tax.specialRateTax = specialTax;

    const normalTaxableIncome = Math.max(0, tax.totalTaxableIncome - specialRateIncome);

    const calcResult = isNewRegime
      ? calculateNewRegimeTax(normalTaxableIncome, p.assessmentYear, specialTax)
      : calculateOldRegimeTax(normalTaxableIncome, false, false, specialTax);

    tax.taxOnTotalIncome = calcResult.slabTax;
    tax.rebate87A = calcResult.rebate87A;
    tax.taxAfterRebate = calcResult.taxAfterRebate;
    tax.surcharge = calcResult.surcharge;
    tax.cess = calcResult.cess;
    tax.grossTaxLiability = calcResult.taxAfterRebate + calcResult.surcharge + calcResult.cess;
  } else {
    tax.taxAfterRebate = Math.max(0, tax.taxOnTotalIncome + tax.specialRateTax - tax.rebate87A);
    if (tax.cess === 0 || autoComputeTax) {
      tax.cess = Math.round((tax.taxAfterRebate + tax.surcharge) * 0.04);
    }
    tax.grossTaxLiability = tax.taxAfterRebate + tax.surcharge + tax.cess;
  }

  tax.netTaxLiability = Math.max(0, tax.grossTaxLiability - tax.relief89 - tax.relief90_91);
  tax.totalTaxAndInterest = tax.netTaxLiability + tax.interest234A + tax.interest234B + tax.interest234C + tax.fee234F;

  // Taxes Paid & Refund / Demand
  paid.totalTaxesPaid = paid.advanceTax + paid.tdsSalary + paid.tdsNonSalary + paid.tcs + paid.selfAssessmentTax;

  if (paid.totalTaxesPaid >= tax.totalTaxAndInterest) {
    paid.refundDue = roundOff288B(paid.totalTaxesPaid - tax.totalTaxAndInterest);
    paid.taxPayable = 0;
  } else {
    paid.refundDue = 0;
    paid.taxPayable = roundOff288B(tax.totalTaxAndInterest - paid.totalTaxesPaid);
  }

  return {
    ...data,
    incomeHeads: inc,
    deductions: ded,
    taxComputation: tax,
    taxesPaid: paid,
  };
}

/**
 * Parses raw text extracted from ITR-V Acknowledgement or ITR Form PDF.
 */
export function parseITRFromText(rawText: string, fileName = 'ITR_Document.pdf'): CompleteITRData {
  const base = getDefaultITRData();
  base.sourceFileName = fileName;
  base.extractionMethod = 'pdf_text';

  const text = rawText.replace(/\r\n/g, '\n');

  // 1. PAN Extraction (5 uppercase letters, 4 numbers, 1 uppercase letter)
  const panMatch = text.match(/\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b/);
  if (panMatch) base.personalInfo.pan = panMatch[1];

  // 2. Assessment Year
  const ayMatch = text.match(/(?:Assessment\s*Year|AY|A\.Y\.)\s*[:\-]?\s*(\d{4}[-–]\d{2,4})/i) || text.match(/\b(20\d{2}[-–]\d{2,4})\b/);
  if (ayMatch) {
    let ay = ayMatch[1].replace('–', '-');
    if (ay.length === 7) base.personalInfo.assessmentYear = ay;
    const startYear = parseInt(ay.substring(0, 4));
    if (!isNaN(startYear)) {
      base.personalInfo.financialYear = `${startYear - 1}-${(startYear % 100).toString().padStart(2, '0')}`;
    }
  }

  // 3. Form Type
  const formMatch = text.match(/\b(ITR-[1-7]|ITR-V|ITR\s*[1-7]|Sahaj|Sugam)\b/i);
  if (formMatch) {
    const rawForm = formMatch[1].toUpperCase();
    if (rawForm.includes('1') || rawForm.includes('SAHAJ')) base.personalInfo.formType = 'ITR-1';
    else if (rawForm.includes('2')) base.personalInfo.formType = 'ITR-2';
    else if (rawForm.includes('3')) base.personalInfo.formType = 'ITR-3';
    else if (rawForm.includes('4') || rawForm.includes('SUGAM')) base.personalInfo.formType = 'ITR-4';
    else if (rawForm.includes('5')) base.personalInfo.formType = 'ITR-5';
    else if (rawForm.includes('6')) base.personalInfo.formType = 'ITR-6';
    else if (rawForm.includes('7')) base.personalInfo.formType = 'ITR-7';
    else if (rawForm.includes('V')) base.personalInfo.formType = 'ITR-V';
  }

  // 4. Name extraction
  const namePatterns = [
    /(?:Name\s*of\s*the\s*Assessee|Name\s*of\s*Assessee|Assessee\s*Name|Name)\s*[:\-]?\s*([A-Za-z\s\.]{3,50})/i,
    /(?:Shri\/Smt\/M\/s|Mr\.|Ms\.|Dr\.)\s*([A-Za-z\s\.]{3,40})/i,
  ];
  for (const pat of namePatterns) {
    const m = text.match(pat);
    if (m && m[1].trim().length > 2 && !m[1].toLowerCase().includes('income') && !m[1].toLowerCase().includes('return')) {
      base.personalInfo.name = m[1].trim().toUpperCase();
      break;
    }
  }

  // 5. Acknowledgment Number (15 digits)
  const ackMatch = text.match(/(?:Acknowledgment\s*Number|Acknowledgement\s*No|Ack\s*No|Receipt\s*No)\s*[:\-]?\s*(\d{14,16})/i) || text.match(/\b(\d{15})\b/);
  if (ackMatch) {
    base.personalInfo.ackNumber = ackMatch[1];
  }

  // 6. Filing Date
  const dateMatch = text.match(/(?:Date\s*of\s*Filing|Filed\s*on|Date|Verification\s*Date)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})/i);
  if (dateMatch) {
    base.personalInfo.filingDate = dateMatch[1];
  }

  // 7. Tax Regime
  if (/new\s*tax\s*regime|115BAC\s*opted|115BAC\s*\(1A\)|new\s*regime/i.test(text)) {
    base.personalInfo.taxRegime = 'New Regime';
  } else if (/old\s*tax\s*regime|old\s*regime|opted\s*out\s*of\s*115BAC/i.test(text)) {
    base.personalInfo.taxRegime = 'Old Regime';
  }

  // Father's Name
  const fatherMatch = text.match(/(?:Father's\s*Name|son\/daughter\s*of|Father\s*Name)\s*[:\-]?\s*([A-Za-z\s\.]{3,50})/i);
  if (fatherMatch && !fatherMatch[1].toLowerCase().includes('income')) {
    base.personalInfo.fatherName = fatherMatch[1].trim().toUpperCase();
  }

  // Mobile & Email
  const mobileMatch = text.match(/(?:Mobile|Phone|Contact)\s*[:\-]?\s*(\+?91[\s\-]?[6-9]\d{9}|[6-9]\d{9})/i);
  if (mobileMatch) base.personalInfo.mobile = mobileMatch[1].trim();

  const emailMatch = text.match(/\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b/);
  if (emailMatch && !emailMatch[1].includes('incometax.gov.in') && !emailMatch[1].includes('example.com')) {
    base.personalInfo.email = emailMatch[1].trim();
  }

  // Address, City & Pincode
  const pinMatch = text.match(/\b(3\d{5}|4\d{5}|5\d{5}|6\d{5}|1\d{5}|2\d{5}|7\d{5}|8\d{5})\b/);
  if (pinMatch) base.personalInfo.pincode = pinMatch[1];

  const cityMatch = text.match(/(?:City\/Town\/District|City|District)\s*[:\-]?\s*([A-Za-z\s]{3,30})/i);
  if (cityMatch) base.personalInfo.city = cityMatch[1].trim().toUpperCase();

  // Bank details
  const ifscMatch = text.match(/\b([A-Z]{4}0[A-Z0-9]{6})\b/);
  if (ifscMatch) base.personalInfo.bankIfsc = ifscMatch[1];

  const acctMatch = text.match(/(?:Account\s*Number|Bank\s*A\/c|A\/c\s*No)\s*[:\-]?\s*(\d{9,18})/i);
  if (acctMatch) base.personalInfo.bankAccountNumber = acctMatch[1];

  function extractAmount(patterns: RegExp[]): number {
    for (const pat of patterns) {
      const match = text.match(pat);
      if (match && match[1]) {
        const num = parseIndianNumber(match[1]);
        if (num !== 0) return num;
      }
    }
    return 0;
  }

  // Gross Salary
  base.incomeHeads.salaryGross = extractAmount([
    /(?:Gross\s*Salary|Salary\s*as\s*per\s*section\s*17\(1\)|Income\s*from\s*Salary)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
    /(?:1\.\s*Gross\s*Salary)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
    /(?:1a\s*Salary\s*as\s*per\s*section\s*17\(1\))\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);

  base.incomeHeads.salaryStandardDeduction = extractAmount([
    /(?:Standard\s*Deduction\s*u\/s\s*16\(ia\)|Standard\s*Deduction|5a\s*Standard\s*deduction)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  if (base.incomeHeads.salaryStandardDeduction === 0 && base.incomeHeads.salaryGross > 0) {
    base.incomeHeads.salaryStandardDeduction = base.personalInfo.assessmentYear >= '2025' ? 75000 : 50000;
  }

  base.incomeHeads.housePropertyGross = extractAmount([
    /(?:Gross\s*Rent\s*Received|Annual\s*Value\s*of\s*House|Income\s*from\s*House\s*Property)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);

  base.incomeHeads.businessGrossReceipts = extractAmount([
    /(?:Gross\s*Turnover|Gross\s*Receipts\s*u\/s\s*44AD|Total\s*Turnover)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.businessNetProfit = extractAmount([
    /(?:Profits\s*and\s*gains\s*of\s*business|Income\s*from\s*Business\s*or\s*Profession|Net\s*Profit\s*as\s*per\s*P&L)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);

  // Capital Gains Breakdown
  base.incomeHeads.capitalGainsSTCG_20Pct = extractAmount([
    /(?:Short-term\s*capital\s*gain.*111A.*20%|STCG\s*@\s*20%|A2e\s*Short-term)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.capitalGainsSTCG_15Pct = extractAmount([
    /(?:Short-term\s*capital\s*gain.*111A.*15%|STCG\s*@\s*15%)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.capitalGainsLTCG_12_5Pct = extractAmount([
    /(?:Long-term\s*capital\s*gain.*112A.*12\.5%|LTCG\s*@\s*12\.5%|B3a\s*Pass\s*through.*112A)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.capitalGainsLTCG_10Pct = extractAmount([
    /(?:Long-term\s*capital\s*gain.*112A.*10%|LTCG\s*@\s*10%)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);

  base.incomeHeads.capitalGainsNet = extractAmount([
    /(?:Total\s*Capital\s*Gains|Income\s*from\s*Capital\s*Gains|Net\s*Capital\s*Gains|3c\s*Total\s*Capital\s*Gains)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  if (base.incomeHeads.capitalGainsNet === 0 && (base.incomeHeads.capitalGainsSTCG_20Pct || base.incomeHeads.capitalGainsLTCG_12_5Pct)) {
    base.incomeHeads.capitalGainsNet = (base.incomeHeads.capitalGainsSTCG_20Pct || 0) + (base.incomeHeads.capitalGainsLTCG_12_5Pct || 0) + base.incomeHeads.capitalGainsSTCG_15Pct + base.incomeHeads.capitalGainsLTCG_10Pct;
  }

  // Other Sources
  base.incomeHeads.otherSourcesDividends = extractAmount([
    /(?:Dividend\s*income|Dividends\s*from\s*Indian\s*companies|1a\s*Dividends)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.otherSourcesInterestSavings = extractAmount([
    /(?:Interest\s*from\s*Savings\s*Bank|Savings\s*Bank\s*Interest|1b_i\s*From\s*Savings\s*Bank)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.otherSourcesInterestDeposits = extractAmount([
    /(?:Interest\s*on\s*Fixed\s*Deposits|Term\s*Deposits|1b_ii\s*From\s*Deposit)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  base.incomeHeads.otherSourcesNet = extractAmount([
    /(?:Income\s*from\s*Other\s*Sources|Total\s*Other\s*Sources|Other\s*Sources\s*Income|Net\s*Income\s*from\s*Other\s*Sources|9\s*Income\s*under\s*the\s*head\s*Other\s*sources)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  if (base.incomeHeads.otherSourcesNet === 0 && (base.incomeHeads.otherSourcesDividends > 0 || base.incomeHeads.otherSourcesInterestSavings > 0)) {
    base.incomeHeads.otherSourcesNet = base.incomeHeads.otherSourcesDividends + base.incomeHeads.otherSourcesInterestSavings + base.incomeHeads.otherSourcesInterestDeposits;
  }

  const extractedGTI = extractAmount([
    /(?:Gross\s*Total\s*Income|GTI|Part\s*B.*TI.*Gross\s*Total\s*Income)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  if (extractedGTI > 0) base.incomeHeads.grossTotalIncome = extractedGTI;

  // Deductions
  base.deductions.sec80C = extractAmount([/(?:80C|Section\s*80C)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.deductions.sec80D = extractAmount([/(?:80D|Section\s*80D)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.deductions.sec80CCD1B = extractAmount([/(?:80CCD\(1B\)|NPS\s*80CCD)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.deductions.sec80CCD2 = extractAmount([/(?:80CCD\(2\)|Employer\s*NPS)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.deductions.sec80G = extractAmount([/(?:80G|Section\s*80G|Donations)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.deductions.sec80TTA = extractAmount([/(?:80TTA|Section\s*80TTA)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);

  const totalDeductionsExtracted = extractAmount([
    /(?:Total\s*Deductions\s*under\s*Chapter\s*VI-A|Total\s*Chapter\s*VI-A\s*Deductions|Total\s*Deductions)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i,
  ]);
  if (totalDeductionsExtracted > 0) base.deductions.totalDeductions = totalDeductionsExtracted;

  // Taxes Paid
  base.taxesPaid.advanceTax = extractAmount([/(?:Advance\s*Tax)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.tdsSalary = extractAmount([/(?:TDS\s*on\s*Salary|TDS\s*192|Schedule\s*TDS1|TDS\s*as\s*per\s*Form\s*16)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.tdsNonSalary = extractAmount([/(?:TDS\s*on\s*other\s*than\s*Salary|TDS\s*Non-Salary|Schedule\s*TDS2)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.tcs = extractAmount([/(?:TCS|Tax\s*Collected\s*at\s*Source)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.selfAssessmentTax = extractAmount([/(?:Self\s*Assessment\s*Tax|SAT)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.refundDue = extractAmount([/(?:Refund\s*Due|Refund\s*Claimed|Net\s*Refund|5\s*Refund)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);
  base.taxesPaid.taxPayable = extractAmount([/(?:Net\s*Tax\s*Payable|Amount\s*Payable|Balance\s*Tax\s*Payable|4\s*Net\s*tax\s*payable)\s*[:\-]?\s*([₹Rs\.\d,\s]+)/i]);

  return recalculateITR(base);
}

/**
 * Parses official JSON schema exported from Income Tax e-filing portal
 */
export function parseITRFromJSON(jsonObj: any, fileName = 'ITR_Efiling.json'): CompleteITRData {
  const base = getDefaultITRData();
  base.sourceFileName = fileName;
  base.extractionMethod = 'json_efiling';

  const root = jsonObj.ITR || jsonObj.ITR1 || jsonObj.ITR2 || jsonObj.ITR3 || jsonObj.ITR4 || jsonObj;
  const personal = root.PersonalInfo || root.PersonalDetails || root.CreationInfo || {};
  const incomeDeductions = root.IncomeDeductions || root.PartB_TI || root.ScheduleSalary || {};
  const taxPaid = root.TaxPaid || root.TaxesPaid || root.ScheduleIT || {};

  // Personal Info
  if (personal.PAN) base.personalInfo.pan = personal.PAN;
  if (personal.AssesseeName?.FirstName || personal.AssesseeName?.SurNameOrOrgName) {
    const parts = [
      personal.AssesseeName?.FirstName,
      personal.AssesseeName?.MiddleName,
      personal.AssesseeName?.SurNameOrOrgName,
    ].filter(Boolean);
    base.personalInfo.name = parts.join(' ').toUpperCase();
  } else if (personal.Name) {
    base.personalInfo.name = String(personal.Name).toUpperCase();
  }

  if (personal.DOB) base.personalInfo.dob = personal.DOB;
  if (personal.AadhaarCardNo) base.personalInfo.aadhaar = personal.AadhaarCardNo;
  if (personal.MobileNo) base.personalInfo.mobile = String(personal.MobileNo);
  if (personal.EmailAddress) base.personalInfo.email = String(personal.EmailAddress);

  if (root.FormName || root.Form_ITR) {
    base.personalInfo.formType = (root.FormName || root.Form_ITR) as any;
  }
  if (root.AssessmentYear || root.AY) {
    base.personalInfo.assessmentYear = String(root.AssessmentYear || root.AY);
  }

  // Salary
  if (incomeDeductions.GrossSalary) base.incomeHeads.salaryGross = parseIndianNumber(incomeDeductions.GrossSalary);
  if (incomeDeductions.DeductionUs16ia) base.incomeHeads.salaryStandardDeduction = parseIndianNumber(incomeDeductions.DeductionUs16ia);
  if (incomeDeductions.TotalIncomeOfHP) base.incomeHeads.housePropertyNet = parseIndianNumber(incomeDeductions.TotalIncomeOfHP);
  if (incomeDeductions.IncomeOthSrc) base.incomeHeads.otherSourcesNet = parseIndianNumber(incomeDeductions.IncomeOthSrc);
  if (incomeDeductions.GrossTotIncome) base.incomeHeads.grossTotalIncome = parseIndianNumber(incomeDeductions.GrossTotIncome);

  // Deductions
  const ded = incomeDeductions.Us80C || incomeDeductions.DeductUndChapVIA || {};
  if (ded.Section80C) base.deductions.sec80C = parseIndianNumber(ded.Section80C);
  if (ded.Section80D) base.deductions.sec80D = parseIndianNumber(ded.Section80D);
  if (ded.Section80CCD1B) base.deductions.sec80CCD1B = parseIndianNumber(ded.Section80CCD1B);
  if (ded.Section80CCD2) base.deductions.sec80CCD2 = parseIndianNumber(ded.Section80CCD2);
  if (ded.Section80G) base.deductions.sec80G = parseIndianNumber(ded.Section80G);
  if (ded.TotalChapVIADeductions) base.deductions.totalDeductions = parseIndianNumber(ded.TotalChapVIADeductions);

  // Tax Paid
  if (taxPaid.TaxesPaid?.TotalTaxesPaid) base.taxesPaid.totalTaxesPaid = parseIndianNumber(taxPaid.TaxesPaid.TotalTaxesPaid);
  if (taxPaid.TaxesPaid?.AdvanceTax) base.taxesPaid.advanceTax = parseIndianNumber(taxPaid.TaxesPaid.AdvanceTax);
  if (taxPaid.TaxesPaid?.TDS) base.taxesPaid.tdsSalary = parseIndianNumber(taxPaid.TaxesPaid.TDS);
  if (taxPaid.Refund?.RefundDue) base.taxesPaid.refundDue = parseIndianNumber(taxPaid.Refund.RefundDue);
  if (taxPaid.BalTaxPayable) base.taxesPaid.taxPayable = parseIndianNumber(taxPaid.BalTaxPayable);

  return recalculateITR(base);
}

/**
 * Built-in Sample Datasets for CA Practice & instant testing
 */
export const SAMPLE_ITR_DATASETS: { id: string; label: string; desc: string; data: CompleteITRData }[] = [
  {
    id: 'sample_salaried_itr1',
    label: 'ITR-1: Sahaj (Salaried Individual)',
    desc: 'Salary ₹12.5L, Standard Deduction ₹50K, 80C ₹1.5L, 80D ₹25K, Savings Interest ₹15K • Old Regime',
    data: recalculateITR({
      ...getDefaultITRData(),
      id: 'sample_itr1_sahaj',
      sourceFileName: 'Sample_ITR1_Sahaj.pdf',
      personalInfo: {
        ...getDefaultITRData().personalInfo,
        name: 'RAHUL SURESH SHARMA',
        pan: 'ABCPR1234D',
        aadhaar: '5xxx xxxx 1234',
        formType: 'ITR-1',
        status: 'Individual',
        taxRegime: 'Old Regime',
        assessmentYear: '2024-25',
        financialYear: '2023-24',
        ackNumber: '102938475610293',
        filingDate: '20/07/2024',
        city: 'Pune',
        state: 'Maharashtra',
        bankName: 'State Bank of India',
        bankAccountNumber: '30291827364',
        bankIfsc: 'SBIN0001428',
      },
      incomeHeads: {
        ...getDefaultITRData().incomeHeads,
        salaryGross: 1250000,
        salaryExemptAllowances: 0,
        salaryStandardDeduction: 50000,
        salaryProfessionalTax: 2400,
        salaryNet: 1197600,
        housePropertyGross: 0,
        housePropertyTaxes: 0,
        housePropertyStandardDeduction: 0,
        housePropertyInterest: 0,
        housePropertyNet: 0,
        businessGrossReceipts: 0,
        businessGrossProfit: 0,
        businessExpenses: 0,
        businessNetProfit: 0,
        businessPresumptive44AD: 0,
        businessPresumptive44ADA: 0,
        capitalGainsSTCG_15Pct: 0,
        capitalGainsSTCG_20Pct: 0,
        capitalGainsSTCG_Slab: 0,
        capitalGainsLTCG_10Pct: 0,
        capitalGainsLTCG_12_5Pct: 0,
        capitalGainsLTCG_20Pct: 0,
        capitalGainsNet: 0,
        otherSourcesInterestSavings: 15400,
        otherSourcesInterestDeposits: 0,
        otherSourcesDividends: 0,
        otherSourcesOthers: 0,
        otherSourcesNet: 15400,
        grossTotalIncome: 1213000,
      },
      deductions: {
        ...getDefaultITRData().deductions,
        sec80C: 150000,
        sec80D: 25000,
        sec80TTA: 10000,
        totalDeductions: 185000,
      },
      taxComputation: {
        ...getDefaultITRData().taxComputation,
        totalTaxableIncome: 1028000,
        taxOnTotalIncome: 120900,
        specialRateTax: 0,
        rebate87A: 0,
        taxAfterRebate: 120900,
        surcharge: 0,
        cess: 4836,
        grossTaxLiability: 125736,
        netTaxLiability: 125736,
        totalTaxAndInterest: 125736,
      },
      taxesPaid: {
        advanceTax: 0,
        tdsSalary: 135000,
        tdsNonSalary: 0,
        tcs: 0,
        selfAssessmentTax: 0,
        totalTaxesPaid: 135000,
        refundDue: 9264,
        taxPayable: 0,
      },
    }),
  },
  {
    id: 'sample_jaimin_itr2',
    label: 'ITR-2: Jaimin Patel (Salary + STCG/LTCG)',
    desc: 'Salary ₹27.08L, STCG 111A ₹1.16L, LTCG 112A ₹11.7K, Dividend ₹13.5K, TDS ₹4.46L • Net Refund ₹33,210',
    data: getDefaultITRData(),
  },
  {
    id: 'sample_business_itr3',
    label: 'ITR-3: CA / Consultant (PGBP + Capital Gains)',
    desc: 'Professional with Gross Receipts ₹28.5L, Equity Gains ₹2.25L, 80C & Medical • Old Regime',
    data: recalculateITR({
      ...getDefaultITRData(),
      id: 'sample_itr3',
      sourceFileName: 'Sample_ITR3_Professional.pdf',
      personalInfo: {
        ...getDefaultITRData().personalInfo,
        name: 'PRIYA SUNDARAM & ASSOCIATES',
        pan: 'AAAFP9876Q',
        formType: 'ITR-3',
        status: 'Individual',
        taxRegime: 'Old Regime',
        assessmentYear: '2024-25',
        financialYear: '2023-24',
        ackNumber: '918274019283746',
        filingDate: '31/10/2024',
        city: 'Mumbai',
        state: 'Maharashtra',
      },
      incomeHeads: {
        ...getDefaultITRData().incomeHeads,
        salaryGross: 0,
        salaryStandardDeduction: 0,
        salaryNet: 0,
        businessGrossReceipts: 2850000,
        businessGrossProfit: 2850000,
        businessExpenses: 1120000,
        businessNetProfit: 1730000,
        housePropertyGross: 360000,
        housePropertyTaxes: 15000,
        housePropertyStandardDeduction: 103500,
        housePropertyInterest: 180000,
        housePropertyNet: 61500,
        capitalGainsSTCG_15Pct: 85000,
        capitalGainsLTCG_10Pct: 140000,
        capitalGainsNet: 225000,
        otherSourcesInterestDeposits: 64000,
        otherSourcesDividends: 22000,
        otherSourcesNet: 86000,
        grossTotalIncome: 2102500,
      },
      deductions: {
        ...getDefaultITRData().deductions,
        sec80C: 150000,
        sec80D: 45000,
        sec80CCD1B: 50000,
        sec80G: 25000,
        sec80TTA: 10000,
        totalDeductions: 280000,
      },
      taxComputation: {
        ...getDefaultITRData().taxComputation,
        taxOnTotalIncome: 359250,
        specialRateTax: 16750,
        rebate87A: 0,
        surcharge: 0,
        cess: 15040,
        grossTaxLiability: 391040,
        netTaxLiability: 391040,
        totalTaxAndInterest: 391040,
      },
      taxesPaid: {
        advanceTax: 320000,
        tdsSalary: 0,
        tdsNonSalary: 95000,
        tcs: 0,
        selfAssessmentTax: 0,
        totalTaxesPaid: 415000,
        refundDue: 23960,
        taxPayable: 0,
      },
    }),
  },
  {
    id: 'sample_presumptive_itr4',
    label: 'ITR-4 Sugam: Presumptive Business (Sec 44AD)',
    desc: 'Retail Trader with ₹48.5L Turnover declaring 8% Net Profit (₹3.88L) • Zero Tax with 87A Rebate',
    data: recalculateITR({
      ...getDefaultITRData(),
      id: 'sample_itr4',
      sourceFileName: 'Sample_ITR4_Sugam.pdf',
      personalInfo: {
        ...getDefaultITRData().personalInfo,
        name: 'VIKRAM TRADING COMPANY (PROP. VIKRAM MEHTA)',
        pan: 'BKMPM4567K',
        formType: 'ITR-4',
        status: 'Individual',
        taxRegime: 'New Regime',
        assessmentYear: '2024-25',
        financialYear: '2023-24',
        ackNumber: '654321098765432',
        filingDate: '15/07/2024',
        city: 'Ahmedabad',
        state: 'Gujarat',
      },
      incomeHeads: {
        ...getDefaultITRData().incomeHeads,
        salaryGross: 0,
        salaryStandardDeduction: 0,
        salaryNet: 0,
        businessGrossReceipts: 4850000,
        businessPresumptive44AD: 388000,
        businessNetProfit: 388000,
        otherSourcesInterestSavings: 12400,
        otherSourcesNet: 12400,
        grossTotalIncome: 400400,
      },
      deductions: {
        ...getDefaultITRData().deductions,
        totalDeductions: 0,
      },
      taxesPaid: {
        advanceTax: 0,
        tdsSalary: 0,
        tdsNonSalary: 4850,
        tcs: 0,
        selfAssessmentTax: 0,
        totalTaxesPaid: 4850,
        refundDue: 4850,
        taxPayable: 0,
      },
    }),
  },
];
