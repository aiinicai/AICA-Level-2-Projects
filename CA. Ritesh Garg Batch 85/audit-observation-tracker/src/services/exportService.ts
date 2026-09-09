import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import { Document, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel, BorderStyle, ShadingType, Packer } from 'docx';
import { saveAs } from 'file-saver';
import { Engagement, Observation, FirmProfile, AuditType } from '../types/audit';
import { formatDate, formatINR, formatINRNumberOnly } from '../utils/formatters';

export class ExportService {
  private static normalizeFirm(firm?: Partial<FirmProfile>): FirmProfile {
    return {
      firmName: firm?.firmName || 'R. K. Garg & Associates',
      frn: firm?.frn || '014285N',
      address: firm?.address || 'Suite 402, Mercantile House, 15 K.G. Marg, Connaught Place',
      city: firm?.city || 'New Delhi - 110001',
      phone: firm?.phone || '+91 11 4356 8900',
      email: firm?.email || 'audit@rkgargca.in',
      partnerName: firm?.partnerName || 'CA Ritesh Garg, FCA',
      membershipNo: firm?.membershipNo || '098765',
      website: firm?.website || 'www.rkgargca.com',
    };
  }

  /**
   * Generates a single Observation PDF in official CA firm letterhead format
   */
  static exportSingleObservationPDF(
    obs: Observation,
    eng: Engagement,
    auditType: AuditType | undefined,
    firm?: Partial<FirmProfile>
  ) {
    const f = ExportService.normalizeFirm(firm);
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    let y = 15;

    // Header / Firm Letterhead
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.setTextColor(30, 41, 59); // Slate 800
    doc.text(f.firmName.toUpperCase(), pageWidth / 2, y, { align: 'center' });

    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139); // Slate 500
    doc.text(`Chartered Accountants | FRN: ${f.frn}`, pageWidth / 2, y, { align: 'center' });

    y += 4;
    doc.text(`${f.address}, ${f.city} | Email: ${f.email} | Phone: ${f.phone}`, pageWidth / 2, y, { align: 'center' });

    y += 3;
    doc.setDrawColor(203, 213, 225); // Slate 300
    doc.setLineWidth(0.5);
    doc.line(14, y, pageWidth - 14, y);

    y += 7;

    // Title & Reference Badge
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text('AUDIT OBSERVATION MEMORANDUM', 14, y);

    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text(`Ref No: ${obs.referenceNo}`, pageWidth - 14, y, { align: 'right' });

    y += 6;

    // Engagement Overview Box
    autoTable(doc, {
      startY: y,
      theme: 'grid',
      head: [['Assignment Context', 'Details']],
      body: [
        ['Client Name', eng.clientName],
        ['PAN / GSTIN', eng.clientPanGstin || 'Not Specified'],
        ['Audit Type & FY', `${auditType?.name || 'Audit'} (${eng.financialYear})`],
        ['Branch / Location', eng.branchLocation || 'Head Office / Central'],
        ['Engagement Partner', `${eng.engagementPartner} (${f.partnerName})`],
        ['Date of Observation', formatDate(obs.dateOfObservation)],
      ],
      headStyles: {
        fillColor: [30, 41, 59],
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        fontSize: 8.5,
      },
      styles: {
        fontSize: 8.5,
        cellPadding: 2,
        textColor: [30, 41, 59],
      },
      columnStyles: {
        0: { cellWidth: 45, fontStyle: 'bold', fillColor: [248, 250, 252] },
        1: { cellWidth: 'auto' },
      },
      margin: { left: 14, right: 14 },
    });

    y = (doc as any).lastAutoTable.finalY + 5;

    // Severity & Status Highlights
    const severityColor: [number, number, number] =
      obs.severity === 'Critical' ? [225, 29, 72] :
      obs.severity === 'High' ? [217, 119, 6] :
      obs.severity === 'Medium' ? [202, 138, 4] : [16, 185, 129];

