/**
 * Professional Microsoft Word (.docx) Document Generator for Indian ITRs.
 * Uses the docx npm package to produce publication-grade, styled, CA-compliant
 * Computation of Income, Tax Audit Summaries, and Loan/Visa Financial Statements.
 */

import {
  Document,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  BorderStyle,
  Header,
  Footer,
  PageNumber,
  ShadingType,
  VerticalAlign,
  Packer,
} from 'docx';
import { saveAs } from 'file-saver';
import { CompleteITRData, DocxStyleConfig } from '../itr-types';
import { formatIndianCurrency, numberToIndianRupeesWords } from './numberParsing';
import { compareTaxRegimes } from './taxCalculator';

interface ThemePalette {
  primary: string;       // Primary header & accent color e.g. "1E3A8A"
  primaryText: string;   // Text color on primary e.g. "FFFFFF"
  secondaryBg: string;   // Light background for table headers e.g. "EFF6FF"
  borderColor: string;   // Table border color e.g. "CBD5E1"
  highlightBg: string;   // Total row highlight e.g. "F8FAFC"
  accentText: string;    // Subheading accent e.g. "1E40AF"
}

const THEME_PALETTES: Record<DocxStyleConfig['themeColor'], ThemePalette> = {
  navy: {
    primary: '1E3A8A',
    primaryText: 'FFFFFF',
    secondaryBg: 'E0E7FF',
    borderColor: 'CBD5E1',
    highlightBg: 'F1F5F9',
    accentText: '1E40AF',
  },
  slate: {
    primary: '334155',
    primaryText: 'FFFFFF',
    secondaryBg: 'F1F5F9',
    borderColor: 'E2E8F0',
    highlightBg: 'F8FAFC',
    accentText: '475569',
  },
  emerald: {
    primary: '065F46',
    primaryText: 'FFFFFF',
    secondaryBg: 'D1FAE5',
    borderColor: 'A7F3D0',
    highlightBg: 'ECFDF5',
    accentText: '047857',
  },
  burgundy: {
    primary: '831843',
    primaryText: 'FFFFFF',
    secondaryBg: 'FCE7F3',
    borderColor: 'FBCFE8',
    highlightBg: 'FFF1F2',
    accentText: '9D174D',
  },
  classic: {
    primary: '18181B',
    primaryText: 'FFFFFF',
    secondaryBg: 'F4F4F5',
    borderColor: 'E4E4E7',
    highlightBg: 'FAFAFA',
    accentText: '27272A',
  },
};

/**
 * Creates standard cell borders
 */
function getCellBorders(color: string) {
  return {
    top: { style: BorderStyle.SINGLE, size: 4, color },
    bottom: { style: BorderStyle.SINGLE, size: 4, color },
    left: { style: BorderStyle.SINGLE, size: 4, color },
    right: { style: BorderStyle.SINGLE, size: 4, color },
  };
}

function getHeaderCellBorders(color: string) {
  return {
    top: { style: BorderStyle.SINGLE, size: 8, color },
    bottom: { style: BorderStyle.SINGLE, size: 8, color },
    left: { style: BorderStyle.SINGLE, size: 4, color },
    right: { style: BorderStyle.SINGLE, size: 4, color },
  };
}

/**
 * Builds the entire DOCX Document object
 */
