import React from 'react';
import { TDSAnalysisData } from '../types';
import { RiskBadge } from './RiskBadge';
import { 
  Percent, 
  AlertOctagon, 
  AlertTriangle, 
  CheckCircle2, 
  FileText, 
  ArrowRight, 
  Scale, 
  ShieldAlert, 
  HelpCircle,
  Clock,
  FileSpreadsheet,
  Briefcase
} from 'lucide-react';
import { TDS_SECTIONS_MASTER } from '../utils/gstUtils';

interface TDSAnalyserModuleProps {
  data: TDSAnalysisData;
  onExportExcel: () => void;
}

export const TDSAnalyserModule: React.FC<TDSAnalyserModuleProps> = ({
  data,
  onExportExcel,
}) => {
  const isShortOrMissed = data.isShortDeduction || data.isTDSMissed || data.tdsVariance > 0;

  return (
    <div className="space-y-4">
      
      {/* 4-Box Direct Tax Metric Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Gross Service Amount</p>
          <div className="flex items-center justify-between">
            <span className="text-xl font-bold font-mono text-slate-800">
              ₹{data.grossServiceAmount?.toLocaleString('en-IN') || '0'}
            </span>
            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-bold truncate max-w-[90px]">
              {data.natureOfService || 'Service'}
            </span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Applicable Section &amp; Rate</p>
          <div className="flex items-center justify-between">
            <span className="text-xl font-bold font-mono text-indigo-700">
              {data.recommendedTDSSection}
            </span>
            <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold font-mono">
              {data.standardRate}% Rate
            </span>
          </div>
        </div>

        <div className={`bg-white p-4 rounded-xl border shadow-xs ${
          isShortOrMissed ? 'border-slate-200 border-l-4 border-l-red-500' : 'border-slate-200 border-l-4 border-l-emerald-500'
        }`}>
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Statutory TDS Variance</p>
          <div className="flex items-center justify-between">
            <span className={`text-xl font-bold font-mono ${isShortOrMissed ? 'text-red-600' : 'text-emerald-700'}`}>
              {data.tdsVariance > 0 ? `₹${data.tdsVariance.toLocaleString('en-IN')}` : '₹0'}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
              isShortOrMissed ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {isShortOrMissed ? 'Shortfall' : 'Compliant'}
            </span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Section 201 Risk</p>
          <div className="flex items-center justify-between">
            <span className={`text-sm font-bold font-mono ${isShortOrMissed ? 'text-red-600' : 'text-emerald-700'}`}>
              {isShortOrMissed ? '1% p.m. Interest' : 'Nil Liability'}
            </span>
            <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-bold">
              {isShortOrMissed ? '40(a)(ia)' : 'Form 26AS OK'}
            </span>
          </div>
        </div>
      </div>

      {/* Section Re-Classification Comparison Card */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
            <h3 className="font-bold text-slate-800 text-sm">
              Statutory Classification &amp; Rate Verification (Chapter XVII-B)
            </h3>
          </div>
          <RiskBadge 
            level={data.riskStatus} 
            label={data.isTDSMissed ? 'MISSED TDS' : data.isShortDeduction ? 'SHORT DEDUCTION' : 'COMPLIANT TDS'}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
          {/* Assessee Applied */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">
              Assessee / Client Applied Section:
            </span>
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-700">
                {data.declaredTDSSection || 'None / Not Deducted'}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono font-bold">
                Rate: {data.appliedRate}%
              </span>
            </div>
            <div className="flex justify-between text-slate-500 text-xs pt-2 border-t border-slate-200">
              <span>Actual TDS Deducted:</span>
              <span className="font-mono font-bold text-slate-800">
                ₹{data.actualTDSDeducted?.toLocaleString('en-IN') || '0'}
              </span>
            </div>
          </div>

          {/* Statutory Required */}
          <div className={`p-3.5 rounded-xl border space-y-2 ${
            isShortOrMissed 
              ? 'bg-red-50/40 border-red-200' 
              : 'bg-emerald-50/40 border-emerald-200'
          }`}>
            <span className="text-[10px] uppercase font-bold text-slate-600 block">
              Statutory Mandatory Classification:
            </span>
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-900">
                {data.recommendedTDSSection} ({data.sectionTitle})
              </span>
              <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-mono font-bold">
                Rate: {data.standardRate}%
              </span>
            </div>
            <div className="flex justify-between text-xs pt-2 border-t border-slate-200">
              <span className="text-slate-600">Expected Statutory TDS:</span>
              <span className="font-mono font-bold text-indigo-700">
                ₹{data.expectedTDSDeducted?.toLocaleString('en-IN') || '0'}
              </span>
            </div>
          </div>
        </div>

        {/* Deductor & Deductee Profiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3.5 pt-3 border-t border-slate-100 text-xs">
          <div>
            <span className="text-slate-400 block text-[10px] font-medium">Deductor TAN</span>
            <span className="font-mono font-bold text-slate-700">{data.deductorTAN || 'PNEP12345E'}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-medium">Deductee PAN</span>
            <span className="font-mono font-bold text-slate-700">{data.deducteePAN || 'AAAFR8921K'}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-medium">Sec 197 Certificate</span>
            <span className="font-medium text-slate-700">{data.lowerDeductionCertStatus.replace('_', ' ')}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] font-medium">Form 26AS Status</span>
            <span className="font-mono text-slate-700">{data.form26ASDeclarationStatus}</span>
          </div>
        </div>
      </div>

      {/* Section-Wise Breakdown Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
            <h2 className="font-bold text-slate-700 text-sm">
              Section-by-Section TDS Computation ({data.sectionWiseBreakdown?.length || 0})
            </h2>
          </div>
          <button 
            onClick={onExportExcel}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export to Excel</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-100/60">
              <tr className="border-b border-slate-200 text-[11px] text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-2.5 pl-5">Section</th>
                <th className="p-2.5">Nature of Payment</th>
                <th className="p-2.5 text-right">Taxable Base (₹)</th>
                <th className="p-2.5 text-right">Statutory %</th>
                <th className="p-2.5 text-right">Deducted %</th>
                <th className="p-2.5 text-right">Expected (₹)</th>
                <th className="p-2.5 text-right">Actual (₹)</th>
                <th className="p-2.5 text-right">Shortfall (₹)</th>
                <th className="p-2.5 pr-5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {data.sectionWiseBreakdown && data.sectionWiseBreakdown.length > 0 ? (
                data.sectionWiseBreakdown.map((sec, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="p-2.5 pl-5 font-bold font-mono text-indigo-700">{sec.section}</td>
                    <td className="p-2.5 font-semibold text-slate-800">{sec.natureOfPayment}</td>
                    <td className="p-2.5 text-right font-mono text-slate-700">
                      ₹{sec.taxableAmount?.toLocaleString('en-IN')}
                    </td>
                    <td className="p-2.5 text-right font-mono font-semibold text-slate-700">
                      {sec.applicableRate}%
                    </td>
                    <td className="p-2.5 text-right font-mono font-semibold text-slate-500">
                      {sec.deductedRate}%
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                      ₹{sec.expectedTDS?.toLocaleString('en-IN')}
                    </td>
                    <td className="p-2.5 text-right font-mono font-semibold text-slate-700">
                      ₹{sec.actualTDS?.toLocaleString('en-IN')}
                    </td>
                    <td className={`p-2.5 text-right font-mono font-bold ${
                      sec.variance > 0 ? 'text-red-600' : 'text-emerald-700'
                    }`}>
                      {sec.variance > 0 ? `₹${sec.variance.toLocaleString('en-IN')}` : '₹0'}
                    </td>
                    <td className="p-2.5 pr-5 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        sec.status === 'SHORT_DEDUCTION' || sec.status === 'MISSED_TDS'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {sec.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="p-4 text-center text-slate-400">
                    No section breakdown available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Sleek Summary Bottom Bar */}
        <div className="p-3 bg-slate-900 flex items-center justify-between text-white text-xs">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">TDS RECONCILIATION</span>
            <span className="text-[11px] text-slate-300">
              Assessee Deduction: ₹{data.actualTDSDeducted?.toLocaleString('en-IN')} • Statutory Demand: ₹{data.expectedTDSDeducted?.toLocaleString('en-IN')}
            </span>
          </div>
          <button 
            onClick={onExportExcel}
            className="bg-indigo-600 text-white px-3 py-1 rounded text-[10px] font-bold uppercase hover:bg-indigo-500 transition-colors shadow-2xs"
          >
            Export TDS Annexure
          </button>
        </div>
      </div>

      {/* Actionable CA Audit Recommendations */}
      {data.caAuditRecommendations && data.caAuditRecommendations.length > 0 && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Statutory Audit Recommendations &amp; Risk Mitigation ({data.caAuditRecommendations.length})
            </h4>
          </div>

          <div className="space-y-2">
            {data.caAuditRecommendations.map((rec, i) => (
              <div 
                key={i}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs flex items-start gap-3"
              >
                <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-mono font-bold flex items-center justify-center shrink-0 text-[10px]">
                  {i + 1}
                </span>
                <p className="text-slate-700 leading-relaxed font-medium">
                  {rec}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};

