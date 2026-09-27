import React, { useState } from 'react';
import {
  AlertTriangle,
  Bot,
  Building2,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Lightbulb,
  Send,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  User,
} from 'lucide-react';
import {
  askCfoCopilot,
  CopilotResponse,
  CopilotStructuredItem,
  generateDeterministicCfoAnalysis,
} from '../services/copilotService';
import { DashboardMetrics, DischargeMonitorRow, FinancialException } from '../types';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface Message {
  id: string;
  sender: 'user' | 'copilot';
  text: string;
  response?: CopilotResponse;
  timestamp: string;
}

interface CfoCopilotViewProps {
  metrics: DashboardMetrics;
  exceptions: FinancialException[];
  dischargeMonitor: DischargeMonitorRow[];
  onSelectEncounter?: (encounterId: string) => void;
  onNavigateToTab?: (tab: string) => void;
  extraContext?: {
    pendingClearanceCount?: number;
    tariffVarianceExposure?: number;
    budgetVariance?: number;
    totalAR?: number;
    currentAR?: number;
    overdueAR?: number;
    ar90plus?: number;
    collectionRate?: number;
    knownPayers?: string[];
  };
}

export const CfoCopilotView: React.FC<CfoCopilotViewProps> = ({
  metrics,
  exceptions,
  dischargeMonitor,
  onSelectEncounter,
  onNavigateToTab,
  extraContext,
}) => {
  // 10 Grounded Executive CFO Quick Action Prompts
  const cannedQuestions = [
    'What needs my attention today?',
    'Which departments have the highest potential exposure?',
    'Why is Pharmacy showing high exceptions?',
    "Summarise today's financial risks.",
    'Which TPA claims need follow-up?',
    'Which departments have pending clearance?',
    'Where are the largest tariff variances?',
    'How is AR performing?',
    'Compare Budget vs Actual performance',
    'Generate CFO Daily Briefing',
  ];

  const initialWelcomeMessage: Message = {
    id: 'welcome',
    sender: 'copilot',
    text: `Good day, CFO. I am your Hospital Financial Control & Revenue Intelligence Assistant.
    
All financial calculations are strictly derived deterministically from the hospital's control engines (C01–C08, Departmental Clearance, Tariff Master, and Budget). I synthesize verified figures into executive briefings, department action items, and risk mitigations without speculation.`,
    timestamp: 'Just now',
  };

  const [messages, setMessages] = useState<Message[]>([initialWelcomeMessage]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedNoteId, setCopiedNoteId] = useState<string | null>(null);

  const handleCopyNote = (msgId: string, text: string, structured?: CopilotStructuredItem) => {
    let note = text;
    if (structured) {
      note += `\n\n--- EXECUTIVE MANAGEMENT NOTE ---\n• Responsible Unit: ${structured.responsibleDepartment}\n• Financial Exposure: ${structured.financialExposure}\n• Action Directive: ${structured.recommendedAction}\n• Affected Encounters: ${structured.affectedEncounters.join(', ')}`;
    }
    navigator.clipboard.writeText(note);
    setCopiedNoteId(msgId);
    setTimeout(() => setCopiedNoteId(null), 2500);
  };

  const handleSend = async (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await askCfoCopilot(query, metrics, exceptions, dischargeMonitor, extraContext);
      const copilotMsg: Message = {
        id: `copilot-${Date.now()}`,
        sender: 'copilot',
        text: response.answer,
        response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch {
      const activeExceptions = exceptions.filter(
        (e) => e.Status === 'OPEN' || e.Status === 'UNDER_REVIEW'
      );
      const latestDate = dischargeMonitor.map((d) => d.Discharge_Date).filter(Boolean).sort().reverse()[0];
      const dischargesRecent = latestDate
        ? dischargeMonitor.filter((d) => d.Discharge_Date === latestDate)
        : dischargeMonitor;
      const dischargesWithExceptions = dischargesRecent.filter((d) => d.Exception_Count > 0);
      const highestExpEnc = [...dischargeMonitor].sort((a, b) => b.Total_Exposure - a.Total_Exposure)[0];

      const fallback = generateDeterministicCfoAnalysis(query, {
        question: query,
        metrics,
        topExceptions: activeExceptions.slice(0, 8),
        dischargeSummary: {
          totalDischarges: dischargesRecent.length,
          withExceptions: dischargesWithExceptions.length,
          highestExposureEncounter: highestExpEnc
            ? `${highestExpEnc.Encounter_ID} (${formatINR(highestExpEnc.Total_Exposure)} in ${highestExpEnc.Department})`
            : 'None',
        },
        extraContext,
      });

      const copilotMsg: Message = {
        id: `copilot-${Date.now()}`,
        sender: 'copilot',
        text: fallback.answer,
        response: fallback,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const hasFinancialData =
    (metrics?.grossBilling > 0 || exceptions.length > 0 || dischargeMonitor.length > 0);

  if (!hasFinancialData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            CFO Copilot Intelligence Desk
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            AI-assisted financial control analytics, audit preparation, and executive decision support.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No Financial Data for Copilot Analysis"
          description="CFO Copilot generates briefings, exposure assessments, and executive notes grounded strictly in your hospital's uploaded data. Upload your financial extracts to activate AI review."
          badge="Copilot Standby"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Billing Invoices & Revenue Registers',
            'Inpatient Encounters & Discharge Status',
            'Clinical Orders & Tariff Master',
            'TPA Claims & Adjudications',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header & Verification Compliance Banner */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">Hospital CFO Grounded Copilot</h2>
                <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3 text-emerald-600" />
                  Deterministic Grounding Enforced
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Agentic financial decision-support strictly synthesizing deterministic control outcomes. Zero invented numbers.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-slate-700">
              <span className="text-slate-500">Verified Exposure: </span>
              <strong className="text-amber-900 font-bold">
                {formatINR(metrics.potentialFinancialExposure)}
              </strong>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-slate-700">
              <span className="text-slate-500">Active Exceptions: </span>
              <strong className="text-teal-800 font-bold">{metrics.openExceptionsCount}</strong>
            </div>
          </div>
        </div>

        {/* Quick Executive Questions Prompts */}
        <div className="mt-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-teal-600" />
            Grounded CFO Quick Action Prompts:
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {cannedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                disabled={isLoading}
                className="rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-teal-500 p-2 text-xs font-medium text-slate-700 transition text-left active:scale-95 disabled:opacity-50 shadow-2xs cursor-pointer truncate"
                title={q}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Conversation Stream */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 min-h-[460px] flex flex-col justify-between shadow-xs">
        <div className="space-y-5 max-h-[520px] overflow-y-auto pr-2">
          {messages.map((msg) => {
            const isCopilot = msg.sender === 'copilot';
            const structured = msg.response?.structuredData;

            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isCopilot ? 'items-start' : 'items-start flex-row-reverse'}`}
              >
                {/* Avatar */}
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                    isCopilot
                      ? 'bg-teal-50 text-teal-700 border border-teal-200'
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  }`}
                >
                  {isCopilot ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                </div>

                {/* Bubble */}
                <div
                  className={`max-w-3xl rounded-xl p-4 text-xs leading-relaxed space-y-3 ${
                    isCopilot
                      ? 'border border-slate-200 bg-slate-50 text-slate-800 shadow-2xs w-full'
                      : 'border border-teal-200 bg-teal-50/50 text-teal-950 shadow-2xs'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 text-[10px] text-slate-500 border-b border-slate-200 pb-1.5">
                    <span className="font-semibold text-slate-700">
                      {isCopilot ? 'Hospital CFO Copilot Intelligence' : 'Chief Financial Officer'}
                    </span>
                    <div className="flex items-center gap-2">
                      <span>{msg.timestamp}</span>
                      {isCopilot && (
                        <button
                          onClick={() => handleCopyNote(msg.id, msg.text, structured)}
                          className="flex items-center gap-1 rounded bg-white hover:bg-slate-100 text-[10px] text-teal-800 border border-slate-200 px-2 py-0.5 transition cursor-pointer"
                        >
                          {copiedNoteId === msg.id ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-600" />
                              <span className="text-emerald-700 font-semibold">Copied Note</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              <span>Copy to Management Note</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* STRUCTURED RESPONSE CARD (Every Response Requirement) */}
                  {structured && (
                    <div className="rounded-lg border border-teal-200 bg-white p-3 space-y-2 shadow-2xs">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-teal-900 border-b border-teal-100 pb-1 flex items-center justify-between">
                        <span>Executive Synthesis &amp; Grounded Action Directive</span>
                        <span className="text-amber-900 font-bold">{structured.financialExposure} Exposure</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-500 block text-[10px] uppercase">Grounded Figures</span>
                          <span className="font-semibold text-slate-800">{structured.groundedFigures}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px] uppercase">Responsible Department</span>
                          <span className="font-bold text-teal-800">{structured.responsibleDepartment}</span>
                        </div>
                        <div className="sm:col-span-2">
                          <span className="text-slate-500 block text-[10px] uppercase">Recommended Action</span>
                          <span className="text-slate-900 font-medium">{structured.recommendedAction}</span>
                        </div>
                        {structured.affectedEncounters.length > 0 && (
                          <div className="sm:col-span-2 flex items-center gap-2">
                            <span className="text-slate-500 text-[10px] uppercase">Affected Encounters:</span>
                            <div className="flex flex-wrap gap-1">
                              {Array.from(new Set(structured.affectedEncounters)).map((encId, encIdx) => (
                                <button
                                  key={`${encId}-${encIdx}`}
                                  onClick={() => onSelectEncounter?.(encId)}
                                  className="font-mono text-[10px] font-bold text-teal-800 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded hover:bg-teal-100 transition cursor-pointer flex items-center gap-0.5"
                                >
                                  {encId} <ExternalLink className="h-2.5 w-2.5 opacity-60" />
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Message Body */}
                  <div className="space-y-2 whitespace-pre-wrap">
                    {msg.text.split('\n\n').map((block, idx) => {
                      if (block.startsWith('### 📋 FACTUAL DATA') || block.startsWith('### 📊 Calculated Deterministic Facts')) {
                        const title = block.startsWith('### 📋 FACTUAL DATA') ? 'FACTUAL DATA' : 'Calculated Deterministic Facts (Zero Hallucination)';
                        const content = block.replace(/^### [^\n]+\n/, '');
                        return (
                          <div
                            key={idx}
                            className="rounded-lg border border-teal-200 bg-teal-50/40 p-3 my-2"
                          >
                            <div className="text-xs font-bold text-teal-900 flex items-center gap-1.5 mb-2 uppercase tracking-wide">
                              <CheckCircle2 className="h-3.5 w-3.5 text-teal-600" />
                              {title}
                            </div>
                            <div className="space-y-1 text-slate-700 text-[11px] leading-normal font-sans">
                              {content
                                .split('\n')
                                .filter((line) => line.trim())
                                .map((line, lIdx) => (
                                  <div key={lIdx} className="flex items-start gap-1.5">
                                    <span className="text-teal-700 font-bold">•</span>
                                    <span>{line.replace(/^-\s*/, '')}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        );
                      }

                      if (block.startsWith('### 📐 CALCULATED METRIC')) {
                        const content = block.replace(/^### 📐 CALCULATED METRIC\n/, '');
                        return (
                          <div
                            key={idx}
                            className="rounded-lg border border-sky-200 bg-sky-50/40 p-3 my-2"
                          >
                            <div className="text-xs font-bold text-sky-900 flex items-center gap-1.5 mb-2 uppercase tracking-wide">
                              <ShieldCheck className="h-3.5 w-3.5 text-sky-600" />
                              CALCULATED METRIC
                            </div>
                            <div className="space-y-1 text-slate-700 text-[11px] leading-normal font-sans">
                              {content
                                .split('\n')
                                .filter((line) => line.trim())
                                .map((line, lIdx) => (
                                  <div key={lIdx} className="flex items-start gap-1.5">
                                    <span className="text-sky-700 font-bold">•</span>
                                    <span>{line.replace(/^-\s*/, '')}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        );
                      }

                      if (block.startsWith('### 💡 AI COMMENTARY') || block.startsWith('### 💡 Executive CFO Strategic Commentary')) {
                        const title = block.startsWith('### 💡 AI COMMENTARY') ? 'AI COMMENTARY' : 'Executive CFO Strategic Commentary & Action Items';
                        const content = block.replace(/^### [^\n]+\n/, '');
                        return (
                          <div
                            key={idx}
                            className="rounded-lg border border-amber-200 bg-amber-50/40 p-3 my-2"
                          >
                            <div className="text-xs font-bold text-amber-900 flex items-center gap-1.5 mb-2 uppercase tracking-wide">
                              <Lightbulb className="h-3.5 w-3.5 text-amber-600" />
                              {title}
                            </div>
                            <div className="space-y-1.5 text-slate-700 text-[11px] leading-normal">
                              {content
                                .split('\n')
                                .filter((line) => line.trim())
                                .map((line, lIdx) => (
                                  <div key={lIdx} className="flex items-start gap-1.5">
                                    <span className="text-amber-800 font-bold">&rarr;</span>
                                    <span>{line.replace(/^-\s*/, '')}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        );
                      }

                      if (block.startsWith('### 🎯 SUGGESTED ACTION')) {
                        const content = block.replace(/^### 🎯 SUGGESTED ACTION\n/, '');
                        return (
                          <div
                            key={idx}
                            className="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 my-2"
                          >
                            <div className="text-xs font-bold text-emerald-900 flex items-center gap-1.5 mb-2 uppercase tracking-wide">
                              <Check className="h-3.5 w-3.5 text-emerald-600" />
                              SUGGESTED ACTION
                            </div>
                            <div className="space-y-1.5 text-slate-700 text-[11px] leading-normal">
                              {content
                                .split('\n')
                                .filter((line) => line.trim())
                                .map((line, lIdx) => (
                                  <div key={lIdx} className="flex items-start gap-1.5">
                                    <span className="text-emerald-800 font-bold">✓</span>
                                    <span>{line.replace(/^-\s*/, '')}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        );
                      }

                      return <p key={idx}>{block}</p>;
                    })}
                  </div>

                  {/* Follow-up prompt buttons */}
                  {msg.response?.suggestedFollowUps && msg.response.suggestedFollowUps.length > 0 && (
                    <div className="pt-2 border-t border-slate-200 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] text-slate-500 font-medium">Follow-up:</span>
                      {msg.response.suggestedFollowUps.map((fu, fIdx) => (
                        <button
                          key={fIdx}
                          onClick={() => handleSend(fu)}
                          className="rounded bg-white hover:bg-slate-100 text-[10px] px-2 py-0.5 text-teal-800 border border-slate-300 transition shadow-2xs cursor-pointer"
                        >
                          {fu}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex gap-3 items-center text-xs text-slate-500 pl-2">
              <Bot className="h-4 w-4 animate-spin text-teal-600" />
              <span>Analyzing calculated control results &amp; generating executive brief...</span>
            </div>
          )}
        </div>

        {/* Query Input Box */}
        <div className="mt-4 pt-3 border-t border-slate-100">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(inputText);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask CFO Copilot about revenue capture, tariff variances, working capital, departmental clearance..."
              disabled={isLoading}
              className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs text-slate-900 placeholder-slate-400 focus:border-teal-600 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="flex items-center gap-1.5 rounded-xl bg-teal-700 hover:bg-teal-800 disabled:opacity-50 px-4 py-2.5 text-xs font-semibold text-white transition shadow-xs active:scale-95 cursor-pointer"
            >
              <span>Ask Copilot</span>
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
          <div className="mt-2 text-[10px] text-slate-500 flex items-center justify-between">
            <span>
              Mandate: AI receives pre-calculated numbers from deterministic control engine; zero independent financial calculations.
            </span>
            <span>Indian Financial Conventions (₹, Lakhs, Crores) &bull; Grounded Deterministic Accounting Data</span>
          </div>
        </div>
      </div>
    </div>
  );
};
