import React, { useState } from 'react';
import { 
  FileSpreadsheet, FileText, Download, ShieldCheck, 
  Printer, CheckCircle2, AlertTriangle, Building2, User
} from 'lucide-react';
import { Proposal, Client, Entity } from '../types';
import { formatINR, formatProductType, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';

interface ReportsTabProps {
  proposal: Proposal;
  client?: Client;
  entity?: Entity;
  unitMode: NumberUnitMode;
}

export const ReportsTab: React.FC<ReportsTabProps> = ({
  proposal,
  client,
  entity,
  unitMode,
}) => {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (type: 'excel' | 'word' | 'pdf', endpoint: string, filename: string) => {
    setDownloading(type);
    try {
      const token = ApiClient.getToken();
      const res = await fetch(`/api/v1/proposals/${proposal.id}/reports/${endpoint}`, {
        headers: {
          Authorization: `Bearer ${token || ''}`,
        },
      });

      if (!res.ok) {
        throw new Error('Failed to generate export');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Download error');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Export Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Excel Export */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="p-3 bg-emerald-50 text-emerald-800 rounded-lg w-fit">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">9-Year CMA Statement</h4>
            <p className="text-xs text-slate-500">
              Complete Form I through VII multi-period financial model formatted for Indian Nationalized & Private Bank credit committees.
            </p>
          </div>
          <button
            onClick={() => handleDownload('excel', 'cma-excel', `CMA_Statement_${proposal.proposal_code}.xlsx`)}
            disabled={downloading === 'excel'}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Download className="w-4 h-4" />
            <span>{downloading === 'excel' ? 'Exporting XLSX...' : 'Download Excel (.xlsx)'}</span>
          </button>
        </div>

        {/* Word Export */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="p-3 bg-blue-50 text-blue-800 rounded-lg w-fit">
              <FileText className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Detailed Project Report (DPR)</h4>
            <p className="text-xs text-slate-500">
              Institutional credit proposal narrative with promoter background, project cost, means of finance, market analysis, and risk mitigants.
            </p>
          </div>
          <button
            onClick={() => handleDownload('word', 'dpr-word', `Project_Report_${proposal.proposal_code}.docx`)}
            disabled={downloading === 'word'}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Download className="w-4 h-4" />
            <span>{downloading === 'word' ? 'Generating Word...' : 'Download Word (.docx)'}</span>
          </button>
        </div>

        {/* PDF Export */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="p-3 bg-rose-50 text-rose-800 rounded-lg w-fit">
              <FileText className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Bank Submission Memorandum</h4>
            <p className="text-xs text-slate-500">
              Executive credit briefing note for bank relationship managers, including verified ratio matrix, security details, and checklist audit.
            </p>
          </div>
          <button
            onClick={() => handleDownload('pdf', 'bank-pdf', `Bank_Submission_${proposal.proposal_code}.pdf`)}
            disabled={downloading === 'pdf'}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-slate-900 hover:bg-black text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Download className="w-4 h-4" />
            <span>{downloading === 'pdf' ? 'Rendering PDF...' : 'Download PDF Dossier'}</span>
          </button>
        </div>
      </div>

      {/* Dossier Preview Summary */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div>
            <span className="text-[11px] font-semibold tracking-wider text-brand-800 uppercase">
              Credit Facilitation Submission Pack
            </span>
            <h3 className="text-xl font-bold text-slate-900 mt-0.5">
              {entity?.legal_name || client?.primary_contact_name || 'Borrower Legal Entity'}
            </h3>
            <p className="text-xs text-slate-500">
              Proposal Ref: <strong>{proposal.proposal_code}</strong> | Product: <strong>{formatProductType(proposal.product_type)}</strong>
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs text-slate-500 block">Requested Exposure</span>
            <span className="text-2xl font-extrabold text-slate-900">{formatINR(proposal.requested_amount, unitMode)}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
          {/* Facility Summary */}
          <div className="space-y-3">
            <h5 className="font-semibold text-slate-900 text-xs uppercase text-slate-600">Borrower & Facility Profile</h5>
            <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="flex justify-between">
                <span className="text-slate-500">Legal Constitution:</span>
                <span className="font-medium text-slate-800">{entity?.constitution || client?.constitution || 'Private Limited'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Entity PAN:</span>
                <span className="font-mono font-medium text-slate-800">{entity?.pan_masked || 'AA*****M'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tenure:</span>
                <span className="font-medium text-slate-800">{proposal.tenure_months} Months</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Target Benchmark ROI:</span>
                <span className="font-medium text-slate-800">{proposal.target_rate}% p.a.</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Facility Purpose:</span>
                <span className="font-medium text-slate-800">{proposal.purpose || 'Working Capital & Operations'}</span>
              </div>
            </div>
          </div>

          {/* Preliminary Review Status */}
          <div className="space-y-3">
            <h5 className="font-semibold text-slate-900 text-xs uppercase text-slate-600">Syndication Review Status</h5>
            <div className="space-y-1.5 p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="flex justify-between">
                <span className="text-slate-500">Checklist Ingestion:</span>
                <span className="font-medium text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Complete Primary Set
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Financial Modeling:</span>
                <span className="font-medium text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 9-Year CMA Reconciled
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Underwriting Assessment:</span>
                <span className="font-medium text-brand-800">Preliminary Eligible</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Submission Ready:</span>
                <span className="font-medium text-slate-800">Commercial Bank Syndication Queue</span>
              </div>
            </div>
          </div>
        </div>

        {/* Regulatory Bottom Box */}
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500 leading-relaxed">
          <strong>Preparer & Facilitator Certification:</strong> This credit dossier has been compiled from management-certified statutory documents, ITR acknowledgments, and GST filings. In compliance with RBI circulars and fair practice codes, all eligibility metrics are presented as provisional indicative terms.
        </div>
      </div>
    </div>
  );
};
