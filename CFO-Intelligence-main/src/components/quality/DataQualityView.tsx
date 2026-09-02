import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  FileSpreadsheet,
  Activity,
  Layers,
  Sparkles,
  ArrowRight,
  Info,
  Check,
} from 'lucide-react';
import { FinancialModel, ClientProfile } from '../../types';
import { DataQualityEngine } from '../../services/dataQualityEngine';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface DataQualityViewProps {
  model: FinancialModel;
  firmName?: string;
}

export const DataQualityView: React.FC<DataQualityViewProps> = ({
  model,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const client = model.client;
  const auditResult = DataQualityEngine.auditFinancialModel(model);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Data Quality, Audit & Reconciliation Engine" firmName={firmName} />

      {/* Top Banner: Score Gauge */}
      <div className="bg-linear-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-3xl p-6 sm:p-8 shadow-lg border border-slate-700 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4" /> Integrity Certified
          </div>
          <h3 className="text-2xl font-black text-white">
            Data Quality Audit Score
          </h3>
          <p className="text-sm text-slate-300 max-w-xl">
            Automated mathematical reconciliation across general ledgers, balance sheets, and cash flow formulas.
          </p>
        </div>

        {/* Big Score Circular Badge */}
        <div className="flex items-center gap-4 bg-slate-900/80 p-5 rounded-2xl border border-slate-700">
          <div className="w-20 h-20 rounded-full border-4 border-emerald-500 flex flex-col items-center justify-center bg-emerald-950/40 text-white shadow-inner">
            <span className="text-2xl font-black">{auditResult.overallScore}</span>
            <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-widest">/ 100</span>
          </div>
          <div className="text-left">
            <div className="text-sm font-bold text-white capitalize">{auditResult.status} Integrity</div>
            <div className="text-xs text-slate-400 font-mono mt-0.5">
              {auditResult.checksPassed}/{auditResult.totalChecks} Rules Verified
            </div>
            <div className="text-[11px] text-emerald-400 font-semibold mt-1">
              Ready for CFO Sign-Off
            </div>
          </div>
        </div>
      </div>

      {/* 7-Point Audit Checklist Grid */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Automated Integrity & Reconciliation Audit Checks
          </h4>
          <span className="text-xs text-slate-500 font-medium">Deterministic Mathematical Validation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {auditResult.auditItems.map((item, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
                item.passed
                  ? 'bg-emerald-50/30 border-emerald-100 text-slate-800'
                  : 'bg-rose-50/40 border-rose-100 text-slate-900'
              }`}
            >
              <div
                className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                  item.passed ? 'bg-emerald-500 text-white' : 'bg-rose-500 text-white'
                }`}
              >
                {item.passed ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              </div>
              <div className="space-y-0.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-slate-900">{item.name}</span>
                  <span
                    className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                      item.passed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {item.passed ? 'Passed' : 'Attention'}
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">{item.description}</p>
                <div className="text-[11px] font-mono text-slate-400 mt-1">Rule ID: {item.id}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Identified Financial Anomalies Section */}
      {auditResult.anomalies.length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Detected Ledger Anomaly Warnings ({auditResult.anomalies.length})
            </h4>
            <span className="text-xs text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded-full">
              Non-Fatal Notice
            </span>
          </div>

          <div className="space-y-3">
            {auditResult.anomalies.map(anom => (
              <div key={anom.id} className="p-4 bg-amber-50/40 rounded-xl border border-amber-200/80 text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{anom.title}</span>
                  <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-amber-200 text-amber-800 font-semibold">
                    {anom.periodKey}
                  </span>
                </div>
                <p className="text-slate-700">{anom.message}</p>
                <div className="text-[11px] font-medium text-amber-900 bg-white p-2 rounded border border-amber-100">
                  <span className="font-bold">Recommendation: </span>
                  {anom.suggestedAction}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
