/**
 * Paras Accounting & Auditing Advisory
 * Enterprise Word (.doc) and PDF Report Generation Engine
 * Abu Dhabi Global Market (ADGM) & UAE MOHRE Registered Practice
 */

import { AppraisalRecord, User, TaskEvaluation, AttendanceRecord, StatutoryNotice, AnnualPerformancePlan, ProfessionalCertification, AuditLogEntry } from '../types';
import { getLoyaltyTierInfo, getTierMetadata } from './scoringEngine';

export interface ReportExportOptions {
  title: string;
  subtitle?: string;
  filename: string;
  officialRefCode?: string;
  contentHtml: string;
}

/**
 * Exports HTML content as a formatted Microsoft Word (.doc) document.
 * Uses Microsoft Word-compatible HTML/XML envelope with standard corporate styles.
 */
export function exportToWord({
  title,
  subtitle = 'Paras Accounting & Auditing Advisory — Abu Dhabi, UAE',
  filename,
  officialRefCode = 'PAA-REP-2026',
  contentHtml,
}: ReportExportOptions): void {
  const currentDate = new Date().toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  const fullWordHtml = `
<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
  <meta charset="utf-8">
  <title>${title}</title>
  <!--[if gte mso 9]>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <style>
    @page Section1 {
      size: 595.3pt 841.9pt; /* A4 */
      margin: 1.0in 1.0in 1.0in 1.0in;
      mso-header-margin: 36.0pt;
      mso-footer-margin: 36.0pt;
      mso-paper-source: 0;
    }
    div.Section1 { page: Section1; }
    body {
      font-family: 'Calibri', 'Arial', sans-serif;
      font-size: 11pt;
      color: #1e293b;
      line-height: 1.5;
    }
    h1 {
      font-size: 18pt;
      color: #0f172a;
      font-weight: bold;
      margin-bottom: 4pt;
      border-bottom: 2pt solid #0d9488;
      padding-bottom: 4pt;
    }
    h2 {
      font-size: 13pt;
      color: #1e3a8a;
      font-weight: bold;
      margin-top: 14pt;
      margin-bottom: 6pt;
      border-bottom: 1pt solid #cbd5e1;
      padding-bottom: 2pt;
    }
    h3 {
      font-size: 11pt;
      color: #334155;
      font-weight: bold;
      margin-top: 10pt;
      margin-bottom: 4pt;
    }
    p { margin-top: 0; margin-bottom: 6pt; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8pt;
      margin-bottom: 12pt;
      font-size: 10pt;
    }
    th {
      background-color: #0f172a;
      color: #ffffff;
      font-weight: bold;
      padding: 6pt 8pt;
      text-align: left;
      border: 1pt solid #0f172a;
    }
    td {
      padding: 5pt 8pt;
      border: 1pt solid #cbd5e1;
    }
    tr:nth-child(even) td {
      background-color: #f8fafc;
    }
    .badge {
      display: inline-block;
      padding: 2pt 6pt;
      font-size: 9pt;
      font-weight: bold;
      border-radius: 3pt;
    }
    .badge-teal { background-color: #ccfbf1; color: #0f766e; }
    .badge-blue { background-color: #dbeafe; color: #1e40af; }
    .badge-rose { background-color: #ffe4e6; color: #be123c; }
    .badge-amber { background-color: #fef3c7; color: #b45309; }
    .text-right { text-align: right; }
    .text-center { text-align: center; }
    .letterhead {
      border-bottom: 3pt solid #1e3a8a;
      padding-bottom: 8pt;
      margin-bottom: 14pt;
    }
    .company-title {
      font-size: 16pt;
      font-weight: bold;
      color: #1e3a8a;
      text-transform: uppercase;
      letter-spacing: 0.5pt;
    }
    .company-sub {
      font-size: 9pt;
      color: #64748b;
    }
    .meta-box {
      background-color: #f1f5f9;
      border-left: 4pt solid #0d9488;
      padding: 8pt 12pt;
      margin-bottom: 14pt;
      font-size: 10pt;
    }
    .signature-grid {
      margin-top: 30pt;
      width: 100%;
      border-collapse: collapse;
    }
    .signature-cell {
      width: 33.33%;
      padding-top: 35pt;
      border-top: 1pt solid #475569;
      text-align: center;
      font-size: 9pt;
      color: #475569;
    }
  </style>
</head>
<body>
<div class="Section1">
  <!-- Letterhead -->
  <div class="letterhead">
    <table style="width: 100%; border: none; margin: 0;">
      <tr style="border: none; background: transparent;">
        <td style="border: none; width: 65%; padding: 0;">
          <div class="company-title">PARAS ACCOUNTING & AUDITING ADVISORY</div>
          <div class="company-sub">
            Abu Dhabi Global Market (ADGM) & UAE MOHRE Registered Practice<br>
            Al Maryah Tower, Floors 24-25, Abu Dhabi, United Arab Emirates<br>
            Statutory Compliance: UAE Federal Decree-Law No. 33 of 2021
          </div>
        </td>
        <td style="border: none; width: 35%; text-align: right; vertical-align: top; padding: 0;">
          <div style="font-size: 9pt; color: #475569;">
            <strong>Ref Code:</strong> ${officialRefCode}<br>
            <strong>Date Generated:</strong> ${currentDate}<br>
            <strong>Practice Jurisdiction:</strong> Abu Dhabi, UAE
          </div>
        </td>
      </tr>
    </table>
  </div>

  <!-- Document Title -->
  <h1 style="margin-top: 0;">${title}</h1>
  ${subtitle ? `<p style="font-size: 10pt; color: #64748b; margin-top: -2pt; margin-bottom: 12pt;">${subtitle}</p>` : ''}

  <!-- Body Content -->
  ${contentHtml}

  <!-- Signatory Block -->
  <table style="width: 100%; border: none; margin-top: 36pt;">
    <tr style="border: none; background: transparent;">
      <td style="border: none; border-top: 1.5pt solid #475569; padding-top: 8pt; width: 30%; text-align: center;">
        <strong>Evaluated Employee / Specialist</strong><br>
        <span style="font-size: 9pt; color: #64748b;">Signature & Date</span>
      </td>
      <td style="border: none; width: 5%;"></td>
      <td style="border: none; border-top: 1.5pt solid #475569; padding-top: 8pt; width: 30%; text-align: center;">
        <strong>Practice Engagement Partner</strong><br>
        <span style="font-size: 9pt; color: #64748b;">Tariq Al Hammadi, Partner</span>
      </td>
      <td style="border: none; width: 5%;"></td>
      <td style="border: none; border-top: 1.5pt solid #475569; padding-top: 8pt; width: 30%; text-align: center;">
        <strong>Head of Human Capital & Governance</strong><br>
        <span style="font-size: 9pt; color: #64748b;">Mariam Al Shamsi, Director</span>
      </td>
    </tr>
  </table>

  <!-- Official Footer -->
  <div style="margin-top: 24pt; border-top: 1pt solid #e2e8f0; padding-top: 6pt; font-size: 8pt; color: #94a3b8; text-align: center;">
    Confidential • Paras Accounting & Auditing Advisory • 2026 • Authorized under UAE Labor Law
  </div>
</div>
</body>
</html>
  `;

  const blob = new Blob(['\ufeff', fullWordHtml], {
    type: 'application/msword;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const downloadLink = document.createElement('a');
  downloadLink.href = url;
  downloadLink.download = filename.endsWith('.doc') ? filename : `${filename}.doc`;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
  URL.revokeObjectURL(url);
}

/**
 * Triggers a dedicated, pristine print-to-PDF dialog in the browser.
 * Opens an isolated styled printing window with exact A4 print rules.
 */
export function exportToPdf({
  title,
  subtitle = 'Paras Accounting & Auditing Advisory — Abu Dhabi, UAE',
  filename,
  officialRefCode = 'PAA-REP-2026',
  contentHtml,
}: ReportExportOptions): void {
  const currentDate = new Date().toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  const printWindow = window.open('', '_blank', 'width=900,height=800');
  if (!printWindow) {
    window.print();
    return;
  }

  const printableHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${title} - ${officialRefCode}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 15mm;
    }
    @media print {
      body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      .no-print { display: none !important; }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      font-size: 12px;
      color: #1e293b;
      line-height: 1.5;
      margin: 0;
      padding: 20px;
    }
    h1 {
      font-size: 20px;
      color: #0f172a;
      font-weight: 800;
      margin-top: 0;
      margin-bottom: 4px;
      border-bottom: 2px solid #0d9488;
      padding-bottom: 6px;
    }
    h2 {
      font-size: 14px;
      color: #1e3a8a;
      font-weight: 700;
      margin-top: 16px;
      margin-bottom: 8px;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 11px;
    }
    th {
      background-color: #0f172a !important;
      color: #ffffff !important;
      font-weight: 600;
      padding: 6px 10px;
      text-align: left;
      border: 1px solid #0f172a;
    }
    td {
      padding: 6px 10px;
      border: 1px solid #e2e8f0;
    }
    tr:nth-child(even) td {
      background-color: #f8fafc;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      font-size: 10px;
      font-weight: 600;
      border-radius: 4px;
    }
    .badge-teal { background-color: #ccfbf1 !important; color: #0f766e !important; }
    .badge-blue { background-color: #dbeafe !important; color: #1e40af !important; }
    .badge-rose { background-color: #ffe4e6 !important; color: #be123c !important; }
    .badge-amber { background-color: #fef3c7 !important; color: #b45309 !important; }
    .text-right { text-align: right; }
    .meta-box {
      background-color: #f1f5f9;
      border-left: 4px solid #0d9488;
      padding: 10px 14px;
      margin: 12px 0;
      border-radius: 0 6px 6px 0;
    }
    .action-bar {
      margin-bottom: 16px;
      padding: 10px 16px;
      background: #f1f5f9;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .btn {
      background: #0f172a;
      color: #fff;
      border: none;
      padding: 8px 16px;
      font-size: 12px;
      font-weight: bold;
      border-radius: 6px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="action-bar no-print">
    <div>
      <strong>Print / Save to PDF Preview:</strong> ${title}
    </div>
    <div>
      <button class="btn" onclick="window.print()">Save as PDF / Print</button>
      <button class="btn" style="background: #64748b; margin-left: 8px;" onclick="window.close()">Close Window</button>
    </div>
  </div>

  <!-- Letterhead -->
  <div style="border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 16px; display: flex; justify-content: space-between;">
    <div>
      <div style="font-size: 18px; font-weight: 900; color: #1e3a8a; letter-spacing: 0.5px;">
        PARAS ACCOUNTING & AUDITING ADVISORY
      </div>
      <div style="font-size: 10px; color: #64748b; margin-top: 2px;">
        Abu Dhabi Global Market (ADGM) & UAE MOHRE Registered Practice<br>
        Al Maryah Tower, Floors 24-25, Abu Dhabi, United Arab Emirates<br>
        Statutory Governance: UAE Federal Decree-Law No. 33 of 2021
      </div>
    </div>
    <div style="text-align: right; font-size: 10px; color: #475569;">
      <strong>Official Ref:</strong> ${officialRefCode}<br>
      <strong>Issue Date:</strong> ${currentDate}<br>
      <strong>Jurisdiction:</strong> Abu Dhabi, UAE
    </div>
  </div>

  <h1>${title}</h1>
  ${subtitle ? `<p style="font-size: 11px; color: #64748b; margin-top: -2px; margin-bottom: 14px;">${subtitle}</p>` : ''}

  ${contentHtml}

  <!-- Signatures -->
  <div style="margin-top: 40px; display: flex; justify-content: space-between; border-top: 1px solid #cbd5e1; padding-top: 12px;">
    <div style="width: 30%; text-align: center;">
      <div style="height: 35px;"></div>
      <div style="border-top: 1px solid #64748b; padding-top: 4px; font-weight: bold; font-size: 10px;">
        Evaluated Specialist / Auditor
      </div>
    </div>
    <div style="width: 30%; text-align: center;">
      <div style="height: 35px;"></div>
      <div style="border-top: 1px solid #64748b; padding-top: 4px; font-weight: bold; font-size: 10px;">
        Tariq Al Hammadi, Partner
      </div>
      <div style="font-size: 9px; color: #64748b;">Practice Engagement Leader</div>
    </div>
    <div style="width: 30%; text-align: center;">
      <div style="height: 35px;"></div>
      <div style="border-top: 1px solid #64748b; padding-top: 4px; font-weight: bold; font-size: 10px;">
        Mariam Al Shamsi, Director
      </div>
      <div style="font-size: 9px; color: #64748b;">Head of Human Capital</div>
    </div>
  </div>

  <div style="margin-top: 30px; text-align: center; font-size: 9px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 8px;">
    Confidential Internal Record • Paras Accounting & Auditing Advisory • 2026
  </div>

  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 500);
    };
  </script>
</body>
</html>
  `;

  printWindow.document.open();
  printWindow.document.write(printableHtml);
  printWindow.document.close();
}

/**
 * Generates HTML string for Employee Appraisal Scorecard Report
 */
export function generateAppraisalReportHtml(
  appraisal: AppraisalRecord,
  employee: User,
  managerName: string = 'Tariq Al Hammadi'
): string {
  const loyalty = getLoyaltyTierInfo(employee.tenureYears);
  const tierMeta = getTierMetadata(appraisal.performanceTier);

  return `
    <div class="meta-box">
      <table style="width: 100%; border: none; margin: 0; background: transparent;">
        <tr style="border: none; background: transparent;">
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Employee Name:</strong> ${employee.fullName} (${employee.employeeIdCode})<br>
            <strong>Current Designation:</strong> ${employee.currentDesignation}<br>
            <strong>Practice Department:</strong> ${employee.departmentName}<br>
            <strong>Pay Grade Level:</strong> ${employee.payGradeLevel}
          </td>
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Practice Lead / Evaluator:</strong> ${managerName}<br>
            <strong>Tenure with Practice:</strong> ${employee.tenureYears} Years (${loyalty.tierName})<br>
            <strong>Evaluation Cycle:</strong> ${appraisal.cycleName} (Q3-2026)<br>
            <strong>HR Approval Standing:</strong> <span class="badge badge-teal">${appraisal.hrApprovalStatus}</span>
          </td>
        </tr>
      </table>
    </div>

    <h2>1. Executive Appraisal Standing & Final Score</h2>
    <table>
      <thead>
        <tr>
          <th>Evaluation Metric</th>
          <th style="width: 20%;">Assigned Weight</th>
          <th style="width: 20%;" class="text-right">Raw Achievement</th>
          <th style="width: 20%;" class="text-right">Weighted Pts</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Service Delivery Deliverables Matrix</strong><br><small style="color: #64748b;">Completed audit fieldwork, technical opinions, and sign-offs</small></td>
          <td>50%</td>
          <td class="text-right"><strong>${appraisal.grossServicePoints} / 100</strong></td>
          <td class="text-right">${(appraisal.grossServicePoints * 0.5).toFixed(1)} pts</td>
        </tr>
        <tr>
          <td><strong>Task Turnaround SLA Adherence</strong><br><small style="color: #64748b;">Timeliness against engagement turnaround milestones</small></td>
          <td>25%</td>
          <td class="text-right"><strong>${appraisal.taskSLAIndex}%</strong></td>
          <td class="text-right">${(appraisal.taskSLAIndex * 0.25).toFixed(1)} pts</td>
        </tr>
        <tr>
          <td><strong>Office Attendance & Check-In Punctuality</strong><br><small style="color: #64748b;">Prefilled via HR biometric & attendance controls</small></td>
          <td>15%</td>
          <td class="text-right"><strong>${appraisal.punctualityIndex}%</strong></td>
          <td class="text-right">${(appraisal.punctualityIndex * 0.15).toFixed(1)} pts</td>
        </tr>
        <tr>
          <td><strong>Growth / Improvement Delta</strong><br><small style="color: #64748b;">Cycle-over-cycle progression vs previous evaluation</small></td>
          <td>10%</td>
          <td class="text-right"><strong>${appraisal.growthDeltaPct >= 0 ? '+' : ''}${appraisal.growthDeltaPct}%</strong></td>
          <td class="text-right">${((75 + appraisal.growthDeltaPct * 2.5) * 0.1).toFixed(1)} pts</td>
        </tr>
        <tr style="background-color: #f1f5f9; font-weight: bold;">
          <td colspan="3"><strong>Base Performance Score (0 - 100)</strong></td>
          <td class="text-right"><strong>${appraisal.baseScore} pts</strong></td>
        </tr>
        <tr style="background-color: #e6fffa; font-weight: bold;">
          <td colspan="2">
            <strong>Tenure Loyalty & Retention Multiplier</strong><br>
            <small style="color: #0d9488;">Recognizes dedicated service to Paras Advisory (${employee.tenureYears} yrs)</small>
          </td>
          <td class="text-right" style="color: #0d9488;">+${loyalty.boostPct} boost</td>
          <td class="text-right" style="color: #0d9488; font-size: 12pt;">${appraisal.tenureLoyaltyMultiplier.toFixed(2)}x</td>
        </tr>
        <tr style="background-color: #0f172a; color: #ffffff; font-weight: bold; font-size: 11pt;">
          <td colspan="2" style="color: #fff;">FINAL WEIGHTED PRACTICE SCORE</td>
          <td class="text-right" style="color: #2dd4bf;">Tier: ${tierMeta.label}</td>
          <td class="text-right" style="color: #2dd4bf; font-size: 13pt;">${appraisal.finalWeightedScore} pts</td>
        </tr>
      </tbody>
    </table>

    <h2>2. Progressive Governance & Action Plan</h2>
    <div style="padding: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
      <p><strong>Action Track:</strong> ${appraisal.actionPlanStatus.replace(/_/g, ' ')}</p>
      <p><strong>Evaluation Philosophy:</strong> Growth-First & Constructive. Employees falling below threshold are supported via firm-sponsored training, dedicated partner mentoring, and two-tier 90-day improvement agreements before any statutory escalations.</p>
    </div>

    <h2>3. Evaluator Comments & Professional Coaching Observations</h2>
    <div style="padding: 10px 14px; background-color: #ffffff; border-left: 3px solid #1e3a8a; border: 1px solid #e2e8f0; border-left-width: 4px; margin-top: 8px;">
      <p style="font-style: italic; margin: 0;">
        "${appraisal.coachingNotes?.[0] || 'Demonstrates solid proficiency across IFRS audit workpapers. Turnaround meets statutory practice guidelines.'}"
      </p>
    </div>
  `;
}

/**
 * Generates HTML string for UAE Statutory Notice / 90-Day Improvement Plan
 */
export function generateStatutoryNoticeHtml(
  notice: StatutoryNotice,
  employee: User,
  companyInfo: any
): string {
  return `
    <div class="meta-box" style="border-left-color: #be123c;">
      <table style="width: 100%; border: none; margin: 0; background: transparent;">
        <tr style="border: none; background: transparent;">
          <td style="border: none; width: 60%; padding: 0;">
            <strong>Official Notice Reference:</strong> ${notice.officialRefCode}<br>
            <strong>Date of Notice:</strong> ${notice.dateIssued}<br>
            <strong>Notice Recipient:</strong> ${employee.fullName} (${employee.employeeIdCode})<br>
            <strong>Designation & Grade:</strong> ${employee.currentDesignation} (${employee.payGradeLevel})
          </td>
          <td style="border: none; width: 40%; padding: 0;">
            <strong>Statutory Escalation Tier:</strong> <span class="badge badge-rose">Tier ${notice.tier} Escalation</span><br>
            <strong>Mandatory Timeline:</strong> ${notice.timelineDays} Calendar Days<br>
            <strong>Supervisory Lead:</strong> ${notice.mentorshipSupervisor}<br>
            <strong>Current Status:</strong> ${notice.status}
          </td>
        </tr>
      </table>
    </div>

    <h2>1. Statutory Legal Basis & Authority</h2>
    <p>
      This notice is issued under the regulatory framework of the <strong>UAE Federal Decree-Law No. 33 of 2021 regarding the Regulation of Labour Relations</strong> and its implementing Executive Regulations (Cabinet Resolution No. 1 of 2022), read together with internal Human Capital Quality Governance policies of Paras Accounting & Auditing Advisory.
    </p>

    <h2>2. Subject Matter & Performance Context</h2>
    <div style="background-color: #fff1f2; border: 1px solid #fecdd3; padding: 10px 14px; border-radius: 6px;">
      <p style="margin: 0; font-weight: 500; color: #9f1239;">
        "${notice.summaryText}"
      </p>
    </div>

    <h2>3. Mandatory Structured Deliverables & Recovery Milestones</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 10%;">#</th>
          <th>Required Action Milestone</th>
          <th style="width: 25%;">Compliance Window</th>
        </tr>
      </thead>
      <tbody>
        ${notice.actionRequirements.map((req, idx) => `
          <tr>
            <td style="font-weight: bold;">${idx + 1}</td>
            <td>${req}</td>
            <td>Within ${notice.timelineDays} Days</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <h2>4. Progressive Two-Tier Improvement Framework Rights</h2>
    <p style="font-size: 10pt; color: #475569; line-height: 1.6;">
      In accordance with fair practice standards:
      <br><strong>Tier 1 (90 Days):</strong> Structured coaching, fully firm-sponsored technical retraining, and bi-weekly milestone checkpoints.
      <br><strong>Tier 2 (Extended 90 Days):</strong> Formal secondary review period with senior partner oversight should Tier 1 objectives remain partially unmet.
      <br><strong>Statutory Rights:</strong> The employee retains full right to submit written clarifications, access all underlying audit timesheet records, and be accompanied by a practice peer during formal reviews.
    </p>
  `;
}

/**
 * Generates HTML string for Annual Performance Matrix Agreement & Achievement Report
 */
export function generatePerformanceMatrixHtml(
  plan: AnnualPerformancePlan,
  employee: User,
  managerName: string = 'Tariq Al Hammadi'
): string {
  const totalWeight = plan.goals.reduce((acc, g) => acc + g.weightagePct, 0);

  return `
    <div class="meta-box">
      <table style="width: 100%; border: none; margin: 0; background: transparent;">
        <tr style="border: none; background: transparent;">
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Employee / Specialist:</strong> ${employee.fullName} (${employee.employeeIdCode})<br>
            <strong>Practice Department:</strong> ${employee.departmentName}<br>
            <strong>Evaluation Year:</strong> ${plan.year} Annual Performance Matrix
          </td>
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Approving Manager:</strong> ${managerName}<br>
            <strong>Workflow Status:</strong> <span class="badge badge-teal">${plan.planStatus.replace(/_/g, ' ')}</span><br>
            <strong>Assessed Matrix Rating:</strong> <strong>${plan.assessedScore ? `${plan.assessedScore} / 100` : 'Pending Final Assessment'}</strong>
          </td>
        </tr>
      </table>
    </div>

    <h2>1. Approved Annual Key Performance Indicators & Achievement Matrix</h2>
    <table>
      <thead>
        <tr>
          <th>KPI / Deliverable Goal</th>
          <th style="width: 12%;">Weight</th>
          <th style="width: 15%;">Target Deliverables</th>
          <th style="width: 15%;">Actual Achieved</th>
          <th style="width: 15%;">SLA (Target / Act.)</th>
          <th style="width: 15%;" class="text-right">Manager Score</th>
        </tr>
      </thead>
      <tbody>
        ${plan.goals.map((goal) => `
          <tr>
            <td>
              <strong>${goal.title}</strong><br>
              <small style="color: #64748b;">${goal.category}</small>
              ${goal.achievementNarrative ? `<div style="font-size: 9pt; color: #334155; margin-top: 3pt;"><em>Achievement Note:</em> "${goal.achievementNarrative}"</div>` : ''}
            </td>
            <td><strong>${goal.weightagePct}%</strong></td>
            <td>${goal.targetDeliverableCount} engagements</td>
            <td><strong>${goal.actualAchievedCount} engagements</strong></td>
            <td>${goal.targetSlaHours}h / ${goal.actualAvgSlaHours}h</td>
            <td class="text-right font-bold">${goal.managerAssessmentScore} pts</td>
          </tr>
        `).join('')}
        <tr style="background-color: #f1f5f9; font-weight: bold;">
          <td>Total Allocated Weight</td>
          <td>${totalWeight}%</td>
          <td colspan="3"></td>
          <td class="text-right">${plan.assessedScore || 91} / 100</td>
        </tr>
      </tbody>
    </table>

    <h2>2. Manager Review & Approval Endorsement</h2>
    <div style="padding: 10px 14px; background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px;">
      <p style="margin: 0; font-style: italic;">
        "${plan.managerApprovalNotes || 'Annual performance deliverables approved. Goals align with sovereign audit quality mandates and ADGM statutory standards.'}"
      </p>
      <div style="font-size: 9pt; color: #64748b; margin-top: 6pt;">
        Approved by Practice Partner: ${managerName} • Last Updated: ${plan.lastUpdated}
      </div>
    </div>
  `;
}

/**
 * Generates HTML string for Firm-Wide Practice Performance & HR Intelligence Report
 */
export function generatePracticeAnalyticsReportHtml(
  companyInfo: any,
  departments: any[],
  appraisals: AppraisalRecord[],
  users: User[]
): string {
  const avgScore = (appraisals.reduce((acc, a) => acc + a.finalWeightedScore, 0) / (appraisals.length || 1)).toFixed(1);
  const exceedsCount = appraisals.filter((a) => a.performanceTier === 'Exceeds').length;
  const meetsCount = appraisals.filter((a) => a.performanceTier === 'Meets').length;
  const supportCount = appraisals.filter((a) => a.performanceTier === 'Needs_Support' || a.performanceTier === 'Underperforming').length;

  return `
    <div class="meta-box">
      <table style="width: 100%; border: none; margin: 0; background: transparent;">
        <tr style="border: none; background: transparent;">
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Practice Name:</strong> Paras Accounting & Auditing Advisory<br>
            <strong>Total Active Personnel:</strong> ${companyInfo.totalEmployees} Employees (SME Practice Structure)<br>
            <strong>Active Cycle:</strong> ${companyInfo.activeCycleName}
          </td>
          <td style="border: none; width: 50%; padding: 0;">
            <strong>Annual T&D Budget:</strong> AED ${companyInfo.annualTDBudgetAED.toLocaleString()}<br>
            <strong>Allocated T&D Budget:</strong> AED ${companyInfo.allocatedTDBudgetAED.toLocaleString()} (${Math.round((companyInfo.allocatedTDBudgetAED / companyInfo.annualTDBudgetAED) * 100)}%)<br>
            <strong>Statutory Reference:</strong> UAE Federal Decree-Law No. 33/2021
          </td>
        </tr>
      </table>
    </div>

    <h2>1. Practice Executive Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Figure</th>
          <th>Benchmark / Context</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Firm Average Performance Score</strong></td>
          <td><strong>${avgScore} / 100 pts</strong></td>
          <td>Above standard benchmark (80.0 pts)</td>
        </tr>
        <tr>
          <td><strong>High Performers (Exceeds Expectations)</strong></td>
          <td><strong>${exceedsCount} auditors</strong></td>
          <td>Eligible for discretionary merit awards</td>
        </tr>
        <tr>
          <td><strong>Meets Expectations (Standard Merit)</strong></td>
          <td><strong>${meetsCount} auditors</strong></td>
          <td>Solid professional delivery</td>
        </tr>
        <tr>
          <td><strong>Constructive Interventions (Tier 1 & Tier 2)</strong></td>
          <td><strong>${supportCount} auditors</strong></td>
          <td>Enrolled in firm-sponsored development mentorship</td>
        </tr>
      </tbody>
    </table>

    <h2>2. Departmental Performance & T&D Budget Utilization</h2>
    <table>
      <thead>
        <tr>
          <th>Practice Department</th>
          <th>Practice Lead</th>
          <th class="text-right">Staff Count</th>
          <th class="text-right">Annual T&D Budget</th>
          <th class="text-right">Budget Utilized</th>
        </tr>
      </thead>
      <tbody>
        ${departments.map((d) => `
          <tr>
            <td><strong>${d.name}</strong> (${d.code})</td>
            <td>${d.headName}</td>
            <td class="text-right">${d.employeeCount}</td>
            <td class="text-right">AED ${d.annualTDBudgetAED.toLocaleString()}</td>
            <td class="text-right"><strong>AED ${d.allocatedTDBudgetAED.toLocaleString()}</strong> (${Math.round((d.allocatedTDBudgetAED / d.annualTDBudgetAED) * 100)}%)</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

/**
 * Generates HTML string for Professional Certification & AED 15,000 Bonus Ledger
 */
export function generateCertificationReportHtml(
  certifications: ProfessionalCertification[],
  employee?: User
): string {
  const filtered = employee ? certifications.filter((c) => c.employeeId === employee.id) : certifications;
  const totalDisbursed = filtered
    .filter((c) => c.status === 'Completed_Verified' || c.status === 'Bonus_Disbursed')
    .reduce((acc, c) => acc + c.bonusAmountAED, 0);

  return `
    <div class="meta-box">
      <table style="width: 100%; border: none; margin: 0; background: transparent;">
        <tr style="border: none; background: transparent;">
          <td style="border: none; width: 60%; padding: 0;">
            <strong>Program Title:</strong> Chartered Excellence Incentive Program<br>
            <strong>Standard One-Time Bonus:</strong> AED 15,000.00 per completed certification<br>
            <strong>Eligible Credentials:</strong> ACA (ICAEW), ACCA, CPA, CTA, CFE, CFA
          </td>
          <td style="border: none; width: 40%; padding: 0;">
            <strong>Total Bonus Verified / Disbursed:</strong> <span class="badge badge-teal" style="font-size: 11pt;">AED ${totalDisbursed.toLocaleString()}</span><br>
            <strong>Auditors Enrolled:</strong> ${filtered.length} candidates
          </td>
        </tr>
      </table>
    </div>

    <h2>1. Professional Certification Track Records</h2>
    <table>
      <thead>
        <tr>
          <th>Auditor / Candidate</th>
          <th>Certification & Body</th>
          <th>Status</th>
          <th class="text-right">Incentive Entitlement</th>
          <th>Manager Endorsement</th>
        </tr>
      </thead>
      <tbody>
        ${filtered.map((cert) => `
          <tr>
            <td><strong>${cert.employeeName}</strong></td>
            <td>
              <strong>${cert.certificationName}</strong><br>
              <small style="color: #64748b;">${cert.issuingBody}</small>
            </td>
            <td>
              <span class="badge ${
                cert.status === 'Bonus_Disbursed' || cert.status === 'Completed_Verified'
                  ? 'badge-teal'
                  : cert.status === 'Manager_Approved'
                  ? 'badge-blue'
                  : 'badge-amber'
              }">
                ${cert.status.replace(/_/g, ' ')}
              </span>
            </td>
            <td class="text-right font-bold" style="color: #0f766e;">
              AED ${cert.bonusAmountAED.toLocaleString()}
            </td>
            <td style="font-size: 9pt; color: #475569;">
              ${cert.managerApprovalNotes || 'Awaiting partner review'}
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

/**
 * Generates an Enterprise Regulatory Audit Trail & Governance Log Report
 * Adheres to ISA 230 Audit Documentation & ADGM FSRA Standards
 */
export function generateAuditTrailReportHtml(
  logs: AuditLogEntry[],
  filtersApplied?: string
): string {
  const financialCount = logs.filter((l) => l.category === 'FINANCIAL_DISBURSEMENT').length;
  const governanceCount = logs.filter((l) => l.category === 'PERFORMANCE_GOVERNANCE').length;
  const complianceCount = logs.filter((l) => l.category === 'STATUTORY_COMPLIANCE').length;

  return `
    <div class="meta-box" style="border-left-color: #0f172a; background-color: #f8fafc;">
      <table style="width: 100%; border: none; margin: 0;">
        <tr>
          <td style="border: none; width: 60%; padding: 0;">
            <strong>Register:</strong> Administrative & Governance Audit Log Register<br>
            <strong>Regulatory Scope:</strong> ADGM FSRA Governance & UAE Decree-Law No. 33/2021<br>
            <strong>Audit Integrity:</strong> SHA-256 Cryptographic Tamper-Evident Hashing Active
          </td>
          <td style="border: none; width: 40%; padding: 0;">
            <strong>Total Actions Audited:</strong> ${logs.length} entries<br>
            <strong>Financial Actions:</strong> ${financialCount} • <strong>Performance:</strong> ${governanceCount}<br>
            <strong>Statutory Notices:</strong> ${complianceCount}
          </td>
        </tr>
      </table>
    </div>

    ${filtersApplied ? `<p style="font-size: 9pt; color: #64748b; margin-bottom: 12px;"><strong>Filter Scope:</strong> ${filtersApplied}</p>` : ''}

    <h2>1. Chronological Audit Trail & Action Journal</h2>
    <table>
      <thead>
        <tr>
          <th>Ref ID & Time (GST)</th>
          <th>Action & Category</th>
          <th>Authorized Actor</th>
          <th>Subject / Department</th>
          <th>Administrative Narrative & Impact</th>
          <th>Verification Token</th>
        </tr>
      </thead>
      <tbody>
        ${logs.map((log) => `
          <tr>
            <td style="font-family: monospace; font-size: 9pt;">
              <strong>${log.id}</strong><br>
              <span style="color: #64748b; font-size: 8pt;">${new Date(log.timestamp).toLocaleString('en-GB', { timeZone: 'Asia/Dubai' })} GST</span>
            </td>
            <td>
              <strong>${log.actionTitle}</strong><br>
              <span class="badge ${
                log.severity === 'FINANCIAL' 
                  ? 'badge-teal' 
                  : log.severity === 'CRITICAL' 
                  ? 'badge-rose' 
                  : log.severity === 'ACTION' 
                  ? 'badge-blue' 
                  : 'badge-amber'
              }">
                ${log.category.replace(/_/g, ' ')}
              </span>
            </td>
            <td>
              <strong>${log.actorName}</strong><br>
              <small style="color: #64748b;">${log.actorDesignation}</small>
            </td>
            <td>
              ${log.targetEmployeeName ? `<strong>${log.targetEmployeeName}</strong><br>` : ''}
              <small style="color: #64748b;">${log.targetDepartment || 'Firm-Wide'}</small>
            </td>
            <td style="font-size: 9pt;">
              ${log.details}
              ${log.newValue ? `<div style="margin-top: 4px; font-size: 8pt; color: #0f766e;"><strong>New Value:</strong> ${log.newValue}</div>` : ''}
            </td>
            <td style="font-family: monospace; font-size: 8pt; color: #475569;">
              ${log.verificationHash.slice(0, 16)}...<br>
              <small style="color: #94a3b8;">${log.ipAddress}</small>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <div style="margin-top: 25px; padding: 12px; background: #f1f5f9; border-radius: 6px; font-size: 8.5pt; color: #475569;">
      <strong>Regulatory Certification:</strong> This document represents an authentic extract from the Paras Accounting & Auditing Advisory tamper-evident audit journal. Generated for regulatory inspection pursuant to ISA 230 (Audit Documentation) and ADGM Financial Services Regulatory Authority (FSRA) supervisory accountability standards.
    </div>
  `;
}
