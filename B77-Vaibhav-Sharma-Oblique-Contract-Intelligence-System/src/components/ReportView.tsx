import React, { useState } from 'react';
import { 
  Printer, 
  Download, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  Building2, 
  Coins, 
  Calendar, 
  ShieldAlert, 
  GitMerge, 
  HelpCircle,
  Clock,
  Sparkles,
  ExternalLink,
  Eye,
  Check,
  FileCheck2
} from 'lucide-react';
import { ContractDocument, Finding } from '../types/contract';

interface ReportViewProps {
  contract: ContractDocument;
}

export const ReportView: React.FC<ReportViewProps> = ({ contract }) => {
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [isPrinting, setIsPrinting] = useState(false);
  const [copiedNotification, setCopiedNotification] = useState(false);

  const redFindings = contract.findings.filter(f => f.attention === 'RED');
  const amberFindings = contract.findings.filter(f => f.attention === 'AMBER');
  const blueFindings = contract.findings.filter(f => f.attention === 'BLUE');

  const accountingFindings = contract.findings.filter(f => f.domains.includes('Accounting') || f.domains.includes('Financial Reporting'));
  const gstFindings = contract.findings.filter(f => f.domains.includes('GST'));
  const tdsFindings = contract.findings.filter(f => f.domains.includes('TDS'));
  const msmeFindings = contract.findings.filter(f => f.domains.includes('MSME'));

  /**
   * Generates a pristine standalone HTML representation of the A4 report
   * with embedded inline styles for flawless standalone printing or PDF conversion.
   */
  const generateStandaloneHTML = () => {
    const dateStr = new Date().toLocaleDateString('en-IN', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });

    const findingsHtml = contract.findings.map(f => {
      const isRed = f.attention === 'RED';
      const isAmber = f.attention === 'AMBER';
      const borderColor = isRed ? '#fecdd3' : isAmber ? '#fde68a' : '#bfdbfe';
      const bgColor = isRed ? '#fff1f2' : isAmber ? '#fffbeb' : '#eff6ff';
      const badgeBg = isRed ? '#e11d48' : isAmber ? '#d97706' : '#2563eb';
      const badgeColor = '#ffffff';

      return `
        <div style="margin-bottom: 14px; padding: 14px 16px; background-color: ${bgColor}; border: 1px solid ${borderColor}; border-radius: 8px; page-break-inside: avoid; break-inside: avoid;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="background: ${badgeBg}; color: ${badgeColor}; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;">${f.attention}</span>
              <strong style="color: #0f172a; font-size: 13px;">${f.id}: ${f.title}</strong>
            </div>
            <span style="font-family: monospace; font-size: 11px; color: #64748b; background: #ffffff; padding: 2px 8px; border-radius: 4px; border: 1px solid #cbd5e1;">Page ${f.source.page} • Cl ${f.source.clause}</span>
          </div>
          <p style="margin: 6px 0 4px 0; color: #1e293b; font-size: 12px; font-weight: 600; line-height: 1.4;">${f.whyItMatters}</p>
          <p style="margin: 0 0 8px 0; color: #475569; font-size: 11.5px; line-height: 1.5;">${f.potentialImpact}</p>
          
          <div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0; font-size: 11px; color: #334155;">
            <strong>Statutory Reference:</strong> ${f.frameworkToConfirm.join(' • ')}
          </div>
        </div>
      `;
    }).join('');

    const crossClauseHtml = contract.crossClauseInsights.length > 0 ? `
      <div style="margin-top: 24px; page-break-inside: avoid; break-inside: avoid;">
        <h3 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #581c87; border-bottom: 2px solid #e9d5ff; padding-bottom: 4px; margin-bottom: 12px;">
          4. Cross-Clause Synergies & Compound Risk Insights (Second-Pass Reasoning)
        </h3>
        ${contract.crossClauseInsights.map(cc => `
          <div style="margin-bottom: 12px; padding: 12px 14px; background-color: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px; page-break-inside: avoid;">
            <strong style="color: #581c87; font-size: 12.5px; display: block; margin-bottom: 4px;">${cc.title}</strong>
            <p style="margin: 0 0 6px 0; color: #334155; font-size: 11.5px; line-height: 1.45;">${cc.whyItMatters}</p>
            <div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; border: 1px solid #d8b4fe; font-size: 11px; color: #6b21a8;">
              <strong>CA Remediation Strategy:</strong> ${cc.recommendedAction}
            </div>
          </div>
        `).join('')}
      </div>
    ` : '';

    const evidenceHtml = Array.from(new Set(contract.findings.flatMap(f => f.evidenceRequired))).map(doc => `
      <div style="display: flex; align-items: flex-start; gap: 6px; background: #f8fafc; padding: 8px 10px; border-radius: 6px; border: 1px solid #e2e8f0; font-size: 11px; color: #334155;">
        <span style="color: #059669; font-weight: bold;">✓</span>
        <span>${doc}</span>
      </div>
    `).join('');

    const questionsHtml = Array.from(new Set(contract.findings.flatMap(f => f.managementQuestions))).map((q, idx) => `
      <div style="display: flex; align-items: flex-start; gap: 8px; background: #fffbeb; padding: 8px 10px; border-radius: 6px; border: 1px solid #fef3c7; font-size: 11px; color: #92400e; margin-bottom: 6px;">
        <strong>Q${idx + 1}.</strong>
        <span>${q}</span>
      </div>
    `).join('');

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>OBLIQUE Impact Working Paper - ${contract.identity.title}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 15mm 12mm 15mm 12mm;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      margin: 0;
      padding: 24px;
      font-size: 11.5px;
      line-height: 1.45;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .header-rule {
      border-bottom: 2px solid #0f172a;
      padding-bottom: 12px;
      margin-bottom: 18px;
    }
    .meta-tag {
      font-size: 9.5px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #64748b;
      font-weight: 700;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .grid-4 {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr 1fr;
      gap: 8px;
    }
    .card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 12px;
    }
    .section-title {
      font-size: 12.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #0f172a;
      border-bottom: 1.5px solid #cbd5e1;
      padding-bottom: 4px;
      margin-top: 20px;
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
    }
    .avoid-break {
      page-break-inside: avoid;
      break-inside: avoid;
    }
    @media print {
      body { padding: 0; }
    }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header-rule">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span class="meta-tag">OBLIQUE • CONTRACT INTELLIGENCE SYSTEM • BY CA VAIBHAV SHARMA</span>
      <span class="meta-tag">Working Paper Date: ${dateStr}</span>
    </div>
    <h1 style="margin: 0 0 4px 0; font-size: 20px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">
      COMMERCIAL CONTRACT IMPACT & AUDIT WORKING PAPER
    </h1>
    <div style="font-size: 14px; font-weight: 700; color: #2563eb; margin-bottom: 8px;">
      ${contract.identity.title}
    </div>
    <div style="display: flex; gap: 16px; font-size: 11px; color: #475569;">
      <span><strong>Contract Ref:</strong> ${contract.identity.contractNumber || 'N/A'}</span>
      <span>•</span>
      <span><strong>Statutory Framework:</strong> ${contract.selectedFramework}</span>
      <span>•</span>
      <span><strong>Parties:</strong> ${contract.parties.map(p => `${p.name} (${p.role})`).join(' & ')}</span>
    </div>
  </div>

  <!-- 1. Executive Summary -->
  <div class="avoid-break" style="margin-bottom: 16px;">
    <div class="section-title">
      <span>1. Executive Summary & Review Snapshot</span>
      <span style="font-family: monospace; font-size: 11px; color: #64748b;">${contract.findings.length} Total Findings</span>
    </div>
    <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 14px; font-size: 11.5px; line-height: 1.5; color: #1e293b; white-space: pre-line;">
${contract.executiveSummary}
    </div>
  </div>

  <!-- 2. Commercial Terms -->
  <div class="avoid-break" style="margin-bottom: 16px;">
    <div class="section-title">
      <span>2. Contract Commercial Snapshot</span>
    </div>
    <div class="grid-4">
      <div class="card">
        <span style="display: block; font-size: 9px; text-transform: uppercase; font-weight: bold; color: #64748b;">Contract Value</span>
        <strong style="font-size: 13px; color: #0f172a;">${contract.commercialTerms.contractValue}</strong>
      </div>
      <div class="card">
        <span style="display: block; font-size: 9px; text-transform: uppercase; font-weight: bold; color: #64748b;">Credit Period</span>
        <strong style="font-size: 13px; color: ${contract.commercialTerms.creditPeriodDays && contract.commercialTerms.creditPeriodDays > 45 ? '#e11d48' : '#0f172a'};">
          ${contract.commercialTerms.creditPeriodDays || 'N/A'} Days
        </strong>
      </div>
      <div class="card">
        <span style="display: block; font-size: 9px; text-transform: uppercase; font-weight: bold; color: #64748b;">Retention Money</span>
        <strong style="font-size: 13px; color: #b45309;">${contract.commercialTerms.retentionMoney?.percentage || '10%'} (${contract.commercialTerms.retentionMoney?.amount || 'N/A'})</strong>
      </div>
      <div class="card">
        <span style="display: block; font-size: 9px; text-transform: uppercase; font-weight: bold; color: #64748b;">Mobilization Advance</span>
        <strong style="font-size: 13px; color: #0f172a;">${contract.commercialTerms.advances?.percentage || '15%'}</strong>
      </div>
    </div>
  </div>

  <!-- 3. Key Findings -->
  <div style="margin-bottom: 16px;">
    <div class="section-title">
      <span>3. Detailed Statutory & Accounting Findings</span>
      <span style="font-size: 10.5px; color: #e11d48;">${redFindings.length} RED • ${amberFindings.length} AMBER</span>
    </div>
    ${findingsHtml}
  </div>

  <!-- 4. Cross Clause Reasoning -->
  ${crossClauseHtml}

  <!-- 5. Documentary Evidence Checklist -->
  <div class="avoid-break" style="margin-top: 20px; margin-bottom: 16px;">
    <div class="section-title">
      <span>5. Master Documentary Evidence Checklist</span>
    </div>
    <div class="grid-2">
      ${evidenceHtml}
    </div>
  </div>

  <!-- 6. Questions for Management -->
  <div class="avoid-break" style="margin-bottom: 16px;">
    <div class="section-title">
      <span>6. Critical Questions for CFO & Accounts Team</span>
    </div>
    <div>
      ${questionsHtml}
    </div>
  </div>

  <!-- 7. Sign-off Blocks -->
  <div class="avoid-break" style="margin-top: 28px; padding-top: 14px; border-top: 2px solid #0f172a;">
    <div class="grid-2" style="gap: 32px;">
      <div>
        <strong style="display: block; font-size: 11px; color: #0f172a; margin-bottom: 2px;">Prepared & Reviewed By:</strong>
        <div style="font-size: 11px; color: #475569; font-weight: 600;">Chartered Accountant / Statutory Auditor</div>
        <div style="height: 36px; border-bottom: 1px dashed #94a3b8; margin-top: 12px;"></div>
        <div style="font-size: 9.5px; color: #64748b; margin-top: 4px;">Membership No. / Firm Registration No. / Date</div>
      </div>
      <div>
        <strong style="display: block; font-size: 11px; color: #0f172a; margin-bottom: 2px;">Client & Management Acknowledgment:</strong>
        <div style="font-size: 11px; color: #475569; font-weight: 600;">Chief Financial Officer / Authorized Signatory</div>
        <div style="height: 36px; border-bottom: 1px dashed #94a3b8; margin-top: 12px;"></div>
        <div style="font-size: 9.5px; color: #64748b; margin-top: 4px;">Name, Designation & Date</div>
      </div>
    </div>
  </div>

  <!-- Disclaimer Notice -->
  <div class="avoid-break" style="margin-top: 20px; padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 9.5px; color: #64748b; line-height: 1.4;">
    <strong>STATUTORY NOTICE:</strong> This document represents an AI-assisted professional impact analysis generated by OBLIQUE (Contract Intelligence System). The findings and suggested considerations must be independently evaluated and verified against original source documents, statutory provisions (Ind AS, Income Tax Act, CGST Act, MSMED Act, Companies Act 2013), and specific business context prior to final accounting or tax treatment.
  </div>

  <script>
    // Auto-trigger print if launched in dedicated print window
    window.addEventListener('DOMContentLoaded', () => {
      if (window.location.hash === '#print') {
        setTimeout(() => {
          window.print();
        }, 500);
      }
    });
  </script>
</body>
</html>`;
  };

  /**
   * Primary Print / Save PDF Handler:
   * Uses an isolated hidden iframe with complete standalone styling and print triggers,
   * guaranteeing that sandboxed parent windows or multi-pane scroll issues do not block printing.
   */
  const handlePrint = () => {
    setIsPrinting(true);

    try {
      // 1. Check if a hidden print iframe already exists, else create it
      let iframe = document.getElementById('oblique-print-frame') as HTMLIFrameElement;
      if (!iframe) {
        iframe = document.createElement('iframe');
        iframe.id = 'oblique-print-frame';
        iframe.style.position = 'fixed';
        iframe.style.right = '0';
        iframe.style.bottom = '0';
        iframe.style.width = '0';
        iframe.style.height = '0';
        iframe.style.border = '0';
        document.body.appendChild(iframe);
      }

      const htmlContent = generateStandaloneHTML();
      const doc = iframe.contentWindow?.document || iframe.contentDocument;

      if (doc) {
        doc.open();
        doc.write(htmlContent);
        doc.close();

        // Give styles a moment to paint in the iframe, then trigger print
        setTimeout(() => {
          iframe.contentWindow?.focus();
          iframe.contentWindow?.print();
          setIsPrinting(false);
        }, 400);
      } else {
        // Fallback to window.print()
        window.print();
        setIsPrinting(false);
      }
    } catch (e) {
      console.warn('Iframe print delegation failed, falling back to window.print():', e);
      window.print();
      setIsPrinting(false);
    }
  };

  /**
   * Direct Standalone HTML/PDF-Ready Working Paper Download
   */
  const handleDownloadStandaloneHTML = () => {
    const htmlContent = generateStandaloneHTML();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.href = url;
    downloadAnchor.download = `OBLIQUE_Working_Paper_${contract.identity.contractNumber || 'Analysis'}.html`;
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(contract, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `Contract_Impact_Report_${contract.identity.contractNumber || 'Analysis'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleExportCSV = () => {
    const headers = ["ID", "Title", "Attention", "Domains", "Page", "Clause", "Why It Matters", "Potential Impact", "Status"];
    const rows = contract.findings.map(f => [
      `"${f.id}"`,
      `"${f.title.replace(/"/g, '""')}"`,
      `"${f.attention}"`,
      `"${f.domains.join(', ')}"`,
      `"${f.source.page}"`,
      `"${f.source.clause}"`,
      `"${f.whyItMatters.replace(/"/g, '""')}"`,
      `"${f.potentialImpact.replace(/"/g, '""')}"`,
      `"${f.status}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", encodeURI(csvContent));
    downloadAnchor.setAttribute("download", `Findings_Matrix_${contract.identity.contractNumber || 'Export'}.csv`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Action Header (Hidden during actual print) */}
      <div className="print:hidden bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
            <h2 className="text-base font-bold text-slate-900">CA Professional Impact & Working Paper Report</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Standardized for audit documentation, board presentation, and tax working papers (Ind AS / AS / GST / MSME).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* A4 Visualizer Toggle */}
          <button
            onClick={() => setIsPreviewMode(!isPreviewMode)}
            className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              isPreviewMode 
                ? 'bg-blue-50 text-blue-700 border-blue-300' 
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300'
            }`}
            title="Toggle exact A4 sheet paper visualizer"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>{isPreviewMode ? 'Exit A4 Sheet View' : 'A4 Paper Preview'}</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>

          <button
            onClick={handleDownloadStandaloneHTML}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition"
            title="Download self-contained offline working paper with embedded print styles"
          >
            <FileCheck2 className="w-3.5 h-3.5 text-blue-600" />
            <span>Save Working Paper (HTML/PDF)</span>
          </button>

          <button
            onClick={handlePrint}
            disabled={isPrinting}
            className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition disabled:opacity-50 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>{isPrinting ? 'Preparing PDF...' : 'Print / Save PDF'}</span>
          </button>
        </div>
      </div>

      {/* A4 Sheet Guide Banner when Visualizer is Active */}
      {isPreviewMode && (
        <div className="print:hidden bg-blue-50 border border-blue-200 rounded-xl p-3.5 text-xs text-blue-900 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <strong>A4 Sheet Visualizer:</strong> Displaying exact page boundaries, margin alignments, and typography scale matching physical print output.
            </span>
          </div>
          <button
            onClick={handlePrint}
            className="px-2.5 py-1 rounded bg-blue-600 text-white font-semibold text-[11px] hover:bg-blue-700 transition shrink-0"
          >
            Send to Printer
          </button>
        </div>
      )}

      {/* Printable Report Canvas */}
      <div 
        id="oblique-printable-report"
        className={`bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-10 space-y-8 text-xs text-slate-800 printable-report-canvas print:border-none print:shadow-none print:p-0 ${
          isPreviewMode ? 'max-w-[210mm] mx-auto border-2 border-slate-400 shadow-xl bg-white min-h-[297mm]' : ''
        }`}
      >
        {/* Cover Header */}
        <div className="border-b-2 border-slate-900 pb-5 space-y-2 page-break-avoid">
          <div className="flex items-center justify-between text-slate-500 uppercase tracking-widest text-[9.5px] font-bold">
            <span>OBLIQUE • CONTRACT INTELLIGENCE SYSTEM • BY CA VAIBHAV SHARMA</span>
            <span>Generated: {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}</span>
          </div>

          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
            COMMERCIAL CONTRACT IMPACT ANALYSIS REPORT
          </h1>
          <p className="text-sm font-bold text-blue-900">
            {contract.identity.title}
          </p>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 pt-1">
            <span><strong>Contract Ref:</strong> {contract.identity.contractNumber || 'N/A'}</span>
            <span>•</span>
            <span><strong>Framework:</strong> {contract.selectedFramework}</span>
            <span>•</span>
            <span><strong>Parties:</strong> {contract.parties.map(p => `${p.name} (${p.role})`).join(' & ')}</span>
          </div>
        </div>

        {/* Section 1: Executive Summary */}
        <div className="space-y-2.5 report-section page-break-avoid">
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1 flex items-center justify-between">
            <span>1. Executive Summary & Review Snapshot</span>
            <span className="font-mono text-slate-500 text-[11px]">{contract.findings.length} Total Findings</span>
          </h3>
          <p className="text-slate-700 bg-slate-50 p-4 rounded-lg border border-slate-200 leading-relaxed whitespace-pre-line font-medium text-xs">
            {contract.executiveSummary}
          </p>
        </div>

        {/* Section 2: Key Commercial Terms */}
        <div className="space-y-2.5 report-section page-break-avoid">
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
            2. Contract Snapshot & Key Commercial Terms
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[9.5px] uppercase font-bold">Total Contract Value</span>
              <span className="font-bold text-slate-900 text-sm">{contract.commercialTerms.contractValue}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[9.5px] uppercase font-bold">Credit Period</span>
              <span className={`font-bold text-sm ${contract.commercialTerms.creditPeriodDays && contract.commercialTerms.creditPeriodDays > 45 ? 'text-rose-700' : 'text-slate-900'}`}>
                {contract.commercialTerms.creditPeriodDays || 'N/A'} Days
              </span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[9.5px] uppercase font-bold">Retention Money</span>
              <span className="font-bold text-amber-800 text-sm">
                {contract.commercialTerms.retentionMoney?.percentage || '10%'} ({contract.commercialTerms.retentionMoney?.amount || 'N/A'})
              </span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[9.5px] uppercase font-bold">Mobilization Advance</span>
              <span className="font-bold text-slate-900 text-sm">
                {contract.commercialTerms.advances?.percentage || '15%'} ({contract.commercialTerms.advances?.amount || 'N/A'})
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: High Attention Findings (RED) */}
        {redFindings.length > 0 && (
          <div className="space-y-3 report-section">
            <h3 className="text-xs font-black uppercase tracking-wider text-rose-900 border-b border-rose-200 pb-1 flex items-center justify-between">
              <span>3. High Attention Priority Issues (RED)</span>
              <span className="font-mono text-rose-700">{redFindings.length} Critical Points</span>
            </h3>
            <div className="space-y-3">
              {redFindings.map(f => (
                <div key={f.id} className="p-4 rounded-lg bg-rose-50/50 border border-rose-200 space-y-2 page-break-avoid">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs">
                      {f.id}: {f.title}
                    </span>
                    <span className="font-mono text-slate-500 text-[10px] bg-white px-2 py-0.5 rounded border border-slate-200">
                      Page {f.source.page}, Clause {f.source.clause}
                    </span>
                  </div>
                  <p className="text-rose-950 font-medium">{f.whyItMatters}</p>
                  <p className="text-slate-700 text-[11px] leading-relaxed">{f.potentialImpact}</p>
                  <div className="pt-1 text-[10.5px] text-slate-600 bg-white p-2 rounded border border-rose-100">
                    <strong>Statutory Framework:</strong> {f.frameworkToConfirm.join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 4: Accounting & Ind AS Implications */}
        {accountingFindings.length > 0 && (
          <div className="space-y-3 report-section">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
              4. Accounting & Financial Reporting Implications (Ind AS / AS)
            </h3>
            <div className="space-y-3">
              {accountingFindings.map(f => (
                <div key={f.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 page-break-avoid">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{f.title}</span>
                    <span className="text-slate-500 font-mono text-[10px]">Cl {f.source.clause}</span>
                  </div>
                  <p className="text-slate-700">{f.whyItMatters}</p>
                  <div className="pt-1 text-[11px] text-slate-600">
                    <strong>Audit Step:</strong> {f.whatToVerify[0]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 5: GST & Tax Implications */}
        {(gstFindings.length > 0 || tdsFindings.length > 0) && (
          <div className="space-y-3 report-section">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
              5. Indirect Tax (GST) & Direct Tax (TDS) Considerations
            </h3>
            <div className="space-y-3">
              {[...gstFindings, ...tdsFindings].map(f => (
                <div key={f.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 page-break-avoid">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{f.title}</span>
                    <span className="text-blue-700 font-semibold text-[10px]">{f.domains.join(', ')}</span>
                  </div>
                  <p className="text-slate-700">{f.potentialImpact}</p>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Statute: {f.frameworkToConfirm.join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 6: MSME & Section 43B(h) */}
        {msmeFindings.length > 0 && (
          <div className="space-y-3 report-section">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
              6. MSME Compliance & Section 43B(h) Evaluation
            </h3>
            <div className="space-y-3">
              {msmeFindings.map(f => (
                <div key={f.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 page-break-avoid">
                  <span className="font-bold text-slate-900 block">{f.title}</span>
                  <p className="text-slate-700">{f.whyItMatters}</p>
                  <p className="text-slate-600 text-[11px]">{f.potentialImpact}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 7: Cross Clause Reasoning Pass */}
        {contract.crossClauseInsights.length > 0 && (
          <div className="space-y-3 report-section">
            <h3 className="text-xs font-black uppercase tracking-wider text-purple-900 border-b border-purple-200 pb-1">
              7. Cross-Clause Synergies & Compound Risk Insights
            </h3>
            <div className="space-y-3">
              {contract.crossClauseInsights.map(insight => (
                <div key={insight.id} className="p-4 rounded-lg bg-purple-50/40 border border-purple-200 space-y-2 page-break-avoid">
                  <span className="font-bold text-purple-950 block text-xs">{insight.title}</span>
                  <p className="text-slate-700 text-xs">{insight.whyItMatters}</p>
                  <div className="p-2 bg-white rounded border border-purple-100 text-[11px] text-purple-900">
                    <strong>CA Remediation Strategy:</strong> {insight.recommendedAction}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 8: Targeted Evidence Checklist */}
        <div className="space-y-3 report-section page-break-avoid">
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
            8. Master Documentary Evidence Checklist
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Array.from(new Set(contract.findings.flatMap(f => f.evidenceRequired))).map((doc, idx) => (
              <div key={idx} className="flex items-start space-x-2 bg-slate-50 p-2.5 rounded border border-slate-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span className="text-slate-700 text-xs">{doc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Section 9: Questionnaire for Management */}
        <div className="space-y-3 report-section page-break-avoid">
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-1">
            9. Questionnaire for Client Management / CFO
          </h3>
          <div className="space-y-2">
            {Array.from(new Set(contract.findings.flatMap(f => f.managementQuestions))).map((q, idx) => (
              <div key={idx} className="flex items-start space-x-2 bg-amber-50/40 p-2.5 rounded border border-amber-200">
                <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                <span className="text-slate-800 font-medium text-xs">{q}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Section 10: Sign-Off Box */}
        <div className="pt-6 border-t-2 border-slate-900 grid grid-cols-1 sm:grid-cols-2 gap-8 text-xs page-break-avoid sign-off-section">
          <div className="space-y-3">
            <div>
              <span className="block font-bold text-slate-900">Reviewed By (Chartered Accountant / Auditor):</span>
              <div className="h-10 border-b border-slate-300 mt-2" />
              <span className="text-slate-500 text-[10px]">Membership No. / FRN / Sign & Date</span>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <span className="block font-bold text-slate-900">Client / CFO Acknowledgment:</span>
              <div className="h-10 border-b border-slate-300 mt-2" />
              <span className="text-slate-500 text-[10px]">Name & Designation / Sign & Stamp</span>
            </div>
          </div>
        </div>

        {/* Statutory Disclaimer */}
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-[10px] text-slate-500 leading-relaxed page-break-avoid">
          <strong>STATUTORY NOTICE:</strong> This document represents an AI-assisted professional impact analysis generated by OBLIQUE (Contract Intelligence System). The findings and suggested considerations must be independently evaluated and verified against original source documents, statutory provisions (Ind AS, Income Tax Act, CGST Act, MSMED Act, Companies Act 2013), and specific business context prior to final accounting or tax treatment.
        </div>
      </div>
    </div>
  );
};
