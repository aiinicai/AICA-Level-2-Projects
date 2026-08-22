import React, { useState } from 'react';
import {
  Mail,
  Sparkles,
  Search,
  FileEdit,
  CheckCircle2,
  AlertCircle,
  Calendar,
  ExternalLink,
  Tag,
  ShieldCheck,
  RefreshCw,
  Send,
  Info,
  Clock,
  FileCheck,
  Lock,
  Key,
} from 'lucide-react';
import { RegulatoryUpdate, SourceProvenance, BriefingSource, ActiveBriefingInfo } from '../types';
import { GmailIngestionView } from './GmailIngestionView';
import { GmailConnectionState } from '../services/firebaseAuth';

interface TodaysBriefingViewProps {
  updates: RegulatoryUpdate[];
  briefingDate: string;
  setBriefingDate: (date: string) => void;
  onImportGmail: () => void;
  onLoadDemo: () => void;
  onAddManualUpdate: (updateData: any) => void;
  isExtracting: boolean;
  extractionError: string | null;
  gmailState: GmailConnectionState;
  onGmailStateChange: (state: GmailConnectionState) => void;
  onImportBriefingFromText: (text: string, subject?: string, importMeta?: any) => void;
  isLiveSystem?: boolean;
  briefingSource?: BriefingSource;
  isDemoMode?: boolean;
  activeBriefingInfo?: ActiveBriefingInfo;
  onLogAudit: (action: string, target: string, details: string) => void;
}

