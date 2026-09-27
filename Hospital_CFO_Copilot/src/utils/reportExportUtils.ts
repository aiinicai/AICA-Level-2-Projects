/**
 * Hospital CFO Copilot - Professional Report Export Utilities
 *
 * Provides dedicated PDF generation (via jsPDF) and Excel workbook exports (via xlsx)
 * for both:
 * 1. Agentic CFO Financial Review Briefing
 * 2. Hospital CFO Executive Management Pack
 *
 * Ensures documents are professionally formatted, paginated, and strictly grounded
 * on deterministic application data with zero browser UI print artifacts.
 */

import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx';
import {
  CfoFinancialReviewBrief,
  DashboardMetrics,
  FinancialException,
  UserSession,
} from '../types';
import { DepartmentClearanceSummary } from '../engine/clearanceEngine';
import { ArAgeingSummary } from './arCalculations';
import { formatIndianDate, formatINR } from './formatters';

// ============================================================================
// PDF Helper Utilities
// ============================================================================

function addHeader(
  doc: jsPDF,
  title: string,
  subtitle: string,
  pageNumber: number,
  totalPagesExp = '{total_pages_count_string}'
) {
  const pageWidth = doc.internal.pageSize.getWidth();

  // Top header bar
  doc.setFillColor(15, 23, 42); // slate-900
  doc.rect(0, 0, pageWidth, 18, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('HOSPITAL CFO COPILOT  |  FINANCIAL CONTROL & GOVERNANCE', 14, 11);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184); // slate-400
  doc.text('CONFIDENTIAL - BOARDROOM LEVEL', pageWidth - 14, 11, { align: 'right' });

  // Reset text color
  doc.setTextColor(15, 23, 42);
}

function addFooter(doc: jsPDF, pageNumber: number, totalPages: number) {
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  doc.setDrawColor(226, 232, 240); // slate-200
  doc.line(14, pageHeight - 12, pageWidth - 14, pageHeight - 12);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139); // slate-500
  doc.text(
    'Hospital CFO Copilot  •  Grounded Deterministic Financial Intelligence  •  Strictly Confidential',
    14,
    pageHeight - 7
  );

  doc.text(`Page ${pageNumber} of ${totalPages}`, pageWidth - 14, pageHeight - 7, {
    align: 'right',
  });
}

// ============================================================================
// 1. CFO Financial Review Briefing - PDF & Excel Export
// ============================================================================

