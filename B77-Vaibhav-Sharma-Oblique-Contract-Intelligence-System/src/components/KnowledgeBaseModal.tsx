import React, { useState, useMemo } from 'react';
import { 
  BookOpen, 
  Search, 
  Tag, 
  ExternalLink, 
  ChevronRight, 
  Scale, 
  HelpCircle,
  CheckCircle2
} from 'lucide-react';
import { INDIAN_COMPLIANCE_RULES, ComplianceRule } from '../knowledge/rules';
import { AnalysisDomain } from '../types/contract';

export const KnowledgeBaseView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDomain, setSelectedDomain] = useState<string>('All');
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(INDIAN_COMPLIANCE_RULES[0]?.id || null);

  const domainsList = [
    'All',
    'Accounting',
    'GST',
    'TDS',
    'MSME',
    'Related Party',
    'Audit',
    'Financial Reporting',
    'Working Capital'
  ];

  const filteredRules = useMemo(() => {
    return INDIAN_COMPLIANCE_RULES.filter(rule => {
      if (selectedDomain !== 'All' && rule.domain !== selectedDomain) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = rule.title.toLowerCase().includes(q);
        const matchesCitation = rule.statutoryCitation.toLowerCase().includes(q);
        const matchesSummary = rule.summary.toLowerCase().includes(q);
        const matchesKeywords = rule.triggerKeywords.some(k => k.toLowerCase().includes(q));
        if (!matchesTitle && !matchesCitation && !matchesSummary && !matchesKeywords) {
          return false;
        }
      }
      return true;
    });
  }, [selectedDomain, searchQuery]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">
              Indian Compliance & Accounting Rules Knowledge Base
            </h1>
            <p className="text-xs text-slate-500">
              Statutory frameworks, statutory thresholds, and standard audit verification checklists for Indian Chartered Accountants.
            </p>
          </div>
        </div>

        {/* Search & Domain Filter Strip */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
            {domainsList.map(domain => (
              <button
                key={domain}
                onClick={() => setSelectedDomain(domain)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                  selectedDomain === domain
                    ? 'bg-amber-600 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {domain}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sections, rules, or keywords..."
              className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-amber-500"
            />
          </div>
        </div>
      </div>

      {/* Rules Grid & Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left 1 Col: Rule List */}
        <div className="space-y-2.5 max-h-[700px] overflow-y-auto">
          {filteredRules.map(rule => (
            <div
              key={rule.id}
              onClick={() => setExpandedRuleId(rule.id)}
              className={`p-3.5 rounded-xl border transition cursor-pointer text-xs ${
                expandedRuleId === rule.id
                  ? 'bg-amber-50/80 border-amber-300 shadow-xs ring-1 ring-amber-400/40'
                  : 'bg-white border-slate-200 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-bold text-amber-900 font-mono text-[11px]">
                  {rule.statutoryCitation}
                </span>
                <span className="px-2 py-0.2 rounded text-[10px] bg-slate-100 text-slate-700 font-semibold">
                  {rule.domain}
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-xs mb-1">{rule.title}</h3>
              <p className="text-slate-500 text-[11px] line-clamp-2">{rule.summary}</p>
            </div>
          ))}
        </div>

        {/* Right 2 Cols: Expanded Rule Inspector */}
        <div className="lg:col-span-2">
          {expandedRuleId ? (
            (() => {
              const rule = INDIAN_COMPLIANCE_RULES.find(r => r.id === expandedRuleId) || INDIAN_COMPLIANCE_RULES[0];
              return (
                <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6 text-xs text-slate-800">
                  {/* Top Bar */}
                  <div className="border-b border-slate-100 pb-4 space-y-1.5">
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200 uppercase font-mono">
                        {rule.statutoryCitation}
                      </span>
                      <span className="text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                        {rule.domain} Reference
                      </span>
                    </div>
                    <h2 className="text-base font-bold text-slate-900 tracking-tight">
                      {rule.title}
                    </h2>
                  </div>

                  {/* Summary */}
                  <div className="space-y-1.5">
                    <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                      Core Statutory Provision & Accounting Mandate
                    </h4>
                    <p className="text-slate-700 bg-slate-50 p-3.5 rounded-lg border border-slate-200 leading-relaxed font-medium">
                      {rule.summary}
                    </p>
                  </div>

                  {/* Key Trigger Keywords */}
                  <div className="space-y-1.5">
                    <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                      Contract Clause Trigger Terms
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {rule.triggerKeywords.map(kw => (
                        <span key={kw} className="px-2 py-0.5 bg-slate-100 rounded text-[11px] font-mono text-slate-700 border border-slate-200">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* CA Verification Checklist */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                      Mandatory CA Verification Steps
                    </h4>
                    <ul className="space-y-1.5">
                      {rule.caVerificationSteps.map((step, idx) => (
                        <li key={idx} className="flex items-start space-x-2 bg-slate-50 p-2.5 rounded border border-slate-200">
                          <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                          <span className="text-slate-700">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Targeted Evidence List */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                      Documentary Evidence Required
                    </h4>
                    <ul className="space-y-1.5">
                      {rule.requiredEvidence.map((ev, idx) => (
                        <li key={idx} className="flex items-start space-x-2 bg-emerald-50/40 p-2.5 rounded border border-emerald-200 text-emerald-950 font-medium">
                          <span className="font-mono text-emerald-700 font-bold">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Questions to Ask Management */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                      Key Questions for Client Management / CFO
                    </h4>
                    <ul className="space-y-1.5">
                      {rule.managementQuestions.map((q, idx) => (
                        <li key={idx} className="flex items-start space-x-2 bg-amber-50/40 p-2.5 rounded border border-amber-200">
                          <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                          <span className="text-slate-800 font-medium">{q}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400">
              Select a compliance rule to view full statutory references and verification checklist.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