export const TodaysBriefingView: React.FC<TodaysBriefingViewProps> = ({
  updates,
  briefingDate,
  setBriefingDate,
  onImportGmail,
  onLoadDemo,
  onAddManualUpdate,
  isExtracting,
  extractionError,
  gmailState,
  onGmailStateChange,
  onImportBriefingFromText,
  isLiveSystem,
  briefingSource = 'DEMO',
  isDemoMode,
  activeBriefingInfo,
  onLogAudit,
}) => {
  const isLive = isLiveSystem !== undefined ? isLiveSystem : gmailState.isConnected;
  const [activeSubTab, setActiveSubTab] = useState<'extracted' | 'gmail' | 'manual'>('extracted');

  // Form state
  const [manualTitle, setManualTitle] = useState('');
  const [manualSource, setManualSource] = useState('CBIC / Income Tax Dept / MCA Circular');
  const [manualDate, setManualDate] = useState(new Date().toISOString().split('T')[0]);
  const [manualRefNo, setManualRefNo] = useState('');
  const [manualUrl, setManualUrl] = useState('');
  const [manualText, setManualText] = useState('');
  const [manualSuccessMsg, setManualSuccessMsg] = useState(false);

  // Extract provenance from first update if available
  const sampleProvenance: SourceProvenance | undefined = updates[0]?.provenance;

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle || !manualText) return;

    onAddManualUpdate({
      title: manualTitle,
      source: manualSource,
      date: manualDate,
      referenceNo: manualRefNo,
      url: manualUrl,
      fullText: manualText,
    });

    setManualSuccessMsg(true);
    setTimeout(() => setManualSuccessMsg(false), 3000);
    setManualTitle('');
    setManualRefNo('');
    setManualText('');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Action Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <Mail className="w-4 h-4" />
            <span>PRIMARY INPUT SOURCE — GMAIL BRIEFING ENGINE</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Today's Professional Briefing</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Subject pattern:{' '}
            <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded font-mono text-[11px]">
              Daily Professional Briefing – [Date]
            </code>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={briefingDate}
              onChange={(e) => setBriefingDate(e.target.value)}
              className="bg-transparent font-bold text-slate-800 w-28 focus:outline-none"
              placeholder="e.g. 7 August 2026"
            />
          </div>

          <button
            onClick={onImportGmail}
            disabled={isExtracting}
            className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50"
          >
            {isExtracting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            <span>IMPORT TODAY'S BRIEFING</span>
          </button>

          <button
            onClick={onLoadDemo}
            className="flex items-center space-x-2 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 text-xs font-bold px-4 py-2.5 rounded-xl shadow-xs transition-all cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-amber-600" />
            <span>LOAD DEMO BRIEFING</span>
          </button>
        </div>
      </div>

      {/* Gmail Connection Status Notice */}
      {!gmailState.isConnected && (
        <div className="p-4 bg-amber-50 border border-amber-300 text-amber-900 rounded-2xl text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <span className="font-bold block">Gmail Integration Not Connected</span>
              <span className="text-amber-800 text-[11px]">
                Gmail is not connected. Connect Gmail to import today's professional briefing or use Load Demo Briefing.
              </span>
            </div>
          </div>
          <button
            onClick={() => setActiveSubTab('gmail')}
            className="bg-amber-800 text-white font-bold px-3.5 py-2 rounded-xl text-xs hover:bg-amber-900 transition-all cursor-pointer shrink-0 flex items-center space-x-1.5"
          >
            <Key className="w-3.5 h-3.5" />
            <span>Connect Gmail OAuth</span>
          </button>
        </div>
      )}

      {extractionError && (
        <div className="p-4 bg-rose-50 border border-rose-300 text-rose-900 rounded-2xl text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="font-semibold">{extractionError}</span>
        </div>
      )}

      {/* Sub Tabs */}
      <div className="flex flex-wrap items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveSubTab('extracted')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            activeSubTab === 'extracted'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Extracted Briefing Updates ({updates.length})
        </button>
        <button
          onClick={() => setActiveSubTab('gmail')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
            activeSubTab === 'gmail'
              ? 'bg-teal-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Mail className="w-3.5 h-3.5" />
          <span>Gmail Daily Briefing Ingestion Module</span>
          {gmailState.isConnected ? (
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block ml-1" />
          ) : (
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block ml-1" />
          )}
        </button>
        <button
          onClick={() => setActiveSubTab('manual')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            activeSubTab === 'manual'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          ANALYSE SPECIFIC UPDATE (Manual Entry)
        </button>
      </div>

      {/* Gmail Ingestion View Subtab */}
      {activeSubTab === 'gmail' && (
        <GmailIngestionView
          gmailState={gmailState}
          onStateChange={onGmailStateChange}
          briefingDate={briefingDate}
          setBriefingDate={setBriefingDate}
          onImportBriefing={onImportBriefingFromText}
          isExtracting={isExtracting}
          extractionError={extractionError}
          onSwitchToDemoMode={onLoadDemo}
          isLiveSystem={isLive}
          briefingSource={briefingSource}
          isDemoMode={isDemoMode}
          activeBriefingInfo={activeBriefingInfo}
          onLogAudit={onLogAudit}
        />
      )}

      {/* Extracted Updates List */}
      {activeSubTab === 'extracted' && (
        <div className="space-y-4">
          {/* SOURCE PROVENANCE CARD */}
          {sampleProvenance && (
            <div className="bg-slate-900 text-white border border-slate-800 rounded-2xl p-5 text-xs shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
                <span className="font-bold uppercase tracking-wider text-teal-400 flex items-center space-x-2 text-[11px]">
                  <FileCheck className="w-4 h-4" />
                  <span>SOURCE PROVENANCE & VERIFICATION AUDIT TRAIL</span>
                </span>
                <span className="bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded-full text-[10px] font-mono">
                  Audit ID: {updates[0].id}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-slate-300">
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Source Type</span>
                  <span className="font-bold text-white">{sampleProvenance.sourceType}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Subject Header</span>
                  <span className="font-semibold text-white truncate block">{sampleProvenance.emailSubject}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Received Date/Time</span>
                  <span className="font-mono text-slate-200 text-[11px]">{sampleProvenance.emailReceivedDateTime}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Imported Date/Time</span>
                  <span className="font-mono text-slate-200 text-[11px]">{sampleProvenance.importedDateTime}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Extracted Count</span>
                  <span className="font-bold text-teal-300">{sampleProvenance.extractedCount} Updates</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">Official Check</span>
                  <span className="font-bold text-amber-300">{sampleProvenance.authoritativeSourceCheck}</span>
                </div>
              </div>
            </div>
          )}
          {updates.length === 0 ? (
            <div className="text-center py-12 bg-white border border-slate-200 rounded-2xl p-6">
              <Mail className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800">No Professional Briefing Loaded Yet</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                Click "IMPORT TODAY'S BRIEFING" to search Gmail or click "LOAD DEMO BRIEFING" to load 5 sample regulatory updates.
              </p>
              <div className="mt-4 flex justify-center space-x-3">
                <button
                  onClick={onLoadDemo}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
                >
                  Load Demo Briefing
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {updates.map((upd) => (
                <div
                  key={upd.id}
                  className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs hover:border-teal-400 hover:shadow-md transition-all relative flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="px-2.5 py-0.5 bg-teal-50 text-teal-800 font-bold text-[10px] rounded-md border border-teal-200">
                          {upd.category}
                        </span>
                        <span className="text-[11px] text-slate-500 font-medium">{upd.nature}</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          upd.riskLevel === 'Critical'
                            ? 'bg-rose-100 text-rose-700 border border-rose-200'
                            : upd.riskLevel === 'High'
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : 'bg-teal-100 text-teal-700 border border-teal-200'
                        }`}
                      >
                        {upd.riskLevel} Risk
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 leading-snug">{upd.title}</h3>

                    <div className="mt-3 p-3 bg-slate-50 rounded-xl text-xs space-y-1.5 border border-slate-100">
                      <div>
                        <span className="font-semibold text-slate-700">Authority:</span>{' '}
                        <span className="text-slate-600">{upd.issuingAuthority}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-700">Reference:</span>{' '}
                        <span className="text-slate-600 font-mono text-[11px]">{upd.referenceNo}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-700">Source Facts:</span>{' '}
                        <span className="text-slate-600 line-clamp-2">{upd.sourceFacts}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <div className="text-[11px] text-slate-500">
                      Verification:{' '}
                      <span className="font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                        {upd.verificationStatus}
                      </span>
                    </div>
                    <div className="text-[11px] text-rose-600 font-bold">
                      Deadline: {upd.dates?.statutoryDeadline || upd.dates?.effectiveDate}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Manual Entry */}
      {activeSubTab === 'manual' && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs max-w-3xl">
          <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-600 mb-1">
            <FileEdit className="w-4 h-4" />
            <span>SECONDARY INPUT SOURCE — MANUAL CIRCULAR ANALYSIS</span>
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-4">ANALYSE SPECIFIC UPDATE</h2>

          {manualSuccessMsg && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Update analyzed with Gemini and added to Update Inbox!</span>
            </div>
          )}

          <form onSubmit={handleManualSubmit} className="space-y-4 text-xs">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Title of Circular / Development *</label>
              <input
                type="text"
                required
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                placeholder="e.g. GST Notification on Rule 88C DRC-01B Mismatch Notices"
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Issuing Authority / Source *</label>
                <input
                  type="text"
                  required
                  value={manualSource}
                  onChange={(e) => setManualSource(e.target.value)}
                  placeholder="e.g. CBIC / CBDT / MCA / RBI"
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Date *</label>
                <input
                  type="date"
                  required
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Reference / Circular Number</label>
                <input
                  type="text"
                  value={manualRefNo}
                  onChange={(e) => setManualRefNo(e.target.value)}
                  placeholder="e.g. Circular No. 219/13/2026-GST"
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">URL / Link</label>
                <input
                  type="url"
                  value={manualUrl}
                  onChange={(e) => setManualUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
                />
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Full Update Text / Press Release *</label>
              <textarea
                required
                rows={5}
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                placeholder="Paste the full circular text, press release, or notification content here..."
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:border-teal-500"
              />
            </div>

            <button
              type="submit"
              className="flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs px-5 py-3 rounded-xl shadow-md transition-all cursor-pointer"
            >
              <Send className="w-4 h-4" />
              <span>ANALYSE UPDATE NOW</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
