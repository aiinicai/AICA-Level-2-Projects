import React, { useState } from 'react';
import { 
  X, 
  Download, 
  Printer, 
  FileText, 
  FileSpreadsheet, 
  Copy, 
  Check, 
  ShieldCheck, 
  Share2,
  FileCode,
  CheckCircle2
} from 'lucide-react';
import { AuditReportData } from '../types';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: AuditReportData | null;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  report,
}) => {
  const [copiedMd, setCopiedMd] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isOpen || !report) return null;

  const triggerDownload = (blob: Blob, filename: string, label: string) => {
    try {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }, 200);
      setDownloadSuccess(label);
      setTimeout(() => setDownloadSuccess(null), 3000);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const getEntityNameClean = () => {
    return (report.summary.entityName || 'Entity').replace(/[^a-zA-Z0-9_-]/g, '_');
  };

  // 1. Generate Full HTML Document
  const generateHtmlDossier = (): string => {
    const title = `${report.summary.entityName || 'Entity'} - Statutory Audit & Note Proofreading Dossier`;
    const date = new Date(report.timestamp || Date.now()).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${title}</title>
  <style>
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .no-print { display: none !important; }
      .page-break { page-break-before: always; }
    }
    body {
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
      margin: 0;
      padding: 30px;
      background: #FFFFFF;
      color: #141414;
      line-height: 1.5;
      font-size: 13px;
    }
    .container { max-width: 1000px; margin: 0 auto; }
    .header-box {
      border: 2px solid #141414;
      padding: 20px;
      background: #F4F4F2;
      margin-bottom: 25px;
    }
    .badge {
      display: inline-block;
      padding: 3px 8px;
      background: #141414;
      color: #00FF00;
      font-family: monospace;
      font-size: 11px;
      font-weight: bold;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    h1 { margin: 0 0 5px 0; font-size: 20px; text-transform: uppercase; letter-spacing: -0.5px; }
    h2 { font-size: 15px; text-transform: uppercase; margin: 25px 0 10px 0; border-bottom: 2px solid #141414; padding-bottom: 4px; font-family: monospace; }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-top: 15px;
      font-family: monospace;
      font-size: 11px;
    }
    .meta-item { border: 1px solid #141414; padding: 8px; background: #FFFFFF; }
    .meta-label { color: #666; font-size: 10px; text-transform: uppercase; display: block; }
    .meta-val { font-weight: bold; font-size: 12px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
    th { background: #141414; color: #FFFFFF; text-align: left; padding: 8px 10px; font-family: monospace; font-size: 11px; text-transform: uppercase; }
    td { border: 1px solid #D1D0CC; padding: 8px 10px; vertical-align: top; }
    tr:nth-child(even) td { background: #FAFAF8; }
    .status-tag {
      font-family: monospace;
      font-weight: bold;
      padding: 2px 6px;
      font-size: 10px;
      text-transform: uppercase;
      border: 1px solid #141414;
      display: inline-block;
    }
    .status-complied { background: #D1E7DD; color: #0F5132; }
    .status-missing { background: #F8D7DA; color: #842029; }
    .status-partial { background: #FFF3CD; color: #664D03; }
    .risk-high { background: #842029; color: #FFF; font-weight: bold; font-family: monospace; padding: 2px 6px; }
    .risk-medium { background: #FFF3CD; color: #664D03; font-weight: bold; font-family: monospace; padding: 2px 6px; }
    .risk-low { background: #E2E3E5; color: #41464B; font-family: monospace; padding: 2px 6px; }
    .action-bar {
      margin-bottom: 20px;
      padding: 12px;
      background: #141414;
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .btn {
      background: #00FF00;
      color: #141414;
      font-weight: bold;
      padding: 8px 16px;
      font-family: monospace;
      text-decoration: none;
      cursor: pointer;
      border: none;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="action-bar no-print">
      <span><strong>STATUTORY AUDIT WORKING PAPER & NOTE PROOFREADING DOSSIER</strong></span>
      <button class="btn" onclick="window.print()">PRINT / SAVE AS PDF</button>
    </div>

    <div class="header-box">
      <span class="badge">ICAI & IND AS COMPLIANCE AUDIT WORKING PAPER</span>
      <h1>${report.summary.entityName || 'Audited Entity'}</h1>
      <p style="margin: 0; color: #555; font-style: italic;">
        Statutory Financial Statement Disclosure, Note-by-Note Proofreading & Schedule III Review
      </p>

      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Audit Score</span>
          <span class="meta-val">${report.summary.overallComplianceScore}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Reporting Period</span>
          <span class="meta-val">${report.summary.reportingPeriod || 'FY 2024-25'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Scale</span>
          <span class="meta-val">${report.summary.reportingScale || '₹ in Lakhs'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Audit Date</span>
          <span class="meta-val">${date}</span>
        </div>
      </div>
    </div>

    <h2>1. Executive Summary & Critical Risk Areas</h2>
    <p style="background: #F9F9F7; border: 1px solid #141414; padding: 12px; font-size: 13px;">
      ${report.summary.keyRiskAreas}
    </p>

    <h2>2. Mandatory Ind AS / AS Disclosures Matrix</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 15%;">Standard</th>
          <th style="width: 35%;">Requirement</th>
          <th style="width: 12%;">Status</th>
          <th style="width: 38%;">Auditor Observation</th>
        </tr>
      </thead>
      <tbody>
        ${report.part1Disclosures.map(d => `
          <tr>
            <td style="font-family: monospace; font-weight: bold;">${d.standard}</td>
            <td>${d.requirement}</td>
            <td><span class="status-tag ${d.status === 'Complied' ? 'status-complied' : d.status === 'Missing' ? 'status-missing' : 'status-partial'}">${d.status}</span></td>
            <td>${d.observation}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <div class="page-break"></div>

    <h2>3. Mathematical Castings & Internal Consistency Checks</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 25%;">Line Item</th>
          <th style="width: 15%;">Primary Statement</th>
          <th style="width: 15%;">Note Figure / Subtotal</th>
          <th style="width: 35%;">Variance / Conflict Explanation</th>
          <th style="width: 10%;">Risk</th>
        </tr>
      </thead>
      <tbody>
        ${report.part2Inconsistencies.map(i => `
          <tr>
            <td style="font-weight: bold;">${i.lineItem}</td>
            <td style="font-family: monospace;">${i.primaryFigure}</td>
            <td style="font-family: monospace;">${i.noteFigure}</td>
            <td>${i.discrepancy}</td>
            <td><span class="${i.riskLevel === 'High' ? 'risk-high' : i.riskLevel === 'Medium' ? 'risk-medium' : 'risk-low'}">${i.riskLevel}</span></td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    ${report.noteProofreading && report.noteProofreading.length > 0 ? `
      <h2>4. Comprehensive Note-by-Note Proofreading & Scrutiny</h2>
      <table>
        <thead>
          <tr>
            <th style="width: 12%;">Note No.</th>
            <th style="width: 22%;">Note Title</th>
            <th style="width: 14%;">Proofreading Status</th>
            <th style="width: 32%;">Auditor Observations & Footing</th>
            <th style="width: 20%;">Mandatory Clauses Checked</th>
          </tr>
        </thead>
        <tbody>
          ${report.noteProofreading.map(n => `
            <tr>
              <td style="font-family: monospace; font-weight: bold;">${n.noteNumber}</td>
              <td style="font-weight: bold;">${n.noteTitle}</td>
              <td><span class="status-tag ${n.proofreadingStatus === 'Complied' ? 'status-complied' : 'status-missing'}">${n.proofreadingStatus}</span></td>
              <td>
                ${n.observations}
                ${n.draftingOrArithmeticIssues ? `<div style="margin-top: 4px; color: #842029; font-weight: bold; font-size: 11px;">[Drafting Issue]: ${n.draftingOrArithmeticIssues}</div>` : ''}
              </td>
              <td style="font-size: 11px; color: #555;">${n.mandatoryClausesChecked}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    ` : ''}

    ${report.scheduleIIIGuidanceFindings && report.scheduleIIIGuidanceFindings.length > 0 ? `
      <h2>5. ICAI Schedule III Guidance Note & 2021 MCA Amendments</h2>
      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Clause / Subject</th>
            <th style="width: 20%;">Requirement</th>
            <th style="width: 12%;">Compliance</th>
            <th style="width: 30%;">Detailed Finding</th>
            <th style="width: 13%;">Reference</th>
          </tr>
        </thead>
        <tbody>
          ${report.scheduleIIIGuidanceFindings.map(s => `
            <tr>
              <td style="font-weight: bold;">${s.clause}</td>
              <td>${s.requirement}</td>
              <td><span class="status-tag ${s.complianceStatus === 'Complied' ? 'status-complied' : s.complianceStatus === 'Non-Compliant' ? 'status-missing' : 'status-partial'}">${s.complianceStatus}</span></td>
              <td>${s.detailedFinding}</td>
              <td style="font-family: monospace; font-size: 10px;">${s.guidanceNoteReference}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    ` : ''}

    <h2>6. Actionable CA Audit Recommendations</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 15%;">Priority</th>
          <th style="width: 20%;">Category</th>
          <th style="width: 15%;">Action For</th>
          <th style="width: 35%;">Recommended CA Action</th>
          <th style="width: 15%;">Ref</th>
        </tr>
      </thead>
      <tbody>
        ${report.part3Recommendations.map(r => `
          <tr>
            <td><span class="${r.priority === 'Immediate' ? 'risk-high' : 'risk-medium'}">${r.priority}</span></td>
            <td style="font-weight: bold;">${r.category}</td>
            <td style="font-family: monospace;">${r.actionFor}</td>
            <td>${r.recommendation}</td>
            <td style="font-family: monospace; font-size: 10px;">${r.statutoryReference || ''}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <div style="margin-top: 30px; padding: 15px; border: 1px solid #141414; background: #F4F4F2; font-family: monospace; font-size: 11px; text-align: center;">
      AUDIT WORKING PAPER GENERATED VIA STATUTORY AUDIT & IND AS QRB COMPLIANCE ENGINE • STRICT CA WORKING PAPER CONVENTIONS
    </div>
  </div>
</body>
</html>`;
  };

  // 1. Download HTML Dossier
  const handleDownloadHtml = () => {
    const htmlContent = generateHtmlDossier();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    triggerDownload(blob, `Audit_Dossier_${getEntityNameClean()}_${Date.now()}.html`, 'HTML Audit Dossier');
  };

  // 2. Download Microsoft Word (.doc)
  const handleDownloadWord = () => {
    const htmlContent = generateHtmlDossier();
    const wordContent = `\ufeff<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head><meta charset='utf-8'><title>Audit Report</title></head><body>${htmlContent}</body></html>`;
    const blob = new Blob([wordContent], { type: 'application/msword;charset=utf-8' });
    triggerDownload(blob, `Audit_Working_Paper_${getEntityNameClean()}_${Date.now()}.doc`, 'Microsoft Word Document');
  };

  // 3. Download Excel CSV Working Paper
  const handleDownloadCsv = () => {
    let csvContent = `\uFEFF=== STATUTORY AUDIT WORKING PAPER & NOTE PROOFREADING ===\n`;
    csvContent += `Entity: "${report.summary.entityName || 'Entity'}"\n`;
    csvContent += `Period: "${report.summary.reportingPeriod || 'FY 2024-25'}"\n`;
    csvContent += `Compliance Score: "${report.summary.overallComplianceScore}"\n`;
    csvContent += `Scale: "${report.summary.reportingScale || '₹ in Lakhs'}"\n\n`;

    csvContent += "=== PART 1: IND AS MANDATORY DISCLOSURES ===\n";
    csvContent += "Standard,Requirement,Status,Observation,Applicable Paragraph\n";
    report.part1Disclosures.forEach((d) => {
      csvContent += `"${(d.standard || '').replace(/"/g, '""')}","${(d.requirement || '').replace(/"/g, '""')}","${(d.status || '').replace(/"/g, '""')}","${(d.observation || '').replace(/"/g, '""')}","${(d.applicableParagraph || '').replace(/"/g, '""')}"\n`;
    });

    csvContent += "\n=== PART 2: NUMERICAL INCONSISTENCIES & CASTINGS ===\n";
    csvContent += "Line Item,Primary Statement Figure,Note Figure,Discrepancy,Risk Level\n";
    report.part2Inconsistencies.forEach((i) => {
      csvContent += `"${(i.lineItem || '').replace(/"/g, '""')}","${(i.primaryFigure || '').replace(/"/g, '""')}","${(i.noteFigure || '').replace(/"/g, '""')}","${(i.discrepancy || '').replace(/"/g, '""')}","${(i.riskLevel || '').replace(/"/g, '""')}"\n`;
    });

    if (report.noteProofreading && report.noteProofreading.length > 0) {
      csvContent += "\n=== PART 3: NOTE-BY-NOTE PROOFREADING & SCRUTINY ===\n";
      csvContent += "Note Number,Note Title,Proofreading Status,Observations,Mandatory Clauses Checked,Drafting Issues\n";
      report.noteProofreading.forEach((n) => {
        csvContent += `"${(n.noteNumber || '').replace(/"/g, '""')}","${(n.noteTitle || '').replace(/"/g, '""')}","${(n.proofreadingStatus || '').replace(/"/g, '""')}","${(n.observations || '').replace(/"/g, '""')}","${(n.mandatoryClausesChecked || '').replace(/"/g, '""')}","${(n.draftingOrArithmeticIssues || '').replace(/"/g, '""')}"\n`;
      });
    }

    if (report.scheduleIIIGuidanceFindings && report.scheduleIIIGuidanceFindings.length > 0) {
      csvContent += "\n=== PART 4: ICAI SCHEDULE III GUIDANCE NOTE & 2021 MCA AMENDMENTS ===\n";
      csvContent += "Clause,Requirement,Compliance Status,Detailed Finding,Guidance Reference\n";
      report.scheduleIIIGuidanceFindings.forEach((s) => {
        csvContent += `"${(s.clause || '').replace(/"/g, '""')}","${(s.requirement || '').replace(/"/g, '""')}","${(s.complianceStatus || '').replace(/"/g, '""')}","${(s.detailedFinding || '').replace(/"/g, '""')}","${(s.guidanceNoteReference || '').replace(/"/g, '""')}"\n`;
      });
    }

    csvContent += "\n=== PART 5: ACTIONABLE CA AUDIT RECOMMENDATIONS ===\n";
    csvContent += "Category,Priority,Action For,Recommendation,Statutory Reference\n";
    report.part3Recommendations.forEach((r) => {
      csvContent += `"${(r.category || '').replace(/"/g, '""')}","${(r.priority || '').replace(/"/g, '""')}","${(r.actionFor || '').replace(/"/g, '""')}","${(r.recommendation || '').replace(/"/g, '""')}","${(r.statutoryReference || '').replace(/"/g, '""')}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    triggerDownload(blob, `Audit_Working_Paper_${getEntityNameClean()}_${Date.now()}.csv`, 'Excel CSV Working Paper');
  };

  // 4. Download Full JSON Working Paper
  const handleDownloadJson = () => {
    const jsonStr = JSON.stringify(report, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
    triggerDownload(blob, `Audit_Report_${getEntityNameClean()}_${Date.now()}.json`, 'JSON Data Model');
  };

  // 5. Copy Full Markdown Report
  const handleCopyMarkdown = () => {
    let md = report.rawMarkdownReport || '';
    if (!md || md.length < 50) {
      md = `# STATUTORY AUDIT & NOTE PROOFREADING REPORT\n## Entity: ${report.summary.entityName || 'Audited Entity'}\n- Overall Score: ${report.summary.overallComplianceScore}\n- Total Discrepancies: ${report.summary.totalDiscrepancies}\n- Key Risks: ${report.summary.keyRiskAreas}\n\n### PART 1: IND AS DISCLOSURES\n` +
        report.part1Disclosures.map(d => `- **${d.standard}**: ${d.requirement} -> [${d.status}] ${d.observation}`).join('\n') +
        `\n\n### PART 2: NUMERICAL INCONSISTENCIES\n` +
        report.part2Inconsistencies.map(i => `- **${i.lineItem}**: Primary: ${i.primaryFigure} vs Note: ${i.noteFigure} | ${i.discrepancy} [${i.riskLevel}]`).join('\n') +
        `\n\n### PART 3: RECOMMENDATIONS\n` +
        report.part3Recommendations.map(r => `- [${r.priority}] **${r.category}** (For: ${r.actionFor}): ${r.recommendation}`).join('\n');
    }
    navigator.clipboard.writeText(md);
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 2500);
  };

  // 6. Open in New Tab for Direct Printing
  const handleOpenPrintTab = () => {
    const htmlContent = generateHtmlDossier();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white border-2 border-[#141414] shadow-dense max-w-2xl w-full overflow-hidden animate-scaleIn my-8">
        {/* Header */}
        <div className="bg-[#141414] text-white p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#00FF00] flex items-center justify-center text-[#141414] font-bold">
              <Download className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs sm:text-sm uppercase tracking-tight text-white font-mono">
                Export Statutory Working Papers & Note Scrutiny
              </h3>
              <p className="text-[10px] text-neutral-400 font-serif italic">
                Direct export to PDF/HTML, Word, Excel CSV, and complete audit dossiers
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 hover:bg-neutral-800 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Feedback Alert if file downloaded */}
        {downloadSuccess && (
          <div className="bg-green-100 border-b border-green-300 p-2.5 px-4 flex items-center space-x-2 text-green-900 text-xs font-mono font-bold">
            <CheckCircle2 className="w-4 h-4 text-green-700 shrink-0" />
            <span>DOWNLOAD SUCCESSFUL: {downloadSuccess} saved to your device.</span>
          </div>
        )}

        {/* Body Options */}
        <div className="p-5 space-y-3.5 bg-white">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* HTML Dossier / Printable Report */}
            <button
              id="export-html-dossier-btn"
              onClick={handleDownloadHtml}
              className="p-3.5 border-2 border-[#141414] bg-[#F9F9F7] hover:bg-[#E4E3E0] text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer group"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0 group-hover:bg-neutral-800">
                <FileCode className="w-4 h-4 text-[#00FF00]" />
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  Download HTML Dossier (.HTML)
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/80 block mt-0.5">
                  Complete self-contained printable report with all 5 audit matrices
                </span>
              </div>
            </button>

            {/* Microsoft Word Export */}
            <button
              id="export-word-doc-btn"
              onClick={handleDownloadWord}
              className="p-3.5 border-2 border-[#141414] bg-[#F9F9F7] hover:bg-[#E4E3E0] text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer group"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0 group-hover:bg-neutral-800">
                <FileText className="w-4 h-4 text-[#00FF00]" />
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  Download Word Report (.DOC)
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/80 block mt-0.5">
                  Formatted CA Audit Memorandum ready for editing in MS Word
                </span>
              </div>
            </button>

            {/* CSV Working Paper */}
            <button
              id="export-excel-csv-btn"
              onClick={handleDownloadCsv}
              className="p-3.5 border-2 border-[#141414] bg-[#F9F9F7] hover:bg-[#E4E3E0] text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer group"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0 group-hover:bg-neutral-800">
                <FileSpreadsheet className="w-4 h-4 text-[#00FF00]" />
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  Download Excel CSV (.CSV)
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/80 block mt-0.5">
                  Structured multi-section working papers for Excel audit files
                </span>
              </div>
            </button>

            {/* Print / Open In New Window */}
            <button
              id="export-print-window-btn"
              onClick={handleOpenPrintTab}
              className="p-3.5 border-2 border-[#141414] bg-[#F9F9F7] hover:bg-[#E4E3E0] text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer group"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0 group-hover:bg-neutral-800">
                <Printer className="w-4 h-4 text-[#00FF00]" />
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  Open Printable Window / PDF
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/80 block mt-0.5">
                  Opens clean printable report in new tab to Print or Save as PDF
                </span>
              </div>
            </button>

            {/* Markdown Copy */}
            <button
              id="export-copy-md-btn"
              onClick={handleCopyMarkdown}
              className="p-3.5 border border-[#141414] bg-[#F9F9F7] hover:bg-white text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0">
                {copiedMd ? <Check className="w-4 h-4 text-[#00FF00]" /> : <Copy className="w-4 h-4 text-white" />}
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  {copiedMd ? 'COPIED TO CLIPBOARD!' : 'Copy Markdown Report'}
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/70 block mt-0.5">
                  Full 5-part report formatted in standard Markdown
                </span>
              </div>
            </button>

            {/* JSON Export */}
            <button
              id="export-json-btn"
              onClick={handleDownloadJson}
              className="p-3.5 border border-[#141414] bg-[#F9F9F7] hover:bg-white text-left transition flex items-start space-x-2.5 shadow-dense-sm cursor-pointer"
            >
              <div className="w-9 h-9 bg-[#141414] text-white flex items-center justify-center shrink-0">
                <Share2 className="w-4 h-4 text-[#00FF00]" />
              </div>
              <div>
                <span className="text-[11px] font-mono font-bold uppercase text-[#141414] block">
                  Export Raw JSON (.JSON)
                </span>
                <span className="text-[10px] font-serif italic text-[#141414]/70 block mt-0.5">
                  Programmatic audit data model & verification schema
                </span>
              </div>
            </button>
          </div>

          <div className="p-2.5 bg-[#F9F9F7] border border-[#141414] text-[10px] text-[#141414] flex items-center space-x-2 font-mono uppercase">
            <ShieldCheck className="w-4 h-4 text-green-700 shrink-0" />
            <span>
              ALL EXPORTS ADHERE STRICTLY TO ICAI / IND AS REPORTING CONVENTIONS AND MCA SCHEDULE III GUIDELINES.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#E4E3E0] border-t border-[#141414] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-mono font-bold uppercase text-[#141414] bg-white hover:bg-neutral-100 border border-[#141414] transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