    doc.setFillColor(severityColor[0], severityColor[1], severityColor[2]);
    doc.roundedRect(14, y, 35, 7, 1, 1, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.setTextColor(255, 255, 255);
    doc.text(`Risk: ${obs.severity.toUpperCase()}`, 17, y + 4.8);

    doc.setFillColor(241, 245, 249);
    doc.setDrawColor(203, 213, 225);
    doc.roundedRect(53, y, 45, 7, 1, 1, 'FD');
    doc.setTextColor(30, 41, 59);
    doc.text(`Status: ${obs.status}`, 56, y + 4.8);

    if (obs.financialImpact && obs.financialImpact > 0) {
      doc.setFillColor(254, 242, 242);
      doc.setDrawColor(254, 202, 202);
      doc.roundedRect(102, y, 55, 7, 1, 1, 'FD');
      doc.setTextColor(153, 27, 27);
      doc.text(`Exposure: ${formatINR(obs.financialImpact)}`, 105, y + 4.8);
    }

    y += 11;

    // Observation Findings Table
    autoTable(doc, {
      startY: y,
      theme: 'grid',
      head: [['Key Parameter', 'Audit Finding & Discussion Particulars']],
      body: [
        ['Process / Area', obs.areaProcess],
        ['Observation Description', obs.description],
        ['Root Cause Analysis', obs.rootCause || 'Not specified'],
        ['Audit Recommendation', obs.recommendation || 'Management to ensure compliance.'],
        ['Discussion Stakeholder(s)', obs.discussionStakeholder || 'Discussed during fieldwork'],
        ['Date of Discussion', formatDate(obs.dateOfDiscussion)],
        ['Management Response', obs.managementResponse || 'Pending management confirmation.'],
        ['Rectification Status', `${obs.rectificationStatus} ${obs.targetRectificationDate ? `(Target: ${formatDate(obs.targetRectificationDate)})` : ''}`],
        ['Responsible Auditor', obs.personResponsible],
        ['Supporting Reference(s)', obs.attachments || 'Field audit working papers'],
      ],
      headStyles: {
        fillColor: [51, 65, 85],
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        fontSize: 8.5,
      },
      styles: {
        fontSize: 8.5,
        cellPadding: 2.5,
        textColor: [30, 41, 59],
        overflow: 'linebreak',
      },
      columnStyles: {
        0: { cellWidth: 45, fontStyle: 'bold', fillColor: [248, 250, 252] },
        1: { cellWidth: 'auto' },
      },
      margin: { left: 14, right: 14 },
    });

    y = (doc as any).lastAutoTable.finalY + 12;

    // Check page break for signature block
    if (y > 250) {
      doc.addPage();
      y = 25;
    }

    // Sign-off block
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(71, 85, 105);

    doc.text('For and on behalf of the Audit Team:', 14, y);
    doc.text('Client Acknowledgement / Discussion Sign-off:', pageWidth - 14, y, { align: 'right' });

    y += 12;
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text(`(${f.partnerName})`, 14, y);
    doc.text(`(${obs.discussionStakeholder ? obs.discussionStakeholder.split(',')[0] : 'Authorised Signatory'})`, pageWidth - 14, y, { align: 'right' });

    y += 4;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text(`Partner | M. No. ${f.membershipNo}`, 14, y);
    doc.text(`Designation: Management Representative`, pageWidth - 14, y, { align: 'right' });

    // Footer
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(7);
      doc.setTextColor(148, 163, 184);
      doc.text(
        `Generated via CA Audit Observation Tracker | ${f.firmName} | Page ${i} of ${pageCount}`,
        pageWidth / 2,
        290,
        { align: 'center' }
      );
    }

