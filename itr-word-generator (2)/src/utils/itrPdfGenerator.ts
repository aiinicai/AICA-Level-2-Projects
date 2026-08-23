/**
 * Professional PDF Document Generator for Indian ITRs.
 * Uses jsPDF and jspdf-autotable to produce publication-grade, CA-compliant
 * Computation of Total Income and Tax Liability statements matching the approved Word layout.
 */

import { jsPDF } from 'jspdf';
import autoTable, { UserOptions } from 'jspdf-autotable';
import { saveAs } from 'file-saver';
import { CompleteITRData, DocxStyleConfig } from '../itr-types';
import { formatIndianCurrency, numberToIndianRupeesWords } from './numberParsing';

interface PdfPalette {
  primary: [number, number, number];       // Primary header & accent [R, G, B]
  primaryHex: string;
  secondaryBg: [number, number, number];   // Light background for table headers
  borderColor: [number, number, number];   // Table border color
  highlightBg: [number, number, number];   // Total row highlight
  accentText: [number, number, number];    // Subheading accent
  textDark: [number, number, number];
  textMuted: [number, number, number];
}

const PDF_PALETTES: Record<DocxStyleConfig['themeColor'], PdfPalette> = {
  navy: {
    primary: [30, 58, 138],        // #1E3A8A
    primaryHex: '#1E3A8A',
    secondaryBg: [224, 231, 255],  // #E0E7FF
    borderColor: [203, 213, 225],  // #CBD5E1
    highlightBg: [241, 245, 249],  // #F1F5F9
    accentText: [30, 64, 175],     // #1E40AF
    textDark: [17, 24, 39],
    textMuted: [100, 116, 139],
  },
  slate: {
    primary: [51, 65, 85],         // #334155
    primaryHex: '#334155',
    secondaryBg: [241, 245, 249],  // #F1F5F9
    borderColor: [226, 232, 240],  // #E2E8F0
    highlightBg: [248, 250, 252],  // #F8FAFC
    accentText: [71, 85, 105],     // #475569
    textDark: [17, 24, 39],
    textMuted: [100, 116, 139],
  },
  emerald: {
    primary: [6, 95, 70],          // #065F46
    primaryHex: '#065F46',
    secondaryBg: [209, 250, 229],  // #D1FAE5
    borderColor: [167, 243, 208],  // #A7F3D0
    highlightBg: [236, 253, 245],  // #ECFDF5
    accentText: [4, 120, 87],      // #047857
    textDark: [17, 24, 39],
    textMuted: [100, 116, 139],
  },
  burgundy: {
    primary: [131, 24, 67],        // #831843
    primaryHex: '#831843',
    secondaryBg: [252, 231, 243],  // #FCE7F3
    borderColor: [251, 207, 232],  // #FBCFE8
    highlightBg: [255, 241, 242],  // #FFF1F2
    accentText: [157, 23, 77],     // #9D174D
    textDark: [17, 24, 39],
    textMuted: [100, 116, 139],
  },
  classic: {
    primary: [24, 24, 27],         // #18181B
    primaryHex: '#18181B',
    secondaryBg: [244, 244, 245],  // #F4F4F5
    borderColor: [228, 228, 231],  // #E4E4E7
    highlightBg: [250, 250, 250],  // #FAFAFA
    accentText: [39, 39, 42],      // #27272A
    textDark: [17, 24, 39],
    textMuted: [100, 116, 139],
  },
};

/**
 * Builds the complete jsPDF computation document
 */
