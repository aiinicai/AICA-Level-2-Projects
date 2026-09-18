import * as XLSX from 'xlsx';
import { EngagementData, ComputedMateriality } from '../types';
import { formatINR, formatCompactINR } from './calculations';

// ==========================================
// 1. EXCEL (.XLSX) MULTI-SHEET EXPORTER
// ==========================================

export function exportWorkpaperToExcel(
  engagement: EngagementData,
  materiality: ComputedMateriality
): void {
  const wb = XLSX.utils.book_new();

  // Helper to set column widths
  const applyCols = (ws: XLSX.WorkSheet, colWidths: number[]) => {
    ws['!cols'] = colWidths.map((w) => ({ wch: w }));
  };

  // --- TAB 1: ENGAGEMENT SUMMARY ---
  const summaryRows = [
    ['STATUTORY AUDIT PLANNING WORKPAPER - ENGAGEMENT OVERVIEW'],
    ['Conducted in accordance with Standards on Auditing (SAs) issued by ICAI'],
    [''],
    ['Client Name', engagement.clientName],
    ['Corporate Identification Number (CIN)', engagement.cin],
    ['Permanent Account Number (PAN)', engagement.pan],
    ['Financial Year', engagement.financialYear],
    ['Audit Period', engagement.auditPeriod],
    ['Registered Office Address', engagement.registeredAddress],
    ['Audit Engagement Type', engagement.auditType],
    ['Engagement Partner', engagement.engagementPartner],
    ['Audit Senior / Team Lead', engagement.auditSenior],
    ['Preceding Statutory Auditor', engagement.precedingAuditor],
    ['Date of Acceptance', engagement.dateOfAcceptance],
    ['Acceptance Conclusion', engagement.acceptanceConclusion],
    ['Acceptance Notes', engagement.acceptanceNotes],
    [''],
    ['SIGN-OFF & QUALITY CONTROL STATUS (SQC 1)'],
    ['Preparer Declaration', engagement.signOffReview.preparer.declared ? 'Signed / Completed' : 'Draft / Pending'],
    ['Preparer Name & Date', `${engagement.signOffReview.preparer.name} (${engagement.signOffReview.preparer.date || 'N/A'})`],
    ['Reviewer Conclusion', engagement.signOffReview.reviewer.conclusion],
    ['Reviewer Name & Date', `${engagement.signOffReview.reviewer.name} (${engagement.signOffReview.reviewer.date || 'N/A'})`],
    ['Reviewer Comments', engagement.signOffReview.reviewer.concludingRemarks || engagement.signOffReview.reviewer.comments || ''],
  ];
  const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);
  applyCols(wsSummary, [32, 60]);
  XLSX.utils.book_append_sheet(wb, wsSummary, 'Engagement_Overview');

  // --- TAB 2: SA 320 MATERIALITY ---
  const matRows = [
    ['MATERIALITY DETERMINATION SCHEDULE (SA 320 / SA 450)'],
    [''],
    ['Parameter / Threshold', 'Configured Value', 'Computed INR Amount', 'ICAI Guidance / Formula'],
    ['Benchmark Basis', engagement.materiality.benchmarkBasis, '', 'Selected per SA 320 para 10 & A3'],
    ['Benchmark Reference Amount', engagement.materiality.benchmarkAmount, formatINR(engagement.materiality.benchmarkAmount), 'Financial statements baseline (TB)'],
    ['Overall Materiality (OM) %', `${engagement.materiality.omPercent}%`, '', 'Industry benchmark percentage'],
    ['Overall Materiality (OM) Amount', '', formatINR(materiality.overallMateriality), 'Materiality for FS as a whole (SA 320)'],
    ['Performance Materiality (PM) %', `${engagement.materiality.pmPercent}%`, '', 'Typically 50% - 75% of OM'],
    ['Performance Materiality (PM) Amount', '', formatINR(materiality.performanceMateriality), 'Materiality for scoping & testing (SA 320.11)'],
    ['Clearly Trivial (CT) %', `${engagement.materiality.ctPercent}%`, '', 'Typically 3% - 5% of OM'],
    ['Clearly Trivial Threshold Amount', '', formatINR(materiality.clearlyTrivialThreshold), 'Under SA 450; trivial misstatements accumulated'],
    [''],
    ['RATIONALE & PROFESSIONAL JUDGMENT:'],
    [engagement.materiality.rationale],
  ];
  const wsMat = XLSX.utils.aoa_to_sheet(matRows);
  applyCols(wsMat, [32, 22, 28, 45]);
  XLSX.utils.book_append_sheet(wb, wsMat, 'Materiality_SA320');

  // --- TAB 3: TRIAL BALANCE (IF AVAILABLE) ---
  if (engagement.trialBalance && engagement.trialBalance.items.length > 0) {
    const tb = engagement.trialBalance;
    const tbRows: any[][] = [
      ['CLIENT TRIAL BALANCE & FINANCIAL AGGREGATES'],
      [`Source File: ${tb.fileName || 'Imported'} | Imported: ${tb.importedAt || 'N/A'}`],
      [`Status: ${tb.summary.isBalanced ? 'BALANCED (Dr = Cr)' : 'OUT OF BALANCE'} | Total Items: ${tb.summary.itemCount}`],
      [''],
      ['Key Financial Indicators', 'Amount (INR)', 'Compact Notation'],
      ['Turnover / Revenue from Operations', tb.summary.totalRevenue, formatCompactINR(tb.summary.totalRevenue)],
      ['Total Expenses', tb.summary.totalExpenses, formatCompactINR(tb.summary.totalExpenses)],
      ['Profit Before Tax (PBT)', tb.summary.profitBeforeTax, formatCompactINR(tb.summary.profitBeforeTax)],
      ['Total Assets', tb.summary.totalAssets, formatCompactINR(tb.summary.totalAssets)],
      ['Total Liabilities', tb.summary.totalLiabilities, formatCompactINR(tb.summary.totalLiabilities)],
      ['Total Equity / Net Worth', tb.summary.totalEquity, formatCompactINR(tb.summary.totalEquity)],
      ['Total Borrowings', tb.summary.totalBorrowings, formatCompactINR(tb.summary.totalBorrowings)],
      ['Total Debits', tb.summary.totalDebit, formatINR(tb.summary.totalDebit)],
      ['Total Credits', tb.summary.totalCredit, formatINR(tb.summary.totalCredit)],
      ['Difference (Dr - Cr)', tb.summary.difference, formatINR(tb.summary.difference)],
      [''],
      [
        'Account Code',
        'Account / Ledger Name',
        'Schedule III Group',
        'Category',
        'Debit (INR)',
        'Credit (INR)',
        'Net Closing Balance (INR)',
        'Prior Year (INR)',
        'Variance %',
        'Materiality Flag',
        'Notes',
      ],
    ];

    tb.items.forEach((item) => {
      tbRows.push([
        item.accountCode,
        item.accountName,
        item.scheduleIIIGroup,
        item.category,
        item.currentYearDebit,
        item.currentYearCredit,
        item.currentYearNet,
        item.priorYearBalance ?? '',
        item.variancePercent !== undefined ? `${item.variancePercent}%` : '',
        item.materialityFlag || 'Normal',
        item.notes || '',
      ]);
    });

    const wsTB = XLSX.utils.aoa_to_sheet(tbRows);
    applyCols(wsTB, [14, 38, 32, 14, 16, 16, 20, 18, 14, 18, 30]);
    XLSX.utils.book_append_sheet(wb, wsTB, 'Trial_Balance');
  }

  // --- TAB 4: SA 315 FS RISK ASSESSMENT ---
  const fsRiskHeaders = [
    'Line Item Name',
    'Schedule III Category',
    'Inherent Risk Level',
    'Quantitative Significance',
    'Applicable Assertions',
    'Audit Rationale & Risk Assessment',
  ];
  const fsRiskRows: any[][] = [
    ['FINANCIAL STATEMENT LEVEL & ASSERTION RISK ASSESSMENT (SA 315 REVISED)'],
    [''],
    fsRiskHeaders,
  ];
  engagement.fsLineItemRisks.forEach((r) => {
    fsRiskRows.push([
      r.lineItemName,
      r.scheduleIIICategory,
      r.inherentRisk,
      r.quantitativeSignificance || '',
      r.assertions.join(', '),
      r.rationale,
    ]);
  });
  const wsFSRisk = XLSX.utils.aoa_to_sheet(fsRiskRows);
  applyCols(wsFSRisk, [30, 24, 18, 24, 36, 60]);
  XLSX.utils.book_append_sheet(wb, wsFSRisk, 'FS_Risk_SA315');

  // --- TAB 5: SA 240 FRAUD RISKS ---
  const revPresumption = typeof engagement.fraudRisks.revenuePresumption === 'object'
    ? engagement.fraudRisks.revenuePresumption
    : { rebutted: false, rationale: engagement.fraudRisks.revenueRationale || '', plannedResponse: '' };

  const mgmtOverride = typeof engagement.fraudRisks.managementOverride === 'object'
    ? engagement.fraudRisks.managementOverride
    : { rationale: 'Non-rebuttable fraud risk under SA 240 para 31', plannedResponse: engagement.fraudRisks.managementOverrideProcedures || '' };

  const fraudRows: any[][] = [
    ['FRAUD RISK ASSESSMENT REGISTER & PROCEDURES (SA 240)'],
    [''],
    ['MANDATORY PRESUMPTION 1: REVENUE RECOGNITION (SA 240 Para 26)'],
    ['Presumption Rebutted?', revPresumption.rebutted ? 'YES (Rebutted)' : 'NO (Presumption Maintained - Significant Fraud Risk)'],
    ['Documentation Rationale', revPresumption.rationale],
    ['Planned Audit Responses', revPresumption.plannedResponse],
    [''],
    ['MANDATORY PRESUMPTION 2: MANAGEMENT OVERRIDE OF CONTROLS (SA 240 Para 31)'],
    ['Status', 'Non-Rebuttable Inherent Fraud Risk'],
    ['Assessment Rationale', mgmtOverride.rationale],
    ['Planned Response & Journal Entry Testing', mgmtOverride.plannedResponse],
    [''],
    ['SPECIFIC IDENTIFIED FRAUD RISKS (FRAUD TRIANGLE ANALYSIS)'],
    ['Risk Description', 'Line Item / Cycle', 'Fraud Triangle Element', 'Planned Audit Response'],
  ];

  const additionalFraud = engagement.fraudRisks.additionalRisks || engagement.fraudRisks.identifiedRisks || [];
  additionalFraud.forEach((f) => {
    fraudRows.push([
      f.riskDescription || f.rationale || '',
      f.lineItemName || f.impactedAccounts || '',
      f.fraudTriangleCategory || f.fraudType || '',
      f.plannedResponse || f.plannedProcedures || '',
    ]);
  });

  const wsFraud = XLSX.utils.aoa_to_sheet(fraudRows);
  applyCols(wsFraud, [32, 28, 24, 60]);
  XLSX.utils.book_append_sheet(wb, wsFraud, 'Fraud_Risks_SA240');

  // --- TAB 6: SA 315 CONTROL RISK REGISTER ---
  const crHeaders = [
    'Line Item / Process / Risk',
    'Associated Key Controls Identified',
    'Probability (1-5)',
    'Magnitude (1-5)',
    'Suggested Rating',
    'Final Risk Rating',
    'Partner Override Rationale',
    'Significant Risk?',
  ];
  const crRows: any[][] = [
    ['INTERNAL CONTROL RISK REGISTER (SA 315 / SA 330)'],
    [''],
    crHeaders,
  ];
  engagement.controlRiskRegister.forEach((cr) => {
    crRows.push([
      cr.lineItemOrRisk || cr.lineItemOrProcess || '',
      cr.controlsIdentified || cr.associatedControls || '',
      cr.probability,
      cr.magnitude,
      cr.suggestedRating,
      cr.finalRating,
      cr.isOverridden ? cr.overrideRationale : 'No Override',
      cr.finalRating === 'Significant' || cr.isSignificantRisk ? 'YES - Significant Risk' : 'No',
    ]);
  });
  const wsCR = XLSX.utils.aoa_to_sheet(crRows);
  applyCols(wsCR, [35, 45, 16, 16, 18, 18, 35, 20]);
  XLSX.utils.book_append_sheet(wb, wsCR, 'Control_Risk_Register');

  // --- TAB 7: SA 330 AUDIT STRATEGY ---
  const stratHeaders = [
    'Assessed Risk Description',
    'Financial Statement Line Item',
    'Assessed Risk Level',
    'Test of Controls (TOC)',
    'Test of Details (TOD)',
    'Analytical Procedures (AP)',
    'Extent of Testing',
    'Timing',
    'Planned Substantive Audit Procedures & Approach (SA 330)',
  ];
  const stratRows: any[][] = [
    ['OVERALL AUDIT STRATEGY & TESTING MATRIX (SA 330)'],
    [''],
    stratHeaders,
  ];
  engagement.auditStrategy.forEach((st) => {
    stratRows.push([
      st.riskDescription,
      st.lineItem,
      st.riskLevel || st.assessedRiskLevel || '',
      st.testOfControls ? 'YES' : 'NO',
      st.testOfDetails ? 'YES' : 'NO',
      st.analyticalProcedures ? 'YES' : 'NO',
      st.extent,
      st.timing,
      st.proceduresNotes,
    ]);
  });
  const wsStrat = XLSX.utils.aoa_to_sheet(stratRows);
  applyCols(wsStrat, [35, 25, 18, 12, 12, 12, 15, 15, 60]);
  XLSX.utils.book_append_sheet(wb, wsStrat, 'Audit_Strategy_SA330');

  // --- TAB 8: AUDIT PLANNING MEMO (SECTIONS) ---
  const memoRows: any[][] = [
    ['AUDIT PLANNING MEMORANDUM (SA 300)'],
    [`Client: ${engagement.clientName} | Financial Year: ${engagement.financialYear}`],
    [''],
  ];
  if (engagement.planningMemo.sections && engagement.planningMemo.sections.length > 0) {
    engagement.planningMemo.sections.forEach((sec) => {
      memoRows.push([sec.title.toUpperCase()]);
      memoRows.push([sec.content || sec.autoTemplate]);
      memoRows.push(['']);
    });
  } else {
    memoRows.push(['Executive Summary', engagement.planningMemo.executiveSummary || '']);
    memoRows.push(['Scope and Objectives', engagement.planningMemo.scopeAndObjectives || '']);
    memoRows.push(['Entity Understanding & Risks', engagement.planningMemo.entityAndRiskAssessment || '']);
    memoRows.push(['Materiality Determination', engagement.planningMemo.materialityDetermination || '']);
    memoRows.push(['Significant Risks & Fraud', engagement.planningMemo.significantRisksAndFraud || '']);
    memoRows.push(['Audit Approach & Staffing', engagement.planningMemo.auditApproachAndStaffing || '']);
  }
  const wsMemo = XLSX.utils.aoa_to_sheet(memoRows);
  applyCols(wsMemo, [30, 80]);
  XLSX.utils.book_append_sheet(wb, wsMemo, 'Planning_Memo_SA300');

  // --- TAB 9: REVIEW NOTES & SIGN OFF ---
  const reviewHeaders = ['Note ID', 'Stage Ref', 'Raised By', 'Date', 'Query / Review Observation', 'Status', 'Preparer Response'];
  const reviewRows: any[][] = [
    ['SQC 1 QUALITY CONTROL REVIEW NOTES REGISTER'],
    [''],
    reviewHeaders,
  ];
  engagement.signOffReview.reviewNotes.forEach((rn) => {
    reviewRows.push([
      rn.id,
      rn.stageRef || `Stage ${rn.stageNumber || 'General'}`,
      rn.raisedBy || '',
      rn.date || '',
      rn.noteText || rn.query || '',
      rn.status,
      rn.preparerResponse || rn.response || '',
    ]);
  });
  const wsReview = XLSX.utils.aoa_to_sheet(reviewRows);
  applyCols(wsReview, [12, 15, 22, 14, 45, 12, 45]);
  XLSX.utils.book_append_sheet(wb, wsReview, 'SQC1_Review_Notes');

  // Generate and trigger download
  const safeClient = engagement.clientName.replace(/[^a-zA-Z0-9]/g, '_');
  const safeFY = engagement.financialYear.replace(/[^a-zA-Z0-9]/g, '_');
  const fileName = `Audit_Workpapers_${safeClient}_${safeFY}.xlsx`;

  XLSX.writeFile(wb, fileName);
}