    doc.save(`Observation_${obs.referenceNo}.pdf`);
  }

  /**
   * Generates a single Observation in Microsoft Word (.docx) format
   */
  static async exportSingleObservationDocx(
    obs: Observation,
    eng: Engagement,
    auditType: AuditType | undefined,
    firm?: Partial<FirmProfile>
  ) {
    const f = ExportService.normalizeFirm(firm);
    const doc = new Document({
      sections: [
        {
          properties: {},
          children: [
            // Firm Header
            new Paragraph({
              text: f.firmName.toUpperCase(),
              heading: HeadingLevel.HEADING_1,
              alignment: AlignmentType.CENTER,
              spacing: { after: 60 },
            }),
            new Paragraph({
              children: [
                new TextRun({
                  text: `Chartered Accountants | FRN: ${f.frn}\n`,
                  bold: true,
                  size: 18,
                  color: '475569',
                }),
                new TextRun({
                  text: `${f.address}, ${f.city} | Email: ${f.email} | Phone: ${f.phone}`,
                  size: 16,
                  color: '64748B',
                }),
              ],
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
            }),

            // Title
            new Paragraph({
              children: [
                new TextRun({
                  text: 'AUDIT OBSERVATION MEMORANDUM',
                  bold: true,
                  size: 24,
                  color: '0F172A',
                }),
                new TextRun({
                  text: `\nReference No: ${obs.referenceNo} | Date: ${formatDate(obs.dateOfObservation)}`,
                  size: 20,
                  bold: true,
                  color: '2563EB',
                }),
              ],
              alignment: AlignmentType.LEFT,
              spacing: { before: 100, after: 200 },
            }),

            // Details Table
            new Table({
              width: { size: 100, type: WidthType.PERCENTAGE },
              rows: [
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Client Name', style: 'bold' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                      width: { size: 30, type: WidthType.PERCENTAGE },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: eng.clientName })],
                      width: { size: 70, type: WidthType.PERCENTAGE },
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'PAN / GSTIN' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: eng.clientPanGstin || 'N/A' })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Audit Type & Period' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: `${auditType?.name || 'Audit'} (${eng.financialYear})` })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Branch / Location' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: eng.branchLocation || 'Central / Main' })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Severity & Exposure' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: `${obs.severity.toUpperCase()} | Financial Impact: ${formatINR(obs.financialImpact)}` })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Area / Process' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: obs.areaProcess })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Observation Finding' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: obs.description })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Root Cause' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: obs.rootCause || 'Not specified' })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Recommendation' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: obs.recommendation || 'Ensure necessary corrective action' })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Discussion Particulars' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: `Discussed with: ${obs.discussionStakeholder || 'N/A'} on ${formatDate(obs.dateOfDiscussion)}` })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Management Response' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: obs.managementResponse || 'Awaiting response' })],
                    }),
                  ],
                }),
                new TableRow({
                  children: [
                    new TableCell({
                      children: [new Paragraph({ text: 'Status & Rectification' })],
                      shading: { fill: 'F1F5F9', type: ShadingType.CLEAR, color: 'auto' },
                    }),
                    new TableCell({
                      children: [new Paragraph({ text: `Status: ${obs.status} | Rectification: ${obs.rectificationStatus} ${obs.targetRectificationDate ? `(Target: ${formatDate(obs.targetRectificationDate)})` : ''}` })],
                    }),
                  ],
                }),
              ],
            }),

            // Sign-off
            new Paragraph({
              children: [
                new TextRun({
                  text: `\n\nFor ${firm.firmName}\nChartered Accountants\n\n\n(${firm.partnerName})\nPartner | M. No. ${firm.membershipNo}`,
                  size: 20,
                  bold: true,
                }),
              ],
              spacing: { before: 300 },
            }),
          ],
        },
      ],
    });

    const blob = await Packer.toBlob(doc);
    saveAs(blob, `Observation_${obs.referenceNo}.docx`);
  }

  /**
   * Generates Combined PDF Report for an entire Engagement (Executive Summary + Detailed Sheets)
   */
  static exportEngagementReportPDF(
    eng: Engagement,
    observations: Observation[],
    auditType: AuditType | undefined,
    firm?: Partial<FirmProfile>
  ) {
    const f = ExportService.normalizeFirm(firm);
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    let y = 15;

    // Firm Letterhead
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.setTextColor(30, 41, 59);
    doc.text(f.firmName.toUpperCase(), pageWidth / 2, y, { align: 'center' });

    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text(`Chartered Accountants | FRN: ${f.frn} | ${f.address}, ${f.city}`, pageWidth / 2, y, { align: 'center' });

    y += 3;
    doc.setDrawColor(203, 213, 225);
    doc.line(14, y, pageWidth - 14, y);

    y += 8;

    // Report Title
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(15, 23, 42);
    doc.text('AUDIT OBSERVATION & EXECUTIVE MANAGEMENT REPORT', pageWidth / 2, y, { align: 'center' });

    y += 7;

    // Executive Summary Box
    const totalExposure = observations.reduce((acc, o) => acc + (o.financialImpact || 0), 0);
    const criticalCount = observations.filter(o => o.severity === 'Critical').length;
    const highCount = observations.filter(o => o.severity === 'High').length;
    const mediumCount = observations.filter(o => o.severity === 'Medium').length;
    const lowCount = observations.filter(o => o.severity === 'Low').length;
    const closedCount = observations.filter(o => o.status === 'Closed' || o.status === 'Rectified').length;
    const openCount = observations.length - closedCount;

    autoTable(doc, {
      startY: y,
      theme: 'grid',
      head: [['Engagement Particulars', 'Summary Metrics']],
      body: [
        ['Client Name', eng.clientName],
        ['PAN / GSTIN', eng.clientPanGstin || 'Not Specified'],
        ['Audit Type', auditType?.name || 'Audit'],
        ['Period / FY', eng.financialYear],
        ['Audit Period', `${formatDate(eng.startDate)} to ${formatDate(eng.endDate)}`],
        ['Engagement Partner & Team', `${eng.engagementPartner} | Team: ${eng.teamMembers.join(', ') || 'Staff'}`],
        ['Total Observations Logged', `${observations.length} (Open: ${openCount} | Rectified/Closed: ${closedCount})`],
        ['Risk Breakdown', `Critical: ${criticalCount} | High: ${highCount} | Medium: ${mediumCount} | Low: ${lowCount}`],
        ['Total Financial Exposure (₹)', formatINR(totalExposure)],
      ],
      headStyles: {
        fillColor: [30, 41, 59],
        fontSize: 8.5,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 8.5,
        cellPadding: 2,
      },
      columnStyles: {
        0: { cellWidth: 50, fontStyle: 'bold', fillColor: [248, 250, 252] },
        1: { cellWidth: 'auto' },
      },
      margin: { left: 14, right: 14 },
    });

    y = (doc as any).lastAutoTable.finalY + 8;

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text('Summary Table of Audit Observations', 14, y);

    y += 4;

    // Observations List Table
    autoTable(doc, {
      startY: y,
      theme: 'grid',
      head: [['Ref No.', 'Date', 'Area / Process', 'Severity', 'Financial Exposure', 'Status', 'Rectification']],
      body: observations.map(o => [
        o.referenceNo,
        formatDate(o.dateOfObservation),
        o.areaProcess,
        o.severity,
        formatINR(o.financialImpact),
        o.status,
        o.rectificationStatus,
      ]),
      headStyles: {
        fillColor: [51, 65, 85],
        fontSize: 8,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 7.5,
        cellPadding: 2,
      },
      columnStyles: {
        0: { cellWidth: 32, fontStyle: 'bold' },
        1: { cellWidth: 20 },
        2: { cellWidth: 40 },
        3: { cellWidth: 18 },
        4: { cellWidth: 25 },
        5: { cellWidth: 25 },
        6: { cellWidth: 25 },
      },
      margin: { left: 14, right: 14 },
    });

    // Detailed Observations Pages
    for (let index = 0; index < observations.length; index++) {
      const o = observations[index];
      doc.addPage();
      let pageY = 15;

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(30, 41, 59);
      doc.text(`ANNEXURE ${index + 1}: OBSERVATION RECORD`, 14, pageY);

      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105);
      doc.text(`Ref: ${o.referenceNo}`, pageWidth - 14, pageY, { align: 'right' });

      pageY += 5;
      doc.setDrawColor(203, 213, 225);
      doc.line(14, pageY, pageWidth - 14, pageY);

      pageY += 4;

      autoTable(doc, {
        startY: pageY,
        theme: 'grid',
        body: [
          ['Area / Process', o.areaProcess],
          ['Severity Level', `${o.severity} ${o.financialImpact ? `(Financial Impact: ${formatINR(o.financialImpact)})` : ''}`],
          ['Observation Description', o.description],
          ['Root Cause Analysis', o.rootCause || 'N/A'],
          ['Audit Recommendation', o.recommendation || 'Compliance needed'],
          ['Discussion Stakeholders', `${o.discussionStakeholder || 'Management'} (Date: ${formatDate(o.dateOfDiscussion)})`],
          ['Management Response', o.managementResponse || 'Pending'],
          ['Lifecycle Status', `Current Status: ${o.status} | Rectification: ${o.rectificationStatus}`],
          ['Timeline', `Target: ${formatDate(o.targetRectificationDate)} | Actual: ${formatDate(o.actualRectificationDate)}`],
          ['Auditor Responsible', o.personResponsible],
          ['Supporting References', o.attachments || 'Audit Papers'],
          ['Internal Remarks', o.remarks || 'None'],
        ],
        styles: {
          fontSize: 8.5,
          cellPadding: 2.5,
          overflow: 'linebreak',
        },
        columnStyles: {
          0: { cellWidth: 45, fontStyle: 'bold', fillColor: [248, 250, 252] },
          1: { cellWidth: 'auto' },
        },
        margin: { left: 14, right: 14 },
      });
    }

    // Footers
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(7);
      doc.setTextColor(148, 163, 184);
      doc.text(
        `Audit Report - ${eng.clientName} (${eng.financialYear}) | ${f.firmName} | Page ${i} of ${pageCount}`,
        pageWidth / 2,
        290,
        { align: 'center' }
      );
    }

    doc.save(`Audit_Report_${eng.clientCode}_${eng.financialYear}.pdf`);
  }

  /**
   * Generates Combined Word Report (.docx) for an entire Engagement
   */
  static async exportEngagementReportDocx(
    eng: Engagement,
    observations: Observation[],
    auditType: AuditType | undefined,
    firm?: Partial<FirmProfile>
  ) {
    const f = ExportService.normalizeFirm(firm);
    const tableRows = observations.map((o, idx) => {
      return new TableRow({
        children: [
          new TableCell({ children: [new Paragraph({ text: String(idx + 1) })] }),
          new TableCell({ children: [new Paragraph({ text: o.referenceNo })] }),
          new TableCell({ children: [new Paragraph({ text: o.areaProcess })] }),
          new TableCell({ children: [new Paragraph({ text: o.severity })] }),
          new TableCell({ children: [new Paragraph({ text: formatINR(o.financialImpact) })] }),
          new TableCell({ children: [new Paragraph({ text: o.status })] }),
          new TableCell({ children: [new Paragraph({ text: o.rectificationStatus })] }),
        ],
      });
    });

    const doc = new Document({
      sections: [
        {
          properties: {},
          children: [
            new Paragraph({
              text: f.firmName.toUpperCase(),
              heading: HeadingLevel.HEADING_1,
              alignment: AlignmentType.CENTER,
            }),
            new Paragraph({
              text: `Chartered Accountants | FRN: ${f.frn}\n${f.address}, ${f.city}`,
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
            }),
            new Paragraph({
              text: `AUDIT OBSERVATION REPORT: ${eng.clientName.toUpperCase()}`,
              heading: HeadingLevel.HEADING_2,
              alignment: AlignmentType.CENTER,
              spacing: { after: 100 },
            }),
            new Paragraph({
              text: `Audit Type: ${auditType?.name || 'Audit'} | Financial Year: ${eng.financialYear} | Status: ${eng.overallStatus}`,
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
            }),

            // Summary Table
            new Table({
              width: { size: 100, type: WidthType.PERCENTAGE },
              rows: [
                new TableRow({
                  children: [
                    new TableCell({ children: [new Paragraph({ text: 'S.No', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Ref No', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Area / Process', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Severity', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Exposure (₹)', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Status', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                    new TableCell({ children: [new Paragraph({ text: 'Rectification', style: 'bold' })], shading: { fill: 'E2E8F0', type: ShadingType.CLEAR, color: 'auto' } }),
                  ],
                }),
                ...tableRows,
              ],
            }),

            // Detailed Findings
            new Paragraph({
              text: '\nDETAILED OBSERVATION PARTICULARS',
              heading: HeadingLevel.HEADING_2,
              spacing: { before: 300, after: 150 },
            }),
            ...observations.flatMap((o, i) => [
              new Paragraph({
                text: `${i + 1}. [${o.referenceNo}] ${o.areaProcess} (${o.severity} Risk - ${formatINR(o.financialImpact)})`,
                heading: HeadingLevel.HEADING_3,
                spacing: { before: 150, after: 50 },
              }),
              new Paragraph({
                children: [
                  new TextRun({ text: 'Description: ', bold: true }),
                  new TextRun({ text: o.description }),
                ],
              }),
              new Paragraph({
                children: [
                  new TextRun({ text: 'Audit Recommendation: ', bold: true }),
                  new TextRun({ text: o.recommendation }),
                ],
              }),
              new Paragraph({
                children: [
                  new TextRun({ text: 'Management Discussion & Response: ', bold: true }),
                  new TextRun({ text: `${o.managementResponse || 'Pending'} (Discussed with ${o.discussionStakeholder || 'Mgt'} on ${formatDate(o.dateOfDiscussion)})` }),
                ],
                spacing: { after: 150 },
              }),
            ]),
          ],
        },
      ],
    });

    const blob = await Packer.toBlob(doc);
    saveAs(blob, `Audit_Report_${eng.clientCode}_${eng.financialYear}.docx`);
  }

  /**
   * Generates Multi-Sheet Excel Workbook (.xlsx) with:
   * Tab 1: Executive Summary & Risk Analysis
   * Tab 2: Master Observation Register
   */
  static exportObservationsToExcel(
    observations: Observation[],
    engagements: Engagement[],
    auditTypes: AuditType[],
    sheetNamePrefix = 'Audit_Observations'
  ) {
    const wb = XLSX.utils.book_new();

    // Map lookups
    const engMap = new Map<string, Engagement>(engagements.map(e => [e.id, e]));
    const auditTypeMap = new Map<string, AuditType>(auditTypes.map(at => [at.id, at]));

    // Tab 1: Executive Summary Data
    const totalObs = observations.length;
    const criticalObs = observations.filter(o => o.severity === 'Critical').length;
    const highObs = observations.filter(o => o.severity === 'High').length;
    const mediumObs = observations.filter(o => o.severity === 'Medium').length;
    const lowObs = observations.filter(o => o.severity === 'Low').length;

    const openObs = observations.filter(o => o.status === 'Open').length;
    const underDiscObs = observations.filter(o => o.status === 'Under Discussion').length;
    const mgtAwaitedObs = observations.filter(o => o.status === 'Management Response Awaited').length;
    const rectifiedObs = observations.filter(o => o.status === 'Rectified').length;
    const closedObs = observations.filter(o => o.status === 'Closed').length;
    const notAcceptedObs = observations.filter(o => o.status === 'Not Accepted').length;

    const totalExposure = observations.reduce((acc, o) => acc + (o.financialImpact || 0), 0);

    const summaryData = [
      ['CA FIRM AUDIT OBSERVATION TRACKER - EXECUTIVE SUMMARY'],
      ['Generated On', new Date().toLocaleString('en-IN')],
      [],
      ['KPI / METRIC', 'COUNT / VALUE'],
      ['Total Observations Logged', totalObs],
      ['Total Financial Impact Exposure (INR)', totalExposure],
      [],
      ['SEVERITY BREAKDOWN', 'COUNT'],
      ['Critical', criticalObs],
      ['High', highObs],
      ['Medium', mediumObs],
      ['Low', lowObs],
      [],
      ['STATUS BREAKDOWN', 'COUNT'],
      ['Open', openObs],
      ['Under Discussion', underDiscObs],
      ['Management Response Awaited', mgtAwaitedObs],
      ['Rectified', rectifiedObs],
      ['Closed', closedObs],
      ['Not Accepted', notAcceptedObs],
    ];

    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Executive Summary');

    // Tab 2: Detailed Observations Register
    const detailedRows = observations.map((o, idx) => {
      const eng = engMap.get(o.engagementId);
      const at = eng ? auditTypeMap.get(eng.auditTypeId) : undefined;

      return {
        'S.No': idx + 1,
        'Reference No': o.referenceNo,
        'Client Name': eng?.clientName || 'N/A',
        'Audit Type': at?.name || 'N/A',
        'Financial Year': eng?.financialYear || 'N/A',
        'Date of Observation': formatDate(o.dateOfObservation),
        'Area / Process': o.areaProcess,
        'Observation Description': o.description,
        'Severity Level': o.severity,
        'Financial Impact (INR)': o.financialImpact || 0,
        'Root Cause': o.rootCause || '',
        'Audit Recommendation': o.recommendation || '',
        'Discussion Stakeholder': o.discussionStakeholder || '',
        'Date of Discussion': formatDate(o.dateOfDiscussion),
        'Management Response': o.managementResponse || '',
        'Overall Status': o.status,
        'Rectification Status': o.rectificationStatus,
        'Target Rectification Date': formatDate(o.targetRectificationDate),
        'Actual Rectification Date': formatDate(o.actualRectificationDate),
        'Person Responsible': o.personResponsible,
        'Attachments / Evidence': o.attachments || '',
        'Audit Remarks': o.remarks || '',
        'Branch / Location': eng?.branchLocation || '',
        'Engagement Partner': eng?.engagementPartner || '',
      };
    });

    const detailedSheet = XLSX.utils.json_to_sheet(detailedRows);
    XLSX.utils.book_append_sheet(wb, detailedSheet, 'Observation Register');

    // Export file
    const fileName = `${sheetNamePrefix}_${new Date().toISOString().split('T')[0]}.xlsx`;
    XLSX.writeFile(wb, fileName);
  }

  /**
   * Generates a Filtered Observation Register in PDF format
   */
  static exportFilteredObservationsPDF(
    observations: Observation[],
    engagements: Engagement[],
    auditTypes: AuditType[],
    firm?: Partial<FirmProfile>,
    filterDescription = 'All Filtered Observations'
  ) {
    const f = ExportService.normalizeFirm(firm);
    const doc = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4',
    });

    const engMap = new Map(engagements.map(e => [e.id, e]));
    const auditTypeMap = new Map(auditTypes.map(at => [at.id, at]));
    const pageWidth = doc.internal.pageSize.getWidth();

    let y = 14;

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(30, 41, 59);
    doc.text(f.firmName.toUpperCase(), pageWidth / 2, y, { align: 'center' });

    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text(`Chartered Accountants | FRN: ${f.frn} | Filtered Audit Observation Register`, pageWidth / 2, y, { align: 'center' });

    y += 3;
    doc.setDrawColor(203, 213, 225);
    doc.line(14, y, pageWidth - 14, y);

    y += 5;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(15, 23, 42);
    doc.text(`Scope: ${filterDescription} (Total: ${observations.length} Observations)`, 14, y);

    const totalExposure = observations.reduce((acc, o) => acc + (o.financialImpact || 0), 0);
    doc.text(`Total Exposure: ${formatINR(totalExposure)}`, pageWidth - 14, y, { align: 'right' });

    y += 4;

    autoTable(doc, {
      startY: y,
      theme: 'grid',
      head: [['Ref No', 'Client & FY', 'Audit Type', 'Area / Process', 'Description', 'Severity', 'Impact (₹)', 'Status', 'Rectification', 'Responsible']],
      body: observations.map(o => {
        const eng = engMap.get(o.engagementId);
        const at = eng ? auditTypeMap.get(eng.auditTypeId) : undefined;
        return [
          o.referenceNo,
          `${eng?.clientName || 'N/A'}\n(${eng?.financialYear || ''})`,
          at?.code || 'AUD',
          o.areaProcess,
          o.description.length > 90 ? `${o.description.slice(0, 90)}...` : o.description,
          o.severity,
          formatINRNumberOnly(o.financialImpact),
          o.status,
          o.rectificationStatus,
          o.personResponsible,
        ];
      }),
      headStyles: {
        fillColor: [30, 41, 59],
        fontSize: 7.5,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 7,
        cellPadding: 1.8,
      },
      columnStyles: {
        0: { cellWidth: 26, fontStyle: 'bold' },
        1: { cellWidth: 32 },
        2: { cellWidth: 15 },
        3: { cellWidth: 30 },
        4: { cellWidth: 65 },
        5: { cellWidth: 16 },
        6: { cellWidth: 22 },
        7: { cellWidth: 24 },
        8: { cellWidth: 22 },
        9: { cellWidth: 22 },
      },
      margin: { left: 14, right: 14 },
    });

    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(7);
      doc.setTextColor(148, 163, 184);
      doc.text(
        `CA Audit Register | ${f.firmName} | Page ${i} of ${pageCount}`,
        pageWidth / 2,
        200,
        { align: 'center' }
      );
    }

    doc.save(`Filtered_Audit_Observations_${new Date().toISOString().split('T')[0]}.pdf`);
  }
}
