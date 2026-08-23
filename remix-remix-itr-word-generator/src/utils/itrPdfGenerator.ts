/**
 * Professional PDF Document Generator for Indian Income Tax Returns (ITR).
 * Uses jsPDF and jspdf-autotable to produce publication-grade, styled, CA-compliant
 * Computation of Income, Tax Audit Summaries, and Loan/Visa Financial Statements.
 *
 * Reproduces the exact computation, structure, figures, and styling of the approved Word document.
 */

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { saveAs } from 'file-saver';
import { CompleteITRData, DocxStyleConfig } from '../itr-types';
import { formatIndianCurrency, numberToIndianRupeesWords } from './numberParsing';

interface ThemeRgb {
  primary: [number, number, number];
  primaryHex: string;
  secondaryBg: [number, number, number];
  borderColor: [number, number, number];
  highlightBg: [number, number, number];
  accentText: [number, number, number];
}

const HEX_TO_RGB = (hex: string): [number, number, number] => {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16) || 0;
  const g = parseInt(clean.substring(2, 4), 16) || 0;
  const b = parseInt(clean.substring(4, 6), 16) || 0;
  return [r, g, b];
};

const THEME_PALETTES: Record<DocxStyleConfig['themeColor'], ThemeRgb> = {
  navy: {
    primary: [30, 58, 138],
    primaryHex: '#1E3A8A',
    secondaryBg: [224, 231, 255],
    borderColor: [203, 213, 225],
    highlightBg: [241, 245, 249],
    accentText: [30, 64, 175],
  },
  slate: {
    primary: [51, 65, 85],
    primaryHex: '#334155',
    secondaryBg: [241, 245, 249],
    borderColor: [226, 232, 240],
    highlightBg: [248, 250, 252],
    accentText: [71, 85, 105],
  },
  emerald: {
    primary: [6, 95, 70],
    primaryHex: '#065F46',
    secondaryBg: [209, 250, 229],
    borderColor: [167, 243, 208],
    highlightBg: [236, 253, 245],
    accentText: [4, 120, 87],
  },
  burgundy: {
    primary: [131, 24, 67],
    primaryHex: '#831843',
    secondaryBg: [252, 231, 243],
    borderColor: [251, 207, 232],
    highlightBg: [255, 241, 242],
    accentText: [157, 23, 77],
  },
  classic: {
    primary: [24, 24, 27],
    primaryHex: '#18181B',
    secondaryBg: [244, 244, 245],
    borderColor: [228, 228, 231],
    highlightBg: [250, 250, 250],
    accentText: [39, 39, 42],
  },
};

/**
 * Builds the complete jsPDF document
 */
