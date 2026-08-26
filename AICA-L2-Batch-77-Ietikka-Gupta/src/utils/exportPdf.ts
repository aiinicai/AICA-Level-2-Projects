import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { ChallanRecord, AssesseeDetails } from '../types';

export function exportTaxAuditToPdf(
  records: ChallanRecord[],
  assessee: AssesseeDetails
) {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  // Colors
  const primaryColor: [number, number, number] = [15, 23, 42]; // Slate 900
  const accentColor: [number, number, number] = [2, 132, 199]; // Sky 600
  const errorColor: [number, number, number] = [185, 28, 28]; // Red 700
  const successColor: [number, number, number] = [21, 128, 61]; // Green 700

  // 1. Header Bar
  doc.setFillColor(...primaryColor);
  doc.rect(0, 0, pageWidth, 22, 'F');

  // Title
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text("TAX AUDIT ANNEXURE: FORM 3CD - CLAUSE 20(b)", 14, 11);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text("Statement of Sums Received from Employees towards PF / ESI & Credited to Funds u/s 36(1)(va)", 14, 17);

  // Auditor Tag in Header
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text(`Tax Auditor: ${assessee.auditorName}`, pageWidth - 14, 11, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text(`${assessee.auditorDesignation} | ${assessee.firmName || "Tax Audit Practice"}`, pageWidth - 14, 16, { align: 'right' });

  // 2. Client & Audit Particulars Card
  let currentY = 28;

  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(14, currentY, pageWidth - 28, 22, 2, 2, 'FD');

  doc.setTextColor(51, 65, 85);
  doc.setFontSize(9);

  // Row 1
  doc.setFont('helvetica', 'bold');
  doc.text("Assessee Name:", 18, currentY + 7);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.name || "N/A", 48, currentY + 7);

  doc.setFont('helvetica', 'bold');
  doc.text("PAN:", 135, currentY + 7);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.pan || "N/A", 148, currentY + 7);

  doc.setFont('helvetica', 'bold');
  doc.text("Assessment Year:", 210, currentY + 7);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.assessmentYear || "2025-26", 244, currentY + 7);

  // Row 2
  doc.setFont('helvetica', 'bold');
  doc.text("Financial Year:", 18, currentY + 15);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.financialYear || "2024-25", 48, currentY + 15);

  doc.setFont('helvetica', 'bold');
  doc.text("Date of Audit:", 135, currentY + 15);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.dateOfReport, 160, currentY + 15);

  doc.setFont('helvetica', 'bold');
  doc.text("Report Certified By:", 210, currentY + 15);
  doc.setFont('helvetica', 'normal');
  doc.text(assessee.auditorName, 244, currentY + 15);

  // 3. Summary Metrics
  currentY += 26;

  const totalEmployeeContrib = records.reduce((s, r) => s + r.employeeContribution, 0);
  const totalDisallowed = records.reduce((s, r) => s + r.disallowableAmount, 0);
  const totalComplied = totalEmployeeContrib - totalDisallowed;
  const totalChallanPaid = records.reduce((s, r) => s + r.totalChallanAmount, 0);
  const delayedCount = records.filter(r => r.status === 'DELAYED').length;

  const cardWidth = (pageWidth - 28 - 9) / 4;

  // Metric Card 1: Total Deposited
  doc.setFillColor(241, 245, 249);
  doc.setDrawColor(203, 213, 225);
  doc.roundedRect(14, currentY, cardWidth, 16, 2, 2, 'FD');
  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(100, 116, 139);
  doc.text("TOTAL CHALLAN DEPOSIT", 18, currentY + 5);
  doc.setFontSize(10.5);
  doc.setTextColor(15, 23, 42);
  doc.text(`Rs. ${totalChallanPaid.toLocaleString('en-IN')}`, 18, currentY + 12);

  // Metric Card 2: Total Employee Share
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(14 + cardWidth + 3, currentY, cardWidth, 16, 2, 2, 'FD');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text("EMPLOYEE SHARE (36(1)(va))", 18 + cardWidth + 3, currentY + 5);
  doc.setFontSize(10.5);
  doc.setTextColor(15, 23, 42);
  doc.text(`Rs. ${totalEmployeeContrib.toLocaleString('en-IN')}`, 18 + cardWidth + 3, currentY + 12);

  // Metric Card 3: Complied On Time
  doc.setFillColor(240, 253, 244);
  doc.setDrawColor(187, 247, 208);
  doc.roundedRect(14 + (cardWidth + 3) * 2, currentY, cardWidth, 16, 2, 2, 'FD');
  doc.setFontSize(7.5);
  doc.setTextColor(22, 101, 52);
  doc.text("PAID BY DUE DATE (ALLOWED)", 18 + (cardWidth + 3) * 2, currentY + 5);
  doc.setFontSize(10.5);
  doc.setTextColor(21, 128, 61);
  doc.text(`Rs. ${totalComplied.toLocaleString('en-IN')}`, 18 + (cardWidth + 3) * 2, currentY + 12);

  // Metric Card 4: Disallowed u/s 36(1)(va)
  const isDisallowance = totalDisallowed > 0;
  doc.setFillColor(isDisallowance ? 254 : 241, isDisallowance ? 242 : 245, isDisallowance ? 242 : 249);
  doc.setDrawColor(isDisallowance ? 254 : 203, isDisallowance ? 202 : 213, isDisallowance ? 202 : 225);
  doc.roundedRect(14 + (cardWidth + 3) * 3, currentY, cardWidth, 16, 2, 2, 'FD');
  doc.setFontSize(7.5);
  doc.setTextColor(isDisallowance ? 185 : 100, isDisallowance ? 28 : 116, isDisallowance ? 28 : 139);
  doc.text("DISALLOWABLE U/S 36(1)(va)", 18 + (cardWidth + 3) * 3, currentY + 5);
  doc.setFontSize(10.5);
  doc.setTextColor(isDisallowance ? 185 : 15, isDisallowance ? 28 : 23, isDisallowance ? 28 : 42);
  doc.text(`Rs. ${totalDisallowed.toLocaleString('en-IN')}${delayedCount > 0 ? ` (${delayedCount} delayed)` : ''}`, 18 + (cardWidth + 3) * 3, currentY + 12);

  currentY += 20;

  // 4. Clause 20(b) Table
  const tableRows = records.map((rec, idx) => {
    const fundLabel = rec.fundType === 'PF' 
      ? `Employees' Provident Fund\n(${rec.wageMonth})` 
      : `Employees' State Insurance\n(${rec.wageMonth})`;

    const statusRemarks = rec.status === 'DELAYED'
      ? `DELAYED by ${rec.delayDays} day(s)\nRef: ${rec.challanReference}`
      : `Paid on time\nRef: ${rec.challanReference}`;

    return [
      String(idx + 1),
      fundLabel,
      `Rs. ${rec.employeeContribution.toLocaleString('en-IN')}`,
      rec.statutoryDueDate,
      rec.actualPaymentDate,
      `Rs. ${rec.employeeContribution.toLocaleString('en-IN')}`,
      rec.disallowableAmount > 0 ? `Rs. ${rec.disallowableAmount.toLocaleString('en-IN')}` : "NIL",
      statusRemarks,
    ];
  });

  // Add Grand Total Row
  tableRows.push([
    "TOTAL",
    "GRAND TOTAL",
    `Rs. ${totalEmployeeContrib.toLocaleString('en-IN')}`,
    "-",
    "-",
    `Rs. ${totalEmployeeContrib.toLocaleString('en-IN')}`,
    `Rs. ${totalDisallowed.toLocaleString('en-IN')}`,
    totalDisallowed > 0 
      ? `Total 36(1)(va) Disallowance: Rs. ${totalDisallowed.toLocaleString('en-IN')}`
      : "Full Statutory Compliance"
  ]);

  autoTable(doc, {
    startY: currentY,
    head: [[
      "Sl. No.",
      "Nature of Fund",
      "Sum Received from Employees",
      "Due Date for Payment",
      "Actual Date of Payment",
      "Actual Amount Paid",
      "Amount Not Credited by Due Date (Disallowed u/s 36(1)(va))",
      "Remarks / TRRN / Challan Ref"
    ]],
    body: tableRows,
    theme: 'grid',
    headStyles: {
      fillColor: [30, 41, 59],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8,
      halign: 'center',
      valign: 'middle',
    },
    bodyStyles: {
      fontSize: 7.5,
      textColor: [30, 41, 59],
      valign: 'middle',
    },
    columnStyles: {
      0: { cellWidth: 12, halign: 'center' },
      1: { cellWidth: 48 },
      2: { cellWidth: 34, halign: 'right' },
      3: { cellWidth: 26, halign: 'center' },
      4: { cellWidth: 26, halign: 'center' },
      5: { cellWidth: 34, halign: 'right' },
      6: { cellWidth: 42, halign: 'right', fontStyle: 'bold' },
      7: { cellWidth: 46 },
    },
    didParseCell: (data) => {
      // Highlight delayed disallowable rows
      if (data.section === 'body' && data.row.index < records.length) {
        const record = records[data.row.index];
        if (record && record.status === 'DELAYED') {
          if (data.column.index === 6) {
            data.cell.styles.textColor = [185, 28, 28]; // Red
            data.cell.styles.fillColor = [254, 242, 242];
          }
        }
      }
      // Grand total row styling
      if (data.section === 'body' && data.row.index === records.length) {
        data.cell.styles.fontStyle = 'bold';
        data.cell.styles.fillColor = [241, 245, 249];
        if (data.column.index === 6 && totalDisallowed > 0) {
          data.cell.styles.textColor = [185, 28, 28];
        }
      }
    },
    margin: { left: 14, right: 14, bottom: 35 },
  });

  // 5. Statutory Notes and Auditor Signature
  let finalY = (doc as any).lastAutoTable.finalY + 6;

  if (finalY > pageHeight - 35) {
    doc.addPage();
    finalY = 20;
  }

  // Statutory Note box
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(14, finalY, pageWidth - 120, 22, 1, 1, 'FD');

  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(71, 85, 105);
  doc.text("STATUTORY & AUDIT NOTES (FORM 3CD - CLAUSE 20(b)):", 17, finalY + 4.5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  doc.setTextColor(100, 116, 139);
  doc.text("1. As per Section 36(1)(va), employee contribution is allowable ONLY if deposited on/before the 15th of the succeeding month.", 17, finalY + 9);
  doc.text("2. Landmark Supreme Court Ruling in Checkmate Services P. Ltd vs CIT [2022] 448 ITR 518 (SC) confirms Section 43B does NOT apply.", 17, finalY + 13.5);
  doc.text("3. Any amount appearing under Column 7 must be disallowed and added back to Total Income in the Tax Audit Report.", 17, finalY + 18);

  // Auditor Signature Box
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(203, 213, 225);
  doc.roundedRect(pageWidth - 98, finalY, 84, 22, 1, 1, 'FD');

  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(15, 23, 42);
  doc.text("CERTIFIED & COMPILED BY:", pageWidth - 94, finalY + 5);

  doc.setFontSize(9);
  doc.setTextColor(2, 132, 199);
  doc.text(assessee.auditorName, pageWidth - 94, finalY + 11);

  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100, 116, 139);
  doc.text(`${assessee.auditorDesignation} | M.No: ${assessee.membershipNumber || "524189"}`, pageWidth - 94, finalY + 16);
  doc.text(`Date: ${assessee.dateOfReport} | Digitized Tax Audit Schedule`, pageWidth - 94, finalY + 20);

  // Footer on all pages
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(148, 163, 184);
    doc.text(
      `Tax Audit ESI & PF Digitizer | Created by CA Ietikka Gupta | Page ${i} of ${totalPages}`,
      pageWidth / 2,
      pageHeight - 5,
      { align: 'center' }
    );
  }

  const cleanAssesseeName = (assessee.name || "Assessee").replace(/[^a-zA-Z0-9]/g, "_");
  const fileName = `Form_3CD_Clause_20b_Report_${cleanAssesseeName}_AY_${assessee.assessmentYear.replace('/', '_')}.pdf`;
  doc.save(fileName);
}
