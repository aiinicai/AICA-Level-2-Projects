import React, { useState } from 'react';
import { Client, NoticeCase } from '../types';
import { Building2, ChevronDown, Plus, Settings, FileText, LogOut } from 'lucide-react';

interface HeaderProps {
  activeClient: Client | null;
  allClients: Client[];
  activeCase: NoticeCase | null;
  allCases: NoticeCase[];
  firmName: string;
  onSelectClient: (clientId: string) => void;
  onSelectCase: (caseId: string) => void;
  onOpenIntake: () => void;
  onOpenSettings: () => void;
  onOpenAddClient: () => void;
  onSignOut: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeClient,
  allClients,
  activeCase,
  allCases,
  firmName,
  onSelectClient,
  onSelectCase,
  onOpenIntake,
  onOpenSettings,
  onOpenAddClient,
  onSignOut,
}) => {
  const [clientMenuOpen, setClientMenuOpen] = useState(false);
  const [caseMenuOpen, setCaseMenuOpen] = useState(false);

  const clientCases = allCases.filter((c) => c.clientId === activeClient?.id);

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-2.5 flex items-center justify-between shadow-xs select-none z-20">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 pr-4 border-r border-gray-200">
          <div className="w-8 h-8 rounded-lg bg-[#4338CA] text-white flex items-center justify-center font-bold text-sm shadow-xs">
            CA
          </div>
          <div>
            <div className="text-[10px] font-bold tracking-wider text-[#4338CA] uppercase leading-tight">
              GST Notice Analyser
            </div>
            <div className="text-xs font-semibold text-gray-800 leading-tight">
              {firmName || 'CA Workstation'}
            </div>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={() => setClientMenuOpen(!clientMenuOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 border border-gray-200 text-left transition-colors"
          >
            <Building2 className="w-4 h-4 text-[#4338CA]" />
            <div>
              <div className="text-xs font-bold text-gray-900 leading-tight">
                {activeClient?.legalName || 'Select Client'}
              </div>
              <div className="text-[10px] text-gray-500 font-mono leading-tight">
                {activeClient?.gstin || 'No GSTIN Selected'}
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-1" />
          </button>

          {clientMenuOpen && (
            <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
              <div className="px-3 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex justify-between items-center">
                <span>Select Client</span>
                <button
                  onClick={() => {
                    setClientMenuOpen(false);
                    onOpenAddClient();
                  }}
                  className="text-[#4338CA] hover:underline font-bold"
                >
                  + Add New
                </button>
              </div>
              <div className="max-h-60 overflow-y-auto">
                {allClients.map((client) => (
                  <button
                    key={client.id}
                    onClick={() => {
                      onSelectClient(client.id);
                      setClientMenuOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-[#EEF2FF] flex flex-col ${
                      activeClient?.id === client.id ? 'bg-[#EEF2FF] font-bold' : ''
                    }`}
                  >
                    <span className="text-gray-900">{client.legalName}</span>
                    <span className="text-[10px] text-gray-500 font-mono">{client.gstin}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {clientCases.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setCaseMenuOpen(!caseMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 border border-gray-200 text-left transition-colors"
            >
              <FileText className="w-4 h-4 text-amber-600" />
              <div>
                <div className="text-xs font-bold text-gray-900 leading-tight">
                  {activeCase ? `${activeCase.formType} • ${activeCase.noticeNumber}` : 'Select Notice Case'}
                </div>
                <div className="text-[10px] text-gray-500 leading-tight">
                  {activeCase ? `FY ${activeCase.financialYear} (Due: ${activeCase.replyDeadline})` : 'No Case Selected'}
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-1" />
            </button>

            {caseMenuOpen && (
              <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
                <div className="px-3 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Notices for this Client ({clientCases.length})
                </div>
                <div className="max-h-60 overflow-y-auto">
                  {clientCases.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        onSelectCase(c.id);
                        setCaseMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-[#EEF2FF] flex flex-col ${
                        activeCase?.id === c.id ? 'bg-[#EEF2FF] font-bold' : ''
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-gray-900 font-semibold">{c.formType} - {c.noticeNumber}</span>
                        <span className="text-[10px] font-bold text-red-600">₹{c.totalDemand.toLocaleString('en-IN')}</span>
                      </div>
                      <span className="text-[10px] text-gray-500">FY {c.financialYear} • Deadline: {c.replyDeadline}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2.5">
        <button
          onClick={onOpenIntake}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#4338CA] text-white hover:bg-[#3730A3] text-xs font-bold shadow-xs active:scale-98 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add Notice</span>
        </button>

        <button
          onClick={onOpenSettings}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors cursor-pointer"
          title="Firm profile & team"
        >
          <Settings className="w-4 h-4" />
        </button>

        <button
          onClick={onSignOut}
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors cursor-pointer"
          title="Sign out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