// ==========================================
// 2. WORD (.DOC / .DOCX) DOCUMENT EXPORTER
// ==========================================

export function exportWorkpaperToWord(
  engagement: EngagementData,
  materiality: ComputedMateriality
): void {
  const safeClient = engagement.clientName.replace(/[^a-zA-Z0-9]/g, '_');
  const safeFY = engagement.financialYear.replace(/[^a-zA-Z0-9]/g, '_');
  const fileName = `Audit_Planning_Memorandum_${safeClient}_${safeFY}.doc`;

  // Build high-fidelity HTML markup that Microsoft Word natively renders into full styled document
  const revPresumption = typeof engagement.fraudRisks.revenuePresumption === 'object'
    ? engagement.fraudRisks.revenuePresumption
    : { rebutted: false, rationale: engagement.fraudRisks.revenueRationale || '', plannedResponse: '' };

  const mgmtOverride = typeof engagement.fraudRisks.managementOverride === 'object'
    ? engagement.fraudRisks.managementOverride
    : { rationale: 'Non-rebuttable fraud risk under SA 240 para 31', plannedResponse: engagement.fraudRisks.managementOverrideProcedures || '' };

  const significantRisks = engagement.controlRiskRegister.filter((r) => r.finalRating === 'Significant');

  let memoSectionsHtml = '';
  if (engagement.planningMemo.sections && engagement.planningMemo.sections.length > 0) {
    memoSectionsHtml = engagement.planningMemo.sections
      .map(
        (sec) => `
        <div style="margin-bottom: 24px;">
          <h2 style="font-size: 14pt; color: #1e293b; border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px; margin-top: 18px;">
            ${sec.title}
          </h2>
          <p style="font-size: 10.5pt; line-height: 1.6; color: #334155; white-space: pre-line; margin-top: 8px;">
            ${sec.content || sec.autoTemplate}
          </p>
        </div>
      `
      )
      .join('');
  } else {
    memoSectionsHtml = `
      <div style="margin-bottom: 20px;">
        <h2 style="font-size: 14pt; color: #1e293b; border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px;">1. Executive Summary</h2>
        <p style="font-size: 10.5pt; line-height: 1.6; color: #334155;">${engagement.planningMemo.executiveSummary || 'No executive summary drafted.'}</p>
      </div>
      <div style="margin-bottom: 20px;">
        <h2 style="font-size: 14pt; color: #1e293b; border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px;">2. Scope and Objectives</h2>
        <p style="font-size: 10.5pt; line-height: 1.6; color: #334155;">${engagement.planningMemo.scopeAndObjectives || 'Statutory audit under Companies Act 2013.'}</p>
      </div>
    `;
  }

  // Trial Balance Schedule Table HTML if available
  let tbHtml = '';
  if (engagement.trialBalance && engagement.trialBalance.items.length > 0) {
    const tb = engagement.trialBalance;
    const rows = tb.items
      .slice(0, 40) // Include primary accounts
      .map(
        (item) => `
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 6px 8px; font-family: monospace; font-size: 9pt;">${item.accountCode}</td>
          <td style="padding: 6px 8px; font-size: 9.5pt;">${item.accountName}</td>
          <td style="padding: 6px 8px; font-size: 9pt; color: #64748b;">${item.scheduleIIIGroup}</td>
          <td style="padding: 6px 8px; font-size: 9pt; text-align: right;">${item.currentYearDebit ? formatINR(item.currentYearDebit) : '-'}</td>
          <td style="padding: 6px 8px; font-size: 9pt; text-align: right;">${item.currentYearCredit ? formatINR(item.currentYearCredit) : '-'}</td>
          <td style="padding: 6px 8px; font-size: 9pt; font-weight: bold; text-align: right;">${formatINR(item.currentYearNet)}</td>
          <td style="padding: 6px 8px; font-size: 8.5pt; color: ${item.materialityFlag?.includes('>OM') ? '#b91c1c' : '#475569'};">${item.materialityFlag || 'Normal'}</td>
        </tr>
      `
      )
      .join('');

    tbHtml = `
      <div style="page-break-before: always; margin-top: 24px;">
        <h2 style="font-size: 14pt; color: #1e293b; border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px;">
          Annexure: Trial Balance & Financial Highlights
        </h2>
        <p style="font-size: 10pt; color: #64748b; margin-bottom: 12px;">
          Imported File: <b>${tb.fileName || 'Client Trial Balance'}</b> | Reconciliation Status: <b>${tb.summary.isBalanced ? 'BALANCED (Dr = Cr)' : 'OUT OF BALANCE'}</b>
        </p>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px; font-size: 10pt; background: #f8fafc; border: 1px solid #cbd5e1;">
          <tr>
            <td style="padding: 8px 12px; border-right: 1px solid #cbd5e1;"><b>Turnover / Revenue:</b> ${formatINR(tb.summary.totalRevenue)}</td>
            <td style="padding: 8px 12px; border-right: 1px solid #cbd5e1;"><b>PBT:</b> ${formatINR(tb.summary.profitBeforeTax)}</td>
            <td style="padding: 8px 12px; border-right: 1px solid #cbd5e1;"><b>Total Assets:</b> ${formatINR(tb.summary.totalAssets)}</td>
            <td style="padding: 8px 12px;"><b>Net Worth:</b> ${formatINR(tb.summary.totalEquity)}</td>
          </tr>
        </table>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
          <thead>
            <tr style="background-color: #f1f5f9; border-bottom: 2px solid #94a3b8; font-size: 9pt; font-weight: bold; text-align: left;">
              <th style="padding: 8px;">Code</th>
              <th style="padding: 8px;">Account / Ledger</th>
              <th style="padding: 8px;">Schedule III Group</th>
              <th style="padding: 8px; text-align: right;">Debit (INR)</th>
              <th style="padding: 8px; text-align: right;">Credit (INR)</th>
              <th style="padding: 8px; text-align: right;">Net Balance</th>
              <th style="padding: 8px;">Materiality</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  }

  const htmlContent = `
    <!DOCTYPE html>
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
      <meta charset="utf-8">
      <title>Audit Planning Memorandum - ${engagement.clientName}</title>
      <style>
        body { font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e293b; line-height: 1.5; margin: 30px; }
        h1 { font-size: 22pt; color: #0f172a; margin-bottom: 4px; font-weight: bold; }
        h2 { font-size: 14pt; color: #334155; margin-top: 20px; margin-bottom: 8px; }
        h3 { font-size: 12pt; color: #475569; margin-top: 14px; margin-bottom: 6px; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt; }
        th, td { padding: 7px 10px; border: 1px solid #cbd5e1; }
        th { background-color: #f1f5f9; font-weight: bold; color: #0f172a; text-align: left; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt; font-weight: bold; }
        .badge-red { background-color: #fee2e2; color: #991b1b; }
        .badge-amber { background-color: #fef3c7; color: #92400e; }
        .badge-green { background-color: #dcfce7; color: #166534; }
        .header-box { border-bottom: 3px solid #0f172a; padding-bottom: 12px; margin-bottom: 24px; }
        .meta-table { width: 100%; margin-bottom: 24px; border: none; }
        .meta-table td { border: none; padding: 4px 8px; font-size: 10pt; }
      </style>
    </head>
    <body>
      <!-- COVER / HEADER -->
      <div class="header-box">
        <p style="font-size: 9.5pt; text-transform: uppercase; letter-spacing: 2px; color: #92400e; font-weight: bold; margin: 0;">
          Statutory Audit Workpaper • Confidential
        </p>
        <h1 style="margin: 6px 0 2px 0;">AUDIT PLANNING MEMORANDUM</h1>
        <p style="font-size: 14pt; font-weight: bold; color: #334155; margin: 0 0 4px 0;">
          ${engagement.clientName}
        </p>
        <p style="font-size: 10pt; color: #64748b; margin: 0;">
          CIN: <b>${engagement.cin}</b> | PAN: <b>${engagement.pan}</b> | Financial Year: <b>${engagement.financialYear}</b>
        </p>
        <p style="font-size: 9pt; color: #64748b; margin-top: 4px;">
          Conducted under ICAI Standards on Auditing (SA 300, SA 315, SA 240, SA 330, SA 320 & SQC 1)
        </p>
      </div>

      <!-- METADATA TABLE -->
      <table class="meta-table" style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px;">
        <tr>
          <td><b>Engagement Partner:</b> ${engagement.engagementPartner}</td>
          <td><b>Audit Senior / Lead:</b> ${engagement.auditSenior}</td>
        </tr>
        <tr>
          <td><b>Audit Engagement Type:</b> ${engagement.auditType}</td>
          <td><b>Preceding Auditor:</b> ${engagement.precedingAuditor}</td>
        </tr>
        <tr>
          <td><b>Date of Acceptance:</b> ${engagement.dateOfAcceptance}</td>
          <td><b>Acceptance Conclusion:</b> ${engagement.acceptanceConclusion}</td>
        </tr>
      </table>

      <!-- MATERIALITY SCHEDULE -->
      <h2 style="border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px;">
        1. Materiality Determination Schedule (SA 320 / SA 450)
      </h2>
      <table>
        <thead>
          <tr>
            <th>Materiality Level</th>
            <th>Formula / Basis</th>
            <th>Percentage</th>
            <th style="text-align: right;">Amount (INR)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>Overall Materiality (OM)</b></td>
            <td>${engagement.materiality.benchmarkBasis} (${formatINR(engagement.materiality.benchmarkAmount)})</td>
            <td>${engagement.materiality.omPercent}%</td>
            <td style="text-align: right; font-weight: bold;">${formatINR(materiality.overallMateriality)}</td>
          </tr>
          <tr>
            <td><b>Performance Materiality (PM)</b></td>
            <td>Applied to Overall Materiality</td>
            <td>${engagement.materiality.pmPercent}%</td>
            <td style="text-align: right; font-weight: bold; color: #b45309;">${formatINR(materiality.performanceMateriality)}</td>
          </tr>
          <tr>
            <td><b>Clearly Trivial Threshold (CT)</b></td>
            <td>Threshold for trivial misstatements (SA 450)</td>
            <td>${engagement.materiality.ctPercent}%</td>
            <td style="text-align: right; font-weight: bold; color: #475569;">${formatINR(materiality.clearlyTrivialThreshold)}</td>
          </tr>
        </tbody>
      </table>
      <p style="font-size: 10pt; color: #475569; background: #fdfaf3; padding: 10px; border-left: 3px solid #b45309;">
        <b>Materiality Rationale:</b> ${engagement.materiality.rationale}
      </p>

      <!-- SIGNIFICANT RISKS -->
      <h2 style="border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px; margin-top: 24px;">
        2. Significant Risks & Key Audit Matters Identified (SA 315 / SA 240)
      </h2>
      <table>
        <thead>
          <tr>
            <th>Line Item / Process</th>
            <th>Associated Control Identified</th>
            <th>Risk Rating</th>
            <th>Override Rationale</th>
          </tr>
        </thead>
        <tbody>
          ${significantRisks
            .map(
              (r) => `
            <tr>
              <td><b>${r.lineItemOrRisk || r.lineItemOrProcess}</b></td>
              <td>${r.controlsIdentified || 'Key internal controls identified'}</td>
              <td><span class="badge badge-red">Significant Risk</span></td>
              <td>${r.isOverridden ? r.overrideRationale : 'Scored as Significant based on high magnitude/probability'}</td>
            </tr>
          `
            )
            .join('')}
        </tbody>
      </table>

      <!-- SA 240 FRAUD RISKS -->
      <h2 style="border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px; margin-top: 24px;">
        3. Mandatory Fraud Risk Evaluation (SA 240)
      </h2>
      <table style="margin-bottom: 16px;">
        <tr>
          <td style="width: 30%; background: #f8fafc;"><b>Revenue Recognition Presumption (Para 26)</b></td>
          <td>
            <b>Status:</b> ${revPresumption.rebutted ? 'REBUTTED' : 'PRESUMPTION MAINTAINED (Significant Fraud Risk)'}<br>
            <b>Rationale:</b> ${revPresumption.rationale}<br>
            <b>Audit Response:</b> ${revPresumption.plannedResponse}
          </td>
        </tr>
        <tr>
          <td style="width: 30%; background: #f8fafc;"><b>Management Override of Controls (Para 31)</b></td>
          <td>
            <b>Status:</b> Non-Rebuttable Inherent Significant Risk<br>
            <b>Procedures:</b> Testing of non-standard manual journal entries, retrospection of accounting estimates for bias, and rationale for significant unusual transactions.<br>
            <b>Specific Response:</b> ${mgmtOverride.plannedResponse}
          </td>
        </tr>
      </table>

      <!-- SA 330 AUDIT STRATEGY TABLE -->
      <h2 style="border-bottom: 1.5pt solid #cbd5e1; padding-bottom: 4px; margin-top: 24px;">
        4. Overall Audit Strategy & Substantive Testing Responses (SA 330)
      </h2>
      <table>
        <thead>
          <tr>
            <th>Risk Description</th>
            <th>FS Line Item</th>
            <th>TOC</th>
            <th>TOD</th>
            <th>AP</th>
            <th>Extent</th>
            <th>Timing</th>
            <th>Planned Audit Approach</th>
          </tr>
        </thead>
        <tbody>
          ${engagement.auditStrategy
            .map(
              (st) => `
            <tr>
              <td><b>${st.riskDescription}</b></td>
              <td>${st.lineItem}</td>
              <td style="text-align: center;">${st.testOfControls ? 'Yes' : 'No'}</td>
              <td style="text-align: center;">${st.testOfDetails ? 'Yes' : 'No'}</td>
              <td style="text-align: center;">${st.analyticalProcedures ? 'Yes' : 'No'}</td>
              <td>${st.extent}</td>
              <td>${st.timing}</td>
              <td style="font-size: 9pt;">${st.proceduresNotes}</td>
            </tr>
          `
            )
            .join('')}
        </tbody>
      </table>

      <!-- MEMO BODY SECTIONS -->
      <div style="page-break-before: always; margin-top: 24px;">
        <h1 style="font-size: 18pt; border-bottom: 2px solid #0f172a; padding-bottom: 6px;">
          5. Audit Planning Memorandum Sections (SA 300)
        </h1>
        ${memoSectionsHtml}
      </div>

      <!-- TRIAL BALANCE (IF IMPORTED) -->
      ${tbHtml}

      <!-- SIGN OFF BLOCK -->
      <div style="page-break-before: always; margin-top: 30px; border-top: 2px solid #0f172a; padding-top: 20px;">
        <h2 style="margin-top: 0;">6. Quality Control Sign-Off & Approvals (SQC 1 / SA 220)</h2>
        <table style="width: 100%; border: 1px solid #cbd5e1; margin-top: 14px;">
          <tr>
            <td style="width: 50%; padding: 14px; vertical-align: top;">
              <p style="font-size: 9pt; text-transform: uppercase; color: #64748b; margin: 0;">Audit Preparer</p>
              <p style="font-size: 11pt; font-weight: bold; margin: 4px 0;">${engagement.signOffReview.preparer.name || engagement.auditSenior}</p>
              <p style="font-size: 9pt; color: #475569; margin: 0;">Declaration: ${engagement.signOffReview.preparer.declared ? 'Completed & Submitted for Review' : 'Pending Final Declaration'}</p>
              <p style="font-size: 9pt; color: #64748b; margin: 2px 0;">Date: ${engagement.signOffReview.preparer.date || 'N/A'}</p>
            </td>
            <td style="width: 50%; padding: 14px; vertical-align: top; border-left: 1px solid #cbd5e1;">
              <p style="font-size: 9pt; text-transform: uppercase; color: #64748b; margin: 0;">Engagement Partner / Reviewer</p>
              <p style="font-size: 11pt; font-weight: bold; margin: 4px 0;">${engagement.signOffReview.reviewer.name || engagement.engagementPartner}</p>
              <p style="font-size: 9pt; color: #475569; margin: 0;">Conclusion: <b>${engagement.signOffReview.reviewer.conclusion}</b></p>
              <p style="font-size: 9pt; color: #64748b; margin: 2px 0;">Date: ${engagement.signOffReview.reviewer.date || 'N/A'}</p>
            </td>
          </tr>
        </table>
      </div>
    </body>
    </html>
  `;

  // Create Blob with application/msword mime type and trigger download
  const blob = new Blob(['\ufeff', htmlContent], {
    type: 'application/msword;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ==========================================
// 3. PDF GENERATOR USING JSPDF
// ==========================================

export async function exportWorkpaperToPdf(
  engagement: EngagementData,
  materiality: ComputedMateriality
): Promise<void> {
  const { jsPDF } = await import('jspdf');

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  let y = margin;

  const checkPageBreak = (neededHeight: number) => {
    if (y + neededHeight > pageHeight - margin) {
      doc.addPage();
      y = margin;
      drawHeader();
    }
  };

  const drawHeader = () => {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(140, 140, 140);
    doc.text('CONFIDENTIAL • ICAI STATUTORY AUDIT WORKPAPER', margin, 9);
    doc.text(`${engagement.clientName} | ${engagement.financialYear}`, pageWidth - margin, 9, { align: 'right' });
    doc.setDrawColor(220, 220, 220);
    doc.setLineWidth(0.3);
    doc.line(margin, 11, pageWidth - margin, 11);
    doc.setTextColor(20, 20, 20);
  };

  // First page banner
  doc.setFillColor(245, 243, 237);
  doc.rect(margin, y, pageWidth - margin * 2, 28, 'F');
  doc.setDrawColor(180, 120, 50);
  doc.setLineWidth(0.8);
  doc.rect(margin, y, pageWidth - margin * 2, 28, 'S');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(28, 34, 43);
  doc.text('AUDIT PLANNING MEMORANDUM & WORKPAPERS', margin + 6, y + 9);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10.5);
  doc.setTextColor(160, 80, 20);
  doc.text(engagement.clientName, margin + 6, y + 16);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(90, 90, 90);
  doc.text(
    `CIN: ${engagement.cin} | Financial Year: ${engagement.financialYear} | Conducted under ICAI SAs`,
    margin + 6,
    y + 22
  );

  y += 34;

  // Metadata Block
  doc.setFillColor(250, 250, 250);
  doc.rect(margin, y, pageWidth - margin * 2, 16, 'F');
  doc.setDrawColor(220, 220, 220);
  doc.rect(margin, y, pageWidth - margin * 2, 16, 'S');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(50, 50, 50);
  doc.text('Partner:', margin + 4, y + 6);
  doc.setFont('helvetica', 'normal');
  doc.text(engagement.engagementPartner, margin + 20, y + 6);

  doc.setFont('helvetica', 'bold');
  doc.text('Audit Senior:', margin + 95, y + 6);
  doc.setFont('helvetica', 'normal');
  doc.text(engagement.auditSenior, margin + 118, y + 6);

  doc.setFont('helvetica', 'bold');
  doc.text('Audit Type:', margin + 4, y + 12);
  doc.setFont('helvetica', 'normal');
  doc.text(engagement.auditType.split(' ')[0], margin + 22, y + 12);

  doc.setFont('helvetica', 'bold');
  doc.text('Acceptance:', margin + 95, y + 12);
  doc.setFont('helvetica', 'normal');
  doc.text(`${engagement.acceptanceConclusion} (${engagement.dateOfAcceptance})`, margin + 118, y + 12);

  y += 22;

  // SECTION 1: MATERIALITY SCHEDULE
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(30, 40, 50);
  doc.text('1. MATERIALITY DETERMINATION (SA 320 & SA 450)', margin, y);
  y += 4;

  // Materiality Table Box
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.2);

  const matData = [
    ['Benchmark Basis & Reference', `${engagement.materiality.benchmarkBasis} (${formatCompactINR(engagement.materiality.benchmarkAmount)})`],
    ['Overall Materiality (OM)', `${formatINR(materiality.overallMateriality)} (${engagement.materiality.omPercent}% of benchmark)`],
    ['Performance Materiality (PM)', `${formatINR(materiality.performanceMateriality)} (${engagement.materiality.pmPercent}% of OM)`],
    ['Clearly Trivial Threshold (CT)', `${formatINR(materiality.clearlyTrivialThreshold)} (${engagement.materiality.ctPercent}% of OM)`],
  ];

  matData.forEach(([label, val]) => {
    doc.setFillColor(248, 248, 248);
    doc.rect(margin, y, 65, 6, 'FD');
    doc.setFillColor(255, 255, 255);
    doc.rect(margin + 65, y, pageWidth - margin * 2 - 65, 6, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(60, 60, 60);
    doc.text(label, margin + 3, y + 4.2);

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(20, 20, 20);
    doc.text(val, margin + 68, y + 4.2);

    y += 6;
  });

  y += 6;

  // SECTION 2: TRIAL BALANCE HIGHLIGHTS (IF IMPORTED)
  if (engagement.trialBalance && engagement.trialBalance.items.length > 0) {
    checkPageBreak(30);
    const tb = engagement.trialBalance;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(30, 40, 50);
    doc.text('2. TRIAL BALANCE & FINANCIAL AGGREGATES', margin, y);
    y += 4;

    const tbMetrics = [
      ['Turnover / Revenue', formatINR(tb.summary.totalRevenue)],
      ['Profit Before Tax (PBT)', formatINR(tb.summary.profitBeforeTax)],
      ['Total Balance Sheet Assets', formatINR(tb.summary.totalAssets)],
      ['Total Net Worth / Equity', formatINR(tb.summary.totalEquity)],
      ['Total Consortium Borrowings', formatINR(tb.summary.totalBorrowings)],
      ['TB Reconciliation Proof', tb.summary.isBalanced ? 'BALANCED: Dr = Cr (Diff: Rs. 0)' : 'OUT OF BALANCE'],
    ];

    tbMetrics.forEach(([lbl, val]) => {
      doc.setFillColor(248, 248, 248);
      doc.rect(margin, y, 65, 5.5, 'FD');
      doc.setFillColor(255, 255, 255);
      doc.rect(margin + 65, y, pageWidth - margin * 2 - 65, 5.5, 'FD');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text(lbl, margin + 3, y + 3.8);

      doc.setFont('helvetica', 'normal');
      doc.text(val, margin + 68, y + 3.8);

      y += 5.5;
    });

    y += 6;
  }

  // SECTION 3: SIGNIFICANT RISKS
  checkPageBreak(35);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(30, 40, 50);
  doc.text('3. SIGNIFICANT RISKS & FRAUD RISK REGISTER (SA 315 / SA 240)', margin, y);
  y += 4;

  const sigRisks = engagement.controlRiskRegister.filter((r) => r.finalRating === 'Significant');
  sigRisks.slice(0, 6).forEach((sr) => {
    checkPageBreak(12);
    doc.setFillColor(254, 242, 242);
    doc.setDrawColor(252, 165, 165);
    doc.rect(margin, y, pageWidth - margin * 2, 11, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(153, 27, 27);
    doc.text(`[SIGNIFICANT RISK] ${sr.lineItemOrRisk || sr.lineItemOrProcess}`, margin + 3, y + 4.5);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(50, 50, 50);
    const notes = sr.controlsIdentified || sr.overrideRationale || 'Mandatory substantive response required under SA 330.';
    doc.text(notes.substring(0, 115) + (notes.length > 115 ? '...' : ''), margin + 3, y + 8.5);

    y += 13;
  });

  // SECTION 4: AUDIT STRATEGY SAMPLE
  checkPageBreak(40);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(30, 40, 50);
  doc.text('4. AUDIT TESTING RESPONSES & PROCEDURES (SA 330)', margin, y);
  y += 4;

  engagement.auditStrategy.slice(0, 4).forEach((st) => {
    checkPageBreak(15);
    doc.setFillColor(250, 250, 250);
    doc.setDrawColor(210, 210, 210);
    doc.rect(margin, y, pageWidth - margin * 2, 13, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(20, 20, 20);
    doc.text(`${st.riskDescription} (${st.lineItem})`, margin + 3, y + 4.5);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.2);
    doc.setTextColor(80, 80, 80);
    doc.text(
      `TOC: ${st.testOfControls ? 'YES' : 'NO'} | TOD: ${st.testOfDetails ? 'YES' : 'NO'} | AP: ${st.analyticalProcedures ? 'YES' : 'NO'} | Extent: ${st.extent} | Timing: ${st.timing}`,
      margin + 3,
      y + 8
    );
    doc.text(st.proceduresNotes.substring(0, 110) + '...', margin + 3, y + 11.5);

    y += 15;
  });

  // SECTION 5: SIGN OFF BLOCK
  checkPageBreak(30);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(30, 40, 50);
  doc.text('5. QUALITY CONTROL & ENGAGEMENT SIGN-OFF (SQC 1)', margin, y);
  y += 4;

  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(203, 213, 225);
  doc.rect(margin, y, (pageWidth - margin * 2) / 2 - 2, 18, 'FD');
  doc.rect(margin + (pageWidth - margin * 2) / 2 + 2, y, (pageWidth - margin * 2) / 2 - 2, 18, 'FD');

  // Preparer
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text('PREPARED BY', margin + 4, y + 5);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text(engagement.signOffReview.preparer.name || engagement.auditSenior, margin + 4, y + 10);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.text(`Status: ${engagement.signOffReview.preparer.declared ? 'Declared & Submitted' : 'Draft'}`, margin + 4, y + 14);

  // Reviewer
  const rx = margin + (pageWidth - margin * 2) / 2 + 6;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text('REVIEWED & APPROVED BY', rx, y + 5);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text(engagement.signOffReview.reviewer.name || engagement.engagementPartner, rx, y + 10);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.text(`Conclusion: ${engagement.signOffReview.reviewer.conclusion}`, rx, y + 14);

  const safeClient = engagement.clientName.replace(/[^a-zA-Z0-9]/g, '_');
  const safeFY = engagement.financialYear.replace(/[^a-zA-Z0-9]/g, '_');
  doc.save(`Audit_Planning_Workpaper_${safeClient}_${safeFY}.pdf`);
}
