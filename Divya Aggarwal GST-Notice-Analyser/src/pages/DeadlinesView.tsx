import React from 'react';
import { NoticeCase, Client } from '../types';
import { CalendarClock, Clock } from 'lucide-react';

interface DeadlinesViewProps {
  allCases: NoticeCase[];
  allClients: Client[];
  onSelectCase: (caseId: string) => void;
  onNavigateToTab: (tab: any) => void;
}

export const DeadlinesView: React.FC<DeadlinesViewProps> = ({
  allCases,
  allClients,
  onSelectCase,
  onNavigateToTab,
}) => {
  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-2xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-red-50 text-red-700 rounded-xl border border-red-200">
            <CalendarClock className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">
              Statutory Reply Deadlines & Personal Hearing Radar
            </h1>
            <p className="text-xs text-gray-500">
              Never miss a 30-day statutory reply window or hearing schedule across all active clients.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {allCases.map((c) => {
          const client = allClients.find((cl) => cl.id === c.clientId);
          return (
            <div
              key={c.id}
              className="bg-white rounded-2xl border border-gray-200 p-5 shadow-2xs flex items-center justify-between hover:border-[#4338CA] transition-all"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-200">
                    {c.formType}
                  </span>
                  <span className="text-sm font-bold text-gray-900">{c.noticeNumber}</span>
                  <span className="text-xs text-gray-500 font-medium">
                    Taxpayer: <strong className="text-gray-800">{client?.legalName}</strong> ({client?.gstin})
                  </span>
                </div>

                <div className="text-xs text-gray-600 flex items-center gap-4">
                  <span>Period: FY {c.financialYear} ({c.period})</span>
                  <span>•</span>
                  <span>Notice Date: {c.noticeDate}</span>
                  <span>•</span>
                  <span>Authority: {c.issuingAuthority}</span>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div className="text-right">
                  <div className="text-[10px] text-gray-400 font-bold uppercase">Statutory Reply Due</div>
                  <div className="text-base font-black text-red-600 flex items-center gap-1 justify-end">
                    <Clock className="w-4 h-4" />
                    <span>{c.replyDeadline}</span>
                  </div>
                  {c.hearingDate && (
                    <div className="text-[11px] font-bold text-[#4338CA] mt-0.5">
                      Hearing: {c.hearingDate}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => {
                    onSelectCase(c.id);
                    onNavigateToTab('split_view');
                  }}
                  className="px-4 py-2 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
                >
                  Open Notice
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
