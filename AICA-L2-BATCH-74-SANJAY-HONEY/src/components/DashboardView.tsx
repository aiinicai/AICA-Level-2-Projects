import React from 'react';
import {
  Mail,
  Sparkles,
  FileEdit,
  Zap,
  Users,
  FileText,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  TrendingUp,
  Building2,
  ChevronRight,
  Info,
  Server,
  Activity,
  CheckCircle,
  XCircle,
  HelpCircle,
  Lock,
} from 'lucide-react';
import {
  RegulatoryUpdate,
  ClientMaster,
  ClientAdvisory,
  NavTab,
  OperatingMode,
  BriefingSource,
  IntegrationStatus,
} from '../types';
import { GmailConnectionState } from '../services/firebaseAuth';

interface DashboardViewProps {
  operatingMode?: OperatingMode;
  setOperatingMode?: (mode: OperatingMode) => void;
  isLiveSystem?: boolean;
  briefingSource?: BriefingSource;
  integrationStatus?: IntegrationStatus;
  gmailState?: GmailConnectionState;
  updates: RegulatoryUpdate[];
  clients: ClientMaster[];
  advisories: ClientAdvisory[];
  setActiveTab: (tab: NavTab) => void;
  onImportGmail: () => void;
  onLoadDemo: () => void;
  onAnalyseAll: () => void;
  onSelectUpdateForAnalysis: (update: RegulatoryUpdate) => void;
  onShowGmailConnectModal?: () => void;
}

const defaultIntegrationStatus: IntegrationStatus = {
  geminiConnected: true,
  gmailConnected: false,
  clientDatabaseLive: true,
  sourceVerificationLive: true,
  whatsappExportReady: true,
  approvalWorkflowActive: true,
};

