import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Scale, 
  Info
} from 'lucide-react';
import { PolicyRule } from '../types';
import { POLICY_RULES } from '../data/mockData';

export const PolicyCompliance: React.FC = () => {
  const [selectedFramework, setSelectedFramework] = useState<string>('All');
  const [rules] = useState<PolicyRule[]>(POLICY_RULES);

  const frameworks = ['All', 'Ind AS 16', 'Companies Act Sch II', 'CARO 2020', 'Ind AS 36', 'Income Tax Sec 32'];

  const filteredRules = rules.filter((r) =>
    selectedFramework === 'All' ? true : r.framework === selectedFramework
  );

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
              <Scale className="w-4 h-4 text-blue-600" />
              <span>Statutory & Accounting Standard Repository</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
              Policy & Statutory Compliance Matrix
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Automated surveillance against Ind AS 16 (PPE), Companies Act 2013 Schedule II, Ind AS 36 (Impairment), Income Tax Act 1961 Section 32, and CARO 2020.
            </p>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 max-w-sm shrink-0">
            <div className="flex items-center space-x-1.5 text-amber-800 text-xs font-bold">
              <Info className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Mandatory Professional Notice</span>
            </div>
            <p className="text-[11px] text-amber-700 mt-1 italic leading-tight">
              “Illustrative assessment — professional validation required.”
            </p>
          </div>
        </div>

        {/* Framework Selector Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto scrollbar-none pt-2 border-t border-slate-100">
          {frameworks.map((fw) => (
            <button
              key={fw}
              onClick={() => setSelectedFramework(fw)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                selectedFramework === fw
                  ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-2xs'
                  : 'bg-slate-50 text-slate-600 border border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {fw}
            </button>
          ))}
        </div>
      </div>

      {/* Rules & Compliance Cards Grid */}
      <div className="space-y-4">
        {filteredRules.map((rule) => {
          const isCompliant = rule.complianceStatus === 'Compliant';
          return (
            <div
              key={rule.id}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 hover:border-slate-300 transition-all"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                    {rule.framework}
                  </span>
                  <span className="font-mono text-xs text-slate-500 font-semibold">
                    {rule.clause}
                  </span>
                  <h3 className="text-base font-bold text-slate-900">
                    {rule.title}
                  </h3>
                </div>

                <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center space-x-1.5 self-start sm:self-auto ${
                  isCompliant
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                  {isCompliant ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                  <span>{rule.complianceStatus}</span>
                </span>
              </div>

              {/* Requirement & Enterprise Impact */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
                  <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                    Statutory Rule Requirement
                  </span>
                  <p className="text-slate-700 leading-relaxed">
                    {rule.requirement}
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
                  <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                    Enterprise Asset Register Impact
                  </span>
                  <p className="text-slate-700 leading-relaxed">
                    {rule.impactExplanation}
                  </p>
                </div>
              </div>

              {/* Footer Evidence Ref & Count */}
              <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100 gap-2">
                <span>
                  Applicable Assets Monitored: <strong className="text-slate-900 font-mono font-bold">{rule.applicableAssetsCount}</strong>
                </span>
                <span className="font-mono text-slate-500">
                  Evidence Repository Ref: <strong className="text-blue-700">{rule.evidenceRef}</strong>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* CARO 2020 Clause 3(i) Checklist Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-bold text-slate-900">
            CARO 2020 Clause 3(i) — Statutory Auditor Checklist
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {[
            { clause: '3(i)(a)(A)', title: 'Proper Records of PPE', desc: 'Full quantitative details, serial numbers, and physical situations maintained in digital register.', status: 'Compliant' },
            { clause: '3(i)(a)(B)', title: 'Intangible Assets Records', desc: 'ERP and software licenses recorded with amortization schedules.', status: 'Compliant' },
            { clause: '3(i)(b)', title: 'Physical Verification Discrepancies', desc: 'Annual program active; discrepancies exceeding 10% under active investigation.', status: 'Remediation Underway' },
            { clause: '3(i)(c)', title: 'Title Deeds of Immovable Property', desc: 'All 6 land and factory premises title deeds held in company name.', status: 'Compliant' },
            { clause: '3(i)(d)', title: 'PPE Revaluation', desc: 'Cost model applied; no revaluations in current period.', status: 'Not Applicable' },
            { clause: '3(i)(e)', title: 'Benami Property Proceedings', desc: 'No proceedings initiated or pending against company.', status: 'Compliant' }
          ].map((item, idx) => (
            <div key={idx} className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-blue-700">{item.clause}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  item.status === 'Compliant' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                  {item.status}
                </span>
              </div>
              <h4 className="font-bold text-slate-900 text-xs">{item.title}</h4>
              <p className="text-slate-600 text-[11px] leading-tight">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
