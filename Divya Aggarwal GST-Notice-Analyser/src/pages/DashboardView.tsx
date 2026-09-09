import React from 'react';
import { Client, NoticeCase } from '../types';
import { FileText, Clock, ArrowRight, ShieldCheck, Plus, Scale, Building2, UserPlus } from 'lucide-react';
import { FEATURES } from '../config';

interface DashboardViewProps {
  activeClient: Client | null;
  activeCase: NoticeCase | null;
  allClients: Client[];
  allCases: NoticeCase[];
  onSelectCase: (caseId: string) => void;
  onOpenIntake: () => void;
  onOpenAddClient: () => void;
  onNavigateToTab: (tab: any) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  activeClient,
  activeCase,
  allClients,
  allCases,
  onSelectCase,
  onOpenIntake,
  onOpenAddClient,
  onNavigateToTab,
}) => {
  const clientCases = allCases.filter((c) => c.clientId === activeClient?.id);

  if (allClients.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 bg-[#F8FAFC] p-8 text-center">
        <div className="rounded-2xl bg-indigo-50 p-4 text-[#4338CA]"><Building2 className="h-8 w-8" /></div>
        <div>
          <h2 className="text-base font-bold text-slate-900">Set up your first client</h2>
          <p className="mt-1 max-w-sm text-xs text-slate-500">
            Add a GST client (legal name + GSTIN), then upload the notice you received for them.
            Everything stays on this computer.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onOpenAddClient}
            className="flex items-center gap-2 rounded-lg bg-[#4338CA] px-4 py-2 text-xs font-semibold text-white hover:bg-[#3730A3]"
          >
            <UserPlus className="h-4 w-4" /> Add client
          </button>
        </div>
      </div>
    );
  }

  if (clientCases.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 bg-[#F8FAFC] p-8 text-center">
        <div className="rounded-2xl bg-indigo-50 p-4 text-[#4338CA]"><FileText className="h-8 w-8" /></div>
        <div>
          <h2 className="text-base font-bold text-slate-900">No notices for {activeClient?.legalName || 'this client'} yet</h2>
          <p className="mt-1 max-w-sm text-xs text-slate-500">
            Upload the GST notice and extract its details — issues, demand figures, deadlines and defence points.
          </p>
        </div>
        <button
          onClick={onOpenIntake}
          className="flex items-center gap-2 rounded-lg bg-[#4338CA] px-4 py-2 text-xs font-semibold text-white hover:bg-[#3730A3]"
        >
          <Plus className="h-4 w-4" /> Add notice
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-[#4338CA] rounded-2xl p-6 text-white shadow-sm flex items-center justify-between">
        <div className="space-y-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-200">
            GST Notice Assessment
          </div>
          <h1 className="text-xl font-bold tracking-tight">
            {activeClient?.legalName || 'Select a client'}
          </h1>
          <p className="text-xs text-indigo-100 font-mono">
            GSTIN: {activeClient?.gstin || '—'} · {clientCases.length} active notice{clientCases.length === 1 ? '' : 's'}
          </p>
        </div>

        <button
          onClick={onOpenIntake}
          className="flex items-center gap-2 px-4 py-2.5 bg-white text-[#4338CA] hover:bg-indigo-50 rounded-xl text-xs font-bold shadow-md transition-all active:scale-98 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add notice</span>
        </button>
      </div>

      {activeCase && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Active Case Demand Summary ({activeCase.formType} - {activeCase.noticeNumber})
            </span>
            <span className="text-xs font-bold text-red-600 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              Reply Due: {activeCase.replyDeadline}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-gray-500">Principal Tax Disputed</div>
              <div className="text-lg font-bold text-gray-900 mt-1">
                ₹{activeCase.principalTax.toLocaleString('en-IN')}
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5 font-medium">Under Sec 73/74 Demand</div>
            </div>

            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-gray-500">Interest Demanded (Sec 50)</div>
              <div className="text-lg font-bold text-amber-700 mt-1">
                ₹{activeCase.interest.toLocaleString('en-IN')}
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5 font-medium">Interest calculations</div>
            </div>

            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-2xs">
              <div className="text-[11px] font-semibold text-gray-500">Penalty Proposed (Sec 122)</div>
              <div className="text-lg font-bold text-red-700 mt-1">
                ₹{activeCase.penalty.toLocaleString('en-IN')}
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5 font-medium">10% / Statutory minimum</div>
            </div>

            <div className="bg-[#EEF2FF] rounded-xl p-4 border border-indigo-200 shadow-2xs">
              <div className="text-[11px] font-bold text-[#4338CA] uppercase">Total Disputed Demand</div>
              <div className="text-xl font-black text-[#4338CA] mt-1">
                ₹{activeCase.totalDemand.toLocaleString('en-IN')}
              </div>
              <div className="text-[10px] text-indigo-700 font-medium">
                FY {activeCase.financialYear} ({activeCase.period})
              </div>
            </div>
          </div>
        </div>
      )}

      <div className={`grid gap-4 ${FEATURES.figureSource ? 'grid-cols-3' : 'grid-cols-2'}`}>
        <div
          onClick={() => onNavigateToTab('split_view')}
          className="bg-white hover:bg-indigo-50/50 p-4 rounded-xl border border-gray-200 hover:border-[#4338CA] transition-all cursor-pointer shadow-2xs flex flex-col justify-between group"
        >
          <div className="space-y-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-[#4338CA] flex items-center justify-center font-bold">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-900 group-hover:text-[#4338CA]">
              Side-by-Side Notice Analysis
            </h3>
            <p className="text-[11px] text-gray-500 leading-relaxed">
              View original scanned notice with extracted issue accordions, facts, and legal positions.
            </p>
          </div>
          <div className="flex items-center gap-1 text-[11px] font-bold text-[#4338CA] mt-3">
            <span>Open Split Screen</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        {FEATURES.figureSource && (
          <div
            onClick={() => onNavigateToTab('figure_source')}
            className="bg-white hover:bg-blue-50/50 p-4 rounded-xl border border-gray-200 hover:border-blue-500 transition-all cursor-pointer shadow-2xs flex flex-col justify-between group"
          >
            <div className="space-y-2">
              <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                <Scale className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-gray-900 group-hover:text-blue-700">
                Department Figure Source Finder
              </h3>
              <p className="text-[11px] text-gray-500 leading-relaxed">
                Find out where the officer obtained disputed numbers (GSTR-2B Table 3 vs 3B 4(A)(5), RCM, EWB).
              </p>
            </div>
            <div className="flex items-center gap-1 text-[11px] font-bold text-blue-700 mt-3">
              <span>Inspect Figure Sources</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        )}

        <div
          onClick={() => onNavigateToTab('reply_gen')}
          className="bg-white hover:bg-emerald-50/50 p-4 rounded-xl border border-gray-200 hover:border-emerald-500 transition-all cursor-pointer shadow-2xs flex flex-col justify-between group"
        >
          <div className="space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-900 group-hover:text-emerald-700">
              Legal Word Reply (.docx) & Email
            </h3>
            <p className="text-[11px] text-gray-500 leading-relaxed">
              Generate ready-to-file legal reply for the GST Officer and draft document request emails.
            </p>
          </div>
          <div className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 mt-3">
            <span>Draft Legal Reply</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-2xs">
        <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center bg-[#F9FAFB]">
          <span className="text-xs font-bold text-gray-800 uppercase tracking-wider">
            Notices & Proceedings for {activeClient?.legalName} ({clientCases.length})
          </span>
          <button onClick={onOpenIntake} className="text-xs font-bold text-[#4338CA] hover:underline cursor-pointer">
            + Upload Another Notice
          </button>
        </div>

        <div className="divide-y divide-gray-100">
          {clientCases.map((c) => {
            const isSelected = activeCase?.id === c.id;
            return (
              <div
                key={c.id}
                onClick={() => onSelectCase(c.id)}
                className={`p-4 flex items-center justify-between hover:bg-gray-50 transition-colors cursor-pointer ${
                  isSelected ? 'bg-[#EEF2FF]/70 border-l-4 border-[#4338CA]' : ''
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700 border border-red-200">
                      {c.formType}
                    </span>
                    <span className="text-xs font-bold text-gray-900">{c.noticeNumber}</span>
                    <span className="text-[10px] text-gray-500">
                      Dated: {c.noticeDate} • FY {c.financialYear}
                    </span>
                  </div>
                  <div className="text-[11px] text-gray-600">
                    Authority: {c.issuingAuthority} • Sections: {c.sectionsMentioned}
                  </div>
                </div>

                <div className="flex items-center gap-6 text-right">
                  <div>
                    <div className="text-[10px] text-gray-400 font-bold uppercase">Total Disputed Demand</div>
                    <div className="text-sm font-bold text-[#4338CA]">
                      ₹{c.totalDemand.toLocaleString('en-IN')}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] text-gray-400 font-bold uppercase">Statutory Reply Due</div>
                    <div className="text-xs font-bold text-red-600">{c.replyDeadline}</div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCase(c.id);
                      onNavigateToTab('split_view');
                    }}
                    className="px-3 py-1.5 bg-[#4338CA] text-white rounded-lg text-xs font-bold hover:bg-[#3730A3] transition-colors cursor-pointer"
                  >
                    Open Case
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
