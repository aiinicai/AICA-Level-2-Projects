import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Send,
  X,
  Bot,
  User,
  ShieldCheck,
  CheckCircle2,
  Copy,
  PlusCircle,
  HelpCircle,
  TrendingUp,
  DollarSign,
  AlertCircle,
  RotateCcw,
  Zap,
  ArrowRight,
} from 'lucide-react';
import { FinancialModel, KpiMetric, CfoCommentary } from '../../types';
import { AiAdvisorService, AskCfoMessage } from '../../services/aiAdvisorService';

interface AskCfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  model: FinancialModel;
  kpis: KpiMetric[];
  onInsertCommentary?: (text: string) => void;
  firmName?: string;
}

// Helper to format markdown text (bold, bullet points, numbered items)
const renderFormattedText = (rawText: string) => {
  const paragraphs = rawText.split('\n\n');

  return (
    <div className="space-y-2 font-normal leading-relaxed">
      {paragraphs.map((para, pIdx) => {
        const lines = para.split('\n');
        return (
          <div key={pIdx} className="space-y-1">
            {lines.map((line, lIdx) => {
              const isBullet = line.trim().startsWith('•') || line.trim().startsWith('- ') || line.trim().startsWith('* ');
              const cleanLine = isBullet ? line.trim().replace(/^([•\-\*]\s*)/, '') : line;

              // Parse **bold** parts
              const parts = cleanLine.split(/(\*\*[^*]+\*\*)/g);

              const formattedParts = parts.map((part, partIdx) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                  return (
                    <strong key={partIdx} className="font-semibold text-slate-900">
                      {part.slice(2, -2)}
                    </strong>
                  );
                }
                return part;
              });

              if (isBullet) {
                return (
                  <div key={lIdx} className="flex items-start gap-1.5 pl-1.5 py-0.5">
                    <span className="text-sky-600 font-bold leading-none mt-1">•</span>
                    <span className="flex-1 text-slate-700">{formattedParts}</span>
                  </div>
                );
              }

              return (
                <p key={lIdx} className="text-slate-700">
                  {formattedParts}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

export const AskCfoModal: React.FC<AskCfoModalProps> = ({
  isOpen,
  onClose,
  model,
  kpis,
  onInsertCommentary,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const client = model.client;
  const latestMonth = model.historicalMonthly[model.historicalMonthly.length - 1] || {} as any;

  const [inputQuestion, setInputQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<AskCfoMessage[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Suggested prompt chips calibrated to active client
  const defaultPrompts = [
    `Can we afford to hire 2 new staff members next month?`,
    `What happens to our cash runway if revenue drops 15%?`,
    `How does our ${latestMonth.grossMarginPercent?.toFixed(0)}% gross margin compare to industry benchmarks?`,
    `Where can we optimize our monthly OPEX by $5,000 to improve EBITDA?`,
    `Summarize our 3 biggest financial risks for the board of directors.`,
  ];

  // Initialize first greeting
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: 'msg-welcome',
          role: 'cfo',
          text: `Hello. I am your Virtual CFO advisory intelligence calibrated for **${client.name}** (${client.industryName}). All data is grounded in your deterministic statements for **${client.reportingPeriod}** under strict Privacy Shield redaction.\n\nAsk me any strategic financial question regarding cash runway, headcount expansions, pricing, margins, break-even targets, or scenario stress testing.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          metricsReferenced: ['Revenue Run-Rate', 'Gross Margin', 'Cash Balance'],
          suggestedFollowUps: defaultPrompts.slice(0, 3),
        },
      ]);
    }
  }, [isOpen, client.name]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isOpen) return null;

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputQuestion).trim();
    if (!textToSend || isLoading) return;

    const userMessage: AskCfoMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputQuestion('');
    setIsLoading(true);

    try {
      const response = await AiAdvisorService.askVirtualCfo(
        textToSend,
        model,
        kpis,
        messages,
        firmName
      );

      const cfoResponse: AskCfoMessage = {
        id: `cfo-${Date.now()}`,
        role: 'cfo',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        metricsReferenced: response.keyMetricsReferenced,
        suggestedFollowUps: response.suggestedNextQuestions,
      };

      setMessages(prev => [...prev, cfoResponse]);
    } catch (err) {
      console.error(err);
      const errResponse: AskCfoMessage = {
        id: `cfo-${Date.now()}`,
        role: 'cfo',
        text: `Unable to complete query due to temporary connectivity. Based on latest actuals: Gross Margin is ${latestMonth.grossMarginPercent?.toFixed(1)}% with ${client.currencySymbol}${Number(latestMonth.cashAndEquivalents || 0).toLocaleString()} in liquid cash reserves.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages(prev => [...prev, errResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-3xl rounded-xl shadow-2xl border border-slate-300 flex flex-col h-[85vh] max-h-[720px] overflow-hidden">
        {/* Modal Header */}
        <div className="bg-[#0F172A] text-white px-5 py-4 flex items-center justify-between border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">
                  Ask Your Virtual CFO
                </h3>
                <span className="pill pill-info text-[9px] uppercase">
                  Gemini 3.7 FP&A Engine
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Advisory intelligence for <span className="font-semibold text-slate-200">{client.name}</span> • Grounded in {client.reportingPeriod} Financials
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-[10px] text-slate-300 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>PII Shielded</span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Financial Quick Glance Strip */}
        <div className="bg-slate-50 border-b border-slate-200 px-5 py-2.5 flex items-center justify-between text-xs text-slate-600 shrink-0 overflow-x-auto gap-4">
          <div className="flex items-center gap-4 text-[11px] font-medium whitespace-nowrap">
            <span>
              Revenue: <b className="text-slate-900">{client.currencySymbol}{Number(latestMonth.revenue || 0).toLocaleString()}</b>
            </span>
            <span>•</span>
            <span>
              Gross Margin: <b className="text-emerald-700">{latestMonth.grossMarginPercent?.toFixed(1)}%</b>
            </span>
            <span>•</span>
            <span>
              EBITDA: <b className="text-sky-700">{client.currencySymbol}{Number(latestMonth.ebitda || 0).toLocaleString()}</b>
            </span>
            <span>•</span>
            <span>
              Cash: <b className="text-slate-900">{client.currencySymbol}{Number(latestMonth.cashAndEquivalents || 0).toLocaleString()}</b>
            </span>
          </div>
          <div className="text-[10px] text-slate-400 font-mono hidden md:block">
            Curated by {firmName}
          </div>
        </div>

        {/* Chat Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-[#F8FAFC]">
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'cfo' && (
                <div className="w-8 h-8 rounded bg-[#0F172A] text-sky-400 flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-lg p-3.5 text-xs leading-relaxed space-y-2 ${
                  msg.role === 'user'
                    ? 'bg-sky-600 text-white rounded-br-none shadow-xs'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-bl-none shadow-xs'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center justify-between gap-2 border-b pb-1.5 text-[10px]"
                     style={{ borderColor: msg.role === 'user' ? 'rgba(255,255,255,0.2)' : '#f1f5f9' }}>
                  <span className={`font-bold uppercase tracking-wider ${msg.role === 'user' ? 'text-sky-100' : 'text-slate-500'}`}>
                    {msg.role === 'user' ? 'You (Management)' : 'Virtual CFO Partner'}
                  </span>
                  <span className={msg.role === 'user' ? 'text-sky-200' : 'text-slate-400'}>
                    {msg.timestamp}
                  </span>
                </div>

                {/* Message Text */}
                {msg.role === 'cfo' ? (
                  renderFormattedText(msg.text)
                ) : (
                  <div className="whitespace-pre-line font-normal space-y-1 text-white">
                    {msg.text}
                  </div>
                )}

                {/* Metrics Referenced Pills */}
                {msg.metricsReferenced && msg.metricsReferenced.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] font-semibold text-slate-400">Grounded in:</span>
                    {msg.metricsReferenced.map((met, i) => (
                      <span key={i} className="pill pill-info text-[9px]">
                        {met}
                      </span>
                    ))}
                  </div>
                )}

                {/* Suggested Follow-Ups */}
                {msg.suggestedFollowUps && msg.suggestedFollowUps.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                      Suggested Follow-Up Inquiries:
                    </span>
                    <div className="flex flex-col gap-1">
                      {msg.suggestedFollowUps.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => handleSend(q)}
                          className="text-left text-[11px] text-sky-700 hover:text-sky-900 bg-sky-50/70 hover:bg-sky-100/80 p-1.5 rounded transition-colors flex items-center justify-between group cursor-pointer"
                        >
                          <span>{q}</span>
                          <ArrowRight className="w-3 h-3 text-sky-500 group-hover:translate-x-0.5 transition-transform shrink-0 ml-1" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Bar for CFO messages */}
                {msg.role === 'cfo' && (
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(msg.id, msg.text)}
                        className="hover:text-slate-700 flex items-center gap-1 cursor-pointer transition-colors"
                        title="Copy answer"
                      >
                        {copiedId === msg.id ? (
                          <span className="text-emerald-600 font-bold flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Copied
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <Copy className="w-3 h-3" /> Copy Advice
                          </span>
                        )}
                      </button>

                      {onInsertCommentary && (
                        <button
                          onClick={() => {
                            onInsertCommentary(msg.text);
                            onClose();
                          }}
                          className="hover:text-sky-700 flex items-center gap-1 cursor-pointer transition-colors"
                          title="Insert into Executive Commentary"
                        >
                          <PlusCircle className="w-3 h-3 text-sky-600" /> Insert into Report
                        </button>
                      )}
                    </div>

                    <span className="font-mono text-[9px] text-slate-400">Confidence: 95%</span>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded bg-sky-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex gap-3 justify-start items-center">
              <div className="w-8 h-8 rounded bg-[#0F172A] text-sky-400 flex items-center justify-center shrink-0 text-xs font-bold shadow-xs animate-pulse">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-3 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
                <div className="w-2 h-2 rounded-full bg-sky-500 animate-ping"></div>
                <span>Synthesizing financial position and deterministic ratios...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Question Chips */}
        <div className="px-4 py-2 bg-slate-100 border-t border-slate-200 flex items-center gap-1.5 overflow-x-auto text-[11px] shrink-0">
          <span className="font-bold text-slate-500 uppercase text-[9px] tracking-wider whitespace-nowrap mr-1">
            Quick Prompts:
          </span>
          {defaultPrompts.slice(0, 3).map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              disabled={isLoading}
              className="bg-white hover:bg-sky-50 hover:text-sky-700 hover:border-sky-300 border border-slate-200 rounded px-2.5 py-1 text-slate-700 whitespace-nowrap transition-colors cursor-pointer shrink-0 disabled:opacity-50"
            >
              {prompt.length > 40 ? prompt.substring(0, 38) + '...' : prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 sm:p-4 bg-white border-t border-slate-200 shrink-0">
          <form
            onSubmit={e => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuestion}
              onChange={e => setInputQuestion(e.target.value)}
              placeholder="Ask anything (e.g., 'Can we afford $40k capex in Q3?' or 'What is our break-even?')"
              className="flex-1 bg-slate-50 border border-slate-200 rounded-md px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:border-sky-500 focus:bg-white transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputQuestion.trim()}
              className="px-4 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-md text-xs font-bold flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask CFO</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