export function buildITRDocxDocument(data: CompleteITRData): Document {
  const cfg = data.styleConfig;
  const palette = THEME_PALETTES[cfg.themeColor] || THEME_PALETTES.navy;
  const font = cfg.fontFamily || 'Calibri';
  const p = data.personalInfo;
  const inc = data.incomeHeads;
  const ded = data.deductions;
  const tax = data.taxComputation;
  const paid = data.taxesPaid;

  const sections: any[] = [];

  // Table Row helper
  const makeDataRow = (
    sr: string,
    particulars: string,
    amount1: string | number,
    amount2: string | number,
    options: { isBold?: boolean; isTotal?: boolean; bg?: string; indent?: boolean } = {}
  ) => {
    const { isBold = false, isTotal = false, bg, indent = false } = options;
    const a1Str = typeof amount1 === 'number' ? (amount1 !== 0 ? formatIndianCurrency(amount1, { showSymbol: false }) : '-') : amount1;
    const a2Str = typeof amount2 === 'number' ? (amount2 !== 0 ? formatIndianCurrency(amount2, { showSymbol: false }) : '-') : amount2;

    const cellBg = isTotal ? palette.highlightBg : bg;

    return new TableRow({
      children: [
        new TableCell({
          width: { size: 600, type: WidthType.DXA },
          shading: cellBg ? { fill: cellBg, type: ShadingType.CLEAR } : undefined,
          borders: getCellBorders(palette.borderColor),
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: sr, font, size: isBold ? 20 : 19, bold: isBold })],
            }),
          ],
        }),
        new TableCell({
          width: { size: 5400, type: WidthType.DXA },
          shading: cellBg ? { fill: cellBg, type: ShadingType.CLEAR } : undefined,
          borders: getCellBorders(palette.borderColor),
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: (indent ? '     •  ' : '') + particulars,
                  font,
                  size: isBold ? 20 : 19,
                  bold: isBold,
                  color: isTotal ? palette.accentText : '111827',
                }),
              ],
            }),
          ],
        }),
        new TableCell({
          width: { size: 1700, type: WidthType.DXA },
          shading: cellBg ? { fill: cellBg, type: ShadingType.CLEAR } : undefined,
          borders: getCellBorders(palette.borderColor),
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [new TextRun({ text: a1Str, font, size: isBold ? 20 : 19, bold: isBold })],
            }),
          ],
        }),
        new TableCell({
          width: { size: 1700, type: WidthType.DXA },
          shading: cellBg ? { fill: cellBg, type: ShadingType.CLEAR } : undefined,
          borders: getCellBorders(palette.borderColor),
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [
                new TextRun({
                  text: a2Str,
                  font,
                  size: isBold ? 20 : 19,
                  bold: isBold,
                  color: isTotal ? palette.accentText : '111827',
                }),
              ],
            }),
          ],
        }),
      ],
    });
  };

  // Header banner paragraphs
  const titleParagraphs = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
      children: [
        new TextRun({
          text: cfg.documentTitle.toUpperCase(),
          font,
          bold: true,
          size: 28,
          color: palette.primary,
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 180 },
      children: [
        new TextRun({
          text: cfg.subtitle || `Assessment Year ${p.assessmentYear} | Financial Year ${p.financialYear}`,
          font,
          size: 20,
          color: '4B5563',
        }),
      ],
    }),
  ];

  // Personal Details 2-Column Info Table
  const makeInfoCell = (label: string, value: string, widthDxa: number) => {
    return new TableCell({
      width: { size: widthDxa, type: WidthType.DXA },
      borders: getCellBorders(palette.borderColor),
      shading: { fill: 'FAFAFA', type: ShadingType.CLEAR },
      children: [
        new Paragraph({
          children: [
            new TextRun({ text: `${label}: `, font, bold: true, size: 19, color: '374151' }),
            new TextRun({ text: value || '-', font, size: 19, color: '111827' }),
          ],
        }),
      ],
    });
  };

  const personalInfoTable = new Table({
    width: { size: 9400, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    rows: [
      new TableRow({
        children: [
          makeInfoCell('Name of Assessee', p.name, 4700),
          makeInfoCell('Permanent Account Number (PAN)', p.pan, 4700),
        ],
      }),
      new TableRow({
        children: [
          makeInfoCell('Status / Constitution', p.status, 4700),
          makeInfoCell('Tax Regime', (p.taxRegime && p.taxRegime.includes('Old')) ? 'Old Regime' : 'New Regime', 4700),
        ],
      }),
      new TableRow({
        children: [
          makeInfoCell('Assessment Year', `${p.assessmentYear} (FY ${p.financialYear})`, 4700),
          makeInfoCell('Form Type Filed', `${p.formType} u/s ${p.filingStatus}`, 4700),
        ],
      }),
      new TableRow({
        children: [
          makeInfoCell('Acknowledgment / Receipt No.', p.ackNumber || 'N/A', 4700),
          makeInfoCell('Filing / E-Verification Date', p.filingDate || 'N/A', 4700),
        ],
      }),
      new TableRow({
        children: [
          makeInfoCell('Residential Status', p.residentialStatus, 4700),
          makeInfoCell('Contact / Email', [p.mobile, p.email].filter(Boolean).join(' | ') || '-', 4700),
        ],
      }),
      ...(p.address
        ? [
            new TableRow({
              children: [
                new TableCell({
                  width: { size: 9400, type: WidthType.DXA },
                  columnSpan: 2,
                  borders: getCellBorders(palette.borderColor),
                  shading: { fill: 'FAFAFA', type: ShadingType.CLEAR },
                  children: [
                    new Paragraph({
                      children: [
                        new TextRun({ text: 'Registered Address: ', font, bold: true, size: 19, color: '374151' }),
                        new TextRun({
                          text: [p.address, p.city, p.state, p.pincode].filter(Boolean).join(', '),
                          font,
                          size: 19,
                          color: '111827',
                        }),
                      ],
                    }),
                  ],
                }),
              ],
            }),
          ]
        : []),
    ],
  });

  // Table Header for Computation of Income
  const computationHeaderRow = new TableRow({
    tableHeader: true,
    children: [
      new TableCell({
        width: { size: 600, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: 'Sr.', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
      new TableCell({
        width: { size: 5400, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: 'Particulars of Income / Deductions', font, bold: true, size: 20, color: palette.primaryText }),
            ],
          }),
        ],
      }),
      new TableCell({
        width: { size: 1700, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: 'Details (₹)', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
      new TableCell({
        width: { size: 1700, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: 'Amount (₹)', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
    ],
  });

  const computationRows: TableRow[] = [computationHeaderRow];

  // Head 1: Salary
  if (inc.salaryGross > 0 || inc.salaryNet > 0) {
    computationRows.push(makeDataRow('I', 'INCOME FROM SALARY', '', '', { isBold: true, bg: palette.secondaryBg }));
    computationRows.push(makeDataRow('', 'Gross Salary / Pension u/s 17(1)', inc.salaryGross, '', { indent: true }));
    if (inc.salaryExemptAllowances > 0) {
      computationRows.push(makeDataRow('', 'Less: Allowances Exempt u/s 10', `(${formatIndianCurrency(inc.salaryExemptAllowances, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.salaryStandardDeduction > 0) {
      computationRows.push(makeDataRow('', 'Less: Standard Deduction u/s 16(ia)', `(${formatIndianCurrency(inc.salaryStandardDeduction, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.salaryProfessionalTax > 0) {
      computationRows.push(makeDataRow('', 'Less: Professional Tax / Entertainment Allow. u/s 16(iii)', `(${formatIndianCurrency(inc.salaryProfessionalTax, { showSymbol: false })})`, '', { indent: true }));
    }
    computationRows.push(makeDataRow('', 'Net Income Chargeable under the Head Salaries', '', inc.salaryNet, { isBold: true }));
  }

  // Head 2: House Property
  if (inc.housePropertyGross > 0 || inc.housePropertyNet !== 0) {
    computationRows.push(makeDataRow('II', 'INCOME FROM HOUSE PROPERTY', '', '', { isBold: true, bg: palette.secondaryBg }));
    computationRows.push(makeDataRow('', 'Gross Annual Rent Received / Receivable', inc.housePropertyGross, '', { indent: true }));
    if (inc.housePropertyTaxes > 0) {
      computationRows.push(makeDataRow('', 'Less: Municipal / Local Taxes Paid', `(${formatIndianCurrency(inc.housePropertyTaxes, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.housePropertyStandardDeduction > 0) {
      computationRows.push(makeDataRow('', 'Less: 30% Standard Deduction u/s 24(a)', `(${formatIndianCurrency(inc.housePropertyStandardDeduction, { showSymbol: false })})`, '', { indent: true }));
    }
    if (inc.housePropertyInterest > 0) {
      computationRows.push(makeDataRow('', 'Less: Interest Payable on Housing Loan u/s 24(b)', `(${formatIndianCurrency(inc.housePropertyInterest, { showSymbol: false })})`, '', { indent: true }));
    }
    computationRows.push(makeDataRow('', 'Net Income / (Loss) from House Property', '', inc.housePropertyNet, { isBold: true }));
  }

  // Head 3: Business or Profession (PGBP)
  if (inc.businessGrossReceipts > 0 || inc.businessNetProfit !== 0) {
    computationRows.push(makeDataRow('III', 'PROFITS AND GAINS OF BUSINESS OR PROFESSION', '', '', { isBold: true, bg: palette.secondaryBg }));
    if (inc.businessPresumptive44AD > 0) {
      computationRows.push(makeDataRow('', `Presumptive Business Income u/s 44AD (Turnover: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44AD, '', { indent: true }));
    } else if (inc.businessPresumptive44ADA > 0) {
      computationRows.push(makeDataRow('', `Presumptive Professional Income u/s 44ADA (Gross: ${formatIndianCurrency(inc.businessGrossReceipts)})`, inc.businessPresumptive44ADA, '', { indent: true }));
    } else {
      computationRows.push(makeDataRow('', 'Gross Turnover / Receipts from Business/Profession', inc.businessGrossReceipts, '', { indent: true }));
      if (inc.businessExpenses > 0) {
        computationRows.push(makeDataRow('', 'Less: Total Operating & Administrative Expenses', `(${formatIndianCurrency(inc.businessExpenses, { showSymbol: false })})`, '', { indent: true }));
      }
    }
    computationRows.push(makeDataRow('', 'Net Income from Business or Profession', '', inc.businessNetProfit, { isBold: true }));
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
    computationRows.push(makeDataRow('IV', 'CAPITAL GAINS', '', '', { isBold: true, bg: palette.secondaryBg }));
    if (inc.capitalGainsSTCG_20Pct && inc.capitalGainsSTCG_20Pct > 0) {
      computationRows.push(makeDataRow('', 'Short Term Capital Gains u/s 111A (New Rate @ 20% / Post 23-Jul-2024)', inc.capitalGainsSTCG_20Pct, '', { indent: true }));
    }
    if (inc.capitalGainsSTCG_15Pct > 0) {
      computationRows.push(makeDataRow('', 'Short Term Capital Gains u/s 111A (Old Rate @ 15% / Pre 23-Jul-2024)', inc.capitalGainsSTCG_15Pct, '', { indent: true }));
    }
    if (inc.capitalGainsSTCG_Slab > 0) {
      computationRows.push(makeDataRow('', 'Short Term Capital Gains (Taxable at Applicable Slab Rates)', inc.capitalGainsSTCG_Slab, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_12_5Pct && inc.capitalGainsLTCG_12_5Pct > 0) {
      computationRows.push(makeDataRow('', 'Long Term Capital Gains u/s 112A (New Rate @ 12.5% / Post 23-Jul-2024)', inc.capitalGainsLTCG_12_5Pct, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_10Pct > 0) {
      computationRows.push(makeDataRow('', 'Long Term Capital Gains u/s 112A (Old Rate @ 10% / Pre 23-Jul-2024)', inc.capitalGainsLTCG_10Pct, '', { indent: true }));
    }
    if (inc.capitalGainsLTCG_20Pct > 0) {
      computationRows.push(makeDataRow('', 'Long Term Capital Gains u/s 112 (Old Rate @ 20% with Indexation)', inc.capitalGainsLTCG_20Pct, '', { indent: true }));
    }
    computationRows.push(makeDataRow('', 'Net Chargeable Capital Gains', '', inc.capitalGainsNet, { isBold: true }));
  }

  // Head 5: Other Sources
  if (inc.otherSourcesNet > 0 || inc.otherSourcesInterestSavings > 0 || inc.otherSourcesDividends > 0) {
    computationRows.push(makeDataRow('V', 'INCOME FROM OTHER SOURCES', '', '', { isBold: true, bg: palette.secondaryBg }));
    if (inc.otherSourcesInterestSavings > 0) {
      computationRows.push(makeDataRow('', 'Interest from Savings Bank Accounts', inc.otherSourcesInterestSavings, '', { indent: true }));
    }
    if (inc.otherSourcesInterestDeposits > 0) {
      computationRows.push(makeDataRow('', 'Interest on Fixed Deposits / Term Deposits / Bonds', inc.otherSourcesInterestDeposits, '', { indent: true }));
    }
    if (inc.otherSourcesDividends > 0) {
      computationRows.push(makeDataRow('', 'Dividend Income from Indian Companies / Mutual Funds', inc.otherSourcesDividends, '', { indent: true }));
    }
    if (inc.otherSourcesFamilyPension > 0) {
      computationRows.push(makeDataRow('', 'Family Pension Received', inc.otherSourcesFamilyPension, '', { indent: true }));
    }
    if (inc.otherSourcesOthers > 0) {
      computationRows.push(makeDataRow('', 'Other Miscellaneous Income', inc.otherSourcesOthers, '', { indent: true }));
    }
    if (inc.otherSourcesDeductions > 0) {
      computationRows.push(makeDataRow('', 'Less: Deduction u/s 57', `(${formatIndianCurrency(inc.otherSourcesDeductions, { showSymbol: false })})`, '', { indent: true }));
    }
    computationRows.push(makeDataRow('', 'Net Income from Other Sources', '', inc.otherSourcesNet, { isBold: true }));
  }

  // Gross Total Income Row
  computationRows.push(
    makeDataRow('A', 'GROSS TOTAL INCOME (I + II + III + IV + V)', '', inc.grossTotalIncome, {
      isBold: true,
      isTotal: true,
    })
  );

  // Chapter VI-A Deductions
  if (ded.totalDeductions > 0) {
    computationRows.push(makeDataRow('B', 'LESS: DEDUCTIONS UNDER CHAPTER VI-A', '', '', { isBold: true, bg: palette.secondaryBg }));
    if (ded.sec80C > 0) computationRows.push(makeDataRow('', 'Section 80C (LIC, PPF, EPF, ELSS, School Fees, Principal Loan)', ded.sec80C, '', { indent: true }));
    if (ded.sec80CCD1B > 0) computationRows.push(makeDataRow('', 'Section 80CCD(1B) (National Pension Scheme - Additional ₹50,000)', ded.sec80CCD1B, '', { indent: true }));
    if (ded.sec80CCD2 > 0) computationRows.push(makeDataRow('', 'Section 80CCD(2) (Employer Contribution to NPS)', ded.sec80CCD2, '', { indent: true }));
    if (ded.sec80D > 0) computationRows.push(makeDataRow('', 'Section 80D (Health Insurance Premium / Medical Expenditure)', ded.sec80D, '', { indent: true }));
    if (ded.sec80G > 0) computationRows.push(makeDataRow('', 'Section 80G (Donations to Approved Funds / Charities)', ded.sec80G, '', { indent: true }));
    if (ded.sec80TTA > 0) computationRows.push(makeDataRow('', 'Section 80TTA (Interest on Savings Account up to ₹10,000)', ded.sec80TTA, '', { indent: true }));
    if (ded.sec80TTB > 0) computationRows.push(makeDataRow('', 'Section 80TTB (Interest for Senior Citizens up to ₹50,000)', ded.sec80TTB, '', { indent: true }));
    if (ded.otherDeductions > 0) computationRows.push(makeDataRow('', 'Other Applicable Deductions under Chapter VI-A', ded.otherDeductions, '', { indent: true }));
    computationRows.push(makeDataRow('', 'Total Chapter VI-A Deductions Allowable', '', `(${formatIndianCurrency(ded.totalDeductions, { showSymbol: false })})`, { isBold: true }));
  }

  // Total Taxable Income
  computationRows.push(
    makeDataRow('C', 'TOTAL TAXABLE INCOME (Rounded off u/s 288A)', '', tax.totalTaxableIncome, {
      isBold: true,
      isTotal: true,
    })
  );

  const computationTable = new Table({
    width: { size: 9400, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    rows: computationRows,
  });

  // Tax Liability & Taxes Paid Table
  const taxCompHeaderRow = new TableRow({
    tableHeader: true,
    children: [
      new TableCell({
        width: { size: 600, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: 'Sr.', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
      new TableCell({
        width: { size: 5400, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            children: [new TextRun({ text: 'Computation of Tax, Cess, Interest & Taxes Paid', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
      new TableCell({
        width: { size: 1700, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: 'Details (₹)', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
      new TableCell({
        width: { size: 1700, type: WidthType.DXA },
        shading: { fill: palette.primary, type: ShadingType.CLEAR },
        borders: getHeaderCellBorders(palette.primary),
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: 'Amount (₹)', font, bold: true, size: 20, color: palette.primaryText })],
          }),
        ],
      }),
    ],
  });

  const taxRows: TableRow[] = [taxCompHeaderRow];
  taxRows.push(makeDataRow('1', 'Tax on Total Income (Calculated as per Applicable Slab Rates)', tax.taxOnTotalIncome, '', { isBold: false }));
  if (tax.specialRateTax > 0) {
    taxRows.push(makeDataRow('2', 'Tax on Special Rate Incomes (STCG u/s 111A / LTCG u/s 112/112A)', tax.specialRateTax, '', { isBold: false }));
  }
  if (tax.rebate87A > 0) {
    taxRows.push(makeDataRow('3', 'Less: Tax Rebate admissible u/s 87A', `(${formatIndianCurrency(tax.rebate87A, { showSymbol: false })})`, '', { isBold: false }));
  }
  taxRows.push(makeDataRow('4', 'Tax Payable after Rebate', '', tax.taxAfterRebate, { isBold: true }));
  if (tax.surcharge > 0) {
    taxRows.push(makeDataRow('5', 'Add: Surcharge on Tax', tax.surcharge, '', { isBold: false }));
  }
  taxRows.push(makeDataRow('6', 'Add: Health & Education Cess @ 4%', tax.cess, '', { isBold: false }));
  taxRows.push(makeDataRow('7', 'Gross Tax Liability', '', tax.grossTaxLiability, { isBold: true }));

  if (tax.relief89 > 0 || tax.relief90_91 > 0) {
    taxRows.push(makeDataRow('8', 'Less: Relief u/s 89 / 90 / 91', `(${formatIndianCurrency(tax.relief89 + tax.relief90_91, { showSymbol: false })})`, '', { isBold: false }));
  }
  taxRows.push(makeDataRow('9', 'Net Tax Liability', '', tax.netTaxLiability, { isBold: true }));

  if (tax.interest234A > 0 || tax.interest234B > 0 || tax.interest234C > 0 || tax.fee234F > 0) {
    taxRows.push(makeDataRow('10', 'Interest u/s 234A (Delay in filing return)', tax.interest234A, '', { indent: true }));
    taxRows.push(makeDataRow('11', 'Interest u/s 234B (Default in payment of advance tax)', tax.interest234B, '', { indent: true }));
    taxRows.push(makeDataRow('12', 'Interest u/s 234C (Deferment of advance tax instalments)', tax.interest234C, '', { indent: true }));
    if (tax.fee234F > 0) {
      taxRows.push(makeDataRow('13', 'Late Filing Fee u/s 234F', tax.fee234F, '', { indent: true }));
    }
  }
  taxRows.push(makeDataRow('D', 'TOTAL TAX, CESS, FEE AND INTEREST PAYABLE', '', tax.totalTaxAndInterest, { isBold: true, isTotal: true }));

  // Taxes Paid Section
  taxRows.push(makeDataRow('E', 'TAXES PAID / PREPAID TAXES CREDITS', '', '', { isBold: true, bg: palette.secondaryBg }));
  if (paid.advanceTax > 0) taxRows.push(makeDataRow('', 'Advance Tax Paid (Challan 280 / e-Pay Tax)', paid.advanceTax, '', { indent: true }));
  if (paid.tdsSalary > 0) taxRows.push(makeDataRow('', 'TDS on Salaries (As per Form 16 / 26AS / AIS)', paid.tdsSalary, '', { indent: true }));
  if (paid.tdsNonSalary > 0) taxRows.push(makeDataRow('', 'TDS on Other than Salaries (Form 16A / 26AS)', paid.tdsNonSalary, '', { indent: true }));
  if (paid.tcs > 0) taxRows.push(makeDataRow('', 'Tax Collected at Source (TCS)', paid.tcs, '', { indent: true }));
  if (paid.selfAssessmentTax > 0) taxRows.push(makeDataRow('', 'Self Assessment Tax Paid (u/s 140A)', paid.selfAssessmentTax, '', { indent: true }));
  taxRows.push(makeDataRow('F', 'TOTAL TAXES PAID / CREDITED', '', paid.totalTaxesPaid, { isBold: true, isTotal: true }));

  // Final Result Row: Refund Due or Tax Payable
  if (paid.refundDue > 0) {
    taxRows.push(
      makeDataRow('G', 'NET REFUND DUE TO ASSESSEE (Rounded off u/s 288B)', '', paid.refundDue, {
        isBold: true,
        bg: palette.secondaryBg,
      })
    );
  } else {
    taxRows.push(
      makeDataRow('G', 'BALANCE NET TAX PAYABLE (Rounded off u/s 288B)', '', paid.taxPayable, {
        isBold: true,
        bg: palette.secondaryBg,
      })
    );
  }

  const taxCompTable = new Table({
    width: { size: 9400, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    rows: taxRows,
  });

  // Words Callout Box
  const wordsParagraphs = [
    new Paragraph({
      spacing: { before: 120, after: 60 },
      children: [
        new TextRun({ text: 'Total Taxable Income in Words: ', font, bold: true, size: 20, color: palette.accentText }),
        new TextRun({ text: numberToIndianRupeesWords(tax.totalTaxableIncome), font, bold: true, size: 20 }),
      ],
    }),
    new Paragraph({
      spacing: { before: 0, after: 120 },
      children: [
        new TextRun({
          text: paid.refundDue > 0 ? 'Net Refund Claimed in Words: ' : 'Net Tax Payable in Words: ',
          font,
          bold: true,
          size: 20,
          color: palette.accentText,
        }),
        new TextRun({
          text: numberToIndianRupeesWords(paid.refundDue > 0 ? paid.refundDue : paid.taxPayable),
          font,
          bold: true,
          size: 20,
        }),
      ],
    }),
  ];

  // Bank details table (Concluding section of export)
  let bankDetailsTable: Table | null = null;
  if (cfg.includeBankDetails !== false) {
    bankDetailsTable = new Table({
      width: { size: 9400, type: WidthType.DXA },
      alignment: AlignmentType.CENTER,
      rows: [
        new TableRow({
          children: [
            makeInfoCell('Nominated Bank Name', p.bankName || 'State Bank of India', 3133),
            makeInfoCell('Account Number', p.bankAccountNumber || 'Provided on Portal', 3133),
            makeInfoCell('IFSC Code', p.bankIfsc || 'SBIN0001234', 3134),
          ],
        }),
      ],
    });
  }

  // Assemble document body children (strictly: Income -> Tax -> Bank Account)
  const bodyChildren: any[] = [
    ...titleParagraphs,
    personalInfoTable,
    new Paragraph({ spacing: { before: 140, after: 60 }, children: [new TextRun({ text: 'I. COMPUTATION OF TOTAL INCOME', font, bold: true, size: 22, color: palette.primary })] }),
    computationTable,
    new Paragraph({ spacing: { before: 140, after: 60 }, children: [new TextRun({ text: 'II. COMPUTATION OF TAX LIABILITY & TAXES PAID', font, bold: true, size: 22, color: palette.primary })] }),
    taxCompTable,
    ...wordsParagraphs,
  ];

  if (bankDetailsTable) {
    bodyChildren.push(
      new Paragraph({ spacing: { before: 120, after: 40 }, children: [new TextRun({ text: 'III. BANK ACCOUNT PARTICULARS FOR REFUND', font, bold: true, size: 20, color: palette.primary })] }),
      bankDetailsTable
    );
  }

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 720,    // 0.5 inch (720 dxa)
              bottom: 720,
              left: 720,
              right: 720,
            },
          },
        },
        headers: cfg.includeHeaderFooter
          ? {
              default: new Header({
                children: [
                  new Paragraph({
                    alignment: AlignmentType.RIGHT,
                    children: [
                      new TextRun({
                        text: `${p.name} | PAN: ${p.pan} | AY: ${p.assessmentYear}`,
                        font,
                        size: 16,
                        color: '9CA3AF',
                      }),
                    ],
                  }),
                ],
              }),
            }
          : undefined,
        footers: cfg.includeHeaderFooter
          ? {
              default: new Footer({
                children: [
                  new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                      new TextRun({ text: 'Page ', font, size: 16, color: '9CA3AF' }),
                      new TextRun({ children: [PageNumber.CURRENT], font, size: 16, color: '9CA3AF' }),
                      new TextRun({ text: ' of ', font, size: 16, color: '9CA3AF' }),
                      new TextRun({ children: [PageNumber.TOTAL_PAGES], font, size: 16, color: '9CA3AF' }),
                      new TextRun({ text: '  •  Generated via ITR Computation Studio', font, size: 16, color: '9CA3AF' }),
                    ],
                  }),
                ],
              }),
            }
          : undefined,
        children: bodyChildren,
      },
    ],
  });

  return doc;
}

/**
 * Exports and triggers instant download of the Word Document in browser
 */
export async function downloadITRDocx(data: CompleteITRData, customFileName?: string): Promise<Blob> {
  const doc = buildITRDocxDocument(data);
  const blob = await Packer.toBlob(doc);

  const cleanName = (data.personalInfo.name || 'Assessee').replace(/[^A-Za-z0-9]/g, '_').slice(0, 25);
  const pan = data.personalInfo.pan || 'PAN';
  const ay = (data.personalInfo.assessmentYear || '2026-27').replace(/[^0-9-]/g, '');
  const fileName = customFileName || `ITR_Computation_${cleanName}_${pan}_AY${ay}.docx`;

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
