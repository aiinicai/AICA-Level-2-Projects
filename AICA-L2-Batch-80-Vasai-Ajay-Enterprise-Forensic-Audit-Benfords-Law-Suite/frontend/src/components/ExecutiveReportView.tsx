import React, { useState } from 'react';
import {
  FileText, Download, ShieldCheck, CheckCircle2,
  FileSpreadsheet, FileCode, Hash, Printer, Lock
} from 'lucide-react';
import { BenfordSuiteResponse, ForensicTestsResponse, IngestionResult } from '../types';

interface ExecutiveReportViewProps {
  benfordData: BenfordSuiteResponse | null;
  forensicsData: ForensicTestsResponse | null;
  ingestionResult: IngestionResult | null;
  auditorName: string;
  organizationFiduciary: string;
}

export const ExecutiveReportView: React.FC<ExecutiveReportViewProps> = ({
  benfordData,
  forensicsData,
  ingestionResult,
  auditorName,
  organizationFiduciary
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const handleDownloadPdf = () => {
    setDownloadingFormat('pdf');
    window.open('/api/report/pdf', '_blank');
    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  const handleDownloadExcel = () => {
    setDownloadingFormat('excel');
    window.open('/api/report/excel', '_blank');
    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  const handleDownloadWord = () => {
    setDownloadingFormat('docx');
    window.open('/api/report/docx', '_blank');
    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  const handleDownloadJson = async () => {
    try {
      const res = await fetch('/api/audit/certificate');
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `DPDP_Forensic_Certificate_${Date.now()}.json`;
      a.click();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-4">
      {/* Header & Export Action Suite */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-400" />
            Executive Forensic Audit Dossier &amp; Multi-Format Exports
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Courtroom &amp; Audit Committee Grade Forensic Findings &bull; PDF &bull; Detailed Excel Workbook &bull; Word Report &bull; JSON Certificate
          </p>
        </div>

        {/* 4 Multi-Format Export Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingFormat !== null}
            className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white text-xs font-bold shadow-lg shadow-rose-500/20 transition-all flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloadingFormat === 'pdf' ? 'Exporting...' : 'PDF Report'}</span>
          </button>

          <button
            onClick={handleDownloadExcel}
            disabled={downloadingFormat !== null}
            className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-xs font-bold shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{downloadingFormat === 'excel' ? 'Exporting...' : 'Detailed Excel (.xlsx)'}</span>
          </button>

          <button
            onClick={handleDownloadWord}
            disabled={downloadingFormat !== null}
            className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xs font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{downloadingFormat === 'docx' ? 'Exporting...' : 'Word Dossier (.docx)'}</span>
          </button>

          <button
            onClick={handleDownloadJson}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-all shadow"
          >
            <Hash className="w-3.5 h-3.5 text-slate-400" />
            <span>JSON Certificate</span>
          </button>
        </div>
      </div>

      {/* Printable Report Sheet Mockup */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-8 sm:p-10 space-y-8 shadow-2xl">
        {/* Dossier Header */}
        <div className="text-center border-b border-slate-800 pb-6 space-y-1">
          <span className="text-[11px] font-bold text-brand-400 uppercase tracking-widest block">
            CONFIDENTIAL FINANCIAL FORENSIC DOSSIER
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            ENTERPRISE FORENSIC AUDIT &amp; BENFORD'S LAW SUITE
          </h1>
          <p className="text-xs text-slate-400">
            Compliant with the Indian Digital Personal Data Protection (DPDP) Act, 2023
          </p>
        </div>

        {/* Legal Disclaimer Box */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 leading-relaxed italic">
          <b>Statutory Notice &amp; Disclaimer:</b> This dossier is compiled for analytical risk assessment and internal forensic evaluation.
          Statistical deviations from Benford's Law or identified anomaly flags represent investigative focal points requiring independent
          verification by certified auditors. Processing adheres to Sections 4 &amp; 7 of the Indian DPDP Act, 2023.
        </div>

        {/* Key Findings Summary Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-400">Auditing Fiduciary:</span>
            <div className="text-white font-bold">{organizationFiduciary || 'Declared Entity'}</div>
            <span className="text-slate-500 text-[10px]">Lead: {auditorName}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-400">Nigrini MAD Rating:</span>
            <div className="text-brand-400 font-bold font-mono">
              {benfordData?.overall_summary?.conformity_rating || 'Pending Analysis'}
            </div>
            <span className="text-slate-500 text-[10px]">
              MAD = {benfordData?.overall_summary?.mad_f2d?.toFixed(5) || '-'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-slate-400">Dataset Cryptographic Fingerprint:</span>
            <div className="text-emerald-400 font-mono text-[10px] truncate">
              {ingestionResult?.dataset_hash || 'SHA-256 Fingerprint'}
            </div>
            <span className="text-slate-500 text-[10px]">
              {ingestionResult?.row_count?.toLocaleString() || 0} Ingested Records
            </span>
          </div>
        </div>

        {/* DPDP Compliance Attestation */}
        <div className="p-5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-3">
          <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-white block">
              Indian DPDP Act, 2023 Statutory Compliance Attestation
            </span>
            <p className="text-slate-300">
              1. <b>Purpose Limitation:</b> Audit records processed strictly under Section 4 &amp; 7 statutory mandates.<br/>
              2. <b>Data Minimisation:</b> Aadhaar verified via Verhoeff checksum; PAN/GSTIN structures validated and salted HMAC-SHA256 pseudonymized.<br/>
              3. <b>Air-Gap Execution:</b> Processing executed in-memory with zero cloud egress.<br/>
              4. <b>Audit Trail:</b> Every analytical action logged to an immutable SHA-256 hash chained journal.
            </p>
          </div>
        </div>

        {/* Auditor Sign-off Placeholder */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 pt-8 border-t border-slate-800 text-xs">
          <div className="text-center p-4 border border-dashed border-slate-700 rounded-xl">
            <span className="text-slate-400 block mb-8 font-medium">LEAD FORENSIC AUDITOR SIGNATURE</span>
            <div className="text-white font-bold font-mono">{auditorName}</div>
            <span className="text-slate-500 text-[10px]">Chartered Accountant / Certified Fraud Examiner</span>
          </div>

          <div className="text-center p-4 border border-dashed border-slate-700 rounded-xl">
            <span className="text-slate-400 block mb-8 font-medium">DATA FIDUCIARY COMPLIANCE OFFICER</span>
            <div className="text-white font-bold font-mono">{organizationFiduciary}</div>
            <span className="text-slate-500 text-[10px]">Indian DPDP Act, 2023 Governance Officer</span>
          </div>
        </div>
      </div>
    </div>
  );
};