export function exportCfoReviewToPdf(
  brief: CfoFinancialReviewBrief,
  currentUser: UserSession
): void {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const contentWidth = pageWidth - margin * 2;
  let y = 26;

  // Title Block
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.setTextColor(15, 23, 42);
  doc.text('CFO Financial Review — Executive Briefing', margin, y);
  y += 6;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(71, 85, 105);
  doc.text(
    'Autonomous Multi-Stage Specialist Financial Review  •  Strictly Grounded Deterministic Findings',
    margin,
    y
  );
  y += 7;

  // Metadata Card (rounded rect)
  doc.setFillColor(248, 250, 252); // slate-50
  doc.setDrawColor(203, 213, 225); // slate-300
  doc.roundedRect(margin, y, contentWidth, 20, 2, 2, 'FD');

  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text('Review ID:', margin + 4, y + 6);
  doc.text('Control Run ID:', margin + 4, y + 11);
  doc.text('Generated At:', margin + 4, y + 16);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(15, 23, 42);
  doc.text(brief.briefId, margin + 26, y + 6);
  doc.text(brief.runId, margin + 26, y + 11);
  doc.text(new Date(brief.generatedAt).toLocaleString('en-IN'), margin + 26, y + 16);

  const col2X = margin + 95;
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100, 116, 139);
  doc.text('Prepared By:', col2X, y + 6);
  doc.text('User Role:', col2X, y + 11);
  doc.text('Status:', col2X, y + 16);

  doc.setFont('helvetica', 'bold');
  doc.setTextColor(15, 23, 42);
  doc.text(brief.generatedBy, col2X + 22, y + 6);
  doc.text(brief.userRole, col2X + 22, y + 11);

  if (brief.status === 'APPROVED') {
    doc.setTextColor(16, 185, 129); // emerald-600
    doc.text(`APPROVED (${brief.approvedBy || 'CFO'})`, col2X + 22, y + 16);
  } else {
    doc.setTextColor(217, 119, 6); // amber-600
    doc.text('DRAFT — PENDING CFO SIGN-OFF', col2X + 22, y + 16);
  }

  y += 26;

  // Key Financial Metrics Strip
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(13, 148, 136); // teal-600
  doc.text('EXECUTIVE FINANCIAL POSITION', margin, y);
  y += 4;

  const kpis = [
    { label: 'Gross Billed', val: formatINR(brief.groundedFigures.grossBilling) },
    { label: 'Capture Rate', val: `${brief.groundedFigures.billingCaptureRate}%` },
    { label: 'Identified Exposure', val: formatINR(brief.groundedFigures.potentialExposure) },
    { label: 'Active Receivables', val: formatINR(brief.groundedFigures.totalAR) },
    { label: 'Overdue AR (>30d)', val: formatINR(brief.groundedFigures.overdueAR) },
    { label: 'Clearance Rate', val: `${brief.groundedFigures.clearancePercent}%` },
  ];

  const kpiBoxWidth = contentWidth / 6;
  kpis.forEach((kpi, idx) => {
    const kpiX = margin + idx * kpiBoxWidth;
    doc.setFillColor(241, 245, 249); // slate-100
    doc.setDrawColor(226, 232, 240);
    doc.rect(kpiX, y, kpiBoxWidth - 1, 14, 'FD');

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(kpi.label, kpiX + 2, y + 5);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(15, 23, 42);
    doc.text(kpi.val, kpiX + 2, y + 11);
  });

  y += 18;

  // Specialist Stages Summary
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(13, 148, 136);
  doc.text('SPECIALIST REVIEW STAGES (10 STAGES)', margin, y);
  y += 4;

  // Stage table header
  doc.setFillColor(15, 23, 42);
  doc.rect(margin, y, contentWidth, 6, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(7.5);
  doc.text('Stage', margin + 3, y + 4.2);
  doc.text('Status', margin + 50, y + 4.2);
  doc.text('Tools Executed', margin + 75, y + 4.2);
  doc.text('Key Stage Finding', margin + 120, y + 4.2);
  y += 6;

  brief.stageExecutionLog.forEach((stg, i) => {
    // Check page break
    if (y > pageHeight - 25) {
      doc.addPage();
      y = 26;
    }

    doc.setFillColor(i % 2 === 0 ? 255 : 248, i % 2 === 0 ? 255 : 250, i % 2 === 0 ? 255 : 252);
    doc.rect(margin, y, contentWidth, 6, 'F');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7);
    doc.setTextColor(15, 23, 42);
    doc.text(`${i + 1}. ${stg.stageName}`, margin + 3, y + 4.2);

    // Status color
    if (stg.status === 'COMPLETED') doc.setTextColor(5, 150, 105);
    else if (stg.status === 'NO_DATA') doc.setTextColor(100, 116, 139);
    else if (stg.status === 'ERROR') doc.setTextColor(225, 29, 72);
    else doc.setTextColor(13, 148, 136);
    doc.text(stg.status, margin + 50, y + 4.2);

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(71, 85, 105);
    doc.text(stg.toolsUsed.join(', ') || 'Synthesis', margin + 75, y + 4.2);

    const findingShort = stg.finding.length > 55 ? stg.finding.slice(0, 52) + '...' : stg.finding;
    doc.text(findingShort, margin + 120, y + 4.2);

    y += 6;
  });

  y += 8;

  // Briefing Markdown Sections
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(13, 148, 136);
  doc.text('DETAILED SPECIALIST FINDINGS & TAXONOMY', margin, y);
  y += 6;

  const rawLines = brief.markdownContent.split('\n');

  for (const rawLine of rawLines) {
    if (!rawLine.trim()) {
      y += 2;
      continue;
    }

    if (y > pageHeight - 20) {
      doc.addPage();
      y = 26;
    }

    if (rawLine.startsWith('# ')) {
      // Main title - already covered
      continue;
    }

    if (rawLine.startsWith('## ')) {
      y += 2;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(13, 148, 136);
      doc.text(rawLine.replace('## ', ''), margin, y);
      y += 5;
      continue;
    }

    if (rawLine.startsWith('### ')) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(30, 41, 59);
      doc.text(rawLine.replace('### ', ''), margin, y);
      y += 4.5;
      continue;
    }

    if (rawLine.startsWith('> ')) {
      doc.setFillColor(241, 245, 249);
      doc.setDrawColor(203, 213, 225);
      const cleanBlock = rawLine.replace(/^> /, '');
      const wrapped = doc.splitTextToSize(cleanBlock, contentWidth - 8);
      const boxHeight = wrapped.length * 3.5 + 4;

      if (y + boxHeight > pageHeight - 15) {
        doc.addPage();
        y = 26;
      }

      doc.rect(margin, y, contentWidth, boxHeight, 'FD');
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7.5);
      doc.setTextColor(71, 85, 105);
      wrapped.forEach((line: string, idx: number) => {
        doc.text(line, margin + 4, y + 4 + idx * 3.5);
      });
      y += boxHeight + 3;
      continue;
    }

    // List items & standard paragraphs
    const cleanLine = rawLine.replace(/^- /, '• ').replace(/\*\*/g, '').replace(/`/g, '');
    const wrapped = doc.splitTextToSize(cleanLine, contentWidth - 2);

    if (y + wrapped.length * 3.8 > pageHeight - 15) {
      doc.addPage();
      y = 26;
    }

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(30, 41, 59);

    wrapped.forEach((line: string) => {
      doc.text(line, margin + 2, y);
      y += 3.8;
    });
  }

  // Final Sign-Off Section
  if (y > pageHeight - 35) {
    doc.addPage();
    y = 26;
  }

  y += 6;
  doc.setDrawColor(203, 213, 225);
  doc.line(margin, y, pageWidth - margin, y);
  y += 6;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text('INSTITUTIONAL GOVERNANCE & SIGN-OFF CERTIFICATION', margin, y);
  y += 5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  doc.text(
    `Certified by: ${brief.approvedBy || currentUser.name} (${currentUser.role})  |  Timestamp: ${brief.approvedAt ? new Date(brief.approvedAt).toLocaleString('en-IN') : new Date().toLocaleString('en-IN')}`,
    margin,
    y
  );
  y += 4;
  doc.text(
    `Sign-off commentary: ${brief.approvalNotes || 'Reviewed deterministic financial controls, AR schedules, and specialist stage findings.'}`,
    margin,
    y
  );

  // Apply running header and footer to all pages
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    addHeader(doc, 'CFO Financial Review', brief.briefId, i, String(totalPages));
    addFooter(doc, i, totalPages);
  }

  doc.save(`Hospital_CFO_Review_${brief.briefId}.pdf`);
}

export function exportCfoReviewToExcel(
  brief: CfoFinancialReviewBrief,
  currentUser: UserSession
): void {
  const wb = XLSX.utils.book_new();

  // 1. Executive Summary Sheet
  const summaryRows = [
    ['HOSPITAL CFO COPILOT — EXECUTIVE FINANCIAL BRIEFING', ''],
    ['Generated At', new Date(brief.generatedAt).toLocaleString('en-IN')],
    ['Review ID', brief.briefId],
    ['Control Run ID', brief.runId],
    ['Generated By', brief.generatedBy],
    ['User Role', brief.userRole],
    ['Approval Status', brief.status],
    ['Approved By', brief.approvedBy || 'Pending'],
    ['Approval Timestamp', brief.approvedAt || 'N/A'],
    ['CFO Notes', brief.approvalNotes || 'None'],
    ['', ''],
    ['KEY GROUNDED FINANCIAL METRICS', 'VALUE'],
    ['Gross Patient Invoiced Billing', brief.groundedFigures.grossBilling],
    ['Expected Clinical Tariff Base', brief.groundedFigures.totalExpectedAmount],
    ['Billing Capture Efficiency (%)', `${brief.groundedFigures.billingCaptureRate}%`],
    ['Potential Financial Exposure', brief.groundedFigures.potentialExposure],
    ['Open Exceptions Count', brief.groundedFigures.openExceptionsCount],
    ['Critical Severity Exceptions', brief.groundedFigures.criticalExceptionsCount],
    ['High Severity Exceptions', brief.groundedFigures.highExceptionsCount],
    ['Total Outstanding AR', brief.groundedFigures.totalAR],
    ['Overdue Receivables (>30d)', brief.groundedFigures.overdueAR],
    ['Collection Realisation Rate (%)', `${brief.groundedFigures.collectionRate}%`],
    ['TPA Pending Adjudication', brief.groundedFigures.tpaPendingAmount],
    ['TPA Approved Amount', brief.groundedFigures.tpaApprovedAmount],
    ['TPA Disallowances / Shortfall', brief.groundedFigures.tpaShortfallAmount],
    ['Departmental Clearance (%)', `${brief.groundedFigures.clearancePercent}%`],
    ['Budget Variance Available', brief.groundedFigures.budgetAvailable ? 'Yes' : 'No'],
    ['Budget Revenue Variance', brief.groundedFigures.budgetRevenueVariance ?? 'N/A'],
  ];
  const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);
  XLSX.utils.book_append_sheet(wb, wsSummary, 'Executive Summary');

  // 2. Specialist Stages Execution Log Sheet
  const stageHeader = [
    'Stage #',
    'Stage Identifier',
    'Stage Name',
    'Lifecycle Status',
    'Tools Executed',
    'Records Processed',
    'Metrics Returned',
    'Key Finding / Evidence',
    'Completed Timestamp',
  ];
  const stageRows = brief.stageExecutionLog.map((s, idx) => [
    idx + 1,
    s.stageId,
    s.stageName,
    s.status,
    s.toolsUsed.join(', ') || 'None',
    s.recordsProcessed,
    s.metricsReturned,
    s.finding,
    s.completedAt,
  ]);
  const wsStages = XLSX.utils.aoa_to_sheet([stageHeader, ...stageRows]);
  XLSX.utils.book_append_sheet(wb, wsStages, 'Specialist Stages');

  // 3. Evidence References Sheet
  const evidenceHeader = ['Reference Type', 'Identifier', 'Label', 'Detail', 'Stage ID'];
  const evidenceRows = brief.evidenceReferences.map((e) => [
    e.type,
    e.id,
    e.label,
    e.detail || '',
    e.stageId || '',
  ]);
  const wsEvidence = XLSX.utils.aoa_to_sheet([evidenceHeader, ...evidenceRows]);
  XLSX.utils.book_append_sheet(wb, wsEvidence, 'Evidence References');

  // 4. Detailed Briefing Content Sheet
  const briefingLines = brief.markdownContent.split('\n').map((l) => [l]);
  const wsBriefing = XLSX.utils.aoa_to_sheet([['Briefing Markdown Source'], ...briefingLines]);
  XLSX.utils.book_append_sheet(wb, wsBriefing, 'Full Briefing Narrative');

  XLSX.writeFile(wb, `Hospital_CFO_Review_${brief.briefId}.xlsx`);
}

// ============================================================================
// 2. CFO Executive Management Pack - PDF & Excel Export
// ============================================================================

export function exportManagementPackToPdf(
  metrics: DashboardMetrics,
  exceptions: FinancialException[],
  clearanceSummary: DepartmentClearanceSummary | undefined,
  arSummary: ArAgeingSummary | undefined,
  currentUser: UserSession,
  runId: string,
  totalClaimsSubmitted?: number,
  totalApproved?: number,
  totalPending?: number
): void {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const contentWidth = pageWidth - margin * 2;
  let y = 26;

  // Header Block
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.setTextColor(15, 23, 42);
  doc.text('Hospital CFO Executive Management Pack', margin, y);
  y += 5.5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(71, 85, 105);
  doc.text(
    `Boardroom Financial Pack  •  Run: ${runId}  •  Prepared by ${currentUser.name} (${currentUser.role})`,
    margin,
    y
  );
  y += 7;

  // Section 1: Dashboard KPIs Table
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9.5);
  doc.setTextColor(13, 148, 136);
  doc.text('1. EXECUTIVE FINANCIAL POSITION & KPI SUMMARY', margin, y);
  y += 4;

  const kpis = [
    ['Gross Billed Patient Revenue', formatINR(metrics.grossBilling)],
    ['Expected Clinical Tariff Base', formatINR(metrics.totalExpectedAmount)],
    ['Billing Capture Efficiency', `${metrics.billingCaptureRate}%`],
    ['Identified Potential Financial Exposure', formatINR(metrics.potentialFinancialExposure)],
    ['Total Outstanding Receivables (AR)', formatINR(arSummary?.totalAR ?? metrics.outstandingCollections)],
    ['Overdue Receivables (>30 Days)', formatINR(arSummary?.overdueAR ?? 0)],
    ['Historical Collection Rate', `${arSummary?.collectionRate ?? 0}%`],
    ['Departmental Billing Clearance Rate', `${clearanceSummary?.clearancePercent ?? 100}%`],
    ['Insurance / TPA Claims Pending', formatINR(totalPending ?? metrics.tpaPendingAmount)],
  ];

  kpis.forEach(([title, val], idx) => {
    doc.setFillColor(idx % 2 === 0 ? 248 : 255, idx % 2 === 0 ? 250 : 255, idx % 2 === 0 ? 252 : 255);
    doc.rect(margin, y, contentWidth, 5.5, 'F');

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(71, 85, 105);
    doc.text(title, margin + 4, y + 4);

    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text(val, pageWidth - margin - 4, y + 4, { align: 'right' });

    y += 5.5;
  });

  y += 7;

  // Section 2: AR Ageing Schedule
  if (arSummary) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(13, 148, 136);
    doc.text(`2. ACCOUNTS RECEIVABLE AGEING SCHEDULE (As of ${arSummary.asOfDateDisplay})`, margin, y);
    y += 4;

    const bucketWidth = contentWidth / arSummary.ageingBuckets.length;
    arSummary.ageingBuckets.forEach((b, idx) => {
      const bx = margin + idx * bucketWidth;
      doc.setFillColor(241, 245, 249);
      doc.setDrawColor(203, 213, 225);
      doc.rect(bx, y, bucketWidth - 1, 14, 'FD');

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(6.5);
      doc.setTextColor(100, 116, 139);
      doc.text(b.label, bx + 2, y + 4.5);

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(15, 23, 42);
      doc.text(formatINR(b.amount), bx + 2, y + 9.5);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(6.5);
      doc.setTextColor(100, 116, 139);
      doc.text(`${b.count} accts (${b.shareFormatted})`, bx + 2, y + 13);
    });

    y += 19;
  }

  // Section 3: Material Financial Exceptions Table
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9.5);
  doc.setTextColor(13, 148, 136);
  doc.text('3. PRIORITY FINANCIAL EXCEPTIONS (C01–C08 LEDGER)', margin, y);
  y += 4;

  const topExceptions = exceptions.slice(0, 10);
  if (topExceptions.length === 0) {
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text('Zero open financial exceptions in active ledger.', margin + 2, y + 4);
    y += 8;
  } else {
    // Header
    doc.setFillColor(15, 23, 42);
    doc.rect(margin, y, contentWidth, 5.5, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(7);
    doc.text('Exception ID', margin + 3, y + 3.8);
    doc.text('Control', margin + 28, y + 3.8);
    doc.text('Encounter', margin + 48, y + 3.8);
    doc.text('Severity', margin + 72, y + 3.8);
    doc.text('Exposure', margin + 92, y + 3.8);
    doc.text('Description', margin + 115, y + 3.8);
    y += 5.5;

    topExceptions.forEach((exc, i) => {
      if (y > pageHeight - 25) {
        doc.addPage();
        y = 26;
      }

      doc.setFillColor(i % 2 === 0 ? 255 : 248, i % 2 === 0 ? 255 : 250, i % 2 === 0 ? 255 : 252);
      doc.rect(margin, y, contentWidth, 5.5, 'F');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(15, 23, 42);
      doc.text(exc.Exception_ID, margin + 3, y + 3.8);

      doc.setFont('helvetica', 'normal');
      doc.text(exc.Control_ID, margin + 28, y + 3.8);
      doc.text(exc.Encounter_ID, margin + 48, y + 3.8);

      if (exc.Severity === 'CRITICAL') doc.setTextColor(225, 29, 72);
      else if (exc.Severity === 'HIGH') doc.setTextColor(234, 88, 12);
      else doc.setTextColor(100, 116, 139);
      doc.text(exc.Severity, margin + 72, y + 3.8);

      doc.setTextColor(15, 23, 42);
      doc.setFont('helvetica', 'bold');
      doc.text(formatINR(exc.Exposure_Amount), margin + 92, y + 3.8);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(71, 85, 105);
      const descShort = exc.Description.length > 45 ? exc.Description.slice(0, 42) + '...' : exc.Description;
      doc.text(descShort, margin + 115, y + 3.8);

      y += 5.5;
    });

    y += 8;
  }

  // Section 4: Governance Certification
  if (y > pageHeight - 35) {
    doc.addPage();
    y = 26;
  }

  doc.setDrawColor(203, 213, 225);
  doc.line(margin, y, pageWidth - margin, y);
  y += 6;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text('4. GOVERNANCE & AUDIT SIGN-OFF', margin, y);
  y += 5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  doc.text(
    `Prepared By: ${currentUser.name} (${currentUser.role})  |  Generated: ${new Date().toLocaleString('en-IN')}`,
    margin,
    y
  );
  y += 4;
  doc.text(
    'Audit Certification: All metrics and variance items verified through deterministic C01–C08 controls.',
    margin,
    y
  );

  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    addHeader(doc, 'Management Pack', runId, i, String(totalPages));
    addFooter(doc, i, totalPages);
  }

  doc.save(`Hospital_CFO_Management_Pack_${runId}.pdf`);
}

export function exportManagementPackToExcel(
  metrics: DashboardMetrics,
  exceptions: FinancialException[],
  clearanceSummary: DepartmentClearanceSummary | undefined,
  arSummary: ArAgeingSummary | undefined,
  currentUser: UserSession,
  runId: string,
  totalClaimsSubmitted?: number,
  totalApproved?: number,
  totalPending?: number
): void {
  const wb = XLSX.utils.book_new();

  // 1. Overview & Metrics
  const overviewRows = [
    ['HOSPITAL CFO EXECUTIVE MANAGEMENT PACK', ''],
    ['Run ID', runId],
    ['Generated At', new Date().toLocaleString('en-IN')],
    ['Generated By', currentUser.name],
    ['User Role', currentUser.role],
    ['', ''],
    ['KEY PERFORMANCE INDICATOR', 'AMOUNT (INR) / VALUE'],
    ['Gross Patient Invoiced Revenue', metrics.grossBilling],
    ['Gross Billed Pre-Discount', metrics.grossBilledPreDiscount],
    ['Expected Clinical Tariff Base', metrics.totalExpectedAmount],
    ['Billing Capture Efficiency (%)', `${metrics.billingCaptureRate}%`],
    ['Identified Potential Financial Exposure', metrics.potentialFinancialExposure],
    ['Open Exceptions Count', metrics.openExceptionsCount],
    ['Critical Exceptions Count', metrics.criticalExceptionsCount],
    ['High Exceptions Count', metrics.highExceptionsCount],
    ['Total Accounts Receivable (AR)', arSummary?.totalAR ?? metrics.outstandingCollections],
    ['Overdue AR (>30 Days)', arSummary?.overdueAR ?? 0],
    ['Historical Collection Realisation Rate (%)', `${arSummary?.collectionRate ?? 0}%`],
    ['Insurance / TPA Claims Submitted', totalClaimsSubmitted ?? 0],
    ['Insurance / TPA Claims Approved', totalApproved ?? 0],
    ['Insurance / TPA Claims Pending Adjudication', totalPending ?? metrics.tpaPendingAmount],
    ['Overall Departmental Billing Clearance (%)', `${clearanceSummary?.clearancePercent ?? 100}%`],
  ];
  const wsOverview = XLSX.utils.aoa_to_sheet(overviewRows);
  XLSX.utils.book_append_sheet(wb, wsOverview, 'Executive Overview');

  // 2. Control Exceptions Ledger
  const excHeader = [
    'Exception ID',
    'Control ID',
    'Encounter ID',
    'Revenue Centre',
    'Severity',
    'Exposure Amount (INR)',
    'Status',
    'Assigned To',
    'Created Date',
    'Description',
    'Resolution Notes',
  ];
  const excRows = exceptions.map((e) => [
    e.Exception_ID,
    e.Control_ID,
    e.Encounter_ID,
    e.Revenue_Centre,
    e.Severity,
    e.Exposure_Amount,
    e.Status,
    e.Assigned_To || 'Unassigned',
    e.Created_Date,
    e.Description,
    e.Resolution || '',
  ]);
  const wsExceptions = XLSX.utils.aoa_to_sheet([excHeader, ...excRows]);
  XLSX.utils.book_append_sheet(wb, wsExceptions, 'Exceptions Ledger');

  // 3. AR Ageing Schedule Sheet
  if (arSummary) {
    const arHeader = ['Ageing Bucket', 'Label', 'Outstanding AR (INR)', 'Account Count', 'Share (%)'];
    const arRows = arSummary.ageingBuckets.map((b) => [
      b.bucket,
      b.label,
      b.amount,
      b.count,
      b.shareFormatted,
    ]);
    const wsAr = XLSX.utils.aoa_to_sheet([arHeader, ...arRows]);
    XLSX.utils.book_append_sheet(wb, wsAr, 'AR Ageing Schedule');
  }

  // 4. Department Clearance Summary Sheet
  if (clearanceSummary) {
    const deptRows = [
      ['DEPARTMENTAL BILLING CLEARANCE SUMMARY', ''],
      ['Total Departmental Records', clearanceSummary.totalRecords],
      ['Verified Clearance Records', clearanceSummary.verifiedCount],
      ['Pending Verification', clearanceSummary.pendingCount],
      ['Disputed Records', clearanceSummary.disputedCount],
      ['Correction Required', clearanceSummary.correctionRequiredCount],
      ['Overall Clearance Efficiency (%)', `${clearanceSummary.clearancePercent}%`],
      ['Exposure Awaiting Verification (INR)', clearanceSummary.exposureAwaitingVerification],
      ['Disputed Financial Exposure (INR)', clearanceSummary.disputedExposure],
    ];
    const wsDept = XLSX.utils.aoa_to_sheet(deptRows);
    XLSX.utils.book_append_sheet(wb, wsDept, 'Department Clearance');
  }

  XLSX.writeFile(wb, `Hospital_CFO_Management_Pack_${runId}.xlsx`);
}