export function buildITRPdfDocument(data: CompleteITRData): jsPDF {
  const cfg = data.styleConfig || {
    documentTitle: 'COMPUTATION OF TOTAL INCOME & TAX LIABILITY',
    subtitle: '',
    themeColor: 'navy',
    fontFamily: 'Calibri',
    includeHeaderFooter: true,
    includeIndianRupeeWords: true,
    includeTaxComputationTable: true,
    includeDeductionsBreakdown: true,
    includeTaxesPaidBreakdown: true,
    includeBankDetails: true,
    includeVerificationClause: false,
    fontSize: 'standard',
    layoutType: 'standard_computation',
  };

  const palette = PDF_PALETTES[cfg.themeColor] || PDF_PALETTES.navy;
  const p = data.personalInfo;
  const inc = data.incomeHeads;
  const ded = data.deductions;
  const tax = data.taxComputation;
  const paid = data.taxesPaid;

  // Initialize jsPDF A4 portrait
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'pt',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 36; // 0.5 inch (36 pt)
  const contentWidth = pageWidth - margin * 2;

  let currentY = margin + 10;

  // 1. Header Title & Subtitle
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text(cfg.documentTitle.toUpperCase(), pageWidth / 2, currentY, { align: 'center' });

  currentY += 16;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9.5);
  doc.setTextColor(75, 85, 99);
  const subtitle = cfg.subtitle || `Assessment Year ${p.assessmentYear} | Financial Year ${p.financialYear}`;
  doc.text(subtitle, pageWidth / 2, currentY, { align: 'center' });

  currentY += 16;

  // 2. Personal Info Table (2-Column Key Value Grid)
  const personalInfoBody: any[] = [
    [
      { content: `Name of Assessee: ${p.name || '-'}`, styles: { fontStyle: 'bold' } },
      { content: `Permanent Account Number (PAN): ${p.pan || '-'}`, styles: { fontStyle: 'bold' } },
    ],
    [
      { content: `Status / Constitution: ${p.status || 'Individual'}` },
      { content: `Tax Regime: ${(p.taxRegime && p.taxRegime.includes('Old')) ? 'Old Regime' : 'New Regime'}` },
    ],
    [
      { content: `Assessment Year: ${p.assessmentYear} (FY ${p.financialYear})` },
      { content: `Form Type Filed: ${p.formType} u/s ${p.filingStatus}` },
    ],
    [
      { content: `Acknowledgment / Receipt No.: ${p.ackNumber || 'N/A'}` },
      { content: `Filing / E-Verification Date: ${p.filingDate || 'N/A'}` },
    ],
    [
      { content: `Residential Status: ${p.residentialStatus || 'Resident'}` },
      { content: `Contact / Email: ${[p.mobile, p.email].filter(Boolean).join(' | ') || '-'}` },
    ],
  ];

  if (p.address) {
    personalInfoBody.push([
      {
        content: `Registered Address: ${[p.address, p.city, p.state, p.pincode].filter(Boolean).join(', ')}`,
        colSpan: 2,
      },
    ]);
  }

  autoTable(doc, {
    startY: currentY,
    margin: { left: margin, right: margin },
    body: personalInfoBody,
    theme: 'grid',
    styles: {
      fontSize: 8.5,
      cellPadding: 4,
      textColor: [17, 24, 39],
      lineColor: palette.borderColor,
      lineWidth: 0.5,
      fillColor: [250, 250, 250],
    },
    columnStyles: {
      0: { cellWidth: contentWidth / 2 },
      1: { cellWidth: contentWidth / 2 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 12;

  // 3. Section I: Computation of Total Income
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text('I. COMPUTATION OF TOTAL INCOME', margin, currentY);

  currentY += 6;

  const computationRows: any[] = [];

  const addCompRow = (
    sr: string,
    particulars: string,
    a1: number | string,
    a2: number | string,
    opts: { isHeader?: boolean; isTotal?: boolean; indent?: boolean } = {}
  ) => {
    const a1Str = typeof a1 === 'number' ? (a1 !== 0 ? formatIndianCurrency(a1, { showSymbol: false }) : '-') : a1;
    const a2Str = typeof a2 === 'number' ? (a2 !== 0 ? formatIndianCurrency(a2, { showSymbol: false }) : '-') : a2;

    const rowStyles: any = {};
    if (opts.isHeader) {
      rowStyles.fillColor = palette.secondaryBg;
      rowStyles.fontStyle = 'bold';
      rowStyles.textColor = palette.textDark;
    } else if (opts.isTotal) {
      rowStyles.fillColor = palette.highlightBg;
      rowStyles.fontStyle = 'bold';
      rowStyles.textColor = palette.accentText;
    }

    computationRows.push([
      { content: sr, styles: { halign: 'center', ...rowStyles } },
      { content: (opts.indent ? '     •  ' : '') + particulars, styles: { ...rowStyles } },
      { content: a1Str, styles: { halign: 'right', ...rowStyles } },
      { content: a2Str, styles: { halign: 'right', ...rowStyles } },
    ]);
  };

  // Head 1: Salary
  if (inc.salaryGross > 0 || inc.salaryNet > 0) {
    addCompRow('I', 'INCOME FROM SALARY', '', '', { isHeader: true });
    addCompRow('', 'Gross Salary / Pension u/s 17(1)', inc.salaryGross, '', { indent: true });
    if (inc.salaryExemptAllowances > 0) {
      addCompRow('', 'Less: Allowances Exempt u/s 10', `(${formatIndianCurrency(inc.salaryExemptAllowances, { showSymbol: false })})`, '', { indent: true });
    }
    if (inc.salaryStandardDeduction > 0) {
      addCompRow('', 'Less: Standard Deduction u/s 16(ia)', `(${formatIndianCurrency(inc.salaryStandardDeduction, { showSymbol: false })})`, '', { indent: true });
    }
    if (inc.salaryProfessionalTax > 0) {
      addCompRow('', 'Less: Professional Tax / Entertainment Allow. u/s 16(iii)', `(${formatIndianCurrency(inc.salaryProfessionalTax, { showSymbol: false })})`, '', { indent: true });
    }
    addCompRow('', 'Net Income Chargeable under the Head Salaries', '', inc.salaryNet, { isTotal: true });
  }

  // Head 2: House Property
  if (inc.housePropertyGross > 0 || inc.housePropertyNet !== 0) {
    addCompRow('II', 'INCOME FROM HOUSE PROPERTY', '', '', { isHeader: true });
    addCompRow('', 'Gross Annual Rent Received / Receivable', inc.housePropertyGross, '', { indent: true });
    if (inc.housePropertyTaxes > 0) {
      addCompRow('', 'Less: Municipal / Local Taxes Paid', `(${formatIndianCurrency(inc.housePropertyTaxes, { showSymbol: false })})`, '', { indent: true });
    }
    if (inc.housePropertyStandardDeduction > 0) {
      addCompRow('', 'Less: 30% Standard Deduction u/s 24(a)', `(${formatIndianCurrency(inc.housePropertyStandardDeduction, { showSymbol: false })})`, '', { indent: true });
    }
    if (inc.housePropertyInterest > 0) {
      addCompRow('', 'Less: Interest Payable on Housing Loan u/s 24(b)', `(${formatIndianCurrency(inc.housePropertyInterest, { showSymbol: false })})`, '', { indent: true });
    }
    addCompRow('', 'Net Income / (Loss) from House Property', '', inc.housePropertyNet, { isTotal: true });
  }

  // Head 3: Business/Profession
  if (inc.businessGrossReceipts > 0 || inc.businessNetProfit !== 0) {
    addCompRow('III', 'PROFITS AND GAINS OF BUSINESS OR PROFESSION', '', '', { isHeader: true });
    if (inc.businessPresumptive44AD > 0) {
      addCompRow('', `Presumptive Business Income u/s 44AD (Turnover: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44AD, '', { indent: true });
    } else if (inc.businessPresumptive44ADA > 0) {
      addCompRow('', `Presumptive Professional Income u/s 44ADA (Gross: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44ADA, '', { indent: true });
    } else {
      addCompRow('', 'Gross Turnover / Receipts from Business/Profession', inc.businessGrossReceipts, '', { indent: true });
      if (inc.businessExpenses > 0) {
        addCompRow('', 'Less: Total Operating & Administrative Expenses', `(${formatIndianCurrency(inc.businessExpenses, { showSymbol: false })})`, '', { indent: true });
      }
    }
    addCompRow('', 'Net Income from Business or Profession', '', inc.businessNetProfit, { isTotal: true });
  }

  // Head 4: Capital Gains
  const hasCG =
    inc.capitalGainsNet !== 0 ||
    inc.capitalGainsSTCG_15Pct > 0 ||
    Boolean(inc.capitalGainsSTCG_20Pct && inc.capitalGainsSTCG_20Pct > 0) ||
    inc.capitalGainsSTCG_Slab > 0 ||
    inc.capitalGainsLTCG_10Pct > 0 ||
    Boolean(inc.capitalGainsLTCG_12_5Pct && inc.capitalGainsLTCG_12_5Pct > 0) ||
    inc.capitalGainsLTCG_20Pct > 0;

  if (hasCG) {
    addCompRow('IV', 'CAPITAL GAINS', '', '', { isHeader: true });
    if (inc.capitalGainsSTCG_20Pct && inc.capitalGainsSTCG_20Pct > 0) {
      addCompRow('', 'Short Term Capital Gains u/s 111A (New Rate @ 20% / Post 23-Jul-2024)', inc.capitalGainsSTCG_20Pct, '', { indent: true });
    }
    if (inc.capitalGainsSTCG_15Pct > 0) {
      addCompRow('', 'Short Term Capital Gains u/s 111A (Old Rate @ 15% / Pre 23-Jul-2024)', inc.capitalGainsSTCG_15Pct, '', { indent: true });
    }
    if (inc.capitalGainsSTCG_Slab > 0) {
      addCompRow('', 'Short Term Capital Gains (Taxable at Applicable Slab Rates)', inc.capitalGainsSTCG_Slab, '', { indent: true });
    }
    if (inc.capitalGainsLTCG_12_5Pct && inc.capitalGainsLTCG_12_5Pct > 0) {
      addCompRow('', 'Long Term Capital Gains u/s 112A (New Rate @ 12.5% / Post 23-Jul-2024)', inc.capitalGainsLTCG_12_5Pct, '', { indent: true });
    }
    if (inc.capitalGainsLTCG_10Pct > 0) {
      addCompRow('', 'Long Term Capital Gains u/s 112A (Old Rate @ 10% / Pre 23-Jul-2024)', inc.capitalGainsLTCG_10Pct, '', { indent: true });
    }
    if (inc.capitalGainsLTCG_20Pct > 0) {
      addCompRow('', 'Long Term Capital Gains u/s 112 (Old Rate @ 20% with Indexation)', inc.capitalGainsLTCG_20Pct, '', { indent: true });
    }
    addCompRow('', 'Net Chargeable Capital Gains', '', inc.capitalGainsNet, { isTotal: true });
  }

  // Head 5: Other Sources
  if (inc.otherSourcesNet > 0 || inc.otherSourcesInterestSavings > 0 || inc.otherSourcesDividends > 0) {
    addCompRow('V', 'INCOME FROM OTHER SOURCES', '', '', { isHeader: true });
    if (inc.otherSourcesInterestSavings > 0) {
      addCompRow('', 'Interest from Savings Bank Accounts', inc.otherSourcesInterestSavings, '', { indent: true });
    }
    if (inc.otherSourcesInterestDeposits > 0) {
      addCompRow('', 'Interest on Fixed Deposits / Term Deposits / Bonds', inc.otherSourcesInterestDeposits, '', { indent: true });
    }
    if (inc.otherSourcesDividends > 0) {
      addCompRow('', 'Dividend Income from Indian Companies / Mutual Funds', inc.otherSourcesDividends, '', { indent: true });
    }
    if (inc.otherSourcesFamilyPension > 0) {
      addCompRow('', 'Family Pension Received', inc.otherSourcesFamilyPension, '', { indent: true });
    }
    if (inc.otherSourcesOthers > 0) {
      addCompRow('', 'Other Miscellaneous Income', inc.otherSourcesOthers, '', { indent: true });
    }
    if (inc.otherSourcesDeductions > 0) {
      addCompRow('', 'Less: Deduction u/s 57', `(${formatIndianCurrency(inc.otherSourcesDeductions, { showSymbol: false })})`, '', { indent: true });
    }
    addCompRow('', 'Net Income from Other Sources', '', inc.otherSourcesNet, { isTotal: true });
  }

  // Gross Total Income
  addCompRow('A', 'GROSS TOTAL INCOME (I + II + III + IV + V)', '', inc.grossTotalIncome, { isTotal: true });

  // Deductions
  if (ded.totalDeductions > 0) {
    addCompRow('B', 'LESS: DEDUCTIONS UNDER CHAPTER VI-A', '', '', { isHeader: true });
    if (ded.sec80C > 0) addCompRow('', 'Section 80C (LIC, PPF, EPF, ELSS, School Fees, Principal Loan)', ded.sec80C, '', { indent: true });
    if (ded.sec80CCD1B > 0) addCompRow('', 'Section 80CCD(1B) (National Pension Scheme - Additional ₹50,000)', ded.sec80CCD1B, '', { indent: true });
    if (ded.sec80CCD2 > 0) addCompRow('', 'Section 80CCD(2) (Employer Contribution to NPS)', ded.sec80CCD2, '', { indent: true });
    if (ded.sec80D > 0) addCompRow('', 'Section 80D (Health Insurance Premium / Medical Expenditure)', ded.sec80D, '', { indent: true });
    if (ded.sec80G > 0) addCompRow('', 'Section 80G (Donations to Approved Funds / Charities)', ded.sec80G, '', { indent: true });
    if (ded.sec80TTA > 0) addCompRow('', 'Section 80TTA (Interest on Savings Account up to ₹10,000)', ded.sec80TTA, '', { indent: true });
    if (ded.sec80TTB > 0) addCompRow('', 'Section 80TTB (Interest for Senior Citizens up to ₹50,000)', ded.sec80TTB, '', { indent: true });
    if (ded.otherDeductions > 0) addCompRow('', 'Other Applicable Deductions under Chapter VI-A', ded.otherDeductions, '', { indent: true });
    addCompRow('', 'Total Chapter VI-A Deductions Allowable', '', `(${formatIndianCurrency(ded.totalDeductions, { showSymbol: false })})`, { isTotal: true });
  }

  // Total Taxable Income
  addCompRow('C', 'TOTAL TAXABLE INCOME (Rounded off u/s 288A)', '', tax.totalTaxableIncome, { isTotal: true });

  autoTable(doc, {
    startY: currentY,
    margin: { left: margin, right: margin },
    head: [
      [
        { content: 'Sr.', styles: { halign: 'center', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Particulars of Income / Deductions', styles: { halign: 'left', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Details (₹)', styles: { halign: 'right', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Amount (₹)', styles: { halign: 'right', fillColor: palette.primary, textColor: [255, 255, 255] } },
      ],
    ],
    body: computationRows,
    theme: 'grid',
    styles: {
      fontSize: 8,
      cellPadding: 3.5,
      textColor: [17, 24, 39],
      lineColor: palette.borderColor,
      lineWidth: 0.5,
    },
    columnStyles: {
      0: { cellWidth: 32 },
      1: { cellWidth: contentWidth - 32 - 95 - 95 },
      2: { cellWidth: 95 },
      3: { cellWidth: 95 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 12;

  // 4. Section II: Computation of Tax Liability & Taxes Paid
  // Check if we need page break
  if (currentY > pageHeight - 160) {
    doc.addPage();
    currentY = margin + 10;
  }

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text('II. COMPUTATION OF TAX LIABILITY & TAXES PAID', margin, currentY);

  currentY += 6;

  const taxRows: any[] = [];
  const addTaxRow = (
    sr: string,
    particulars: string,
    a1: number | string,
    a2: number | string,
    opts: { isHeader?: boolean; isTotal?: boolean; indent?: boolean } = {}
  ) => {
    const a1Str = typeof a1 === 'number' ? (a1 !== 0 ? formatIndianCurrency(a1, { showSymbol: false }) : '-') : a1;
    const a2Str = typeof a2 === 'number' ? (a2 !== 0 ? formatIndianCurrency(a2, { showSymbol: false }) : '-') : a2;

    const rowStyles: any = {};
    if (opts.isHeader) {
      rowStyles.fillColor = palette.secondaryBg;
      rowStyles.fontStyle = 'bold';
      rowStyles.textColor = palette.textDark;
    } else if (opts.isTotal) {
      rowStyles.fillColor = palette.highlightBg;
      rowStyles.fontStyle = 'bold';
      rowStyles.textColor = palette.accentText;
    }

    taxRows.push([
      { content: sr, styles: { halign: 'center', ...rowStyles } },
      { content: (opts.indent ? '     •  ' : '') + particulars, styles: { ...rowStyles } },
      { content: a1Str, styles: { halign: 'right', ...rowStyles } },
      { content: a2Str, styles: { halign: 'right', ...rowStyles } },
    ]);
  };

  addTaxRow('1', 'Tax on Total Income (Calculated as per Applicable Slab Rates)', tax.taxOnTotalIncome, '');
  if (tax.specialRateTax > 0) {
    addTaxRow('2', 'Tax on Special Rate Incomes (STCG u/s 111A / LTCG u/s 112/112A)', tax.specialRateTax, '');
  }
  if (tax.rebate87A > 0) {
    addTaxRow('3', 'Less: Tax Rebate admissible u/s 87A', `(${formatIndianCurrency(tax.rebate87A, { showSymbol: false })})`, '');
  }
  addTaxRow('4', 'Tax Payable after Rebate', '', tax.taxAfterRebate, { isTotal: true });
  if (tax.surcharge > 0) {
    addTaxRow('5', 'Add: Surcharge on Tax', tax.surcharge, '');
  }
  addTaxRow('6', 'Add: Health & Education Cess @ 4%', tax.cess, '');
  addTaxRow('7', 'Gross Tax Liability', '', tax.grossTaxLiability, { isTotal: true });

  if (tax.relief89 > 0 || tax.relief90_91 > 0) {
    addTaxRow('8', 'Less: Relief u/s 89 / 90 / 91', `(${formatIndianCurrency(tax.relief89 + tax.relief90_91, { showSymbol: false })})`, '');
  }
  addTaxRow('9', 'Net Tax Liability', '', tax.netTaxLiability, { isTotal: true });

  if (tax.interest234A > 0 || tax.interest234B > 0 || tax.interest234C > 0 || tax.fee234F > 0) {
    taxRows.push([
      { content: '10', styles: { halign: 'center' } },
      { content: '     •  Interest u/s 234A (Delay in filing return)' },
      { content: formatIndianCurrency(tax.interest234A, { showSymbol: false }), styles: { halign: 'right' } },
      { content: '' },
    ]);
    taxRows.push([
      { content: '11', styles: { halign: 'center' } },
      { content: '     •  Interest u/s 234B (Default in payment of advance tax)' },
      { content: formatIndianCurrency(tax.interest234B, { showSymbol: false }), styles: { halign: 'right' } },
      { content: '' },
    ]);
    taxRows.push([
      { content: '12', styles: { halign: 'center' } },
      { content: '     •  Interest u/s 234C (Deferment of advance tax instalments)' },
      { content: formatIndianCurrency(tax.interest234C, { showSymbol: false }), styles: { halign: 'right' } },
      { content: '' },
    ]);
    if (tax.fee234F > 0) {
      taxRows.push([
        { content: '13', styles: { halign: 'center' } },
        { content: '     •  Late Filing Fee u/s 234F' },
        { content: formatIndianCurrency(tax.fee234F, { showSymbol: false }), styles: { halign: 'right' } },
        { content: '' },
      ]);
    }
  }

  addTaxRow('D', 'TOTAL TAX, CESS, FEE AND INTEREST PAYABLE', '', tax.totalTaxAndInterest, { isTotal: true });

  // Taxes Paid Section
  addTaxRow('E', 'TAXES PAID / PREPAID TAXES CREDITS', '', '', { isHeader: true });
  if (paid.advanceTax > 0) addTaxRow('', 'Advance Tax Paid (Challan 280 / e-Pay Tax)', paid.advanceTax, '', { indent: true });
  if (paid.tdsSalary > 0) addTaxRow('', 'TDS on Salaries (As per Form 16 / 26AS / AIS)', paid.tdsSalary, '', { indent: true });
  if (paid.tdsNonSalary > 0) addTaxRow('', 'TDS on Other than Salaries (Form 16A / 26AS)', paid.tdsNonSalary, '', { indent: true });
  if (paid.tcs > 0) addTaxRow('', 'Tax Collected at Source (TCS)', paid.tcs, '', { indent: true });
  if (paid.selfAssessmentTax > 0) addTaxRow('', 'Self Assessment Tax Paid (u/s 140A)', paid.selfAssessmentTax, '', { indent: true });
  addTaxRow('F', 'TOTAL TAXES PAID / CREDITED', '', paid.totalTaxesPaid, { isTotal: true });

  // Refund / Tax Payable
  if (paid.refundDue > 0) {
    addTaxRow('G', 'NET REFUND DUE TO ASSESSEE (Rounded off u/s 288B)', '', paid.refundDue, { isHeader: true });
  } else {
    addTaxRow('G', 'BALANCE NET TAX PAYABLE (Rounded off u/s 288B)', '', paid.taxPayable, { isHeader: true });
  }

  autoTable(doc, {
    startY: currentY,
    margin: { left: margin, right: margin },
    head: [
      [
        { content: 'Sr.', styles: { halign: 'center', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Computation of Tax, Cess, Interest & Taxes Paid', styles: { halign: 'left', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Details (₹)', styles: { halign: 'right', fillColor: palette.primary, textColor: [255, 255, 255] } },
        { content: 'Amount (₹)', styles: { halign: 'right', fillColor: palette.primary, textColor: [255, 255, 255] } },
      ],
    ],
    body: taxRows,
    theme: 'grid',
    styles: {
      fontSize: 8,
      cellPadding: 3.5,
      textColor: [17, 24, 39],
      lineColor: palette.borderColor,
      lineWidth: 0.5,
    },
    columnStyles: {
      0: { cellWidth: 32 },
      1: { cellWidth: contentWidth - 32 - 95 - 95 },
      2: { cellWidth: 95 },
      3: { cellWidth: 95 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 10;

  // 5. In-Words Callout Box
  if (currentY > pageHeight - 80) {
    doc.addPage();
    currentY = margin + 10;
  }

  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(palette.borderColor[0], palette.borderColor[1], palette.borderColor[2]);
  doc.rect(margin, currentY, contentWidth, 36, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(palette.accentText[0], palette.accentText[1], palette.accentText[2]);
  doc.text('Total Taxable Income in Words: ', margin + 8, currentY + 14);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(17, 24, 39);
  doc.text(numberToIndianRupeesWords(tax.totalTaxableIncome), margin + 140, currentY + 14);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(palette.accentText[0], palette.accentText[1], palette.accentText[2]);
  const actionWordsLabel = paid.refundDue > 0 ? 'Net Refund Claimed in Words: ' : 'Net Tax Payable in Words: ';
  doc.text(actionWordsLabel, margin + 8, currentY + 28);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(17, 24, 39);
  doc.text(numberToIndianRupeesWords(paid.refundDue > 0 ? paid.refundDue : paid.taxPayable), margin + 140, currentY + 28);

  currentY += 46;

  // 6. Section III: Bank Account Particulars for Refund
  if (cfg.includeBankDetails !== false) {
    if (currentY > pageHeight - 80) {
      doc.addPage();
      currentY = margin + 10;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
    doc.text('III. BANK ACCOUNT PARTICULARS FOR REFUND', margin, currentY);

    currentY += 6;

    autoTable(doc, {
      startY: currentY,
      margin: { left: margin, right: margin },
      body: [
        [
          { content: `Nominated Bank Name: ${p.bankName || 'State Bank of India'}` },
          { content: `Account Number: ${p.bankAccountNumber || 'Provided on Portal'}` },
          { content: `IFSC Code: ${p.bankIfsc || 'SBIN0001234'}` },
        ],
      ],
      theme: 'grid',
      styles: {
        fontSize: 8,
        cellPadding: 4,
        textColor: [17, 24, 39],
        lineColor: palette.borderColor,
        lineWidth: 0.5,
        fillColor: [250, 250, 250],
      },
      columnStyles: {
        0: { cellWidth: contentWidth / 3 },
        1: { cellWidth: contentWidth / 3 },
        2: { cellWidth: contentWidth / 3 },
      },
    });

    currentY = (doc as any).lastAutoTable.finalY + 12;
  }

  // 7. CA Signatory Details (if enabled)
  if (data.caDetails && data.caDetails.includeCASection) {
    if (currentY > pageHeight - 110) {
      doc.addPage();
      currentY = margin + 10;
    }

    const ca = data.caDetails;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
    doc.text('IV. CHARTERED ACCOUNTANT VERIFICATION & AUDIT TRAIL', margin, currentY);

    currentY += 6;

    autoTable(doc, {
      startY: currentY,
      margin: { left: margin, right: margin },
      body: [
        [
          { content: `Verified & Computed By: ${ca.caName || 'Chartered Accountant'}\nFirm: ${ca.firmName || 'Proprietor / Firm'}\nMembership No.: ${ca.membershipNo || 'XXXXXX'}\nFRN: ${ca.firmRegistrationNo || 'XXXXXX'}` },
          { content: `Unique Document Identification Number (UDIN):\n${ca.udin || 'Generated upon verification'}\n\nPlace: ${ca.place || 'Ahmedabad'}\nDate: ${ca.date || new Date().toLocaleDateString('en-GB')}` },
        ],
      ],
      theme: 'grid',
      styles: {
        fontSize: 8,
        cellPadding: 5,
        textColor: [17, 24, 39],
        lineColor: palette.borderColor,
        lineWidth: 0.5,
        fillColor: [250, 250, 250],
      },
      columnStyles: {
        0: { cellWidth: contentWidth / 2 },
        1: { cellWidth: contentWidth / 2 },
      },
    });
  }

  // 8. Headers and Footers on each page
  if (cfg.includeHeaderFooter) {
    const totalPages = (doc.internal as any).getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);

      // Running Header on page 2+
      if (i > 1) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(7.5);
        doc.setTextColor(156, 163, 175);
        doc.text(`${p.name || 'Assessee'} | PAN: ${p.pan || 'PAN'} | AY: ${p.assessmentYear || '2026-27'}`, pageWidth - margin, margin - 10, { align: 'right' });
        doc.setDrawColor(229, 231, 235);
        doc.setLineWidth(0.5);
        doc.line(margin, margin - 6, pageWidth - margin, margin - 6);
      }

      // Running Footer
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(156, 163, 175);
      doc.setDrawColor(229, 231, 235);
      doc.setLineWidth(0.5);
      doc.line(margin, pageHeight - margin + 6, pageWidth - margin, pageHeight - margin + 6);
      doc.text(
        `Page ${i} of ${totalPages}   •   Generated via ITR Computation Studio`,
        pageWidth / 2,
        pageHeight - margin + 18,
        { align: 'center' }
      );
    }
  }

  return doc;
}

/**
 * Exports and triggers instant download of the computation as a PDF
 */
export async function downloadITRPdf(data: CompleteITRData, customFileName?: string): Promise<Blob> {
  const doc = buildITRPdfDocument(data);
  const blob = doc.output('blob');

  const cleanName = (data.personalInfo.name || 'Assessee').replace(/[^A-Za-z0-9]/g, '_').slice(0, 25);
  const pan = data.personalInfo.pan || 'PAN';
  const ay = (data.personalInfo.assessmentYear || '2026-27').replace(/[^0-9-]/g, '');
  const fileName = customFileName || `ITR_Computation_${cleanName}_${pan}_AY${ay}.pdf`;

  let downloaded = false;

  if (typeof window !== 'undefined' && window.URL && window.URL.createObjectURL) {
    try {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      link.setAttribute('download', fileName);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        try {
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
        } catch (e) {
          // ignore
        }
      }, 2000);
      downloaded = true;
    } catch (err) {
      console.warn('Native anchor download attempt failed for PDF:', err);
    }
  }

  if (!downloaded) {
    try {
      if (typeof saveAs === 'function') {
        saveAs(blob, fileName);
        downloaded = true;
      }
    } catch (saveErr) {
      console.error('file-saver download failed for PDF:', saveErr);
    }
  }

  return blob;
}
