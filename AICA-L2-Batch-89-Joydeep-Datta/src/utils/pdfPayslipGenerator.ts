import jsPDF from 'jspdf';
import { toPng } from 'html-to-image';
import { MonthlySalaryRecord } from '../types/payroll';
import { amountToWordsIndian } from './numberToWords';

/**
 * Pure vector fallback generator using jsPDF primitives.
 * Completely immune to CSS parser issues like oklch(), cross-origin images, or iframe sandbox restrictions.
 */
export function buildVectorPayslipDoc(record: MonthlySalaryRecord): jsPDF {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = 210;
  const leftMargin = 15;
  const rightMargin = 195;
  const contentWidth = rightMargin - leftMargin;

  // Header Banner
  doc.setFillColor(15, 23, 42); // slate-900
  doc.rect(leftMargin, 12, contentWidth, 22, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text('ACME ENTERPRISES INDIA PVT LTD', leftMargin + 6, 20);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(203, 213, 225); // slate-300
  doc.text('Corporate Payroll & Statutory TDS Disbursement Division', leftMargin + 6, 25);
  doc.text('Registered Office: Cyber City, Tower B, Gurugram, HR 122002', leftMargin + 6, 29);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text(`SALARY SLIP: ${record.monthName.toUpperCase()} ${record.year}`, rightMargin - 6, 20, { align: 'right' });

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(148, 163, 184);
  doc.text('Per Indian IT Rules u/s 192', rightMargin - 6, 26, { align: 'right' });

  let y = 39;

  // Employee Details Box
  doc.setDrawColor(226, 232, 240);
  doc.setFillColor(248, 250, 252);
  doc.roundedRect(leftMargin, y, contentWidth, 26, 2, 2, 'FD');

  const colW = contentWidth / 4;
  const details = [
    [
      { label: 'Employee Code', val: record.employeeCode, bold: true },
      { label: 'Employee Name', val: record.employeeName, bold: true },
      { label: 'Designation', val: record.designation },
      { label: 'Department', val: record.department },
    ],
    [
      { label: 'PAN', val: record.pan, bold: true },
      { label: 'Tax Regime', val: `${record.regimeApplied} Regime`, highlight: true },
      { label: 'Bank A/C No', val: record.bankAccountNo },
      { label: 'Bank & IFSC', val: `${record.bankName} (${record.ifsc})` },
    ],
  ];

  details.forEach((row, rIdx) => {
    const rowY = y + 7 + rIdx * 11;
    row.forEach((item, cIdx) => {
      const colX = leftMargin + 4 + cIdx * colW;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(6.5);
      doc.setTextColor(100, 116, 139);
      doc.text(item.label.toUpperCase(), colX, rowY);

      doc.setFont('helvetica', item.bold ? 'bold' : 'normal');
      doc.setFontSize(8);
      if (item.highlight) {
        doc.setTextColor(79, 70, 229); // indigo
      } else {
        doc.setTextColor(15, 23, 42);
      }
      doc.text(String(item.val), colX, rowY + 4.5);
    });
  });

  y += 30;

  // Attendance Bar
  doc.setFillColor(241, 245, 249);
  doc.rect(leftMargin, y, contentWidth, 8, 'F');
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);

  const attX1 = leftMargin + 6;
  const attX2 = leftMargin + 50;
  const attX3 = leftMargin + 95;
  const attX4 = leftMargin + 140;

  doc.text(`Total Days: ${record.totalDaysInMonth}`, attX1, y + 5.5);
  doc.text(`Payable Days: ${record.payableDays}`, attX2, y + 5.5);
  doc.text(`Loss of Pay (LOP): ${record.lopDays} days`, attX3, y + 5.5);
  doc.text(`Proration: ${(record.prorationFactor * 100).toFixed(1)}%`, attX4, y + 5.5);

  y += 12;

  // Tables Grid: Left = Earnings, Right = Deductions
  const halfW = (contentWidth - 6) / 2;
  const leftTableX = leftMargin;
  const rightTableX = leftMargin + halfW + 6;

  // Header background
  doc.setFillColor(241, 245, 249);
  doc.rect(leftTableX, y, halfW, 7, 'F');
  doc.rect(rightTableX, y, halfW, 7, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text('EARNINGS', leftTableX + 4, y + 5);
  doc.text('AMOUNT (INR)', leftTableX + halfW - 4, y + 5, { align: 'right' });

  doc.text('DEDUCTIONS', rightTableX + 4, y + 5);
  doc.text('AMOUNT (INR)', rightTableX + halfW - 4, y + 5, { align: 'right' });

  y += 7;

  // Rows data
  const earningsList: [string, number][] = [
    ['Basic Salary', record.basicEarned],
    ['House Rent Allowance (HRA)', record.hraEarned],
    ['Conveyance Allowance', record.conveyanceEarned],
    ['Special Allowance', record.specialAllowanceEarned],
  ];
  if (record.ceaEarned > 0) earningsList.push(['Children Education Allw', record.ceaEarned]);
  if (record.ltaEarned > 0) earningsList.push(['Leave Travel Allowance (LTA)', record.ltaEarned]);

  const deductionsList: [string, number][] = [
    ['Employee Provident Fund (EPF 12%)', record.employeePf],
    ['Professional Tax (PT)', record.professionalTax],
    ['Income Tax / TDS (Sec 192)', record.tdsDeducted],
  ];
  if (record.otherDeductions > 0) {
    deductionsList.push(['Other Recurring Deductions', record.otherDeductions]);
  }

  const maxRows = Math.max(earningsList.length, deductionsList.length);
  const rowHeight = 6.5;

  for (let i = 0; i < maxRows; i++) {
    const curY = y + i * rowHeight;
    // alternating row background
    if (i % 2 === 1) {
      doc.setFillColor(248, 250, 252);
      doc.rect(leftTableX, curY, halfW, rowHeight, 'F');
      doc.rect(rightTableX, curY, halfW, rowHeight, 'F');
    }

    // Border line bottom
    doc.setDrawColor(241, 245, 249);
    doc.line(leftTableX, curY + rowHeight, leftTableX + halfW, curY + rowHeight);
    doc.line(rightTableX, curY + rowHeight, rightTableX + halfW, curY + rowHeight);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(51, 65, 85);

    if (i < earningsList.length) {
      const [lbl, amt] = earningsList[i];
      doc.text(lbl, leftTableX + 4, curY + 4.5);
      doc.text(`INR ${amt.toLocaleString('en-IN')}`, leftTableX + halfW - 4, curY + 4.5, { align: 'right' });
    }

    if (i < deductionsList.length) {
      const [lbl, amt] = deductionsList[i];
      doc.text(lbl, rightTableX + 4, curY + 4.5);
      doc.text(`INR ${amt.toLocaleString('en-IN')}`, rightTableX + halfW - 4, curY + 4.5, { align: 'right' });
    }
  }

  y += maxRows * rowHeight;

  // Totals Row
  doc.setFillColor(241, 245, 249);
  doc.rect(leftTableX, y, halfW, 7, 'F');
  doc.rect(rightTableX, y, halfW, 7, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(15, 23, 42);
  doc.text('TOTAL GROSS EARNINGS', leftTableX + 4, y + 5);
  doc.text(`INR ${record.grossEarned.toLocaleString('en-IN')}`, leftTableX + halfW - 4, y + 5, { align: 'right' });

  doc.text('TOTAL DEDUCTIONS', rightTableX + 4, y + 5);
  doc.text(`INR ${record.totalDeductions.toLocaleString('en-IN')}`, rightTableX + halfW - 4, y + 5, { align: 'right' });

  y += 11;

  // Net Pay Box
  doc.setFillColor(238, 242, 255); // indigo-50
  doc.setDrawColor(199, 210, 254); // indigo-200
  doc.roundedRect(leftMargin, y, contentWidth, 18, 2, 2, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(30, 27, 75); // indigo-950
  doc.text('NET TAKE-HOME PAY (Disbursed to Bank)', leftMargin + 6, y + 7.5);

  doc.setFontSize(14);
  doc.setTextColor(67, 56, 202); // indigo-700
  doc.text(`INR ${record.netPay.toLocaleString('en-IN')}`, rightMargin - 6, y + 8, { align: 'right' });

  doc.setFont('helvetica', 'italic');
  doc.setFontSize(7.5);
  doc.setTextColor(79, 70, 229);
  const netWords = amountToWordsIndian(record.netPay);
  doc.text(`In Words: ${netWords}`, leftMargin + 6, y + 14);

  y += 22;

  // Income Tax / TDS Summary Grid
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(leftMargin, y, contentWidth, 24, 2, 2, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(15, 23, 42);
  doc.text(`ANNUAL INCOME TAX SUMMARY (AY 2026-27 | ${record.regimeApplied.toUpperCase()} REGIME)`, leftMargin + 6, y + 6);

  const taxCalc = record.taxCalculation;
  const projectedGross = taxCalc ? taxCalc.annualGrossSalary : 0;
  const exemptionsAnd80C = taxCalc
    ? (taxCalc.exemptionsSec10?.total || 0) + (taxCalc.chapterViaDeductions?.total || 0)
    : 0;
  const netTaxable = taxCalc ? taxCalc.netTaxableIncome : 0;
  const totalAnnualTax = taxCalc ? taxCalc.totalAnnualTaxLiability : (record.annualTaxLiability || 0);
  const remainingMonthlyTds = taxCalc ? taxCalc.currentMonthTds : record.tdsDeducted;

  const tdsCols = [
    { lbl: 'Projected Gross', val: `INR ${projectedGross.toLocaleString('en-IN')}` },
    { lbl: 'Exemptions & 80C', val: `INR ${exemptionsAnd80C.toLocaleString('en-IN')}` },
    { lbl: 'Net Taxable', val: `INR ${netTaxable.toLocaleString('en-IN')}` },
    { lbl: 'Total Annual Tax', val: `INR ${totalAnnualTax.toLocaleString('en-IN')}` },
    { lbl: 'Remaining TDS / Mo', val: `INR ${remainingMonthlyTds.toLocaleString('en-IN')}` },
  ];

  const tdsColW = contentWidth / 5;
  tdsCols.forEach((col, idx) => {
    const colX = leftMargin + 6 + idx * tdsColW;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(col.lbl.toUpperCase(), colX, y + 13);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(15, 23, 42);
    doc.text(col.val, colX, y + 19);
  });

  y += 29;

  // Disclaimer and Signature Note
  doc.setFont('helvetica', 'italic');
  doc.setFontSize(6.5);
  doc.setTextColor(148, 163, 184);
  doc.text('Note: This is a system-generated salary slip and does not require a physical signature.', leftMargin, y + 5);
  doc.text(`Generated on: ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} | ACME Enterprises HR-Portal`, rightMargin, y + 5, { align: 'right' });

  return doc;
}

export function generateDirectVectorPayslipPdf(record: MonthlySalaryRecord): void {
  const doc = buildVectorPayslipDoc(record);
  const filename = `Payslip_${record.employeeCode}_${record.monthName}_${record.year}.pdf`;
  doc.save(filename);
}

export function getVectorPayslipBlobUrl(record: MonthlySalaryRecord): string {
  const doc = buildVectorPayslipDoc(record);
  const blob = doc.output('blob');
  return URL.createObjectURL(blob);
}

/**
 * Downloads payslip as PDF with multi-layer fallback:
 * 1. Tries html-to-image toPng (which natively supports oklch colors).
 * 2. If blocked or error occurs, seamlessly executes direct vector generator.
 */
export async function downloadPayslipPdf(
  elementId: string,
  record: MonthlySalaryRecord
): Promise<void> {
  const payslipElement = document.getElementById(elementId);

  // Strategy 1: Attempt html-to-image (handles modern css/oklch natively via SVG foreignObject)
  if (payslipElement) {
    try {
      const dataUrl = await toPng(payslipElement, {
        quality: 0.98,
        pixelRatio: 2,
        backgroundColor: '#ffffff',
        cacheBust: true,
      });

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      const imgWidth = 210;
      const pageHeight = 297;

      // Load image to determine native aspect ratio
      const img = new Image();
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error('Image failed to load from toPng'));
        img.src = dataUrl;
      });

      const imgHeight = (img.height * imgWidth) / img.width;
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(dataUrl, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(dataUrl, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      const filename = `Payslip_${record.employeeCode}_${record.monthName}_${record.year}.pdf`;
      pdf.save(filename);
      return;
    } catch (err) {
      console.warn('html-to-image capture encountered issue, switching to direct vector PDF generator:', err);
    }
  }

  // Strategy 2: Direct Vector Generation (100% reliable, zero css dependencies)
  generateDirectVectorPayslipPdf(record);
}
