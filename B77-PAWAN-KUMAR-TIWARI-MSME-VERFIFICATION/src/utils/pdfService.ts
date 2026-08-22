import jsPDF from 'jspdf';
import 'jspdf-autotable';
import { formatINR, formatDate } from './formatters';
import { InvoiceInterestResult, AgeingBucketSummary } from '../types';

interface ExportPdfOptions {
  title: string;
  subtitle?: string;
  reportCode?: string;
  columns: { header: string; dataKey: string }[];
  data: any[];
  summaryRows?: { label: string; value: string }[];
  fileName: string;
  orientation?: 'portrait' | 'landscape';
}

export function exportReportToPDF(options: ExportPdfOptions) {
  const {
    title,
    subtitle = 'MSMED Act 2006 & Section 43B(h) Statutory Compliance Report',
    reportCode = 'FIN-MSME-MIS',
    columns,
    data,
    summaryRows = [],
    fileName,
    orientation = 'landscape',
  } = options;

  const doc = new jsPDF({
    orientation,
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();

  // Header banner
  doc.setFillColor(15, 23, 42); // Deep slate
  doc.rect(0, 0, pageWidth, 24, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(255, 255, 255);
  doc.text('CORPORATE FINANCE & ACCOUNTS DEPARTMENT', 14, 10);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text(`MSME Statutory Compliance & Delayed Payment Tracking System | Report Ref: ${reportCode}`, 14, 16);

  const printDate = new Date().toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  doc.text(`Generated: ${printDate}`, pageWidth - 14, 16, { align: 'right' });

  // Report Title
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(15, 23, 42);
  doc.text(title, 14, 33);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(100, 116, 139);
  doc.text(subtitle, 14, 38);

  let currentY = 42;

  // Summary Metrics Banner if provided
  if (summaryRows.length > 0) {
    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(14, currentY, pageWidth - 28, 12, 2, 2, 'FD');

    doc.setFontSize(8);
    const colWidth = (pageWidth - 32) / summaryRows.length;
    summaryRows.forEach((item, idx) => {
      const itemX = 16 + idx * colWidth;
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(100, 116, 139);
      doc.text(item.label, itemX, currentY + 4.5);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.text(item.value, itemX, currentY + 9.5);
    });
    currentY += 16;
  }

  // Table rendering via autoTable
  (doc as any).autoTable({
    startY: currentY,
    head: [columns.map((c) => c.header)],
    body: data.map((row) => columns.map((c) => row[c.dataKey] ?? '—')),
    theme: 'grid',
    styles: {
      fontSize: 7.5,
      cellPadding: 2,
      font: 'helvetica',
      textColor: [30, 41, 59],
      lineColor: [226, 232, 240],
      lineWidth: 0.2,
    },
    headStyles: {
      fillColor: [30, 41, 59],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8,
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252],
    },
    margin: { left: 14, right: 14, bottom: 20 },
    didDrawPage: (dataObj: any) => {
      const pageCount = (doc as any).internal.getNumberOfPages();
      const pageCurrent = dataObj.pageNumber;
      
      // Footer
      doc.setFontSize(7.5);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(148, 163, 184);
      doc.text(
        'Confidential | Generated for Statutory Audit & MSME Delayed Payment Compliance (Section 15, 16 & 22 of MSMED Act 2006)',
        14,
        doc.internal.pageSize.getHeight() - 8
      );
      doc.text(
        `Page ${pageCurrent} of ${pageCount}`,
        pageWidth - 14,
        doc.internal.pageSize.getHeight() - 8,
        { align: 'right' }
      );
    },
  });

  doc.save(`${fileName}.pdf`);
}

export function exportInterestCalculationPDF(
  calculations: InvoiceInterestResult[],
  asOfDate: string,
  rateBasisText: string
) {
  const totalPrincipal = calculations.reduce((s, c) => s + c.outstandingPrincipal, 0);
  const totalInterest = calculations.reduce((s, c) => s + c.totalInterestPayable, 0);

  const columns = [
    { header: 'Invoice No', dataKey: 'invoiceNumber' },
    { header: 'Vendor Name', dataKey: 'vendorName' },
    { header: 'Category', dataKey: 'msmeCategory' },
    { header: 'Invoice Date', dataKey: 'invoiceDate' },
    { header: 'Due Date', dataKey: 'finalDueDate' },
    { header: 'Delay (Days)', dataKey: 'daysDelayed' },
    { header: 'Outstanding (₹)', dataKey: 'outstanding' },
    { header: 'Applicable Rate', dataKey: 'rate' },
    { header: 'MSME Interest (₹)', dataKey: 'interest' },
    { header: 'Status', dataKey: 'status' },
  ];

  const data = calculations.map((c) => ({
    invoiceNumber: c.invoiceNumber,
    vendorName: c.vendorName,
    msmeCategory: c.msmeCategory,
    invoiceDate: formatDate(c.invoiceDate),
    finalDueDate: formatDate(c.finalDueDate),
    daysDelayed: c.isOverdue ? `${c.totalDelayDays}d` : '0d',
    outstanding: formatINR(c.outstandingPrincipal),
    rate: `${c.applicableAnnualRate}% (3x RBI)`,
    interest: formatINR(c.totalInterestPayable),
    status: c.isOverdue ? 'OVERDUE' : 'COMPLIANT',
  }));

  exportReportToPDF({
    title: 'MSME Delayed Payment Statutory Interest Schedule',
    subtitle: `Calculated under Section 15 & 16 of MSMED Act 2006 as of ${formatDate(asOfDate)} | Rate: ${rateBasisText}`,
    reportCode: 'MSME-SEC16-INTEREST',
    columns,
    data,
    summaryRows: [
      { label: 'Total Invoices Evaluated', value: `${calculations.length} Invoices` },
      { label: 'Total Outstanding Principal', value: formatINR(totalPrincipal) },
      { label: 'Total Accrued Compounded Interest', value: formatINR(totalInterest) },
      { label: 'Tax Deductibility (Sec 23)', value: '100% Non-Deductible' },
    ],
    fileName: `MSME_Interest_Schedule_AsOf_${asOfDate}`,
    orientation: 'landscape',
  });
}

export function exportAgeingSchedulePDF(ageingSummary: any, asOfDate: string) {
  const columns = [
    { header: 'Ageing Bucket', dataKey: 'bucketName' },
    { header: 'Invoice Count', dataKey: 'invoiceCount' },
    { header: 'Total Principal Outstanding (₹)', dataKey: 'totalPrincipal' },
    { header: 'Accrued Interest (₹)', dataKey: 'totalInterest' },
    { header: 'Total Payable (₹)', dataKey: 'totalPayable' },
    { header: 'Vendor Count', dataKey: 'vendorCount' },
  ];

  const data = (ageingSummary.buckets || []).map((b: AgeingBucketSummary) => ({
    bucketName: b.bucketName,
    invoiceCount: String(b.invoiceCount),
    totalPrincipal: formatINR(b.totalPrincipal),
    totalInterest: formatINR(b.totalInterest),
    totalPayable: formatINR(b.totalPayable),
    vendorCount: String(b.vendorCount),
  }));

  exportReportToPDF({
    title: 'MSME Statutory Ageing & Delay Distribution Schedule',
    subtitle: `Outstanding balance & Section 16 interest by statutory delay buckets as of ${formatDate(asOfDate)}`,
    reportCode: 'MSME-AGEING-MATRIX',
    columns,
    data,
    summaryRows: [
      { label: 'Total Principal Outstanding', value: formatINR(ageingSummary.totalPrincipal || 0) },
      { label: 'Total Compounded Interest', value: formatINR(ageingSummary.totalInterest || 0) },
      { label: 'Total Statutory Liability', value: formatINR(ageingSummary.totalPayable || 0) },
    ],
    fileName: `MSME_Ageing_Matrix_AsOf_${asOfDate}`,
    orientation: 'portrait',
  });
}

export function exportMSME1ReturnPDF(delayedInvoices: InvoiceInterestResult[], periodName: string, fy: string) {
  const totalDue = delayedInvoices.reduce((s, c) => s + c.outstandingPrincipal, 0);

  const columns = [
    { header: 'Supplier Name', dataKey: 'vendorName' },
    { header: 'Category', dataKey: 'msmeCategory' },
    { header: 'Invoice No', dataKey: 'invoiceNumber' },
    { header: 'Invoice Date', dataKey: 'invoiceDate' },
    { header: 'Statutory Due Date', dataKey: 'finalDueDate' },
    { header: 'Delay (Days)', dataKey: 'daysDelayed' },
    { header: 'Amount Due (₹)', dataKey: 'amount' },
    { header: 'Reason for Delay', dataKey: 'reason' },
  ];

  const data = delayedInvoices.map((c) => ({
    vendorName: c.vendorName,
    msmeCategory: c.msmeCategory,
    invoiceNumber: c.invoiceNumber,
    invoiceDate: formatDate(c.invoiceDate),
    finalDueDate: formatDate(c.finalDueDate),
    daysDelayed: `${c.totalDelayDays} Days`,
    amount: formatINR(c.outstandingPrincipal),
    reason: 'Under commercial reconciliation & working capital allocation',
  }));

  exportReportToPDF({
    title: 'MCA Form MSME-1 (Half-Yearly Statutory Return)',
    subtitle: `Furnishing information regarding outstanding payment to Micro & Small Enterprises exceeding 45 days | Period: ${periodName} (FY ${fy})`,
    reportCode: 'MCA-FORM-MSME1',
    columns,
    data,
    summaryRows: [
      { label: 'Total Defaulting Invoices', value: `${delayedInvoices.length} Invoices` },
      { label: 'Total Overdue Amount', value: formatINR(totalDue) },
      { label: 'Statutory Authority', value: 'Ministry of Corporate Affairs' },
    ],
    fileName: `MCA_Form_MSME1_Return_${fy}`,
    orientation: 'landscape',
  });
}

export function exportSection43BHReportPDF(riskInvoices: InvoiceInterestResult[], fy: string, asOfDate: string) {
  const totalDisallowance = riskInvoices.reduce((s, c) => s + c.outstandingPrincipal, 0);
  const estTaxHit = totalDisallowance * 0.2517;

  const columns = [
    { header: 'Vendor Name', dataKey: 'vendorName' },
    { header: 'Category', dataKey: 'msmeCategory' },
    { header: 'Invoice No', dataKey: 'invoiceNumber' },
    { header: 'Invoice Date', dataKey: 'invoiceDate' },
    { header: 'Due Date', dataKey: 'finalDueDate' },
    { header: 'Disallowed Principal (₹)', dataKey: 'disallowed' },
    { header: 'MSME Interest (₹)', dataKey: 'interest' },
    { header: 'Est. Tax Impact (₹)', dataKey: 'taxHit' },
  ];

  const data = riskInvoices.map((c) => ({
    vendorName: c.vendorName,
    msmeCategory: c.msmeCategory,
    invoiceNumber: c.invoiceNumber,
    invoiceDate: formatDate(c.invoiceDate),
    finalDueDate: formatDate(c.finalDueDate),
    disallowed: formatINR(c.outstandingPrincipal),
    interest: formatINR(c.totalInterestPayable),
    taxHit: formatINR(c.outstandingPrincipal * 0.2517),
  }));

  exportReportToPDF({
    title: 'Income Tax Act – Section 43B(h) Disallowance Audit Schedule',
    subtitle: `Tax Audit Form 3CD Schedule for Micro & Small Supplier Dues Unpaid Beyond Section 15 Limits | FY: ${fy} as of ${formatDate(asOfDate)}`,
    reportCode: 'TAX-AUDIT-SEC43BH',
    columns,
    data,
    summaryRows: [
      { label: 'Total Disallowance (Add-back to PGBP)', value: formatINR(totalDisallowance) },
      { label: 'Est. Corporate Tax Impact (@ 25.17%)', value: formatINR(estTaxHit) },
      { label: 'Applicable Categories', value: 'Micro & Small Only' },
    ],
    fileName: `Tax_Audit_Sec_43BH_Disallowance_${fy}`,
    orientation: 'landscape',
  });
}

export function exportSection22DisclosuresPDF(metrics: any, fy: string, asOfDate: string) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();

  // Header
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, pageWidth, 28, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(255, 255, 255);
  doc.text('SECTION 22 MSMED ACT – FINANCIAL STATEMENTS DISCLOSURE', 14, 12);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(203, 213, 225);
  doc.text(`Mandatory Audit Note for Balance Sheet & P&L Accounts | FY ${fy} (As at ${formatDate(asOfDate)})`, 14, 19);

  const disclosureData = [
    [
      '(i)',
      'Principal amount remaining unpaid to MSME suppliers at the end of the accounting year',
      formatINR(metrics.totalMSMEOutstanding),
    ],
    [
      '(ii)',
      'Interest due on above principal remaining unpaid to MSME suppliers at year end',
      formatINR(metrics.estimatedInterestLiability),
    ],
    [
      '(iii)',
      'The amount of interest paid by the buyer in terms of Section 16, along with the amounts of payment made beyond appointed day',
      '₹0.00',
    ],
    [
      '(iv)',
      'Interest due and payable for the period of delay in making payment (which has been paid but beyond appointed day)',
      formatINR(metrics.estimatedInterestLiability),
    ],
    [
      '(v)',
      'Interest accrued and remaining unpaid at the end of the accounting year',
      formatINR(metrics.estimatedInterestLiability),
    ],
    [
      '(vi)',
      'Further interest remaining due and payable in succeeding years until actual payment',
      formatINR(metrics.estimatedInterestLiability),
    ],
  ];

  (doc as any).autoTable({
    startY: 38,
    head: [['Item', 'Statutory Particulars / Disclosure Clause', 'Amount (₹)']],
    body: disclosureData,
    theme: 'grid',
    styles: { fontSize: 8.5, cellPadding: 3, textColor: [30, 41, 59] },
    headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontStyle: 'bold' },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 15, halign: 'center' },
      1: { cellWidth: 125 },
      2: { fontStyle: 'bold', halign: 'right', cellWidth: 45 },
    },
    margin: { left: 14, right: 14 },
  });

  const finalY = (doc as any).lastAutoTable.finalY + 10;

  // Notes
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text('Auditor / Management Statutory Confirmation:', 14, finalY);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  const notes = [
    'The identification of suppliers registered under the Micro, Small and Medium Enterprises Development Act, 2006 is based on information available with the Company.',
    'Interest payable under Section 16 of MSMED Act has been computed with monthly rests at three times the RBI Bank Rate.',
    'Under Section 23 of MSMED Act, interest accrued/paid under this Act is disallowed as an expense in income tax assessment.',
  ];
  doc.text(notes, 14, finalY + 5);

  doc.save(`MSMED_Act_Sec22_Audit_Disclosures_FY_${fy}.pdf`);
}