export function buildITRPdfDocument(data: CompleteITRData): jsPDF {
  const cfg = data.styleConfig || {
    themeColor: 'navy',
    fontFamily: 'Calibri',
    includeHeaderFooter: true,
    includeBankDetails: true,
    documentTitle: 'Computation of Total Income & Tax Liability',
    subtitle: '',
  };

  const palette = THEME_PALETTES[cfg.themeColor] || THEME_PALETTES.navy;
  const p = data.personalInfo;
  const inc = data.incomeHeads;
  const ded = data.deductions;
  const tax = data.taxComputation;
  const paid = data.taxesPaid;

  // Initialize PDF in A4 portrait format (dimensions in mm: 210 x 297)
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const leftMargin = 12;
  const rightMargin = 12;
  const contentWidth = pageWidth - leftMargin - rightMargin; // 186mm

  let currentY = 14;

  // 1. Document Title & Subtitle
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text((cfg.documentTitle || 'COMPUTATION OF TOTAL INCOME & TAX LIABILITY').toUpperCase(), pageWidth / 2, currentY, {
    align: 'center',
  });

  currentY += 5;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(75, 85, 99);
  const subtitleText = cfg.subtitle || `Assessment Year ${p.assessmentYear} | Financial Year ${p.financialYear}`;
  doc.text(subtitleText, pageWidth / 2, currentY, { align: 'center' });

  currentY += 5;

  // Helper for formatting currency cells
  const fmtVal = (val: number | string, isDetail = false) => {
    if (typeof val === 'string') return val;
    if (val === 0) return '-';
    return formatIndianCurrency(val, { showSymbol: false });
  };

  // 2. Assessee Personal Information 2-Column Table
  const personalInfoBody: any[] = [
    [
      { content: `Name of Assessee:  ${p.name || '-'}`, styles: { fontStyle: 'bold' } },
      { content: `Permanent Account Number (PAN):  ${p.pan || '-'}`, styles: { fontStyle: 'bold' } },
    ],
    [
      { content: `Status / Constitution:  ${p.status || '-'}` },
      { content: `Tax Regime:  ${p.taxRegime && p.taxRegime.includes('Old') ? 'Old Regime' : 'New Regime'}` },
    ],
    [
      { content: `Assessment Year:  ${p.assessmentYear} (FY ${p.financialYear})` },
      { content: `Form Type Filed:  ${p.formType} u/s ${p.filingStatus}` },
    ],
    [
      { content: `Acknowledgment / Receipt No.:  ${p.ackNumber || 'N/A'}` },
      { content: `Filing / E-Verification Date:  ${p.filingDate || 'N/A'}` },
    ],
    [
      { content: `Residential Status:  ${p.residentialStatus || '-'}` },
      { content: `Contact / Email:  ${[p.mobile, p.email].filter(Boolean).join(' | ') || '-'}` },
    ],
  ];

  if (p.address) {
    const fullAddress = [p.address, p.city, p.state, p.pincode].filter(Boolean).join(', ');
    personalInfoBody.push([
      { content: `Registered Address:  ${fullAddress}`, colSpan: 2 },
      {},
    ]);
  }

  autoTable(doc, {
    startY: currentY,
    margin: { left: leftMargin, right: rightMargin },
    theme: 'grid',
    body: personalInfoBody,
    styles: {
      fontSize: 8,
      cellPadding: 1.6,
      textColor: [31, 41, 55],
      lineColor: palette.borderColor,
      lineWidth: 0.2,
      fillColor: [250, 250, 250],
      valign: 'middle',
    },
    columnStyles: {
      0: { cellWidth: contentWidth / 2 },
      1: { cellWidth: contentWidth / 2 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 4;

  // 3. Section I: Computation of Total Income
  // Section heading
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text('I. COMPUTATION OF TOTAL INCOME', leftMargin, currentY);
  currentY += 2;

  // Build rows for Computation Table
  const compRows: any[] = [];

  const makeRow = (
    sr: string,
    particulars: string,
    details: string | number,
    amount: string | number,
    opt: { isBold?: boolean; isHeaderSection?: boolean; isTotal?: boolean; indent?: boolean } = {}
  ) => {
    const { isBold = false, isHeaderSection = false, isTotal = false, indent = false } = opt;
    const dStr = typeof details === 'number' ? fmtVal(details, true) : details;
    const aStr = typeof amount === 'number' ? fmtVal(amount) : amount;

    let fill: [number, number, number] | undefined = undefined;
    if (isHeaderSection) fill = palette.secondaryBg;
    if (isTotal) fill = palette.highlightBg;

    let textCol: [number, number, number] = [17, 24, 39];
    if (isTotal) textCol = palette.accentText;

    return [
      {
        content: sr,
        styles: {
          halign: 'center',
          fontStyle: isBold || isHeaderSection ? 'bold' : 'normal',
          fillColor: fill,
          textColor: textCol,
        },
      },
      {
        content: (indent ? '     •  ' : '') + particulars,
        styles: {
          halign: 'left',
          fontStyle: isBold || isHeaderSection ? 'bold' : 'normal',
          fillColor: fill,
          textColor: textCol,
        },
      },
      {
        content: dStr,
        styles: {
          halign: 'right',
          fontStyle: isBold ? 'bold' : 'normal',
          fillColor: fill,
          textColor: textCol,
        },
      },
      {
        content: aStr,
        styles: {
          halign: 'right',
          fontStyle: isBold || isTotal ? 'bold' : 'normal',
          fillColor: fill,
          textColor: textCol,
        },
      },
    ];
  };

  // Head 1: Salary
  if (inc.salaryGross > 0 || inc.salaryNet > 0) {
    compRows.push(makeRow('I', 'INCOME FROM SALARY', '', '', { isBold: true, isHeaderSection: true }));
    compRows.push(makeRow('', 'Gross Salary / Pension u/s 17(1)', inc.salaryGross, '', { indent: true }));
    if (inc.salaryExemptAllowances > 0) {
      compRows.push(makeRow('', 'Less: Allowances Exempt u/s 10', `(${formatIndianCurrency(inc.salaryExemptAllowances, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.salaryStandardDeduction > 0) {
      compRows.push(makeRow('', 'Less: Standard Deduction u/s 16(ia)', `(${formatIndianCurrency(inc.salaryStandardDeduction, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.salaryProfessionalTax > 0) {
      compRows.push(makeRow('', 'Less: Professional Tax / Entertainment Allow. u/s 16(iii)', `(${formatIndianCurrency(inc.salaryProfessionalTax, { showSymbol: false })})`, '', { indent: true }));
    }
    compRows.push(makeRow('', 'Net Income Chargeable under the Head Salaries', '', inc.salaryNet, { isBold: true }));
  }

  // Head 2: House Property
  if (inc.housePropertyGross > 0 || inc.housePropertyNet !== 0) {
    compRows.push(makeRow('II', 'INCOME FROM HOUSE PROPERTY', '', '', { isBold: true, isHeaderSection: true }));
    compRows.push(makeRow('', 'Gross Annual Rent Received / Receivable', inc.housePropertyGross, '', { indent: true }));
    if (inc.housePropertyTaxes > 0) {
      compRows.push(makeRow('', 'Less: Municipal / Local Taxes Paid', `(${formatIndianCurrency(inc.housePropertyTaxes, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.housePropertyStandardDeduction > 0) {
      compRows.push(makeRow('', 'Less: 30% Standard Deduction u/s 24(a)', `(${formatIndianCurrency(inc.housePropertyStandardDeduction, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.housePropertyInterest > 0) {
      compRows.push(makeRow('', 'Less: Interest Payable on Housing Loan u/s 24(b)', `(${formatIndianCurrency(inc.housePropertyInterest, { showSymbol: false })})`, '', { indent: true }));
    }
    compRows.push(makeRow('', 'Net Income / (Loss) from House Property', '', inc.housePropertyNet, { isBold: true }));
  }

  // Head 3: Business or Profession (PGBP)
  if (inc.businessGrossReceipts > 0 || inc.businessNetProfit !== 0) {
    compRows.push(makeRow('III', 'PROFITS AND GAINS OF BUSINESS OR PROFESSION', '', '', { isBold: true, isHeaderSection: true }));
    if (inc.businessPresumptive44AD > 0) {
      compRows.push(makeRow('', `Presumptive Business Income u/s 44AD (Turnover: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44AD, '', { indent: true }));
    } else if (inc.businessPresumptive44ADA > 0) {
      compRows.push(makeRow('', `Presumptive Professional Income u/s 44ADA (Gross: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44ADA, '', { indent: true }));
    } else {
      compRows.push(makeRow('', 'Gross Turnover / Receipts from Business/Profession', inc.businessGrossReceipts, '', { indent: true }));
      if (inc.businessExpenses > 0) {
        compRows.push(makeRow('', 'Less: Total Operating & Administrative Expenses', `(${formatIndianCurrency(inc.businessExpenses, { showSymbol: false })})`, '', { indent: true }));
      }
    }
    compRows.push(makeRow('', 'Net Income from Business or Profession', '', inc.businessNetProfit, { isBold: true }));
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
    compRows.push(makeRow('IV', 'CAPITAL GAINS', '', '', { isBold: true, isHeaderSection: true }));
    if (inc.capitalGainsSTCG_20Pct && inc.capitalGainsSTCG_20Pct > 0) {
      compRows.push(makeRow('', 'Short Term Capital Gains u/s 111A (New Rate @ 20% / Post 23-Jul-2024)', inc.capitalGainsSTCG_20Pct, '', { indent: true }));
    }
    if (inc.capitalGainsSTCG_15Pct > 0) {
      compRows.push(makeRow('', 'Short Term Capital Gains u/s 111A (Old Rate @ 15% / Pre 23-Jul-2024)', inc.capitalGainsSTCG_15Pct, '', { indent: true }));
    }
    if (inc.capitalGainsSTCG_Slab > 0) {
      compRows.push(makeRow('', 'Short Term Capital Gains (Taxable at Applicable Slab Rates)', inc.capitalGainsSTCG_Slab, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_12_5Pct && inc.capitalGainsLTCG_12_5Pct > 0) {
      compRows.push(makeRow('', 'Long Term Capital Gains u/s 112A (New Rate @ 12.5% / Post 23-Jul-2024)', inc.capitalGainsLTCG_12_5Pct, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_10Pct > 0) {
      compRows.push(makeRow('', 'Long Term Capital Gains u/s 112A (Old Rate @ 10% / Pre 23-Jul-2024)', inc.capitalGainsLTCG_10Pct, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_20Pct > 0) {
      compRows.push(makeRow('', 'Long Term Capital Gains u/s 112 (Old Rate @ 20% with Indexation)', inc.capitalGainsLTCG_20Pct, '', { indent: true }));
    }
    compRows.push(makeRow('', 'Net Chargeable Capital Gains', '', inc.capitalGainsNet, { isBold: true }));
  }

  // Head 5: Other Sources
  if (inc.otherSourcesNet > 0 || inc.otherSourcesInterestSavings > 0 || inc.otherSourcesDividends > 0) {
    compRows.push(makeRow('V', 'INCOME FROM OTHER SOURCES', '', '', { isBold: true, isHeaderSection: true }));
    if (inc.otherSourcesInterestSavings > 0) {
      compRows.push(makeRow('', 'Interest from Savings Bank Accounts', inc.otherSourcesInterestSavings, '', { indent: true }));
    }
    if (inc.otherSourcesInterestDeposits > 0) {
      compRows.push(makeRow('', 'Interest on Fixed Deposits / Term Deposits / Bonds', inc.otherSourcesInterestDeposits, '', { indent: true }));
    }
    if (inc.otherSourcesDividends > 0) {
      compRows.push(makeRow('', 'Dividend Income from Indian Companies / Mutual Funds', inc.otherSourcesDividends, '', { indent: true }));
    }
    if (inc.otherSourcesFamilyPension > 0) {
      compRows.push(makeRow('', 'Family Pension Received', inc.otherSourcesFamilyPension, '', { indent: true }));
    }
    if (inc.otherSourcesOthers > 0) {
      compRows.push(makeRow('', 'Other Miscellaneous Income', inc.otherSourcesOthers, '', { indent: true }));
    }
    if (inc.otherSourcesDeductions > 0) {
      compRows.push(makeRow('', 'Less: Deduction u/s 57', `(${formatIndianCurrency(inc.otherSourcesDeductions, { showSymbol: false })})`, '', { indent: true }));
    }
    compRows.push(makeRow('', 'Net Income from Other Sources', '', inc.otherSourcesNet, { isBold: true }));
  }

  // Row A: Gross Total Income
  compRows.push(
    makeRow('A', 'GROSS TOTAL INCOME (I + II + III + IV + V)', '', inc.grossTotalIncome, {
      isBold: true,
      isTotal: true,
    })
  );

  // Chapter VI-A Deductions
  if (ded.totalDeductions > 0) {
    compRows.push(makeRow('B', 'LESS: DEDUCTIONS UNDER CHAPTER VI-A', '', '', { isBold: true, isHeaderSection: true }));
    if (ded.sec80C > 0) compRows.push(makeRow('', 'Section 80C (LIC, PPF, EPF, ELSS, School Fees, Principal Loan)', ded.sec80C, '', { indent: true }));
    if (ded.sec80CCD1B > 0) compRows.push(makeRow('', 'Section 80CCD(1B) (National Pension Scheme - Additional ₹50,000)', ded.sec80CCD1B, '', { indent: true }));
    if (ded.sec80CCD2 > 0) compRows.push(makeRow('', 'Section 80CCD(2) (Employer Contribution to NPS)', ded.sec80CCD2, '', { indent: true }));
    if (ded.sec80D > 0) compRows.push(makeRow('', 'Section 80D (Health Insurance Premium / Medical Expenditure)', ded.sec80D, '', { indent: true }));
    if (ded.sec80G > 0) compRows.push(makeRow('', 'Section 80G (Donations to Approved Funds / Charities)', ded.sec80G, '', { indent: true }));
    if (ded.sec80TTA > 0) compRows.push(makeRow('', 'Section 80TTA (Interest on Savings Account up to ₹10,000)', ded.sec80TTA, '', { indent: true }));
    if (ded.sec80TTB > 0) compRows.push(makeRow('', 'Section 80TTB (Interest for Senior Citizens up to ₹50,000)', ded.sec80TTB, '', { indent: true }));
    if (ded.otherDeductions > 0) compRows.push(makeRow('', 'Other Applicable Deductions under Chapter VI-A', ded.otherDeductions, '', { indent: true }));
    compRows.push(makeRow('', 'Total Chapter VI-A Deductions Allowable', '', `(${formatIndianCurrency(ded.totalDeductions, { showSymbol: false })})`, { isBold: true }));
  }

  // Row C: Total Taxable Income
  compRows.push(
    makeRow('C', 'TOTAL TAXABLE INCOME (Rounded off u/s 288A)', '', tax.totalTaxableIncome, {
      isBold: true,
      isTotal: true,
    })
  );

  autoTable(doc, {
    startY: currentY,
    margin: { left: leftMargin, right: rightMargin },
    theme: 'grid',
    head: [
      [
        { content: 'Sr.', styles: { halign: 'center' } },
        { content: 'Particulars of Income / Deductions', styles: { halign: 'left' } },
        { content: 'Details (₹)', styles: { halign: 'right' } },
        { content: 'Amount (₹)', styles: { halign: 'right' } },
      ],
    ],
    body: compRows,
    headStyles: {
      fillColor: palette.primary,
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8.5,
      cellPadding: 2,
    },
    styles: {
      fontSize: 8,
      cellPadding: 1.5,
      lineColor: palette.borderColor,
      lineWidth: 0.15,
      valign: 'middle',
    },
    columnStyles: {
      0: { cellWidth: 10 },
      1: { cellWidth: contentWidth - 10 - 32 - 32 },
      2: { cellWidth: 32 },
      3: { cellWidth: 32 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 4;

  // 4. Section II: Computation of Tax Liability & Taxes Paid
  // Check if we need to add a page break before section II if space is too low
  if (currentY > pageHeight - 50) {
    doc.addPage();
    currentY = 14;
  }

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
  doc.text('II. COMPUTATION OF TAX LIABILITY & TAXES PAID', leftMargin, currentY);
  currentY += 2;

  const taxRows: any[] = [];
  taxRows.push(makeRow('1', 'Tax on Total Income (Calculated as per Applicable Slab Rates)', tax.taxOnTotalIncome, '', { isBold: false }));
  if (tax.specialRateTax > 0) {
    taxRows.push(makeRow('2', 'Tax on Special Rate Incomes (STCG u/s 111A / LTCG u/s 112/112A)', tax.specialRateTax, '', { isBold: false }));
  }
  if (tax.rebate87A > 0) {
    taxRows.push(makeRow('3', 'Less: Tax Rebate admissible u/s 87A', `(${formatIndianCurrency(tax.rebate87A, { showSymbol: false })})`, '', { isBold: false }));
  }
  taxRows.push(makeRow('4', 'Tax Payable after Rebate', '', tax.taxAfterRebate, { isBold: true }));
  if (tax.surcharge > 0) {
    taxRows.push(makeRow('5', 'Add: Surcharge on Tax', tax.surcharge, '', { isBold: false }));
  }
  taxRows.push(makeRow('6', 'Add: Health & Education Cess @ 4%', tax.cess, '', { isBold: false }));
  taxRows.push(makeRow('7', 'Gross Tax Liability', '', tax.grossTaxLiability, { isBold: true }));

  if (tax.relief89 > 0 || tax.relief90_91 > 0) {
    taxRows.push(makeRow('8', 'Less: Relief u/s 89 / 90 / 91', `(${formatIndianCurrency(tax.relief89 + tax.relief90_91, { showSymbol: false })})`, '', { isBold: false }));
  }
  taxRows.push(makeRow('9', 'Net Tax Liability', '', tax.netTaxLiability, { isBold: true }));

  if (tax.interest234A > 0 || tax.interest234B > 0 || tax.interest234C > 0 || tax.fee234F > 0) {
    taxRows.push(makeRow('10', 'Interest u/s 234A (Delay in filing return)', tax.interest234A, '', { indent: true }));
    taxRows.push(makeRow('11', 'Interest u/s 234B (Default in payment of advance tax)', tax.interest234B, '', { indent: true }));
    taxRows.push(makeRow('12', 'Interest u/s 234C (Deferment of advance tax instalments)', tax.interest234C, '', { indent: true }));
    if (tax.fee234F > 0) {
      taxRows.push(makeRow('13', 'Late Filing Fee u/s 234F', tax.fee234F, '', { indent: true }));
    }
  }
  taxRows.push(makeRow('D', 'TOTAL TAX, CESS, FEE AND INTEREST PAYABLE', '', tax.totalTaxAndInterest, { isBold: true, isTotal: true }));

  // Taxes Paid Section
  taxRows.push(makeRow('E', 'TAXES PAID / PREPAID TAXES CREDITS', '', '', { isBold: true, isHeaderSection: true }));
  if (paid.advanceTax > 0) taxRows.push(makeRow('', 'Advance Tax Paid (Challan 280 / e-Pay Tax)', paid.advanceTax, '', { indent: true }));
  if (paid.tdsSalary > 0) taxRows.push(makeRow('', 'TDS on Salaries (As per Form 16 / 26AS / AIS)', paid.tdsSalary, '', { indent: true }));
  if (paid.tdsNonSalary > 0) taxRows.push(makeRow('', 'TDS on Other than Salaries (Form 16A / 26AS)', paid.tdsNonSalary, '', { indent: true }));
  if (paid.tcs > 0) taxRows.push(makeRow('', 'Tax Collected at Source (TCS)', paid.tcs, '', { indent: true }));
  if (paid.selfAssessmentTax > 0) taxRows.push(makeRow('', 'Self Assessment Tax Paid (u/s 140A)', paid.selfAssessmentTax, '', { indent: true }));
  taxRows.push(makeRow('F', 'TOTAL TAXES PAID / CREDITED', '', paid.totalTaxesPaid, { isBold: true, isTotal: true }));

  // Final Result Row: Refund Due or Tax Payable
  if (paid.refundDue > 0) {
    taxRows.push(
      makeRow('G', 'NET REFUND DUE TO ASSESSEE (Rounded off u/s 288B)', '', paid.refundDue, {
        isBold: true,
        isHeaderSection: true,
      })
    );
  } else {
    taxRows.push(
      makeRow('G', 'BALANCE NET TAX PAYABLE (Rounded off u/s 288B)', '', paid.taxPayable, {
        isBold: true,
        isHeaderSection: true,
      })
    );
  }

  autoTable(doc, {
    startY: currentY,
    margin: { left: leftMargin, right: rightMargin },
    theme: 'grid',
    head: [
      [
        { content: 'Sr.', styles: { halign: 'center' } },
        { content: 'Computation of Tax, Cess, Interest & Taxes Paid', styles: { halign: 'left' } },
        { content: 'Details (₹)', styles: { halign: 'right' } },
        { content: 'Amount (₹)', styles: { halign: 'right' } },
      ],
    ],
    body: taxRows,
    headStyles: {
      fillColor: palette.primary,
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8.5,
      cellPadding: 2,
    },
    styles: {
      fontSize: 8,
      cellPadding: 1.5,
      lineColor: palette.borderColor,
      lineWidth: 0.15,
      valign: 'middle',
    },
    columnStyles: {
      0: { cellWidth: 10 },
      1: { cellWidth: contentWidth - 10 - 32 - 32 },
      2: { cellWidth: 32 },
      3: { cellWidth: 32 },
    },
  });

  currentY = (doc as any).lastAutoTable.finalY + 4;

  // 5. Words Callout Block
  if (currentY > pageHeight - 35) {
    doc.addPage();
    currentY = 14;
  }

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(palette.accentText[0], palette.accentText[1], palette.accentText[2]);
  doc.text('Total Taxable Income in Words: ', leftMargin, currentY);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(17, 24, 39);
  doc.text(numberToIndianRupeesWords(tax.totalTaxableIncome), leftMargin + 48, currentY);

  currentY += 4.5;
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(palette.accentText[0], palette.accentText[1], palette.accentText[2]);
  const refundOrPayLabel = paid.refundDue > 0 ? 'Net Refund Claimed in Words: ' : 'Net Tax Payable in Words: ';
  doc.text(refundOrPayLabel, leftMargin, currentY);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(17, 24, 39);
  doc.text(numberToIndianRupeesWords(paid.refundDue > 0 ? paid.refundDue : paid.taxPayable), leftMargin + 48, currentY);

  currentY += 6;

  // 6. Section III: Bank Account Particulars for Refund
  if (cfg.includeBankDetails !== false) {
    if (currentY > pageHeight - 28) {
      doc.addPage();
      currentY = 14;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(palette.primary[0], palette.primary[1], palette.primary[2]);
    doc.text('III. BANK ACCOUNT PARTICULARS FOR REFUND', leftMargin, currentY);
    currentY += 2;

    const bankBody: any[] = [
      [
        { content: `Nominated Bank Name:  ${p.bankName || 'State Bank of India'}`, styles: { fontStyle: 'normal' } },
        { content: `Account Number:  ${p.bankAccountNumber || 'Provided on Portal'}`, styles: { fontStyle: 'bold' } },
        { content: `IFSC Code:  ${p.bankIfsc || 'SBIN0001234'}`, styles: { fontStyle: 'bold' } },
      ],
    ];

    autoTable(doc, {
      startY: currentY,
      margin: { left: leftMargin, right: rightMargin },
      theme: 'grid',
      body: bankBody,
      styles: {
        fontSize: 8,
        cellPadding: 1.8,
        textColor: [31, 41, 55],
        lineColor: palette.borderColor,
        lineWidth: 0.2,
        fillColor: [250, 250, 250],
        valign: 'middle',
      },
      columnStyles: {
        0: { cellWidth: contentWidth / 3 },
        1: { cellWidth: contentWidth / 3 },
        2: { cellWidth: contentWidth / 3 },
      },
    });
  }

  // 7. Running Header & Footer with Page Numbers
  if (cfg.includeHeaderFooter) {
    const totalPages = (doc as any).internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);

      // Running Header (from page 1 or subsequent)
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(156, 163, 175);
      const headerText = `${p.name || 'Assessee'} | PAN: ${p.pan || 'PAN'} | AY: ${p.assessmentYear || '2026-27'}`;
      doc.text(headerText, pageWidth - rightMargin, 7, { align: 'right' });

      // Running Footer
      const footerText = `Page ${i} of ${totalPages}  •  Generated via ITR Word & PDF Generator`;
      doc.text(footerText, pageWidth / 2, pageHeight - 6, { align: 'center' });
    }
  }

  return doc;
}

/**
 * Exports and triggers instant download of the PDF Document in browser
 */
export async function downloadITRPdf(data: CompleteITRData, customFileName?: string): Promise<Blob> {
  const doc = buildITRPdfDocument(data);
  const blob = doc.output('blob');

  const cleanName = (data.personalInfo.name || 'Assessee').replace(/[^A-Za-z0-9]/g, '_').slice(0, 25);
  const pan = data.personalInfo.pan || 'PAN';
  const ay = (data.personalInfo.assessmentYear || '2026-27').replace(/[^0-9-]/g, '');
  const fileName = customFileName || `ITR_Computation_${cleanName}_${pan}_AY${ay}.pdf`;

  // Multi-tier browser download triggers (Works in all browsers, sandboxes & iframes)
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
          // ignore cleanup
        }
      }, 2000);
      downloaded = true;
    } catch (err) {
      console.warn('Native anchor download attempt failed:', err);
    }
  }

  if (!downloaded) {
    try {
      if (typeof saveAs === 'function') {
        saveAs(blob, fileName);
        downloaded = true;
      }
    } catch (saveErr) {
      console.error('file-saver download attempt failed:', saveErr);
    }
  }

  return blob;
}