export const DashboardView: React.FC<DashboardViewProps> = ({
  operatingMode = 'DEMO',
  setOperatingMode = (_mode: OperatingMode) => {},
  isLiveSystem,
  briefingSource = 'DEMO',
  integrationStatus = defaultIntegrationStatus,
  gmailState,
  updates = [],
  clients = [],
  advisories = [],
  setActiveTab,
  onImportGmail,
  onLoadDemo,
  onAnalyseAll,
  onSelectUpdateForAnalysis,
  onShowGmailConnectModal = () => {},
}) => {
  const currentStatus = integrationStatus || defaultIntegrationStatus;
  const isLive = isLiveSystem !== undefined ? isLiveSystem : Boolean(gmailState?.isConnected);

  const badgeText = isLive
    ? briefingSource === 'GMAIL'
      ? '⚡ LIVE SYSTEM — GMAIL BRIEFING INGESTED'
      : '⚡ LIVE SYSTEM — GMAIL CONNECTED'
    : '⚠️ DEMO MODE ACTIVE';

  const badgeSubtext = isLive
    ? `Connected Gmail: ${gmailState?.userEmail || 'Google OAuth Verified'}`
    : 'Simulated Data Engine (Connect Gmail in Briefing tab)';

  const criticalUpdates = (updates || []).filter((u) => u.riskLevel === 'Critical' || u.riskLevel === 'High');
  const pendingApprovals = (advisories || []).filter((a) => a.approvalStatus === 'Pending Review');
  const approvedAdvisories = (advisories || []).filter((a) => a.approvalStatus === 'Approved');

  // Count verified vs unverified
  const verifiedCount = (updates || []).filter(
    (u) => u.verificationStatus === 'Verified from Authoritative Source'
  ).length;
  const pendingVerificationCount = (updates || []).filter(
    (u) =>
      u.verificationStatus === 'Source Identified — Verification Pending' ||
      u.verificationStatus === 'Demo / Simulated Data'
  ).length;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header Bar with Prominent Mode Indicator */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span
              className={`text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full border ${
                !isLive
                  ? 'bg-amber-100 text-amber-800 border-amber-300'
                  : 'bg-emerald-100 text-emerald-800 border-emerald-300'
              }`}
            >
              {badgeText}
            </span>
            <span className="text-xs text-slate-400 font-mono">{badgeSubtext}</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">CA Intelligence Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated regulatory intelligence, client impact analysis & mandatory CA sign-off system.
          </p>
        </div>

        {/* Action Controls & Mode Switch */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="bg-slate-100 p-1 rounded-xl flex items-center border border-slate-200 text-xs font-bold">
            <button
              onClick={() => setOperatingMode('DEMO')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                operatingMode === 'DEMO'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Demo Mode
            </button>
            <button
              onClick={() => setOperatingMode('LIVE')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                operatingMode === 'LIVE'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Live Mode
            </button>
          </div>

          <button
            onClick={onLoadDemo}
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border border-slate-200 cursor-pointer"
          >
            Load Demo Briefing
          </button>
          <button
            onClick={onImportGmail}
            className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md flex items-center space-x-2 cursor-pointer"
          >
            <Mail className="w-4 h-4" />
            <span>Import Today's Briefing</span>
          </button>
        </div>
      </div>

      {/* LIVE READINESS & INTEGRATION STATUS PANEL (Section B Requirement) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 text-white shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-3 mb-4 gap-2">
          <div>
            <h2 className="text-sm font-bold flex items-center space-x-2 text-teal-400">
              <Activity className="w-4 h-4" />
              <span>SYSTEM LIVE READINESS & INTEGRATION STATUS</span>
            </h2>
            <p className="text-[11px] text-slate-400">
              Transparent verification of active API connections versus prototype modules
            </p>
          </div>
          <button
            onClick={onShowGmailConnectModal}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-teal-300 px-3 py-1.5 rounded-lg border border-slate-700 font-semibold cursor-pointer"
          >
            Configure Integrations
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          {/* Gemini AI */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              Gemini AI Engine
            </span>
            <div className="flex items-center space-x-1.5">
              {currentStatus.geminiConnected ? (
                <>
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="font-bold text-emerald-300">Connected</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span className="font-bold text-amber-300">Not Connected</span>
                </>
              )}
            </div>
            <span className="text-[9px] text-slate-400 block mt-1">Model: gemini-3.6-flash</span>
          </div>

          {/* Gmail */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              Gmail Ingestion
            </span>
            <div className="flex items-center space-x-1.5">
              {currentStatus.gmailConnected ? (
                <>
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="font-bold text-emerald-300">Connected</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span className="font-bold text-rose-300">Not Connected</span>
                </>
              )}
            </div>
            <span className="text-[9px] text-slate-300 block mt-1 font-mono truncate" title={gmailState?.userEmail || 'Not Authenticated'}>
              Account: {gmailState?.userEmail || 'Not Authenticated'}
            </span>
            <span className="text-[9px] text-slate-400 block mt-0.5">
              Gmail API: {gmailState?.gmailApiProfileStatus === 'PASS' ? 'Passed' : gmailState?.gmailApiProfileStatus === 'FAIL' ? 'Failed' : 'Pending Verification'}
            </span>
          </div>

          {/* Client Database */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              Client Master Data
            </span>
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="font-bold text-amber-300">
                Demo Client Dataset
              </span>
            </div>
            <span className="text-[9px] text-slate-400 block mt-1">{clients.length} Demo Records</span>
          </div>

          {/* Regulatory Verification */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              Source Verification
            </span>
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="font-bold text-amber-300">
                {currentStatus.sourceVerificationLive ? 'Live Checks' : 'Demo / Pending'}
              </span>
            </div>
            <span className="text-[9px] text-slate-400 block mt-1">Official Gazette Check</span>
          </div>

          {/* WhatsApp Status Export */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              WhatsApp Status
            </span>
            <div className="flex items-center space-x-1.5">
              <CheckCircle className="w-4 h-4 text-teal-400 shrink-0" />
              <span className="font-bold text-teal-300">9:16 Prototype</span>
            </div>
            <span className="text-[9px] text-slate-400 block mt-1">5-Card Set Generation</span>
          </div>

          {/* Approval Workflow */}
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3">
            <span className="text-[10px] text-slate-400 font-semibold block uppercase tracking-wider mb-1">
              CA Review Gate
            </span>
            <div className="flex items-center space-x-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="font-bold text-emerald-300">Active Gate</span>
            </div>
            <span className="text-[9px] text-slate-400 block mt-1">Human Sign-off Mandatory</span>
          </div>
        </div>
      </div>

      {/* Bento Grid: KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Total Updates */}
        <div
          onClick={() => setActiveTab('inbox')}
          className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-xs hover:border-teal-500 transition-all cursor-pointer"
        >
          <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1">
            Total Updates
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-black text-slate-900">{updates.length}</span>
            <span className="text-xs text-teal-600 font-bold bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200">
              +{updates.length} Extracted
            </span>
          </div>
        </div>

        {/* Verified Updates */}
        <div
          onClick={() => setActiveTab('inbox')}
          className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-xs hover:border-emerald-500 transition-all cursor-pointer"
        >
          <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1">
            Verified Source
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-black text-emerald-600">{verifiedCount}</span>
            <span className="text-[10px] text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
              {pendingVerificationCount} Demo/Pending
            </span>
          </div>
        </div>

        {/* Critical Risk */}
        <div
          onClick={() => setActiveTab('impact')}
          className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-xs hover:border-rose-400 transition-all cursor-pointer"
        >
          <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1">
            Critical Risk
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-black text-rose-600">{criticalUpdates.length}</span>
            <span className="text-xs text-rose-600 font-bold bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
              High Impact
            </span>
          </div>
        </div>

        {/* Advisories Generated */}
        <div
          onClick={() => setActiveTab('advisories')}
          className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-xs hover:border-blue-500 transition-all cursor-pointer"
        >
          <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1">
            Advisories Generated
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-black text-blue-600">{advisories.length}</span>
            <span className="text-xs text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
              {approvedAdvisories.length} Approved
            </span>
          </div>
        </div>

        {/* Pending Approval */}
        <div
          onClick={() => setActiveTab('approval')}
          className="bg-white border border-slate-200 rounded-2xl p-4 flex flex-col justify-between shadow-xs hover:border-amber-400 transition-all cursor-pointer"
        >
          <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1">
            Pending CA Approval
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-black text-amber-500">{pendingApprovals.length}</span>
            <span className="text-xs text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
              CA Sign-Off
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Regulatory Updates Inbox */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-800 flex items-center space-x-2 text-sm">
              <span className="w-2.5 h-2.5 bg-teal-500 rounded-full animate-pulse" />
              <span>Today's Extracted Briefing Updates</span>
            </h3>
            <span className="text-[11px] font-semibold text-slate-400">{updates.length} Items</span>
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[380px] pr-1">
            {updates.map((upd) => {
              const borderAccent =
                upd.category === 'GST'
                  ? 'border-l-rose-500'
                  : upd.category === 'Income Tax'
                  ? 'border-l-amber-500'
                  : upd.category === 'MCA / Companies Act'
                  ? 'border-l-teal-500'
                  : 'border-l-blue-500';

              return (
                <div
                  key={upd.id}
                  onClick={() => onSelectUpdateForAnalysis(upd)}
                  className={`p-3.5 border border-slate-100 rounded-xl bg-slate-50 hover:bg-teal-50/60 hover:border-teal-200 cursor-pointer transition-all border-l-4 ${borderAccent}`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-[10px] font-bold bg-slate-200 text-slate-800 px-2 py-0.5 rounded uppercase">
                      {upd.category}
                    </span>
                    <span className="text-[10px] text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      {upd.verificationStatus}
                    </span>
                  </div>
                  <p className="text-xs font-bold text-slate-900 mb-1 leading-snug">{upd.title}</p>
                  <p className="text-[11px] text-slate-500 line-clamp-1">{upd.keyDevelopment}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Client Matching & Advisory Control Matrix */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-800 flex items-center space-x-2 text-sm">
                <Users className="w-4 h-4 text-teal-600" />
                <span>Client Master Matching Summary</span>
              </h3>
              <span className="text-[10px] bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-full text-slate-600 font-bold">
                Hard Exclusion Rules Active
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[11px] uppercase text-slate-400 border-b border-slate-100">
                    <th className="pb-2.5 font-bold">Client Name</th>
                    <th className="pb-2.5 font-bold">Legal Entity</th>
                    <th className="pb-2.5 font-bold">Industry</th>
                    <th className="pb-2.5 font-bold">Turnover</th>
                    <th className="pb-2.5 text-right font-bold">Action</th>
                  </tr>
                </thead>
                <tbody className="text-xs">
                  {clients.map((cli) => (
                    <tr key={cli.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                      <td className="py-3 font-semibold text-slate-800">{cli.clientName}</td>
                      <td className="py-3 text-slate-500 font-mono text-[11px]">{cli.entityType}</td>
                      <td className="py-3 text-slate-500">{cli.industry}</td>
                      <td className="py-3 text-slate-500 font-mono text-[11px]">{cli.annualTurnoverRange}</td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => setActiveTab('matching')}
                          className="text-teal-600 font-bold hover:underline cursor-pointer"
                        >
                          Run Match
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-end">
            <button
              onClick={onAnalyseAll}
              className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl shadow-xs transition-all cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>RUN MATCHING ENGINE FOR ALL CLIENTS</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
