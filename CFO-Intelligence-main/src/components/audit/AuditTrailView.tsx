import React, { useState } from 'react';
import {
  History,
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  FileSpreadsheet,
  Sparkles,
  Download,
  Lock,
} from 'lucide-react';
import { ClientProfile } from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface AuditTrailViewProps {
  client: ClientProfile;
  firmName?: string;
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({
  client,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const auditEvents = [
    {
      id: 'aud_1',
      timestamp: '2026-08-25 04:15:22',
      actor: 'Jasleen Daswal, CPA (Lead Partner)',
      action: 'Executive Commentary Signed & Approved',
      details: 'Reviewed and validated AI synthesis; signed off on Q3 runway buffer assessment.',
      category: 'advisory',
      badge: 'Sign-off',
    },
    {
      id: 'aud_2',
      timestamp: '2026-08-25 03:45:10',
      actor: 'AI CFO Engine (Gemini 3.7)',
      action: 'Automated Financial Diagnostic & Red Flags Generated',
      details: 'Evaluated 12-month trailing matrix against industry benchmarks; flagged clinic provider variance.',
      category: 'ai_engine',
      badge: 'AI Diagnostic',
    },
    {
      id: 'aud_3',
      timestamp: '2026-08-25 03:30:00',
      actor: 'Privacy Shield Tokenizer',
      action: 'Client PII Redaction Manifest Generated',
      details: '12 sensitive entities tokenized (Company Legal Name, Tax IDs, Banking Wire Routes).',
      category: 'privacy',
      badge: 'Privacy Redacted',
    },
    {
      id: 'aud_4',
      timestamp: '2026-08-25 03:15:40',
      actor: 'Data Quality Engine',
      action: 'Deterministic Reconciliation Audit Passed (96/100)',
      details: 'Reconciled Gross Margin, EBITDA, Balance Sheet net assets, and Operating Cash Flow variance.',
      category: 'integrity',
      badge: 'Audit 96/100',
    },
    {
      id: 'aud_5',
      timestamp: '2026-08-24 18:20:11',
      actor: 'FP&A Advisory Team',
      action: '12-Month Pro-Forma Forecast & Scenarios Run',
      details: 'Executed Base vs Conservative Downturn scenario sensitivity models.',
      category: 'fpa',
      badge: 'Forecast Run',
    },
  ];

  const filtered = auditEvents.filter(
    e =>
      e.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.actor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.details.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Governance, Security & Audit Trail" firmName={firmName} />

      {/* Top Search Bar */}
      <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search audit trail events..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-900 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Showing <span className="font-bold text-slate-900">{filtered.length}</span> verified audit records
        </div>
      </div>

      {/* Audit Log Timeline */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="divide-y divide-slate-100">
          {filtered.map(event => (
            <div key={event.id} className="p-5 hover:bg-slate-50 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-sm">{event.action}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                    {event.badge}
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">{event.details}</p>
                <div className="text-[11px] text-slate-400 font-medium">
                  Actor: <span className="text-slate-700 font-semibold">{event.actor}</span>
                </div>
              </div>

              <div className="sm:text-right shrink-0">
                <span className="font-mono text-slate-500 text-[11px] block">{event.timestamp}</span>
                <span className="inline-flex items-center gap-1 text-emerald-700 text-[10px] font-bold mt-1">
                  <CheckCircle2 className="w-3 h-3" /> Immutable Log
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
